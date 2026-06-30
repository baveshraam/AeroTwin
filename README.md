# AeroTwin-Edge

**Offline edge AI for aircraft structural inspection** — detect & severity-grade
defects on a Raspberry Pi 5, grow a per-tail digital twin, predict when a defect
crosses its SRM limit, and draft a manual-cited work order. Built for **Tata
Technologies InnoVent-27 · AI at the Edge · Aerospace**.

> Scope of this POC: the narrow, flawless **L0 → L3** chain (one panel, one defect,
> one tail, fully offline). L4 federated learning / L5 ops / L6 AR are deck-only
> vision. See [docs/PLAN.md](docs/PLAN.md).

## The chain

```
crack on panel
  → L0  DETECT + SIZE + GRADE   "CRITICAL crack 8.0 mm · ATA 53 stringer 14"
  → L1  TWIN                    "tail VT-AXB: was 6.0 mm, now 8.0 mm (+2.0)"
  → L2  PROGRESSION             "crosses 12 mm SRM limit in ~N cycles"
  → L3  AGENT                   drafts work order citing SRM 53-30-01 (human signs)
  → AUDIT                       hash-chained, tamper-evident
```

## Quick start (Windows / laptop)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 1) Run the whole chain once (mock detector — no model needed yet)
python -m src.pipeline

# 2) Seed a 2-scan growth story, then open the twin dashboard
python -m src.pipeline --seed
uvicorn src.l1_twin.app:app --port 8000
#   -> open http://127.0.0.1:8000

# 3) Make a synthetic test panel (ArUco marker + crack) to test real mm-sizing
python tools/make_demo_panel.py
```

Everything above runs **offline** and needs no trained model — the detector returns a
mock detection so you can demo the full twin/progression/agent/audit chain today,
then swap in the real model one piece at a time.

## Going real

| Step | What | Where |
|---|---|---|
| Train detector | YOLOv8-seg on crack data | `tools/train.py` |
| Use real model | `--real` + weights at `models/weights/crack-seg.pt` | `src/l0_detect/detect.py` |
| Real mm sizing | print an ArUco marker, put it in frame | `src/l0_detect/sizing.py` |
| Edge deploy | export INT8 ONNX, run on Pi 5 in airplane mode | see `tools/train.py` notes |
| Local LLM agent | Ollama (phi3/qwen) over the manual corpus | `src/l3_agent/agent.py` |

## Layout

```
src/
  l0_detect/   detect.py · sizing.py (ArUco) · grade.py (SRM limits)
  l1_twin/     db.py (SQLite) · app.py (FastAPI dashboard + growth chart)
  l2_progress/ paris.py (crack-growth -> cycles-to-limit)
  l3_agent/    agent.py (citation-required draft) · audit.py (hash chain)
  pipeline.py  the unbroken L0->L3 runner (--seed / --image / --real)
data/
  srm_limits.csv          allowable-damage-limit table
  manuals/srm_53-30.md    controlled corpus for the agent (ILLUSTRATIVE)
tools/
  make_demo_panel.py      synthetic panel generator (no camera needed)
  train.py                YOLOv8-seg training entrypoint
docs/
  PLAN.md · task-board.md · deck-outline.md
```

## Disclaimer

All SRM/AMM content here is **fictional and illustrative** for a POC. Never use on a
real aircraft. Real manual data is OEM-controlled.
