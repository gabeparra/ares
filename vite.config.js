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
      '/sdapi': {
        target: process.env.VITE_SD_API_URL,
        changeOrigin: true,
        secure: false,
        auth: process.env.API_USERNAME && process.env.API_PASSWORD
          ? `${process.env.API_USERNAME}:${process.env.API_PASSWORD}`
          : undefined,
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            // Ensure proper headers are set
            proxyReq.setHeader('Accept', 'application/json')
            if (req.method === 'POST' || req.method === 'PUT') {
              proxyReq.setHeader('Content-Type', 'application/json')
            }
          })
          proxy.on('error', (err, _req, _res) => {
            if (err.code !== 'ECONNREFUSED') {
              console.error('SD API proxy error:', err)
            }
          })
        },
      },
      '/internal': {
        target: process.env.VITE_SD_API_URL,
        changeOrigin: true,
        secure: false,
        auth: process.env.API_USERNAME && process.env.API_PASSWORD
          ? `${process.env.API_USERNAME}:${process.env.API_PASSWORD}`
          : undefined,
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            // Ensure proper headers are set
            proxyReq.setHeader('Accept', 'application/json')
            if (req.method === 'POST' || req.method === 'PUT') {
              proxyReq.setHeader('Content-Type', 'application/json')
            }
          })
          proxy.on('error', (err, _req, _res) => {
            if (err.code !== 'ECONNREFUSED') {
              console.error('SD API proxy error:', err)
            }
          })
        },
      },
      // Ollama Management API proxy (custom API on port 60006, not native Ollama on 11434)
      '/api/ollama': {
        target: process.env.OLLAMA_MANAGEMENT_API_URL,
        changeOrigin: true,
        secure: false,
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            proxyReq.setHeader('Accept', 'application/json')
            if (req.method === 'POST' || req.method === 'PUT') {
              proxyReq.setHeader('Content-Type', 'application/json')
            }
          })
          proxy.on('error', (err, _req, _res) => {
            if (err.code !== 'ECONNREFUSED') {
              console.error('Ollama API proxy error:', err)
            }
          })
        },
      },
    },
  },
  build: {
    outDir: 'web/dist',
    emptyOutDir: true,
  },
})