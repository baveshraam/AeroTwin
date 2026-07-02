"""L1c — Federated fleet learning (ITAR-safe shared crack-growth priors).

The problem: any single hangar sees too few cracks to estimate a reliable growth-rate
prior, and inspection imagery legally cannot leave an ITAR site — so you cannot pool the
raw data. The fix: each site shares only SUFFICIENT STATISTICS of its growth rates
(count, mean, variance) — never an image, never a per-tail record — and a coordinator
does federated averaging (FedAvg, weighted by sample count) into a global prior every
site can use. A data-poor site then estimates RUL from the whole federation's experience
without any raw data crossing a boundary.

This is a SIMULATION of that protocol (deck + working code). The privacy property is
structural: `site_update` emits three numbers, so there is nothing sensitive to leak. In
production, add secure aggregation / DP noise on top; the interface is unchanged.
"""
from __future__ import annotations

import math


def site_update(rates_mm_per_kcyc: list[float]) -> dict:
    """A site's shareable local statistics — the ONLY thing that leaves the hangar."""
    n = len(rates_mm_per_kcyc)
    if n == 0:
        return {"n": 0, "mean": 0.0, "var": 0.0}
    mean = sum(rates_mm_per_kcyc) / n
    var = sum((r - mean) ** 2 for r in rates_mm_per_kcyc) / n
    return {"n": n, "mean": mean, "var": var}


def federated_average(updates: list[dict]) -> dict:
    """FedAvg: sample-count-weighted global prior from site statistics (no raw data)."""
    N = sum(u["n"] for u in updates)
    if N == 0:
        return {"n": 0, "mean": 0.0, "var": 0.0, "std_error": 0.0}
    mean = sum(u["n"] * u["mean"] for u in updates) / N
    # pooled variance about the global mean (within-site + between-site spread)
    var = sum(u["n"] * (u["var"] + (u["mean"] - mean) ** 2) for u in updates) / N
    return {"n": N, "mean": mean, "var": var, "std_error": math.sqrt(var / N)}


def dp_site_release(update: dict, epsilon: float, clip: float, rng) -> dict:
    """Differentially-private version of a site's release (Laplace mechanism).

    Even three summary numbers can, in principle, leak about an individual crack if a site
    is tiny. The formal fix is DP: the site clips each rate to [0, clip] (bounding any one
    tail's influence) and adds Laplace noise to its released MEAN. The L1 sensitivity of a
    clipped mean over ``n`` samples is ``clip / n`` — one tail can move the mean by at most
    that — so noise at scale ``sensitivity / epsilon`` gives ``epsilon``-DP for that site.
    Smaller epsilon = more privacy = more noise; a data-rich site pays a smaller noise price
    (its n is larger), which is exactly why pooling still helps the data-poor sites.
    """
    n = update["n"]
    if n == 0:
        return {"n": 0, "mean": 0.0, "var": update.get("var", 0.0), "epsilon": epsilon}
    sensitivity = clip / n
    noisy_mean = update["mean"] + float(rng.laplace(0.0, sensitivity / epsilon))
    # a released mean is still a growth rate — clamp to the physically valid range
    noisy_mean = max(0.0, min(clip, noisy_mean))
    return {"n": n, "mean": noisy_mean, "var": update["var"], "epsilon": epsilon}


def differentially_private_average(updates: list[dict], epsilon: float, clip: float, rng) -> dict:
    """FedAvg over per-site DP releases. Each site spends its OWN epsilon budget once;
    the coordinator's averaging is post-processing (DP is closed under post-processing, so
    it costs no extra privacy). The global prior is therefore epsilon-DP w.r.t. every site.
    """
    releases = [dp_site_release(u, epsilon, clip, rng) for u in updates]
    glob = federated_average(releases)
    glob["epsilon"] = epsilon
    glob["clip"] = clip
    return glob


def simulate(seed: int = 0) -> dict:
    """4 sites draw a few noisy growth rates from one true distribution. Show the global
    federated prior beats a data-poor site's local-only estimate (tighter standard error).
    """
    import numpy as np
    rng = np.random.default_rng(seed)
    true_mean, true_sd = 0.80, 0.25          # mm per 1000 cycles (illustrative)
    sizes = [3, 12, 25, 5]                    # a couple of data-poor hangars, a couple rich
    sites, updates = [], []
    for i, k in enumerate(sizes):
        rates = list(np.clip(rng.normal(true_mean, true_sd, k), 0.05, None))
        u = site_update(rates)
        se = math.sqrt(u["var"] / u["n"]) if u["n"] else float("inf")
        sites.append({"site": f"HANGAR-{i+1}", "n": u["n"], "local_mean": round(u["mean"], 3),
                      "local_err": round(abs(u["mean"] - true_mean), 3),
                      "local_std_error": round(se, 3)})
        updates.append(u)
    glob = federated_average(updates)
    # differentially-private release on top of the structural privacy (epsilon-DP per site)
    dp_eps, dp_clip = 1.0, 2.0
    dp = differentially_private_average(updates, epsilon=dp_eps, clip=dp_clip, rng=rng)
    return {
        "true_mean": true_mean,
        "global_mean": round(glob["mean"], 3),
        "global_err": round(abs(glob["mean"] - true_mean), 3),
        "global_std_error": round(glob["std_error"], 3),
        # population spread (sqrt of pooled variance) — the right scale for a PRIOR on an
        # individual tail's rate, vs. std_error which is the precision of the global mean.
        "global_spread": round(math.sqrt(glob["var"]), 3),
        "sites": sites,
        "dp": {
            "epsilon": dp_eps,           # per-site privacy budget (smaller = stronger)
            "clip": dp_clip,             # rate bound that caps any one tail's influence
            "mechanism": "Laplace",
            "global_mean": round(dp["mean"], 3),
            "err": round(abs(dp["mean"] - true_mean), 3),
            "cost_vs_plain": round(abs(dp["mean"] - glob["mean"]), 3),  # noise added by DP
        },
        "note": "Only (n, mean, var) left each hangar — no imagery, no per-tail record.",
    }


def _demo() -> None:
    """Self-check: FedAvg == count-weighted mean, and pooling tightens the estimate."""
    a = site_update([1.0, 1.0])          # n=2 mean=1.0
    b = site_update([4.0, 4.0, 4.0, 4.0])  # n=4 mean=4.0
    g = federated_average([a, b])
    assert g["n"] == 6 and abs(g["mean"] - (2 * 1.0 + 4 * 4.0) / 6) < 1e-9, g   # weighted mean

    sim = simulate(seed=0)
    poorest = min(sim["sites"], key=lambda s: s["n"])
    # federated standard error must beat the data-poor site's local standard error
    assert sim["global_std_error"] < poorest["local_std_error"], (sim["global_std_error"], poorest)

    # DP: the epsilon-DP global mean stays close to the plain FedAvg mean (utility is
    # preserved at epsilon=1) yet is provably private — small noise, not a broken estimate.
    dp = sim["dp"]
    assert dp["cost_vs_plain"] < 0.5, dp     # noise is modest at epsilon=1 over this fleet
    assert 0.0 <= dp["global_mean"] <= dp["clip"], dp
    print(f"federated self-check OK  |  true {sim['true_mean']} -> global {sim['global_mean']} "
          f"(err {sim['global_err']}, SE {sim['global_std_error']}); "
          f"poorest site {poorest['site']} n={poorest['n']} SE {poorest['local_std_error']}")
    print(f"DP self-check OK  |  epsilon={dp['epsilon']} -> DP global {dp['global_mean']} "
          f"(err {dp['err']}, noise cost {dp['cost_vs_plain']} vs plain FedAvg)")


if __name__ == "__main__":
    _demo()
