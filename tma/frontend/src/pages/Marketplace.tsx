import { useEffect, useState, useCallback } from 'react'
import { hapticFeedbackNotificationOccurred, showPopup } from '@telegram-apps/sdk'
import { getMarketplace, sellCard, buyListing, getCards } from '../api/client'

const RARITY_COLORS: Record<string, string> = {
  common: '#95A5A6', rare: '#4488FF', epic: '#6B2EBE', legendary: '#F4A800', mythic: '#E74C3C',
}

type View = 'browse' | 'sell'

export default function Marketplace() {
  const [view, setView] = useState<View>('browse')
  const [listings, setListings] = useState<any[]>([])
  const [myCards, setMyCards] = useState<any[]>([])
  const [selectedCard, setSelectedCard] = useState<any>(null)
  const [price, setPrice] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const loadListings = useCallback(() => {
    setLoading(true)
    setError('')
    getMarketplace()
      .then(r => { setListings(r.data.listings || []); setLoading(false) })
      .catch(() => { setError('Failed to load marketplace.'); setLoading(false) })
  }, [])

  useEffect(() => { loadListings() }, [loadListings])

  const handleBuy = async (listing: any) => {
    if (busy) return
    let confirmed = true
    if (showPopup.isAvailable()) {
      try {
        const btn = await showPopup({
          title: `Buy ${listing.card_name}?`,
          message: `Cost: ${listing.price} 💰 gold`,
          buttons: [
            { id: 'buy', type: 'default', text: `Buy for ${listing.price} gold` },
            { id: 'cancel', type: 'cancel' },
          ],
        })
        confirmed = btn === 'buy'
      } catch {
        confirmed = window.confirm(`Buy ${listing.card_name} for ${listing.price} gold?`)
      }
    } else {
      confirmed = window.confirm(`Buy ${listing.card_name} for ${listing.price} gold?`)
    }
    if (!confirmed) return

    setBusy(true)
    try {
      await buyListing(listing.listing_id)
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('success')
      loadListings()
    } catch (e: any) {
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('error')
      alert(e.response?.data?.detail || 'Purchase failed')
    } finally {
      setBusy(false)
    }
  }

  const openSellView = () => {
    setLoading(true)
    getCards()
      .then(r => { setMyCards(r.data.cards || []); setLoading(false); setView('sell') })
      .catch(() => { setError('Failed to load your cards.'); setLoading(false) })
  }

  const handleSellSubmit = async () => {
    if (!selectedCard || !price) return
    const priceNum = parseInt(price)
    if (isNaN(priceNum) || priceNum <= 0) { alert('Enter a valid gold price'); return }
    setBusy(true)
    try {
      await sellCard({ card_id: selectedCard.card_id, price: priceNum })
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('success')
      setSelectedCard(null)
      setPrice('')
      setView('browse')
      loadListings()
    } catch (e: any) {
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('error')
      alert(e.response?.data?.detail || 'Failed to list card')
    } finally {
      setBusy(false)
    }
  }

  const tabBar = (
    <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
      <button
        onClick={() => setView('browse')}
        style={{
          flex: 1, padding: '8px 0', borderRadius: 8, border: 'none', cursor: 'pointer',
          fontWeight: 700, fontSize: 13,
          background: view === 'browse' ? '#6B2EBE' : '#1a1740',
          color: view === 'browse' ? '#fff' : '#8888aa',
        }}
      >
        🛒 Browse
      </button>
      <button
        onClick={openSellView}
        style={{
          flex: 1, padding: '8px 0', borderRadius: 8, border: 'none', cursor: 'pointer',
          fontWeight: 700, fontSize: 13,
          background: view === 'sell' ? '#6B2EBE' : '#1a1740',
          color: view === 'sell' ? '#fff' : '#8888aa',
        }}
      >
        💸 Sell Card
      </button>
    </div>
  )

  if (loading) return <div style={{ padding: '8px 0', color: '#8888aa', fontSize: 13 }}>Loading...</div>
  if (error) return (
    <div style={{ padding: '8px 0' }}>
      <div style={{ color: '#E74C3C', fontSize: 13, marginBottom: 10 }}>{error}</div>
      <button
        onClick={loadListings}
        style={{ background: '#6B2EBE', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontWeight: 700 }}
      >
        Retry
      </button>
    </div>
  )

  if (view === 'sell') return (
    <div>
      {tabBar}
      <p style={{ color: '#8888aa', fontSize: 12, marginBottom: 12 }}>Select a card from your collection:</p>
      {myCards.length === 0 && (
        <p style={{ color: '#888', textAlign: 'center', marginTop: 24 }}>No cards to sell.</p>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
        {myCards.map(card => {
          const color = RARITY_COLORS[(card.rarity || 'common').toLowerCase()] || '#95A5A6'
          const isSelected = selectedCard?.card_id === card.card_id
          return (
            <div
              key={card.card_id}
              onClick={() => setSelectedCard(isSelected ? null : card)}
              style={{
                background: isSelected ? '#2a1760' : '#1a1740',
                border: `2px solid ${isSelected ? '#F4A800' : color + '55'}`,
                borderRadius: 10, padding: 10, cursor: 'pointer',
              }}
            >
              {card.image_url && (
                <img
                  src={card.image_url}
                  alt={card.name}
                  style={{ width: '100%', borderRadius: 6, aspectRatio: '16/9', objectFit: 'cover' }}
                />
              )}
              <div style={{ fontWeight: 700, fontSize: 12, marginTop: 6 }}>{card.name}</div>
              <div style={{ color, fontSize: 11 }}>{card.rarity?.toUpperCase()} • ⚡{card.power}</div>
            </div>
          )
        })}
      </div>

      {selectedCard && (
        <div style={{ background: '#1a1740', borderRadius: 12, padding: 14 }}>
          <div style={{ fontWeight: 700, marginBottom: 10 }}>Listing: {selectedCard.name}</div>
          <input
            type="number"
            placeholder="Price in gold 💰"
            value={price}
            onChange={e => setPrice(e.target.value)}
            style={{
              width: '100%', padding: '10px 12px', borderRadius: 8,
              background: '#0D0B2E', color: '#fff', border: '1px solid #6B2EBE',
              fontSize: 14, boxSizing: 'border-box', marginBottom: 10,
            }}
          />
          <button
            onClick={handleSellSubmit}
            disabled={busy || !price}
            style={{
              width: '100%', padding: '12px 0',
              background: busy || !price ? '#2a1760' : '#6B2EBE',
              color: '#fff', border: 'none', borderRadius: 8,
              fontWeight: 700, fontSize: 14, cursor: busy || !price ? 'not-allowed' : 'pointer',
            }}
          >
            {busy ? 'Listing...' : '💸 List for Sale'}
          </button>
        </div>
      )}
    </div>
  )

  // Browse view
  return (
    <div>
      {tabBar}
      {listings.length === 0 && (
        <p style={{ color: '#888', textAlign: 'center', marginTop: 24 }}>No listings right now. Be the first to sell!</p>
      )}
      {listings.map(listing => {
        const color = RARITY_COLORS[(listing.rarity || 'common').toLowerCase()] || '#95A5A6'
        return (
          <div
            key={listing.listing_id}
            style={{
              background: '#1a1740', borderRadius: 12, padding: 12, marginBottom: 10,
              border: `1px solid ${color}44`, display: 'flex', gap: 10, alignItems: 'center',
            }}
          >
            {listing.image_url && (
              <img
                src={listing.image_url}
                alt={listing.card_name}
                style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 8, flexShrink: 0 }}
              />
            )}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {listing.card_name}
              </div>
              <div style={{ color, fontSize: 11 }}>{listing.rarity?.toUpperCase()} • ⚡{listing.power}</div>
              <div style={{ color: '#8888aa', fontSize: 11 }}>By: {listing.seller_username || 'Unknown'}</div>
            </div>
            <button
              onClick={() => handleBuy(listing)}
              disabled={busy}
              style={{
                padding: '8px 12px', background: '#2ECC71', color: '#000',
                border: 'none', borderRadius: 8, fontWeight: 700, fontSize: 13,
                cursor: busy ? 'not-allowed' : 'pointer', flexShrink: 0,
              }}
            >
              {listing.price} 💰
            </button>
          </div>
        )
      })}
    </div>
  )
}
