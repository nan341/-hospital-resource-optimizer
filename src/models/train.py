import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.api.db import SessionLocal
from src.db.models import Patient
from src.data_pipeline.calibration import calibrate_from_data, get_calibration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retrain_forecaster_from_db():
    """
    Analyzes historical patient arrivals in the database to recalibrate
    department baseline arrival rates and diurnal hourly profiles.
    """
    session = SessionLocal()
    try:
        patients = session.query(Patient).all()
        logger.info(f"Retraining forecaster using {len(patients)} patient records from DB...")

        if len(patients) < 10:
            logger.info("Insufficient patient records in DB (<10). Using base calibration.")
            return calibrate_from_data()

        # Convert to DataFrame
        data = []
        for p in patients:
            data.append({
                "arrival_time": p.arrival_time,
                "department_id": p.department_needed,
                "severity": p.severity,
                "stay_hours": p.predicted_stay_hours
            })
        df = pd.DataFrame(data)

        calibration = get_calibration()

        # Update hourly multipliers
        df["hour"] = pd.to_datetime(df["arrival_time"]).dt.hour
        hourly_counts = df["hour"].value_counts().reindex(range(24), fill_value=0).values
        if hourly_counts.sum() > 0:
            mean_hr = hourly_counts.mean()
            if mean_hr > 0:
                calibration["hourly_multipliers"] = [round(float(c / mean_hr), 3) for c in hourly_counts]

        # Update severity distribution
        sev_counts = df["severity"].value_counts(normalize=True).to_dict()
        calibration["severity_distribution"] = {
            "critical": round(float(sev_counts.get("critical", 0.15)), 3),
            "moderate": round(float(sev_counts.get("moderate", 0.45)), 3),
            "low": round(float(sev_counts.get("low", 0.40)), 3)
        }

        # Save back
        import json
        processed_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))
        cal_path = os.path.join(processed_dir, "calibration.json")
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(calibration, f, indent=2)

        logger.info("Forecaster parameters recalibrated and saved successfully.")
        return calibration
    except Exception as e:
        logger.error(f"Error retraining forecaster: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    retrain_forecaster_from_db()
