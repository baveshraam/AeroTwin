"""L1 — Prescriptive fleet planner & rupee ledger (predict -> PRESCRIBE -> PRICE).

The twin brain (twin.py) tells us each aircraft's condition. This turns that into the
decision a maintenance planner is actually paid to make: given a limited number of
hangar slots this planning window, WHICH tails do we service, which do we safely
defer, and what is each choice worth in rupees versus the blind calendar?

This is the layer that makes it a digital-twin PLATFORM, not a health dashboard:
  predict (RUL)  ->  prescribe (an optimised, capacity-constrained plan)  ->  price (Rs).

All money constants are ILLUSTRATIVE and live in ONE place below so a judge can see
exactly where every rupee comes from. Calibrate per operator before quoting a slide.
"""
from __future__ import annotations

from src.l1_twin.twin import CALENDAR_INTERVAL_CYCLES, fleet_summary

# --- ILLUSTRATIVE economics (calibrate per operator; one source of truth) ---------
DOWNTIME_COST_PER_CHECK = 1_200_000   # Rs: ground time + labour for one scheduled structural check
AOG_EVENT_COST          = 20_000_000  # Rs: an unplanned AOG grounding (~one narrow-body AOG day, ~2 Cr)
HANGAR_CAPACITY         = 3           # aircraft that fit a service window (the real constraint planners fight)


def inr(n: float) -> str:
    """Human rupee formatting (console-safe; the UI can swap 'Rs' for the symbol)."""
    if n >= 1e7:
        return f"Rs {n / 1e7:.2f} Cr"
    if n >= 1e5:
        return f"Rs {n / 1e5:.1f} L"
    return f"Rs {n:,.0f}"


def _priority(s: dict) -> tuple:
    """Service order: grounded first, then sickest, then soonest to hit its limit."""
    return (not s["grounded"], s["health"],
            s["rul_cycles"] if s["rul_cycles"] is not None else 10 ** 9)


def _classify(s: dict) -> tuple[str, bool, int]:
    """(action, needs_service_this_window, avoidable_AOG_risk_Rs) for one tail."""
    if s["grounded"]:
        return "SERVICE NOW - grounded, beyond limit", True, AOG_EVENT_COST
    if "PULL" in s["action"]:
        return "SERVICE THIS WINDOW - growth outruns the calendar", True, AOG_EVENT_COST
    if "EXTEND" in s["action"]:
        return "SAFE TO DEFER - healthier than the calendar assumes", False, 0
    return "SERVICE AT SCHEDULED CHECK", True, 0  # critical HOLD / no-trend


def fleet_plan(states: list[dict] | None = None, capacity: int = HANGAR_CAPACITY) -> dict:
    """Turn per-tail twin states into a priced, capacity-constrained service plan.

    Compared against the calendar baseline (which services EVERY tail every window):
      - deferring a healthy tail recovers one check's downtime cost,
      - servicing a fast grower / grounded tail in time avoids its AOG event cost,
      - if more tails need service than hangar slots, the overflow is QUEUED and its
        risk is carried (made explicit) instead of silently ignored.
    """
    states = states if states is not None else fleet_summary()
    ranked = sorted(states, key=_priority)

    plan, downtime_recovered, aog_avoided, aog_carried, serviced = [], 0, 0, 0, 0
    for s in ranked:
        action, needs, risk = _classify(s)
        if not needs:
            slot = "deferred"
            downtime_recovered += DOWNTIME_COST_PER_CHECK
        elif serviced < capacity:
            slot = "scheduled"
            serviced += 1
            aog_avoided += risk
        else:
            slot = "QUEUED - no slot"
            aog_carried += risk
        plan.append({
            "tail": s["tail"], "health": s["health"], "rul_cycles": s["rul_cycles"],
            "action": action, "slot": slot, "risk": risk,
        })

    deferred = sum(1 for p in plan if p["slot"] == "deferred")
    ledger = {
        "window_cycles": CALENDAR_INTERVAL_CYCLES,
        "capacity": capacity,
        "calendar_checks": len(states),     # calendar services everyone, every window
        "twin_serviced": serviced,
        "safely_deferred": deferred,
        "queued": sum(1 for p in plan if p["slot"].startswith("QUEUED")),
        "downtime_recovered": downtime_recovered,
        "aog_risk_avoided": aog_avoided,
        "aog_risk_carried": aog_carried,     # honest: shortfall when at-risk > capacity
        "net_value": downtime_recovered + aog_avoided,
    }
    return {"plan": plan, "ledger": ledger}


def scenario_defer(tail: str, states: list[dict] | None = None) -> dict:
    """What-if: what does deferring one at-risk tail cost? (drives the 'run the twin forward' story)."""
    states = states if states is not None else fleet_summary()
    base = fleet_plan(states)
    forced = [dict(s, action="SAFE TO EXTEND (forced defer)", grounded=False)
              if s["tail"] == tail else s for s in states]
    what_if = fleet_plan(forced)
    return {
        "tail": tail,
        "added_risk": base["ledger"]["aog_risk_avoided"] - what_if["ledger"]["aog_risk_avoided"],
        "base_net": base["ledger"]["net_value"],
        "whatif_net": what_if["ledger"]["net_value"],
    }


def scenario_add_capacity(states: list[dict] | None = None, extra: int = 1) -> dict:
    """What-if: add `extra` hangar slots — how much carried AOG risk does it release?"""
    states = states if states is not None else fleet_summary()
    base, more = fleet_plan(states), fleet_plan(states, capacity=HANGAR_CAPACITY + extra)
    return {
        "extra_slots": extra,
        "base_net": base["ledger"]["net_value"],
        "whatif_net": more["ledger"]["net_value"],
        "risk_released": base["ledger"]["aog_risk_carried"] - more["ledger"]["aog_risk_carried"],
    }


# --- spares: RUL -> which repair kit to pre-stage, and by when (ILLUSTRATIVE) ----------
KIT = {
    ("crack", "53"): ("Fuselage skin doubler + fastener kit", 1500),
    ("corrosion", "53"): ("Corrosion blend-out + primer/sealant kit", 800),
}
DEFAULT_KIT = ("General structural repair kit", 1200)  # (kit name, procurement lead-time cycles)


def spares_forecast(states: list[dict] | None = None, horizon_cycles: int = 8000) -> dict:
    """Turn conservative RUL (P10) into a pre-staging plan: for every tail that will need
    a repair within the horizon, which kit, and the cycle by which it must be on order so
    it lands before the aircraft does. Ties the money story to logistics.
    """
    states = states if states is not None else fleet_summary()
    orders = []
    for s in states:
        w = s.get("worst")
        if not w:
            continue
        rul = 0 if s.get("grounded") else (s.get("rul_band") or {}).get("p10")
        if rul is None or rul > horizon_cycles:
            continue  # outside the planning horizon — don't tie up inventory
        kit, lead = KIT.get((w["defect_type"], w["ata_zone"]), DEFAULT_KIT)
        orders.append({
            "tail": s["tail"], "kit": kit, "defect": w["defect_type"], "ata_zone": w["ata_zone"],
            "rul_p10": rul, "lead_time_cycles": lead, "grounded": s.get("grounded", False),
            "order_by_cycle": s.get("current_cycles", 0) + max(0, rul - lead),
        })
    orders.sort(key=lambda o: o["order_by_cycle"])
    qty: dict[str, int] = {}
    for o in orders:
        qty[o["kit"]] = qty.get(o["kit"], 0) + 1
    return {"horizon_cycles": horizon_cycles, "orders": orders,
            "kits": [{"kit": k, "qty": q} for k, q in qty.items()]}


def print_plan(res: dict) -> None:
    lg = res["ledger"]
    print(f"FLEET PLAN (window {lg['window_cycles']} cyc, hangar capacity {lg['capacity']}):")
    for p in res["plan"]:
        r = f"  risk {inr(p['risk'])}" if p["risk"] else ""
        print(f"  {p['tail']:8} health {p['health']:3}/100  [{p['slot']:14}] {p['action']}{r}")
    print(f"\nLEDGER vs blind calendar (services all {lg['calendar_checks']} tails):")
    print(f"  service {lg['twin_serviced']}, safely defer {lg['safely_deferred']}, queued {lg['queued']}")
    print(f"  downtime recovered : {inr(lg['downtime_recovered'])}")
    print(f"  AOG risk avoided   : {inr(lg['aog_risk_avoided'])}")
    if lg["aog_risk_carried"]:
        print(f"  AOG risk CARRIED   : {inr(lg['aog_risk_carried'])}  (add hangar capacity to close)")
    print(f"  NET VALUE / window : {inr(lg['net_value'])}")


def _demo() -> None:
    """Self-check: the plan must triage under capacity and price the calls (no DB)."""
    states = [
        {"tail": "G", "health": 0, "grounded": True, "rul_cycles": 0, "action": "GROUND"},
        {"tail": "P1", "health": 12, "grounded": False, "rul_cycles": 3000,
         "action": "PULL INSPECTION FORWARD 4500 cycles"},
        {"tail": "P2", "health": 33, "grounded": False, "rul_cycles": 4400,
         "action": "PULL INSPECTION FORWARD 3800 cycles"},
        {"tail": "H", "health": 75, "grounded": False, "rul_cycles": 72000,
         "action": "SAFE TO EXTEND inspection 30000 cycles"},
    ]
    res = fleet_plan(states, capacity=2)
    lg = res["ledger"]
    # grounded G and worst pull-forward P1 get the 2 slots; P2 is queued; H deferred
    assert res["plan"][0]["tail"] == "G" and res["plan"][0]["slot"] == "scheduled", res["plan"][0]
    assert lg["safely_deferred"] == 1 and lg["queued"] == 1, lg
    assert lg["downtime_recovered"] == DOWNTIME_COST_PER_CHECK, lg
    assert lg["aog_risk_avoided"] == 2 * AOG_EVENT_COST, lg     # G + P1 serviced in time
    assert lg["aog_risk_carried"] == AOG_EVENT_COST, lg         # P2 queued

    # capacity 3 clears the queue -> more AOG avoided, none carried
    res3 = fleet_plan(states, capacity=3)
    assert res3["ledger"]["queued"] == 0 and res3["ledger"]["aog_risk_carried"] == 0
    assert res3["ledger"]["aog_risk_avoided"] == 3 * AOG_EVENT_COST

    # add-capacity what-if: with 4 at-risk tails vs default capacity 3, one is queued;
    # a 4th slot releases exactly one AOG event of carried risk.
    four_atrisk = states + [{"tail": "P3", "health": 20, "grounded": False, "rul_cycles": 4000,
                             "action": "PULL INSPECTION FORWARD 4000 cycles"}]
    add = scenario_add_capacity(four_atrisk, extra=1)
    assert add["risk_released"] == AOG_EVENT_COST, add

    # spares: grounded orders immediately; a tail beyond the horizon is excluded
    sp_states = [
        {"tail": "G", "grounded": True, "current_cycles": 12000, "worst": {"defect_type": "crack", "ata_zone": "53"}, "rul_band": {"p10": 0}},
        {"tail": "H", "grounded": False, "current_cycles": 12000, "worst": {"defect_type": "crack", "ata_zone": "53"}, "rul_band": {"p10": 50000}},
    ]
    sp = spares_forecast(sp_states, horizon_cycles=8000)
    assert len(sp["orders"]) == 1 and sp["orders"][0]["tail"] == "G", sp   # H is out of horizon
    assert sp["orders"][0]["order_by_cycle"] == 12000, sp                  # grounded -> order now

    print("planner self-check OK  |  cap2 net:", inr(lg["net_value"]),
          " carried:", inr(lg["aog_risk_carried"]),
          " | +1 slot releases", inr(add["risk_released"]),
          " | spares orders:", len(sp["orders"]))
    print()
    print_plan(res3)


if __name__ == "__main__":
    _demo()
