"""BigQuery: plots and assessments for the officer dashboard and Looker Studio.

Tables are created by `python -m scripts.setup_bigquery`. Writing to BigQuery
must never fail a user's request, so callers wrap record_assessment().
"""

import logging
from datetime import datetime, timezone

from google.cloud import bigquery

from app import config
from app.storage import bq_client

log = logging.getLogger("claimsat")

PLOTS_SCHEMA = [
    bigquery.SchemaField("plot_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("farmer_id", "STRING"),
    bigquery.SchemaField("survey_number", "STRING"),
    bigquery.SchemaField("farmer_name", "STRING"),
    bigquery.SchemaField("village", "STRING"),
    bigquery.SchemaField("crop", "STRING"),
    bigquery.SchemaField("geom", "GEOGRAPHY"),
    bigquery.SchemaField("area_ha", "FLOAT64"),
    bigquery.SchemaField("created_at", "TIMESTAMP"),
]

ASSESSMENTS_SCHEMA = [
    bigquery.SchemaField("assessment_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("plot_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("event_type", "STRING"),
    bigquery.SchemaField("event_date", "DATE"),
    bigquery.SchemaField("ndvi_before", "FLOAT64"),
    bigquery.SchemaField("ndvi_after", "FLOAT64"),
    bigquery.SchemaField("ndvi_baseline_after", "FLOAT64"),
    bigquery.SchemaField("ndvi_loss", "FLOAT64"),
    bigquery.SchemaField("flood_fraction", "FLOAT64"),
    bigquery.SchemaField("rain_deficit", "FLOAT64"),
    bigquery.SchemaField("crop_fraction", "FLOAT64"),
    bigquery.SchemaField("damage_score", "FLOAT64"),
    bigquery.SchemaField("damage_level", "STRING"),
    bigquery.SchemaField("confidence", "STRING"),
    bigquery.SchemaField("evidence_hash", "STRING"),
    bigquery.SchemaField("source", "STRING"),
    bigquery.SchemaField("created_at", "TIMESTAMP"),
]

CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}
AFFECTED_LEVELS = ("moderate", "severe")


def table(name):
    return f"{config.GCP_PROJECT}.{config.BQ_DATASET}.{name}"


def view_sql():
    return f"""
CREATE OR REPLACE VIEW `{table("v_dashboard")}` AS
SELECT
  a.assessment_id, a.plot_id, p.farmer_id, p.survey_number, p.farmer_name, p.village, p.crop, p.geom, p.area_ha,
  a.event_type, a.event_date, a.ndvi_before, a.ndvi_after, a.ndvi_baseline_after,
  a.ndvi_loss, a.flood_fraction, a.rain_deficit, a.crop_fraction,
  a.damage_score, a.damage_level, a.confidence, a.evidence_hash, a.source,
  a.created_at AS assessed_at
FROM `{table("assessments")}` AS a
-- A registered plot is written again with each assessment: keep its latest row.
JOIN (
  SELECT * FROM `{table("plots")}`
  WHERE TRUE
  QUALIFY ROW_NUMBER() OVER (PARTITION BY plot_id ORDER BY created_at DESC) = 1
) AS p USING (plot_id)
"""


def latest_view_sql():
    """One row per plot (its latest assessment), for Looker Studio."""
    return f"""
CREATE OR REPLACE VIEW `{table("v_dashboard_latest")}` AS
SELECT * FROM `{table("v_dashboard")}`
WHERE TRUE
QUALIFY ROW_NUMBER() OVER (PARTITION BY plot_id ORDER BY assessed_at DESC) = 1
"""


# --- Rows (pure functions) ---------------------------------------------------------------


def polygon_wkt(geometry):
    """GeoJSON Polygon (outer ring) -> WKT, which BigQuery reads as GEOGRAPHY."""
    ring = geometry["coordinates"][0]
    return "POLYGON((" + ", ".join(f"{lng} {lat}" for lng, lat in ring) + "))"


def rows_for(result):
    """(plot_row, assessment_row) for one assessment in the shared result shape."""
    plot = result["plot"]
    metrics = result["metrics"]
    created_at = result.get("created_at") or datetime.now(timezone.utc).isoformat()
    plot_row = {
        "plot_id": plot["plot_id"],
        "farmer_id": plot.get("farmer_id") or None,
        "survey_number": plot.get("survey_number") or None,
        "farmer_name": plot.get("farmer_name") or None,
        "village": plot.get("village") or None,
        "crop": plot.get("crop") or None,
        "geom": polygon_wkt(plot["geometry"]),
        "area_ha": plot.get("area_ha"),
        "created_at": created_at,
    }
    assessment_row = {
        "assessment_id": result["assessment_id"],
        "plot_id": plot["plot_id"],
        "event_type": result["event"]["type"],
        "event_date": result["event"]["date"],
        **{
            k: metrics.get(k)
            for k in (
                "ndvi_before", "ndvi_after", "ndvi_baseline_after", "ndvi_loss",
                "flood_fraction", "rain_deficit", "crop_fraction",
            )
        },
        "damage_score": result["score"]["damage_score"],
        "damage_level": result["score"]["damage_level"],
        "confidence": result["confidence"]["level"],
        "evidence_hash": result.get("evidence_hash"),
        "source": result.get("source"),
        "created_at": created_at,
    }
    return plot_row, assessment_row


def summarise(plots):
    """Summary cards and the 'visit first' order for the dashboard."""
    affected = [p for p in plots if p["damage_level"] in AFFECTED_LEVELS]
    visit_first = sorted(
        (p for p in plots if p.get("damage_score") is not None),
        key=lambda p: (-p["damage_score"], CONFIDENCE_RANK.get(p.get("confidence"), 3)),
    )
    return {
        "summary": {
            "plots": len(plots),
            "severe": sum(p["damage_level"] == "severe" for p in plots),
            "moderate": sum(p["damage_level"] == "moderate" for p in plots),
            "low_or_none": sum(p["damage_level"] in ("low", "none") for p in plots),
            "unknown": sum(p["damage_level"] == "unknown" for p in plots),
            "hectares_affected": round(sum(p.get("area_ha") or 0 for p in affected), 2),
        },
        "visit_first": [p["assessment_id"] for p in visit_first[:15]],
    }


# --- BigQuery calls --------------------------------------------------------------------------


def record_assessment(result):
    """Stream one assessment (and its plot) into BigQuery."""
    plot_row, assessment_row = rows_for(result)
    client = bq_client()
    for name, row in (("plots", plot_row), ("assessments", assessment_row)):
        errors = client.insert_rows_json(table(name), [row])
        if errors:
            raise RuntimeError(f"BigQuery insert into {name} failed: {errors}")


def load_rows(name, rows, replace_source=None):
    """Batch-load rows (used by scripts). Optionally delete earlier rows of one source first."""
    client = bq_client()
    if replace_source:
        if name == "assessments":
            sql = f"DELETE FROM `{table(name)}` WHERE source = @source"
        else:
            sql = (
                f"DELETE FROM `{table(name)}` WHERE plot_id IN "
                f"(SELECT plot_id FROM `{table('assessments')}` WHERE source = @source)"
            )
        params = [bigquery.ScalarQueryParameter("source", "STRING", replace_source)]
        client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
    schema = PLOTS_SCHEMA if name == "plots" else ASSESSMENTS_SCHEMA
    job = client.load_table_from_json(
        rows,
        table(name),
        job_config=bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND"),
    )
    job.result()


def dashboard(limit=1000):
    """Latest assessment per plot, with GeoJSON geometry, plus summary."""
    sql = f"""
SELECT
  assessment_id, plot_id, farmer_id, survey_number, farmer_name, village, crop, area_ha, event_type,
  CAST(event_date AS STRING) AS event_date, damage_score, damage_level, confidence,
  ndvi_loss, flood_fraction, rain_deficit, source,
  FORMAT_TIMESTAMP('%FT%TZ', assessed_at) AS assessed_at,
  ST_ASGEOJSON(geom) AS geojson
FROM `{table("v_dashboard")}`
WHERE TRUE
QUALIFY ROW_NUMBER() OVER (PARTITION BY plot_id ORDER BY assessed_at DESC) = 1
ORDER BY damage_score DESC
LIMIT @limit
"""
    params = [bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    rows = bq_client().query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result(timeout=30)
    return [dict(row) for row in rows]
