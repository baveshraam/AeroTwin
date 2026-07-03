import { NavLink, Route, Routes } from 'react-router-dom'
import { TwinProvider, useTwin } from './DataContext'
import Overview from './pages/Overview'
import FleetPlanning from './pages/FleetPlanning'
import AircraftHealth from './pages/AircraftHealth'
import CopilotAudit from './pages/CopilotAudit'
import LearningEdge from './pages/LearningEdge'

function Hud() {
  const { tele } = useTwin()
  if (!tele) return <div className="hud" />
  return <div className="hud">
    <div className="chip live" title={tele.simulated ? '* simulated on the laptop; real psutil on the Pi' : ''}>fps<b>{tele.fps}{tele.simulated ? '*' : ''}</b></div>
    <div className="chip">latency<b>{tele.latency_ms}ms</b></div>
    <div className="chip">cpu<b>{tele.cpu_temp_c}°</b></div>
    <div className="chip live">edge<b>OFFLINE</b></div>
  </div>
}

function Shell() {
  return <>
    <nav className="nav">
      <div className="brand"><span className="dot" /><b>AeroTwin</b><s>·Edge</s></div>
      <div className="navlinks">
        <NavLink to="/" end>Overview</NavLink>
        <NavLink to="/aircraft">Aircraft Health</NavLink>
        <NavLink to="/copilot">Copilot &amp; Audit</NavLink>
        <NavLink to="/learning">Fleet Learning</NavLink>
        <NavLink to="/planning">Planning &amp; Cost</NavLink>
      </div>
      <Hud />
    </nav>
    <div className="container">
      <Routes>
        <Route path="/" element={<Overview />} />
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
