import { NavLink, Route, Routes } from 'react-router-dom'
import { TwinProvider } from './DataContext'
import Overview from './pages/Overview'
import RiskBoard from './pages/RiskBoard'
import MLPipeline from './pages/MLPipeline'
import FleetPlanning from './pages/FleetPlanning'
import AircraftHealth from './pages/AircraftHealth'
import CopilotAudit from './pages/CopilotAudit'
import LearningEdge from './pages/LearningEdge'

// Edge-node identity: the whole point is that this runs on a sealed, offline box —
// so the status reads device + airgap, not a reel of jittering fake sensor numbers.
function Hud() {
  return <div className="hud">
    <span className="edge-node"><span className="en-led" />Raspberry&nbsp;Pi&nbsp;5 · 8&nbsp;GB</span>
    <span className="edge-air">✈ airplane mode · no network</span>
  </div>
}

function Shell() {
  return <>
    <nav className="nav">
      <div className="brand"><span className="dot" /><b>AeroTwin</b><s>·Edge</s></div>
      <div className="navlinks">
        <NavLink to="/" end>Console</NavLink>
        <NavLink to="/board">Fleet Risk</NavLink>
        <NavLink to="/pipeline">ML Pipeline</NavLink>
        <NavLink to="/aircraft">Aircraft</NavLink>
        <NavLink to="/copilot">Audit</NavLink>
        <NavLink to="/learning">Fleet Learning</NavLink>
        <NavLink to="/planning">Cost</NavLink>
      </div>
      <Hud />
    </nav>
    <div className="container">
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/board" element={<RiskBoard />} />
        <Route path="/pipeline" element={<MLPipeline />} />
        <Route path="/aircraft" element={<AircraftHealth />} />
        <Route path="/copilot" element={<CopilotAudit />} />
        <Route path="/learning" element={<LearningEdge />} />
        <Route path="/planning" element={<FleetPlanning />} />
      </Routes>
    </div>
  </>
}

export default function App() {
  return <TwinProvider><Shell /></TwinProvider>
}
