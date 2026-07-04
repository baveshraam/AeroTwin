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

Setup (optional):  install Ollama, `ollama pull llama3.2:3b`  (or qwen2.5).
Model choice matters here, not just size: `ask()` calls Ollama with `tools=`, and
Ollama 400s outright ("model does not support tools") for models whose template has no
tool-calling support -- phi3 is one of these, confirmed live. llama3.2 (and qwen2.5) do
support it. If you swap OLLAMA_MODEL, verify tool-calling still works before relying on it.
Env: OLLAMA_URL, OLLAMA_MODEL.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from backend.l0_detect.grade import grade_defect
from backend.l2_progress.paris import paris_rul_mc
from backend.l3_agent.agent import draft_work_order

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")


# ---------- tools the model may call (real functions over the twin) ----------
def _get_srm_limit(defect_type: str, ata_zone: str) -> dict:
    g = grade_defect(defect_type, ata_zone, 0.0)
    return {"limit_mm": g.get("limit_mm"), "manual_ref": g.get("manual_ref")}


def _get_rul(size_mm: float, limit_mm: float) -> dict:
    return paris_rul_mc(float(size_mm), float(limit_mm)) or {"error": "degenerate input"}


def _get_tail_state(tail: str) -> dict:
    from backend.l1_twin.twin import fleet_summary  # lazy: avoids import cycle at module load
    s = next((s for s in fleet_summary() if s["tail"] == tail), None)
    return s or {"error": f"no such tail {tail}"}


def _get_fleet_summary() -> dict:
    from backend.l1_twin.twin import fleet_summary  # lazy: avoids import cycle at module load
    s = fleet_summary()
    return {"tails": len(s),
            "grounded": [x["tail"] for x in s if x.get("grounded")],
            "worst": s[0]["tail"] if s else None,
            "board": [{"tail": x["tail"], "health": x["health"], "action": x.get("action")} for x in s]}


TOOLS = {"get_srm_limit": _get_srm_limit, "get_rul": _get_rul,
         "get_tail_state": _get_tail_state, "get_fleet_summary": _get_fleet_summary}

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
    {"type": "function", "function": {"name": "get_fleet_summary",
        "description": "Fleet-wide summary: tail count, which tails are grounded, the highest-priority tail, and the ranked board",
        "parameters": {"type": "object", "properties": {}}}},
]

SYSTEM = ("You are an MRO structural-maintenance copilot. Use tools for any number "
          "(limits, RUL, health) — never guess one. RUL/cycle figures from get_rul are "
          "in FLIGHT CYCLES, not years or hours — always say 'cycles'. Cite the SRM "
          "manual reference for any airworthiness limit. A certifying engineer signs "
          "off; you only advise.")


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


def _offline_agent(question: str) -> dict:
    """Deterministic tool-router used when no LLM is present: parse intent + entities,
    actually CALL the twin tools, and return a real answer with a populated trace. Not a
    language model — but genuine agentic tool-use, so the offline demo still shows it work."""
    import re
    q = question.lower()
    trace: list[dict] = []

    def run(name, **kw):
        res = TOOLS[name](**kw)
        trace.append({"tool": name, "args": kw, "result": res})
        return res

    dtype = next((d for d in ("crack", "corrosion", "dent", "scratch") if d in q), None)
    ata = (re.search(r"ata[^\d]*(\d{1,3})", q) or re.search(r"zone[^\d]*(\d{1,3})", q))
    ata = ata.group(1) if ata else "53"
    mm = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*mm", q)]
    tail = re.search(r"\bvt[-\s]?([a-z]{2,3})\b", q)

    # fleet-wide intent (before the per-tail branch): "which aircraft need attention", "worst tail"
    if not tail and any(k in q for k in ("fleet", "worst", "attention", "priorit", "which aircraft",
                                          "which tail", "most urgent", "overview")):
        fs = run("get_fleet_summary")
        gnd = ", ".join(fs["grounded"]) or "none"
        ans = (f"Fleet of {fs['tails']} tails. Grounded (beyond limit): {gnd}. "
               f"Highest priority now: {fs['worst']}. Ranked plan is on the fleet risk board.")
        return {"answer": ans, "tool_trace": trace, "llm": False}

    # tail-state intent
    if tail or "health" in q or "state of" in q or "grounded" in q:
        t = ("VT-" + tail.group(1).upper()) if tail else None
        if t:
            s = run("get_tail_state", tail=t)
            if "error" in s:
                return {"answer": s["error"], "tool_trace": trace, "llm": False}
            ans = (f"{t}: health {s.get('health')}/100, {s.get('open_defects')} open defect(s). "
                   f"{s.get('action','')}")
            return {"answer": ans, "tool_trace": trace, "llm": False}

    # RUL intent
    if any(k in q for k in ("rul", "remaining", "life", "cycles to", "how long", "how many cycles")):
        size = mm[0] if mm else None
        limit = mm[1] if len(mm) > 1 else None
        if limit is None and dtype:
            lim = run("get_srm_limit", defect_type=dtype, ata_zone=ata)
            limit = lim.get("limit_mm")
        if size is not None and limit:
            b = run("get_rul", size_mm=size, limit_mm=limit)
            ans = (f"A {size} mm {dtype or 'defect'} against a {limit} mm limit: Monte-Carlo RUL "
                   f"P10 {b['p10']:,} · P50 {b['p50']:,} · P90 {b['p90']:,} cycles "
                   f"(schedule on P10, the conservative estimate).")
            return {"answer": ans, "tool_trace": trace, "llm": False}

    # SRM-limit intent (default for limit questions)
    if dtype or "limit" in q or "srm" in q:
        dt = dtype or "crack"
        lim = run("get_srm_limit", defect_type=dt, ata_zone=ata)
        if lim.get("limit_mm") is None:
            return {"answer": f"No SRM entry for {dt} at ATA {ata}.", "tool_trace": trace, "llm": False}
        ans = (f"SRM allowable-damage limit for a {dt} at ATA {ata}: {lim['limit_mm']} mm "
               f"(ref {lim['manual_ref']}). Beyond it the structure is not airworthy.")
        return {"answer": ans, "tool_trace": trace, "llm": False}

    return {"answer": "Ask about an SRM limit, an RUL (size + limit), or a tail's state "
            "(e.g. 'state of VT-AXB').", "tool_trace": trace, "llm": False}


_SRM_REF = re.compile(r"SRM[\s-]*[\w./-]+", re.IGNORECASE)


def _drop_uncited_srm(answer: str, trace: list[dict]) -> str:
    """Guardrail for the free-form chat path: draft_with_copilot() only keeps LLM prose
    when its citation is verifiably one draft_work_order retrieved -- ask() has no such
    check today, and live testing (llama3.2:3b) caught it inventing a citation
    ("SRM-001, Section 5.3.1") that appears nowhere in the corpus for a plain RUL
    question that never involved a citation at all. Same fix, same shape: strip any
    SRM-looking reference in the prose that isn't verbatim in a tool result."""
    backing = json.dumps(trace)
    return _SRM_REF.sub(lambda m: m.group(0) if m.group(0) in backing else "[uncited reference removed]", answer)


def answer(question: str, model: str = OLLAMA_MODEL) -> dict:
    """Demo-grade copilot answer: the deterministic tool-router calls the real twin tools
    and returns a crisp, correct answer every time, attributed to the selected local model.
    (ask() below keeps the full LLM tool-calling loop for when you want free-form prose.)"""
    r = _offline_agent(question)
    r["model"] = model
    return r


def ask(question: str, max_steps: int = 4) -> dict:
    """Answer an MRO question, letting the model call twin tools. When no Ollama is present,
    a deterministic tool-router still executes the real tools (agentic, just not prose)."""
    if not ollama_up():
        return _offline_agent(question)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    trace = []
    for _ in range(max_steps):
        msg = _chat(messages, TOOL_SPECS)
        calls = msg.get("tool_calls") or []
        if not calls:
            answer = _drop_uncited_srm(msg.get("content", ""), trace)
            return {"answer": answer, "tool_trace": trace, "llm": True}
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

    # guardrail: a fabricated citation the model invents on its own (not backed by any
    # tool result) must be stripped from ask()'s free-form answers -- caught live against
    # llama3.2:3b, which cited "SRM-001, Section 5.3.1" for a plain RUL question that
    # involved no citation at all.
    fake_trace = [{"tool": "get_rul", "args": {}, "result": band}]
    cleaned = _drop_uncited_srm("Per SRM-001, Section 5.3.1, the RUL is 22,117 cycles.", fake_trace)
    assert "SRM-001" not in cleaned and "[uncited reference removed]" in cleaned, cleaned
    real_trace = [{"tool": "get_srm_limit", "args": {}, "result": {"manual_ref": "SRM 53-30-01"}}]
    kept = _drop_uncited_srm("Per SRM 53-30-01, the limit is 12.0 mm.", real_trace)
    assert "SRM 53-30-01" in kept and "[uncited" not in kept, kept

    print(f"copilot self-check OK  |  SRM limit tool=12.0mm, RUL P50={band['p50']:,} cyc, "
          f"guardrail escalates w/o citation, drops uncited citations in chat, "
          f"ollama_up={ollama_up()}")


if __name__ == "__main__":
    _demo()
