# 🎵 Music Legends — Discord Card Game

Music Legends is a Discord card game where players collect artist cards, build decks, battle friends, buy packs with gold or Stripe, and compete in seasonal events for exclusive rewards.

## 🚀 **Current Status: PRODUCTION READY** ✅

- ✅ **Battle System**: 4-tier wager system with critical hits
- ✅ **Pack System**: Buy built-in tier packs (Community/Gold/Platinum) or browse creator packs
- ✅ **Season System**: 60-day Battle Pass with 50 tiers of free + premium rewards
- ✅ **VIP Membership**: $4.99/month with battle bonuses, marketplace perks, and cosmetics
- ✅ **Marketplace**: Buy/sell cards, browse creator packs by genre
- ✅ **Stripe Payments**: Secure checkout for packs, Battle Pass, and VIP
- ✅ **Audio/Visual Feedback**: Sound effects and animated GIFs for special moments
- ✅ **Railway Deployment**: Docker containerized and running

---

## 🎮 **For Players (How to Play)**

### **Getting Started**
1. Join a server with the Music Legends bot
2. Click **Daily Claim** in the User Hub to get your first gold + a free card
3. Use `/buy_pack` to purchase your first pack
4. Use `/battle @user` to challenge someone
5. Track your progress with `/season_progress`

### **Core Commands**
| Command | Description |
|---------|-------------|
| `/buy_pack` | Purchase a tier pack (Community, Gold, or Platinum) |
| `/packs` | Browse creator packs by genre |
| `/open_pack <pack_id>` | Open a specific pack |
| `/battle <@user>` | Challenge a player to a card battle |
| `/battle_stats [user]` | View battle record and statistics |
| `/deck` | View your battle deck (top 3 cards) |
| `/stats` | View your battle statistics |
| `/leaderboard [metric]` | View global rankings |
| `/sell <card_id> <price>` | List a card for sale on the marketplace |
| `/buy <card_id>` | Purchase a card from the marketplace |
| `/market` | View marketplace listings |

### **Season & Battle Pass Commands**
| Command | Description |
|---------|-------------|
| `/battlepass` | View tier progress, rewards, and claim tiers |
| `/season_info` | Current season details and countdown |
| `/season_progress` | Your level, XP, and rank |
| `/season_rewards` | Browse available rewards |
| `/season_leaderboard` | Top 25 players |
| `/claim_reward <id>` | Claim your earned rewards |

### **User Hub** (Persistent Menu)
Admins post the User Hub via `/setup_user_hub`. Players use its buttons for:
- **Daily Claim** — Claim daily gold + free card (streak bonuses up to 1,100g at 30 days)
- **Collection** — View all owned cards
- **Stats** — Personal battle statistics
- **Battle Pass** — Season progress and rewards
- **VIP** — Membership status and benefits
- **Help** — How-to guide

---

## 📦 **Pack System**

### **Built-In Tier Packs** (`/buy_pack`)

| Tier | Price (USD) | Price (Gold/Tickets) | Cards | Bonuses |
|------|-------------|----------------------|-------|---------|
| **Community** | $2.99 | 500 Gold | 5 | +100 Gold |
| **Gold** | $4.99 | 100 Tickets | 5 | +250 Gold, +2 Tickets |
| **Platinum** | $6.99 | 2,500 Gold or 200 Tickets | 10 | +500 Gold, +5 Tickets |

Built-in packs pull **random cards from the master card database** using weighted rarity odds. Each tier has different odds for Common, Rare, Epic, and Legendary cards.

You can also access this from the **Shop menu** → **Buy Pack** button.

### **Creator Packs** (`/packs`)
Browse and buy community-created packs organized by genre (EDM, Rock, R&B, Pop, Hip Hop). Creator packs contain hand-picked artist cards.

---

## ⚔️ **Battle System**

### **How Battles Work**
- **Best-of-3 Rounds**: First to win 2 rounds wins the match
- **3-Card Decks**: Each player uses their top 3 cards
- **Stat Categories**: Impact, Skill, Longevity, Culture
- **Critical Hits**: 15% chance for 1.5x damage multiplier

### **Wager Tiers**

| Tier | Wager | Winner Gets | Winner XP | Loser Gets | Loser XP |
|------|-------|-------------|-----------|------------|----------|
| Casual | 50g | 100g | 25 XP | 10g | 5 XP |
| Standard | 100g | 175g | 38 XP | 10g | 5 XP |
| High Stakes | 250g | 350g | 50 XP | 10g | 5 XP |
| Extreme | 500g | 650g | 75 XP | 10g | 5 XP |

---

## 🏆 **Season System (Battle Pass)**

### **Season 1: Rhythm Rising**
- **Duration**: 60 days
- **Tiers**: 50 (free track + premium track)
- **Premium Unlock**: $9.99
- **Tier Skip**: $1.00 or 10 tickets per tier

### **Earning XP**

| Activity | XP |
|----------|-----|
| Daily Claim | +50 XP |
| Battle Win | +25 XP |
| Battle Loss | +5 XP |
| Quest Complete | +100 XP |
| First Win of Day | +50 XP |
| Friend Battle | +10 XP |

### **Rank Progression**

| Rank | XP Required | Wins Required |
|------|-------------|---------------|
| 🥉 Bronze | 0 | 0 |
| 🥈 Silver | 100 | 10 |
| 🥇 Gold | 250 | 25 |
| 💎 Platinum | 500 | 50 |
| 💠 Diamond | 1,000 | 100 |
| 👑 Legend | 2,500 | 250 |

### **Rewards**
- **Free Track**: Gold (100–4,000), Common/Rare/Epic/Legendary cards, XP boosts, Community Packs, Tickets
- **Premium Track**: All free rewards + exclusive cosmetics, Gold Packs, extra tickets, exclusive cards
- **Tier 50 Free**: "Rhythm Rising Champion" Mythic card
- **Tier 50 Premium**: Ultimate bundle (10,000 gold, 100 tickets, 10 Gold Packs)

---

## 👑 **VIP Membership**

**$4.99/month** (or 50 tickets)

| Perk | VIP | Non-VIP |
|------|-----|---------|
| Daily Gold | 200 | 100 |
| Daily Tickets | +1 | 0 |
| Battle Gold Multiplier | 1.5x | 1.0x |
| Battle XP Multiplier | 1.5x | 1.0x |
| Wager Protection | Lose only 50% | Lose full wager |
| Marketplace Listing Fee | 0% | 10% |
| Trade Fee | 0g | 50g |
| Daily Trade Limit | 20 | 5 |
| Marketplace Slots | 10 | 3 |
| Monthly Free Gold Pack | Yes | No |
| Exclusive Cosmetics | Yes | No |

---

## 💰 **Economy System**

### **Daily Streak Rewards**

| Streak | Gold | Tickets |
|--------|------|---------|
| Day 1 | 100 | 0 |
| Day 3 | 150 | 0 |
| Day 7 | 300 | 1 |
| Day 14 | 600 | 2 |
| Day 30 | 1,100 | 5 |

Every daily claim also grants a **free random card** (70% Common, 25% Rare, 5% Epic).

### **Card Selling Prices**

| Rarity | Sell Price | With Duplicate Bonus (1.5x) |
|--------|-----------|----------------------------|
| Common | 10g | 15g |
| Rare | 25g | 38g |
| Epic | 75g | 113g |
| Legendary | 200g | 300g |

### **New Player Starting Resources**
- 500 Gold, 0 Tickets

---

## 🛠️ **For Server Owners**

### **Setup**
1. Add bot to your server
2. Run `/setup_user_hub` in your main channel
3. (Optional) Create a support ticket for revenue sharing

### **Admin Commands**
| Command | Description |
|---------|-------------|
| `/setup_user_hub` | Post the persistent User Hub menu |
| `/start_game` | Initialize Music Legends in the server |
| `/server_analytics [days]` | View server usage analytics (premium) |
| `/server_info` | View server subscription status |
| `/premium_subscribe` | Upgrade server to Premium |

### **Revenue Sharing (FREE BOT!)**
- **10% base** revenue share from all purchases in your server
- **+10% per NFT** you own (up to 2 NFTs = 30% max)
- **Weekly payouts** via Stripe Connect ($25 minimum)
- Set up via support ticket in the official server

---

## 🏗️ **Technical Architecture**

### **Key Integrations**
- **YouTube API**: Video search and thumbnail extraction
- **TheAudioDB**: Artist images and metadata
- **Last.fm**: Music data and statistics
- **Spotify**: Artist information (fallback)
- **Stripe**: Payment processing for packs, Battle Pass, and VIP

### **Database**
SQLite (local) or PostgreSQL (via `DATABASE_URL`). Core tables: `users`, `user_inventory`, `cards`, `user_cards`, `creator_packs`, `purchases`, `battle_matches`, `season_progress`, `marketplace_listings`, `audit_logs`.

### **Project Structure**
```
├── main.py                 # Bot entry point
├── database.py             # Database management
├── stripe_payments.py      # Stripe checkout sessions
├── config/
│   ├── economy.py          # All pricing, rewards, ranks
│   ├── battle_pass.py      # Season/Battle Pass config
│   └── vip.py              # VIP membership config
├── schemas/
│   └── pack_definition.py  # Pack tier definitions and odds
├── cogs/
│   ├── card_game.py        # Core game commands (deck, stats, leaderboard)
│   ├── marketplace.py      # Buy/sell, packs, /buy_pack
│   ├── menu_system.py      # User Hub, Shop, Battle menus
│   ├── battle_commands.py  # /battle, /battle_stats
│   ├── battlepass_commands.py # Season & Battle Pass commands
│   ├── gameplay.py         # Card drops and grabs
│   ├── start_game.py       # Server initialization
│   └── admin_commands.py   # Server analytics
├── views/
│   └── pack_opening.py     # Pack opening animation
├── webhooks/
│   └── stripe_hook.py      # Stripe webhook fulfillment
└── requirements.txt
```

---

## 🚀 **Deployment**

### **Railway (Production)**
```bash
# Dockerfile-based deployment with environment variables
# SQLite with automatic backups, full logging
```

### **Local Development**
```bash
git clone https://github.com/samuraifrenchienft/Music-Legends
cd Music-Legends
pip install -r requirements.txt
cp .env.txt.example .env.txt
# Edit .env.txt with your tokens
python main.py
```

### **Environment Variables**
```env
BOT_TOKEN=your_discord_bot_token
DISCORD_APPLICATION_ID=your_application_id
TEST_SERVER_ID=your_test_server_id
YOUTUBE_API_KEY=your_youtube_api_key
LASTFM_API_KEY=your_lastfm_api_key
AUDIODB_API_KEY=1
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
DEV_USER_IDS=your_discord_user_id
```

---

## 📚 **Documentation**

- **[Player Guide](PLAYER_GUIDE.md)** — Seasons, daily rewards, marketplace tips
- **[Game Documentation](GAME_DOCUMENTATION.md)** — Technical details, card system, database schema

---

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 🆘 **Support**

- **GitHub Issues**: [Report bugs](https://github.com/samuraifrenchienft/Music-Legends/issues)

---

**Last Updated**: February 2026
**Version**: 3.0 (Buy Pack + Battle Pass + VIP)
