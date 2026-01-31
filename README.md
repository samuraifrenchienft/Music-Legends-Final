# 🎵 Music Legends — Discord Card Game

Music Legends is a Discord card game where players collect artist cards, create custom packs, and battle friends with a comprehensive battle system.

## 🚀 **Current Status: PRODUCTION READY** ✅

- ✅ **Battle System**: Complete 4-tier wager system with critical hits
- ✅ **Pack Creation**: Interactive YouTube/Spotify integration  
- ✅ **Database**: SQLite with full schema support
- ✅ **Railway Deployment**: Docker containerized and running
- ✅ **JSON Issues**: All resolved and working

---

## 🎮 **For Players (How to Play)**

### **Core Commands**
- **🎴 Open a pack:** `/open_pack <pack_id>`
- **👀 View your cards:** `/deck` (shows battle deck)
- **⚔️ Battle someone:** `/battle @user <wager>`
- **📊 Check stats:** `/stats`
- **🏆 Leaderboard:** `/leaderboard`
- **💰 Check balance:** `/balance`
- **🎁 Daily reward:** `/daily`

### **Battle System**
- **4 Wager Tiers**: Casual (50g), Standard (100g), High Stakes (250g), Extreme (500g)
- **Critical Hits**: Random chance for bonus damage
- **Accept Battles**: `/battle_accept <match_id>`
- **Power-based**: Card stats determine winner

### **Pack Creation**
- **Create Pack:** `/create_pack <name> <artist>`
- **Browse Packs:** `/packs`
- **YouTube Integration**: Automatic video search and card generation
- **Interactive Selection**: Song selection UI for custom packs

---

## 🛠️ **For Server Owners**

### **Admin Commands**
- **📈 Server Analytics:** `/server_analytics`
- **ℹ️ Server Info:** `/server_info`
- **🗑️ Delete Pack:** `/delete_pack <pack_id>` (DEV ONLY)
- **💎 Premium:** `/premium_subscribe`

### **Setup Requirements**
1. **Add Bot to Server**
2. **Set Up Channel Permissions**
3. **Configure Economy** (optional)
4. **Enable Battle Commands**

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

### **📦 Pack Commands**
- `/create_pack` - Create custom artist packs
- `/open_pack` - Open packs and receive cards
- `/packs` - Browse available creator packs

### **💎 Premium/Admin Commands**
- `/premium_subscribe` - Upgrade to premium
- `/server_info` - View server status
- `/server_analytics` - View usage analytics
- `/delete_pack` - Delete packs (DEV only)

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
