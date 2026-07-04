import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import ThreeScene, { SceneHandle } from '../ThreeScene'
import { useTwin } from '../DataContext'
import { HealthRing, Copilot } from '../panels'
import { sevCol, inr, attn } from '../api'

// CAS-annunciator status for a tail: GO (airworthy) · CAUTION (degrading) · STOP (grounded)
const statOf = (s: any) => s.grounded ? 'stop' : (s.health != null && s.health < 55) ? 'caution' : 'go'
const STAT_COL: any = { go: 'var(--cyan)', caution: 'var(--amber)', stop: 'var(--red)' }
const PIPELINE = ['SENSE', 'PREDICT', 'TWIN', 'PRESCRIBE', 'PRICE', 'PROVE']

const SIM_MAX = 12000, SIM_STEP = 600
export default function Overview() {
  const scene = useRef<SceneHandle>(null)
  const { tail, sel, states, ledger, scrub, scrubTo, selectTail, addAircraft } = useTwin()
  const [view, setView] = useState('orbit')
  const [playing, setPlaying] = useState(false)
  const [adding, setAdding] = useState(false)
  useEffect(() => { if (tail) scene.current?.setTail(tail) }, [tail])

  // live simulation: advance the fleet through the twin on a clock (▶). A ref tracks the
  // latest cycle so the interval doesn't churn every step.
  const scrubRef = useRef(scrub); scrubRef.current = scrub
  useEffect(() => {
    if (!playing) return
    const id = setInterval(() => {
      const next = scrubRef.current + SIM_STEP
      if (next >= SIM_MAX) { scrubTo(SIM_MAX); setPlaying(false); return }
      scrubTo(next)
    }, 850)
    return () => clearInterval(id)
  }, [playing])

  async function onAdd() { setAdding(true); const t = await addAircraft(); if (t) selectTail(t); setAdding(false) }

  const st = tail?.state || {}
  const grounded = states.filter((s: any) => s.grounded).length
  const caution = states.filter((s: any) => statOf(s) === 'caution').length
  const go = states.length - grounded - caution
  const avg = states.length ? Math.round(states.reduce((a: number, s: any) => a + (s.grounded ? 0 : s.health), 0) / states.length) : 0

  // worst-first ordering for the annunciator
  const ranked = [...states].sort((a: any, b: any) =>
    (b.grounded ? 1 : 0) - (a.grounded ? 1 : 0) || (a.health ?? 100) - (b.health ?? 100))

  return (
    <div className="console">
      {/* ── master status rail ─────────────────────────────── */}
      <div className="rail">
        <Tile k="fleet" v={states.length} sub="tails under twin" />
        <div className="tile">
          <div className="t-k">status</div>
          <div className="t-lamps">
            <span className="lamp go">{go}<i>go</i></span>
            <span className="lamp caution">{caution}<i>caution</i></span>
            <span className="lamp stop">{grounded}<i>stop</i></span>
          </div>
        </div>
        <Tile k="fleet health" v={avg} unit="/100" col={sevCol(avg)} sub="0 = grounded · 100 = pristine" />
        <Tile k="needs attention" v={caution + grounded} col={caution + grounded ? 'var(--amber)' : undefined} sub="tails to action now" />
        <Link to="/planning" className="tile save-tile">
          <div className="t-k">saved this week</div>
          <div className="t-v" style={{ color: 'var(--cyan)' }}>{ledger ? inr(ledger.net_value) : '—'}<span className="save-star">*</span></div>
          <div className="t-sub">indicative — edit costs on Cost →</div>
        </Link>
      </div>

      {/* ── fleet annunciator (the "at a glance" signature) ── */}
      <section className="panel col-fleet">
        <header className="p-head">fleet annunciator
          <button className="addtail" onClick={onAdd} disabled={adding}>{adding ? '…' : '+ add aircraft'}</button>
        </header>
        <div className="annun">
          {ranked.map((s: any) => {
            const stt = statOf(s)
            return <button key={s.tail} className={`ann-row ${s.tail === sel ? 'sel' : ''}`} onClick={() => selectTail(s.tail)}>
              <span className={`ann-lamp ${stt}`} />
              <span className="ann-tail">{s.tail}</span>
              <span className="ann-bar"><i style={{ width: Math.max(s.grounded ? 100 : s.health, 5) + '%', background: STAT_COL[stt] }} /></span>
              <span className="ann-v" style={{ color: STAT_COL[stt] }}>{s.grounded ? 'GND' : s.health}</span>
            </button>
          })}
          {!states.length ? <p className="muted" style={{ padding: 12 }}>Bringing the fleet online…</p> : null}
        </div>
      </section>

      {/* ── twin viewport ──────────────────────────────────── */}
      <section className="col-twin">
        <div className="stage-card">
          <ThreeScene ref={scene} onDefectClick={(i) => scene.current?.flyToDefect(i)} />
          <div className="hud-frame" />
          <div className="loadmsg" id="loadmsg"><span className="spin" /><span id="loadtxt">Loading airframe…</span></div>
          <div className="badge">
            <HealthRing health={st.health ?? 0} grounded={st.grounded} />
            <div>
              <div className="tl">{sel || '—'}</div>
              <div className="sub">{tail ? (st.grounded ? 'grounded · beyond limit' : `health ${st.health}/100 · ${st.open_defects || 0} open`) : 'select an aircraft'}</div>
              {st.action ? <div className="act"><span className={`pill ${attn(st.health, st.grounded) ? 'hot' : 'calm'}`}>{(st.basis || 'plan').toUpperCase()}</span><br />{st.action}</div> : null}
            </div>
          </div>
          <div className="viewbtns">
            {['orbit', 'top', 'side'].map(v => <button key={v} className={view === v ? 'on' : ''} onClick={() => { setView(v); scene.current?.setView(v) }}>{v[0].toUpperCase() + v.slice(1)}</button>)}
          </div>
        </div>

        {/* fleet time machine — ▶ plays the WHOLE fleet forward through the twin */}
        <div className="scrubcard">
          <div className="scrub inline">
            <button className={`playbtn ${playing ? 'on' : ''}`} onClick={() => setPlaying(p => !p)} title={playing ? 'pause' : 'run simulation'}>{playing ? '❚❚' : '▶'}</button>
            <label>simulate&nbsp;fleet</label>
            <span className="val">{scrub === 0 ? 'today' : `+${scrub.toLocaleString()} cyc`}</span>
            <input type="range" min={0} max={SIM_MAX} step={250} value={scrub} onChange={e => { setPlaying(false); scrubTo(+e.target.value) }} />
            {scrub > 0
              ? <button className="resetbtn" onClick={() => { setPlaying(false); scrubTo(0) }}>reset</button>
              : <span className="fs">every tail ages together</span>}
          </div>
          <Link to="/pipeline" className="stage-rail" title="ML pipeline">
            {PIPELINE.map((p, i) => <span key={p} className="stg">{p}{i < PIPELINE.length - 1 ? <em>▸</em> : null}</span>)}
          </Link>
        </div>
      </section>

      {/* ── copilot console ────────────────────────────────── */}
      <section className="panel col-copilot">
        <header className="p-head">mro copilot<span className="p-note">tool-calling</span></header>
        <Copilot />
      </section>
    </div>
  )
}

function Tile({ k, v, unit, sub, col }: { k: string, v: any, unit?: string, sub?: string, col?: string }) {
  return <div className="tile">
    <div className="t-k">{k}</div>
    <div className="t-v" style={{ color: col }}>{v}{unit ? <span className="t-u">{unit}</span> : null}</div>
    {sub ? <div className="t-sub">{sub}</div> : null}
  </div>
}
