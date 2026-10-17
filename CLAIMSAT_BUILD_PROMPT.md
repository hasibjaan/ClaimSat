# ClaimSat: phase-by-phase build instructions

You are helping a student team build **ClaimSat** in a one-day hackathon ("Digital Campus on Google Cloud Hack Sprint", FinTech theme). The app must run on Google Cloud. Read this whole file and `CLAUDE.md` before writing any code.

## What ClaimSat does

Crop insurance claims under PMFBY (India's crop insurance scheme) are slow and disputed, because damage is assessed by field visits that often happen too late. ClaimSat gives the farmer independent, time-stamped satellite evidence for their own plot:

1. The user draws their plot on a satellite map and picks an event type (flood / drought / other), an event date and a crop.
2. The backend uses Earth Engine to compare vegetation health (NDVI) before and after the event, against the same plot's 3-year baseline, and measures flooded area with Sentinel-1 radar (which sees through monsoon clouds).
3. Gemini writes a bilingual (English + Kannada) evidence report.
4. Every assessment is stored in BigQuery, and an insurer/officer dashboard shows damage across a whole village or taluk.

ClaimSat is **supporting evidence, not an official loss assessment**. Say this in the UI and in every report.

## How to work

- Work **one phase at a time**. At the end of each phase, stop and report: what you built, how to run it, the result of each acceptance check, and anything the team must do by hand. Then wait for the user to say "next" before starting the next phase.
- Keep it simple. This is a one-day build. No user accounts, no TypeScript, no state-management libraries, no component libraries beyond what's listed here.
- Before creating or changing cloud resources (buckets, datasets, service accounts, deploys), show the exact commands and ask first.
- Never put credentials or keys in code. Use Application Default Credentials (ADC) on the backend; no API keys are needed.
- If something in this file turns out to be wrong (a dataset ID, an SDK call, a package version), check the official docs, fix it, and tell the user what you changed.
- `shared/sample_result.json` is the contract between backend and frontend. If you change the result shape, update that file in the same change.

## Fixed tech stack

| Part | Choice |
|---|---|
| **Frontend** | **Next.js (App Router) + Tailwind CSS + JavaScript (no TypeScript)**, in `web/`. Scaffold with `npx create-next-app@latest web --js --tailwind --eslint --app --src-dir --import-alias "@/*"` and pin the installed versions in `package.json`. |
| Map | Leaflet + react-leaflet, with Leaflet-Geoman (free) for polygon drawing, Esri World Imagery basemap (with attribution). Map components must be client-only: `"use client"` plus `next/dynamic` with `ssr: false`. Check that the react-leaflet major version matches the installed React version. |
| Charts | Chart.js + react-chartjs-2 |
| Fonts | `next/font/google`: Inter for English, Noto Sans Kannada for Kannada |
| Backend | Python 3.13, FastAPI, Uvicorn, in `api/` |
| Satellite analysis | `earthengine-api` (Earth Engine Python API) |
| AI | `google-genai` SDK with Vertex AI (`genai.Client(vertexai=True, project=..., location=...)`). Model name comes from env var `GEMINI_MODEL`; default to the current Gemini Flash model on Vertex AI. Use structured JSON output. |
| Storage | Cloud Storage (images), BigQuery (plots, assessments) |
| Deploy | Two Cloud Run services in `asia-south1`: `claimsat-api` (FastAPI, Dockerfile) and `claimsat-web` (Next.js with `output: "standalone"`, Dockerfile). |
| Dashboard | Looker Studio on BigQuery, plus the in-app `/dashboard` page as a backup |

**How the frontend talks to the backend:** the browser only ever calls the Next.js app. A catch-all route handler at `web/src/app/api/[...path]/route.js` forwards requests to the FastAPI service, using the `API_URL` env var read at request time. This avoids CORS, and avoids baking the API URL in at build time. It must forward the method, query string, body (JSON and multipart) and response headers, and allow responses that take up to 60 seconds.

## Repo layout

```
CLAUDE.md
CLAIMSAT_BUILD_PROMPT.md
README.md
shared/
  sample_result.json      contract for the assessment result JSON
api/
  app/
    main.py               FastAPI app and routes
    config.py             env vars and constants
    ee_analysis.py        all Earth Engine logic
    scoring.py            pure functions: damage score, level, confidence (unit tested, no EE calls)
    report.py             Gemini call
    storage.py            Cloud Storage and BigQuery helpers
    photo_check.py        Phase 5 (stretch)
  scripts/
    find_demo_plots.py
    precompute_demo.py
    batch_village.py
  demo_cache/             precomputed JSON results and demo plots
  tests/test_scoring.py
  Dockerfile
  requirements.txt
  .env.example
web/
  src/app/
    layout.js             fonts, metadata, global disclaimer footer
    globals.css           Tailwind import and theme tokens
    page.js               main map + assessment screen
    report/[id]/page.js   printable bilingual report
    dashboard/page.js     officer dashboard
    api/[...path]/route.js  proxy to FastAPI
  src/components/
    PlotMap.jsx           Leaflet map with polygon drawing (client-only)
    AssessForm.jsx
    LoadingSteps.jsx
    ResultsPanel.jsx
    ScoreGauge.jsx
    ConfidenceBadge.jsx
    BeforeAfterSlider.jsx
    NdviChart.jsx
    LanguageToggle.jsx
    DashboardMap.jsx      (client-only)
  src/lib/
    api.js                fetch helpers for /api/*
    format.js             number, date and area formatting
  next.config.mjs
  Dockerfile
  .env.example
```

## Environment variables

**api/**: `GCP_PROJECT`, `GCP_REGION=asia-south1`, `VERTEX_LOCATION` (default `us-central1`), `GEMINI_MODEL`, `GCS_BUCKET`, `BQ_DATASET=claimsat`, `DEMO_MODE` (`true` = serve cached results when live Earth Engine calls fail or time out).

**web/**: `API_URL` (FastAPI base URL; `http://localhost:8000` locally, the `claimsat-api` Cloud Run URL in production).

## Remote-sensing rules (follow these exactly unless you find an error)

**Datasets**
- Optical: `COPERNICUS/S2_HARMONIZED` (Sentinel-2 top-of-atmosphere, available since 2015). Use this rather than the surface-reflectance collection, because surface reflectance isn't available over India for the earliest baseline years. Use the same collection for every window so comparisons stay consistent.
- Cloud mask: `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`, linked with `linkCollection`, keep pixels where `cs >= 0.6`.
- Radar: `COPERNICUS/S1_GRD`, `instrumentMode == "IW"`, band `VV`.
- Permanent water mask: the latest JRC Global Surface Water collection (`JRC/GSW1_x/GlobalSurfaceWater`, band `occurrence`), treat `occurrence > 50` as permanent water and exclude it from flood results.
- Rainfall: `UCSB-CHG/CHIRPS/DAILY`.
- Cropland check: `GOOGLE/DYNAMICWORLD/V1`, mean of the `crops` probability band over the 12 months before the event.

**Time windows** (event date = E)
- Flood: before = E−30 to E−1 days; after = E+5 to E+30 days. Radar: pre = E−30 to E−1 (median VV), post = E to E+10 (minimum VV).
- Drought: compare the season window the user picks (default: June 1 to September 30 of that year) against the same window in the baseline years.
- Other (hail, pest, fire): same windows as flood, NDVI only.
- Baseline: the same "after" window in each of the previous 3 years, averaged.

**Metrics** (all are means over the plot polygon at 10 m scale)
- `ndvi_before`, `ndvi_after`, `ndvi_baseline_after` from median cloud-masked composites. NDVI = normalizedDifference(B8, B4).
- `ndvi_loss = clamp((ndvi_baseline_after − ndvi_after) / max(ndvi_baseline_after, 0.1), 0, 1)`. This is the share of normal vegetation that is missing, which avoids mistaking a normal harvest for damage.
- `flood_fraction` = share of plot pixels where post VV < −16 dB AND (post − pre) < −3 dB AND not permanent water. Keep both thresholds in `config.py`.
- `rain_deficit = clamp(1 − season_rain / baseline_rain, 0, 1)`, with the CHIRPS baseline = mean of the same window over the previous 20 years.
- `crop_fraction` = mean Dynamic World `crops` probability.
- `clear_obs_before`, `clear_obs_after` = number of Sentinel-2 images in each window with at least 50% of plot pixels cloud-free.
- `ndvi_series` = per-image mean NDVI over the plot for E−90 to E+60 (by day offset from E), for this year and for the baseline mean (for the chart).

**Damage score (0–100, a documented heuristic)**
- Flood: `100 × (0.5 × flood_fraction + 0.5 × ndvi_loss)`
- Drought: `100 × (0.6 × ndvi_loss + 0.4 × rain_deficit)`
- Other: `100 × ndvi_loss`
- Damage level from the score: `none` < 15 ≤ `low` < 35 ≤ `moderate` < 60 ≤ `severe`. This is computed in `scoring.py`, never by Gemini.

**Confidence**
- High: ≥3 clear observations in both windows, plot ≥ 20 pixels, `crop_fraction ≥ 0.6`, and for floods at least one radar image in each window.
- Low: any window has 0 clear observations (and, for floods, no radar either), or `crop_fraction < 0.3`, or plot < 10 pixels.
- Medium: everything else.
- Always return the list of reasons behind the confidence level.

**Input validation** (on the backend, mirrored in the form for quick feedback): valid polygon, area 0.05–20 hectares, inside India's bounding box, event date between 2016-01-01 and 7 days ago.

## UI direction

- Clean, trustworthy, government-service feel: white and off-white surfaces, one deep green accent, amber for warnings, red only for severe damage. Define colours as theme tokens in `globals.css` and use them through Tailwind classes; don't scatter hex values through components.
- Large tap targets and readable text, since farmers and field agents will use phones outdoors.
- Every screen shows the note "Supporting evidence, not an official loss assessment" (in the footer from `layout.js`).
- Must work at 375 px width with no horizontal scrolling. On phones the side panel becomes a bottom sheet over the map.

---

## Phase 0: Setup and skeleton (target: 45 min)

1. Create the `api/` layout, `requirements.txt`, `api/.env.example` and `api/Dockerfile`.
2. Scaffold `web/` with the `create-next-app` command above. Set `output: "standalone"` in `next.config.mjs`, add `web/Dockerfile` (multi-stage, runs `node server.js` on `$PORT`), and add the API proxy route handler.
3. List the manual steps for the team, with exact commands:
   - `gcloud auth login` and `gcloud auth application-default login`
   - enable APIs: Earth Engine, Vertex AI, Cloud Run, Cloud Build, Artifact Registry, Cloud Storage, BigQuery
   - **register the Cloud project for Earth Engine (noncommercial use)** at https://code.earthengine.google.com/register. Tell the team to do this first, because approval can take time.
   - create a service account for `claimsat-api` with roles: Earth Engine Resource Viewer, Service Usage Consumer, Vertex AI User, BigQuery Data Editor, BigQuery Job User, Storage Object Admin (on the bucket)
   - create the GCS bucket and BigQuery dataset
4. Implement `GET /api/health` in FastAPI, which checks Earth Engine (a trivial `getInfo()`), Vertex AI (a one-word Gemini call) and BigQuery (a `SELECT 1`), and returns the status of each.
5. Make the Next.js home page call `/api/health` through the proxy and show the three statuses.
6. Deploy both services to Cloud Run (`claimsat-api` first, then `claimsat-web` with `API_URL` set to the API's URL).

**Acceptance:** the deployed `claimsat-web` URL shows all three services as OK, and `npm run build` and `npm run lint` pass in `web/`.

## Phase 1: Earth Engine analysis (target: 2 h)

1. Implement `ee_analysis.assess(geometry_geojson, event_type, event_date, season_window=None)` returning every metric above, the Sentinel-2 and Sentinel-1 image dates used, and the plot area in hectares and pixels. Batch the server-side computation so a single assessment makes as few `getInfo()` calls as possible.
2. Implement `ee_analysis.thumbnails(...)` that produces PNGs (true-colour before, true-colour after, NDVI after, flood mask over the true-colour image) for the plot plus a 300 m buffer, with the plot outline drawn on. Use `getThumbURL`, download the PNGs and upload them to GCS (thumbnail URLs expire).
3. Implement `scoring.py` (damage score, damage level, confidence and reasons) as pure functions, with unit tests in `tests/test_scoring.py`.
4. Write `scripts/find_demo_plots.py`: for the August 2019 Krishna river floods in Belagavi/Bagalkot districts, Karnataka, scan cropland along the river, and propose 3 plot-sized polygons (about 1 ha) with high flood fraction, plus 1 nearby unflooded control plot. Do the same for one drought plot from the 2023 Karnataka kharif drought. Confirm the actual flood dates from the radar data rather than assuming them. Save the plots to `api/demo_cache/demo_plots.json`.
5. A CLI test: `python -m app.ee_analysis --demo flood1` prints the metrics and the runtime.
6. Make sure the output matches `shared/sample_result.json`; update the sample if the real output needs extra fields.

**Acceptance:** the flooded demo plots show high `flood_fraction` and clear `ndvi_loss`, the control plot shows low values on both, unit tests pass, and one assessment finishes in under 30 seconds.

## Phase 2: API and map UI (target: 2 h)

1. `POST /api/assess` with `{geometry, event_type, event_date, crop, farmer_name, village, season_window?}`. It validates input, runs the analysis and thumbnails, scores the result, and returns JSON in the shape of `shared/sample_result.json`, with thumbnail URLs served via `GET /api/assets/{path}`, which streams from GCS.
2. If `DEMO_MODE=true` and the live call fails or takes longer than 45 seconds, return the cached result from `demo_cache/` for a matching demo plot, marked `"source": "cache"`.
3. `GET /api/demo-plots` returns the demo plots so the UI can load them in one click.
4. Frontend, in `web/src/app/page.js` and the components listed above:
   - full-screen satellite map centred on Karnataka (`PlotMap.jsx`), with a polygon draw tool and a live area readout in hectares and acres
   - side panel (bottom sheet on phones) with `AssessForm.jsx` (event type, date, crop, farmer name, village) and "Load demo plot" buttons
   - `LoadingSteps.jsx`, which explains what's happening ("Fetching radar images…", "Comparing with the last 3 years…"), because the call can take 20–30 seconds
   - `ResultsPanel.jsx`: `ScoreGauge`, `ConfidenceBadge` with reasons, `BeforeAfterSlider`, flood mask image, `NdviChart` (this year vs baseline), and a "Generate report" button linking to `/report/[id]`
   - clear inline errors for bad input and failed requests
5. Build the frontend against `shared/sample_result.json` first (a mock mode in `src/lib/api.js`), so it doesn't wait for the backend.

**Acceptance:** drawing a demo plot and submitting shows correct results at both laptop and 375 px widths, bad input (tiny polygon, future date) shows a clear error, and `npm run build` passes.

## Phase 3: Gemini evidence report (target: 1.5 h)

1. In `report.py`, add `POST /api/report/{assessment_id}`, which calls Gemini with the metrics JSON and a structured output schema:
   `{summary_en, summary_kn, findings: [{title_en, title_kn, detail_en, detail_kn}], limitations_en, limitations_kn, recommended_next_steps_en, recommended_next_steps_kn}`.
   Store the result with the assessment and return it. `GET /api/assessments/{assessment_id}` returns the full assessment, including the report once generated.
2. Prompt rules for Gemini: use only the numbers provided, never invent values, dates or sources; write plain language a farmer can understand; state the damage level and confidence exactly as given, with the confidence reasons; always say this is supporting evidence for the claim, not an official assessment; mention the PMFBY 72-hour reporting window in the next steps.
3. `web/src/app/report/[id]/page.js` renders the report:
   - header with ClaimSat name, assessment ID, generated timestamp
   - plot details: farmer, village, crop, centroid coordinates, area, event
   - before/after images, flood mask, NDVI chart
   - damage score and level, confidence and reasons, findings, limitations, next steps
   - data sources with exact image acquisition dates
   - the SHA-256 hash of the metrics JSON (computed on the backend), labelled "Evidence fingerprint", so later tampering is detectable
   - `LanguageToggle` (English / ಕನ್ನಡ), using the Noto Sans Kannada font for Kannada
   - Tailwind `print:` styles plus an `@page` A4 rule in `globals.css`, so "Print → Save as PDF" gives a clean document with no map controls or buttons
4. Stretch: a QR code on the printed report linking to the online version.

**Acceptance:** a report for a demo flood plot reads correctly in both languages, every number in it matches the metrics JSON, and print preview fits A4 cleanly.

## Phase 4: BigQuery and the officer dashboard (target: 1.5 h)

1. BigQuery tables:
   - `plots`: `plot_id STRING, farmer_name STRING, village STRING, crop STRING, geom GEOGRAPHY, area_ha FLOAT64, created_at TIMESTAMP`
   - `assessments`: `assessment_id STRING, plot_id STRING, event_type STRING, event_date DATE, ndvi_before FLOAT64, ndvi_after FLOAT64, ndvi_baseline_after FLOAT64, ndvi_loss FLOAT64, flood_fraction FLOAT64, rain_deficit FLOAT64, crop_fraction FLOAT64, damage_score FLOAT64, damage_level STRING, confidence STRING, evidence_hash STRING, source STRING, created_at TIMESTAMP`
   - a view `v_dashboard` joining the two
2. Write every assessment from `/api/assess` to BigQuery. A BigQuery failure must not break the user's request; log it instead.
3. `scripts/batch_village.py`: generate 50–150 plot polygons over cropland in the demo flood area (use Dynamic World to keep only cropland), assess them in one server-side `reduceRegions` pass rather than one call per plot, and load the results into BigQuery with `source = "batch"`.
4. `GET /api/dashboard` returns plots (as GeoJSON) with their scores, plus summary counts.
5. `web/src/app/dashboard/page.js`: `DashboardMap` with plots coloured by damage level, summary cards (plots, severe, moderate, estimated hectares affected), and a "Visit first" list sorted by damage score and confidence.
6. Write step-by-step instructions in the README for building the Looker Studio report on `v_dashboard` (Google Maps chart with the `geom` field, a scorecard, a table).

**Acceptance:** the dashboard shows the batch village with a visible damage pattern along the river, and new assessments from the main UI appear in BigQuery.

## Phase 5 (stretch): Photo corroboration (target: 1 h, only if time allows)

1. `POST /api/photo-check` with an image upload (multipart) and an `assessment_id`.
2. Read EXIF GPS and timestamp. Report the distance from the plot and the time from the event, and say plainly if GPS is missing.
3. Send the photo and the satellite metrics to Gemini (vision) and ask whether the photo is consistent with the satellite evidence (standing water, flattened or dried crop, healthy crop), returning `{consistent: bool, observations_en, observations_kn}`.
4. Add a photo upload to `ResultsPanel` and show the result there and in the report.

**Acceptance:** a flooded-field photo near the plot comes back "consistent"; a photo with no GPS is flagged.

## Phase 6: Demo hardening and handover (target: 1 h)

1. Run `scripts/precompute_demo.py` to cache results, images and reports for every demo plot. Confirm the full UI works with Earth Engine turned off in `DEMO_MODE`.
2. Check all error states, loading states and the 375 px layout once more. Run `npm run build` and `npm run lint`.
3. Deploy the final versions of both services and run the full demo flow on the deployed URL.
4. Finish the README: one-paragraph pitch, architecture diagram (Mermaid), list of Google Cloud services and what each does, how to run locally, how to deploy, formulas and their limitations, data sources and licences.
5. Write `DEMO_SCRIPT.md`: a 3-minute walkthrough (farmer story → draw plot → results → bilingual report → officer dashboard), plus answers to likely judge questions: insurer acceptance, clouds, fraud resistance, small plots, scaling and cost, business model, and how this differs from the government's YES-TECH and CROPIC programmes (those work at district scale for the government; ClaimSat gives plot-level evidence to the farmer).

**Acceptance:** the full demo runs end to end on the deployed URL in under 3 minutes, and it still works if Earth Engine is slow.

---

## Parallel work for a team of 4

Once Phase 0 is done, everyone works against `shared/sample_result.json`:
- **Person A, frontend:** Phase 2 UI using the mock mode in `src/lib/api.js`, then the Phase 4 dashboard page.
- **Person B, Earth Engine:** Phase 1.
- **Person C, backend + AI:** Phase 2 API routes, the Phase 3 Gemini call, then the report page.
- **Person D, data + pitch:** Phase 4 BigQuery and Looker Studio, slides, architecture diagram, demo script.
