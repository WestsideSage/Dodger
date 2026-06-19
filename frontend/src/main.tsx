import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource-variable/archivo';
import '@fontsource-variable/fraunces';
import '@fontsource/geist-sans';
import '@fontsource/geist-mono';
import './styles/tokens.css';
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
