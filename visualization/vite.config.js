import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // Relative base so assets resolve under the bucket path
  // (https://storage.googleapis.com/gmdata-adaptive-benchmark/) instead of the
  // storage.googleapis.com origin root, which 404s and yields a blank page.
  base: './',
  plugins: [react()],
})
