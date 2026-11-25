import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/** Dev server for the live simulator. Proxies /api to the isolated API only. */
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    strictPort: true,
    proxy: {
      '/api': 'http://127.0.0.1:5002',
    },
  },
})
