"""L3 — Agentic MRO copilot (citation-required, human-gated).

Drafts a maintenance work order from a finding. The critical safety property is the
CITATION-REQUIRED GUARDRAIL: the agent may only state an airworthiness limit if it
can cite a manual section it actually retrieved. If retrieval returns nothing, it
REFUSES and escalates — it never free-generates a limit. A human (certifying staff)
always signs; the agent only drafts.

Today this uses lightweight keyword retrieval over a controlled manual corpus and a
template work order — no LLM needed, fully offline, deterministic and demoable. To
upgrade: embed the corpus, retrieve top-k, and have a local quantized LLM (Ollama
phi3 / qwen) write the prose under the same citation guardrail. The guardrail and
human gate stay identical.
"""
from __future__ import annotations

from pathlib import Path

CORPUS = Path(__file__).resolve().parents[2] / "data" / "manuals" / "srm_53-30.md"


def retrieve(defect_type: str, ata_zone: str) -> list[str]:
    """Tiny RAG: return manual paragraphs mentioning the defect type or ATA zone."""
    if not CORPUS.exists():
        return []
    text = CORPUS.read_text(encoding="utf-8")
    needles = (defect_type.lower(), f"ata {ata_zone}".lower(), f"{ata_zone}-".lower())
    return [p.strip() for p in text.split("\n\n") if any(n in p.lower() for n in needles)]


def draft_work_order(finding: dict, grade: dict, progression: str) -> dict:
    """Draft a work order, or escalate if no manual citation is available."""
    citations = retrieve(finding["defect_type"], finding["ata_zone"])
    manual_ref = grade.get("manual_ref")

    # CITATION-REQUIRED GUARDRAIL
    if not citations or not manual_ref:
        return {
            "status": "ESCALATE",
            "reason": "No governing manual section retrieved — refusing to draft a "
            "limit (citation-required guardrail). Routed to certifying staff.",
            "tail": finding["tail"],
        }

    return {
        "status": "DRAFT_FOR_SIGNOFF",
        "tail": finding["tail"],
        "title": f"Structural finding — ATA {finding['ata_zone']} {finding['location']}",
        "summary": (
            f"{grade['grade'].upper()} {finding['defect_type']} "
            f"{finding['size_mm']} mm at ATA {finding['ata_zone']} {finding['location']}"
        ),
        "airworthiness": grade["airworthiness"],
        "progression": progression,
        "citation": manual_ref,
        "manual_excerpt": citations[0][:500],
        "recommended_action": _action_for_grade(grade["grade"]),
        "human_gate": "Requires certifying staff (Part 145) review and signature "
        "before any return to service. Agent output is decision support only.",
    }


def _action_for_grade(grade: str) -> str:
    return {
        "minor": "Record in structural log; re-inspect at next scheduled check.",
        "major": "Raise a scheduled repair task; continue service under DTA until repair.",
        "critical": "Shorten inspection interval; embody repair before limit crossing.",
        "beyond-limit": "Ground aircraft; embody certified repair scheme before return to service.",
    }.get(grade, "Escalate to certifying staff for assessment.")
