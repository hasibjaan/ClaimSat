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

# --- The one satellite: Sentinel-2 -------------------------------------------
# Every damage measurement comes from Sentinel-2: one image ~1 week before the
# event and the most recent image of the plot. From each image we read crop
# health (NDVI, bands B8/B4) and standing water (MNDWI, bands B3/B11).
# Cloud Score+ is Sentinel-2's own cloud mask.
S2_COLLECTION = "COPERNICUS/S2_HARMONIZED"
CS_PLUS_COLLECTION = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
CS_BAND = "cs"
SCALE_M = 10

# --- Weather, used only to verify a claim (step 2), never to score damage ----
ERA5_DAILY = "ECMWF/ERA5_LAND/DAILY_AGGR"
ERA5_SCALE_M = 11132
WEATHER_REGION_KM = 50       # rain upstream can flood fields: look at the region too
WEATHER_NORMAL_YEARS = 10    # "normal" = same dates in the previous 10 years

# --- Thresholds ----------------------------------------------------------------
CS_CLEAR_THRESHOLD = 0.6          # Cloud Score+ value at or above which a pixel is clear
CLEAR_IMAGE_MIN_FRACTION = 0.5    # an image is usable if this share of the plot is clear
WATER_MNDWI_THRESHOLD = 0.0       # MNDWI above this = open water
MIN_CROP_NDVI = 0.2               # below this before the event, there was little crop to lose

# --- Time windows (days relative to the event date E, inclusive) ---------------
BEFORE_TARGET_DAY = -7            # the "before" image: the clear one closest to 1 week before
BEFORE_SEARCH = (-12, -3)
NOW_SEARCH = (0, 14)              # the "now" image: the latest clear one (up to today)
SERIES_WINDOW = (-30, 14)

# --- Nearby reports (case severity) ----------------------------------------------
NEARBY_RADIUS_KM = 2
NEARBY_WINDOW_DAYS = 7

EVENT_TYPES = ("flood", "drought", "other")
