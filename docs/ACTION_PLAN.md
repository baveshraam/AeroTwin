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

## 3c. Session 3 (2026-07-02) — LIGHT UI overhaul + the twin now *learns*

Directive: the 3D twin looked bad (a light source detached from the airframe on orbit, an
incomplete/rough model, a dark theme the user rejected), and — ML training aside — pick the
best remaining thread and ship it. Two deliverables:

| Thread | Status | Where / notes |
|---|---|---|
| **Root-cause + fix the "floating light" bug** | ✅ done | The bright blob that detached from the plane on rotation was a **hard specular highlight** — the fuselage was near-mirror metal (`metalness:0.82`) and the cockpit was a `roughness:0.08` glass sphere, so the directional key light left a world-locked hotspot. Real aircraft are *painted*: airframe is now matte (`metalness:0.15, roughness:0.48`), the glossy cockpit sphere is gone (replaced by matte windshield panels), and the key light dropped 3.0→1.7 with a soft daylight rig. A matte surface physically cannot produce that hotspot. |
| **Light minimalist theme (whole UI)** | ✅ done | [static/index.html](../src/l1_twin/static/index.html) rebuilt on a **light** 3-colour system: soft-light ground `#eef1f5`, white surfaces, near-black ink `#14181f` at 3 opacities, one warm amber `#e07d17` = "look here". Floating glass cards (blur + hairline + soft shadow), rounded 11–16px radii, refined type scale. Same honest rule kept: calm neutral = healthy, amber = attention. Stage/floor/grid/fog/env all recoloured light; defect halos switched from additive (invisible on white) to normal-blended amber so they read on a light stage. |
| **More complete aircraft model** | ✅ done | Refined `LatheGeometry` profile (rounded ogive nose, long tapered tail cone), bevelled airfoil wings **with canted winglets**, horizontal + vertical stabs, under-wing nacelles with intake lip + fan + **spinner + exhaust cone** + pylon, cabin window strip, **cockpit windshield panels**, subtle door outlines. Health still tints the airframe toward amber only when it needs attention. |
| **Bayesian per-tail growth-rate learning (was deferred #1 — NOW DONE)** | ✅ done + self-checked | [src/l2_progress/bayes.py](../src/l2_progress/bayes.py). Closed-form **Normal-Normal** conjugate update: each defect's crack-growth rate starts at the **federated global prior** (`federated.simulate()` now also emits `global_spread`, the right scale for a per-tail prior) and is updated by that defect's own consecutive-scan growth observations. Posterior SD shrinks monotonically with each scan; the tightened rate distribution is pushed through `remaining_mm / rate` into a **learned P10/P50/P90 RUL band** narrower than the one-size-fits-all physics band. Wired into `twin.tail_state()` as `rul_learned` and surfaced in the UI under each defect's RUL band ("prior ±X → posterior ±Y · ×N tighter"). Self-check: posterior never widens, pulls toward faster-than-prior data, ×10 tighter after 4 obs; band ordering holds. This makes the "digital twin that learns" claim real and ties **federated → per-tail Bayesian → RUL band** into one story. |

Verification this session: `python -m src.l2_progress.bayes`, `python -m src.l1_twin.federated`,
`python -m src.l1_twin.twin` all green; `python -m src.pipeline --seed` still nets ₹6.12 Cr
(1 grounded, 2 serviced, 1 deferred); FastAPI `TestClient` confirms `/api/tail/{t}` carries
`rul_learned` (×1.4 tighter on the seed's 2-scan defects — more scans tighten further) and
`/api/federated` carries `global_spread`; index serves 200 and the inline JS parses clean.
(WebGL can't be screenshotted in this headless env — the visual needs a human eye, but the
material/lighting fix is deterministic, not a tuning guess.)

## 3d. Session 4 (2026-07-02, third pass) — "floating light" killed, jet completed, dashboard merged, DP

Directive: the twin still looked bad — a light "emitting from inside the plane but floating
outside when you rotate it", an incomplete/garbage-looking model, and the separate classic
dashboard preview was never folded into the main app. Plus: pick the best no-GPU thread and
ship it. Five deliverables:

| Thread | Status | Where / notes |
|---|---|---|
| **Root-cause + fix the *real* floating-light bug** | ✅ done | The blob that detached from the airframe on orbit was **not** a specular this time — it was the amber defect **halo sprites**, created with `depthTest:false` ([static/index.html](../src/l1_twin/static/index.html), `glowSprite()`). That flag draws a sprite on top of everything regardless of 3D depth, so a defect glow on the *far* side of the fuselage still rendered in front of the plane and looked like a light floating outside it. Fix: `depthTest:true` (kept `depthWrite:false` so halos still blend) → halos are now correctly occluded by the airframe. Session 3 had fixed speculars but never touched the sprites, which is why it persisted. |
| **Hotspots redrawn as surface-conforming markers** | ✅ done | Each defect is now a flat **amber ring decal laid on the skin** (oriented to the fuselage surface normal) + a small emissive core + the (now depth-tested) soft halo. Reads as a painted inspection marker, occludes naturally, no floating billboard. |
| **More complete aircraft model** | ✅ done | Kept the **parametric** `LatheGeometry` fuselage on purpose — the clickable ATA-zone defect hotspots are computed from `radiusAt()/xToT()/segAngle()`, so a black-box glTF swap would break the twin's core interaction (and can't be visually verified in this headless env). Added: **tricycle landing gear** (nose + twin-wheel mains) for a complete parked stance, a **wing-body fairing** so the wing root blends instead of looking stuck-on, an **amber tail-fin brand accent** (the one warm mark on a calm airframe), softer matte materials (killed the glossy nacelle lip), and a **Top / Side / Orbit** view switcher. |
| **Classic dashboard preview merged into the main app** | ✅ done | [data/dashboard_preview.html](../data/dashboard_preview.html)'s richer views are now in the 3D app: a **Fleet risk board** (per-tail prescribed action + slot + AOG-risk column, click-to-select, from `/api/fleet`'s `plan`) and a **per-defect scan-history table** (date / cycles / size / grade, from `/api/tail`'s `history`). |
| **Interactive What-if planner surfaced** | ✅ done | `/api/whatif` (defer-a-tail cost) and `/api/scenario/capacity` (add-slots risk released) were live but the frontend never used them — now a compact planner with two dropdowns re-prices the plan live and shows the delta (base net vs scenario net). |
| **Differential privacy on federated aggregation (deferred #3 — NOW DONE)** | ✅ done + self-checked | [src/l1_twin/federated.py](../src/l1_twin/federated.py). Added `dp_site_release()` (Laplace mechanism: each site clips its rates to `[0, clip]` bounding any one tail's influence, then adds noise at scale `sensitivity/ε` where the clipped-mean L1 sensitivity is `clip/n`) and `differentially_private_average()` (FedAvg over DP releases — averaging is post-processing, so it costs no extra ε; the global prior is ε-DP w.r.t. every site). `simulate()` now emits a `dp` block (ε, clip, mechanism, DP global mean, noise cost vs plain FedAvg); surfaced in the UI's federated panel as an `ε=1.0` badge. Self-check: at ε=1 the DP mean stays within 0.5 of plain FedAvg (utility preserved, `0.767` vs `0.801`, only `0.034` mm/kcyc of noise) and inside the valid `[0, clip]` range. |

Verification this session (all green): `python -m src.l1_twin.federated` (FedAvg + new DP self-check),
`python -m src.l2_progress.bayes`, `python -m src.l1_twin.twin`, and `python -m src.pipeline --seed`
(still nets ₹6.12 Cr — 1 grounded / 2 serviced / 1 deferred). FastAPI `TestClient`: index serves 200
with all new markup (`renderBoard`, `runWhatif`, `histTable`, `depthTest:true`, landing gear, DP badge)
present; `/api/federated` carries the `dp` block; `/api/whatif` + `/api/scenario/capacity` return the
expected keys; `/api/tail/{t}` carries per-defect `history`. The inline app JS passes `node --check`
(no syntax errors).

**Visual verification (new this session):** the WebGL scene was rendered headless via Playwright +
Chromium (SwiftShader) and screenshotted — no console/page errors. Confirmed with hard evidence:
(1) the airframe renders (73 parts / 34k triangles, centre projects to screen-centre); (2) the
floating-light bug is gone — an underside/far-side orbit angle (which would have exposed a
depth-broken halo) shows **zero** amber glow outside the airframe; (3) defect hotspots render as amber
markers **on the skin**, not floating. **Key visual finding:** a near-white airframe (`#f4f6f9`) was
invisible against the light stage (white-on-white) — the fix was a mid silver-grey `#aeb7c2` airframe
plus a close low side-quarter hero framing so the fuselage/windows/wing fill the frame and read.

## 3e. Session 5 (2026-07-03) — registration-readiness pass: honesty audit, real training, real LLM

Directive: finish the project for July 5 registration. Sync a teammate's UI push, then a
priority-ordered pass — fix the most damaging honesty gap first, start real training, get
a real LLM running, audit every "simulated" label end-to-end, fix hotspot placement math,
clean up, update docs. UI/`static/` was explicitly off-limits this session.

| Priority | Status | Where / notes |
|---|---|---|
| **P0 — `model_version` dishonesty** | ✅ fixed | `detect_defects()` in [detect.py](../src/l0_detect/detect.py) now stamps `model_version` itself based on what actually ran, and [pipeline.py](../src/pipeline.py) reads that instead of inferring from the `--real` flag (which previously stamped `"yolov8-seg"` even when the mock path silently fired). Three honest values: `"yolov8-seg"` (a real model ran), `"mock-v0"` (the intentional demo mock / seeded fleet), `"mock-fixed"` (`--real` asked but fell back — flagged distinctly so a silent fallback is visible, never a false real claim). The `mock-v0` value reconciles with the teammate's UI "SYNTHETIC DATA · mock-v0" badge, which reads `model_version` dynamically. |
| **P1 — real crack-seg training** | 🔄 running | This machine has a CUDA GPU (RTX 4060, 8GB) unlike the prior CPU-only session. Found and fixed a real bug on the way: `fetch_datasets.py` never redirected ultralytics' dataset cache, so `crack-seg` was landing in a stray top-level `datasets/` instead of `data/datasets/` — consolidated, fixed the script, added `/datasets/` to `.gitignore`. Kicked off `yolov8s-seg`, imgsz 1280, 40 epochs (had to restart once — the script's batch=8 default was pinning 97% VRAM and would've taken ~22hrs; batch=6 is the safe setting). ArUco sizing path independently re-verified: real marker → 0.2513 mm/px, no marker → correct 0.025 fallback. |
| **P2 — real local LLM** | ✅ done, with a caveat | Ollama installed and running. **Found: `phi3` (the code's original default) cannot do tool-calling at all** — confirmed live, Ollama 400s with `"does not support tools"`. Switched `OLLAMA_MODEL` default to `llama3.2:3b`, verified real tool-calling end-to-end (SRM limit / RUL / tail-state questions all trigger genuine calls into the twin). **Found and fixed a second gap**: the LLM fabricated a citation ("SRM-001, Section 5.3.1" — doesn't exist) for a plain RUL question involving no citation at all — the citation guardrail only covered `draft_with_copilot()`'s work-order path, not the general `ask()` chat path. Added `_drop_uncited_srm()` mirroring the same guardrail, self-checked deterministically. **Known limitation, not patched further**: tool-calling isn't fully reliable even on a supported model — re-running an identical question 3x, it worked once and twice returned malformed pseudo-JSON as plain text. Inherent small-model behavior; the guardrails exist because of this, not instead of it. |
| **P3 — synthetic/simulated labeling audit** | ✅ fixed (converged with teammate) | I first added `synthetic: true` flags in `shm.py`/`federated.py`. The teammate's branch independently added the **same** honesty flags at the API layer in [app.py](../src/l1_twin/app.py) (`/api/shm` → `synthetic:true`, `/api/federated` → `simulated:true`, each with a `synthetic_note`) — plus the matching UI chips (SYNTHETIC STREAM / SIMULATED) and the [honesty-qa.md](honesty-qa.md) judge script. On merge I **removed my function-level flags** and kept his API-layer labeling as the single owner (avoids the dict-spread emitting two keys, e.g. both `synthetic` and `simulated`, for the same fact). Net: every synthetic source is flagged in API + UI + docs, consistently. The telemetry HUD's `*`-only on-screen hint is now backed by his hover-note + the honesty ledger, so it's no longer the only signal. |
| **P4 — hotspot placement math** | ✅ solved (by teammate, superseding my tool) | I first fit a real fuselage-radius profile from `Airplane-body/airplane.obj` (isolating the `11803_Airplane_body` sub-mesh, replicating `loadAirframe()`'s transform) into `tools/fit_hotspot_radius.py`, to fix the old constant-`R=0.72` `radiusAt()` formula (off by up to 0.42 world units at nose/tail). **On merging the teammate's `feat/ui-hardening-honesty-hotspots` branch, his independent fix turned out better and superseded mine**: he *removed* `radiusAt`/`xToT` entirely and replaced them with **raycasting against the actual loaded mesh** (`skinPointFor`/`fuselageAxisAt`) — markers land exactly on the real skin regardless of geometry, upper-hemisphere only, `SHOW_HOTSPOTS` flipped back to `true`. My radius-fit tool was therefore removed during the merge (it generated code for a `radiusAt` that no longer exists). His approach is the one that ships. |
| **P5 — cleanup** | ✅ done | Removed an unused import (`copilot.py`), two harmless f-string lints, one unused variable, a stray unreferenced 5.5MB model file, and a duplicate ~127MB dataset download. Added the genuinely-missing `scikit-learn` to `requirements.txt` (used directly by `train_anomaly.py`, not covered transitively by ultralytics) and removed two declared-but-never-imported deps (`jinja2`, `python-dateutil`). Investigated and deliberately kept `tools/train_anomaly.py` (real MVTec AUROC validator, not redundant with `anomaly.py`) and `tools/render_dashboard.py` (documented fallback demo path in the submission runbook). |
| **P6 — docs accuracy** | ✅ this entry | README gained a "what's real vs. simulated" status table and two corrections (missing `anomaly.py` in the file layout; Ollama wrongly attributed to `agent.py` instead of `copilot.py`). Both docs' `ollama pull phi3` instruction corrected to `llama3.2:3b` (phi3 can't do tool-calling — same finding as P2). |

## 4. What's still open

**Base crack training is validated and, as of session 5, actually running to convergence**
on a GPU (`yolov8s-seg`, imgsz 1280, 40 epochs) — see 3e above for live status. The
remaining depth is the **on-domain aircraft fine-tune**, which needs gated data:
1. Free-tier account signups (IEEE DataPort for Aircraft_Fuselage_DET2023, Kaggle for
   Severstal, Roboflow API key for the aircraft-skin sets) — these gate `--stage adapt`.
2. Once the base run finishes: `--deploy-base` so `--real` uses it, `--export` for INT8
   ONNX, `python -m src.pipeline --image <panel.jpg> --real` — confirm it's genuinely
   detecting (not just running) before calling this done.
3. `--stage adapt --data data/datasets/aircraft/data.yaml` once the gated aircraft set is
   pulled → promotes to `crack-seg.pt` (the on-domain flagship).
4. ✅ **Anomaly branch is now coded** ([src/l0_detect/anomaly.py](../src/l0_detect/anomaly.py),
   real PatchCore, self-checked). It fits any folder of normal images
   (`train_from_folder`) — point it at AeBAD / MVTec 'good' sets when pulled.

**Deliberately deferred (not blocking, named so they don't rot into "forgotten"):**
- ✅ **Bayesian per-tail growth-rate updating — DONE (session 3)**
  ([src/l2_progress/bayes.py](../src/l2_progress/bayes.py)). The twin now learns per tail:
  Normal-Normal posterior seeded by the federated prior, tightening each defect's RUL band
  as scans arrive (`rul_learned` in `tail_state`, shown in the UI). Next refinement would be
  a full Normal-inverse-gamma model (learn the observation noise too) and persisting the
  posterior across sessions so it accumulates over a tail's whole service life.
- Real sensor hardware integration for SHM (today's `shm.py` is a physically-motivated
  synthetic stream + a real detector algorithm — swap the stream for field telemetry
  later; the CUSUM detector and twin interface don't need to change).
- ✅ **Differential privacy on the federated aggregation — DONE (session 4)**
  ([src/l1_twin/federated.py](../src/l1_twin/federated.py), `dp_site_release` /
  `differentially_private_average`, Laplace mechanism + rate clipping, ε-DP per site,
  self-checked, surfaced in the UI). Next refinement would be **secure aggregation**
  (so the coordinator never sees even a single site's noised value) and **privacy
  accounting** across repeated releases (composition / RDP), plus a Gaussian-mechanism
  option with an (ε, δ) budget.

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

Optional local LLM copilot: install Ollama, `ollama pull llama3.2:3b` (must be a
tool-calling-capable model — confirmed live that `phi3` is NOT and Ollama 400s on it),
then the "MRO copilot" box in the UI (or `POST /api/ask`) gets real prose instead of
the tool-only fallback.

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
