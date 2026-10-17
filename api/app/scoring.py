"""Scoring rules. Pure functions: no Earth Engine or Gemini calls.

  damage score  = how bad THIS plot looks (Sentinel-2, 1 week before vs now)
  case severity = damage score combined with how many OTHER farmers nearby
                  reported the same event; one report alone can't be "severe"
  verification  = step 1 satellite shows damage + step 2 weather supports it

All formulas are documented heuristics (see README), meant to support a claim,
not to replace an official loss assessment.
"""

# Damage score weights per event type.
WEIGHTS = {
    "flood": {"flood_fraction": 0.5, "ndvi_loss": 0.5},
    "drought": {"ndvi_loss": 1.0},
    "other": {"ndvi_loss": 1.0},
}

# Score thresholds: none < 15 <= low < 35 <= moderate < 60 <= severe.
LEVEL_THRESHOLDS = ((15, "none"), (35, "low"), (60, "moderate"))
LEVEL_ORDER = ("none", "low", "moderate", "severe")

COMPONENT_LABELS = {"flood_fraction": "new standing water", "ndvi_loss": "crop health change"}

# Case severity: 70% this plot's damage, 30% nearby reports (5+ other farmers = full).
SEVERITY_DAMAGE_WEIGHT = 0.7
SEVERITY_AREA_WEIGHT = 0.3
FARMERS_FOR_FULL_AREA_SCORE = 5


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def ndvi_loss(ndvi_now, ndvi_before):
    """Share of the crop health seen 1 week before the event that is gone now."""
    if ndvi_now is None or ndvi_before is None:
        return None
    return clamp((ndvi_before - ndvi_now) / max(ndvi_before, 0.1))


def damage_score(event_type, metrics):
    """Return (score 0-100 or None, list of missing components)."""
    weights = WEIGHTS[event_type]
    available = {k: w for k, w in weights.items() if metrics.get(k) is not None}
    missing = [k for k in weights if k not in available]
    if not available:
        return None, missing
    total = sum(available.values())
    return round(100 * sum(metrics[k] * w for k, w in available.items()) / total), missing


def damage_level(score):
    if score is None:
        return "unknown"
    for threshold, level in LEVEL_THRESHOLDS:
        if score < threshold:
            return level
    return "severe"


def confidence(event_type, metrics, area_pixels, missing_components=()):
    """How much to trust the damage score: {"level", "reasons"}."""
    before_date, now_date = metrics.get("before_image_date"), metrics.get("now_image_date")
    before_clear, now_clear = metrics.get("before_clear") or 0, metrics.get("now_clear") or 0
    gap = metrics.get("days_between")
    ndvi_before = metrics.get("ndvi_before")
    pixels = area_pixels or 0

    reasons = [
        f"Clear Sentinel-2 image 1 week before: {before_date}" if before_date else "No clear image from the week before the event",
        f"Clear Sentinel-2 image now: {now_date}" if now_date else "No clear image since the event yet",
        f"Plot covers {pixels} satellite pixels (10 m each)",
    ]
    if ndvi_before is not None and ndvi_before < 0.2:
        reasons.append("Little crop was visible before the event")
    if gap is not None and gap > 21:
        reasons.append(f"The two images are {gap} days apart")
    if missing_components:
        reasons.append("Score uses partial data: no " + ", ".join(COMPONENT_LABELS.get(c, c) for c in missing_components) + " measurement")

    if not before_date or not now_date or pixels < 10 or (ndvi_before is not None and ndvi_before < 0.2):
        level = "low"
    elif min(before_clear, now_clear) >= 0.8 and (gap or 99) <= 21 and pixels >= 20 and (ndvi_before or 0) >= 0.4 and not missing_components:
        level = "high"
    else:
        level = "medium"
    return {"level": level, "reasons": reasons}


def score_assessment(event_type, metrics, area_pixels):
    score, missing = damage_score(event_type, metrics)
    return {
        "score": {"damage_score": score, "damage_level": damage_level(score)},
        "confidence": confidence(event_type, metrics, area_pixels, missing),
    }


# --- Nearby reports ---------------------------------------------------------------------


def area_level(nearby_farmers):
    if nearby_farmers >= 3:
        return "widespread"
    if nearby_farmers >= 1:
        return "some"
    return "isolated"


# --- Two-step verification -----------------------------------------------------------------


def satellite_step(score, confidence_result):
    """Step 1: do the images show damage we can rely on?"""
    level = score["damage_level"]
    if level == "unknown" or confidence_result["level"] == "low":
        return {"passed": None, "reason": "Not enough clear satellite images to judge the damage."}
    if level == "none":
        return {"passed": False, "reason": "The satellite images show no clear damage on this plot."}
    return {"passed": True, "reason": f"The satellite images show {level} damage on this plot."}


def verification_status(satellite_passed, weather_verdict):
    """verified = both steps agree; not_supported = both contradict; else needs_review."""
    if satellite_passed is True and weather_verdict == "supported":
        return "verified"
    if satellite_passed is False and weather_verdict == "not_supported":
        return "not_supported"
    return "needs_review"


# --- Case severity ---------------------------------------------------------------------------


def severity(damage, area, status):
    """Combine plot damage with nearby reports. Returns {"score", "level", "reasons"}."""
    farmers = area.get("nearby_farmers", 0) if area else 0
    if damage is None:
        return {"score": None, "level": "unknown", "reasons": ["The plot's damage couldn't be measured."]}

    area_score = min(100, 100 * farmers / FARMERS_FOR_FULL_AREA_SCORE)
    score = round(SEVERITY_DAMAGE_WEIGHT * damage + SEVERITY_AREA_WEIGHT * area_score)
    level = damage_level(score)
    reasons = [
        f"Plot damage score {damage}/100",
        f"{farmers} other farmer{'s' if farmers != 1 else ''} within {area.get('radius_km', 2) if area else 2} km reported the same event"
        if farmers
        else "No other farmers nearby have reported this event yet",
    ]

    def cap(max_level, why):
        nonlocal level
        if LEVEL_ORDER.index(level) > LEVEL_ORDER.index(max_level):
            level = max_level
            reasons.append(why)

    if farmers == 0:
        cap("moderate", "A single report can't be rated severe until nearby reports confirm it")
    if status == "not_supported":
        cap("low", "Satellite and weather data don't support the claim")
    return {"score": score, "level": level, "reasons": reasons}
