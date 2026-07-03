import { useTwin } from '../DataContext'
import { HealthRing, Defects, SHM, Cert, PredictionConfidence } from '../panels'
import { attn } from '../api'

export default function AircraftHealth() {
  const { states, sel, tail, selectTail } = useTwin()
  const st = tail?.state || {}

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Predict → Explain</div>
        <h1>Aircraft Health</h1>
        <p>Per-tail predictive detail: structural health index, remaining-useful-life bands, between-inspection monitoring, and the certifiable, manual-cited work order. Pick an aircraft below.</p>
      </div>

      <div className="tailchips">
        {states.map((s: any) => <button key={s.tail} className={s.tail === sel ? 'on' : ''} onClick={() => selectTail(s.tail)}>{s.tail}</button>)}
      </div>

      <div className="card">
        <div className="tail-hero">
          <HealthRing health={st.health ?? 0} grounded={st.grounded} size={92} />
          <div>
            <div className="tl">{sel || '—'}</div>
            <div className="sub">{tail ? (st.grounded ? 'grounded · beyond limit' : `${st.open_defects || 0} open defects · RUL P10 ${st.rul_band ? st.rul_band.p10.toLocaleString() : '—'} cyc · ${st.current_cycles?.toLocaleString?.() || '—'} cycles`) : 'select an aircraft'}</div>
            {st.action ? <div className="act"><span className={`pill ${attn(st.health, st.grounded) ? 'hot' : 'calm'}`}>{(st.basis || 'plan').toUpperCase()}</span><br />{st.action}</div> : null}
          </div>
        </div>
      </div>

      <div className="grid c2">
        <div className="card">
          <h2>Prediction &amp; confidence <span className="tt">maintenance-need · RUL</span></h2>
          <PredictionConfidence />
        </div>
        <div className="card">
          <h2>Certification · tamper-evident</h2>
          <Cert />
        </div>
      </div>

      <div className="card">
        <h2>Open defects · RUL bands <span className="tt">{sel || '—'}</span></h2>
        <Defects />
      </div>

      <div className="card">
        <h2>Between-inspection monitoring (SHM) <span className="synthflag" style={{ fontSize: 8, padding: '2px 7px' }}>SYNTHETIC STREAM</span></h2>
        <p className="caption" style={{ marginTop: 0, marginBottom: 14 }}>Between scheduled inspections, fused sensor signals are watched for a sudden change (a CUSUM change-point) that means a defect is growing faster than expected — an early warning to inspect before the next check.</p>
        <SHM />
      </div>
    </div>
  )
}
