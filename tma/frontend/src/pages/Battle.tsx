import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedbackNotificationOccurred, openTelegramLink } from '@telegram-apps/sdk'
import { getPacks, getCards, createChallenge, acceptBattle, getBattle } from '../api/client'

type Phase = 'select-pack' | 'challenge-sent' | 'accept' | 'resolving' | 'result'

const RARITY_COLORS: Record<string, string> = {
  common: '#95A5A6', rare: '#4488FF', epic: '#6B2EBE', legendary: '#F4A800', mythic: '#E74C3C',
}

export default function Battle() {
  const [searchParams] = useSearchParams()
  const battleIdParam = searchParams.get('id')
  const [phase, setPhase] = useState<Phase>(battleIdParam ? 'accept' : 'select-pack')
  const [packs, setPacks] = useState<any[]>([])
  const [selectedPackId, setSelectedPackId] = useState<string>('')
  const [selectionType, setSelectionType] = useState<'pack' | 'card'>('pack')
  const [battleId, setBattleId] = useState(battleIdParam || '')
  const [battleLink, setBattleLink] = useState('')
  const [result, setResult] = useState<any>(null)
  const [loadingBattle, setLoadingBattle] = useState(!!battleIdParam)
  const pollRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  useEffect(() => {
    getPacks()
      .then(async r => {
        const ownedPacks = r.data.packs || []
        if (ownedPacks.length > 0) {
          setPacks(ownedPacks)
          return
        }
        // Fallback flow: allow battle from collection when user has cards but no purchased packs.
        try {
          const cardsResp = await getCards()
          const cards = cardsResp.data.cards || []
          const synthetic = cards.map((c: any) => ({
            pack_id: `card:${c.card_id}`,
            pack_name: `Card: ${c.name || c.card_id}`,
            pack_tier: c.rarity || 'community',
            cards: [c],
            _type: 'card',
          }))
          setPacks(synthetic)
        } catch {
          setPacks([])
        }
      })
      .catch(async () => {
        try {
          const cardsResp = await getCards()
          const cards = cardsResp.data.cards || []
          const synthetic = cards.map((c: any) => ({
            pack_id: `card:${c.card_id}`,
            pack_name: `Card: ${c.name || c.card_id}`,
            pack_tier: c.rarity || 'community',
            cards: [c],
            _type: 'card',
          }))
          setPacks(synthetic)
        } catch {
          setPacks([])
        }
      })
    if (battleIdParam) {
      getBattle(battleIdParam)
        .then((r) => {
          if (r.data?.status === 'complete' && r.data?.result) {
            setResult(r.data.result)
            setPhase('result')
          } else {
            setPhase('accept')
          }
        })
        .catch(() => {
          setPhase('accept')
        })
        .finally(() => setLoadingBattle(false))
    } else {
      setLoadingBattle(false)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleChallenge = async () => {
    if (!selectedPackId) return
    const selected = packs.find((p: any) => String(p.pack_id) === String(selectedPackId))
    const label = selected?.pack_name || selected?.name || selectedPackId
    if (!window.confirm(`Create battle challenge with "${label}"?`)) return
    try {
      const body: any = { opponent_telegram_id: 0, wager_tier: 'casual' }
      if (selectionType === 'card' || selectedPackId.startsWith('card:')) body.card_id = selectedPackId.replace('card:', '')
      else body.pack_id = selectedPackId
      const r = await createChallenge(body)
      setBattleId(r.data.battle_id)
      setBattleLink(r.data.link)
      setPhase('challenge-sent')
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('success')
      pollRef.current = setInterval(async () => {
        try {
          const poll = await getBattle(r.data.battle_id)
          if (poll.data.status === 'complete') {
            clearInterval(pollRef.current)
            setResult(poll.data.result)
            setPhase('result')
            if (hapticFeedbackNotificationOccurred.isAvailable()) {
              hapticFeedbackNotificationOccurred(poll.data.result?.winner === 1 ? 'success' : 'error')
            }
          }
        } catch {
          // Keep polling; transient network errors should not break battle completion flow.
        }
      }, 3000)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to create challenge')
    }
  }

  const handleAccept = async () => {
    if (!selectedPackId || !battleId) return
    const selected = packs.find((p: any) => String(p.pack_id) === String(selectedPackId))
    const label = selected?.pack_name || selected?.name || selectedPackId
    if (!window.confirm(`Confirm accepting this battle using "${label}"?`)) return
    try {
      setPhase('resolving')
      const body: any = {}
      if (selectionType === 'card' || selectedPackId.startsWith('card:')) body.card_id = selectedPackId.replace('card:', '')
      else body.pack_id = selectedPackId
      const r = await acceptBattle(battleId, body)
      setResult(r.data.result)
      setPhase('result')
      if (hapticFeedbackNotificationOccurred.isAvailable()) {
        hapticFeedbackNotificationOccurred(r.data.result?.winner === 2 ? 'success' : 'error')
      }
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to accept battle')
    }
  }

  useEffect(() => {
    if (!mountMainButton.isAvailable()) return
    mountMainButton()
    if (phase === 'select-pack') {
      setMainButtonParams({
        text: selectedPackId ? '⚔️ Create Challenge' : 'Select a Card or Pack',
        isEnabled: !!selectedPackId,
        isVisible: true,
        backgroundColor: '#E74C3C',
      })
      const off = onMainButtonClick(handleChallenge)
      return () => { off(); unmountMainButton() }
    }
    if (phase === 'accept') {
      setMainButtonParams({
        text: selectedPackId ? '⚔️ Accept Battle!' : 'Select Your Card or Pack',
        isEnabled: !!selectedPackId,
        isVisible: true,
        backgroundColor: '#E74C3C',
      })
      const off = onMainButtonClick(handleAccept)
      return () => { off(); unmountMainButton() }
    }
    if (phase === 'challenge-sent') {
      setMainButtonParams({ text: '🔗 Share Challenge Link', isEnabled: true, isVisible: true, backgroundColor: '#6B2EBE' })
      const off = onMainButtonClick(() => {
        if (openTelegramLink.isAvailable()) openTelegramLink(battleLink)
        else window.open(battleLink, '_blank')
      })
      return () => { off(); unmountMainButton() }
    }
    if (phase === 'resolving') {
      setMainButtonParams({ text: 'Resolving Battle...', isEnabled: false, isVisible: true, backgroundColor: '#6B2EBE' })
      return () => { unmountMainButton() }
    }
    if (phase === 'result') {
      // "Play Again" button on result screen
      setMainButtonParams({ text: 'Battle Again', isEnabled: true, isVisible: true, backgroundColor: '#E74C3C' })
      const off = onMainButtonClick(() => {
        setResult(null)
        setSelectedPackId('')
        setBattleId('')
        setBattleLink('')
        setPhase('select-pack')
      })
      return () => { off(); unmountMainButton() }
    }
    unmountMainButton()
  }, [phase, selectedPackId, battleLink]) // eslint-disable-line react-hooks/exhaustive-deps

  if (phase === 'result' && result) {
    const c = result.challenger, o = result.opponent, winner = result.winner
    const winnerCard = winner === 1 ? c : winner === 2 ? o : null
    return (
      <div className={result.is_critical ? 'shake' : ''} style={{ padding: '20px 16px 100px', textAlign: 'center' }}>
        <h3 style={{ color: '#F4A800', fontSize: 22 }}>
          {winner === 1 ? '🏆 You Won!' : winner === 2 ? '😔 You Lost' : '🤝 Draw!'}
        </h3>
        {result.is_critical && <p style={{ color: '#FF4E9A', fontWeight: 700 }}>⚡ CRITICAL HIT!</p>}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', margin: '20px 0' }}>
          {[c, o].map((player, i) => (
            <div key={i} style={{
              flex: 1, background: '#1a1740', borderRadius: 12, padding: 12,
              border: `2px solid ${RARITY_COLORS[player?.rarity || 'common']}`,
              opacity: (i === 0 ? winner !== 2 : winner !== 1) ? 1 : 0.5,
            }}>
              {player?.image_url && <img src={player.image_url} alt={player.name} style={{ width: '100%', borderRadius: 8, aspectRatio: '16/9', objectFit: 'cover' }} />}
              <div style={{ fontWeight: 700, marginTop: 6, fontSize: 12 }}>{player?.name}</div>
              <div style={{ color: RARITY_COLORS[player?.rarity || 'common'], fontSize: 18, fontWeight: 700 }}>{player?.power}</div>
              <div style={{ color: '#2ECC71', fontSize: 12 }}>+{player?.gold_reward} 💰</div>
            </div>
          ))}
        </div>
        {/* YouTube link for the winning card */}
        {winnerCard?.youtube_url && (
          <a
            href={winnerCard.youtube_url}
            target="_blank"
            rel="noreferrer"
            style={{
              display: 'inline-block', marginTop: 8, padding: '8px 18px',
              background: '#FF0000', color: '#fff', borderRadius: 8,
              fontSize: 13, fontWeight: 700, textDecoration: 'none',
            }}
          >
            ▶ Watch {winnerCard.name} on YouTube
          </a>
        )}
      </div>
    )
  }

  return (
    <div style={{ padding: '16px 16px 80px' }}>
      {loadingBattle && (
        <div style={{ textAlign: 'center', color: '#8888aa', padding: '12px 0 16px' }}>
          Loading battle status...
        </div>
      )}
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>
        {phase === 'accept' ? '⚔️ Battle Challenge!' : '⚔️ Battle'}
      </h3>
      {phase === 'resolving' && (
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <div style={{ fontSize: 36 }}>⚡</div>
          <div style={{ color: '#F4A800', fontWeight: 700 }}>Battle in progress...</div>
          <div style={{ color: '#8888aa', fontSize: 12, marginTop: 6 }}>Calculating winner and rewards.</div>
        </div>
      )}
      {phase === 'accept' && <p style={{ color: '#F4A800', fontSize: 13, marginBottom: 12 }}>Someone challenged you! Pick your best card or pack.</p>}
      {phase === 'challenge-sent' && (
        <div style={{ textAlign: 'center', padding: 20 }}>
          <div style={{ fontSize: 40 }}>✅</div>
          <p style={{ color: '#2ECC71', marginTop: 8 }}>Challenge created!</p>
          <p style={{ color: '#8888aa', fontSize: 12 }}>Share the link with your opponent. Waiting for them to accept...</p>
          <div style={{ marginTop: 12, padding: '8px 12px', background: '#1a1740', borderRadius: 8, fontSize: 12, color: '#F4A800', wordBreak: 'break-all' }}>{battleLink}</div>
        </div>
      )}
      {(phase === 'select-pack' || phase === 'accept') && (
        <>
          <p style={{ color: '#8888aa', fontSize: 13, marginBottom: 14 }}>
            Choose your battle entry (pack or single card):
          </p>
          {packs.map(pack => (
            <div key={pack.pack_id} onClick={() => {
              setSelectedPackId(pack.pack_id)
              setSelectionType((pack._type === 'card' || String(pack.pack_id).startsWith('card:')) ? 'card' : 'pack')
            }} style={{
              background: selectedPackId === pack.pack_id ? '#2a1760' : '#1a1740',
              border: `2px solid ${selectedPackId === pack.pack_id ? '#F4A800' : '#2a2760'}`,
              borderRadius: 10, padding: 12, marginBottom: 8, cursor: 'pointer',
            }}>
              <div style={{ fontWeight: 700 }}>{pack.pack_name || pack.name || pack.pack_id}</div>
              <div style={{ fontSize: 12, color: '#8888aa' }}>
                {(pack.pack_tier || pack.tier || 'community').toUpperCase()} • {(pack.cards || []).length} card{(pack.cards || []).length === 1 ? '' : 's'}
                {(pack._type === 'card' || String(pack.pack_id).startsWith('card:')) ? ' • Auto-build squad' : ''}
              </div>
            </div>
          ))}
          {packs.length === 0 && <p style={{ color: '#888', textAlign: 'center', marginTop: 40 }}>No packs or cards found yet. Open/claim cards first, then try battle again.</p>}
          {packs.length > 0 && !mountMainButton.isAvailable() && (
            <button
              onClick={phase === 'accept' ? handleAccept : handleChallenge}
              disabled={!selectedPackId}
              style={{
                width: '100%', padding: '14px 0', marginTop: 16,
                background: selectedPackId ? '#E74C3C' : '#4a2a4a',
                color: '#fff', border: 'none', borderRadius: 12,
                fontWeight: 700, fontSize: 15, cursor: selectedPackId ? 'pointer' : 'not-allowed',
              }}
            >
              {phase === 'accept'
                ? (selectedPackId ? '⚔️ Accept Battle!' : 'Select Your Card or Pack')
                : (selectedPackId ? '⚔️ Create Challenge' : 'Select a Card or Pack')}
            </button>
          )}
        </>
      )}
    </div>
  )
}
