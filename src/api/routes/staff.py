from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from src.api.db import get_db
from src.db.models import Staff, Patient
from src.api.schemas import StaffResponse

router = APIRouter(prefix="/staff", tags=["staff"])

@router.get("", response_model=List[StaffResponse])
def get_staff(
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    status: Optional[str] = Query(None, description="Filter by status: on_duty, off_duty, reassigned"),
    db: Session = Depends(get_db)
):
    query = db.query(Staff)
    if department_id:
        query = query.filter(Staff.department_id == department_id)
    if status:
        query = query.filter(Staff.status == status)
    
    staff_members = query.order_by(Staff.staff_id).all()
    results = []
    for s in staff_members:
        active_count = db.query(Patient).filter(
            Patient.assigned_staff_id == s.staff_id,
            Patient.status == "admitted"
        ).count()
        results.append(StaffResponse(
            staff_id=s.staff_id,
            role=s.role,
            department_id=s.department_id,
            shift_start=s.shift_start,
            shift_end=s.shift_end,
            status=s.status,
            active_patients=active_count,
            is_busy=active_count > 0
        ))
    return results
