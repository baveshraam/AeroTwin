"""NGAFID maintenance-need trainer — the real-data heart of AeroTwin's prognostics.

Data: NGAFID maintenance dataset (zenodo.org/records/6624956), extracted to
data/ngafid/all_flights/  (flight_header.csv + one_parq/part.N.parquet).

Task, honestly framed:
  * classify  : is this flight BEFORE an unscheduled maintenance event (problem
                brewing) or AFTER it (fixed)?  P(before) = maintenance-need risk.
  * regress   : for pre-maintenance flights, days until the maintenance event,
                as a P10/P50/P90 quantile band (the RUL confidence band).

LEAKAGE — the two header columns you must NOT feed the classifier:
  * date_diff              : its sign IS the label (negative=before, positive=after).
                             We only use |date_diff| as the regression TARGET.
  * number_flights_before  : -1 for every after/same row, >=0 for before rows —
                             target-derived bookkeeping, 100% fake accuracy if used.
Features are flight_length + per-flight sensor aggregates (mean/std/max of oil
temp/pressure, CHT1-4, EGT1-4, RPM, fuel flow, IAS, NormAc, ...) from the parquet.

Splits are grouped by maintenance event (consecutive header rows sharing a label),
so flights around one event never sit in both train and test.

Run:  python -m ml.ngafid_train            # default: 80 parquet parts (~20% of flights)
      python -m ml.ngafid_train --parts 0  # header-only (near-chance — proves honesty)
      python -m ml.ngafid_train --parts 401 --out ml/models  # everything (slow)

Artifacts (gitignored, ~a few MB):
  ml/models/ngafid_risk.joblib     model bundle + healthy-fleet stats + importances
  ml/models/ngafid_flights.parquet scored per-flight feature table for the API board
"""
from __future__ import annotations

import argparse
import glob
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NGAFID = ROOT / "data" / "ngafid" / "all_flights"

# every numeric channel in the parquet except bookkeeping
SENSORS = ["volt1", "volt2", "amp1", "amp2", "FQtyL", "FQtyR", "E1 FFlow",
           "E1 OilT", "E1 OilP", "E1 RPM", "E1 CHT1", "E1 CHT2", "E1 CHT3",
           "E1 CHT4", "E1 EGT1", "E1 EGT2", "E1 EGT3", "E1 EGT4",
           "OAT", "IAS", "VSpd", "NormAc", "AltMSL"]


def load_header() -> pd.DataFrame:
    df = pd.read_csv(NGAFID / "flight_header.csv")
    df = df.rename(columns={"Master Index": "master_index"})
    # one maintenance event = a run of 'before' flights then its same/after flights;
    # a new event starts where a 'before' row follows a non-'before' row (or new label)
    is_before = df["before_after"] == "before"
    new_event = (is_before & ~is_before.shift(fill_value=False)) | (df["label"] != df["label"].shift())
    df["event_id"] = new_event.cumsum()
    return df


def sensor_features(n_parts: int) -> pd.DataFrame:
    """Per-flight mean/std/max for every sensor channel.

    A flight's rows can straddle two parquet parts, so we keep per-part partial
    sums (count/sum/sumsq/max) and combine them exactly — never a row lost or
    double-averaged."""
    allparts = sorted(glob.glob(str(NGAFID / "one_parq" / "part.*.parquet")),
                      key=lambda p: int(p.rsplit(".", 2)[-2]))
    # stride-sample across the whole archive: labels are stored in contiguous blocks,
    # so taking the first N parts would cover only a couple of maintenance types
    stride = max(1, len(allparts) // n_parts)
    parts = allparts[::stride][:n_parts]
    partials = []
    for i, p in enumerate(parts):
        d = pd.read_parquet(p, columns=SENSORS)   # "Master Index" is the parquet index
        g = d.groupby(level=0)
        agg = pd.concat({"count": g.count(), "sum": g.sum(),
                         "sumsq": d.pow(2).groupby(level=0).sum(),
                         "max": g.max()}, axis=1)
        partials.append(agg)
        if (i + 1) % 20 == 0:
            print(f"  parquet {i + 1}/{len(parts)}")
    if not partials:
        return pd.DataFrame()
    allp = pd.concat(partials)
    part = lambda k: allp[k].groupby(level=0)   # select stat first: drops the column level
    cnt, s, ss = part("count").sum(), part("sum").sum(), part("sumsq").sum()
    mean = s / cnt
    var = (ss / cnt - mean ** 2).clip(lower=0)
    out = pd.concat({"mean": mean, "std": np.sqrt(var), "max": part("max").max()}, axis=1)
    out.columns = [f"{ch} ({stat})" for stat, ch in out.columns]
    return out


def build_dataset(n_parts: int) -> tuple[pd.DataFrame, list[str]]:
    hdr = load_header()
    df = hdr[hdr["before_after"].isin(["before", "after"])].copy()  # 'same'-day rows are ambiguous
    df["y"] = (df["before_after"] == "before").astype(int)
    df["days_to_maint"] = -df["date_diff"]          # regression target, before-rows only
    feats = ["flight_length"]
    if n_parts:
        sf = sensor_features(n_parts)
        df = df.join(sf, on="master_index", how="inner")
        feats += list(sf.columns)
    return df.reset_index(drop=True), feats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", type=int, default=80, help="parquet parts to read (0 = header only)")
    ap.add_argument("--out", default=str(ROOT / "ml" / "models"))
    args = ap.parse_args()
    t0 = time.time()

    from sklearn.ensemble import GradientBoostingRegressor, HistGradientBoostingClassifier
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import balanced_accuracy_score, roc_auc_score
    from sklearn.model_selection import GroupShuffleSplit

    df, feats = build_dataset(args.parts)
    print(f"dataset: {len(df)} flights, {len(feats)} features, "
          f"{df['event_id'].nunique()} maintenance events ({time.time() - t0:.0f}s)")

    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=7)
                  .split(df, groups=df["event_id"]))
    train, test = df.iloc[tr], df.iloc[te]

    clf = HistGradientBoostingClassifier(random_state=7)  # NaN-native: sensors may drop out
    clf.fit(train[feats], train["y"])
    prob = clf.predict_proba(test[feats])[:, 1]
    auc = roc_auc_score(test["y"], prob)
    bacc = balanced_accuracy_score(test["y"], prob > 0.5)
    print(f"classifier  ROC-AUC {auc:.3f}   balanced-acc {bacc:.3f}   (event-grouped test)")

    # ---- RUL band: days-to-maintenance quantile regression on before-rows ----
    btr, bte = train[train["y"] == 1], test[test["y"] == 1]
    qmods = {}
    for q in (0.1, 0.5, 0.9):
        m = GradientBoostingRegressor(loss="quantile", alpha=q, random_state=7)
        m.fit(btr[feats].fillna(btr[feats].median()), btr["days_to_maint"])
        qmods[q] = m
    Xb = bte[feats].fillna(btr[feats].median())
    p10, p50, p90 = (qmods[q].predict(Xb) for q in (0.1, 0.5, 0.9))
    mae = float(np.abs(p50 - bte["days_to_maint"]).mean())
    cover = float(((bte["days_to_maint"] >= p10) & (bte["days_to_maint"] <= p90)).mean())
    print(f"RUL P50 MAE {mae:.1f} days   P10-P90 coverage {cover:.0%} (target 80%)")

    # ---- explainability: global importances + healthy-fleet baseline ----
    imp = permutation_importance(clf, test[feats], test["y"], n_repeats=3, random_state=7)
    importances = dict(sorted(zip(feats, imp.importances_mean), key=lambda kv: -kv[1]))
    print("top signals:", [k for k in importances][:6])
    healthy = train[train["y"] == 0][feats]
    fill = btr[feats].median()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"clf": clf, "quantiles": qmods, "features": feats, "fill": fill,
                 "healthy_mean": healthy.mean(), "healthy_std": healthy.std().replace(0, 1),
                 "importances": importances,
                 "metrics": {"roc_auc": float(auc), "balanced_acc": float(bacc),
                             "rul_p50_mae_days": mae, "rul_band_coverage": cover,
                             "n_train": len(train), "n_test": len(test),
                             "parts_used": args.parts},
                 }, out / "ngafid_risk.joblib")
    keep = ["master_index", "event_id", "label", "hierarchy", "before_after",
            "days_to_maint", "y"] + feats
    df[keep].to_parquet(out / "ngafid_flights.parquet", index=False)
    (out / "ngafid_metrics.json").write_text(json.dumps(
        {"roc_auc": float(auc), "balanced_acc": float(bacc), "rul_p50_mae_days": mae,
         "rul_band_coverage": cover, "top_signals": list(importances)[:10]}, indent=2))
    print(f"saved -> {out / 'ngafid_risk.joblib'}   ({time.time() - t0:.0f}s total)")


if __name__ == "__main__":
    main()
