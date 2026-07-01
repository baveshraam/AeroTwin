"""L1 — Twin state & fleet health (the digital-twin 'brain').

The findings table (db.py) is just an event log. THIS is where it becomes a
digital twin: pure functions that turn raw findings into the state an MRO planner
actually acts on —

  - tail_state()  : one aircraft's current structural state — health index (0-100),
                    worst open defect, remaining useful life (RUL) in flight cycles,
                    and a condition-based next-check recommendation.
  - fleet_summary(): every tail ranked worst-health-first — the fleet risk board.

The real-world problem this attacks: structural checks are scheduled on a fixed
CALENDAR/hard-time interval. That over-maintains healthy jets (wasted downtime) and
under-maintains the few with fast-growing damage (safety + AOG risk). The twin knows
each tail's actual condition, so it can PULL a check FORWARD on a bad tail and
SAFELY EXTEND it on a healthy one — condition-based maintenance (CBM+), the lever
the whole MRO industry is moving toward.

No I/O of its own beyond db reads, so the math is trivial to test (see __main__).
"""
from __future__ import annotations

from src.l0_detect.grade import grade_defect
from src.l1_twin import db

# ponytail: one fleet-wide baseline interval stands in for the calendar/hard-time
# check. Per-ATA-zone intervals if a customer's maintenance program needs them.
CALENDAR_INTERVAL_CYCLES = 6000
# Damage-tolerance rule of thumb: schedule the next look at half the remaining life,
# i.e. two inspection opportunities before a defect could reach its limit.
DTA_INSPECT_FRACTION = 0.5


def _limit_mm(f: dict) -> float | None:
    return grade_defect(f["defect_type"], f["ata_zone"], f["size_mm"]).get("limit_mm")


def _severity_ratio(f: dict) -> float:
    """How far the defect has eaten into its allowable limit (0 = new, 1 = at limit)."""
    lim = _limit_mm(f)
    if not lim:
        return 0.0
    return min(f["size_mm"] / lim, 1.0)


def _open_defects(findings: list[dict]) -> list[dict]:
    """Latest finding per (location, defect_type) — the tail's current open state."""
    groups: dict[tuple, dict] = {}
    for f in sorted(findings, key=lambda x: x["cycles"] or 0):
        groups[(f["location"], f["defect_type"])] = f
    return list(groups.values())


def maintenance_recommendation(
    current_cycles: int, rul_cycles: int | None, grounded: bool, worst_grade: str = ""
) -> dict:
    """Condition-based next-check decision, compared against the calendar baseline.

    Severity gates the schedule: a CRITICAL defect is never extended past the calendar
    however rosy the (illustrative) growth projection looks — it may only be pulled in.
    """
    calendar_next = current_cycles + CALENDAR_INTERVAL_CYCLES
    if grounded:
        return {
            "basis": "grounded",
            "action": "GROUND - beyond-limit damage; embody certified repair before return to service",
            "next_check_cycles": current_cycles,
            "vs_calendar_cycles": None,
        }
    if rul_cycles is not None:
        cbm_next = current_cycles + int(rul_cycles * DTA_INSPECT_FRACTION)
        if worst_grade == "critical" and cbm_next > calendar_next:
            return {
                "basis": "condition-based",
                "action": "HOLD at scheduled check - critical defect; repair before limit, no extension",
                "next_check_cycles": calendar_next,
                "vs_calendar_cycles": 0,
            }
        delta = cbm_next - calendar_next  # negative = sooner than calendar
        if delta < 0:
            action = (f"PULL INSPECTION FORWARD {abs(delta)} cycles - defect growth "
                      f"outruns the {CALENDAR_INTERVAL_CYCLES}-cycle calendar interval")
        else:
            action = (f"SAFE TO EXTEND inspection {delta} cycles - structure is healthier "
                      f"than the calendar assumes (deferred downtime)")
        return {
            "basis": "condition-based",
            "action": action,
            "next_check_cycles": cbm_next,
            "vs_calendar_cycles": delta,
        }
    return {
        "basis": "calendar",
        "action": "No growth trend yet — inspect at next scheduled check",
        "next_check_cycles": calendar_next,
        "vs_calendar_cycles": 0,
    }


def tail_state(tail: str, findings: list[dict]) -> dict:
    """Current structural state of one aircraft, computed from its findings."""
    opens = _open_defects(findings)
    worst = max(opens, key=_severity_ratio) if opens else None
    health = round(100 * (1 - _severity_ratio(worst))) if worst else 100
    grounded = any(f["grade"] == "beyond-limit" for f in opens)
    ruls = [f["cycles_to_limit"] for f in opens if f.get("cycles_to_limit") is not None]
    rul = min(ruls) if ruls else None
    current_cycles = max((f["cycles"] or 0 for f in findings), default=0)
    rec = maintenance_recommendation(current_cycles, rul, grounded,
                                     worst["grade"] if worst else "")
    return {
        "tail": tail,
        "health": health,
        "grounded": grounded,
        "open_defects": len(opens),
        "worst": worst,
        "rul_cycles": rul,
        "current_cycles": current_cycles,
        **rec,
    }


def fleet_summary() -> list[dict]:
    """Every tail as a twin state, ranked worst-health-first (the fleet risk board)."""
    by_tail: dict[str, list[dict]] = {}
    for r in db.all_findings():
        by_tail.setdefault(r["tail"], []).append(r)
    states = [tail_state(t, fs) for t, fs in by_tail.items()]
    states.sort(key=lambda s: (not s["grounded"], s["health"]))  # grounded, then sickest
    return states


def _demo() -> None:
    """Self-check: the twin math must classify a fleet correctly (no DB needed)."""
    # crack, ATA 53 -> SRM limit 12 mm (from data/srm_limits.csv)
    healthy = [{"tail": "T1", "location": "s14", "defect_type": "crack", "ata_zone": "53",
                "size_mm": 3.0, "grade": "major", "cycles": 12000, "cycles_to_limit": 40000}]
    urgent = [{"tail": "T2", "location": "s14", "defect_type": "crack", "ata_zone": "53",
               "size_mm": 10.0, "grade": "critical", "cycles": 12000, "cycles_to_limit": 1000}]
    grounded = [{"tail": "T3", "location": "s14", "defect_type": "crack", "ata_zone": "53",
                 "size_mm": 13.0, "grade": "beyond-limit", "cycles": 12000, "cycles_to_limit": 0}]

    h = tail_state("T1", healthy)
    assert h["health"] == 75, h["health"]                    # 3/12 -> 25% consumed
    assert h["vs_calendar_cycles"] > 0, "healthy jet should be safe to EXTEND"

    u = tail_state("T2", urgent)
    assert u["basis"] == "condition-based" and u["vs_calendar_cycles"] < 0, "urgent -> PULL FORWARD"

    g = tail_state("T3", grounded)
    assert g["grounded"] and g["health"] == 0 and g["basis"] == "grounded", g

    # severity gate: a critical defect with an optimistic RUL must NOT be extended
    crit_rosy = [{"tail": "T4", "location": "s14", "defect_type": "crack", "ata_zone": "53",
                  "size_mm": 8.0, "grade": "critical", "cycles": 12000, "cycles_to_limit": 52000}]
    c = tail_state("T4", crit_rosy)
    assert c["vs_calendar_cycles"] == 0 and "no extension" in c["action"], c

    print("twin self-check OK  |  health:", h["health"], u["health"], g["health"], c["health"],
          " basis:", h["basis"], u["basis"], g["basis"], c["basis"])


if __name__ == "__main__":
    _demo()
