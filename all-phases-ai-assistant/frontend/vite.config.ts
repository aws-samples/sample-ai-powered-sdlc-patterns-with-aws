import react from '@vitejs/plugin-react'
import path from 'path'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    global: 'globalThis',
  },
  build: {
    outDir: 'build',
    sourcemap: true,
  },
  root: '.',
  publicDir: 'public',
  server: {
    port: 3000,
    open: true,
  },
})