import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy: the FastAPI backend (uvicorn on :8000) still serves the JSON API and the
// 3D model assets. The vendored three.js libs live in public/vendor and are served by Vite.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/model-assets': 'http://127.0.0.1:8000',
      '/static': 'http://127.0.0.1:8000',
    },
  },
})
