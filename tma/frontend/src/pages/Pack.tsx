import { useEffect, useState } from 'react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedbackNotificationOccurred, showPopup } from '@telegram-apps/sdk'
import AnimatedCard from '../components/AnimatedCard'
import { getPacks, openPack } from '../api/client'

type Phase = 'list' | 'revealing' | 'results'

export default function Pack() {
  const [packs, setPacks] = useState<any[]>([])
  const [phase, setPhase] = useState<Phase>('list')
  const [pendingPack, setPendingPack] = useState<any>(null)
  const [revealedCards, setRevealedCards] = useState<any[]>([])
  const [revealIndex, setRevealIndex] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getPacks()
      .then(r => { setPacks(r.data.packs); setLoading(false) })
      .catch(() => { setError('Failed to load packs. Please close and reopen the app.'); setLoading(false) })
  }, [])

  const handleOpenPack = async (pack: any) => {
    let confirmed = true
    if (showPopup.isAvailable()) {
      try {
        const btn = await showPopup({
          title: `Open ${pack.pack_name}?`,
          message: `This will open your ${pack.pack_tier?.toUpperCase() || ''} pack.`,
          buttons: [
            { id: 'open', type: 'default', text: 'Open It!' },
            { id: 'cancel', type: 'cancel' },
          ],
        })
        confirmed = btn === 'open'
      } catch {
        confirmed = window.confirm(`Open ${pack.pack_name}?`)
      }
    } else {
      confirmed = window.confirm(`Open ${pack.pack_name}?`)
    }
    if (!confirmed) return

    setPendingPack(pack)
    setPhase('revealing')
    setRevealedCards([])
    setRevealIndex(0)

    try {
      const r = await openPack(pack.pack_id)
      setRevealedCards(r.data.cards)
    } catch (e: any) {
      setPhase('list')
      alert(e.response?.data?.detail || 'Failed to open pack')
    }
  }

  // Staggered card reveal — one every 0.8s
  useEffect(() => {
    if (phase !== 'revealing' || revealedCards.length === 0) return
    if (revealIndex >= revealedCards.length) {
      setTimeout(() => setPhase('results'), 600)
      return
    }
    const t = setTimeout(() => {
      if (hapticFeedbackNotificationOccurred.isAvailable()) {
        hapticFeedbackNotificationOccurred(
          (revealedCards[revealIndex]?.rarity || 'common') === 'mythic' ? 'success' : 'warning'
        )
      }
      setRevealIndex(i => i + 1)
    }, 800)
    return () => clearTimeout(t)
  }, [revealIndex, revealedCards, phase])

  // MainButton on results screen
  useEffect(() => {
    if (phase !== 'results') return
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('success')
    setMainButtonParams({ text: '✅ Done', isEnabled: true, isVisible: true, backgroundColor: '#2ECC71' })
    const off = onMainButtonClick(() => {
      getPacks().then(r => setPacks(r.data.packs))
      setPhase('list')
    })
    return () => { off(); unmountMainButton() }
  }, [phase])

  if (loading) return <div style={{ padding: 16, paddingBottom: 80, color: '#8888aa' }}>Loading packs...</div>
  if (error) return <div style={{ padding: 16, paddingBottom: 80, color: '#E74C3C' }}>{error}</div>

  if (phase === 'list') return (
    <div style={{ padding: '16px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 14 }}>📦 My Packs ({packs.length})</h3>
      {packs.length === 0 && (
        <p style={{ textAlign: 'center', color: '#888', marginTop: 40 }}>
          No packs yet. Claim your daily reward to get started!
        </p>
      )}
      {packs.map(pack => (
        <div key={pack.pack_id} style={{
          background: '#1a1740', borderRadius: 12, padding: 14, marginBottom: 10,
          border: '1px solid #2a2760',
        }}>
          <div style={{ fontWeight: 700 }}>{pack.pack_name}</div>
          <div style={{ color: '#8888aa', fontSize: 12, marginTop: 2 }}>
            {pack.pack_tier?.toUpperCase()} • {(pack.cards || []).length} cards
          </div>
          <button onClick={() => handleOpenPack(pack)} style={{
            marginTop: 10, width: '100%', padding: '10px 0',
            background: '#6B2EBE', color: '#fff', border: 'none',
            borderRadius: 8, fontWeight: 700, fontSize: 14, cursor: 'pointer',
          }}>
            🎴 Open Pack
          </button>
        </div>
      ))}
    </div>
  )

  if (phase === 'revealing') return (
    <div style={{ padding: '16px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', textAlign: 'center' }}>Opening {pendingPack?.pack_name}...</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 16 }}>
        {revealedCards.slice(0, revealIndex).map((card, i) => (
          <AnimatedCard key={i} card={card} revealOnMount delay={i * 100} />
        ))}
      </div>
    </div>
  )

  return (
    <div style={{ padding: '16px 16px 100px' }}>
      <h3 style={{ color: '#F4A800', textAlign: 'center', marginBottom: 16 }}>🎉 Pack Opened!</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        {revealedCards.map((card, i) => (
          <AnimatedCard key={i} card={card} />
        ))}
      </div>
    </div>
  )
}
