import { useEffect, useState } from 'react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton } from '@telegram-apps/sdk'
import { useNavigate } from 'react-router-dom'
import { getMe } from '../api/client'

export default function Home() {
  const [user, setUser] = useState<any>(null)
  const navigate = useNavigate()

  useEffect(() => {
    getMe().then(r => setUser(r.data)).catch(console.error)
  }, [])

  // MainButton → "Open Packs"
  useEffect(() => {
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    setMainButtonParams({ text: '📦 Open Packs', isEnabled: true, isVisible: true, backgroundColor: '#F4A800', textColor: '#000000' })
    const off = onMainButtonClick(() => navigate('/packs'))
    return () => { off(); unmountMainButton() }
  }, [navigate])

  if (!user) return (
    <div style={{ padding: 24, textAlign: 'center', paddingBottom: 80 }}>
      <div style={{ color: '#8888aa' }}>Loading...</div>
    </div>
  )

  const LOGO = 'https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeiehxk5zhdxidab4qtuxg6lblrasxcxb2bkj6a3ipyjue5f7pzo3qi'

  return (
    <div style={{ padding: '20px 16px', paddingBottom: 100 }}>
      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <img src={LOGO} alt="Music Legends" style={{ width: 72, height: 72, borderRadius: '50%', border: '2px solid #F4A800' }} />
        <h2 style={{ color: '#F4A800', margin: '10px 0 4px' }}>Music Legends</h2>
        <p style={{ color: '#8888aa', margin: 0, fontSize: 13 }}>
          Welcome back, {user.username}!{user.is_new ? ' 🎉 New player!' : ''}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
        {[
          { label: '💰 Gold',    value: user.gold?.toLocaleString() },
          { label: '⭐ XP',      value: user.xp?.toLocaleString() },
          { label: '⚔️ Battles', value: user.total_battles },
          { label: '🏆 Wins',    value: user.wins },
        ].map(s => (
          <div key={s.label} style={{
            background: '#1a1740', borderRadius: 12, padding: '14px 12px',
            textAlign: 'center', border: '1px solid #2a2760',
          }}>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{s.value ?? '—'}</div>
            <div style={{ color: '#8888aa', fontSize: 12, marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
