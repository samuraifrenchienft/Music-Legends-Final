import React from 'react'
import ReactDOM from 'react-dom/client'
import { init, viewport, themeParams } from '@telegram-apps/sdk'
import App from './App'
import './index.css'

// Initialise TMA SDK — each call in its own try/catch so one failure
// doesn't block the rest (e.g. expandViewport not available on desktop).
try { init() } catch { /* outside Telegram or already initialised */ }
try { viewport.mount() } catch { /* ignore */ }
try { viewport.expand() } catch { /* ignore */ }
try { viewport.bindCssVars() } catch { /* ignore */ }
try { themeParams.mountSync() } catch { /* ignore */ }
try { themeParams.bindCssVars() } catch { /* ignore */ }

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
