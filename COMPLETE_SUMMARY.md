# AeroTwin — Complete Project Summary

**AeroTwin : An Edge-AI Digital Twin for Digital-Twin-Enabled MRO — On-Device Prognostics
& Health Management (PHM) with Explainable RUL, Condition-Based Maintenance, and
Privacy-Preserving Federated Fleet Intelligence.**

*Tata InnoVent-27 · AI at the Edge · Aerospace · Subcategory 3.2.3.1 (Digital-Twin-Enabled MRO)*

> This document explains the whole project in plain language. If you have never seen the
> code, you can read this top-to-bottom and understand what AeroTwin is, why it matters, how
> it works, and what it is built with. Use it as the base for the presentation and the script.

---

## 1. The 30-second version (say this first)

Airlines and maintenance companies (MRO = **Maintenance, Repair & Overhaul**) still service
aircraft mostly by a **fixed calendar** — "every X flight-hours, do this check" — regardless
of how healthy that specific aircraft actually is. That is wrong in two expensive ways at
once: healthy aircraft get pulled out of service for checks they didn't need (wasted money),
and the few aircraft that are quietly degrading can fail *between* checks (a grounded aircraft
costs **₹8 lakh–1.25 crore per hour**).

**AeroTwin is a small, offline computer (a Raspberry Pi) that sits at the aircraft and acts as
a "digital twin" — a living, predictive health record of every aircraft in the fleet.** It
reads the aircraft's own sensor data, **predicts which aircraft will need maintenance before it
fails**, explains *why* in plain language, ranks the whole fleet by risk, works out the smartest
repair plan under real hangar limits, puts a **rupee value** on every decision, and drafts the
paperwork for a human engineer to approve — all **without any internet** (which matters because
secure/defence hangars aren't allowed to send data to the cloud).

In one line: **AeroTwin turns "fix on a calendar" into "fix exactly what needs fixing, exactly
when, and prove it — on a ₹10,000 box, offline."**

---

## 2. The problem, in simple terms

| Today's way | Why it hurts |
|---|---|
| Maintenance scheduled by **calendar / flight-hours**, not actual condition | Over-services healthy jets (waste) **and** misses fast-degrading ones (risk) |
| **No continuous health record** per aircraft | Nobody can reliably answer "is *this* tail getting worse?" |
| Sensor data exists but is **thrown away or siloed** | The information needed to predict failure is never used |
| Findings live on **paper** | Slow, error-prone, hard to audit |
| Cloud AI tools **can't be used** in secure/ITAR hangars | The obvious digital fix is legally blocked |

**The missing piece is a digital twin that lives at the edge** — on-site, offline — that turns
raw sensor data into a prediction and a decision.

---

## 3. What AeroTwin does — the features (complete list)

Grouped by what a viewer sees. **Core = the primary graded domain (MRO prediction).
Extra = supporting features.**

### Core — Predictive Aircraft Health (the main event)
- **Failure / maintenance-need prediction** — reads aircraft/engine sensor telemetry and
  predicts whether a tail is heading toward an **unscheduled maintenance event**.
- **Remaining Useful Life (RUL)** — estimates how much healthy life is left, as a *range*
  (P10 / P50 / P90 confidence band), not a fake single number.
- **Explainable "why"** — for every alert, it names the **exact sensors** that triggered it
  (e.g., "oil-temperature trend + rising vibration"), so an engineer can trust it.
- **Health index (0–100)** per aircraft — one glanceable number.
- **Condition-based scheduling** — recommends **pull forward / safely defer / ground**, each
  compared against what the blind calendar would have said.
- **Fleet risk board** — every aircraft ranked worst-first; the planner's morning screen.

### Core — Prescribe & Price (turning prediction into money)
- **Capacity-constrained fleet plan** — with only N hangar slots, service the riskiest first,
  defer the healthy, and make the *carried risk* explicit when demand exceeds slots.
- **Rupee ledger** — every plan is priced: **downtime recovered + AOG risk avoided − risk
  carried = net value** for the window, versus the blind calendar. Every money constant is
  visible and editable, so the figure is defensible.
- **What-if planner** — change a decision (defer a tail, add a hangar slot) and watch the plan
  and the price re-compute live.

### Core — Act & Prove
- **Agentic MRO copilot** — a small offline AI assistant that drafts the **work order**, but
  only if it can **cite the manual** (a guardrail against making things up). A human engineer
  always signs off.
- **Tamper-evident audit trail** — every decision is written to a **hash-chained** log; any
  edit breaks the chain. Built for regulatory audit from day one.

### Core — The twin learns
- **Per-tail Bayesian learning** — each aircraft's RUL prediction gets *tighter* as more data
  arrives.
- **Federated learning** — every site's model improves the shared model **without raw data ever
  leaving the site** (uses **differential privacy** — only safe, noisy statistics are shared).

### Extra — Structural inspection (one more sensor into the twin)
- **Crack / corrosion detection** on aircraft-skin images (computer vision).
- **Zero-label anomaly detection** — flags "this looks wrong" even for damage types never
  labelled, so it isn't dependent on scarce aerospace defect data.
- **Millimetre sizing** against a repair-manual limit table, and a **crack-growth (Paris-law)**
  progression model.

### Extra — Edge & trust
- **Runs fully offline** on a Raspberry Pi 5 — no internet, no cloud.
- **Live edge telemetry** — shows on-device speed / latency / power during the demo.
- **3D digital-twin view** — an interactive aircraft you can orbit; health tints the airframe,
  defects glow as markers you can click.

---

## 4. The pipeline — how data flows, step by step

Read this as one sentence per stage. This is the spine of the demo.

```
 (1) SENSE            aircraft/engine sensor telemetry comes in
        │             (+ optional crack/corrosion images as an extra sensor)
        ▼
 (2) PREDICT          an on-device ML model forecasts maintenance-need / RUL
        │             with a confidence band
        ▼
 (3) EXPLAIN          it names the sensors driving the prediction (SHAP),
        │             and the copilot writes a plain-English note
        ▼
 (4) TWIN             per-aircraft health record: health index, RUL,
        │             condition-based decision vs the calendar
        ▼
 (5) PRESCRIBE        fleet risk board + a hangar-capacity-limited service plan
        │
        ▼
 (6) PRICE            rupee ledger: net value of the plan vs the blind calendar
        │
        ▼
 (7) ACT              agent drafts a manual-cited work order → human signs
        │
        ▼
 (8) PROVE & LEARN    hash-chained audit trail; federated learning improves
                      the fleet model without data leaving the site
```

Everything from (2) onward runs **on the Raspberry Pi, offline**.

---

## 5. Working principles — the "how", explained simply

**How does it predict failure?**
It learns from **real historical flight data** where we know what happened next (some flights
were followed by an unplanned repair, some weren't; some engines ran all the way to failure).
The model learns the sensor "fingerprint" of an aircraft that is about to need maintenance, then
watches new flights for that fingerprint. Training happens once, off the device (on a laptop or
free cloud GPU); the finished, shrunk-down model runs on the Pi.

**Why can a tiny Pi do this?** Two reasons. (1) We use **lightweight models** (gradient-boosted
trees / a fast time-series transform) that need almost no compute to *run* (training is the heavy
part, and that's done elsewhere). (2) We **quantize** the model (shrink it to 8-bit integers), so
it's a few megabytes and runs in milliseconds.

**Why explainability matters.** A prediction an engineer can't trust is useless. **SHAP** is a
standard method that assigns each sensor a "how much did you contribute to this alert" score, so
the system can say *"flagged because oil temp is trending up and vibration is rising"* instead of
"trust me." That's what makes it acceptable in a safety-critical, regulated industry.

**Why "digital twin" and not just "a model".** A model gives a number. The **twin remembers** —
it keeps each aircraft's history, so it can see trajectories (getting worse or stable), compare to
the calendar, and drive a *decision*, not just a score.

**Why "at the edge / offline" is essential (not a gimmick).** Secure and defence hangars are
often network-isolated, and **ITAR** rules can make it *illegal* to send the data to a cloud.
Also, a decision at the aircraft in seconds beats an upload-analyse-download loop while the jet
is losing money on the ground. So edge isn't a nice-to-have — it's the only compliant path.

**Why federated learning + differential privacy.** Every airline/site wants a smarter shared
model, but nobody can share raw sensitive data. Federated learning shares only **model updates /
aggregate statistics**; differential privacy adds a little math "noise" so even those can't be
reversed back to the source. The fleet gets smarter together, safely.

**Why the audit trail is a security feature.** In aviation, you must *prove* every airworthiness
decision. A **hash chain** links each record to the previous one cryptographically — change any
past record and the chain visibly breaks. That's tamper-evidence, not just logging.

---

## 6. Final tech stack (this is the target stack — not everything is built yet)

> Note for the team: the frontend is **moving to React** (the current single-file HTML is being
> replaced). The prediction core (models on real datasets) is the **active build**. The twin,
> planner, ledger, agent, audit, and federated layers already exist in Python and are reused.

### Frontend
- **React** + **TypeScript** + **Vite** (fast dev/build)
- **react-three-fiber** + **Three.js** — the interactive 3D aircraft twin
- **Tailwind CSS** — styling
- **Recharts** — RUL bands, SHAP bars, sparklines

### Backend
- **FastAPI** (Python) — serves the JSON API (`/api/fleet`, `/api/tail/{id}`, `/api/predict`,
  `/api/whatif`, etc.) and the model assets

### Machine Learning (the prediction core)
- **LightGBM** — the main model (accurate on sensor features, tiny, CPU-fast, and **explainable
  via SHAP**)
- **MiniRocket** (via **sktime**) — fast time-series alternative on raw sensor sequences
- **SHAP** — explainability (the "why")
- **scikit-learn / PyTorch** — supporting model development
- **InceptionTime** — deep-learning benchmark only (not shipped to the Pi)

### Edge deployment
- **ONNX Runtime** / **TensorFlow Lite** — run the model on-device
- **INT8 quantization** — shrink the model for the Pi
- **Raspberry Pi 5 (8 GB)** — the offline edge device

### GenAI / agent
- **Ollama** — a small **local** LLM (offline) for the copilot, with **retrieval-augmented
  generation (RAG)** over the maintenance manuals and a **citation-required** guardrail

### Learning & trust
- **Federated averaging + differential privacy** — fleet learning with zero raw-data egress
- **Hash-chained audit log** — tamper-evident record

### Data (real, public)
- **NGAFID** — ~29,000 real general-aviation flights, 23 sensors, labelled around real unplanned
  maintenance events (the core prediction dataset; CC BY 4.0)
- **NASA C-MAPSS** — turbofan run-to-failure data (the RUL benchmark; public)
- *(Extra, structural)* NEU-DET / SDNET2018 / aircraft-skin defect image sets

---

## 7. Why AeroTwin wins (the differentiators)

1. **Edge + offline + ITAR-safe by design** — it runs where cloud tools legally cannot.
2. **Prediction that's explainable** — it says *why*, so engineers and regulators can trust it.
3. **It doesn't stop at a prediction — it prices the decision** in rupees. Almost nobody does this.
4. **A real digital twin**: sense → predict → explain → decide → prescribe → price → act → learn,
   all closed-loop.
5. **Trained on real public fleet data**, not a mock — a credible, defensible demo.
6. **Fleet learning without data leaving the site** — a moat that cloud competitors structurally
   can't match.

No single existing product combines all of these — that combination is the novelty.

---

## 8. Honesty notes (say these before a judge asks)

- The **prediction core trains on real public data** (NGAFID, C-MAPSS).
- Where data is **synthetic** (the between-inspection sensor stream, the simulated federation
  sites, the laptop telemetry HUD), it is **clearly labelled** on screen and in the API — the
  *algorithm* is real and tested; only the *sensor feed* is stand-in until field hardware exists.
- All money and manual-limit constants are **illustrative and editable** — calibrate per operator.
- We report honest metrics (recall bias, RUL error), not a single flattering accuracy number.

---

## 9. Glossary (plain English)

| Term | Meaning |
|---|---|
| **MRO** | Maintenance, Repair & Overhaul — the business of keeping aircraft airworthy |
| **Edge AI** | Running the AI on a small on-site device, not in the cloud |
| **Digital twin** | A live, data-fed virtual copy of a real aircraft used to predict and decide |
| **PHM** | Prognostics & Health Management — predicting maintenance needs before failure |
| **RUL** | Remaining Useful Life — how much healthy life a part/aircraft has left |
| **CBM+** | Condition-Based Maintenance — service by actual condition, not a calendar |
| **AOG** | Aircraft-on-Ground — a grounded, money-losing aircraft |
| **SHAP** | A method that explains which inputs drove a model's prediction |
| **Federated learning** | Many sites train a shared model without sharing raw data |
| **Differential privacy** | Math that stops shared statistics being reversed to source data |
| **ITAR** | US rules that can forbid sending defence-related data off-site / to the cloud |
| **Quantization** | Shrinking a model (e.g., to 8-bit) so it runs on small hardware |
| **Hash chain** | Cryptographic linking of records so tampering is detectable |
| **NGAFID / C-MAPSS** | The real public flight/engine datasets we train the predictor on |
