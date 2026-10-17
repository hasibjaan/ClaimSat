"""Check a farmer's field photo against the satellite evidence.

1. Read where and when the photo was taken from its EXIF data.
2. Compare that with the plot outline and the event date.
3. Ask Gemini (vision) whether what the photo shows is consistent with the
   satellite measurements. Gemini judges consistency only; it never accuses
   anyone of fraud and never changes the damage score.

Only a downscaled copy without EXIF is stored, so the photo's location data
isn't kept or shared.
"""

import io
import json
import math
import uuid
from datetime import date, datetime, timezone
from typing import Literal

from google.genai import types
from PIL import ExifTags, Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

from app import config, report

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "MPO"}  # MPO: some phone cameras' JPEG variant
MAX_SIDE_PX = 1600
NEAR_PLOT_M = 200         # photos taken further than this from the plot are flagged
LATE_PHOTO_DAYS = 60      # photos taken this long after the event are flagged

FLAG_TEXT = {
    "no_gps": "The photo has no location data, so it can't be tied to this plot.",
    "far_from_plot": "The photo was taken more than 200 m from the plot.",
    "no_timestamp": "The photo has no date, so it can't be tied to the event.",
    "taken_before_event": "The photo was taken before the event date.",
    "taken_long_after_event": "The photo was taken more than 60 days after the event.",
}


class PhotoError(ValueError):
    """A user-facing message about the uploaded file."""


# --- EXIF (pure) ------------------------------------------------------------------------


def _dms_to_degrees(dms, ref):
    degrees, minutes, seconds = (float(v) for v in dms)
    value = degrees + minutes / 60 + seconds / 3600
    return -value if ref in ("S", "W") else value


def read_exif(image):
    """Return {"gps": {"lat","lng"} or None, "taken_at": ISO string or None}."""
    exif = image.getexif()
    gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps = None
    try:
        lat = _dms_to_degrees(gps_ifd[ExifTags.GPS.GPSLatitude], gps_ifd.get(ExifTags.GPS.GPSLatitudeRef, "N"))
        lng = _dms_to_degrees(gps_ifd[ExifTags.GPS.GPSLongitude], gps_ifd.get(ExifTags.GPS.GPSLongitudeRef, "E"))
        if -90 <= lat <= 90 and -180 <= lng <= 180 and not (lat == 0 and lng == 0):
            gps = {"lat": round(lat, 6), "lng": round(lng, 6)}
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        pass

    raw = exif.get_ifd(ExifTags.IFD.Exif).get(ExifTags.Base.DateTimeOriginal) or exif.get(ExifTags.Base.DateTime)
    taken_at = None
    if raw:
        try:
            taken_at = datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S").isoformat()
        except ValueError:
            pass
    return {"gps": gps, "taken_at": taken_at}


# --- Location and time (pure) -----------------------------------------------------------


def _point_in_ring(lng, lat, ring):
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def distance_to_plot_m(lat, lng, geometry):
    """0 if the point is inside the plot, else the distance to its edge in metres."""
    ring = geometry["coordinates"][0]
    if _point_in_ring(lng, lat, ring):
        return 0.0
    # Local flat projection around the point (fine at field scale).
    m_per_deg_lat = 111_320
    m_per_deg_lng = 111_320 * math.cos(math.radians(lat))

    def to_xy(p):
        return ((p[0] - lng) * m_per_deg_lng, (p[1] - lat) * m_per_deg_lat)

    best = math.inf
    for a, b in zip(ring, ring[1:]):
        (ax, ay), (bx, by) = to_xy(a), to_xy(b)
        dx, dy = bx - ax, by - ay
        t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def location_and_time(exif, geometry, event_date):
    """Distance, days from the event, and flags explaining any problem."""
    flags = []
    distance = None
    if exif["gps"]:
        distance = round(distance_to_plot_m(exif["gps"]["lat"], exif["gps"]["lng"], geometry))
        if distance > NEAR_PLOT_M:
            flags.append("far_from_plot")
    else:
        flags.append("no_gps")

    days = None
    if exif["taken_at"]:
        days = (datetime.fromisoformat(exif["taken_at"]).date() - date.fromisoformat(event_date)).days
        if days < 0:
            flags.append("taken_before_event")
        elif days > LATE_PHOTO_DAYS:
            flags.append("taken_long_after_event")
    else:
        flags.append("no_timestamp")
    return {"distance_m": distance, "inside_plot": None if distance is None else distance == 0, "days_from_event": days, "flags": flags}


# --- Image handling ----------------------------------------------------------------------


def load_photo(data):
    """Validate the upload. Returns (exif info, downscaled JPEG bytes without EXIF)."""
    if not data:
        raise PhotoError("The photo is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise PhotoError("The photo is larger than 10 MB. Please upload a smaller photo.")
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise PhotoError("That file isn't a photo we can read. Please upload a JPG or PNG.") from None
    if image.format not in ALLOWED_FORMATS:
        raise PhotoError("Please upload a JPG, PNG or WebP photo.")

    exif = read_exif(image)
    clean = ImageOps.exif_transpose(image).convert("RGB")  # apply camera rotation, drop alpha
    clean.thumbnail((MAX_SIDE_PX, MAX_SIDE_PX))
    out = io.BytesIO()
    clean.save(out, "JPEG", quality=85)  # no exif= argument: metadata is not copied
    return exif, out.getvalue()


# --- Gemini vision -------------------------------------------------------------------------


class PhotoVerdict(BaseModel):
    what_photo_shows: Literal[
        "standing_water", "flattened_or_damaged_crop", "dried_crop", "healthy_crop",
        "bare_soil", "not_a_field", "unclear",
    ]
    consistent: bool = Field(description="Does the photo agree with the satellite evidence?")
    observations_en: str = Field(description="2-3 plain sentences: what the photo shows and whether it agrees")
    observations_kn: str = Field(description="The same in simple Kannada")


PHOTO_INSTRUCTION = """\
You compare a farmer's field photo with satellite evidence for a crop insurance
claim. Look only at what is visible in the photo.

- Decide what the photo mainly shows, and whether that is consistent with the
  satellite evidence (for example: severe flood damage + standing water or
  flattened crop = consistent; severe damage + a healthy green crop = not
  consistent; no clear damage + healthy crop = consistent).
- If the photo is not of a farm field, or is too dark or blurry to judge, say so
  and set consistent to false.
- Never accuse anyone of fraud or of faking the photo. Do not change or restate
  the damage score; only describe agreement.
- Use plain language a farmer understands. Kannada must be simple and natural.
- Use Western digits. Do not invent numbers.
"""


def _photo_facts(assessment):
    return {
        "event_type": assessment["event"]["type"],
        "event_date": assessment["event"]["date"],
        "crop_reported_by_user": assessment["plot"].get("crop") or None,
        "satellite_damage_level": assessment["score"]["damage_level"],
        "satellite_confidence": assessment["confidence"]["level"],
        "field_flooded_percent": None
        if assessment["metrics"].get("flood_fraction") is None
        else round(assessment["metrics"]["flood_fraction"] * 100),
        "crop_health_lost_percent": None
        if assessment["metrics"].get("ndvi_loss") is None
        else round(assessment["metrics"]["ndvi_loss"] * 100),
    }


def ask_gemini(jpeg, assessment):
    response = report.get_client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
            "Satellite evidence (JSON):\n" + json.dumps(_photo_facts(assessment), ensure_ascii=False),
        ],
        config=types.GenerateContentConfig(
            system_instruction=PHOTO_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=PhotoVerdict,
            temperature=0.2,
        ),
    )
    if response.parsed is None:
        raise RuntimeError("Gemini did not return a valid photo check")
    return response.parsed


def check(data, assessment):
    """Full check. Returns (photo_check dict, stored JPEG bytes, photo_id)."""
    exif, jpeg = load_photo(data)
    place_time = location_and_time(exif, assessment["plot"]["geometry"], assessment["event"]["date"])
    verdict = ask_gemini(jpeg, assessment)
    photo_id = "ph_" + uuid.uuid4().hex[:10]
    result = {
        "photo_id": photo_id,
        "photo_url": f"/api/photos/{assessment['assessment_id']}/{photo_id}.jpg",
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "model": config.GEMINI_MODEL,
        "gps": exif["gps"],
        "taken_at": exif["taken_at"],
        **place_time,
        "flag_messages": [FLAG_TEXT[f] for f in place_time["flags"]],
        **verdict.model_dump(),
    }
    return result, jpeg, photo_id
