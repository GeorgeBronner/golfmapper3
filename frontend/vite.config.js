import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test-setup.js'],
  },
  plugins: [
    react(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    extensions: ['.js', '.jsx', '.json']
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true
    },
    allowedHosts: true,
    proxy: {
      // Backend routers are mounted at /api/v1 (see backend/app/main.py),
      // matching what services/api.js requests — no rewrite needed.
      '/api': {
        target: `http://${process.env.BACKEND_SERVER_IP || '127.0.0.1'}:${process.env.BACKEND_PORT || '8005'}`,
        changeOrigin: true,
        // Without this the backend's rate limiter (keyed on X-Forwarded-For)
        // sees every proxied request as the same peer, so unrelated tabs
        // share one rate-limit bucket per endpoint in local dev.
        xfwd: true
      }
    }
  }
});
