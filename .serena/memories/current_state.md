# Music Legends Bot — Current State

## Active Branch / Worktree
- **Main branch:** `C:/Users/AbuBa/Desktop/Music-Legends` (commit 23a3289)
- **TMA worktree:** `C:/Users/AbuBa/Desktop/Music-Legends/.worktrees/feature-tma`
- **TMA branch latest commit:** e22d04d — Home stats grid + MainButton; Collection animated cards + skeleton

## Current Focus: Telegram Mini App (feature-tma worktree)
Plan file: `docs/plans/2026-02-21-telegram-mini-app-v2.md`

### TMA Tasks — Status
- [x] Task 1: Schema migration — platform-agnostic identity + battle table
- [x] Task 2: New DatabaseManager methods for TMA
- [x] Task 3: FastAPI skeleton + initData auth
- [x] Task 4: Users router — `/api/me` and `/api/link`
- [x] Task 5: Cards router
- [x] Task 6: Packs router
- [x] Task 7: Economy router
- [x] Task 8: Battle router — challenge + accept + poll
- [x] Task 9: Bot handlers + webhook route
- [x] Task 10: Vite scaffold + TMA SDK setup
- [x] Task 11: TMA initialization + API client
- [x] Task 12: App.tsx routing + theme + NavBar with BackButton
- [x] Task 13: Animated card component
- [x] Task 14: Home page with MainButton
- [x] Task 15: Collection page
- [x] Task 16: Pack opening page with full animation sequence
- [x] Task 17: Battle page — challenge + accept flow
- [x] Task 18: Daily claim page with countdown
- [x] Task 19: Multi-stage Dockerfile
- [ ] Task 20: Railway service setup (human steps)  ← NEXT (human action required)

## Build Status
- Frontend build: CLEAN (111 modules, 339kB bundle) — commit fa96c76
- All pages TypeScript-clean and Vite-built successfully

## Latest Fixes (fa96c76)
- battle.py: `youtube_url` added to challenger + opponent in result payload
- Battle.tsx: YouTube link button shown for winning card on result screen
- Battle.tsx: "Battle Again" MainButton added to result screen (was stuck with no exit)

## TMA File Structure (worktree)
- `tma/api/main.py` — FastAPI app entry
- `tma/api/routers/` — cards, packs, economy, battle, users
- `tma/api/bot/` — python-telegram-bot handlers + webhook
- `tma/api/auth.py` — initData verification
- `tma/frontend/src/` — React+Vite TMA app

## Discord Bot (main branch) — Stable
- 40 tests passing: `python -m pytest tests/test_bot_core.py -v --noconftest`
- Latest fix: role-swap guard in battle_commands.py (commit 94aa0b0)
- **Outstanding:** live battle flow end-to-end test still needed (pack selection hang fix not verified live)

## Key Architecture Reminders
- `get_db()` singleton — ALL cogs use this, never `DatabaseManager()` directly
- Rewards BEFORE animation — Discord API failure must not orphan gold/XP
- `_PgCursorWrapper` translates SQLite-style SQL to PostgreSQL
- `pack_purchases` is source of truth for /pack command
- Pool: size=2, max_overflow=3, TCP keepalives

## Env / Secrets
- `.env` file lives in the project root (gitignored)
- Example: `env-example.txt`
