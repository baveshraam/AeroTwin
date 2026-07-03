# Task Board — MRO re-tune split (2026-07-03)

Re-tuned for the **MRO/PHM re-center** (see [PLAN.md](PLAN.md) + ACTION_PLAN §3e). The
primary domain is now **predictive aircraft health management** on real telemetry
(NGAFID/C-MAPSS); crack detection is a demoted extra. Split by **ML-core vs App/Frontend**
so two people work concurrently. Hardware/Pi deployment stays deferred (software-only for now).
The old GPU/non-GPU split (all crack-detection work) is preserved below the line as history.

**Before either starts:** `git pull`. Keep big files (data, weights, videos) out of git.

---

## Track A — Predict core (the graded heart)

Owns: the new PHM pipeline — dataset loaders, feature engineering, model training + SHAP,
edge export. New dirs: `src/l4_predict/` (or similar), `data/phm/`. Don't touch the React
app or `src/l1_twin/static/` — Track B's territory.

- [ ] **A1** NGAFID loader — download (Zenodo, no login, 5.4 GB), parse the flight-header +
      per-flight 23-sensor frames, build the before/after-maintenance labels. Small sample
      committed for tests; full data stays out of git.
- [ ] **A2** C-MAPSS loader — FD001–FD004, build the RUL target (piecewise-linear cap ~125).
- [ ] **A3** First edge PHM model — **LightGBM** on engineered per-flight features (NGAFID
      classification) + a C-MAPSS RUL regressor. Report honest metrics (recall bias / RUL error),
      not just accuracy.
- [ ] **A4** **SHAP** on the model → top-driver sensors per prediction. This feeds the "why"
      panel — it is a headline feature, not optional.
- [ ] **A5** Export ONNX/TFLite INT8; record model size + a CPU inference timing (the Pi story).
- [ ] **A6** Expose it to the twin: a `predict(telemetry) → {maintenance_need|rul, band, top_features}`
      function the FastAPI layer can call and the twin can consume alongside the existing findings.

## Track B — App, twin integration & frontend (React)

Owns: `src/l1_twin/*` (FastAPI + API), the new **React** app, `docs/*`. Reuse the existing
twin/planner/agent/audit — wire the new predict output into them; don't rewrite them.

- [ ] **B1** Scaffold the **React** app (Vite + TS + Tailwind + react-three-fiber + Recharts).
      **Page 1 = Predictive Aircraft Health (pure MRO)**, Page 2 = Structural Inspection (extra),
      Page 3 = Fleet Learning & Edge. Only MRO on Page 1.
- [ ] **B2** JSON API: add `/api/predict` (+ per-tail prediction/RUL/SHAP) feeding the existing
      `/api/fleet` `/api/tail` `/api/whatif` etc. Keep the honest synthetic/real flags.
- [ ] **B3** Migrate the 3D twin (current vendored Three.js `static/index.html`) into
      **react-three-fiber** on Page 1 — health-shaded airframe, RUL bands, the "why flagged"
      SHAP panel, rupee ledger, edge HUD.
- [ ] **B4** Move all crack/corrosion/anomaly UI to **Page 2** (structural inspection).
- [ ] **B5** Wire the offline GenAI copilot to narrate the SHAP top-features as a plain-English
      maintenance note (citation-gated, deterministic fallback stays).

## Structural inspection — maintenance only (was the whole project, now the extra)

Existing crack pipeline is done and green; just keep it working as a Page-2 sensor. No new
investment unless Track A/B are fully landed.
- [ ] **X1** Keep `python -m src.pipeline --seed` green; ensure the crack detector still loads
      under `--real` after the re-tune. (Base model: ~67% box / ~43% mask recall — say so.)

## Shared
- [ ] **S1** Once A6 + B2 land: end-to-end check — telemetry in → prediction + why → twin →
      ledger → work order → audit, all offline.
- [ ] **S2** Full offline dry-run — deferred to the hardware/Pi phase (not blocking now).

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
