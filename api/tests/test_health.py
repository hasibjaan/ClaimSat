"""Health endpoint shape, with the cloud checks stubbed out (no network needed)."""

from fastapi.testclient import TestClient

from app import ee_analysis, main, report, storage


def test_health_all_ok(monkeypatch):
    monkeypatch.setattr(ee_analysis, "check", lambda: "ee fine")
    monkeypatch.setattr(report, "check", lambda: "gemini fine")
    monkeypatch.setattr(storage, "check", lambda: "bq fine")

    body = TestClient(main.app).get("/api/health").json()

    assert body["ok"] is True
    assert set(body["services"]) == {"earth_engine", "vertex_ai", "bigquery"}
    assert body["services"]["vertex_ai"]["detail"] == "gemini fine"


def test_health_reports_failure_without_crashing(monkeypatch):
    def boom():
        raise RuntimeError("no credentials")

    monkeypatch.setattr(ee_analysis, "check", boom)
    monkeypatch.setattr(report, "check", lambda: "gemini fine")
    monkeypatch.setattr(storage, "check", lambda: "bq fine")

    response = TestClient(main.app).get("/api/health")
    body = response.json()

    assert response.status_code == 200
    assert body["ok"] is False
    assert body["services"]["earth_engine"]["status"] == "error"
    assert "no credentials" in body["services"]["earth_engine"]["detail"]
