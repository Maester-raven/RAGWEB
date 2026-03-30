import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // /v1 代理默认走本地 HTTP 服务，避免把明文 HTTP 误配成 HTTPS 触发 EPROTO
  // 可通过 VITE_PROXY_TARGET 覆盖，例如：https://your-api-host
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://localhost:8000'
  const chatBackendTarget = env.VITE_CHAT_BACKEND_URL || 'http://localhost:9000'

  return {
    base: '/RAGWEB/',
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
        '/api/chat': {
          target: chatBackendTarget,
          changeOrigin: true,
          xfwd: true,
          secure: false,
        },
        '/v1': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})