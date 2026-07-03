import { Ledger, FleetBoard, WhatIf, Spares } from '../panels'

export default function FleetPlanning() {
  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Prescribe → Price</div>
        <h1>Fleet Planning &amp; Rupee Ledger</h1>
        <p>The twin doesn't stop at a prediction — it prescribes a hangar-capacity-constrained service plan and prices every decision in rupees against the blind calendar. Change a decision and watch the plan re-optimise live.</p>
      </div>

      <div className="grid c2">
        <div className="card"><h2>Prescriptive plan · rupee ledger</h2><Ledger /></div>
        <div className="card"><h2>What-if planner <span className="tt">re-price live</span></h2><WhatIf /></div>
      </div>

      <div className="card">
        <h2>Fleet risk board <span className="tt">predict → prescribe → price</span></h2>
        <FleetBoard />
      </div>

      <div className="card" style={{ maxWidth: 640 }}>
        <h2>Spares to pre-stage <span className="tt">RUL-driven</span></h2>
        <Spares />
      </div>
    </div>
  )
}
