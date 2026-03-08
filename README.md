# Music Legends

Music Legends is a collectible music-card game with two active player surfaces:

- `Discord bot` for the full command + menu gameplay loop.
- `Telegram Mini App` for mobile-first collection, packs, battle, and daily flow.

## Current Gameplay Surface

### Discord (primary, full feature set)

Loaded command modules include:

- `start_game`, `game_info`, `gameplay`, `card_game`, `menu_system`
- `marketplace`, `battle_commands`, `battlepass_commands`, `trade_commands`
- `dust_commands` (+ admin/dev cogs for operations)

Player-facing command highlights:

- Core: `/menu`, `/start_game`, `/deck`, `/stats`, `/leaderboard`
- Packs: `/pack`, `/packs`, `/buy_pack`, `/open_pack`
- Market: `/market`, `/buy`, `/sell`, `/delist`
- Battle: `/battle`, `/battle_stats`
- Battle Pass: `/battlepass`, `/claim_bp`
- Trade: `/trade`, `/trade_history`
- Dust economy: `/dust`, `/craft`, `/boost`, `/reroll`, `/buy_pack_dust`, `/dust_shop`

### Telegram (active, narrower than Discord)

Telegram bot and Mini App are live via `tma/`:

- Bot entry commands: `/start`, `/link`
- Mini App tabs/pages currently shipped:
  - `Home`
  - `Cards`
  - `Packs`
  - `Battle`
  - `Daily`

Current Mini App API helpers in `tma/frontend/src/api/client.ts`:

- `/api/me`, `/api/cards`, `/api/cards/{id}`
- `/api/packs`, `/api/packs/store`, `/api/packs/{id}/open`
- `/api/economy`, `/api/economy/daily`, `/api/leaderboard`
- `/api/battle/challenge`, `/api/battle/{id}/accept`, `/api/battle/{id}`
- `/api/link/generate`

## Product UX Recommendation

- Use `group chats` for discovery, social proof, and announcements.
- Use `bot private chat + Mini App` for actual gameplay.
- Keep heavy interactions in UI (Mini App / Discord menus), not raw chat commands.

## Setup Notes

### Discord runtime

- Start with `main.py`
- Requires `DISCORD_TOKEN` and `DISCORD_APPLICATION_ID`

### Telegram runtime

- Start with `uvicorn tma.api.main:app --host 0.0.0.0 --port 8080`
- Required env vars:
  - `TELEGRAM_BOT_TOKEN`
  - `TMA_URL` (Mini App URL)
  - `RAILWAY_PUBLIC_DOMAIN` or `TMA_API_URL` (for webhook setup)

## Documentation

- `PLAYER_GUIDE.md` - player onboarding and gameplay flow
- `GAME_DOCUMENTATION.md` - technical systems and command reference

Last updated: 2026-03-07
