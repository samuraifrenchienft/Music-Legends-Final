# 🔧 RAILWAY/DOCKER DEPLOYMENT TROUBLESHOOTING

**Issue:** Code changes not reflecting in deployed bot  
**Root Cause:** Docker caching - old image was being used  
**Solution:** Updated cache busting flags to force rebuild

---

## ✅ CHANGES MADE

### 1. Updated Dockerfile (Line 5)
**Before:**
```
ARG CACHE_BUST=2026-02-03-02-25-00-SIMPLIFIED-MODAL
```

**After:**
```
ARG CACHE_BUST=2026-02-03-CARD-GAME-CREATE-PACK-FIX
```

This forces Docker to invalidate its cache and rebuild the entire image with new code.

### 2. Updated railway.toml (Line 5)
**Before:**
```
# Force rebuild - 2026-02-03-02-25-00-SIMPLIFIED-MODAL
```

**After:**
```
# Force rebuild - 2026-02-03-CARD-GAME-CREATE-PACK-FIX
```

This tells Railway to trigger a new deployment.

---

## 📋 WHY THIS WORKS

Docker caches every layer of the Dockerfile to speed up builds. The `ARG CACHE_BUST` argument is a trick to force Docker to rebuild:

1. When you change the `CACHE_BUST` value
2. Docker sees the argument changed
3. It invalidates ALL cached layers below that point
4. Forces a complete rebuild with fresh code

---

## 🚀 WHAT TO DO NOW

### Step 1: Push Changes to Git
```bash
git add .
git commit -m "Force Docker rebuild - deploy card_game.py pack creation fix"
git push
```

### Step 2: Railway Auto-Deploy
Once you push to Git:
1. Railway detects the push
2. Sees the Dockerfile change
3. Builds a NEW Docker image (with cache bust)
4. Deploys automatically

### Step 3: Verify Deployment
In Railway dashboard:
1. Go to your project
2. Watch the "Deployments" tab
3. You should see a new build in progress
4. Status changes: `Building` → `Running`
5. Your bot will restart with new code

---

## ⏱️ TYPICAL DEPLOYMENT TIME

- Build time: 2-5 minutes (first build longer due to no cache)
- Deploy time: 1-2 minutes
- Total: 3-7 minutes

---

## 🔍 HOW TO CHECK IF DEPLOYMENT SUCCEEDED

### In Railway Dashboard:
- ✅ Deployment shows "Success"
- ✅ Bot service shows "Running" (green)
- ✅ No error logs in "Logs" tab

### In Discord:
- ✅ Bot goes offline briefly then comes back
- ✅ `/create_pack` now only asks for artist name
- ✅ No "pack_name" parameter visible

---

## ❌ IF DEPLOYMENT FAILS

### Check These Things:

1. **Git Push Successful?**
   - Verify in your GitHub repo that files are updated
   - Check timestamps match your recent changes

2. **Railway Sees Changes?**
   - Check Railway "Deployments" tab
   - Should show new build triggered

3. **Build Errors?**
   - Click on failed deployment
   - Check "Build Logs" tab for specific errors
   - Look for Python syntax errors

4. **Bot Won't Connect?**
   - Check environment variables in Railway
   - Verify BOT_TOKEN is set correctly
   - Check "Runtime Logs" for connection errors

---

## 🆘 TROUBLESHOOTING STEPS

### If bot doesn't update after 10 minutes:

1. **Force a manual deploy in Railway:**
   - Go to Railway Dashboard
   - Click your service
   - Click "Deploy" button
   - Select "Latest" commit
   - Click "Deploy"

2. **Or push an empty commit:**
   ```bash
   git commit --allow-empty -m "Force redeploy"
   git push
   ```

3. **Or rebuild Docker locally:**
   ```bash
   docker build --no-cache -t discord-bot .
   docker run discord-bot
   ```

---

## 📊 FILES CHANGED FOR DEPLOYMENT

- ✅ `cogs/card_game.py` - Removed pack_name parameter from /create_pack
- ✅ `cogs/menu_system.py` - Already had single artist_name field
- ✅ `Dockerfile` - Updated CACHE_BUST flag
- ✅ `railway.toml` - Updated rebuild comment

---

## ✅ CODE IS CORRECT

All code changes are correct and in place:
- `/create_pack` only accepts `artist_name` 
- Pack name automatically = artist name
- Both dev panel and commands unified

**Just needed Docker cache busting to deploy!**

