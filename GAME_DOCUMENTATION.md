# Music Legends - Game Documentation

Technical reference aligned with the current command surface and Telegram Mini App state.

## Runtime Surfaces

### Discord bot (`main.py`)

Primary loaded gameplay cogs:

- `cogs.start_game`
- `cogs.game_info`
- `cogs.gameplay`
- `cogs.card_game`
- `cogs.menu_system`
- `cogs.marketplace`
- `cogs.battle_commands`
- `cogs.battlepass_commands`
- `cogs.trade_commands`
- `cogs.dust_commands`

### Telegram Mini App (`tma/`)

- FastAPI app: `tma/api/main.py`
- Bot webhook handlers: `tma/api/bot/handlers.py`
- Frontend routes: `/`, `/collection`, `/packs`, `/battle`, `/daily`
- Bot commands: `/start`, `/link`

## Core Systems

- `Cards`: collectible music artist cards with stat-based battle use.
- `Packs`: built-in tier purchases + creator-pack browsing/opening.
- `Battle`: PvP wager flow via Discord and Mini App challenge/accept APIs.
- `Economy`: daily claim, gold/tickets progression, leaderboard.
- `Battle Pass`: `/battlepass` and `/claim_bp` in Discord; partial API on Telegram.
- `Marketplace`: buy/sell/list/delist in Discord.
- `Trade`: player-to-player offers/history in Discord.
- `Dust`: craft/boost/reroll/dust-pack loop in Discord.

## Command Reference (Current)

### Discord Player Commands

| Command | Source |
|---|---|
| `/menu` | `cogs/menu_system.py` |
| `/deck` | `cogs/card_game.py` |
| `/stats` | `cogs/card_game.py` |
| `/leaderboard` | `cogs/card_game.py` |
| `/open_pack` | `cogs/card_game.py` |
| `/pack` | `cogs/marketplace.py` |
| `/packs` | `cogs/marketplace.py` |
| `/buy_pack` | `cogs/marketplace.py` |
| `/market` | `cogs/marketplace.py` |
| `/buy` | `cogs/marketplace.py` |
| `/sell` | `cogs/marketplace.py` |
| `/delist` | `cogs/marketplace.py` |
| `/battle` | `cogs/battle_commands.py` |
| `/battle_stats` | `cogs/battle_commands.py` |
| `/battlepass` | `cogs/battlepass_commands.py` |
| `/claim_bp` | `cogs/battlepass_commands.py` |
| `/trade` | `cogs/trade_commands.py` |
| `/trade_history` | `cogs/trade_commands.py` |
| `/dust` | `cogs/dust_commands.py` |
| `/craft` | `cogs/dust_commands.py` |
| `/boost` | `cogs/dust_commands.py` |
| `/reroll` | `cogs/dust_commands.py` |
| `/buy_pack_dust` | `cogs/dust_commands.py` |
| `/dust_shop` | `cogs/dust_commands.py` |

### Discord Admin / Ops Commands

| Command | Source |
|---|---|
| `/start_game` | `cogs/start_game.py` |
| `/setup_user_hub` | `cogs/menu_system.py` |
| `/post_game_info` | `cogs/game_info.py` |
| `/server_analytics` | `cogs/admin_commands.py` |
| `/import_packs` | `cogs/admin_bulk_import.py` |

### Telegram APIs in Frontend Client

| Endpoint helper | Path |
|---|---|
| `getMe` | `/api/me` |
| `getCards`, `getCard` | `/api/cards`, `/api/cards/{id}` |
| `getPacks`, `getPackStore`, `openPack` | `/api/packs`, `/api/packs/store`, `/api/packs/{id}/open` |
| `getEconomy`, `claimDaily`, `getLeaderboard` | `/api/economy`, `/api/economy/daily`, `/api/leaderboard` |
| `createChallenge`, `acceptBattle`, `getBattle` | `/api/battle/challenge`, `/api/battle/{id}/accept`, `/api/battle/{id}` |
| `generateLink` | `/api/link/generate` |

## Telegram Parity Notes

- Telegram gameplay is active for collection/packs/battle/daily.
- Discord currently has broader economy coverage (`marketplace`, `trade`, `dust`) and richer command/menu tooling.
- Keep docs and product messaging explicit that Telegram is mobile-first and not full parity yet.

## Data Layer Notes

- `database.py` handles both SQLite and PostgreSQL compatibility flows.
- Runtime has legacy mixed schema patterns in some areas; cast/typing safety is important for Postgres.
- When documenting numbers (prices, reward values), treat config files as source of truth:
  - `config/economy.py`
  - `config/battle_pass.py`
  - `config/vip.py`

## Project Layout (Key Paths)

```text
main.py
database.py
cogs/
tma/api/
tma/frontend/
config/
services/
tests/
```

Last updated: 2026-03-07
