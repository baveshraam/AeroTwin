"""AeroTwin-Edge — the unbroken L0 -> L3 inspection chain.

One panel, one defect, one tail, fully offline. This is the 3-minute demo:

    crack on panel
      -> L0  DETECT + SIZE + GRADE   "CRITICAL crack 8.0 mm, ATA 53 stringer 14"
      -> L1  TWIN                    "tail VT-XYZ: was 6.0 mm, now 8.0 mm (+2.0)"
      -> L2  PROGRESSION             "crosses 12 mm SRM limit in ~N cycles"
      -> L3  AGENT                   drafts work order citing SRM 53-30-01
      -> AUDIT                       hash-chained, awaiting certifying-staff signature

Usage:
    python -m src.pipeline                 # one mock scan through the whole chain
    python -m src.pipeline --seed          # seed a 2-scan growth story for the demo
    python -m src.pipeline --image path.jpg --real   # use a trained YOLO model
"""
from __future__ import annotations

import argparse

from src.l0_detect.detect import detect_defects
from src.l0_detect.grade import grade_defect
from src.l0_detect.sizing import mm_per_pixel, measure_mm
from src.l1_twin import db
from src.l1_twin.twin import tail_state
from src.l2_progress.paris import empirical_cycles_to_limit, paris_cycles_to_limit
from src.l3_agent import audit
from src.l3_agent.agent import draft_work_order

DEFAULT_SCALE_MM_PER_PX = 0.025  # fallback when no ArUco marker is in the frame


def _scale_for(image_path: str | None) -> float:
    """Real mm/px from an ArUco marker if the image has one, else the fallback."""
    if image_path:
        try:
            import cv2
            img = cv2.imread(image_path)
            if img is not None:
                s = mm_per_pixel(img)
                if s:
                    return s
        except Exception:
            pass
    return DEFAULT_SCALE_MM_PER_PX


def run_scan(
    image_path: str | None = None,
    *,
    tail: str = "VT-XYZ",
    ata_zone: str = "53",
    location: str = "stringer 14",
    scan_date: str = "2026-07-01",
    cycles: int = 12000,
    mock: bool = True,
    quiet: bool = False,
    detections: list[dict] | None = None,
) -> dict:
    db.init()

    # ---- L0: detect + size + grade ----
    if detections is None:
        detections = detect_defects(image_path, mock=mock)
    if not detections:
        if not quiet:
            print("[L0] no defects detected")
        return {"status": "NO_DEFECT"}
    d = detections[0]
    scale = _scale_for(image_path)
    size_mm = measure_mm(d["mask_length_px"], scale)
    grade = grade_defect(d["defect_type"], ata_zone, size_mm)

    # ---- L0b: zero-label anomaly branch — flags never-seen damage the detector wasn't
    # trained on. Only on real imagery, only if a normal-skin memory bank has been fit. ----
    anomaly = None
    if image_path and not mock:
        try:
            from src.l0_detect.anomaly import PatchCore, BANK_PATH
            if BANK_PATH.exists():
                a = PatchCore.load().score(image_path)
                anomaly = {"score": round(a["score"], 3), "is_anomaly": a["is_anomaly"]}
        except Exception:
            anomaly = None

    # ---- L1: twin history, then persist ----
    hist = db.history(tail, location, d["defect_type"])

    # ---- L2: progression ----
    ctl = None
    if hist:
        prev = hist[-1]
        ctl = empirical_cycles_to_limit(
            prev["size_mm"], size_mm, cycles - (prev["cycles"] or 0), grade["limit_mm"]
        )
    if ctl is None and grade["limit_mm"]:
        ctl = paris_cycles_to_limit(size_mm, grade["limit_mm"])
    progression = (
        f"crosses {grade['limit_mm']} mm SRM limit in ~{ctl} cycles"
        if ctl else "insufficient data for progression"
    )

    finding = {
        "tail": tail, "ata_zone": ata_zone, "location": location,
        "defect_type": d["defect_type"], "size_mm": size_mm,
        "grade": grade["grade"], "airworthiness": grade["airworthiness"],
        "scan_date": scan_date, "cycles": cycles, "cycles_to_limit": ctl,
        "confidence": d["confidence"], "model_version": "mock-v0" if mock else "yolov8-seg",
    }
    db.add_finding(finding)

    # ---- L1b: twin state — what does this do to the aircraft's health & schedule? ----
    state = tail_state(tail, db.findings_for_tail(tail))

    # ---- L3: agent drafts work order + audit ----
    work_order = draft_work_order(finding, grade, progression)
    entry = audit.append({"finding": finding, "work_order": work_order})

    if not quiet:
        print(f"[L0] {grade['grade'].upper()} {d['defect_type']} {size_mm} mm  "
              f"ATA {ata_zone} {location}  (conf {d['confidence']:.2f}, scale {scale:.4f} mm/px)")
        if hist:
            prev = hist[-1]
            delta = round(size_mm - prev["size_mm"], 1)
            print(f"[L1] tail {tail}: was {prev['size_mm']} mm @ {prev['cycles']} cyc "
                  f"-> now {size_mm} mm ({'+' if delta >= 0 else ''}{delta})")
        else:
            print(f"[L1] tail {tail}: first recorded scan of this defect")
        if anomaly is not None:
            flag = "ANOMALY" if anomaly["is_anomaly"] else "nominal"
            print(f"[L0b] zero-label anomaly: {flag} (score {anomaly['score']})")
        print(f"[L2] {progression}")
        print(f"[TWIN] {tail} health {state['health']}/100 "
              f"({state['open_defects']} open) -> {state['basis'].upper()}: {state['action']}")
        print(f"[L3] {work_order['status']}: {work_order.get('summary', work_order.get('reason',''))}")
        if work_order.get("citation"):
            print(f"     cites {work_order['citation']} - {work_order['recommended_action']}")
        print(f"[AUDIT] chain hash {entry['hash'][:16]}...  verified={audit.verify()}  "
              f"(awaiting certifying-staff signature)")

    return {"finding": finding, "grade": grade, "twin": state,
            "work_order": work_order, "audit": entry, "anomaly": anomaly}


def seed_demo() -> None:
    """Seed a small FLEET so the twin has something to rank — the demo money shot.

    Four tails, four stories: a growing crack (pull-forward), a healthy jet (safe to
    extend), a corrosion patch near limit, and one beyond-limit (grounded).
    """
    print("Seeding demo fleet (4 tails) ...\n")
    db.DB.unlink(missing_ok=True)  # ponytail: --seed is a demo reset; start from a clean twin
    audit.LOG.unlink(missing_ok=True)
    # VT-AXB — the hero growth story: crack 6.0 -> 8.0 mm across two C-checks.
    _seed_scan("VT-AXB", "crack", "53", "stringer 14", mask_px=240.0, cycles=9800, date="2026-04-12")
    _seed_scan("VT-AXB", "crack", "53", "stringer 14", mask_px=320.0, cycles=12000, date="2026-07-01")
    # VT-AXC — healthy: a small 3.0 mm crack, plenty of life -> safe to extend.
    _seed_scan("VT-AXC", "crack", "53", "stringer 09", mask_px=100.0, cycles=8000, date="2026-05-02")
    _seed_scan("VT-AXC", "crack", "53", "stringer 09", mask_px=120.0, cycles=12000, date="2026-07-01")
    # VT-AXD — corrosion patch marching toward its 8.0 mm limit.
    _seed_scan("VT-AXD", "corrosion", "53", "lap joint 22", mask_px=240.0, cycles=9000, date="2026-04-20")
    _seed_scan("VT-AXD", "corrosion", "53", "lap joint 22", mask_px=280.0, cycles=12000, date="2026-07-01")
    # VT-AXE — beyond limit: 13.0 mm crack past the 12 mm SRM limit -> grounded.
    _seed_scan("VT-AXE", "crack", "53", "stringer 14", mask_px=520.0, cycles=12000, date="2026-07-01")

    from src.l1_twin.planner import fleet_plan, print_plan
    print()
    print_plan(fleet_plan())
    print("\nDone. Start the dashboard:  uvicorn src.l1_twin.app:app --port 8000")


def _seed_scan(tail: str, defect: str, ata: str, location: str,
               mask_px: float, cycles: int, date: str) -> None:
    # Inject an explicit detection of a known size so the growth stories are stable.
    run_scan(
        tail=tail, ata_zone=ata, location=location, scan_date=date, cycles=cycles, mock=True,
        detections=[{"defect_type": defect, "mask_length_px": mask_px, "confidence": 0.84}],
        quiet=True,
    )
    print(f"  seeded {tail}: {defect} @ ATA {ata} {location}, {date}, {cycles} cyc")


def main() -> None:
    ap = argparse.ArgumentParser(description="AeroTwin-Edge inspection chain")
    ap.add_argument("--image", default=None, help="path to a panel image")
    ap.add_argument("--real", action="store_true", help="use trained YOLO model instead of mock")
    ap.add_argument("--seed", action="store_true", help="seed a 2-scan demo growth story")
    ap.add_argument("--tail", default="VT-XYZ")
    ap.add_argument("--cycles", type=int, default=12000)
    args = ap.parse_args()

    if args.seed:
        seed_demo()
        return
    run_scan(image_path=args.image, tail=args.tail, cycles=args.cycles, mock=not args.real)


if __name__ == "__main__":
    main()
