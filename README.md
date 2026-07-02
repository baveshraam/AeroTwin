# AeroTwin-Edge

### The ₹10,000 box that decides which jet to ground — and which to fly.

**Edge AI for Digital Twin-Enabled MRO.** An offline, ITAR-safe structural **digital
twin** for an aircraft fleet, running on a Raspberry Pi 5. It grows a living per-tail
condition record, forecasts each defect's remaining life to its repair-manual limit,
and turns the whole fleet's health into a **rupee-priced maintenance plan** — it doesn't
just *predict*, it **prescribes** which aircraft to service, defer, or ground, and
**prices** every call against the blind calendar. No cloud. Tamper-proof audit trail.
Built for **Tata Technologies InnoVent-27 · AI at the Edge · Aerospace**.

> **predict → prescribe → price.** Defect detection is the *sensor*; the twin is the
> *product*; the prescriptive fleet plan is the *payoff*. See [docs/PLAN.md](docs/PLAN.md).

## The real-world problem

Airline & MRO structural maintenance runs on a fixed **calendar / hard-time interval** —
a blind clock that is wrong in two expensive directions at once:

- **Over-maintenance.** Healthy jets get pulled off-line for checks they didn't need —
  wasted downtime, labour, parts. Most of a fleet is healthy most of the time.
- **Under-maintenance.** The few tails with a fast-growing crack can outrun the calendar
  and reach a limit *between* checks — the safety + AOG (aircraft-on-ground,
  ~₹8L–1.25Cr/hr) tail-risk.

There is no continuous per-tail condition record to schedule against, and cloud can't
hold it (ITAR-isolated hangars). **AeroTwin-Edge is the missing system-of-record — and
the planner that acts on it.**

## What it does: predict → prescribe → price

```
inspection (any sensor: camera today, borescope/eddy-current later)
  → SENSE      size + severity-grade the defect vs its SRM allowable limit
  → TWIN       append to this tail's record; health index (0–100); how much did it grow?
  ── PREDICT ──────────────────────────────────────────────────────────────────
  → RUL        remaining useful life in flight cycles to the SRM limit
  ── PRESCRIBE ────────────────────────────────────────────────────────────────
  → DECIDE     PULL FORWARD (fast grower) | SAFE TO DEFER (healthy) | GROUND (beyond limit)
  → PLAN       optimise across the fleet under real hangar capacity → who to service now
  ── PRICE ────────────────────────────────────────────────────────────────────
  → LEDGER     ₹ downtime recovered + ₹ AOG risk avoided − ₹ risk carried = net value
  → AGENT      draft the manual-cited work order (human certifying-staff signs)
  → AUDIT      hash-chained, tamper-evident — the regulator's evidence trail
```

On the seeded 4-tail demo fleet the twin outputs, live and offline: *ground 1, service
2, safely defer 1 → **~₹6 Cr net value this window** vs the blind calendar* — every
rupee traceable to the constants in [src/l1_twin/planner.py](src/l1_twin/planner.py).

## Quick start (Windows / laptop)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 1) Run one inspection through the whole twin chain (mock sensor — no model needed)
python -m src.pipeline

# 2) Seed a 4-tail fleet -> prints the prescriptive plan + rupee ledger
python -m src.pipeline --seed

# 3) Open the 3D digital twin: orbitable aircraft shaded by health, clickable defect
#    hotspots (RUL P10/P50/P90 bands), a time-scrub that grows cracks and grounds jets
#    live, fleet strip, rupee ledger, and edge telemetry HUD.
python tools/vendor_three.py                   # once, online: vendors Three.js -> then offline forever
uvicorn src.l1_twin.app:app --port 8000        # -> http://127.0.0.1:8000  (classic view at /classic)

# 4) The twin's decision + money math in isolation (self-checks)
python -m src.l1_twin.twin                      # health / RUL / condition-based call
python -m src.l1_twin.planner                   # capacity-constrained plan + ₹ ledger

# 5) Get real training data + train the detector (see the dataset hunt below)
python tools/fetch_datasets.py --list          # ranked real datasets + how to pull each
python tools/train.py --stage base             # YOLOv8-seg on the public crack corpus
python tools/train.py --stage adapt --data data/datasets/aircraft/data.yaml   # aircraft fine-tune

# 6) Make a synthetic test panel (ArUco marker + crack) for real mm-sizing
python tools/make_demo_panel.py
```

Everything runs **offline** and needs no trained model — the sensor returns a mock
detection so the full predict → prescribe → price story demos today; swap in the real
detector later, one piece at a time.

## Going real (swap the sensor, keep the twin)

| Step | What | Where |
|---|---|---|
| Train detector | YOLOv8-seg on crack data | `tools/train.py` |
| Use real model | `--real` + weights at `models/weights/crack-seg.pt` | `src/l0_detect/detect.py` |
| Real mm sizing | print an ArUco marker, put it in frame | `src/l0_detect/sizing.py` |
| Calibrate economics | set the ₹ + capacity constants per operator | `src/l1_twin/planner.py` |
| Edge deploy | export INT8 ONNX, run on Pi 5 in airplane mode | see `tools/train.py` notes |
| Local LLM agent | Ollama (phi3/qwen) over the manual corpus | `src/l3_agent/agent.py` |

## Layout

```
src/
  l0_detect/   detect.py · sizing.py (ArUco) · grade.py (SRM limits)   ← the SENSOR
  l1_twin/     db.py (record) · twin.py (health/RUL/fleet/CBM + forward-projection)
               planner.py (capacity plan + rupee ledger + spares + what-if)  ← THE PAYOFF
               shm.py (between-inspection sensor-fusion + CUSUM alert)
               federated.py (ITAR-safe shared growth priors, FedAvg)
               app.py (3D twin UI + JSON API) · view.py (classic view)
               static/index.html (Three.js 3D twin, vendored, offline)
  l2_progress/ paris.py (crack-growth + Monte-Carlo RUL with P10/P50/P90 bands)
  l3_agent/    agent.py (citation guardrail) · copilot.py (deterministic tool-router; optional Ollama)
               workorder.py (draft→sign→close lifecycle + tamper-evident PDF) · audit.py
  pipeline.py  the unbroken sense → twin → predict → prescribe → price → agent runner
data/
  srm_limits.csv · manuals/srm_53-30.md (controlled corpus, ILLUSTRATIVE)
tools/
  fetch_datasets.py (real dataset registry) · train.py (2-stage YOLOv8-seg → INT8 ONNX)
  vendor_three.py (offline Three.js) · make_demo_panel.py · render_dashboard.py
docs/
  PLAN.md · task-board.md · deck-outline.md
```

## Why this wins (the moat)

Every team can build a defect detector, and a good team can build a health dashboard.
AeroTwin-Edge goes a level higher: **predict → prescribe → price**, offline, in an ITAR
hangar. Under one roof, all running: an **interactive 3D structural twin** you scrub
forward in flight cycles to watch defects grow and jets ground themselves; **uncertainty-
aware RUL** (Monte-Carlo P10/P50/P90, not false precision); **continuous SHM** between
inspections (sensor-fusion + CUSUM); a **capacity-aware fleet plan quantified in rupees**
with spares pre-staging and live what-ifs; a **citation-gated agentic copilot** — a
deterministic offline tool-router by default (optional local LLM via Ollama) — that
tool-calls the twin; a **work-order lifecycle** closed out with a **tamper-evident PDF**;
and **ITAR-safe federated learning** that shares growth priors, never imagery. No single
competitor combines all of it. One avoided AOG day pays for the ₹10,000 node many times over.

## What's real vs. synthetic (honesty ledger)

We label every synthetic source in the API, the UI, and here — nothing is presented as
more "live" than it is. The *algorithms* are real and tested; what's synthetic is the
*data feeding them*, because we don't have field sensor hardware or an ITAR data-sharing
agreement for a POC.

| Component | Algorithm (real) | Data (synthetic — why) | Where it's flagged |
|---|---|---|---|
| **Defect detection** | YOLOv8-seg pipeline + SRM grading | mock detector returns a fixed size (`model_version: mock-v0`) — real model trains separately | API `model_version`; UI header **"SYNTHETIC DATA · mock-v0"** badge |
| **SHM stream** | EWMA + CUSUM change-point detector (standard SHM) | physics-motivated synthetic strain/AE/vibration signal — no onboard sensors on a laptop | API `synthetic:true`; UI **"SYNTHETIC STREAM"** chip + panel caption |
| **Federated learning** | FedAvg + Laplace differential privacy | 4 simulated hangars drawing from one true distribution — no field federation yet | API `simulated:true`; UI **"SIMULATED"** chip + panel note |
| **Edge telemetry HUD** | real `psutil` values on the Pi | fps/latency/cpu/power are simulated on a laptop | API `simulated:true`; UI fps `*` + hover note |
| **Copilot** | deterministic intent-parse → real twin tool-calls, citation guardrail | no LLM by default (optional Ollama) | UI "deterministic tool-router"; answer footer |

## Disclaimer

All SRM/AMM content, Paris-law constants, and the rupee/capacity economics are
**illustrative** for a POC and must be calibrated per operator/structure before any real
use. Never use on a real aircraft. Real manual data is OEM-controlled.
