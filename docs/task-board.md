# Task Board — current split (2026-07-03, registration closes 2026-07-05)

Supersedes the old "Person A / Person B" split below the line — that was written for
the project's early, general-skills-split phase. Most of it is done (see
[ACTION_PLAN.md](ACTION_PLAN.md) for the full history/status table). What's left is
narrow enough to split by **GPU vs. non-GPU** so two people can work concurrently
without touching each other's files. Hardware/Pi deployment is explicitly deferred —
software-only for now.

**Before either of you starts:** `git pull` — `feat/session5-honesty-real-ml` is the
active branch, up to date with origin as of this writing.

---

## Track A — GPU owner

Owns: running `tools/train.py` / `tools/train_anomaly.py`, everything under
`models/weights/`, `runs/`, `data/datasets/`. Don't edit `src/l1_twin/*`,
`src/pipeline.py`, or `docs/task-board.md` — that's Track B's territory this round.

- [ ] **A1** Deploy the completed base model: `python tools/train.py --deploy-base`,
      then `python -m src.pipeline --image data/samples/panel_demo.png --real` —
      confirm it genuinely detects (not just runs) before calling it done. It's a
      real crack-corpus detector (67% box recall / 43% mask recall on held-out val),
      not yet aircraft-adapted — say so if you demo with it.
- [ ] **A2** Re-run the INT8 export for real against the deployed model with the full
      calibration set: `python tools/train.py --export` (calibration data already
      defaults to real crack images, not the old network-downloaded COCO stand-in).
      Record the ONNX file size + a CPU inference timing.
- [ ] **A3** Get a free Roboflow API key (the one remaining human dependency), then:
      `python tools/fetch_datasets.py aircraft-dent-crack aircraft-skin-defects` →
      `python tools/fetch_datasets.py --merge-aircraft` (auto-validates itself) →
      `python tools/train.py --stage adapt --data data/datasets/aircraft/data.yaml`.
      This is the on-domain fine-tune — the credibility flagship over the base model.
- [ ] **A4** (Optional, time-permitting) Anomaly branch: fit AeBAD (the aerospace pick,
      `python tools/fetch_datasets.py --list` for the link) the same way MVTec bottle
      was fit — `from src.l0_detect.anomaly import train_from_folder;
      train_from_folder("<aebad_normal_dir>")`. Currently only MVTec-validated
      (AUROC 1.000, real data).

## Track B — non-GPU owner

Owns: `src/l1_twin/*` (app.py, view.py, static/), `src/l0_detect/detect.py`,
`src/pipeline.py`, `tools/render_dashboard.py`, `docs/*`. Don't run any training or
touch `tools/train.py`/`tools/train_anomaly.py`/`models/weights/`/`runs/` — treat
those as read-only inputs produced by Track A.

- [ ] **B1** Merge `origin/finish-l0-l3-app` (teammate's unmerged branch, commit
      `9286534`). Real conflicts in `src/l1_twin/view.py`, `src/pipeline.py`,
      `tools/render_dashboard.py`, `docs/task-board.md` (this file — expect to
      reconcile it against whatever's in that branch), plus two generated/binary
      files (`data/dashboard_preview.html`, `data/samples/panel_demo.png` — just
      take whichever is newer or regenerate). It contains real value: `audit.py`
      `verify()` failing safe on corrupt/tampered JSON (merges clean, no conflict —
      take it as-is), and honest `--real`-with-no-weights labelling in
      `pipeline.py` — check this against the current `model_version` logic in
      `detect.py`/`pipeline.py` before taking the teammate's version verbatim, they
      may have converged on the same fix independently.
- [ ] **B2** Wire the anomaly branch into the UI/API — today `[L0b]` only prints to
      console (`src/pipeline.py`'s `run_scan()` already returns an `anomaly` key in
      its result dict, just not exposed via `/api/*` or rendered in
      `static/index.html`). Add an endpoint + a small panel, same honest-labelling
      pattern as the SHM/federated chips (this one's real data now, so no
      "synthetic" caveat needed — label it "PatchCore, real MVTec-validated,
      bank fit on real normal images").
- [ ] **B3** SAHI tiling at inference for small/thin cracks (`train.py`'s own
      docstring calls this out, never implemented) — `src/l0_detect/detect.py`'s
      real-mode path does a single plain forward pass today; a full-res image can
      lose a thin crack when downscaled to the model's input size.
- [ ] **B4** Docs pass: `docs/demo-script.md` still says the detector is "mid-training"
      (training finished — reword to "trained, not yet deployed to the live demo
      path" or update once A1 deploys it). Sanity-check `docs/deck-outline.md` /
      `honesty-qa.md` against whatever B1/B2 change.

## Shared / whichever track gets there first
- [ ] **S1** Once A1 (deploy) + B1 (merge) both land: full `python -m src.pipeline
      --seed` then `--image <real photo> --real` end-to-end check.
- [ ] **S3** Full offline dry-run — deferred to the hardware/Pi phase per current
      direction (not blocking software completeness now).

---

# (superseded) Original Person A / Person B split — kept for history

Problem statement: **Edge AI for Digital Twin-Enabled MRO**. The twin is the product;
the detector is one sensor feeding it. JSON contract locked early (see git history) —
L0 (sensor) emits it, the twin/predict/agent consume it.

## Person A — Sensor & Edge ("the camera side")
- [x] **A1** Collect crack data — done, `crack-seg` (4,029 real imgs, auto-downloads).
- [x] **A2** Train `tools/train.py` — done, see Track A above for current status.
- [ ] **A3** Verify `src/l0_detect/detect.py --real` returns real detections — folded
      into Track A / A1 above.
- [ ] **A4** ArUco sizing — verified independently this session (real marker 0.2513
      mm/px, no-marker fallback 0.025 — both correct).
- [ ] **A5** Tune `src/l0_detect/grade.py` + `data/srm_limits.csv` for your defects.
- [ ] **A6** Export INT8 ONNX; run on the Pi 5 — export path proven (Track A A2);
      Pi run itself deferred to the hardware phase.
- [ ] **A7** Build the induced-defect panel and photograph it with a phone.

## Person B — Twin, Fleet & Pitch ("the product + story side")
- [x] **B1** Polish `src/l1_twin/view.py` — done (fleet risk board, work-order
      surfacing, multiple UI passes — see ACTION_PLAN.md sessions 2-5).
- [x] **B2** Calibrate `twin.py` / `paris.py` constants — done, self-checks green.
- [x] **B2b** Calibrate `planner.py` economics — done, self-check green.
- [x] **B3** Local LLM (Ollama) — done, `llama3.2:3b` (phi3 can't tool-call).
- [x] **B4** `audit.py verify()` tamper demo — done (and a fail-safe fix pending in
      the finish-l0-l3-app merge, see Track B B1 above).
- [ ] **B5** Build the PPT (`docs/deck-outline.md`).
- [ ] **B6** Google Drive folder + POC media.
- [ ] **B7** Record the 3-minute demo video (`docs/demo-script.md`).

## Git workflow (simple, safe for 2 people)
```bash
git checkout -b your-branch-name
# ... commit small, often ...
git push origin your-branch-name       # open a PR / merge to feat/session5-honesty-real-ml
git pull                                # sync before starting each session
```
Keep big files (weights, videos) OUT of git (already in .gitignore) — share via Drive.
