# Submission Runbook — AeroTwin-Edge (final assembly)

> ⏰ **DEADLINE: registration closes 05 July 2026.** As of 03 July 2026 that's ~2 days.
> The form must be completed in **one uninterrupted session** (can't save/resume), so
> gather everything below FIRST, then fill it once. — InnoVent-27 rules §4.1, §4.4.

## Status at a glance

| Deliverable | State | Owner |
|---|---|---|
| Working POC (twin + UI + API, offline) | ✅ built & verified end-to-end | done |
| Real-vs-synthetic labelling (API/UI/README) | ✅ done — see [honesty ledger](../README.md) + [honesty-qa.md](../docs/honesty-qa.md) | done |
| Demo script (3-min, click-by-click) | ✅ [docs/demo-script.md](../docs/demo-script.md) | done |
| Deck outline (12–14 slides) | ✅ [docs/deck-outline.md](../docs/deck-outline.md) | done |
| UI screenshots (dark/light/grounded/scrub) | ✅ 5 in [docs/screenshots/](../docs/screenshots/) | mostly done |
| **3-min demo video** | ⬜ record on your laptop | **YOU** |
| **PPT deck** (built on InnoVent Section-4 template) | ⬜ assemble from outline + screenshots | **YOU** |
| **College ID scans** (all members) | ⬜ scan/photo | **YOU** |
| **Google Drive folder** (public, team-named) | ⬜ create + set link public | **YOU** |
| **Pi 5 dry-run** (if hardware available) | ⬜ optional | **YOU** |

## What YOU must do (in order)

### 1. Record the 3-minute demo video
- Follow [docs/demo-script.md](../docs/demo-script.md) **verbatim** — it's timed and every
  interaction is verified. Open on `http://127.0.0.1:8000/dark`.
- **Pre-load the page** before hitting record (the airframe parses in ~4–5 s; a spinner now
  covers it, but don't film the wait).
- Pre-flight: `py -m src.pipeline --seed` then `py -m uvicorn src.l1_twin.app:app --port 8000`.
- Capture at 1080p, screen + mic. Keep it under 3:00. Save as `AeroTwin-Edge_demo.mp4`.

### 2. Grab the deck screenshots (from the REAL browser, not headless)
- Reuse the 5 already in [docs/screenshots/](../docs/screenshots/):
  `01-dark-overview` (headline: plane + ₹6.12 Cr ledger + board),
  `02-grounded-tail`, `03-light-overview`, `04-scrub-future`,
  `05-synthetic-labels-sidebar` (the SYNTHETIC STREAM / SIMULATED chips — honesty proof).
- **Grab 2 fresh ones** that show the new work:
  - a tail selected with the **amber defect pin on the fuselage** (hotspots are now on);
  - the **SHM panel** with the CUSUM change-point + "SYNTHETIC STREAM" chip.
- Full list + naming per slide is in [02_POC_Media/MEDIA_CHECKLIST.txt](02_POC_Media/MEDIA_CHECKLIST.txt).
- Headline image (deck slides 6 & 8) = `01-dark-overview.png`.

### 3. Build the PPT (InnoVent Section-4 template)
- Structure: [docs/deck-outline.md](../docs/deck-outline.md). Lead with the twin + the money.
- Put `01-dark-overview.png` big on slides 6 and 8. Label every projected number
  "engineering projection" — that honesty reads as maturity to the SMEs.
- Put the Drive video link on slide 6 as a live-demo fallback.

### 4. Google Drive folder (rules §4.2–4.3)
- Create a folder **titled exactly your team name**.
- Put in: the PPT, the demo video, POC screenshots/images, and **college ID cards for
  every team member**.
- Share → General access → **Anyone with the link** (verify it opens in an incognito window).
- Paste that link into the registration form.
- ⚠️ The claude.ai Google Drive connector isn't authorized in this environment, so this step
  is manual (or authorize it in your claude.ai connector settings first).

### 5. (Optional) Pi 5 dry-run — only if hardware is on hand
- Copy the repo to the Pi, `pip install -r requirements.txt`.
- `py -m src.pipeline --seed` then run uvicorn; open the UI in Chromium on the Pi.
- The perf guard auto-sheds shadows/blur/hi-DPI under 40 fps (lite mode); gzip cuts the
  12 MB model to ~3 MB on the wire. Expect a slower cold-load (SD-card read + parse) — that's
  why the loading spinner exists. Note real fps/temp from the terminal for slide 6.
- If it's too slow, don't force it: the laptop demo is the primary; the Pi is the "runs on a
  ₹10,000 box" claim, provable later.

## Pre-submit sanity check
- [ ] Video ≤ 3:00, audio clear, shows H1 grounding + H2 scrub + H3 ledger.
- [ ] Deck built, headline screenshot on slides 6 & 8, projections labelled.
- [ ] Drive link is PUBLIC (tested incognito) and folder is team-named.
- [ ] All member ID cards in the folder.
- [ ] Form fields drafted offline (see [00_Project_Overview/README.txt](00_Project_Overview/README.txt))
      so the one-session form goes fast.
