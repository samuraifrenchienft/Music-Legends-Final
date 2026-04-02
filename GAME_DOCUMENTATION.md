# Music Legends - Game Documentation

Technical reference aligned with `main.py`, the cog command surface, and the Telegram Mini App.

## Runtime Surfaces

### Discord bot (`main.py`)

Production cogs (always attempted):

| Module | Role |
|--------|------|
| `cogs.start_game` | Server onboarding `/start_game` |
| `cogs.game_info` | `/post_game_info` |
| `cogs.gameplay` | Collection, cards, daily, dust-adjacent actions, etc. |
| `cogs.card_game` | Deck, stats, packs, creator tools, premium commands |
| `cogs.menu_system` | `/menu`, `/setup_user_hub` |
| `cogs.marketplace` | Market + pack browsing/buy |
| `cogs.admin_commands` | `/server_analytics`, `/dev_grant_all_cards` |
| `cogs.battle_commands` | `/battle`, `/battle_stats` |
| `cogs.battlepass_commands` | `/battlepass`, `/claim_bp` |
| `cogs.trade_commands` | `/trade`, `/trade_history` |
| `cogs.dust_commands` | Dust economy slash commands |

Dev-only extensions (loaded only when `ENABLE_DEV_COMMANDS=true`):

| Module | Commands (examples) |
|--------|------------------------|
| `cogs.admin_bulk_import` | `/import_packs` |
| `cogs.dev_webhook_commands` | `/dev_announcement`, `/dev_create_community_pack`, `/dev_create_gold_pack`, `/dev_restart` |
| `cogs.dev_supply_commands` | `/dev_supply`, `/dev_grant_pack`, `/dev_reset_daily`, `/give_gold`, `/dev_debug`, `/test_battle` |

The `gameplay` cog also defines `/drop`, which refuses non-dev use unless `ENABLE_DEV_COMMANDS` and dev checks pass.

**Registry note:** Each slash command name is unique across the loaded tree—Discord does not allow two global commands with the same name, and the codebase does not define duplicates.

**Not loaded by default:** `cogs/vip_commands.py` (`/vip`, `/buy_vip`, `/cancel_vip`) and `cogs/payment_security.py` are not in the `main.py` load list.

### Telegram Mini App (`tma/`)

- FastAPI app: `tma/api/main.py`
- Bot webhook: `tma/api/bot/handlers.py`
- Frontend routes (SPA): `/`, `/collection`, `/packs`, `/battle`, `/daily`, etc.
- Bot commands: `/start`, `/link`

## Core Systems

- **Cards:** Collectible artist cards with stat-based battles.
- **Packs:** Tier and creator packs; open/purchase via Discord and TMA APIs.
- **Battle:** PvP wagers via Discord and TMA challenge/accept flow.
- **Economy:** Daily claim, currency, leaderboard.
- **Battle Pass:** Full Discord commands; TMA exposes `/api/battle_pass` routes—confirm implementation status in `tma/api/routers/battle_pass.py` before claiming feature parity.
- **Marketplace / trade / dust:** Full Discord commands; TMA routers under `/api/marketplace`, `/api/trades`, `/api/dust`.

## Command Reference — Discord (production load)

Commands below are registered when their cog loads successfully. Permissions and premium gates are enforced inside each handler.

### `cogs/menu_system.py`

| Command | Notes |
|---------|--------|
| `/menu` | Main menu |
| `/setup_user_hub` | Post User Hub (admin/manage channels as implemented) |

### `cogs/start_game.py`

| Command | Notes |
|---------|--------|
| `/start_game` | Start Music Legends in the server |

### `cogs/game_info.py`

| Command | Notes |
|---------|--------|
| `/post_game_info` | Post branded guide (admin) |

### `cogs/gameplay.py`

| Command | Notes |
|---------|--------|
| `/collection` | Browse collection |
| `/view` | Card by id/serial |
| `/card` | Preview DB card |
| `/lookup` | Search by artist |
| `/burn` | Card → dust |
| `/upgrade` | Tier upgrade |
| `/daily` | Daily claim (Discord) |
| `/rank` | Rank / XP |
| `/quicksell` | Sell card for gold |
| `/drop` | Dev-gated; see above |

### `cogs/card_game.py`

| Command | Notes |
|---------|--------|
| `/deck` | Battle deck |
| `/stats` | Battle stats |
| `/leaderboard` | Leaderboard |
| `/open_pack` | Open pack |
| `/create_pack` | Create pack |
| `/premium_subscribe` | Server premium |
| `/server_info` | Server subscription info |

### `cogs/marketplace.py`

| Command |
|---------|
| `/sell`, `/buy`, `/market`, `/pack`, `/packs`, `/buy_pack`, `/delist` |

### `cogs/battle_commands.py`

| Command |
|---------|
| `/battle`, `/battle_stats` |

### `cogs/battlepass_commands.py`

| Command |
|---------|
| `/battlepass`, `/claim_bp` |

### `cogs/trade_commands.py`

| Command |
|---------|
| `/trade`, `/trade_history` |

### `cogs/dust_commands.py`

| Command |
|---------|
| `/dust`, `/craft`, `/boost`, `/reroll`, `/buy_pack_dust`, `/dust_shop` |

### `cogs/admin_commands.py`

| Command | Notes |
|---------|--------|
| `/server_analytics` | Admin; premium feature gate in handler |
| `/dev_grant_all_cards` | Restricted to `DEV_USER_IDS` |

### Dev-only (when `ENABLE_DEV_COMMANDS=true`)

See dev table above, plus `/import_packs` from `cogs/admin_bulk_import.py`.

## Telegram API (representative)

| Area | Prefix / paths |
|------|----------------|
| Users | `/api/me`, `/api/link/generate`, `/api/players/search` |
| Cards | `/api/cards`, `/api/cards/{id}` |
| Packs | `/api/packs`, `/api/packs/store`, `/api/packs/{id}/open`, `/api/packs/{id}/purchase` |
| Economy | `/api/economy`, `/api/economy/daily`, `/api/leaderboard` |
| Battle | `/api/battle/*` (challenge, register, opponents, incoming, updates, accept, cancel, get by id) |
| Marketplace | `/api/marketplace`, sell, buy |
| Trades | `/api/trades` + partners routes |
| Dust | `/api/dust`, `dust_cards`, `craft_card` |
| Battle pass | `/api/battle_pass/*` |

Frontend helpers live in `tma/frontend/src/api/client.ts`; paths should match the routers in `tma/api/main.py`.

## Data Layer Notes

- `database.py` supports SQLite and PostgreSQL; treat `config/economy.py`, `config/battle_pass.py`, and `config/vip.py` as sources for numeric tuning when documenting rewards.

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

Last updated: 2026-04-02
