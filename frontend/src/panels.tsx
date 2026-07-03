import { useState } from 'react'
import { useTwin } from './DataContext'
import * as API from './api'
import { inr, sevCol, attn } from './api'

const ACCENT = '#e0842a'

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

// ---------- rupee ledger ----------
export function Ledger() {
  const { ledger } = useTwin()
  if (!ledger) return <p className="muted">Loading…</p>
  return <>
    <div className="hero"><div className="v">{inr(ledger.net_value)}</div><div className="k">net value this maintenance window vs blind calendar</div></div>
    <div className="grid3">
      <div className="cell hot"><b>{inr(ledger.aog_risk_avoided)}</b><span>AOG risk avoided</span></div>
      <div className="cell"><b>{inr(ledger.downtime_recovered)}</b><span>downtime recovered</span></div>
      <div className={`cell ${ledger.aog_risk_carried ? 'hot' : ''}`}><b>{ledger.aog_risk_carried ? inr(ledger.aog_risk_carried) : ledger.twin_serviced + '/' + ledger.calendar_checks}</b><span>{ledger.aog_risk_carried ? 'AOG risk carried' : 'serviced · cap ' + ledger.capacity}</span></div>
    </div>
  </>
}

// ---------- fleet risk board ----------
export function FleetBoard() {
  const { plan, states, sel, selectTail, err } = useTwin()
  if (err) return <p className="muted">⚠ Can't reach the twin API — is the server running? Retrying…</p>
  if (!plan) return <p className="muted">Loading…</p>
  return <div className="board">{plan.map((p: any) => {
    const s = states.find((x: any) => x.tail === p.tail) || {}
    const col = sevCol(s.health, s.grounded)
    const slotCls = p.slot === 'deferred' ? 'def' : p.slot?.startsWith('QUEUED') ? 'q' : 'go'
    const slotLbl = p.slot === 'deferred' ? 'defer' : p.slot?.startsWith('QUEUED') ? 'queued' : 'service'
    return <div key={p.tail} className={`brow ${p.tail === sel ? 'sel' : ''}`} onClick={() => selectTail(p.tail)}>
      <div><div className="bt">{p.tail}</div><div className="bh">{s.grounded ? 'grounded' : p.health + '/100'}</div>
        <div className="minibar"><i style={{ width: Math.max(p.health, 4) + '%', background: col }} /></div></div>
      <div className="ba"><span className={`slot ${slotCls}`}>{slotLbl}</span><br />{p.action}</div>
      <div className={`br ${p.risk ? 'risk' : 'none'}`}>{p.risk ? inr(p.risk) : '—'}</div>
    </div>
  })}</div>
}

// ---------- fleet strip -> responsive grid ----------
export function FleetGrid() {
  const { states, sel, selectTail } = useTwin()
  return <div className="fleet-grid">{states.map((s: any) => {
    const col = sevCol(s.health, s.grounded)
    return <div key={s.tail} className={`fcard ${attn(s.health, s.grounded) ? 'attn' : ''} ${s.tail === sel ? 'sel' : ''}`} onClick={() => selectTail(s.tail)}>
      <div className="ft">{s.tail}{s.grounded ? <span className="pill">GROUNDED</span> : null}</div>
      <div className="fm">{s.grounded ? 'beyond limit' : s.health + '/100 · ' + s.open_defects + ' open'}</div>
      <div className="hbar"><div style={{ width: Math.max(s.health, 4) + '%', background: col }} /></div>
    </div>
  })}</div>
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
    <div className="desc">Fused strain · acoustic-emission · vibration → damage index (synthetic edge stream, EWMA+CUSUM).</div>
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
    <div className="note"><b>Simulated</b> 4-hangar federation — the FedAvg + DP math is real; there is no field federation yet. Only (n, mean, var) leaves each hangar — no imagery, no per-tail record.</div>
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

// ---------- copilot ----------
export function Copilot() {
  const [ask, setAsk] = useState('')
  const [answer, setAnswer] = useState<any>(null)
  async function go(q?: string) {
    const question = (q ?? ask).trim(); if (!question) return
    setAsk(question); setAnswer({ thinking: true })
    try { setAnswer(await API.ask(question)) } catch { setAnswer({ error: true }) }
  }
  return <div className="copilot">
    <div className="lead">Deterministic offline tool-router (no LLM required): parses intent and calls real tools into the twin — SRM limits, Monte-Carlo RUL, tail state — under a citation guardrail. Optional local LLM (Ollama) adds prose.</div>
    <div className="askbar">
      <input value={ask} placeholder="SRM limit for a crack at ATA 53?" onChange={e => setAsk(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') go() }} />
      <button className="b" onClick={() => go()}>Ask</button>
    </div>
    <div className="suggest">{['SRM limit for a crack at ATA 53?', 'RUL for an 8 mm crack, 12 mm limit', 'state of VT-AXB'].map(s => <span key={s} onClick={() => go(s)}>{s}</span>)}</div>
    <div className="answer">
      {answer?.thinking ? <span className="off">…thinking (calling twin tools)</span> :
        answer?.error ? <span className="off">copilot error</span> :
          answer ? <>{answer.answer}
            {(answer.tool_trace || []).map((t: any, i: number) => <div key={i} className="trace">  ↳ {t.tool}({JSON.stringify(t.args)})</div>)}
            {!answer.llm && <span className="off">(deterministic tool-router — start Ollama for free-form prose)</span>}
          </> : null}
    </div>
  </div>
}
