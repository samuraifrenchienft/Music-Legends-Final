# 🔧 Discord Bot Permission Fix

## ❌ Current Error: 403 Forbidden (Missing Access)

This error occurs when your bot doesn't have the required permissions to sync slash commands with your Discord server.

## 🔑 Required Bot Permissions

Your bot needs these permissions:
- **applications.commands** scope (for slash commands)
- **bot** scope
- **Administrator** permission (or at minimum: Send Messages, Read Messages, Use Slash Commands)

## 🚀 How to Fix

### Step 1: Generate New Invite Link

1. Go to: https://discord.com/developers/applications
2. Select your application (ID: 1462769520660709408)
3. Go to **OAuth2** → **URL Generator**
4. Select these **SCOPES**:
   - ✅ `bot`
   - ✅ `applications.commands`
5. Select these **BOT PERMISSIONS**:
   - ✅ Administrator (recommended)
   - OR at minimum:
     - ✅ Send Messages
     - ✅ Read Messages/View Channels
     - ✅ Use Slash Commands
     - ✅ Embed Links
     - ✅ Attach Files
     - ✅ Add Reactions
     - ✅ Use External Emojis
6. Copy the generated URL at the bottom

### Step 2: Re-invite Your Bot

1. **Kick the bot** from your Discord server first (if already added)
2. Use the new invite URL to add the bot back
3. Make sure to authorize all requested permissions

### Step 3: Verify Bot Permissions

After re-inviting:
1. Go to your Discord server
2. Right-click on your bot → View Profile
3. Check that it has the correct roles and permissions

## ✅ After Fixing

Once you've re-invited the bot with correct permissions:
1. Redeploy your bot on Railway
2. The bot should now successfully sync slash commands
3. You should see: `✅ Synced X commands to guild`

## 🔍 Common Issues

**Bot still shows 403 error:**
- Make sure you used the NEW invite link with `applications.commands` scope
- Verify the bot has Administrator role or all required permissions
- Check that TEST_SERVER_ID in your .env matches your Discord server ID

**Bot joins but commands don't appear:**
- Wait 5-10 minutes for Discord to update
- Try `/` in your server to see if commands appear
- Restart Discord app (Ctrl+R)

## 📞 Still Having Issues?

If the bot still shows 403 errors after re-inviting:
1. Double-check your BOT_TOKEN is correct
2. Verify APPLICATION_ID matches your bot's application ID
3. Ensure TEST_SERVER_ID is your actual Discord server ID
