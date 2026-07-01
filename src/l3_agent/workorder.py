"""L3 — Work-order lifecycle + tamper-evident evidence pack.

Closes the loop the draft-only agent left open. A work order moves DRAFT -> SIGNED ->
CLOSED, and EVERY transition is appended to the hash chain (audit.py), so the record of
who signed what, when, is itself tamper-evident. Illegal transitions (sign twice, close
before sign) are refused — the chain only ever reflects a valid lifecycle.

evidence_pdf() renders the whole chain into a regulator-grade PDF, stamped VERIFIED or
BROKEN from a live re-walk of the chain. The PDF is written by hand (no dependency) so it
works offline on the Pi — a minimal Courier text document, not a rich layout.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from src.l3_agent import audit

STATUSES = ("DRAFT", "SIGNED", "CLOSED")
_NEXT = {"DRAFT": "SIGNED", "SIGNED": "CLOSED"}


def wo_id(finding: dict) -> str:
    key = f"{finding['tail']}|{finding['ata_zone']}|{finding['location']}|{finding['defect_type']}"
    return "WO-" + hashlib.sha1(key.encode()).hexdigest()[:8].upper()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _emit(wid: str, status: str, extra: dict) -> dict:
    entry = audit.append({"event": "work_order", "wo_id": wid, "status": status,
                          "ts": _now(), **extra})
    return {"wo_id": wid, "status": status, "hash": entry["hash"]}


def open_wo(finding: dict, work_order: dict) -> dict:
    """Create a DRAFT work order on the chain."""
    return _emit(wo_id(finding), "DRAFT", {"work_order": work_order})


def sign_wo(wid: str, signer: str, role: str = "Part-145 certifying staff") -> dict:
    """Certifying-staff signature. Refused unless the order is currently DRAFT."""
    cur = lifecycle().get(wid, {}).get("status")
    if cur != "DRAFT":
        return {"status": "REFUSED", "reason": f"cannot sign a {cur or 'nonexistent'} order", "wo_id": wid}
    return _emit(wid, "SIGNED", {"signer": signer, "role": role})


def close_wo(wid: str, note: str = "repair embodied; returned to service") -> dict:
    """Close out. Refused unless the order is currently SIGNED."""
    cur = lifecycle().get(wid, {}).get("status")
    if cur != "SIGNED":
        return {"status": "REFUSED", "reason": f"cannot close a {cur or 'nonexistent'} order", "wo_id": wid}
    return _emit(wid, "CLOSED", {"note": note})


def lifecycle() -> dict:
    """Replay the chain -> current status + transition history per work order."""
    import json
    out: dict[str, dict] = {}
    if not audit.LOG.exists():
        return out
    for line in audit.LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        p = json.loads(line).get("payload", {})
        if p.get("event") != "work_order":
            continue
        wid = p["wo_id"]
        wo = out.setdefault(wid, {"wo_id": wid, "status": None, "history": []})
        wo["status"] = p["status"]
        wo["history"].append({"status": p["status"], "ts": p.get("ts"),
                              "signer": p.get("signer"), "note": p.get("note")})
    return out


# ---------- tamper-evident PDF (hand-rolled, no dependency) ----------
def _pdf_bytes(pages: list[list[str]]) -> bytes:
    objs: dict[int, str] = {
        1: "<</Type/Catalog/Pages 2 0 R>>",
        3: "<</Type/Font/Subtype/Type1/BaseFont/Courier>>",
    }
    page_ids = [4 + 2 * i for i in range(len(pages))]
    objs[2] = f"<</Type/Pages/Kids[{' '.join(f'{p} 0 R' for p in page_ids)}]/Count {len(pages)}>>"
    for i, lines in enumerate(pages):
        pid, cid = 4 + 2 * i, 5 + 2 * i
        objs[pid] = (f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                     f"/Resources<</Font<</F1 3 0 R>>>>/Contents {cid} 0 R>>")
        s = ["BT", "/F1 9 Tf", "40 760 Td", "11 TL"]
        for j, ln in enumerate(lines):
            esc = ln.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            s.append("T*" if j else "")
            s.append(f"({esc}) Tj")
        s.append("ET")
        stream = "\n".join(x for x in s if x)
        objs[cid] = f"<</Length {len(stream)}>>\nstream\n{stream}\nendstream"

    out = b"%PDF-1.4\n"
    offsets: dict[int, int] = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n{objs[oid]}\nendobj\n".encode("latin-1")
    n = max(objs) + 1
    xref_pos = len(out)
    out += f"xref\n0 {n}\n".encode() + b"0000000000 65535 f \n"
    for oid in range(1, n):
        out += f"{offsets[oid]:010d} 00000 n \n".encode()
    out += f"trailer\n<</Size {n}/Root 1 0 R>>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
    return out


def evidence_pdf() -> bytes:
    """Render the full audit chain as a tamper-evident PDF, stamped from a live re-walk."""
    import json
    verified = audit.verify()
    lines = ["AeroTwin-Edge  |  STRUCTURAL MAINTENANCE EVIDENCE PACK",
             "=" * 64,
             f"Generated : {_now()}",
             f"Chain     : {'VERIFIED - no entry altered' if verified else '*** BROKEN - TAMPERING DETECTED ***'}",
             "Note      : illustrative POC data; certifying staff signature governs.",
             "=" * 64, ""]
    entries = []
    if audit.LOG.exists():
        entries = [json.loads(l) for l in audit.LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    for i, e in enumerate(entries):
        p = e["payload"]
        summ = (f"{p.get('event','finding')} {p.get('status','')} {p.get('wo_id','')}").strip()
        if p.get("event") != "work_order" and "finding" in p:
            f = p["finding"]
            summ = f"finding {f['tail']} ATA{f['ata_zone']} {f['location']} {f['size_mm']}mm {f['grade']}"
        lines += [f"#{i:03d}  hash {e['hash'][:16]}..  prev {e['prev'][:12]}..",
                  f"      {summ}",
                  f"      signer: {p.get('signer','-')}  ts: {p.get('ts','-')}"]
    pages = [lines[k:k + 62] for k in range(0, max(len(lines), 1), 62)]
    return _pdf_bytes(pages)


def _demo() -> None:
    """Self-check: lifecycle guards + a valid, verifiable evidence PDF (no real-log writes)."""
    import tempfile
    from pathlib import Path
    orig = audit.LOG
    audit.LOG = Path(tempfile.mkdtemp()) / "audit.jsonl"
    try:
        f = {"tail": "VT-AXB", "ata_zone": "53", "location": "stringer 14",
             "defect_type": "crack", "size_mm": 8.0, "grade": "critical"}
        wid = open_wo(f, {"status": "DRAFT_FOR_SIGNOFF"})["wo_id"]
        assert close_wo(wid)["status"] == "REFUSED", "must not close before sign"
        assert sign_wo(wid, "A. Rao (LWTR-12345)")["status"] == "SIGNED"
        assert sign_wo(wid, "again")["status"] == "REFUSED", "must not sign twice"
        assert close_wo(wid)["status"] == "CLOSED"
        lc = lifecycle()[wid]
        assert lc["status"] == "CLOSED" and len(lc["history"]) == 3, lc
        pdf = evidence_pdf()
        assert pdf.startswith(b"%PDF") and pdf.rstrip().endswith(b"%%EOF"), "invalid PDF"
        assert audit.verify(), "chain must verify"
        print(f"workorder self-check OK  |  {wid} DRAFT->SIGNED->CLOSED, "
              f"evidence PDF {len(pdf)} bytes, chain verified")
    finally:
        audit.LOG = orig


if __name__ == "__main__":
    _demo()
