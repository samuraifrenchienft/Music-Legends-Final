# Music Legends Player Guide

Last updated: 2026-04-02

This guide reflects the intended live gameplay surfaces: Discord (full command set) and Telegram Mini App (mobile-first UI with API-backed features).

## Where To Play

- **Discord:** Full command set, menus, and fastest access to every loop.
- **Telegram:** Open the bot DM and use the Mini App for cards, packs, battles, daily rewards, and linked economy flows.

Recommended flow:

1. Discover the game in a group or server.
2. Open the bot private chat.
3. Use `/menu` (Discord) or **Play** / Mini App (Telegram).

## Quick Start

### Discord

1. Join a server that has Music Legends (or ask an admin to run `/start_game` to set the bot up).
2. Run `/menu` or use the **User Hub** posted with `/setup_user_hub`.
3. Claim rewards with `/daily`, browse `/collection`, and use `/packs` / `/open_pack` as you progress.
4. Use `/battle` and `/trade` when you are ready for PvP and player trades.

### Telegram

1. Open a private chat with the bot.
2. Use `/start` to launch the Mini App (or your bot’s configured entry).
3. Use the app sections: Home, Cards, Packs, Battle, Daily.
4. Use `/link` if you need to connect Telegram to an existing Discord account.

## Discord Commands (current production load)

Slash names are unique—there is no duplicate command for the same name. The list below is grouped for readability; optional dev-only commands are omitted here (see `GAME_DOCUMENTATION.md` if `ENABLE_DEV_COMMANDS` is on).

### Menu and server

- `/menu` — main menu  
- `/start_game` — **server setup** (onboard the game to a server; not the same as daily rewards)  
- `/setup_user_hub` — post the persistent hub (admins)  
- `/post_game_info` — post the full guide (admins)

### Collection, profile, and daily

- `/collection`, `/view`, `/card`, `/lookup`  
- `/deck`, `/stats`, `/leaderboard`, `/rank`  
- `/daily` — claim daily rewards on Discord  

### Packs and card actions

- `/pack`, `/packs`, `/buy_pack`, `/open_pack`  
- `/burn`, `/upgrade`, `/quicksell`  
- `/create_pack` — pack creation where enabled  

### Marketplace

- `/market`, `/buy`, `/sell`, `/delist`

### Battles and progression

- `/battle`, `/battle_stats`  
- `/battlepass`, `/claim_bp`  

### Trades

- `/trade`, `/trade_history`

### Dust economy

- `/dust`, `/craft`, `/boost`, `/reroll`, `/buy_pack_dust`, `/dust_shop`

### Server premium (where applicable)

- `/premium_subscribe`, `/server_info`

## Gameplay Loops

- **Daily loop:** claim on Discord (`/daily`) or in the Telegram Mini App; keep streaks and currency flowing.  
- **Collection loop:** acquire packs, open them, refine your deck.  
- **PvP loop:** challenges and wagers on Discord or in the Mini App.  
- **Economy loop:** marketplace, trades, dust—Discord has the full command set; Telegram uses in-app flows backed by `/api/marketplace`, `/api/trades`, `/api/dust` where implemented in the UI.  
- **Progression loop:** battle pass tiers (`/battlepass` / `/claim_bp` on Discord; Telegram battle pass API may still be partial—check in-app behavior).

## Important Telegram Notes

- Groups are best for discovery; play from the bot DM + Mini App.  
- Feature parity with Discord is intentionally broader on Discord; the Mini App focuses on touch-friendly flows.  

## FAQ

**Do I play in Telegram groups directly?**  
No. Use groups for discovery, then open the bot privately.

**What should new players do first?**  
Claim daily rewards, open packs, run a battle, then explore market/trade/dust as you like.

**Where are all options easiest to access?**  
Discord `/menu` and the Telegram Mini App navigation.

For technical detail and admin/dev command listings, see `GAME_DOCUMENTATION.md`.
