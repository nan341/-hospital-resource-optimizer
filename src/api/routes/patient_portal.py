from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from src.api.db import get_db
from src.db.models import Department, Bed, DiagnosticFacility, Staff, Appointment
from src.allocation.appointment_engine import appointment_scheduler

router = APIRouter(prefix="/patient-portal", tags=["patient-portal"])

class BookAppointmentRequest(BaseModel):
    patient_name: str = Field(..., min_length=2, max_length=100)
    patient_age: Optional[int] = Field(default=None, ge=0, le=130)
    reason_for_visit: Optional[str] = Field(default=None, max_length=300)
    department_id: str

@router.get("/availability")
def get_public_availability(db: Session = Depends(get_db)):
    """
    Public patient-facing availability.
    Strictly qualitative (Available / Full) with NO raw counts, numbers, or percentages.
    Includes estimated wait times for outpatient clinics.
    """
    departments = db.query(Department).all()
    results = []

    for dept in departments:
        if dept.total_beds > 0:
            # Inpatient department
            available_beds = db.query(Bed).filter_by(
                department_id=dept.department_id,
                status="available"
            ).count()

            free_diag = db.query(DiagnosticFacility).filter_by(
                department_id=dept.department_id,
                status="free"
            ).count()

            total_diag = db.query(DiagnosticFacility).filter_by(
                department_id=dept.department_id
            ).count()

            diag_status = "Available" if free_diag > 0 else ("Full" if total_diag > 0 else "N/A")

            results.append({
                "department_id": dept.department_id,
                "name": dept.name,
                "type": "inpatient",
                "beds_status": "Available" if available_beds > 0 else "Full",
                "diagnostics_status": diag_status
            })
        else:
            # Outpatient department (OPD, ENT)
            doctors = db.query(Staff).filter_by(department_id=dept.department_id).all()
            min_wait = 0
            if doctors:
                # Calculate minimum wait time across doctors in this clinic
                waits = []
                for doc in doctors:
                    scheduled_count = db.query(Appointment).filter(
                        Appointment.doctor_id == doc.staff_id,
                        Appointment.status == "scheduled"
                    ).count()
                    in_consult = db.query(Appointment).filter(
                        Appointment.doctor_id == doc.staff_id,
                        Appointment.status == "in_consultation"
                    ).count()
                    wait_time = (scheduled_count + (1 if in_consult > 0 else 0)) * (doc.avg_consult_minutes or 15)
                    waits.append(wait_time)
                min_wait = min(waits) if waits else 0

            results.append({
                "department_id": dept.department_id,
                "name": dept.name,
                "type": "outpatient",
                "clinic_status": "Open",
                "estimated_wait_minutes": min_wait
            })

    return results

@router.get("/departments")
def get_outpatient_departments(db: Session = Depends(get_db)):
    """
    Returns outpatient departments (total_beds == 0) for appointment booking dropdown.
    """
    depts = db.query(Department).filter(Department.total_beds == 0).all()
    return [{"department_id": d.department_id, "name": d.name} for d in depts]

@router.post("/book-appointment")
def book_appointment(req: BookAppointmentRequest, db: Session = Depends(get_db)):
    """
    Books an outpatient appointment and returns doctor/location/queue details.
    """
    try:
        res = appointment_scheduler.book_appointment(
            session=db,
            patient_name=req.patient_name,
            patient_age=req.patient_age,
            reason_for_visit=req.reason_for_visit,
            department_id=req.department_id
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/appointment/{appointment_id}")
def check_appointment_status(appointment_id: str, db: Session = Depends(get_db)):
    """
    Public lookup for appointment status and queue position.
    """
    apt = appointment_scheduler.get_appointment_status(db, appointment_id)
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' not found."
        )
    return apt
