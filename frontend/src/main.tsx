import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// bundled variable fonts (offline-safe): Sora (display) · Manrope (body) · JetBrains Mono (data)
import '@fontsource-variable/sora'
import '@fontsource-variable/manrope'
import '@fontsource-variable/jetbrains-mono'
import App from './App'
import './index.css'
import './app.css'

createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
)
