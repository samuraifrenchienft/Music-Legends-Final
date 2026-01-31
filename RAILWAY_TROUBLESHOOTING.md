# Railway Deployment Troubleshooting Guide

## Issue: Changes Not Taking Effect on Railway

### Common Causes and Solutions:

#### 1. **Cache Issues**
**Problem:** Railway is using cached layers instead of rebuilding with your changes.

**Solution:**
- Updated cache busting timestamp in `Dockerfile` (line 5)
- Updated cache busting comment in `railway.toml` (line 5)
- Force redeploy by making a small change to these files

#### 2. **Conflicting Start Commands**
**Problem:** Different configuration files have different start commands.

**Fixed:**
- `railway.toml`: `python run_bot.py` ✅
- `nixpacks.toml`: `python run_bot.py` ✅ (was `python main.py`)
- `Dockerfile`: `CMD ["python", "run_bot.py"]` ✅

#### 3. **Environment Variables Not Set**
**Problem:** Railway environment variables not configured.

**Solution:**
1. Go to your Railway project
2. Click on your service
3. Go to "Variables" tab
4. Add these required variables:
   ```
   BOT_TOKEN=your_discord_bot_token
   DISCORD_APPLICATION_ID=your_application_id
   YOUTUBE_API_KEY=your_youtube_api_key
   LASTFM_API_KEY=your_lastfm_api_key
   AUDIODB_API_KEY=1
   DEV_USER_IDS=your_discord_user_id
   ```

#### 4. **Build Process Issues**
**Problem:** Build fails but Railway doesn't show the error.

**Solution:**
- Check the "Build Logs" tab in Railway
- Look for Python import errors
- Ensure all dependencies are in `requirements.txt`

### Steps to Force Railway Redeploy:

1. **Push Changes to Git:**
   ```bash
   git add .
   git commit -m "Fix Railway deployment - update cache bust and start commands"
   git push origin main
   ```

2. **Manual Redeploy (if needed):**
   - Go to Railway dashboard
   - Click your service
   - Click "Settings" tab
   - Click "Redeploy" button

3. **Check Build Logs:**
   - Go to "Build Logs" tab
   - Look for any errors during build
   - Ensure all Python packages install successfully

4. **Check Runtime Logs:**
   - Go to "Logs" tab
   - Look for bot startup messages
   - Check for any runtime errors

### Verification Steps:

1. **Build Success:** Build should complete without errors
2. **Bot Starts:** Look for "🐳 DOCKER DEBUG" messages in logs
3. **Bot Online:** Bot should appear online in Discord
4. **Commands Work:** Test `/battle` or other commands

### Common Error Messages:

#### "BOT_TOKEN is required but not set"
- **Cause:** Environment variable not set in Railway
- **Fix:** Add BOT_TOKEN in Railway Variables tab

#### "ModuleNotFoundError: No module named 'discord'"
- **Cause:** Dependencies not installed
- **Fix:** Check requirements.txt and build logs

#### "CommandAlreadyRegistered"
- **Cause:** Multiple cogs registering same command
- **Fix:** Check which cogs are loading (this is expected in current setup)

### Current Configuration Status:
✅ Dockerfile cache bust updated
✅ Railway.toml start command consistent  
✅ Nixpacks.toml start command fixed
✅ All files use `run_bot.py` as entry point
✅ Environment variables documented

### Next Steps:
1. Push changes to git
2. Check Railway build logs
3. Verify bot starts successfully
4. Test commands in Discord

If issues persist, check the specific error messages in Railway build/runtime logs.
