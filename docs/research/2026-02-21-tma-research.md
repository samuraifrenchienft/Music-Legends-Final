# Telegram Mini App (TMA) — Research Notes
> Saved: 2026-02-21 | Session-crash-safe reference

---

## 1. What Is a Telegram Mini App?

A Mini App (TMA) is an HTML5 web app embedded inside Telegram, opened via a bot button or inline menu. It runs in a WebView inside the Telegram client (mobile + desktop). Users never leave Telegram.

- Official docs: https://core.telegram.org/bots/webapps
- 1 billion MAU as of 2025 — massive built-in distribution
- No App Store required

---

## 2. Recommended Tech Stack (2025)

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript | Official TMA template uses this |
| TMA SDK | `@telegram-apps/sdk` | First-party Telegram SDK |
| Backend | FastAPI (Python) | Async, auto-docs, reuses our Python DB layer |
| Bot | `python-telegram-bot` (PTB 21+) | Webhook mode on Railway |
| DB | Existing Railway PostgreSQL | **Zero migration** — shared with Discord bot |
| Payments | Telegram Stars | Native TMA payment, no Stripe needed |
| Hosting | Railway | Already there; add 1-2 new services |

Official TMA React template: https://github.com/Telegram-Mini-Apps/reactjs-template

---

## 3. Authentication — How It Works

Telegram provides `initData` (URL-encoded string) when a user opens the Mini App. It contains:
- `user` — Telegram user ID, username, first_name, language_code
- `hash` — HMAC-SHA256 signature, signed with bot token

**Validation algorithm (Python):**
```python
import hmac, hashlib, urllib.parse

def validate_init_data(init_data: str, bot_token: str) -> dict | None:
    params = dict(urllib.parse.parse_qsl(init_data))
    received_hash = params.pop("hash", "")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(received_hash, expected_hash):
        return json.loads(params["user"])  # Returns user dict with telegram_user_id
    return None
```

Python libraries available:
- `telegram-init-data` — https://github.com/iCodeCraft/telegram-init-data
- `init-data-py` — https://github.com/nimaxin/init-data-py
- `telegram-webapp-auth` — https://pypi.org/project/telegram-webapp-auth/

**No JWT needed** — Telegram IS the auth provider. Each API request sends `initData` in `Authorization` header; backend validates it every time (or cache for 1hr).

---

## 4. User Identity Problem

Discord bot uses Discord user IDs (integers). Telegram users have different IDs.

**Solution:** Add `telegram_user_id` column to existing `users` table. Link on first TMA login.

```sql
ALTER TABLE users ADD COLUMN telegram_user_id BIGINT UNIQUE;
ALTER TABLE users ADD COLUMN telegram_username TEXT;
```

On first TMA login:
- Check if `telegram_user_id` already exists in `users` → return that user
- If not: create new user row with `telegram_user_id` (no Discord columns needed)
- Optional: let user link their Discord account later

---

## 5. Existing Game — What Gets Ported

### Core Database Methods (already in `database.py` — ZERO rewrite)
```
get_or_create_user()          → TMA login / registration
get_user_collection()         → Collection page
get_user_purchased_packs()    → My Packs page
open_pack_for_drop()          → Open a pack
get_user_economy()            → Show gold/XP/tickets
claim_daily_reward()          → Daily claim
get_leaderboard()             → Leaderboard
get_random_live_pack_by_tier() → Drop system
```

### Battle System (needs async-safe wrapper)
The battle logic lives in:
- `config/cards.py` → `compute_card_power()`, `compute_team_power()`, `RARITY_BONUS`
- `battle_engine.py` → `BattleEngine.execute_battle()`

These are pure Python with no Discord dependency — can be imported directly into FastAPI.

### NOT ported initially (scope control)
- Creator pack creation (complex multi-step flow)
- Stripe payments (replaced by Telegram Stars for TMA)
- Trade system
- Battle pass / quests (Phase 2+)

---

## 6. Battle Flow — TMA Adaptation

Discord battle: 2 players simultaneously select packs in real-time via Discord UI components.
TMA challenge: Can't use Discord's synchronous view system. Options:

| Option | Complexity | Latency |
|---|---|---|
| **Bot notification + polling** | Low | ~2-5s | ← **MVP choice**
| WebSocket | Medium | Real-time |
| Server-Sent Events | Medium | Real-time |

**MVP Flow:**
1. Player 1 opens TMA → "Challenge" → picks pack → submits
2. FastAPI creates `pending_battle` record → bot sends notification to Player 2
3. Player 2 opens TMA (from bot notification) → sees challenge → picks pack → submits
4. FastAPI executes battle → both players see result via polling or push

---

## 7. Telegram Stars Payment

Replaces Stripe for TMA. Native to Telegram.

- Docs: https://core.telegram.org/bots/payments-stars
- No credit card forms — 1-tap purchase
- Bot receives `successful_payment` update when user pays
- 0% Telegram commission (only taxes/Apple/Google fees on initial Stars purchase)

**Pack prices in Stars (approximate):**
- Silver Pack ($4.99 USD) ≈ 99 Stars (1 Star ≈ $0.05)
- Black Pack ($6.99 USD) ≈ 139 Stars

---

## 8. Deployment on Railway

Current Railway setup: Discord bot + PostgreSQL.

**New services to add:**
1. `tma-api` — FastAPI backend (Python) — connects to SAME PostgreSQL
2. `tma-frontend` — Static React build (Nginx or serve via FastAPI's StaticFiles)

Or combine: FastAPI serves the React `dist/` as static files + handles `/api/*` routes.
Single Railway service = simpler.

**Required env vars for TMA service:**
```
DATABASE_URL=<same as Discord bot>
TELEGRAM_BOT_TOKEN=<new bot token from @BotFather>
TELEGRAM_BOT_TOKEN_HASH=<HMAC secret derived from token>
FRONTEND_URL=https://tma.up.railway.app (or custom domain)
```

---

## 9. Project Structure (New `tma/` directory in repo)

```
tma/
├── api/
│   ├── main.py           # FastAPI app + static file mounting
│   ├── auth.py           # initData validation dependency
│   ├── database.py       # Symlink or import from ../database.py
│   ├── routers/
│   │   ├── users.py      # GET /me, POST /register
│   │   ├── cards.py      # GET /cards, GET /cards/{id}
│   │   ├── packs.py      # GET /packs, POST /packs/{id}/open
│   │   ├── battle.py     # POST /battle/challenge, GET /battle/{id}
│   │   ├── economy.py    # GET /economy, POST /daily
│   │   └── payments.py   # POST /payments/stars (webhook)
│   └── bot/
│       └── handlers.py   # Telegram bot: /start, notifications
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Collection.tsx
│   │   │   ├── Pack.tsx
│   │   │   ├── Battle.tsx
│   │   │   └── Daily.tsx
│   │   ├── components/
│   │   │   ├── CardComponent.tsx
│   │   │   ├── PowerBar.tsx
│   │   │   └── NavBar.tsx
│   │   └── api/
│   │       └── client.ts  # Axios/fetch wrapper with initData auth
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── Dockerfile             # Multi-stage: build React → serve with FastAPI
└── railway.toml
```

---

## 10. Key Libraries

**Python (add to requirements.txt):**
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-telegram-bot[webhooks]>=21.0
telegram-webapp-auth>=1.0.0
```

**Node (frontend, new package.json):**
```json
{
  "@telegram-apps/sdk": "^2.0.0",
  "react": "^18",
  "react-router-dom": "^6",
  "axios": "^1.6"
}
```

---

## Sources
- [Telegram Mini Apps Official Docs](https://core.telegram.org/bots/webapps)
- [TMA React Template](https://github.com/Telegram-Mini-Apps/reactjs-template)
- [Telegram Stars Payments](https://core.telegram.org/bots/payments-stars)
- [initData Validation](https://docs.telegram-mini-apps.com/platform/init-data)
- [python-telegram-bot](https://python-telegram-bot.org/)
