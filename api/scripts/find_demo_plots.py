"""Find demo plots for ClaimSat and save them to demo_cache/demo_plots.json.

August 2019 Krishna river floods, Belagavi/Bagalkot districts, Karnataka.
Using Sentinel-2 only (the same satellite the app uses):
  1. Build cloud-free composites for the week before the event and the two
     weeks after it, and map cropland (green before) that became water.
  2. Pick up to 3 one-hectare cells that flooded, plus 1 nearby cell that
     stayed dry and green (control).
Every candidate is then checked with the real assessment (app.ee_analysis.assess),
which compares single images: ~1 week before vs the latest clear image.

Monsoon clouds can hide many days; if nothing is found, try a different
EVENT_DATE or AOI.

Run from api/:  python -m scripts.find_demo_plots
"""

import json
import math
from datetime import date, datetime, timezone

import ee

from app import config, scoring
from app.ee_analysis import DEMO_PLOTS_PATH, S2_BANDS, _s2_masked, assess, build_windows, init_ee, ndvi, water

UTM_43N = "EPSG:32643"  # covers Karnataka; true 10 m and 100 m grids
CELL_M = 100            # demo plots are 100 m x 100 m squares (1 ha)
FLOOD_AOI = [74.55, 16.30, 75.75, 16.95]   # Krishna river, Athani-Raibag-Jamkhandi
EVENT_DATE = "2019-08-07"


def _square(lng, lat, size_m=CELL_M):
    """GeoJSON polygon for a size_m x size_m square centred on (lng, lat)."""
    half_lat = (size_m / 2) / 111_320
    half_lng = (size_m / 2) / (111_320 * math.cos(math.radians(lat)))
    ring = [
        [lng - half_lng, lat - half_lat],
        [lng + half_lng, lat - half_lat],
        [lng + half_lng, lat + half_lat],
        [lng - half_lng, lat + half_lat],
        [lng - half_lng, lat - half_lat],
    ]
    return {"type": "Polygon", "coordinates": [[[round(x, 6), round(y, 6)] for x, y in ring]]}


def _distance_km(a, b):
    lng1, lat1, lng2, lat2 = map(math.radians, [*a, *b])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _points(feature_collection):
    """[((lng, lat), properties)], geometries converted from UTM to lat/lng."""
    in_wgs84 = feature_collection.map(lambda f: f.transform("EPSG:4326", 1))
    return [(tuple(f["geometry"]["coordinates"]), f["properties"]) for f in in_wgs84.getInfo()["features"]]


def _check(geometry):
    result = assess(geometry, "flood", EVENT_DATE)
    result.update(scoring.score_assessment("flood", result["metrics"], result["plot_stats"]["area_pixels"]))
    m = result["metrics"]
    summary = (
        f"score={result['score']['damage_score']} ({result['score']['damage_level']}), "
        f"confidence={result['confidence']['level']}, new water={m['flood_fraction']}, "
        f"crop health lost={m['ndvi_loss']}, images {m['before_image_date']} -> {m['now_image_date']}"
    )
    return result, summary


def _plot(plot_id, label, geometry, control, summary):
    return {
        "id": plot_id,
        "label": label,
        "event_type": "flood",
        "event_date": EVENT_DATE,
        "crop": "sugarcane",
        "crop_note": "Assumed for the demo: sugarcane dominates this stretch of the Krishna. Not verified.",
        "control": control,
        "geometry": geometry,
        "check": summary,
    }


def main():
    init_ee()
    aoi = ee.Geometry.Rectangle(FLOOD_AOI)
    windows = build_windows(date.fromisoformat(EVENT_DATE))
    before = _s2_masked(aoi, windows["before"]).select(S2_BANDS + [config.CS_BAND]).median()
    now = _s2_masked(aoi, windows["now"]).select(S2_BANDS + [config.CS_BAND]).median()

    green_before = ndvi(before).gt(0.4).rename("green")
    new_water = water(now).And(water(before).Not()).rename("flooded")
    stack = new_water.addBands(green_before).reproject(ee.Projection(UTM_43N).atScale(config.SCALE_M))
    cells = stack.reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(ee.Projection(UTM_43N).atScale(CELL_M))
    samples = cells.sample(region=aoi, scale=CELL_M, projection=UTM_43N, numPixels=30000, seed=7, geometries=True)

    flooded = _points(
        samples.filter(ee.Filter.And(ee.Filter.gte("green", 0.7), ee.Filter.gte("flooded", 0.6))).sort("flooded", False).limit(40)
    )
    dry = _points(samples.filter(ee.Filter.And(ee.Filter.gte("green", 0.8), ee.Filter.eq("flooded", 0))).limit(400))
    print(f"{len(flooded)} flooded cropland cells, {len(dry)} dry cropland cells")
    if not flooded:
        raise SystemExit("No flooded cropland found in clear images. Try another EVENT_DATE or AOI.")

    plots, picked = [], []
    for point, _ in flooded:
        if len(plots) == 3:
            break
        if any(_distance_km(point, p) < 2 for p in picked):
            continue
        geometry = _square(*point)
        result, summary = _check(geometry)
        print(f"  flood candidate {point}: {summary}")
        m = result["metrics"]
        if (m["flood_fraction"] or 0) >= 0.4 and result["confidence"]["level"] != "low":
            picked.append(point)
            plots.append(_plot(f"flood{len(plots) + 1}", f"Flooded field near the Krishna river #{len(plots) + 1}", geometry, False, summary))
    if not plots:
        raise SystemExit("No flood candidate passed the single-image check.")

    for point, _ in sorted((c for c in dry if 3 <= _distance_km(c[0], picked[0]) <= 15), key=lambda c: _distance_km(c[0], picked[0]))[:6]:
        geometry = _square(*point)
        result, summary = _check(geometry)
        print(f"  control candidate {point}: {summary}")
        if (result["metrics"]["flood_fraction"] or 0) < 0.1 and (result["metrics"]["ndvi_loss"] or 0) < 0.2:
            plots.append(_plot("control1", "Unflooded field nearby (control)", geometry, True, summary))
            break
    else:
        print("WARNING: no control candidate passed the check; no control plot saved.")

    DEMO_PLOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMO_PLOTS_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "method": "scripts/find_demo_plots.py (Sentinel-2 only)",
                "event_date": EVENT_DATE,
                "plots": plots,
            },
            indent=2,
        )
    )
    print(f"\nSaved {len(plots)} demo plots to {DEMO_PLOTS_PATH}:")
    for p in plots:
        print(f"  {p['id']}: {p['check']}")


if __name__ == "__main__":
    main()
