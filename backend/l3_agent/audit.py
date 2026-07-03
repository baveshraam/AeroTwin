"""L3 — Tamper-evident audit trail (hash chain).

Every airworthiness-relevant decision is appended to an append-only, hash-chained
log. Each entry's hash covers the previous hash + the entry body, so any edit to a
past entry breaks the chain. This is the 'learning assurance / audit' evidence that
regulated aerospace demands — a security control, not just paperwork.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

LOG = Path(__file__).resolve().parents[2] / "data" / "audit_log.jsonl"
GENESIS = "0" * 64


def _hash(prev_hash: str, body: str) -> str:
    return hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()


def last_hash() -> str:
    if not LOG.exists():
        return GENESIS
    prev = GENESIS
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            prev = json.loads(line)["hash"]
    return prev


def append(payload: dict) -> dict:
    """Append a payload to the chain and return the new entry."""
    LOG.parent.mkdir(parents=True, exist_ok=True)
    prev = last_hash()
    body = json.dumps(payload, sort_keys=True)
    entry = {"prev": prev, "payload": payload, "hash": _hash(prev, body)}
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def verify() -> bool:
    """Re-walk the chain and confirm no entry has been tampered with."""
    if not LOG.exists():
        return True
    prev = GENESIS
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        body = json.dumps(entry["payload"], sort_keys=True)
        if entry["prev"] != prev or entry["hash"] != _hash(prev, body):
            return False
        prev = entry["hash"]
    return True
