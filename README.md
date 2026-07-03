# AeroTwin

**An Edge-AI Digital Twin for Digital-Twin-Enabled MRO — On-Device Prognostics & Health
Management (PHM) with Explainable RUL, Condition-Based Maintenance, and Privacy-Preserving
Federated Fleet Intelligence.**

*Tata Technologies InnoVent-27 · AI at the Edge · Aerospace (subcategory 3.2.3.1).*

An offline, ITAR-safe digital twin of an aircraft fleet on a Raspberry Pi 5. It reads each
aircraft's condition, **predicts what will need maintenance before it fails**, explains why,
ranks the fleet by urgency, and produces a certifiable, audit-ready decision — no cloud.

## Docs
- **[COURSE_OF_ACTION.md](COURSE_OF_ACTION.md)** — the authoritative plan: current state, features, tech stack, roadmap.
- **[COMPLETE_SUMMARY.md](COMPLETE_SUMMARY.md)** — plain-English overview for the deck/script.
- **[problem-statement.txt](problem-statement.txt)** — canonical InnoVent submission answers.

## Run

```bash
# backend — twin API + 3D model assets
py -m src.pipeline --seed
py -m uvicorn src.l1_twin.app:app --port 8000

# frontend — React (Vite), proxies /api to the backend
cd frontend && npm install && npm run dev      # http://localhost:5173
```

## Layout
- `frontend/` — React + TypeScript + Vite app (the product UI).
- `src/l1_twin/` — FastAPI server + the digital-twin brain (health, RUL, scheduling, planner).
- `src/l2_progress/` — Monte-Carlo RUL + Bayesian learning + Paris-law growth.
- `src/l3_agent/` — agentic copilot, work-order lifecycle, hash-chained audit.
- `src/l0_detect/` — structural crack/corrosion detector + anomaly branch (the extra sensor).

Algorithms are real and tested; synthetic data (SHM stream, federation, laptop telemetry,
mock detector findings) is labelled everywhere it appears. SRM limits and money constants are
illustrative and editable.
