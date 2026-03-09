import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      // 保留你原有/v1的代理配置
      '/v1': {
        target: 'http://localhost:6006',
        changeOrigin: true,
      },
      // 新增/api代理配置（对接后端chat接口）
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      }
    },
  },
})