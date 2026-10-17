"""Date windows and result shaping (pure Python, no Earth Engine)."""

from datetime import date, datetime, timezone

import pytest

from app import ee_analysis

TODAY = date(2026, 10, 17)


def ms(iso, hour=5):
    return int(datetime.fromisoformat(iso).replace(hour=hour, tzinfo=timezone.utc).timestamp() * 1000)


def test_windows_one_week_before_and_latest():
    w = ee_analysis.build_windows(date(2019, 8, 7), today=TODAY)
    assert w["before_target"] == "2019-07-31"           # exactly 1 week before
    assert w["before"] == {"start": "2019-07-26", "end": "2019-08-04"}
    assert w["now"] == {"start": "2019-08-07", "end": "2019-08-21"}
    assert w["series"] == {"start": "2019-07-08", "end": "2019-08-21"}


def test_now_window_ends_today_for_recent_events():
    w = ee_analysis.build_windows(date(2026, 10, 15), today=TODAY)
    assert w["now"] == {"start": "2026-10-15", "end": "2026-10-17"}


def test_weather_windows():
    w = ee_analysis.weather_windows(date(2019, 8, 7))
    assert w["event_local"] == {"start": "2019-08-04", "end": "2019-08-08"}
    assert w["week_region"] == {"start": "2019-07-31", "end": "2019-08-07"}
    assert w["month_local"] == {"start": "2019-07-08", "end": "2019-08-07"}


def test_shift_years_handles_leap_day():
    assert ee_analysis.shift_years(date(2020, 2, 29), -1) == date(2019, 2, 28)


def test_shape_result():
    raw = {
        "ndvi_before": 0.72, "ndvi_now": 0.25, "water_before": 0.02, "water_now": 0.86, "flood_fraction": 0.83,
        "before_t": ms("2019-07-31"), "now_t": ms("2019-08-15"), "before_clear": 0.941, "now_clear": 0.88,
        "area_m2": 10200, "area_pixels": 102, "centroid": [75.06, 16.73],
        "series": {"t": [ms("2019-07-31", 5), ms("2019-07-31", 6)], "ndvi": [0.7, 0.74]},
    }
    windows = ee_analysis.build_windows(date(2019, 8, 7), today=TODAY)
    out = ee_analysis.shape_result(raw, "flood", date(2019, 8, 7), windows)
    m = out["metrics"]
    assert m["ndvi_loss"] == pytest.approx(0.653, abs=0.001)
    assert (m["before_image_date"], m["now_image_date"], m["days_between"]) == ("2019-07-31", "2019-08-15", 15)
    assert out["acquisitions"] == {"before": "2019-07-31", "now": "2019-08-15", "satellite": "Sentinel-2"}
    assert out["ndvi_series"]["this_year"] == [{"day_offset": -7, "date": "2019-07-31", "ndvi": 0.72}]
    assert out["plot_stats"]["area_ha"] == 1.02


def test_shape_result_without_images():
    raw = {"area_m2": 10000, "area_pixels": 100, "centroid": [75.06, 16.73], "series": {"t": [], "ndvi": []}}
    out = ee_analysis.shape_result(raw, "flood", date(2019, 8, 7), {})
    assert out["metrics"]["before_image_date"] is None and out["metrics"]["days_between"] is None
    assert out["metrics"]["ndvi_loss"] is None


def test_shape_weather_converts_units_and_averages_normals():
    raw = {
        "rain_event_local": 0.1426, "max_daily_local": 0.0713, "rain_week_region": 0.2864,
        "rain_month_local": 0.512, "tmax_week_local": 302.55,
        "normal_week_region": [0.07, 0.08, None], "normal_month_local": [0.25, 0.287],
        "days_with_data": 10,
    }
    facts = ee_analysis.shape_weather(raw, {})
    assert facts["rain_week_region_mm"] == 286.4
    assert facts["normal_week_region_mm"] == 75.0     # missing years are skipped
    assert facts["max_temp_c"] == 29.4
