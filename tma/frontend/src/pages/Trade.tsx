import { useEffect, useMemo, useState } from 'react'
import { acceptTrade, cancelTrade, createTrade, getCards, getTrades } from '../api/client'

export default function Trade() {
  const [cards, setCards] = useState<any[]>([])
  const [trades, setTrades] = useState<any[]>([])
  const [partnerId, setPartnerId] = useState('')
  const [offeredIds, setOfferedIds] = useState('')
  const [requestedIds, setRequestedIds] = useState('')
  const [offeredGold, setOfferedGold] = useState('0')
  const [requestedGold, setRequestedGold] = useState('0')
  const [busyTradeId, setBusyTradeId] = useState('')
  const [creating, setCreating] = useState(false)

  const cardHints = useMemo(
    () => cards.slice(0, 8).map((c: any) => `${c.card_id} (${c.name || 'card'})`),
    [cards]
  )

  const load = async () => {
    const [c, t] = await Promise.all([getCards(), getTrades()])
    setCards(c.data?.cards || [])
    setTrades(t.data?.trades || [])
  }

  useEffect(() => { load().catch(() => undefined) }, [])

  const parseIds = (raw: string) => raw.split(',').map((s) => s.trim()).filter(Boolean)

  const onCreate = async () => {
    const pid = Number(partnerId)
    if (!Number.isFinite(pid) || pid <= 0) return alert('Enter partner Telegram ID')
    setCreating(true)
    try {
      await createTrade({
        partner_id: Math.floor(pid),
        offered_card_ids: parseIds(offeredIds),
        requested_card_ids: parseIds(requestedIds),
        offered_gold: Math.max(0, Math.floor(Number(offeredGold) || 0)),
        requested_gold: Math.max(0, Math.floor(Number(requestedGold) || 0)),
      })
      setPartnerId('')
      setOfferedIds('')
      setRequestedIds('')
      setOfferedGold('0')
      setRequestedGold('0')
      await load()
      alert('Trade created')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to create trade')
    } finally {
      setCreating(false)
    }
  }

  const onAccept = async (tradeId: string) => {
    setBusyTradeId(tradeId)
    try {
      await acceptTrade(tradeId)
      await load()
      alert('Trade accepted')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to accept trade')
    } finally {
      setBusyTradeId('')
    }
  }

  const onCancel = async (tradeId: string) => {
    setBusyTradeId(tradeId)
    try {
      await cancelTrade(tradeId)
      await load()
      alert('Trade cancelled')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Failed to cancel trade')
    } finally {
      setBusyTradeId('')
    }
  }

  return (
    <div style={{ padding: '16px 16px 90px' }}>
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>🤝 Trade Center</h3>
      <p style={{ color: '#8888aa', marginTop: 0, fontSize: 13 }}>
        Create direct trades and manage pending offers.
      </p>

      <div style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 12, padding: 12, marginBottom: 14 }}>
        <div style={{ fontWeight: 700, marginBottom: 8 }}>Create Trade</div>
        <input value={partnerId} onChange={(e) => setPartnerId(e.target.value)} placeholder="Partner Telegram ID" style={inputStyle} />
        <textarea value={offeredIds} onChange={(e) => setOfferedIds(e.target.value)} placeholder="Offered card IDs (comma-separated)" style={textareaStyle} />
        <textarea value={requestedIds} onChange={(e) => setRequestedIds(e.target.value)} placeholder="Requested card IDs (comma-separated)" style={textareaStyle} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <input value={offeredGold} onChange={(e) => setOfferedGold(e.target.value)} placeholder="Offered gold" style={inputStyle} />
          <input value={requestedGold} onChange={(e) => setRequestedGold(e.target.value)} placeholder="Requested gold" style={inputStyle} />
        </div>
        <button
          onClick={onCreate}
          disabled={creating}
          style={{ width: '100%', marginTop: 8, padding: 10, background: '#6B2EBE', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 700 }}
        >
          {creating ? 'Creating...' : 'Create Trade'}
        </button>
        <div style={{ marginTop: 8, color: '#8888aa', fontSize: 11 }}>
          Card ID hints: {cardHints.join(', ')}
        </div>
      </div>

      <h4 style={{ color: '#F4A800', marginBottom: 8 }}>My Trades</h4>
      {trades.length === 0 && <p style={{ color: '#8888aa' }}>No trades yet.</p>}
      {trades.map((t: any) => (
        <div key={t.id} style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 12, padding: 12, marginBottom: 8 }}>
          <div style={{ fontWeight: 700 }}>Trade #{String(t.id).slice(0, 8)}</div>
          <div style={{ color: '#8888aa', fontSize: 12 }}>Status: {t.status}</div>
          <div style={{ marginTop: 6, fontSize: 12 }}>A→B cards: {(t.cards_a || []).length}, B→A cards: {(t.cards_b || []).length}</div>
          <div style={{ fontSize: 12 }}>Gold: A {t.gold_a || 0} / B {t.gold_b || 0}</div>
          {t.status === 'pending' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
              <button onClick={() => onAccept(t.id)} disabled={busyTradeId === t.id} style={actionBtn('#2ECC71')}>
                Accept
              </button>
              <button onClick={() => onCancel(t.id)} disabled={busyTradeId === t.id} style={actionBtn('#E74C3C')}>
                Cancel
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

const inputStyle = {
  width: '100%',
  marginBottom: 8,
  padding: 8,
  borderRadius: 8,
  background: '#0f1030',
  color: '#fff',
  border: '1px solid #2a2760',
} as const

const textareaStyle = {
  ...inputStyle,
  minHeight: 52,
} as const

const actionBtn = (bg: string) => ({
  width: '100%',
  padding: 9,
  background: bg,
  color: '#fff',
  border: 'none',
  borderRadius: 8,
  fontWeight: 700,
}) as const
