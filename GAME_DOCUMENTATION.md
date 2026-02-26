# 🎵 Music Legends - Game Documentation

Technical reference for the Music Legends Discord card game.

## Table of Contents
1. [Card System](#card-system)
2. [Pack System](#pack-system)
3. [Battle System](#battle-system)
4. [Economy](#economy)
5. [Season / Battle Pass](#season--battle-pass)
6. [VIP Membership](#vip-membership)
7. [Marketplace & Trading](#marketplace--trading)
8. [Stripe Payments](#stripe-payments)
9. [Database Schema](#database-schema)
10. [Slash Commands Reference](#slash-commands-reference)
11. [Project Structure](#project-structure)

---

## Card System

### Card Stats

Each artist card has five core stats (0–100):

| Stat | Description |
|------|-------------|
| **Impact** | Overall influence and popularity |
| **Skill** | Technical ability and artistry |
| **Longevity** | Career endurance and relevance |
| **Culture** | Cultural significance and impact |
| **Hype** | Current momentum (tie-breaker in battles) |

### Rarity Tiers

| Rarity | Emoji | Stat Range | Daily Drop Rate |
|--------|-------|------------|-----------------|
| Common | ⚪ | 0–39 | 70% |
| Rare | 🔵 | 40–59 | 25% |
| Epic | 🟣 | 60–74 | 5% |
| Legendary | ⭐ | 75–89 | 0% (packs only) |
| Mythic | 🔴 | 90–100 | 0% (season rewards only) |

### Card Acquisition

| Source | Details |
|--------|---------|
| Daily Claim | 1 free random card per day (70% Common, 25% Rare, 5% Epic) |
| Built-In Packs | `/buy_pack` — random cards from master DB using tier odds |
| Creator Packs | `/packs` — hand-curated cards from community creators |
| Card Drops | `/drop` spawns cards in channel; players react to grab |
| Battle Rewards | Consolation gold for losers |
| Season Rewards | Exclusive cards at specific Battle Pass tiers |

---

## Pack System

### Built-In Tier Packs

Purchased via `/buy_pack` or the Shop menu's **Buy Pack** button. Cards are pulled randomly from the master `cards` table using weighted rarity odds.

| Tier | Cards | USD | Gold | Tickets | Bonus Gold | Bonus Tickets | Rarity Odds |
|------|-------|-----|------|---------|------------|---------------|-------------|
| Community | 5 | $2.99 | 500 | — | +100 | — | 80% Common, 20% Rare |
| Gold | 5 | $4.99 | — | 100 | +250 | +2 | 40% Common, 30% Rare, 20% Epic, 10% Legendary |
| Platinum | 10 | $6.99 | 2,500 | 200 | +500 | +5 | 25% Common, 35% Rare, 25% Epic, 15% Legendary |

**Flow**: User selects tier → sees price/odds embed → picks "Buy with Gold" or "Buy Pack (Stripe)" → system rolls random cards → grants to user → pack opening animation.

### Creator Packs

Community-created packs with hand-picked artist cards. Browsed via `/packs` with genre filters (EDM, Rock, R&B, Pop, Hip Hop). Created via `/create_pack` on the dev server.

### Pack Definitions (`schemas/pack_definition.py`)

Additional pack tiers defined internally:

| Key | Name | Cards | Price | Notes |
|-----|------|-------|-------|-------|
| starter | Starter Pack | 3 | $2.99 | Mapped to "community" tier |
| silver | Silver Pack | 4 | $4.99 | Guaranteed gold rarity |
| gold | Gold Pack | 5 | $6.99 | Epic chances |
| platinum | Platinum Pack | 10 | $6.99 | Hero slot, legendary chances |
| black | Black Pack | 5 | $9.99 | Hero slot guaranteed |
| founder_gold | Founder Gold | 7 | $19.99 | Guaranteed epics |
| founder_black | Founder Black | 8 | $29.99 | Guaranteed platinums |

---

## Battle System

### Mechanics

- **Format**: Best-of-3 rounds, first to 2 wins
- **Decks**: Top 3 cards per player
- **Categories**: Impact, Skill, Longevity, Culture (randomly selected per round)
- **Critical Hits**: 15% chance, 1.5x damage multiplier
- **Hype Bonus**: Winners gain +5 hype next round (capped at +10)
- **Tie-Breaking**: Higher Hype stat → higher total power → coin flip

### Wager Tiers (`config/economy.py`)

| Tier | Wager | Win Total | Win XP | Loss Consolation | Loss XP | Tie Gold | Tie XP |
|------|-------|-----------|--------|------------------|---------|----------|--------|
| Casual | 50g | 100g | 25 | 10g | 5 | 25g | 10 |
| Standard | 100g | 175g | 38 | 10g | 5 | 25g | 10 |
| High Stakes | 250g | 350g | 50 | 10g | 5 | 25g | 10 |
| Extreme | 500g | 650g | 75 | 10g | 5 | 25g | 10 |

### Commands

- `/battle <@opponent>` — Challenge with wager selection
- `/battle_stats [user]` — View battle record

---

## Economy

### Daily Streak Rewards

| Streak | Gold | Tickets |
|--------|------|---------|
| Day 1 (default) | 100 | 0 |
| Day 3 | 150 | 0 |
| Day 7 | 300 | 1 |
| Day 14 | 600 | 2 |
| Day 30 | 1,100 | 5 |

Each daily claim also grants **1 free random card** and **+50 XP**.

### Card Sell Prices

| Rarity | Base | Duplicate Bonus (1.5x) |
|--------|------|------------------------|
| Common | 10g | 15g |
| Rare | 25g | 38g |
| Epic | 75g | 113g |
| Legendary | 200g | 300g |

### Rank Progression

| Rank | XP Required | Wins Required | Emoji |
|------|-------------|---------------|-------|
| Bronze | 0 | 0 | 🥉 |
| Silver | 100 | 10 | 🥈 |
| Gold | 250 | 25 | 🥇 |
| Platinum | 500 | 50 | 💎 |
| Diamond | 1,000 | 100 | 💠 |
| Legend | 2,500 | 250 | 👑 |

### Starting Resources
- 500 Gold, 0 Tickets, 0 Dust, 0 Gems

---

## Season / Battle Pass

### Season 1: Rhythm Rising (`config/battle_pass.py`)

| Setting | Value |
|---------|-------|
| Duration | 60 days |
| Total Tiers | 50 |
| Premium Price | $9.99 |
| Tier Skip | $1.00 or 10 tickets |
| Total XP Required | 14,500 |

### XP Sources

| Activity | XP |
|----------|-----|
| Daily Claim | +50 |
| Battle Win | +25 |
| Battle Loss | +5 |
| Quest Complete | +100 |
| First Win of Day | +50 |
| Friend Battle | +10 |

### XP Per Tier (Progressive)

| Tiers | XP Each |
|-------|---------|
| 1–5 | 100 |
| 6–10 | 150 |
| 11–15 | 200 |
| 16–20 | 250 |
| 21–30 | 300 |
| 31–40 | 400 |
| 41–50 | 500 |

### Reward Tracks

**Free Track** (all players):
- Gold rewards scaling from 100 to 4,000
- Common, Rare, Epic, Legendary card drops at various tiers
- XP boosts (10%–50% duration)
- Community Packs at tiers 10, 20, 30, 40
- Tickets (1–3)
- **Tier 50**: "Rhythm Rising Champion" Mythic exclusive card

**Premium Track** ($9.99 unlock):
- All free track rewards plus:
- Exclusive cosmetics (card backs, badges, emotes, profile frames)
- Gold Packs (1–10 packs total)
- Extra tickets (5–50 total)
- Exclusive cards ("Rhythm Rising Elite", "Master", "Legend", "Ultimate")
- **Tier 50**: Ultimate bundle — 10,000 gold, 100 tickets, 10 Gold Packs

### Commands

| Command | Description |
|---------|-------------|
| `/battlepass` | View tier progress, claim rewards |
| `/season_info` | Season details and countdown |
| `/season_progress` | Level, XP, and rank |
| `/season_rewards` | Browse all rewards |
| `/season_leaderboard` | Top 25 players |
| `/claim_reward <id>` | Claim earned reward |

---

## VIP Membership

**$4.99/month** or **50 tickets** (`config/vip.py`)

### Daily Bonuses
| Perk | VIP | Non-VIP |
|------|-----|---------|
| Daily Gold | 200 | 100 |
| Daily Tickets | +1 | 0 |
| Monthly Pack | Free Gold Pack | — |
| XP Boost | +50% | — |

### Battle Bonuses
| Perk | VIP | Non-VIP |
|------|-----|---------|
| Gold Multiplier | 1.5x | 1.0x |
| XP Multiplier | 1.5x | 1.0x |
| Wager Protection | Lose only 50% | Lose full |
| Win Streak Bonus | +25g/win (max +250) | — |

### Marketplace Perks
| Perk | VIP | Non-VIP |
|------|-----|---------|
| Listing Fee | 0% | 10% |
| Trade Fee | 0g | 50g |
| Trade Limit | 20/day | 5/day |
| Marketplace Slots | 10 | 3 |
| Priority Placement | Yes | No |

### Cosmetics
- Gold username color, VIP Crown Badge, exclusive profile frame
- Monthly rotating card backs, 5 exclusive emotes
- Gold battle entrance animation, gold leaderboard highlight

---

## Marketplace & Trading

### Marketplace Commands

| Command | Description |
|---------|-------------|
| `/sell <card_id> <price>` | List a card for sale |
| `/buy <card_id>` | Purchase a card |
| `/market` | View all listings |

### Trading Rules (`config/economy.py`)

| Setting | Value |
|---------|-------|
| Direct Trade Fee | 10% (both sides) |
| Trade Cooldown | 24 hours (same card) |
| Max Trades/Day | 5 (20 for VIP) |
| Marketplace Listing Fee | 5% |
| Marketplace Sale Fee | 10% |
| Max Active Listings | 10 |

---

## Stripe Payments

### Checkout Types (`stripe_payments.py`)

| Type | Metadata Key | Handler |
|------|-------------|---------|
| Built-in tier pack | `tier_pack_purchase` | `_fulfill_tier_pack_purchase()` |
| Creator pack | `pack_purchase` | `_fulfill_pack_purchase()` |
| Battle Pass Premium | `battlepass_purchase` | `_fulfill_battlepass_purchase()` |

### Webhook Flow (`webhooks/stripe_hook.py`)

1. Stripe sends `checkout.session.completed` event
2. Webhook reads `metadata.type` to route to correct handler
3. Handler grants cards/items, records purchase in `purchases` table
4. For tier packs: calls `db.generate_tier_pack_cards()` which rolls random cards by rarity

---

## Database Schema

### Core Tables

```
users               — User profiles (user_id, username, discord_tag)
user_inventory      — Economy (gold, tickets, dust, gems, xp, level, daily_streak)
cards               — Master card catalog (card_id, name, rarity, tier, stats, image_url)
user_cards          — Ownership (user_id, card_id, acquired_from)
creator_packs       — Pack metadata (pack_id, creator_id, name, cards_data JSON, status, price)
purchases           — Transaction audit (purchase_id, user_id, pack_id, amount_cents, payment_method)
battle_matches      — Battle history and results
season_progress     — Battle Pass tier tracking, claimed rewards
marketplace_listings — Card sales
audit_logs          — Action logging
```

### Relationships

- `users` → `user_inventory` (1:1 economy data)
- `users` → `user_cards` → `cards` (collection ownership)
- `users` → `battle_matches` (battle history)
- `users` → `creator_packs` (pack creation)
- `creator_packs` → `purchases` (sales tracking)
- `users` → `season_progress` (Battle Pass state)

---

## Slash Commands Reference

### Player Commands

| Command | Cog File | Description |
|---------|----------|-------------|
| `/buy_pack` | `cogs/marketplace.py` | Purchase tier pack (Community/Gold/Platinum) |
| `/packs [genre]` | `cogs/marketplace.py` | Browse creator packs by genre |
| `/buy <card_id>` | `cogs/marketplace.py` | Buy card from marketplace |
| `/sell <card_id> <price>` | `cogs/marketplace.py` | List card for sale |
| `/market` | `cogs/marketplace.py` | View marketplace listings |
| `/pack` | `cogs/marketplace.py` | View your available packs |
| `/open_pack <pack_id>` | `cogs/card_game.py` | Open a pack |
| `/deck` | `cogs/card_game.py` | View battle deck (top 3 cards) |
| `/stats` | `cogs/card_game.py` | View battle statistics |
| `/leaderboard [metric]` | `cogs/card_game.py` | Global rankings |
| `/battle <@opponent>` | `cogs/battle_commands.py` | Challenge to battle |
| `/battle_stats [user]` | `cogs/battle_commands.py` | Battle record |
| `/drop` | `cogs/gameplay.py` | Spawn card drop in channel |
| `/grab <card_number>` | `cogs/gameplay.py` | Grab card from active drop |

### Season Commands

| Command | Cog File | Description |
|---------|----------|-------------|
| `/battlepass` | `cogs/battlepass_commands.py` | Battle Pass progress and rewards |
| `/season_info` | `cogs/battlepass_commands.py` | Season details and countdown |
| `/season_progress` | `cogs/battlepass_commands.py` | Level, XP, rank |
| `/season_rewards` | `cogs/battlepass_commands.py` | Browse rewards |
| `/season_leaderboard` | `cogs/battlepass_commands.py` | Top 25 players |
| `/claim_reward <id>` | `cogs/battlepass_commands.py` | Claim earned reward |

### Admin Commands

| Command | Cog File | Description |
|---------|----------|-------------|
| `/setup_user_hub` | `cogs/menu_system.py` | Post persistent User Hub |
| `/start_game` | `cogs/start_game.py` | Initialize bot in server |
| `/server_analytics [days]` | `cogs/admin_commands.py` | Usage analytics (premium) |
| `/server_info` | `cogs/card_game.py` | Server subscription status |
| `/premium_subscribe` | `cogs/card_game.py` | Upgrade to Premium |
| `/create_pack <artist>` | `cogs/card_game.py` | Create pack (dev server) |

---

## Project Structure

```
├── main.py                     # Bot entry point, DB init, cog loader
├── database.py                 # DatabaseManager — all DB operations
├── stripe_payments.py          # Stripe checkout session creation
├── battle_engine.py            # Battle logic, stat comparison, crits
├── card_data.py                # Card data management
├── discord_cards.py            # Card display components
│
├── config/
│   ├── economy.py              # Daily rewards, wagers, ranks, pack pricing
│   ├── battle_pass.py          # Season config, tier rewards, XP sources
│   └── vip.py                  # VIP membership config
│
├── schemas/
│   └── pack_definition.py      # PackDefinition dataclass, PACK_DEFINITIONS registry
│
├── cogs/
│   ├── card_game.py            # /deck, /stats, /leaderboard, /open_pack, /create_pack
│   ├── marketplace.py          # /buy_pack, /packs, /sell, /buy, /market + tier views
│   ├── menu_system.py          # /setup_user_hub, ShopView, BattleView, User Hub
│   ├── battle_commands.py      # /battle, /battle_stats
│   ├── battlepass_commands.py  # /battlepass, /season_info, /season_progress, etc.
│   ├── gameplay.py             # /drop, /grab
│   ├── start_game.py           # /start_game
│   ├── admin_commands.py       # /server_analytics
│   └── admin_bulk_import.py    # /import_packs (dev only)
│
├── views/
│   └── pack_opening.py         # PackOpeningAnimator, open_pack_with_animation()
│
├── webhooks/
│   └── stripe_hook.py          # Stripe webhook handlers
│
├── infrastructure/             # Bot infrastructure utilities
├── scheduler/                  # Background jobs
├── Dockerfile                  # Production container
├── railway.toml                # Railway config
├── nixpacks.toml               # Alt build system
└── requirements.txt            # Python dependencies
```

---

**Last Updated**: February 2026
**Version**: 3.0
