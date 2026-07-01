"""L1 — Per-tail digital twin (persistent structural record).

A SQLite-backed record of every finding, pinned to a tail number + ATA zone +
location, with the inspection cycle count and model version. This is what turns a
one-off detector into a product: 'did this crack grow since the last check?' becomes
a query, not a guess.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "twin.db"


def connect() -> sqlite3.Connection:
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def init() -> None:
    con = connect()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS findings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            tail          TEXT NOT NULL,
            ata_zone      TEXT NOT NULL,
            location      TEXT NOT NULL,
            defect_type   TEXT NOT NULL,
            size_mm       REAL NOT NULL,
            grade         TEXT NOT NULL,
            airworthiness TEXT,
            scan_date     TEXT,
            cycles        INTEGER,
            cycles_to_limit INTEGER,
            confidence    REAL,
            model_version TEXT
        )
        """
    )
    con.commit()
    con.close()


def add_finding(f: dict) -> int:
    con = connect()
    cur = con.execute(
        """
        INSERT INTO findings
            (tail, ata_zone, location, defect_type, size_mm, grade, airworthiness,
             scan_date, cycles, cycles_to_limit, confidence, model_version)
        VALUES
            (:tail, :ata_zone, :location, :defect_type, :size_mm, :grade, :airworthiness,
             :scan_date, :cycles, :cycles_to_limit, :confidence, :model_version)
        """,
        {**{k: f.get(k) for k in (
            "tail", "ata_zone", "location", "defect_type", "size_mm", "grade",
            "airworthiness", "scan_date", "cycles", "cycles_to_limit",
            "confidence", "model_version")}},
    )
    con.commit()
    rowid = cur.lastrowid
    con.close()
    return rowid


def history(tail: str, location: str, defect_type: str) -> list[dict]:
    """All prior findings of the same defect at the same spot on the same tail."""
    con = connect()
    rows = con.execute(
        """SELECT * FROM findings
           WHERE tail=? AND location=? AND defect_type=?
           ORDER BY cycles""",
        (tail, location, defect_type),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def findings_for_tail(tail: str) -> list[dict]:
    con = connect()
    rows = con.execute("SELECT * FROM findings WHERE tail=? ORDER BY cycles", (tail,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def all_findings() -> list[dict]:
    con = connect()
    rows = con.execute("SELECT * FROM findings ORDER BY tail, cycles").fetchall()
    con.close()
    return [dict(r) for r in rows]
