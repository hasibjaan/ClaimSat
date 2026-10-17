"""All Earth Engine logic for ClaimSat.

One satellite, Sentinel-2, for every damage measurement:
  * "before" = the cloud-free image closest to 1 week before the event,
  * "now"    = the most recent cloud-free image of the plot (up to 14 days after).
From each image we read crop health (NDVI) and standing water (MNDWI).
`weather_facts()` reads ERA5-Land weather, used only to verify a claim.

Run a demo plot from the command line:
    python -m app.ee_analysis --demo flood1 [--thumbs out_dir]
"""

import argparse
import json
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import ee
import google.auth
import requests

from app import config, scoring

DEMO_PLOTS_PATH = Path(__file__).resolve().parent.parent / "demo_cache" / "demo_plots.json"
S2_BANDS = ["B2", "B3", "B4", "B8", "B11"]
RAIN_BAND = "total_precipitation_sum"   # metres per day
TMAX_BAND = "temperature_2m_max"        # kelvin

_init_lock = threading.Lock()
_initialized = False


def init_ee():
    """Initialise Earth Engine once per process, using Application Default Credentials."""
    global _initialized
    with _init_lock:
        if _initialized:
            return
        credentials, _ = google.auth.default(scopes=config.EE_SCOPES)
        ee.Initialize(credentials=credentials, project=config.GCP_PROJECT or None)
        _initialized = True


def check():
    """Health check: run a trivial server-side computation."""
    init_ee()
    value = ee.Number(1).add(1).getInfo()
    if value != 2:
        raise RuntimeError(f"Unexpected Earth Engine result: {value}")
    return "Earth Engine reachable"


# --- Dates and windows (pure Python) -------------------------------------------


def shift_years(d, years):
    """Same calendar day `years` later (Feb 29 falls back to Feb 28)."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def _window(start, end):
    return {"start": start.isoformat(), "end": end.isoformat()}


def _offset_window(event_date, offsets, today):
    start = event_date + timedelta(days=offsets[0])
    end = min(event_date + timedelta(days=offsets[1]), today)
    return _window(start, max(start, end))


def build_windows(event_date, today=None):
    """Inclusive date windows. End dates are clipped to today."""
    today = today or date.today()
    return {
        "before": _offset_window(event_date, config.BEFORE_SEARCH, today),
        "before_target": (event_date + timedelta(days=config.BEFORE_TARGET_DAY)).isoformat(),
        "now": _offset_window(event_date, config.NOW_SEARCH, today),
        "series": _offset_window(event_date, config.SERIES_WINDOW, today),
    }


def weather_windows(event_date):
    d = lambda n: (event_date + timedelta(days=n)).isoformat()  # noqa: E731
    return {
        "event_local": {"start": d(-3), "end": d(1)},
        "week_region": {"start": d(-7), "end": d(0)},
        "month_local": {"start": d(-30), "end": d(0)},
    }


# --- Post-processing helpers (pure Python) -------------------------------------


def ms_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


def unique_dates(timestamps_ms):
    """Sorted unique ISO dates (Sentinel scenes often come in several tiles per day)."""
    return sorted({ms_to_date(t).isoformat() for t in timestamps_ms or []})


def daily_means(timestamps_ms, values):
    """Average values that fall on the same day. Returns [(date, mean)] sorted by date."""
    by_day = defaultdict(list)
    for t, v in zip(timestamps_ms or [], values or []):
        if v is not None:
            by_day[ms_to_date(t)].append(v)
    return sorted((d, sum(vs) / len(vs)) for d, vs in by_day.items())


def build_series(event_date, timestamps_ms, values):
    """Crop health (NDVI) per clear image, for the chart."""
    return {
        "this_year": [
            {"day_offset": (d - event_date).days, "date": d.isoformat(), "ndvi": round(v, 3)}
            for d, v in daily_means(timestamps_ms, values)
        ],
        "baseline": [],
    }


def _round(value, digits=3):
    return None if value is None else round(value, digits)


def _mean_or_none(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


# --- Earth Engine building blocks ----------------------------------------------


def _ee_range(window):
    """Inclusive window -> EE (start, end) with an exclusive end date."""
    return ee.Date(window["start"]), ee.Date(window["end"]).advance(1, "day")


def _empty(bands):
    """A fully masked image with the given bands, so empty windows give nulls, not errors."""
    return ee.Image.constant([0] * len(bands)).rename(bands).updateMask(ee.Image(0))


def _s2_masked(geom, window):
    """Sentinel-2 images in the window, cloudy pixels masked out."""
    start, end = _ee_range(window)

    def mask(img):
        return img.updateMask(img.select(config.CS_BAND).gte(config.CS_CLEAR_THRESHOLD))

    return (
        ee.ImageCollection(config.S2_COLLECTION)
        .filterBounds(geom)
        .filterDate(start, end)
        .linkCollection(ee.ImageCollection(config.CS_PLUS_COLLECTION), [config.CS_BAND])
        .filter(ee.Filter.listContains("system:band_names", config.CS_BAND))
        .map(mask)
    )


def _with_clear_fraction(collection, geom):
    """Tag each image with the share of plot pixels that are cloud-free."""

    def tag(img):
        clear = img.select(config.CS_BAND).mask().rename("clear")
        fraction = clear.reduceRegion(ee.Reducer.mean(), geom, config.SCALE_M).get("clear")
        return img.set("clear_fraction", fraction)

    return collection.map(tag)


def pick_image(geom, window, target_date=None):
    """One clear image: the one closest to target_date, or else the latest.

    Returns a masked placeholder (all-null measurements) if there is none.
    """
    clear = _with_clear_fraction(_s2_masked(geom, window).select(S2_BANDS + [config.CS_BAND]), geom).filter(
        ee.Filter.gte("clear_fraction", config.CLEAR_IMAGE_MIN_FRACTION)
    )
    if target_date:
        target_ms = ee.Date(target_date).millis()
        ordered = clear.map(
            lambda img: img.set("distance", ee.Number(img.get("system:time_start")).subtract(target_ms).abs())
        ).sort("distance")
    else:
        ordered = clear.sort("system:time_start", False)
    placeholder = ee.ImageCollection([_empty(S2_BANDS + [config.CS_BAND])])
    return ee.Image(ordered.merge(placeholder).first())


def ndvi(img):
    return img.normalizedDifference(["B8", "B4"]).rename("NDVI")


def water(img):
    """1 where the pixel is open water (MNDWI = green vs short-wave infrared)."""
    return img.normalizedDifference(["B3", "B11"]).gt(config.WATER_MNDWI_THRESHOLD).rename("water")


def _plot_mean(image, geom, band):
    return image.reduceRegion(ee.Reducer.mean(), geom, config.SCALE_M).get(band)


def _series_values(collection, geom):
    """Per-image mean NDVI over the plot, for clear images only."""
    clear = _with_clear_fraction(collection, geom).filter(
        ee.Filter.gte("clear_fraction", config.CLEAR_IMAGE_MIN_FRACTION)
    )
    features = ee.FeatureCollection(
        clear.map(lambda img: ee.Feature(None, {"t": img.get("system:time_start"), "ndvi": _plot_mean(ndvi(img), geom, "NDVI")}))
    ).filter(ee.Filter.notNull(["ndvi"]))
    return {"t": features.aggregate_array("t"), "ndvi": features.aggregate_array("ndvi")}


# --- Assessment ------------------------------------------------------------------


def assess(geometry_geojson, event_type, event_date):
    """Measure the plot: 1 week before vs now. One getInfo() call."""
    if event_type not in config.EVENT_TYPES:
        raise ValueError(f"event_type must be one of {config.EVENT_TYPES}")
    if isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)

    init_ee()
    geom = ee.Geometry(geometry_geojson)
    windows = build_windows(event_date)
    before = pick_image(geom, windows["before"], windows["before_target"])
    now = pick_image(geom, windows["now"])

    request = {
        "ndvi_before": _plot_mean(ndvi(before), geom, "NDVI"),
        "ndvi_now": _plot_mean(ndvi(now), geom, "NDVI"),
        "water_before": _plot_mean(water(before), geom, "water"),
        "water_now": _plot_mean(water(now), geom, "water"),
        # New water: wet now, dry before (only pixels clear in both images count).
        "flood_fraction": _plot_mean(water(now).And(water(before).Not()).rename("new"), geom, "new"),
        "before_t": before.get("system:time_start"),
        "now_t": now.get("system:time_start"),
        "before_clear": before.get("clear_fraction"),
        "now_clear": now.get("clear_fraction"),
        "area_m2": geom.area(1),
        "area_pixels": ee.Image.constant(1).rename("px").reduceRegion(ee.Reducer.count(), geom, config.SCALE_M).get("px"),
        "centroid": geom.centroid(1).coordinates(),
        "series": _series_values(_s2_masked(geom, windows["series"]), geom),
    }
    raw = ee.Dictionary(request).getInfo()
    return shape_result(raw, event_type, event_date, windows)


def shape_result(raw, event_type, event_date, windows):
    """Turn the raw Earth Engine numbers into the result shape (pure Python)."""
    before_date = ms_to_date(raw["before_t"]).isoformat() if raw.get("before_t") else None
    now_date = ms_to_date(raw["now_t"]).isoformat() if raw.get("now_t") else None
    loss = scoring.ndvi_loss(raw.get("ndvi_now"), raw.get("ndvi_before"))
    metrics = {
        "ndvi_before": _round(raw.get("ndvi_before")),
        "ndvi_now": _round(raw.get("ndvi_now")),
        "ndvi_loss": _round(loss),
        "water_before": _round(raw.get("water_before")),
        "water_now": _round(raw.get("water_now")),
        "flood_fraction": _round(raw.get("flood_fraction")),
        "before_image_date": before_date,
        "now_image_date": now_date,
        "before_clear": _round(raw.get("before_clear"), 2),
        "now_clear": _round(raw.get("now_clear"), 2),
        "days_between": (date.fromisoformat(now_date) - date.fromisoformat(before_date)).days
        if before_date and now_date
        else None,
    }
    lng, lat = raw["centroid"]
    return {
        "event": {"type": event_type, "date": event_date.isoformat(), "windows": windows},
        "plot_stats": {
            "area_ha": round(raw["area_m2"] / 10_000, 2),
            "area_pixels": raw["area_pixels"],
            "centroid": {"lat": round(lat, 6), "lng": round(lng, 6)},
        },
        "metrics": metrics,
        "acquisitions": {"before": before_date, "now": now_date, "satellite": "Sentinel-2"},
        "ndvi_series": build_series(event_date, raw["series"]["t"], raw["series"]["ndvi"]),
    }


# --- Weather (verification only) ----------------------------------------------------


def weather_facts(geometry_geojson, event_type, event_date):
    """ERA5-Land rainfall and heat around the event, and what is normal for those dates."""
    if isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)
    init_ee()
    point = ee.Geometry(geometry_geojson).centroid(1)
    region = point.buffer(config.WEATHER_REGION_KM * 1000)
    era5 = ee.ImageCollection(config.ERA5_DAILY)
    windows = weather_windows(event_date)

    def reduce(band, window, area, how, shift=0):
        start = shift_years(date.fromisoformat(window["start"]), shift)
        end = shift_years(date.fromisoformat(window["end"]), shift)
        images = era5.filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat()).select(band)
        combined = getattr(images.merge(ee.ImageCollection([_empty([band])])), how)()
        return combined.reduceRegion(ee.Reducer.mean(), area, config.ERA5_SCALE_M).get(band)

    request = {
        "rain_event_local": reduce(RAIN_BAND, windows["event_local"], point, "sum"),
        "max_daily_local": reduce(RAIN_BAND, {"start": windows["week_region"]["start"], "end": windows["event_local"]["end"]}, point, "max"),
        "rain_week_region": reduce(RAIN_BAND, windows["week_region"], region, "sum"),
        "rain_month_local": reduce(RAIN_BAND, windows["month_local"], point, "sum"),
        "tmax_week_local": reduce(TMAX_BAND, windows["week_region"], point, "max"),
        "normal_week_region": [reduce(RAIN_BAND, windows["week_region"], region, "sum", -k) for k in range(1, config.WEATHER_NORMAL_YEARS + 1)],
        "normal_month_local": [reduce(RAIN_BAND, windows["month_local"], point, "sum", -k) for k in range(1, config.WEATHER_NORMAL_YEARS + 1)],
        "days_with_data": era5.filterDate(windows["week_region"]["start"], (event_date + timedelta(days=2)).isoformat()).size(),
    }
    raw = ee.Dictionary(request).getInfo()
    return shape_weather(raw, windows)


def shape_weather(raw, windows):
    mm = lambda v: None if v is None else round(v * 1000, 1)  # noqa: E731
    normal_week = _mean_or_none(raw.get("normal_week_region") or [])
    normal_month = _mean_or_none(raw.get("normal_month_local") or [])
    return {
        "rain_event_local_mm": mm(raw.get("rain_event_local")),
        "max_daily_rain_local_mm": mm(raw.get("max_daily_local")),
        "rain_week_region_mm": mm(raw.get("rain_week_region")),
        "normal_week_region_mm": mm(normal_week),
        "rain_month_local_mm": mm(raw.get("rain_month_local")),
        "normal_month_local_mm": mm(normal_month),
        "max_temp_c": None if raw.get("tmax_week_local") is None else round(raw["tmax_week_local"] - 273.15, 1),
        "days_with_data": raw.get("days_with_data", 0),
        "region_km": config.WEATHER_REGION_KM,
        "windows": windows,
        "source": "ERA5-Land daily weather (ECMWF / Copernicus)",
    }


# --- Thumbnails ------------------------------------------------------------------

RGB_VIS = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.2}
NDVI_VIS = {"min": 0, "max": 0.9, "palette": ["8c510a", "d8b365", "f6e8c3", "c7e9c0", "41ab5d", "006d2c"]}
NO_DATA_GREY = 210


def thumbnails(geometry_geojson, event_type, event_date, dimensions=512):
    """Evidence PNGs from the same two images used for the measurements.

    Returns {name: png_bytes}. Cloud-masked areas show as light grey.
    """
    if isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)
    init_ee()
    geom = ee.Geometry(geometry_geojson)
    windows = build_windows(event_date)
    region = geom.buffer(300).bounds()
    before = pick_image(geom, windows["before"], windows["before_target"])
    now = pick_image(geom, windows["now"])
    outline = ee.Image().byte().paint(ee.FeatureCollection([ee.Feature(geom)]), 1, 2).visualize(palette=["ffd400"])

    def finish(vis):
        return vis.unmask(NO_DATA_GREY).blend(outline)

    now_rgb = now.visualize(**RGB_VIS)
    new_water = water(now).And(water(before).Not()).selfMask().visualize(palette=["1e88e5"], opacity=0.75)
    images = {
        "true_colour_before": finish(before.visualize(**RGB_VIS)),
        "true_colour_now": finish(now_rgb),
        "ndvi_now": finish(ndvi(now).visualize(**NDVI_VIS)),
        "flood_mask": now_rgb.unmask(NO_DATA_GREY).blend(new_water).blend(outline),
    }
    params = {"region": region, "dimensions": dimensions, "format": "png"}

    def render(item):
        name, image = item
        response = requests.get(image.getThumbURL(params), timeout=90)
        response.raise_for_status()
        return name, response.content

    with ThreadPoolExecutor(max_workers=len(images)) as pool:
        return dict(pool.map(render, images.items()))


# --- Command line ----------------------------------------------------------------


def load_demo_plot(plot_id):
    if not DEMO_PLOTS_PATH.exists():
        raise SystemExit(f"{DEMO_PLOTS_PATH} not found. Run `python -m scripts.find_demo_plots` first.")
    plots = json.loads(DEMO_PLOTS_PATH.read_text())["plots"]
    for plot in plots:
        if plot["id"] == plot_id:
            return plot
    raise SystemExit(f"No demo plot '{plot_id}'. Available: {[p['id'] for p in plots]}")


def main():
    parser = argparse.ArgumentParser(description="Run a ClaimSat assessment.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", help="demo plot id from demo_cache/demo_plots.json")
    source.add_argument("--geojson", help="path to a GeoJSON Polygon geometry")
    parser.add_argument("--event-type", choices=config.EVENT_TYPES)
    parser.add_argument("--date", help="event date, YYYY-MM-DD")
    parser.add_argument("--thumbs", help="directory to save thumbnail PNGs into")
    args = parser.parse_args()

    if args.demo:
        plot = load_demo_plot(args.demo)
        geometry, event_type, event_date = plot["geometry"], plot["event_type"], plot["event_date"]
    else:
        if not (args.event_type and args.date):
            parser.error("--geojson needs --event-type and --date")
        geometry = json.loads(Path(args.geojson).read_text())
        event_type, event_date = args.event_type, args.date

    started = time.perf_counter()
    result = assess(geometry, event_type, event_date)
    result.update(scoring.score_assessment(event_type, result["metrics"], result["plot_stats"]["area_pixels"]))
    result["weather"] = weather_facts(geometry, event_type, event_date)
    print(json.dumps(result, indent=2))
    print(f"\nAssessment + weather took {time.perf_counter() - started:.1f}s")

    if args.thumbs:
        out_dir = Path(args.thumbs)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, png in thumbnails(geometry, event_type, event_date).items():
            (out_dir / f"{name}.png").write_bytes(png)
        print(f"Thumbnails saved to {out_dir}")


if __name__ == "__main__":
    main()
