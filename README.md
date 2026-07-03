# AeroTwin: Edge-AI Digital-Twin MRO with Explainable RUL Prognostics and Federated Fleet Intelligence

*Tata Technologies InnoVent-27 · AI at the Edge · Aerospace (subcategory 3.2.3.1).*

An offline, ITAR-safe digital twin of an aircraft fleet on a Raspberry Pi 5. It learns from
**real flight telemetry (NGAFID, 28,935 flights around real maintenance events)** to predict
which aircraft needs maintenance before it fails, explains why by naming the exact sensors,
forecasts remaining useful life as an honest P10/P50/P90 band, ranks the fleet by urgency,
prices every decision in rupees, and produces a certifiable, audit-ready work order — no cloud.

## Docs
- **[COMPLETE_SUMMARY.md](COMPLETE_SUMMARY.md)** — the single source of truth: features, principles, stack, honesty ledger.
- **[docs/PIPELINE_OVERVIEW.md](docs/PIPELINE_OVERVIEW.md)** — technical deep-dive: modules, data shapes, ML status.
- **[docs/problem-statement.txt](docs/problem-statement.txt)** — canonical InnoVent submission answers.

## Run

```bash
# backend — twin API (serves the built frontend + 21 JSON routes)
py -m backend.pipeline --seed
py -m uvicorn backend.l1_twin.app:app --port 8000

# frontend — React (Vite), proxies /api to the backend
cd frontend && npm install && npm run dev      # http://localhost:5173

# ML — retrain the NGAFID maintenance-need model (dataset: zenodo.org/records/6624956
# extracted to data/ngafid/all_flights/)
py -m ml.ngafid_train
```

## Layout (one folder per team — push in parallel)
- `frontend/` — React + TypeScript + Vite + Three.js (the product UI + 3D twin).
- `backend/` — FastAPI + the twin brain: `l0_detect` (structural CV), `l1_twin` (twin, planner,
  NGAFID risk board), `l2_progress` (RUL physics + Bayesian learning), `l3_agent` (copilot,
  work orders, audit chain).
- `ml/` — training pipelines (`ngafid_train`, `train`, `train_anomaly`, `fetch_datasets`)
  and `ml/models/` (gitignored artifacts).
- `data/` — datasets (`ngafid/` gitignored, 5.6 GB), SRM limits, manuals, runtime twin.db.
- `docs/` — technical docs and screenshots.

Algorithms are real and tested; synthetic data (SHM stream, federation sites, laptop
telemetry) is labelled everywhere it appears. Model metrics are measured, not claimed —
see the honesty ledger in COMPLETE_SUMMARY.md §8.
