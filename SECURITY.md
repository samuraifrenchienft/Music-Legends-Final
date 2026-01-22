# 🔐 SECURITY SETUP - Environment Variables

## **⚠️ IMPORTANT: Keep Your Secrets Safe!**

Your Discord bot token is **extremely sensitive** - anyone with it can control your bot!

### **✅ Secure Setup (Recommended):**

1. **Create your `.env` file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your real credentials:**
   ```env
   BOT_TOKEN=your_actual_discord_bot_token_here
   APPLICATION_ID=your_actual_application_id_here  
   TEST_SERVER_ID=your_actual_test_server_id_here
   ```

3. **`.env` is automatically ignored by Git** (see `.gitignore`)

### **🚫 NEVER DO THIS:**
- ❌ Commit tokens to GitHub
- ❌ Share `config.json` with real tokens
- ❌ Post tokens in Discord/public channels
- ❌ Include tokens in screenshots

### **🔒 Files Created:**
- **`.env.example`** - Template for setup (safe to share)
- **`.gitignore`** - Prevents secrets from being committed
- **Updated `main.py`** - Uses environment variables instead of config.json

### **📍 Where to Get Your Credentials:**
1. **Bot Token**: Discord Developer Portal → Bot → Token (Reset/View)
2. **Application ID**: Discord Developer Portal → General Information → Application ID
3. **Test Server ID**: Right-click your server in Discord → Copy Server ID

### **🛡️ Security Benefits:**
- ✅ Secrets never committed to version control
- ✅ Easy to share code without exposing credentials
- ✅ Different configs for development/production
- ✅ Industry standard security practice

### **📋 Updated Files:**
- `main.py` - Now uses `.env` instead of `config.json`
- `cogs/card_game.py` - Updated for environment variables
- `cogs/example.py` - Updated for environment variables
- `requirements.txt` - Added `python-dotenv` dependency

**Your bot is now secure and ready for safe development!** 🔐
