import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import case, asc

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.db import SessionLocal
from src.db.models import Department, Bed, Staff, DiagnosticFacility, Patient, EventLog
from src.allocation.rules import (
    SEVERITY_WEIGHTS,
    find_overflow_bed,
    evaluate_staff_rebalancing,
    release_completed_diagnostics,
    get_department_occupancy
)
from src.models.forecasting import forecaster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HospitalAllocationEngine:
    def __init__(self):
        self.forecaster = forecaster

    def discharge_completed_patients(self, session: Session) -> int:
        """Discharges patients whose stay duration has finished, freeing beds."""
        now = datetime.now()
        # In accelerated simulation, check if admitted patients have stayed their duration
        admitted_patients = session.query(Patient).filter(Patient.status == "admitted").all()
        discharged_count = 0

        for patient in admitted_patients:
            # Check elapsed time (scaled for demo)
            elapsed_hours = (now - patient.arrival_time).total_seconds() / 3600.0
            # For demonstration, if elapsed minutes > predicted stay hours * 2 (or minimum threshold)
            elapsed_seconds = (now - patient.arrival_time).total_seconds()
            # Fast-track discharge: 1 stay hour ~ 20 real seconds
            if elapsed_seconds > max(30.0, patient.predicted_stay_hours * 15.0):
                patient.status = "discharged"

                # Free the bed
                if patient.assigned_bed_id:
                    bed = session.query(Bed).filter_by(bed_id=patient.assigned_bed_id).first()
                    if bed:
                        bed.status = "available"
                        bed.current_patient_id = None
                        bed.last_updated = now

                # Log discharge event
                dept = session.query(Department).filter_by(department_id=patient.department_needed).first()
                dept_name = dept.name if dept else patient.department_needed

                event = EventLog(
                    event_type="patient_discharged",
                    entity_id=patient.patient_id,
                    description=f"Patient {patient.patient_id} successfully treated and discharged from {dept_name}. Bed {patient.assigned_bed_id or 'N/A'} is now AVAILABLE.",
                    triggered_by="rule_engine",
                    timestamp=now
                )
                session.add(event)
                discharged_count += 1

        return discharged_count

    def allocate_diagnostics_for_patient(
        self,
        session: Session,
        patient: Patient,
        assigned_dept_id: str,
        assigned_dept_name: str
    ):
        """Attempts to assign a free diagnostic facility in the patient's assigned department."""
        now = datetime.now()
        free_diag = session.query(DiagnosticFacility).filter(
            DiagnosticFacility.department_id == assigned_dept_id,
            DiagnosticFacility.status == "free"
        ).first()

        if free_diag:
            free_diag.status = "in_use"
            free_diag.current_patient_id = patient.patient_id
            free_diag.in_use_since = now

            diag_event = EventLog(
                event_type="diagnostic_assigned",
                entity_id=free_diag.facility_id,
                description=f"Assigned {free_diag.type} to patient {patient.patient_id} in {assigned_dept_name}.",
                triggered_by="rule_engine",
                timestamp=now
            )
            session.add(diag_event)
        else:
            diag_event = EventLog(
                event_type="diagnostic_unavailable",
                entity_id=patient.patient_id,
                description=f"Diagnostic facilities in {assigned_dept_name} currently in use for patient {patient.patient_id}; queued for next available scanner.",
                triggered_by="rule_engine",
                timestamp=now
            )
            session.add(diag_event)

    def find_least_loaded_staff(self, session: Session, department_id: str) -> Optional[Staff]:
        """Finds the on-duty staff member with the fewest currently-admitted patients."""
        from sqlalchemy import func
        staff_load = (
            session.query(Staff.staff_id, func.count(Patient.patient_id).label("load"))
            .outerjoin(
                Patient,
                (Patient.assigned_staff_id == Staff.staff_id) & (Patient.status == "admitted")
            )
            .filter(
                Staff.department_id == department_id,
                Staff.status.in_(["on_duty", "reassigned"])
            )
            .group_by(Staff.staff_id)
            .order_by("load")
            .first()
        )
        if not staff_load:
            return None
        return session.query(Staff).filter_by(staff_id=staff_load[0]).first()

    def run_allocation_cycle(self, session: Optional[Session] = None) -> Dict[str, Any]:
        """
        Main execution loop for priority-queue resource allocation:
        1. Release completed diagnostics and eligible discharges
        2. Priority Queue processing (Critical > Moderate > Low, then FIFO)
        3. Primary bed matching
        4. Critical overflow fallback routing
        5. Diagnostic facility pairing
        6. Capacity alert logging
        7. Predictive staff rebalancing
        """
        is_external_session = session is not None
        if not is_external_session:
            session = SessionLocal()

        now = datetime.now()
        results = {
            "admitted_primary": 0,
            "admitted_overflow": 0,
            "critical_no_capacity": 0,
            "staff_reassigned": 0,
            "diagnostics_released": 0,
            "discharges": 0
        }

        try:
            # 1. Housekeeping: Diagnostic releases & Patient discharges
            results["diagnostics_released"] = release_completed_diagnostics(session)
            results["discharges"] = self.discharge_completed_patients(session)

            # 2. Query all waiting patients with strict priority ordering
            # Severity mapping: critical=1, moderate=2, low=3
            severity_order = case(
                (Patient.severity == "critical", 1),
                (Patient.severity == "moderate", 2),
                (Patient.severity == "low", 3),
                else_=4
            )

            waiting_patients = (
                session.query(Patient)
                .filter(Patient.status == "waiting")
                .order_by(severity_order, asc(Patient.arrival_time))
                .all()
            )

            # 3. Process each waiting patient
            for patient in waiting_patients:
                dept_needed = session.query(Department).filter_by(department_id=patient.department_needed).first()
                dept_name = dept_needed.name if dept_needed else patient.department_needed

                # Step A: Primary department bed search
                primary_bed = (
                    session.query(Bed)
                    .filter(
                        Bed.department_id == patient.department_needed,
                        Bed.status == "available"
                    )
                    .first()
                )

                if primary_bed:
                    # Allocate primary bed
                    primary_bed.status = "occupied"
                    primary_bed.current_patient_id = patient.patient_id
                    primary_bed.last_updated = now

                    patient.status = "admitted"
                    patient.assigned_bed_id = primary_bed.bed_id

                    # Assign load-aware least-burdened staff member
                    staff = self.find_least_loaded_staff(session, patient.department_needed)
                    if staff:
                        patient.assigned_staff_id = staff.staff_id

                    event = EventLog(
                        event_type="bed_assigned",
                        entity_id=primary_bed.bed_id,
                        description=f"Assigned Bed {primary_bed.bed_id} in {dept_name} to patient {patient.patient_id} [Severity: {patient.severity.upper()}].",
                        triggered_by="rule_engine",
                        timestamp=now
                    )
                    session.add(event)
                    session.flush()
                    results["admitted_primary"] += 1

                    # Diagnostic facility allocation step
                    self.allocate_diagnostics_for_patient(session, patient, patient.department_needed, dept_name)

                # Step B: Overflow routing for critical patients
                elif patient.severity == "critical":
                    overflow_bed = find_overflow_bed(session, patient)

                    if overflow_bed:
                        overflow_bed.status = "occupied"
                        overflow_bed.current_patient_id = patient.patient_id
                        overflow_bed.last_updated = now

                        patient.status = "admitted"
                        patient.assigned_bed_id = overflow_bed.bed_id

                        overflow_dept = overflow_bed.department
                        overflow_dept_name = overflow_dept.name if overflow_dept else overflow_bed.department_id

                        # Assign load-aware least-burdened staff in overflow department
                        staff = self.find_least_loaded_staff(session, overflow_bed.department_id)
                        if staff:
                            patient.assigned_staff_id = staff.staff_id

                        overflow_event = EventLog(
                            event_type="overflow_assigned",
                            entity_id=overflow_bed.bed_id,
                            description=f"CRITICAL OVERFLOW ROUTING: {dept_name} full. Transferred critical patient {patient.patient_id} to Bed {overflow_bed.bed_id} in {overflow_dept_name}.",
                            triggered_by="rule_engine",
                            timestamp=now
                        )
                        session.add(overflow_event)
                        session.flush()
                        results["admitted_overflow"] += 1

                        # Diagnostic facility in overflow department
                        self.allocate_diagnostics_for_patient(session, patient, overflow_bed.department_id, overflow_dept_name)
                    else:
                        # Zero bed capacity hospital-wide
                        alert_event = EventLog(
                            event_type="critical_no_capacity",
                            entity_id=patient.patient_id,
                            description=f"CRITICAL HOSPITAL CAPACITY ALERT: No standard or overflow beds available for critical patient {patient.patient_id}!",
                            triggered_by="rule_engine",
                            timestamp=now
                        )
                        session.add(alert_event)
                        results["critical_no_capacity"] += 1

                else:
                    # Moderate / Low priority patients wait in queue until capacity opens
                    pass

            # 4. Staff rebalancing pass via 2-hour predictive demand
            try:
                forecasts = self.forecaster.predict_all_departments(session, horizon_hours=2)
                reassignments = evaluate_staff_rebalancing(session, forecasts)

                for r in reassignments:
                    st = session.query(Staff).filter_by(staff_id=r["staff_id"]).first()
                    if st:
                        from_dept = session.query(Department).filter_by(department_id=r["from_dept"]).first()
                        to_dept = session.query(Department).filter_by(department_id=r["to_dept"]).first()
                        st.department_id = r["to_dept"]
                        st.status = "reassigned"

                        st_event = EventLog(
                            event_type="staff_reassigned",
                            entity_id=st.staff_id,
                            description=f"Predictive Staff Rebalance: Reassigned {st.role} ({st.staff_id}) from {from_dept.name if from_dept else r['from_dept']} to {to_dept.name if to_dept else r['to_dept']}. Reason: {r['reason']}",
                            triggered_by="prediction_engine",
                            timestamp=now
                        )
                        session.add(st_event)
                        results["staff_reassigned"] += 1
            except Exception as e:
                logger.warning(f"Staff rebalancing check encountered: {e}")

            session.commit()
            return results

        except Exception as e:
            session.rollback()
            logger.error(f"Error in allocation cycle: {e}")
            raise
        finally:
            if not is_external_session:
                session.close()

# Global allocation engine instance
allocation_engine = HospitalAllocationEngine()
