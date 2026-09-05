import os
import sys
from datetime import datetime

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.db import engine, SessionLocal, Base
from src.db.models import Department, Bed, Staff, DiagnosticFacility, Patient, Appointment, StaffNotification, EventLog

def init_database(drop_existing: bool = False):
    """Creates tables and seeds initial hospital departments, beds, staff, and diagnostic facilities."""
    # Ensure data directory exists
    db_dir = os.path.dirname(os.path.abspath("data/hospital.db"))
    os.makedirs(db_dir, exist_ok=True)

    if drop_existing:
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        # Check if already seeded
        if session.query(Department).count() > 0:
            print("Database already initialized and seeded.")
            return

        departments_config = [
            {
                "id": "er",
                "name": "Emergency Room (ER)",
                "total_beds": 8,
                "staff_slots": 4,
                "bed_type": "emergency",
                "staff": [
                    {"id": "staff-er-1", "role": "ER Physician", "shift": ("07:00", "19:00"), "floor": "Ground", "room": "ER-Bay-1", "specialty": "Emergency Medicine", "avg_consult": 20},
                    {"id": "staff-er-2", "role": "Trauma Nurse", "shift": ("07:00", "19:00"), "floor": "Ground", "room": "ER-Bay-2", "specialty": "Trauma Care", "avg_consult": 15},
                    {"id": "staff-er-3", "role": "Triage Nurse", "shift": ("07:00", "19:00"), "floor": "Ground", "room": "ER-Triage", "specialty": "Emergency Triage", "avg_consult": 10},
                    {"id": "staff-er-4", "role": "ER Tech", "shift": ("07:00", "19:00"), "floor": "Ground", "room": "ER-Tech-1", "specialty": "Emergency Support", "avg_consult": 15},
                ],
                "diagnostics": [
                    {"id": "diag-er-1", "type": "Trauma CT Scanner", "minutes": 25},
                    {"id": "diag-er-2", "type": "Emergency Digital X-Ray", "minutes": 15},
                ]
            },
            {
                "id": "general_ward",
                "name": "General Ward",
                "total_beds": 20,
                "staff_slots": 8,
                "bed_type": "standard",
                "staff": [
                    {"id": "staff-gw-1", "role": "Ward Physician", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Off-1", "specialty": "Internal Medicine", "avg_consult": 15},
                    {"id": "staff-gw-2", "role": "Senior Staff Nurse", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Nurse-1", "specialty": "Inpatient Nursing", "avg_consult": 15},
                    {"id": "staff-gw-3", "role": "Staff Nurse", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Nurse-2", "specialty": "Inpatient Nursing", "avg_consult": 15},
                    {"id": "staff-gw-4", "role": "Staff Nurse", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Nurse-3", "specialty": "Inpatient Nursing", "avg_consult": 15},
                    {"id": "staff-gw-5", "role": "Staff Nurse", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Nurse-4", "specialty": "Inpatient Nursing", "avg_consult": 15},
                    {"id": "staff-gw-6", "role": "Nursing Assistant", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Care-1", "specialty": "Patient Care", "avg_consult": 15},
                    {"id": "staff-gw-7", "role": "Nursing Assistant", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Care-2", "specialty": "Patient Care", "avg_consult": 15},
                    {"id": "staff-gw-8", "role": "Clinical Pharmacist", "shift": ("08:00", "20:00"), "floor": "2nd Floor", "room": "GW-Pharm", "specialty": "Pharmacy", "avg_consult": 15},
                ],
                "diagnostics": [
                    {"id": "diag-gw-1", "type": "Diagnostic Ultrasound", "minutes": 30},
                    {"id": "diag-gw-2", "type": "12-Lead ECG Station", "minutes": 10},
                ]
            },
            {
                "id": "icu",
                "name": "Intensive Care Unit (ICU)",
                "total_beds": 6,
                "staff_slots": 6,
                "bed_type": "icu",
                "staff": [
                    {"id": "staff-icu-1", "role": "Intensivist", "shift": ("07:00", "19:00"), "floor": "3rd Floor", "room": "ICU-Doc-1", "specialty": "Critical Care Medicine", "avg_consult": 30},
                    {"id": "staff-icu-2", "role": "Critical Care Specialist", "shift": ("07:00", "19:00"), "floor": "3rd Floor", "room": "ICU-Doc-2", "specialty": "Critical Care", "avg_consult": 25},
                    {"id": "staff-icu-3", "role": "ICU Senior Nurse", "shift": ("07:00", "19:00"), "floor": "3rd Floor", "room": "ICU-Nurse-1", "specialty": "Critical Care Nursing", "avg_consult": 20},
                    {"id": "staff-icu-4", "role": "ICU Staff Nurse", "shift": ("07:00", "19:00"), "floor": "3rd Floor", "room": "ICU-Nurse-2", "specialty": "Critical Care Nursing", "avg_consult": 20},
                    {"id": "staff-icu-5", "role": "ICU Staff Nurse", "shift": ("07:00", "19:00"), "floor": "3rd Floor", "room": "ICU-Nurse-3", "specialty": "Critical Care Nursing", "avg_consult": 20},
                    {"id": "staff-icu-6", "role": "Respiratory Therapist", "shift": ("07:00", "19:00"), "floor": "3rd Floor", "room": "ICU-Resp", "specialty": "Pulmonology", "avg_consult": 20},
                ],
                "diagnostics": [
                    {"id": "diag-icu-1", "type": "Point-of-Care Blood Gas Analyzer", "minutes": 10},
                    {"id": "diag-icu-2", "type": "Mobile ICU Digital X-Ray", "minutes": 20},
                ]
            },
            {
                "id": "pediatrics",
                "name": "Pediatrics",
                "total_beds": 10,
                "staff_slots": 4,
                "bed_type": "pediatric",
                "staff": [
                    {"id": "staff-peds-1", "role": "Pediatrician", "shift": ("08:00", "20:00"), "floor": "1st Floor", "room": "Peds-Doc-1", "specialty": "General Pediatrics", "avg_consult": 20},
                    {"id": "staff-peds-2", "role": "Pediatric Senior Nurse", "shift": ("08:00", "20:00"), "floor": "1st Floor", "room": "Peds-Nurse-1", "specialty": "Pediatric Care", "avg_consult": 15},
                    {"id": "staff-peds-3", "role": "Pediatric Nurse", "shift": ("08:00", "20:00"), "floor": "1st Floor", "room": "Peds-Nurse-2", "specialty": "Pediatric Care", "avg_consult": 15},
                    {"id": "staff-peds-4", "role": "Child Life Specialist", "shift": ("08:00", "20:00"), "floor": "1st Floor", "room": "Peds-Play", "specialty": "Pediatric Support", "avg_consult": 20},
                ],
                "diagnostics": [
                    {"id": "diag-peds-1", "type": "Pediatric Echo/Ultrasound", "minutes": 25},
                    {"id": "diag-peds-2", "type": "Pediatric Spirometer Unit", "minutes": 15},
                ]
            },
            {
                "id": "opd",
                "name": "General OPD",
                "total_beds": 0,
                "staff_slots": 4,
                "bed_type": None,
                "staff": [
                    {"id": "staff-opd-1", "role": "OPD Physician", "shift": ("08:00", "17:00"), "floor": "1st Floor", "room": "OPD-101", "specialty": "General Medicine", "avg_consult": 15},
                    {"id": "staff-opd-2", "role": "OPD Physician", "shift": ("08:00", "17:00"), "floor": "1st Floor", "room": "OPD-102", "specialty": "General Medicine", "avg_consult": 15},
                    {"id": "staff-opd-3", "role": "OPD Physician", "shift": ("09:00", "18:00"), "floor": "1st Floor", "room": "OPD-103", "specialty": "General Medicine", "avg_consult": 15},
                ],
                "diagnostics": []
            },
            {
                "id": "ent",
                "name": "ENT Department",
                "total_beds": 0,
                "staff_slots": 2,
                "bed_type": None,
                "staff": [
                    {"id": "staff-ent-1", "role": "ENT Specialist", "shift": ("08:00", "16:00"), "floor": "1st Floor", "room": "ENT-101", "specialty": "ENT", "avg_consult": 20},
                    {"id": "staff-ent-2", "role": "ENT Specialist", "shift": ("09:00", "17:00"), "floor": "1st Floor", "room": "ENT-102", "specialty": "ENT", "avg_consult": 20},
                ],
                "diagnostics": []
            }
        ]

        for dept in departments_config:
            d_obj = Department(
                department_id=dept["id"],
                name=dept["name"],
                total_beds=dept["total_beds"],
                total_staff_slots=dept["staff_slots"]
            )
            session.add(d_obj)

            # Add beds only for departments with total_beds > 0
            if dept["total_beds"] > 0 and dept.get("bed_type"):
                for b_idx in range(1, dept["total_beds"] + 1):
                    bed_id = f"bed-{dept['id']}-{b_idx:02d}"
                    bed = Bed(
                        bed_id=bed_id,
                        department_id=dept["id"],
                        bed_type=dept["bed_type"],
                        status="available",
                        last_updated=datetime.now()
                    )
                    session.add(bed)

            # Add staff
            for s_info in dept["staff"]:
                st = Staff(
                    staff_id=s_info["id"],
                    role=s_info["role"],
                    department_id=dept["id"],
                    shift_start=s_info["shift"][0],
                    shift_end=s_info["shift"][1],
                    status="on_duty",
                    floor=s_info.get("floor"),
                    room_number=s_info.get("room"),
                    specialty=s_info.get("specialty"),
                    avg_consult_minutes=s_info.get("avg_consult", 15)
                )
                session.add(st)

            # Add diagnostic facilities (status = 'free')
            for d_info in dept.get("diagnostics", []):
                diag = DiagnosticFacility(
                    facility_id=d_info["id"],
                    type=d_info["type"],
                    department_id=dept["id"],
                    status="free",
                    avg_procedure_minutes=d_info["minutes"]
                )
                session.add(diag)

        # Log system initialized event
        init_event = EventLog(
            event_type="system_initialized",
            entity_id="hospital_system",
            description="Hospital Resource Optimizer database initialized with 6 departments (including General OPD & ENT), 44 inpatient beds, 27 on-duty staff, and 8 diagnostic facilities.",
            triggered_by="manual",
            timestamp=datetime.now()
        )
        session.add(init_event)

        session.commit()
        print(f"Successfully initialized database with {len(departments_config)} departments.")
    except Exception as e:
        session.rollback()
        print(f"Error initializing database: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    drop = "--reset" in sys.argv or "-r" in sys.argv
    init_database(drop_existing=drop)
