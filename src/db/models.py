from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Enum,
    Text,
    Boolean,
)
from sqlalchemy.orm import relationship
from src.api.db import Base

class Department(Base):
    __tablename__ = "departments"

    department_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    total_beds = Column(Integer, default=0, nullable=False)
    total_staff_slots = Column(Integer, default=0, nullable=False)

    # Relationships
    beds = relationship("Bed", back_populates="department", cascade="all, delete-orphan")
    staff_members = relationship("Staff", back_populates="department", cascade="all, delete-orphan")
    diagnostic_facilities = relationship("DiagnosticFacility", back_populates="department", cascade="all, delete-orphan")
    patients = relationship("Patient", back_populates="department", foreign_keys="[Patient.department_needed]")


class Bed(Base):
    __tablename__ = "beds"

    bed_id = Column(String(50), primary_key=True, index=True)
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False, index=True)
    bed_type = Column(String(50), default="standard")  # standard, icu, pediatric, emergency
    status = Column(String(50), default="available", index=True)  # available, occupied, cleaning, reserved
    current_patient_id = Column(String(50), ForeignKey("patients.patient_id", use_alter=True, name="fk_bed_patient"), nullable=True)
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    department = relationship("Department", back_populates="beds")
    current_patient = relationship("Patient", foreign_keys=[current_patient_id], post_update=True)


class Staff(Base):
    __tablename__ = "staff"

    staff_id = Column(String(50), primary_key=True, index=True)
    role = Column(String(50), nullable=False)  # doctor, nurse, technician, specialist
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False, index=True)
    shift_start = Column(String(20), default="08:00")
    shift_end = Column(String(20), default="20:00")
    status = Column(String(50), default="on_duty", index=True)  # on_duty, off_duty, reassigned
    room_number = Column(String(20), nullable=True)
    floor = Column(String(20), nullable=True)
    specialty = Column(String(100), nullable=True)
    avg_consult_minutes = Column(Integer, default=15)

    # Relationships
    department = relationship("Department", back_populates="staff_members")


class DiagnosticFacility(Base):
    __tablename__ = "diagnostic_facilities"

    facility_id = Column(String(50), primary_key=True, index=True)
    type = Column(String(100), nullable=False)  # CT Scanner, X-Ray, Ultrasound, ECG, Blood Gas Analyzer, Spirometer
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False, index=True)
    status = Column(String(50), default="free", index=True)  # free, in_use, maintenance
    avg_procedure_minutes = Column(Integer, default=30)
    current_patient_id = Column(String(50), ForeignKey("patients.patient_id", use_alter=True, name="fk_facility_patient"), nullable=True)
    in_use_since = Column(DateTime, nullable=True)

    # Relationships
    department = relationship("Department", back_populates="diagnostic_facilities")


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String(50), primary_key=True, index=True)
    arrival_time = Column(DateTime, default=datetime.now, index=True)
    department_needed = Column(String(50), ForeignKey("departments.department_id"), nullable=False, index=True)
    severity = Column(String(50), nullable=False, index=True)  # critical, moderate, low
    predicted_stay_hours = Column(Float, default=4.0)
    status = Column(String(50), default="waiting", index=True)  # waiting, admitted, in_diagnostic, discharged
    assigned_bed_id = Column(String(50), ForeignKey("beds.bed_id", use_alter=True, name="fk_patient_bed"), nullable=True)
    assigned_staff_id = Column(String(50), ForeignKey("staff.staff_id", use_alter=True, name="fk_patient_staff"), nullable=True)
    age = Column(Integer, nullable=True)
    reason_for_visit = Column(Text, nullable=True)

    # Relationships
    department = relationship("Department", back_populates="patients", foreign_keys=[department_needed])
    assigned_bed = relationship("Bed", foreign_keys=[assigned_bed_id], post_update=True)
    assigned_staff = relationship("Staff", foreign_keys=[assigned_staff_id], post_update=True)


class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(String(50), primary_key=True, index=True)
    patient_name = Column(String(100), nullable=False)
    patient_age = Column(Integer, nullable=True)
    reason_for_visit = Column(Text, nullable=True)
    department_id = Column(String(50), ForeignKey("departments.department_id"), nullable=False)
    doctor_id = Column(String(50), ForeignKey("staff.staff_id"), nullable=True)
    scheduled_time = Column(DateTime, default=datetime.now)
    estimated_wait_minutes = Column(Integer, default=0)
    queue_position = Column(Integer, nullable=True)
    status = Column(String(50), default="scheduled")  # scheduled, in_consultation, completed, no_show, cancelled
    patient_id = Column(String(50), ForeignKey("patients.patient_id"), nullable=True)

    # Relationships
    department = relationship("Department")
    doctor = relationship("Staff", foreign_keys=[doctor_id])


class StaffNotification(Base):
    __tablename__ = "staff_notifications"

    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    staff_id = Column(String(50), ForeignKey("staff.staff_id"), nullable=False, index=True)
    patient_id = Column(String(50), nullable=True)
    appointment_id = Column(String(50), nullable=True)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    staff = relationship("Staff")


class EventLog(Base):
    __tablename__ = "events_log"

    event_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # patient_arrival, bed_assigned, overflow_assigned, diagnostic_assigned, diagnostic_released, diagnostic_unavailable, staff_reassigned, critical_no_capacity, discharge, appointment_booked
    entity_id = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    triggered_by = Column(String(50), default="rule_engine")  # prediction_engine, manual, rule_engine, simulation, patient_portal
