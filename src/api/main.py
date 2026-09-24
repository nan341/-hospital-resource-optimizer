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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from src.api.db import get_db, SessionLocal
from src.db.models import Department, Bed, Staff, DiagnosticFacility, Patient, EventLog
from src.db.init_db import init_database
from src.api.auth import login_with_role, require_role, ADMIN_PASSWORD, STAFF_ACCESS_CODE, SPABrowserNavigation
from src.api.schemas import (
    DepartmentResponse,
    DiagnosticFacilityResponse,
    SurgeRequest,
    SimulationControlRequest,
    SimulationStatusResponse,
    ForecastResponse
)
from src.api.routes import patients, beds, staff, events, patient_portal, staff_portal, case_log
from src.data_pipeline.synthetic_generator import simulator
from src.allocation.engine import allocation_engine
from src.allocation.appointment_engine import appointment_scheduler
from src.models.forecasting import forecaster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import time

# Demo Admin Token configuration
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", os.getenv("ADMIN_PASSWORD", "changeme"))

# Rate-limiting state for demo protection: { "ip:action": timestamp }
_rate_limit_state: Dict[str, float] = {}

def check_rate_limit(request: Request, action: str, cooldown_seconds: float = 2.0):
    """Enforces a lightweight in-memory rate limit per IP per action."""
    client_ip = request.client.host if request.client else "unknown"
    if client_ip == "testclient":
        return
    key = f"{client_ip}:{action}"
    now_ts = time.time()
    last_ts = _rate_limit_state.get(key, 0.0)
    if (now_ts - last_ts) < cooldown_seconds:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please wait {cooldown_seconds}s before triggering '{action}' again."
        )
    _rate_limit_state[key] = now_ts

# Idle activity tracking for automatic demo baseline reset
last_activity_time = datetime.now()

def mark_activity():
    global last_activity_time
    last_activity_time = datetime.now()

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

                from sqlalchemy import or_
                all_staff = []
                for s in session.query(Staff).all():
                    active_count = session.query(Patient).filter(
                        or_(
                            Patient.assigned_doctor_id == s.staff_id,
                            Patient.assigned_nurse_id == s.staff_id,
                            Patient.assigned_staff_id == s.staff_id
                        ),
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
                        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                        "event_type": e.event_type,
                        "entity_id": e.entity_id,
                        "description": e.description,
                        "triggered_by": e.triggered_by
                    }
                    for e in session.query(EventLog).order_by(EventLog.timestamp.desc(), EventLog.event_id.desc()).limit(30).all()
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

            # Check for idle auto-reset if no active ws connections, sim stopped, and 10 mins elapsed
            if not simulator.is_running and len(manager.active_connections) == 0:
                elapsed_idle = (datetime.now() - last_activity_time).total_seconds()
                if elapsed_idle >= 600.0:
                    session = SessionLocal()
                    try:
                        waiting_count = session.query(Patient).filter(Patient.status == "waiting").count()
                        if waiting_count > 0:
                            logger.info("Auto-reset triggered due to 10 minutes of inactivity.")
                            init_database(drop_existing=True)
                            mark_activity()
                    finally:
                        session.close()
            else:
                mark_activity()

        except Exception as e:
            logger.error(f"Error in background worker loop: {e}", exc_info=True)

        await asyncio.sleep(2.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database exists & self-heals if empty
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

# CORS configuration - configurable via CORS_ORIGINS
raw_cors = os.getenv("CORS_ORIGINS", "*")
cors_origins = ["*"] if raw_cors.strip() == "*" else [orig.strip() for orig in raw_cors.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# HEALTH CHECK ENDPOINT
# ==========================================
@app.get("/health", tags=["system"])
def health_check():
    """Health check endpoint for container readiness and load balancers."""
    return {"status": "ok"}

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

# Consolidated Case Log & Clinical Notes (Self-authenticating: Admin or Assigned Clinician)
app.include_router(case_log.router)

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
def start_simulation(request: Request, body: Optional[SimulationControlRequest] = None):
    check_rate_limit(request, "start_sim", cooldown_seconds=2.0)
    mark_activity()
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
    mark_activity()
    simulator.stop()
    return {"status": "stopped", "message": "Simulation paused."}

@app.post("/simulation/surge", tags=["simulation"], dependencies=[Depends(require_role("admin"))])
def trigger_surge(request: Request, req: SurgeRequest, db: Session = Depends(get_db)):
    check_rate_limit(request, "surge", cooldown_seconds=2.5)
    mark_activity()
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

@app.post("/simulation/reset", tags=["simulation"])
def reset_system(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    auth_token: Optional[dict] = Depends(require_role("admin"))
):
    """
    Resets the database to initial seed capacity. Requires X-Admin-Token header matching ADMIN_TOKEN.
    """
    if not x_admin_token or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo Protection: Resetting the hospital system requires a valid X-Admin-Token header."
        )
    simulator.stop()
    init_database(drop_existing=True)
    mark_activity()
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
    mark_activity()
    try:
        while True:
            data = await websocket.receive_text()
            mark_activity()
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

# ==========================================
# STATIC FILES & SPA FALLBACK (PRODUCTION DEMO)
# ==========================================
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
if os.path.exists(dist_dir):
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.exception_handler(SPABrowserNavigation)
    async def spa_browser_navigation_handler(request: Request, exc: SPABrowserNavigation):
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=401, detail="Missing Authorization header.")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Serve static file from dist if it exists
        file_path = os.path.join(dist_dir, full_path)
        if full_path and os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Fallback to SPA index.html for all client routes
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)

        raise HTTPException(status_code=404, detail="File not found")
