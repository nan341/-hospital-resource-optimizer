import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from pydantic import BaseModel

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.api.db import get_db, SessionLocal
from src.db.models import Department, Bed, Staff, DiagnosticFacility, Patient, EventLog
from src.db.init_db import init_database
from src.api.auth import login_with_role, require_role, ADMIN_PASSWORD, STAFF_ACCESS_CODE
from src.api.schemas import (
    DepartmentResponse,
    DiagnosticFacilityResponse,
    SurgeRequest,
    SimulationControlRequest,
    SimulationStatusResponse,
    ForecastResponse
)
from src.api.routes import patients, beds, staff, events, patient_portal, staff_portal
from src.data_pipeline.synthetic_generator import simulator
from src.allocation.engine import allocation_engine
from src.allocation.appointment_engine import appointment_scheduler
from src.models.forecasting import forecaster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Login Request Schema
class LoginRequest(BaseModel):
    password: str

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending message to websocket client: {e}")
                disconnected.append(connection)
        for dead in disconnected:
            self.disconnect(dead)

manager = ConnectionManager()

# Background Worker Loop
async def background_allocation_and_broadcast_worker():
    """Periodically runs allocation engine, outpatient queue advancement, and broadcasts state to WebSocket clients."""
    logger.info("Starting background allocation and broadcast worker...")
    while True:
        try:
            # 1. Run simulation step if active
            if simulator.is_running:
                await simulator.run_simulation_step(time_step_seconds=3.0)

            # 2. Run allocation engine & appointment queue advancement
            session = SessionLocal()
            try:
                alloc_res = allocation_engine.run_allocation_cycle(session)
                apt_res = appointment_scheduler.advance_queue(session)

                # 3. Gather snapshot for live WebSocket broadcast
                departments = session.query(Department).all()
                dept_data = []
                for d in departments:
                    occ = session.query(Bed).filter_by(department_id=d.department_id, status="occupied").count()
                    avail = session.query(Bed).filter_by(department_id=d.department_id, status="available").count()
                    free_diag = session.query(DiagnosticFacility).filter_by(department_id=d.department_id, status="free").count()
                    tot_diag = session.query(DiagnosticFacility).filter_by(department_id=d.department_id).count()
                    on_duty = session.query(Staff).filter(
                        Staff.department_id == d.department_id,
                        Staff.status.in_(["on_duty", "reassigned"])
                    ).count()
                    dept_data.append({
                        "department_id": d.department_id,
                        "name": d.name,
                        "total_beds": d.total_beds,
                        "occupied_beds": occ,
                        "available_beds": avail,
                        "free_diagnostics": free_diag,
                        "total_diagnostics": tot_diag,
                        "on_duty_staff": on_duty
                    })

                all_beds = [
                    {
                        "bed_id": b.bed_id,
                        "department_id": b.department_id,
                        "bed_type": b.bed_type,
                        "status": b.status,
                        "current_patient_id": b.current_patient_id
                    }
                    for b in session.query(Bed).all()
                ]

                all_staff = []
                for s in session.query(Staff).all():
                    active_count = session.query(Patient).filter(
                        Patient.assigned_staff_id == s.staff_id,
                        Patient.status == "admitted"
                    ).count()
                    all_staff.append({
                        "staff_id": s.staff_id,
                        "role": s.role,
                        "department_id": s.department_id,
                        "status": s.status,
                        "shift_start": s.shift_start,
                        "shift_end": s.shift_end,
                        "floor": s.floor,
                        "room_number": s.room_number,
                        "specialty": s.specialty,
                        "active_patients": active_count,
                        "is_busy": active_count > 0
                    })

                waiting_patients = [
                    {
                        "patient_id": p.patient_id,
                        "department_needed": p.department_needed,
                        "severity": p.severity,
                        "predicted_stay_hours": p.predicted_stay_hours,
                        "arrival_time": p.arrival_time.isoformat(),
                        "age": p.age,
                        "reason_for_visit": p.reason_for_visit
                    }
                    for p in session.query(Patient).filter_by(status="waiting").order_by(Patient.arrival_time.asc()).all()
                ]

                recent_events = [
                    {
                        "event_id": e.event_id,
                        "timestamp": e.timestamp.strftime("%H:%M:%S"),
                        "event_type": e.event_type,
                        "entity_id": e.entity_id,
                        "description": e.description,
                        "triggered_by": e.triggered_by
                    }
                    for e in session.query(EventLog).order_by(EventLog.timestamp.desc()).limit(30).all()
                ]

                diagnostics_data = [
                    {
                        "facility_id": df.facility_id,
                        "type": df.type,
                        "department_id": df.department_id,
                        "status": df.status,
                        "current_patient_id": df.current_patient_id
                    }
                    for df in session.query(DiagnosticFacility).all()
                ]

                forecasts_data = {}
                for d in departments:
                    if d.total_beds > 0:
                        fc = forecaster.predict_next_hours(session, d.department_id, horizon_hours=2)
                        forecasts_data[d.department_id] = fc

                payload = {
                    "type": "state_update",
                    "timestamp": datetime.now().isoformat(),
                    "departments": dept_data,
                    "beds": all_beds,
                    "staff": all_staff,
                    "waiting_patients": waiting_patients,
                    "recent_events": recent_events,
                    "diagnostics": diagnostics_data,
                    "forecasts": forecasts_data,
                    "allocation_cycle": alloc_res,
                    "appointment_cycle": apt_res,
                    "simulation": {
                        "is_running": simulator.is_running,
                        "speed_factor": simulator.speed_factor
                    }
                }

                if manager.active_connections:
                    await manager.broadcast(payload)

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error in background worker loop: {e}", exc_info=True)

        await asyncio.sleep(2.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database exists
    init_database()
    worker_task = asyncio.create_task(background_allocation_and_broadcast_worker())
    yield
    # Shutdown
    worker_task.cancel()
    simulator.stop()

app = FastAPI(
    title="Intelligent Hospital Resource Optimizer API",
    description="Real-time demand forecasting, dynamic priority-queue bed allocation, outpatient appointment scheduling, and role-separated hospital orchestration.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration - Allow all origins for LAN cross-device access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# PUBLIC AUTHENTICATION ENDPOINTS
# ==========================================
@app.post("/admin/login", tags=["auth"])
def admin_login(body: LoginRequest):
    """
    Authenticates administrator password and returns a signed 8-hour admin JWT token.
    """
    token = login_with_role(body.password, ADMIN_PASSWORD, role="admin")
    return {"token": token, "role": "admin"}

@app.post("/staff/login", tags=["auth"])
def staff_login(body: LoginRequest):
    """
    Authenticates staff access code and returns a signed 8-hour staff JWT token.
    """
    token = login_with_role(body.password, STAFF_ACCESS_CODE, role="staff")
    return {"token": token, "role": "staff"}

# ==========================================
# ROUTER REGISTRATION
# ==========================================
# Public Patient Portal (No Auth)
app.include_router(patient_portal.router)

# Staff Portal (Requires Staff Role Token)
app.include_router(staff_portal.router)

# Protected Admin Sub-routers (Require Admin Role Token)
app.include_router(patients.router, dependencies=[Depends(require_role("admin"))])
app.include_router(beds.router, dependencies=[Depends(require_role("admin"))])
app.include_router(staff.router, dependencies=[Depends(require_role("admin"))])
app.include_router(events.router, dependencies=[Depends(require_role("admin"))])

# ==========================================
# PROTECTED ADMIN DATA ENDPOINTS
# ==========================================
@app.get("/departments", response_model=List[DepartmentResponse], tags=["departments"], dependencies=[Depends(require_role("admin"))])
def get_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).all()
    results = []
    for d in departments:
        occupied = db.query(Bed).filter(Bed.department_id == d.department_id, Bed.status == "occupied").count()
        available = db.query(Bed).filter(Bed.department_id == d.department_id, Bed.status == "available").count()
        cleaning = db.query(Bed).filter(Bed.department_id == d.department_id, Bed.status == "cleaning").count()
        reserved = db.query(Bed).filter(Bed.department_id == d.department_id, Bed.status == "reserved").count()
        on_duty = db.query(Staff).filter(Staff.department_id == d.department_id, Staff.status.in_(["on_duty", "reassigned"])).count()
        total_diag = db.query(DiagnosticFacility).filter(DiagnosticFacility.department_id == d.department_id).count()
        free_diag = db.query(DiagnosticFacility).filter(DiagnosticFacility.department_id == d.department_id, DiagnosticFacility.status == "free").count()

        occ_rate = round((occupied / d.total_beds), 3) if d.total_beds > 0 else 0.0

        results.append(DepartmentResponse(
            department_id=d.department_id,
            name=d.name,
            total_beds=d.total_beds,
            total_staff_slots=d.total_staff_slots,
            occupied_beds=occupied,
            available_beds=available,
            cleaning_beds=cleaning,
            reserved_beds=reserved,
            occupancy_rate=occ_rate,
            on_duty_staff=on_duty,
            total_diagnostics=total_diag,
            free_diagnostics=free_diag
        ))
    return results

@app.get("/diagnostics", response_model=List[DiagnosticFacilityResponse], tags=["diagnostics"], dependencies=[Depends(require_role("admin"))])
def get_diagnostics(
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    db: Session = Depends(get_db)
):
    query = db.query(DiagnosticFacility)
    if department_id:
        query = query.filter(DiagnosticFacility.department_id == department_id)
    return query.order_by(DiagnosticFacility.facility_id).all()

# Demand forecast endpoint (Public)
@app.get("/forecast/{department_id}", response_model=ForecastResponse, tags=["forecasting"])
def get_department_forecast(
    department_id: str,
    horizon_hours: int = Query(2, ge=1, le=24, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
):
    dept = db.query(Department).filter_by(department_id=department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department '{department_id}' not found")

    forecast = forecaster.predict_next_hours(db, department_id, horizon_hours=horizon_hours)
    return ForecastResponse(**forecast)

# ==========================================
# PROTECTED SIMULATION CONTROL ENDPOINTS
# ==========================================
@app.post("/simulation/start", tags=["simulation"], dependencies=[Depends(require_role("admin"))])
def start_simulation(body: Optional[SimulationControlRequest] = None):
    if body and body.speed_factor:
        simulator.speed_factor = body.speed_factor
    simulator.is_running = True
    return {
        "status": "started",
        "speed_factor": simulator.speed_factor,
        "message": "Synthetic patient arrival simulation started."
    }

@app.post("/simulation/stop", tags=["simulation"], dependencies=[Depends(require_role("admin"))])
def stop_simulation():
    simulator.stop()
    return {"status": "stopped", "message": "Simulation paused."}

@app.post("/simulation/surge", tags=["simulation"], dependencies=[Depends(require_role("admin"))])
def trigger_surge(req: SurgeRequest, db: Session = Depends(get_db)):
    dept = db.query(Department).filter_by(department_id=req.department).first()
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department '{req.department}' not found")

    created = simulator.execute_surge_now(req.department, req.patient_count)
    alloc_result = allocation_engine.run_allocation_cycle(db)

    return {
        "status": "surge_triggered",
        "department": req.department,
        "patient_count": len(created),
        "allocation_result": alloc_result,
        "message": f"Successfully triggered surge of {len(created)} critical patients in {dept.name}."
    }

@app.post("/simulation/reset", tags=["simulation"], dependencies=[Depends(require_role("admin"))])
def reset_system():
    simulator.stop()
    init_database(drop_existing=True)
    return {"status": "reset_completed", "message": "Hospital system database reset to initial seeded state."}

@app.get("/simulation/status", response_model=SimulationStatusResponse, tags=["simulation"], dependencies=[Depends(require_role("admin"))])
def get_simulation_status(db: Session = Depends(get_db)):
    total_pts = db.query(Patient).count()
    queue_len = db.query(Patient).filter_by(status="waiting").count()
    active_adm = db.query(Patient).filter_by(status="admitted").count()

    return SimulationStatusResponse(
        is_running=simulator.is_running,
        speed_factor=simulator.speed_factor,
        simulated_time=simulator.current_sim_time.strftime("%Y-%m-%d %H:%M:%S"),
        total_patients_generated=total_pts,
        queue_length=queue_len,
        active_admissions=active_adm
    )

# ==========================================
# REAL-TIME WEBSOCKET ENDPOINT (PUBLIC)
# ==========================================
@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "surge":
                    dept = msg.get("department", "er")
                    cnt = int(msg.get("count", 5))
                    simulator.execute_surge_now(dept, cnt)
                elif msg.get("action") == "start":
                    simulator.is_running = True
                elif msg.get("action") == "stop":
                    simulator.stop()
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
