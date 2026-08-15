from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from src.api.db import get_db
from src.db.models import Bed
from src.api.schemas import BedResponse

router = APIRouter(prefix="/beds", tags=["beds"])

@router.get("", response_model=List[BedResponse])
def get_beds(
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    status: Optional[str] = Query(None, description="Filter by bed status"),
    db: Session = Depends(get_db)
):
    query = db.query(Bed)
    if department_id:
        query = query.filter(Bed.department_id == department_id)
    if status:
        query = query.filter(Bed.status == status)
    return query.order_by(Bed.bed_id).all()

@router.get("/{bed_id}", response_model=BedResponse)
def get_bed(bed_id: str, db: Session = Depends(get_db)):
    bed = db.query(Bed).filter_by(bed_id=bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    return bed

@router.put("/{bed_id}/status", response_model=BedResponse)
def update_bed_status(bed_id: str, status: str, db: Session = Depends(get_db)):
    bed = db.query(Bed).filter_by(bed_id=bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    bed.status = status
    bed.last_updated = datetime.now()
    db.commit()
    db.refresh(bed)
    return bed
