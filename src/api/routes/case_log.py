import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.db import get_db
from src.api.auth import get_auth_payload
from src.db.models import Patient, Appointment, Staff, PatientCaseNote, EventLog, Department

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/case-log", tags=["case-log"])

# Request Schemas
class AddPatientNoteRequest(BaseModel):
    staff_id: str
    note_type: str = Field(..., description="initial_assessment or discharge_summary")
    content: str = Field(..., min_length=1, max_length=2000)

class AddAppointmentNoteRequest(BaseModel):
    staff_id: str
    note_type: str = Field(..., description="consultation_outcome")
    content: str = Field(..., min_length=1, max_length=2000)


@router.get("/appointments")
def list_appointments_for_admin(
    apt_status: Optional[str] = Query(None, alias="status", description="Filter by appointment status: scheduled, in_consultation, completed, cancelled, no_show"),
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    token_payload: dict = Depends(get_auth_payload),
    db: Session = Depends(get_db)
):
    """
    Returns list of outpatient appointments for admin case-log browsing.
    Protected: Admin role.
    """
    role = token_payload.get("role")
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to browse all appointments."
        )

    query = db.query(Appointment)
    if apt_status:
        query = query.filter(Appointment.status == apt_status)
    if department_id:
        query = query.filter(Appointment.department_id == department_id)


    apts = query.order_by(Appointment.scheduled_time.desc()).all()
    results = []
    for a in apts:
        doc = a.doctor
        dept = a.department
        results.append({
            "appointment_id": a.appointment_id,
            "patient_name": a.patient_name,
            "patient_age": a.patient_age,
            "reason_for_visit": a.reason_for_visit,
            "department_id": a.department_id,
            "department_name": dept.name if dept else a.department_id,
            "doctor_id": a.doctor_id,
            "doctor_name": doc.role if doc else "Physician",
            "specialty": doc.specialty if doc else "General",
            "room_number": doc.room_number if doc else "Room 101",
            "floor": doc.floor if doc else "1st Floor",
            "status": a.status,
            "queue_position": a.queue_position,
            "department_queue_position": a.department_queue_position,
            "estimated_wait_minutes": a.estimated_wait_minutes,
            "scheduled_time": a.scheduled_time.isoformat() if a.scheduled_time else None
        })
    return results



@router.get("/patient/{patient_id}")
def get_patient_case_log(
    patient_id: str,
    staff_id: Optional[str] = Query(None, description="Requesting clinician staff ID"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-Id"),
    token_payload: dict = Depends(get_auth_payload),
    db: Session = Depends(get_db)
):
    """
    Returns consolidated patient case log and merged chronological timeline of events and clinical notes.
    Protected: Admin OR assigned clinician (doctor/nurse).
    """
    patient = db.query(Patient).filter_by(patient_id=patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found."
        )

    # Authorization verification
    role = token_payload.get("role")
    if role != "admin":
        req_staff_id = staff_id or x_staff_id
        if not req_staff_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff ID required to verify patient assignment."
            )
        is_assigned = (
            patient.assigned_doctor_id == req_staff_id or
            patient.assigned_nurse_id == req_staff_id or
            patient.assigned_staff_id == req_staff_id
        )
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: you are not assigned to this patient."
            )

    dept = db.query(Department).filter_by(department_id=patient.department_needed).first()
    doctor = db.query(Staff).filter_by(staff_id=patient.assigned_doctor_id).first() if patient.assigned_doctor_id else None
    nurse = db.query(Staff).filter_by(staff_id=patient.assigned_nurse_id).first() if patient.assigned_nurse_id else None

    # Fetch events & notes
    events = db.query(EventLog).filter(EventLog.entity_id == patient_id).all()
    notes = db.query(PatientCaseNote).filter(PatientCaseNote.patient_id == patient_id).all()

    timeline = []
    for e in events:
        timeline.append({
            "type": "event",
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "event_type": e.event_type,
            "description": e.description,
            "triggered_by": e.triggered_by
        })

    for n in notes:
        author = n.staff
        timeline.append({
            "type": "note",
            "timestamp": n.created_at.isoformat() if n.created_at else None,
            "note_id": n.note_id,
            "note_type": n.note_type,
            "content": n.content,
            "author_id": n.staff_id,
            "author_name": f"{author.role} ({author.staff_id})" if author else n.staff_id,
            "author_role": author.role if author else "Clinician",
            "author_specialty": author.specialty if author else None
        })

    # Sort timeline chronologically (oldest to newest)
    timeline.sort(key=lambda item: item["timestamp"] or "")

    return {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "patient_name": patient.name,
        "age": patient.age,
        "reason_for_visit": patient.reason_for_visit,
        "severity": patient.severity,
        "department_id": patient.department_needed,
        "department_name": dept.name if dept else patient.department_needed,
        "assigned_doctor_id": patient.assigned_doctor_id,
        "assigned_doctor_name": doctor.role if doctor else None,
        "assigned_doctor_specialty": doctor.specialty if doctor else None,
        "assigned_nurse_id": patient.assigned_nurse_id,
        "assigned_nurse_name": nurse.role if nurse else None,
        "assigned_bed_id": patient.assigned_bed_id,
        "arrival_time": patient.arrival_time.isoformat() if patient.arrival_time else None,
        "status": patient.status,
        "timeline": timeline
    }


@router.get("/appointment/{appointment_id}")
def get_appointment_case_log(
    appointment_id: str,
    staff_id: Optional[str] = Query(None, description="Requesting clinician staff ID"),
    x_staff_id: Optional[str] = Header(None, alias="X-Staff-Id"),
    token_payload: dict = Depends(get_auth_payload),
    db: Session = Depends(get_db)
):
    """
    Returns outpatient appointment case log and merged timeline.
    Protected: Admin OR assigned doctor/nurse.
    """
    apt = db.query(Appointment).filter_by(appointment_id=appointment_id).first()
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' not found."
        )

    role = token_payload.get("role")
    if role != "admin":
        req_staff_id = staff_id or x_staff_id
        if not req_staff_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff ID required to verify appointment assignment."
            )
        is_assigned = (
            apt.doctor_id == req_staff_id or
            apt.nurse_id == req_staff_id
        )
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: you are not assigned to this appointment."
            )

    dept = apt.department
    doctor = apt.doctor
    nurse = apt.nurse

    events = db.query(EventLog).filter(EventLog.entity_id == appointment_id).all()
    notes = db.query(PatientCaseNote).filter(PatientCaseNote.appointment_id == appointment_id).all()

    timeline = []
    for e in events:
        timeline.append({
            "type": "event",
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "event_type": e.event_type,
            "description": e.description,
            "triggered_by": e.triggered_by
        })

    for n in notes:
        author = n.staff
        timeline.append({
            "type": "note",
            "timestamp": n.created_at.isoformat() if n.created_at else None,
            "note_id": n.note_id,
            "note_type": n.note_type,
            "content": n.content,
            "author_id": n.staff_id,
            "author_name": f"{author.role} ({author.staff_id})" if author else n.staff_id,
            "author_role": author.role if author else "Clinician",
            "author_specialty": author.specialty if author else None
        })

    timeline.sort(key=lambda item: item["timestamp"] or "")

    return {
        "appointment_id": apt.appointment_id,
        "patient_name": apt.patient_name,
        "patient_age": apt.patient_age,
        "reason_for_visit": apt.reason_for_visit,
        "department_id": apt.department_id,
        "department_name": dept.name if dept else apt.department_id,
        "doctor_id": apt.doctor_id,
        "doctor_name": doctor.role if doctor else None,
        "doctor_specialty": doctor.specialty if doctor else None,
        "room_number": doctor.room_number if doctor else None,
        "floor": doctor.floor if doctor else None,
        "scheduled_time": apt.scheduled_time.isoformat() if apt.scheduled_time else None,
        "status": apt.status,
        "timeline": timeline
    }


@router.post("/patient/{patient_id}/note")
def add_patient_clinical_note(
    patient_id: str,
    body: AddPatientNoteRequest,
    token_payload: dict = Depends(get_auth_payload),
    db: Session = Depends(get_db)
):
    """
    Adds a clinical note (initial_assessment or discharge_summary) for an admitted inpatient.
    Protected: Assigned staff member only.
    """
    role = token_payload.get("role")
    if role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only clinical staff can author case notes."
        )

    patient = db.query(Patient).filter_by(patient_id=patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found."
        )

    # Check assignment
    is_assigned = (
        patient.assigned_doctor_id == body.staff_id or
        patient.assigned_nurse_id == body.staff_id or
        patient.assigned_staff_id == body.staff_id
    )
    if not is_assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Staff member '{body.staff_id}' is not assigned to patient '{patient_id}'."
        )

    # Validate note_type for inpatient
    allowed_types = ["initial_assessment", "discharge_summary"]
    if body.note_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid note_type '{body.note_type}'. Allowed types for inpatient cases: {', '.join(allowed_types)}."
        )

    now = datetime.now()
    note = PatientCaseNote(
        patient_id=patient_id,
        staff_id=body.staff_id,
        note_type=body.note_type,
        content=body.content,
        created_at=now
    )
    db.add(note)

    staff = db.query(Staff).filter_by(staff_id=body.staff_id).first()
    staff_label = f"{staff.role} ({body.staff_id})" if staff else body.staff_id

    event = EventLog(
        event_type="clinical_note_added",
        entity_id=patient_id,
        description=f"Clinical note [{body.note_type}] authored by {staff_label}: {body.content[:80]}...",
        triggered_by="staff",
        timestamp=now
    )
    db.add(event)
    db.commit()
    db.refresh(note)

    return {
        "status": "success",
        "note_id": note.note_id,
        "patient_id": note.patient_id,
        "note_type": note.note_type,
        "staff_id": note.staff_id,
        "created_at": note.created_at.isoformat()
    }


@router.post("/appointment/{appointment_id}/note")
def add_appointment_clinical_note(
    appointment_id: str,
    body: AddAppointmentNoteRequest,
    token_payload: dict = Depends(get_auth_payload),
    db: Session = Depends(get_db)
):
    """
    Adds a consultation outcome note for an outpatient appointment.
    Protected: Assigned doctor only.
    """
    role = token_payload.get("role")
    if role != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only clinical staff can author consultation outcome notes."
        )

    apt = db.query(Appointment).filter_by(appointment_id=appointment_id).first()
    if not apt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' not found."
        )

    # Check assignment
    is_assigned = (
        apt.doctor_id == body.staff_id or
        apt.nurse_id == body.staff_id
    )
    if not is_assigned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Staff member '{body.staff_id}' is not assigned to appointment '{appointment_id}'."
        )

    if body.note_type != "consultation_outcome":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid note_type. Allowed type for outpatient appointments is: consultation_outcome."
        )

    now = datetime.now()
    note = PatientCaseNote(
        appointment_id=appointment_id,
        staff_id=body.staff_id,
        note_type=body.note_type,
        content=body.content,
        created_at=now
    )
    db.add(note)

    staff = db.query(Staff).filter_by(staff_id=body.staff_id).first()
    staff_label = f"{staff.role} ({body.staff_id})" if staff else body.staff_id

    event = EventLog(
        event_type="clinical_note_added",
        entity_id=appointment_id,
        description=f"Consultation outcome note authored by {staff_label}: {body.content[:80]}...",
        triggered_by="staff",
        timestamp=now
    )
    db.add(event)
    db.commit()
    db.refresh(note)

    return {
        "status": "success",
        "note_id": note.note_id,
        "appointment_id": note.appointment_id,
        "note_type": note.note_type,
        "staff_id": note.staff_id,
        "created_at": note.created_at.isoformat()
    }
