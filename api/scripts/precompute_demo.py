"""Save real results for every demo plot, so the demo works even if Earth Engine is slow.

For each plot in demo_cache/demo_plots.json (from find_demo_plots.py) this runs
the full assessment, saves the evidence images to demo_cache/assets/, asks
Gemini for the bilingual report, and writes demo_cache/results/<id>.json.
With DEMO_MODE=true the API serves these when a live call fails or takes
longer than 45 seconds (marked "Saved demo result" in the UI).

Run from api/:  python -m scripts.precompute_demo [--skip-report]
"""

import argparse
import json
import re
import time

from app import assessments, ee_analysis, plots, report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skip-report", action="store_true", help="don't call Gemini")
    args = parser.parse_args()

    demos = assessments.demo_plots()
    if not demos:
        raise SystemExit("No demo plots yet. Run `python -m scripts.find_demo_plots` first.")
    ee_analysis.init_ee()
    (assessments.DEMO_CACHE / "results").mkdir(parents=True, exist_ok=True)

    for demo in demos:
        started = time.perf_counter()
        plot = plots.get_plot(f"plt_{demo['id']}")
        request = assessments.validate_request(
            {
                "plot_id": plot["plot_id"],
                "event_type": demo["event_type"],
                "event_date": demo["event_date"],
                "season_window": demo.get("season_window"),
            }
        )
        # Fixed ids, so re-running replaces the same files (ids allow [a-z0-9] only).
        assessment_id = "asm_demo" + re.sub(r"[^a-z0-9]", "", demo["id"].lower())
        call = (request["geometry"], request["event_type"], request["event_date"], request["season_window"])

        analysis = ee_analysis.assess(*call)
        thumbs = ee_analysis.thumbnails(*call)
        asset_dir = assessments.DEMO_CACHE / "assets" / assessment_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        for name, png in thumbs.items():
            (asset_dir / f"{name}.png").write_bytes(png)

        result = assessments.build_result(assessment_id, request, request["area_ha"], analysis, thumbs, "live")
        if not args.skip_report:
            try:
                result["report"] = report.generate(result)
            except Exception as exc:  # the cache is still useful without a report
                print(f"  ! report failed for {demo['id']}: {exc}")

        (assessments.DEMO_CACHE / "results" / f"{demo['id']}.json").write_text(json.dumps(result, ensure_ascii=False))
        score = result["score"]
        print(
            f"{demo['id']:>9}: score {score['damage_score']} ({score['damage_level']}), "
            f"confidence {result['confidence']['level']}, {len(thumbs)} images, "
            f"report {'yes' if result.get('report') else 'no'}, {time.perf_counter() - started:.0f}s"
        )

    print(f"\nSaved {len(demos)} results in {assessments.DEMO_CACHE / 'results'}")


if __name__ == "__main__":
    main()
