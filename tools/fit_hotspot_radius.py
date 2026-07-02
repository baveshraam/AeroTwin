"""Fit a real fuselage-radius lookup table from Airplane-body/airplane.obj, for
src/l1_twin/static/index.html's defect-hotspot placement (radiusAt/xToT).

Why this exists: the hotspot markers place a defect on the fuselage SKIN using an
idealized cylinder (constant R=0.72 + a guessed nose/tail taper curve) because the
placement math predates the real textured OBJ model. That guess is off by up to ~0.4
world units right where it matters most (nose and tail-cone taper) -- see the printed
comparison below. This script instead measures the REAL radius directly from the
model's own "11803_Airplane_body" mesh group (the fuselage only -- wings/tail/nacelles
are separate named groups in the OBJ and are deliberately excluded, since ATA 53
defects belong on the fuselage tube, not the wings).

Usage:
    python tools/fit_hotspot_radius.py
Prints a ready-to-paste FUSELAGE_X / FUSELAGE_R JS array pair and the replacement
radiusAt() body. Does NOT modify static/index.html -- paste it in by hand.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

OBJ = Path(__file__).resolve().parents[1] / "Airplane-body" / "airplane.obj"
FUSELAGE_GROUP = "11803_Airplane_body"
FL = 10.0          # must match the FL constant in index.html's loadAirframe()
N_BINS = 40


def _parse_obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (all_vertices, fuselage_vertex_indices), respecting `g` group boundaries
    (OBJ face indices are 1-indexed and cumulative across the whole file)."""
    verts: list[tuple[float, float, float]] = []
    group = None
    idx_by_group: dict[str, set[int]] = {}
    with path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("g "):
                group = line.split(maxsplit=1)[1].strip()
            elif line.startswith("f "):
                idxs = [int(tok.split("/")[0]) - 1 for tok in line.split()[1:]]
                idx_by_group.setdefault(group, set()).update(idxs)
    return np.array(verts), np.array(sorted(idx_by_group[FUSELAGE_GROUP]))


def _world_space(all_verts: np.ndarray) -> np.ndarray:
    """Replicate loadAirframe()'s exact transform: 3ds-Max Z-up -> three.js Y-up
    rotation, fit-to-FL-envelope uniform scale, then center on the origin."""
    rotated = np.column_stack([all_verts[:, 0], all_verts[:, 2], -all_verts[:, 1]])
    size = rotated.max(axis=0) - rotated.min(axis=0)
    scale = (FL * 1.05) / size.max()
    center = (rotated.max(axis=0) + rotated.min(axis=0)) / 2.0
    return (rotated - center) * scale


def fit() -> tuple[np.ndarray, np.ndarray]:
    all_verts, fuselage_idx = _parse_obj(OBJ)
    world = _world_space(all_verts)
    fx, fy, fz = world[fuselage_idx, 0], world[fuselage_idx, 1], world[fuselage_idx, 2]
    radius = np.sqrt(fy ** 2 + fz ** 2)

    edges = np.linspace(fx.min(), fx.max(), N_BINS + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    bins = np.clip(np.digitize(fx, edges) - 1, 0, N_BINS - 1)
    table = np.array([np.median(radius[bins == i]) if (bins == i).any() else np.nan
                       for i in range(N_BINS)])
    nan = np.isnan(table)
    if nan.any():
        table[nan] = np.interp(centers[nan], centers[~nan], table[~nan])
    return centers, table


def _old_radius(x: float, R: float = 0.72) -> float:
    """The formula being replaced, for the before/after comparison this prints."""
    t = (x + FL / 2) / FL
    if t >= 0.86:
        return R * (max((1 - t) / 0.14, 0)) ** 0.5
    if t <= 0.20:
        return R * max(t / 0.20, 0) ** 0.82
    return R


def main() -> None:
    x, r = fit()
    old = np.array([_old_radius(xx) for xx in x])
    diff = np.abs(old - r)
    print(f"fit {N_BINS} points over x in [{x.min():.3f}, {x.max():.3f}]")
    print(f"old-formula vs real-mesh: max diff {diff.max():.3f}, mean diff {diff.mean():.3f}"
          f"  (worst at x={x[diff.argmax()]:.2f})")
    print("\n--- paste into static/index.html, replacing FL/R/radiusAt (xToT is unchanged) ---\n")
    print("const FL=10;")
    print("const FUSELAGE_X=[" + ",".join(f"{v:.3f}" for v in x) + "];")
    print("const FUSELAGE_R=[" + ",".join(f"{v:.3f}" for v in r) + "];")
    print("""function radiusAt(t){
  const x=t*FL-FL/2;
  if(x<=FUSELAGE_X[0]) return FUSELAGE_R[0];
  if(x>=FUSELAGE_X[FUSELAGE_X.length-1]) return FUSELAGE_R[FUSELAGE_R.length-1];
  let i=0; while(FUSELAGE_X[i+1]<x) i++;
  const x0=FUSELAGE_X[i], x1=FUSELAGE_X[i+1], f=(x-x0)/(x1-x0);
  return FUSELAGE_R[i]*(1-f)+FUSELAGE_R[i+1]*f;
}""")


def _demo() -> None:
    """Self-check: the fitted fuselage radius must be positive everywhere, roughly
    constant through the midsection, and taper down near the nose/tail ends."""
    x, r = fit()
    assert (r > 0).all(), "fitted radius must be positive everywhere"
    mid = r[(x > -2) & (x < 2)]
    assert mid.std() < 0.1, f"mid-fuselage radius should be near-constant, got std={mid.std():.3f}"
    # compare the tail/nose ENDS (last few bins, not just one -- the single outermost bin
    # is a small-sample nose-cap artifact) against the mid-fuselage plateau: both ends
    # should on average taper down, not exceed it.
    assert r[:3].mean() < mid.mean() and r[-3:].mean() < mid.mean(), \
        f"both ends should taper below the mid-fuselage plateau ({mid.mean():.3f}), " \
        f"got tail={r[:3].mean():.3f} nose={r[-3:].mean():.3f}"
    print(f"fit_hotspot_radius self-check OK  |  mid-fuselage r={mid.mean():.3f}+/-{mid.std():.3f}, "
          f"tail r={r[0]:.3f}, nose r={r[-1]:.3f}")


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv:
        _demo()
    else:
        main()
