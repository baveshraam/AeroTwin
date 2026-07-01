"""L2 — Defect progression -> predictive scheduling.

This is the cost -> predictive value jump: given how big a crack is now, predict the
flight cycle at which it will cross its SRM limit, so maintenance can be pulled
forward for THIS defect instead of waiting for a calendar interval.

Two estimators:

1. empirical_cycles_to_limit — when you have two real scans of the same defect, use
   the measured growth rate. Honest and simple; best when data exists.
2. paris_cycles_to_limit — Paris' law fatigue crack-growth model for a single scan:
       da/dN = C * (dK)^m,   dK = delta_sigma * Y * sqrt(pi * a)
   Integrated numerically. C, m, delta_sigma, Y are material/loading constants and
   are ILLUSTRATIVE here — calibrate them per structure before quoting a slide.
"""
from __future__ import annotations

import math


def paris_cycles_to_limit(
    a_current_mm: float,
    a_limit_mm: float,
    *,
    C: float = 1.0e-11,
    m: float = 3.0,
    delta_sigma: float = 100.0,  # MPa, illustrative cyclic stress range
    Y: float = 1.12,             # geometry factor (edge crack ~1.12)
    steps: int = 2000,
) -> int | None:
    """Cycles for a crack to grow from a_current to a_limit under Paris' law.

    Returns 0 if already at/over the limit, or None on degenerate input.
    """
    a = a_current_mm / 1000.0      # mm -> m
    a_lim = a_limit_mm / 1000.0
    if a_lim <= 0:
        return None
    if a >= a_lim:
        return 0
    da = (a_lim - a) / steps
    cycles = 0.0
    for _ in range(steps):
        dK = delta_sigma * Y * math.sqrt(math.pi * a)
        dadn = C * (dK ** m)
        if dadn <= 0:
            return None
        cycles += da / dadn
        a += da
    return int(round(cycles))


def empirical_cycles_to_limit(
    prev_mm: float,
    curr_mm: float,
    cycles_between: int,
    a_limit_mm: float,
) -> int | None:
    """Linear growth-rate extrapolation from two real scans.

    rate = (curr - prev) / cycles_between  [mm per cycle]
    Returns cycles until curr reaches a_limit, 0 if already past, None if no growth.
    """
    if cycles_between <= 0 or curr_mm <= prev_mm:
        return None
    rate = (curr_mm - prev_mm) / cycles_between
    remaining = a_limit_mm - curr_mm
    if remaining <= 0:
        return 0
    return int(round(remaining / rate))


def paris_rul_mc(
    a_current_mm: float,
    a_limit_mm: float,
    *,
    C: float = 1.0e-11,
    m: float = 3.0,
    delta_sigma: float = 100.0,
    Y: float = 1.12,
    n: int = 400,
    steps: int = 400,
    c_sigma_dex: float = 0.3,   # C scatters ~0.3 decades (lognormal) — it spans orders of magnitude
    m_sigma: float = 0.15,      # m scatters ~0.15 (normal)
    seed: int | None = 7,
) -> dict | None:
    """Monte-Carlo RUL: propagate Paris-constant uncertainty into a DISTRIBUTION of
    cycles-to-limit, so the twin reports P50 with a P10-P90 band, not false precision.

    The material constants C (crack-growth coefficient) and m (exponent) carry real
    scatter; a single deterministic RUL hides that. We sample them (C lognormal because
    it spans decades, m normal), integrate Paris' law for every sample, and return
    percentiles. The conservative scheduling figure is P10 (only a 10% chance the defect
    reaches its limit sooner). Spreads are ILLUSTRATIVE — calibrate per structure.
    """
    import numpy as np
    a = a_current_mm / 1000.0
    a_lim = a_limit_mm / 1000.0
    if a_lim <= 0:
        return None
    if a >= a_lim:
        return {"p10": 0, "p50": 0, "p90": 0, "mean": 0, "n": n}

    rng = np.random.default_rng(seed)
    Cs = C * 10.0 ** rng.normal(0.0, c_sigma_dex, n)   # lognormal in C
    ms = rng.normal(m, m_sigma, n)
    da = (a_lim - a) / steps
    cycles = np.zeros(n)
    ai = a
    # da is identical across samples (fixed crack geometry), so vectorize over C,m:
    for _ in range(steps):
        dK = delta_sigma * Y * math.sqrt(math.pi * ai)
        cycles += da / (Cs * dK ** ms)
        ai += da
    return {
        "p10": int(np.percentile(cycles, 10)),
        "p50": int(np.percentile(cycles, 50)),
        "p90": int(np.percentile(cycles, 90)),
        "mean": int(cycles.mean()),
        "n": n,
    }


def project_growth(prev_mm: float, curr_mm: float, cycles_between: int, n_points: int = 6) -> list[tuple[int, float]]:
    """Return [(cycle_offset, size_mm), ...] projecting the measured rate forward.

    Used by the dashboard to draw the crack-growth trend line.
    """
    if cycles_between <= 0:
        return [(0, curr_mm)]
    rate = max((curr_mm - prev_mm) / cycles_between, 0.0)
    step = max(cycles_between, 1)
    return [(i * step, round(curr_mm + rate * i * step, 2)) for i in range(n_points)]


def _demo() -> None:
    """Self-check: MC RUL must be ordered and monotone in crack size (safety path)."""
    small = paris_rul_mc(6.0, 12.0)
    big = paris_rul_mc(10.0, 12.0)
    assert small and big
    assert small["p10"] <= small["p50"] <= small["p90"], small     # percentiles ordered
    assert big["p50"] < small["p50"], (big["p50"], small["p50"])    # bigger crack -> less life
    assert paris_rul_mc(13.0, 12.0)["p50"] == 0                     # already past limit
    # deterministic estimator should sit inside the MC band
    det = paris_cycles_to_limit(6.0, 12.0)
    assert small["p10"] <= det <= small["p90"], (small, det)
    print(f"paris MC self-check OK  |  6->12mm RUL P10/P50/P90 = "
          f"{small['p10']:,}/{small['p50']:,}/{small['p90']:,} cyc (det {det:,})")


if __name__ == "__main__":
    _demo()
