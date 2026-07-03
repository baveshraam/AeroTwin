# AeroTwin: Edge-AI Digital-Twin MRO with Explainable RUL Prognostics and Federated Fleet Intelligence

*Tata Technologies InnoVent-27 · AI at the Edge · Aerospace · Subcategory 3.2.3.1 (Digital-Twin-Enabled MRO)*

> The single source of truth for what AeroTwin is. Read top-to-bottom with zero code
> knowledge and you'll understand what it does, why it matters, how it works, what is
> already real, and what is planned. Use it as the base for the deck and the demo script.

---

## 1. The 30-second version (say this first)

Airlines and MRO shops still service aircraft mostly by a **fixed calendar** — "every X
flight-hours, do this check" — regardless of how healthy that specific aircraft actually is.
That is expensive in both directions at once: healthy aircraft get pulled for checks they
didn't need, and quietly-degrading aircraft fail *between* checks (a grounded aircraft costs
**₹8 lakh–1.25 crore per hour**).

**AeroTwin is a small, offline computer (a Raspberry Pi) that lives at the aircraft and acts
as a digital twin — a living, predictive health record of every tail in the fleet.** It reads
real engine telemetry, **predicts which aircraft is heading toward unscheduled maintenance
before it fails**, says *why* by naming the exact sensors, forecasts remaining useful life as
an honest confidence band, ranks the fleet worst-first, computes the smartest repair plan
under real hangar limits, prices every decision in rupees, drafts the paperwork with manual
citations for a human engineer to sign, and writes every decision to a tamper-evident audit
chain — all **without internet** (secure/ITAR hangars can't use the cloud anyway).

In one line: **AeroTwin turns "fix on a calendar" into "fix exactly what needs fixing,
exactly when, prove it, and price it — on a ₹10,000 box, offline."**

---

## 2. The problem, in simple terms

| Today's way | Why it hurts |
|---|---|
| Maintenance by **calendar / flight-hours**, not condition | Over-services healthy jets (waste) **and** misses fast-degrading ones (risk) |
| **No continuous health record** per aircraft | Nobody can answer "is *this* tail getting worse?" |
| Sensor data is **thrown away or siloed** | The information needed to predict failure is never used |
| Findings live on **paper** | Slow, error-prone, hard to audit |
| Cloud AI **can't be used** in secure/ITAR hangars | The obvious digital fix is legally blocked |

The missing piece is a digital twin that lives **at the edge** — on-site, offline — and turns
raw sensor data into a prediction, a decision, a price, and a proof.

---

## 3. The features — buffed, and honest about status

Legend: **[LIVE]** = running in the repo today, demoable. **[NEXT]** = designed, slotting
into an existing pipeline hook. Everything LIVE is validated honestly (details in §8).

### Core — Predictive Aircraft Health (the main event)

- **Maintenance-need prediction on REAL fleet data [LIVE]** — a model trained on the NGAFID
  dataset: 28,935 real general-aviation flights recorded around real unscheduled maintenance
  events (36 issue types: gasket leaks, baffle cracks, engine roughness…). For every flight
  it reads 70 engine-telemetry features (oil temperature/pressure, 4× cylinder-head temps,
  4× exhaust-gas temps, RPM, fuel flow, airspeed, vertical acceleration…) and outputs
  P(maintenance needed). *The buff over a demo-toy:* validation is grouped by maintenance
  event (no flight from the same episode in both train and test), and the two dataset
  columns that leak the answer were found and excluded — with them the score is a fake
  100%; without them it's a defensible **ROC-AUC 0.702**. Judges can grill this and it holds.
- **Remaining Useful Life as a band, never a fake number [LIVE]** — three quantile-regression
  models forecast **days until the maintenance event** as P10/P50/P90. *The buff:* the band
  is *calibrated and measured* — 80% of real events land inside the P10–P90 band (exactly the
  design target), P50 off by 1.2 days on average. A second RUL scale (flight cycles to
  structural limit, Paris-law Monte-Carlo) covers the structural branch. **[NEXT]**: NASA
  C-MAPSS turbofan run-to-failure as a third benchmark.
- **Explainable "why", per alert [LIVE]** — every risk score comes with named sensors:
  *"E1 OilT variability high (1.3σ vs healthy fleet); E1 CHT4 peak high…"*. Mechanism:
  each feature's z-score against the **post-maintenance healthy-fleet baseline**, weighted by
  the model's own measured feature importances. *The buff:* the explanation vocabulary is the
  mechanic's vocabulary (oil, CHT, EGT), not ML jargon — and the top fleet-wide signals the
  model discovered (oil-pressure instability, oil-temp instability, CHT4 peaks) are exactly
  the physics you'd expect for gasket/baffle failures. That agreement is the trust story.
- **Health index 0–100 per aircraft [LIVE]** — `100 × (1 − risk)`, glanceable, with the full
  risk trajectory behind a click (risk-now vs risk-peak shows *improving vs degrading*).
- **Condition-based scheduling [LIVE]** — every aircraft gets **pull forward / monitor /
  fly**, with visible thresholds. *The buff [NEXT]:* thresholds set by the rupee ledger
  (choose the cutoff that minimises expected cost, not an arbitrary 0.5) — prediction and
  pricing become one optimisation.
- **Fleet risk board [LIVE]** — `/api/ngafid/board`: **1,425 real maintenance episodes**
  ranked worst-first, each row carrying risk-now, risk-peak, RUL band, issue type, action,
  and the named-sensor "why". The planner's morning screen, powered by real data.

### Core — Prescribe & Price (turning prediction into money)

- **Capacity-constrained fleet plan [LIVE]** — with N hangar slots: grounded first, then
  sickest, then soonest-to-limit; healthy tails deferred; and when demand exceeds slots the
  **carried risk is explicit** — the plan says what it could NOT service and what that costs.
- **Rupee ledger [LIVE]** — every plan is priced: **downtime recovered + AOG risk avoided −
  risk carried = net value vs the blind calendar**. Every money constant is visible and
  editable — the figure survives a CFO's "where did that number come from?".
- **What-if planner [LIVE]** — defer a tail or add a hangar slot and watch the plan and price
  recompute live (`/api/whatif`, `/api/scenario/capacity`). Time-scrub the whole fleet
  forward N cycles (`/api/scrub`) and watch health, RUL, and the ledger age together.
- **Spares pre-staging [LIVE]** — RUL-P10 (the pessimistic edge of the band) drives which
  repair kit to order by which cycle, so the part arrives before the failure does.

### Core — Act & Prove

- **Agentic MRO copilot [LIVE]** — a local LLM (Ollama, llama3.2:3b, fully offline) with
  **tool-calling into the live twin**: it fetches real limits, real RUL, real fleet state —
  it is *incapable* of inventing a number, because every number comes from a tool. *The
  guardrail with teeth:* a work-order draft is only issued if the manual citation survives
  into the final text — tested against a live case where the model invented a citation and
  the gate caught it. No Ollama installed? The same contract runs on a deterministic
  template — the demo never dies.
- **Human sign-off workflow [LIVE]** — work orders have a lifecycle (DRAFT → SIGNED →
  CLOSED), illegal transitions refused, every step on the audit chain. The AI advises;
  a certifying engineer decides. That's not a disclaimer, it's the architecture.
- **Tamper-evident audit trail [LIVE]** — every airworthiness decision is SHA-256
  hash-chained; edit any past record and `verify()` visibly breaks. One click exports an
  **evidence-pack PDF** stamped VERIFIED/BROKEN from a live re-walk of the chain. Built for
  DGCA/EASA-style auditability from day one.

### Core — The twin learns

- **Per-tail Bayesian learning [LIVE]** — each aircraft's RUL band starts at the fleet prior
  and tightens with every new scan (closed-form Normal-Normal update). Two aircraft with the
  same crack get different bands if their histories differ — that's what makes it a *twin*.
- **Federated fleet intelligence [LIVE, simulated sites]** — sites improve the shared
  growth-rate prior via FedAvg with **differential-privacy noise** on every release; raw data
  never leaves a site. The math is real and tested; the four hangars are simulated (clearly
  labelled) until a multi-site partner exists. The federated prior feeds straight back into
  each tail's Bayesian update — the loop is closed.

### Extra — Structural inspection (one more sensor into the twin)

- **Crack/dent detection on aircraft skin [LIVE]** — YOLOv8-seg fine-tuned on aircraft
  surfaces; INT8-quantized ONNX (11.9 MB) for the Pi. Honest recall numbers, verified on
  photos it never trained on.
- **Zero-label anomaly detection [LIVE]** — PatchCore: flags "this looks wrong" for damage
  types never labelled (AUROC 1.000 on held-out real MVTec category), so the system isn't
  hostage to scarce aerospace defect data.
- **Millimetre sizing + physics progression [LIVE]** — ArUco fiducial gives real mm/px; the
  measured size is graded against an SRM-style limit table and projected forward with
  Paris-law crack growth (Monte-Carlo band, not false precision).

### Extra — Edge & trust

- **Fully offline on a Raspberry Pi 5 [LIVE]** — training happens off-device; inference is
  CPU-only, quantized, milliseconds. No internet anywhere in the loop.
- **Live edge telemetry HUD [LIVE, simulated on laptop]** — fps/latency/power, honestly
  labelled `simulated` until it reads the Pi's psutil.
- **3D digital-twin view [LIVE]** — orbit a real airframe model; health tints the skin,
  defects glow as clickable markers; a time slider scrubs the whole fleet's future.

---

## 4. The pipeline — how data flows

```
 (1) SENSE      real flight telemetry (NGAFID parquet; 23 engine/airframe channels)
      │         + optional skin images as one more sensor
      ▼
 (2) PREDICT    on-device model → P(maintenance-need) + P10/P50/P90 days-to-event
      ▼
 (3) EXPLAIN    named sensors, z vs healthy fleet × model importance
      ▼
 (4) TWIN       per-tail record: health 0-100, RUL band, trajectory, Bayesian update
      ▼
 (5) PRESCRIBE  fleet board ranked worst-first → capacity-constrained service plan
      ▼
 (6) PRICE      rupee ledger: net value vs the blind calendar; what-ifs recompute live
      ▼
 (7) ACT        copilot drafts a manual-cited work order → human signs → status lifecycle
      ▼
 (8) PROVE      SHA-256 hash chain + evidence PDF; federated learning improves the fleet
     & LEARN    prior with zero raw-data egress
```

Every stage is a real, importable Python module with a self-check; stages (2)–(8) run
offline on the Pi. Full technical detail: [docs/PIPELINE_OVERVIEW.md](docs/PIPELINE_OVERVIEW.md).

---

## 5. Working principles, in plain language

**How does it predict failure?** It learns the sensor fingerprint of an aircraft that is
about to need maintenance from flights where we *know* what happened next (NGAFID labels
every flight as before or after a real maintenance event). New flights are scored against
that fingerprint. Training is the heavy part and happens on a laptop; the finished model is
small and scores a flight in milliseconds on the Pi.

**Why is the validation trustworthy?** Two traps were found and removed: (1) flights around
the same maintenance event never appear in both training and test (otherwise the model just
memorises the episode), and (2) two bookkeeping columns in the dataset encode the answer
outright (`date_diff`'s sign IS the label) — they are excluded from features, and one of
them is reused *honestly* as the regression target for days-to-event. This is the difference
between a demo that survives judge questions and one that doesn't.

**Why a band and not a number for RUL?** A single number ("23 days left") is false
precision. AeroTwin gives P10/P50/P90 — "80% chance the event lands in this window" — and we
*measured* that 80% of real events do. Planners can be aggressive on P50 and safe on P10.

**Why explainability matters.** A prediction an engineer can't interrogate is useless in a
regulated industry. Every alert names its sensors in mechanic vocabulary, benchmarked
against the healthy fleet. The model's global top signals (oil-pressure/temperature
instability, CHT peaks) match the failure physics — the model rediscovered what mechanics
know, which is exactly why the mechanic can trust it on the next flight.

**Why "digital twin" and not just "a model".** A model gives a score. The twin *remembers* —
per-aircraft history, trajectories, Bayesian bands that tighten with evidence, decisions
compared against the calendar, and a priced plan. Score → decision → money → proof.

**Why edge/offline is essential, not a gimmick.** Secure and defence hangars are
network-isolated; ITAR can make cloud upload *illegal*. A ₹10,000 box at the aircraft is the
only compliant path — and it answers in seconds while a cloud round-trip is still uploading.

**Why federated learning + differential privacy.** Everyone wants a smarter shared model;
nobody may share raw data. Sites share only noisy aggregate statistics — mathematically
protected against reversal — and the shared prior makes every site's twin smarter.

**Why the audit trail is a security feature.** Aviation requires *proving* every
airworthiness decision. Hash-chaining makes the log tamper-evident: change one byte of
history and the chain visibly breaks, and the exported evidence PDF says so.

---

## 6. Tech stack & repo layout

Repo is organised for parallel work — four independent surfaces, four teams can push at once:

```
frontend/   React + TypeScript + Vite + Three.js — the dashboard & 3D twin (npm run dev)
backend/    FastAPI + the twin brain: l0_detect, l1_twin, l2_progress, l3_agent, pipeline.py
ml/         training pipelines (ngafid_train, train, train_anomaly, fetch_datasets) + models/
data/       datasets (ngafid/ - gitignored 5.6GB), SRM limits, manuals, twin.db
docs/       PIPELINE_OVERVIEW.md (tech deep-dive), problem-statement.txt, screenshots
```

| Layer | Tech |
|---|---|
| Prediction core | **HistGradientBoosting** (NaN-native, CPU-fast) + quantile GBMs for the RUL band; scikit-learn |
| Explainability | permutation importance + healthy-fleet z-scores today; SHAP upgrade path |
| Structural CV | YOLOv8-seg (fine-tuned), PatchCore anomaly, OpenCV ArUco sizing |
| Physics | Paris-law crack growth, Monte-Carlo bands, closed-form Bayesian updates |
| Twin/planner | pure Python + SQLite; capacity triage; rupee ledger |
| GenAI agent | **Ollama (llama3.2:3b, offline)** tool-calling + citation-gated RAG; deterministic fallback |
| Trust | SHA-256 hash chain, hand-rolled evidence PDF, FedAvg + Laplace DP |
| API | FastAPI + Uvicorn — 21 JSON routes; frontend computes nothing |
| Frontend | React + TS + Vite, Three.js 3D twin, served by FastAPI (offline bundle) |
| Edge | Raspberry Pi 5 (8GB), ONNX Runtime, INT8 quantization |
| Data | **NGAFID** (real, 28,935 flights, CC BY 4.0) · C-MAPSS (planned) · crack-seg/MVTec (structural) |

---

## 7. Why AeroTwin wins (the differentiators)

1. **Real data, honest validation** — the prediction core is trained on 28,935 real flights
   around real maintenance events, with leakage found-and-removed and event-grouped testing.
   Most hackathon "predictive maintenance" is a mock; this one survives cross-examination.
2. **Edge + offline + ITAR-safe by design** — it runs where cloud tools legally cannot.
3. **Explainable in the mechanic's language** — named sensors vs the healthy fleet, and the
   model's discovered signals agree with failure physics.
4. **It prices the decision in rupees** — prediction → plan → net value vs the calendar.
   Almost nobody closes this loop.
5. **A real digital twin** — sense → predict → explain → decide → price → act → prove →
   learn, closed-loop, every stage a live module.
6. **Fleet learning without data leaving the site** — a structural moat cloud competitors
   can't copy.
7. **Trust is architecture, not a slide** — citation-gated GenAI, human sign-off lifecycle,
   hash-chained evidence.

---

## 8. Honesty ledger (say these before a judge asks)

- **Measured, current numbers** (retrain: `python -m ml.ngafid_train`): maintenance-need
  ROC-AUC **0.702**, balanced-acc 0.636, on an event-grouped test set of real flights; RUL
  band coverage **80%** (design target 80%), P50 MAE 1.2 days. These will improve with more
  parquet shards and trend features — but they are *real today*.
- **Leakage disclosed**: `date_diff` and `number_flights_before` encode the label; both are
  excluded from features (the trainer's docstring documents the trap for reviewers).
- **Simulated and labelled as such**: the SHM between-inspection stream, the 4 federated
  hangar sites, and the laptop telemetry HUD — algorithms real, feeds stand-in, every
  response carries `simulated: true`.
- **Money and limit constants are illustrative and editable** — calibrate per operator.
- The prototype uses a **subset** of NGAFID (80 of 401 parquet shards, stride-sampled for
  label diversity); the pipeline scales to all 401 with one flag.

---

## 9. Glossary (plain English)

| Term | Meaning |
|---|---|
| **MRO** | Maintenance, Repair & Overhaul — keeping aircraft airworthy |
| **PHM** | Prognostics & Health Management — predicting maintenance needs before failure |
| **Digital twin** | A live, data-fed virtual copy of an aircraft used to predict and decide |
| **RUL** | Remaining Useful Life — how much healthy life is left |
| **P10/P50/P90** | Pessimistic / median / optimistic bounds — the confidence band |
| **CBM** | Condition-Based Maintenance — service by condition, not calendar |
| **AOG** | Aircraft-on-Ground — a grounded, money-losing aircraft |
| **NGAFID** | Real public dataset: 28,935 GA flights labelled around maintenance events |
| **CHT / EGT** | Cylinder-head / exhaust-gas temperature — key engine health channels |
| **Leakage** | When training data secretly contains the answer — fake accuracy |
| **Federated learning** | Sites train a shared model without sharing raw data |
| **Differential privacy** | Noise that stops shared statistics being reversed to source data |
| **ITAR** | US rules that can forbid sending defence-related data off-site |
| **Hash chain** | Cryptographic record-linking that makes tampering visible |
| **Quantization** | Shrinking a model (e.g., INT8) so it runs fast on small hardware |
