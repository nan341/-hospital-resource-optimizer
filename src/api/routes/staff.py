from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from src.api.db import get_db
from src.db.models import Staff
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
    return query.order_by(Staff.staff_id).all()
