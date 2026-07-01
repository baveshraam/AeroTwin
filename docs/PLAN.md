# AeroTwin-Edge — Plan & Strategy

## Problem statement we own
**Edge AI for Digital Twin-Enabled MRO** (InnoVent-27 · Aerospace). We are *inside the
digital-twin vertical*, not the inspection one. Inspection/defect-detection is our
sensor; the **twin is the product** — the per-tail, per-fleet system-of-record that
drives condition-based maintenance (CBM+).

## The real problem, in MRO's language
Structural checks run on a fixed **calendar / hard-time interval**. That simultaneously
**over-maintains** the healthy majority of the fleet (wasted downtime & labour) and
**under-maintains** the few fast-growing defects that outrun the interval (safety + AOG
risk, ~₹8L–1.25Cr/hr). There is no continuous per-tail condition history to schedule
against, and cloud can't hold it (ITAR-isolated hangars). The twin is the missing record.

## Where we are
- **Stage 1, pre-shortlist.** Ship a working demo *now*. A team with running code + a
  clean video at application time beats pure-concept entries.
- **Team:** 2 people, both general/learning, collaborating via git.
- **Hardware:** Raspberry Pi 5 (8GB), **no camera / no Hailo yet**. Workaround:
  photograph an induced-defect panel with a **phone**, copy files to the Pi, run offline
  inference on the files. The "offline edge twin on the Pi" story holds 100%.

## Build scope (narrow & flawless beats broad & broken)
- **Sensor (L0)** detect + ArUco mm sizing + SRM severity grade .......... BUILD
- **Twin (L1)** per-tail SQLite record + **twin brain** (health index, RUL,
  fleet risk board, condition-based scheduling vs calendar) + dashboard ... BUILD ← hero
- **Prescribe + price (L1b)** capacity-constrained fleet plan + **rupee ledger**
  (downtime recovered + AOG risk avoided − risk carried) ................. BUILD ← the payoff
- **Predict (L2)** Paris-law / empirical growth → cycles-to-limit ......... BUILD
- **Agent (L3)** citation-required work order + hash-chain audit .......... BUILD
- **Federated fleet learning / ops / AR** ............................... DECK ONLY

## What makes it a *platform*, not a defect log (predict → prescribe → price)
`src/l1_twin/twin.py` is the brain (**predict + prescribe**):
- **Health index (0–100)** per tail from worst open defect vs its SRM limit.
- **RUL** — minimum cycles-to-limit across the tail's open defects.
- **Condition-based decision** — PULL FORWARD a fast grower, SAFE TO DEFER a healthy
  jet, GROUND a beyond-limit one — each quantified against the calendar baseline.
- **Fleet risk board** — every tail ranked worst-first; the planner's morning screen.

`src/l1_twin/planner.py` is the payoff (**price**):
- **Capacity-constrained plan** — with only N hangar slots, service the highest-risk
  tails first, defer the healthy, and make the *carried* risk explicit when at-risk > slots.
- **Rupee ledger** — downtime recovered (deferred healthy checks) + AOG risk avoided
  (fast growers serviced in time) − risk carried = **net value vs the blind calendar**.
- All money/capacity constants are ILLUSTRATIVE and in one place — calibrate per operator.

## Sequence
- **Now:** repo runs end-to-end in mock mode (done). Fleet seed + dashboard fleet board
  (done). Drive folder + ID scans up. Deck skeleton from `docs/deck-outline.md`.
- **Week 1:** train a small crack detector (`tools/train.py`); wire `--real`; test ArUco
  sizing on `make_demo_panel.py`; calibrate the twin's scheduling constants.
- **Week 2:** run the real chain offline on the Pi 5 (airplane mode); record the clean
  3-minute chain; finalise deck + upload media.

## The 3-minute demo (record this)
1. 30s hook: fleets are maintained on a blind calendar → over-maintain the healthy,
   miss the fast growers. AOG costs ₹8L–1.25Cr/hr. Cloud is blocked in ITAR hangars.
2. Show a cracked panel → `python -m src.pipeline --image panel.jpg --real`.
3. **Twin:** tail VT-AXB grew 6.0 → 8.0 mm; health drops; "~N cycles to limit".
4. **Fleet risk board:** four tails ranked — one GROUNDED, two PULL FORWARD, one SAFE TO
   DEFER. *This* is condition-based maintenance on a screen.
5. **The money slide:** the prescriptive plan + rupee ledger — "ground 1, service 2,
   defer 1 → ~₹6 Cr net value this window vs the calendar." Nobody else prices it.
6. Agent drafts the SRM-cited work order; human signs; audit chain verified.
6. Pi in **airplane mode**, latency on screen. Close on the moat: edge + twin + fleet
   CBM + agent + certifiable — no competitor combines all five.

## Demo contingency (lazy-senior rule)
Record a PERFECT run as backup video. Test the WHOLE chain **offline first** — if it
needs the network it fails on stage. Carry a spare flashed SD card. `--seed` resets the
twin to a clean, deterministic 4-tail fleet, so the board looks the same every take.

## Honesty rules (judges will probe)
- Never fake an FPS/accuracy number — say CPU-only vs Hailo explicitly.
- All SRM data + Paris/scheduling constants are illustrative; say so. The novelty is the
  *twin + fleet CBM combination*, not one model.
- Report recall bias + POD methodology, not just mAP.
