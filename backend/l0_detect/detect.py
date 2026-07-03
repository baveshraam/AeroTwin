"""L0 — Defect detection + segmentation.

Returns a list of detections with a pixel length for each defect mask. Two modes:

* mock=True (default until you train a model): returns a synthetic detection so the
  whole L0 -> L3 chain runs today. Great for wiring up the twin/agent/dashboard.
* real: loads a trained YOLOv8-seg model from ml/models/crack-seg.pt and runs
  segmentation. Cracks are thin and tiny, so for the real build use high-resolution
  tiling (SAHI) and an anchor-free small-object detector — see ml/train.py.

The 'length' of a crack mask is estimated from the polygon's bounding diagonal as a
simple, honest proxy. Upgrade to skeleton/medial-axis length for accuracy later.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

WEIGHTS = Path(__file__).resolve().parents[2] / "ml" / "models" / "crack-seg.pt"


def detect_defects(image_path: str | None = None, mock: bool = False) -> list[dict]:
    """Detect defects in an image. Each item: {defect_type, mask_length_px, confidence,
    model_version}. model_version is the source of truth for what actually ran — callers
    must not infer it from the `mock` argument, since `--real` silently falls back to the
    mock detection whenever no weights are on disk or no image was given:
      * "yolov8-seg" — a real trained model actually ran inference
      * "mock-v0"    — the intentional demo mock (mock=True, the default before training)
      * "mock-fixed" — `--real` was asked but we fell back (no weights/image) — same fixed
                       mock output, but flagged distinctly so a silent fallback shows up in
                       logs/audit instead of hiding as a plain demo mock (and never a false
                       "yolov8-seg" claim)."""
    if mock or not WEIGHTS.exists() or image_path is None:
        # Synthetic detection so the chain is runnable before a model exists.
        return [{"defect_type": "crack", "mask_length_px": 320.0, "confidence": 0.81,
                 "model_version": "mock-v0" if mock else "mock-fixed"}]

    from ultralytics import YOLO  # imported lazily so mock mode needs no heavy deps

    model = YOLO(str(WEIGHTS))
    result = model(image_path, verbose=False)[0]
    detections: list[dict] = []
    if result.masks is not None:
        for box, polygon in zip(result.boxes, result.masks.xy):
            detections.append(
                {
                    "defect_type": result.names[int(box.cls)],
                    "mask_length_px": _polyline_length(polygon),
                    "confidence": float(box.conf),
                    "model_version": "yolov8-seg",
                }
            )
    return detections


def _polyline_length(points) -> float:
    """Bounding-diagonal length of a mask polygon, in pixels."""
    pts = np.asarray(points, dtype=float)
    if len(pts) < 2:
        return 0.0
    return float(np.linalg.norm(pts.max(axis=0) - pts.min(axis=0)))
