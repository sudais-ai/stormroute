/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const proxyTarget = process.env.API_PROXY_TARGET ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
        // Backend route generation + weather calls take 60-90s; default proxy timeout is 30s.
        proxyTimeout: 120000,
        timeout: 120000,
      },
    },
  },
  // `vite preview` (local production-style serve) needs its own proxy entry:
  // server.proxy does NOT carry over, and API calls would 502 against it.
  preview: {
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET ?? 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  // Phase 8 verification gate fix: Vite's dev pre-bundling corrupts
  // maplibre-gl v6's module-worker URL ("Worker failed to load" ×2). Serving
  // maplibre as raw ESM in dev (with the worker URL set explicitly via
  // `?url` in MapViewport.tsx) fixes worker creation in dev AND prod.
  optimizeDeps: {
    exclude: ['maplibre-gl'],
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    globals: false,
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
