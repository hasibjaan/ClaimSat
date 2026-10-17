"""Cloud Storage and BigQuery helpers.

Files (thumbnails, assessment JSON) go to the GCS bucket when GCS_BUCKET is
set. Without a bucket (local development before cloud setup), they go to
api/.local_store/ instead, so the app still works end to end.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from google.cloud import bigquery, storage

from app import config

log = logging.getLogger("claimsat")

LOCAL_STORE = Path(__file__).resolve().parent.parent / ".local_store"


def using_gcs():
    bucket = config.GCS_BUCKET
    return bool(bucket) and not bucket.startswith("your-")


@lru_cache(maxsize=1)
def _bucket():
    return storage.Client(project=config.GCP_PROJECT or None).bucket(config.GCS_BUCKET)


def save_bytes(path, data, content_type):
    if using_gcs():
        _bucket().blob(path).upload_from_string(data, content_type=content_type)
    else:
        target = LOCAL_STORE / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def load_bytes(path):
    """Return the file's bytes, or None if it doesn't exist."""
    if using_gcs():
        blob = _bucket().blob(path)
        try:
            return blob.download_as_bytes()
        except Exception as exc:  # google.api_core.exceptions.NotFound and friends
            if getattr(exc, "code", None) == 404:
                return None
            raise
    target = LOCAL_STORE / path
    return target.read_bytes() if target.exists() else None


def save_json(path, value):
    save_bytes(path, json.dumps(value, ensure_ascii=False).encode(), "application/json")


def load_json(path):
    data = load_bytes(path)
    return None if data is None else json.loads(data)


@lru_cache(maxsize=1)
def bq_client():
    return bigquery.Client(project=config.GCP_PROJECT or None)


def check():
    """Health check: SELECT 1 in BigQuery."""
    rows = list(bq_client().query("SELECT 1 AS ok").result(timeout=20))
    if rows[0]["ok"] != 1:
        raise RuntimeError("Unexpected BigQuery result")
    return "BigQuery reachable"
