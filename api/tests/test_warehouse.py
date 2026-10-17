"""BigQuery rows, dashboard summary and endpoints (BigQuery stubbed)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import assessments, config, ee_analysis, main, storage, warehouse
from scripts import batch_village
from tests.test_api import BODY, FAKE_ANALYSIS
from tests.test_validation import square

OFFICER = {"X-Officer-Code": "test-code"}
SAMPLE = json.loads((Path(__file__).parents[2] / "shared" / "sample_result.json").read_text())


def test_polygon_wkt():
    wkt = warehouse.polygon_wkt({"type": "Polygon", "coordinates": [[[75, 16], [75.1, 16], [75.1, 16.1], [75, 16]]]})
    assert wkt == "POLYGON((75 16, 75.1 16, 75.1 16.1, 75 16))"


def test_rows_match_the_table_schemas():
    plot_row, assessment_row = warehouse.rows_for(SAMPLE)
    assert set(plot_row) == {f.name for f in warehouse.PLOTS_SCHEMA}
    assert set(assessment_row) == {f.name for f in warehouse.ASSESSMENTS_SCHEMA}
    assert plot_row["geom"].startswith("POLYGON((75.0595 16.7295")
    assert assessment_row["damage_level"] == "severe"
    assert assessment_row["confidence"] == "high"
    assert assessment_row["plot_id"] == plot_row["plot_id"]


def plot(aid, score, level, confidence="high", area=1.0):
    return {"assessment_id": aid, "damage_score": score, "damage_level": level, "confidence": confidence, "area_ha": area}


def test_summary_and_visit_first_order():
    plots = [
        plot("a", 40, "moderate", area=1.5),
        plot("b", 80, "severe", "low"),
        plot("c", 80, "severe", "high"),
        plot("d", 10, "none"),
        plot("e", None, "unknown"),
    ]
    result = warehouse.summarise(plots)
    assert result["summary"] == {
        "plots": 5, "severe": 2, "moderate": 1, "low_or_none": 1, "unknown": 1, "hectares_affected": 3.5,
    }
    # Highest score first; for equal scores, higher confidence first; no-score plots left out.
    assert result["visit_first"] == ["c", "b", "a", "d"]


def make_client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GCS_BUCKET", "")
    monkeypatch.setattr(config, "DEMO_MODE", False)
    monkeypatch.setattr(config, "OFFICER_ACCESS_CODE", "test-code")
    monkeypatch.setattr(storage, "LOCAL_STORE", tmp_path / "store")
    monkeypatch.setattr(assessments, "DEMO_CACHE", tmp_path / "demo_cache")
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: FAKE_ANALYSIS)
    monkeypatch.setattr(ee_analysis, "thumbnails", lambda *a: {})
    return TestClient(main.app)


def test_live_assessments_are_recorded(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    recorded = []
    monkeypatch.setattr(warehouse, "record_assessment", recorded.append)
    result = client.post("/api/assess", json=BODY).json()
    assert [r["assessment_id"] for r in recorded] == [result["assessment_id"]]


def test_bigquery_failure_does_not_break_the_assessment(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    def boom(result):
        raise RuntimeError("table not found")

    monkeypatch.setattr(warehouse, "record_assessment", boom)
    response = client.post("/api/assess", json=BODY)
    assert response.status_code == 200
    assert response.json()["source"] == "live"


def test_dashboard_endpoint(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    row = {
        "assessment_id": "asm_1", "plot_id": "plt_1", "damage_score": 72.0, "damage_level": "severe",
        "confidence": "high", "area_ha": 1.2, "source": "live",
        "geojson": json.dumps(square()),
    }
    monkeypatch.setattr(warehouse, "dashboard", lambda: [dict(row)])
    body = client.get("/api/dashboard", headers=OFFICER).json()
    assert body["source"] == "bigquery"
    assert body["plots"][0]["geometry"]["type"] == "Polygon"
    assert "geojson" not in body["plots"][0]
    assert body["summary"]["severe"] == 1
    assert body["visit_first"] == ["asm_1"]


def test_dashboard_falls_back_to_cache_in_demo_mode(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)

    def boom():
        raise RuntimeError("no credentials")

    monkeypatch.setattr(warehouse, "dashboard", boom)
    assert client.get("/api/dashboard", headers=OFFICER).status_code == 502

    monkeypatch.setattr(config, "DEMO_MODE", True)
    (tmp_path / "demo_cache").mkdir()
    (tmp_path / "demo_cache" / "dashboard.json").write_text(json.dumps({"plots": [], "summary": {}, "visit_first": []}))
    body = client.get("/api/dashboard", headers=OFFICER).json()
    assert body["source"] == "cache"


def test_village_grid_and_batch_results():
    plots = batch_village.grid_plots(75.06, 16.73)
    n = 2 * int(batch_village.GRID_HALF_KM * 1000 / batch_village.GRID_STEP_M) + 1
    assert len(plots) == n * n

    measured = [
        {"properties": {"i": 0, "ndvi_before": 0.7, "ndvi_after": 0.2, "ndvi_baseline_after": 0.7,
                        "flood_fraction": 0.9, "crop_fraction": 0.9, "clear_obs_before": 3.2, "clear_obs_after": 2.6}},
        {"properties": {"i": 1, "crop_fraction": 0.2}},  # not cropland: dropped
    ]
    results = batch_village.build_results(plots, measured, {"pre": 2, "post": 1}, "flood", "2019-08-07", {}, 120)
    assert len(results) == 1
    r = results[0]
    assert r["source"] == "batch"
    assert r["metrics"]["clear_obs_after"] == 3
    assert r["score"]["damage_level"] == "severe"
    assert 0.9 < r["plot"]["area_ha"] < 1.1
    assert r["evidence_hash"].startswith("sha256:")
    warehouse.rows_for(r)  # must be loadable into BigQuery


def test_dashboard_needs_the_officer_code(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    monkeypatch.setattr(warehouse, "dashboard", lambda: [])
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/dashboard", headers={"X-Officer-Code": "wrong"}).status_code == 401
    assert client.get("/api/dashboard", headers=OFFICER).status_code == 200
    monkeypatch.setattr(config, "OFFICER_ACCESS_CODE", "")
    response = client.get("/api/dashboard", headers=OFFICER)
    assert response.status_code == 503 and "isn't set up" in response.json()["error"]
