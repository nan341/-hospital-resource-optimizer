import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.db.models import Department, Bed, Staff, DiagnosticFacility, Patient, EventLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "critical": 1,
    "moderate": 2,
    "low": 3
}

def get_department_occupancy(session: Session) -> Dict[str, Dict[str, Any]]:
    """Calculates bed occupancy statistics per department."""
    departments = session.query(Department).all()
    occupancy_data = {}

    for dept in departments:
        total_beds = dept.total_beds
        occupied_beds = session.query(Bed).filter(
            Bed.department_id == dept.department_id,
            Bed.status == "occupied"
        ).count()
        available_beds = session.query(Bed).filter(
            Bed.department_id == dept.department_id,
            Bed.status == "available"
        ).count()

        rate = (occupied_beds / total_beds) if total_beds > 0 else 1.0
        occupancy_data[dept.department_id] = {
            "department_id": dept.department_id,
            "department_name": dept.name,
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "available_beds": available_beds,
            "occupancy_rate": round(rate, 3)
        }

    return occupancy_data

def find_overflow_bed(session: Session, patient: Patient) -> Optional[Bed]:
    """
    Finds an available bed in another department for a critical patient,
    ranking candidate departments by lowest occupancy rate.
    """
    occupancy_data = get_department_occupancy(session)

    # Filter out patient's own department and departments with 0 available beds
    candidate_depts = [
        dept_id for dept_id, stats in occupancy_data.items()
        if dept_id != patient.department_needed and stats["available_beds"] > 0
    ]

    if not candidate_depts:
        return None

    # Sort candidate departments by occupancy rate ascending
    candidate_depts.sort(key=lambda d: occupancy_data[d]["occupancy_rate"])
    best_dept_id = candidate_depts[0]

    # Pick first available bed in best department
    overflow_bed = session.query(Bed).filter(
        Bed.department_id == best_dept_id,
        Bed.status == "available"
    ).first()

    return overflow_bed

def evaluate_staff_rebalancing(
    session: Session,
    forecasts: Dict[str, Dict[str, Any]],
    load_threshold: float = 0.80
) -> List[Dict[str, Any]]:
    """
    Compares 2-hour predicted load against current on-duty staff capacity per department.
    Identifies if a heavily burdened department needs staff reallocated from a slack department.
    """
    reassignments = []
    departments = session.query(Department).all()

    dept_stats = {}
    for dept in departments:
        on_duty_staff = session.query(Staff).filter(
            Staff.department_id == dept.department_id,
            Staff.status.in_(["on_duty", "reassigned"])
        ).count()

        admitted_patients = session.query(Patient).filter(
            Patient.status == "admitted",
            Patient.department_needed == dept.department_id
        ).count()

        forecast_info = forecasts.get(dept.department_id, {})
        pred_arrivals = forecast_info.get("predicted_count", 1.0)
        projected_total_demand = admitted_patients + pred_arrivals

        # Ratio of projected demand per on-duty staff member
        demand_per_staff = projected_total_demand / max(1, on_duty_staff)
        dept_stats[dept.department_id] = {
            "department": dept,
            "on_duty_staff": on_duty_staff,
            "projected_demand": projected_total_demand,
            "demand_per_staff": demand_per_staff
        }

    # Find overloaded departments (demand_per_staff > 3.0 or high threshold)
    overloaded = [d for d, s in dept_stats.items() if s["demand_per_staff"] > 3.5 and s["on_duty_staff"] < 10]
    # Find slack departments (demand_per_staff < 1.5 and on_duty_staff > 2)
    slack = [d for d, s in dept_stats.items() if s["demand_per_staff"] < 1.5 and s["on_duty_staff"] > 2]

    if overloaded and slack:
        # Sort overloaded by highest demand ratio, slack by lowest
        overloaded.sort(key=lambda d: dept_stats[d]["demand_per_staff"], reverse=True)
        slack.sort(key=lambda d: dept_stats[d]["demand_per_staff"])

        target_dept_id = overloaded[0]
        source_dept_id = slack[0]

        if target_dept_id != source_dept_id:
            # Find a movable staff member in source dept
            staff_to_move = session.query(Staff).filter(
                Staff.department_id == source_dept_id,
                Staff.status.in_(["on_duty", "reassigned"])
            ).first()

            if staff_to_move:
                reassignments.append({
                    "staff_id": staff_to_move.staff_id,
                    "role": staff_to_move.role,
                    "from_dept": source_dept_id,
                    "to_dept": target_dept_id,
                    "reason": f"Projected surge load {dept_stats[target_dept_id]['demand_per_staff']:.1f} pts/staff in {target_dept_id}"
                })

    return reassignments

def release_completed_diagnostics(session: Session, max_duration_seconds: float = 15.0) -> int:
    """
    Releases diagnostic facilities that have finished their procedure duration.
    In prototype simulation, facilities are freed after max_duration_seconds.
    """
    now = datetime.now()
    cutoff = now - timedelta(seconds=max_duration_seconds)

    in_use_facilities = session.query(DiagnosticFacility).filter(
        DiagnosticFacility.status == "in_use"
    ).all()

    released_count = 0
    for fac in in_use_facilities:
        # If in_use_since is past cutoff or unset
        if fac.in_use_since is None or fac.in_use_since <= cutoff:
            prev_patient_id = fac.current_patient_id
            dept_name = fac.department.name if fac.department else fac.department_id
            fac.status = "free"
            fac.current_patient_id = None
            fac.in_use_since = None
            released_count += 1

            rel_event = EventLog(
                event_type="diagnostic_released",
                entity_id=fac.facility_id,
                description=f"Diagnostic facility '{fac.type}' in {dept_name} completed procedure for patient {prev_patient_id or 'N/A'} and is now FREE.",
                triggered_by="rule_engine",
                timestamp=now
            )
            session.add(rel_event)

    return released_count
