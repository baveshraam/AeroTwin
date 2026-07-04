import { useEffect, useMemo, useState } from 'react'
import { getNgafidBoard, getNgafidFlight, CYAN, AMBER, RED } from '../api'

const PAGE = 100 // ponytail: render in chunks; virtualise if 7k rows ever need to be on screen at once

const riskCol = (r: number, th: any) => r >= (th?.ground ?? 0.7) ? RED : r >= (th?.monitor ?? 0.45) ? AMBER : CYAN
const band = (b: any) => b?.p50 == null ? '—' : `${b.p10}–${b.p50}–${b.p90} d`

function Detail({ idx, onClose }: { idx: number, onClose: () => void }) {
  const [d, setD] = useState<any>(null)
  useEffect(() => { setD(null); getNgafidFlight(idx).then(setD).catch(() => setD({ error: 'unreachable' })) }, [idx])
  if (!d) return <div className="card nb-detail"><p className="muted">Loading flight {idx}…</p></div>
  if (d.error) return <div className="card nb-detail"><p className="muted">⚠ {d.error}</p></div>
  return <div className="card nb-detail fade-in">
    <div className="nb-dhead">
      <h2 style={{ margin: 0 }}>Flight #{d.master_index} <span className="tt">worst pre-event flight of this episode</span></h2>
      <button className="b" onClick={onClose}>close</button>
    </div>
    <div className="nb-dgrid">
      <div className="cell"><b style={{ color: riskCol(d.risk, null) }}>{(d.risk * 100).toFixed(0)}%</b><span>maintenance-need risk</span></div>
      <div className="cell"><b>{band(d.rul_days)}</b><span>days to event · P10–P50–P90</span></div>
      <div className="cell"><b style={{ textTransform: 'uppercase' }}>{d.truth}</b><span>ground truth (labelled dataset)</span></div>
    </div>
    <div className="nb-why">
      <div className="k">Why — straight from the maintenance record, nothing fabricated:</div>
      {(d.why || []).map((w: string, i: number) => <div key={i} className="nb-whyrow">▸ {w}</div>)}
    </div>
    <div className="nb-action">{d.action}</div>
  </div>
}

export default function RiskBoard() {
  const [data, setData] = useState<any>(null)
  const [q, setQ] = useState('')
  const [act, setAct] = useState('')          // '' | 'pull' | 'monitor' | 'fly'
  const [limit, setLimit] = useState(PAGE)
  const [sel, setSel] = useState<number | null>(null)

  useEffect(() => { getNgafidBoard().then(setData).catch(() => setData({ ready: false, hint: "can't reach the twin API" })) }, [])

  const rows = useMemo(() => {
    if (!data?.rows) return []
    const needle = q.toLowerCase()
    return data.rows.filter((r: any) =>
      (!act || r.action.startsWith(act)) &&
      (!needle || r.tail.toLowerCase().includes(needle) || r.issue.toLowerCase().includes(needle) || r.system.toLowerCase().includes(needle)))
  }, [data, q, act])

  if (!data) return <div className="page"><p className="muted">Loading the fleet board…</p></div>
  if (!data.ready) return <div className="page"><div className="card"><p className="muted">⚠ {data.hint}</p></div></div>

  const th = data.thresholds
  const counts = { pull: 0, monitor: 0, fly: 0 } as any
  data.rows.forEach((r: any) => { counts[r.action.split(' ')[0]]++ })

  return <div className="page">
    <div className="page-head">
      <div className="eyebrow">Sense → Predict</div>
      <h1>Fleet Risk Board</h1>
      <p>{data.model.n_episodes.toLocaleString()} real maintenance episodes from {data.model.n_flights.toLocaleString()} NGAFID flights,
        ranked worst-first by risk at the latest pre-event flight. {data.source}.</p>
    </div>

    <div className="card nb-model">
      <span className="mr-st serving" style={{ fontSize: 8, padding: '2px 7px' }}>SCORING MODEL</span>
      <span className="muted" style={{ fontSize: 11 }}> {data.model.formula}</span>
    </div>

    <div className="nb-ctl">
      <input value={q} placeholder="Filter by tail / issue / system…" onChange={e => { setQ(e.target.value); setLimit(PAGE) }} />
      {[['', `all ${data.rows.length}`], ['pull', `pull forward ${counts.pull}`], ['monitor', `monitor ${counts.monitor}`], ['fly', `fly ${counts.fly}`]]
        .map(([v, l]) => <button key={v} className={`b ${act === v ? 'on' : ''}`} onClick={() => { setAct(v); setLimit(PAGE) }}>{l}</button>)}
    </div>

    {sel != null && <Detail idx={sel} onClose={() => setSel(null)} />}

    <div className="board">
      <div className="nb-row nb-head">
        <span>aircraft</span><span>issue · system</span><span>risk now</span><span>peak</span><span>RUL band</span><span>action · why</span>
      </div>
      {rows.slice(0, limit).map((r: any) => {
        const col = riskCol(r.risk_now, th)
        return <div key={r.tail} className={`nb-row ${sel === r.flight ? 'sel' : ''}`} onClick={() => setSel(r.flight)}>
          <span><b className="bt">{r.tail}</b><span className="bh"> · {r.flights} flt</span></span>
          <span className="nb-issue">{r.issue}<i>{r.system}</i></span>
          <span><b style={{ color: col }}>{(r.risk_now * 100).toFixed(0)}%</b>
            <span className="minibar"><i style={{ width: Math.max(r.risk_now * 100, 4) + '%', background: col }} /></span></span>
          <span className="muted">{(r.risk_peak * 100).toFixed(0)}%</span>
          <span className="mono">{band(r.rul_days)}</span>
          <span className="nb-act"><span className={`slot ${r.action.startsWith('pull') ? 'q' : r.action.startsWith('monitor') ? 'def' : 'go'}`}>{r.action.split(' ')[0]}</span> {r.why[1] || r.why[0]}</span>
        </div>
      })}
    </div>
    {rows.length > limit && <button className="b nb-more" onClick={() => setLimit(l => l + PAGE * 4)}>show more · {rows.length - limit} hidden</button>}
  </div>
}
