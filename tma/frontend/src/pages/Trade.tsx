import { useEffect, useMemo, useState } from 'react'
import {
  acceptTrade,
  cancelTrade,
  createTrade,
  getCards,
  getPartnerCards,
  getTrades,
  searchTradePartners,
} from '../api/client'

export default function Trade() {
  const [myCards, setMyCards] = useState<any[]>([])
  const [partnerCards, setPartnerCards] = useState<any[]>([])
  const [trades, setTrades] = useState<any[]>([])
  const [partnerQuery, setPartnerQuery] = useState('')
  const [partnerResults, setPartnerResults] = useState<any[]>([])
  const [selectedPartner, setSelectedPartner] = useState<any>(null)
  const [offeredIds, setOfferedIds] = useState<string[]>([])
  const [requestedIds, setRequestedIds] = useState<string[]>([])
  const [offeredGold, setOfferedGold] = useState('0')
  const [requestedGold, setRequestedGold] = useState('0')
  const [busyTradeId, setBusyTradeId] = useState('')
  const [creating, setCreating] = useState(false)
  const [loadingPartnerCards, setLoadingPartnerCards] = useState(false)
  const [myRarity, setMyRarity] = useState('all')
  const [partnerRarity, setPartnerRarity] = useState('all')
  const [myCardSearch, setMyCardSearch] = useState('')
  const [partnerCardSearch, setPartnerCardSearch] = useState('')
  const normalizedPartnerQuery = partnerQuery.trim().replace(/^@+/, '').toLowerCase()
  const autoResolvedPartner = selectedPartner || resolvePartnerFromQuery(partnerResults, normalizedPartnerQuery)

  const myTopCards = useMemo(
    () => filterCards(myCards, myRarity, myCardSearch).slice(0, 40),
    [myCards, myRarity, myCardSearch]
  )
  const partnerTopCards = useMemo(
    () => filterCards(partnerCards, partnerRarity, partnerCardSearch).slice(0, 40),
    [partnerCards, partnerRarity, partnerCardSearch]
  )

  const load = async () => {
    const [c, t] = await Promise.all([getCards(), getTrades()])
    setMyCards(c.data?.cards || [])
    setTrades(t.data?.trades || [])
  }

  useEffect(() => { load().catch(() => undefined) }, [])

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      if (!partnerQuery.trim()) {
        setPartnerResults([])
        return
      }
      try {
        const res = await searchTradePartners(partnerQuery.trim())
        if (!cancelled) setPartnerResults(res.data?.partners || [])
      } catch {
        if (!cancelled) setPartnerResults([])
      }
    }
    run()
    return () => { cancelled = true }
  }, [partnerQuery])

  const pickPartner = async (partner: any) => {
    setSelectedPartner(partner)
    setRequestedIds([])
    setLoadingPartnerCards(true)
    try {
      const res = await getPartnerCards(Number(partner.telegram_id))
      setPartnerCards(res.data?.cards || [])
    } catch {
      setPartnerCards([])
    } finally {
      setLoadingPartnerCards(false)
    }
  }

  const toggleId = (ids: string[], setIds: (v: string[]) => void, id: string) => {
    if (ids.includes(id)) setIds(ids.filter((x) => x !== id))
    else setIds([...ids, id])
  }

  const onCreate = async () => {
    let partner = autoResolvedPartner
    if (!partner && normalizedPartnerQuery) {
      try {
        const r = await searchTradePartners(normalizedPartnerQuery)
        partner = resolvePartnerFromQuery(r.data?.partners || [], normalizedPartnerQuery)
      } catch {
        partner = null
      }
    }
    const pid = Number(partner?.telegram_id)
    if (!Number.isFinite(pid) || pid <= 0) return alert('Select a trade partner')
    setCreating(true)
    try {
      await createTrade({
        partner_id: Math.floor(pid),
        offered_card_ids: offeredIds,
        requested_card_ids: requestedIds,
        offered_gold: Math.max(0, Math.floor(Number(offeredGold) || 0)),
        requested_gold: Math.max(0, Math.floor(Number(requestedGold) || 0)),
      })
      setSelectedPartner(null)
      setPartnerQuery('')
      setPartnerResults([])
      setOfferedIds([])
      setRequestedIds([])
      setPartnerCards([])
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

  useEffect(() => {
    // Auto-load partner cards when an exact/single search match is present.
    if (!autoResolvedPartner?.telegram_id || !normalizedPartnerQuery) return
    if (selectedPartner?.telegram_id === autoResolvedPartner.telegram_id) return
    pickPartner(autoResolvedPartner).catch(() => undefined)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [partnerResults, normalizedPartnerQuery, selectedPartner?.telegram_id])

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
        <input
          value={partnerQuery}
          onChange={(e) => setPartnerQuery(e.target.value)}
          placeholder="Search partner by username or Telegram ID"
          style={inputStyle}
        />
        {partnerResults.length > 0 && (
          <div style={{ background: '#0f1030', border: '1px solid #2a2760', borderRadius: 8, marginBottom: 8, maxHeight: 150, overflowY: 'auto' }}>
            {partnerResults.map((p: any) => (
              <button
                key={String(p.telegram_id)}
                onClick={() => pickPartner(p)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  background: selectedPartner?.telegram_id === p.telegram_id ? '#2a1760' : 'transparent',
                  color: '#fff',
                  border: 'none',
                  padding: '8px 10px',
                  cursor: 'pointer',
                }}
              >
                @{p.username} (ID: {p.telegram_id})
              </button>
            ))}
          </div>
        )}

        {(selectedPartner || autoResolvedPartner) && (
          <div style={{ marginBottom: 8, fontSize: 12, color: '#F4A800' }}>
            <span style={avatarBadgeStyle}>{avatarInitial((selectedPartner || autoResolvedPartner).username)}</span>{' '}
            Trading with: <b>@{(selectedPartner || autoResolvedPartner).username}</b> (ID: {(selectedPartner || autoResolvedPartner).telegram_id})
            {!selectedPartner && autoResolvedPartner && (
              <span style={{ color: '#2ECC71' }}> • auto-selected</span>
            )}
          </div>
        )}

        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: '#8888aa', marginBottom: 4 }}>Your offered cards</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 6 }}>
            <select value={myRarity} onChange={(e) => setMyRarity(e.target.value)} style={inputStyle}>
              <option value="all">All rarities</option>
              <option value="common">Common</option>
              <option value="rare">Rare</option>
              <option value="epic">Epic</option>
              <option value="legendary">Legendary</option>
              <option value="mythic">Mythic</option>
            </select>
            <input value={myCardSearch} onChange={(e) => setMyCardSearch(e.target.value)} placeholder="Search your cards" style={inputStyle} />
          </div>
          <div style={cardGridStyle}>
            {myTopCards.map((c: any) => (
              <button
                key={c.card_id}
                onClick={() => toggleId(offeredIds, setOfferedIds, c.card_id)}
                style={chipStyle(offeredIds.includes(c.card_id))}
              >
                {(c.name || c.card_id)} [{(c.rarity || 'common').toUpperCase()}]
              </button>
            ))}
            {myTopCards.length === 0 && <span style={{ color: '#8888aa', fontSize: 12 }}>No cards found</span>}
          </div>
        </div>

        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: '#8888aa', marginBottom: 4 }}>Requested cards from partner</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 6 }}>
            <select value={partnerRarity} onChange={(e) => setPartnerRarity(e.target.value)} style={inputStyle}>
              <option value="all">All rarities</option>
              <option value="common">Common</option>
              <option value="rare">Rare</option>
              <option value="epic">Epic</option>
              <option value="legendary">Legendary</option>
              <option value="mythic">Mythic</option>
            </select>
            <input value={partnerCardSearch} onChange={(e) => setPartnerCardSearch(e.target.value)} placeholder="Search partner cards" style={inputStyle} />
          </div>
          {loadingPartnerCards && <div style={{ color: '#8888aa', fontSize: 12 }}>Loading partner cards...</div>}
          <div style={cardGridStyle}>
            {partnerTopCards.map((c: any) => (
              <button
                key={c.card_id}
                onClick={() => toggleId(requestedIds, setRequestedIds, c.card_id)}
                style={chipStyle(requestedIds.includes(c.card_id))}
              >
                {(c.name || c.card_id)} [{(c.rarity || 'common').toUpperCase()}]
              </button>
            ))}
            {!loadingPartnerCards && selectedPartner && partnerTopCards.length === 0 && (
              <span style={{ color: '#8888aa', fontSize: 12 }}>No cards visible for this user</span>
            )}
          </div>
        </div>

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
      </div>

      <h4 style={{ color: '#F4A800', marginBottom: 8 }}>My Trades</h4>
      {trades.length === 0 && <p style={{ color: '#8888aa' }}>No trades yet.</p>}
      {trades.map((t: any) => (
        <div key={t.id} style={{ background: '#1a1740', border: '1px solid #2a2760', borderRadius: 12, padding: 12, marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
            <div style={{ fontWeight: 700 }}>Trade #{String(t.id).slice(0, 8)}</div>
            <div style={{ fontSize: 12, color: '#F4A800' }}>
              <span style={avatarBadgeStyle}>{avatarInitial(t.partner_username)}</span>{' '}
              @{t.partner_username || 'partner'}
            </div>
          </div>
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

const cardGridStyle = {
  display: 'flex',
  gap: 6,
  flexWrap: 'wrap',
  maxHeight: 120,
  overflowY: 'auto',
  background: '#0f1030',
  border: '1px solid #2a2760',
  borderRadius: 8,
  padding: 6,
} as const

const avatarBadgeStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 18,
  height: 18,
  borderRadius: 999,
  background: '#6B2EBE',
  color: '#fff',
  fontSize: 10,
  fontWeight: 700,
  verticalAlign: 'middle',
} as const

const avatarInitial = (username?: string) => {
  const v = (username || '').trim()
  return v ? v[0].toUpperCase() : '?'
}

const filterCards = (cards: any[], rarity: string, query: string) => {
  const q = query.trim().toLowerCase()
  return (cards || []).filter((c: any) => {
    const r = String(c?.rarity || '').toLowerCase()
    if (rarity !== 'all' && r !== rarity) return false
    if (!q) return true
    const name = String(c?.name || '').toLowerCase()
    const id = String(c?.card_id || '').toLowerCase()
    return name.includes(q) || id.includes(q)
  })
}

const resolvePartnerFromQuery = (results: any[], normalizedQuery: string) => {
  if (!normalizedQuery) return null
  const exactUser = results.find((p: any) => String(p?.username || '').toLowerCase() === normalizedQuery)
  if (exactUser) return exactUser
  const digitsOnly = normalizedQuery.replace(/\D/g, '')
  if (digitsOnly) {
    const exactId = results.find((p: any) => String(p?.telegram_id || '') === digitsOnly)
    if (exactId) return exactId
  }
  return results.length === 1 ? results[0] : null
}

const chipStyle = (active: boolean) => ({
  border: '1px solid #2a2760',
  background: active ? '#6B2EBE' : '#1a1740',
  color: '#fff',
  borderRadius: 999,
  padding: '6px 10px',
  fontSize: 11,
  cursor: 'pointer',
}) as const

const actionBtn = (bg: string) => ({
  width: '100%',
  padding: 9,
  background: bg,
  color: '#fff',
  border: 'none',
  borderRadius: 8,
  fontWeight: 700,
}) as const
