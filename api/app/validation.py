"""Input validation for assessment requests. Pure Python, no Earth Engine.

The frontend mirrors these rules for quick feedback (web/src/lib/geo.js), but
the backend is the source of truth.
"""

import math
from datetime import date, timedelta

from app import config

EARTH_RADIUS_M = 6_378_137
MIN_AREA_HA = 0.05
MAX_AREA_HA = 20
INDIA_BBOX = (68.0, 6.0, 98.0, 37.5)  # min lng, min lat, max lng, max lat
EARLIEST_EVENT = date(2016, 1, 1)
MIN_DAYS_AGO = 1   # the comparison uses the latest image, so recent events are fine
MAX_TEXT = 80
MAX_VERTICES = 200


class ValidationError(ValueError):
    """A user-facing message explaining what's wrong with the request."""


def ring_area_m2(ring):
    """Area of a lng/lat ring on a sphere (Chamberlain & Duquette)."""
    total = 0.0
    for (lng1, lat1), (lng2, lat2) in zip(ring, ring[1:]):
        total += math.radians(lng2 - lng1) * (
            2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2))
        )
    return abs(total) * EARTH_RADIUS_M**2 / 2


def ring_centroid(ring):
    """Mean of the vertices (good enough for plots of a few hectares)."""
    points = ring[:-1] if ring[0] == ring[-1] else ring
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    )


def _segments_cross(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    d1, d2 = orient(c, d, a), orient(c, d, b)
    d3, d4 = orient(a, b, c), orient(a, b, d)
    return d1 * d2 < 0 and d3 * d4 < 0


def _self_intersects(ring):
    edges = list(zip(ring, ring[1:]))
    n = len(edges)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue  # first and last edges share a vertex
            if _segments_cross(*edges[i], *edges[j]):
                return True
    return False


def validate_geometry(geometry):
    """Return a clean GeoJSON Polygon (outer ring only, closed) and its area in ha."""
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        raise ValidationError("Draw your plot as a single polygon.")
    rings = geometry.get("coordinates")
    if not isinstance(rings, list) or not rings or not isinstance(rings[0], list):
        raise ValidationError("The plot shape is missing its coordinates.")

    try:
        ring = [(float(p[0]), float(p[1])) for p in rings[0]]
    except (TypeError, ValueError, IndexError):
        raise ValidationError("The plot shape has invalid coordinates.") from None
    if not all(math.isfinite(v) for p in ring for v in p):
        raise ValidationError("The plot shape has invalid coordinates.")
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    if len(ring) < 4:
        raise ValidationError("A plot needs at least 3 corners.")
    if len(ring) > MAX_VERTICES:
        raise ValidationError(f"Please draw the plot with fewer than {MAX_VERTICES} corners.")

    min_lng, min_lat, max_lng, max_lat = INDIA_BBOX
    if not all(min_lng <= lng <= max_lng and min_lat <= lat <= max_lat for lng, lat in ring):
        raise ValidationError("The plot must be in India.")
    if _self_intersects(ring):
        raise ValidationError("The plot outline crosses itself. Please redraw it.")

    area_ha = ring_area_m2(ring) / 10_000
    if area_ha < MIN_AREA_HA:
        raise ValidationError(
            f"The plot is too small ({area_ha:.2f} ha). Draw at least {MIN_AREA_HA} ha (about 500 m²)."
        )
    if area_ha > MAX_AREA_HA:
        raise ValidationError(
            f"The plot is too large ({area_ha:.1f} ha). Draw a single field of up to {MAX_AREA_HA} ha."
        )
    return {"type": "Polygon", "coordinates": [[list(p) for p in ring]]}, area_ha


def _parse_date(value, label):
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(f"{label} must be a date in YYYY-MM-DD format.") from None


def validate_event(event_type, event_date, season_window=None, today=None):
    """Return (event_type, event_date, season_window or None)."""
    today = today or date.today()
    if event_type not in config.EVENT_TYPES:
        raise ValidationError("Choose an event type: flood, drought or other.")

    event = _parse_date(event_date, "The event date")
    latest = today - timedelta(days=MIN_DAYS_AGO)
    if event < EARLIEST_EVENT:
        raise ValidationError("Satellite data for ClaimSat starts in 2016. Choose a later date.")
    if event > latest:
        raise ValidationError(
            "The event date must be before today."
        )

    season = None
    if event_type == "drought" and season_window:
        start = _parse_date(season_window.get("start"), "The season start")
        end = _parse_date(season_window.get("end"), "The season end")
        if not start < end:
            raise ValidationError("The season must end after it starts.")
        if start < EARLIEST_EVENT or start > latest:
            raise ValidationError("The season must start between 2016 and a week ago.")
        if (end - start).days > 366:
            raise ValidationError("The season can be at most one year long.")
        season = {"start": start.isoformat(), "end": end.isoformat()}
    return event_type, event, season


def clean_text(value):
    return " ".join(str(value or "").split())[:MAX_TEXT]
