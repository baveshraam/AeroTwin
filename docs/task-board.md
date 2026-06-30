# Task Board — 2 people, both general/learning

You share code via git. Agree the **JSON contract** below on day one so you never
block each other: L0 emits it, L1/L2/L3 consume it.

```json
{ "tail": "VT-AXB", "ata_zone": "53", "location": "stringer 14",
  "defect_type": "crack", "size_mm": 8.0, "confidence": 0.84,
  "scan_date": "2026-07-01", "cycles": 12000 }
```

---

## Person A — Perception & Edge ("the camera side")
Owns everything that turns an image into a graded finding, and the Pi.

- [ ] **A1** Collect crack data (SDNET2018 / NEU-DET) + label ~150 aircraft-skin crops
      (Roboflow/CVAT) in YOLO-seg format → `data/dataset/`.
- [ ] **A2** Train `tools/train.py`; copy best weights → `models/weights/crack-seg.pt`.
- [ ] **A3** Verify `src/l0_detect/detect.py --real` returns real detections.
- [ ] **A4** ArUco sizing: print marker (`python -m src.l0_detect.sizing`), test on
      `tools/make_demo_panel.py` output; confirm mm matches a ruler.
- [ ] **A5** Tune `src/l0_detect/grade.py` + `data/srm_limits.csv` for your defects.
- [ ] **A6** Export INT8 ONNX; run on the Pi 5 (airplane mode); record latency/FPS
      (CPU-only — state it honestly).
- [ ] **A7** Build the induced-defect panel (scored crack, corrosion patch, dent,
      loose bolt as FOD) and photograph it with a phone.

## Person B — Twin, Agent & Pitch ("the software + story side")
Owns the twin, the prediction, the agent, and the deliverables.

- [ ] **B1** Polish `src/l1_twin/app.py` dashboard (already has growth chart) — make
      it screen-record-ready; add a tail selector if time.
- [ ] **B2** Calibrate `src/l2_progress/paris.py` constants; sanity-check that
      cycles-to-limit is monotonic and sane across two scans.
- [ ] **B3** Upgrade `src/l3_agent/agent.py` to a local LLM (Ollama phi3/qwen) over
      the manual corpus, keeping the **citation-required guardrail** + human gate.
- [ ] **B4** Confirm `src/l3_agent/audit.py verify()` stays true; show a tamper demo
      (edit a log line → verify() fails) — great for the security slide.
- [ ] **B5** Build the **PPT** on the official Section-4 template (content from
      `docs/deck-outline.md` + `problem-statement.txt`).
- [ ] **B6** Set up the **Google Drive folder** (Viewer access), add ID scans, add
      POC media.
- [ ] **B7** Record & edit the 3-minute demo video.

## Shared / integration
- [ ] **S1** Lock the JSON contract above (do this first).
- [ ] **S2** Run `python -m src.pipeline --image <real photo> --real` end-to-end and
      confirm L0→L3 all fire.
- [ ] **S3** Full offline dry-run on the Pi the night before any deadline.

## Git workflow (simple, safe for 2 people)
```bash
git checkout -b a-detector      # each works on a branch
# ... commit small, often ...
git push origin a-detector      # open a PR / merge to master
git pull origin master          # sync before starting each session
```
Keep big files (weights, videos) OUT of git (already in .gitignore) — share those
via Google Drive.
