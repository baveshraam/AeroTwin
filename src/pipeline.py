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

from src.l0_detect.detect import WEIGHTS, detect_defects
from src.l0_detect.grade import grade_defect
from src.l0_detect.sizing import mm_per_pixel, measure_mm
from src.l1_twin import db
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
    # Honesty: the real YOLO path only runs when a model is asked for, exists, and
    # has an image. Otherwise we fall back to the mock — and label it as such, so a
    # `--real` run with no weights is never passed off as a real inference.
    used_real = (not mock) and image_path is not None and WEIGHTS.exists()
    if not mock and not used_real and detections is None and not quiet:
        why = "no image given" if image_path is None else f"no weights at {WEIGHTS}"
        print(f"[L0] --real requested but {why}; falling back to MOCK detector")
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
        "confidence": d["confidence"], "model_version": "yolov8-seg" if used_real else "mock-v0",
    }
    db.add_finding(finding)

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
        print(f"[L2] {progression}")
        print(f"[L3] {work_order['status']}: {work_order.get('summary', work_order.get('reason',''))}")
        if work_order.get("citation"):
            print(f"     cites {work_order['citation']} - {work_order['recommended_action']}")
        print(f"[AUDIT] chain hash {entry['hash'][:16]}...  verified={audit.verify()}  "
              f"(awaiting certifying-staff signature)")

    return {"finding": finding, "grade": grade, "work_order": work_order, "audit": entry}


def seed_demo() -> None:
    """Create a believable 2-scan growth story on one tail for the dashboard/demo."""
    print("Seeding demo growth story for tail VT-AXB ...\n")
    # Scan 1: earlier check, smaller crack. Force a smaller mock size via scale.
    _seed_scan(mask_px=240.0, cycles=9800, date="2026-04-12")   # ~6.0 mm
    print()
    _seed_scan(mask_px=320.0, cycles=12000, date="2026-07-01")  # ~8.0 mm
    print("\nDone. Start the dashboard:  uvicorn src.l1_twin.app:app --port 8000")


def _seed_scan(mask_px: float, cycles: int, date: str) -> None:
    # Inject an explicit detection of a known size so the two scans show growth.
    run_scan(
        tail="VT-AXB", location="stringer 14", scan_date=date, cycles=cycles, mock=True,
        detections=[{"defect_type": "crack", "mask_length_px": mask_px, "confidence": 0.84}],
    )


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
