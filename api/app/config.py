"""Settings read from environment variables (and api/.env when running locally)."""

import os

from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.getenv("GCP_PROJECT", "")
GCP_REGION = os.getenv("GCP_REGION", "asia-south1")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GCS_BUCKET = os.getenv("GCS_BUCKET", "")
BQ_DATASET = os.getenv("BQ_DATASET", "claimsat")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
# Shared code that unlocks the officer pages (dashboard, plot registration). Empty = locked.
OFFICER_ACCESS_CODE = os.getenv("OFFICER_ACCESS_CODE", "")

# OAuth scopes Earth Engine needs when using Application Default Credentials.
EE_SCOPES = [
    "https://www.googleapis.com/auth/earthengine",
    "https://www.googleapis.com/auth/cloud-platform",
]

# --- Earth Engine datasets ---------------------------------------------------
# Top-of-atmosphere Sentinel-2 (since 2015). Surface reflectance doesn't cover
# India for the 2016-2018 baseline years, so we use TOA everywhere.
S2_COLLECTION = "COPERNICUS/S2_HARMONIZED"
CS_PLUS_COLLECTION = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
CS_BAND = "cs"
S1_COLLECTION = "COPERNICUS/S1_GRD"
GSW_IMAGE = "JRC/GSW1_4/GlobalSurfaceWater"
CHIRPS_COLLECTION = "UCSB-CHG/CHIRPS/DAILY"
DYNAMIC_WORLD_COLLECTION = "GOOGLE/DYNAMICWORLD/V1"

SCALE_M = 10            # Sentinel-2 / Sentinel-1 / Dynamic World pixel size
CHIRPS_SCALE_M = 5566   # CHIRPS pixel size (~0.05 degrees)

# --- Thresholds ----------------------------------------------------------------
CS_CLEAR_THRESHOLD = 0.6          # Cloud Score+ value at or above which a pixel is clear
CLEAR_IMAGE_MIN_FRACTION = 0.5    # an image counts as a "clear observation" above this
FLOOD_VV_THRESHOLD_DB = -16.0     # post-event VV backscatter below this looks like water
FLOOD_CHANGE_THRESHOLD_DB = -3.0  # ...and it must have dropped by at least this much
PERMANENT_WATER_OCCURRENCE = 50   # JRC occurrence (%) above which water is permanent

# --- Time windows (days relative to the event date E, inclusive) ---------------
BEFORE_WINDOW = (-30, -1)
AFTER_WINDOW = (5, 30)
RADAR_PRE_WINDOW = (-30, -1)
RADAR_POST_WINDOW = (0, 10)
SERIES_WINDOW = (-90, 60)
SERIES_BIN_DAYS = 10
CROPLAND_LOOKBACK_DAYS = 365
DROUGHT_SEASON_DEFAULT = ((6, 1), (9, 30))  # (month, day) start and end
DROUGHT_BEFORE_DAYS = 30                     # "before" = the 30 days before the season
BASELINE_YEARS = 3
RAIN_BASELINE_YEARS = 20

EVENT_TYPES = ("flood", "drought", "other")
