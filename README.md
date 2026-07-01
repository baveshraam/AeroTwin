# AeroTwin-Edge

**Edge AI for Digital Twin-Enabled MRO** — a living, per-tail *and* per-fleet
structural digital twin that runs fully offline on a Raspberry Pi 5, turns every
inspection into a condition record, predicts remaining useful life, and tells the
maintenance planner **which aircraft to pull forward and which are safe to defer** —
instead of maintaining the whole fleet on a blind calendar. Built for **Tata
Technologies InnoVent-27 · AI at the Edge · Aerospace**.

> **Problem statement: Digital Twin-Enabled MRO.** Inspection/defect-detection is the
> *sensor* here, not the product. The product is the twin: the system-of-record that
> remembers each tail's condition over time and drives condition-based maintenance
> (CBM+). See [docs/PLAN.md](docs/PLAN.md).

## The real-world problem

Airline & MRO structural maintenance is scheduled on a fixed **calendar / hard-time
interval**. That is wrong in two expensive directions at once:

- **Over-maintenance.** Healthy jets get pulled off-line for checks they didn't need —
  wasted downtime, wasted labour, wasted parts. Most of a fleet is healthy most of the time.
- **Under-maintenance.** The few tails with a fast-growing crack or advancing corrosion
  can outrun the calendar and reach a limit *between* scheduled checks — the safety and
  AOG (aircraft-on-ground, ~₹8L–1.25Cr/hr) tail-risk.

And the data that would fix this — "did this crack grow since the last C-check on *this*
tail?" — lives on paper task cards and siloed systems. There is no continuous condition
history per tail. Cloud can't rescue it either: ITAR/OEM hangars are network-isolated
and imagery legally cannot leave the site.

**AeroTwin-Edge is the missing system-of-record.** A digital twin per tail number,
built and queried at the edge, that converts inspections into a condition trajectory and
a scheduling decision.

## What the twin does

```
inspection (any sensor: camera today, borescope/eddy-current later)
  → SENSE      size + severity-grade the defect vs its SRM allowable limit
  → TWIN       append to this tail's structural record; how much did it grow?
  → PREDICT    remaining useful life (RUL) in flight cycles to the SRM limit
  → DECIDE     health index (0–100) + condition-based call:
               PULL FORWARD (fast grower) | SAFE TO EXTEND (healthy) | GROUND (beyond limit)
  → FLEET      rank every tail worst-first — the planner's morning risk board
  → AGENT      draft the manual-cited work order (human certifying-staff signs)
  → AUDIT      hash-chained, tamper-evident — the regulator's evidence trail
```

The **fleet risk board** is the money shot: one screen, every tail ranked by structural
health, each with a condition-based scheduling call and the delta vs the dumb calendar
(*"VT-AXD: pull forward 4,500 cycles"* / *"VT-AXC: safe to extend 30,000 cycles"*).

## Quick start (Windows / laptop)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 1) Run one inspection through the whole twin chain (mock sensor — no model needed)
python -m src.pipeline

# 2) Seed a 4-tail demo FLEET, then open the twin dashboard + fleet risk board
python -m src.pipeline --seed
uvicorn src.l1_twin.app:app --port 8000        # -> http://127.0.0.1:8000
#   ...or, with nothing but Python installed:
python tools/render_dashboard.py               # writes data/dashboard_preview.html

# 3) Check the condition-based scheduling math in isolation
python -m src.l1_twin.twin                      # twin self-check

# 4) Make a synthetic test panel (ArUco marker + crack) for real mm-sizing
python tools/make_demo_panel.py
```

Everything runs **offline** and needs no trained model — the sensor returns a mock
detection so you can demo the full twin / fleet / prediction / scheduling / agent / audit
story today, then swap in the real detector one piece at a time.

## Going real (swap the sensor, keep the twin)

| Step | What | Where |
|---|---|---|
| Train detector | YOLOv8-seg on crack data | `tools/train.py` |
| Use real model | `--real` + weights at `models/weights/crack-seg.pt` | `src/l0_detect/detect.py` |
| Real mm sizing | print an ArUco marker, put it in frame | `src/l0_detect/sizing.py` |
| Edge deploy | export INT8 ONNX, run on Pi 5 in airplane mode | see `tools/train.py` notes |
| Local LLM agent | Ollama (phi3/qwen) over the manual corpus | `src/l3_agent/agent.py` |
| More sensors | borescope, eddy-current, tap-test → same twin record | `src/l1_twin/db.py` schema |

## Layout

```
src/
  l0_detect/   detect.py · sizing.py (ArUco) · grade.py (SRM limits)   ← the SENSOR
  l1_twin/     db.py (SQLite record) · twin.py (health/RUL/fleet/CBM)  ← THE TWIN (product)
               app.py + view.py (dashboard: fleet risk board + per-tail growth)
  l2_progress/ paris.py (crack-growth → cycles-to-limit)
  l3_agent/    agent.py (citation-required draft) · audit.py (hash chain)
  pipeline.py  the unbroken sense → twin → predict → decide → agent runner
data/
  srm_limits.csv          allowable-damage-limit table
  manuals/srm_53-30.md    controlled corpus for the agent (ILLUSTRATIVE)
tools/
  make_demo_panel.py      synthetic panel generator (no camera needed)
  render_dashboard.py     dump the dashboard to static HTML (no web stack)
  train.py                YOLOv8-seg training entrypoint
docs/
  PLAN.md · task-board.md · deck-outline.md
```

## Why this wins (the moat)

Edge **+** a per-tail twin **+** fleet-level condition-based scheduling **+** a
citation-gated agent **+** a tamper-evident audit trail — offline, in an ITAR hangar. A
crack detector is a commodity; the *twin that decides what to fix, when, on which tail,
and proves it to the regulator* is the product. One avoided AOG day pays for the edge
node many times over.

## Disclaimer

All SRM/AMM content here is **fictional and illustrative** for a POC. Paris-law and
scheduling constants are illustrative and must be calibrated per structure before any
real use. Never use on a real aircraft. Real manual data is OEM-controlled.
