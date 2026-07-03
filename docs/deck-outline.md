# Deck Outline — AeroTwin (~12–14 slides)

> **AeroTwin : An Edge-AI Digital Twin for Digital-Twin-Enabled MRO — On-Device PHM,
> Explainable RUL, Condition-Based Maintenance & Federated Fleet Intelligence.**
> Problem statement: **3.2.3.1 Edge AI for Digital-Twin-Enabled MRO** (PRIMARY). Build on the InnoVent
> Section-4 template. **Lead with prediction — the edge twin that forecasts failure from
> sensor telemetry and moves money.** Structural inspection is one *extra sensor*, shown
> late, not the story. Judges grade depth in the primary domain, so keep the front of the
> deck 100% predictive MRO.

1. **Title** — "AeroTwin — an Edge-AI digital twin that predicts aircraft failures before
   they ground the fleet." Sub: offline PHM on a ₹10k Pi — **predict → explain → prescribe
   → price → certify.** AOG hook (₹8L–1.25Cr/grounded hr).
2. **Why now** — edge silicon (Pi 5) + the CBM+/PHM regulatory shift (EASA/FAA) + real
   public fleet datasets (NGAFID, C-MAPSS) + local LLMs + India MRO $2B→$4B. Curves cross now.
3. **The problem (MRO's language)** — maintenance runs on a blind **calendar/flight-hour**
   interval: over-maintain the healthy, miss the few drifting to failure. No per-asset
   condition brain at the edge. Cloud blocked in ITAR hangars.
4. **The insight** — a **digital twin per tail** at the edge turns raw **sensor telemetry**
   into a *predicted health trajectory* → maintain on actual condition + forecast, not the calendar.
5. **★ LIVE DEMO ★** — offline on the Pi: telemetry in → **failure/RUL prediction + the
   "why" (top sensors)** → fleet risk board → **prescriptive plan + rupee ledger** → cited
   work order → audit. All predictive MRO, all offline.
6. **The predict engine (the heart)** — edge ML (LightGBM/MiniRocket) on NGAFID/C-MAPSS →
   "this tail is trending to an unplanned maintenance event / has ~N cycles left," P10/P50/P90
   band. Tiny, CPU-only, real-time on a Pi. This is the graded core.
7. **Explainability — trust the prediction** — SHAP surfaces the driving sensors ("oil-temp
   trend + RPM variance"); the offline GenAI copilot writes the plain-English maintenance
   note. An unexplained prediction is useless to a Part-145 engineer — we solve that.
8. **The twin brain (prescribe)** — health index (0–100), RUL, condition-based call:
   PULL FORWARD / SAFE TO DEFER / GROUND — each quantified vs the calendar. Fleet risk board.
9. **★ THE MONEY SLIDE (price) ★** — capacity-constrained fleet plan + rupee ledger:
   "ground 1, service 2, safely defer 1 → **~₹6 Cr net value this window**" = downtime
   recovered + AOG risk avoided − risk carried. Live, offline. Nobody else prices the decision.
10. **The twin learns (ITAR-safe)** — Bayesian per-tail RUL tightening + **federated** growth
    priors with **differential privacy** — sites share only (n, mean, var); no data leaves the hangar.
11. **Prescribe → agent → audit** — citation-gated LLM work order (refuses to state a limit it
    can't cite), Part-145 human sign-off, hash-chained tamper-evident evidence PDF. Certifiable.
12. **Extra sensor — structural inspection** *(one slide, late)* — the same twin also ingests
    a crack/corrosion detector (YOLOv8-seg) + zero-label anomaly branch + Paris-law growth.
    Framed as "more sensors into the same twin," not the headline.
13. **Regulatory + security + moat** — ITAR-safe by design, EASA ML learning-assurance,
    edge + per-tail PHM twin + rupee-priced plan + certifiable audit. Others detect or
    dashboard; only we **predict → explain → prescribe → price → certify** at the edge.
14. **Business + sustainability + team + ask** — TAM ($100B+ global, $4B India), per-tail
    SaaS + outcome pricing; fewer needless checks = less scrap/ferry flights; the 2-person
    team; tech stack (React + FastAPI + edge ONNX + Ollama); the ask.

## Slide-making tips
- One idea per slide; big numbers, few words.
- The **prediction + "why" panel** (slide 5/7) and the **rupee ledger** (slide 9) are your
  instant-credibility images — put them big.
- Keep the demo video link (Drive) on slide 5 as a live-failure fallback.
- Every projected number labelled "engineering projection"; every synthetic stream labelled —
  that honesty reads as maturity.
- **Front 9 slides = pure predictive MRO.** Structural inspection appears once, at slide 12.
