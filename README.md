# 🎵 Music Legends - Discord Card Game Bot with Creator Economy

Create custom music card packs, battle with friends, and earn from your creations - all on Discord!

## 🎮 Features

### 📦 **Pack Creation System**
- **Custom Packs**: Create packs with 5, 10, or 15 cards
- **Spotify Integration**: Seamless artist selection with real data
- **Automatic Stats**: Stats generated from Spotify popularity/followers
- **Creator Economy**: Earn 30% revenue from pack sales

### ⚔️ **Battle System**
- **PvP Battles**: Best-of-3 card duels
- **Smart Categories**: Impact, Skill, Longevity, Culture, Hype
- **Victory Tokens**: Earn guaranteed pack rewards
- **Ticket System**: Controlled PvP economy

### 💰 **Monetization**
- **Stripe Payments**: Real payment processing
- **Revenue Split**: 70% platform / 30% creator
- **Daily Packs**: Free daily pack claims
- **Creator Tools**: Complete pack management

## 🛠️ Tech Stack

- **Discord.py v2.7.0** - Bot framework
- **Spotify Web API** - Artist data and stats
- **Stripe** - Payment processing
- **SQLite** - Database storage
- **Flask** - Webhook server

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Spotify API credentials (optional)
- Stripe account (for payments)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/samuraifrenchienft/Music-Legends.git
cd Music-Legends
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
cp .env.txt.example .env.txt
# Edit .env.txt with your credentials
```

**Required for basic functionality:**
- `BOT_TOKEN` - Your Discord bot token
- `APPLICATION_ID` - Your Discord application ID  
- `TEST_SERVER_ID` - Your test server ID (or 0 for global)

**Optional for enhanced features:**
- `SPOTIFY_CLIENT_ID` & `SPOTIFY_CLIENT_SECRET` - Spotify API access
- `STRIPE_SECRET_KEY` & `STRIPE_WEBHOOK_SECRET` - Payment processing
- `YOUTUBE_API_KEY` - Music video integration

4. **Run the bot**
```bash
python main.py
```

## 📋 Environment Variables

Copy `.env.txt.example` to `.env.txt` and configure:

### Required (Basic Functionality)
```env
BOT_TOKEN=your_discord_bot_token
APPLICATION_ID=your_application_id
TEST_SERVER_ID=your_test_server_id
```

### Optional (Enhanced Features)
```env
# Spotify Integration
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# Stripe Payments
STRIPE_SECRET_KEY=sk_test_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# YouTube Integration
YOUTUBE_API_KEY=your_youtube_api_key
```

**Note**: The bot works with just the required Discord credentials. All other features have mock fallbacks when API keys aren't provided.

## 🎯 Commands

### Pack Creation
- `/pack_create <name> <description> <size>` - Create new pack
- `/pack_add_artist_smart` - Smart Spotify artist selection
- `/pack_add_artist` - Manual artist addition
- `/pack_preview` - Preview and validate pack
- `/pack_publish` - Publish pack (requires payment)
- `/pack_cancel` - Cancel draft pack
- `/packs` - Browse available packs

### Gameplay
- `/claimpack` - Claim daily pack
- `/battle <user>` - Challenge to PvP duel
- `/redeem` - Redeem victory token
- `/collection` - View your card collection

### Management
- `/stats` - View your statistics
- `/leaderboard` - Global rankings
- `/help` - Show all commands

## 💾 Database Schema

### Core Tables
- `creator_packs` - Pack information and status
- `creator_pack_limits` - Creator restrictions and cooldowns
- `cards` - Minimal Spotify-canonical card storage
- `pack_purchases` - Purchase tracking with revenue splits
- `creator_revenue` - Earnings tracking

### Card Storage Philosophy
- **Spotify Canonical**: Store IDs, not huge catalogs
- **Computed Stats**: Generate once, store forever
- **Minimal Data**: Only essential fields stored

## 🎵 Stat Generation System

### Input Signals (Spotify)
- **Popularity** (0-100)
- **Followers** (log scaled)
- **Genres** (for flavor)

### Output Stats
- **Impact** - Overall influence
- **Skill** - Technical ability
- **Longevity** - Career endurance
- **Culture** - Cultural impact
- **Hype** - Current momentum (tie-breaker)

### Rarity Assignment
- **0-39**: Common
- **40-59**: Rare  
- **60-74**: Epic
- **75-89**: Legendary
- **90-100**: Mythic (official packs only)

## 💰 Economy System

### Creator Revenue
- **Pack Publishing**: 30% of publishing fee
- **Pack Sales**: 30% of purchase price
- **Future Trading**: 0.5% of trading fees

### Player Economy
- **Daily Packs**: Free pack every 24 hours
- **Victory Tokens**: Guaranteed from PvP wins
- **Tickets**: PvP entry currency from PvE
- **Coins**: Consolation rewards

## 🎮 Battle Rules

### Format
- **Best-of-3** rounds
- **3 cards per player**
- **Category selection**: Random → Loser picks → Random

### Categories
- Impact / Skill / Longevity / Culture

### Tie-breakers
1. Higher Hype stat
2. Higher total power
3. Coin flip (rare)

## 🌐 Deployment

### Discord Bot
1. Create Discord application and bot
2. Invite bot to server with required permissions
3. Set up slash commands (auto-sync on startup)

### Stripe Webhook
1. Deploy `stripe_webhook.py` to hosting service
2. Configure webhook endpoint in Stripe dashboard
3. Set webhook secret in environment variables

### Database
- SQLite database created automatically
- No external database required
- All data persisted locally

## 🔧 Configuration

### Pack Sizes & Pricing
- **Micro Pack** (5 cards): $10.00
- **Mini Pack** (10 cards): $25.00
- **Event Pack** (15 cards): $50.00

### Creator Limits
- **1 live pack** per creator at a time
- **7-day cooldown** between publications
- **Maximum 92** stats for creator packs

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Discord Server**: [Join our community](https://discord.gg/yourserver)
- **GitHub Issues**: [Report bugs](https://github.com/samuraifrenchienft/Music-Legends/issues)
- **Documentation**: [Wiki](https://github.com/samuraifrenchienft/Music-Legends/wiki)

## 🎯 Roadmap

- [ ] Song card creation
- [ ] Trading system
- [ ] Tournament mode
- [ ] Mobile app
- [ ] NFT integration

---

**Built with ❤️ for the Discord music community**
