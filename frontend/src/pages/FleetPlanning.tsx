import { Ledger, FleetBoard, WhatIf, Spares } from '../panels'

export default function FleetPlanning() {
  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Prescribe · Price</div>
        <h1>Cost &amp; Planning</h1>
        <p>Condition beats the calendar in rupees: the twin turns each prediction into a hangar-capacity-constrained plan and shows exactly what fixing the right jet at the right time is worth.</p>
      </div>

      <div className="grid c2">
        <div className="card"><h2>What condition-based upkeep saved</h2><Ledger /></div>
        <div className="card"><h2>What-if planner <span className="tt">re-price live</span></h2><WhatIf /></div>
      </div>

      <div className="card">
        <h2>Priced fleet plan <span className="tt">AOG risk in ₹</span></h2>
        <FleetBoard priced />
      </div>

      <div className="card" style={{ maxWidth: 640 }}>
        <h2>Spares to pre-stage <span className="tt">RUL-driven</span></h2>
        <Spares />
      </div>
    </div>
  )
}
