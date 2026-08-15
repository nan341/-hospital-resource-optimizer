import pytest
from src.api.db import SessionLocal
from src.models.forecasting import DemandForecaster

def test_demand_forecasting():
    session = SessionLocal()
    forecaster = DemandForecaster()
    try:
        forecast = forecaster.predict_next_hours(session, "er", horizon_hours=2)
        assert forecast is not None
        assert "predicted_count" in forecast
        assert forecast["predicted_count"] >= 0
        assert forecast["department_id"] == "er"
        assert len(forecast["hourly_breakdown"]) == 2
        assert forecast["ci_lower"] <= forecast["predicted_count"] <= forecast["ci_upper"]

        all_forecasts = forecaster.predict_all_departments(session, horizon_hours=2)
        assert "er" in all_forecasts
        assert "general_ward" in all_forecasts
        assert "icu" in all_forecasts
        assert "pediatrics" in all_forecasts
    finally:
        session.close()
