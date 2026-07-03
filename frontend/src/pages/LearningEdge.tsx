import { useTwin } from '../DataContext'
import { Federated, Copilot } from '../panels'

export default function LearningEdge() {
  const { tele } = useTwin()
  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Learn · Edge · Trust</div>
        <h1>Fleet Learning &amp; Edge</h1>
        <p>The twin gets smarter across the fleet without any raw data leaving a site (federated learning + differential privacy), and the MRO copilot answers questions by calling real tools into the twin — all offline, on edge hardware.</p>
      </div>

      <div className="card">
        <h2>Federated fleet learning <span className="tt">FedAvg · DP</span> <span className="synthflag" style={{ fontSize: 8, padding: '2px 7px' }}>SIMULATED</span></h2>
        <Federated />
      </div>

      <div className="card">
        <h2>Edge telemetry <span className="tt">on-device · offline</span></h2>
        {tele ? <div className="grid c4">
          <div className="metric"><div className="v accent">{tele.fps}{tele.simulated ? '*' : ''}</div><div className="k">frames / sec {tele.simulated ? '(simulated on laptop; real psutil on the Pi)' : ''}</div></div>
          <div className="metric"><div className="v">{tele.latency_ms}<span style={{ fontSize: 14 }}>ms</span></div><div className="k">inference latency</div></div>
          <div className="metric"><div className="v">{tele.cpu_temp_c}<span style={{ fontSize: 14 }}>°C</span></div><div className="k">CPU temperature</div></div>
          <div className="metric"><div className="v">{tele.power_w}<span style={{ fontSize: 14 }}>W</span></div><div className="k">power draw · network OFFLINE</div></div>
        </div> : <p className="muted">Loading telemetry…</p>}
      </div>

      <div className="card">
        <h2>MRO copilot <span className="tt">offline · tool-router</span></h2>
        <Copilot />
      </div>

      <div className="card">
        <h2>Honesty notes</h2>
        <p className="muted" style={{ lineHeight: 1.7, fontSize: 12.5 }}>
          The algorithms are real and tested; where data is a stand-in it is labelled. The SHM stream, the 4-site federation, and the laptop telemetry HUD are <b>synthetic/simulated</b> until field hardware and a data-sharing agreement exist — the detector, twin math, Monte-Carlo RUL, Bayesian learning, FedAvg + differential privacy, and hash-chained audit are all real. SRM limits and rupee/capacity constants are illustrative and editable.
        </p>
      </div>
    </div>
  )
}
