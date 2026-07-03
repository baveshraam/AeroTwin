# Live Demo Script — AeroTwin-Edge (~3 min, click-by-click)

> ⚠️ **RE-TUNE PENDING (2026-07-03):** this script describes the *current* structural-twin
> HTML demo. Under the MRO re-tune (see [PLAN.md](PLAN.md)), the demo will be **re-led by
> predictive health**: telemetry in → **failure/RUL prediction + the "why" (SHAP top sensors)**
> → fleet board → ledger → work order → audit, in the new **React** app with MRO on Page 1 and
> structural inspection on Page 2. Rewrite this walk once the PHM core + React app land; the
> hero moments below (grounding, time-scrub, rupee ledger) still apply, just after the
> prediction beat leads. The structural/crack steps move to the Page-2 "extra sensor" segment.

> Rehearse against this exact path. Every interaction below was verified against the
> running UI + API on 2026-07-03. Times are target cues, not hard limits.
> **Open on the dark theme:** `http://127.0.0.1:8000/dark` — the near-black hangar makes
> the red "grounded" wash and the amber ledger pop on a projector. (`/` is the light/cream
> theme; keep it as a backup if the room is very bright.)

## Before you present (do NOT skip)
1. Seed a clean fleet: `py -m src.pipeline --seed` (4 tails, the four stories).
2. Start the server: `py -m uvicorn src.l1_twin.app:app --port 8000`.
3. **Pre-load the page and leave it open** — the textured airframe is a 12.5 MB model that
   parses in ~4–5 s on a laptop (longer on the Pi). A spinner + "Loading airframe… X/Y MB"
   now covers the wait (no more blank stage), and the server gzips the model to ~3 MB on the
   wire — but still pre-load so judges never watch a spinner.
4. Confirm the HUD (top-right) is ticking and the board shows 4 tails, VT-AXE grounded.

## The 3 hero moments (must be bulletproof — rehearse these most)
- **H1 — a tail gets grounded.** VT-AXE red, health ring 0, "GROUND — beyond-limit".
- **H2 — time-scrub crack growth.** Drag "Run twin forward" → healthy tails decay to
  amber/red, board re-sorts, "grounded / flying" counter updates. Verified smooth
  (scrub API ~20 ms/step, GPU held 60–120 fps).
- **H3 — the rupee ledger re-prices live.** ₹ net-value figure count-up animates every time
  the plan changes (load, scrub, what-if).

---

## The walk

**0:00 — 0:20 · The box.**
Page is already open on `/dark`, VT-AXE auto-selected (grounded, red).
> "This is an offline structural digital twin for a whole fleet, running on a ₹10,000
> Raspberry Pi — no cloud, ITAR-safe. It doesn't just *find* damage. It decides which jet
> to ground and which to fly, and prices that decision in rupees."
Gesture at the red airframe + the "GROUNDED" badge. **[H1]**

**0:20 — 0:50 · Fleet risk board — predict → prescribe.** (right panel, "Fleet risk board")
> "Every tail, ranked worst-first by structural health, not by the calendar."
Point down the board: VT-AXE `SERVICE NOW`, VT-AXD/VT-AXB `SERVICE THIS WINDOW`,
VT-AXC `DEFER`. Note the coloured health bars (red→amber→cyan) and the ₹2.00 Cr risk tags.

**0:50 — 1:20 · The money slide — price.** (top of right panel, "Prescriptive plan · rupee ledger")
> "Here's what nobody else does — we price it. Ground one, service two, safely defer one:
> **₹6.12 crore of net value this maintenance window** versus a blind calendar — downtime
> recovered plus AOG risk avoided."
Let the ₹6.12 Cr figure sit. This is the win-the-room number.

**1:20 — 2:00 · Time-scrub — the twin runs forward. [H2 + H3]**
Grab the "Run twin forward" slider (bottom-left) and drag slowly to ~+9,000 cyc.
> "This is the twin projecting each crack forward under Paris-law growth. Watch the healthy
> jets decay, the board re-rank itself, and the ledger re-price — live, offline, in real time."
Watch tails flip amber→red, the "grounded / flying" counter climb, the ₹ figure re-count.
Drag back to **now** to reset.

**2:00 — 2:30 · Healthy vs grounded — the per-tail story.**
Click **VT-AXC** in the bottom fleet strip (or board).
> "The same twin says this one is *healthier* than the calendar assumes — safe to defer,
> recovering downtime we'd otherwise waste."
Ring turns cyan (75), badge reads SAFE TO EXTEND. Scroll the "Open defects" panel: point at
the **growth sparkline** and the **RUL band (P10/P50/P90, Monte-Carlo)** — the crack's
trajectory to the SRM limit. Then click **VT-AXB** to show a fast grower with 2 scans of history.
Click the **defect card** (or the amber pin on the fuselage) — the camera flies to the marker
sitting on the airframe skin, and the SHM panel below shows the **CUSUM change-point** on the
synthetic between-inspection stream (tagged "SYNTHETIC STREAM", so nothing is oversold).

**2:30 — 2:50 · Prescribe → agent → audit.** (scroll right panel to "Certification")
> "The agent drafts the work order — but only if it can cite the SRM. Human signs off.
> Part-145 stays in charge."
Click **Draft (agent)** → **Sign** → the status chips advance DRAFT→SIGNED. Point at
"↓ Tamper-evident evidence PDF · hash-chained".
(Optional, if time) Copilot: click the suggestion chip *"SRM limit for a crack at ATA 53?"* →
show the tool-trace answer (offline, citation-gated). It's a **deterministic tool-router** —
it calls the real twin tools, not an LLM — so say that plainly; the footer already labels it.

**2:50 — 3:00 · Close.**
> "Predict, prescribe, price — the whole chain, offline, on the edge. One avoided AOG day
> pays for the box for years."

---

## If something breaks (recovery lines)
- **Board shows "⚠ Can't reach the twin API — Retrying…"** → the API is down. It now
  self-heals (retries every 2.5 s), so just restart uvicorn and it recovers on its own; the
  other panels degrade to "unavailable" rather than freezing. Hard-refresh if needed.
- **Model didn't appear / spinner stuck** → you loaded live; wait for the "Loading airframe…"
  progress to finish, or refresh. Always pre-load. A red "airframe failed to load" message
  means the model assets aren't being served — check the `/model-assets` mount.
- **Scrub feels laggy on the Pi** → drag in bigger steps; the re-price is server-side and
  fast, any lag is GPU compositing, not the math (the perf guard auto-sheds effects <40 fps).
- **Fallback:** keep the recorded demo video (Drive, slide 6) ready to play.

## Honesty notes for Q&A (say these before a judge asks)
Full spoken-out-loud paragraphs per source are in **[honesty-qa.md](honesty-qa.md)** — skim
those before presenting. The short version:
- The detector is currently **mock-v0** (real crack detector mid-training). The twin math,
  pricing, and audit are real; the *findings feeding them* are seeded until the model lands.
  The header shows a "SYNTHETIC DATA · mock-v0" badge, so it's already stated on screen.
- The edge telemetry HUD (fps/latency/temp/power) is **simulated on the laptop** (the `*`
  next to FPS) — real psutil values come from the Pi when deployed.
- **SHM** panel is tagged "SYNTHETIC STREAM", **Federated** panel is tagged "SIMULATED" — in
  both, the algorithm (CUSUM detector; FedAvg + differential privacy) is real, the sensor/site
  data is synthetic. Point at the chips if asked — the labeling is deliberate, not hidden.
