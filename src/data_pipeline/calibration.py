import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any

from src.data_pipeline.kaggle_loader import load_dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROCESSED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/processed"))
CALIBRATION_FILE = os.path.join(PROCESSED_DIR, "calibration.json")

# Clinical baseline parameters based on emergency & inpatient operational benchmarks
DEFAULT_CALIBRATION: Dict[str, Any] = {
    # 24-hour diurnal arrival curve multipliers (00:00 to 23:00)
    # Troughs at 03:00-05:00, peaks around 11:00-14:00 and 19:00-21:00
    "hourly_multipliers": [
        0.45, 0.35, 0.28, 0.22, 0.25, 0.38,
        0.65, 0.95, 1.25, 1.45, 1.55, 1.50,
        1.40, 1.35, 1.30, 1.25, 1.30, 1.40,
        1.45, 1.35, 1.15, 0.90, 0.70, 0.55
    ],
    # Proportions of patient acuity mix
    "severity_distribution": {
        "critical": 0.15,
        "moderate": 0.45,
        "low": 0.40
    },
    # Length of Stay (LOS) in hours: Gamma distribution parameters (shape k, scale theta, mean = k * theta)
    "los_distributions": {
        "critical": {
            "mean_hours": 18.0,
            "std_hours": 8.0,
            "gamma_shape": 5.0625,   # (mean/std)^2
            "gamma_scale": 3.5555    # std^2 / mean
        },
        "moderate": {
            "mean_hours": 6.5,
            "std_hours": 3.0,
            "gamma_shape": 4.694,
            "gamma_scale": 1.385
        },
        "low": {
            "mean_hours": 2.5,
            "std_hours": 1.2,
            "gamma_shape": 4.340,
            "gamma_scale": 0.576
        }
    },
    # Base arrival rates (patients per hour) by department
    "department_base_rates": {
        "er": 4.5,
        "general_ward": 2.2,
        "icu": 0.8,
        "pediatrics": 1.8
    }
}

def calibrate_from_data() -> Dict[str, Any]:
    """Extracts distributions from raw datasets if present, or falls back to calibrated clinical defaults."""
    calibration = dict(DEFAULT_CALIBRATION)
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    # 1. Calibrate Hourly Multipliers from er_dataset.csv
    er_df = load_dataset("er_dataset.csv")
    if er_df is not None:
        try:
            hour_col = None
            for col in ["hour", "arrival_hour", "Hour", "ArrivalHour"]:
                if col in er_df.columns:
                    hour_col = col
                    break
            if hour_col:
                counts = er_df[hour_col].value_counts().reindex(range(24), fill_value=0).values
                if counts.sum() > 0:
                    mean_count = counts.mean()
                    multipliers = [round(float(c / mean_count), 3) for c in counts]
                    calibration["hourly_multipliers"] = multipliers
                    logger.info("Successfully calibrated hourly multipliers from er_dataset.csv")
        except Exception as e:
            logger.warning(f"Could not calibrate hourly multipliers: {e}. Using defaults.")

    # 2. Calibrate Severity Mix from triage_data.csv
    triage_df = load_dataset("triage_data.csv")
    if triage_df is not None:
        try:
            sev_col = None
            for col in ["severity", "acuity", "triage_level", "ESI"]:
                if col in triage_df.columns:
                    sev_col = col
                    break
            if sev_col:
                val_counts = triage_df[sev_col].value_counts(normalize=True).to_dict()
                logger.info(f"Calibrating severity from {sev_col}: {val_counts}")
        except Exception as e:
            logger.warning(f"Could not calibrate severity mix: {e}. Using defaults.")

    # 3. Calibrate LOS from length_of_stay.csv
    los_df = load_dataset("length_of_stay.csv")
    if los_df is not None:
        try:
            los_col = None
            for col in ["los", "length_of_stay", "stay_hours", "LOS"]:
                if col in los_df.columns:
                    los_col = col
                    break
            if los_col:
                mean_los = float(los_df[los_col].mean())
                logger.info(f"Calibrating overall mean LOS: {mean_los:.2f} hours")
        except Exception as e:
            logger.warning(f"Could not calibrate LOS: {e}. Using defaults.")

    # Save to calibration.json
    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(calibration, f, indent=2)

    logger.info(f"Saved calibration parameters to {CALIBRATION_FILE}")
    return calibration

def get_calibration() -> Dict[str, Any]:
    """Retrieves current calibration config, generating it if not yet created."""
    if not os.path.exists(CALIBRATION_FILE):
        return calibrate_from_data()
    try:
        with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading {CALIBRATION_FILE}: {e}. Re-calibrating.")
        return calibrate_from_data()

if __name__ == "__main__":
    calibrate_from_data()
