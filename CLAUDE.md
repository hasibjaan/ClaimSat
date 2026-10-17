# ClaimSat

Satellite evidence for crop insurance claims. Built in one day for the "Digital Campus on Google Cloud Hack Sprint" (Yenepoya University, 17 Oct 2026, FinTech theme). A farmer draws their plot, ClaimSat compares satellite data before and after a flood or drought, and Gemini writes an English + Kannada evidence report to attach to a PMFBY crop insurance claim. An officer dashboard shows damage across a village.

**The full build plan is in `CLAIMSAT_BUILD_PROMPT.md`.** Read it before starting any phase. It holds the formulas, datasets, phase list and acceptance checks.

## How a claim is judged (keep these rules)

- **One satellite:** every damage measurement comes from Sentinel-2: the clear image closest to 1 week before the event vs the latest clear image (`ee_analysis.assess`). NDVI = crop health, MNDWI = water. No radar, CHIRPS, Dynamic World or JRC.
- **Two-step verification** (`scoring.satellite_step`, `weather_check.check`, `scoring.verification_status`): step 1 satellite shows damage; step 2 ERA5-Land weather supports the claim (rule first, then Gemini; rule verdict if Gemini is down). Never let Gemini accuse anyone.
- **Case severity** (`scoring.severity`, `area.nearby`): 70% plot damage + 30% other farmers within 2 km / ±7 days. A single report is never "severe"; "not supported" caps at low.
- Gemini report falls back to `report_template.build` (same numbers, English + Kannada).

## Roles and pages

- `/` landing page with two entry points. `/farmer`: farmer enters their Farmer ID and picks one of **their registered plots** (view-only map, no drawing). `/officer`, `/officer/dashboard`, `/officer/register`: behind the officer access code.
- **Farmers can never draw or change a plot outline** (fraud risk: claiming more land). Officers register plots from the land records (`app/plots.py`, `POST /api/plots`); overlapping outlines and repeated survey numbers are refused. `/api/assess` takes a `plot_id` and always uses the registered outline; any geometry in the request is ignored. Keep it that way.
- Officer endpoints (`/api/plots`, `/api/dashboard`, `/api/officer/check`) require the `X-Officer-Code` header matching `OFFICER_ACCESS_CODE`. The browser keeps the code in sessionStorage (`web/src/lib/officer.js`). This is a hackathon-grade shared code, not real auth.
- Sample registered plots live in `api/app/seed_plots.json` (farmer KA-DEMO-001); demo plots from `find_demo_plots.py` are registered automatically to KA-DEMO-001 / KA-DEMO-002.

## Working rules

- Build one phase at a time. At the end of a phase, report what was built, how to run it, and each acceptance check result, then wait for "next".
- Ask before creating, changing or deleting cloud resources, and before any `gcloud run deploy`.
- No credentials or keys in code or in git. The backend uses Application Default Credentials.
- `shared/sample_result.json` is the backend/frontend contract. Change it in the same commit as any change to the result shape.
- The app is **supporting evidence, not an official loss assessment**. Never remove that note from the UI or reports, and never let Gemini invent numbers.
- Prefer the simplest thing that works for a live demo today. Don't add libraries beyond the stack below without asking.

## Stack

- **Frontend (`web/`):** Next.js 16 App Router, **JavaScript only (no TypeScript)**, Tailwind CSS, react-leaflet + Leaflet-Geoman, Chart.js via react-chartjs-2, `next/font/google` (Inter, Noto Sans Kannada).
- **Backend (`api/`):** Python 3.13, FastAPI, `earthengine-api`, `google-genai` (Vertex AI), `google-cloud-bigquery`, `google-cloud-storage`.
- **Google Cloud:** Earth Engine, Vertex AI (Gemini), Cloud Run (two services: `claimsat-api`, `claimsat-web`, region `asia-south1`), Cloud Storage, BigQuery, Looker Studio.

## Commands

```bash
# Backend
cd api && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt
cd api && uvicorn app.main:app --reload --port 8000
cd api && pytest
cd api && python -m app.ee_analysis --demo flood1

# Frontend
cd web && npm install
cd web && npm run dev        # http://localhost:3000, proxies /api/* to API_URL; /status = health page
cd web && npm run build
cd web && npm run lint

# Deploy (ask first)
gcloud run deploy claimsat-api --source api --region asia-south1   # full flags in README.md
gcloud run deploy claimsat-web --source web --region asia-south1 --set-env-vars API_URL=<api-url>
```

## Frontend conventions

- Files are `.js` / `.jsx`. Components in `src/components/` use PascalCase filenames; one component per file.
- Server components by default. Add `"use client"` only where needed (state, effects, browser APIs).
- Leaflet touches `window`, so map components are client-only: import them with `next/dynamic` and `{ ssr: false }`, and import Leaflet CSS inside those components.
- The browser only calls `/api/*` on the Next.js app. `src/app/api/[...path]/route.js` forwards to FastAPI using `process.env.API_URL` at request time. Don't call the FastAPI URL directly from the browser.
- Colours live as theme tokens in `src/app/globals.css` (Tailwind v4 `@theme`). Use the token classes, not raw hex values in components.
- Mobile first: everything must work at 375 px with no horizontal scroll. Large tap targets.
- Kannada text uses the Noto Sans Kannada font variable; don't rely on system fonts for it.
- Keep API calls in `src/lib/api.js`. `NEXT_PUBLIC_MOCK_API=1` (in `web/.env.local`) makes it return the sample result from `src/lib/sampleResult.json` (a copy of `shared/sample_result.json`) with placeholder images in `public/mock/`. Turn it off once the backend can reach Earth Engine; never set it on Cloud Run.
- The map app (`ClaimSatApp`) loads with `ssr: false` via `AppShell`, so it can use `window` and today's date freely. Leaflet-Geoman needs `window.L`, which `src/lib/leafletGlobal.js` sets; import it before Geoman.

## Backend conventions

- All Earth Engine code lives in `app/ee_analysis.py`. Scoring and confidence are pure functions in `app/scoring.py` with unit tests; they must not call Earth Engine.
- Thresholds and windows are constants in `app/config.py`, not inline numbers.
- Minimise `getInfo()` calls: build the computation server-side and fetch once.
- BigQuery writes must never fail the user's request. Log and continue.
- DEMO_MODE fallback order (`assessments.find_cached`): precomputed results in `demo_cache/results/` (from `scripts/precompute_demo.py`, source `cache`), then, for the `plt_seed_*` sample plots only, their entry in `app/sample_results.json` (source `sample`, labelled "Sample data" in the UI). That file and `web/src/lib/sampleResults.json` are generated by `python -m scripts.build_samples` with the real scoring code: re-run it after changing scoring, verification, severity or the report template. A served saved result is stored under its id so the report and photo check work. Never give real farmers' plots a sample fallback.
- User-facing errors are plain sentences; technical details go to the logs only.
- Deploy with `./deploy.sh PROJECT_ID OFFICER_CODE [GEMINI_MODEL]` (ask first). Demo-day order is in the README.
- Files go through `app/storage.py`: GCS when `GCS_BUCKET` is set, otherwise `api/.local_store/` (so local dev works before the bucket exists).
- The report: `app/report.py` sends Gemini only pre-formatted facts and a fixed JSON schema, then checks every percentage in the text against the measurements (one retry, then `number_check.ok = false`). Fixed report labels in both languages are in `web/src/lib/reportLabels.js`; Kannada wording should be checked by a native speaker.
- BigQuery code is in `app/warehouse.py` (schemas, rows, dashboard query, summary). Tables and views come from `scripts/setup_bigquery.py`; the village demo data from `scripts/batch_village.py`. Live assessments are streamed in after each `/api/assess`; tests stub `warehouse.record_assessment`.
- Farmer photo check: `app/photo_check.py` reads EXIF GPS and date, flags photos without location or date, more than 200 m from the plot, or taken before / more than 60 days after the event, and asks Gemini (vision) only whether the photo agrees with the satellite evidence. It never accuses anyone of fraud and never changes the score. Only a downscaled JPEG **without EXIF** is stored (`photos/{assessment_id}/{photo_id}.jpg`). The UI shows a green verdict only when Gemini agrees *and* there are no flags.
- Input validation lives in `app/validation.py` (mirrored for quick feedback in `web/src/lib/geo.js`). Errors are returned as `{"error": "..."}` with status 422; analysis failures as 502/504.
- When `DEMO_MODE=true`, fall back to `demo_cache/` if Earth Engine fails or takes longer than 45 seconds, and mark the result `"source": "cache"`.

## Gotchas

- **Earth Engine must be registered for the Cloud project** (noncommercial) before any EE call works: https://code.earthengine.google.com/register
- Use `COPERNICUS/S2_HARMONIZED` (top-of-atmosphere, available since 2015): surface reflectance doesn't cover India before late 2018.
- Monsoon clouds block Sentinel-2. With no clear image, the measurement is null and confidence is low; don't add other satellites to work around it (one-satellite rule).
- A harvest inside the 1-week window can look like damage; the weather check and nearby reports are the safeguard.
- ERA5-Land daily data lags a few days, so very recent claims get weather verdict "uncertain" (pending).
- `getThumbURL` links expire. Download thumbnails and store them in GCS.
- Assessments take 20–30 seconds. The UI must show progress, and the Next.js proxy must not time out before the API answers (its upstream timeout is 90 seconds).
- **Next.js 16.4 is newer than most training data.** Read `web/AGENTS.md` and the relevant guide in `web/node_modules/next/dist/docs/` before writing Next.js code. Cache Components is enabled in `next.config.mjs`; route `params` are promises (`await params`); what used to be `middleware` is now called `proxy` in Next 16. Our `/api/[...path]` route handler is a normal route, not that `proxy` file.
- `useParams()` (and other URL hooks) in a client component must sit inside `<Suspense>` with Cache Components on, or `next build` fails while prerendering (see `src/app/report/[id]/page.js`).
- **Pages are kept alive between navigations** (Cache Components uses React `<Activity>`: up to 3 recent pages are hidden, not unmounted; effects clean up and re-run, state survives). Leaflet maps break under this, so every `MapContainer` takes `key={useRemountKey()}` (`src/lib/useRemountKey.js`) and is rebuilt on return. Anything a rebuilt map must remember (drawn plot, view) lives outside it. Use the same pattern for any other imperative library that owns DOM.
- Tailwind v4 drops theme variables that no utility class uses. Colours read from JavaScript (the dashboard's `--color-level-*`) live in an `@theme static` block in `globals.css`.
- `react-hooks/set-state-in-effect` lint rule is on: don't call `setState` synchronously in an effect body; set state in the promise callback instead (see `HealthStatus.jsx`).
- `gcloud run deploy --source web` only uploads `web/`, so the frontend can't import `../shared/sample_result.json` in production builds. Copy what the mock mode needs into `web/src/lib/` (and keep it in sync).
