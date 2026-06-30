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


def project_growth(prev_mm: float, curr_mm: float, cycles_between: int, n_points: int = 6) -> list[tuple[int, float]]:
    """Return [(cycle_offset, size_mm), ...] projecting the measured rate forward.

    Used by the dashboard to draw the crack-growth trend line.
    """
    if cycles_between <= 0:
        return [(0, curr_mm)]
    rate = max((curr_mm - prev_mm) / cycles_between, 0.0)
    step = max(cycles_between, 1)
    return [(i * step, round(curr_mm + rate * i * step, 2)) for i in range(n_points)]
