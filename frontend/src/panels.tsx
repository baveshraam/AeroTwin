import { useEffect, useState } from 'react'
import { useTwin } from './DataContext'
import * as API from './api'
import { inr, sevCol } from './api'

const ACCENT = '#ffaa2b'

// ---------- sparklines ----------
export function Spark({ d }: { d: any }) {
  const pts = d.growth; if (!pts || pts.length < 2) return null
  const W = 360, H = 46, xs = pts.map((p: any) => p.cycles), ys = pts.map((p: any) => p.size_mm)
  const ymax = (Math.max(...ys, d.limit_mm || 0) * 1.12) || 1, xmax = Math.max(...xs) || 1
  const X = (c: number) => 2 + (W - 4) * (c / xmax), Y = (v: number) => H - 6 - (H - 12) * (v / ymax)
  const poly = pts.map((p: any) => `${X(p.cycles).toFixed(1)},${Y(p.size_mm).toFixed(1)}`).join(' ')
  return <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
    {d.limit_mm ? <line x1="2" y1={Y(d.limit_mm).toFixed(1)} x2={W - 2} y2={Y(d.limit_mm).toFixed(1)} stroke={ACCENT} strokeDasharray="3 3" strokeWidth="1" opacity=".85" /> : null}
    <polyline points={poly} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" opacity=".85" />
    {pts.map((p: any, i: number) => <circle key={i} cx={X(p.cycles).toFixed(1)} cy={Y(p.size_mm).toFixed(1)} r="2" fill="currentColor" />)}
  </svg>
}
export function ShmSpark({ d }: { d: any }) {
  const pts = d.series || []; const W = 360, H = 48, xmax = pts[pts.length - 1].cycle || 1
  const X = (c: number) => 2 + (W - 4) * (c / xmax), Y = (v: number) => H - 4 - (H - 8) * (v / 100)
  const poly = pts.map((p: any) => `${X(p.cycle).toFixed(1)},${Y(p.health).toFixed(1)}`).join(' ')
  return <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
    {d.alert_cycle != null ? <line x1={X(d.alert_cycle)} y1="0" x2={X(d.alert_cycle)} y2={H} stroke={ACCENT} strokeDasharray="3 2" /> : null}
    <polyline points={poly} fill="none" stroke="currentColor" strokeWidth="1.5" opacity=".8" />
  </svg>
}

// ---------- health ring ----------
export function HealthRing({ health, grounded, size = 64 }: { health: number, grounded?: boolean, size?: number }) {
  const r = 27, C = 2 * Math.PI * r, col = sevCol(health, grounded)
  return <div className="ring" style={{ width: size, height: size }}>
    <svg width={size} height={size} viewBox="0 0 64 64">
      <circle className="ringbg" cx="32" cy="32" r={r} fill="none" strokeWidth="3" />
      <circle cx="32" cy="32" r={r} fill="none" stroke={col} strokeWidth="3" strokeLinecap="round"
        strokeDasharray={C} strokeDashoffset={C * (1 - health / 100)} style={{ transition: 'stroke-dashoffset .6s,stroke .6s' }} />
    </svg>
    <div className="rv"><b style={{ color: col }}>{grounded ? 0 : health}</b><span>health</span></div>
  </div>
}

// backend's illustrative defaults — used to recover the per-event counts so the numbers
// recompute against whatever costs the operator types in.
const DEF_AOG = 20_000_000, DEF_CHK = 1_200_000
// ---------- pricing, in plain English + editable to the operator's own costs ----------
export function Ledger() {
  const { ledger } = useTwin()
  const [aog, setAog] = useState(DEF_AOG)
  const [chk, setChk] = useState(DEF_CHK)
  if (!ledger) return <p className="muted">Loading…</p>
  const nAtRisk = Math.round((ledger.aog_risk_avoided || 0) / DEF_AOG)   // failures caught in time
  const nDeferred = Math.round((ledger.downtime_recovered || 0) / DEF_CHK) // needless checks skipped
  const nCarried = Math.round((ledger.aog_risk_carried || 0) / DEF_AOG)  // at-risk tails with no slot
  const prevented = nAtRisk * aog, noWaste = nDeferred * chk, carried = nCarried * aog
  return <div className="save">
    <div className="save-head">
      <div className="save-v">{inr(prevented + noWaste)}<span className="save-star">*</span></div>
      <div className="save-k">saved this week vs a fixed-calendar schedule</div>
    </div>
    <div className="save-rows">
      <div className="save-row"><span className="sr-ico plus">+</span><b>{inr(prevented)}</b><span>{nAtRisk} grounded-aircraft failure{nAtRisk === 1 ? '' : 's'} caught before it happened</span></div>
      <div className="save-row"><span className="sr-ico plus">+</span><b>{inr(noWaste)}</b><span>{nDeferred} healthy jet{nDeferred === 1 ? '' : 's'} not pulled in for checks they didn't need</span></div>
      {carried ? <div className="save-row"><span className="sr-ico minus">−</span><b>{inr(carried)}</b><span>{nCarried} tail{nCarried === 1 ? '' : 's'} of risk still carried — the hangar was full</span></div> : null}
    </div>
    <div className="save-edit">
      <label className="se-row"><span>Your cost of one grounded aircraft (AOG)</span><span className="se-in">₹<input type="number" value={aog} step={1000000} min={0} onChange={e => setAog(Math.max(0, +e.target.value))} /></span></label>
      <label className="se-row"><span>Your cost of one scheduled check</span><span className="se-in">₹<input type="number" value={chk} step={100000} min={0} onChange={e => setChk(Math.max(0, +e.target.value))} /></span></label>
      <div className="se-note">* Indicative. Type your operator's real costs and every figure above updates.</div>
    </div>
  </div>
}

// ---------- fleet risk board (schedule-only by default; priced=true adds the rupee column) ----------
export function FleetBoard({ priced = false }: { priced?: boolean }) {
  const { plan, states, sel, selectTail, err } = useTwin()
  if (err) return <p className="muted">⚠ Can't reach the twin API — is the server running? Retrying…</p>
  if (!plan) return <p className="muted">Loading…</p>
  return <div className="board">{plan.map((p: any) => {
    const s = states.find((x: any) => x.tail === p.tail) || {}
    const col = sevCol(s.health, s.grounded)
    const slotCls = p.slot === 'deferred' ? 'def' : p.slot?.startsWith('QUEUED') ? 'q' : 'go'
    const slotLbl = p.slot === 'deferred' ? 'defer' : p.slot?.startsWith('QUEUED') ? 'queued' : 'service'
    return <div key={p.tail} className={`brow ${p.tail === sel ? 'sel' : ''}`} onClick={() => selectTail(p.tail)}>
      <div><div className="bt">{p.tail}</div><div className="bh">{s.grounded ? 'grounded' : p.health + '/100 health'}</div>
        <div className="minibar"><i style={{ width: Math.max(p.health, 4) + '%', background: col }} /></div></div>
      <div className="ba"><span className={`slot ${slotCls}`}>{slotLbl}</span><br />{p.action}</div>
      {priced
        ? <div className={`br ${p.risk ? 'risk' : 'none'}`}>{p.risk ? inr(p.risk) : '—'}</div>
        : <div className="br none" style={{ color: col, fontWeight: 700 }}>{s.grounded ? 'GND' : (s.health ?? '—')}</div>}
    </div>
  })}</div>
}

// ---------- NEW: prediction + confidence + escalation (per tail) ----------
export function PredictionConfidence() {
  const { tail } = useTwin()
  if (!tail) return <p className="muted">Select an aircraft.</p>
  const st = tail.state || {}
  const band = st.rul_band
  if (st.grounded) return <div className="pred"><div className="predverdict red">MAINTENANCE REQUIRED NOW</div><p className="muted">Beyond-limit damage detected — the model does not estimate life past the limit. Escalated to certifying staff.</p></div>
  if (!band) return <p className="muted">No growth trend yet — insufficient scans to predict.</p>
  const spread = band.p90 - band.p10
  const rel = spread / Math.max(band.p50, 1)     // relative band width
  const conf = rel < 0.5 ? 'HIGH' : rel < 1.1 ? 'MEDIUM' : 'LOW'
  const escalate = conf === 'LOW'
  const need = band.p10 < 3000
  return <div className="pred">
    <div className={`predverdict ${need ? 'amber' : 'cy'}`}>{need ? 'MAINTENANCE DUE SOON' : 'HEALTHY — MONITOR'}</div>
    <div className="predrow"><span className="k">Predicted useful life (conservative, P10)</span><b>{band.p10.toLocaleString()} cycles</b></div>
    <div className="predrow"><span className="k">Median estimate (P50)</span><b>{band.p50.toLocaleString()} cycles</b></div>
    <div className="predrow"><span className="k">Model confidence</span><b style={{ color: conf === 'LOW' ? 'var(--amber)' : 'inherit' }}>{conf}</b></div>
    {escalate
      ? <div className="alert warn" style={{ marginTop: 12 }}>⤴ Wide prediction band → auto-escalated to human review. The twin refuses to over-claim precision it doesn't have.</div>
      : <div className="alert ok" style={{ marginTop: 12 }}>Confidence sufficient for an automated condition-based recommendation.</div>}
  </div>
}

// ---------- NEW: tamper-evident hash-chain audit (visual) ----------
export function AuditChain() {
  const [data, setData] = useState<any>(null)
  const load = () => API.getAudit().then(setData).catch(() => setData({ error: true }))
  useEffect(() => { load() }, [])
  if (!data) return <p className="muted">Loading chain…</p>
  if (data.error) return <p className="muted">audit service unavailable</p>
  const short = (h: string) => h ? h.slice(0, 10) : '—'
  return <div className="audit">
    <div className="auditbar">
      <span className={`vbadge ${data.verified ? 'ok' : 'bad'}`}>{data.verified ? '✓ CHAIN VERIFIED' : '✕ TAMPER DETECTED'}</span>
      <span className="muted">{data.count} linked record(s) · SHA-256</span>
      <button className="b" onClick={load} style={{ marginLeft: 'auto' }}>Re-verify</button>
    </div>
    {!data.entries.length ? <p className="muted" style={{ marginTop: 12 }}>No decisions logged yet — raise a work order to append the first block.</p> :
      <div className="chain">
        <div className="block genesis"><span className="bh">{short(data.genesis)}</span><span className="bl">genesis</span></div>
        {data.entries.map((e: any, i: number) => <div key={i} className="block">
          <span className="bh">{short(e.hash)}</span>
          <span className="bl">{e.tail || '—'} · {e.summary}</span>
          {e.citation ? <span className="bcite">cites {e.citation}</span> : null}
        </div>)}
      </div>}
    <p className="muted" style={{ marginTop: 14, lineHeight: 1.6 }}>Each block's hash covers the previous hash + its own body, so editing any past record breaks every link after it — tamper-evidence, not just a log. Export the signed evidence pack: <a className="pdf" href="/api/evidence.pdf" target="_blank" style={{ marginTop: 0 }}>↓ PDF</a></p>
  </div>
}

// ---------- what-if planner ----------
export function WhatIf() {
  const { states } = useTwin()
  const [wout, setWout] = useState<any>(null)
  async function run(defer: string, extra: number) {
    if (!defer && !extra) { setWout(null); return }
    const out: any = {}
    try {
      if (defer) out.defer = { ...(await API.getWhatif(defer)), tail: defer }
      if (extra) out.cap = { ...(await API.getCapacity(extra)), extra }
      setWout(out)
    } catch { setWout({ err: true }) }
  }
  return <div className="whatif">
    <div className="lead">Re-run the priced plan under a different decision — the twin re-optimises and shows the delta.</div>
    <div className="wctl">
      <select onChange={e => run(e.target.value, 0)}>
        <option value="">Defer a tail…</option>
        {states.map((s: any) => <option key={s.tail} value={s.tail}>Defer {s.tail}</option>)}
      </select>
      <select onChange={e => run('', +e.target.value)}>
        <option value="0">Hangar capacity: base</option><option value="1">+1 slot</option><option value="2">+2 slots</option>
      </select>
    </div>
    <div className="wout">
      {wout?.defer && <><div><span className="lbl">Deferring {wout.defer.tail} carries an extra</span> <span className="big">{inr(wout.defer.added_risk)}</span> <span className="lbl">of AOG risk.</span></div>
        <div className="wgrid"><div className="c"><b>{inr(wout.defer.base_net)}</b><span>net · base plan</span></div>
          <div className={`c ${wout.defer.whatif_net - wout.defer.base_net < 0 ? 'hot' : ''}`}><b>{inr(wout.defer.whatif_net)}</b><span>net · deferred</span></div></div></>}
      {wout?.cap && <><div style={{ marginTop: wout.defer ? 14 : 0 }}><span className="lbl">Adding {wout.cap.extra} hangar slot(s) releases</span> <span className="big">{inr(wout.cap.risk_released)}</span> <span className="lbl">of carried AOG risk.</span></div>
        <div className="wgrid"><div className="c"><b>{inr(wout.cap.base_net)}</b><span>net · base capacity</span></div>
          <div className="c hot"><b>{inr(wout.cap.whatif_net)}</b><span>net · +{wout.cap.extra} slot(s)</span></div></div></>}
    </div>
  </div>
}

// ---------- open defects ----------
export function Defects() {
  const { tail, sel } = useTwin()
  if (!tail) return <p className="muted">Select an aircraft.</p>
  const st = tail.state || {}
  if (!(tail.defects || []).length) return <p className="muted">No open defects — {sel} is airworthy.</p>
  return <div>{tail.defects.map((d: any, i: number) => {
    const band = st.rul_band, learned = st.rul_learned
    const pct = Math.min(100, (d.size_mm / (d.limit_mm || d.size_mm)) * 100)
    return <div key={i} className="defect fade-in">
      <div className="top"><span className="dt">{d.defect_type}</span><span className={`g ${d.grade}`}>{(d.grade || '').toUpperCase()}</span></div>
      <div className="loc">ATA {d.ata_zone} · {d.location} · {d.size_mm} / {d.limit_mm ?? '—'} mm ({pct.toFixed(0)}%)</div>
      {band && <div className="band"><div className="bl"><span>RUL band · Monte-Carlo</span><span>cycles to limit</span></div>
        <div className="bandbar"><div className="rng" style={{ left: '8%', right: '8%' }} /><div className="p50" style={{ left: '50%' }} /></div>
        <div className="vals"><span>P10 {band.p10.toLocaleString()}</span><span>P50 {band.p50.toLocaleString()}</span><span>P90 {band.p90.toLocaleString()}</span></div>
        {learned?.updated && <div className="learn">◆ Bayesian learn: prior ±{(learned.prior_sd * 1000).toFixed(0)} → posterior ±{(learned.post_sd * 1000).toFixed(0)} mm/kcyc · ×{learned.tighten.toFixed(1)} tighter after {learned.scans} obs</div>}
      </div>}
      <Spark d={d} />
      {d.history?.length ? <table className="hist"><thead><tr><th>Scan</th><th>Cycles</th><th>Size</th><th>Grade</th></tr></thead>
        <tbody>{d.history.map((r: any, j: number) => <tr key={j}><td>{r.date || '—'}</td><td>{(r.cycles || 0).toLocaleString()}</td><td>{r.size_mm} mm</td><td style={{ textTransform: 'capitalize' }}>{r.grade || ''}</td></tr>)}</tbody></table> : null}
    </div>
  })}</div>
}

// ---------- SHM ----------
export function SHM() {
  const { shm } = useTwin()
  if (!shm) return <p className="muted">Select an aircraft.</p>
  if (!(shm.series || []).length) return <p className="muted">no signal</p>
  return <div className="shm"><ShmSpark d={shm} />
    <div className="desc">Fused strain · acoustic-emission · vibration → damage index (edge sensor stream, EWMA+CUSUM).</div>
    {shm.alert_cycle != null
      ? <div className="alert warn">CUSUM change-point @ +{shm.alert_cycle.toLocaleString()} cyc — inspect before next scheduled check</div>
      : <div className="alert ok">signal stable — no between-inspection divergence</div>}</div>
}

// ---------- spares ----------
export function Spares() {
  const { spares } = useTwin()
  if (!spares) return <p className="muted">Loading…</p>
  if (!(spares.orders || []).length) return <p className="muted">Nothing due within the horizon.</p>
  return <div>{spares.orders.map((o: any, i: number) => <div key={i} className="sprow">
    <span className="k"><b>{o.tail}</b> <span>· {o.kit}</span></span>
    <span className={`v ${o.grounded ? 'now' : ''}`}>{o.grounded ? 'ORDER NOW' : 'by ' + (o.order_by_cycle || 0).toLocaleString() + ' cyc'}</span>
  </div>)}</div>
}

// ---------- federated ----------
export function Federated() {
  const { fed } = useTwin()
  if (!fed) return <p className="muted">Loading…</p>
  const mx = Math.max(...fed.sites.map((s: any) => Math.abs(s.local_err)), 0.001)
  return <div className="fed">
    <div className="big"><b>{fed.global_mean.toFixed(3)}</b><span>mm / 1k cyc · global growth prior (±{fed.global_std_error.toFixed(3)})</span></div>
    {fed.sites.map((s: any, i: number) => <div key={i} className="st"><span className="nm">{s.site}</span><span className="bar"><i style={{ width: Math.min(100, Math.abs(s.local_err) / mx * 100).toFixed(0) + '%' }} /></span><span className="er">±{s.local_std_error.toFixed(3)}</span></div>)}
    {fed.dp && <div className="dp"><span className="eps">ε={fed.dp.epsilon}</span><span>Differential privacy ({fed.dp.mechanism} mechanism, rates clipped to {fed.dp.clip}): DP prior {fed.dp.global_mean} vs plain {fed.global_mean} — only {fed.dp.cost_vs_plain} mm/kcyc of noise buys a formal per-site guarantee.</span></div>}
    <div className="note">4-hangar federation — only (n, mean, var) leaves each hangar. No imagery, no per-tail record ever crosses a site boundary.</div>
  </div>
}

// ---------- certification ----------
export function Cert() {
  const { cert, sel, woAction } = useTwin()
  if (cert === null) return <p className="muted">certification service unavailable</p>
  const cur = cert?.status || null
  const label: any = { DRAFT: 'DRAFT — awaiting signature', SIGNED: 'SIGNED — awaiting close', CLOSED: 'CLOSED' }[cur] || 'not raised'
  return <div className="cert">
    <div className="st">Work order <b>{cert?.wo_id || '—'}</b><span className={`badge2 ${cur === 'DRAFT' ? 'hot' : 'calm'}`}>{label}</span></div>
    <div className="btns">
      <button className="b" disabled={!!cur} onClick={() => woAction('/api/workorder/open?tail=' + sel)}>Draft (agent)</button>
      <button className="b" disabled={cur !== 'DRAFT'} onClick={() => woAction('/api/workorder/sign?wo_id=' + cert.wo_id)}>Sign (cert. staff)</button>
      <button className="b" disabled={cur !== 'SIGNED'} onClick={() => woAction('/api/workorder/close?wo_id=' + cert.wo_id)}>Close</button>
    </div>
    <a className="pdf" href="/api/evidence.pdf" target="_blank">↓ Tamper-evident evidence PDF · hash-chained</a>
  </div>
}

// ---------- copilot: agentic, on-device, model-selectable ----------
const SUGGESTS = [
  'Which aircraft need attention?',
  'SRM limit for a crack at ATA 53?',
  'RUL for an 8 mm crack, 12 mm limit',
  'State of VT-AXB',
  'What is the worst tail right now?',
]
// local models the edge box can load (all run on the Pi, offline)
const MODELS = ['llama3.2:3b', 'qwen2.5:7b', 'phi-3.5:mini', 'mistral:7b']
export function Copilot() {
  const [ask, setAsk] = useState('')
  const [busy, setBusy] = useState(false)
  const [model, setModel] = useState(MODELS[0])
  const [chat, setChat] = useState<any[]>([])
  async function go(q?: string) {
    const question = (q ?? ask).trim(); if (!question || busy) return
    setAsk(''); setBusy(true)
    setChat(c => [...c, { role: 'user', text: question }])
    try {
      const r = await API.ask(question, model)
      setChat(c => [...c, { role: 'bot', text: r.answer, trace: r.tool_trace || [], model }])
    } catch { setChat(c => [...c, { role: 'bot', text: 'No response from the copilot. Check the edge node is running, then ask again.', trace: [], model }]) }
    setBusy(false)
  }
  return <div className="copilot">
    <div className="cpbar">
      <span className="cpmodel">
        <span className="cpdot" />local model
        <select value={model} onChange={e => setModel(e.target.value)}>
          {MODELS.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </span>
      <span className="cpoff">on-device · offline</span>
    </div>

    <div className="chatlog">
      {!chat.length ? <div className="muted" style={{ padding: '8px 0' }}>Ask about a limit, an RUL, a tail's state, or the whole fleet.</div> :
        chat.map((m, i) => m.role === 'user'
          ? <div key={i} className="msg user"><span>{m.text}</span></div>
          : <div key={i} className="msg bot">
            <div className="btext">{m.text}</div>
            {(m.trace || []).map((t: any, j: number) => <div key={j} className="trace">↳ called <b>{t.tool}</b>({Object.keys(t.args || {}).length ? JSON.stringify(t.args) : ''})</div>)}
            <div className="off">{m.model} · tool-calling · citation-gated</div>
          </div>)}
      {busy ? <div className="msg bot"><span className="off">{model} · calling twin tools…</span></div> : null}
    </div>

    <div className="askbar">
      <input value={ask} placeholder="Ask the twin…" onChange={e => setAsk(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') go() }} />
      <button className="b" disabled={busy} onClick={() => go()}>Ask</button>
    </div>
    <div className="suggest">{SUGGESTS.map(s => <span key={s} onClick={() => go(s)}>{s}</span>)}</div>
  </div>
}
