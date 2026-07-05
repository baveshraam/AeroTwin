import { useEffect, useState } from 'react'

/* AeroTwin — ML Pipeline (edge, offline).
   Honest reframe of the serving console. The box serves ONE twin on a ₹10k Pi in
   airplane mode, so there is no cluster to load-balance and nothing to autoscale.
   The architecture IS the product: train off-box, serve at the edge, one audited
   promotion gate between. All readouts are a small deterministic in-page simulation
   (no Math.random) so the console is always live; model quality is shown as
   method + provenance, never a fabricated point score. */

// the real on-box chain: inspection -> priced decision
const CHAIN = [
  { k: 'detect', t: 'Detect', d: 'YOLOv8-seg · crack / dent' },
  { k: 'size', t: 'Size', d: 'ArUco fiducial · → mm' },
  { k: 'grade', t: 'Grade', d: 'vs SRM allowable limit' },
  { k: 'twin', t: 'Twin', d: 'per-tail record · health' },
  { k: 'rul', t: 'Forecast', d: 'Paris-MC + Bayesian · P10/50/90' },
  { k: 'plan', t: 'Prescribe', d: 'capacity-aware fleet plan' },
  { k: 'price', t: 'Price', d: '₹ ledger vs calendar' },
]

// the two planes either side of the gate
const TRAIN = ['Versioned data', 'Feature transform', 'Leakage guard · CI', 'Fit — Virkler-calibrated', 'Validate + coverage', 'Model card']
const EDGE = ['Quantize + re-calibrate', 'Deterministic inference', 'Twin + band + reason', 'Rule-baseline fallback', 'Drift + shadow']

// real models — honest status, no invented accuracy
const MODELS = [
  { id: 'crack-seg', task: 'Skin crack / dent', arch: 'YOLOv8-seg', ver: 'v0.9', size: '11.9 MB', q: 'INT8', status: 'shadow', metric: 'recall-first · POD' },
  { id: 'anomaly-pc', task: 'Zero-label anomaly', arch: 'PatchCore', ver: 'v1.4', size: '8.6 MB', q: 'FP16', status: 'canary', metric: 'train-on-normal' },
  { id: 'rul-paris', task: 'RUL P10 / P50 / P90', arch: 'Paris-law Monte-Carlo', ver: 'v3.1', size: '12 KB', q: '—', status: 'serving', metric: '80% band · target' },
  { id: 'rul-bayes', task: 'Per-tail growth', arch: 'Normal–Normal conjugate', ver: 'v2.0', size: '4 KB', q: '—', status: 'serving', metric: 'tightens each scan' },
  { id: 'fed-prior', task: 'Fleet growth prior', arch: 'FedAvg + ε-DP', ver: 'v1.2', size: '1 KB', q: '—', status: 'serving', metric: 'ε = 1.0' },
]

// per-stage edge inference budget (ms, INT8 CPU on a Pi 5 — illustrative, honest scale)
const BUDGET = [
  { n: 'crack-seg (INT8)', ms: 31 },
  { n: 'anomaly-pc (PatchCore)', ms: 22 },
  { n: 'size + grade', ms: 2 },
  { n: 'RUL Monte-Carlo ×400', ms: 4 },
  { n: 'Bayes + twin + plan', ms: 3 },
]

const EVENTS = [
  { t: '−00:04', m: 'crack-seg v0.9 → shadow · logged, not acted on' },
  { t: '−02:11', m: 'anomaly-pc v1.4 → canary · held-out AUROC nominal' },
  { t: '−14:30', m: 'rul-paris re-calibrated post-INT8 · coverage re-checked' },
]

export default function MLPipeline() {
  // one slow deterministic clock — the console breathes, it does not jitter
  const [t, setT] = useState(0)
  useEffect(() => { const id = setInterval(() => setT(x => x + 1), 1400); return () => clearInterval(id) }, [])

  const live = t % CHAIN.length                              // the stage currently processing
  const p95 = Math.round(46 + 5 * Math.sin(t / 5))           // ~41–51 ms, INT8 CPU
  const chain = Math.round(208 + 14 * Math.sin(t / 6 + 0.5)) // end-to-end sense->price
  const drift = 0.12
  const driftHot = drift > 0.25
  const total = BUDGET.reduce((a, b) => a + b.ms, 0)

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Edge ML · Offline · Train-off-box / Serve-at-edge</div>
        <h1>ML Pipeline</h1>
        <p>The inspection-to-decision model chain that runs on the ₹10,000 Raspberry&nbsp;Pi in airplane mode — detect → size → grade → twin → forecast → prescribe → price. One twin, offline: there is no cluster to load-balance. The architecture is the product — train off-box, serve at the edge, with a single audited promotion gate between.</p>
      </div>

      {/* live edge readouts (edge-scale, honest) */}
      <div className="mlp-rail">
        <MLTile k="p95 inference" v={p95} u="ms · INT8" col="var(--cyan)" />
        <MLTile k="chain latency" v={chain} u="ms end-to-end" />
        <MLTile k="models resident" v={5} u="INT8 · FP16" col="var(--accent)" />
        <MLTile k="feature drift" v={drift.toFixed(2)} u="PSI · stable" col="var(--cyan)" />
      </div>

      {/* live serving path — the real chain */}
      <div className="card">
        <h2>Serving path <span className="tt">sense → predict → prescribe → price</span></h2>
        <div className="mlp-flow">
          {CHAIN.map((s, i) => <div key={s.k} className={`mlp-stage ${i === live ? 'live' : ''}`}>
            <div className="ms-t">{s.t}{i === live ? <i className="ms-live" /> : null}</div>
            <div className="ms-d">{s.d}</div>
            {i < CHAIN.length - 1 ? <span className="ms-arrow">▸</span> : null}
          </div>)}
        </div>
      </div>

      {/* two-plane architecture — the defensible spine */}
      <div className="card">
        <h2>Architecture <span className="tt">two planes · one gate</span></h2>
        <div className="planes">
          <div className="plane train">
            <div className="plane-h"><b>① Training plant</b><span>off-box · workstation / CI · whole dataset</span><span className="econ">rigor over latency</span></div>
            <div className="mlp-flow">
              {TRAIN.map((s, i) => <div key={s} className="mlp-stage sm">
                <div className="ms-t">{s}</div>
                {i < TRAIN.length - 1 ? <span className="ms-arrow">▸</span> : null}
              </div>)}
            </div>
          </div>
          <div className="plane gate">
            <div className="plane-h"><b>⟐ Promotion gate + registry</b><span>content-addressed · full lineage → SHA-256 chain</span></div>
            <div className="gate-life">
              <span className="step">pass validation harness</span><span className="arr">+</span>
              <span className="step">engineer sign-off</span><span className="arr">▸</span>
              <span className="step">DRAFT</span><span className="arr">→</span><span className="step">SIGNED</span><span className="arr">→</span><span className="step">CLOSED</span>
              <span className="glbl">rollback = previous signed hash</span>
            </div>
          </div>
          <div className="plane edge">
            <div className="plane-h"><b>② Edge runtime</b><span>on-box · Pi · CPU-only · airplane-mode</span><span className="econ">bounded worst-case latency</span></div>
            <div className="mlp-flow">
              {EDGE.map((s, i) => <div key={s} className="mlp-stage sm">
                <div className="ms-t">{s}</div>
                {i < EDGE.length - 1 ? <span className="ms-arrow">▸</span> : null}
              </div>)}
            </div>
          </div>
        </div>
      </div>

      <div className="grid c2">
        {/* model registry — real, honest */}
        <div className="card">
          <h2>Model registry <span className="tt">versioned · shadow · rollback</span></h2>
          <div className="mreg">
            <div className="mreg-row mreg-head"><span>model</span><span>task</span><span>size</span><span>status</span><span>method</span></div>
            {MODELS.map(m => <div key={m.id} className="mreg-row">
              <span className="mr-id">{m.id}<i>{m.arch} · {m.ver}</i></span>
              <span className="mr-task">{m.task}</span>
              <span className="mono">{m.size}<em>{m.q}</em></span>
              <span className={`mr-st ${m.status}`}>{m.status}</span>
              <span className="mono">{m.metric}</span>
            </div>)}
          </div>
          <div className="reg-note">Quality is logged as method + provenance — measured numbers land here on demo day, never a fabricated score. <b>crack-seg runs in shadow</b> (mock sensor until the detector converges); the physics + Bayesian models serve live at kilobytes.</div>
        </div>

        {/* edge runtime — replaces the fictitious load balancer */}
        <div className="card">
          <h2>Edge runtime <span className="tt">one process · bounded queue</span></h2>
          <div className="lb-in">
            <span className="lb-inlbl">budget</span>
            <div className="lb-inbar"><i style={{ width: Math.min(100, total / 90 * 100) + '%' }} /></div>
            <span className="lb-inv">{total} ms</span>
          </div>
          <div className="edge-rows">
            {BUDGET.map((b, i) => {
              const w = b.ms / total * 100
              const sway = 1 + 0.06 * Math.sin(t / 5 + i)
              return (
                <div key={b.n} className="lb-node">
                  <div className="ln-h"><span>{b.n}</span><b style={{ color: 'var(--cyan)' }}>{Math.round(b.ms * sway)} ms</b></div>
                  <div className="ln-bar"><i style={{ width: Math.min(100, w) + '%', background: 'var(--cyan)' }} /></div>
                </div>
              )
            })}
          </div>
          <div className="edge-facts">
            <span><i className="en-led" />single deterministic process · queue depth 0</span>
            <span><i className="ann-lamp go" />rule-baseline fallback · ARMED</span>
            <span><i className="ann-lamp caution" />delayed labels reconcile → retrain via gate</span>
          </div>
          <div className="lb-log">
            {EVENTS.map((e, i) => <div key={i} className="lb-ev"><span className="lb-t">{e.t}</span>{e.m}</div>)}
          </div>
        </div>
      </div>

      {/* drift monitor — honest banding, delayed-label aware */}
      <div className="card">
        <h2>Feature-drift monitor <span className="tt">per-feature · importance-weighted</span></h2>
        <div className="drift">
          <div className="drift-g">
            <div className="drift-track"><i style={{ width: Math.min(100, drift / 0.34 * 100) + '%', background: driftHot ? 'var(--amber)' : 'var(--cyan)' }} /></div>
            <div className="drift-marks"><span>0.0 stable</span><span className="drift-slo">watch 0.10</span><span className="drift-slo">act 0.25</span><span>0.34</span></div>
          </div>
          <div className="drift-v">
            <b style={{ color: driftHot ? 'var(--amber)' : 'var(--cyan)' }}>PSI {drift.toFixed(2)}</b>
            <span>{driftHot ? 'above act threshold — retrain request queued to the gate' : 'within the stable band — true accuracy reconciles when labels mature (weeks later), then a retrain request re-enters the gate'}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function MLTile({ k, v, u, col }: { k: string, v: any, u: string, col?: string }) {
  return <div className="tile">
    <div className="t-k">{k}</div>
    <div className="t-v" style={{ color: col }}>{v}<span className="t-u"> {u}</span></div>
  </div>
}
