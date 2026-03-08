import { useEffect, useState } from 'react'
import { buyListing, getCards, getMarketplace, sellCard } from '../api/client'

export default function Market() {
  const [listings, setListings] = useState<any[]>([])
  const [cards, setCards] = useState<any[]>([])
  const [selectedCardId, setSelectedCardId] = useState('')
  const [price, setPrice] = useState('100')
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const [m, c] = await Promise.all([getMarketplace(), getCards()])
      setListings(m.data?.listings || [])
      setCards(c.data?.cards || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleSell = async () => {
    if (!selectedCardId) return alert('Select a card first')
    const parsed = Number(price)
    if (!Number.isFinite(parsed) || parsed <= 0) return alert('Enter a valid price')
    try {
      await sellCard({ card_id: selectedCardId, price: Math.floor(parsed) })
      setSelectedCardId('')
      await load()
      alert('Card listed on market')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to list card')
    }
  }

  const handleBuy = async (listingId: number) => {
    setBusyId(listingId)
    try {
      await buyListing(listingId)
      await load()
      alert('Purchase successful')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to buy listing')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div style={{ padding: '16px 16px 90px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>🏪 Marketplace</h3>
      <p style={{ color: '#8888aa', marginTop: 0, fontSize: 13 }}>Buy listed cards or sell cards from your collection.</p>

      <div style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 12, padding: 12, marginBottom: 14 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>List a Card</div>
        <select
          value={selectedCardId}
          onChange={(e) => setSelectedCardId(e.target.value)}
          style={{ width: '100%', marginBottom: 8, padding: 8, borderRadius: 8, background: '#0f1030', color: '#fff', border: '1px solid #2a2760' }}
        >
          <option value="">Select your card</option>
          {cards.map((c: any) => <option key={c.card_id} value={c.card_id}>{c.name || c.card_id} ({c.rarity || 'common'})</option>)}
        </select>
        <input
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder="Price in gold"
          style={{ width: '100%', marginBottom: 8, padding: 8, borderRadius: 8, background: '#0f1030', color: '#fff', border: '1px solid #2a2760' }}
        />
        <button onClick={handleSell} style={{ width: '100%', padding: 10, background: '#6B2EBE', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700 }}>
          Sell Card
        </button>
      </div>

      <h4 style={{ color: '#F4A800', marginBottom: 8 }}>Active Listings</h4>
      {loading && <p>Loading market...</p>}
      {!loading && listings.length === 0 && <p style={{ color: '#8888aa' }}>No active listings.</p>}
      {listings.map((l: any) => (
        <div key={l.listing_id} style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 12, padding: 12, marginBottom: 8 }}>
          <div style={{ fontWeight: 700 }}>{l.card_id}</div>
          <div style={{ color: '#8888aa', fontSize: 12, marginTop: 2 }}>Seller: {l.seller_id}</div>
          <div style={{ marginTop: 6 }}>💰 <b>{Number(l.price || 0).toLocaleString()} gold</b></div>
          <button
            onClick={() => handleBuy(Number(l.listing_id))}
            disabled={busyId === Number(l.listing_id)}
            style={{ marginTop: 8, width: '100%', padding: 10, background: '#F4A800', color: '#000', border: 'none', borderRadius: 8, fontWeight: 700 }}
          >
            {busyId === Number(l.listing_id) ? 'Buying...' : 'Buy'}
          </button>
        </div>
      ))}
    </div>
  )
}
