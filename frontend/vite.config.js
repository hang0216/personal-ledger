import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发环境：前端 http://localhost:5173，后端 http://127.0.0.1:8000
// 联调方式与 api/http.js 的 baseURL 对应（直连 + CORS，spec §8、architecture §11）
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: 'localhost',
    port: 5173,
  },
})