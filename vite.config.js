import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // Permite acceso desde fuera del contenedor
    strictPort: true,
    watch: {
      usePolling: true, // Necesario para hot-reload en Docker
    },
    hmr: process.env.VITE_HMR_HOST
      ? {
        host: process.env.VITE_HMR_HOST,
        clientPort: Number(process.env.VITE_HMR_CLIENT_PORT || 443),
        protocol: process.env.VITE_HMR_PROTOCOL || 'wss',
      }
      : true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://backend:8000',
        changeOrigin: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            if (err.code !== 'ECONNREFUSED') {
              console.error('Proxy error:', err)
            }
          })
        },
      },
      '/ws': {
        target: process.env.VITE_WS_URL || 'ws://backend:8000',
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            if (err.code !== 'ECONNREFUSED') {
              console.error('WebSocket proxy error:', err)
            }
          })
        },
      },
      '/admin': {
        target: process.env.VITE_API_URL || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'web/dist',
    emptyOutDir: true,
  },
})