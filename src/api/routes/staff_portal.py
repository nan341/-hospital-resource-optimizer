from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.api.db import get_db
from src.api.auth import require_role
from src.db.models import Staff, Department, Patient, Appointment, StaffNotification

router = APIRouter(
    prefix="/staff-portal",
    tags=["staff-portal"],
    dependencies=[Depends(require_role("staff"))]
)

@router.get("/roster")
def get_staff_roster(db: Session = Depends(get_db)):
    """
    Returns full staff roster for identity selection in the Staff Portal.
    Protected by staff role.
    """
    staff_list = db.query(Staff).order_by(Staff.department_id, Staff.staff_id).all()
    return [
        {
            "staff_id": s.staff_id,
            "role": s.role,
            "department_id": s.department_id,
            "department_name": s.department.name if s.department else s.department_id,
            "shift_start": s.shift_start,
            "shift_end": s.shift_end,
            "status": s.status,
            "floor": s.floor,
            "room_number": s.room_number,
            "specialty": s.specialty
        }
        for s in staff_list
    ]

@router.get("/{staff_id}/dashboard")
def get_staff_dashboard(staff_id: str, db: Session = Depends(get_db)):
    """
    Returns personalized dashboard data for a given staff member:
    - Shift times, duty status, department details
    - Inpatient assigned patients (with age & reason)
    - Outpatient appointments queue (scheduled/in_consultation)
    """
    staff = db.query(Staff).filter_by(staff_id=staff_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member '{staff_id}' not found."
        )

    dept = staff.department
    is_outpatient = dept and dept.total_beds == 0

    assigned_patients = []
    if not is_outpatient:
        # Inpatient staff: currently admitted patients
        patients = db.query(Patient).filter(
            Patient.assigned_staff_id == staff_id,
            Patient.status == "admitted"
        ).order_by(Patient.arrival_time.desc()).all()

        assigned_patients = [
            {
                "patient_id": p.patient_id,
                "age": p.age,
                "reason_for_visit": p.reason_for_visit or "General Inpatient Care",
                "severity": p.severity,
                "predicted_stay_hours": p.predicted_stay_hours,
                "assigned_bed_id": p.assigned_bed_id,
                "arrival_time": p.arrival_time.isoformat() if p.arrival_time else None
            }
            for p in patients
        ]

    appointments = []
    if is_outpatient:
        # Outpatient doctor: active appointments
        apts = db.query(Appointment).filter(
            Appointment.doctor_id == staff_id,
            Appointment.status.in_(["scheduled", "in_consultation"])
        ).order_by(Appointment.status.desc(), Appointment.scheduled_time.asc()).all()

        appointments = [
            {
                "appointment_id": a.appointment_id,
                "patient_name": a.patient_name,
                "patient_age": a.patient_age,
                "reason_for_visit": a.reason_for_visit or "Consultation",
                "queue_position": a.queue_position,
                "scheduled_time": a.scheduled_time.isoformat() if a.scheduled_time else None,
                "status": a.status,
                "estimated_wait_minutes": a.estimated_wait_minutes
            }
            for a in apts
        ]

    unread_notifs_count = db.query(StaffNotification).filter(
        StaffNotification.staff_id == staff_id,
        StaffNotification.is_read == False
    ).count()

    return {
        "staff_id": staff.staff_id,
        "role": staff.role,
        "department_id": staff.department_id,
        "department_name": dept.name if dept else staff.department_id,
        "shift_start": staff.shift_start,
        "shift_end": staff.shift_end,
        "status": staff.status,
        "floor": staff.floor,
        "room_number": staff.room_number,
        "specialty": staff.specialty,
        "is_outpatient": is_outpatient,
        "assigned_patients": assigned_patients,
        "appointments": appointments,
        "unread_notifications_count": unread_notifs_count
    }

@router.get("/{staff_id}/notifications")
def get_staff_notifications(
    staff_id: str,
    unread_only: bool = Query(True, description="Filter for unread notifications only"),
    db: Session = Depends(get_db)
):
    """
    Returns notifications for the specified staff member, sorted newest first.
    """
    query = db.query(StaffNotification).filter(StaffNotification.staff_id == staff_id)
    if unread_only:
        query = query.filter(StaffNotification.is_read == False)

    notifs = query.order_by(StaffNotification.created_at.desc()).all()
    return [
        {
            "notification_id": n.notification_id,
            "staff_id": n.staff_id,
            "patient_id": n.patient_id,
            "appointment_id": n.appointment_id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifs
    ]

@router.post("/{staff_id}/notifications/{notification_id}/mark-read")
def mark_notification_read(
    staff_id: str,
    notification_id: int,
    db: Session = Depends(get_db)
):
    """
    Marks a staff notification as read.
    """
    notif = db.query(StaffNotification).filter_by(
        notification_id=notification_id,
        staff_id=staff_id
    ).first()

    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found."
        )

    notif.is_read = True
    db.commit()
    return {"status": "success", "notification_id": notification_id, "is_read": True}

@router.post("/{staff_id}/toggle-duty")
def toggle_staff_duty(
    staff_id: str,
    db: Session = Depends(get_db)
):
    """
    Toggles staff duty between on_duty and off_duty.
    Reassigned staff cannot be manually toggled (returns 409 Conflict).
    """
    staff = db.query(Staff).filter_by(staff_id=staff_id).first()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff member '{staff_id}' not found."
        )

    if staff.status == "reassigned":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Staff is currently assigned to emergency surge response and cannot change duty status manually."
        )

    staff.status = "off_duty" if staff.status == "on_duty" else "on_duty"
    db.commit()
    return {"status": "success", "staff_id": staff_id, "new_status": staff.status}
