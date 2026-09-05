Pimport os
import sys
import time
import asyncio
import argparse
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api.db import SessionLocal
from src.db.init_db import init_database
from src.data_pipeline.synthetic_generator import SyntheticPatientSimulator
from src.allocation.engine import HospitalAllocationEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def run_standalone_simulation(
    duration_seconds: int = 60,
    speed_factor: float = 2.0,
    surge_department: str = None,
    surge_count: int = 6,
    surge_after_seconds: int = 15
):
    sim = SyntheticPatientSimulator(speed_factor=speed_factor)
    engine = HospitalAllocationEngine()

    logger.info(f"Starting standalone simulation for {duration_seconds}s at {speed_factor}x speed...")
    start_time = time.time()
    surge_triggered = False

    while (time.time() - start_time) < duration_seconds:
        elapsed = time.time() - start_time

        # Check if surge should trigger
        if surge_department and not surge_triggered and elapsed >= surge_after_seconds:
            logger.info(f"TRIGGERING SCRIPTED SURGE: {surge_count} critical patients into {surge_department}")
            sim.execute_surge_now(surge_department, surge_count)
            surge_triggered = True

        # Run simulation step
        arrivals = await sim.run_simulation_step(time_step_seconds=3.0)
        if arrivals:
            logger.info(f"Simulated {len(arrivals)} new arrivals: {[p['patient_id'] for p in arrivals]}")

        # Run allocation pass
        session = SessionLocal()
        try:
            alloc_summary = engine.run_allocation_cycle(session)
            logger.info(f"Allocation Cycle: Primary={alloc_summary['admitted_primary']}, Overflow={alloc_summary['admitted_overflow']}, StaffReassigned={alloc_summary['staff_reassigned']}")
        finally:
            session.close()

        await asyncio.sleep(3.0)

    logger.info("Simulation completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Hospital Resource Optimizer synthetic simulation against live DB.")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (default: 60)")
    parser.add_argument("--speed", type=float, default=2.5, help="Simulation speed factor (default: 2.5)")
    parser.add_argument("--surge-dept", type=str, default="er", help="Department for scripted surge (default: er)")
    parser.add_argument("--surge-count", type=int, default=8, help="Number of critical patients in surge (default: 8)")
    parser.add_argument("--surge-after", type=int, default=10, help="Seconds before surge triggers (default: 10)")
    parser.add_argument("--reset", action="store_true", help="Reset DB before starting")

    args = parser.parse_args()

    if args.reset:
        init_database(drop_existing=True)

    asyncio.run(run_standalone_simulation(
        duration_seconds=args.duration,
        speed_factor=args.speed,
        surge_department=args.surge_dept,
        surge_count=args.surge_count,
        surge_after_seconds=args.surge_after
    ))
