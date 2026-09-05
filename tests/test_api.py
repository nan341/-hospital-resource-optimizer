import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.db.init_db import init_database

@pytest.fixture(autouse=True)
def setup_api_db():
    init_database(drop_existing=True)
    yield

client = TestClient(app)

def get_admin_headers():
    res = client.post("/admin/login", json={"password": "changeme"})
    token = res.json()["token"]
    return {"Authorization": f"Bearer {token}"}

def test_get_departments():
    headers = get_admin_headers()
    response = client.get("/departments", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 6  # er, general_ward, icu, pediatrics, opd, ent
    dept_ids = [d["department_id"] for d in data]
    assert "er" in dept_ids
    assert "general_ward" in dept_ids
    assert "icu" in dept_ids
    assert "pediatrics" in dept_ids
    assert "opd" in dept_ids
    assert "ent" in dept_ids
    # Check diagnostic fields
    assert all("free_diagnostics" in d for d in data)

def test_get_beds():
    headers = get_admin_headers()
    response = client.get("/beds", headers=headers)
    assert response.status_code == 200
    beds = response.json()
    assert len(beds) == 44  # 8 + 20 + 6 + 10 (OPD and ENT have 0 beds)

    # Filter by department
    res_er = client.get("/beds?department_id=er", headers=headers)
    assert res_er.status_code == 200
    assert len(res_er.json()) == 8

def test_get_diagnostics():
    headers = get_admin_headers()
    response = client.get("/diagnostics", headers=headers)
    assert response.status_code == 200
    diagnostics = response.json()
    assert len(diagnostics) == 8  # 2 per department * 4 inpatient departments
    assert all(d["status"] == "free" for d in diagnostics)

    # Filter by department
    res_icu = client.get("/diagnostics?department_id=icu", headers=headers)
    assert res_icu.status_code == 200
    assert len(res_icu.json()) == 2

def test_get_staff():
    headers = get_admin_headers()
    response = client.get("/staff", headers=headers)
    assert response.status_code == 200
    staff = response.json()
    assert len(staff) == 27  # 22 inpatient + 3 OPD + 2 ENT

def test_get_events():
    headers = get_admin_headers()
    response = client.get("/events?limit=10", headers=headers)
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)

def test_forecast_endpoint():
    response = client.get("/forecast/er")
    assert response.status_code == 200
    data = response.json()
    assert data["department_id"] == "er"
    assert "predicted_count" in data
    assert "hourly_breakdown" in data

def test_simulation_controls_and_surge():
    headers = get_admin_headers()
    # Start simulation
    res_start = client.post("/simulation/start", json={"speed_factor": 3.0}, headers=headers)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "started"

    # Trigger surge
    res_surge = client.post("/simulation/surge", json={"department": "er", "patient_count": 4}, headers=headers)
    assert res_surge.status_code == 200
    data = res_surge.json()
    assert data["status"] == "surge_triggered"
    assert data["patient_count"] == 4

    # Stop simulation
    res_stop = client.post("/simulation/stop", headers=headers)
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "stopped"

    # Check status
    res_status = client.get("/simulation/status", headers=headers)
    assert res_status.status_code == 200
    assert res_status.json()["total_patients_generated"] >= 4

def test_patient_intake():
    headers = get_admin_headers()
    # 1. Test successful patient intake with age and reason_for_visit
    payload = {
        "department_needed": "er",
        "severity": "critical",
        "predicted_stay_hours": 6.0,
        "notes": "Severe chest pain and shortness of breath",
        "age": 58,
        "reason_for_visit": "Acute Coronary Syndrome suspicion"
    }
    response = client.post("/patients/intake", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "registered"
    assert data["patient_id"].startswith("PAT-")
    patient_id = data["patient_id"]

    # 2. Confirm patient is in waiting status and has age/reason
    res_waiting = client.get("/patients?status=waiting", headers=headers)
    assert res_waiting.status_code == 200
    waiting_patients = res_waiting.json()
    p_match = next((p for p in waiting_patients if p["patient_id"] == patient_id), None)
    assert p_match is not None
    assert p_match["age"] == 58
    assert p_match["reason_for_visit"] == "Acute Coronary Syndrome suspicion"

    # 3. Confirm arrival event was logged
    res_events = client.get("/events?limit=10", headers=headers)
    assert res_events.status_code == 200
    events = res_events.json()
    assert any(e["entity_id"] == patient_id and e["triggered_by"] == "manual" for e in events)

    # 4. Test invalid department returns 404
    res_bad_dept = client.post("/patients/intake", json={
        "department_needed": "nonexistent_dept",
        "severity": "moderate"
    }, headers=headers)
    assert res_bad_dept.status_code == 404
