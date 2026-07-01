"""Train AeroTwin-Edge's L0 crack/corrosion detector (YOLOv8-seg), the honest way.

Two-stage transfer, because aircraft-skin labels are scarce (that's the whole problem):

  STAGE 1  base    train on the big public crack corpus (crack-seg / CrackSeg9k)
                   -> a model that already knows what a crack looks like.
  STAGE 2  adapt   fine-tune that on the small ON-DOMAIN aircraft set
                   (Aircraft_Fuselage_DET2023 / Roboflow aircraft skin) so it
                   transfers to fuselage skin, rivets, lap joints, corrosion.

Get the data first:   python tools/fetch_datasets.py --list
Then:
    python tools/train.py --stage base                       # 1) train the base
    python tools/train.py --stage adapt --data data/datasets/aircraft/data.yaml
    python tools/train.py --export                            # 3) INT8 ONNX for the Pi

Cracks are thin and tiny: high imgsz (1280) + SAHI tiling at inference so a small
crack isn't lost in a downscaled frame. We report POD (probability of detection) and
recall bias, NOT just mAP — a missed crack is the expensive error in aerospace.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEIGHTS_DIR = ROOT / "models" / "weights"
BASE_WEIGHTS = WEIGHTS_DIR / "crack-base.pt"
DEPLOY_WEIGHTS = WEIGHTS_DIR / "crack-seg.pt"  # what src/l0_detect/detect.py loads


def train_base(epochs: int, imgsz: int, batch: int) -> None:
    """Stage 1: learn 'crack' on the big public corpus (auto-downloads)."""
    from ultralytics import YOLO
    model = YOLO("yolov8s-seg.pt")  # s = accuracy/edge balance; n for the Pi, m if you have GPU
    model.train(data="crack-seg.yaml", epochs=epochs, imgsz=imgsz, batch=batch,
                patience=20, project="runs", name="base")
    _promote(ROOT / "runs" / "base" / "weights" / "best.pt", BASE_WEIGHTS)


def train_adapt(data_yaml: str, epochs: int, imgsz: int, batch: int) -> None:
    """Stage 2: fine-tune the base on the small on-domain aircraft set."""
    from ultralytics import YOLO
    start = BASE_WEIGHTS if BASE_WEIGHTS.exists() else "yolov8s-seg.pt"
    if start == "yolov8s-seg.pt":
        print("! no base weights yet — run `--stage base` first for the transfer benefit.")
    model = YOLO(str(start))
    model.train(data=data_yaml, epochs=epochs, imgsz=imgsz, batch=batch,
                patience=15, lr0=0.001, project="runs", name="aircraft")  # low lr = gentle adapt
    best = ROOT / "runs" / "aircraft" / "weights" / "best.pt"
    _promote(best, DEPLOY_WEIGHTS)
    _report_pod(best, data_yaml)


def export_edge() -> None:
    """INT8 ONNX for the Raspberry Pi (airplane-mode edge inference)."""
    if not DEPLOY_WEIGHTS.exists():
        raise SystemExit(f"No {DEPLOY_WEIGHTS} yet — train first.")
    from ultralytics import YOLO
    YOLO(str(DEPLOY_WEIGHTS)).export(format="onnx", int8=True, imgsz=1280)
    print("Exported INT8 ONNX next to the .pt — copy to the Pi; run with onnxruntime.")


def _report_pod(weights: Path, data_yaml: str) -> None:
    """POD/recall, not just mAP — the aerospace-honest metric (a miss is the costly error)."""
    if not weights.exists():
        return
    from ultralytics import YOLO
    m = YOLO(str(weights)).val(data=data_yaml, split="val")
    r = float(getattr(m.seg, "mr", getattr(m.box, "mr", 0.0)))  # mean recall ~ POD proxy
    print(f"\nPOD (mean recall, mask): {r:.3f}   [misses = 1-POD = {1-r:.3f}]")
    print("Report this + the recall/confidence curve, not mAP alone. State CPU vs Hailo FPS.")


def _promote(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        print(f"Promoted {src.name} -> {dst}")
    else:
        print(f"! expected {src} — training may have failed; check runs/.")


def main() -> None:
    ap = argparse.ArgumentParser(description="AeroTwin L0 detector training")
    ap.add_argument("--stage", choices=["base", "adapt"], help="base corpus, or on-domain fine-tune")
    ap.add_argument("--data", default="data/datasets/aircraft/data.yaml", help="YOLO data.yaml for --stage adapt")
    ap.add_argument("--export", action="store_true", help="INT8 ONNX for the Pi")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    if args.export:
        export_edge()
    elif args.stage == "base":
        train_base(args.epochs, args.imgsz, args.batch)
    elif args.stage == "adapt":
        train_adapt(args.data, args.epochs, args.imgsz, args.batch)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
