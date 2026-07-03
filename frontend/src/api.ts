// Typed-ish client for the FastAPI twin API. Same endpoints the original index.html called.
const j = async (u: string, opt?: RequestInit) => (await fetch(u, opt)).json()

export const getFleet = () => j('/api/fleet')
export const getTail = (t: string) => j('/api/tail/' + t)
export const getFederated = () => j('/api/federated')
export const getSpares = () => j('/api/spares')
export const getSHM = (t: string) => j('/api/shm/' + t)
export const getWhatif = (defer: string) => j('/api/whatif?defer=' + encodeURIComponent(defer))
export const getCapacity = (extra: number) => j('/api/scenario/capacity?extra=' + extra)
export const getWorkorders = () => j('/api/workorders')
export const postWO = (path: string) => fetch(path, { method: 'POST' }).then(r => r.json())
export const getScrub = (c: number) => j('/api/scrub?cycles=' + c)
export const getTelemetry = () => j('/api/telemetry')
export const getAudit = () => j('/api/audit')
export const ask = (q: string) => j('/api/ask?question=' + encodeURIComponent(q), { method: 'POST' })

// ₹ formatter — identical to the original inr()
export const inr = (n: number) =>
  n >= 1e7 ? '₹' + (n / 1e7).toFixed(2) + ' Cr'
  : n >= 1e5 ? '₹' + (n / 1e5).toFixed(1) + ' L'
  : '₹' + Math.round(n || 0).toLocaleString('en-IN')

// health -> colour, matching the original three-state logic
export const CYAN = '#35e0d0', AMBER = '#f2a93b', RED = '#ff5b6a'
export const attn = (h: number | null | undefined, g?: boolean) => !!g || (h != null && h < 40)
export const sevCol = (h: number | null | undefined, g?: boolean) =>
  g ? RED : (h != null && h < 40 ? AMBER : CYAN)
