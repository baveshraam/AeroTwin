"""Train AeroTwin-Edge's L0 crack/corrosion detector (YOLOv8-seg), the honest way.

Two-stage transfer, because aircraft-skin labels are scarce (that's the whole problem):

  STAGE 1  base    train on the big public crack corpus (crack-seg / CrackSeg9k)
                   -> a model that already knows what a crack looks like.
  STAGE 2  adapt   fine-tune that on the small ON-DOMAIN aircraft set
                   (Aircraft_Fuselage_DET2023 / Roboflow aircraft skin) so it
                   transfers to fuselage skin, rivets, lap joints, corrosion.

Get the data first:   python ml/fetch_datasets.py --list
Then:
    python ml/train.py --stage base                       # 1) train the base
    python ml/train.py --stage adapt --data data/datasets/aircraft/data.yaml
    python ml/train.py --export                            # 3) INT8 ONNX for the Pi

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


def _configure_dirs() -> None:
    """Keep every download/run inside the repo (the default datasets_dir may be unwritable)."""
    ds = ROOT / "data" / "datasets"
    ds.mkdir(parents=True, exist_ok=True)
    try:
        from ultralytics.utils import SETTINGS
        SETTINGS.update({"datasets_dir": str(ds), "weights_dir": str(WEIGHTS_DIR),
                         "runs_dir": str(ROOT / "runs")})
    except Exception as e:  # noqa: BLE001
        print(f"! could not set ultralytics dirs ({e}); using defaults")


def train_base(epochs: int, imgsz: int, batch: int, model: str = "yolov8s-seg.pt",
               fraction: float = 1.0, device: str = None) -> None:
    """Stage 1: learn 'crack' on the big public corpus (auto-downloads).

    model: yolov8n-seg.pt is CPU/Pi-tractable; s = accuracy/edge balance; m if you have a GPU.
    fraction: train on a subset (<1.0) when CPU-bound — still a real model, honest about scope.
    """
    _configure_dirs()
    from ultralytics import YOLO
    m = YOLO(model)
    m.train(data="crack-seg.yaml", epochs=epochs, imgsz=imgsz, batch=batch,
            patience=max(5, epochs // 3), fraction=fraction, device=device,
            project="runs", name="base")
    _promote(Path(m.trainer.save_dir) / "weights" / "best.pt", BASE_WEIGHTS)


def train_adapt(data_yaml: str, epochs: int, imgsz: int, batch: int,
                model: str = "yolov8s-seg.pt", fraction: float = 1.0, device: str = None) -> None:
    """Stage 2: fine-tune the base on the small on-domain aircraft set."""
    _configure_dirs()
    from ultralytics import YOLO
    start = BASE_WEIGHTS if BASE_WEIGHTS.exists() else model
    if not BASE_WEIGHTS.exists():
        print("! no base weights yet — run `--stage base` first for the transfer benefit.")
    m = YOLO(str(start))
    m.train(data=data_yaml, epochs=epochs, imgsz=imgsz, batch=batch,
            patience=max(5, epochs // 3), lr0=0.001, fraction=fraction, device=device,
            project="runs", name="aircraft")  # low lr = gentle adapt
    best = Path(m.trainer.save_dir) / "weights" / "best.pt"
    _promote(best, DEPLOY_WEIGHTS)
    _report_pod(best, data_yaml)


def export_edge(imgsz: int = 1280, device: str = "cpu", calib_data: str = "crack-seg.yaml") -> None:
    """INT8 ONNX for the Raspberry Pi (airplane-mode edge inference). Defaults to CPU
    since the deployment target (the Pi) has no GPU -- pass device="cuda" only to
    speed up the int8 calibration pass itself on a machine that has a free GPU.

    calib_data MUST be a real crack/aircraft set, not left to ultralytics' own default:
    with no `data=`, it silently downloads generic coco8-seg (8 furniture/animal images)
    over the network for calibration -- both a hole in "fully offline" and statistically
    the wrong image distribution to calibrate a crack detector's INT8 ranges against.
    """
    if not DEPLOY_WEIGHTS.exists():
        raise SystemExit(f"No {DEPLOY_WEIGHTS} yet — train (and --deploy-base) first.")
    from ultralytics import YOLO
    YOLO(str(DEPLOY_WEIGHTS)).export(format="onnx", int8=True, imgsz=imgsz, device=device,
                                      data=calib_data)
    print("Exported INT8 ONNX next to the .pt — copy to the Pi; run with onnxruntime.")


def deploy_base() -> None:
    """Promote the public-crack base model into the slot detect.py loads, so `--real` works
    even before the (gated) on-domain aircraft fine-tune. It's a genuine crack detector —
    just trained on the public corpus, not yet adapted to fuselage skin (say so honestly)."""
    if not BASE_WEIGHTS.exists():
        raise SystemExit(f"No {BASE_WEIGHTS} yet — run `--stage base` first.")
    _promote(BASE_WEIGHTS, DEPLOY_WEIGHTS)
    print(f"{DEPLOY_WEIGHTS.name} is now the base crack detector — `python -m backend.pipeline "
          f"--image <panel.jpg> --real` will use it.")


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
    ap.add_argument("--deploy-base", action="store_true", dest="deploy_base",
                    help="promote crack-base.pt -> crack-seg.pt so --real uses the base detector")
    ap.add_argument("--export-device", default="cpu", help="device for the export/calibration pass")
    ap.add_argument("--calib-data", default="crack-seg.yaml",
                     help="real dataset for INT8 calibration (never leave this to ultralytics' "
                          "own coco8-seg default -- see export_edge docstring)")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=1280)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--model", default="yolov8s-seg.pt",
                    help="base arch: yolov8n-seg.pt (CPU/Pi), yolov8s-seg.pt (balance), yolov8m-seg.pt (GPU)")
    ap.add_argument("--fraction", type=float, default=1.0, help="fraction of the train set to use (CPU-bound runs)")
    ap.add_argument("--device", default=None, help="cpu | 0 | 0,1 (default: auto)")
    args = ap.parse_args()

    if args.deploy_base:
        deploy_base()
    elif args.export:
        export_edge(args.imgsz, args.export_device, args.calib_data)
    elif args.stage == "base":
        train_base(args.epochs, args.imgsz, args.batch, args.model, args.fraction, args.device)
    elif args.stage == "adapt":
        train_adapt(args.data, args.epochs, args.imgsz, args.batch, args.model, args.fraction, args.device)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
