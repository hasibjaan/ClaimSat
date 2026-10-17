"""Runs an assessment end to end and shapes it like shared/sample_result.json."""

import asyncio
import copy
import hashlib
import json
import logging
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app import config, ee_analysis, photo_check, plots, report, scoring, storage, validation, warehouse

log = logging.getLogger("claimsat")

DEMO_CACHE = Path(__file__).resolve().parent.parent / "demo_cache"
SAMPLE_RESULT = Path(__file__).resolve().parent / "sample_demo_result.json"
LIVE_TIMEOUT_DEMO_S = 45   # in DEMO_MODE, fall back to the cache after this
LIVE_TIMEOUT_S = 85        # otherwise give up after this (the web proxy waits 90 s)
CACHE_MATCH_M = 30         # a plot matches a demo plot if centroids are this close
REPORT_TIMEOUT_S = 75      # Gemini may be asked twice (see report.generate)
BIGQUERY_TIMEOUT_S = 10    # recording an assessment must not hold up the user
DASHBOARD_TIMEOUT_S = 35
PHOTO_TIMEOUT_S = 60

ASSET_PATH = re.compile(r"^(asm_[a-z0-9]+)/([a-z_]+)\.png$")
ASSESSMENT_ID = re.compile(r"^asm_[a-z0-9]+$")
PHOTO_PATH = re.compile(r"^(asm_[a-z0-9]+)/(ph_[a-z0-9]+)\.jpg$")


class AnalysisError(RuntimeError):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def evidence_hash(result):
    """SHA-256 over the evidence fields, so later edits to a report are detectable."""
    evidence = {
        "geometry": result["plot"]["geometry"],
        "event": result["event"],
        "metrics": result["metrics"],
        "score": result["score"],
        "acquisitions": result["acquisitions"],
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def build_result(assessment_id, request, area_ha, analysis, images, source):
    scored = scoring.score_assessment(
        analysis["event"]["type"], analysis["metrics"], analysis["plot_stats"]["area_pixels"]
    )
    result = {
        "assessment_id": assessment_id,
        "source": source,
        "created_at": _now(),
        "plot": {
            "plot_id": request["plot_id"],
            "farmer_id": request["farmer_id"],
            "survey_number": request["survey_number"],
            "farmer_name": request["farmer_name"],
            "village": request["village"],
            "crop": request["crop"],
            "area_ha": analysis["plot_stats"]["area_ha"] or round(area_ha, 2),
            "area_pixels": analysis["plot_stats"]["area_pixels"],
            "centroid": analysis["plot_stats"]["centroid"],
            "geometry": request["geometry"],
        },
        "event": analysis["event"],
        "metrics": analysis["metrics"],
        "score": scored["score"],
        "confidence": scored["confidence"],
        "images": {name: f"/api/assets/{assessment_id}/{name}.png" for name in images},
        "acquisitions": analysis["acquisitions"],
        "ndvi_series": analysis["ndvi_series"],
        "report": None,
        "photo_check": None,
    }
    result["evidence_hash"] = evidence_hash(result)
    return result


# --- Demo cache -------------------------------------------------------------------


def _distance_m(a, b):
    lng1, lat1, lng2, lat2 = map(math.radians, [*a, *b])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def demo_plots():
    path = DEMO_CACHE / "demo_plots.json"
    return json.loads(path.read_text())["plots"] if path.exists() else []


def find_cached(geometry, event_type, plot_id=None):
    """A saved result to fall back on in DEMO_MODE.

    First a precomputed result (scripts/precompute_demo.py) for a demo plot at
    this location; else, for the sample seed plots only, the bundled sample
    result, which is marked source=sample and labelled as sample data in the UI.
    """
    centroid = validation.ring_centroid(geometry["coordinates"][0])
    for plot in demo_plots():
        if plot["event_type"] != event_type:
            continue
        plot_centroid = validation.ring_centroid(plot["geometry"]["coordinates"][0])
        if _distance_m(centroid, plot_centroid) <= CACHE_MATCH_M:
            path = DEMO_CACHE / "results" / f"{plot['id']}.json"
            if path.exists():
                cached = json.loads(path.read_text())
                cached["source"] = "cache"
                return cached
    if plot_id and plot_id.startswith("plt_seed_") and event_type == "flood":
        sample = json.loads(SAMPLE_RESULT.read_text())
        sample.pop("_note", None)
        return sample
    return None


def load_asset(path):
    """PNG bytes for /api/assets/{path}, from storage or the demo cache."""
    if not ASSET_PATH.match(path):
        return None
    data = storage.load_bytes(f"assets/{path}")
    if data is None:
        cached = DEMO_CACHE / "assets" / path
        data = cached.read_bytes() if cached.exists() else None
    return data


def load_assessment(assessment_id):
    if not ASSESSMENT_ID.match(assessment_id):
        return None
    result = storage.load_json(f"assessments/{assessment_id}.json")
    if result is None:
        for path in (DEMO_CACHE / "results").glob("*.json"):
            cached = json.loads(path.read_text())
            if cached.get("assessment_id") == assessment_id:
                return cached
    return result


# --- Running an assessment ------------------------------------------------------------


def validate_request(body):
    """The plot comes from the registry by id; any outline sent by the browser is ignored."""
    plot = plots.get_plot(str(body.get("plot_id") or ""))
    if plot is None:
        raise AnalysisError("That plot isn't registered. Ask your agriculture office to register your land.", 404)
    geometry, area_ha = validation.validate_geometry(plot["geometry"])
    event_type, event_date, season = validation.validate_event(
        body.get("event_type"), body.get("event_date"), body.get("season_window")
    )
    return {
        "plot_id": plot["plot_id"],
        "farmer_id": plot["farmer_id"],
        "survey_number": plot["survey_number"],
        "geometry": geometry,
        "area_ha": area_ha,
        "event_type": event_type,
        "event_date": event_date,
        "season_window": season,
        # The crop can change by season, so the farmer may state this season's crop.
        "crop": validation.clean_text(body.get("crop")) or plot.get("crop") or "",
        "farmer_name": plot["farmer_name"],
        "village": plot["village"],
    }


async def run(body):
    """Validate, analyse, store and return one assessment."""
    request = validate_request(body)
    assessment_id = "asm_" + uuid.uuid4().hex[:12]
    args = (request["geometry"], request["event_type"], request["event_date"], request["season_window"])
    timeout = LIVE_TIMEOUT_DEMO_S if config.DEMO_MODE else LIVE_TIMEOUT_S

    try:
        analysis, thumbs = await asyncio.wait_for(
            asyncio.gather(
                asyncio.to_thread(ee_analysis.assess, *args),
                asyncio.to_thread(ee_analysis.thumbnails, *args),
                return_exceptions=True,
            ),
            timeout,
        )
        if isinstance(analysis, BaseException):
            raise analysis
    except Exception as exc:
        timed_out = isinstance(exc, asyncio.TimeoutError)
        log.warning("Live analysis failed (%s): %s", "timeout" if timed_out else type(exc).__name__, exc)
        if config.DEMO_MODE:
            cached = find_cached(request["geometry"], request["event_type"], request["plot_id"])
            if cached:
                log.info("Serving saved %s result %s", cached["source"], cached["assessment_id"])
                return serve_saved(copy.deepcopy(cached), request)
        if timed_out:
            raise AnalysisError("The satellite analysis took too long. Please try again in a minute.", 504) from exc
        raise AnalysisError(
            "We couldn't get satellite images for your field right now. Please try again in a few minutes."
        ) from exc

    images = {}
    if isinstance(thumbs, BaseException):
        log.warning("Thumbnails failed: %s", thumbs)
    else:
        for name, png in thumbs.items():
            try:
                storage.save_bytes(f"assets/{assessment_id}/{name}.png", png, "image/png")
                images[name] = True
            except Exception as exc:
                log.warning("Saving thumbnail %s failed: %s", name, exc)

    result = build_result(assessment_id, request, request["area_ha"], analysis, images, "live")
    try:
        storage.save_json(f"assessments/{assessment_id}.json", result)
    except Exception as exc:
        log.warning("Saving assessment %s failed: %s", assessment_id, exc)
    await record_in_bigquery(result)
    return result


def serve_saved(saved, request):
    """Fit a saved result to the requesting plot, and store it so the report and photo check work."""
    for field in ("plot_id", "farmer_id", "survey_number", "farmer_name", "village", "crop"):
        saved["plot"][field] = request[field]
    if saved["source"] == "sample":
        # The sample's numbers are illustrative; show it on the farmer's own outline.
        saved["plot"]["geometry"] = request["geometry"]
        saved["plot"]["area_ha"] = round(request["area_ha"], 2)
        saved["evidence_hash"] = evidence_hash(saved)
    try:
        storage.save_json(f"assessments/{saved['assessment_id']}.json", saved)
    except Exception as exc:
        log.warning("Saving served result %s failed: %s", saved["assessment_id"], exc)
    return saved


async def record_in_bigquery(result):
    """Best effort: a BigQuery problem is logged, never shown to the user."""
    try:
        await asyncio.wait_for(asyncio.to_thread(warehouse.record_assessment, result), BIGQUERY_TIMEOUT_S)
    except Exception as exc:
        log.warning("Recording %s in BigQuery failed: %s", result["assessment_id"], exc or type(exc).__name__)


# --- Farmer photo ---------------------------------------------------------------------------


async def check_photo(assessment_id, data):
    """Compare an uploaded field photo with the assessment and store the result."""
    assessment = await asyncio.to_thread(load_assessment, assessment_id)
    if assessment is None:
        raise AnalysisError("Assessment not found.", 404)
    try:
        result, jpeg, photo_id = await asyncio.wait_for(
            asyncio.to_thread(photo_check.check, data, assessment), PHOTO_TIMEOUT_S
        )
    except photo_check.PhotoError as exc:
        raise validation.ValidationError(str(exc)) from exc
    except asyncio.TimeoutError as exc:
        raise AnalysisError("Checking the photo took too long. Please try again.", 504) from exc
    except Exception as exc:
        log.warning("Photo check failed for %s: %s", assessment_id, exc)
        raise AnalysisError("We couldn't check the photo right now. Please try again in a few minutes.") from exc

    await asyncio.to_thread(storage.save_bytes, f"photos/{assessment_id}/{photo_id}.jpg", jpeg, "image/jpeg")
    assessment["photo_check"] = result
    try:
        await asyncio.to_thread(storage.save_json, f"assessments/{assessment_id}.json", assessment)
    except Exception as exc:
        log.warning("Saving photo check for %s failed: %s", assessment_id, exc)
    return {"photo_check": result}


def load_photo(path):
    return storage.load_bytes(f"photos/{path}") if PHOTO_PATH.match(path) else None


# --- Dashboard --------------------------------------------------------------------------


async def dashboard_data():
    """Plots with their latest assessment, from BigQuery (or the demo cache in DEMO_MODE)."""
    try:
        rows = await asyncio.wait_for(asyncio.to_thread(warehouse.dashboard), DASHBOARD_TIMEOUT_S)
    except Exception as exc:
        log.warning("Dashboard query failed: %s", exc or type(exc).__name__)
        cached = DEMO_CACHE / "dashboard.json"
        if config.DEMO_MODE and cached.exists():
            data = json.loads(cached.read_text())
            data["source"] = "cache"
            return data
        raise AnalysisError("The dashboard data couldn't be loaded right now. Please try again shortly.") from exc

    plots = []
    for row in rows:
        geojson = row.pop("geojson", None)
        plots.append({**row, "geometry": json.loads(geojson) if geojson else None})
    return {"source": "bigquery", "plots": plots, **warehouse.summarise(plots)}


# --- Report -----------------------------------------------------------------------------


async def generate_report(assessment_id, refresh=False):
    """Add the Gemini report to a stored assessment (reusing an existing one unless refresh)."""
    assessment = await asyncio.to_thread(load_assessment, assessment_id)
    if assessment is None:
        raise AnalysisError("Assessment not found.", 404)
    if assessment.get("report") and not refresh:
        return assessment

    try:
        report_text = await asyncio.wait_for(asyncio.to_thread(report.generate, assessment), REPORT_TIMEOUT_S)
    except asyncio.TimeoutError as exc:
        raise AnalysisError("Writing the report took too long. Please try again.", 504) from exc
    except Exception as exc:
        log.warning("Report generation failed for %s: %s", assessment_id, exc)
        raise AnalysisError("We couldn't write the report right now. Please try again in a few minutes.") from exc

    assessment["report"] = report_text
    try:
        await asyncio.to_thread(storage.save_json, f"assessments/{assessment_id}.json", assessment)
    except Exception as exc:
        log.warning("Saving report for %s failed: %s", assessment_id, exc)
    return assessment
