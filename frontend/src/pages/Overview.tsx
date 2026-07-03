import { useEffect, useRef, useState } from 'react'
import ThreeScene, { SceneHandle } from '../ThreeScene'
import { useTwin } from '../DataContext'
import { HealthRing, FleetGrid, PriorityAlerts, FleetBoard } from '../panels'
import { sevCol, attn } from '../api'

export default function Overview() {
  const scene = useRef<SceneHandle>(null)
  const { tail, sel, states, scrub, scrubTo, fleetStat } = useTwin()
  const [view, setView] = useState('orbit')

  useEffect(() => { if (tail) scene.current?.setTail(tail) }, [tail])

  const st = tail?.state || {}
  const grounded = states.filter((s: any) => s.grounded).length
  const openFindings = states.reduce((a: number, s: any) => a + (s.open_defects || 0), 0)
  const avg = states.length ? Math.round(states.reduce((a: number, s: any) => a + (s.grounded ? 0 : s.health), 0) / states.length) : 0

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Predictive Aircraft Health · Edge Digital Twin</div>
        <h1>Fleet Overview</h1>
        <p>A live, per-tail digital twin running offline at the edge. It reads each aircraft's condition, predicts what will need maintenance before it fails, and tells you which jets need attention now. Select any aircraft to inspect it.</p>
      </div>

      {/* the 3D twin — a spacious, minimalist hero */}
      <div className="stage-card">
        <ThreeScene ref={scene} onDefectClick={(i) => scene.current?.flyToDefect(i)} />
        <div className="loadmsg" id="loadmsg"><span className="spin" /><span id="loadtxt">Loading airframe…</span></div>
        <div className="badge">
          <HealthRing health={st.health ?? 0} grounded={st.grounded} />
          <div>
            <div className="tl">{sel || '—'}</div>
            <div className="sub">{tail ? (st.grounded ? 'grounded · beyond limit' : `health ${st.health}/100 · ${st.open_defects || 0} open`) : 'select an aircraft'}</div>
            {st.action ? <div className="act"><span className={`pill ${attn(st.health, st.grounded) ? 'hot' : 'calm'}`}>{(st.basis || 'plan').toUpperCase()}</span><br />{st.action}</div> : null}
          </div>
        </div>
        <div className="legend">
          <div className="hd">airframe health</div>
          <div>healthy <span className="sw cy" /></div>
          <div><b style={{ color: 'var(--amber)' }}>needs attention</b> <span className="sw am" /></div>
          <div>grounded <span className="sw rd" /></div>
        </div>
        <div className="viewbtns">
          {['orbit', 'top', 'side'].map(v => <button key={v} className={view === v ? 'on' : ''} onClick={() => { setView(v); scene.current?.setView(v) }}>{v[0].toUpperCase() + v.slice(1)}</button>)}
        </div>
        <div className="hint">drag to orbit · scroll to zoom</div>
      </div>

      {/* time-projection — clearly explained */}
      <div className="card">
        <h2>Look into the future <span className="tt">condition projection</span></h2>
        <p className="caption" style={{ marginTop: 0, marginBottom: 14 }}>Drag the slider to <b>fast-forward the fleet in flight cycles</b>. The twin grows every known defect at its measured rate and re-checks it against the limit — so you can see <b>which aircraft will need maintenance, and roughly when</b>, before it happens.</p>
        <div className="scrub inline">
          <label>Fast-forward</label>
          <span className="val">{scrub === 0 ? 'today' : `+${scrub.toLocaleString()} flight cycles`}</span>
          <input type="range" min={0} max={12000} step={250} value={scrub} onChange={e => scrubTo(+e.target.value)} />
          <span className="fs" dangerouslySetInnerHTML={{ __html: (fleetStat || '').replace(/(\d+)/g, '<b>$1</b>') }} />
        </div>
      </div>

      {/* priority alerts — the "what needs attention now" list */}
      <div className="card">
        <h2>Needs attention now <span className="tt">priority alerts</span></h2>
        <p className="caption" style={{ marginTop: 0, marginBottom: 14 }}>The twin ranks the fleet by urgency so nothing slips: <b>red</b> = grounded / act now, <b>amber</b> = degrading fast, <b>grey</b> = at-risk but queued behind hangar capacity.</p>
        <PriorityAlerts />
      </div>

      {/* fleet maintenance schedule (the condition-based schedule; no rupees here) */}
      <div className="card">
        <h2>Maintenance schedule <span className="tt">condition-based, not calendar</span></h2>
        <p className="caption" style={{ marginTop: 0, marginBottom: 14 }}>Every aircraft ranked worst-first, with the twin's recommended action — <b>service now</b>, <b>service this window</b>, or <b>safe to defer</b> — decided by actual condition instead of a fixed calendar. The number on the right is the health index.</p>
        <FleetBoard />
      </div>

      {/* key metrics — each with a plain-English description */}
      <div className="grid c4">
        <div className="metric"><div className="v">{states.length}</div><div className="k">aircraft (tails) under twin management</div></div>
        <div className="metric"><div className="v" style={{ color: grounded ? 'var(--red)' : undefined }}>{grounded}</div><div className="k">grounded — beyond-limit, not airworthy</div></div>
        <div className="metric"><div className="v" style={{ color: sevCol(avg) }}>{avg}<span style={{ fontSize: 15, color: 'var(--ink-3)' }}>/100</span></div><div className="k">average fleet health (100 = pristine, 0 = grounded)</div></div>
        <div className="metric"><div className="v">{openFindings}</div><div className="k">open findings awaiting action across the fleet</div></div>
      </div>

      {/* fleet strip */}
      <div className="card">
        <h2>Fleet <span className="tt">click a card to inspect</span></h2>
        <FleetGrid />
        <p className="caption">Each card shows the aircraft's <b>tail number</b>, its <b>health index (x/100)</b>, and how many <b>open findings</b> it has. The coloured bar is the same health, at a glance.</p>
      </div>
    </div>
  )
}
