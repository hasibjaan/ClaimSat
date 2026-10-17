"""Plot registry: officer registration, overlap and duplicate checks, farmer lookup."""

import pytest
from fastapi.testclient import TestClient

from app import assessments, config, main, plots, storage
from tests.test_validation import square

OFFICER = {"X-Officer-Code": "test-code"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GCS_BUCKET", "")
    monkeypatch.setattr(config, "OFFICER_ACCESS_CODE", "test-code")
    monkeypatch.setattr(storage, "LOCAL_STORE", tmp_path / "store")
    monkeypatch.setattr(assessments, "DEMO_CACHE", tmp_path / "demo_cache")
    return TestClient(main.app)


def new_plot(**overrides):
    body = {
        "geometry": square(lng=75.10, lat=16.80),  # far from the seed plots
        "farmer_id": "ka-1234",
        "farmer_name": "  Lakshmi  ",
        "village": "Kagwad",
        "survey_number": "45/2",
        "crop": "paddy",
    }
    body.update(overrides)
    return body


def test_polygons_overlap():
    a = square(lng=75.0, lat=16.0)
    assert plots.polygons_overlap(a, square(lng=75.0003, lat=16.0))       # shifted, edges cross
    assert plots.polygons_overlap(a, square(lng=75.0, lat=16.0, half_deg=0.0001))  # inside
    assert plots.polygons_overlap(square(lng=75.0, lat=16.0, half_deg=0.0001), a)  # contains
    assert not plots.polygons_overlap(a, square(lng=75.002, lat=16.0))    # apart


def test_officer_registers_a_plot_and_the_farmer_sees_it(client):
    response = client.post("/api/plots", json=new_plot(), headers=OFFICER)
    assert response.status_code == 200, response.text
    plot = response.json()["plot"]
    assert plot["farmer_id"] == "KA-1234"
    assert plot["farmer_name"] == "Lakshmi"
    assert plot["source"] == "officer"
    assert 1.1 < plot["area_ha"] < 1.25

    mine = client.get("/api/farmers/KA-1234/plots").json()["plots"]
    assert [p["plot_id"] for p in mine] == [plot["plot_id"]]
    assert plot["plot_id"] in {p["plot_id"] for p in client.get("/api/plots", headers=OFFICER).json()["plots"]}


def test_registration_needs_the_officer_code(client):
    assert client.post("/api/plots", json=new_plot()).status_code == 401
    assert client.get("/api/plots").status_code == 401
    assert client.get("/api/officer/check", headers=OFFICER).json() == {"ok": True}


def test_overlapping_plot_is_rejected(client):
    client.post("/api/plots", json=new_plot(), headers=OFFICER)
    overlapping = new_plot(geometry=square(lng=75.1004, lat=16.80), survey_number="46/1", farmer_id="KA-9999")
    response = client.post("/api/plots", json=overlapping, headers=OFFICER)
    assert response.status_code == 409
    assert "overlaps a registered plot (survey number 45/2" in response.json()["error"]


def test_overlapping_a_seed_plot_is_rejected(client):
    response = client.post("/api/plots", json=new_plot(geometry=square()), headers=OFFICER)
    assert response.status_code == 409 and "112/3" in response.json()["error"]


def test_duplicate_survey_number_is_rejected(client):
    client.post("/api/plots", json=new_plot(), headers=OFFICER)
    again = new_plot(geometry=square(lng=75.12, lat=16.80), survey_number="45/2 ")
    response = client.post("/api/plots", json=again, headers=OFFICER)
    assert response.status_code == 409 and "already registered" in response.json()["error"]


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"farmer_id": "x"}, "valid Farmer ID"),
        ({"farmer_name": " "}, "farmer's name"),
        ({"survey_number": ""}, "survey number"),
        ({"village": ""}, "village"),
        ({"geometry": square(half_deg=0.01)}, "too large"),
    ],
)
def test_registration_validation(client, overrides, message):
    response = client.post("/api/plots", json=new_plot(**overrides), headers=OFFICER)
    assert response.status_code == 422
    assert message in response.json()["error"]


def test_unknown_farmer(client):
    response = client.get("/api/farmers/KA-0000/plots")
    assert response.status_code == 404
    assert "agriculture office" in response.json()["error"]
    assert client.get("/api/farmers/!!/plots").status_code == 422
