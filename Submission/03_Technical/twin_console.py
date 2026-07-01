"""
AeroTwin-Edge Console — standalone single-tail twin/progression/agent shell.

NOTE: this is a legacy standalone shell. The PRIMARY dashboard is now the repo's
per-tail + per-fleet twin with the FLEET RISK BOARD (health index / RUL / condition-
based scheduling). Demo and screenshot THAT, not this one:
    python -m src.pipeline --seed
    uvicorn src.l1_twin.app:app --port 8000      # or: python tools/render_dashboard.py

Detection numbers are REAL (from detect_and_size.py); the twin history and the
crack-growth projection here are seeded/illustrative for the POC.

    pip install streamlit numpy matplotlib
    streamlit run twin_console.py
"""
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

# --- seeded twin (hand-entered for the POC; the real system reads the twin store) ---
TAIL = "VT-XYZ"
LOCATION = "ATA 53 / fuselage skin / stringer 14"
SRM_LIMIT_MM = 12.0
SRM_REF = "SRM 53-XX-XX"
HISTORY = [  # (check label, flight cycles since new, crack mm)
    ("C-check 2024", 18200, 6.0),
    ("This scan",    19050, 8.0),
]

# ponytail: headline cycles-to-limit is a single seeded knob so the video, this chart,
# and the slides all agree. 40 = a deliberately fast-growth scenario; see the runbook
# note before recording. The real system integrates Paris' law (da/dN = C*(dK)^m).
PROJECTED_CYCLES = 40


def projection_curve(a0_mm, a_c_mm, n_cycles=PROJECTED_CYCLES, accel=2.5):
    """Accelerating crack-growth shape, pinned to cross a_c at n_cycles.
    Illustrative (Paris-law-like convexity); not a calibrated integration."""
    n = np.linspace(0, n_cycles, 100)
    a = a0_mm + (a_c_mm - a0_mm) * (n / n_cycles) ** accel
    return n, a


def grade(size_mm, limit_mm):
    frac = size_mm / limit_mm
    if frac >= 1.0:
        return "BEYOND-LIMIT", frac
    if frac >= 0.5:
        return "MAJOR", frac
    return "MINOR", frac


st.set_page_config(page_title="AeroTwin-Edge Console", layout="wide")
st.title("AeroTwin-Edge — Structural Health Console")
st.caption("Offline edge node · per-tail digital twin · condition-based maintenance")

current = HISTORY[-1][2]
g, frac = grade(current, SRM_LIMIT_MM)

c1, c2, c3 = st.columns(3)
c1.metric("Tail", TAIL)
c2.metric("Location", LOCATION)
c3.metric("Crack size", f"{current:.1f} mm",
          f"{g} · {frac * 100:.0f}% of {SRM_LIMIT_MM:.0f} mm limit")

st.subheader("Condition history")
st.table({
    "Check": [h[0] for h in HISTORY],
    "Flight cycles": [h[1] for h in HISTORY],
    "Crack (mm)": [h[2] for h in HISTORY],
})

st.subheader("Progression — crack-growth projection (illustrative)")
n, a = projection_curve(current, SRM_LIMIT_MM)
fig, ax = plt.subplots()
ax.plot(n, a)
ax.axhline(SRM_LIMIT_MM, ls="--", color="red", label=f"{SRM_LIMIT_MM:.0f} mm SRM limit")
ax.set_xlabel("flight cycles from now")
ax.set_ylabel("crack length (mm)")
ax.set_title(f"crosses {SRM_LIMIT_MM:.0f} mm SRM limit in ~{PROJECTED_CYCLES} cycles")
ax.legend()
st.pyplot(fig)
st.warning(f"Projected limit-crossing in ~{PROJECTED_CYCLES} flight cycles -> "
           f"recommend pulling inspection forward (illustrative constants).")

st.subheader("Agentic MRO copilot — drafted work order")
st.code(
    f"""WORK ORDER (DRAFT — requires certifying-engineer sign-off)
Tail:        {TAIL}
Finding:     fatigue crack, {current:.1f} mm, {LOCATION}
Severity:    {g} ({frac * 100:.0f}% of {SRM_LIMIT_MM:.0f} mm allowable)
Governing:   {SRM_REF} (allowable damage limits, fuselage skin)        [CITED]
Repair:      per {SRM_REF} Fig. X; ref AMM 51-XX standard practices
Disposition: not dispatchable beyond limit; schedule repair within projected interval
Generated offline by AeroTwin-Edge agent · citation-required · human gate enforced""",
    language="text",
)
if st.button("Route to certifying engineer for sign-off"):
    st.success("Routed. Awaiting certifying-engineer acceptance. (Human retains authority.)")
