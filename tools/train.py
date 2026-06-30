"""Train the L0 crack detector/segmenter (YOLOv8-seg).

This is the real-model path. Steps:

1. Get data. Start with public sets and transfer to aircraft skin:
   - SDNET2018 (concrete/metal cracks), NEU-DET (metal surface defects), GAPs.
   - Label a small aircraft-skin set yourself (Roboflow / LabelImg / CVAT) in YOLO
     segmentation format. Even 100-300 labelled crops moves the needle with a
     pretrained backbone.
2. Put a data.yaml in data/dataset/ pointing at train/val images + labels.
3. Run:  python tools/train.py
4. The best weights land in runs/.. ; copy them to models/weights/crack-seg.pt
5. Quantize/export for the Pi:  yolo export model=models/weights/crack-seg.pt format=onnx int8=True

Cracks are thin and tiny — for accuracy use high-resolution input (imgsz=1280) and,
for inference, SAHI tiling so small cracks aren't lost in a downscaled image.
"""
from __future__ import annotations

from pathlib import Path

DATA_YAML = Path("data/dataset/data.yaml")


def main() -> None:
    if not DATA_YAML.exists():
        raise SystemExit(
            f"Missing {DATA_YAML}. Create a YOLO dataset first (see this file's docstring)."
        )
    from ultralytics import YOLO

    model = YOLO("yolov8n-seg.pt")  # nano = edge-friendly; try yolov8s-seg for accuracy
    model.train(
        data=str(DATA_YAML),
        epochs=100,
        imgsz=1280,          # high-res: cracks are small
        batch=8,
        patience=20,
        project="runs",
        name="crack-seg",
    )
    print("Done. Copy runs/crack-seg/weights/best.pt -> models/weights/crack-seg.pt")


if __name__ == "__main__":
    main()
