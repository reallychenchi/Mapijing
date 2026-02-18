import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.tsx'
import { E2ETest } from './pages/E2ETest'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/e2e-test" element={<E2ETest />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
