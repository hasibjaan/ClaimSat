"""Nearby reports, for case severity.

Every live assessment adds a small entry to the report index (registry of who
reported what, where and when). A case's severity counts the OTHER farmers who
reported the same kind of event within 2 km and 7 days. Seed reports
(seed_reports.json) make the sample area realistic for demos.
"""

import json
import math
from datetime import date
from pathlib import Path

from app import config, scoring, storage

SEED_PATH = Path(__file__).resolve().parent / "seed_reports.json"
INDEX_PATH = "reports/index.json"


def _distance_km(lat1, lng1, lat2, lng2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def all_reports():
    seed = json.loads(SEED_PATH.read_text())["reports"]
    return seed + (storage.load_json(INDEX_PATH) or [])


def record(result):
    """Add a live assessment to the report index."""
    entry = {
        "assessment_id": result["assessment_id"],
        "farmer_id": result["plot"].get("farmer_id"),
        "plot_id": result["plot"]["plot_id"],
        "lat": result["plot"]["centroid"]["lat"],
        "lng": result["plot"]["centroid"]["lng"],
        "event_type": result["event"]["type"],
        "event_date": result["event"]["date"],
        "damage_score": result["score"]["damage_score"],
        "created_at": result.get("created_at"),
    }
    storage.save_json(INDEX_PATH, (storage.load_json(INDEX_PATH) or []) + [entry])


def nearby(lat, lng, farmer_id, event_type, event_date, reports=None):
    """Other farmers' reports of the same event type within the radius and time window."""
    event = date.fromisoformat(event_date)
    matches = [
        r
        for r in (reports if reports is not None else all_reports())
        if r["event_type"] == event_type
        and r.get("farmer_id") != farmer_id
        and abs((date.fromisoformat(r["event_date"]) - event).days) <= config.NEARBY_WINDOW_DAYS
        and _distance_km(lat, lng, r["lat"], r["lng"]) <= config.NEARBY_RADIUS_KM
    ]
    # One farmer reporting several times counts once (their latest report).
    latest = {}
    for r in sorted(matches, key=lambda r: r.get("created_at") or ""):
        latest[r.get("farmer_id") or r["assessment_id"]] = r
    scores = [r["damage_score"] for r in latest.values() if r.get("damage_score") is not None]
    farmers = len(latest)
    return {
        "radius_km": config.NEARBY_RADIUS_KM,
        "window_days": config.NEARBY_WINDOW_DAYS,
        "nearby_reports": len(matches),
        "nearby_farmers": farmers,
        "nearby_avg_damage": round(sum(scores) / len(scores)) if scores else None,
        "level": scoring.area_level(farmers),
    }
