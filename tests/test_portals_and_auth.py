import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.db.init_db import init_database

@pytest.fixture(autouse=True)
def setup_db():
    init_database(drop_existing=True)
    yield
    init_database(drop_existing=True)

client = TestClient(app)

def test_admin_and_staff_auth_separation():
    # 1. Unauthenticated request to protected admin route -> 401
    res = client.post("/simulation/start")
    assert res.status_code == 401

    # 2. Invalid password for admin login -> 401
    res_bad_admin = client.post("/admin/login", json={"password": "wrongpassword"})
    assert res_bad_admin.status_code == 401

    # 3. Successful Admin Login
    res_admin = client.post("/admin/login", json={"password": "changeme"})
    assert res_admin.status_code == 200
    admin_token = res_admin.json()["token"]
    assert res_admin.json()["role"] == "admin"
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 4. Admin token accesses protected admin routes
    res_start = client.post("/simulation/start", json={"speed_factor": 2.0}, headers=admin_headers)
    assert res_start.status_code == 200
    res_depts = client.get("/departments", headers=admin_headers)
    assert res_depts.status_code == 200
    assert len(res_depts.json()) == 6

    # 5. Invalid code for staff login -> 401
    res_bad_staff = client.post("/staff/login", json={"password": "wrongcode"})
    assert res_bad_staff.status_code == 401

    # 6. Successful Staff Login
    res_staff = client.post("/staff/login", json={"password": "staff123"})
    assert res_staff.status_code == 200
    staff_token = res_staff.json()["token"]
    assert res_staff.json()["role"] == "staff"
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # 7. Staff token accesses staff portal
    res_roster = client.get("/staff-portal/roster", headers=staff_headers)
    assert res_roster.status_code == 200
    assert len(res_roster.json()) == 27  # 22 inpatient + 5 outpatient

    # 8. Strict Role Separation: Admin token on staff route -> 403 Forbidden
    res_admin_on_staff = client.get("/staff-portal/roster", headers=admin_headers)
    assert res_admin_on_staff.status_code == 403

    # 9. Strict Role Separation: Staff token on admin route -> 403 Forbidden
    res_staff_on_admin = client.get("/departments", headers=staff_headers)
    assert res_staff_on_admin.status_code == 403
    res_staff_on_sim = client.post("/simulation/start", headers=staff_headers)
    assert res_staff_on_sim.status_code == 403

def test_patient_portal_public_access_and_no_leakage():
    # 1. Availability is public and has NO numeric bed counts
    res = client.get("/patient-portal/availability")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 6

    for dept in data:
        # Check no numeric occupancy leakage
        assert "total_beds" not in dept
        assert "occupied_beds" not in dept
        assert "occupancy_rate" not in dept
        if dept["type"] == "inpatient":
            assert dept["beds_status"] in ["Available", "Full"]
            assert dept["diagnostics_status"] in ["Available", "Full", "N/A"]
        elif dept["type"] == "outpatient":
            assert dept["clinic_status"] == "Open"
            assert "estimated_wait_minutes" in dept

    # 2. Outpatient departments dropdown is public
    res_depts = client.get("/patient-portal/departments")
    assert res_depts.status_code == 200
    outpatient_ids = [d["department_id"] for d in res_depts.json()]
    assert "opd" in outpatient_ids
    assert "ent" in outpatient_ids
    assert "er" not in outpatient_ids  # Inpatient excluded

def test_appointment_booking_and_doctor_dashboard():
    # 1. Book OPD appointment
    book_payload = {
        "patient_name": "Elena Fisher",
        "patient_age": 34,
        "reason_for_visit": "Persistent headache and fever",
        "department_id": "opd"
    }
    res_book = client.post("/patient-portal/book-appointment", json=book_payload)
    assert res_book.status_code == 200
    apt_data = res_book.json()
    assert apt_data["patient_name"] == "Elena Fisher"
    assert apt_data["appointment_id"].startswith("APT-")
    assert apt_data["room_number"] is not None
    assert apt_data["floor"] is not None
    apt_id = apt_data["appointment_id"]
    assigned_doc_id = apt_data["doctor_id"]

    # 2. Check appointment status (Public)
    res_status = client.get(f"/patient-portal/appointment/{apt_id}")
    assert res_status.status_code == 200
    assert res_status.json()["appointment_id"] == apt_id
    assert res_status.json()["status"] == "scheduled"

    # 3. Log in as staff and check doctor's dashboard
    res_staff = client.post("/staff/login", json={"password": "staff123"})
    staff_token = res_staff.json()["token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    res_dash = client.get(f"/staff-portal/{assigned_doc_id}/dashboard", headers=staff_headers)
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert dash_data["staff_id"] == assigned_doc_id
    assert dash_data["is_outpatient"] is True
    assert len(dash_data["appointments"]) >= 1
    assert any(a["appointment_id"] == apt_id for a in dash_data["appointments"])

    # 4. Check doctor's notifications
    res_notifs = client.get(f"/staff-portal/{assigned_doc_id}/notifications", headers=staff_headers)
    assert res_notifs.status_code == 200
    notifs = res_notifs.json()
    assert len(notifs) >= 1
    target_notif = next((n for n in notifs if n["appointment_id"] == apt_id), None)
    assert target_notif is not None
    assert "Elena Fisher" in target_notif["message"]

    # 5. Mark notification as read
    notif_id = target_notif["notification_id"]
    res_read = client.post(f"/staff-portal/{assigned_doc_id}/notifications/{notif_id}/mark-read", headers=staff_headers)
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # 6. Set staff status (off_duty, on_duty, toggle-duty, reject on_break)
    res_status_off = client.post(f"/staff-portal/{assigned_doc_id}/set-status", json={"status": "off_duty"}, headers=staff_headers)
    assert res_status_off.status_code == 200
    assert res_status_off.json()["new_status"] == "off_duty"

    # on_break must be rejected with 400
    res_status_break = client.post(f"/staff-portal/{assigned_doc_id}/set-status", json={"status": "on_break"}, headers=staff_headers)
    assert res_status_break.status_code == 400

    res_status_invalid = client.post(f"/staff-portal/{assigned_doc_id}/set-status", json={"status": "vacation"}, headers=staff_headers)
    assert res_status_invalid.status_code == 400

    # Toggle duty back to on_duty
    res_toggle = client.post(f"/staff-portal/{assigned_doc_id}/toggle-duty", headers=staff_headers)
    assert res_toggle.status_code == 200
    assert res_toggle.json()["new_status"] == "on_duty"


def test_department_level_queue_and_off_duty_filtering():
    # 1. Book 4 consecutive OPD appointments
    # In OPD there are 3 doctors: Dr. Rajesh Kumar (staff-opd-1), Dr. Ananya Sen (staff-opd-2), Dr. Vikram Malhotra (staff-opd-3)
    # Department queue position should increment: 0, 1, 2, 3
    results = []
    for i in range(4):
        res = client.post("/patient-portal/book-appointment", json={
            "patient_name": f"Patient {i+1}",
            "patient_age": 30 + i,
            "reason_for_visit": f"Routine checkup {i+1}",
            "department_id": "opd"
        })
        assert res.status_code == 200
        results.append(res.json())

    for i, r in enumerate(results):
        assert r["department_queue_position"] == i

    # Check status lookup returns department_queue_position
    apt_id_3 = results[3]["appointment_id"]
    res_lookup = client.get(f"/patient-portal/appointment/{apt_id_3}")
    assert res_lookup.status_code == 200
    assert res_lookup.json()["department_queue_position"] == 3

    # 2. Test off_duty filtering
    # Log in staff
    res_staff = client.post("/staff/login", json={"password": "staff123"})
    staff_headers = {"Authorization": f"Bearer {res_staff.json()['token']}"}

    # Set staff-opd-1 and staff-opd-2 to off_duty
    client.post("/staff-portal/staff-opd-1/set-status", json={"status": "off_duty"}, headers=staff_headers)
    client.post("/staff-portal/staff-opd-2/set-status", json={"status": "off_duty"}, headers=staff_headers)

    # Now booking in OPD MUST go to staff-opd-3 (the only active doctor)
    res_single = client.post("/patient-portal/book-appointment", json={
        "patient_name": "Lone Active Doc Patient",
        "patient_age": 45,
        "reason_for_visit": "Fever",
        "department_id": "opd"
    })
    assert res_single.status_code == 200
    assert res_single.json()["doctor_id"] == "staff-opd-3"

    # Set staff-opd-3 to off_duty as well -> now 0 active doctors in OPD -> 400 Bad Request (No doctors available)
    client.post("/staff-portal/staff-opd-3/set-status", json={"status": "off_duty"}, headers=staff_headers)
    res_none = client.post("/patient-portal/book-appointment", json={
        "patient_name": "No Doctor Available",
        "patient_age": 50,
        "reason_for_visit": "Fever",
        "department_id": "opd"
    })
    assert res_none.status_code == 400
    assert "No available doctors" in res_none.json()["detail"]


def test_appointment_cancellation_and_queue_recalc():
    # 1. Book 3 appointments
    res1 = client.post("/patient-portal/book-appointment", json={
        "patient_name": "Patient Alpha",
        "department_id": "opd"
    })
    res2 = client.post("/patient-portal/book-appointment", json={
        "patient_name": "Patient Beta",
        "department_id": "opd"
    })
    res3 = client.post("/patient-portal/book-appointment", json={
        "patient_name": "Patient Gamma",
        "department_id": "opd"
    })
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res3.status_code == 200

    apt2_id = res2.json()["appointment_id"]
    apt3_id = res3.json()["appointment_id"]

    # 2. Cancel Patient Beta (apt2)
    res_cancel = client.post(f"/patient-portal/appointment/{apt2_id}/cancel")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["new_status"] == "cancelled"

    # Verify status is now cancelled
    res_check2 = client.get(f"/patient-portal/appointment/{apt2_id}")
    assert res_check2.status_code == 200
    assert res_check2.json()["status"] == "cancelled"

    # Cancelling again should fail with 400
    res_cancel_again = client.post(f"/patient-portal/appointment/{apt2_id}/cancel")
    assert res_cancel_again.status_code == 400

    # 3. Check Patient Gamma (apt3) has recalculated department queue position
    res_check3 = client.get(f"/patient-portal/appointment/{apt3_id}")
    assert res_check3.status_code == 200
    assert res_check3.json()["department_queue_position"] == 1


def test_case_log_and_clinical_notes_access_control():
    # 1. Staff and Admin logins
    res_staff = client.post("/staff/login", json={"password": "staff123"})
    staff_token = res_staff.json()["token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    res_admin = client.post("/admin/login", json={"password": "changeme"})
    admin_token = res_admin.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Book an outpatient appointment
    res_apt = client.post("/patient-portal/book-appointment", json={
        "patient_name": "Marcus Vance",
        "patient_age": 42,
        "reason_for_visit": "Ear pain",
        "department_id": "ent"
    })
    assert res_apt.status_code == 200
    apt_id = res_apt.json()["appointment_id"]
    assigned_doc_id = res_apt.json()["doctor_id"]

    # 3. Unassigned staff member cannot view case log (403)
    unassigned_staff_id = "staff-er-1"
    res_forbidden = client.get(
        f"/case-log/appointment/{apt_id}?staff_id={unassigned_staff_id}",
        headers=staff_headers
    )
    assert res_forbidden.status_code == 403

    # 4. Assigned staff can view case log
    res_case = client.get(
        f"/case-log/appointment/{apt_id}?staff_id={assigned_doc_id}",
        headers=staff_headers
    )
    assert res_case.status_code == 200
    case_data = res_case.json()
    assert case_data["patient_name"] == "Marcus Vance"
    assert len(case_data["timeline"]) >= 1

    # 5. Assigned staff adds a consultation note
    res_note = client.post(
        f"/case-log/appointment/{apt_id}/note",
        json={
            "staff_id": assigned_doc_id,
            "note_type": "consultation_outcome",
            "content": "Otitis media diagnosed. Prescribed amoxicillin 500mg TID x 7 days."
        },
        headers=staff_headers
    )
    assert res_note.status_code == 200
    assert res_note.json()["status"] == "success"

    # Invalid note type returns 400
    res_bad_note = client.post(
        f"/case-log/appointment/{apt_id}/note",
        json={
            "staff_id": assigned_doc_id,
            "note_type": "invalid_type",
            "content": "Some notes"
        },
        headers=staff_headers
    )
    assert res_bad_note.status_code == 400

    # 6. Admin can view case log without staff_id
    res_admin_case = client.get(
        f"/case-log/appointment/{apt_id}",
        headers=admin_headers
    )
    assert res_admin_case.status_code == 200
    assert len(res_admin_case.json()["timeline"]) >= 2  # Event + Note


def test_doctor_and_nurse_inpatient_allocation_and_notes():
    # 1. Admin login to register intake
    res_admin = client.post("/admin/login", json={"password": "changeme"})
    admin_headers = {"Authorization": f"Bearer {res_admin.json()['token']}"}

    intake_payload = {
        "name": "Sarah Connor",
        "age": 29,
        "department_needed": "er",
        "severity": "moderate",
        "reason_for_visit": "Fracture evaluation",
        "predicted_stay_hours": 4.0
    }
    res_intake = client.post("/patients/intake", json=intake_payload, headers=admin_headers)
    assert res_intake.status_code == 200
    p_id = res_intake.json()["patient_id"]



    # 2. Run allocation cycle via rule engine
    from src.allocation.engine import HospitalAllocationEngine
    from src.api.db import SessionLocal
    from src.db.models import Patient

    db = SessionLocal()
    engine = HospitalAllocationEngine()
    engine.run_allocation_cycle(db)

    # 3. Verify Patient has both doctor and nurse assigned
    patient = db.query(Patient).filter_by(patient_id=p_id).first()
    assert patient is not None
    assert patient.assigned_doctor_id is not None
    assert patient.assigned_nurse_id is not None
    assert patient.assigned_doctor_id != patient.assigned_nurse_id
    doc_id = patient.assigned_doctor_id
    nurse_id = patient.assigned_nurse_id

    # 4. Check staff login and add initial_assessment note by doctor
    res_staff = client.post("/staff/login", json={"password": "staff123"})
    staff_headers = {"Authorization": f"Bearer {res_staff.json()['token']}"}

    res_note1 = client.post(
        f"/case-log/patient/{p_id}/note",
        json={
            "staff_id": doc_id,
            "note_type": "initial_assessment",
            "content": "Patient evaluated in ER. Vitals stable. Left arm splint applied."
        },
        headers=staff_headers
    )
    assert res_note1.status_code == 200

    # 5. Add discharge summary note
    res_note2 = client.post(
        f"/case-log/patient/{p_id}/note",
        json={
            "staff_id": doc_id,
            "note_type": "discharge_summary",
            "content": "Patient stable for discharge with follow-up in orthopedic clinic."
        },
        headers=staff_headers
    )
    assert res_note2.status_code == 200

    # 6. Nurse can also view case log
    res_nurse_case = client.get(
        f"/case-log/patient/{p_id}?staff_id={nurse_id}",
        headers=staff_headers
    )
    assert res_nurse_case.status_code == 200
    assert res_nurse_case.json()["patient_name"] == "Sarah Connor"
    assert len(res_nurse_case.json()["timeline"]) >= 3

    db.close()


def test_appointment_rescheduling():
    # 1. Book initial appointment
    res1 = client.post("/patient-portal/book-appointment", json={
        "patient_name": "Oliver Twist",
        "patient_age": 12,
        "reason_for_visit": "Persistent cough",
        "department_id": "opd"
    })
    assert res1.status_code == 200
    old_apt = res1.json()
    old_id = old_apt["appointment_id"]

    # 2. Reschedule the appointment
    res_resched = client.post(f"/patient-portal/appointment/{old_id}/reschedule")
    assert res_resched.status_code == 200
    new_apt = res_resched.json()
    new_id = new_apt["appointment_id"]
    assert new_id != old_id
    assert new_apt["patient_name"] == "Oliver Twist"
    assert new_apt["patient_age"] == 12
    assert new_apt["reason_for_visit"] == "Persistent cough"
    assert new_apt["status"] == "scheduled"
    assert new_apt["rescheduled_from"] == old_id

    # 3. Check old appointment is cancelled
    res_old_check = client.get(f"/patient-portal/appointment/{old_id}")
    assert res_old_check.status_code == 200
    assert res_old_check.json()["status"] == "cancelled"

    # 4. Trying to reschedule a cancelled appointment should return 400
    res_bad = client.post(f"/patient-portal/appointment/{old_id}/reschedule")
    assert res_bad.status_code == 400
    assert "Cannot reschedule" in res_bad.json()["detail"]


def test_admin_case_log_appointments_browser():
    # 1. Book 2 appointments
    client.post("/patient-portal/book-appointment", json={
        "patient_name": "Alice Wonderland",
        "patient_age": 25,
        "reason_for_visit": "Checkup",
        "department_id": "opd"
    })
    client.post("/patient-portal/book-appointment", json={
        "patient_name": "Bob Builder",
        "patient_age": 40,
        "reason_for_visit": "Throat pain",
        "department_id": "ent"
    })

    # 2. Unauthenticated request to /case-log/appointments -> 401
    res_unauth = client.get("/case-log/appointments")
    assert res_unauth.status_code == 401

    # 3. Staff token to /case-log/appointments -> 403
    res_staff = client.post("/staff/login", json={"password": "staff123"})
    staff_token = res_staff.json()["token"]
    res_staff_forb = client.get("/case-log/appointments", headers={"Authorization": f"Bearer {staff_token}"})
    assert res_staff_forb.status_code == 403

    # 4. Admin token to /case-log/appointments -> 200 with appointment records
    res_admin = client.post("/admin/login", json={"password": "changeme"})
    admin_token = res_admin.json()["token"]
    res_admin_apts = client.get("/case-log/appointments", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin_apts.status_code == 200
    apts_list = res_admin_apts.json()
    assert len(apts_list) >= 2
    assert any(a["patient_name"] == "Alice Wonderland" for a in apts_list)
    assert any(a["patient_name"] == "Bob Builder" for a in apts_list)



