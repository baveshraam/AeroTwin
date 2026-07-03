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
AIRCRAFT_DIR = DATA_DIR / "aircraft"  # where --stage adapt expects data.yaml

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


def _configure_datasets_dir() -> None:
    """Point ultralytics' persisted datasets_dir at data/datasets (same fix as
    tools/train.py's _configure_dirs) -- otherwise `auto` downloads land wherever
    ultralytics' own settings.json last pointed (its own default, or a stale value),
    not the data/datasets/<key> layout the rest of this script assumes."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from ultralytics.utils import SETTINGS
        SETTINGS.update({"datasets_dir": str(DATA_DIR)})
    except Exception as e:  # noqa: BLE001
        print(f"  ! could not set ultralytics datasets_dir ({e}); using its default")


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
        _configure_datasets_dir()
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
        try:
            from roboflow import Roboflow
        except ImportError:
            print("  ! pip install roboflow first, then re-run.")
            return
        workspace, project_slug = d["url"].rstrip("/").split("roboflow.com/", 1)[1].split("/")[:2]
        raw = AIRCRAFT_DIR / "_raw" / key
        raw.parent.mkdir(parents=True, exist_ok=True)
        import shutil as _sh
        _sh.rmtree(raw, ignore_errors=True)  # roboflow skips extraction if the dir already exists
        try:
            project = Roboflow(api_key=api).workspace(workspace).project(project_slug)
            versions = project.versions()
            v = max((int(str(x.version).rsplit("/", 1)[-1]) for x in versions), default=1)
            project.version(v).download("yolov8", location=str(raw))
            print(f"  OK: downloaded {workspace}/{project_slug} v{v} -> {raw}")
        except Exception as e:
            print(f"  ! Roboflow download failed: {e}\n"
                  f"    Manual: {d['url']} -> export format 'yolov8' -> unzip into {raw}")
        return

    # manual
    print(f"  -> download: {d['url']}\n     unzip into: {dest}")


def _seg_line(parts: list[str]) -> str:
    """Normalize one YOLO label line to a polygon (segmentation) line so a `-seg` model
    can train on it. A box line (`cls cx cy w h`) becomes its 4 rectangular corners; a
    line that is already a polygon (cls + >=3 xy pairs) passes through unchanged. Needed
    because the on-domain Roboflow sets are mixed — some export polygons, some only boxes."""
    if len(parts) != 5:
        return " ".join(parts)  # already a polygon (or malformed — left for validate_dataset)
    cls = parts[0]
    cx, cy, w, h = map(float, parts[1:])
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    c = lambda v: f"{min(1.0, max(0.0, v)):.6f}"  # clamp into the valid [0,1] range
    return " ".join([cls, c(x0), c(y0), c(x1), c(y0), c(x1), c(y1), c(x0), c(y1)])


def merge_aircraft() -> None:
    """Unify every raw Roboflow export under data/datasets/aircraft/_raw/*/ into ONE
    YOLO-seg-style dataset at data/datasets/aircraft/ — the exact data.yaml `--stage adapt`
    expects (matches crack-seg's own path/images/labels layout, proven by validate_dataset.py).

    Roboflow's own export layout (train/valid/test top dirs, its own data.yaml) does NOT
    match that, and each source project has its OWN class list/indices, so this remaps every
    label's class id into one shared, deduped class list before copying anything in.
    """
    import shutil
    try:
        import yaml
    except ImportError:
        print("! pip install pyyaml first, then re-run.")
        return

    raw_root = AIRCRAFT_DIR / "_raw"
    sources = sorted(p for p in raw_root.glob("*") if p.is_dir()) if raw_root.exists() else []
    if not sources:
        print(f"! no raw exports under {raw_root} — run fetch on aircraft-dent-crack / "
              f"aircraft-skin-defects first (needs ROBOFLOW_API_KEY).")
        return

    # 1) union the class lists (case-insensitive dedupe), building each source's old->new map
    unified: list[str] = []
    per_source_map: dict[Path, dict[int, int]] = {}
    for src in sources:
        cfg_path = src / "data.yaml"
        if not cfg_path.exists():
            print(f"  ! skipping {src.name}: no data.yaml in the export")
            continue
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        names = cfg.get("names") or []
        if isinstance(names, dict):
            names = [names[i] for i in sorted(names)]
        idx_map = {}
        for old_i, name in enumerate(names):
            key_name = name.strip().lower()
            if key_name not in (n.lower() for n in unified):
                unified.append(name.strip())
            idx_map[old_i] = next(i for i, n in enumerate(unified) if n.lower() == key_name)
        per_source_map[src] = idx_map

    # 2) copy images + remapped labels into the unified images/{split}/labels/{split} layout,
    #    prefixing filenames by source so two projects can't collide.
    for split_dst, split_srcs in {"train": ("train",), "val": ("valid", "val"), "test": ("test",)}.items():
        img_dst = AIRCRAFT_DIR / "images" / split_dst
        lbl_dst = AIRCRAFT_DIR / "labels" / split_dst
        img_dst.mkdir(parents=True, exist_ok=True)
        lbl_dst.mkdir(parents=True, exist_ok=True)
        for src, idx_map in per_source_map.items():
            for split_src in split_srcs:
                img_src = src / split_src / "images"
                lbl_src = src / split_src / "labels"
                if not img_src.exists():
                    continue
                for img in img_src.iterdir():
                    if not img.is_file():
                        continue
                    stem = f"{src.name}__{img.stem}"
                    shutil.copy2(img, img_dst / f"{stem}{img.suffix}")
                    lbl = lbl_src / f"{img.stem}.txt"
                    out_lines = []
                    if lbl.exists():
                        for ln in lbl.read_text(encoding="utf-8").splitlines():
                            if not ln.strip():
                                continue
                            parts = ln.split()
                            parts[0] = str(idx_map.get(int(parts[0]), parts[0]))
                            out_lines.append(_seg_line(parts))
                    (lbl_dst / f"{stem}.txt").write_text(
                        "\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")

    data_yaml = AIRCRAFT_DIR / "data.yaml"
    data_yaml.write_text(
        # absolute path (posix slashes) so ultralytics resolves it the same regardless of
        # CWD / datasets_dir — a relative `path: .` was mis-resolved to the repo root.
        f"path: {AIRCRAFT_DIR.resolve().as_posix()}\n"
        "train: images/train\nval: images/val\ntest: images/test\n"
        "names:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(unified)),
        encoding="utf-8",
    )
    print(f"Merged {len(sources)} source(s) -> {AIRCRAFT_DIR}\nUnified classes: {unified}")
    print(f"Wrote {data_yaml}")

    try:
        try:
            from validate_dataset import validate  # same-dir script invocation
        except ImportError:
            from tools.validate_dataset import validate  # `python -m tools.fetch_datasets`
        print()
        validate(str(data_yaml))
    except Exception as e:
        print(f"(validation skipped: {e}; run `python tools/validate_dataset.py "
              f"{data_yaml}` by hand)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch AeroTwin training datasets")
    ap.add_argument("keys", nargs="*", help="dataset keys (see --list)")
    ap.add_argument("--list", action="store_true", help="show the ranked registry")
    ap.add_argument("--all-auto", action="store_true", help="fetch every no-login dataset")
    ap.add_argument("--merge-aircraft", action="store_true",
                     help="unify raw Roboflow exports under data/datasets/aircraft/_raw/ "
                          "into the single data.yaml --stage adapt expects, then validate it")
    args = ap.parse_args()

    if args.merge_aircraft:
        merge_aircraft()
        return

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
    """Self-check: registry is well-formed, AND merge_aircraft's class-remap logic is
    correct against two synthetic Roboflow-shaped exports with DIFFERENT class lists
    (real network access isn't needed to prove the merge logic itself)."""
    for k, d in REGISTRY.items():
        assert d["method"] in {"auto", "url", "kaggle", "roboflow", "manual"}, k
        assert d["branch"] in {"DETECTOR", "ANOMALY", "FATIGUE"} and d["tier"] in {1, 2}, k
        assert d["method"] == "auto" or ("url" in d or "kaggle" in d), f"{k} needs a link"
    print(f"fetch_datasets self-check OK  |  {len(REGISTRY)} datasets, "
          f"{sum(1 for d in REGISTRY.values() if d['method'] in ('auto', 'url'))} auto-pullable")

    import shutil
    import tempfile
    global AIRCRAFT_DIR
    orig_aircraft_dir = AIRCRAFT_DIR
    tmp = Path(tempfile.mkdtemp())
    AIRCRAFT_DIR = tmp / "aircraft"
    try:
        # source A: classes [dent, crack] — Roboflow's own train/valid/test + images/labels layout
        a = AIRCRAFT_DIR / "_raw" / "aircraft-dent-crack"
        (a / "train" / "images").mkdir(parents=True)
        (a / "train" / "labels").mkdir(parents=True)
        (a / "data.yaml").write_text("names: ['dent', 'crack']\n", encoding="utf-8")
        (a / "train" / "images" / "im1.jpg").write_bytes(b"\xff\xd8\xff")
        (a / "train" / "labels" / "im1.txt").write_text("1 0.5 0.5 0.1 0.1\n")  # class 1 = crack

        # source B: classes [crack, scratch] — note "crack" is index 0 here, DIFFERENT from A
        b = AIRCRAFT_DIR / "_raw" / "aircraft-skin-defects"
        (b / "valid" / "images").mkdir(parents=True)
        (b / "valid" / "labels").mkdir(parents=True)
        (b / "data.yaml").write_text("names: ['crack', 'scratch']\n", encoding="utf-8")
        (b / "valid" / "images" / "im2.jpg").write_bytes(b"\xff\xd8\xff")
        (b / "valid" / "labels" / "im2.txt").write_text("0 0.3 0.3 0.2 0.2\n")  # class 0 = crack here

        merge_aircraft()

        cfg = (AIRCRAFT_DIR / "data.yaml").read_text(encoding="utf-8")
        assert "dent" in cfg and "crack" in cfg and "scratch" in cfg, cfg
        # "crack" must dedupe to ONE shared index, and both sources' labels must be
        # remapped to point at that same shared index (not left at their own old index).
        unified_names = [ln.split(":", 1)[1].strip() for ln in cfg.splitlines() if ":" in ln and ln.strip()[0].isdigit()]
        crack_idx = unified_names.index("crack")
        row_a = (AIRCRAFT_DIR / "labels" / "train" / "aircraft-dent-crack__im1.txt").read_text().split()
        row_b = (AIRCRAFT_DIR / "labels" / "val" / "aircraft-skin-defects__im2.txt").read_text().split()
        lbl_a, lbl_b = row_a[0], row_b[0]
        assert int(lbl_a) == crack_idx == int(lbl_b), (lbl_a, lbl_b, crack_idx, unified_names)
        # both synthetic sources used box labels (5 fields) -> must now be 4-corner polygons (9 fields)
        assert len(row_a) == 9 and len(row_b) == 9, (row_a, row_b)
        assert (AIRCRAFT_DIR / "images" / "train" / "aircraft-dent-crack__im1.jpg").exists()
        assert (AIRCRAFT_DIR / "images" / "val" / "aircraft-skin-defects__im2.jpg").exists()
        print(f"merge_aircraft self-check OK  |  unified classes {unified_names}, "
              f"both sources' 'crack' remapped to shared index {crack_idx}, "
              f"valid/ -> val/ split rename confirmed")
    finally:
        AIRCRAFT_DIR = orig_aircraft_dir
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _demo()
    else:
        main()
