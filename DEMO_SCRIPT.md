# ClaimSat demo script (3 minutes)

**Before you go on stage**
- Open the app in one tab; in a second tab sign in at `/officer` with the officer code.
- Demo farmer: **KA-DEMO-001** (Ramesh). His three plots each show a different rule:

| Plot | What happened | What ClaimSat says |
|---|---|---|
| **112/3** | Flood after very heavy rain; 6 neighbours reported it | **Verified**, severity **Severe** (82) |
| **118/1** | Heavy damage, but nobody nearby reported it | **Verified**, severity held at **Moderate** (60) |
| **124/2** | A "flood" claimed in the dry season | **Not supported**: no change in the images, no rain |

- If the app shows **"Sample data"**, say so if asked: the numbers are illustrative while live satellite access is being set up.
- Zoom the browser to 110–125% so the room can read it.

---

## 0:00 – 0:20 · The problem

> "When a flood destroys a farmer's crop, PMFBY asks them to report it within 72 hours. But the assessor often arrives days or weeks later, when the water has gone. It becomes the farmer's word against the insurer's. ClaimSat gives both sides evidence they can check."

## 0:20 – 0:40 · Land comes from the records

*Officer tab → Register a plot.*

> "Plots are registered by the agriculture officer from the land records. Farmers can't draw their own land, and overlapping or duplicate survey numbers are refused, so nobody can claim for more land than they own."

## 0:40 – 1:30 · A genuine claim: 112/3

*Farmer tab → `/farmer` → **KA-DEMO-001** → Survey no. **112/3** → Check my field.*

> "Ramesh picks his plot. We take one Sentinel-2 satellite image from a week before the flood and the latest one, and read crop health and standing water from both."

- Point at the slider: **Before · 31 Jul** vs **Now · 15 Aug**: "83% of his field is newly under water; crop health down 65%."
- **Two-step verification:** "Step 1, the satellite shows severe damage. Step 2, our AI checks the weather record: 286 mm of rain in the region that week against a normal of 75. Both agree: **Verified**."
- **Case severity 82, Severe:** "And it isn't just Ramesh: six other farmers within 2 km reported the same flood."

## 1:30 – 2:05 · The rules at work: 118/1 and 124/2

*Check another field → **118/1**.*

> "Same kind of damage here, but nobody nearby has reported anything. One report alone is never rated severe: it stays **Moderate** until neighbours confirm it."

*Check another field → **124/2**.*

> "This one claims a flood in March, in the dry season. The images show no change, and the AI weather check finds under 2 mm of rain that week. **Not supported.** We don't call anyone a cheat; we show the officer what the evidence says."

## 2:05 – 2:30 · The report

*Back to 112/3 → Generate report → switch English / ಕನ್ನಡ.*

> "The farmer gets a report in English and Kannada, with both verification steps, the image dates and an evidence fingerprint that shows if any number is changed later. It prints on two A4 pages to attach to the claim."

## 2:30 – 2:50 · The officer's view

*Officer tab → Village dashboard.*

> "Every assessment goes into BigQuery. The officer sees the whole village and a visit-first list, so field visits go where the damage is."

## 2:50 – 3:00 · Close

> "Evidence while it's still fresh: one satellite, two checks, and the whole neighbourhood behind each claim. Built on Earth Engine, Vertex AI, Cloud Run, Cloud Storage and BigQuery. Thank you."

---

## If something goes wrong

| Problem | What to do |
|---|---|
| Assessment is slow | Talk through the loading steps; after 45 s the saved or sample result appears automatically. |
| Officer pages ask for the code again | Re-enter it (it lasts for the browser tab). |
| Map tiles are slow | Talk over it; the result panel doesn't depend on the tiles. |

## Judge questions

**How does it work, in one sentence?**
One Sentinel-2 image from a week before vs the latest one gives crop health and standing water; an AI weather check and reports from nearby farmers then verify the claim and set its severity.

**Why only one satellite?**
Simpler and more transparent: one image pair, two readings (crop health and water), the same for every claim. Weather is used only to verify, never to score damage.

**What about monsoon clouds?**
Sentinel-2 can't see through thick cloud. When the field is hidden, the app says so (low confidence) and uses the next clear image. The weather check and nearby reports still work, and the photo check adds ground evidence.

**Can a farmer cheat?**
They can't change their land outline. A claim must show damage in the images **and** match the weather record; one report alone can't be severe; a photo is checked against the plot's location and date; and the fingerprint shows edits to the numbers.

**Is the AI deciding who gets paid?**
No. Gemini checks the weather plausibility and explains it in plain language; a transparent rule runs alongside it. ClaimSat is supporting evidence; the insurer and officer decide.

**How is this different from YES-TECH or CROPIC?**
Those government programmes support the scheme at large scale. ClaimSat works plot by plot, for the farmer filing the claim, and complements them.

**How accurate is it?**
The formulas are documented and transparent, but not yet calibrated against field assessments; that's the first thing a pilot would do. Droughts show less in a one-week comparison; the weather check carries more weight there.

**Does it scale, and what does it cost?**
Cloud Run scales to zero when idle and Earth Engine can assess a whole village in one pass. Farmers use it free; insurers pay per assessment and states license the village view.
