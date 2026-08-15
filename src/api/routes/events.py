from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.api.db import get_db
from src.db.models import EventLog
from src.api.schemas import EventLogResponse

router = APIRouter(prefix="/events", tags=["events"])

@router.get("", response_model=List[EventLogResponse])
def get_events(
    limit: int = Query(50, ge=1, le=200, description="Max events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event_type"),
    db: Session = Depends(get_db)
):
    query = db.query(EventLog)
    if event_type:
        query = query.filter(EventLog.event_type == event_type)
    return query.order_by(EventLog.timestamp.desc(), EventLog.event_id.desc()).limit(limit).all()
