"""Step 2 of verification: does the weather record make the claim plausible?

A transparent rule gives a first verdict from ERA5-Land weather facts; then
Gemini reads the same facts (and the rule's verdict) and gives the final
verdict with a plain explanation in English and Kannada. If Gemini is
unavailable, the rule's verdict is used. Gemini never accuses anyone of fraud.
"""

import json
import logging
from typing import Literal

from google.genai import types
from pydantic import BaseModel, Field

from app import config, report

log = logging.getLogger("claimsat")

HEAVY_RAIN_MM_PER_DAY = 64.5   # IMD's "heavy rainfall" threshold
HEATWAVE_C = 40.0

RULE_TEXT = {
    "supported": "The weather record shows conditions that can cause this damage.",
    "not_supported": "The weather record shows no conditions that would cause this damage.",
    "uncertain": "The weather record neither clearly supports nor rules out this claim.",
}


def rule_verdict(event_type, facts):
    """('supported' | 'not_supported' | 'uncertain', reason) from simple thresholds."""
    if not facts or not facts.get("days_with_data"):
        return "uncertain", "Weather data for these dates isn't available yet."

    if event_type == "flood":
        week, normal = facts.get("rain_week_region_mm"), facts.get("normal_week_region_mm")
        max_daily = facts.get("max_daily_rain_local_mm") or 0
        if week is None:
            return "uncertain", "Regional rainfall is missing."
        if max_daily >= HEAVY_RAIN_MM_PER_DAY or week >= max(100, 2 * (normal or 0)):
            return "supported", f"Heavy rain: {week} mm across the region in the week before (normal {normal} mm)."
        if week < 20 and max_daily < 10:
            return "not_supported", f"Only {week} mm of rain across the region in the week before."
        return "uncertain", f"{week} mm of rain across the region in the week before (normal {normal} mm)."

    if event_type == "drought":
        month, normal = facts.get("rain_month_local_mm"), facts.get("normal_month_local_mm")
        if month is None or not normal:
            return "uncertain", "Rainfall history is missing."
        if month < 0.5 * normal:
            return "supported", f"{month} mm of rain in the last 30 days, under half the normal {normal} mm."
        if month > 0.9 * normal:
            return "not_supported", f"{month} mm of rain in the last 30 days, close to or above the normal {normal} mm."
        return "uncertain", f"{month} mm of rain in the last 30 days (normal {normal} mm)."

    # Other damage (hail, storm, heat, pests): weather only helps for some causes.
    max_daily, tmax = facts.get("max_daily_rain_local_mm") or 0, facts.get("max_temp_c") or 0
    if max_daily >= HEAVY_RAIN_MM_PER_DAY:
        return "supported", f"A heavy storm: up to {max_daily} mm of rain in a day."
    if tmax >= HEATWAVE_C:
        return "supported", f"Extreme heat: up to {tmax} °C."
    return "uncertain", "Weather can't confirm or rule out this kind of damage (for example pests)."


class WeatherVerdict(BaseModel):
    verdict: Literal["supported", "not_supported", "uncertain"]
    explanation_en: str = Field(description="2 plain sentences citing the weather facts")
    explanation_kn: str = Field(description="The same in simple Kannada")


INSTRUCTION = """\
You verify crop insurance claims against the weather record. Given the
reported event and ERA5-Land weather facts for the plot and the region around
it, decide whether the weather makes the reported damage plausible:
"supported", "not_supported" or "uncertain".

- A rule-based verdict is included; agree with it unless the facts clearly say otherwise.
- River floods can follow heavy rain upstream or dam releases even when local
  rain is modest: prefer "uncertain" over "not_supported" in that case.
- Droughts need rainfall well below normal over weeks.
- Never accuse anyone of fraud or lying. Say what the weather shows.
- Use only numbers from the facts, Western digits, plain language. Kannada must be simple and natural.
"""


def _ask_gemini(event_type, event_date, facts, rule, reason):
    payload = {
        "reported_event": {"type": event_type, "date": event_date},
        "weather_facts": {k: v for k, v in facts.items() if k != "windows"},
        "rule_based_verdict": rule,
        "rule_reason": reason,
    }
    response = report.get_client().models.generate_content(
        model=config.GEMINI_MODEL,
        contents="Claim and weather (JSON):\n" + json.dumps(payload, ensure_ascii=False),
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCTION,
            response_mime_type="application/json",
            response_schema=WeatherVerdict,
            temperature=0.1,
        ),
    )
    if response.parsed is None:
        raise RuntimeError("Gemini did not return a weather verdict")
    return response.parsed


def check(event_type, event_date, facts):
    """Full step 2. Returns the stored `verification.weather` dict."""
    rule, reason = rule_verdict(event_type, facts)
    result = {
        "verdict": rule,
        "rule_verdict": rule,
        "rule_reason": reason,
        "explanation_en": f"{RULE_TEXT[rule]} {reason}",
        "explanation_kn": None,
        "model": None,
        "facts": facts,
    }
    if not facts or not facts.get("days_with_data"):
        return result
    try:
        ai = _ask_gemini(event_type, event_date, facts, rule, reason)
        result.update(verdict=ai.verdict, explanation_en=ai.explanation_en, explanation_kn=ai.explanation_kn, model=config.GEMINI_MODEL)
    except Exception as exc:  # the rule's verdict still stands
        log.warning("Gemini weather check failed, using the rule: %s", exc)
    return result
