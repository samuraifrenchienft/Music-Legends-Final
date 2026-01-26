# 🔧 REDIS CONFIGURATION GUIDE

## 📍 TWO DIFFERENT ENVIRONMENTS

You have **TWO** separate Redis configurations:
1. **Local Development** (your laptop)
2. **Railway Production** (cloud deployment)

---

## 🏠 LOCAL DEVELOPMENT

### What You Need to Update:

**File: `.env.txt`**

Change this line:
```
REDIS_URL=redis://localhost:6381
```

To:
```
REDIS_URL=redis://localhost:6379
```

### Why?
- Your local Redis server runs on port **6379** (standard port)
- We fixed `redis.conf` and `docker-compose.yml` to use port 6379
- Your `.env.txt` still has the old port 6381

### How to Test Local Redis:
```bash
# Option 1: Start Redis with Docker
docker-compose up -d redis

# Option 2: Start Redis directly (if installed)
redis-server

# Test connection
python test_redis_connection.py
```

---

## ☁️ RAILWAY PRODUCTION

### What Railway Needs:

**Railway automatically provides Redis** when you add a Redis service to your project.

Railway will set the `REDIS_URL` environment variable automatically to something like:
```
redis://default:password@redis.railway.internal:6379
```

### How to Configure on Railway:

#### Option 1: Use Railway's Redis Service (RECOMMENDED)
1. Go to your Railway project dashboard
2. Click **"+ New"** → **"Database"** → **"Add Redis"**
3. Railway automatically creates `REDIS_URL` environment variable
4. Your bot will use this automatically - **NO MANUAL CONFIG NEEDED**

#### Option 2: Use External Redis (e.g., Upstash, Redis Cloud)
1. Get your Redis URL from your provider (e.g., `redis://user:pass@host:port`)
2. Go to Railway project → **Variables** tab
3. Add environment variable:
   - **Key**: `REDIS_URL`
   - **Value**: Your external Redis URL

### Railway Environment Variables You Need:

```
BOT_TOKEN=your_discord_bot_token
DISCORD_APPLICATION_ID=your_application_id
REDIS_URL=<automatically set by Railway Redis OR your external URL>
REDIS_PASSWORD=<optional, if using password>
YOUTUBE_API_KEY=your_youtube_api_key
DEV_USER_IDS=your_discord_user_id
```

**Note**: Railway Redis service sets `REDIS_URL` automatically. You only need to manually set it if using an external Redis provider.

---

## 🔍 SUMMARY

| Environment | Redis URL | How to Set |
|------------|-----------|------------|
| **Local** | `redis://localhost:6379` | Update `.env.txt` manually |
| **Railway** | Auto-generated or external | Railway sets it OR add manually in Variables |

### Local Development:
- ✅ Update `.env.txt` to use port 6379
- ✅ Start Redis locally (Docker or redis-server)
- ✅ Test with `python test_redis_connection.py`

### Railway Production:
- ✅ Add Redis service in Railway (automatic config)
- ✅ OR set `REDIS_URL` manually if using external Redis
- ✅ Set other environment variables (BOT_TOKEN, etc.)
- ✅ Deploy and verify

---

## 🚨 IMPORTANT

**DO NOT** commit `.env.txt` to GitHub with real credentials!

The `.env.txt` file is for **local development only**. Railway uses its own environment variables system.

---

## ✅ NEXT STEPS

1. **For Local Testing:**
   - Update `.env.txt` REDIS_URL to port 6379
   - Run `python test_redis_connection.py`

2. **For Railway Deployment:**
   - Add Redis service in Railway dashboard
   - Set environment variables in Railway
   - Deploy your bot

Your local and Railway environments are **completely separate** - changes to `.env.txt` only affect local development.
