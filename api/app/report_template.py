"""A plain, template-written evidence report in English and Kannada.

Used for the bundled demo samples, and as a fallback when Gemini can't be
reached, so a farmer always gets a report. Every number comes straight from the
assessment, so the percentage check always passes.
"""

import re
from datetime import datetime, timezone

EVENT = {"en": {"flood": "Flood", "drought": "Drought", "other": "Crop damage"}, "kn": {"flood": "ಪ್ರವಾಹ", "drought": "ಬರ", "other": "ಬೆಳೆ ಹಾನಿ"}}
DAMAGE = {
    "en": {"none": "no clear damage", "low": "low damage", "moderate": "moderate damage", "severe": "severe damage", "unknown": "an unclear picture"},
    "kn": {"none": "ಸ್ಪಷ್ಟ ಹಾನಿ ಇಲ್ಲ", "low": "ಕಡಿಮೆ ಹಾನಿ", "moderate": "ಮಧ್ಯಮ ಹಾನಿ", "severe": "ತೀವ್ರ ಹಾನಿ", "unknown": "ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ"},
}
SEVERITY = {
    "en": {"none": "minimal", "low": "low", "moderate": "moderate", "severe": "severe", "unknown": "unknown"},
    "kn": {"none": "ಕನಿಷ್ಠ", "low": "ಕಡಿಮೆ", "moderate": "ಮಧ್ಯಮ", "severe": "ತೀವ್ರ", "unknown": "ತಿಳಿದಿಲ್ಲ"},
}
VERIFICATION = {
    "en": {
        "verified": "Both checks support the claim: the satellite images show damage, and the weather record shows conditions that can cause it.",
        "needs_review": "One of the two checks could not confirm the claim, so an agriculture officer should review it.",
        "not_supported": "Neither the satellite images nor the weather record support this claim.",
    },
    "kn": {
        "verified": "ಎರಡೂ ಪರಿಶೀಲನೆಗಳು ಕ್ಲೇಮ್ ಅನ್ನು ಬೆಂಬಲಿಸುತ್ತವೆ: ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ಹಾನಿಯನ್ನು ತೋರಿಸುತ್ತವೆ ಮತ್ತು ಹವಾಮಾನ ದಾಖಲೆಗಳು ಅದಕ್ಕೆ ಕಾರಣವಾಗಬಹುದಾದ ಪರಿಸ್ಥಿತಿಯನ್ನು ತೋರಿಸುತ್ತವೆ.",
        "needs_review": "ಎರಡು ಪರಿಶೀಲನೆಗಳಲ್ಲಿ ಒಂದು ಕ್ಲೇಮ್ ಅನ್ನು ದೃಢಪಡಿಸಲಿಲ್ಲ, ಆದ್ದರಿಂದ ಕೃಷಿ ಅಧಿಕಾರಿಗಳು ಇದನ್ನು ಪರಿಶೀಲಿಸಬೇಕು.",
        "not_supported": "ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ಅಥವಾ ಹವಾಮಾನ ದಾಖಲೆಗಳು ಈ ಕ್ಲೇಮ್ ಅನ್ನು ಬೆಂಬಲಿಸುವುದಿಲ್ಲ.",
    },
}
WEATHER_KN = {
    "supported": "ಹವಾಮಾನ ದಾಖಲೆಗಳು ಈ ಹಾನಿಗೆ ಕಾರಣವಾಗಬಹುದಾದ ಪರಿಸ್ಥಿತಿಯನ್ನು ತೋರಿಸುತ್ತವೆ.",
    "not_supported": "ಹವಾಮಾನ ದಾಖಲೆಗಳು ಈ ಹಾನಿಗೆ ಕಾರಣವಾಗುವ ಪರಿಸ್ಥಿತಿಯನ್ನು ತೋರಿಸುವುದಿಲ್ಲ.",
    "uncertain": "ಹವಾಮಾನ ದಾಖಲೆಗಳು ಈ ಕ್ಲೇಮ್ ಅನ್ನು ಖಚಿತವಾಗಿ ದೃಢಪಡಿಸುವುದೂ ಇಲ್ಲ, ತಳ್ಳಿಹಾಕುವುದೂ ಇಲ್ಲ.",
}
LIMITATIONS = {
    "en": "Only two images are compared, so slow changes such as drought show less. Clouds can hide parts of a field. Each satellite pixel is 10 metres wide, so field edges are less precise. The crop type is as reported and was not checked from space.",
    "kn": "ಕೇವಲ ಎರಡು ಚಿತ್ರಗಳನ್ನು ಹೋಲಿಸಲಾಗುತ್ತದೆ, ಆದ್ದರಿಂದ ಬರದಂತಹ ನಿಧಾನ ಬದಲಾವಣೆಗಳು ಕಡಿಮೆ ಕಾಣುತ್ತವೆ. ಮೋಡಗಳು ಹೊಲದ ಭಾಗಗಳನ್ನು ಮರೆಮಾಡಬಹುದು. ಪ್ರತಿ ಉಪಗ್ರಹ ಪಿಕ್ಸೆಲ್ 10 ಮೀಟರ್ ಅಗಲವಿರುವುದರಿಂದ ಹೊಲದ ಅಂಚುಗಳ ಅಳತೆ ಕಡಿಮೆ ನಿಖರವಾಗಿರುತ್ತದೆ. ಬೆಳೆಯ ಪ್ರಕಾರವನ್ನು ತಿಳಿಸಿದಂತೆ ಬರೆಯಲಾಗಿದೆ; ಅದನ್ನು ಉಪಗ್ರಹದಿಂದ ಪರಿಶೀಲಿಸಿಲ್ಲ.",
}
NEXT_STEPS = {
    "en": "Report the crop loss to your insurance company, bank or agriculture office within 72 hours of the event, as PMFBY requires, or as soon as possible if that time has passed. Attach this report and ask for a field inspection.",
    "kn": "PMFBY ನಿಯಮದಂತೆ ಘಟನೆ ನಡೆದ 72 ಗಂಟೆಗಳೊಳಗೆ ನಿಮ್ಮ ವಿಮಾ ಕಂಪನಿ, ಬ್ಯಾಂಕ್ ಅಥವಾ ಕೃಷಿ ಕಚೇರಿಗೆ ಬೆಳೆ ನಷ್ಟವನ್ನು ತಿಳಿಸಿ. ಆ ಸಮಯ ಕಳೆದಿದ್ದರೆ ಸಾಧ್ಯವಾದಷ್ಟು ಬೇಗ ತಿಳಿಸಿ. ಈ ವರದಿಯನ್ನು ಲಗತ್ತಿಸಿ ಮತ್ತು ಹೊಲ ಪರಿಶೀಲನೆಗೆ ಮನವಿ ಮಾಡಿ.",
}
# English confidence reasons (app.scoring.confidence) -> Kannada.
REASONS_KN = [
    (r"^Clear Sentinel-2 image 1 week before: (.+)$", r"ಘಟನೆಗೆ 1 ವಾರ ಮೊದಲಿನ ಸ್ಪಷ್ಟ Sentinel-2 ಚಿತ್ರ: \1"),
    (r"^No clear image from the week before the event$", "ಘಟನೆಗೆ ಹಿಂದಿನ ವಾರದ ಸ್ಪಷ್ಟ ಚಿತ್ರ ಲಭ್ಯವಿಲ್ಲ"),
    (r"^Clear Sentinel-2 image now: (.+)$", r"ಇತ್ತೀಚಿನ ಸ್ಪಷ್ಟ Sentinel-2 ಚಿತ್ರ: \1"),
    (r"^No clear image since the event yet$", "ಘಟನೆಯ ನಂತರ ಇನ್ನೂ ಸ್ಪಷ್ಟ ಚಿತ್ರ ಲಭ್ಯವಿಲ್ಲ"),
    (r"^Plot covers (\d+) satellite pixels \(10 m each\)$", r"ಜಮೀನು \1 ಉಪಗ್ರಹ ಪಿಕ್ಸೆಲ್‌ಗಳನ್ನು ಒಳಗೊಂಡಿದೆ (ಪ್ರತಿಯೊಂದು 10 ಮೀ)"),
    (r"^Little crop was visible before the event$", "ಘಟನೆಗೆ ಮೊದಲು ಹೆಚ್ಚು ಬೆಳೆ ಕಾಣುತ್ತಿರಲಿಲ್ಲ"),
    (r"^The two images are (\d+) days apart$", r"ಎರಡು ಚಿತ್ರಗಳ ನಡುವೆ \1 ದಿನಗಳ ಅಂತರವಿದೆ"),
    (r"^Score uses partial data.*$", "ಹಾನಿ ಅಂಕವು ಭಾಗಶಃ ದತ್ತಾಂಶವನ್ನು ಬಳಸುತ್ತದೆ"),
]


def _pct(value):
    return None if value is None else round(value * 100)


def reason_kn(reason):
    for pattern, replacement in REASONS_KN:
        if re.match(pattern, reason):
            return re.sub(pattern, replacement, reason)
    return reason


def build(assessment, model="template"):
    """The report dict, same shape as report.generate()."""
    event, metrics, score = assessment["event"], assessment["metrics"], assessment["score"]
    verification = assessment.get("verification") or {}
    weather = verification.get("weather") or {}
    status = verification.get("status", "needs_review")
    nearby = (assessment.get("area") or {}).get("nearby_farmers", 0)
    radius = (assessment.get("area") or {}).get("radius_km", 2)
    severity = (assessment.get("severity") or {}).get("level", "unknown")
    loss, flood = _pct(metrics.get("ndvi_loss")), _pct(metrics.get("flood_fraction"))
    before, now = metrics.get("before_image_date") or "—", metrics.get("now_image_date") or "—"
    is_flood = event["type"] == "flood" and flood is not None

    water_en = (f" and {flood}% of the field became newly covered by water" if flood else " and no part of the field became newly covered by water")
    water_kn = (f"; ಹೊಲದ {flood}% ಭಾಗ ಹೊಸದಾಗಿ ನೀರಿನಲ್ಲಿ ಮುಳುಗಿದೆ" if flood else "; ಹೊಲದ ಯಾವ ಭಾಗವೂ ಹೊಸದಾಗಿ ನೀರಿನಲ್ಲಿ ಮುಳುಗಿಲ್ಲ")
    change_en = (f"crop health fell by {loss}%" if loss is not None else "crop health couldn't be measured") + (water_en if is_flood else "")
    change_kn = (f"ಬೆಳೆಯ ಆರೋಗ್ಯ {loss}% ಕುಸಿದಿದೆ" if loss is not None else "ಬೆಳೆಯ ಆರೋಗ್ಯವನ್ನು ಅಳೆಯಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ") + (water_kn if is_flood else "")
    nearby_en = (
        f"{nearby} other farmer{'s' if nearby != 1 else ''} within {radius} km reported the same event."
        if nearby
        else f"No other farmers within {radius} km have reported this event yet."
    )
    nearby_kn = (
        f"{radius} ಕಿ.ಮೀ ಒಳಗಿನ ಇನ್ನೂ {nearby} ರೈತರು ಇದೇ ಘಟನೆಯನ್ನು ವರದಿ ಮಾಡಿದ್ದಾರೆ."
        if nearby
        else f"{radius} ಕಿ.ಮೀ ಒಳಗೆ ಬೇರೆ ಯಾವ ರೈತರೂ ಈ ಘಟನೆಯನ್ನು ಇನ್ನೂ ವರದಿ ಮಾಡಿಲ್ಲ."
    )
    weather_en = weather.get("explanation_en") or "The weather check is pending."
    weather_kn = weather.get("explanation_kn") or WEATHER_KN.get(weather.get("verdict"), WEATHER_KN["uncertain"])

    summary_en = (
        f"{EVENT['en'][event['type']]} reported on {event['date']}. Sentinel-2 satellite images of this field from {before} and {now} "
        f"show {DAMAGE['en'][score['damage_level']]} (damage score {score['damage_score'] if score['damage_score'] is not None else '—'}/100): "
        f"{change_en}. {nearby_en} {VERIFICATION['en'][status]} Case severity: {SEVERITY['en'][severity]}. "
        "This report is supporting evidence for your insurance claim, not an official loss assessment."
    )
    summary_kn = (
        f"{event['date']} ರಂದು {EVENT['kn'][event['type']]} ವರದಿಯಾಗಿದೆ. ಈ ಹೊಲದ {before} ಮತ್ತು {now} ರ Sentinel-2 ಉಪಗ್ರಹ ಚಿತ್ರಗಳ ಪ್ರಕಾರ "
        f"ಹಾನಿಯ ಮಟ್ಟ: {DAMAGE['kn'][score['damage_level']]} (ಹಾನಿ ಅಂಕ {score['damage_score'] if score['damage_score'] is not None else '—'}/100). "
        f"{change_kn}. {nearby_kn} {VERIFICATION['kn'][status]} ಪ್ರಕರಣದ ತೀವ್ರತೆ: {SEVERITY['kn'][severity]}. "
        "ಈ ವರದಿ ನಿಮ್ಮ ವಿಮೆ ಕ್ಲೇಮ್‌ಗೆ ಪೂರಕ ಸಾಕ್ಷ್ಯ ಮಾತ್ರ, ಅಧಿಕೃತ ನಷ್ಟ ಮೌಲ್ಯಮಾಪನವಲ್ಲ."
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "model": model,
        "summary_en": summary_en,
        "summary_kn": summary_kn,
        "findings": [
            {
                "title_en": "What the satellite images show",
                "title_kn": "ಉಪಗ್ರಹ ಚಿತ್ರಗಳು ತೋರಿಸುವುದು",
                "detail_en": f"Between {before} and {now}, {change_en}.",
                "detail_kn": f"{before} ಮತ್ತು {now} ರ ನಡುವೆ {change_kn}.",
            },
            {
                "title_en": "What the weather record shows",
                "title_kn": "ಹವಾಮಾನ ದಾಖಲೆ ತೋರಿಸುವುದು",
                "detail_en": weather_en,
                "detail_kn": weather_kn,
            },
            {
                "title_en": "Reports from nearby farmers",
                "title_kn": "ಹತ್ತಿರದ ರೈತರ ವರದಿಗಳು",
                "detail_en": nearby_en,
                "detail_kn": nearby_kn,
            },
        ],
        "confidence_reasons_kn": [reason_kn(r) for r in assessment["confidence"]["reasons"]],
        "limitations_en": LIMITATIONS["en"],
        "limitations_kn": LIMITATIONS["kn"],
        "recommended_next_steps_en": NEXT_STEPS["en"],
        "recommended_next_steps_kn": NEXT_STEPS["kn"],
        "number_check": {"ok": True, "unexpected_percentages": []},
    }
