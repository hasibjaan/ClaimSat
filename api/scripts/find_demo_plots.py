"""Find demo plots for ClaimSat and save them to demo_cache/demo_plots.json.

Flood: August 2019 Krishna river floods, Belagavi/Bagalkot districts, Karnataka.
  1. Find the flood peak date from Sentinel-1 radar rather than assuming it.
  2. Map flooded cropland at that date and pick 3 one-hectare cells that were
     almost fully flooded, plus 1 nearby cropland cell that stayed dry (control).
Drought: 2023 Karnataka kharif drought, Gadag/Koppal area.
  3. Pick the cropland cell with the biggest NDVI drop versus 2020-2022.
Every candidate is then checked with the real assessment (app.ee_analysis.assess).

Run from api/:  python -m scripts.find_demo_plots
"""

import json
import math
from datetime import date, datetime, timedelta, timezone

import ee

from app import config, scoring
from app.ee_analysis import DEMO_PLOTS_PATH, assess, flood_mask, init_ee, ms_to_date

UTM_43N = "EPSG:32643"  # covers Karnataka; used to get true 10 m and 100 m grids
CELL_M = 100            # demo plots are 100 m x 100 m squares (1 ha)

FLOOD_AOI = [74.55, 16.30, 75.75, 16.95]        # Krishna river, Athani-Raibag-Jamkhandi
FLOOD_SEARCH = ("2019-07-25", "2019-09-01")     # when to look for the flood peak
FLOOD_DRY_REFERENCE = ("2019-06-01", "2019-07-15")
FLOOD_CROPLAND_YEAR = ("2018-08-01", "2019-07-31")

DROUGHT_AOI = [75.40, 15.00, 76.60, 15.70]      # Gadag / Koppal
DROUGHT_EVENT_DATE = "2023-08-31"
DROUGHT_SEASON = {"start": "2023-06-01", "end": "2023-09-30"}
DROUGHT_NDVI_WINDOW = ("08-15", "09-30")
DROUGHT_BASELINE_YEARS = (2020, 2021, 2022)


def _s1_vv(region, start, end):
    return (
        ee.ImageCollection(config.S1_COLLECTION)
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .select("VV")
    )


def _cropland(region, start, end):
    """Mean Dynamic World crop probability, on a real 10 m grid."""
    return (
        ee.ImageCollection(config.DYNAMIC_WORLD_COLLECTION)
        .filterBounds(region)
        .filterDate(start, end)
        .select("crops")
        .mean()
        .setDefaultProjection(ee.Projection(UTM_43N).atScale(config.SCALE_M))
    )


def _to_cells(image):
    """Average a 10 m image into 100 m cells."""
    return image.reduceResolution(ee.Reducer.mean(), maxPixels=1024).reproject(
        ee.Projection(UTM_43N).atScale(CELL_M)
    )


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
    """Haversine distance between two (lng, lat) points."""
    lng1, lat1, lng2, lat2 = map(math.radians, [*a, *b])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _points(feature_collection):
    """[((lng, lat), properties)], with geometries converted from UTM to lat/lng."""
    in_wgs84 = feature_collection.map(lambda f: f.transform("EPSG:4326", 1))
    return [
        (tuple(f["geometry"]["coordinates"]), f["properties"])
        for f in in_wgs84.getInfo()["features"]
    ]


def _assess_and_score(geometry, event_type, event_date, season_window=None):
    result = assess(geometry, event_type, event_date, season_window)
    result.update(
        scoring.score_assessment(event_type, result["metrics"], result["plot_stats"]["area_pixels"])
    )
    return result


def _summary(result):
    m = result["metrics"]
    return (
        f"score={result['score']['damage_score']} ({result['score']['damage_level']}), "
        f"confidence={result['confidence']['level']}, flood={m['flood_fraction']}, "
        f"ndvi_loss={m['ndvi_loss']}, rain_deficit={m['rain_deficit']}, crop={m['crop_fraction']}"
    )


# --- Flood ------------------------------------------------------------------------


def find_flood_peak(aoi, cropland):
    """Return (peak_date, {date: flooded share of cropland}) from Sentinel-1."""
    search = _s1_vv(aoi, *FLOOD_SEARCH)
    dates = sorted({ms_to_date(t) for t in search.aggregate_array("system:time_start").getInfo()})
    if not dates:
        raise SystemExit("No Sentinel-1 images found in the flood search window.")

    dry = _s1_vv(aoi, *FLOOD_DRY_REFERENCE)
    is_crop = cropland.gt(0.5)
    shares = {}
    for d in dates:
        day = _s1_vv(aoi, d.isoformat(), (d + timedelta(days=1)).isoformat())
        flooded = (
            flood_mask(dry, day)
            .setDefaultProjection(ee.Projection(UTM_43N).atScale(config.SCALE_M))
            .updateMask(is_crop)
        )
        shares[d.isoformat()] = flooded.reduceRegion(
            ee.Reducer.mean(), aoi, scale=CELL_M, crs=UTM_43N, maxPixels=1e9, bestEffort=True
        ).get("flooded")

    values = ee.Dictionary(shares).getInfo()
    values = {d: v for d, v in values.items() if v is not None}
    print("Flooded share of cropland by radar date:")
    for d, v in sorted(values.items()):
        print(f"  {d}: {v:.1%}")
    peak = max(values, key=values.get)
    return date.fromisoformat(peak), values


def find_flood_plots():
    aoi = ee.Geometry.Rectangle(FLOOD_AOI)
    cropland = _cropland(aoi, *FLOOD_CROPLAND_YEAR)
    peak, _ = find_flood_peak(aoi, cropland)
    # Put the event date 2 days before the peak, so the radar "post" window
    # (E to E+10) includes the peak and the "pre" window ends before it.
    event_date = peak - timedelta(days=2)
    print(f"Flood peak on {peak}; using event date {event_date}")

    flooded = flood_mask(
        _s1_vv(aoi, *FLOOD_DRY_REFERENCE),
        _s1_vv(aoi, peak.isoformat(), (peak + timedelta(days=1)).isoformat()),
    ).reproject(ee.Projection(UTM_43N).atScale(config.SCALE_M))  # fix a 10 m grid before averaging
    cells = _to_cells(flooded.rename("flooded").addBands(cropland.rename("crops")))
    samples = cells.sample(region=aoi, scale=CELL_M, projection=UTM_43N, numPixels=30000, seed=7, geometries=True)

    flooded_cells = _points(
        samples.filter(ee.Filter.And(ee.Filter.gte("crops", 0.7), ee.Filter.gte("flooded", 0.85)))
        .sort("flooded", False)
        .limit(40)
    )
    dry_cells = _points(
        samples.filter(ee.Filter.And(ee.Filter.gte("crops", 0.7), ee.Filter.eq("flooded", 0))).limit(400)
    )
    print(f"{len(flooded_cells)} flooded cropland cells, {len(dry_cells)} dry cropland cells")
    if not flooded_cells or not dry_cells:
        raise SystemExit("Not enough candidate cells. Try widening FLOOD_AOI or lowering thresholds.")

    plots = []
    picked = []
    for point, props in flooded_cells:
        if len(plots) == 3:
            break
        if any(_distance_km(point, p) < 2 for p in picked):
            continue  # spread the demo plots out
        geometry = _square(*point)
        result = _assess_and_score(geometry, "flood", event_date.isoformat())
        print(f"  flood candidate {point}: {_summary(result)}")
        m = result["metrics"]
        if (m["flood_fraction"] or 0) >= 0.5 and (m["ndvi_loss"] or 0) >= 0.2:
            picked.append(point)
            plots.append(
                {
                    "id": f"flood{len(plots) + 1}",
                    "label": f"Flooded field near the Krishna river #{len(plots) + 1}",
                    "event_type": "flood",
                    "event_date": event_date.isoformat(),
                    "crop": "sugarcane",
                    "crop_note": "Assumed for the demo: sugarcane dominates this stretch of the Krishna. Crop type is not verified.",
                    "control": False,
                    "geometry": geometry,
                    "check": _summary(result),
                }
            )

    if not plots:
        raise SystemExit("No flood candidate passed the assessment check.")

    # Control: nearest dry cropland cell 3-15 km from the first flood plot.
    anchor = picked[0]
    dry_sorted = sorted(
        (c for c in dry_cells if 3 <= _distance_km(c[0], anchor) <= 15),
        key=lambda c: _distance_km(c[0], anchor),
    )
    for point, _ in dry_sorted[:6]:
        geometry = _square(*point)
        result = _assess_and_score(geometry, "flood", event_date.isoformat())
        print(f"  control candidate {point}: {_summary(result)}")
        m = result["metrics"]
        if (m["flood_fraction"] or 0) < 0.1 and (m["ndvi_loss"] or 0) < 0.2:
            plots.append(
                {
                    "id": "control1",
                    "label": "Unflooded field nearby (control)",
                    "event_type": "flood",
                    "event_date": event_date.isoformat(),
                    "crop": "sugarcane",
                    "crop_note": "Assumed for the demo. Crop type is not verified.",
                    "control": True,
                    "geometry": geometry,
                    "check": _summary(result),
                }
            )
            break
    else:
        print("WARNING: no control candidate passed the check; no control plot saved.")

    return plots, {"peak_date": peak.isoformat(), "event_date": event_date.isoformat()}


# --- Drought ----------------------------------------------------------------------


def _ndvi_median(region, year):
    start = f"{year}-{DROUGHT_NDVI_WINDOW[0]}"
    end = f"{year}-{DROUGHT_NDVI_WINDOW[1]}"

    def ndvi(img):
        clear = img.select(config.CS_BAND).gte(config.CS_CLEAR_THRESHOLD)
        return img.updateMask(clear).normalizedDifference(["B8", "B4"]).rename("NDVI")

    return (
        ee.ImageCollection(config.S2_COLLECTION)
        .filterBounds(region)
        .filterDate(start, ee.Date(end).advance(1, "day"))
        .linkCollection(ee.ImageCollection(config.CS_PLUS_COLLECTION), [config.CS_BAND])
        .filter(ee.Filter.listContains("system:band_names", config.CS_BAND))
        .map(ndvi)
        .median()
        .setDefaultProjection(ee.Projection(UTM_43N).atScale(config.SCALE_M))
    )


def find_drought_plot():
    aoi = ee.Geometry.Rectangle(DROUGHT_AOI)
    event_year = int(DROUGHT_EVENT_DATE[:4])
    now = _ndvi_median(aoi, event_year)
    baseline = ee.ImageCollection([_ndvi_median(aoi, y) for y in DROUGHT_BASELINE_YEARS]).mean()
    baseline = baseline.setDefaultProjection(ee.Projection(UTM_43N).atScale(config.SCALE_M))
    cropland = _cropland(aoi, f"{event_year - 1}-06-01", f"{event_year}-05-31")

    cells = _to_cells(
        now.rename("now").addBands(baseline.rename("baseline")).addBands(cropland.rename("crops"))
    )
    loss = cells.select("baseline").subtract(cells.select("now")).divide(cells.select("baseline").max(0.1))
    samples = cells.addBands(loss.rename("loss")).sample(
        region=aoi, scale=CELL_M, projection=UTM_43N, numPixels=30000, seed=11, geometries=True
    )
    candidates = _points(
        samples.filter(ee.Filter.And(ee.Filter.gte("crops", 0.7), ee.Filter.gte("baseline", 0.45)))
        .sort("loss", False)
        .limit(8)
    )
    print(f"{len(candidates)} drought candidates")

    for point, props in candidates:
        geometry = _square(*point)
        result = _assess_and_score(geometry, "drought", DROUGHT_EVENT_DATE, DROUGHT_SEASON)
        print(f"  drought candidate {point}: {_summary(result)}")
        m = result["metrics"]
        if (m["ndvi_loss"] or 0) >= 0.3 and (m["rain_deficit"] or 0) >= 0.15:
            return {
                "id": "drought1",
                "label": "Drought-hit field, 2023 kharif season",
                "event_type": "drought",
                "event_date": DROUGHT_EVENT_DATE,
                "season_window": DROUGHT_SEASON,
                "crop": "maize",
                "crop_note": "Assumed for the demo. Crop type is not verified.",
                "control": False,
                "geometry": geometry,
                "check": _summary(result),
            }
    print("WARNING: no drought candidate passed the check; no drought plot saved.")
    return None


def main():
    init_ee()
    plots, flood_info = find_flood_plots()
    drought = find_drought_plot()
    if drought:
        plots.append(drought)

    DEMO_PLOTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEMO_PLOTS_PATH.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "method": "scripts/find_demo_plots.py",
                "flood": flood_info,
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
