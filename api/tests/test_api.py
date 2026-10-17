"""Assessment endpoints with Earth Engine stubbed out and local file storage."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from app import assessments, config, ee_analysis, main, storage, warehouse
from tests.test_validation import square

FAKE_ANALYSIS = {
    "event": {"type": "flood", "date": "2019-08-07", "windows": {}},
    "plot_stats": {"area_ha": 1.18, "area_pixels": 118, "centroid": {"lat": 16.73, "lng": 75.06}},
    "metrics": {
        "ndvi_before": 0.7, "ndvi_after": 0.25, "ndvi_baseline_after": 0.68, "ndvi_loss": 0.632,
        "flood_fraction": 0.8, "rain_deficit": None, "season_rain_mm": None, "baseline_rain_mm": None,
        "crop_fraction": 0.8, "clear_obs_before": 3, "clear_obs_after": 4, "radar_obs_pre": 2, "radar_obs_post": 1,
    },
    "acquisitions": {"s2_before": [], "s2_after": [], "s1_pre": [], "s1_post": []},
    "ndvi_series": {"this_year": [], "baseline": []},
}

# plt_seed_1 is a sample registered plot (app/seed_plots.json) with the same outline as square().
BODY = {
    "plot_id": "plt_seed_1",
    "event_type": "flood",
    "event_date": "2019-08-07",
    "crop": "sugarcane",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GCS_BUCKET", "")
    monkeypatch.setattr(config, "DEMO_MODE", False)
    monkeypatch.setattr(storage, "LOCAL_STORE", tmp_path / "store")
    monkeypatch.setattr(assessments, "DEMO_CACHE", tmp_path / "demo_cache")
    monkeypatch.setattr(warehouse, "record_assessment", lambda result: None)
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: FAKE_ANALYSIS)
    monkeypatch.setattr(ee_analysis, "thumbnails", lambda *a: {"true_colour_before": b"\x89PNG fake"})
    return TestClient(main.app)


def test_assess_returns_contract_shape_and_stores_everything(client):
    response = client.post("/api/assess", json=BODY)
    assert response.status_code == 200, response.text
    result = response.json()

    sample = json.loads((assessments.Path(__file__).parents[2] / "shared" / "sample_result.json").read_text())
    expected_keys = {k for k in sample if not k.startswith("_")}
    assert expected_keys <= set(result)
    assert set(sample["metrics"]) == set(result["metrics"])

    assert result["source"] == "live"
    assert result["plot"]["farmer_name"] == "Ramesh"
    assert result["score"] == {"damage_score": 72, "damage_level": "severe"}
    assert result["confidence"]["level"] == "high"
    assert result["evidence_hash"].startswith("sha256:")
    assert result["images"] == {
        "true_colour_before": f"/api/assets/{result['assessment_id']}/true_colour_before.png"
    }

    image = client.get(result["images"]["true_colour_before"])
    assert image.status_code == 200 and image.headers["content-type"] == "image/png"

    stored = client.get(f"/api/assessments/{result['assessment_id']}").json()
    assert stored["evidence_hash"] == result["evidence_hash"]


def test_invalid_input_gives_a_readable_422(client):
    response = client.post("/api/assess", json={**BODY, "event_date": "2099-01-01"})
    assert response.status_code == 422
    assert "at least 7 days ago" in response.json()["error"]


def test_analysis_failure_without_demo_mode_is_502(client, monkeypatch):
    def boom(*a):
        raise RuntimeError("EE quota exceeded")

    monkeypatch.setattr(ee_analysis, "assess", boom)
    response = client.post("/api/assess", json=BODY)
    assert response.status_code == 502
    assert "couldn't get satellite images" in response.json()["error"]


def test_thumbnail_failure_still_returns_the_assessment(client, monkeypatch):
    def boom(*a):
        raise RuntimeError("thumb failed")

    monkeypatch.setattr(ee_analysis, "thumbnails", boom)
    response = client.post("/api/assess", json=BODY)
    assert response.status_code == 200
    assert response.json()["images"] == {}


def _write_demo_cache(tmp_path):
    cache = tmp_path / "demo_cache"
    (cache / "results").mkdir(parents=True)
    (cache / "demo_plots.json").write_text(json.dumps({"plots": [
        {"id": "flood1", "label": "Demo", "event_type": "flood", "event_date": "2019-08-07",
         "crop": "sugarcane", "control": False, "geometry": square()},
    ]}))
    cached = {"assessment_id": "asm_cached1", "source": "live", "plot": {"farmer_name": "", "village": "", "crop": ""}}
    (cache / "results" / "flood1.json").write_text(json.dumps(cached))


def test_demo_mode_serves_cache_when_live_analysis_fails(client, monkeypatch, tmp_path):
    _write_demo_cache(tmp_path)
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))

    result = client.post("/api/assess", json=BODY).json()
    assert result["assessment_id"] == "asm_cached1"
    assert result["source"] == "cache"
    assert result["plot"]["farmer_name"] == "Ramesh"


def test_demo_mode_serves_cache_on_timeout(client, monkeypatch, tmp_path):
    _write_demo_cache(tmp_path)
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(assessments, "LIVE_TIMEOUT_DEMO_S", 0.2)
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: time.sleep(1) or FAKE_ANALYSIS)

    result = client.post("/api/assess", json=BODY).json()
    assert result["source"] == "cache"


def test_outline_sent_by_the_browser_is_ignored(client):
    # A farmer can't enlarge their plot: only the registered outline is used.
    huge = square(half_deg=0.01)
    result = client.post("/api/assess", json={**BODY, "geometry": huge, "farmer_name": "Someone else"}).json()
    assert result["plot"]["geometry"] == square()
    assert result["plot"]["plot_id"] == "plt_seed_1"
    assert result["plot"]["farmer_id"] == "KA-DEMO-001"
    assert result["plot"]["farmer_name"] == "Ramesh"
    assert result["plot"]["survey_number"] == "112/3"


def test_unregistered_plot_is_rejected(client):
    response = client.post("/api/assess", json={**BODY, "plot_id": "plt_made_up"})
    assert response.status_code == 404
    assert "isn't registered" in response.json()["error"]


def test_demo_plots_are_registered_to_demo_farmers(client, tmp_path):
    _write_demo_cache(tmp_path)
    plots = client.get("/api/farmers/ka-demo-001/plots").json()["plots"]
    assert {p["plot_id"] for p in plots} == {"plt_seed_1", "plt_seed_2", "plt_flood1"}
    flood1 = next(p for p in plots if p["plot_id"] == "plt_flood1")
    assert flood1["default_event"] == {"event_type": "flood", "event_date": "2019-08-07"}


def test_asset_paths_are_restricted(client):
    assert client.get("/api/assets/../../etc/passwd").status_code == 404
    assert client.get("/api/assets/asm_x/../secret.png").status_code == 404
    assert client.get("/api/assessments/not-an-id").status_code == 404


def test_demo_mode_sample_fallback_for_seed_plots(client, monkeypatch):
    # No precomputed results exist: the seed plots fall back to the labelled sample.
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: (_ for _ in ()).throw(RuntimeError("no credentials")))
    result = client.post("/api/assess", json={**BODY, "plot_id": "plt_seed_2"}).json()
    assert result["source"] == "sample"
    assert result["plot"]["plot_id"] == "plt_seed_2" and result["plot"]["survey_number"] == "118/1"
    assert result["plot"]["geometry"]["coordinates"][0][0] == [75.0625, 16.7315]
    assert result["report"]["summary_en"]  # report bundled, no Gemini call needed
    # Stored, so the report page and photo check can load it.
    stored = client.get(f"/api/assessments/{result['assessment_id']}").json()
    assert stored["plot"]["plot_id"] == "plt_seed_2"
    assert client.post(f"/api/report/{result['assessment_id']}").json()["report"]["summary_en"]


def test_no_sample_fallback_outside_demo_mode_or_for_real_plots(client, monkeypatch):
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: (_ for _ in ()).throw(RuntimeError("down")))
    assert client.post("/api/assess", json=BODY).status_code == 502  # DEMO_MODE off
