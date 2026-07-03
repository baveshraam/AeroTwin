# AeroTwin — Course of Action

**AeroTwin : An Edge-AI Digital Twin for Digital-Twin-Enabled MRO — On-Device Prognostics
& Health Management (PHM) with Explainable RUL, Condition-Based Maintenance, and
Privacy-Preserving Federated Fleet Intelligence.**

*Tata InnoVent-27 · AI at the Edge · Aerospace · Subcategory 3.2.3.1 (Digital-Twin-Enabled MRO)*

> This is the single authoritative plan. Older planning docs have been removed. The two
> companion files that remain: **[problem-statement.txt](problem-statement.txt)** (the canonical
> submission answers) and **[COMPLETE_SUMMARY.md](COMPLETE_SUMMARY.md)** (the layman overview
> for the deck/script).

---

## 1. What AeroTwin is

An offline, edge-deployed **digital twin** of an aircraft fleet. It reads each aircraft's
condition, **predicts what will need maintenance before it fails** (Prognostics & Health
Management), explains *why*, ranks the fleet by urgency, and produces a certifiable,
audit-ready decision — all on a Raspberry Pi, with no cloud (ITAR-safe).

**Primary domain = 3.2.3.1 Edge AI for Digital-Twin-Enabled MRO.** Predictive maintenance /
health monitoring (3.2.3.3) is the core depth layer; structural defect inspection (3.2.3.4)
is a secondary sensor; federated + audit (3.2.3.5) is the trust layer.

## 2. Current state (what exists today)

**Frontend — React (Vite + TS), multi-page, the live product:**
- `Overview` — 3D twin (minimalist), condition-projection scrub, **priority alerts**,
  **maintenance schedule** (condition-based, worst-first), fleet health metrics + cards.
- `Aircraft Health` — per-tail health badge, **prediction + confidence with auto-escalation**,
  open defects + Monte-Carlo RUL bands + history, between-inspection SHM.
- `Copilot & Audit` — **agentic MRO copilot** (chat, calls real twin tools, citation-gated,
  offline) + **tamper-evident hash-chain audit** (visual, live verify, evidence PDF).
- `Fleet Learning` — federated learning + differential privacy, edge telemetry, honesty notes.
- `Planning & Cost` — **secondary/last**: the prescribe-and-price economics (rupee ledger,
  what-if, priced plan, spares). Deliberately not on the main pages.

**Backend — Python (FastAPI), the twin brain (real, unit-tested):**
- Health index, condition-based scheduling vs calendar, fleet risk board.
- Monte-Carlo RUL (P10/P50/P90) + Bayesian per-tail tightening.
- Federated averaging + differential privacy (simulated sites; math is real).
- Agentic copilot (tool-router, offline; Ollama optional) + hash-chained audit + evidence PDF.
- Structural-inspection sensor: YOLOv8-seg detector + PatchCore anomaly + ArUco sizing +
  Paris-law growth (the "extra sensor").

**Honesty:** algorithms are real; where data is synthetic (SHM stream, federation sites,
laptop telemetry, and the current mock detector findings) it is labelled on screen and in the
API. SRM limits and rupee/capacity constants are illustrative and editable.

## 3. Feature set (current)

Predictive core: failure/maintenance-need prediction · Remaining Useful Life (RUL) bands ·
explainable "why" · health index · condition-based scheduling / fleet risk board ·
priority-alerts feed · prediction-confidence + auto-escalation · condition-projection ("look
into the future") · between-inspection SHM change-point alerts.
Trust & intelligence: agentic copilot (real tool-calls, citation guardrail) · tamper-evident
hash-chain audit · Bayesian per-tail learning · privacy-preserving federated learning.
Secondary: prescribe-and-price economics (rupee ledger, what-if, spares).
Extra sensor: structural crack/corrosion detection + zero-label anomaly.

## 4. Final tech stack

- **Frontend:** React · TypeScript · Vite · react-router · Three.js (3D twin) · CSS design system.
- **Backend:** FastAPI (Python) JSON API.
- **ML / Edge (target):** LightGBM + SHAP (explainable predict core) · MiniRocket (time-series) ·
  scikit-learn / PyTorch → **INT8 ONNX / TFLite** on **Raspberry Pi 5**, offline.
- **GenAI:** local **Ollama** copilot (offline) with citation-gated tool-calling.
- **Data:** **NGAFID** (real GA flight records, maintenance-labelled) + **NASA C-MAPSS**
  (turbofan RUL) for the predict core; structural image sets for the extra sensor.

## 5. Roadmap / next steps

1. **Build the real PHM predict core** — NGAFID + C-MAPSS loaders → LightGBM (+ SHAP) and/or
   MiniRocket → INT8 edge export → wire a real `/api/predict` into the twin, replacing the
   current mock findings for the predictive path. *This is the top priority.*
2. **Finalise models & datasets** (feature set, metrics: recall bias + RUL error, honestly reported).
3. **Deploy + measure on the Pi 5** (real latency/power; drop the simulated HUD flag).
4. **Serve the React build from FastAPI** (single offline artifact for the Pi). *(Frontend swap: done.)*
5. **Refresh the submission pack** (`Submission/`) + the deck to match the re-tune (PHM-first,
   crack detection as extra), using COMPLETE_SUMMARY.md as the base.

## 6. Run it

```bash
# backend (twin API + model assets)
py -m src.pipeline --seed
py -m uvicorn src.l1_twin.app:app --port 8000

# frontend (dev)
cd frontend && npm install && npm run dev      # http://localhost:5173  (proxies /api to :8000)
```
