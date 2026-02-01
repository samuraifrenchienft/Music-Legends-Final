# 🎵 Music Legends — Discord Card Game

Music Legends is a Discord card game where players collect artist cards, create custom packs, battle friends, and compete in seasonal events for exclusive rewards.

## 🚀 **Current Status: PRODUCTION READY** ✅

- ✅ **Battle System**: Complete 4-tier wager system with critical hits
- ✅ **Pack Creation**: Interactive YouTube/Spotify integration  
- ✅ **Season System**: 60-day competitive seasons with exclusive rewards
- ✅ **Audio Feedback**: Enhanced celebrations with sound effects
- ✅ **Database**: SQLite with full schema support
- ✅ **Railway Deployment**: Docker containerized and running

---

## 🎮 **For Players (How to Play)**

### **Core Commands**
- **🎴 Open a pack:** `/open_pack <pack_id>`
- **👀 View your cards:** Collection button in User Hub
- **⚔️ Battle someone:** `/battle @user <wager>`
- **📊 Check stats:** `/stats`
- **🏆 Leaderboard:** `/leaderboard`
- **💰 Check balance:** `/balance`
- **🎁 Daily reward:** Click "Daily Claim" in User Hub

### **🎮 Season System (NEW!)**
Compete in 60-day seasons to earn exclusive rewards and climb the ranks!

- **📊 View Season Info:** `/season_info` - Current season details and countdown
- **⭐ Track Progress:** `/season_progress` - Your level, XP, and rank
- **🎁 Browse Rewards:** `/season_rewards` - See what you can earn
- **🏆 Leaderboard:** `/season_leaderboard` - Top 25 players
- **💎 Claim Rewards:** `/claim_reward <id>` - Get your earned rewards

**How It Works:**
- Earn XP by opening packs, winning battles, and trading
- Level up to unlock exclusive cards, gold, and cosmetics
- Compete for top ranks: Bronze → Silver → Gold → Platinum → Diamond
- Season-exclusive cards are available ONLY during their season!

### **Battle System**
- **4 Wager Tiers**: Casual (50g), Standard (100g), High Stakes (250g), Extreme (500g)
- **Critical Hits**: Random chance for bonus damage
- **Accept Battles**: `/battle_accept <match_id>`
- **Power-based**: Card stats determine winner

### **Pack Creation**
- **Create Pack:** Use Dev Panel (test server) or menu system
- **Browse Packs:** `/packs`
- **YouTube Integration**: Automatic video search and card generation
- **Interactive Selection**: Song selection UI for custom packs

---

## 🎨 **Enhanced Features**

### **Audio Feedback**
Experience premium audio effects during key moments:
- 🌟 **Legendary Pulls** - Epic sound when you get legendary cards
- 💰 **Daily Rewards** - Coin sounds for daily claims
- 🎴 **Card Pickups** - Whoosh sounds when claiming drops
- 📦 **Purchases** - Success sounds for pack purchases

### **Visual Celebrations**
- Animated GIFs for legendary pulls and milestones
- Emoji fireworks for special achievements
- Rarity-specific effects and colors
- Full-size card images in reveals

---

## 🛠️ **For Server Owners**

### **Admin Commands**
- **📈 Server Analytics:** `/server_analytics`
- **ℹ️ Server Info:** `/server_info`
- **🔄 Sync Commands:** `/sync_commands`
- **📋 Setup User Hub:** `/setup_user_hub`
- **💎 Premium:** `/premium_subscribe`

### **Setup Requirements**
1. **Add Bot to Server**
2. **Run `/setup_user_hub`** in your main channel
3. **Set Up Channel Permissions**
4. **Players start playing!**

---

## 📋 **Complete Command List**

### **🎮 Gameplay Commands**
- `/battle` - Challenge players with wager system
- `/battle_accept` - Accept battle challenges  
- `/deck` - View your battle deck
- `/stats` - View your battle statistics
- `/leaderboard` - View global rankings
- `/daily` - Claim daily rewards
- `/balance` - Check gold and economy

### **🎯 Season Commands (NEW!)**
- `/season_info` - View current season details
- `/season_progress` - Check your level and XP
- `/season_rewards` - Browse available rewards
- `/season_leaderboard` - See top players
- `/claim_reward` - Claim your earned rewards

### **📦 Pack Commands**
- `/create_pack` - Create custom artist packs (dev server)
- `/open_pack` - Open packs and receive cards
- `/packs` - Browse available creator packs

### **💎 Premium/Admin Commands**
- `/premium_subscribe` - Upgrade to premium
- `/server_info` - View server status
- `/server_analytics` - View usage analytics
- `/setup_user_hub` - Post persistent User Hub
- `/sync_commands` - Force sync slash commands

---

## 📚 Documentation

- **[Player Guide](PLAYER_GUIDE.md)** - Complete guide for players (seasons, commands, tips)
- **[Game Documentation](GAME_DOCUMENTATION.md)** - Technical details and architecture
- **[Pack Creation Guide](PACK_CREATION_COMPLETE.md)** - How pack creation works
- **[Bulk Pack Creation](BULK_PACK_CREATION_GUIDE.md)** - Create multiple packs at once

---

## 🏗️ **Technical Architecture**

### **Battle System v2.0**
- **BattleEngine**: Core battle logic with critical hits
- **BattleManager**: Match state management
- **4-Tier Wagers**: Casual → Standard → High Stakes → Extreme
- **PlayerState**: Individual player battle state
- **MatchState**: Complete battle match tracking

### **Database Schema**
```sql
-- Core Tables
creator_packs          - Pack information and cards_data
users                  - User profiles and inventory
user_inventory         - Gold, XP, and assets
battle_matches         - Battle history and results
cards                  - Master card catalog
card_collections       - User card ownership
pack_purchases         - Transaction tracking
audit_logs             - Action logging
```

### **Key Integrations**
- **YouTube API**: Video search and thumbnail extraction
- **TheAudioDB**: Artist images and metadata
- **Last.fm**: Music data and statistics
- **Spotify**: Artist information (fallback)

---

## 🚀 **Deployment**

### **Railway (Production)**
- ✅ **Dockerfile**: Multi-stage build with cache busting
- ✅ **Environment**: All variables configured
- ✅ **Database**: SQLite with automatic backups
- ✅ **Monitoring**: Full logging and error tracking

### **Local Development**
```bash
# Clone and setup
git clone https://github.com/samuraifrenchienft/Music-Legends
cd Music-Legends
pip install -r requirements.txt

# Configure environment
cp .env.txt.example .env.txt
# Edit .env.txt with your tokens

# Run bot
python main.py
```

---

## 💰 **Economy System**

### **Gold Economy**
- **Daily Rewards**: 100-500 gold based on streak
- **Battle Winnings**: Wager-based rewards
- **Pack Creation**: Free (creator-driven)

### **Battle Rewards**
| Wager Tier | Cost | Winner Gold | Winner XP | Loser Gold | Loser XP |
|------------|------|-------------|-----------|------------|---------|
| Casual     | 50g  | 75g         | 10 XP     | 25g        | 5 XP    |
| Standard   | 100g | 150g        | 20 XP     | 50g        | 10 XP   |
| High Stakes| 250g | 375g        | 50 XP     | 125g       | 25 XP   |
| Extreme    | 500g | 750g        | 100 XP    | 250g       | 50 XP   |

---

## � **Recent Major Updates**

### **✅ Completed (v2.0)**
- **Battle System Overhaul**: Complete rewrite with BattleManager
- **JSON Import Fixes**: Resolved all import conflicts across 8 files
- **Railway Deployment**: Production-ready Docker setup
- **Image Validation**: Fallback system for broken thumbnails
- **Command Conflicts**: Resolved duplicate command registrations

### **🔄 In Progress**
- **Trading System**: Card marketplace functionality
- **Tournament Mode**: Multi-player battles
- **Mobile App**: React Native companion

---

## 🔧 **Configuration Files**

### **Environment Variables (.env.txt)**
```env
# Discord Configuration
BOT_TOKEN=your_discord_bot_token
DISCORD_APPLICATION_ID=your_application_id
TEST_SERVER_ID=your_test_server_id

# API Keys
YOUTUBE_API_KEY=your_youtube_api_key
LASTFM_API_KEY=your_lastfm_api_key
AUDIODB_API_KEY=1

# Developer
DEV_USER_IDS=your_discord_user_id
```

### **Deployment Files**
- `railway.toml` - Railway configuration
- `Dockerfile` - Container build
- `nixpacks.toml` - Alternative build system
- `requirements.txt` - Python dependencies

---

## � **Troubleshooting**

### **Common Issues**
- **JSON Errors**: ✅ All resolved (14 local imports fixed)
- **Command Conflicts**: ✅ Fixed duplicate registrations
- **Railway Deployment**: ✅ Cache busting implemented
- **Database Issues**: ✅ Fallback to in-memory DB

### **Debug Commands**
- Bot logs show full startup sequence
- Railway build logs available in dashboard
- JSON errors completely eliminated

---

## 🤝 **Contributing**

1. **Fork** the repository
2. **Create** feature branch (`git checkout -b feature/AmazingFeature`)
3. **Commit** changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to branch (`git push origin feature/AmazingFeature`)
5. **Open** Pull Request

### **Development Guidelines**
- Follow PEP 8 style
- Add proper JSON imports at file top
- Test battle system thoroughly
- Update documentation

---

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🆘 **Support**

- **GitHub Issues**: [Report bugs](https://github.com/samuraifrenchienft/Music-Legends/issues)
- **Documentation**: Check this README and code comments
- **Status**: Bot is production-ready and actively maintained

---

## 🎯 **Live Stats**

- **Bot ID**: 1462769520660709408
- **Commands**: 25+ available
- **Servers**: Running on 1+ servers
- **Battle System**: Fully functional
- **Pack Creation**: Working with YouTube integration
- **Status**: ✅ PRODUCTION READY

---

**🔥 Built with ❤️ for the Discord music community**

**Last Updated**: January 2026  
**Version**: 2.0 (Battle System Complete)
