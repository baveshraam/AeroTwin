"""
AeroTwin-Edge — REAL POC core.

Detect a crack, size it in millimetres against an ArUco fiducial, and grade it
against the SRM allowable-damage-limit table. Offline. No network.

    pip install ultralytics opencv-contrib-python numpy
    python detect_and_size.py path/to/panel_with_aruco.jpg     # full pipeline
    python detect_and_size.py --selftest                       # logic check, no deps beyond cv2/numpy

The sizing/grading logic is pure and self-checked; YOLO is only imported when you
run on a real image, so --selftest works without a model or GPU.
"""
from __future__ import annotations
import argparse
import csv
import os
import sys
import numpy as np

# ponytail: marker size is the ONE real-world calibration knob. Measure your printed
# marker with calipers and set it here; everything downstream is in millimetres.
ARUCO_MARKER_MM = 50.0
ARUCO_DICT = "DICT_4X4_50"


def load_srm_limits(path: str) -> dict[str, float]:
    """defect_class -> allowable-damage limit in mm, from a configurable CSV."""
    limits = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            limits[row["defect_class"].strip().lower()] = float(row["limit_mm"])
    return limits


def grade(size_mm: float, limit_mm: float) -> tuple[str, float]:
    """Return (grade, fraction-of-limit). Beyond-limit at or over 100%."""
    frac = size_mm / limit_mm
    if frac >= 1.0:
        return "BEYOND-LIMIT", frac
    if frac >= 0.5:
        return "MAJOR", frac
    return "MINOR", frac


def mask_major_axis_px(mask: np.ndarray) -> float:
    """Longest side of the min-area rectangle around the mask (pixels)."""
    import cv2
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return 0.0
    (_, (w, h), _) = cv2.minAreaRect(max(cnts, key=cv2.contourArea))
    return float(max(w, h))


def size_defect_mm(mask: np.ndarray, px_per_mm: float) -> float:
    return mask_major_axis_px(mask) / px_per_mm


def aruco_px_per_mm(image, marker_mm: float = ARUCO_MARKER_MM):
    """Detect one ArUco marker; return px-per-mm from its known edge length."""
    import cv2
    aruco = cv2.aruco
    adict = aruco.getPredefinedDictionary(getattr(aruco, ARUCO_DICT))
    detector = aruco.ArucoDetector(adict, aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(image)
    if ids is None or len(corners) == 0:
        return None
    c = corners[0].reshape(4, 2)
    edges = [np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]
    return float(np.mean(edges)) / marker_mm


def run(image_path: str, srm_csv: str, defect_class: str = "crack") -> None:
    import cv2
    from ultralytics import YOLO
    img = cv2.imread(image_path)
    if img is None:
        sys.exit(f"cannot read {image_path}")
    scale = aruco_px_per_mm(img)
    if scale is None:
        sys.exit("no ArUco marker found — put a known-size marker in frame for sizing")

    model = YOLO("yolov8n-seg.pt")  # pretrained; swap for fine-tuned crack weights
    res = model(img, verbose=False)[0]
    if res.masks is None or len(res.masks) == 0:
        print("no defect detected")
        return

    masks = res.masks.data.cpu().numpy()
    primary = max(masks, key=lambda m: m.sum())  # largest mask = primary finding
    size_mm = size_defect_mm(primary, scale)

    limit = load_srm_limits(srm_csv).get(defect_class.lower())
    if limit is None:
        print(f"{defect_class} {size_mm:.1f} mm — no SRM limit on file, ESCALATE to engineer")
        return
    g, frac = grade(size_mm, limit)
    print(f"{defect_class} {size_mm:.1f} mm — {g} — {frac * 100:.0f}% of {limit:.0f} mm SRM limit")


def _selftest() -> None:
    # 200px-long mask at 25 px/mm = 8.0 mm; grade against a 12 mm SRM limit.
    m = np.zeros((50, 300), np.uint8)
    m[24:26, 50:250] = 1  # 200px horizontal bar
    assert abs(mask_major_axis_px(m) - 200.0) < 2.0
    assert abs(size_defect_mm(m, 25.0) - 8.0) < 0.1
    g, frac = grade(8.0, 12.0)
    assert g == "MAJOR" and round(frac, 2) == 0.67
    assert grade(13.0, 12.0)[0] == "BEYOND-LIMIT"
    assert grade(4.0, 12.0)[0] == "MINOR"
    print("selftest ok")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?")
    ap.add_argument("--srm", default=os.path.join(os.path.dirname(__file__), "srm_limits.csv"))
    ap.add_argument("--class", dest="cls", default="crack")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest or not a.image:
        _selftest()
    else:
        run(a.image, a.srm, a.cls)
