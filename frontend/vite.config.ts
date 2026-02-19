import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // 生产环境使用 /mapijing/，开发环境使用相对路径
  const base = mode === 'production' ? '/mapijing/' : './'

  return {
    plugins: [react()],
    base,
  }
})
