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
    Handles booking, load-balanced doctor assignment, department-wide queue positions,
    parallel-throughput wait-time estimation, and queue progression.
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
        2. Assigns least-loaded on-duty doctor in department.
        3. Computes department-level queue position and parallel throughput wait time.
        4. Creates Appointment, StaffNotification, and EventLog.
        """
        # 1. Validate department
        dept = session.query(Department).filter_by(department_id=department_id).first()
        if not dept:
            raise ValueError(f"Department '{department_id}' not found.")
        if dept.total_beds > 0:
            raise ValueError(f"Department '{dept.name}' is an inpatient department. Appointments are only for outpatient clinics (OPD, ENT).")

        # 2. Find on-duty doctors in this department (strictly exclude off_duty and on_break)
        doctors = session.query(Staff).filter(
            Staff.department_id == department_id,
            Staff.status.in_(["on_duty", "reassigned"])
        ).all()

        if not doctors:
            raise ValueError(f"No available doctors currently on duty in department '{dept.name}'.")

        # Calculate active workload for each on-duty doctor (count of scheduled + in_consultation)
        doctor_loads = []
        for doc in doctors:
            active_apts = session.query(Appointment).filter(
                Appointment.doctor_id == doc.staff_id,
                Appointment.status.in_(["scheduled", "in_consultation"])
            ).count()
            doctor_loads.append((doc, active_apts))

        # Sort by load ascending to pick the least-loaded doctor
        doctor_loads.sort(key=lambda x: x[1])
        assigned_doctor = doctor_loads[0][0]

        # 3. Department-Level Queue Position: count of ALL scheduled appointments in this department created before this one
        dept_scheduled_count = session.query(Appointment).filter(
            Appointment.department_id == department_id,
            Appointment.status == "scheduled"
        ).count()
        department_queue_position = dept_scheduled_count  # 0, 1, 2, 3...

        # 4. Department-Wide Estimated Wait Time using parallel throughput:
        # avg_consult across active doctors in department
        avg_consult = (sum(doc.avg_consult_minutes or 15 for doc in doctors) / max(1, len(doctors))) if doctors else (assigned_doctor.avg_consult_minutes or 15)
        num_doctors = len(doctors)
        estimated_wait_minutes = round((department_queue_position / max(1, num_doctors)) * avg_consult)

        # 5. Doctor-specific queue position (for clinical staff portal view)
        doc_scheduled_ahead = session.query(Appointment).filter(
            Appointment.doctor_id == assigned_doctor.staff_id,
            Appointment.status == "scheduled"
        ).count()
        doctor_queue_position = doc_scheduled_ahead + 1

        # 6. Generate appointment ID
        appointment_id = f"APT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now()

        # 7. Create Appointment row
        appointment = Appointment(
            appointment_id=appointment_id,
            patient_name=patient_name,
            patient_age=patient_age,
            reason_for_visit=reason_for_visit,
            department_id=department_id,
            doctor_id=assigned_doctor.staff_id,
            scheduled_time=now,
            estimated_wait_minutes=estimated_wait_minutes,
            queue_position=doctor_queue_position,
            department_queue_position=department_queue_position,
            status="scheduled"
        )
        session.add(appointment)

        # 8. Create StaffNotification for assigned doctor
        age_str = f", Age: {patient_age}" if patient_age is not None else ""
        reason_str = f" | Reason: {reason_for_visit}" if reason_for_visit else ""
        display_pos = department_queue_position + 1
        notif_msg = (
            f"New Appointment: {patient_name}{age_str}{reason_str} "
            f"[Dept Queue #{display_pos}, Est. Wait: {estimated_wait_minutes} mins]"
        )
        notif = StaffNotification(
            staff_id=assigned_doctor.staff_id,
            appointment_id=appointment_id,
            message=notif_msg,
            is_read=False,
            created_at=now
        )
        session.add(notif)

        # 9. Log EventLog
        event = EventLog(
            event_type="appointment_booked",
            entity_id=appointment_id,
            description=f"Appointment {appointment_id} booked for {patient_name} in {dept.name} (Assigned to {assigned_doctor.role}, Dept Line #{display_pos}).",
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
            "department_queue_position": appointment.department_queue_position,
            "estimated_wait_minutes": appointment.estimated_wait_minutes,
            "status": appointment.status,
            "scheduled_time": appointment.scheduled_time.isoformat()
        }

    def advance_queue(self, session: Session, department_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Advances the outpatient consultation queues:
        - For each doctor with an appointment 'in_consultation', checks if completed.
        - If doctor is free (no 'in_consultation'), moves earliest 'scheduled' appointment to 'in_consultation'.
        - Recalculates department_queue_position and estimated_wait_minutes across all remaining scheduled appointments in the department.
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
            on_duty_doctors = [doc for doc in doctors if doc.status in ["on_duty", "reassigned"]]

            for doc in doctors:
                # 1. Check if active consultation has completed
                in_consult = session.query(Appointment).filter(
                    Appointment.doctor_id == doc.staff_id,
                    Appointment.status == "in_consultation"
                ).first()

                if in_consult:
                    elapsed = (now - (in_consult.scheduled_time or now)).total_seconds()
                    # Complete consultation after 20 seconds of simulation time
                    if elapsed >= 20.0:
                        in_consult.status = "completed"
                        completed_count += 1
                        session.add(in_consult)

                        evt = EventLog(
                            event_type="consultation_completed",
                            entity_id=in_consult.appointment_id,
                            description=f"Consultation completed for {in_consult.patient_name} by {doc.role} ({doc.room_number}).",
                            triggered_by="rule_engine",
                            timestamp=now
                        )
                        session.add(evt)
                        in_consult = None

                # 2. If doctor is on_duty/reassigned and has no active consultation, pick next scheduled patient
                if not in_consult and doc.status in ["on_duty", "reassigned"]:
                    next_apt = session.query(Appointment).filter(
                        Appointment.doctor_id == doc.staff_id,
                        Appointment.status == "scheduled"
                    ).order_by(Appointment.scheduled_time.asc()).first()

                    if next_apt:
                        next_apt.status = "in_consultation"
                        next_apt.queue_position = 0
                        next_apt.department_queue_position = 0
                        next_apt.estimated_wait_minutes = 0
                        next_apt.scheduled_time = now
                        session.add(next_apt)
                        consulting_count += 1

                        notif = StaffNotification(
                            staff_id=doc.staff_id,
                            appointment_id=next_apt.appointment_id,
                            message=f"Now Calling: Patient {next_apt.patient_name} to {doc.room_number or 'Consultation Room'}.",
                            is_read=False,
                            created_at=now
                        )
                        session.add(notif)

            # 3. Recalculate department-wide queue positions and parallel wait times for all waiting patients in this department
            all_dept_waiting = session.query(Appointment).filter(
                Appointment.department_id == d_id,
                Appointment.status == "scheduled"
            ).order_by(Appointment.scheduled_time.asc()).all()

            num_active_docs = len(on_duty_doctors)
            avg_consult_dept = (sum(d.avg_consult_minutes or 15 for d in on_duty_doctors) / max(1, num_active_docs)) if on_duty_doctors else 15

            for idx, apt in enumerate(all_dept_waiting):
                apt.department_queue_position = idx
                apt.estimated_wait_minutes = round((idx / max(1, num_active_docs)) * avg_consult_dept)
                session.add(apt)

            # 4. Also update doctor-specific queue positions
            for doc in doctors:
                doc_waiting = session.query(Appointment).filter(
                    Appointment.doctor_id == doc.staff_id,
                    Appointment.status == "scheduled"
                ).order_by(Appointment.scheduled_time.asc()).all()
                for doc_idx, doc_apt in enumerate(doc_waiting, start=1):
                    doc_apt.queue_position = doc_idx
                    session.add(doc_apt)

        session.commit()
        return {
            "completed": completed_count,
            "started_consultation": consulting_count
        }

    def get_appointment_status(self, session: Session, appointment_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches live appointment status and department-wide queue details.
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
            "department_queue_position": apt.department_queue_position,
            "estimated_wait_minutes": apt.estimated_wait_minutes,
            "scheduled_time": apt.scheduled_time.isoformat() if apt.scheduled_time else None
        }

appointment_scheduler = AppointmentScheduler()
