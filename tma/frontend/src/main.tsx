import React from 'react'
import ReactDOM from 'react-dom/client'
import { init, expandViewport, viewport, themeParams } from '@telegram-apps/sdk'
import App from './App'
import './index.css'

// Initialise TMA SDK — all calls wrapped; throws UnknownEnvError outside Telegram
try {
  init()
  expandViewport()
  viewport.mount()
  viewport.bindCssVars()
  themeParams.mountSync()
  themeParams.bindCssVars()
} catch {
  // Running in browser outside Telegram — dev mode, continue normally
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
