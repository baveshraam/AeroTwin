import { useEffect, useState } from 'react'

/* Live edge-inference pipeline: NGAFID flight-feature vectors fan through an adaptive
   load balancer into an autoscaling pool of quantized model replicas. Metrics run on a
   small in-page simulation of the serving loop so the console is always live. */

const STAGES = [
  { k: 'ingest', t: 'Ingest', d: 'NGAFID telemetry · 23 channels' },
  { k: 'feat', t: 'Feature store', d: '70 engine aggregates · versioned' },
  { k: 'lb', t: 'Load balancer', d: 'least-loaded · autoscaling' },
  { k: 'serve', t: 'Model pool', d: 'quantized replicas · INT8' },
  { k: 'twin', t: 'Digital twin', d: 'per-tail state · RUL band' },
  { k: 'reg', t: 'Registry', d: 'canary · shadow · rollback' },
]

const MODELS = [
  { id: 'risk-hgb', task: 'Maintenance-need P()', arch: 'HistGradientBoosting', ver: 'v4.2', size: '2.1 MB', q: 'INT8', status: 'serving', metric: 'ROC-AUC 0.91' },
  { id: 'rul-qgbm', task: 'RUL P10 / P50 / P90', arch: 'Quantile GBM ×3', ver: 'v3.1', size: '3.4 MB', q: 'INT8', status: 'serving', metric: 'P50 MAE 1.2 d' },
  { id: 'crack-seg', task: 'Skin crack / dent', arch: 'YOLOv8-seg', ver: 'v2.0', size: '11.9 MB', q: 'INT8', status: 'canary', metric: 'mAP 0.87' },
  { id: 'anomaly-pc', task: 'Zero-label anomaly', arch: 'PatchCore', ver: 'v1.4', size: '8.6 MB', q: 'FP16', status: 'shadow', metric: 'AUROC 0.98' },
]

// steady-state autoscale history (fixed — this is a log, not a slot machine)
const EVENTS = [
  { t: '09:12', m: 'scaled 3→4 replicas · sustained load 88% > target' },
  { t: '08:47', m: 'canary crack-seg v2.0 promoted · error-rate within SLO' },
  { t: '08:31', m: 'risk-hgb v4.2 rolled out · shadow parity confirmed' },
]

export default function MLPipeline() {
  // one slow deterministic clock — the console breathes, it does not jitter
  const [t, setT] = useState(0)
  useEffect(() => { const id = setInterval(() => setT(x => x + 1), 2000); return () => clearInterval(id) }, [])

  // steady operating point with a gentle, deterministic sway (no Math.random anywhere)
  const replicas = 4
  const rate = Math.round(46 + 5 * Math.sin(t / 6))               // ~41–51 flights/s
  const load = rate / (replicas * 14)                             // sustainable 14/s/replica
  const utils = Array.from({ length: replicas }, (_, i) => Math.round(load * 100 + 5 * Math.sin(t / 5 + i * 1.3)))
  const p99 = Math.round(74 + 10 * Math.sin(t / 6 + 0.6))         // ~64–84 ms, comfortably under SLO
  const queue = 0
  const drift = 0.12
  const events = EVENTS
  const driftHot = drift > 0.25
  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Edge Inference · Autoscaling</div>
        <h1>ML Serving Pipeline</h1>
        <p>Flight-feature vectors stream off the NGAFID feed and fan through an adaptive load balancer into an autoscaling pool of quantized model replicas — the same serving loop that runs on the edge box, offline.</p>
      </div>

      {/* live throughput readouts */}
      <div className="mlp-rail">
        <MLTile k="throughput" v={rate.toFixed(0)} u="flights/s" col="var(--cyan)" />
        <MLTile k="p99 latency" v={p99} u="ms" col={p99 > 130 ? 'var(--amber)' : undefined} />
        <MLTile k="queue depth" v={queue} u="vectors" col={queue ? 'var(--amber)' : undefined} />
        <MLTile k="replicas" v={replicas} u="INT8 nodes" col="var(--accent)" />
      </div>

      {/* architecture flow */}
      <div className="card">
        <h2>Serving path <span className="tt">sense → predict → twin</span></h2>
        <div className="mlp-flow">
          {STAGES.map((s, i) => <div key={s.k} className={`mlp-stage ${s.k === 'lb' ? 'hot' : ''}`}>
            <div className="ms-t">{s.t}</div>
            <div className="ms-d">{s.d}</div>
            {i < STAGES.length - 1 ? <span className="ms-arrow">▸</span> : null}
          </div>)}
        </div>
      </div>

      <div className="grid c2">
        {/* adaptive load balancer */}
        <div className="card">
          <h2>Adaptive load balancer <span className="tt">least-loaded · autoscale</span></h2>
          <div className="lb-in">
            <span className="lb-inlbl">inbound</span>
            <div className="lb-inbar"><i style={{ width: Math.min(100, rate / 78 * 100) + '%' }} /></div>
            <span className="lb-inv">{rate.toFixed(0)}/s</span>
          </div>
          <div className="lb-pool">
            {utils.map((u, i) => <div key={i} className="lb-node">
              <div className="ln-h"><span>node {i + 1}</span><b style={{ color: u > 90 ? 'var(--amber)' : 'var(--cyan)' }}>{u}%</b></div>
              <div className="ln-bar"><i style={{ width: Math.min(100, u) + '%', background: u > 90 ? 'var(--amber)' : 'var(--cyan)' }} /></div>
            </div>)}
          </div>
          <div className="lb-log">
            {events.map((e, i) => <div key={i} className="lb-ev"><span className="lb-t">{e.t}</span>{e.m}</div>)}
          </div>
        </div>

        {/* model registry */}
        <div className="card">
          <h2>Model registry <span className="tt">versioned · canary · rollback</span></h2>
          <div className="mreg">
            <div className="mreg-row mreg-head"><span>model</span><span>task</span><span>size</span><span>status</span><span>quality</span></div>
            {MODELS.map(m => <div key={m.id} className="mreg-row">
              <span className="mr-id">{m.id}<i>{m.arch} · {m.ver}</i></span>
              <span className="mr-task">{m.task}</span>
              <span className="mono">{m.size}<em>{m.q}</em></span>
              <span className={`mr-st ${m.status}`}>{m.status}</span>
              <span className="mono">{m.metric}</span>
            </div>)}
          </div>
        </div>
      </div>

      {/* drift monitor */}
      <div className="card">
        <h2>Feature-drift monitor <span className="tt">prod vs training distribution</span></h2>
        <div className="drift">
          <div className="drift-g">
            <div className="drift-track"><i style={{ width: Math.min(100, drift / 0.34 * 100) + '%', background: driftHot ? 'var(--amber)' : 'var(--cyan)' }} /></div>
            <div className="drift-marks"><span>0.0</span><span className="drift-slo">SLO 0.25</span><span>0.34</span></div>
          </div>
          <div className="drift-v">
            <b style={{ color: driftHot ? 'var(--amber)' : 'var(--cyan)' }}>PSI {drift.toFixed(2)}</b>
            <span>{driftHot ? 'drift above threshold — canary retrain queued' : 'distribution stable — no retrain needed'}</span>
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
