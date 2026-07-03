import { Ledger, FleetBoard, WhatIf, Spares } from '../panels'

// Secondary module (moved to the end): the prescribe-and-price economics layer.
export default function FleetPlanning() {
  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow">Secondary module · economics</div>
        <h1>Planning &amp; Cost</h1>
        <p>An optional economics layer on top of the predictions: it turns the maintenance schedule into a hangar-capacity-constrained plan and prices it in rupees against a blind calendar. Every money constant is illustrative and editable.</p>
      </div>

      <div className="grid c2">
        <div className="card"><h2>Priced plan · rupee ledger</h2><Ledger /></div>
        <div className="card"><h2>What-if planner <span className="tt">re-price live</span></h2><WhatIf /></div>
      </div>

      <div className="card">
        <h2>Priced fleet plan <span className="tt">risk in ₹</span></h2>
        <p className="caption" style={{ marginTop: 0, marginBottom: 14 }}>The same schedule as the Overview, with each aircraft's estimated aircraft-on-ground risk in rupees.</p>
        <FleetBoard priced />
      </div>

      <div className="card" style={{ maxWidth: 640 }}>
        <h2>Spares to pre-stage <span className="tt">RUL-driven</span></h2>
        <Spares />
      </div>
    </div>
  )
}
