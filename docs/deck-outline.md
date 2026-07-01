# Deck Outline — AeroTwin-Edge (~12–14 slides)

> Problem statement: **Edge AI for Digital Twin-Enabled MRO**. Build the PPT on the
> official InnoVent Section-4 template. Lead with the *twin* and the money it moves; let
> the live fleet risk board carry the middle; close on the moat. Inspection is the
> sensor, not the story.

1. **Title** — "AeroTwin-Edge — the ₹10,000 box that decides which jet to ground, and
   which to fly." Sub: an offline structural **digital twin** that goes
   **predict → prescribe → price** for a whole fleet. AOG hook (₹8L–1.25Cr/grounded hr).
2. **Why now** — edge silicon (Pi 5 + Hailo) + CBM+ regulatory shift (EASA/FAA) +
   foundation models + India MRO $2B→$4B. Four curves cross now.
3. **The problem (MRO's language)** — structural checks run on a blind **calendar**:
   over-maintain the healthy majority, miss the few fast growers. No per-tail condition
   history. Cloud blocked in ITAR hangars.
4. **The insight** — a **digital twin per tail**, held at the edge, converts inspections
   into a condition trajectory → schedule on *actual condition*, not the calendar.
5. **Architecture** — sensor → twin → predict → decide → agent → audit. Mark BUILD vs
   vision (federation / ops / AR).
6. **★ LIVE DEMO ★** — the unbroken chain, offline on the Pi: crack → grade → twin
   growth → **fleet risk board → prescriptive plan + rupee ledger** → cited work order → audit.
7. **The twin brain (predict → prescribe)** — health index (0–100), RUL in cycles, and
   the condition-based call: PULL FORWARD / SAFE TO DEFER / GROUND — each quantified vs
   the calendar. Then the fleet risk board: every tail ranked worst-first.
8. **★ THE MONEY SLIDE (price) ★** — the prescriptive fleet plan + rupee ledger. Under
   real hangar capacity: "ground 1, service 2, safely defer 1 → **~₹6 Cr net value this
   window**" = ₹ downtime recovered + ₹ AOG risk avoided − ₹ risk carried. Live, offline.
   Nobody else prices the decision. This is the slide that wins the room.
9. **Damage-tolerance lever** — better POD lowers detectable crack size → DTA widens the
   safe interval → feeds the twin's deferral math (more recovered downtime) or margin.
10. **Regulatory + security** — Part 145 human sign-off, decision-support framing, EASA
    ML learning-assurance, hash-chained audit trail, ITAR-safe by design.
11. **Business** — TAM ($100B+ global, $4B India), per-tail SaaS + outcome-based pricing
    (share of avoided AOG / deferred checks). One avoided AOG day pays for years.
12. **Moats + competition** — edge + per-tail twin + a *rupee-priced, capacity-aware
    fleet plan* + citation-gated agent + certifiable audit. Others detect or dashboard;
    only we predict → prescribe → price. No single competitor combines all of it.
13. **Roadmap + GTM** — Tata captive (Air India / C295) → Indian MROs → Gulf/SE-Asia;
    more sensors (borescope, eddy-current) into the same twin; federated fleet learning.
14. **Sustainability + team + the ask** — fewer needless checks = less scrap & fewer
    ferry flights; paperless task cards; the 2-person team; the ask.

## Slide-making tips
- One idea per slide; big numbers, few words.
- The **rupee ledger + fleet plan screenshot** is your instant-credibility image — put
  it big on slides 6 and 8. The fleet risk board and a still of the cracked panel support it.
- Put the demo video link (Drive) on slide 6 as a fallback if live fails.
- Every projected number labelled "engineering projection" — that honesty reads as maturity.
