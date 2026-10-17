"""All Earth Engine logic for ClaimSat.

`assess()` builds the whole computation server-side and fetches it with a
single getInfo() call. `thumbnails()` renders the PNG evidence images.

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
    return _window(start, end)


def build_windows(event_type, event_date, season_window=None, today=None):
    """Inclusive date windows for each part of the analysis.

    End dates are clipped to today, so a recent event simply has fewer images.
    """
    today = today or date.today()
    if event_type == "drought":
        if season_window:
            season_start = date.fromisoformat(season_window["start"])
            season_end = date.fromisoformat(season_window["end"])
        else:
            (sm, sd), (em, ed) = config.DROUGHT_SEASON_DEFAULT
            season_start = date(event_date.year, sm, sd)
            season_end = date(event_date.year, em, ed)
        windows = {
            "before": _window(
                season_start - timedelta(days=config.DROUGHT_BEFORE_DAYS),
                season_start - timedelta(days=1),
            ),
            "after": _window(season_start, min(season_end, today)),
        }
    else:
        windows = {
            "before": _offset_window(event_date, config.BEFORE_WINDOW, today),
            "after": _offset_window(event_date, config.AFTER_WINDOW, today),
        }
        if event_type == "flood":
            windows["radar_pre"] = _offset_window(event_date, config.RADAR_PRE_WINDOW, today)
            windows["radar_post"] = _offset_window(event_date, config.RADAR_POST_WINDOW, today)

    windows["series"] = _offset_window(event_date, config.SERIES_WINDOW, today)
    windows["baseline_years"] = [event_date.year - k for k in range(config.BASELINE_YEARS, 0, -1)]
    return windows


def _shift_window(window, years):
    return _window(
        shift_years(date.fromisoformat(window["start"]), years),
        shift_years(date.fromisoformat(window["end"]), years),
    )


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


def build_series(event_date, this_year, baseline_by_year):
    """Shape the NDVI time series for the chart.

    this_year: (timestamps_ms, values) for the event year.
    baseline_by_year: {years_back: (timestamps_ms, values)}.
    Baseline points are aligned by day offset from the event date and averaged
    in SERIES_BIN_DAYS-day bins.
    """
    series_this_year = [
        {"day_offset": (d - event_date).days, "date": d.isoformat(), "ndvi": round(v, 3)}
        for d, v in daily_means(*this_year)
    ]

    bins = defaultdict(list)
    for years_back, (timestamps, values) in baseline_by_year.items():
        shifted_event = shift_years(event_date, -years_back)
        for d, v in daily_means(timestamps, values):
            offset = (d - shifted_event).days
            bins[round(offset / config.SERIES_BIN_DAYS) * config.SERIES_BIN_DAYS].append(v)
    series_baseline = [
        {"day_offset": offset, "ndvi": round(sum(vs) / len(vs), 3)}
        for offset, vs in sorted(bins.items())
    ]
    return {"this_year": series_this_year, "baseline": series_baseline}


def _round(value, digits=3):
    return None if value is None else round(value, digits)


# --- Earth Engine building blocks ----------------------------------------------


def _ee_range(window):
    """Inclusive window -> EE (start, end) with an exclusive end date."""
    return ee.Date(window["start"]), ee.Date(window["end"]).advance(1, "day")


def _empty(bands):
    """A fully masked image with the given bands.

    Merged into collections before compositing, so an empty window yields
    masked pixels (and null means) instead of an error.
    """
    return ee.Image.constant([0] * len(bands)).rename(bands).updateMask(ee.Image(0))


def _s2_masked(geom, window):
    """Sentinel-2 images in the window with cloudy pixels masked out."""
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


def _ndvi(img):
    return (
        img.normalizedDifference(["B8", "B4"])
        .rename("NDVI")
        .set({"system:time_start": img.get("system:time_start")})
    )


def _ndvi_composite(collection):
    return collection.map(_ndvi).merge(ee.ImageCollection([_empty(["NDVI"])])).median()


def _rgb_composite(collection):
    bands = ["B4", "B3", "B2"]
    return collection.select(bands).merge(ee.ImageCollection([_empty(bands)])).median()


def _plot_mean(image, geom, band):
    return image.reduceRegion(ee.Reducer.mean(), geom, config.SCALE_M).get(band)


def _series_values(collection, geom):
    """Per-image mean NDVI over the plot, for clear images only."""
    clear = _with_clear_fraction(collection, geom).filter(
        ee.Filter.gte("clear_fraction", config.CLEAR_IMAGE_MIN_FRACTION)
    )

    def to_feature(img):
        return ee.Feature(
            None,
            {
                "t": img.get("system:time_start"),
                "ndvi": _plot_mean(_ndvi(img), geom, "NDVI"),
            },
        )

    features = ee.FeatureCollection(clear.map(to_feature)).filter(ee.Filter.notNull(["ndvi"]))
    return {"t": features.aggregate_array("t"), "ndvi": features.aggregate_array("ndvi")}


def _s1(geom, window):
    start, end = _ee_range(window)
    return (
        ee.ImageCollection(config.S1_COLLECTION)
        .filterBounds(geom)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .select("VV")
    )


def _permanent_water():
    occurrence = ee.Image(config.GSW_IMAGE).select("occurrence").unmask(0)
    return occurrence.gt(config.PERMANENT_WATER_OCCURRENCE)


def flood_mask(pre_collection, post_collection):
    """1 where the land newly looks like open water after the event, else 0.

    Water reflects radar away from the satellite, so flooded fields turn dark
    (low VV backscatter). Requiring a drop versus before the event, and
    excluding permanent rivers and lakes, removes most false positives.
    """
    empty = ee.ImageCollection([_empty(["VV"])])
    pre = pre_collection.merge(empty).median()
    post = post_collection.merge(empty).min()
    return (
        post.lt(config.FLOOD_VV_THRESHOLD_DB)
        .And(post.subtract(pre).lt(config.FLOOD_CHANGE_THRESHOLD_DB))
        .And(_permanent_water().Not())
        .rename("flooded")
    )


def _crop_fraction_image(geom, event_date):
    """Mean Dynamic World crop probability over the 12 months before the event."""
    start = ee.Date(event_date.isoformat()).advance(-config.CROPLAND_LOOKBACK_DAYS, "day")
    return (
        ee.ImageCollection(config.DYNAMIC_WORLD_COLLECTION)
        .filterBounds(geom)
        .filterDate(start, ee.Date(event_date.isoformat()))
        .select("crops")
        .merge(ee.ImageCollection([_empty(["crops"])]))
        .mean()
    )


def _crop_fraction(geom, event_date):
    return _plot_mean(_crop_fraction_image(geom, event_date), geom, "crops")


def _season_rain(point, window):
    start, end = _ee_range(window)
    total = (
        ee.ImageCollection(config.CHIRPS_COLLECTION)
        .filterDate(start, end)
        .select("precipitation")
        .merge(ee.ImageCollection([_empty(["precipitation"])]))
        .sum()
    )
    return total.reduceRegion(ee.Reducer.mean(), point, config.CHIRPS_SCALE_M).get("precipitation")


# --- Assessment ------------------------------------------------------------------


def assess(geometry_geojson, event_type, event_date, season_window=None):
    """Measure damage for one plot.

    Returns event windows, metrics, image acquisition dates, the NDVI series
    and plot stats. Scoring is done separately in app.scoring.
    """
    if event_type not in config.EVENT_TYPES:
        raise ValueError(f"event_type must be one of {config.EVENT_TYPES}")
    if isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)

    init_ee()
    geom = ee.Geometry(geometry_geojson)
    windows = build_windows(event_type, event_date, season_window)

    before = _s2_masked(geom, windows["before"])
    after = _s2_masked(geom, windows["after"])
    clear_filter = ee.Filter.gte("clear_fraction", config.CLEAR_IMAGE_MIN_FRACTION)
    clear_before = _with_clear_fraction(before, geom).filter(clear_filter)
    clear_after = _with_clear_fraction(after, geom).filter(clear_filter)

    baseline_after = ee.ImageCollection(
        [
            _ndvi_composite(_s2_masked(geom, _shift_window(windows["after"], -k)))
            for k in range(1, config.BASELINE_YEARS + 1)
        ]
    ).mean()

    series = {"this_year": _series_values(_s2_masked(geom, windows["series"]), geom)}
    for k in range(1, config.BASELINE_YEARS + 1):
        series[f"minus_{k}"] = _series_values(
            _s2_masked(geom, _shift_window(windows["series"], -k)), geom
        )

    request = {
        "ndvi_before": _plot_mean(_ndvi_composite(before), geom, "NDVI"),
        "ndvi_after": _plot_mean(_ndvi_composite(after), geom, "NDVI"),
        "ndvi_baseline_after": _plot_mean(baseline_after, geom, "NDVI"),
        "crop_fraction": _crop_fraction(geom, event_date),
        "clear_before_t": clear_before.aggregate_array("system:time_start"),
        "clear_after_t": clear_after.aggregate_array("system:time_start"),
        "area_m2": geom.area(1),
        "area_pixels": ee.Image.constant(1)
        .rename("px")
        .reduceRegion(ee.Reducer.count(), geom, config.SCALE_M)
        .get("px"),
        "centroid": geom.centroid(1).coordinates(),
        "series": series,
    }

    if event_type == "flood":
        pre = _s1(geom, windows["radar_pre"])
        post = _s1(geom, windows["radar_post"])
        request["flood_fraction"] = _plot_mean(flood_mask(pre, post), geom, "flooded")
        request["s1_pre_t"] = pre.aggregate_array("system:time_start")
        request["s1_post_t"] = post.aggregate_array("system:time_start")

    if event_type == "drought":
        point = geom.centroid(1)
        request["season_rain"] = _season_rain(point, windows["after"])
        request["baseline_rain"] = [
            _season_rain(point, _shift_window(windows["after"], -k))
            for k in range(1, config.RAIN_BASELINE_YEARS + 1)
        ]

    raw = ee.Dictionary(request).getInfo()
    return _shape_result(raw, event_type, event_date, windows)


def _shape_result(raw, event_type, event_date, windows):
    s2_before = unique_dates(raw["clear_before_t"])
    s2_after = unique_dates(raw["clear_after_t"])
    s1_pre = unique_dates(raw.get("s1_pre_t"))
    s1_post = unique_dates(raw.get("s1_post_t"))

    season_rain = raw.get("season_rain")
    baseline_values = [v for v in raw.get("baseline_rain") or [] if v is not None]
    baseline_rain = sum(baseline_values) / len(baseline_values) if baseline_values else None

    metrics = {
        "ndvi_before": _round(raw["ndvi_before"]),
        "ndvi_after": _round(raw["ndvi_after"]),
        "ndvi_baseline_after": _round(raw["ndvi_baseline_after"]),
        "ndvi_loss": _round(scoring.ndvi_loss(raw["ndvi_after"], raw["ndvi_baseline_after"])),
        "flood_fraction": _round(raw.get("flood_fraction")),
        "rain_deficit": _round(scoring.rain_deficit(season_rain, baseline_rain)),
        "season_rain_mm": _round(season_rain, 1),
        "baseline_rain_mm": _round(baseline_rain, 1),
        "crop_fraction": _round(raw["crop_fraction"]),
        "clear_obs_before": len(s2_before),
        "clear_obs_after": len(s2_after),
        "radar_obs_pre": len(s1_pre) if event_type == "flood" else None,
        "radar_obs_post": len(s1_post) if event_type == "flood" else None,
    }

    series = raw["series"]
    ndvi_series = build_series(
        event_date,
        (series["this_year"]["t"], series["this_year"]["ndvi"]),
        {
            k: (series[f"minus_{k}"]["t"], series[f"minus_{k}"]["ndvi"])
            for k in range(1, config.BASELINE_YEARS + 1)
        },
    )

    lng, lat = raw["centroid"]
    return {
        "event": {"type": event_type, "date": event_date.isoformat(), "windows": windows},
        "plot_stats": {
            "area_ha": round(raw["area_m2"] / 10_000, 2),
            "area_pixels": raw["area_pixels"],
            "centroid": {"lat": round(lat, 6), "lng": round(lng, 6)},
        },
        "metrics": metrics,
        "acquisitions": {
            "s2_before": s2_before,
            "s2_after": s2_after,
            "s1_pre": s1_pre,
            "s1_post": s1_post,
        },
        "ndvi_series": ndvi_series,
    }


# --- Thumbnails ------------------------------------------------------------------

RGB_VIS = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.2}
NDVI_VIS = {"min": 0, "max": 0.9, "palette": ["8c510a", "d8b365", "f6e8c3", "c7e9c0", "41ab5d", "006d2c"]}
NO_DATA_GREY = 210


def thumbnails(geometry_geojson, event_type, event_date, season_window=None, dimensions=512):
    """Render evidence PNGs for the plot plus a 300 m buffer.

    Returns {name: png_bytes}. getThumbURL links expire, so callers must store
    the bytes (in GCS for the API). Cloud-masked areas show as light grey.
    """
    if isinstance(event_date, str):
        event_date = date.fromisoformat(event_date)
    init_ee()
    geom = ee.Geometry(geometry_geojson)
    windows = build_windows(event_type, event_date, season_window)
    region = geom.buffer(300).bounds()

    before = _s2_masked(region, windows["before"])
    after = _s2_masked(region, windows["after"])
    outline = (
        ee.Image()
        .byte()
        .paint(ee.FeatureCollection([ee.Feature(geom)]), 1, 2)
        .visualize(palette=["ffd400"])
    )

    def finish(vis):
        return vis.unmask(NO_DATA_GREY).blend(outline)

    before_rgb = _rgb_composite(before).visualize(**RGB_VIS)
    images = {
        "true_colour_before": finish(before_rgb),
        "true_colour_after": finish(_rgb_composite(after).visualize(**RGB_VIS)),
        "ndvi_after": finish(_ndvi_composite(after).visualize(**NDVI_VIS)),
    }
    if event_type == "flood":
        water = flood_mask(_s1(region, windows["radar_pre"]), _s1(region, windows["radar_post"]))
        water_vis = water.selfMask().visualize(palette=["1e88e5"], opacity=0.75)
        images["flood_mask"] = before_rgb.unmask(NO_DATA_GREY).blend(water_vis).blend(outline)

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
        raise SystemExit(
            f"{DEMO_PLOTS_PATH} not found. Run `python -m scripts.find_demo_plots` first."
        )
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
        season_window = plot.get("season_window")
    else:
        if not (args.event_type and args.date):
            parser.error("--geojson needs --event-type and --date")
        geometry = json.loads(Path(args.geojson).read_text())
        event_type, event_date, season_window = args.event_type, args.date, None

    started = time.perf_counter()
    result = assess(geometry, event_type, event_date, season_window)
    result.update(
        scoring.score_assessment(event_type, result["metrics"], result["plot_stats"]["area_pixels"])
    )
    assess_seconds = time.perf_counter() - started
    print(json.dumps(result, indent=2))
    print(f"\nAssessment took {assess_seconds:.1f}s")

    if args.thumbs:
        started = time.perf_counter()
        out_dir = Path(args.thumbs)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, png in thumbnails(geometry, event_type, event_date, season_window).items():
            (out_dir / f"{name}.png").write_bytes(png)
        print(f"Thumbnails saved to {out_dir} in {time.perf_counter() - started:.1f}s")


if __name__ == "__main__":
    main()
