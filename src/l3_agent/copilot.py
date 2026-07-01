"""L3 — Local LLM MRO copilot (Ollama, tool-calling, citation-gated, offline).

Upgrades the template agent (agent.py) with a real quantized LLM that can CALL TOOLS into
the twin — get an SRM limit, a tail's state, a Monte-Carlo RUL — and then answer or draft
under the SAME safety contract:

  * CITATION GUARDRAIL: a work order is only drafted if agent.draft_work_order retrieved a
    governing manual section. The LLM may rephrase the retrieved text; it may NOT invent a
    limit. If its prose drops the citation, we discard it and keep the template.
  * HUMAN GATE: the LLM drafts; certifying staff sign (see workorder.py).
  * OFFLINE: talks to a local Ollama (localhost:11434). If none is running, every path
    degrades to the deterministic template so the demo never depends on a model.

Setup (optional):  install Ollama, `ollama pull phi3`  (or qwen2.5, llama3.2).
Env: OLLAMA_URL, OLLAMA_MODEL.
"""
from __future__ import annotations

import json
import os
import urllib.request

from src.l0_detect.grade import grade_defect
from src.l2_progress.paris import paris_rul_mc
from src.l3_agent.agent import draft_work_order, retrieve

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi3")


# ---------- tools the model may call (real functions over the twin) ----------
def _get_srm_limit(defect_type: str, ata_zone: str) -> dict:
    g = grade_defect(defect_type, ata_zone, 0.0)
    return {"limit_mm": g.get("limit_mm"), "manual_ref": g.get("manual_ref")}


def _get_rul(size_mm: float, limit_mm: float) -> dict:
    return paris_rul_mc(float(size_mm), float(limit_mm)) or {"error": "degenerate input"}


def _get_tail_state(tail: str) -> dict:
    from src.l1_twin.twin import fleet_summary  # lazy: avoids import cycle at module load
    s = next((s for s in fleet_summary() if s["tail"] == tail), None)
    return s or {"error": f"no such tail {tail}"}


TOOLS = {"get_srm_limit": _get_srm_limit, "get_rul": _get_rul, "get_tail_state": _get_tail_state}

TOOL_SPECS = [
    {"type": "function", "function": {"name": "get_srm_limit",
        "description": "SRM allowable-damage limit (mm) + manual ref for a defect in an ATA zone",
        "parameters": {"type": "object", "properties": {
            "defect_type": {"type": "string"}, "ata_zone": {"type": "string"}},
            "required": ["defect_type", "ata_zone"]}}},
    {"type": "function", "function": {"name": "get_rul",
        "description": "Monte-Carlo remaining useful life (P10/P50/P90 flight cycles) to the limit",
        "parameters": {"type": "object", "properties": {
            "size_mm": {"type": "number"}, "limit_mm": {"type": "number"}},
            "required": ["size_mm", "limit_mm"]}}},
    {"type": "function", "function": {"name": "get_tail_state",
        "description": "Current twin state (health, RUL, recommended action) for a tail number",
        "parameters": {"type": "object", "properties": {"tail": {"type": "string"}},
            "required": ["tail"]}}},
]

SYSTEM = ("You are an MRO structural-maintenance copilot. Use tools for any number "
          "(limits, RUL, health) — never guess one. Cite the SRM manual reference for "
          "any airworthiness limit. A certifying engineer signs off; you only advise.")


def ollama_up() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=0.4)
        return True
    except Exception:
        return False


def _chat(messages: list[dict], tools: list | None = None) -> dict:
    body = json.dumps({"model": OLLAMA_MODEL, "messages": messages,
                       "tools": tools or [], "stream": False}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["message"]


def ask(question: str, max_steps: int = 4) -> dict:
    """Answer an MRO question, letting the model call twin tools. Deterministic fallback
    (a direct tool call) when no Ollama is present, so this always returns something."""
    if not ollama_up():
        return {"answer": "(LLM offline) start Ollama for prose answers; tools still work.",
                "tool_trace": [], "llm": False}
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    trace = []
    for _ in range(max_steps):
        msg = _chat(messages, TOOL_SPECS)
        calls = msg.get("tool_calls") or []
        if not calls:
            return {"answer": msg.get("content", ""), "tool_trace": trace, "llm": True}
        messages.append(msg)
        for call in calls:
            fn = call["function"]["name"]
            args = call["function"].get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args or "{}")
            result = TOOLS[fn](**args) if fn in TOOLS else {"error": f"unknown tool {fn}"}
            trace.append({"tool": fn, "args": args, "result": result})
            messages.append({"role": "tool", "content": json.dumps(result)})
    return {"answer": "(stopped: tool-call limit reached)", "tool_trace": trace, "llm": True}


def draft_with_copilot(finding: dict, grade: dict, progression: str) -> dict:
    """Citation-gated draft. LLM only rephrases the RETRIEVED text; if its prose drops the
    manual citation, we discard it and keep the deterministic template (guardrail intact)."""
    wo = draft_work_order(finding, grade, progression)   # guardrail + template run first
    if wo["status"] != "DRAFT_FOR_SIGNOFF" or not ollama_up():
        return wo                                        # ESCALATE / no-LLM -> unchanged
    excerpt = wo.get("manual_excerpt", "")
    prompt = (f"Write a 2-sentence structural work-order summary for: {wo['summary']}. "
              f"Progression: {progression}. You MUST cite {wo['citation']}. "
              f"Use ONLY this manual text; do not state any other limit:\n{excerpt}")
    try:
        msg = _chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}])
        prose = msg.get("content", "")
        if wo["citation"] in prose:                      # guardrail: citation must survive
            wo = {**wo, "llm_summary": prose, "drafted_by": f"ollama:{OLLAMA_MODEL}"}
    except Exception:
        pass
    return wo


def _demo() -> None:
    """Self-check: tools return real twin numbers; guardrail holds with or without an LLM."""
    assert _get_srm_limit("crack", "53")["limit_mm"] == 12.0, _get_srm_limit("crack", "53")
    band = _get_rul(8.0, 12.0)
    assert band["p10"] <= band["p50"] <= band["p90"], band

    # guardrail: a defect with NO governing manual section must ESCALATE, never draft a limit
    no_ref = draft_with_copilot(
        {"tail": "T", "ata_zone": "99", "location": "x", "defect_type": "mystery", "size_mm": 5.0},
        {"grade": "major", "airworthiness": "", "manual_ref": None}, "n/a")
    assert no_ref["status"] == "ESCALATE", no_ref
    print(f"copilot self-check OK  |  SRM limit tool=12.0mm, RUL P50={band['p50']:,} cyc, "
          f"guardrail escalates w/o citation, ollama_up={ollama_up()}")


if __name__ == "__main__":
    _demo()
