"""ClaimSat API."""

import asyncio
import hmac
import logging
import time

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from app import assessments, config, ee_analysis, plots, report, storage
from app.validation import ValidationError

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("claimsat")

app = FastAPI(title="ClaimSat API")

CHECK_TIMEOUT_SECONDS = 25


# --- Errors: always {"error": "..."} so the frontend can show the message ----------


@app.exception_handler(ValidationError)
async def on_validation_error(_request: Request, exc: ValidationError):
    return JSONResponse({"error": str(exc)}, status_code=422)


@app.exception_handler(RequestValidationError)
async def on_bad_request(_request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
    return JSONResponse(
        {"error": f"Invalid {field}: {first.get('msg', 'bad value')}"}, status_code=422
    )


@app.exception_handler(plots.PlotError)
async def on_plot_error(_request: Request, exc: plots.PlotError):
    return JSONResponse({"error": str(exc)}, status_code=exc.status)


@app.exception_handler(HTTPException)
async def on_http_error(_request: Request, exc: HTTPException):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


def require_officer(x_officer_code: str | None = Header(default=None)):
    """Officer pages need the shared access code (OFFICER_ACCESS_CODE)."""
    expected = config.OFFICER_ACCESS_CODE
    if not expected:
        raise HTTPException(503, "Officer access isn't set up on this server (OFFICER_ACCESS_CODE).")
    if not x_officer_code or not hmac.compare_digest(x_officer_code.encode(), expected.encode()):
        raise HTTPException(401, "Wrong officer access code.")
    return "officer"


@app.exception_handler(assessments.AnalysisError)
async def on_analysis_error(_request: Request, exc: assessments.AnalysisError):
    return JSONResponse({"error": str(exc)}, status_code=exc.status)


# --- Health ------------------------------------------------------------------------


async def _run_check(name, fn):
    """Run a blocking health check in a thread, with a timeout, and never raise."""
    started = time.perf_counter()
    try:
        detail = await asyncio.wait_for(asyncio.to_thread(fn), CHECK_TIMEOUT_SECONDS)
        status = "ok"
    except asyncio.TimeoutError:
        status, detail = "error", f"Timed out after {CHECK_TIMEOUT_SECONDS}s"
    except Exception as exc:  # report any failure in the response instead of crashing
        log.warning("Health check %s failed: %s", name, exc)
        status, detail = "error", f"{type(exc).__name__}: {exc}"[:500]
    return name, {
        "status": status,
        "detail": detail,
        "latency_ms": round((time.perf_counter() - started) * 1000),
    }


@app.get("/api/health")
async def health():
    results = await asyncio.gather(
        _run_check("earth_engine", ee_analysis.check),
        _run_check("vertex_ai", report.check),
        _run_check("bigquery", storage.check),
    )
    services = dict(results)
    return {
        "ok": all(s["status"] == "ok" for s in services.values()),
        "project": config.GCP_PROJECT or None,
        "demo_mode": config.DEMO_MODE,
        "services": services,
    }


# --- Assessments ---------------------------------------------------------------------


@app.post("/api/assess")
async def assess(body: dict):
    return await assessments.run(body)


@app.get("/api/assessments/{assessment_id}")
async def get_assessment(assessment_id: str):
    result = await asyncio.to_thread(assessments.load_assessment, assessment_id)
    if result is None:
        return JSONResponse({"error": "Assessment not found."}, status_code=404)
    return result


@app.post("/api/report/{assessment_id}")
async def create_report(assessment_id: str, refresh: bool = False):
    return await assessments.generate_report(assessment_id, refresh)


@app.get("/api/assets/{path:path}")
async def get_asset(path: str):
    data = await asyncio.to_thread(assessments.load_asset, path)
    if data is None:
        return JSONResponse({"error": "Image not found."}, status_code=404)
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/photo-check")
async def photo_check(assessment_id: str = Form(...), photo: UploadFile = File(...)):
    # Read one byte past the limit so oversized uploads are rejected without loading more.
    data = await photo.read(assessments.photo_check.MAX_UPLOAD_BYTES + 1)
    return await assessments.check_photo(assessment_id, data)


@app.get("/api/photos/{path:path}")
async def get_photo(path: str):
    data = await asyncio.to_thread(assessments.load_photo, path)
    if data is None:
        return JSONResponse({"error": "Photo not found."}, status_code=404)
    return Response(data, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/farmers/{farmer_id}/plots")
async def farmer_plots(farmer_id: str):
    found = await asyncio.to_thread(plots.plots_for_farmer, farmer_id)
    if not found:
        return JSONResponse(
            {"error": "No land is registered to this Farmer ID yet. Ask your agriculture office to register your plot."},
            status_code=404,
        )
    return {"plots": found}


@app.get("/api/officer/check")
async def officer_check(_officer: str = Depends(require_officer)):
    return {"ok": True}


@app.get("/api/plots")
async def list_plots(_officer: str = Depends(require_officer)):
    return {"plots": await asyncio.to_thread(plots.all_plots)}


@app.post("/api/plots")
async def register_plot(body: dict, officer: str = Depends(require_officer)):
    return {"plot": await asyncio.to_thread(plots.register, body, officer)}


@app.get("/api/dashboard")
async def dashboard(_officer: str = Depends(require_officer)):
    return await assessments.dashboard_data()


