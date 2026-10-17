"""Build the bundled sample results for the three demo plots (no cloud needed).

Each sample is run through the real scoring, verification, nearby-report and
report-template code, so demo mode shows exactly what the rules produce:

  plt_seed_1 (112/3): flood, heavy rain, 6 neighbours reported it -> verified, severe
  plt_seed_2 (118/1): heavy damage but no nearby reports          -> held at moderate
  plt_seed_3 (124/2): "flood" claimed in the dry season           -> not supported

The satellite and weather numbers are illustrative, not measurements.

Writes api/app/sample_results.json (backend DEMO_MODE fallback) and
web/src/lib/sampleResults.json (frontend mock mode).

Run from api/:  python -m scripts.build_samples
"""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app import area, assessments, plots, report_template, validation, weather_check
from app.ee_analysis import build_windows, shape_result, weather_windows

API_OUT = Path(__file__).resolve().parents[1] / "app" / "sample_results.json"
WEB_OUT = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "sampleResults.json"
TODAY = date(2026, 10, 17)
MOCK = "/mock/{}.svg"


def ms(day):
    return int(datetime.fromisoformat(day).replace(hour=5, tzinfo=timezone.utc).timestamp() * 1000)


HEAVY_RAIN = {
    "rain_event_local_mm": 142.6, "max_daily_rain_local_mm": 71.3, "rain_week_region_mm": 286.4,
    "normal_week_region_mm": 74.8, "rain_month_local_mm": 512.0, "normal_month_local_mm": 268.5,
    "max_temp_c": 29.4, "days_with_data": 10,
}
HEAVY_RAIN_TEXT = (
    "The region had 286.4 mm of rain in the week before the flood, far above the normal 74.8 mm, "
    "with up to 71.3 mm in a single day. Weather like this can cause the flooding reported.",
    "ಪ್ರವಾಹಕ್ಕೂ ಹಿಂದಿನ ವಾರ ಈ ಪ್ರದೇಶದಲ್ಲಿ 286.4 ಮಿ.ಮೀ ಮಳೆಯಾಗಿದೆ, ಇದು ಸಾಮಾನ್ಯ 74.8 ಮಿ.ಮೀಗಿಂತ ತುಂಬಾ ಹೆಚ್ಚು. "
    "ಒಂದೇ ದಿನದಲ್ಲಿ 71.3 ಮಿ.ಮೀ ವರೆಗೆ ಮಳೆಯಾಗಿದ್ದು, ಇಂತಹ ಪ್ರವಾಹಕ್ಕೆ ಕಾರಣವಾಗಬಹುದು.",
)
DAMAGED_IMAGES = ["true_colour_before", "true_colour_now", "ndvi_now", "flood_mask"]

SCENARIOS = [
    {
        "plot_id": "plt_seed_1",
        "assessment_id": "asm_sampleplot1",
        "event": ("flood", "2019-08-07"),
        "raw": {"ndvi_before": 0.72, "ndvi_now": 0.25, "water_before": 0.02, "water_now": 0.86, "flood_fraction": 0.83,
                "before": "2019-07-31", "now": "2019-08-15", "before_clear": 0.94, "now_clear": 0.88},
        "series": [("2019-07-11", 0.63), ("2019-07-21", 0.69), ("2019-07-31", 0.72), ("2019-08-10", 0.31), ("2019-08-15", 0.25), ("2019-08-20", 0.27)],
        "weather": HEAVY_RAIN,
        "weather_text": HEAVY_RAIN_TEXT,
        "images": {"true_colour_before": "true_colour_before", "true_colour_now": "true_colour_after", "ndvi_now": "ndvi_after", "flood_mask": "flood_mask"},
    },
    {
        "plot_id": "plt_seed_2",
        "assessment_id": "asm_sampleplot2",
        "event": ("flood", "2019-08-07"),
        "raw": {"ndvi_before": 0.70, "ndvi_now": 0.12, "water_before": 0.01, "water_now": 0.91, "flood_fraction": 0.90,
                "before": "2019-07-31", "now": "2019-08-15", "before_clear": 0.92, "now_clear": 0.86},
        "series": [("2019-07-11", 0.61), ("2019-07-21", 0.67), ("2019-07-31", 0.70), ("2019-08-10", 0.18), ("2019-08-15", 0.12)],
        "weather": HEAVY_RAIN,
        "weather_text": HEAVY_RAIN_TEXT,
        "images": {"true_colour_before": "true_colour_before", "true_colour_now": "true_colour_after", "ndvi_now": "ndvi_after", "flood_mask": "flood_mask"},
    },
    {
        "plot_id": "plt_seed_3",
        "assessment_id": "asm_sampleplot3",
        "event": ("flood", "2019-03-12"),
        "raw": {"ndvi_before": 0.55, "ndvi_now": 0.52, "water_before": 0.01, "water_now": 0.01, "flood_fraction": 0.0,
                "before": "2019-03-05", "now": "2019-03-20", "before_clear": 0.97, "now_clear": 0.95},
        "series": [("2019-02-13", 0.53), ("2019-02-23", 0.56), ("2019-03-05", 0.55), ("2019-03-15", 0.53), ("2019-03-20", 0.52)],
        "weather": {"rain_event_local_mm": 0.4, "max_daily_rain_local_mm": 0.6, "rain_week_region_mm": 1.8,
                    "normal_week_region_mm": 3.1, "rain_month_local_mm": 4.2, "normal_month_local_mm": 9.8,
                    "max_temp_c": 36.8, "days_with_data": 10},
        "weather_text": (
            "The region had only 1.8 mm of rain in the week before the reported flood, and at most 0.6 mm in a day. "
            "There was no heavy rain at that time that could cause a flood.",
            "ವರದಿಯಾದ ಪ್ರವಾಹಕ್ಕೂ ಹಿಂದಿನ ವಾರ ಪ್ರದೇಶದಲ್ಲಿ ಕೇವಲ 1.8 ಮಿ.ಮೀ ಮಳೆಯಾಗಿದೆ, ಒಂದು ದಿನದಲ್ಲಿ ಗರಿಷ್ಠ 0.6 ಮಿ.ಮೀ. "
            "ಆ ಸಮಯದಲ್ಲಿ ಪ್ರವಾಹಕ್ಕೆ ಕಾರಣವಾಗುವಷ್ಟು ಭಾರೀ ಮಳೆ ಇರಲಿಲ್ಲ.",
        ),
        # Nothing changed on the field: both images look the same.
        "images": {"true_colour_before": "true_colour_before", "true_colour_now": "true_colour_before"},
    },
]


def build(scenario, seed_reports):
    plot = plots.get_plot(scenario["plot_id"])
    event_type, event_day = scenario["event"]
    event = date.fromisoformat(event_day)
    geometry, area_ha = validation.validate_geometry(plot["geometry"])
    ring = geometry["coordinates"][0][:-1]
    lng, lat = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    r = scenario["raw"]
    raw = {
        **{k: r[k] for k in ("ndvi_before", "ndvi_now", "water_before", "water_now", "flood_fraction", "before_clear", "now_clear")},
        "before_t": ms(r["before"]), "now_t": ms(r["now"]),
        "area_m2": area_ha * 10_000, "area_pixels": round(area_ha * 100), "centroid": [lng, lat],
        "series": {"t": [ms(d) for d, _ in scenario["series"]], "ndvi": [v for _, v in scenario["series"]]},
    }
    analysis = shape_result(raw, event_type, event, build_windows(event, today=TODAY))

    facts = {**scenario["weather"], "region_km": 50, "windows": weather_windows(event),
             "source": "ERA5-Land daily weather (ECMWF / Copernicus)"}
    verdict, reason = weather_check.rule_verdict(event_type, facts)
    weather = {"verdict": verdict, "rule_verdict": verdict, "rule_reason": reason,
               "explanation_en": scenario["weather_text"][0], "explanation_kn": scenario["weather_text"][1],
               "model": "sample", "facts": facts}
    nearby = area.nearby(lat, lng, plot["farmer_id"], event_type, event_day, seed_reports)

    request = {
        "plot_id": plot["plot_id"], "farmer_id": plot["farmer_id"], "survey_number": plot["survey_number"],
        "farmer_name": plot["farmer_name"], "village": plot["village"], "crop": plot.get("crop") or "",
        "geometry": geometry, "area_ha": area_ha,
    }
    result = assessments.build_result(scenario["assessment_id"], request, area_ha, analysis, {}, "sample", weather, nearby)
    result["images"] = {k: MOCK.format(v) for k, v in scenario["images"].items()}
    result["evidence_hash"] = assessments.evidence_hash(result)
    result["report"] = report_template.build(result, model="sample (template)")
    return result


def main():
    seed_reports = json.loads(area.SEED_PATH.read_text())["reports"]
    results = {}
    for scenario in SCENARIOS:
        result = build(scenario, seed_reports)
        results[scenario["plot_id"]] = result
        print(
            f"{scenario['plot_id']} ({result['plot']['survey_number']}): damage {result['score']['damage_score']} "
            f"({result['score']['damage_level']}), nearby {result['area']['nearby_farmers']}, "
            f"{result['verification']['status']}, severity {result['severity']['score']} ({result['severity']['level']})"
        )

    note = "Sample results for the demo plots, built by scripts/build_samples.py with the real scoring code. Illustrative numbers, not measurements."
    API_OUT.write_text(json.dumps({"_note": note, "results": results}, indent=2, ensure_ascii=False) + "\n")
    registry = [
        {k: p.get(k) for k in ("plot_id", "farmer_id", "farmer_name", "village", "survey_number", "crop", "geometry", "default_event", "area_ha", "source")}
        for p in plots.all_plots()
        if p["plot_id"] in results
    ]
    WEB_OUT.write_text(json.dumps({"_note": note, "plots": registry, "results": results}, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {API_OUT} and {WEB_OUT}")


if __name__ == "__main__":
    main()
