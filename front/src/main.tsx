import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css'; // Імпорт стилів

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
      <ToastContainer />
  </StrictMode>,
)
