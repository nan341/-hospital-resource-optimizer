import os
import logging
import pandas as pd
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/raw"))

DATASET_INFO = {
    "triage_data.csv": {
        "description": "Hospital triage & acuity level dataset",
        "expected_cols": ["acuity", "triage_level", "severity"],
        "source": "Kaggle Emergency Department Triage Dataset"
    },
    "er_dataset.csv": {
        "description": "Emergency Department hourly arrivals and wait times",
        "expected_cols": ["arrival_time", "hour", "department"],
        "source": "Kaggle Hospital ER Operations Dataset"
    },
    "length_of_stay.csv": {
        "description": "Inpatient Length of Stay (LOS) dataset",
        "expected_cols": ["los", "length_of_stay", "severity_score"],
        "source": "Kaggle Hospital Inpatient Stay Dataset"
    },
    "noshow_appointments.csv": {
        "description": "Medical Appointment No-Shows dataset",
        "expected_cols": ["AppointmentDay", "No-show"],
        "source": "Kaggle Medical Appointment No Shows"
    }
}

def load_dataset(filename: str) -> Optional[pd.DataFrame]:
    """Loads a specific dataset from data/raw/.
    If the file is not found, logs an informative notice explaining where to place the file."""
    filepath = os.path.join(RAW_DATA_DIR, filename)
    if not os.path.exists(filepath):
        info = DATASET_INFO.get(filename, {})
        source = info.get("source", "Kaggle Datasets")
        desc = info.get("description", filename)
        logger.warning(
            f"Dataset '{filename}' ({desc}) not found at '{filepath}'. "
            f"Please download from {source} and place into '{RAW_DATA_DIR}/' to use empirical calibration."
        )
        return None

    try:
        df = pd.read_csv(filepath)
        logger.info(f"Loaded '{filename}' with shape {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading '{filename}': {e}")
        return None

def load_all_raw_datasets() -> Dict[str, Optional[pd.DataFrame]]:
    """Loads all available raw Kaggle datasets."""
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    results = {}
    for filename in DATASET_INFO.keys():
        results[filename] = load_dataset(filename)
    return results
