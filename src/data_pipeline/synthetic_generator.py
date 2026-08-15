import os
import sys
import uuid
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.db import SessionLocal
from src.db.models import Patient, EventLog, Department
from src.data_pipeline.calibration import get_calibration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyntheticPatientSimulator:
    def __init__(self, speed_factor: float = 1.0):
        """
        speed_factor: simulated hours per real minute.
        e.g., speed_factor = 6.0 means 1 real minute = 6 simulated hours (360x acceleration).
        speed_factor = 1.0 means 1 real minute = 1 simulated hour (60x acceleration).
        """
        self.speed_factor = speed_factor
        self.calibration = get_calibration()
        self.is_running = False
        self.current_sim_time = datetime.now()
        self._surge_queue: List[Dict[str, Any]] = []

    def refresh_calibration(self):
        self.calibration = get_calibration()

    def generate_single_patient(
        self,
        department_id: str,
        severity: Optional[str] = None,
        arrival_time: Optional[datetime] = None,
        is_surge: bool = False
    ) -> Dict[str, Any]:
        """Generates patient properties according to calibration distributions."""
        arrival_dt = arrival_time or self.current_sim_time

        # 1. Acuity / Severity
        if severity is None:
            sev_dist = self.calibration.get("severity_distribution", {"critical": 0.15, "moderate": 0.45, "low": 0.40})
            severities = list(sev_dist.keys())
            weights = list(sev_dist.values())
            severity = random.choices(severities, weights=weights, k=1)[0]

        # 2. Predicted Stay Hours (Gamma distributed)
        los_config = self.calibration.get("los_distributions", {}).get(severity, {
            "gamma_shape": 4.5,
            "gamma_scale": 1.5,
            "mean_hours": 6.0
        })
        shape = los_config.get("gamma_shape", 4.5)
        scale = los_config.get("gamma_scale", 1.5)
        stay_hours = round(float(np.random.gamma(shape, scale)), 1)
        stay_hours = max(0.5, min(stay_hours, 168.0)) # between 30 mins and 7 days

        patient_id = f"PAT-{uuid.uuid4().hex[:8].upper()}"

        return {
            "patient_id": patient_id,
            "department_needed": department_id,
            "severity": severity,
            "predicted_stay_hours": stay_hours,
            "arrival_time": arrival_dt,
            "status": "waiting",
            "is_surge": is_surge
        }

    def schedule_surge(self, department_id: str, patient_count: int, trigger_time: Optional[datetime] = None):
        """Queues a deterministic scripted surge burst."""
        self._surge_queue.append({
            "department_id": department_id,
            "count": patient_count,
            "trigger_time": trigger_time or self.current_sim_time
        })
        logger.info(f"Scheduled surge: {patient_count} critical patients for {department_id}")

    def execute_surge_now(self, department_id: str, patient_count: int) -> List[Dict[str, Any]]:
        """Instantly writes a batch of critical surge patients to the DB."""
        session = SessionLocal()
        created_patients = []
        try:
            dept = session.query(Department).filter_by(department_id=department_id).first()
            dept_name = dept.name if dept else department_id

            now = datetime.now()
            for i in range(patient_count):
                p_data = self.generate_single_patient(
                    department_id=department_id,
                    severity="critical",
                    arrival_time=now,
                    is_surge=True
                )
                patient = Patient(
                    patient_id=p_data["patient_id"],
                    arrival_time=p_data["arrival_time"],
                    department_needed=p_data["department_needed"],
                    severity=p_data["severity"],
                    predicted_stay_hours=p_data["predicted_stay_hours"],
                    status="waiting"
                )
                session.add(patient)

                event = EventLog(
                    event_type="patient_arrival",
                    entity_id=patient.patient_id,
                    description=f"[SURGE ALERT] Critical patient {patient.patient_id} arrived at {dept_name} (Est. Stay: {patient.predicted_stay_hours}h)",
                    triggered_by="simulation",
                    timestamp=now
                )
                session.add(event)
                created_patients.append(p_data)

            # Record high-priority surge event
            surge_event = EventLog(
                event_type="surge_triggered",
                entity_id=department_id,
                description=f"Mass casualty / surge event triggered: {patient_count} critical patients routed to {dept_name}.",
                triggered_by="simulation",
                timestamp=now
            )
            session.add(surge_event)
            session.commit()
            logger.info(f"Executed surge of {patient_count} critical patients into {department_id}")
            return created_patients
        except Exception as e:
            session.rollback()
            logger.error(f"Error executing surge: {e}")
            raise
        finally:
            session.close()

    async def run_simulation_step(self, time_step_seconds: float = 3.0) -> List[Dict[str, Any]]:
        """Advances simulation by one time step, sampling Poisson arrivals."""
        # Calculate simulated hours progressed in this real time step
        # speed_factor = simulated hours per real minute (60s)
        sim_hours_passed = (time_step_seconds / 60.0) * self.speed_factor
        self.current_sim_time += timedelta(hours=sim_hours_passed)
        current_hour = self.current_sim_time.hour

        hourly_mult = self.calibration.get("hourly_multipliers", [1.0] * 24)[current_hour]
        dept_rates = self.calibration.get("department_base_rates", {
            "er": 4.5, "general_ward": 2.2, "icu": 0.8, "pediatrics": 1.8
        })

        generated_batch = []
        session = SessionLocal()

        try:
            # 1. Process any pending surges
            surges_to_run = []
            for surge in list(self._surge_queue):
                if self.current_sim_time >= surge["trigger_time"]:
                    surges_to_run.append(surge)
                    self._surge_queue.remove(surge)

            for surge in surges_to_run:
                batch = self.execute_surge_now(surge["department_id"], surge["count"])
                generated_batch.extend(batch)

            # 2. Sample Poisson arrivals for each department
            for dept_id, base_rate in dept_rates.items():
                # Expected arrivals in this time step = base_rate * multiplier * sim_hours_passed
                lambda_rate = base_rate * hourly_mult * sim_hours_passed
                num_arrivals = np.random.poisson(lambda_rate)

                for _ in range(num_arrivals):
                    p_data = self.generate_single_patient(department_id=dept_id)
                    patient = Patient(
                        patient_id=p_data["patient_id"],
                        arrival_time=p_data["arrival_time"],
                        department_needed=p_data["department_needed"],
                        severity=p_data["severity"],
                        predicted_stay_hours=p_data["predicted_stay_hours"],
                        status="waiting"
                    )
                    session.add(patient)

                    dept = session.query(Department).filter_by(department_id=dept_id).first()
                    dept_name = dept.name if dept else dept_id

                    event = EventLog(
                        event_type="patient_arrival",
                        entity_id=patient.patient_id,
                        description=f"Patient {patient.patient_id} arrived at {dept_name} [Severity: {patient.severity.upper()}, Est. Stay: {patient.predicted_stay_hours}h]",
                        triggered_by="simulation",
                        timestamp=datetime.now()
                    )
                    session.add(event)
                    generated_batch.append(p_data)

            if generated_batch:
                session.commit()
            return generated_batch
        except Exception as e:
            session.rollback()
            logger.error(f"Error in simulation step: {e}")
            return []
        finally:
            session.close()

    async def start(self, interval_seconds: float = 3.0):
        """Runs the continuous async simulation loop."""
        self.is_running = True
        logger.info(f"Starting patient simulation loop (speed_factor={self.speed_factor}x)...")
        while self.is_running:
            await self.run_simulation_step(time_step_seconds=interval_seconds)
            await asyncio.sleep(interval_seconds)

    def stop(self):
        self.is_running = False
        logger.info("Simulation loop stopped.")

# Global simulator instance
simulator = SyntheticPatientSimulator(speed_factor=2.0)
