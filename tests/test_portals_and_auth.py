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

    # 6. Set staff status (on_break, off_duty, on_duty)
    res_status_break = client.post(f"/staff-portal/{assigned_doc_id}/set-status", json={"status": "on_break"}, headers=staff_headers)
    assert res_status_break.status_code == 200
    assert res_status_break.json()["new_status"] == "on_break"

    res_status_invalid = client.post(f"/staff-portal/{assigned_doc_id}/set-status", json={"status": "vacation"}, headers=staff_headers)
    assert res_status_invalid.status_code == 400

    res_status_duty = client.post(f"/staff-portal/{assigned_doc_id}/set-status", json={"status": "on_duty"}, headers=staff_headers)
    assert res_status_duty.status_code == 200
    assert res_status_duty.json()["new_status"] == "on_duty"


def test_department_level_queue_and_on_break_filtering():
    # 1. Book 4 consecutive OPD appointments
    # In OPD there are 3 doctors: Dr. Rajesh Kumar (staff_023), Dr. Ananya Sen (staff_024), Dr. Vikram Malhotra (staff_025)
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

    # 2. Test on_break filtering
    # Log in staff
    res_staff = client.post("/staff/login", json={"password": "staff123"})
    staff_headers = {"Authorization": f"Bearer {res_staff.json()['token']}"}

    # Set staff-opd-1 and staff-opd-2 to on_break
    client.post("/staff-portal/staff-opd-1/set-status", json={"status": "on_break"}, headers=staff_headers)
    client.post("/staff-portal/staff-opd-2/set-status", json={"status": "on_break"}, headers=staff_headers)

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
