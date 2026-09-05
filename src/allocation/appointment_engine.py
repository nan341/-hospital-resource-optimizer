import os
import sys
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.db.models import Department, Staff, Appointment, StaffNotification, EventLog

logger = logging.getLogger(__name__)

class AppointmentScheduler:
    """
    Independent scheduling engine for outpatient departments (OPD, ENT).
    Handles booking, doctor load-balancing, wait-time estimation, and queue progression.
    """

    def book_appointment(
        self,
        session: Session,
        patient_name: str,
        patient_age: Optional[int],
        reason_for_visit: Optional[str],
        department_id: str
    ) -> Dict[str, Any]:
        """
        Books an outpatient appointment:
        1. Validates department is outpatient (total_beds == 0).
        2. Assigns least-loaded doctor in department.
        3. Calculates queue position & estimated wait time.
        4. Creates Appointment, StaffNotification, and EventLog.
        """
        # 1. Validate department
        dept = session.query(Department).filter_by(department_id=department_id).first()
        if not dept:
            raise ValueError(f"Department '{department_id}' not found.")
        if dept.total_beds > 0:
            raise ValueError(f"Department '{dept.name}' is an inpatient department. Appointments are only for outpatient clinics (OPD, ENT).")

        # 2. Find least-loaded doctor in this department
        # Doctors on_duty in this department
        doctors = session.query(Staff).filter(
            Staff.department_id == department_id,
            Staff.status.in_(["on_duty", "reassigned"])
        ).all()

        if not doctors:
            # Fallback to any staff in department if none specifically on duty
            doctors = session.query(Staff).filter_by(department_id=department_id).all()

        if not doctors:
            raise ValueError(f"No available doctors found in department '{dept.name}'.")

        # Calculate active workload for each doctor (count of scheduled + in_consultation)
        doctor_loads = []
        for doc in doctors:
            active_apts = session.query(Appointment).filter(
                Appointment.doctor_id == doc.staff_id,
                Appointment.status.in_(["scheduled", "in_consultation"])
            ).count()
            doctor_loads.append((doc, active_apts))

        # Sort by load ascending
        doctor_loads.sort(key=lambda x: x[1])
        assigned_doctor = doctor_loads[0][0]

        # 3. Queue position is count of scheduled appointments ahead of this one + 1
        scheduled_ahead = session.query(Appointment).filter(
            Appointment.doctor_id == assigned_doctor.staff_id,
            Appointment.status == "scheduled"
        ).count()
        in_consult = session.query(Appointment).filter(
            Appointment.doctor_id == assigned_doctor.staff_id,
            Appointment.status == "in_consultation"
        ).count()

        queue_position = scheduled_ahead + 1
        # Estimated wait = (scheduled ahead + 1 if doctor is currently busy) * avg_consult_minutes
        avg_mins = assigned_doctor.avg_consult_minutes or 15
        estimated_wait_minutes = (scheduled_ahead + (1 if in_consult > 0 else 0)) * avg_mins

        # 4. Generate appointment ID
        appointment_id = f"APT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now()

        # 5. Create Appointment row
        appointment = Appointment(
            appointment_id=appointment_id,
            patient_name=patient_name,
            patient_age=patient_age,
            reason_for_visit=reason_for_visit,
            department_id=department_id,
            doctor_id=assigned_doctor.staff_id,
            scheduled_time=now,
            estimated_wait_minutes=estimated_wait_minutes,
            queue_position=queue_position,
            status="scheduled"
        )
        session.add(appointment)

        # 6. Create StaffNotification for assigned doctor
        age_str = f", Age: {patient_age}" if patient_age is not None else ""
        reason_str = f" | Reason: {reason_for_visit}" if reason_for_visit else ""
        notif_msg = (
            f"New Appointment: {patient_name}{age_str}{reason_str} "
            f"[Queue #{queue_position}, Est. Wait: {estimated_wait_minutes} mins]"
        )
        notif = StaffNotification(
            staff_id=assigned_doctor.staff_id,
            appointment_id=appointment_id,
            message=notif_msg,
            is_read=False,
            created_at=now
        )
        session.add(notif)

        # 7. Log EventLog
        event = EventLog(
            event_type="appointment_booked",
            entity_id=appointment_id,
            description=f"Appointment {appointment_id} booked for {patient_name} with {assigned_doctor.role} in {dept.name} (Queue #{queue_position}).",
            triggered_by="patient_portal",
            timestamp=now
        )
        session.add(event)

        session.commit()
        session.refresh(appointment)

        return {
            "appointment_id": appointment.appointment_id,
            "patient_name": appointment.patient_name,
            "patient_age": appointment.patient_age,
            "reason_for_visit": appointment.reason_for_visit,
            "department_id": appointment.department_id,
            "department_name": dept.name,
            "doctor_id": assigned_doctor.staff_id,
            "doctor_name": assigned_doctor.role,
            "specialty": assigned_doctor.specialty or "General",
            "room_number": assigned_doctor.room_number or "Room 101",
            "floor": assigned_doctor.floor or "1st Floor",
            "queue_position": appointment.queue_position,
            "estimated_wait_minutes": appointment.estimated_wait_minutes,
            "status": appointment.status,
            "scheduled_time": appointment.scheduled_time.isoformat()
        }

    def advance_queue(self, session: Session, department_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Advances the outpatient consultation queues:
        - For each doctor with an appointment 'in_consultation', checks if completed.
        - If doctor is free (no 'in_consultation'), moves earliest 'scheduled' appointment to 'in_consultation'.
        - Updates queue_position and estimated_wait_minutes for remaining waiting appointments.
        """
        now = datetime.now()
        outpatient_depts = session.query(Department).filter(Department.total_beds == 0).all()
        dept_ids = [d.department_id for d in outpatient_depts]

        if department_id:
            dept_ids = [department_id] if department_id in dept_ids else []

        completed_count = 0
        consulting_count = 0

        for d_id in dept_ids:
            doctors = session.query(Staff).filter_by(department_id=d_id).all()
            for doc in doctors:
                avg_mins = doc.avg_consult_minutes or 15

                # 1. Check if active consultation has completed
                in_consult = session.query(Appointment).filter(
                    Appointment.doctor_id == doc.staff_id,
                    Appointment.status == "in_consultation"
                ).first()

                # In real-time / prototype demo, simulate consultation progression
                if in_consult:
                    # If consultation has run for simulated duration (or 15s in active worker loop)
                    elapsed = (now - (in_consult.scheduled_time or now)).total_seconds()
                    # Complete consultation after 20 seconds of simulation time
                    if elapsed >= 20.0:
                        in_consult.status = "completed"
                        completed_count += 1
                        session.add(in_consult)

                        # Create event
                        evt = EventLog(
                            event_type="consultation_completed",
                            entity_id=in_consult.appointment_id,
                            description=f"Consultation completed for {in_consult.patient_name} by {doc.role} ({doc.room_number}).",
                            triggered_by="rule_engine",
                            timestamp=now
                        )
                        session.add(evt)
                        in_consult = None

                # 2. If no active consultation, pick next scheduled patient
                if not in_consult:
                    next_apt = session.query(Appointment).filter(
                        Appointment.doctor_id == doc.staff_id,
                        Appointment.status == "scheduled"
                    ).order_by(Appointment.scheduled_time.asc()).first()

                    if next_apt:
                        next_apt.status = "in_consultation"
                        next_apt.queue_position = 0
                        next_apt.estimated_wait_minutes = 0
                        next_apt.scheduled_time = now
                        session.add(next_apt)
                        consulting_count += 1

                        # Notify doctor
                        notif = StaffNotification(
                            staff_id=doc.staff_id,
                            appointment_id=next_apt.appointment_id,
                            message=f"Now Calling: Patient {next_apt.patient_name} to {doc.room_number or 'Consultation Room'}.",
                            is_read=False,
                            created_at=now
                        )
                        session.add(notif)

                # 3. Recalculate queue positions and estimated wait for remaining scheduled appointments
                waiting_apts = session.query(Appointment).filter(
                    Appointment.doctor_id == doc.staff_id,
                    Appointment.status == "scheduled"
                ).order_by(Appointment.scheduled_time.asc()).all()

                has_active_consult = (in_consult is not None) or (consulting_count > 0)
                for idx, apt in enumerate(waiting_apts, start=1):
                    apt.queue_position = idx
                    apt.estimated_wait_minutes = (idx - 1 + (1 if has_active_consult else 0)) * avg_mins
                    session.add(apt)

        session.commit()
        return {
            "completed": completed_count,
            "started_consultation": consulting_count
        }

    def get_appointment_status(self, session: Session, appointment_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches live appointment status and queue details.
        """
        apt = session.query(Appointment).filter_by(appointment_id=appointment_id).first()
        if not apt:
            return None

        doc = session.query(Staff).filter_by(staff_id=apt.doctor_id).first()
        dept = session.query(Department).filter_by(department_id=apt.department_id).first()

        return {
            "appointment_id": apt.appointment_id,
            "patient_name": apt.patient_name,
            "patient_age": apt.patient_age,
            "reason_for_visit": apt.reason_for_visit,
            "department_id": apt.department_id,
            "department_name": dept.name if dept else apt.department_id,
            "doctor_id": apt.doctor_id,
            "doctor_name": doc.role if doc else "Physician",
            "specialty": doc.specialty if doc else "General",
            "room_number": doc.room_number if doc else "OPD Room",
            "floor": doc.floor if doc else "1st Floor",
            "status": apt.status,
            "queue_position": apt.queue_position,
            "estimated_wait_minutes": apt.estimated_wait_minutes,
            "scheduled_time": apt.scheduled_time.isoformat() if apt.scheduled_time else None
        }

appointment_scheduler = AppointmentScheduler()
