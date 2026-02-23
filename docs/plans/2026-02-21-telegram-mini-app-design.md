# Music Legends — Telegram Mini App Design Doc
> Status: APPROVED — ready for implementation planning
> Brainstormed: 2026-02-21 | Approved by: Slim
> Research notes: `docs/research/2026-02-21-tma-research.md`

---

## Strategic Direction

Telegram Mini App becomes the **primary game experience** — full animations, haptic feedback, immersive card reveals, real gameplay UI. Discord maintains full parity as an equal platform. Neither is secondary for now; decision on priority deferred until Discord updates and bankr integration are complete.

**Why TMA becomes primary eventually:**
- Discord = text embeds edited 3× for "animation", 2-3s API lag per interaction
- TMA = full HTML5/CSS3, 60fps animations, haptics, full-screen card reveals, YouTube video embedded on card, real game feel
- Discord will always be constrained by embed system; TMA has no ceiling

---

## Section 1: Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Railway PostgreSQL                   │
│              (shared — single source of truth)        │
└──────────────────┬──────────────────┬────────────────┘
                   │                  │
    ┌──────────────▼───┐    ┌─────────▼──────────────┐
    │  Discord Bot      │    │  TMA Service (new)      │
    │  (existing)       │    │  FastAPI + React TMA    │
    │  discord.py       │    │  tma/api/               │
    │  cogs/            │    │  tma/frontend/          │
    │  database.py ─────┼────► database.py (imported)  │
    └───────────────────┘    └────────────────────────┘
```

**Shared code (zero duplication):** `database.py`, `battle_engine.py`, `config/cards.py`

**New code:** `tma/` directory only

**One new Railway service:** FastAPI process serves both `/api/*` REST routes and the built React static files at `/`. Discord bot stays its own service. Both services read identical `DATABASE_URL`.

**Build process:** Multi-stage Dockerfile — Stage 1: `npm run build` compiles React to `dist/`. Stage 2: Python image with repo + `dist/`. FastAPI mounts `dist/` as StaticFiles.

---

## Section 2: Data Model

**Minimal schema changes — two alterations only.**

### Change 1: Platform-agnostic user identity

```sql
-- Add to existing users table
ALTER TABLE users ADD COLUMN discord_id  BIGINT UNIQUE;
ALTER TABLE users ADD COLUMN telegram_id BIGINT UNIQUE;

-- Backfill: all current users are Discord users
UPDATE users SET discord_id = user_id WHERE discord_id IS NULL;
```

Existing `user_id` PK is unchanged — Discord cogs keep working identically. New Telegram users get `user_id = 9_000_000_000 + telegram_id` as a synthetic collision-safe value. Account linking merges rows by copying `discord_id` into the Telegram user's row (or vice versa) and deleting the duplicate.

### Change 2: Pending TMA battles

```sql
CREATE TABLE pending_tma_battles (
    battle_id        TEXT PRIMARY KEY,   -- short code e.g. "X9K2QR"
    challenger_id    INTEGER NOT NULL,   -- user_id (our internal ID)
    opponent_id      INTEGER,            -- filled on accept
    challenger_pack  TEXT NOT NULL,      -- pack_id
    opponent_pack    TEXT,               -- filled on accept
    wager_tier       TEXT DEFAULT 'casual',
    status           TEXT DEFAULT 'waiting', -- waiting|complete|expired
    result_json      TEXT,               -- JSON battle result
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at       TIMESTAMP           -- 24 hours from created_at
);
```

No other tables change. All card, pack, economy, and battle history tables serve both platforms unchanged.

---

## Section 3: TMA SDK Features Used

All from `@telegram-apps/sdk-react` and `@telegram-apps/sdk`.

| Feature | How we use it |
|---|---|
| `useLaunchParams()` + `initDataRaw` | Auth — every API request sends raw initData in `Authorization: tma <data>` header. FastAPI validates HMAC with bot token. No login screen. |
| `startParam` | Battle deep links — `tgWebAppStartParam = "battle_X9K2QR"` routes opponent directly to accept screen |
| `mountMainButton` / `setMainButtonParams` | Primary action button per page — "Open Pack", "Accept Battle", "Claim Daily". Native OS-level, feels real. |
| `backButton.show/hide` + `backButton.onClick` | Shows in Telegram header on sub-pages. Tap = `window.history.back()`. |
| `showPopup()` | Native confirmation dialogs — "Confirm wager?", battle result summary |
| `hapticFeedback.notificationOccurred()` | `'success'` on pack open, daily claim, battle win. `'error'` on battle loss, failed action. |
| `expandViewport()` | Called on init — fills full screen |
| `themeParams` | App colors adapt to Telegram light/dark theme automatically |
| `openTelegramLink()` | Opens native Telegram share sheet with battle challenge link |

---

## Section 4: Share-Link Battle Flow

```
CHALLENGER                    FASTAPI                    OPPONENT
─────────────────────────────────────────────────────────────────
1. Battle tab → pick pack
2. MainButton: "Challenge"
                    ──────► POST /api/battle/challenge
                              Creates pending_tma_battles row
                              battle_id = "X9K2QR"
                    ◄──────  { link: "t.me/bot/app?startapp=battle_X9K2QR" }
3. showPopup: "Share link"
4. openTelegramLink(link)
   → native share sheet
   haptic: success

                                          5. Taps link in any chat
                                          6. TMA opens
                                             startParam = "battle_X9K2QR"
                                          7. Challenge accept screen
                                             "SlimShady challenged you!"
                                          8. Pick pack
                                          9. MainButton: "Accept"
                    ◄────────────────────  POST /api/battle/X9K2QR/accept
                              Runs battle engine
                              Distributes gold/XP (BEFORE response)
                              Saves result_json
                              Bot notifies challenger
                    ─────────────────────► Result screen + haptic

10. Bot message: "⚔️ Result!
    You WON vs @opponent
    +175 gold"
11. Tap → TMA opens on
    result screen
```

**Constraints:**
- Gold/XP distributed server-side before any response (rewards never orphaned)
- Link expires after 24hrs (`status = 'expired'`)
- One link = one battle only (accept sets `status = 'complete'`)
- Challenger notified by bot regardless of TMA state

---

## Section 5: Bot Integration

Bot runs inside same FastAPI process. Webhook mode only (no polling).

**Commands:**
- `/start [startParam]` — Sends inline keyboard button opening TMA. If startParam provided (e.g. `battle_X9K2QR`), button URL includes it for direct routing.
- `/link` — Generates 6-char one-time code valid 10 minutes. Player enters in Discord `/link_telegram <code>` to merge accounts.

**Outbound notifications (no user command needed):**
- Battle result → challenger when opponent accepts
- Daily reminder → users who haven't claimed (optional, user can disable)

**Bot does NOT handle:** game commands, inline mode, group gameplay (future consideration)

---

## Section 6: Visual Experience (TMA Advantage)

These are explicit deliverables — not nice-to-haves. This is why TMA exists.

**Pack opening:**
- Cards start face-down, flip with 3D CSS transform revealing art
- Rarity-coloured glow pulses on reveal (CSS box-shadow animation)
- Mythic: screen darkens, spotlight, particle burst, card slams in
- Each card shows full-size YouTube thumbnail art (not Discord thumbnail)

**Battle:**
- Both champion cards displayed large with art
- Power bars animate filling up (challenger vs opponent)
- Screen shake effect on crit hit
- Win/loss cinematic reveal — not a text embed edit

**Card viewer:**
- Full-size card art, tap to flip and see all 5 stats with animated stat bars
- Rarity glow border, YouTube video tappable inline
- Power displayed as animated bar (0–135 scale)

**Daily claim:**
- Live countdown timer ticking to zero
- Satisfying claim animation on collect
- Streak counter with visual growth

**Navigation:**
- Page slide transitions between tabs
- Skeleton loading states (no blank screens)
- Pull-to-refresh on collection

---

## Section 7: Deployment

**Repository:** New `tma/` directory in existing `Music-Legends` repo.

```
tma/
├── api/
│   ├── main.py          FastAPI app entry point
│   ├── auth.py          initData HMAC validation dependency
│   └── routers/
│       ├── users.py     GET /api/me, POST /api/link
│       ├── cards.py     GET /api/cards, GET /api/cards/{id}
│       ├── packs.py     GET /api/packs, POST /api/packs/{id}/open
│       ├── battle.py    POST /api/battle/challenge, /{id}/accept, GET /{id}
│       └── economy.py   GET /api/economy, POST /api/economy/daily
│   └── bot/
│       └── handlers.py  /start, /link, battle notifications
├── frontend/
│   ├── src/
│   │   ├── pages/       Home, Collection, Pack, Battle, Daily
│   │   ├── components/  CardComponent, PowerBar, AnimatedCard, NavBar
│   │   └── api/         client.ts
│   ├── vite.config.ts
│   └── package.json
└── Dockerfile           Multi-stage build
```

**Railway:**

| Service | Command | New env vars |
|---|---|---|
| Discord bot (existing) | `python run_bot.py` | none |
| TMA (new) | `uvicorn tma.api.main:app --port 8080` | `TELEGRAM_BOT_TOKEN`, `TMA_URL` |

---

## What's Deferred (Future Phases)

| Feature | Phase |
|---|---|
| Telegram Stars pack purchases | 2 |
| Live WebSocket battles | 2 |
| Telegram channel drops | 2 |
| Creator pack creation in TMA | 3 |
| Discord ↔ Telegram account linking UI | 3 |
| Group chat gameplay | Future |

---

## Prerequisites Before Building

1. Finish current Discord updates (battle flow live test, any outstanding fixes)
2. Get bankr integration working on Discord
3. Register bot with @BotFather, get `TELEGRAM_BOT_TOKEN`
4. Add new Railway service for TMA
