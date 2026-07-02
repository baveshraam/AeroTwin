"""Validate a YOLO detect/seg dataset's label integrity before wasting a training run on it.

Checks, per split (train/val/test) declared in a data.yaml:
  - the image dir exists and is non-empty
  - every label line is well-formed: class id in range(len(names)), coords are
    floats in [0,1], and an even, >=6-value polygon (seg) or exactly 4 values (box)
  - images missing a label file (background image -- allowed, just counted)
  - orphan label files with no matching image (real problem -- always flagged)
  - per-class instance counts, so a collapsed/empty class jumps out immediately

Usage:
    python tools/validate_dataset.py datasets/crack-seg/crack-seg.yaml
    python tools/validate_dataset.py data/datasets/aircraft/data.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def _load_yaml(path: Path) -> dict:
    if yaml is not None:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    # ponytail: tiny hand-rolled fallback for `key: value` / `key:\n  0: a` yaml if
    # PyYAML isn't installed -- ultralytics depends on PyYAML so this path is rare.
    import re
    text = path.read_text(encoding="utf-8")
    out: dict = {}
    names: dict[int, str] = {}
    in_names = False
    for line in text.splitlines():
        if re.match(r"^names\s*:\s*$", line):
            in_names = True
            continue
        m = re.match(r"^\s+(\d+)\s*:\s*(.+)$", line)
        if in_names and m:
            names[int(m.group(1))] = m.group(2).strip().strip("'\"")
            continue
        in_names = False
        m = re.match(r"^(\w+)\s*:\s*(.+)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    if names:
        out["names"] = names
    return out


def _names_list(cfg: dict) -> list[str]:
    names = cfg.get("names")
    if isinstance(names, dict):
        return [names[i] for i in sorted(names)]
    return list(names or [])


def _split_dirs(data_yaml: Path, cfg: dict) -> dict[str, Path]:
    """Resolve each split dir. `path:` in a data.yaml is conventionally relative to
    Ultralytics' global datasets root, but datasets vendored straight into the repo
    (like ours) instead put the yaml AT the dataset root -- so try both and use
    whichever candidate actually exists on disk."""
    p = cfg.get("path", ".")
    candidates_root = [data_yaml.parent / p, data_yaml.parent]
    splits = {}
    for split in ("train", "val", "test"):
        rel = cfg.get(split)
        if not rel:
            continue
        for root in candidates_root:
            cand = (root / rel).resolve()
            if cand.exists():
                splits[split] = cand
                break
        else:
            splits[split] = (candidates_root[0] / rel).resolve()  # report the "expected" path
    return splits


def _label_dir_for(images_dir: Path) -> Path:
    parts = list(images_dir.parts)
    for i, p in enumerate(parts):
        if p == "images":
            parts[i] = "labels"
            return Path(*parts)
    return images_dir.parent / "labels"  # fallback: sibling 'labels' dir


def validate(data_yaml: str) -> bool:
    path = Path(data_yaml).resolve()
    if not path.exists():
        print(f"FAIL: {path} does not exist")
        return False
    cfg = _load_yaml(path)
    names = _names_list(cfg)
    if not names:
        print(f"FAIL: {path} has no 'names' — can't validate class ids")
        return False
    n_classes = len(names)

    splits = _split_dirs(path, cfg)
    if not splits:
        print(f"FAIL: {path} declares no train/val/test split")
        return False

    ok = True
    print(f"Dataset: {path}\nClasses ({n_classes}): {names}\n")
    for split, img_dir in splits.items():
        if not img_dir.exists():
            print(f"[{split}] FAIL: image dir missing -> {img_dir}")
            ok = False
            continue
        images = sorted(p for p in img_dir.iterdir()
                         if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp"))
        if not images:
            print(f"[{split}] FAIL: {img_dir} has zero images")
            ok = False
            continue
        lbl_dir = _label_dir_for(img_dir)
        label_files = {p.stem: p for p in lbl_dir.glob("*.txt")} if lbl_dir.exists() else {}
        image_stems = {p.stem for p in images}

        no_label = [s for s in image_stems if s not in label_files]
        orphans = [s for s in label_files if s not in image_stems]

        n_boxes, n_polys, empty_labels, bad_lines, class_counts = 0, 0, 0, [], [0] * n_classes
        for stem, lp in label_files.items():
            if stem not in image_stems:
                continue
            lines = [ln for ln in lp.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if not lines:
                empty_labels += 1
                continue
            for ln_no, ln in enumerate(lines, 1):
                vals = ln.split()
                try:
                    cls = int(vals[0])
                    coords = [float(v) for v in vals[1:]]
                except ValueError:
                    bad_lines.append(f"{lp.name}:{ln_no} non-numeric")
                    continue
                if not (0 <= cls < n_classes):
                    bad_lines.append(f"{lp.name}:{ln_no} class {cls} out of range(0,{n_classes})")
                    continue
                if any(not (0.0 <= v <= 1.0) for v in coords):
                    bad_lines.append(f"{lp.name}:{ln_no} coord out of [0,1]")
                    continue
                if len(coords) == 4:
                    n_boxes += 1
                elif len(coords) >= 6 and len(coords) % 2 == 0:
                    n_polys += 1
                else:
                    bad_lines.append(f"{lp.name}:{ln_no} odd/short coord count ({len(coords)})")
                    continue
                class_counts[cls] += 1

        status = "OK" if not orphans and not bad_lines else "FAIL"
        ok = ok and status == "OK"
        print(f"[{split}] {status}  images={len(images)}  labelled={len(label_files)}  "
              f"boxes={n_boxes} polygons={n_polys}  empty_label_files={empty_labels}  "
              f"images_without_label={len(no_label)} (allowed: background)")
        if orphans:
            print(f"         ORPHAN label files (no matching image, {len(orphans)}): "
                  f"{orphans[:5]}{' ...' if len(orphans) > 5 else ''}")
        if bad_lines:
            print(f"         MALFORMED lines ({len(bad_lines)}): "
                  f"{bad_lines[:5]}{' ...' if len(bad_lines) > 5 else ''}")
        print(f"         class distribution: {dict(zip(names, class_counts))}")

    print(f"\n{'PASS' if ok else 'FAIL'}: {path}")
    return ok


def _demo() -> None:
    """Self-check: a hand-built 2-image mini dataset with one bad line must FAIL correctly."""
    import tempfile
    root = Path(tempfile.mkdtemp())
    (root / "images" / "train").mkdir(parents=True)
    (root / "labels" / "train").mkdir(parents=True)
    for name in ("a", "b"):
        (root / "images" / "train" / f"{name}.jpg").write_bytes(b"\xff\xd8\xff")
    (root / "labels" / "train" / "a.txt").write_text("0 0.1 0.1 0.2 0.2 0.3 0.1\n")
    (root / "labels" / "train" / "b.txt").write_text("9 0.1 0.1 0.2 0.2\n")  # class 9 out of range
    (root / "data.yaml").write_text("path: .\ntrain: images/train\nnames:\n  0: crack\n")
    assert validate(str(root / "data.yaml")) is False, "must FAIL on out-of-range class id"
    print("validate_dataset self-check OK")


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate a YOLO dataset's label integrity")
    ap.add_argument("data_yaml", nargs="?", help="path to data.yaml")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    if args.selfcheck or not args.data_yaml:
        _demo()
        return
    sys.exit(0 if validate(args.data_yaml) else 1)


if __name__ == "__main__":
    main()
