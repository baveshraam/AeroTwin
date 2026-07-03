"""Generate a synthetic aircraft-skin panel with an ArUco marker + a crack.

No camera needed. Produces an image you can run the real sizing path on:
    python ml/make_demo_panel.py
    python -m backend.pipeline --image data/samples/panel_demo.png --real   # if a model exists

The marker is 50 mm in the real world; the script prints how many px that is so you
can sanity-check the mm/px scale the pipeline computes.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

OUT = Path("data/samples/panel_demo.png")
MARKER_PX = 200          # marker drawn at 200 px
MARKER_MM = 50.0         # representing 50 mm in the real world


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h, w = 720, 1100
    # brushed-aluminium-ish background
    panel = np.full((h, w, 3), 178, np.uint8)
    panel += np.random.randint(-12, 12, (h, w, 3), dtype=np.int16).astype(np.uint8)

    # rivet rows
    for x in range(120, w - 80, 70):
        cv2.circle(panel, (x, 140), 6, (120, 120, 125), -1)
        cv2.circle(panel, (x, h - 140), 6, (120, 120, 125), -1)

    # a thin, jagged crack along a rivet line (the defect)
    pts = [(330, 300)]
    rng = np.random.default_rng(7)
    for i in range(1, 40):
        x = 330 + i * 8
        y = 300 + int(rng.integers(-6, 6))
        pts.append((x, y))
    for a, b in zip(pts, pts[1:]):
        cv2.line(panel, a, b, (40, 40, 45), 2)
    crack_len_px = pts[-1][0] - pts[0][0]

    # ArUco marker (id 0) bottom-left as the scale fiducial
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(aruco_dict, 0, MARKER_PX)
    marker = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    panel[h - MARKER_PX - 30:h - 30, 30:30 + MARKER_PX] = marker

    cv2.imwrite(str(OUT), panel)
    scale = MARKER_MM / MARKER_PX
    print(f"Wrote {OUT}")
    print(f"Marker: {MARKER_PX}px = {MARKER_MM}mm  ->  {scale:.4f} mm/px")
    print(f"Crack horizontal extent: {crack_len_px}px  ~= {crack_len_px * scale:.1f} mm")


if __name__ == "__main__":
    main()
