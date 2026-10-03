import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  // Saved progress is tied to the page's address, so keep the port fixed.
  server: { port: 5173, strictPort: true },
})
