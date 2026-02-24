import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 生产环境使用 /mapijing/，开发环境使用相对路径
  const base = mode === 'production' ? '/mapijing/' : './'

  return {
    plugins: [react()],
    base,
    server: {
      host: '0.0.0.0',  // 监听所有网络接口，允许局域网访问
      https: {
        key: fs.readFileSync(path.resolve(__dirname, 'key.pem')),
        cert: fs.readFileSync(path.resolve(__dirname, 'cert.pem')),
      },
      proxy: {
        // 代理 WebSocket 连接到远程服务器
        '/mapijing/ws': {
          target: 'wss://ai.chenchi.cc',
          changeOrigin: true,
          ws: true,
          secure: true,
          rewrite: (path) => path,
        },
        // 代理 API 请求到远程服务器
        '/mapijing/api': {
          target: 'https://ai.chenchi.cc',
          changeOrigin: true,
          secure: true,
          rewrite: (path) => path,
        },
      },
    },
  }
})
