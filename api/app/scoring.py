"""Damage score, damage level and confidence. Pure functions: no Earth Engine calls.

All formulas are documented heuristics (see CLAIMSAT_BUILD_PROMPT.md), meant to
support a claim, not to replace an official loss assessment.
"""

# Weights per event type. If a component is missing (for example no radar
# images), the remaining weights are rescaled and confidence drops.
WEIGHTS = {
    "flood": {"flood_fraction": 0.5, "ndvi_loss": 0.5},
    "drought": {"ndvi_loss": 0.6, "rain_deficit": 0.4},
    "other": {"ndvi_loss": 1.0},
}

# Score thresholds: none < 15 <= low < 35 <= moderate < 60 <= severe.
LEVEL_THRESHOLDS = ((15, "none"), (35, "low"), (60, "moderate"))

COMPONENT_LABELS = {
    "flood_fraction": "flood extent",
    "ndvi_loss": "vegetation loss",
    "rain_deficit": "rainfall deficit",
}


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def ndvi_loss(ndvi_after, ndvi_baseline_after):
    """Share of the plot's normal vegetation that is missing after the event.

    Compares against the same weeks in previous years, so a normal harvest
    (which also lowers NDVI) doesn't count as damage.
    """
    if ndvi_after is None or ndvi_baseline_after is None:
        return None
    return clamp((ndvi_baseline_after - ndvi_after) / max(ndvi_baseline_after, 0.1))


def rain_deficit(season_rain_mm, baseline_rain_mm):
    """Share of normal seasonal rainfall that didn't fall."""
    if season_rain_mm is None or not baseline_rain_mm:
        return None
    return clamp(1 - season_rain_mm / baseline_rain_mm)


def damage_score(event_type, metrics):
    """Return (score 0-100 or None, list of missing components)."""
    weights = WEIGHTS[event_type]
    available = {k: w for k, w in weights.items() if metrics.get(k) is not None}
    missing = [k for k in weights if k not in available]
    if not available:
        return None, missing
    total = sum(available.values())
    score = 100 * sum(metrics[k] * w for k, w in available.items()) / total
    return round(score), missing


def damage_level(score):
    if score is None:
        return "unknown"
    for threshold, level in LEVEL_THRESHOLDS:
        if score < threshold:
            return level
    return "severe"


def confidence(event_type, metrics, area_pixels, missing_components=()):
    """Return {"level": "high"|"medium"|"low", "reasons": [...]}."""
    clear_before = metrics.get("clear_obs_before") or 0
    clear_after = metrics.get("clear_obs_after") or 0
    crop = metrics.get("crop_fraction")
    pixels = area_pixels or 0
    is_flood = event_type == "flood"

    reasons = [
        f"{clear_before} cloud-free Sentinel-2 image{'s' if clear_before != 1 else ''} "
        f"before the event and {clear_after} after"
    ]

    radar_ok = True
    if is_flood:
        radar_ok = (metrics.get("radar_obs_pre") or 0) >= 1 and (metrics.get("radar_obs_post") or 0) >= 1
        reasons.append(
            "Radar images available before and after the event"
            if radar_ok
            else "Radar images missing before or after the event"
        )

    if crop is None:
        reasons.append("Could not confirm that the plot is cropland")
    else:
        reasons.append(f"Plot is {round(crop * 100)}% cropland")

    reasons.append(f"Plot covers {pixels} satellite pixels (10 m each)")

    if missing_components:
        names = ", ".join(COMPONENT_LABELS.get(c, c) for c in missing_components)
        reasons.append(f"Score uses partial data: no {names} measurement")

    optical_ok = clear_before >= 3 and clear_after >= 3
    optical_missing = clear_before == 0 or clear_after == 0

    if (
        (optical_missing and (not is_flood or not radar_ok))
        or (crop is not None and crop < 0.3)
        or pixels < 10
    ):
        level = "low"
    elif (
        optical_ok
        and pixels >= 20
        and crop is not None
        and crop >= 0.6
        and radar_ok
        and not missing_components
    ):
        level = "high"
    else:
        level = "medium"

    return {"level": level, "reasons": reasons}


def score_assessment(event_type, metrics, area_pixels):
    """Combine score, level and confidence in the shape of shared/sample_result.json."""
    score, missing = damage_score(event_type, metrics)
    return {
        "score": {"damage_score": score, "damage_level": damage_level(score)},
        "confidence": confidence(event_type, metrics, area_pixels, missing),
    }
