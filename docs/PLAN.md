# AeroTwin-Edge — Plan & Strategy

## Where we are
- **Stage 1, pre-shortlist.** Goal: ship a working demo *now* to maximise shortlist
  probability. A team that shows running code + a clean video at application time
  stands out hard against pure-concept entries.
- **Team:** 2 people, both general/learning, collaborating via git.
- **Hardware:** Raspberry Pi 5 (8GB), **no camera / no Hailo yet**.
  - Workaround: photograph an induced-defect panel with a **phone**, copy the files
    to the Pi, run inference offline on the files. The "offline edge inference on the
    Pi" story holds 100%. Add a Pi camera / Hailo later for live capture & FPS.

## Two parallel tracks
1. **Submission (Google Drive folder)** — required by Rules 4.4/4.5:
   - `AeroTwin-Edge_Presentation.pptx` built on the **official Section-4 template**
     (open the rules page and match their exact fields). Content source = the
     application answers in `problem-statement.txt` + `docs/deck-outline.md`.
   - `/POC-media/` — screen recordings of the chain + dashboard, photos of the panel.
   - `/Team-IDs/` — scanned college ID cards for **both** members.
   - Sharing = **Anyone with the link → Viewer** (test in an incognito window).
2. **Build (this repo)** — the narrow L0→L3 chain, runnable offline today.

## Build scope (be ruthless — narrow & flawless beats broad & broken)
- **L0** detect + ArUco mm sizing + SRM severity grade ........ BUILD (core)
- **L1** per-tail SQLite twin + FastAPI dashboard ............. BUILD
- **L2** Paris-law progression → cycles-to-limit ............. BUILD
- **L3** citation-required agent + hash-chain audit .......... BUILD
- **L4** federated learning / **L5** ops / **L6** AR ......... DECK ONLY

## Sequence
- **Now:** repo runs end-to-end in mock mode (done). Drive folder + ID scans up.
  Deck skeleton from `docs/deck-outline.md`. Record a first rough clip.
- **Week 1:** train a small crack detector (`tools/train.py`); wire `--real`; test
  ArUco sizing on `make_demo_panel.py`; stand the dashboard up nicely.
- **Week 2:** run the real chain offline on the Pi 5 (airplane mode); record the
  clean 3-minute chain; finalise deck + upload media.

## The 3-minute demo (record this)
1. 30s hook: AOG costs ₹8L–1.25Cr/hr; inspection is manual, subjective, cloud-blocked.
2. Show a cracked panel → `python -m src.pipeline --image panel.jpg --real`.
3. Dashboard: tail history shows the crack grew 6.0 → 8.0 mm; "~N cycles to limit".
4. Agent drafts the SRM-cited work order; "human signs"; audit chain verified.
5. Pi in **airplane mode**, latency on screen. Close on the moat: edge + twin +
   federation + agent + certifiable — no competitor combines all five.

## Demo contingency (lazy-senior rule)
Record a PERFECT run as backup video. Test the WHOLE chain **offline first** — if it
needs the network it will fail on stage. Carry a spare flashed SD card.

## Honesty rules (judges will probe)
- Never fake an FPS/accuracy number — say CPU-only vs Hailo explicitly.
- All SRM data is illustrative; say so. The novelty is the *combination*, not one model.
- Report recall bias + POD methodology, not just mAP.
