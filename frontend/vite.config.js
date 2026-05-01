import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // 优先使用 process.env（Docker 容器注入），其次 .env 文件，最后 fallback 到 localhost
  const apiBase = process.env.VITE_API_BASE_URL || env.VITE_API_BASE_URL || 'http://localhost:3001'

  return {
    plugins: [
      vue(),
      // 自动按需导入 Element Plus 组件
      AutoImport({
        resolvers: [ElementPlusResolver()],
        imports: ['vue', 'vue-router', 'pinia'],
        dts: false,
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: false,
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        // 开发时代理 API 请求到后端
        '/api': {
          target: apiBase,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          // 按模块分割 chunk
          manualChunks: {
            'element-plus': ['element-plus'],
            'vue-ecosystem': ['vue', 'vue-router', 'pinia'],
          },
        },
      },
    },
  }
})
