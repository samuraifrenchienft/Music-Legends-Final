import { useEffect, useState, useCallback } from 'react'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedbackNotificationOccurred } from '@telegram-apps/sdk'
import AnimatedCard from '../components/AnimatedCard'
import { getEconomy, claimDaily } from '../api/client'

const DAY_SECONDS = 24 * 60 * 60

function parseServerTimestamp(value?: string): Date | null {
  if (!value) return null
  // Backend timestamps are UTC-ish ISO strings and may arrive without timezone.
  // Force UTC when no explicit timezone is present to avoid local-time inflation.
  const hasTz = /[zZ]$|[+-]\d{2}:\d{2}$/.test(value)
  const normalized = hasTz ? value : `${value}Z`
  const dt = new Date(normalized)
  if (Number.isNaN(dt.getTime())) return null
  return dt
}

function getDailyRemainingSeconds(lastClaim?: string): number {
  const last = parseServerTimestamp(lastClaim)
  if (!last) return 0
  const nowMs = Date.now()
  const nextMs = last.getTime() + DAY_SECONDS * 1000
  const raw = Math.floor((nextMs - nowMs) / 1000)
  // Never show >24h cooldown due to timezone/clock anomalies.
  return Math.max(0, Math.min(DAY_SECONDS, raw))
}

export default function Daily() {
  const [economy, setEconomy] = useState<any>(null)
  const [claiming, setClaiming] = useState(false)
  const [claimed, setClaimed] = useState(false)
  const [cards, setCards] = useState<any[]>([])
  const [timeLeft, setTimeLeft] = useState('')
  const [canClaim, setCanClaim] = useState(false)
  const [error, setError] = useState('')

  const loadEconomy = useCallback(() => {
    setError('')
    getEconomy()
      .then(r => {
        setEconomy(r.data)
        const serverCanClaim = Boolean(r.data?.can_claim_daily)
        if (serverCanClaim) {
          setCanClaim(true)
          setTimeLeft('')
          return
        }
        const serverRemaining = Number(r.data?.daily_cooldown_seconds || 0)
        const remaining = serverRemaining > 0 ? serverRemaining : getDailyRemainingSeconds(r.data.last_daily_claim)
        setCanClaim(remaining <= 0)
      })
      .catch((e: any) => setError(`API error ${e?.response?.status || 'network'}: ${e?.response?.data?.detail || e?.message || 'Could not load economy data'}`))
  }, [])

  useEffect(() => { loadEconomy() }, [loadEconomy])

  // Live countdown ticker
  useEffect(() => {
    const tick = () => {
      if (economy?.can_claim_daily) {
        setCanClaim(true)
        setTimeLeft('')
        return
      }
      const remaining = getDailyRemainingSeconds(economy?.last_daily_claim)
      if (remaining <= 0) { setCanClaim(true); setTimeLeft(''); return }
      setCanClaim(false)
      const h = Math.floor(remaining / 3600)
      const m = Math.floor((remaining % 3600) / 60)
      const s = Math.floor(remaining % 60)
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
      setMainButtonParams({ text: '🎁 Claim Daily Reward', isEnabled: !claiming, isVisible: true, backgroundColor: '#2ECC71', textColor: '#000' })
      const off = onMainButtonClick(handleClaim)
      return () => { off(); unmountMainButton() }
    }
    setMainButtonParams({ isVisible: false })
    return () => { unmountMainButton() }
  }, [canClaim, claimed, claiming]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ padding: '20px 16px 80px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>🎁 Daily Reward</h3>

      {error && (
        <div style={{ background: '#3a1a1a', border: '1px solid #E74C3C', borderRadius: 10, padding: '12px 16px', marginBottom: 16, color: '#E74C3C', fontSize: 13 }}>
          {error}
          <button onClick={loadEconomy} style={{ display: 'block', marginTop: 8, background: '#E74C3C', color: '#fff', border: 'none', borderRadius: 6, padding: '6px 12px', cursor: 'pointer' }}>
            Retry
          </button>
        </div>
      )}

      {economy && (
        <div style={{ background: '#1a1740', borderRadius: 12, padding: '12px 16px', marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>
              {'🔥'.repeat(Math.min(economy.daily_streak || 0, 7))} {economy.daily_streak || 0} day streak
            </div>
            <div style={{ color: '#8888aa', fontSize: 12 }}>💰 {economy.gold?.toLocaleString()} gold</div>
          </div>
          <div style={{ fontSize: 32 }}>{(economy.daily_streak || 0) >= 7 ? '🏆' : '🎖️'}</div>
        </div>
      )}

      {!canClaim && !claimed && timeLeft && (
        <div style={{ textAlign: 'center', padding: '24px 0' }}>
          <div style={{ color: '#8888aa', fontSize: 14 }}>Next reward in</div>
          <div style={{ color: '#F4A800', fontSize: 32, fontWeight: 700, fontVariantNumeric: 'tabular-nums' }}>{timeLeft}</div>
        </div>
      )}

      {/* Fallback HTML button when MainButton isn't available */}
      {canClaim && !claimed && !mountMainButton.isAvailable() && (
        <button
          onClick={handleClaim}
          disabled={claiming}
          style={{
            width: '100%', padding: '16px 0', marginTop: 20,
            background: claiming ? '#1a5c3a' : '#2ECC71',
            color: '#000', border: 'none', borderRadius: 12,
            fontWeight: 700, fontSize: 16, cursor: claiming ? 'not-allowed' : 'pointer',
          }}
        >
          {claiming ? 'Claiming...' : '🎁 Claim Daily Reward'}
        </button>
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
