"""L0 — Dimensional sizing.

Turns pixel measurements into real millimetres using an ArUco fiducial marker of
known physical size placed in the frame next to the defect. This is what converts a
detector output into an airworthiness-relevant number.

Print an ArUco marker (DICT_4X4_50, id 0) at a known size (default 50 mm) and put it
flat next to the panel before you photograph it.
"""
from __future__ import annotations

import cv2
import numpy as np


def mm_per_pixel(image: np.ndarray, marker_length_mm: float = 50.0) -> float | None:
    """Detect an ArUco marker and return the mm-per-pixel scale, or None if no marker.

    The scale is derived from the average side length of the detected marker in
    pixels against its known physical length in millimetres.
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    detector = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(image)
    if ids is None or len(corners) == 0:
        return None
    c = corners[0].reshape(4, 2)
    side_px = float(np.mean([np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]))
    if side_px <= 0:
        return None
    return marker_length_mm / side_px


def measure_mm(length_px: float, scale_mm_per_px: float) -> float:
    """Convert a pixel length to millimetres, rounded to 0.1 mm."""
    return round(length_px * scale_mm_per_px, 1)


def make_marker(path: str = "data/samples/aruco_id0_50mm.png", px: int = 400) -> str:
    """Utility: render a printable ArUco marker (id 0). Print it at 50 mm wide."""
    from pathlib import Path

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    img = cv2.aruco.generateImageMarker(aruco_dict, 0, px)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(path, img)
    return path


if __name__ == "__main__":
    print("Wrote printable marker to", make_marker())
