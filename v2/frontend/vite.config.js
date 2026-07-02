import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        timeout: 180000,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        timeout: 180000,
      }
    }
  }
})
