"""Gemini (Vertex AI) evidence report.

Gemini only writes the words. Every number comes from the assessment, and the
percentages it writes are checked against the measured values afterwards.
"""

import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app import config

log = logging.getLogger("claimsat")


@lru_cache(maxsize=1)
def get_client():
    return genai.Client(
        vertexai=True,
        project=config.GCP_PROJECT or None,
        location=config.VERTEX_LOCATION,
    )


def check():
    """Health check: a one-word Gemini call."""
    response = get_client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents="Reply with the single word OK.",
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response")
    return f"{config.GEMINI_MODEL} replied: {text[:20]}"


# --- Report schema --------------------------------------------------------------------


class Finding(BaseModel):
    title_en: str = Field(description="Short heading, at most 8 words")
    title_kn: str = Field(description="The same heading in Kannada")
    detail_en: str = Field(description="One or two plain sentences")
    detail_kn: str = Field(description="The same sentences in Kannada")


class ReportText(BaseModel):
    summary_en: str = Field(description="3-4 sentences a farmer can understand")
    summary_kn: str
    findings: list[Finding] = Field(description="3 to 5 findings, most important first")
    confidence_reasons_kn: list[str] = Field(
        description="Kannada translation of each confidence reason, same order"
    )
    limitations_en: str
    limitations_kn: str
    recommended_next_steps_en: str
    recommended_next_steps_kn: str


SYSTEM_INSTRUCTION = """\
You write crop damage evidence reports for ClaimSat. A farmer in Karnataka will
attach the report to a crop insurance claim under PMFBY (Pradhan Mantri Fasal
Bima Yojana). Write every field in English (*_en) and in Kannada (*_kn).

Rules:
- Use ONLY the facts in the JSON you are given. Never invent numbers, dates,
  places, crop details, sources or causes.
- When you mention a percentage, use exactly a value from "percentages" in the
  facts, written with Western digits and a % sign (for example 65%). Do not
  calculate new numbers. Kannada text also uses Western digits.
- State the damage level, confidence level, case severity and verification
  status exactly as given. Do not make the damage sound worse or milder.
- Explain the confidence level using the confidence reasons provided.
- Explain the two-step verification: step 1, the satellite images (one from
  about a week before the event, one recent); step 2, the weather record.
- Mention how many other farmers nearby reported the same event, as given.
- Plain, respectful language a farmer can understand. Short sentences. Explain
  terms like NDVI as "crop health measured from satellite images".
- Say clearly that this is supporting evidence for the claim, not an official
  loss assessment.
- In the next steps: report the loss to the insurance company, bank or
  agriculture office within 72 hours of the event as PMFBY requires (or as soon
  as possible if that time has passed), attach this report, and ask for a field
  inspection.
- Limitations: mention clouds, the 10-metre pixel size, that only two images
  are compared (so slow changes such as drought show less), and that the crop
  type is as reported by the user, plus anything the confidence reasons point to.
- Kannada must be natural, simple Kannada as spoken in Karnataka, not a word-by-
  word translation.
"""

PERCENT_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _pct(value):
    return None if value is None else round(value * 100)


def build_facts(assessment):
    """The only information Gemini sees: the measurements, pre-formatted."""
    metrics = assessment["metrics"]
    plot = assessment["plot"]
    event = assessment["event"]
    percentages = {
        "crop_health_lost": _pct(metrics.get("ndvi_loss")),
        "field_newly_under_water": _pct(metrics.get("flood_fraction")),
        "field_under_water_now": _pct(metrics.get("water_now")),
    }
    verification = assessment.get("verification") or {}
    weather = verification.get("weather") or {}
    return {
        "plot": {
            "farmer_name": plot.get("farmer_name") or None,
            "village": plot.get("village") or None,
            "crop_reported_by_user": plot.get("crop") or None,
            "area_hectares": plot.get("area_ha"),
            "satellite_pixels": plot.get("area_pixels"),
            "centroid": plot.get("centroid"),
        },
        "event": {"type": event["type"], "date": event["date"], "windows": event.get("windows")},
        "damage": {
            "score_out_of_100": assessment["score"]["damage_score"],
            "level": assessment["score"]["damage_level"],
        },
        "confidence": assessment["confidence"],
        "case_severity": assessment.get("severity"),
        "nearby_reports": assessment.get("area"),
        "verification": {
            "status": verification.get("status"),
            "step_1_satellite": verification.get("satellite"),
            "step_2_weather_verdict": weather.get("verdict"),
            "step_2_weather_explanation": weather.get("explanation_en"),
            "weather_facts": {k: v for k, v in (weather.get("facts") or {}).items() if k != "windows"},
        },
        "percentages": {k: v for k, v in percentages.items() if v is not None},
        "measurements": {
            "crop_health_1_week_before": metrics.get("ndvi_before"),
            "crop_health_now": metrics.get("ndvi_now"),
            "image_1_week_before_date": metrics.get("before_image_date"),
            "image_now_date": metrics.get("now_image_date"),
        },
        "data_sources": [
            "Sentinel-2 satellite images (European Space Agency, Copernicus): one image about a week before the event and the most recent one",
            "ERA5-Land daily weather (ECMWF / Copernicus), used only to verify the claim",
        ],
        "how_damage_is_measured": (
            "From the same two Sentinel-2 images: crop health (NDVI) and standing water (water index) "
            "about a week before the event are compared with the latest image."
        ),
    }


def _texts(report):
    yield report.summary_en
    yield report.summary_kn
    yield report.limitations_en
    yield report.limitations_kn
    yield report.recommended_next_steps_en
    yield report.recommended_next_steps_kn
    yield from report.confidence_reasons_kn
    for f in report.findings:
        yield from (f.title_en, f.title_kn, f.detail_en, f.detail_kn)


def unexpected_percentages(report, facts):
    """Percentages in the text that don't match a measured value (±1 for rounding)."""
    allowed = set(facts["percentages"].values())
    found = set()
    for text in _texts(report):
        for match in PERCENT_PATTERN.findall(text):
            value = float(match)
            if not any(abs(value - a) <= 1 for a in allowed):
                found.add(match + "%")
    return sorted(found)


def _ask_gemini(facts, correction=None):
    prompt = "Facts (JSON):\n" + json.dumps(facts, ensure_ascii=False, indent=2)
    if correction:
        prompt += "\n\n" + correction
    response = get_client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ReportText,
            temperature=0.2,
        ),
    )
    if response.parsed is None:
        raise RuntimeError("Gemini did not return a valid report")
    return response.parsed


def generate(assessment):
    """Write the bilingual report. Retries once if Gemini uses an unmeasured percentage."""
    facts = build_facts(assessment)
    report = _ask_gemini(facts)
    unexpected = unexpected_percentages(report, facts)
    if unexpected:
        log.warning("Report used unmeasured percentages %s; retrying", unexpected)
        report = _ask_gemini(
            facts,
            correction=(
                f"Your previous answer used percentages that are not in the facts: "
                f"{', '.join(unexpected)}. Only use these percentages: "
                f"{', '.join(f'{v}%' for v in facts['percentages'].values())}."
            ),
        )
        unexpected = unexpected_percentages(report, facts)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "model": config.GEMINI_MODEL,
        **report.model_dump(),
        "number_check": {"ok": not unexpected, "unexpected_percentages": unexpected},
    }
