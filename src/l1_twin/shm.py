"""L1b — Structural Health Monitoring: continuous health BETWEEN inspections.

Inspections are discrete (weeks/months apart); between them the twin goes dark unless
onboard sensors fill the gap. This synthesizes fused strain / acoustic-emission /
vibration features for a tail whose crack is growing, and runs an ONLINE change-point
detector (EWMA baseline + CUSUM over a fused damage index) that raises a
between-inspection alert the moment the signal diverges from the last baseline — turning
discrete scans into a continuous twin.

Honesty: the sensor model + fusion weights are ILLUSTRATIVE, physics-motivated stand-ins
(as a crack grows: peak strain rises, AE hit-rate accelerates, a natural frequency shifts
down with stiffness loss). The DETECTOR (EWMA + CUSUM) is a real, standard SHM algorithm.
Swap the synthetic stream for a trained 1D-CNN/LSTM on field telemetry when it exists —
the detector and the twin interface stay identical. See [[datasets-and-training]].
"""
from __future__ import annotations

import numpy as np

# CUSUM tuning (illustrative): drift allowance and alarm threshold on the fused index.
CUSUM_DRIFT = 0.004
CUSUM_THRESHOLD = 0.06


def shm_health(rate_mm_per_cyc: float, a0_mm: float = 6.0, cycles: int = 6000,
               step: int = 100, seed: int = 0) -> dict:
    """Simulate the fused SHM signal for a growing defect and detect the change online.

    rate_mm_per_cyc: crack-growth rate (from the tail's own scan history).
    Returns {series:[{cycle,strain,ae,freq_shift,fused,health}], alert_cycle, health_now}.
    """
    rng = np.random.default_rng(seed)
    ts = np.arange(0, cycles + 1, step)
    a = a0_mm + rate_mm_per_cyc * ts                      # crack size over the interval
    da = np.clip(a - a0_mm, 0, None)                      # growth since baseline
    dmg = 0.06 * da                                       # latent damage the sensors sense
    strain = 1.0 + 0.5 * dmg + rng.normal(0, 0.01, ts.size)         # microstrain, rises
    ae = 0.15 + 0.9 * dmg + rng.normal(0, 0.015, ts.size)          # AE hit-rate, accelerates
    freq = -0.4 * dmg + rng.normal(0, 0.004, ts.size)             # nat-freq shift, drops
    # fused damage index in ~[0,1]: weighted, normalized combination of the three cues
    fused = np.clip(0.5 * (strain - 1.0) + 0.5 * (ae - 0.15) + 0.4 * (-freq), 0, 1.0)

    # EWMA baseline from the first few samples (the "healthy" reference right after a scan)
    base = float(np.mean(fused[:3]))
    s, alert_cycle = 0.0, None
    series = []
    for i, c in enumerate(ts):
        s = max(0.0, s + (fused[i] - base - CUSUM_DRIFT))            # one-sided CUSUM
        if alert_cycle is None and s > CUSUM_THRESHOLD:
            alert_cycle = int(c)
        health = int(round(100 * (1 - min(fused[i], 1.0))))
        series.append({"cycle": int(c), "strain": round(float(strain[i]), 3),
                       "ae": round(float(ae[i]), 3), "freq_shift": round(float(freq[i]), 4),
                       "fused": round(float(fused[i]), 3), "health": health})
    return {"series": series, "alert_cycle": alert_cycle,
            "health_now": series[-1]["health"], "baseline": round(base, 3)}


def _demo() -> None:
    """Self-check: a growing crack must trip CUSUM; a stable one must not."""
    growing = shm_health(rate_mm_per_cyc=8.0 / 6000)   # ~2mm over the interval, like VT-AXB
    stable = shm_health(rate_mm_per_cyc=0.0)
    assert growing["alert_cycle"] is not None, "growing defect should raise an SHM alert"
    assert stable["alert_cycle"] is None, "stable structure should NOT alert"
    assert growing["health_now"] < stable["health_now"], (growing["health_now"], stable["health_now"])
    print(f"SHM self-check OK  |  growing alerts @ {growing['alert_cycle']} cyc "
          f"(health {growing['health_now']}), stable silent (health {stable['health_now']})")


if __name__ == "__main__":
    _demo()
