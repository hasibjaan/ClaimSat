# ClaimSat demo script (3 minutes)

**Before you go on stage**
- Open the deployed app in one tab, and in a second tab sign in at `/officer` with the officer code.
- Open `/status`: all three services should be green. If Earth Engine is red, the demo still works from saved results; say so honestly if asked.
- Have a field photo on the phone or laptop for the optional photo step (taken near the demo plot works best).
- Zoom the browser to 110–125% so the room can read it.

---

## 0:00 – 0:20 · The problem

> "When a flood destroys a farmer's crop, PMFBY asks them to report it within 72 hours. But the assessor often arrives days or weeks later, and by then the water has gone. It becomes the farmer's word against the insurer's. ClaimSat captures the evidence from space."

## 0:20 – 0:50 · The officer registers the land

*Officer tab → Register a plot.*

> "First, the agriculture officer registers the farmer's plot from the land records, by survey number. Farmers can't draw their own land: that's how someone would claim for more than they own."

- Point at the dashed outlines: "These are already registered. If I draw over one, it's refused."
- *(Optional, 10 s)* Draw a box over a dashed plot, fill the form, press Register: the overlap is rejected.

## 0:50 – 1:50 · The farmer checks the field

*Farmer tab → `/farmer` → Farmer ID **KA-DEMO-001** → Find my land.*

> "This is Ramesh. He enters the Farmer ID from his registration slip and sees only his own plots. His sugarcane field near the Krishna river flooded in August 2019."

- Pick the flooded plot (the date is filled in), press **Check my field**.
- While it loads (about 20–30 s): "We're pulling radar images, which see through monsoon clouds, and comparing his crop's health with the same weeks in the last three years, so a normal harvest never looks like damage."
- On the result: the score and severity, "**high confidence**, and here's why", the before/after slider, the flooded area in blue.

## 1:50 – 2:20 · The report

*Generate report → switch English / ಕನ್ನಡ → point at the fingerprint.*

> "Gemini writes a plain report in English and Kannada, but it never writes the numbers: every percentage is checked against our measurements. The fingerprint at the bottom shows if anyone changes a number later. It prints to two A4 pages to attach to the claim."

*(Optional, 15 s)* Back on the result, add a field photo: "We check its GPS and date against the plot, and we remove the location before storing it."

## 2:20 – 2:50 · The officer's village view

*Officer tab → Village dashboard.*

> "Every assessment goes into BigQuery. The officer sees the whole village: the flooded band along the river, and a visit-first list, worst-hit and most certain first. The same data feeds a Looker Studio report for insurers."

## 2:50 – 3:00 · Close

> "Evidence while it's still fresh: satellite proof of crop damage, in the farmer's language, built on Earth Engine, Vertex AI, Cloud Run, Cloud Storage and BigQuery. Thank you."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Assessment is slow | Keep talking through the loading steps. After 45 s the saved demo result appears automatically (marked "Saved demo result"). |
| Result says "Sample data" | Nothing was precomputed and live data failed. Say: "this is our sample result; live satellite access is being set up." Don't present sample numbers as real. |
| Officer pages ask for the code again | Re-enter the code (it lasts for the browser tab). |
| Map tiles are slow | Talk over it; the result panel doesn't depend on the tiles. |

## Judge questions

**Will insurers accept this?**
It's supporting evidence, not a replacement for the official assessment. It gives the farmer something dated and independent to attach, and helps insurers send assessors to the worst-hit fields first.

**What about clouds during the monsoon?**
Flood extent comes from Sentinel-1 radar, which sees through clouds. Optical crop health is the second signal, and the confidence level drops, with the reason shown, when clouds limit it.

**Can a farmer cheat?**
They can't draw or enlarge their plot: officers register plots from the land records, and overlapping or duplicate survey numbers are refused. The backend ignores any outline sent from the browser. The satellite images are independent and dated, the fingerprint shows edits to the numbers, and photos are checked against the plot's location and the event date.

**How is this different from YES-TECH or CROPIC?**
Those government programmes support the scheme at large scale. ClaimSat works plot by plot, for the farmer filing the claim, and complements them.

**How accurate is the score?**
It's a transparent, documented formula combining flood extent, crop-health loss against normal years, and rainfall shortfall. It hasn't been calibrated against field assessments yet; that's the first thing a pilot would do.

**Small plots?**
Pixels are 10 m, so a 1-hectare plot is about 100 pixels. Very small plots get lower confidence, and the report says so.

**Does it scale, and what does it cost?**
Cloud Run scales to zero when idle, and Earth Engine assesses a whole village in one pass (our village script is built for about 120 plots at once). Farmers use it free; insurers pay per assessment and states license the village view.

**Why Gemini?**
To explain the evidence in plain English and Kannada. It's given only the measured facts and a fixed format, and its percentages are checked automatically.
