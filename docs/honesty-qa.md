# Honesty Q&A — what to say to a judge

> **Re-tune note (2026-07-03):** the primary domain is now **predictive health on real
> telemetry** (NGAFID / C-MAPSS). That flips the honesty story in our favour for the core —
> the *predict engine trains on real, public flight/engine data*, not a synthetic stream.
> The synthetic-data caveats below now apply mainly to the **structural-inspection extra
> feature** (SHM stream, federation sites, telemetry HUD). Add the PHM line below.

Say these out loud if a judge asks "is that real data?" The through-line is the same for
every item: **the algorithm is real and tested; the data feeding it is synthetic, because
we don't have field sensor hardware / a data-sharing agreement for a POC — and we label
that synthetic-ness everywhere it surfaces (API flag, on-screen chip, README).**

### Predict engine — PHM (the new core)

> "The prediction core is trained on **real, public data** — the NGAFID dataset (≈29,000
> real general-aviation flights, 23 sensors, labelled around real unplanned-maintenance
> events) for maintenance-need classification, and NASA C-MAPSS turbofan run-to-failure data
> for remaining-useful-life. We train a compact model (LightGBM / MiniRocket) that runs on a
> Raspberry Pi, and we report honest metrics — recall bias and RUL error, not a flattering
> single number. The predictions are **explainable**: SHAP shows the exact sensors driving
> each flag, and the offline copilot turns that into a plain-English note. Nothing here is a
> mocked prediction — it's a real model on real fleet data, quantised for the edge."

---

### SHM (between-inspection Structural Health Monitoring)

> "The change-detection algorithm is real — it's a standard EWMA baseline plus a one-sided
> CUSUM, the same class of method used in real structural-health-monitoring systems, and
> we've tested that it fires on a growing crack and stays silent on a stable one. What's
> synthetic is the sensor stream it runs over: we don't have strain gauges, acoustic-
> emission, or vibration sensors on a laptop, so we generate a physics-motivated signal —
> as a crack grows, peak strain rises, AE hit-rate accelerates, and a natural frequency
> shifts down with stiffness loss. The moment we have field telemetry, we swap the stream
> for a trained model and the detector and twin interface stay identical. That's why the
> panel is tagged 'SYNTHETIC STREAM' and the API returns `synthetic: true`."

### Federated learning (ITAR-safe shared growth priors)

> "The federated math is real — it's proper FedAvg, sample-count-weighted, plus a Laplace
> differential-privacy mechanism with a per-site epsilon budget, and our self-check proves
> the pooled estimate is tighter than any data-poor site's local one. What's simulated is
> the federation itself: we model four hangars drawing crack-growth rates from one true
> distribution, because there's no live multi-site federation yet. The privacy claim is
> structural, not hand-waved — each site emits only three numbers, count-mean-variance, so
> there's literally no imagery or per-tail record to leak. It's tagged 'SIMULATED' in the
> UI and the API returns `simulated: true`."

### Telemetry HUD (fps / latency / CPU temp / power)

> "Those edge-telemetry numbers are simulated when we run on a laptop — a laptop isn't a
> Raspberry Pi 5, so we don't pretend its fps or power draw are the edge device's. On the
> actual Pi the same HUD reads real `psutil` values. We flag it honestly: the fps carries a
> `*`, hovering explains it, and the API returns `simulated: true` with the device name. The
> ~11 fps and ~6 watt figures are a realistic CPU-only YOLOv8n-seg ballpark for a Pi 5, not
> a measured claim on this machine."

### Defect detection (the sensor)

> "Detection is the one piece we're still training separately, so for the demo the detector
> returns a fixed mock size — that's why every finding is stamped `model_version: mock-v0`
> and the header shows a 'SYNTHETIC DATA' badge. The point of the POC isn't the detector —
> every team can build one — it's the twin on top: predict, prescribe, price. The detector
> is a swappable sensor; the twin is the product."

### Copilot

> "The copilot is a deterministic tool-router by default — no LLM required. It parses your
> question, calls the real twin tools (SRM limit, Monte-Carlo RUL, tail state), and answers
> under a citation guardrail that refuses to state an airworthiness limit it didn't retrieve
> from the manual. You can drop in a local Ollama model for free-form prose, but we don't
> claim a live LLM when one isn't running — the footer tells you which path answered."

---

**If pushed on "so what's actually real?"** — the SRM grading, the Paris-law Monte-Carlo
RUL with P10/P50/P90 bands, the Bayesian per-tail learning, the capacity-constrained fleet
planner and its rupee ledger, the CUSUM detector, the FedAvg + DP math, the hash-chained
tamper-evident audit trail, and the whole offline edge architecture. What's synthetic is
strictly the *sensor data* — and it's labeled as such everywhere.
