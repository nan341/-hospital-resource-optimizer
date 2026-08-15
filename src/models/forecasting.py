import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.data_pipeline.calibration import get_calibration
from src.db.models import Patient, Department

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DemandForecaster:
    def __init__(self, use_prophet_if_available: bool = False):
        self.use_prophet = use_prophet_if_available
        self.calibration = get_calibration()
        self.fitted_weights: Dict[str, float] = {}

    def predict_next_hours(
        self,
        db_session: Session,
        department_id: str,
        horizon_hours: int = 2,
        history_window_hours: int = 6
    ) -> Dict[str, Any]:
        """
        Predicts expected patient arrivals for the next `horizon_hours` for a department.
        Combines recent empirical arrival rate with diurnal hourly multipliers from calibration.
        """
        self.calibration = get_calibration()
        now = datetime.now()
        start_history = now - timedelta(hours=history_window_hours)

        # 1. Fetch recent arrivals from database
        recent_patients = (
            db_session.query(Patient)
            .filter(
                Patient.department_needed == department_id,
                Patient.arrival_time >= start_history
            )
            .all()
        )

        dept = db_session.query(Department).filter_by(department_id=department_id).first()
        dept_name = dept.name if dept else department_id

        # 2. Extract base rates and diurnal curves
        dept_base_rates = self.calibration.get("department_base_rates", {
            "er": 4.5, "general_ward": 2.2, "icu": 0.8, "pediatrics": 1.8
        })
        base_rate = dept_base_rates.get(department_id, 2.0)
        multipliers = self.calibration.get("hourly_multipliers", [1.0] * 24)

        # 3. Calculate weighted recent observed rate
        if recent_patients:
            # Group into 1-hour bins
            hours_elapsed = max(0.5, (now - start_history).total_seconds() / 3600.0)
            observed_hourly_rate = len(recent_patients) / hours_elapsed
            # Exponentially weight observed vs base: 0.6 observed + 0.4 baseline
            adjusted_base_rate = (0.65 * observed_hourly_rate) + (0.35 * base_rate)
        else:
            adjusted_base_rate = base_rate

        # 4. Integrate diurnal multiplier for the next forecast horizon hours
        hourly_forecasts = []
        total_predicted = 0.0

        for h in range(1, horizon_hours + 1):
            future_dt = now + timedelta(hours=h)
            target_hour = future_dt.hour
            multiplier = multipliers[target_hour]
            expected_count = max(0.1, adjusted_base_rate * multiplier)
            total_predicted += expected_count

            hourly_forecasts.append({
                "hour_offset": h,
                "timestamp": future_dt.strftime("%Y-%m-%d %H:00"),
                "predicted_arrivals": round(expected_count, 2),
                "multiplier": multiplier
            })

        # Confidence interval: 80% CI using Poisson variance
        variance = total_predicted
        std_err = np.sqrt(variance) if variance > 0 else 0.5
        ci_lower = max(0.0, total_predicted - (1.28 * std_err))
        ci_upper = total_predicted + (1.28 * std_err)

        return {
            "department_id": department_id,
            "department_name": dept_name,
            "horizon_hours": horizon_hours,
            "predicted_count": round(total_predicted, 1),
            "ci_lower": round(ci_lower, 1),
            "ci_upper": round(ci_upper, 1),
            "hourly_breakdown": hourly_forecasts,
            "recent_observed_rate": round(adjusted_base_rate, 2),
            "model_type": "weighted_seasonality_rolling_avg"
        }

    def predict_all_departments(
        self,
        db_session: Session,
        horizon_hours: int = 2
    ) -> Dict[str, Dict[str, Any]]:
        """Generates demand forecasts for all active hospital departments."""
        departments = db_session.query(Department).all()
        forecasts = {}
        for dept in departments:
            forecasts[dept.department_id] = self.predict_next_hours(
                db_session=db_session,
                department_id=dept.department_id,
                horizon_hours=horizon_hours
            )
        return forecasts

# Global forecaster instance
forecaster = DemandForecaster()
