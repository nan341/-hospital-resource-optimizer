import pytest
from datetime import datetime, timedelta
from src.api.db import SessionLocal, Base, engine
from src.db.models import Department, Bed, Staff, DiagnosticFacility, Patient, EventLog
from src.db.init_db import init_database
from src.allocation.engine import HospitalAllocationEngine
from src.allocation.rules import find_overflow_bed, release_completed_diagnostics

@pytest.fixture(autouse=True)
def reset_db():
    init_database(drop_existing=True)
    yield

def test_primary_bed_and_diagnostic_allocation():
    session = SessionLocal()
    engine_inst = HospitalAllocationEngine()
    try:
        # Create one waiting patient in General Ward
        patient = Patient(
            patient_id="PAT-TEST-001",
            department_needed="general_ward",
            severity="moderate",
            predicted_stay_hours=5.0,
            status="waiting",
            arrival_time=datetime.now()
        )
        session.add(patient)
        session.commit()

        # Run allocation
        res = engine_inst.run_allocation_cycle(session)
        assert res["admitted_primary"] == 1

        # Confirm patient is admitted
        p = session.query(Patient).filter_by(patient_id="PAT-TEST-001").first()
        assert p.status == "admitted"
        assert p.assigned_bed_id is not None

        # Confirm bed is occupied
        bed = session.query(Bed).filter_by(bed_id=p.assigned_bed_id).first()
        assert bed.status == "occupied"
        assert bed.current_patient_id == "PAT-TEST-001"

        # Confirm a diagnostic facility in general_ward was assigned and flipped to 'in_use'
        diag = session.query(DiagnosticFacility).filter(
            DiagnosticFacility.department_id == "general_ward",
            DiagnosticFacility.status == "in_use"
        ).first()
        assert diag is not None
        assert diag.current_patient_id == "PAT-TEST-001"

        # Check event log
        events = session.query(EventLog).filter_by(entity_id=diag.facility_id).all()
        assert len(events) >= 1
        assert any(e.event_type == "diagnostic_assigned" for e in events)

    finally:
        session.close()

def test_critical_overflow_allocation():
    session = SessionLocal()
    engine_inst = HospitalAllocationEngine()
    try:
        # Saturate ER beds completely
        er_beds = session.query(Bed).filter_by(department_id="er").all()
        for idx, b in enumerate(er_beds):
            b.status = "occupied"
            b.current_patient_id = f"PAT-OCCUPIED-{idx}"

        # Add a critical patient who needs ER
        critical_patient = Patient(
            patient_id="PAT-CRIT-999",
            department_needed="er",
            severity="critical",
            predicted_stay_hours=12.0,
            status="waiting",
            arrival_time=datetime.now()
        )
        session.add(critical_patient)
        session.commit()

        # Run allocation
        res = engine_inst.run_allocation_cycle(session)
        assert res["admitted_overflow"] == 1

        # Check patient is admitted
        p = session.query(Patient).filter_by(patient_id="PAT-CRIT-999").first()
        assert p.status == "admitted"
        assert p.assigned_bed_id is not None
        assert not p.assigned_bed_id.startswith("bed-er") # Assigned to another department

        # Confirm overflow event exists
        overflow_event = session.query(EventLog).filter_by(event_type="overflow_assigned").first()
        assert overflow_event is not None
        assert "PAT-CRIT-999" in overflow_event.description

    finally:
        session.close()

def test_priority_queue_ordering():
    session = SessionLocal()
    engine_inst = HospitalAllocationEngine()
    try:
        # Only 1 bed left in pediatrics
        peds_beds = session.query(Bed).filter_by(department_id="pediatrics").all()
        for b in peds_beds[:-1]:
            b.status = "occupied"
            b.current_patient_id = "SOME-PAT"

        now = datetime.now()
        # Add Low severity patient who arrived earlier
        p_low = Patient(
            patient_id="PAT-LOW",
            department_needed="pediatrics",
            severity="low",
            arrival_time=now - timedelta(minutes=30),
            status="waiting"
        )
        # Add Critical severity patient who arrived later
        p_crit = Patient(
            patient_id="PAT-CRIT",
            department_needed="pediatrics",
            severity="critical",
            arrival_time=now - timedelta(minutes=5),
            status="waiting"
        )
        session.add(p_low)
        session.add(p_crit)
        session.commit()

        # Run allocation
        engine_inst.run_allocation_cycle(session)

        # Critical patient should have received the bed over the low severity patient
        crit_refreshed = session.query(Patient).filter_by(patient_id="PAT-CRIT").first()
        low_refreshed = session.query(Patient).filter_by(patient_id="PAT-LOW").first()

        assert crit_refreshed.status == "admitted"
        assert low_refreshed.status == "waiting"

    finally:
        session.close()

def test_load_aware_staff_assignment():
    session = SessionLocal()
    engine_inst = HospitalAllocationEngine()
    try:
        now = datetime.now()
        # Add 3 patients to ER (which has 4 on-duty staff)
        p1 = Patient(patient_id="PAT-STAFF-1", department_needed="er", severity="moderate", arrival_time=now, status="waiting")
        p2 = Patient(patient_id="PAT-STAFF-2", department_needed="er", severity="moderate", arrival_time=now + timedelta(seconds=1), status="waiting")
        p3 = Patient(patient_id="PAT-STAFF-3", department_needed="er", severity="moderate", arrival_time=now + timedelta(seconds=2), status="waiting")

        session.add_all([p1, p2, p3])
        session.commit()

        # Run allocation
        res = engine_inst.run_allocation_cycle(session)
        assert res["admitted_primary"] == 3

        # Retrieve the 3 patients and their assigned staff IDs
        p_records = session.query(Patient).filter(Patient.patient_id.in_(["PAT-STAFF-1", "PAT-STAFF-2", "PAT-STAFF-3"])).all()
        assigned_staff_ids = [p.assigned_staff_id for p in p_records]

        # Confirm all 3 patients got assigned to staff
        assert all(s_id is not None for s_id in assigned_staff_ids)

        # Confirm staff IDs are distinct (distributed across least-loaded staff rather than all piled on the first staff member)
        assert len(set(assigned_staff_ids)) == 3

    finally:
        session.close()

