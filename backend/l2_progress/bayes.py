"""L2b — Bayesian per-tail crack-growth learning (the twin that actually *learns*).

The Monte-Carlo RUL band in `paris.py` propagates *material-constant* uncertainty — it is
the same wide prior for every aircraft, and it never tightens no matter how many times you
scan a given crack. That is honest but it is not learning.

This module closes that loop. Each defect's crack-growth RATE (mm per 1000 cycles) is a
latent quantity we update with a conjugate **Normal-Normal** model as repeated scans arrive:

    prior     rate ~ N(mu0, tau0^2)        <- seeded by the FEDERATED global growth prior
    evidence  each pair of consecutive scans gives one measured rate r_i ~ N(rate, sigma^2)
    posterior rate | data ~ N(mu_n, tau_n^2)   (closed form, no sampling)

So a data-poor tail starts at the whole federation's prior and, scan by scan, converges to
its OWN measured behaviour — the posterior standard deviation shrinks monotonically with
each scan. We then push that tightened rate distribution through remaining-mm / rate to get
a *learned* P10/P50/P90 RUL band that is narrower than the one-size-fits-all physics band.

Everything here is closed-form and deterministic (no RNG), so it is trivial to unit-test.
Constants/spreads remain ILLUSTRATIVE — calibrate per structure before quoting a slide.
"""
from __future__ import annotations

import math

_Z80 = 1.2815515594  # z for the 10th/90th percentile (an 80% central band)
_MIN_OBS_SD = 0.05    # mm/1k cyc — floor on measurement noise, avoids false overconfidence
_MIN_RATE = 0.02      # mm/1k cyc — floor on the slow-growth tail, keeps RUL finite


def rates_from_scans(scans: list[dict]) -> list[float]:
    """Measured growth rates (mm per 1000 cycles) from consecutive scans of ONE defect.

    `scans` are findings dicts with `size_mm` and `cycles`. Each adjacent pair yields one
    rate; non-growing / zero-interval pairs are dropped (a shrinking crack is noise, not
    evidence of negative growth)."""
    s = sorted(scans, key=lambda x: x.get("cycles") or 0)
    rates: list[float] = []
    for a, b in zip(s, s[1:]):
        dc = (b.get("cycles") or 0) - (a.get("cycles") or 0)
        dz = (b.get("size_mm") or 0) - (a.get("size_mm") or 0)
        if dc > 0 and dz > 0:
            rates.append(dz / dc * 1000.0)   # mm/cycle -> mm/1000 cycles
    return rates


def update_growth_rate(rates: list[float], prior_mean: float, prior_sd: float) -> dict:
    """Conjugate Normal-Normal posterior for a defect's growth rate (mm/1k cyc).

    Returns the prior, the posterior (mean, sd), the number of scan-derived observations,
    and `tighten` = prior_sd / post_sd (>= 1; how many times narrower the estimate got)."""
    prior_sd = max(prior_sd, 1e-6)
    n = len(rates)
    if n == 0:
        return {"updated": False, "scans": 0, "prior_mean": prior_mean, "prior_sd": prior_sd,
                "post_mean": prior_mean, "post_sd": prior_sd, "tighten": 1.0}

    rbar = sum(rates) / n
    if n >= 2:
        var = sum((r - rbar) ** 2 for r in rates) / (n - 1)   # sample variance (ddof=1)
        obs_sd = max(math.sqrt(var), _MIN_OBS_SD)
    else:
        obs_sd = max(prior_sd, _MIN_OBS_SD)                   # one obs: lean on prior-scale noise

    prior_prec = 1.0 / (prior_sd ** 2)
    like_prec = n / (obs_sd ** 2)
    post_prec = prior_prec + like_prec
    post_mean = (prior_mean * prior_prec + rbar * like_prec) / post_prec
    post_sd = math.sqrt(1.0 / post_prec)
    return {"updated": True, "scans": n, "obs_mean": rbar, "obs_sd": obs_sd,
            "prior_mean": prior_mean, "prior_sd": prior_sd,
            "post_mean": post_mean, "post_sd": post_sd, "tighten": prior_sd / post_sd}


def learned_rul_band(remaining_mm: float, post_mean_kcyc: float, post_sd_kcyc: float) -> dict | None:
    """Turn a posterior growth-rate distribution into a P10/P50/P90 RUL band (cycles).

    RUL = remaining_mm / rate, so a FAST rate (high percentile) gives a SHORT life: the
    conservative P10 RUL comes from the 90th-percentile rate. Rate is floored positive so
    the optimistic tail stays finite."""
    if remaining_mm <= 0:
        return {"p10": 0, "p50": 0, "p90": 0}
    hi = (post_mean_kcyc + _Z80 * post_sd_kcyc) / 1000.0            # fast growth
    mid = max(post_mean_kcyc, _MIN_RATE) / 1000.0
    lo = max(post_mean_kcyc - _Z80 * post_sd_kcyc, _MIN_RATE) / 1000.0  # slow growth
    hi = max(hi, _MIN_RATE / 1000.0)
    p10, p50, p90 = remaining_mm / hi, remaining_mm / mid, remaining_mm / lo
    p10, p50, p90 = sorted((p10, p50, p90))
    return {"p10": int(round(p10)), "p50": int(round(p50)), "p90": int(round(p90))}


def learn(scans: list[dict], remaining_mm: float, prior_mean: float, prior_sd: float) -> dict | None:
    """Full per-defect learning step: scans -> rates -> posterior -> tightened RUL band.

    Returns None when there is no growth evidence yet (fall back to the physics MC band)."""
    rates = rates_from_scans(scans)
    if not rates:
        return None
    post = update_growth_rate(rates, prior_mean, prior_sd)
    band = learned_rul_band(remaining_mm, post["post_mean"], post["post_sd"])
    return {**post, "remaining_mm": round(remaining_mm, 2), "band": band}


def _demo() -> None:
    """Self-check: posterior tightens monotonically with scans and pulls toward the data."""
    prior_mean, prior_sd = 0.80, 0.25

    p0 = update_growth_rate([], prior_mean, prior_sd)
    assert not p0["updated"] and p0["tighten"] == 1.0, p0

    # a tail whose crack grows ~1.2 mm/kcyc, faster than the fleet prior of 0.8
    obs = [1.15, 1.22, 1.18, 1.25]
    prev_sd, prev_scans = prior_sd, 0
    for k in range(1, len(obs) + 1):
        p = update_growth_rate(obs[:k], prior_mean, prior_sd)
        assert p["post_sd"] <= prev_sd + 1e-9, (k, p["post_sd"], prev_sd)     # never widens
        assert p["scans"] == k > prev_scans
        prev_sd, prev_scans = p["post_sd"], p["scans"]
    assert p["post_mean"] > prior_mean, p          # posterior moved toward the faster data
    assert p["tighten"] > 1.5, p                   # and got meaningfully tighter

    # tighter rate distribution -> narrower RUL band than a vague one
    wide = learned_rul_band(4.0, 0.80, 0.25)
    tight = learned_rul_band(4.0, 1.20, p["post_sd"])
    assert wide["p10"] <= wide["p50"] <= wide["p90"], wide
    assert (tight["p90"] - tight["p10"]) < (wide["p90"] - wide["p10"]), (tight, wide)

    full = learn([{"size_mm": 6.0, "cycles": 1000}, {"size_mm": 7.2, "cycles": 2000}], 4.0,
                 prior_mean, prior_sd)
    assert full and full["updated"] and full["band"]["p10"] <= full["band"]["p90"], full
    print(f"bayes self-check OK  |  prior {prior_mean}±{prior_sd} -> "
          f"posterior {p['post_mean']:.3f}±{p['post_sd']:.3f} (x{p['tighten']:.1f} tighter) "
          f"after {p['scans']} scans; learned band {full['band']}")


if __name__ == "__main__":
    _demo()
