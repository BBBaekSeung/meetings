import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // 프론트에서 /api/... 로 호출하면
      // 백엔드 http://127.0.0.1:8000 로 프록시하면서
      // 경로의 /api 프리픽스 제거 → /meetings 로 전달
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
