import { useEffect, useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { mountMainButton, setMainButtonParams, onMainButtonClick, unmountMainButton,
         hapticFeedbackNotificationOccurred, openTelegramLink } from '@telegram-apps/sdk'
import { getPacks, createChallenge, acceptBattle, getBattle, searchPlayers } from '../api/client'

type Phase = 'select-pack' | 'challenge-sent' | 'accept' | 'result'
type PlayerResult = { user_id: string; username: string; telegram_id: number; active_at?: string }

const RARITY_COLORS: Record<string, string> = {
  common: '#95A5A6', rare: '#4488FF', epic: '#6B2EBE', legendary: '#F4A800', mythic: '#E74C3C',
}

export default function Battle() {
  const [searchParams] = useSearchParams()
  const battleIdParam = searchParams.get('id')
  const [phase, setPhase] = useState<Phase>(battleIdParam ? 'accept' : 'select-pack')
  const [packs, setPacks] = useState<any[]>([])
  const [selectedPackId, setSelectedPackId] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchingPlayers, setSearchingPlayers] = useState(false)
  const [searchResults, setSearchResults] = useState<PlayerResult[]>([])
  const [selectedOpponent, setSelectedOpponent] = useState<PlayerResult | null>(null)
  const [battleId, setBattleId] = useState(battleIdParam || '')
  const [battleLink, setBattleLink] = useState('')
  const [result, setResult] = useState<any>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined)

  useEffect(() => {
    getPacks()
      .then(r => setPacks(r.data.packs))
      .catch(() => setPacks([]))
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handlePlayerSearch = async () => {
    const q = searchQuery.trim()
    if (!q) {
      setSearchResults([])
      return
    }
    setSearchingPlayers(true)
    try {
      const r = await searchPlayers(q, 12)
      setSearchResults(r.data.players || [])
    } catch {
      setSearchResults([])
    } finally {
      setSearchingPlayers(false)
    }
  }

  const handleChallenge = async () => {
    if (!selectedPackId || !selectedOpponent) return
    try {
      const r = await createChallenge({
        pack_id: selectedPackId,
        opponent_telegram_id: selectedOpponent.telegram_id,
        wager_tier: 'casual',
      })
      setBattleId(r.data.battle_id)
      setBattleLink(r.data.link)
      setPhase('challenge-sent')
      if (hapticFeedbackNotificationOccurred.isAvailable()) hapticFeedbackNotificationOccurred('success')
      pollRef.current = setInterval(async () => {
        const poll = await getBattle(r.data.battle_id)
        if (poll.data.status === 'complete') {
          clearInterval(pollRef.current)
          setResult(poll.data.result)
          setPhase('result')
          if (hapticFeedbackNotificationOccurred.isAvailable()) {
            hapticFeedbackNotificationOccurred(poll.data.result?.winner === 1 ? 'success' : 'error')
          }
        }
      }, 3000)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to create challenge')
    }
  }

  const handleAccept = async () => {
    if (!selectedPackId || !battleId) return
    try {
      const r = await acceptBattle(battleId, { pack_id: selectedPackId })
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
      const isReady = !!selectedPackId && !!selectedOpponent
      const text = !selectedOpponent
        ? 'Search & select opponent'
        : selectedPackId
          ? '⚔️ Create Challenge'
          : 'Select a Pack First'
      setMainButtonParams({ text, isEnabled: isReady, isVisible: true, backgroundColor: '#E74C3C' })
      const off = onMainButtonClick(handleChallenge)
      return () => { off(); unmountMainButton() }
    }
    if (phase === 'accept') {
      setMainButtonParams({ text: selectedPackId ? '⚔️ Accept Battle!' : 'Select Your Pack', isEnabled: !!selectedPackId, isVisible: true, backgroundColor: '#E74C3C' })
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
    if (phase === 'result') {
      // "Play Again" button on result screen
      setMainButtonParams({ text: 'Battle Again', isEnabled: true, isVisible: true, backgroundColor: '#E74C3C' })
      const off = onMainButtonClick(() => {
        setResult(null)
        setSelectedPackId('')
        setSelectedOpponent(null)
        setSearchResults([])
        setSearchQuery('')
        setBattleId('')
        setBattleLink('')
        setPhase('select-pack')
      })
      return () => { off(); unmountMainButton() }
    }
    unmountMainButton()
  }, [phase, selectedPackId, selectedOpponent, battleLink]) // eslint-disable-line react-hooks/exhaustive-deps

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
      <h3 style={{ color: '#F4A800', marginBottom: 6 }}>
        {phase === 'accept' ? '⚔️ Battle Challenge!' : '⚔️ Battle'}
      </h3>
      {phase === 'accept' && <p style={{ color: '#F4A800', fontSize: 13, marginBottom: 12 }}>Someone challenged you! Pick your best pack.</p>}
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
          {phase === 'select-pack' && (
            <div style={{ marginBottom: 14 }}>
              <p style={{ color: '#8888aa', fontSize: 13, marginBottom: 8 }}>Challenge a player:</p>
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') void handlePlayerSearch() }}
                  placeholder="Search username or Telegram ID"
                  style={{
                    flex: 1, borderRadius: 10, border: '1px solid #2a2760',
                    background: '#1a1740', color: '#fff', padding: '10px 12px',
                  }}
                />
                <button
                  onClick={() => void handlePlayerSearch()}
                  disabled={searchingPlayers || !searchQuery.trim()}
                  style={{
                    border: 'none', borderRadius: 10, padding: '10px 12px',
                    background: searchingPlayers ? '#4a2a4a' : '#6B2EBE', color: '#fff',
                    cursor: searchingPlayers ? 'not-allowed' : 'pointer',
                  }}
                >
                  {searchingPlayers ? '...' : 'Search'}
                </button>
              </div>
              {searchResults.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {searchResults.map(player => (
                    <div
                      key={`${player.telegram_id}`}
                      onClick={() => setSelectedOpponent(player)}
                      style={{
                        background: selectedOpponent?.telegram_id === player.telegram_id ? '#2a1760' : '#1a1740',
                        border: `2px solid ${selectedOpponent?.telegram_id === player.telegram_id ? '#F4A800' : '#2a2760'}`,
                        borderRadius: 10,
                        padding: 10,
                        marginBottom: 6,
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ fontWeight: 700 }}>@{player.username}</div>
                      <div style={{ fontSize: 12, color: '#8888aa' }}>Telegram ID: {player.telegram_id}</div>
                    </div>
                  ))}
                </div>
              )}
              {searchQuery.trim() && !searchingPlayers && searchResults.length === 0 && (
                <p style={{ color: '#8888aa', fontSize: 12, marginTop: 8 }}>
                  No recently active Telegram players found.
                </p>
              )}
              {selectedOpponent && (
                <p style={{ color: '#2ECC71', fontSize: 12, marginTop: 8 }}>
                  Opponent selected: @{selectedOpponent.username}
                </p>
              )}
            </div>
          )}
          <p style={{ color: '#8888aa', fontSize: 13, marginBottom: 14 }}>Choose your pack:</p>
          {packs.map(pack => (
            <div key={pack.pack_id} onClick={() => setSelectedPackId(pack.pack_id)} style={{
              background: selectedPackId === pack.pack_id ? '#2a1760' : '#1a1740',
              border: `2px solid ${selectedPackId === pack.pack_id ? '#F4A800' : '#2a2760'}`,
              borderRadius: 10, padding: 12, marginBottom: 8, cursor: 'pointer',
            }}>
              <div style={{ fontWeight: 700 }}>{pack.pack_name}</div>
              <div style={{ fontSize: 12, color: '#8888aa' }}>{pack.pack_tier?.toUpperCase()} • {(pack.cards || []).length} cards</div>
            </div>
          ))}
          {packs.length === 0 && <p style={{ color: '#888', textAlign: 'center', marginTop: 40 }}>You need packs to battle! Claim your daily reward first.</p>}
          {packs.length > 0 && !mountMainButton.isAvailable() && (
            <button
              onClick={phase === 'accept' ? handleAccept : handleChallenge}
              disabled={phase === 'accept' ? !selectedPackId : (!selectedPackId || !selectedOpponent)}
              style={{
                width: '100%', padding: '14px 0', marginTop: 16,
                background: (phase === 'accept' ? !!selectedPackId : (!!selectedPackId && !!selectedOpponent)) ? '#E74C3C' : '#4a2a4a',
                color: '#fff', border: 'none', borderRadius: 12,
                fontWeight: 700, fontSize: 15,
                cursor: (phase === 'accept' ? !!selectedPackId : (!!selectedPackId && !!selectedOpponent)) ? 'pointer' : 'not-allowed',
              }}
            >
              {phase === 'accept'
                ? (selectedPackId ? '⚔️ Accept Battle!' : 'Select Your Pack')
                : (!selectedOpponent ? 'Search & Select Opponent' : (selectedPackId ? '⚔️ Create Challenge' : 'Select a Pack First'))}
            </button>
          )}
        </>
      )}
    </div>
  )
}
