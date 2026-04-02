# Music Legends

Music Legends is a collectible music-card game with two active player surfaces:

- `Discord bot` for the full command + menu gameplay loop.
- `Telegram Mini App` for mobile-first collection, packs, battle, daily flow, and growing parity with Discord economy features.

## Current Gameplay Surface

### Discord (primary, full feature set)

Cogs loaded from `main.py` (production):

- `cogs.start_game`, `cogs.game_info`, `cogs.gameplay`, `cogs.card_game`, `cogs.menu_system`
- `cogs.marketplace`, `cogs.admin_commands`, `cogs.battle_commands`, `cogs.battlepass_commands`, `cogs.trade_commands`
- `cogs.dust_commands`

Optional dev cogs (only if `ENABLE_DEV_COMMANDS=true` in env): `cogs.admin_bulk_import`, `cogs.dev_webhook_commands`, `cogs.dev_supply_commands`.

Slash commands are registered once each globally—there are no duplicate names across cogs.

**Highlights (player-facing):**

- Menu: `/menu`
- Server setup: `/start_game` (adds the game to a server)
- Collection & info: `/collection`, `/view`, `/card`, `/lookup`, `/deck`, `/stats`, `/leaderboard`, `/rank`, `/daily`
- Packs: `/pack`, `/packs`, `/buy_pack`, `/open_pack`
- Card actions: `/burn`, `/upgrade`, `/quicksell`, `/create_pack`
- Market: `/market`, `/buy`, `/sell`, `/delist`
- Battle: `/battle`, `/battle_stats`
- Battle Pass: `/battlepass`, `/claim_bp`
- Trade: `/trade`, `/trade_history`
- Dust: `/dust`, `/craft`, `/boost`, `/reroll`, `/buy_pack_dust`, `/dust_shop`
- Server premium (where applicable): `/premium_subscribe`, `/server_info`

**Admin / ops (permissions vary):** `/setup_user_hub`, `/post_game_info`, `/server_analytics`

**Not loaded:** `cogs/vip_commands.py` exists in the repo but is not included in `main.py`, so `/vip`, `/buy_vip`, and `/cancel_vip` are not active unless you add that cog.

### Telegram (Mini App + API)

Telegram bot and Mini App live under `tma/`:

- Bot commands: `/start`, `/link`
- Mini App areas: Home, Cards, Packs, Battle, Daily (and flows that call marketplace, trade, and dust APIs where wired in the UI)

`tma/frontend/src/api/client.ts` provides typed helpers for many endpoints; the backend also exposes routes such as `/api/dust/craft_card` that may be called directly. Representative paths:

- User: `/api/me`, `/api/players/search`, `/api/link/generate`
- Cards: `/api/cards`, `/api/cards/{id}`
- Packs: `/api/packs`, `/api/packs/store`, `/api/packs/{id}/open`, `/api/packs/{id}/purchase`
- Economy: `/api/economy`, `/api/economy/daily`, `/api/leaderboard`
- Battle: `/api/battle/challenge`, `/api/battle/register`, `/api/battle/opponents`, `/api/battle/incoming`, `/api/battle/updates`, `/api/battle/{id}`, `/api/battle/{id}/accept`, `/api/battle/{id}/cancel`
- Marketplace: `/api/marketplace`, `/api/marketplace/sell`, `/api/marketplace/buy/{id}`
- Trade: `/api/trades`, `/api/trades/partners`, `/api/trades/partners/{id}/cards`, plus accept/cancel on specific trades
- Dust: `/api/dust`, `/api/dust/dust_cards`, `/api/dust/craft_card`
- Battle Pass: `/api/battle_pass`, `/api/battle_pass/claim/{tier}` (see `GAME_DOCUMENTATION.md` for current behavior)

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

- `PLAYER_GUIDE.md` — player onboarding and gameplay flow
- `GAME_DOCUMENTATION.md` — technical systems and full command reference

Last updated: 2026-04-02
