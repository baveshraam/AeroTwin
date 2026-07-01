# AeroTwin-Edge — Action Plan (the "buff" pass)

Master record of the 2026-07-01 planning + build session: why the repo changed shape,
every decision made, the full dataset research, what got built, and what's still open.
This supersedes the narrower [PLAN.md](PLAN.md) as the current source of truth; PLAN.md
stays as the original pre-shortlist strategy for historical context.

## 0. Why this pass happened

Original repo verdict going in: the **concept** was strong (predict → prescribe → price,
offline/ITAR-safe, per-tail structural twin + rupee-priced fleet plan) but the **artifact**
was bland — a SQLite event log rendered as server-side HTML with SVG sparklines, and every
"AI/ML" claim was a mocked stand-in (hardcoded detection, single deterministic RUL number,
keyword-match "agent"). Directive from the user:

1. Best-possible UI — ideally a real 3D digital aircraft twin.
2. Real AI/ML/Edge-AI depth, not a mocked pipeline dressed up in docs.
3. Dig deeper — more use cases, more depth layers, not surface-level.
4. Buff the *entire* repository, aggressively.

## 1. Decisions locked in (asked via structured questions, all answered)

| Question | Decision |
|---|---|
| 3D twin ambition/stack | **Full 3D, zero-build**: vendored Three.js, single HTML page, served by the existing FastAPI — no npm/build step so it stays demoable offline on the Pi in airplane mode. |
| ML depth | **Hunt hard for real datasets, then train the best real model.** Compute/time budget is not a constraint. Not a mock-only path. |
| Deeper feature threads | **All five, merged**: work-order lifecycle + tamper-evident PDF; sensor-fusion SHM; local LLM agent w/ tool-calling; scenario/what-if planner + spares forecasting; federated fleet learning. |

Architectural approach: **extend, don't rewrite** the existing clean Python
(`twin.py`/`planner.py`/`agent.py`/`audit.py`); add a JSON API to the existing FastAPI
app for the new frontend; keep every "illustrative" honesty disclaimer from the original
repo (SRM limits, Paris-law constants, rupee/capacity economics are POC-illustrative).

## 2. Real-dataset research (the hunt)

Two ML branches need data: the **supervised detector** (crack/corrosion segmentation →
mm sizing) and the **zero-label anomaly branch** (flags never-seen damage, answers
aerospace's label-scarcity problem). Ranked findings, all wired into
[tools/fetch_datasets.py](../tools/fetch_datasets.py):

**Detector — base corpus (train today, no aircraft yet):**
- **Ultralytics `crack-seg`** — 4,029 images, instance-seg masks, single `crack` class,
  auto-downloads via `ultralytics`, AGPL-3.0. Plugs straight into `crack-seg.yaml`.
- **CrackSeg9k** (Harvard Dataverse, DOI `10.7910/DVN/EGIEBY`) — ~9k pixel-mask images
  merging Crack500/DeepCrack/CrackForest. Bigger, more robust base.

**Detector — aircraft fine-tune (the credibility flagship, on-domain):**
- **Aircraft_Fuselage_DET2023** (IEEE DataPort) — real fuselage defects, ships in
  COCO/VOC/YOLO + unlabeled data. Free IEEE account required.
- **Roboflow: `aircraft-dent-crack`**, **`aircraft_skin_defects`** (IISc, 372 imgs:
  crack/dent/scratch/paint-peel/missing-head), **aircraft-skin-defects-classification**
  (4,557 imgs) — one-click YOLOv8 exports, small but exact-domain.

**Detector — corrosion/metal-surface transfer:**
- **Severstal Steel Defect** (Kaggle) — masks, 4 defect classes → corrosion/pitting transfer.
- **KolektorSDD2** (vicos.si) — 3,335 imgs, fine segmentation masks.
- **NEU-DET** — steel strip, 6 classes incl. crazing/cracks, detection boxes.

**Anomaly branch (train-on-normal-only, zero labels):**
- **AeBAD** (Aero-engine Blade Anomaly Detection) — *the* aerospace pick: normal-only
  training set, test set has breakdown/ablation/groove/fracture. Perfect zero-label story.
- **MVTec AD / AD 2** — the standard anomaly benchmark, validates the autoencoder/
  PatchCore pipeline before trusting it on AeBAD. **CC BY-NC-SA — non-commercial only**,
  fine for a POC but must be disclosed.

**Recommended recipe:** `crack-seg` + CrackSeg9k base → gentle fine-tune (low LR) on
`Aircraft_Fuselage_DET2023` + Roboflow aircraft sets (+ Severstal for a corrosion class)
→ INT8 ONNX export for the Pi. Anomaly branch: autoencoder/PatchCore trained on normal
aircraft-skin patches, validated against AeBAD + MVTec. **Report POD (probability of
detection) + recall bias, not mAP alone** — a missed crack is the expensive error in
aerospace, not a false positive.

Full registry with license/gate/tier for every dataset lives in
[tools/fetch_datasets.py](../tools/fetch_datasets.py) (`python tools/fetch_datasets.py --list`).

## 3. What got built this session (status)

| # | Thread | Status | Where |
|---|---|---|---|
| 1 | Dataset registry + fetch tooling | ✅ done | [tools/fetch_datasets.py](../tools/fetch_datasets.py) |
| 2 | Two-stage training pipeline (base → aircraft adapt → INT8 ONNX, POD report) | ✅ done (code); **training run not yet executed** | [tools/train.py](../tools/train.py) |
| 3 | JSON API on FastAPI (`/api/fleet`, `/api/tail/{t}`, `/api/scrub`, `/api/whatif`, `/api/telemetry`, …) | ✅ done | [src/l1_twin/app.py](../src/l1_twin/app.py) |
| 4 | Monte-Carlo RUL — P10/P50/P90 confidence bands from Paris-law constant uncertainty | ✅ done | [src/l2_progress/paris.py](../src/l2_progress/paris.py) |
| 5 | Forward-projection twin (the time-scrub engine: grow defects by measured rate, re-grade, re-ground) | ✅ done | [src/l1_twin/twin.py](../src/l1_twin/twin.py) (`project_tail_state`, `project_fleet`) |
| 6 | 3D twin frontend — vendored Three.js, procedural aircraft shaded by health, clickable ATA hotspots, time-scrub slider, fleet strip, rupee ledger, edge-telemetry HUD | ✅ done | [src/l1_twin/static/index.html](../src/l1_twin/static/index.html), [tools/vendor_three.py](../tools/vendor_three.py) |
| 7 | Sensor-fusion SHM — synthetic strain/acoustic-emission/vibration fused into a damage index, online EWMA+CUSUM change-point alert between inspections | ✅ done | [src/l1_twin/shm.py](../src/l1_twin/shm.py) |
| 8 | Work-order lifecycle (DRAFT→SIGNED→CLOSED, illegal transitions refused) + hand-rolled tamper-evident PDF evidence pack (no new dependency) | ✅ done | [src/l3_agent/workorder.py](../src/l3_agent/workorder.py) |
| 9 | Scenario/what-if planner (add-capacity, defer-one-tail) + RUL-driven spares/kit pre-staging forecast | ✅ done | [src/l1_twin/planner.py](../src/l1_twin/planner.py) (`scenario_add_capacity`, `spares_forecast`) |
| 10 | Local LLM copilot (Ollama) — real tool-calling into the twin (`get_srm_limit`, `get_rul`, `get_tail_state`), same citation guardrail, graceful offline fallback | ✅ done | [src/l3_agent/copilot.py](../src/l3_agent/copilot.py) |
| 11 | Federated fleet-learning simulation — sites share only `(n, mean, var)` growth-rate statistics, FedAvg coordinator, provably tighter estimate for data-poor sites | ✅ done | [src/l1_twin/federated.py](../src/l1_twin/federated.py) |
| 12 | All of the above wired into the 3D UI (SHM chart, spares list, certification buttons + PDF link, copilot ask-bar) | ✅ done | [src/l1_twin/static/index.html](../src/l1_twin/static/index.html) |

**Verification performed:** every new module ships a `_demo()` self-check run via
`python -m <module>` (twin math, MC RUL ordering/monotonicity, planner triage/pricing,
SHM alert vs. stable, work-order transition guards + PDF validity, copilot tool outputs,
federated pooled-vs-local standard error). All API routes were exercised end-to-end via
FastAPI's `TestClient` (fleet, tail, scrub, whatif, shm, spares, scenario/capacity,
workorder open/sign/close, evidence.pdf, ask, federated, telemetry) and the full
`python -m src.pipeline --seed` chain still runs clean end-to-end (₹6.12 Cr net value,
correct triage: 1 grounded, 2 serviced, 1 deferred).

## 3b. Session 2 (2026-07-01, second pass) — UI redesign + real AI wired

Focus of this pass: (1) a genuinely impressive, minimalist UI, and (2) turning the
mocked/deferred AI into real, runnable AI. What changed:

| Thread | Status | Where / notes |
|---|---|---|
| **UI redesign — strict 3-colour minimalist system** | ✅ done | [static/index.html](../src/l1_twin/static/index.html). Palette is exactly three colours: near-black `#0a0b0e`, soft-white `#eef1f5` (used at 3 opacities for hierarchy), one warm amber `#f0a83a`. Design rule: **calm neutral = healthy, amber = "look here"** (grounded jet, critical defect, SHM/CUSUM alert, AOG-risk-carried, the hero ₹ figure, active selection). Severity is shown by fill / size / weight, not a rainbow. |
| **3D aircraft — cinematic procedural narrow-body** | ✅ done | Smooth `LatheGeometry` fuselage (was 8 visible cylinders), swept tapered wings/stabs/fin via extruded airfoil planforms, engine nacelles w/ intake lip + fan + pylon, window strip + cockpit glass, ACES tone-mapping, PMREM procedural-gradient environment reflections, real contact shadow + shadow-mapped key light. Health tints the whole airframe toward amber only when it needs attention; defect hotspots are amber glow-sprites sized by grade. Camera fly-to on defect/tail select. |
| **Real crack detector (YOLOv8-seg) training** | ✅ runnable + validated | `crack-seg` (4,029 real instance-seg imgs) auto-downloaded into `data/datasets/` (no login). [tools/train.py](../tools/train.py) fixed for Windows (ultralytics `datasets_dir`/`runs_dir` were pointing at an unwritable `C:\Users\datasets`) and made CPU-tractable (`--model yolov8n-seg.pt --fraction --device`). New `--deploy-base` promotes the base crack model into the slot `detect.py` loads so `--real` works without the gated aircraft set; `--export` INT8-ONNX now honours `--imgsz`. |
| **Zero-label anomaly branch — NOW CODED (was design-only)** | ✅ done + self-checked | [src/l0_detect/anomaly.py](../src/l0_detect/anomaly.py). Real **PatchCore**: frozen pretrained ResNet-18 patch features → greedy k-center **coreset memory bank** of normal-only patches → kNN anomaly score + localisation heat-map. Threshold calibrated on a **held-out** normal split. Self-check: damaged 3.9 vs normal 1.2, 5/5 flagged, 0/5 false alarms. `train_from_folder()` fits AeBAD/MVTec 'good' sets; fused into `--real` pipeline (`[L0b]`). Runs on CPU, backbone weights cache once then offline. |
| **Agentic copilot — now works OFFLINE** | ✅ done | [copilot.py](../src/l3_agent/copilot.py). Previously the tool-trace only appeared if Ollama was running. Added a deterministic **tool-router**: parses intent + entities and actually calls the twin tools (`get_srm_limit`/`get_rul`/`get_tail_state`), returning a real answer + populated trace with no LLM. Honestly labelled "deterministic tool-router — start Ollama for prose." |
| **Federated panel surfaced in the UI** | ✅ done | `/api/federated` was live but unused by the frontend; now a compact FedAvg panel (global growth prior ± std-error, per-site error bars, "only (n,mean,var) leaves each hangar"). |

Environment note: this machine is CPU-only (AMD Radeon iGPU, no CUDA), so training uses
`yolov8n-seg` at reduced imgsz — a *real* model, stated honestly (report POD + CPU FPS,
not a GPU mAP number). torch/torchvision/ultralytics/onnxruntime all installed.

## 4. What's still open

**Base crack training is validated and runnable** (session 2); the remaining depth is the
**on-domain aircraft fine-tune**, which needs gated data:
1. Free-tier account signups (IEEE DataPort for Aircraft_Fuselage_DET2023, Kaggle for
   Severstal, Roboflow API key for the aircraft-skin sets) — these gate `--stage adapt`.
2. Full base run to convergence: `python tools/train.py --stage base --model yolov8n-seg.pt`
   (CPU) or `--model yolov8s-seg.pt` on a GPU. Then `--deploy-base` so `--real` uses it,
   `--export` for INT8 ONNX, `python -m src.pipeline --image <panel.jpg> --real`.
3. `--stage adapt --data data/datasets/aircraft/data.yaml` once the gated aircraft set is
   pulled → promotes to `crack-seg.pt` (the on-domain flagship).
4. ✅ **Anomaly branch is now coded** ([src/l0_detect/anomaly.py](../src/l0_detect/anomaly.py),
   real PatchCore, self-checked). It fits any folder of normal images
   (`train_from_folder`) — point it at AeBAD / MVTec 'good' sets when pulled.

**Deliberately deferred (not blocking, named so they don't rot into "forgotten"):**
- Bayesian per-tail growth-rate updating (the twin currently uses the Monte-Carlo band
  for uncertainty; it does not yet *learn* and tighten per tail as more scans arrive).
- Real sensor hardware integration for SHM (today's `shm.py` is a physically-motivated
  synthetic stream + a real detector algorithm — swap the stream for field telemetry
  later; the CUSUM detector and twin interface don't need to change).
- Secure aggregation / differential privacy on top of the federated simulation (the
  protocol is structurally private — only 3 numbers per site leave the hangar — but
  production would add DP noise / secure aggregation).

## 5. How to run the buffed system end-to-end

```bash
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

python tools/vendor_three.py                 # once, online: vendors Three.js -> offline forever after
python -m src.pipeline --seed                # deterministic 4-tail demo fleet
uvicorn src.l1_twin.app:app --port 8000       # -> http://127.0.0.1:8000 (classic view at /classic)

# Real ML (the one remaining thread):
python tools/fetch_datasets.py --list
python tools/train.py --stage base
python tools/train.py --stage adapt --data data/datasets/aircraft/data.yaml
python tools/train.py --export                # INT8 ONNX for the Pi
```

Optional local LLM copilot: install Ollama, `ollama pull phi3`, then the "MRO copilot"
box in the UI (or `POST /api/ask`) gets real prose instead of the tool-only fallback.

## 6. File map (everything touched this session)

```
tools/
  fetch_datasets.py      NEW  ranked real-dataset registry + auto/kaggle/roboflow/manual fetch
  train.py                    REWRITTEN  two-stage YOLOv8-seg (base -> aircraft adapt) + INT8 export + POD report
  vendor_three.py         NEW  downloads Three.js + OrbitControls for offline use
src/l1_twin/
  app.py                      REWRITTEN  serves 3D UI + full JSON API (fleet/tail/scrub/whatif/shm/spares/
                               scenario/workorder lifecycle/evidence.pdf/ask/federated/telemetry)
  twin.py                     EXTENDED   rul_band (MC), project_tail_state/project_fleet (time-scrub engine)
  planner.py                  EXTENDED   scenario_add_capacity, spares_forecast
  shm.py                  NEW  synthetic strain/AE/vibration fusion + EWMA/CUSUM change detector
  federated.py            NEW  site_update/federated_average/simulate (FedAvg growth priors)
  static/index.html       NEW  the 3D twin: Three.js aircraft, hotspots, time-scrub, ledger, SHM, spares,
                               certification panel, copilot bar, telemetry HUD
  static/vendor/          NEW  three.min.js, OrbitControls.js (vendored, offline)
src/l2_progress/
  paris.py                     EXTENDED   paris_rul_mc (Monte-Carlo P10/P50/P90 RUL band)
src/l3_agent/
  workorder.py            NEW  DRAFT->SIGNED->CLOSED lifecycle on the hash chain + hand-rolled tamper-evident PDF
  copilot.py               NEW  Ollama tool-calling copilot (get_srm_limit/get_rul/get_tail_state), citation-gated
README.md                      UPDATED    run steps, layout table, moat paragraph reflect the buffed system
docs/ACTION_PLAN.md        NEW  this document
```
