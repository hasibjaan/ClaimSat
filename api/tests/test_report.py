"""Gemini report: facts, number check, retry, and the endpoint (Gemini stubbed)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import assessments, config, ee_analysis, main, report, storage, warehouse
from tests.test_api import BODY, FAKE_ANALYSIS

SAMPLE = json.loads((Path(__file__).parents[2] / "shared" / "sample_result.json").read_text())


def report_text(percent="65%", flooded="83%"):
    finding = report.Finding(
        title_en="Crop health dropped",
        title_kn="ಬೆಳೆಯ ಆರೋಗ್ಯ ಕುಸಿದಿದೆ",
        detail_en=f"About {percent} of normal crop health was lost.",
        detail_kn=f"ಸಾಮಾನ್ಯ ಬೆಳೆ ಆರೋಗ್ಯದ ಸುಮಾರು {percent} ನಷ್ಟವಾಗಿದೆ.",
    )
    return report.ReportText(
        summary_en=f"Satellite images show severe damage. {flooded} of the field was flooded.",
        summary_kn=f"ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ತೀವ್ರ ಹಾನಿಯನ್ನು ತೋರಿಸುತ್ತವೆ. ಹೊಲದ {flooded} ಭಾಗ ಜಲಾವೃತವಾಗಿತ್ತು.",
        findings=[finding],
        confidence_reasons_kn=["ಕಾರಣ"],
        limitations_en="Clouds can hide the field.",
        limitations_kn="ಮೋಡಗಳು ಹೊಲವನ್ನು ಮರೆಮಾಡಬಹುದು.",
        recommended_next_steps_en="Report the loss within 72 hours.",
        recommended_next_steps_kn="72 ಗಂಟೆಗಳೊಳಗೆ ನಷ್ಟವನ್ನು ವರದಿ ಮಾಡಿ.",
    )


def test_facts_contain_only_measured_percentages():
    facts = report.build_facts(SAMPLE)
    assert facts["percentages"] == {"crop_health_lost": 65, "field_flooded": 83, "plot_is_cropland": 78}
    assert facts["damage"] == {"score_out_of_100": 74, "level": "severe"}
    assert facts["confidence"]["level"] == "high"


def test_number_check_accepts_measured_values_and_flags_invented_ones():
    facts = report.build_facts(SAMPLE)
    assert report.unexpected_percentages(report_text("65%"), facts) == []
    assert report.unexpected_percentages(report_text("66%"), facts) == []  # rounding tolerance
    assert report.unexpected_percentages(report_text("40%"), facts) == ["40%"]


def test_generate_retries_once_when_a_percentage_is_invented(monkeypatch):
    calls = []

    def fake_ask(facts, correction=None):
        calls.append(correction)
        return report_text("40%" if correction is None else "65%")

    monkeypatch.setattr(report, "_ask_gemini", fake_ask)
    result = report.generate(SAMPLE)
    assert len(calls) == 2 and "40%" in calls[1]
    assert result["number_check"] == {"ok": True, "unexpected_percentages": []}
    assert result["summary_kn"].startswith("ಉಪಗ್ರಹ")


def test_generate_flags_a_report_that_is_still_wrong(monkeypatch):
    monkeypatch.setattr(report, "_ask_gemini", lambda facts, correction=None: report_text("40%"))
    result = report.generate(SAMPLE)
    assert result["number_check"] == {"ok": False, "unexpected_percentages": ["40%"]}


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


def test_report_endpoint_generates_stores_and_reuses(client, monkeypatch):
    calls = []
    monkeypatch.setattr(report, "_ask_gemini", lambda facts, correction=None: calls.append(1) or report_text("63%", "80%"))
    assessment_id = client.post("/api/assess", json=BODY).json()["assessment_id"]

    first = client.post(f"/api/report/{assessment_id}")
    assert first.status_code == 200, first.text
    assert first.json()["report"]["findings"][0]["title_en"] == "Crop health dropped"

    stored = client.get(f"/api/assessments/{assessment_id}").json()
    assert stored["report"]["summary_en"] == first.json()["report"]["summary_en"]

    client.post(f"/api/report/{assessment_id}")
    assert len(calls) == 1  # reused, not regenerated
    client.post(f"/api/report/{assessment_id}?refresh=true")
    assert len(calls) == 2


def test_report_endpoint_errors(client, monkeypatch):
    assert client.post("/api/report/asm_missing").status_code == 404

    def boom(facts, correction=None):
        raise RuntimeError("model not found")

    monkeypatch.setattr(report, "_ask_gemini", boom)
    assessment_id = client.post("/api/assess", json=BODY).json()["assessment_id"]
    response = client.post(f"/api/report/{assessment_id}")
    assert response.status_code == 502
    assert "couldn't write the report" in response.json()["error"]
