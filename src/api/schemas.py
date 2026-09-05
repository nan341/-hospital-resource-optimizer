from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    department_id: str
    name: str
    total_beds: int
    total_staff_slots: int
    occupied_beds: int = 0
    available_beds: int = 0
    cleaning_beds: int = 0
    reserved_beds: int = 0
    occupancy_rate: float = 0.0
    on_duty_staff: int = 0
    total_diagnostics: int = 0
    free_diagnostics: int = 0

class BedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bed_id: str
    department_id: str
    bed_type: str
    status: str
    current_patient_id: Optional[str] = None
    last_updated: Optional[datetime] = None

class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    staff_id: str
    role: str
    department_id: str
    shift_start: str
    shift_end: str
    status: str
    active_patients: int = 0
    is_busy: bool = False

class DiagnosticFacilityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    facility_id: str
    type: str
    department_id: str
    status: str
    avg_procedure_minutes: int
    current_patient_id: Optional[str] = None
    in_use_since: Optional[datetime] = None

class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    patient_id: str
    arrival_time: datetime
    department_needed: str
    severity: str
    predicted_stay_hours: float
    status: str
    assigned_bed_id: Optional[str] = None
    assigned_staff_id: Optional[str] = None
    age: Optional[int] = None
    reason_for_visit: Optional[str] = None

class PatientIntakeRequest(BaseModel):
    department_needed: str = Field(..., description="Target department ID (e.g. er, general_ward, icu, pediatrics)")
    severity: str = Field(..., pattern="^(critical|moderate|low)$", description="Acuity level: critical, moderate, low")
    predicted_stay_hours: float = Field(default=4.0, ge=0.5, le=336.0, description="Estimated stay duration in hours")
    notes: Optional[str] = Field(default=None, max_length=200, description="Optional clinical/admission notes")
    age: Optional[int] = Field(default=None, ge=0, le=130, description="Patient age in years")
    reason_for_visit: Optional[str] = Field(default=None, max_length=300, description="Chief complaint / clinical reason for visit")

class PatientIntakeResponse(BaseModel):
    status: str
    patient_id: str
    arrival_time: str


class EventLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    timestamp: datetime
    event_type: str
    entity_id: str
    description: str
    triggered_by: str

class SurgeRequest(BaseModel):
    department: str = Field(default="er", description="Target department ID e.g. er, general_ward, icu, pediatrics")
    patient_count: int = Field(default=8, ge=1, le=50, description="Number of critical patients in surge burst")

class SimulationControlRequest(BaseModel):
    speed_factor: Optional[float] = 2.0

class SimulationStatusResponse(BaseModel):
    is_running: bool
    speed_factor: float
    simulated_time: str
    total_patients_generated: int
    queue_length: int
    active_admissions: int

class ForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    department_id: str
    department_name: str
    horizon_hours: int
    predicted_count: float
    ci_lower: float
    ci_upper: float
    hourly_breakdown: List[Dict[str, Any]]
    recent_observed_rate: float
    model_type: str
