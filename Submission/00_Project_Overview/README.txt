AeroTwin-Edge — Tata Technologies InnoVent-27 (Aerospace, 3.2.3.4)
Stage 2 — Virtual Proof of Concept submission

ONE-LINE PITCH
A fully-offline edge inspector that detects and severity-grades aircraft defects on
a Raspberry Pi 5, grows a living digital twin per tail number, predicts when a defect
crosses its SRM limit, and drafts the work order via an agentic MRO copilot — with
zero raw imagery ever leaving the secure site.

WHAT IS REAL vs ROADMAP (read this first — we are explicit about scope)
REAL in this POC:
  - crack detection + segmentation (YOLO-seg)
  - ArUco fiducial -> millimetre sizing -> SRM allowable-limit grading
  - per-tail digital twin console with condition history
  - Paris-law crack-growth projection (illustrative constants)
  - agentic, manual-cited work-order draft with a human sign-off gate
  - offline execution (no network)
ROADMAP (architected, not built):
  - unsupervised anomaly detection, INT8/Hailo acceleration
  - federated fleet learning + secure aggregation + differential privacy
  - hash-chained audit trail, signed models, OTA registry

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
