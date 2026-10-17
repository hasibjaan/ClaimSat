"""Registered plots.

Farmers can't draw their own plots: someone could outline more land than they
own. An agriculture officer registers each plot (checked against the land
records, by survey number), and a farmer can only choose from the plots
registered to their Farmer ID. Assessments always use the registered outline.

Sources, merged: the seed file (sample plots), the demo plots found by
scripts/find_demo_plots.py, and plots officers registered (stored in
registry/plots.json via app.storage).
"""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app import storage, validation

SEED_PATH = Path(__file__).resolve().parent / "seed_plots.json"
REGISTRY_PATH = "registry/plots.json"
FARMER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{2,31}$")

# Demo plots from find_demo_plots.py belong to these demo farmers.
DEMO_FARMERS = {
    False: {"farmer_id": "KA-DEMO-001", "farmer_name": "Ramesh", "village": "Athani taluk"},
    True: {"farmer_id": "KA-DEMO-002", "farmer_name": "Suresh", "village": "Neighbouring village"},
}


class PlotError(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalise_farmer_id(value):
    farmer_id = str(value or "").strip().upper()
    if not FARMER_ID.match(farmer_id):
        raise PlotError("Enter a valid Farmer ID (letters, digits and dashes, for example KA-DEMO-001).")
    return farmer_id


def _demo_plots():
    from app import assessments  # imported here: assessments imports this module

    plots = []
    for i, demo in enumerate(assessments.demo_plots(), start=1):
        farmer = DEMO_FARMERS[bool(demo.get("control"))]
        plots.append(
            {
                "plot_id": f"plt_{demo['id']}",
                **farmer,
                "survey_number": f"DEMO-{i}",
                "crop": demo.get("crop"),
                "geometry": demo["geometry"],
                "default_event": {
                    "event_type": demo["event_type"],
                    "event_date": demo["event_date"],
                    **({"season_window": demo["season_window"]} if demo.get("season_window") else {}),
                },
                "source": "demo",
                "registered_by": "demo",
                "registered_at": None,
            }
        )
    return plots


def _registered():
    return storage.load_json(REGISTRY_PATH) or []


def all_plots():
    seed = json.loads(SEED_PATH.read_text())["plots"]
    plots = seed + _demo_plots() + _registered()
    for plot in plots:
        plot.setdefault("area_ha", round(validation.ring_area_m2(plot["geometry"]["coordinates"][0]) / 10_000, 2))
    return plots


def get_plot(plot_id):
    return next((p for p in all_plots() if p["plot_id"] == plot_id), None)


def plots_for_farmer(farmer_id):
    farmer_id = normalise_farmer_id(farmer_id)
    return [p for p in all_plots() if p["farmer_id"] == farmer_id]


# --- Overlap check (pure) -------------------------------------------------------------


def _point_in_ring(lng, lat, ring):
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def polygons_overlap(a, b):
    """True if two GeoJSON polygons' outer rings overlap (touching edges don't count)."""
    ring_a, ring_b = a["coordinates"][0], b["coordinates"][0]
    for p, q in zip(ring_a, ring_a[1:]):
        for r, s in zip(ring_b, ring_b[1:]):
            if validation._segments_cross(p, q, r, s):
                return True
    # No crossing edges: overlap only if one polygon sits inside the other.
    inside = lambda ring, other: _point_in_ring(*validation.ring_centroid(ring), other)  # noqa: E731
    return inside(ring_a, ring_b) or inside(ring_b, ring_a)


# --- Registration (officers only) ----------------------------------------------------------


def register(body, officer="officer"):
    """Register a plot after checking the outline and that it overlaps no other plot."""
    geometry, area_ha = validation.validate_geometry(body.get("geometry"))
    farmer_id = normalise_farmer_id(body.get("farmer_id"))
    farmer_name = validation.clean_text(body.get("farmer_name"))
    survey_number = validation.clean_text(body.get("survey_number"))
    village = validation.clean_text(body.get("village"))
    if not farmer_name:
        raise PlotError("Enter the farmer's name.")
    if not survey_number:
        raise PlotError("Enter the survey number from the land records.")
    if not village:
        raise PlotError("Enter the village.")

    existing = all_plots()
    for plot in existing:
        if plot["survey_number"].lower() == survey_number.lower() and plot["village"].lower() == village.lower():
            raise PlotError(f"Survey number {survey_number} in {village} is already registered.", 409)
        if polygons_overlap(geometry, plot["geometry"]):
            raise PlotError(
                f"This outline overlaps a registered plot (survey number {plot['survey_number']}, "
                f"{plot['village']}). Check the land records and redraw.",
                409,
            )

    plot = {
        "plot_id": "plt_" + uuid.uuid4().hex[:12],
        "farmer_id": farmer_id,
        "farmer_name": farmer_name,
        "village": village,
        "survey_number": survey_number,
        "crop": validation.clean_text(body.get("crop")) or None,
        "geometry": geometry,
        "area_ha": round(area_ha, 2),
        "default_event": None,
        "source": "officer",
        "registered_by": officer,
        "registered_at": _now(),
    }
    storage.save_json(REGISTRY_PATH, _registered() + [plot])
    return plot
