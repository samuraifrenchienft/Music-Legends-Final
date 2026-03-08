import { useEffect, useState } from 'react'
import { buyPack, getEconomy, getPackStore } from '../api/client'

export default function Store() {
  const [packs, setPacks] = useState<any[]>([])
  const [gold, setGold] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busyPackId, setBusyPackId] = useState<string>('')
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

  if (loading) return <div style={{ padding: 16, paddingBottom: 90 }}>Loading store...</div>

  return (
    <div style={{ padding: '16px 16px 90px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>🛒 Store</h3>
      <p style={{ color: '#8888aa', marginTop: 0, fontSize: 13 }}>Buy live packs with gold.</p>
      <div style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 10, padding: 10, marginBottom: 14 }}>
        💰 Your Gold: <b>{gold.toLocaleString()}</b>
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
              disabled={busyPackId === p.pack_id}
              style={{
                marginTop: 10, width: '100%', padding: '10px 0',
                background: '#F4A800', color: '#000', border: 'none', borderRadius: 8,
                fontWeight: 700, cursor: busyPackId === p.pack_id ? 'wait' : 'pointer',
              }}
            >
              {busyPackId === p.pack_id ? 'Purchasing...' : 'Buy Pack'}
            </button>
          </div>
        )
      })}
    </div>
  )
}
