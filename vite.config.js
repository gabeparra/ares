import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            // Suppress connection refused errors - backend may not be ready yet
            if (err.code !== 'ECONNREFUSED') {
              console.error('Proxy error:', err)
            }
          })
        },
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            // Suppress connection refused errors - backend may not be ready yet
            if (err.code !== 'ECONNREFUSED') {
              console.error('WebSocket proxy error:', err)
            }
          })
        },
      },
      '/admin': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'web/dist',
    emptyOutDir: true,
  },
})

