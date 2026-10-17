"""Assess a whole village of plots in one Earth Engine pass and load them into BigQuery.

Lays a grid of 1-hectare plots over the demo flood area (centred on the flood1
demo plot), keeps the ones that are mostly cropland, measures every plot with a
single server-side reduceRegions call, scores them with app.scoring, and loads
them into BigQuery with source = "batch". Earlier batch rows are replaced.

Also writes demo_cache/dashboard.json so the dashboard works in DEMO_MODE.

Run from api/:  python -m scripts.batch_village [--max-plots 120] [--no-bigquery]
"""

import argparse
import json
import math
import random
import uuid
from datetime import date, datetime, timezone

import ee

from app import assessments, config, scoring, validation, warehouse
from app.ee_analysis import (
    _crop_fraction_image,
    _ndvi_composite,
    _s1,
    _s2_masked,
    _shift_window,
    build_windows,
    flood_mask,
    init_ee,
    load_demo_plot,
)
from scripts.find_demo_plots import _square

GRID_HALF_KM = 1.6   # the village area is about 3.2 km x 3.2 km
GRID_STEP_M = 150    # plot centres every 150 m (plots are 100 m wide, so they don't touch)
MIN_CROPLAND = 0.6
VILLAGE_NAME = "Demo village, Krishna floodplain"


def grid_plots(center_lng, center_lat):
    """GeoJSON squares on a regular grid around the centre."""
    lat_step = GRID_STEP_M / 111_320
    lng_step = GRID_STEP_M / (111_320 * math.cos(math.radians(center_lat)))
    n = int(GRID_HALF_KM * 1000 / GRID_STEP_M)
    return [
        _square(center_lng + i * lng_step, center_lat + j * lat_step)
        for i in range(-n, n + 1)
        for j in range(-n, n + 1)
    ]


def clear_count(collection):
    """Per-pixel number of cloud-free observations (its plot mean ~ clear images)."""
    return (
        collection.map(lambda img: img.select(config.CS_BAND).mask().rename("n"))
        .merge(ee.ImageCollection([ee.Image.constant(0).rename("n")]))
        .sum()
    )


def measure(plots, event_type, event_date):
    """One reduceRegions pass: every metric for every plot."""
    event = date.fromisoformat(event_date)
    windows = build_windows(event_type, event)
    region = ee.Geometry.MultiPolygon([p["coordinates"] for p in plots]).bounds()

    before = _s2_masked(region, windows["before"])
    after = _s2_masked(region, windows["after"])
    baseline = ee.ImageCollection(
        [_ndvi_composite(_s2_masked(region, _shift_window(windows["after"], -k))) for k in range(1, config.BASELINE_YEARS + 1)]
    ).mean()
    pre = _s1(region, windows["radar_pre"])
    post = _s1(region, windows["radar_post"])

    stack = ee.Image.cat(
        [
            _ndvi_composite(before).rename("ndvi_before"),
            _ndvi_composite(after).rename("ndvi_after"),
            baseline.rename("ndvi_baseline_after"),
            flood_mask(pre, post).rename("flood_fraction"),
            _crop_fraction_image(region, event).rename("crop_fraction"),
            clear_count(before).rename("clear_obs_before"),
            clear_count(after).rename("clear_obs_after"),
        ]
    )
    features = ee.FeatureCollection([ee.Feature(ee.Geometry(p), {"i": i}) for i, p in enumerate(plots)])
    measured = stack.reduceRegions(features, ee.Reducer.mean(), config.SCALE_M)
    radar_counts = {"pre": pre.size(), "post": post.size()}
    return measured.getInfo()["features"], ee.Dictionary(radar_counts).getInfo(), windows


def build_results(plots, measured, radar, event_type, event_date, windows, max_plots):
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    results = []
    for feature in measured:
        props = feature["properties"]
        if (props.get("crop_fraction") or 0) < MIN_CROPLAND:
            continue
        geometry = plots[props["i"]]
        r = lambda k, d=3: None if props.get(k) is None else round(props[k], d)  # noqa: E731
        metrics = {
            "ndvi_before": r("ndvi_before"),
            "ndvi_after": r("ndvi_after"),
            "ndvi_baseline_after": r("ndvi_baseline_after"),
            "ndvi_loss": None,
            "flood_fraction": r("flood_fraction"),
            "rain_deficit": None,
            "season_rain_mm": None,
            "baseline_rain_mm": None,
            "crop_fraction": r("crop_fraction"),
            # Approximate: mean per-pixel count of clear images over the plot.
            "clear_obs_before": round(props.get("clear_obs_before") or 0),
            "clear_obs_after": round(props.get("clear_obs_after") or 0),
            "radar_obs_pre": radar["pre"],
            "radar_obs_post": radar["post"],
        }
        loss = scoring.ndvi_loss(metrics["ndvi_after"], metrics["ndvi_baseline_after"])
        metrics["ndvi_loss"] = None if loss is None else round(loss, 3)
        area_ha = round(validation.ring_area_m2(geometry["coordinates"][0]) / 10_000, 2)
        scored = scoring.score_assessment(event_type, metrics, area_pixels=100)
        result = {
            "assessment_id": "asm_b" + uuid.uuid4().hex[:11],
            "source": "batch",
            "created_at": created_at,
            "plot": {
                "plot_id": "plt_b" + uuid.uuid4().hex[:11],
                "farmer_name": None,
                "village": VILLAGE_NAME,
                "crop": None,
                "area_ha": area_ha,
                "geometry": geometry,
            },
            "event": {"type": event_type, "date": event_date, "windows": windows},
            "metrics": metrics,
            **scored,
            "acquisitions": {},
        }
        result["evidence_hash"] = assessments.evidence_hash(result)
        results.append(result)

    random.Random(42).shuffle(results)
    return results[:max_plots]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plot", default="flood1", help="demo plot to centre the village on")
    parser.add_argument("--max-plots", type=int, default=120)
    parser.add_argument("--no-bigquery", action="store_true", help="only write demo_cache/dashboard.json")
    args = parser.parse_args()

    init_ee()
    demo = load_demo_plot(args.plot)
    if demo["event_type"] != "flood":
        raise SystemExit("The village batch is built around a flood demo plot (e.g. --plot flood1).")
    ring = demo["geometry"]["coordinates"][0][:-1]
    center = (sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring))
    plots = grid_plots(*center)
    print(f"Measuring {len(plots)} grid cells around {center} for the {demo['event_date']} {demo['event_type']}…")

    measured, radar, windows = measure(plots, demo["event_type"], demo["event_date"])
    results = build_results(plots, measured, radar, demo["event_type"], demo["event_date"], windows, args.max_plots)
    levels = {}
    for res in results:
        levels[res["score"]["damage_level"]] = levels.get(res["score"]["damage_level"], 0) + 1
    print(f"{len(results)} cropland plots kept. Damage levels: {levels}")

    # Dashboard cache for DEMO_MODE (same shape as GET /api/dashboard).
    dashboard_plots = [
        {
            "assessment_id": res["assessment_id"],
            "plot_id": res["plot"]["plot_id"],
            "farmer_name": None,
            "village": VILLAGE_NAME,
            "crop": None,
            "area_ha": res["plot"]["area_ha"],
            "event_type": res["event"]["type"],
            "event_date": res["event"]["date"],
            "damage_score": res["score"]["damage_score"],
            "damage_level": res["score"]["damage_level"],
            "confidence": res["confidence"]["level"],
            "ndvi_loss": res["metrics"]["ndvi_loss"],
            "flood_fraction": res["metrics"]["flood_fraction"],
            "rain_deficit": None,
            "source": "batch",
            "assessed_at": res["created_at"],
            "geometry": res["plot"]["geometry"],
        }
        for res in results
    ]
    cache = assessments.DEMO_CACHE / "dashboard.json"
    cache.write_text(json.dumps({"source": "cache", "plots": dashboard_plots, **warehouse.summarise(dashboard_plots)}))
    print(f"Wrote {cache}")

    if args.no_bigquery:
        return
    plot_rows, assessment_rows = zip(*(warehouse.rows_for(res) for res in results))
    warehouse.load_rows("plots", list(plot_rows), replace_source="batch")
    warehouse.load_rows("assessments", list(assessment_rows), replace_source="batch")
    print(f"Loaded {len(results)} plots into {warehouse.table('assessments')}")


if __name__ == "__main__":
    main()
