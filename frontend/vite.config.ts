import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const apiPort = Number(process.env.DODGEBALL_API_PORT ?? 8000)
const appPort = Number(process.env.DODGEBALL_APP_PORT ?? 5173)

export default defineConfig({
  plugins: [
    tailwindcss(),
    react()
  ],
  server: {
    host: '127.0.0.1',
    port: appPort,
    strictPort: true,
    proxy: {
      '/api': `http://127.0.0.1:${apiPort}`,
    },
  },
})
