import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// bundled fonts (offline-safe): Space Grotesk (display/body) · IBM Plex Mono (data/labels).
// latin subset only — the app ships no other scripts, so don't bundle cyrillic/greek/etc.
import '@fontsource-variable/space-grotesk'
import '@fontsource/ibm-plex-mono/latin-400.css'
import '@fontsource/ibm-plex-mono/latin-500.css'
import '@fontsource/ibm-plex-mono/latin-600.css'
import '@fontsource/ibm-plex-mono/latin-700.css'
import App from './App'
import './index.css'
import './app.css'

createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
)
