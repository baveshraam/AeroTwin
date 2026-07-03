# AeroTwin — Plan & Strategy (north-star)

> **AeroTwin : An Edge-AI Digital Twin for Digital-Twin-Enabled MRO — On-Device Prognostics
> & Health Management (PHM) with Explainable RUL, Condition-Based Maintenance, and
> Privacy-Preserving Federated Fleet Intelligence** *(technical title; alternates in
> [problem-statement.txt](../problem-statement.txt) Q42).*
>
> Problem statement we own (InnoVent-27 · **AI at the Edge** · Aerospace): **3.2.3.1 Edge AI
> for Digital-Twin-Enabled MRO** (PRIMARY). This doc is the *direction* north-star. The
> build-history log lives in [ACTION_PLAN.md](ACTION_PLAN.md).

---

## 0. The re-tune (2026-07-03) — read this first

The project drifted too far into **crack detection**. Crack detection is a *sensor*, not the
core of MRO — and judges grade on **how deep we go in the primary domain (Edge AI · Digital
Twin · MRO), not on total feature count.** So we are re-centering:

- **NEW CORE (the graded domain):** an offline, edge-deployed **digital twin** that ingests
  **aircraft/engine sensor telemetry** and *predicts maintenance need, remaining useful life,
  and impending failure BEFORE it happens* — **Prognostics & Health Management (PHM)** —
  then prescribes and prices the action, explains *why*, and produces a certifiable work
  order + audit. Trained on **real predictive-maintenance datasets** (NGAFID flight data,
  NASA C-MAPSS turbofan).
- **EXTRA FEATURE (demoted, moved off the front page):** the structural-inspection module
  (crack/corrosion detection, sizing, Paris-law growth, anomaly branch). It feeds the *same*
  twin as one additional sensor — kept, but no longer the headline.
- **STACK:** frontend moves **HTML → React** (impressive, real tech stack). Backend stays
  FastAPI. Edge inference stays on the Raspberry Pi 5, offline.

Everything built so far (3D twin UI, RUL math, planner, ledger, agent, audit, federated
learning + DP) is **reused** — we change what feeds the twin, not the twin.

## 1. The real problem, in MRO's language

Aircraft maintenance is still driven by **fixed calendar / flight-hour intervals**. That
**over-maintains** the healthy majority (wasted downtime, cost) and **under-maintains** the
few units drifting toward failure (unscheduled removal, **AOG at ₹8L–1.25Cr/hr**, safety
risk). The industry lever is **condition-based / predictive maintenance (CBM+ / PHM)** —
but doing it per-asset in real time needs inference **where the data is born**: on the
aircraft / in the hangar (bandwidth, latency, and ITAR data-sovereignty rule out cloud).
**The edge digital twin is the missing record + the missing brain.**

## 2. What AeroTwin does (the pipeline, re-centered)

```
  SENSOR TELEMETRY (primary)            ┌─────────── all offline, on a ₹10k Pi 5 ───────────┐
  NGAFID 23-ch flight data  ─┐          │                                                   │
  C-MAPSS turbofan sensors  ─┼─► PREDICT (edge ML) ─► EXPLAIN ─► TWIN ─► PRESCRIBE+PRICE ─► ACT ─► LEARN
  [extra] crack/corrosion ──┘   LightGBM/MiniRocket   SHAP +     health   capacity-aware    agent   Bayesian +
          inspection            → maintenance-need /  GenAI      index,    fleet plan +      work    federated
                                 RUL band (PHM)       "why"      RUL, CBM  rupee ledger      order   (ITAR-safe) + DP
                                                                 vs cal.                     + audit
```

- **Predict (the new heart):** edge ML on telemetry → "this tail is trending toward an
  unplanned maintenance event / has ~N cycles of useful life left," with a P10/P50/P90 band.
- **Explain:** SHAP surfaces the top sensors ("oil-temp trend + RPM variance"); the local
  GenAI copilot turns that into a plain-English maintenance note. *Explainability is a
  headline feature — an unexplained prediction is useless to a Part-145 engineer.*
- **Twin → Prescribe → Price → Act → Learn:** the existing chain (health index, condition-
  based scheduling vs calendar, fleet risk board, capacity-constrained plan + rupee ledger,
  citation-gated agent work order, hash-chained audit, Bayesian + federated + DP learning).

## 3. Website / product structure (React) — MRO owns the front page

**Page 1 · Predictive Aircraft Health (PURE MRO — the graded core):** fleet health board,
per-tail failure/RUL prediction from sensor telemetry, the "why flagged" explainability
panel, prescribe + price (rupee ledger), agent + audit, edge-telemetry HUD. **Only MRO
here.**
**Page 2 · Structural Inspection (extra feature):** crack/corrosion detection, mm-sizing,
Paris-law growth, zero-label anomaly branch — framed as *one more sensor feeding the twin.*
**Page 3 · Fleet Learning & Edge:** federated + differential-privacy panel, the offline/
ITAR-safe edge story, the tech stack.

## 4. Build scope (narrow & deep in domain-1 beats broad)

| Layer | What | Status |
|---|---|---|
| **Ingest** sensor telemetry (NGAFID / C-MAPSS loaders) | BUILD ← new | to do |
| **Predict** edge PHM model (LightGBM/MiniRocket → RUL/maintenance-need + SHAP) | BUILD ← hero | to do |
| **Explain** SHAP → GenAI "why" note | BUILD ← hero | partial (copilot exists) |
| **Twin** health index, CBM vs calendar, fleet board | reuse | ✅ done |
| **Prescribe + price** capacity plan + rupee ledger | reuse | ✅ done |
| **Act** citation-gated agent work order + hash-chain audit | reuse | ✅ done |
| **Learn** Bayesian per-tail + federated + DP | reuse | ✅ done |
| **Frontend** React app (3 pages above) | BUILD ← new | to do |
| **Structural inspection** crack/corrosion/anomaly/sizing | demote to Page 2 | ✅ done |

## 5. Tech stack (make it impressive, and real)

- **Frontend:** React + TypeScript + Vite · react-three-fiber (3D twin) · TailwindCSS ·
  Recharts (RUL bands / SHAP).
- **Backend:** FastAPI (Python) JSON API.
- **ML / Edge:** scikit-learn · LightGBM · MiniRocket (sktime) · PyTorch (structural) →
  **ONNX / TFLite INT8** → `onnxruntime` on **Raspberry Pi 5**, fully offline.
- **GenAI:** local **Ollama** copilot (offline), citation-gated tool-calling into the twin.
- **Data:** NGAFID (CC BY 4.0), NASA C-MAPSS (public). See [DATASETS.md](DATASETS.md).

## 6. Datasets & models — direction (specifics finalised later)

- **Primary — PHM:** **NGAFID** (real GA flight telemetry, 23 sensors @1Hz, ~29k flights,
  labelled before/after unplanned maintenance) → maintenance-need classification;
  **NASA C-MAPSS** (turbofan run-to-failure) → RUL regression.
- **Model direction:** **LightGBM / MiniRocket** — tiny, CPU-fast on the Pi, and (LightGBM)
  **explainable via SHAP**, which feeds the "why" story. Deep time-series nets (InceptionTime)
  are a stretch/benchmark only. *Exact model + feature set to be finalised.*
- **Extra — structural:** existing crack/corrosion/anomaly datasets (see DATASETS.md §Structural).

## 7. Honesty rules (judges will probe) — unchanged

- The **algorithms are real; synthetic data is always labelled** (on-screen chip + API flag).
- Never fake an FPS/accuracy number — CPU-only vs accelerator stated explicitly; report
  **POD / recall bias**, not just mAP; report RUL error honestly.
- SRM limits and rupee/capacity economics stay **illustrative** — OEM/operator-controlled,
  calibrate before real use. The novelty is the **edge twin + PHM + prescribe→price→certify
  combination**, not any single model.

## 8. Sequence

- **Now:** re-tune docs (this pass); stand up NGAFID/C-MAPSS loaders + a first edge PHM model;
  scaffold the React app with MRO on page 1.
- **Next:** train + SHAP + wire the "why" note; migrate the 3D twin into React (react-three-fiber);
  move structural inspection to page 2.
- **Then:** offline dry-run on the Pi; record the demo; finalise the deck ([deck-outline.md](deck-outline.md)).
