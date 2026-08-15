from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from src.api.db import get_db
from src.db.models import Patient
from src.api.schemas import PatientResponse

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

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter_by(patient_id=patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
