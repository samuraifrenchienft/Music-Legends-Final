import { useState } from 'react'
import './AnimatedCard.css'

const RARITY_COLORS: Record<string, string> = {
  common: '#95A5A6', rare: '#4488FF', epic: '#6B2EBE',
  legendary: '#F4A800', mythic: '#E74C3C',
}

interface Props {
  card: any
  revealOnMount?: boolean   // true during pack opening
  delay?: number            // stagger delay in ms
  onClick?: () => void
}

export default function AnimatedCard({ card, revealOnMount = false, delay = 0, onClick }: Props) {
  const [flipped, setFlipped] = useState(revealOnMount ? false : true)
  const [revealed, setRevealed] = useState(!revealOnMount)
  const rarity = (card.rarity || 'common').toLowerCase()
  const isMythic = rarity === 'mythic'
  const power = card.power || 0

  const handleReveal = () => {
    if (flipped) { onClick?.(); return }
    setTimeout(() => {
      setFlipped(true)
      setRevealed(true)
    }, delay)
  }

  const pct = Math.round((power / 135) * 100)

  return (
    <>
      {isMythic && flipped && (
        <div className="mythic-overlay" onClick={() => {}}>
          <div className="mythic-spotlight">
            <div className={`card-face card-front glow-mythic`} style={{ position: 'relative', width: 260, height: 360, borderRadius: 14 }}>
              {card.image_url && <img src={card.image_url} alt={card.name} style={{ width: '100%', height: '75%', objectFit: 'cover' }} />}
              <div style={{ padding: '8px 12px', background: '#0D0B2E' }}>
                <div style={{ fontWeight: 'bold', color: '#FF4E9A' }}>{card.name}</div>
                <div style={{ fontSize: 12, color: '#E74C3C' }}>🔴 MYTHIC</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card-scene" onClick={handleReveal}>
        <div className={`card-flip ${flipped ? 'flipped' : ''}`}>
          {/* Back face — shown before reveal */}
          <div className="card-face card-back">🎵</div>

          {/* Front face — revealed card */}
          <div className={`card-face card-front glow-${rarity}`}>
            {card.image_url && (
              <img src={card.image_url} alt={card.name}
                style={{ width: '100%', height: '60%', objectFit: 'cover' }} />
            )}
            <div style={{ padding: '8px 10px', flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: '#fff' }}>{card.name}</div>
              {card.title && <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>{card.title}</div>}
              <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ flex: 1, height: 4, background: '#333', borderRadius: 2 }}>
                  <div style={{
                    width: revealed ? `${pct}%` : '0%',
                    height: '100%',
                    background: RARITY_COLORS[rarity],
                    borderRadius: 2,
                    transition: 'width 0.8s ease 0.3s',
                  }} />
                </div>
                <span style={{ fontSize: 11, color: RARITY_COLORS[rarity], fontWeight: 700 }}>{power}</span>
              </div>
              <div style={{ marginTop: 4, fontSize: 10, color: '#8888aa' }}>
                {card.rarity_emoji} {(rarity).charAt(0).toUpperCase() + rarity.slice(1)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
