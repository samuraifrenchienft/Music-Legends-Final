import { useEffect, useState, useCallback } from 'react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedbackNotificationOccurred } from '@telegram-apps/sdk'
import AnimatedCard from '../components/AnimatedCard'
import { getEconomy, claimDaily } from '../api/client'

export default function Daily() {
  const [economy, setEconomy] = useState<any>(null)
  const [claiming, setClaiming] = useState(false)
  const [claimed, setClaimed] = useState(false)
  const [cards, setCards] = useState<any[]>([])
  const [timeLeft, setTimeLeft] = useState('')
  const [canClaim, setCanClaim] = useState(false)

  const loadEconomy = useCallback(() => {
    getEconomy().then(r => {
      setEconomy(r.data)
      const last = r.data.last_daily_claim
      if (!last) { setCanClaim(true); return }
      const next = new Date(last)
      next.setHours(next.getHours() + 24)
      setCanClaim(next.getTime() - Date.now() <= 0)
    })
  }, [])

  useEffect(() => { loadEconomy() }, [loadEconomy])

  // Live countdown ticker
  useEffect(() => {
    const tick = () => {
      if (!economy?.last_daily_claim) return
      const next = new Date(economy.last_daily_claim)
      next.setHours(next.getHours() + 24)
      const diff = next.getTime() - Date.now()
      if (diff <= 0) { setCanClaim(true); setTimeLeft(''); return }
      const h = Math.floor(diff / 3600000)
      const m = Math.floor((diff % 3600000) / 60000)
      const s = Math.floor((diff % 60000) / 1000)
      setTimeLeft(`${h}h ${m}m ${s}s`)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [economy])

  const handleClaim = async () => {
    setClaiming(true)
    try {
      const r = await claimDaily()
      setCards(r.data.cards || [])
      setClaimed(true)
      setCanClaim(false)
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('success')
      loadEconomy()
    } catch (e: any) {
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('error')
      alert(e.response?.data?.detail || 'Already claimed today')
    } finally {
      setClaiming(false)
    }
  }

  useEffect(() => {
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    if (canClaim && !claimed) {
      setMainButtonParams({ text: '?? Claim Daily Reward', isEnabled: !claiming, isVisible: true, backgroundColor: '#2ECC71', textColor: '#000' })
      const off = onMainButtonClick(handleClaim)
      return () => { off(); unmountMainButton() }
    }
    setMainButtonParams({ isVisible: false })
    return () => { unmountMainButton() }
  }, [canClaim, claimed, claiming]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ padding: '20px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>?? Daily Reward</h3>

      {economy && (
        <div style={{ background: '#1a1740', borderRadius: 12, padding: '12px 16px', marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>
              {'??'.repeat(Math.min(economy.daily_streak || 0, 7))} {economy.daily_streak || 0} day streak
            </div>
            <div style={{ color: '#8888aa', fontSize: 12 }}>?? {economy.gold?.toLocaleString()} gold</div>
          </div>
          <div style={{ fontSize: 32 }}>{(economy.daily_streak || 0) >= 7 ? '??' : '??'}</div>
        </div>
      )}

      {!canClaim && !claimed && timeLeft && (
        <div style={{ textAlign: 'center', padding: '24px 0' }}>
          <div style={{ color: '#8888aa', fontSize: 14 }}>Next reward in</div>
          <div style={{ color: '#F4A800', fontSize: 32, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>{timeLeft}</div>
        </div>
      )}

      {claimed && cards.length > 0 && (
        <>
          <p style={{ color: '#2ECC71', textAlign: 'center', marginBottom: 12 }}>✅ Claimed! Here are your cards:</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {cards.map((card, i) => (
              <AnimatedCard key={i} card={card} revealOnMount delay={i * 200} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
