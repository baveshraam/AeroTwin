import { useTwin } from '../DataContext'
import { Federated, Copilot } from '../panels'

export default function LearningEdge() {
  const { tele } = useTwin()
  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Learn · Edge · Trust</div>
        <h1>Fleet Learning &amp; Edge</h1>
        <p>The twin gets smarter across the fleet without any raw data leaving a site — federated learning with differential privacy — and the copilot answers by calling real tools into the twin, all offline on edge hardware.</p>
      </div>

      <div className="card">
        <h2>Federated fleet learning <span className="tt">FedAvg · DP</span></h2>
        <Federated />
      </div>

      <div className="card">
        <h2>Edge telemetry <span className="tt">on-device · offline</span></h2>
        {tele ? <div className="grid c4">
          <div className="metric"><div className="v accent">{tele.fps}</div><div className="k">frames / sec</div></div>
          <div className="metric"><div className="v">{tele.latency_ms}<span style={{ fontSize: 14 }}>ms</span></div><div className="k">inference latency</div></div>
          <div className="metric"><div className="v">{tele.cpu_temp_c}<span style={{ fontSize: 14 }}>°C</span></div><div className="k">CPU temperature</div></div>
          <div className="metric"><div className="v">{tele.power_w}<span style={{ fontSize: 14 }}>W</span></div><div className="k">power draw · network OFFLINE</div></div>
        </div> : <p className="muted">Loading telemetry…</p>}
      </div>

      <div className="card">
        <h2>MRO copilot <span className="tt">on-device · tool-calling</span></h2>
        <Copilot />
      </div>
    </div>
  )
}
