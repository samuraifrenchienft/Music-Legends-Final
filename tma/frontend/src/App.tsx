import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation, useNavigate } from 'react-router-dom'
import { useLaunchParams, useSignal } from '@telegram-apps/sdk-react'
import { backButton, themeParams } from '@telegram-apps/sdk'
import NavBar from './components/NavBar'
import Home from './pages/Home'
import Collection from './pages/Collection'
import Pack from './pages/Pack'
import Battle from './pages/Battle'
import Daily from './pages/Daily'

function Inner() {
  const location = useLocation()
  const navigate = useNavigate()
  const bgColor  = useSignal(themeParams.backgroundColor)
  const txtColor = useSignal(themeParams.textColor)

  // Handle BackButton — show on all non-root pages
  useEffect(() => {
    const isRoot = location.pathname === '/'
    try {
      if (backButton.isSupported()) {
        isRoot ? backButton.hide() : backButton.show()
        const off = backButton.onClick(() => navigate(-1))
        return () => off()
      }
    } catch {
      // Outside Telegram — ignore
    }
  }, [location.pathname, navigate])

  // Handle deep link startParam — e.g. battle_X9K2QR
  const lp = useLaunchParams()
  useEffect(() => {
    const sp: string = (lp as any).startParam || (lp as any).tgWebAppStartParam || ''
    if (sp.startsWith('battle_')) {
      navigate(`/battle?id=${sp.replace('battle_', '')}`)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{
      minHeight: 'var(--tg-viewport-height, 100vh)',
      backgroundColor: bgColor || '#0D0B2E',
      color: txtColor || '#ffffff',
      maxWidth: 480,
      margin: '0 auto',
    }}>
      <Routes>
        <Route path="/"           element={<Home />} />
        <Route path="/collection" element={<Collection />} />
        <Route path="/packs"      element={<Pack />} />
        <Route path="/battle"     element={<Battle />} />
        <Route path="/daily"      element={<Daily />} />
      </Routes>
      <NavBar />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Inner />
    </BrowserRouter>
  )
}
