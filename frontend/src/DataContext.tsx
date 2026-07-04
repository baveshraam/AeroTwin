import { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react'
import * as API from './api'

// One shared store for the whole app, so every page reads the same live twin data
// and selecting a tail on one page persists to the others.
const Ctx = createContext<any>(null)
export const useTwin = () => useContext(Ctx)

export function TwinProvider({ children }: { children: ReactNode }) {
  const [states, setStates] = useState<any[]>([])
  const [plan, setPlan] = useState<any>(null)
  const [ledger, setLedger] = useState<any>(null)
  const [sel, setSel] = useState<string | null>(null)
  const [tail, setTail] = useState<any>(null)
  const [shm, setShm] = useState<any>(null)
  const [fed, setFed] = useState<any>(null)
  const [spares, setSpares] = useState<any>(null)
  const [cert, setCert] = useState<any>(null)
  const [tele, setTele] = useState<any>(null)
  const [err, setErr] = useState(false)
  const [scrub, setScrub] = useState(0)
  const [fleetStat, setFleetStat] = useState('')
  const selRef = useRef<string | null>(null)

  async function loadFleet() {
    try {
      const f = await API.getFleet()
      setStates(f.states); setPlan(f.plan.plan); setLedger(f.plan.ledger); setErr(false)
      API.getFederated().then(setFed).catch(() => setFed(null))
      API.getSpares().then(setSpares).catch(() => setSpares(null))
      if (!selRef.current && f.states.length) selectTail(f.states[0].tail)
    } catch { setErr(true); setTimeout(loadFleet, 2500) }
  }

  async function selectTail(t: string) {
    setSel(t); selRef.current = t
    try {
      setTail(await API.getTail(t))
      API.getSHM(t).then(setShm).catch(() => setShm(null))
      loadCert()
    } catch { setTail(null) }
    setScrub(0); setFleetStat('')
  }

  async function loadCert() {
    try {
      const wos = (await API.getWorkorders()).work_orders || {}
      setCert(Object.values(wos).find((w: any) => w && w.wo_id && w.history) || {})
    } catch { setCert(null) }
  }
  async function woAction(path: string) { await API.postWO(path); loadCert() }

  async function scrubTo(cyc: number) {
    setScrub(cyc)
    if (cyc === 0) {
      setFleetStat(''); loadFleet()
      if (selRef.current) API.getTail(selRef.current).then(setTail).catch(() => { })
      return
    }
    try {
      const r = await API.getScrub(cyc)
      setStates(r.states); setPlan(r.plan.plan); setLedger(r.plan.ledger)
      const gnd = r.states.filter((s: any) => s.grounded).length
      setFleetStat(`${gnd} grounded · ${r.states.length - gnd} flying`)
      // age the selected aircraft's 3D twin in step with the fleet
      if (selRef.current) API.getTail(selRef.current, cyc).then(setTail).catch(() => { })
    } catch { setFleetStat('⚠ scrub unavailable') }
  }

  async function addAircraft() {
    try {
      const r = await API.addAircraft()
      setStates(r.states); setPlan(r.plan.plan); setLedger(r.plan.ledger)
      return r.added
    } catch { return null }
  }

  useEffect(() => { loadFleet() }, [])
  useEffect(() => {
    const poll = () => API.getTelemetry().then(setTele).catch(() => { })
    poll(); const id = setInterval(poll, 1500); return () => clearInterval(id)
  }, [])

  const value = {
    states, plan, ledger, sel, tail, shm, fed, spares, cert, tele, err, scrub, fleetStat,
    selectTail, scrubTo, woAction, loadFleet, addAircraft,
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
