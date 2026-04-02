import { useEffect, useState } from 'react'
import {
  buyPack,
  checkoutCreatorPack,
  checkoutTierPack,
  getEconomy,
  getPackStore,
} from '../api/client'

function openStripeCheckoutUrl(url: string) {
  const tg = (window as any)?.Telegram?.WebApp
  if (tg?.openLink) {
    tg.openLink(url, { try_instant_view: false })
  } else {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

export default function Store() {
  const [packs, setPacks] = useState<any[]>([])
  const [gold, setGold] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busyPackId, setBusyPackId] = useState<string>('')
  const [busyTier, setBusyTier] = useState<string>('')
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [storeRes, ecoRes] = await Promise.all([getPackStore(), getEconomy()])
      setPacks(storeRes.data?.packs || [])
      setGold(ecoRes.data?.gold || 0)
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to load store')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleBuy = async (packId: string) => {
    setBusyPackId(packId)
    setError('')
    try {
      await buyPack(packId)
      await load()
      alert('Pack purchased! Open it in My Packs.')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Purchase failed')
    } finally {
      setBusyPackId('')
    }
  }

  const handleStripeCreatorPack = async (packId: string) => {
    setBusyPackId(`card:${packId}`)
    setError('')
    try {
      const res = await checkoutCreatorPack(packId)
      const url = res.data?.checkout_url
      if (url) openStripeCheckoutUrl(url)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Could not start card checkout')
    } finally {
      setBusyPackId('')
    }
  }

  const handleStripeTier = async (tier: string) => {
    setBusyTier(tier)
    setError('')
    try {
      const res = await checkoutTierPack(tier)
      const url = res.data?.checkout_url
      if (url) openStripeCheckoutUrl(url)
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Could not start card checkout')
    } finally {
      setBusyTier('')
    }
  }

  if (loading) return <div style={{ padding: 16, paddingBottom: 90 }}>Loading store...</div>

  return (
    <div style={{ padding: '16px 16px 90px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>🛒 Store</h3>
      <p style={{ color: '#8888aa', marginTop: 0, fontSize: 13 }}>
        Buy live packs with gold, or pay with card (Stripe). Cards are delivered after payment completes.
      </p>
      <div style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 10, padding: 10, marginBottom: 14 }}>
        💰 Your Gold: <b>{gold.toLocaleString()}</b>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 700, marginBottom: 8, fontSize: 14 }}>Quick tier packs (card)</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {(['community', 'gold', 'platinum'] as const).map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => handleStripeTier(tier)}
              disabled={busyTier === tier}
              style={{
                padding: '8px 12px',
                background: '#2a2760',
                color: '#fff',
                border: '1px solid #3d3a80',
                borderRadius: 8,
                fontWeight: 600,
                cursor: busyTier === tier ? 'wait' : 'pointer',
              }}
            >
              {busyTier === tier ? '…' : `${tier.charAt(0).toUpperCase() + tier.slice(1)} (USD)`}
            </button>
          ))}
        </div>
      </div>

      {error && <div style={{ color: '#E74C3C', marginBottom: 10 }}>{error}</div>}
      {packs.length === 0 && <p style={{ color: '#8888aa' }}>No packs in store right now.</p>}

      {packs.map((p) => {
        const price = Number(p.price || 0) > 0 ? Number(p.price) : 500
        return (
          <div key={p.pack_id} style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 12, padding: 12, marginBottom: 10 }}>
            <div style={{ fontWeight: 700 }}>{p.name || p.pack_name || p.pack_id}</div>
            <div style={{ color: '#8888aa', fontSize: 12, marginTop: 4 }}>
              {(p.pack_tier || 'community').toUpperCase()} • {(p.card_count || p.cards?.length || 0)} cards
            </div>
            <div style={{ marginTop: 8, fontSize: 13 }}>Price: <b>{price.toLocaleString()} gold</b></div>
            <button
              onClick={() => handleBuy(p.pack_id)}
              disabled={busyPackId === p.pack_id || busyPackId === `card:${p.pack_id}`}
              style={{
                marginTop: 10, width: '100%', padding: '10px 0',
                background: '#F4A800', color: '#000', border: 'none', borderRadius: 8,
                fontWeight: 700, cursor: busyPackId === p.pack_id ? 'wait' : 'pointer',
              }}
            >
              {busyPackId === p.pack_id ? 'Purchasing...' : 'Buy with gold'}
            </button>
            <button
              type="button"
              onClick={() => handleStripeCreatorPack(p.pack_id)}
              disabled={busyPackId === `card:${p.pack_id}` || busyPackId === p.pack_id}
              style={{
                marginTop: 8, width: '100%', padding: '10px 0',
                background: '#1e5a9e', color: '#fff', border: 'none', borderRadius: 8,
                fontWeight: 700, cursor: busyPackId === `card:${p.pack_id}` ? 'wait' : 'pointer',
              }}
            >
              {busyPackId === `card:${p.pack_id}` ? 'Opening checkout…' : 'Pay with card'}
            </button>
          </div>
        )
      })}
    </div>
  )
}
