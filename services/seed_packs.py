"""
Seed Pack Loader

Loads genre_seed_packs.json on startup so the marketplace always has
a baseline catalogue of packs.  Packs are idempotent — if a seed pack
already exists in the DB it is skipped, so this is safe to call every boot.

Each genre has 15 artists. For each artist:
- Fetch 5 songs from YouTube API
- Create 1 pack per artist with 5 song cards
- Card rarities per pack: 1 epic, 2 rare, 2 common
- Stats are scaled based on tier (community vs gold)
- Images and metadata from YouTube
Result: 15 packs per genre
"""

import json
import hashlib
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List

def _get_db_connection():
    """Get database connection - PostgreSQL if DATABASE_URL set, else SQLite."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # PostgreSQL on Railway
        import psycopg2
        # Convert Railway format if needed
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(database_url), "postgresql"
    else:
        # Local SQLite
        return sqlite3.connect("music_legends.db"), "sqlite"

# Rarity assignment per card slot (index 0-4 inside each pack)
SLOT_RARITIES = ["epic", "rare", "rare", "common", "common"]

# Stat ranges by rarity
RARITY_STAT_RANGES = {
    "common":    (18, 38),
    "rare":      (32, 55),
    "epic":      (50, 75),
    "legendary": (65, 92),
}

# Genre → emoji for pack display
GENRE_EMOJI = {
    "EDM Bangers":           "🎧",
    "Rock Classics":         "🎸",
    "R&B Soul Pack":         "🎷",
    "Pop Hits 2024":         "🎤",
    "Hip Hop Legends":       "🎙️",
}


def _deterministic_stat(artist_name: str, stat_name: str, lo: int, hi: int) -> int:
    """Generate a repeatable stat from the artist+stat name so values
    don't change across restarts."""
    seed = hashlib.md5(f"{artist_name}:{stat_name}".encode()).hexdigest()
    # Use first 8 hex chars → 0..4294967295, then scale to range
    val = int(seed[:8], 16)
    return lo + (val % (hi - lo + 1))


def _deterministic_uuid(genre: str, vol: int, artist: str) -> str:
    """Stable UUID so the same seed data always produces the same card_id."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"musiclegends:{genre}:vol{vol}:{artist}"))


def _rarity_to_tier(rarity: str) -> str:
    """Map rarity to tier"""
    return {
        "common": "community",
        "rare": "gold",
        "epic": "platinum",
        "legendary": "legendary",
        "mythic": "legendary",
    }.get(rarity.lower(), "community")




def _seed_pack_id(genre: str, vol: int) -> str:
    """Stable pack_id so we can detect if a seed pack already exists."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"musiclegends:pack:{genre}:vol{vol}"))


def load_seed_data() -> Dict[str, List[List[str]]]:
    """Load the genre seed JSON file."""
    seed_path = Path(__file__).resolve().parent.parent / "data" / "genre_seed_packs.json"
    if not seed_path.exists():
        print(f"⚠️  Seed file not found: {seed_path}")
        return {}
    with open(seed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_packs_into_db(db_path: str = "music_legends.db", force_reseed: bool = False) -> Dict[str, int]:
    """Insert seed packs into the database. Skips packs that already exist.

    Args:
        db_path: Path to SQLite database (ignored if DATABASE_URL is set)
        force_reseed: If True, delete existing seed packs and re-insert all

    Returns dict with counts: {"inserted": N, "skipped": N}
    """
    # Check for force reseed environment variable
    if os.getenv("FORCE_RESEED_PACKS") == "1":
        force_reseed = True
        print("🔄 [SEED_PACKS] FORCE_RESEED_PACKS=1 detected, will delete and re-insert all seed packs")

    genre_data = load_seed_data()
    if not genre_data:
        print("⚠️ [SEED_PACKS] No genre data loaded from JSON file")
        return {"inserted": 0, "skipped": 0, "error": "no_data"}

    inserted = 0
    skipped = 0

    try:
        conn, db_type = _get_db_connection()
        print(f"✅ [SEED_PACKS] Connected to {db_type} database")
    except Exception as e:
        print(f"❌ [SEED_PACKS] Database connection failed: {e}")
        return {"inserted": 0, "skipped": 0, "error": str(e)}

    try:
        cursor = conn.cursor()
        # PostgreSQL uses %s placeholders, SQLite uses ?
        ph = "%s" if db_type == "postgresql" else "?"

        # Force reseed: delete all existing seed packs first
        if force_reseed:
            print("🗑️ [SEED_PACKS] Deleting existing seed packs (stripe_payment_id = 'SEED_PACK')...")
            cursor.execute("DELETE FROM creator_packs WHERE stripe_payment_id = 'SEED_PACK'")
            deleted_count = cursor.rowcount
            print(f"🗑️ [SEED_PACKS] Deleted {deleted_count} existing seed packs")
            conn.commit()

        # Ensure creator_packs table exists with required columns
        if db_type == "postgresql":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_packs (
                    pack_id TEXT PRIMARY KEY,
                    creator_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    pack_type TEXT DEFAULT 'creator',
                    pack_size INTEGER DEFAULT 10,
                    status TEXT DEFAULT 'DRAFT',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP,
                    stripe_payment_id TEXT,
                    price_cents INTEGER DEFAULT 500,
                    total_purchases INTEGER DEFAULT 0,
                    cards_data TEXT
                )
            """)
            # Ensure cards table exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL DEFAULT 'artist',
                    name TEXT NOT NULL,
                    artist_name TEXT,
                    title TEXT,
                    image_url TEXT,
                    youtube_url TEXT,
                    rarity TEXT NOT NULL,
                    tier TEXT,
                    variant TEXT DEFAULT 'Classic',
                    era TEXT,
                    impact INTEGER,
                    skill INTEGER,
                    longevity INTEGER,
                    culture INTEGER,
                    hype INTEGER,
                    serial_number TEXT,
                    print_number INTEGER DEFAULT 1,
                    quality TEXT DEFAULT 'standard',
                    effect_type TEXT,
                    effect_value TEXT,
                    pack_id TEXT,
                    created_by_user_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

        # Initialize all 3 APIs: Last.fm (metadata) + TheAudioDB (images) + YouTube (URLs)
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        lastfm_api_key = os.getenv("LASTFM_API_KEY")
        audiodb_api_key = os.getenv("AUDIODB_API_KEY", "1")  # Default public key

        if not youtube_api_key:
            print("⚠️ [SEED_PACKS] No YouTube API key - video URLs will be limited")
        if not lastfm_api_key:
            print("⚠️ [SEED_PACKS] No Last.fm API key - song metadata will be limited")

        # Import all integrations
        try:
            from youtube_integration import YouTubeIntegration
            from lastfm_integration import LastFmIntegration
            from audiodb_integration import AudioDBIntegration
            yt = YouTubeIntegration(youtube_api_key) if youtube_api_key else None
            lastfm = LastFmIntegration() if lastfm_api_key else None
            audiodb = AudioDBIntegration()  # Always available with public key
            print("✅ [SEED_PACKS] API integrations loaded: Last.fm, TheAudioDB, YouTube")
        except Exception as e:
            print(f"⚠️ [SEED_PACKS] API integration unavailable: {e}")
            yt = None
            lastfm = None
            audiodb = None

        for genre, artist_list in genre_data.items():
            emoji = GENRE_EMOJI.get(genre, "🎵")

            # Each artist becomes 1 pack with 5 song cards
            for artist_idx, artist_name in enumerate(artist_list, start=1):
                pack_id = _seed_pack_id(genre, artist_idx)
                pack_name = f"{emoji} {artist_name}"

                # Check if this seed pack already exists
                cursor.execute(
                    f"SELECT 1 FROM creator_packs WHERE pack_id = {ph}",
                    (pack_id,)
                )
                if cursor.fetchone():
                    skipped += 1
                    continue

                # Step 1: Get artist info from TheAudioDB for high-quality images
                artist_info = None
                artist_videos = []
                if audiodb:
                    try:
                        print(f"🎨 Fetching artist info for {artist_name} from TheAudioDB...")
                        artist_results = audiodb.search_artist(artist_name, limit=1)
                        if artist_results:
                            artist_info = artist_results[0]
                            artist_id = artist_info.get('id')
                            # Get music videos for high-quality thumbnails
                            if artist_id:
                                artist_videos = audiodb.get_music_videos(artist_id)
                                print(f"✅ Found {len(artist_videos)} music videos from TheAudioDB")
                    except Exception as e:
                        print(f"⚠️ TheAudioDB fetch failed for {artist_name}: {e}")

                # Step 2: Get top 5 tracks from Last.fm (metadata)
                tracks = []
                if lastfm:
                    try:
                        print(f"🎵 Fetching top tracks for {artist_name} from Last.fm...")
                        tracks = lastfm.get_top_tracks(artist_name, limit=5)
                        print(f"✅ Found {len(tracks)} tracks from Last.fm")
                    except Exception as e:
                        print(f"⚠️ Last.fm fetch failed for {artist_name}: {e}")
                        tracks = []

                # Step 3: Combine data from all APIs
                songs = []
                for idx, track in enumerate(tracks[:5]):
                    song_name = track.get('name', '')
                    song_data = {
                        'title': f"{artist_name} - {song_name}",
                        'song_name': song_name,
                        'playcount': track.get('playcount', 0),
                        'listeners': track.get('listeners', 0),
                        'thumbnail_url': '',
                        'youtube_url': ''
                    }

                    # Try to get matching music video thumbnail from TheAudioDB
                    if artist_videos and idx < len(artist_videos):
                        video = artist_videos[idx]
                        song_data['thumbnail_url'] = video.get('thumbnail', '')

                    # Get YouTube URL for playback
                    if yt and song_name:
                        try:
                            videos = yt.search_music_video(artist_name, song_name, limit=1)
                            if videos:
                                # Use YouTube thumbnail if TheAudioDB didn't provide one
                                if not song_data['thumbnail_url']:
                                    song_data['thumbnail_url'] = videos[0].get('thumbnail_url', '')
                                song_data['youtube_url'] = videos[0].get('youtube_url', '')
                        except Exception as e:
                            print(f"⚠️ YouTube fetch failed for {song_name}: {e}")

                    songs.append(song_data)

                # If we don't have 5 songs, create placeholders
                if len(songs) < 5:
                    print(f"⚠️ Using {5 - len(songs)} placeholder songs for {artist_name}")
                    # Use artist image from TheAudioDB for placeholders if available
                    fallback_image = artist_info.get('thumb', '') if artist_info else ''
                    for i in range(len(songs), 5):
                        songs.append({
                            'title': f"{artist_name} - Song {i+1}",
                            'song_name': f"Song {i+1}",
                            'playcount': 0,
                            'listeners': 0,
                            'thumbnail_url': fallback_image,
                            'youtube_url': ''
                        })

                # Build 5 cards (1 per song) with rarities from SLOT_RARITIES
                cards = []
                for slot_idx, song in enumerate(songs[:5]):
                    rarity = SLOT_RARITIES[slot_idx]
                    lo, hi = RARITY_STAT_RANGES[rarity]
                    song_title = song.get('title', f"{artist_name} - Song {slot_idx+1}")
                    card_id = _deterministic_uuid(genre, artist_idx, song_title)

                    cards.append({
                        "card_id":       card_id,
                        "name":          song_title,
                        "artist_name":   artist_name,
                        "title":         song_title,
                        "rarity":        rarity,
                        "tier":          _rarity_to_tier(rarity),
                        "serial_number": card_id,
                        "print_number":  slot_idx + 1,
                        "quality":       "standard",
                        "impact":        _deterministic_stat(song_title, "impact", lo, hi),
                        "skill":         _deterministic_stat(song_title, "skill", lo, hi),
                        "longevity":     _deterministic_stat(song_title, "longevity", lo, hi),
                        "culture":       _deterministic_stat(song_title, "culture", lo, hi),
                        "hype":          _deterministic_stat(song_title, "hype", lo, hi),
                        "image_url":     song.get('thumbnail_url', ''),
                        "youtube_url":   song.get('youtube_url', ''),
                        "pack_id":       pack_id,
                    })

                cards_json = json.dumps(cards)

                # Insert pack as LIVE
                if db_type == "postgresql":
                    cursor.execute(f"""
                        INSERT INTO creator_packs
                        (pack_id, creator_id, name, description, pack_size,
                         status, cards_data, published_at, price_cents, stripe_payment_id)
                        VALUES ({ph}, 0, {ph}, {ph}, {ph}, 'LIVE', {ph}, CURRENT_TIMESTAMP, 0, 'SEED_PACK')
                    """, (
                        pack_id,
                        pack_name,
                        f"Official {artist_name} pack from {genre} with 5 songs",
                        len(cards),
                        cards_json,
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO creator_packs
                        (pack_id, creator_id, name, description, pack_size,
                         status, cards_data, published_at, price_cents, stripe_payment_id)
                        VALUES (?, 0, ?, ?, ?, 'LIVE', ?, CURRENT_TIMESTAMP, 0, 'SEED_PACK')
                    """, (
                        pack_id,
                        pack_name,
                        f"Official {artist_name} pack from {genre} with 5 songs",
                        len(cards),
                        cards_json,
                    ))

                # Insert each card into the master cards table
                # PostgreSQL uses ON CONFLICT, SQLite uses INSERT OR IGNORE
                if db_type == "postgresql":
                    for card in cards:
                        cursor.execute(f"""
                            INSERT INTO cards
                            (card_id, name, artist_name, title, rarity, tier, serial_number,
                             print_number, quality, impact, skill, longevity, culture, hype,
                             image_url, youtube_url, type, pack_id)
                            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph},
                                    {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, 'artist', {ph})
                            ON CONFLICT (card_id) DO NOTHING
                        """, (
                            card["card_id"],
                            card["name"],
                            card["artist_name"],
                            card["title"],
                            card["rarity"],
                            card["tier"],
                            card["serial_number"],
                            card["print_number"],
                            card["quality"],
                            card["impact"],
                            card["skill"],
                            card["longevity"],
                            card["culture"],
                            card["hype"],
                            card["image_url"],
                            card["youtube_url"],
                            pack_id,
                        ))
                else:
                    for card in cards:
                        cursor.execute("""
                            INSERT OR IGNORE INTO cards
                            (card_id, name, artist_name, title, rarity, tier, serial_number,
                             print_number, quality, impact, skill, longevity, culture, hype,
                             image_url, youtube_url, type, pack_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'artist', ?)
                        """, (
                            card["card_id"],
                            card["name"],
                            card["artist_name"],
                            card["title"],
                            card["rarity"],
                            card["tier"],
                            card["serial_number"],
                            card["print_number"],
                            card["quality"],
                            card["impact"],
                            card["skill"],
                            card["longevity"],
                            card["culture"],
                            card["hype"],
                            card["image_url"],
                            card["youtube_url"],
                            pack_id,
                        ))

                inserted += 1

        conn.commit()
        print(f"✅ [SEED_PACKS] Committed {inserted} packs, skipped {skipped}")
    except Exception as e:
        print(f"❌ [SEED_PACKS] Error during insertion: {e}")
        import traceback
        traceback.print_exc()
        return {"inserted": inserted, "skipped": skipped, "error": str(e)}
    finally:
        conn.close()

    return {"inserted": inserted, "skipped": skipped}
