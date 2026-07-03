"""L0 — Severity grading against SRM Allowable Damage Limits.

Maps a measured defect (type, ATA zone, size in mm) to an airworthiness grade by
looking it up in data/srm_limits.csv. This is the aerospace-literate move: not a
generic 'object detected', but 'minor / major / critical / beyond-limit' against the
governing manual limit.
"""
from __future__ import annotations

import csv
from pathlib import Path

LIMITS = Path(__file__).resolve().parents[2] / "data" / "srm_limits.csv"


def load_limits() -> list[dict]:
    with open(LIMITS, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def grade_defect(defect_type: str, ata_zone: str, size_mm: float) -> dict:
    """Return grade + airworthiness verdict + the limit and manual reference."""
    for row in load_limits():
        if row["defect_type"] == defect_type and str(row["ata_zone"]) == str(ata_zone):
            minor = float(row["minor_max_mm"])
            major = float(row["major_max_mm"])
            limit = float(row["limit_mm"])
            if size_mm <= minor:
                grade, air = "minor", "airworthy — monitor at next scheduled check"
            elif size_mm <= major:
                grade, air = "major", "airworthy — schedule repair"
            elif size_mm <= limit:
                grade, air = "critical", "airworthy — repair before limit crossing; shorten interval"
            else:
                grade, air = "beyond-limit", "NOT AIRWORTHY — grounded until repair"
            return {
                "grade": grade,
                "airworthiness": air,
                "limit_mm": limit,
                "manual_ref": row["manual_ref"],
                "material": row["material"],
            }
    return {
        "grade": "unknown",
        "airworthiness": "no SRM entry found — escalate to certifying staff",
        "limit_mm": None,
        "manual_ref": None,
        "material": None,
    }
