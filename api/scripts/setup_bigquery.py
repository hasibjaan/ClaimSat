"""Create the ClaimSat BigQuery tables and dashboard view (safe to re-run).

The dataset must already exist (see README: `bq mk --dataset PROJECT_ID:claimsat`).
Run from api/:  python -m scripts.setup_bigquery
"""

from google.cloud import bigquery

from app import config, warehouse
from app.storage import bq_client


def main():
    if not config.GCP_PROJECT or config.GCP_PROJECT.startswith("your-"):
        raise SystemExit("Set GCP_PROJECT in api/.env first.")
    client = bq_client()
    for name, schema in (("plots", warehouse.PLOTS_SCHEMA), ("assessments", warehouse.ASSESSMENTS_SCHEMA)):
        table = client.create_table(bigquery.Table(warehouse.table(name), schema=schema), exists_ok=True)
        print(f"Table ready: {table.full_table_id}")
    client.query(warehouse.view_sql()).result()
    print(f"View ready: {warehouse.table('v_dashboard')}")
    client.query(warehouse.latest_view_sql()).result()
    print(f"View ready: {warehouse.table('v_dashboard_latest')} (use this one in Looker Studio)")


if __name__ == "__main__":
    main()
