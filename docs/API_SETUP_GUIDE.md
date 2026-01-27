# Music API Setup Guide - Last.fm & TheAudioDB

This guide will help you set up **Last.fm** and **TheAudioDB** APIs as alternatives to Spotify for Music Legends bot.

---

## Why Last.fm & TheAudioDB?

| Feature | Last.fm | TheAudioDB | Spotify |
|---------|---------|------------|---------|
| **Free API** | ✅ Yes | ✅ Yes (donations) | ❌ Complex OAuth |
| **Artist Info** | ✅ Excellent | ✅ Excellent | ✅ Good |
| **Album Art** | ✅ Yes | ✅ High Quality | ✅ Yes |
| **Track Search** | ✅ Yes | ⚠️ Limited | ✅ Excellent |
| **Popularity Stats** | ✅ Play counts | ⚠️ Limited | ✅ Followers |
| **Setup Difficulty** | 🟢 Easy | 🟢 Very Easy | 🔴 Hard |

**Recommendation:** Use **Last.fm as primary** with **TheAudioDB as fallback** for album art.

---

## 1. Last.fm API Setup (Primary)

### Step 1: Create Last.fm Account
1. Go to https://www.last.fm/join
2. Sign up for a free account
3. Verify your email

### Step 2: Get API Key
1. Go to https://www.last.fm/api/account/create
2. Fill out the form:
   - **Application Name:** Music Legends Bot
   - **Application Description:** Discord bot for music card battles
   - **Application Homepage:** Your Discord server invite or GitHub repo
   - **Callback URL:** Leave blank (not needed for bot)
3. Click **Submit**
4. You'll receive:
   - **API Key** (32 characters)
   - **Shared Secret** (32 characters)

### Step 3: Add to .env.txt
```env
# Last.fm API
LASTFM_API_KEY=your_api_key_here
LASTFM_SHARED_SECRET=your_shared_secret_here
```

### Last.fm API Endpoints We'll Use:
```
artist.getInfo       - Get artist details, images, bio
artist.search        - Search for artists
artist.getTopTracks  - Get artist's top songs
track.search         - Search for tracks
track.getInfo        - Get track details
```

### Rate Limits:
- **Free Tier:** Unlimited requests
- **No authentication required** for read-only operations
- Very generous rate limits

---

## 2. TheAudioDB API Setup (Fallback for Images)

### Step 1: Get API Key
1. Go to https://www.theaudiodb.com/api_guide.php
2. **Free Tier:** Use API key `1` (public test key)
3. **Patreon Tier ($3/month):** Get your own key at https://www.patreon.com/thedatadb
   - Faster responses
   - Higher quality images
   - Priority support

### Step 2: Add to .env.txt
```env
# TheAudioDB API
AUDIODB_API_KEY=1
# Or if you support on Patreon:
# AUDIODB_API_KEY=your_patreon_key_here
```

### TheAudioDB API Endpoints:
```
search.php?s=artist_name     - Search for artist
artist.php?i=artist_id       - Get artist details + images
track.php?m=track_id         - Get track details
mvid.php?i=artist_id         - Get music videos
```

### Rate Limits:
- **Free Tier (Key=1):** 100 requests/day per IP
- **Patreon Tier:** 1000+ requests/day

---

## 3. API Comparison Chart

### Artist Search Quality:
```
Query: "Drake"

Last.fm Response:
✅ Name: Drake
✅ Play count: 5.2 billion
✅ Listeners: 4.8 million
✅ Images: Small, Medium, Large, XLarge
✅ Bio: Full biography
✅ Similar artists
✅ Top tags: hip hop, rap, canadian

TheAudioDB Response:
✅ Name: Drake
✅ High-res images (1000x1000)
✅ Logo images
✅ Banner images
✅ Biography
✅ Genre: Hip Hop
✅ Country: Canada
⚠️ No play counts

YouTube Response (current):
✅ Video thumbnails
✅ View counts
⚠️ No artist metadata
⚠️ Inconsistent naming
```

---

## 4. Implementation Strategy

### Waterfall Approach (Best Results):
```
1. Last.fm - Primary artist/track search
   ↓ (if no results)
2. TheAudioDB - Fallback for artist info
   ↓ (if no results)
3. YouTube - Final fallback for videos
```

### Hybrid Approach (Best Quality):
```
1. Last.fm - Get artist info + track list
2. TheAudioDB - Get high-res images
3. YouTube - Get video links for cards
```

---

## 5. Code Examples

### Last.fm Artist Search:
```python
import requests

LASTFM_API_KEY = "your_key_here"
BASE_URL = "http://ws.audioscrobbler.com/2.0/"

def search_artist(artist_name):
    params = {
        'method': 'artist.search',
        'artist': artist_name,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
        'limit': 10
    }
    
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    
    if 'results' in data and 'artistmatches' in data['results']:
        artists = data['results']['artistmatches']['artist']
        return artists
    return []

# Usage:
artists = search_artist("Drake")
for artist in artists:
    print(f"{artist['name']} - {artist['listeners']} listeners")
```

### Last.fm Get Top Tracks:
```python
def get_top_tracks(artist_name, limit=10):
    params = {
        'method': 'artist.getTopTracks',
        'artist': artist_name,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
        'limit': limit
    }
    
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    
    if 'toptracks' in data and 'track' in data['toptracks']:
        return data['toptracks']['track']
    return []

# Usage:
tracks = get_top_tracks("Drake", limit=5)
for track in tracks:
    print(f"{track['name']} - {track['playcount']} plays")
```

### TheAudioDB Artist Search:
```python
AUDIODB_API_KEY = "1"  # or your Patreon key
AUDIODB_BASE = "https://www.theaudiodb.com/api/v1/json"

def search_artist_audiodb(artist_name):
    url = f"{AUDIODB_BASE}/{AUDIODB_API_KEY}/search.php"
    params = {'s': artist_name}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data and 'artists' in data and data['artists']:
        return data['artists'][0]  # First match
    return None

# Usage:
artist = search_artist_audiodb("Drake")
if artist:
    print(f"Name: {artist['strArtist']}")
    print(f"Image: {artist['strArtistThumb']}")
    print(f"Genre: {artist['strGenre']}")
```

---

## 6. Recommended .env.txt Setup

```env
# ============================================
# MUSIC API KEYS
# ============================================

# Last.fm (Primary) - https://www.last.fm/api/account/create
LASTFM_API_KEY=your_lastfm_api_key_here
LASTFM_SHARED_SECRET=your_lastfm_shared_secret_here

# TheAudioDB (Images) - https://www.theaudiodb.com/api_guide.php
AUDIODB_API_KEY=1
# Upgrade to Patreon key for better rate limits

# YouTube (Videos) - Already configured
YOUTUBE_API_KEY=your_youtube_key_here

# ============================================
# API PRIORITY ORDER
# ============================================
# 1. Last.fm - Artist info, track search, popularity
# 2. TheAudioDB - High-res images, album art
# 3. YouTube - Music videos, thumbnails
```

---

## 7. Testing Your Setup

### Test Last.fm:
```bash
# Replace YOUR_KEY with your actual API key
curl "http://ws.audioscrobbler.com/2.0/?method=artist.search&artist=Drake&api_key=YOUR_KEY&format=json"
```

Expected response:
```json
{
  "results": {
    "artistmatches": {
      "artist": [
        {
          "name": "Drake",
          "listeners": "4800000",
          "url": "https://www.last.fm/music/Drake",
          "image": [...]
        }
      ]
    }
  }
}
```

### Test TheAudioDB:
```bash
curl "https://www.theaudiodb.com/api/v1/json/1/search.php?s=Drake"
```

Expected response:
```json
{
  "artists": [
    {
      "strArtist": "Drake",
      "strArtistThumb": "https://www.theaudiodb.com/images/media/artist/thumb/...",
      "strGenre": "Hip Hop",
      "strBiographyEN": "..."
    }
  ]
}
```

---

## 8. Next Steps

After setting up your API keys:

1. ✅ Add keys to `.env.txt`
2. ✅ Test API endpoints with curl
3. ⏭️ I'll create `lastfm_integration.py`
4. ⏭️ I'll create `audiodb_integration.py`
5. ⏭️ I'll update pack creation to use new APIs
6. ⏭️ I'll add fallback logic (Last.fm → AudioDB → YouTube)

---

## 9. Cost Comparison

| Service | Free Tier | Paid Tier | Best For |
|---------|-----------|-----------|----------|
| **Last.fm** | ✅ Unlimited | N/A | Artist info, track search |
| **TheAudioDB** | 100 req/day | $3/mo (1000+ req/day) | High-res images |
| **YouTube** | 10,000 units/day | $0.01 per 100 units | Music videos |
| **Spotify** | ❌ Complex OAuth | Free but hard setup | Track metadata |

**Recommendation:** Start with free Last.fm + free TheAudioDB (key=1). Upgrade TheAudioDB to Patreon if you need more requests.

---

## 10. Troubleshooting

### Last.fm "Invalid API Key" Error:
- Check your API key is correct in `.env.txt`
- Make sure there are no spaces before/after the key
- Verify at https://www.last.fm/api/accounts

### TheAudioDB No Results:
- Try different artist name spellings
- Use Last.fm as primary, AudioDB as fallback
- Free tier (key=1) has limited data

### Rate Limit Errors:
- Last.fm: Very rare, contact support if happens
- TheAudioDB: Upgrade to Patreon tier ($3/mo)
- YouTube: Already handled in existing code

---

## Ready to Implement?

Once you have your API keys, let me know and I'll:
1. Create the integration modules
2. Update pack creation flow
3. Add fallback logic
4. Test everything

**Get your Last.fm API key here:** https://www.last.fm/api/account/create
