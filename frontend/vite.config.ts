import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1300,
    rolldownOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/three/')) {
            return 'three-core'
          }
          if (
            id.includes('node_modules/@react-three/') ||
            id.includes('node_modules/three-stdlib/')
          ) {
            return 'r3f-drei'
          }
        },
      },
    },
  },
})
