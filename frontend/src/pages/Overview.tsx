import { useEffect, useRef, useState } from 'react'
import ThreeScene, { SceneHandle } from '../ThreeScene'
import { useTwin } from '../DataContext'
import { HealthRing, FleetGrid } from '../panels'
import { inr, sevCol, attn } from '../api'

export default function Overview() {
  const scene = useRef<SceneHandle>(null)
  const { tail, sel, states, ledger, scrub, scrubTo, fleetStat } = useTwin()
  const [view, setView] = useState('orbit')

  // drive the 3D whenever the shared selected-tail changes
  useEffect(() => { if (tail) scene.current?.setTail(tail) }, [tail])

  const st = tail?.state || {}
  const grounded = states.filter((s: any) => s.grounded).length
  const avg = states.length ? Math.round(states.reduce((a: number, s: any) => a + (s.grounded ? 0 : s.health), 0) / states.length) : 0

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Predictive Aircraft Health · Edge Digital Twin</div>
        <h1>Fleet Overview</h1>
        <p>A live, per-tail digital twin running offline on the edge. The airframe is tinted by health; amber markers are open findings. Select any aircraft to inspect it, or run the twin forward in time.</p>
      </div>

      {/* the 3D twin, now a spacious hero card */}
      <div className="stage-card">
        <ThreeScene ref={scene} onDefectClick={(i) => scene.current?.flyToDefect(i)} />
        <div className="loadmsg" id="loadmsg"><span className="spin" /><span id="loadtxt">Loading airframe…</span></div>

        <div className="badge">
          <HealthRing health={st.health ?? 0} grounded={st.grounded} />
          <div>
            <div className="tl">{sel || '—'}</div>
            <div className="sub">{tail ? (st.grounded ? 'grounded · beyond limit' : `${st.open_defects || 0} open · RUL P10 ${st.rul_band ? st.rul_band.p10.toLocaleString() : '—'} cyc`) : 'select an aircraft'}</div>
            {st.action ? <div className="act"><span className={`pill ${attn(st.health, st.grounded) ? 'hot' : 'calm'}`}>{(st.basis || 'plan').toUpperCase()}</span><br />{st.action}</div> : null}
          </div>
        </div>

        <div className="legend">
          <div className="hd">aircraft health</div>
          <div>healthy <span className="sw cy" /></div>
          <div><b style={{ color: 'var(--amber)' }}>attention</b> <span className="sw am" /></div>
          <div>grounded <span className="sw rd" /></div>
          <div style={{ marginTop: 6 }}><b style={{ color: 'var(--accent)' }}>◉</b> defect · click</div>
        </div>

        <div className="viewbtns">
          {['orbit', 'top', 'side'].map(v => <button key={v} className={view === v ? 'on' : ''} onClick={() => { setView(v); scene.current?.setView(v) }}>{v[0].toUpperCase() + v.slice(1)}</button>)}
        </div>
        <div className="hint">drag to orbit · scroll to zoom · click a defect</div>
      </div>

      {/* time-scrub */}
      <div className="card">
        <h2>Run the twin forward <span className="tt">Paris-law growth projection</span></h2>
        <div className="scrub inline">
          <label>Cycles ahead</label>
          <span className="val">{scrub === 0 ? 'now' : `+${scrub.toLocaleString()} cyc`}</span>
          <input type="range" min={0} max={12000} step={250} value={scrub} onChange={e => scrubTo(+e.target.value)} />
          <span className="fs" dangerouslySetInnerHTML={{ __html: (fleetStat || '').replace(/(\d+)/g, '<b>$1</b>') }} />
        </div>
      </div>

      {/* key metrics */}
      <div className="grid c4">
        <div className="metric"><div className="v accent">{ledger ? inr(ledger.net_value) : '—'}</div><div className="k">net value this window vs blind calendar</div></div>
        <div className="metric"><div className="v">{states.length}</div><div className="k">tails under twin management</div></div>
        <div className="metric"><div className="v" style={{ color: grounded ? 'var(--red)' : undefined }}>{grounded}</div><div className="k">grounded · beyond limit</div></div>
        <div className="metric"><div className="v" style={{ color: sevCol(avg) }}>{avg}</div><div className="k">average fleet health index</div></div>
      </div>

      {/* fleet strip */}
      <div className="card">
        <h2>Fleet <span className="tt">click to inspect</span></h2>
        <FleetGrid />
      </div>
    </div>
  )
}
