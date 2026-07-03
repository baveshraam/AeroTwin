"""NGAFID risk board — maintenance-need prediction on REAL flight telemetry.

Serves what ml/ngafid_train.py learned: per-flight P(maintenance-needed) from
engine sensor aggregates, a P10/P50/P90 days-to-maintenance band, and a named-
sensor explanation for every score (z-scores against the post-maintenance
"healthy fleet" baseline, weighted by the model's own feature importances).

Each maintenance event in the dataset is shown as one aircraft episode
("N-<event_id>"): its telemetry drifting toward the event is exactly the story
the fleet board tells. If the model artifact is missing the API answers with a
clear "train first" payload instead of faking numbers.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "ml" / "models" / "ngafid_risk.joblib"
FLIGHTS = ROOT / "ml" / "models" / "ngafid_flights.parquet"

# ponytail: fixed thresholds; make them query params if the what-if page needs sliders
GROUND_AT, MONITOR_AT = 0.70, 0.45


@lru_cache(maxsize=1)
def _load():
    if not (BUNDLE.exists() and FLIGHTS.exists()):
        return None
    import joblib
    import pandas as pd
    b = joblib.load(BUNDLE)
    df = pd.read_parquet(FLIGHTS)
    feats = b["features"]
    df["risk"] = b["clf"].predict_proba(df[feats])[:, 1]
    X = df[feats].fillna(b["fill"])
    for q, name in ((0.1, "p10"), (0.5, "p50"), (0.9, "p90")):
        df[name] = b["quantiles"][q].predict(X).clip(min=0)
    return b, df


def _why(row, b, k: int = 3) -> list[str]:
    """Top-k sensor signals for this flight: |z vs healthy fleet| x model importance."""
    scores = []
    for f, imp in b["importances"].items():
        if imp <= 0:
            continue
        z = (row[f] - b["healthy_mean"][f]) / b["healthy_std"][f]
        if z == z:  # skip NaN sensors
            scores.append((abs(z) * imp, f, z))
    scores.sort(reverse=True)
    return [f"{f} {'high' if z > 0 else 'low'} ({abs(z):.1f} sigma vs healthy fleet)"
            for _, f, z in scores[:k]]


def _action(risk: float) -> str:
    if risk >= GROUND_AT:
        return "pull forward — inspect before next flight"
    if risk >= MONITOR_AT:
        return "monitor — shorten inspection interval"
    return "fly — no telemetry evidence of an issue"


def board() -> dict:
    loaded = _load()
    if loaded is None:
        return {"ready": False,
                "hint": "no model artifact — run: python -m ml.ngafid_train"}
    b, df = loaded
    rows = []
    for eid, g in df.groupby("event_id"):
        g = g.sort_values("master_index")
        now = g.tail(3)["risk"].mean()          # where this aircraft stands today
        pre = g[g["y"] == 1]
        peak = pre["risk"].rolling(3, min_periods=1).mean().max() if len(pre) else 0.0
        worst = g.loc[g["risk"].idxmax()]
        rows.append({
            "tail": f"N-{eid}", "issue": g["label"].iloc[0],
            "system": g["hierarchy"].iloc[0] if g["hierarchy"].notna().any() else "other",
            "flights": int(len(g)),
            "risk_now": round(float(now), 3), "risk_peak": round(float(peak), 3),
            "rul_days": {"p10": round(float(worst["p10"]), 1),
                         "p50": round(float(worst["p50"]), 1),
                         "p90": round(float(worst["p90"]), 1)},
            "action": _action(now),
            "why": _why(worst, b),
        })
    rows.sort(key=lambda r: -r["risk_now"])
    return {"ready": True, "source": "NGAFID (real GA flight + maintenance data)",
            "model": b["metrics"], "thresholds": {"ground": GROUND_AT, "monitor": MONITOR_AT},
            "rows": rows}


def flight(master_index: int) -> dict:
    loaded = _load()
    if loaded is None:
        return {"ready": False, "hint": "run: python -m ml.ngafid_train"}
    b, df = loaded
    m = df[df["master_index"] == master_index]
    if m.empty:
        return {"error": f"no flight {master_index} in the scored sample"}
    r = m.iloc[0]
    return {"ready": True, "master_index": int(master_index),
            "risk": round(float(r["risk"]), 3), "action": _action(float(r["risk"])),
            "truth": r["before_after"],  # honest: this is a labelled research dataset
            "rul_days": {"p10": round(float(r["p10"]), 1), "p50": round(float(r["p50"]), 1),
                         "p90": round(float(r["p90"]), 1)},
            "why": _why(r, b, k=5)}


if __name__ == "__main__":   # smoke check: python -m backend.l1_twin.ngafid_risk
    bd = board()
    assert "ready" in bd
    if bd["ready"]:
        assert bd["rows"] and bd["rows"][0]["risk_now"] >= bd["rows"][-1]["risk_now"]
        print(f"{len(bd['rows'])} aircraft episodes; worst: {bd['rows'][0]['tail']} "
              f"risk {bd['rows'][0]['risk_now']} — {bd['rows'][0]['why']}")
    else:
        print(bd["hint"])
