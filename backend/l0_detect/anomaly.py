"""L0b — Zero-label anomaly detection (PatchCore-style), the aerospace answer to label scarcity.

The supervised detector (``detect.py``) only finds defect types it was *trained* on. But
aircraft structures fail in ways nobody labelled — a novel corrosion morphology, an
impact bruise, a bond-line disbond. Those are exactly the expensive misses.

This branch trains on **normal skin only** (zero defect labels) and flags anything that
doesn't look like healthy structure:

  * A frozen ImageNet backbone (ResNet-18) turns each image into a grid of patch features.
  * ``fit(normal_images)`` builds a **coreset memory bank** of normal-patch features.
  * ``score(image)`` measures each test patch's distance to its nearest normal neighbour;
    the max distance is the image anomaly score, and the distance grid is a heat-map
    localising *where* the structure looks wrong.

This is the PatchCore recipe (Roth et al., 2022) — SOTA on MVTec AD, and it needs **no
defect labels and no training run**, only a bank of normal patches. Validate against
AeBAD (aero-engine blade, normal-only train / defective test) and MVTec AD.

Run the self-check (synthetic normal vs. scratched patches, no downloads needed for the
maths — backbone weights fetch once, then cached offline):

    python -m backend.l0_detect.anomaly
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

WEIGHTS_DIR = Path(__file__).resolve().parents[2] / "models" / "weights"
BANK_PATH = WEIGHTS_DIR / "anomaly_bank.npz"

_IMG = 224  # backbone input side


# --------------------------------------------------------------------------- backbone
def _load_backbone():
    """Frozen ResNet-18 feature extractor. Pretrained if reachable, else random-init
    (the pipeline still works; discrimination is just weaker — stated honestly)."""
    import torch
    from torch import nn
    import torchvision

    try:  # pretrained ImageNet weights (downloads once, then cached — offline after)
        weights = torchvision.models.ResNet18_Weights.IMAGENET1K_V1
        net = torchvision.models.resnet18(weights=weights)
        pretrained = True
    except Exception:  # offline first run / no weights
        net = torchvision.models.resnet18(weights=None)
        pretrained = False

    net.eval()
    for p in net.parameters():
        p.requires_grad_(False)

    class Extractor(nn.Module):
        """Concatenate mid-level feature maps (layer2 + layer3) into a patch grid."""

        def __init__(self, backbone):
            super().__init__()
            self.stem = nn.Sequential(backbone.conv1, backbone.bn1, backbone.relu, backbone.maxpool)
            self.layer1, self.layer2, self.layer3 = backbone.layer1, backbone.layer2, backbone.layer3

        @torch.no_grad()
        def forward(self, x):
            x = self.stem(x)
            x = self.layer1(x)
            f2 = self.layer2(x)                        # (B,128,28,28)
            f3 = self.layer3(f2)                       # (B,256,14,14)
            f3 = nn.functional.interpolate(f3, size=f2.shape[-2:], mode="bilinear", align_corners=False)
            feat = torch.cat([f2, f3], dim=1)          # (B,384,28,28)
            feat = nn.functional.avg_pool2d(feat, 3, 1, 1)  # local neighbourhood aggregation
            return feat

    return Extractor(net).eval(), pretrained


# --------------------------------------------------------------------------- helpers
def _to_tensor(img):
    """Accept an HxWx3 uint8/float array or a path; return a normalised (1,3,224,224) tensor."""
    import torch

    if isinstance(img, (str, Path)):
        from PIL import Image

        arr = np.asarray(Image.open(img).convert("RGB").resize((_IMG, _IMG)), dtype=np.float32) / 255.0
    else:
        arr = np.asarray(img, dtype=np.float32)
        if arr.max() > 1.5:
            arr = arr / 255.0
        if arr.ndim == 2:
            arr = np.repeat(arr[..., None], 3, axis=2)
        if arr.shape[:2] != (_IMG, _IMG):
            from PIL import Image

            arr = np.asarray(Image.fromarray((arr * 255).astype(np.uint8)).resize((_IMG, _IMG)),
                             dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    return torch.from_numpy(arr.transpose(2, 0, 1)[None])


def _coreset(feats: np.ndarray, n: int, seed: int = 0, block: int = 2048) -> np.ndarray:
    """Greedy k-center coreset — a spread-out subset of the normal bank (PatchCore §3.2).

    Falls back to the full set when already small. Distances are computed in blocks so the
    peak allocation stays tiny (Pi-friendly) instead of materialising the whole N×C array."""
    if len(feats) <= n:
        return feats
    rng = np.random.default_rng(seed)
    min_d = np.full(len(feats), np.inf, dtype=np.float32)

    def update(center):
        for i in range(0, len(feats), block):
            blk = feats[i:i + block]
            dd = np.sqrt(((blk - center) ** 2).sum(axis=1))
            np.minimum(min_d[i:i + block], dd, out=min_d[i:i + block])

    idx = [int(rng.integers(len(feats)))]
    update(feats[idx[0]])
    for _ in range(n - 1):
        j = int(np.argmax(min_d))
        idx.append(j)
        update(feats[j])
    return feats[np.array(idx)]


# --------------------------------------------------------------------------- detector
class PatchCore:
    """Train-on-normal-only anomaly detector. Zero defect labels required."""

    def __init__(self, coreset_size: int = 4096):
        self.coreset_size = coreset_size
        self.bank: np.ndarray | None = None
        self.threshold: float = 0.0
        self._grid = 28  # feature-map side for the 224px input
        self._extractor = None

    def _extract(self, img) -> np.ndarray:
        """Return (grid*grid, C) patch features for one image."""
        if self._extractor is None:
            self._extractor, self._pretrained = _load_backbone()
        feat = self._extractor(_to_tensor(img))[0].numpy()   # (C,H,W)
        c, h, w = feat.shape
        self._grid = h
        return feat.reshape(c, h * w).T                       # (H*W, C)

    def fit(self, normal_images: list, val_frac: float = 0.2) -> "PatchCore":
        """Build the memory bank from normal-only images, then calibrate the threshold on a
        HELD-OUT normal split (images not in the bank) — scoring in-bank images gives ~0 and
        would set the threshold far too low, flagging every real normal as anomalous."""
        n = len(normal_images)
        n_val = max(1, int(round(n * val_frac))) if n >= 4 else 0
        bank_imgs = normal_images[n_val:] if n_val else normal_images
        val_imgs = normal_images[:n_val] if n_val else normal_images

        bank = np.concatenate([self._extract(im) for im in bank_imgs], axis=0).astype(np.float32)
        self.bank = _coreset(bank, self.coreset_size)

        val_scores = np.array([self.score(im)["score"] for im in val_imgs])
        # threshold above the worst held-out normal (a small margin), so genuine normals pass
        self.threshold = float(val_scores.max() * 1.1 if n_val
                               else val_scores.mean() + 3.0 * (val_scores.std() + 1e-6))
        return self

    def _knn_dist(self, patches: np.ndarray) -> np.ndarray:
        """Min L2 distance from each test patch to the normal bank (chunked for memory)."""
        out = np.empty(len(patches), dtype=np.float32)
        for i in range(0, len(patches), 256):
            chunk = patches[i:i + 256]
            d = np.linalg.norm(chunk[:, None, :] - self.bank[None, :, :], axis=2)
            out[i:i + 256] = d.min(axis=1)
        return out

    def score(self, img) -> dict:
        """Anomaly score + localisation heat-map for one image.

        Returns ``{score, is_anomaly, heatmap(28x28, 0..1), pretrained}``.
        Higher score = further from anything seen in healthy structure."""
        if self.bank is None:
            raise RuntimeError("fit() the detector on normal images first (or load a bank).")
        patches = self._extract(img)
        dists = self._knn_dist(patches)
        g = self._grid
        heat = dists.reshape(g, g)
        score = float(dists.max())
        norm = (heat - heat.min()) / (np.ptp(heat) + 1e-9)
        return {"score": score, "is_anomaly": bool(score > self.threshold),
                "heatmap": norm, "pretrained": getattr(self, "_pretrained", None)}

    # ---- persistence (bank ships as a small .npz, no imagery leaves the hangar) ----
    def save(self, path: Path = BANK_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, bank=self.bank, threshold=self.threshold, grid=self._grid)

    @classmethod
    def load(cls, path: Path = BANK_PATH) -> "PatchCore":
        d = np.load(path)
        pc = cls()
        pc.bank, pc.threshold, pc._grid = d["bank"], float(d["threshold"]), int(d["grid"])
        return pc


def train_from_folder(normal_dir: str, coreset_size: int = 4096) -> PatchCore:
    """Fit on every image in a folder of NORMAL structure (e.g. AeBAD/MVTec 'good' set)."""
    exts = {".png", ".jpg", ".jpeg", ".bmp"}
    files = [p for p in Path(normal_dir).rglob("*") if p.suffix.lower() in exts]
    if not files:
        raise SystemExit(f"No images under {normal_dir}")
    print(f"fitting PatchCore on {len(files)} normal images from {normal_dir} …")
    pc = PatchCore(coreset_size).fit([str(f) for f in files])
    pc.save()
    print(f"bank: {pc.bank.shape} · threshold {pc.threshold:.3f} -> {BANK_PATH}")
    return pc


# --------------------------------------------------------------------------- self-check
def _synthetic_patch(anomalous: bool, seed: int) -> np.ndarray:
    """A smoothly-textured 'normal skin' tile; if anomalous, paint a bright scratch."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0.5, 0.02, (_IMG, _IMG, 3)).astype(np.float32)
    # low-frequency shading so 'normal' has structure, not just noise
    yy, xx = np.mgrid[0:_IMG, 0:_IMG] / _IMG
    base += (0.06 * np.sin(6 * xx + seed) * np.cos(5 * yy))[..., None]
    if anomalous:
        r = rng.integers(40, 180)
        thick = rng.integers(2, 5)
        base[r:r + thick, 30:190] += np.array([0.5, 0.2, 0.2], dtype=np.float32)  # rust-coloured gash
    return np.clip(base, 0, 1)


def _demo() -> None:
    print("PatchCore anomaly branch — train-on-normal-only self-check\n")
    normal = [_synthetic_patch(False, s) for s in range(12)]
    pc = PatchCore(coreset_size=2000).fit(normal)
    print(f"backbone pretrained : {getattr(pc, '_pretrained', '?')}")
    print(f"memory bank         : {pc.bank.shape[0]} patches x {pc.bank.shape[1]} dims")
    print(f"threshold           : {pc.threshold:.3f}\n")

    clean = [pc.score(_synthetic_patch(False, 100 + s))["score"] for s in range(5)]
    dmg = [pc.score(_synthetic_patch(True, 200 + s))["score"] for s in range(5)]
    print(f"normal test scores  : {np.round(clean, 3)}  (mean {np.mean(clean):.3f})")
    print(f"damaged test scores : {np.round(dmg, 3)}  (mean {np.mean(dmg):.3f})")

    flagged = sum(pc.score(_synthetic_patch(True, 300 + s))["is_anomaly"] for s in range(5))
    missed = sum(pc.score(_synthetic_patch(False, 400 + s))["is_anomaly"] for s in range(5))
    sep = np.mean(dmg) > np.mean(clean)
    print(f"\ndamage flagged      : {flagged}/5   false alarms: {missed}/5")
    print(f"separation (dmg>norm): {'OK' if sep else 'WEAK (random backbone / needs pretrained weights)'}")
    print("\nReport POD (probability of detection) + false-alarm rate, not a single number -")
    print("a missed crack is the expensive error in aerospace.")


if __name__ == "__main__":
    _demo()
