"""Farmer photo check: EXIF, location/time flags, file handling, endpoint (Gemini stubbed)."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import ExifTags, Image

from app import assessments, config, ee_analysis, main, photo_check, storage, warehouse
from tests.test_api import BODY, FAKE_ANALYSIS
from tests.test_validation import square

PLOT = square(lng=75.0584, lat=16.7323)  # ~110 m square: sample plot plt_seed_1


def dms(value):
    value = abs(value)
    d = int(value)
    m = int((value - d) * 60)
    s = round(((value - d) * 60 - m) * 60, 4)
    return (float(d), float(m), s)


def jpeg(lat=None, lng=None, taken="2019:08:10 09:30:00", size=(64, 48), fmt="JPEG"):
    image = Image.new("RGB", size, (60, 120, 200))
    exif = Image.Exif()
    if lat is not None:
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps[ExifTags.GPS.GPSLatitudeRef] = "N" if lat >= 0 else "S"
        gps[ExifTags.GPS.GPSLatitude] = dms(lat)
        gps[ExifTags.GPS.GPSLongitudeRef] = "E" if lng >= 0 else "W"
        gps[ExifTags.GPS.GPSLongitude] = dms(lng)
    if taken:
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.DateTimeOriginal] = taken
    out = io.BytesIO()
    image.save(out, fmt, exif=exif)
    return out.getvalue()


def test_read_exif_gps_and_time():
    exif = photo_check.read_exif(Image.open(io.BytesIO(jpeg(16.7323, 75.0584))))
    assert exif["gps"] == pytest.approx({"lat": 16.7323, "lng": 75.0584}, abs=1e-5)
    assert exif["taken_at"] == "2019-08-10T09:30:00"


def test_read_exif_southern_western_and_missing():
    exif = photo_check.read_exif(Image.open(io.BytesIO(jpeg(-12.5, -45.25))))
    assert exif["gps"]["lat"] < 0 and exif["gps"]["lng"] < 0
    bare = photo_check.read_exif(Image.open(io.BytesIO(jpeg(taken=None))))
    assert bare == {"gps": None, "taken_at": None}


def test_distance_to_plot():
    assert photo_check.distance_to_plot_m(16.7323, 75.0584, PLOT) == 0
    # The top edge is at 16.7328; 0.0005 deg of latitude further north ≈ 56 m.
    assert 50 < photo_check.distance_to_plot_m(16.7333, 75.0584, PLOT) < 60


@pytest.mark.parametrize(
    "exif, flags",
    [
        ({"gps": {"lat": 16.7323, "lng": 75.0584}, "taken_at": "2019-08-10T09:30:00"}, []),
        ({"gps": None, "taken_at": "2019-08-10T09:30:00"}, ["no_gps"]),
        ({"gps": {"lat": 16.75, "lng": 75.0584}, "taken_at": None}, ["far_from_plot", "no_timestamp"]),
        ({"gps": {"lat": 16.7323, "lng": 75.0584}, "taken_at": "2019-08-01T09:30:00"}, ["taken_before_event"]),
        ({"gps": {"lat": 16.7323, "lng": 75.0584}, "taken_at": "2019-12-01T09:30:00"}, ["taken_long_after_event"]),
    ],
)
def test_location_and_time_flags(exif, flags):
    result = photo_check.location_and_time(exif, PLOT, "2019-08-07")
    assert result["flags"] == flags


def test_location_and_time_values():
    result = photo_check.location_and_time({"gps": {"lat": 16.7323, "lng": 75.0584}, "taken_at": "2019-08-10T09:30:00"}, PLOT, "2019-08-07")
    assert result == {"distance_m": 0, "inside_plot": True, "days_from_event": 3, "flags": []}


def test_load_photo_strips_location_and_downscales():
    exif, stored = photo_check.load_photo(jpeg(16.7323, 75.0584, size=(4000, 3000)))
    assert exif["gps"] is not None
    reopened = Image.open(io.BytesIO(stored))
    assert max(reopened.size) == photo_check.MAX_SIDE_PX
    assert reopened.getexif().get_ifd(ExifTags.IFD.GPSInfo) == {}


@pytest.mark.parametrize(
    "data, message",
    [
        (b"", "empty"),
        (b"not an image at all", "isn't a photo"),
        (b"x" * (photo_check.MAX_UPLOAD_BYTES + 1), "larger than 10 MB"),
    ],
)
def test_load_photo_rejects_bad_files(data, message):
    with pytest.raises(photo_check.PhotoError, match=message):
        photo_check.load_photo(data)


def test_load_photo_rejects_gif():
    out = io.BytesIO()
    Image.new("RGB", (10, 10)).save(out, "GIF")
    with pytest.raises(photo_check.PhotoError, match="JPG, PNG or WebP"):
        photo_check.load_photo(out.getvalue())


# --- Endpoint -----------------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "GCS_BUCKET", "")
    monkeypatch.setattr(config, "DEMO_MODE", False)
    monkeypatch.setattr(storage, "LOCAL_STORE", tmp_path / "store")
    monkeypatch.setattr(assessments, "DEMO_CACHE", tmp_path / "demo_cache")
    monkeypatch.setattr(warehouse, "record_assessment", lambda result: None)
    monkeypatch.setattr(ee_analysis, "assess", lambda *a: FAKE_ANALYSIS)
    monkeypatch.setattr(ee_analysis, "thumbnails", lambda *a: {})
    monkeypatch.setattr(
        photo_check,
        "ask_gemini",
        lambda jpeg_bytes, assessment: photo_check.PhotoVerdict(
            what_photo_shows="standing_water",
            consistent=True,
            observations_en="The photo shows standing water in the field.",
            observations_kn="ಫೋಟೋದಲ್ಲಿ ಹೊಲದಲ್ಲಿ ನಿಂತ ನೀರು ಕಾಣುತ್ತದೆ.",
        ),
    )
    return TestClient(main.app)


def upload(client, assessment_id, data, name="field.jpg"):
    return client.post(
        "/api/photo-check",
        data={"assessment_id": assessment_id},
        files={"photo": (name, data, "image/jpeg")},
    )


def test_photo_check_endpoint(client):
    assessment_id = client.post("/api/assess", json=BODY).json()["assessment_id"]
    response = upload(client, assessment_id, jpeg(16.7323, 75.0584))
    assert response.status_code == 200, response.text
    check = response.json()["photo_check"]
    assert check["consistent"] is True
    assert check["what_photo_shows"] == "standing_water"
    assert check["inside_plot"] is True and check["days_from_event"] == 3 and check["flags"] == []

    photo = client.get(check["photo_url"])
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/jpeg"

    stored = client.get(f"/api/assessments/{assessment_id}").json()
    assert stored["photo_check"]["photo_id"] == check["photo_id"]


def test_photo_without_gps_is_flagged(client):
    assessment_id = client.post("/api/assess", json=BODY).json()["assessment_id"]
    check = upload(client, assessment_id, jpeg()).json()["photo_check"]
    assert check["flags"] == ["no_gps"]
    assert "no location data" in check["flag_messages"][0]


def test_photo_check_errors(client, monkeypatch):
    assert upload(client, "asm_missing", jpeg()).status_code == 404
    assessment_id = client.post("/api/assess", json=BODY).json()["assessment_id"]
    bad = upload(client, assessment_id, b"not an image")
    assert bad.status_code == 422 and "isn't a photo" in bad.json()["error"]

    def boom(jpeg_bytes, assessment):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(photo_check, "ask_gemini", boom)
    failed = upload(client, assessment_id, jpeg())
    assert failed.status_code == 502 and "couldn't check the photo" in failed.json()["error"]


def test_photo_paths_are_restricted(client):
    assert client.get("/api/photos/../../etc/passwd").status_code == 404
    assert client.get("/api/photos/asm_x/ph_y.png").status_code == 404
