# 🎵 Music Legends — Discord Card Game

Music Legends is a Discord card game where players open packs, collect artist cards, and battle friends.

## 🎮 For Players (How to Play)

- **Open a pack:** `/pack`
- **View your cards:** `/collection`
- **Show your battle deck:** `/deck`
- **Challenge someone:** `/battle @user`

Full rules and tips:
- `GAMEPLAY_GUIDE.md`

## 🛠️ For Server Owners (Hosting the Game in Your Server)

If your server already has the Music Legends bot added, you can start immediately.

Recommended admin setup:
- `docs/DROP_SYSTEM_GUIDE.md` (drops)

## 🎯 Commands (Quick Reference)

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

## 🧩 Self‑Hosting / Developer Setup (Optional)

If you’re running your own instance of the bot (Railway/Docker/local), use these docs:

- `SETUP.md`
- `DOCKER_DEPLOYMENT.md`

Notes:

- Payments/webhooks are optional and only needed if you enable paid features.

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
