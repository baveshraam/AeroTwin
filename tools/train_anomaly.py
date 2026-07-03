"""Anomaly branch — PatchCore, train-on-normal-only defect detection (no labels needed).

PICK: PatchCore over an autoencoder, given the time constraint. PatchCore needs ZERO
backprop/training loop -- it forward-passes normal images once through a FROZEN,
ImageNet-pretrained CNN, stores the resulting patch features as a "memory bank", and
scores a new image by its distance to the nearest stored patch. That means: no GPU
contention with the crack-seg calibration run, no epoch/loss-curve babysitting, and
(per the PatchCore paper) it beats autoencoder reconstruction-error baselines on MVTec
AD out of the box. An autoencoder would need its own training loop (more wall-clock,
more hyperparameters) for a POC that likely still underperforms this.

Dataset: MVTec AD "bottle" category (CC BY-NC-SA -- NON-COMMERCIAL, validates the
pipeline only; see [[datasets-and-training]]). 209 train/good images, 83 test images
across good + 3 defect types, plus ground_truth masks. Swap in AeBAD (the aerospace
pick) the same way once it's in hand -- only DATA_ROOT changes.

Method (matches the PatchCore paper, with two ponytail simplifications noted below):
  1. Extract patch features from a frozen ResNet18's layer2 + layer3 (ImageNet
     weights), locally average-pooled (3x3) and upsampled/concatenated to one grid.
  2. Store every train/good patch vector as the "memory bank".
  3. ponytail: coreset subsampling is RANDOM, not the paper's greedy minimax-facility
     -location selection -- fine at 209 images (~164k patches); switch to greedy
     coreset if the corpus grows into the thousands and random starts missing rare
     normal patterns.
  4. Score a test image by the max (over its patches) 1-NN distance into the bank;
     ponytail: 1-NN via sklearn brute force, not the paper's re-weighted k-NN -- swap
     in faiss + the reweighting if bank size or latency ever matters.

Usage:
    python tools/train_anomaly.py --data data/datasets/mvtec-ad/bottle          # build + evaluate
    python tools/train_anomaly.py --data data/datasets/mvtec-ad/bottle --bank models/weights/anomaly-bottle.npz --skip-build
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEVICE = "cpu"  # ponytail: hardcoded -- GPU is busy with the crack-seg calibration run;
                # flip to "cuda" once that finishes and re-benchmark the timing claims below.
IMG_SIZE = 224
LAYERS = ("layer2", "layer3")


def _backbone():
    """Frozen ImageNet ResNet18, eval mode, CPU. One-time weight download (~44MB) --
    tooling/setup, not a pipeline runtime network call (see [[offline audit]])."""
    import torch
    import torchvision

    weights = torchvision.models.ResNet18_Weights.IMAGENET1K_V1
    model = torchvision.models.resnet18(weights=weights)
    model.eval().to(DEVICE)
    for p in model.parameters():
        p.requires_grad_(False)

    feats: dict[str, "torch.Tensor"] = {}

    def hook(name):
        def _fn(_module, _inp, out):
            feats[name] = out
        return _fn

    for name in LAYERS:
        getattr(model, name).register_forward_hook(hook(name))
    return model, feats, weights.transforms()


def _patch_features(model, feats, tfm, image_paths: list[Path]) -> np.ndarray:
    """Run a batch of images through the backbone; return [n_images, n_patches, dim]
    local-pooled, multi-layer patch features on a common (grid_h, grid_w) grid."""
    import torch
    import torch.nn.functional as F
    from PIL import Image

    batch = torch.stack([tfm(Image.open(p).convert("RGB")) for p in image_paths]).to(DEVICE)
    with torch.no_grad():
        model(batch)
    grid_h, grid_w = feats[LAYERS[0]].shape[-2:]  # layer2 is the larger grid; align to it
    pooled = []
    for name in LAYERS:
        f = F.avg_pool2d(feats[name], kernel_size=3, stride=1, padding=1)
        if f.shape[-2:] != (grid_h, grid_w):
            f = F.interpolate(f, size=(grid_h, grid_w), mode="nearest")
        pooled.append(f)
    merged = torch.cat(pooled, dim=1)  # [B, C1+C2, grid_h, grid_w]
    b, c, h, w = merged.shape
    return merged.permute(0, 2, 3, 1).reshape(b, h * w, c).cpu().numpy(), (h, w)


def build_memory_bank(data_dir: Path, coreset_size: int = 10_000, batch_size: int = 8,
                       seed: int = 0) -> dict:
    train_dir = data_dir / "train" / "good"
    images = sorted(train_dir.glob("*.png")) or sorted(train_dir.glob("*.*"))
    if not images:
        raise SystemExit(f"no train/good images under {train_dir}")

    model, feats, tfm = _backbone()
    t0 = time.time()
    all_vecs, grid = [], None
    for i in range(0, len(images), batch_size):
        vecs, grid = _patch_features(model, feats, tfm, images[i:i + batch_size])
        all_vecs.append(vecs.reshape(-1, vecs.shape[-1]))
    bank = np.concatenate(all_vecs, axis=0).astype(np.float32)
    elapsed = time.time() - t0

    rng = np.random.default_rng(seed)
    if bank.shape[0] > coreset_size:
        idx = rng.choice(bank.shape[0], size=coreset_size, replace=False)
        bank = bank[idx]

    print(f"  extracted {sum(len(v) for v in all_vecs):,} patches from {len(images)} "
          f"train/good images in {elapsed:.1f}s ({elapsed / len(images):.3f}s/img, CPU) "
          f"-> memory bank {bank.shape[0]:,} x {bank.shape[1]}")
    return {"bank": bank, "grid": grid, "n_train_images": len(images), "build_seconds": elapsed}


def _score_images(model, feats, tfm, bank: np.ndarray, grid: tuple[int, int],
                   image_paths: list[Path]) -> tuple[np.ndarray, np.ndarray]:
    """Return (image_scores, anomaly_maps[n, h, w]) -- max-patch-distance to the bank."""
    from sklearn.neighbors import NearestNeighbors

    nn = NearestNeighbors(n_neighbors=1, algorithm="auto").fit(bank)
    h, w = grid
    scores, maps = [], []
    for p in image_paths:
        vecs, _ = _patch_features(model, feats, tfm, [p])
        dist, _ = nn.kneighbors(vecs[0])
        dist = dist[:, 0]
        scores.append(float(dist.max()))
        maps.append(dist.reshape(h, w))
    return np.array(scores), np.array(maps)


def evaluate(data_dir: Path, mem: dict) -> dict:
    from sklearn.metrics import roc_auc_score

    model, feats, tfm = _backbone()
    bank, grid = mem["bank"], mem["grid"]

    scores_by_class, all_scores, all_labels = {}, [], []
    t0 = time.time()
    n_images = 0
    for cls_dir in sorted((data_dir / "test").iterdir()):
        images = sorted(cls_dir.glob("*.png")) or sorted(cls_dir.glob("*.*"))
        if not images:
            continue
        scores, _maps = _score_images(model, feats, tfm, bank, grid, images)
        is_anomaly = 0 if cls_dir.name == "good" else 1
        scores_by_class[cls_dir.name] = scores
        all_scores.extend(scores.tolist())
        all_labels.extend([is_anomaly] * len(scores))
        n_images += len(images)
    elapsed = time.time() - t0

    auroc = roc_auc_score(all_labels, all_scores)
    print(f"\n  scored {n_images} test images in {elapsed:.1f}s "
          f"({elapsed / n_images:.3f}s/img, CPU)")
    print(f"  image-level AUROC: {auroc:.3f}   (1.0 = perfect separation, 0.5 = chance)")
    for name, s in scores_by_class.items():
        print(f"    {name:16} n={len(s):3}  score mean={s.mean():.2f}  "
              f"min={s.min():.2f}  max={s.max():.2f}")
    return {"auroc": auroc, "scores_by_class": scores_by_class, "eval_seconds": elapsed,
            "seconds_per_image": elapsed / n_images}


def _demo() -> None:
    """Self-check: on synthetic 'normal' (solid squares) vs. a genuinely different
    'anomaly' (a different shape/texture), PatchCore must score the anomaly higher
    than every normal image -- the core train-on-normal-only promise, no MVTec needed."""
    import shutil
    import tempfile

    import numpy as np
    from PIL import Image, ImageDraw

    root = Path(tempfile.mkdtemp())
    train = root / "train" / "good"
    train.mkdir(parents=True)
    rng = np.random.default_rng(0)
    for i in range(12):
        img = Image.new("RGB", (128, 128), "white")
        d = ImageDraw.Draw(img)
        jx, jy = rng.integers(-4, 4, 2)
        d.rectangle([40 + jx, 40 + jy, 88 + jx, 88 + jy], fill=(200, 30, 30))
        img.save(train / f"{i}.png")

    test_good = root / "test" / "good"
    test_bad = root / "test" / "anomaly"
    test_good.mkdir(parents=True)
    test_bad.mkdir(parents=True)
    for i in range(3):
        img = Image.new("RGB", (128, 128), "white")
        ImageDraw.Draw(img).rectangle([42, 42, 86, 86], fill=(200, 30, 30))
        img.save(test_good / f"{i}.png")
    for i in range(3):
        img = Image.new("RGB", (128, 128), "white")
        ImageDraw.Draw(img).ellipse([20, 20, 108, 108], fill=(30, 30, 200))  # different shape+color
        img.save(test_bad / f"{i}.png")

    try:
        mem = build_memory_bank(root, coreset_size=5000, batch_size=4)
        res = evaluate(root, mem)
        assert res["scores_by_class"]["anomaly"].min() > res["scores_by_class"]["good"].max(), (
            res["scores_by_class"])
        assert res["auroc"] == 1.0, res["auroc"]
        print(f"train_anomaly self-check OK  |  synthetic anomaly fully separated, "
              f"AUROC={res['auroc']}")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="PatchCore anomaly baseline (train-on-normal-only)")
    ap.add_argument("--data", default=str(ROOT / "data" / "datasets" / "mvtec-ad" / "bottle"),
                     help="category dir with train/good and test/<class>")
    ap.add_argument("--bank", default=None, help="path to save/load the memory bank .npz")
    ap.add_argument("--coreset-size", type=int, default=10_000)
    ap.add_argument("--skip-build", action="store_true", help="load an existing --bank instead")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()

    if args.selfcheck:
        _demo()
        return

    data_dir = Path(args.data)
    bank_path = Path(args.bank) if args.bank else (
        ROOT / "models" / "weights" / f"anomaly-{data_dir.name}.npz")

    if args.skip_build and bank_path.exists():
        npz = np.load(bank_path, allow_pickle=True)
        mem = {"bank": npz["bank"], "grid": tuple(npz["grid"])}
        print(f"Loaded memory bank {mem['bank'].shape} from {bank_path}")
    else:
        print(f"Building memory bank from {data_dir} ...")
        mem = build_memory_bank(data_dir, coreset_size=args.coreset_size)
        bank_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(bank_path, bank=mem["bank"], grid=np.array(mem["grid"]))
        print(f"  saved -> {bank_path}")

    print(f"\nEvaluating on {data_dir / 'test'} ...")
    evaluate(data_dir, mem)


if __name__ == "__main__":
    main()
