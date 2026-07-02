"""Acquire real training data for AeroTwin-Edge's L0 sensor + anomaly branch.

Aerospace defect data is scarce and access-gated, so this is honest about what can
be pulled automatically vs. what needs a (free) account. Three ML branches are fed:

  DETECTOR  supervised YOLOv8-seg  — crack/corrosion masks -> mm sizing (L0 -> twin)
  ANOMALY   train-on-normal-only   — flags "never-seen" damage with zero labels
  FATIGUE   real crack-growth data — calibrate the twin's Paris-law Monte-Carlo RUL,
                                      replacing the illustrative constants (the PREDICT step)

Usage:
    python tools/fetch_datasets.py --list          # the ranked registry + how to get each
    python tools/fetch_datasets.py --all-auto       # pull everything that needs no login
    python tools/fetch_datasets.py crack-seg        # pull one by key

`auto`/`url` pulls need nothing (ultralytics or a direct public zip). Kaggle sets need
`pip install kaggle` + ~/.kaggle/kaggle.json. Roboflow sets need `pip install roboflow`
+ ROBOFLOW_API_KEY. The rest print a link + where to unzip.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "datasets"

# key -> (branch, method, target, human note). method drives how we fetch it.
#   auto     : ultralytics downloads it on demand, no account
#   kaggle   : needs kaggle CLI + token          roboflow : needs roboflow pkg + API key
#   manual   : account/consent gated -> we print the link and what to do
REGISTRY: dict[str, dict] = {
    "crack-seg": dict(
        branch="DETECTOR", method="auto", tier=1,
        note="Ultralytics crack-seg: 4,029 imgs, instance-seg masks, 1 class. "
             "AGPL-3.0. Base model, one command. `data=crack-seg.yaml`.",
    ),
    "crackseg9k": dict(
        branch="DETECTOR", method="manual", tier=1,
        url="https://doi.org/10.7910/DVN/EGIEBY",
        note="CrackSeg9k (Harvard Dataverse): ~9k pixel-mask crack imgs "
             "(Crack500/DeepCrack/CrackForest merged). Robust base. Open download.",
    ),
    "aircraft-fuselage-det2023": dict(
        branch="DETECTOR", method="manual", tier=1,
        url="https://ieee-dataport.org/documents/aircraftfuselagedet2023-aircraft-fuselage-defect-detection-dataset",
        note="ON-DOMAIN flagship: real fuselage defects, COCO/VOC/YOLO + unlabeled. "
             "Free IEEE account. Fine-tune target for aircraft adaptation.",
    ),
    "aircraft-dent-crack": dict(
        branch="DETECTOR", method="roboflow", tier=1,
        url="https://universe.roboflow.com/aircraft-detection-hpzth/aircraft-dent-crack",
        note="Roboflow: aircraft dent+crack, YOLOv8 export. Small, exact domain.",
    ),
    "aircraft-skin-defects": dict(
        branch="DETECTOR", method="roboflow", tier=1,
        url="https://universe.roboflow.com/ddiisc/aircraft_skin_defects",
        note="Roboflow (IISc): 372 imgs - crack/dent/scratch/paint-peel/missing-head.",
    ),
    "aircraft-skin-new": dict(
        branch="DETECTOR", method="roboflow", tier=1,
        url="https://universe.roboflow.com/dibya-dillip/aircraft-skin-defects-new-dataset",
        note="Roboflow (Dibya Dillip): 1,115 imgs, 5 classes - crack/dent/missing-head/"
             "paint-off/scratch. Larger on-domain object-detection set, YOLOv8 export.",
    ),
    "sdnet2018": dict(
        branch="DETECTOR", method="manual", tier=2,
        url="https://digitalcommons.usu.edu/all_datasets/48/",
        note="SDNET2018 (DOI 10.15142/T3TD19): 56,000 imgs cracked/uncracked concrete, "
             "cracks 0.06-25 mm w/ shadows+debris. Big robust classifier pre-train. CC.",
    ),
    "corrosion-css": dict(
        branch="DETECTOR", method="manual", tier=1,
        url="https://data.lib.vt.edu/articles/dataset/Corrosion_Condition_State_Semantic_Segmentation_Dataset/16624663",
        note="Corrosion Condition State seg (Virginia Tech, Figshare): 440 pixel-masked "
             "imgs, 4 severity states (good/fair/poor/severe). Adds the corrosion class.",
    ),
    "severstal": dict(
        branch="DETECTOR", method="kaggle", tier=2, kaggle="c/severstal-steel-defect-detection",
        note="Severstal steel defects: masks, 4 classes. Corrosion/pitting transfer.",
    ),
    "neu-det": dict(
        branch="DETECTOR", method="manual", tier=2,
        url="https://www.kaggle.com/datasets/kaustubhdikshit/neu-surface-defect-database",
        note="NEU-DET: steel strip, 6 classes incl. crazing/cracks. Detection boxes.",
    ),
    "aebad": dict(
        branch="ANOMALY", method="manual", tier=1,
        url="https://github.com/zhangzilongc/MMR",
        note="AeBAD aero-engine blade anomaly (MMR repo, Google-Drive link inside): "
             "train-on-normal, test breakdown/ablation/groove/fracture; AeBAD-S imgs + "
             "AeBAD-V video. THE aerospace pick for the anomaly branch.",
    ),
    "mvtec-ad": dict(
        branch="ANOMALY", method="manual", tier=2,
        url="https://www.mvtec.com/company/research/datasets/mvtec-ad",
        note="MVTec AD: 15-category anomaly benchmark. CC BY-NC-SA (NON-COMMERCIAL "
             "- POC/research only). Validates the autoencoder/PatchCore pipeline.",
    ),
    # --- FATIGUE / RUL: real growth data to CALIBRATE the twin's Paris-law Monte-Carlo,
    #     replacing the illustrative constants in src/l1_twin & src/l2_progress ---
    "virkler": dict(
        branch="FATIGUE", method="manual", tier=1,
        url="https://rdrr.io/cran/HMMRel/man/Virkler25.html",
        note="Virkler (1979): 68 x 2024-T3 Al specimens, 164 crack lengths each, a0 9->"
             "49.8 mm, dsigma 48.28 MPa, R=0.2. THE benchmark for stochastic crack growth "
             "-> calibrate Paris C,m + P10/P50/P90 bands. CRAN HMMRel::Virkler25 / GitHub.",
    ),
    "nasa-fatigue-lapjoint": dict(
        branch="FATIGUE", method="url", tier=1,
        url="https://phm-datasets.s3.amazonaws.com/NASA/18.+Fatigue+Crack+Growth+in+Aluminum+Lap+Joint.zip",
        note="NASA PCoE #18: fatigue crack growth on Al lap-joints w/ Lamb-wave signals "
             "(T1-T8). Grounds the between-inspection SHM branch (src/l1_twin/shm.py).",
    ),
    "cmapss": dict(
        branch="FATIGUE", method="url", tier=2,
        url="https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip",
        note="NASA C-MAPSS (FD001-FD004): de-facto turbofan RUL benchmark. Reference for "
             "the RUL/uncertainty methodology (not fuselage imagery).",
    ),
}


def _run(cmd: list[str]) -> bool:
    print("  $", " ".join(cmd))
    try:
        return subprocess.run(cmd, check=False).returncode == 0
    except FileNotFoundError:
        return False


def fetch(key: str) -> None:
    d = REGISTRY[key]
    dest = DATA_DIR / key
    print(f"\n[{d['branch']}] {key}  (tier {d['tier']})\n  {d['note']}")

    if d["method"] == "auto":
        try:
            from ultralytics.utils.downloads import check_det_dataset  # type: ignore
        except Exception:
            try:
                from ultralytics.data.utils import check_det_dataset  # newer layout
            except Exception:
                print("  ! `pip install ultralytics` first, then re-run.")
                return
        check_det_dataset("crack-seg.yaml", autodownload=True)
        print("  OK: ultralytics cached crack-seg (see its datasets dir + crack-seg.yaml).")
        return

    if d["method"] == "url":            # direct public download, no login
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / d["url"].split("/")[-1].replace("+", "_")
        print(f"  downloading {d['url']}")
        try:
            import urllib.request
            urllib.request.urlretrieve(d["url"], out)
            print(f"  OK -> {out}  ({out.stat().st_size // (1024*1024)} MB). Unzip in place.")
        except Exception as e:  # noqa: BLE001
            print(f"  ! download failed ({e}); grab it manually: {d['url']}")
        return

    if d["method"] == "kaggle":
        dest.mkdir(parents=True, exist_ok=True)
        ok = _run(["kaggle", "competitions", "download", "-c",
                   d["kaggle"].split("/", 1)[1], "-p", str(dest)])
        print("  OK." if ok else
              f"  ! Needs kaggle CLI + ~/.kaggle/kaggle.json. Manual: {d['url'] if 'url' in d else d['kaggle']}")
        return

    if d["method"] == "roboflow":
        api = os.environ.get("ROBOFLOW_API_KEY")
        if not api:
            print(f"  ! Set ROBOFLOW_API_KEY, or download YOLOv8 export from: {d['url']}")
            return
        print(f"  Use roboflow SDK with your workspace/project from {d['url']} "
              f"-> export format 'yolov8', unzip into {dest}")
        return

    # manual
    print(f"  -> download: {d['url']}\n     unzip into: {dest}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch AeroTwin training datasets")
    ap.add_argument("keys", nargs="*", help="dataset keys (see --list)")
    ap.add_argument("--list", action="store_true", help="show the ranked registry")
    ap.add_argument("--all-auto", action="store_true", help="fetch every no-login dataset")
    args = ap.parse_args()

    if args.list or (not args.keys and not args.all_auto):
        for k, d in sorted(REGISTRY.items(), key=lambda kv: (kv[1]["tier"], kv[1]["branch"])):
            gate = {"auto": "no login", "url": "no login", "kaggle": "kaggle token",
                    "roboflow": "roboflow key", "manual": "account/consent"}[d["method"]]
            print(f"  {k:28} [{d['branch']:8} t{d['tier']} | {gate:16}] {d['note'].splitlines()[0]}")
        print("\n  fetch:  python tools/fetch_datasets.py <key> [<key> ...]  |  --all-auto")
        return

    keys = [k for k, d in REGISTRY.items() if d["method"] in ("auto", "url")] if args.all_auto else args.keys
    for k in keys:
        if k not in REGISTRY:
            print(f"  ! unknown dataset '{k}' (see --list)"); continue
        fetch(k)


def _demo() -> None:
    """Self-check: registry is well-formed so --list/fetch can't KeyError on stage."""
    for k, d in REGISTRY.items():
        assert d["method"] in {"auto", "url", "kaggle", "roboflow", "manual"}, k
        assert d["branch"] in {"DETECTOR", "ANOMALY", "FATIGUE"} and d["tier"] in {1, 2}, k
        assert d["method"] == "auto" or ("url" in d or "kaggle" in d), f"{k} needs a link"
    print(f"fetch_datasets self-check OK  |  {len(REGISTRY)} datasets, "
          f"{sum(1 for d in REGISTRY.values() if d['method'] in ('auto', 'url'))} auto-pullable")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _demo()
    else:
        main()
