"""NGAFID risk board — RULE-BASED baseline over REAL maintenance records.

Honest framing: there is no trained classifier behind this board (that is
next-step ML work — see ml/ngafid_train.py for the full recipe). Instead every
flight in data/ngafid/all_flights/flight_header.csv (28,935 real GA flights
recorded around 7k real unscheduled-maintenance events) is scored by a
deterministic, monotonic, one-sentence formula:

    risk = imminence x (0.6 + 0.25*exposure + 0.15*repeat)
      imminence = 1 / (1 + days_to_event/7)   # 1.0 on the day, 0.5 a week out
      exposure  = flight_length / 6000, clipped to [0,1]
      repeat    = number_flights_before / 4, clipped to [0,1]
    post-maintenance / same-day flights score a flat 0.05.

Explainable by construction: the "why" is the dataset's own recorded issue
(label + hierarchy) plus the imminence/repeat facts — no fabricated sensor
readings. RUL band is a fixed-spread placeholder around the recorded
days-to-event (P50 = days, P10 = 0.6x, P90 = 1.4x).

Each maintenance event is one aircraft episode ("N-<event_id>"); the board
ranks episodes by risk at their latest pre-event flight — the planner's
morning screen, replayed over real history.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "data" / "ngafid" / "all_flights" / "flight_header.csv"

# ponytail: fixed thresholds; make them query params if the what-if page needs sliders
GROUND_AT, MONITOR_AT = 0.70, 0.45


@lru_cache(maxsize=1)
def _load():
    if not HEADER.exists():
        return None
    import pandas as pd
    df = pd.read_csv(HEADER).rename(columns={"Master Index": "master_index"})
    # same event derivation as ml/ngafid_train.py: a new event starts where a
    # 'before' row follows a non-'before' row, or the issue label changes
    is_before = df["before_after"] == "before"
    new_event = (is_before & ~is_before.shift(fill_value=False)) | (df["label"] != df["label"].shift())
    df["event_id"] = new_event.cumsum()
    df["days_to_maint"] = (-df["date_diff"]).where(is_before)

    imminence = 1.0 / (1.0 + df["days_to_maint"] / 7.0)
    exposure = (df["flight_length"] / 6000.0).clip(0, 1)
    repeat = (df["number_flights_before"] / 4.0).clip(0, 1)
    df["risk"] = (imminence * (0.6 + 0.25 * exposure + 0.15 * repeat)).where(is_before, 0.05).round(3)
    return df


def _band(days: float) -> dict:
    # ponytail: fixed +/-40% spread; replace with quantile regression when a model exists
    if days != days:  # NaN — post-maintenance flight, no pending event
        return {"p10": None, "p50": None, "p90": None}
    return {"p10": round(days * 0.6, 1), "p50": round(days, 1), "p90": round(days * 1.4, 1)}


def _why(row, k: int = 3) -> list[str]:
    """Facts straight from the maintenance record — nothing fabricated."""
    if row["before_after"] != "before":
        return [f"post-maintenance flight — {row['label']} resolved"]
    out = [f"recorded issue: {row['label']}",
           f"latest flight {int(row['days_to_maint'])} day(s) before the maintenance event"]
    if row["number_flights_before"] > 0:
        out.append(f"{int(row['number_flights_before'])} prior flight(s) already in this pre-failure window")
    if row["flight_length"] >= 6000:
        out.append(f"long-exposure flight ({int(row['flight_length'])} s)")
    return out[:k + 1]


def _action(risk: float) -> str:
    if risk >= GROUND_AT:
        return "pull forward — inspect before next flight"
    if risk >= MONITOR_AT:
        return "monitor — shorten inspection interval"
    return "fly — no evidence of an imminent issue"


@lru_cache(maxsize=1)
def board() -> dict:
    df = _load()
    if df is None:
        return {"ready": False,
                "hint": "data/ngafid/all_flights/flight_header.csv not found — fetch the NGAFID dataset"}
    rows = []
    for eid, g in df.groupby("event_id"):
        pre = g[g["before_after"] == "before"].sort_values("master_index")
        if pre.empty:  # no pre-event flights recorded — nothing to warn about
            continue
        now = pre.tail(3)["risk"].mean()
        worst = pre.loc[pre["risk"].idxmax()]
        rows.append({
            "tail": f"N-{eid}", "flight": int(worst["master_index"]), "issue": g["label"].iloc[0],
            "system": g["hierarchy"].dropna().iloc[0] if g["hierarchy"].notna().any() else "other",
            "flights": int(len(g)),
            "risk_now": round(float(now), 3), "risk_peak": round(float(pre["risk"].max()), 3),
            "rul_days": _band(float(worst["days_to_maint"])),
            "action": _action(now),
            "why": _why(worst),
        })
    rows.sort(key=lambda r: -r["risk_now"])
    return {"ready": True, "source": "NGAFID (real GA flight + maintenance records)",
            "model": {"kind": "rule-based baseline — no trained classifier",
                      "formula": "risk = 1/(1+days_to_event/7) x (0.6 + 0.25*exposure + 0.15*repeat)",
                      "note": ("deterministic and explainable by construction over real "
                               "maintenance records; trained gradient-boosted classifier is "
                               "next-step ML work (ml/ngafid_train.py)"),
                      "n_flights": int(len(df)), "n_episodes": len(rows)},
            "thresholds": {"ground": GROUND_AT, "monitor": MONITOR_AT},
            "rows": rows}


def flight(master_index: int) -> dict:
    df = _load()
    if df is None:
        return {"ready": False, "hint": "flight_header.csv not found — fetch the NGAFID dataset"}
    m = df[df["master_index"] == master_index]
    if m.empty:
        return {"error": f"no flight {master_index} in the dataset"}
    r = m.iloc[0]
    return {"ready": True, "master_index": int(master_index),
            "risk": round(float(r["risk"]), 3), "action": _action(float(r["risk"])),
            "truth": r["before_after"],  # honest: this is a labelled research dataset
            "rul_days": _band(float(r["days_to_maint"])),
            "why": _why(r, k=5)}


if __name__ == "__main__":   # smoke check: python -m backend.l1_twin.ngafid_risk
    bd = board()
    assert "ready" in bd
    if bd["ready"]:
        rs = bd["rows"]
        assert rs and rs[0]["risk_now"] >= rs[-1]["risk_now"]
        assert all(0.0 <= r["risk_now"] <= 1.0 for r in rs)
        fl = flight(1)
        assert fl["ready"] and fl["truth"] == "before" and fl["rul_days"]["p50"] is not None
        print(f"{len(rs)} aircraft episodes; worst: {rs[0]['tail']} risk {rs[0]['risk_now']} "
              f"({rs[0]['issue']}) — {rs[0]['why']}")
        print(f"actions: pull={sum(r['action'].startswith('pull') for r in rs)} "
              f"monitor={sum(r['action'].startswith('monitor') for r in rs)} "
              f"fly={sum(r['action'].startswith('fly') for r in rs)}")
    else:
        print(bd["hint"])
