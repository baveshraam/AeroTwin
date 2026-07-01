AeroTwin-Edge — Tata Technologies InnoVent-27 (Aerospace)
Problem statement: EDGE AI FOR DIGITAL TWIN-ENABLED MRO
Stage 2 — Virtual Proof of Concept submission

ONE-LINE PITCH
AeroTwin-Edge — the Rs 10,000 box that decides which jet to ground and which to fly.
A fully-offline, per-tail-AND-per-fleet structural DIGITAL TWIN on a Raspberry Pi 5
that goes PREDICT -> PRESCRIBE -> PRICE: it turns every inspection into a condition
record, PREDICTS each aircraft's remaining useful life, PRESCRIBES a hangar-capacity-
constrained fleet maintenance plan (which tails to service, defer, or ground), and
PRICES every decision in rupees against the blind calendar. Defect detection is the
sensor; the priced fleet plan is the payoff. Zero raw imagery leaves the secure site.

WHY IT MATTERS (the real problem we solve)
Fleets are maintained on a fixed CALENDAR interval, which over-maintains the healthy
majority (wasted downtime) and under-maintains the few fast-growing defects that
outrun the interval (safety + AOG risk, ~Rs 8L-1.25Cr/hr). There is no continuous
per-tail condition history to schedule against, and cloud can't hold it (ITAR-isolated
hangars). AeroTwin-Edge is that missing system-of-record.

WHAT IS REAL vs ROADMAP (read this first — we are explicit about scope)
REAL in this POC:
  - the TWIN BRAIN: per-tail health index (0-100), remaining-useful-life in cycles,
    condition-based scheduling call (PULL FORWARD / SAFE TO DEFER / GROUND) vs the
    calendar baseline, and a FLEET RISK BOARD ranking every tail worst-first
  - the PRESCRIPTIVE PLANNER + RUPEE LEDGER: a hangar-capacity-constrained fleet
    service plan priced in rupees vs the calendar (downtime recovered + AOG risk
    avoided - risk carried = net value per window); every constant explicit
  - crack detection + segmentation (YOLO-seg) as the sensor
  - ArUco fiducial -> millimetre sizing -> SRM allowable-limit grading
  - Paris-law / empirical crack-growth projection (illustrative constants)
  - agentic, manual-cited work-order draft with a human sign-off gate
  - hash-chained, tamper-evident audit trail
  - offline execution (no network)
ROADMAP (architected, not built):
  - unsupervised anomaly detection, INT8/Hailo acceleration
  - more sensors (borescope, eddy-current, tap-test) into the same twin record
  - federated fleet learning + secure aggregation + differential privacy
  - signed models, OTA registry

FOLDER MAP
  00_Project_Overview/  this file
  01_Presentation/      SLIDE_BLUEPRINT.txt (copy onto the deck), PRESENTATION_NOTES.txt
  02_POC_Media/         MEDIA_CHECKLIST.txt, VIDEO_SCRIPT.txt, diagrams/ screenshots/
                        video/ graphs/
  03_Technical/         POC_BUILD_RUNBOOK.txt, detect_and_size.py, twin_console.py,
                        srm_limits.csv

HOW TO REPRODUCE THE DEMO
  See 03_Technical/POC_BUILD_RUNBOOK.txt

TEAM
  [names / roles]
