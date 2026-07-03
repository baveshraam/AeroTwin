# AeroTwin-Edge — Tech Stack & Pipeline, End to End

One page, no fluff: what runs, in what order, on what data, with what tech. For the
narrative pitch see [README.md](../README.md); for session-by-session history see
[ACTION_PLAN.md](ACTION_PLAN.md).

## The chain in one line

```
photo of a crack → mm size → SRM severity grade → per-tail twin record → RUL forecast
→ fleet-wide rupee-priced service plan → cited work order → human sign-off → tamper-proof audit
```

Every arrow above is a real Python module, not a mock — the only "synthetic" pieces are
explicitly-flagged *data sources* (SHM sensor stream, federated hangars), never the
*algorithms*. See the honesty ledger in the README for the full list.

## Tech stack

| Layer | Tech | Why |
|---|---|---|
| Detection (L0) | YOLOv8-seg (Ultralytics), PyTorch, CUDA | instance segmentation — a crack is a thin polygon, not a box |
| Sizing (L0) | OpenCV `aruco` (contrib build) | ArUco fiducial marker → real mm/px, not a guessed scale |
| Anomaly (L0b) | PatchCore: frozen ResNet-18 (torchvision) + greedy k-center coreset + kNN | zero-label detection of damage never seen in training |
| Grading (L0) | plain CSV lookup (`data/srm_limits.csv`) | aerospace-literate severity, not a generic confidence score |
| Fatigue physics (L2) | Paris' law, closed-form + Monte-Carlo (NumPy) | crack-growth model, P10/P50/P90 RUL, not false precision |
| Bayesian learning (L2b) | Normal-Normal conjugate update (hand-derived, closed-form) | per-tail RUL band tightens with every scan — the twin *learns* |
| SHM (L1b) | EWMA baseline + one-sided CUSUM | standard change-point detector, continuous between inspections |
| Federated stats (L1c) | FedAvg (sample-weighted) + Laplace-mechanism DP | pools growth-rate priors without any imagery crossing a site boundary |
| Twin/planner (L1) | pure Python + SQLite | health index, fleet ranking, capacity-constrained triage, rupee ledger |
| Agent (L3) | keyword retrieval + template, citation-gated | never states a limit it can't cite — refuses instead |
| Copilot (L3, optional) | Ollama (`llama3.2:3b`) tool-calling, deterministic offline fallback | real LLM when available, same guardrail either way |
| Audit (L3) | SHA-256 hash chain, hand-rolled PDF writer | tamper-evident evidence pack, zero dependencies |
| API | FastAPI + Uvicorn, gzip middleware | 19 JSON routes, nothing computed in the browser |
| Frontend | vendored Three.js r128 + OrbitControls, one static HTML file | zero-build, offline-forever 3D twin |
| Edge export | ONNX Runtime, INT8 post-training quantization | Pi-deployable, CPU-only inference path |

## The L0 → L3 chain, with exact data shapes

**L0 — Detect + Size + Grade** (`src/l0_detect/`)
```
image (jpg/png)
  → detect.py: YOLOv8-seg inference → [{defect_type, mask_length_px, confidence, model_version}]
  → sizing.py: ArUco marker in frame → mm_per_pixel (0.2513 real / 0.025 fallback)
  → grade.py: (defect_type, ata_zone, size_mm) → SRM lookup → {grade, airworthiness, limit_mm, manual_ref}
  → anomaly.py [L0b, optional]: PatchCore vs normal-skin bank → {score, is_anomaly, heatmap}
```
`model_version` is stamped by *what actually ran* (`yolov8-seg` / `mock-v0` / `mock-fixed`),
never inferred from the `--real` flag — a silent fallback must never claim to be real.

**L1 — Twin state** (`src/l1_twin/twin.py`, `db.py`)
```
finding dict → db.add_finding() (SQLite, append-only history)
  → tail_state(): health 0-100, worst open defect, RUL (physics MC band + Bayesian learned band),
                  condition-based next-check vs the 6000-cycle calendar baseline
  → project_tail_state(): grow every open defect by its measured rate — the time-scrub engine
```

**L1b/L1c — Continuous + federated signal** (`shm.py`, `federated.py`)
```
tail's growth rate → shm_health(): synthetic strain/AE/freq-shift stream → CUSUM alert cycle
4 hangar sites → site_update() → federated_average() [+ DP-noised release] → global growth prior
                → fed back into twin.py as the Bayesian PRIOR for every tail's per-defect learning
```

**L2 — Progression / RUL** (`src/l2_progress/`)
```
(size_now, size_prev, cycles_between, limit_mm) → empirical_cycles_to_limit()   [if 2+ scans]
(size_now, limit_mm)                            → paris_cycles_to_limit()      [deterministic]
                                                 → paris_rul_mc()               [P10/P50/P90 band]
scan history + federated prior                  → bayes.learn()                [posterior, tighter band]
```

**L1 — Fleet planner** (`planner.py`) — the payoff layer
```
fleet_summary() (every tail's twin state)
  → fleet_plan(): priority-sort (grounded → sickest → soonest-to-limit) → capacity-constrained
                  triage → {SERVICE NOW / SERVICE THIS WINDOW / SAFE TO DEFER / QUEUED}
  → ledger: downtime recovered + AOG risk avoided − AOG risk carried = NET VALUE (₹)
  → scenario_add_capacity() / scenario_defer(): live what-ifs
  → spares_forecast(): RUL-P10 → which repair kit, ordered by which cycle
```

**L3 — Agent, copilot, work order, audit** (`src/l3_agent/`)
```
finding + grade + progression
  → agent.draft_work_order(): retrieve manual excerpt (defect_type AND ata_zone match required)
                               → DRAFT_FOR_SIGNOFF (with citation) | ESCALATE (no citation found)
  → copilot.draft_with_copilot() [optional]: Ollama rephrases ONLY the retrieved excerpt;
                               citation must survive in the prose or the draft is discarded
  → workorder.open_wo/sign_wo/close_wo(): DRAFT → SIGNED → CLOSED, illegal transitions refused
  → audit.append(): SHA-256 hash-chained JSONL — any past edit breaks verify()
  → workorder.evidence_pdf(): hand-rolled PDF, stamped VERIFIED/BROKEN from a live re-walk
```

**API + 3D UI** (`src/l1_twin/app.py`, `static/index.html`)
19 routes (`/api/fleet`, `/api/tail/{t}`, `/api/scrub`, `/api/whatif`, `/api/shm/{tail}`,
`/api/spares`, `/api/scenario/capacity`, `/api/workorder/*`, `/api/evidence.pdf`, `/api/ask`,
`/api/federated`, `/api/telemetry`, …) — the frontend draws exactly what these return,
nothing is computed in JavaScript. The 3D scene is a parametric `LatheGeometry` fuselage
(clickable ATA-zone hotspots via raycasting against the real mesh), health-tinted, with a
time-scrub slider that calls `project_fleet()` live.

## What's real vs. synthetic (recap — full table in README)

Every *algorithm* above is real and self-tested (`python -m <module>` runs a `_demo()`
assert-based self-check for all 10+ modules). What's synthetic is specific *data feeding*
three of them: the SHM sensor stream (no field hardware), the federated hangar sites (no
multi-site ITAR agreement for a POC), and the edge-telemetry HUD's fps/cpu numbers on a
laptop. All three are flagged `synthetic`/`simulated` in the API response and the UI —
never silently presented as live.

## Current ML status (2026-07-03)

- **Base detector**: trained, real — YOLOv8s-seg, 40 epochs on 4,029-image public crack
  corpus (`crack-seg`), held-out box recall 0.667 / mask recall 0.427. Deployed to the
  `--real` inference path, verified genuinely discriminating (fires on a real crack photo,
  silent on a blank control).
- **INT8 edge export**: done — 11.9 MB ONNX, 499 ms/img (2.0 FPS) CPU @1280px.
- **Aircraft on-domain fine-tune**: **done, deployed** — second attempt, after the first
  regressed (see below). Trained on `aircraft-dent-crack` alone (198/18/12 split, real
  polygon masks, classes `crack`+`dent`, no noisy catch-all class), 54 epochs (best @34),
  mask recall 0.181 mean / 0.278 crack-only on a tiny 36-instance val set — modest, and
  honestly limited by dataset size (198 training images), but genuinely on-domain and
  verified: fires correctly on the demo panel (conf 0.37, labelled "crack"), silent on a
  blank control, and detects on every one of 4 spot-checked real aircraft photos it never
  trained on (1/11/9/2 detections). Deployed to `crack-seg.pt`, the `--real` path.
  *First attempt regressed*: merging in `aircraft-skin-defects` (796 images, one vague
  `defect` class, 94% of it box-derived rectangular pseudo-masks) dominated the loss and
  produced a model that detected **nothing** on the same demo panel — caught by the exact
  same verification check before it was reported as done, rolled back, kept on disk as
  `crack-aircraft-adapt-v1-weak.pt` (not deployed) as a documented lesson, not deleted.
- **Anomaly branch**: real PatchCore, AUROC 1.000 on held-out real MVTec AD `bottle`
  category; pipeline-integrated bank fit on the same real images. Not yet aerospace-domain
  (AeBAD) — that dataset needs a manual gated download.
