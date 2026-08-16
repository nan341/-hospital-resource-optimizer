import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from src.api.db import get_db
from src.db.models import Patient, Department, EventLog
from src.api.schemas import PatientResponse, PatientIntakeRequest, PatientIntakeResponse

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("", response_model=List[PatientResponse])
def get_patients(
    status: Optional[str] = Query(None, description="Filter by status: waiting, admitted, discharged"),
    department_id: Optional[str] = Query(None, description="Filter by department_needed"),
    db: Session = Depends(get_db)
):
    query = db.query(Patient)
    if status:
        query = query.filter(Patient.status == status)
    if department_id:
        query = query.filter(Patient.department_needed == department_id)
    return query.order_by(Patient.arrival_time.desc()).all()

@router.post("/intake", response_model=PatientIntakeResponse)
def register_patient_intake(
    req: PatientIntakeRequest,
    db: Session = Depends(get_db)
):
    """
    Manual/Real-time patient intake endpoint.
    Registers a walk-in or newly transferred patient into the hospital triage queue.
    """
    # 1. Validate department exists
    dept = db.query(Department).filter_by(department_id=req.department_needed).first()
    if not dept:
        raise HTTPException(
            status_code=404,
            detail=f"Department '{req.department_needed}' not found"
        )

    # 2. Generate patient ID following PAT-{8 hex chars uppercase}
    patient_id = f"PAT-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.now()

    # 3. Create Patient record
    patient = Patient(
        patient_id=patient_id,
        arrival_time=now,
        department_needed=req.department_needed,
        severity=req.severity,
        predicted_stay_hours=req.predicted_stay_hours,
        status="waiting"
    )
    db.add(patient)

    # 4. Create EventLog entry
    notes_suffix = f" [Notes: {req.notes}]" if req.notes else ""
    event_desc = (
        f"Manual Patient Intake: {patient.severity.upper()} acuity patient {patient.patient_id} "
        f"registered for {dept.name} (Est. Stay: {patient.predicted_stay_hours}h){notes_suffix}."
    )

    event = EventLog(
        event_type="patient_arrival",
        entity_id=patient.patient_id,
        description=event_desc,
        triggered_by="manual",
        timestamp=now
    )
    db.add(event)

    db.commit()

    return PatientIntakeResponse(
        status="registered",
        patient_id=patient.patient_id,
        arrival_time=patient.arrival_time.isoformat()
    )

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter_by(patient_id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
