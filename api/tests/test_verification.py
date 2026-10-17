"""Two-step verification, nearby reports and case severity."""

import pytest
from fastapi.testclient import TestClient

from app import area, assessments, config, ee_analysis, main, scoring, storage, warehouse, weather_check
from tests.conftest import FAKE_WEATHER
from tests.test_api import BODY, FAKE_ANALYSIS

# --- Step 2: weather rules --------------------------------------------------------------


def weather(**overrides):
    return {**FAKE_WEATHER, **overrides}


@pytest.mark.parametrize(
    "event, facts, verdict",
    [
        ("flood", weather(), "supported"),                                          # very heavy rain
        ("flood", weather(rain_week_region_mm=8, max_daily_rain_local_mm=3), "not_supported"),
        ("flood", weather(rain_week_region_mm=60, max_daily_rain_local_mm=20), "uncertain"),  # maybe upstream
        ("drought", weather(rain_month_local_mm=90, normal_month_local_mm=268.5), "supported"),
        ("drought", weather(rain_month_local_mm=300, normal_month_local_mm=268.5), "not_supported"),
        ("other", weather(max_daily_rain_local_mm=12, max_temp_c=41), "supported"),  # heatwave
        ("other", weather(max_daily_rain_local_mm=12, max_temp_c=30), "uncertain"),  # e.g. pests
        ("flood", weather(days_with_data=0), "uncertain"),                         # no data yet
    ],
)
def test_weather_rule(event, facts, verdict):
    assert weather_check.rule_verdict(event, facts)[0] == verdict


def test_weather_check_uses_gemini_when_available(monkeypatch):
    monkeypatch.setattr(
        weather_check,
        "_ask_gemini",
        lambda *a: weather_check.WeatherVerdict(verdict="uncertain", explanation_en="Upstream rain possible.", explanation_kn="ಮೇಲ್ಭಾಗದ ಮಳೆ ಸಾಧ್ಯ."),
    )
    result = weather_check.check("flood", "2019-08-07", weather(rain_week_region_mm=60, max_daily_rain_local_mm=20))
    assert result["verdict"] == "uncertain" and result["rule_verdict"] == "uncertain"
    assert result["explanation_kn"] == "ಮೇಲ್ಭಾಗದ ಮಳೆ ಸಾಧ್ಯ."


def test_weather_check_falls_back_to_the_rule_without_gemini():
    result = weather_check.check("flood", "2019-08-07", weather())  # conftest: Gemini unavailable
    assert result["verdict"] == "supported" and result["model"] is None
    assert "286.4 mm" in result["explanation_en"]


# --- Step 1 + status ---------------------------------------------------------------------------


def test_satellite_step():
    high = {"level": "high"}
    assert scoring.satellite_step({"damage_level": "severe"}, high)["passed"] is True
    assert scoring.satellite_step({"damage_level": "none"}, high)["passed"] is False
    assert scoring.satellite_step({"damage_level": "severe"}, {"level": "low"})["passed"] is None


@pytest.mark.parametrize(
    "satellite, weather_verdict, status",
    [
        (True, "supported", "verified"),
        (True, "uncertain", "needs_review"),
        (True, "not_supported", "needs_review"),
        (False, "supported", "needs_review"),
        (False, "not_supported", "not_supported"),
        (None, "supported", "needs_review"),
    ],
)
def test_verification_status(satellite, weather_verdict, status):
    assert scoring.verification_status(satellite, weather_verdict) == status


# --- Nearby reports and case severity ------------------------------------------------------------


def report(farmer, lat=16.73, lng=75.06, day="2019-08-07", event="flood", damage=70):
    return {"assessment_id": f"asm_{farmer}", "farmer_id": farmer, "lat": lat, "lng": lng,
            "event_type": event, "event_date": day, "damage_score": damage, "created_at": day}


def test_nearby_counts_other_farmers_close_in_space_and_time():
    reports = [
        report("A"), report("A", day="2019-08-08", damage=90),  # same farmer twice: counts once
        report("B", lat=16.74),                               # ~1.1 km: counts
        report("C", lat=16.76),                               # ~3.3 km: too far
        report("D", day="2019-08-20"),                        # 13 days later: too late
        report("E", event="drought"),                         # different event
        report("ME"),                                         # the farmer themself
    ]
    near = area.nearby(16.73, 75.06, "ME", "flood", "2019-08-07", reports)
    assert near["nearby_farmers"] == 2 and near["nearby_reports"] == 3
    assert near["nearby_avg_damage"] == 80   # A's latest (90) and B (70)
    assert near["level"] == "some"


def test_area_levels():
    assert [scoring.area_level(n) for n in (0, 1, 2, 3, 9)] == ["isolated", "some", "some", "widespread", "widespread"]


def test_severity_combines_damage_and_nearby_reports():
    many = {"nearby_farmers": 6, "radius_km": 2}
    assert scoring.severity(74, many, "verified") == {
        "score": 82, "level": "severe",
        "reasons": ["Plot damage score 74/100", "6 other farmers within 2 km reported the same event"],
    }
    assert scoring.severity(40, {"nearby_farmers": 5}, "verified")["level"] == "moderate"  # 28 + 30


def test_a_single_report_is_never_severe():
    alone = scoring.severity(95, {"nearby_farmers": 0}, "verified")
    assert alone["level"] == "moderate"
    assert "A single report can't be rated severe until nearby reports confirm it" in alone["reasons"]


def test_unsupported_claim_is_capped_low():
    assert scoring.severity(90, {"nearby_farmers": 6}, "not_supported")["level"] == "low"


def test_severity_without_damage_measurement():
    assert scoring.severity(None, {"nearby_farmers": 3}, "needs_review")["level"] == "unknown"


# --- End to end through /api/assess --------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GCS_BUCKET", "")
    monkeypatch.setattr(config, "DEMO_MODE", False)
    monkeypatch.setattr(storage, "LOCAL_STORE", tmp_path / "store")
    monkeypatch.setattr(assessments, "DEMO_CACHE", tmp_path / "demo_cache")
    monkeypatch.setattr(warehouse, "record_assessment", lambda result: None)
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: FAKE_ANALYSIS)
    monkeypatch.setattr(ee_analysis, "thumbnails", lambda *a: {})
    return TestClient(main.app)


def test_assessment_is_verified_and_severity_counts_seed_neighbours(client):
    result = client.post("/api/assess", json=BODY).json()
    assert result["verification"]["status"] == "verified"
    assert result["verification"]["satellite"]["passed"] is True
    assert result["verification"]["weather"]["verdict"] == "supported"
    # The six sample neighbours in app/seed_reports.json reported the same flood.
    assert result["area"]["nearby_farmers"] == 6 and result["area"]["level"] == "widespread"
    assert result["severity"]["level"] == "severe"


def test_each_live_report_adds_to_the_area(client):
    first = client.post("/api/assess", json=BODY).json()
    # A different farmer's plot nearby now sees the first farmer's report too.
    near = area.nearby(16.7333, 75.0594, "KA-SOMEONE-ELSE", "flood", "2019-08-07")
    assert near["nearby_farmers"] == 7
    assert first["assessment_id"] in {r["assessment_id"] for r in area.all_reports()}


def test_dry_weather_makes_a_flood_claim_need_review(client, monkeypatch):
    monkeypatch.setattr(ee_analysis, "weather_facts", lambda *a: weather(rain_week_region_mm=5, max_daily_rain_local_mm=2))
    result = client.post("/api/assess", json=BODY).json()
    assert result["verification"]["weather"]["verdict"] == "not_supported"
    assert result["verification"]["status"] == "needs_review"


def test_missing_weather_data_leaves_the_check_pending(client, monkeypatch):
    def boom(*a):
        raise RuntimeError("ERA5 unavailable")

    monkeypatch.setattr(ee_analysis, "weather_facts", boom)
    result = client.post("/api/assess", json=BODY).json()
    assert result["verification"]["weather"]["verdict"] == "uncertain"
    assert result["verification"]["status"] == "needs_review"
