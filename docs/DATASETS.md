# AeroTwin-Edge · Real datasets

The demo runs on a **mock sensor** so the whole *predict → prescribe → price* story works
with zero downloads. This is the ground-truth path to swap that synthetic data for **real,
verified public datasets** — one branch at a time. Every link below was checked live
(Jul 2026). Pull them with `tools/fetch_datasets.py` (see keys in **bold**).

```bash
python tools/fetch_datasets.py --list        # ranked registry + access gate for each
python tools/fetch_datasets.py --all-auto    # pull everything that needs no login
python tools/fetch_datasets.py <key>         # one dataset by key
```

Access gates: **no login** (direct/ultralytics) · **kaggle token** · **roboflow key** ·
**account/consent** (free account or a consent click).

---

## 1 · SENSE — defect detection & sizing (YOLOv8-seg)

Feeds `src/l0_detect`. Strategy: pre-train on a large generic **crack** corpus, then
fine-tune on **on-domain aircraft** imagery.

| Key | What | Size | Access | License |
|---|---|---|---|---|
| **crack-seg** | Ultralytics crack instance-seg, 1 class | 4,029 imgs | no login | AGPL-3.0 |
| **crackseg9k** | 10 crack sets merged (Crack500/DeepCrack/SDNET/CrackTree/GAPs/Volker/Rissbilder/Masonry/Ceramic), 400×400 pixel masks | 9,255 imgs | account (Harvard Dataverse) | CC |
| **sdnet2018** | Cracked/uncracked concrete, cracks 0.06–25 mm, shadows+debris | 56,000 imgs | account (USU) | CC |
| **aircraft-fuselage-det2023** ★ | **On-domain flagship** — real fuselage defects, 4 types, COCO/VOC/YOLO + unlabeled | 5,601 imgs | free IEEE acct | research |
| **aircraft-skin-new** | Aircraft skin: crack/dent/missing-head/paint-off/scratch, YOLOv8 | 1,115 imgs | roboflow key | open |
| **aircraft-skin-defects** | IISc skin set: crack/dent/scratch/paint-peel/missing-head | 372 imgs | roboflow key | open |
| **aircraft-dent-crack** | Aircraft dent+crack, YOLOv8 export | small | roboflow key | open |
| **corrosion-css** | Corrosion **severity** seg, 4 states (good/fair/poor/severe), pixel masks | 440 imgs | account (VT Figshare) | open |
| **severstal** | Steel surface defects, 4 classes, masks (corrosion/pitting transfer) | ~12k | kaggle token | comp |
| **neu-det** | Steel strip, 6 classes incl. crazing/cracks (boxes) | 1,800 imgs | account (Kaggle) | open |

★ = the one that makes it *aircraft*. Recommended path: `crack-seg`/`crackseg9k` → fine-tune
on `aircraft-fuselage-det2023` + `aircraft-skin-new`; add `corrosion-css` for the corrosion class.

---

## 2 · ANOMALY — flag "never-seen" damage (train-on-normal)

Feeds an unsupervised branch (autoencoder / PatchCore) that needs **no defect labels** —
it learns "normal" skin and flags novelty. The honest answer to "what about damage types
you never labelled?"

| Key | What | Access | License |
|---|---|---|---|
| **aebad** ★ | Aero-engine blade anomaly (AeBAD-S imgs + AeBAD-V video); test = breakdown/ablation/groove/fracture; built-in domain shift | GitHub MMR → Google Drive | research |
| **mvtec-ad** | 15-category industrial anomaly benchmark — validates the pipeline | account (MVTec) | CC BY-NC-SA (**non-commercial**) |

---

## 3 · PREDICT — calibrate the twin's fatigue model (the synthetic→real win)

This is the branch that today uses **illustrative Paris-law constants** in
`src/l2_progress/paris.py` and `src/l1_twin/`. These are the real crack-growth datasets that
replace those constants with fitted `C, m` and empirical **P10/P50/P90** RUL bands.

| Key | What | Why it matters here | Access |
|---|---|---|---|
| **virkler** ★ | Virkler (1979): 68× **2024-T3 aluminium** specimens, 164 crack lengths each; a₀ 9 → 49.8 mm, Δσ 48.28 MPa, R=0.2 | The canonical benchmark for **stochastic crack growth** — fit Paris `C,m` and the scatter that drives the Monte-Carlo RUL bands directly | CRAN `HMMRel::Virkler25` / GitHub `SimoneHermann/hierRegSDE` |
| **nasa-fatigue-lapjoint** ★ | NASA PCoE #18: fatigue crack growth on **Al lap-joints** with **Lamb-wave** signals (T1–T8) | Real between-inspection sensor stream → grounds the SHM/CUSUM branch (`src/l1_twin/shm.py`) | no login (direct zip) |
| **cmapss** | NASA C-MAPSS FD001–FD004: turbofan run-to-failure | De-facto **RUL** benchmark — reference for the uncertainty methodology (not fuselage imagery) | no login (direct zip) |

> With Virkler + the lap-joint set, the twin stops asserting a growth rate and starts
> *fitting* one from real 2024-T3 fatigue data — the same aluminium family as a fuselage skin.

---

## Notes

- **SRM allowable limits & rupee/capacity economics stay illustrative** — those are
  OEM-/operator-controlled and must be calibrated per structure before any real use
  (see the disclaimer in `README.md`). No public dataset substitutes for a controlled SRM.
- Licenses vary; **MVTec AD is non-commercial**. Check each before anything beyond a POC.
- Ultralytics `crack-seg` is AGPL-3.0 (same as YOLOv8) — fine for the POC, note for products.
