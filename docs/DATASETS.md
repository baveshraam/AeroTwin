# AeroTwin · Datasets

**Re-tuned 2026-07-03.** The primary domain is now **predictive aircraft health management
(PHM)** — sensor telemetry → failure/RUL prediction. Those datasets come **first**. The
crack/corrosion image datasets are for the **structural-inspection extra feature** and are
now in §Structural at the bottom. Every link checked live (Jul 2026).

---

## 1 · PREDICT — the core (sensor telemetry → failure / RUL)  ★ PRIMARY

Feeds the edge PHM model (LightGBM / MiniRocket) → maintenance-need classification + P10/P50/P90
RUL band + SHAP explanation. This is the graded core of the project.

| Key | What | Task | Size | Access | License |
|---|---|---|---|---|---|
| **ngafid** ★ | **NGAFID** — real general-aviation flight records: **~29k flights / 31k hrs**, **23 sensors @1Hz** (engine RPM, oil temp/pressure, EGT, airspeed, pitch/roll, OAT…), labelled **before/after** 2,111 unplanned maintenance events across 36 issue types | maintenance-need **classification** (real, non-simulated fleet data) | 5.4 GB (`2days.tar.gz` 1.1 GB + `all_flight.tar.gz` 4.3 GB) | no login (Zenodo) | **CC BY 4.0** |
| **cmapss** ★ | **NASA C-MAPSS** FD001–FD004 — turbofan run-to-failure, 21 sensors + 3 op settings, train/test/RUL-truth | **RUL regression** (the de-facto PHM benchmark) | few MB | no login (direct zip / Kaggle) | public (NASA PCoE) |
| n-cmapss | NASA N-CMAPSS (Turbofan Sim-2) — derived from real flight profiles, 8 subsets, 7 failure modes, HDF5 | RUL, realistic upgrade of C-MAPSS | multi-GB | no login | open (CC BY, Chao/Fink 2021) |

- **NGAFID** — paper arXiv 2210.07317; repo `github.com/hyang0129/NGAFIDDATASET` (loaders +
  InceptionTime/ConvMHSA/MiniRocket reference code, **no pretrained weights — we train our own**).
- **C-MAPSS** — Kaggle `behrad3d/nasa-cmaps`; classic RUL benchmark. Use for the "generalises
  to turbofans" thread; don't make it the headline (it's the most tutorial-ised set in aerospace).
- **Model direction:** LightGBM (explainable via SHAP, tiny on the Pi) on engineered per-flight
  features, and/or MiniRocket on raw sequences. Train off-device (laptop/Colab) → export
  ONNX/TFLite INT8 → infer on the Pi. *Exact model + feature set finalised later.*

> Recommended path: **NGAFID → LightGBM + SHAP** for the explainable maintenance-need core;
> **C-MAPSS → RUL regression** as the second, turbofan thread.

---

## 2 · Structural inspection — the EXTRA feature (crack/corrosion images)

Feeds `src/l0_detect` (YOLOv8-seg detector + PatchCore anomaly). Framed as *one more sensor
into the same twin*, shown on Page 2 of the app, not the headline. Pull via
`tools/fetch_datasets.py` (see keys in **bold**).

### 2a · SENSE — defect detection & sizing (YOLOv8-seg)
| Key | What | Size | Access | License |
|---|---|---|---|---|
| **crack-seg** | Ultralytics crack instance-seg, 1 class | 4,029 imgs | no login | AGPL-3.0 |
| **crackseg9k** | 10 crack sets merged, 400×400 masks | 9,255 imgs | account (Harvard Dataverse) | CC |
| **sdnet2018** | Cracked/uncracked concrete, 0.06–25 mm | 56,000 imgs | account (USU) | CC |
| **aircraft-fuselage-det2023** ★ | On-domain: real fuselage defects, 4 types | 5,601 imgs | free IEEE acct | research |
| **aircraft-skin-new** | Aircraft skin: crack/dent/missing-head/paint-off/scratch | 1,115 imgs | roboflow key | open |
| **aircraft-skin-defects** | IISc skin set (crack/dent/scratch/paint-peel/missing-head) | 372 imgs | roboflow key | open |
| **corrosion-css** | Corrosion severity seg, 4 states | 440 imgs | account (VT Figshare) | open |
| **severstal** | Steel surface defects, 4 classes (corrosion/pitting transfer) | ~12k | kaggle token | comp |

### 2b · ANOMALY — flag "never-seen" damage (train-on-normal)
| Key | What | Access | License |
|---|---|---|---|
| **aebad** ★ | Aero-engine blade anomaly (AeBAD-S/-V); built-in domain shift | GitHub MMR → Drive | research |
| **mvtec-ad** | 15-category industrial anomaly benchmark | account (MVTec) | CC BY-NC-SA (**non-commercial**) |

### 2c · Fatigue growth (calibrates the Paris-law RUL for the structural module)
| Key | What | Why | Access |
|---|---|---|---|
| **virkler** ★ | Virkler (1979): 68× 2024-T3 Al specimens, 164 crack lengths each | Fit Paris `C,m` + scatter for the MC RUL band | CRAN `HMMRel::Virkler25` |
| **nasa-fatigue-lapjoint** ★ | NASA PCoE #18: Al lap-joint crack growth + Lamb-wave signals | Grounds the SHM branch | no login (zip) |

---

## Notes
- **SRM allowable limits & rupee/capacity economics stay illustrative** — OEM/operator-
  controlled, calibrate before real use. No public dataset substitutes for a controlled SRM.
- Licences vary; **MVTec AD is non-commercial**; Ultralytics `crack-seg` is AGPL-3.0. Check
  each before anything beyond a POC. **NGAFID is CC BY 4.0 — attribute it.**
- No repo here ships usable pretrained weights — every model is **trained by us** (which is
  correct: for the edge we pick, train, and quantise our own).
