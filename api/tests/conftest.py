"""Shared test setup: no test may reach Earth Engine, Gemini or BigQuery."""

import pytest

from app import ee_analysis, weather_check

# Heavy rain in the region the week before: the flood rule says "supported".
FAKE_WEATHER = {
    "rain_event_local_mm": 142.6,
    "max_daily_rain_local_mm": 71.3,
    "rain_week_region_mm": 286.4,
    "normal_week_region_mm": 74.8,
    "rain_month_local_mm": 512.0,
    "normal_month_local_mm": 268.5,
    "max_temp_c": 29.4,
    "days_with_data": 10,
    "region_km": 50,
    "windows": {},
    "source": "ERA5-Land daily weather (ECMWF / Copernicus)",
}


@pytest.fixture(autouse=True)
def no_cloud_calls(monkeypatch):
    monkeypatch.setattr(ee_analysis, "weather_facts", lambda *a: dict(FAKE_WEATHER))

    def no_gemini(*a, **k):
        raise RuntimeError("no Gemini in tests")

    # Without Gemini the weather check falls back to its rule verdict.
    monkeypatch.setattr(weather_check, "_ask_gemini", no_gemini)
