"""
Seed Pack Loader

Loads genre_seed_packs.json on startup so the marketplace always has
a baseline catalogue of packs.  Packs are idempotent — if a seed pack
already exists in the DB it is skipped, so this is safe to call every boot.

Each genre has 15 artists. For each artist:
- Attempt to fetch 5 songs from Last.fm / YouTube / AudioDB APIs
- If APIs fail or are unavailable, use placeholder song names
- Create 1 pack per artist with 5 song cards
- Card rarities per pack: 1 epic, 2 rare, 2 common
- Stats are deterministic (hash-based) so they never change
- Each pack is committed individually so partial failures don't lose data
Result: 15 packs per genre = 75 total
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

# Artist power threshold: >= this value → Gold tier, below → Community tier
GOLD_TIER_THRESHOLD = 88

# Card rarity mix per pack tier
TIER_SLOT_RARITIES = {
    "gold":      ["epic", "rare", "rare", "common", "common"],
    "community": ["rare", "rare", "common", "common", "common"],
}

# Stat ranges by rarity
RARITY_STAT_RANGES = {
    "common":    (18, 38),
    "rare":      (32, 55),
    "epic":      (50, 75),
    "legendary": (65, 92),
}

# Artist power rankings (0-100) based on career sales, cultural impact, streaming
ARTIST_POWER = {
    # Hip Hop Legends
    "2Pac": 96, "The Notorious B.I.G.": 95, "Jay-Z": 94, "Eminem": 93,
    "Kanye West": 92, "Kendrick Lamar": 91, "Nas": 90, "Lil Wayne": 89,
    "Dr. Dre": 88, "Snoop Dogg": 87, "OutKast": 86, "Ice Cube": 85,
    "A Tribe Called Quest": 84, "Public Enemy": 83, "Rakim": 82,
    "Wu-Tang Clan": 81,
    # EDM Bangers
    "Daft Punk": 96, "Avicii": 94, "Calvin Harris": 91, "Deadmau5": 90,
    "Tiesto": 89, "Skrillex": 88, "Martin Garrix": 87, "Diplo": 86,
    "Marshmello": 85, "Odesza": 84, "Flume": 83, "Porter Robinson": 82,
    "Eric Prydz": 81, "Disclosure": 80, "Bonobo": 79,
    "Rüfüs Du Sol": 78, "Lane 8": 77,
    # Rock Classics
    "Led Zeppelin": 97, "Pink Floyd": 96, "Queen": 95,
    "The Rolling Stones": 94, "Jimi Hendrix": 93, "AC/DC": 92,
    "The Who": 90, "Fleetwood Mac": 89, "Eagles": 88,
    "Aerosmith": 87, "The Doors": 86, "Rush": 85, "Deep Purple": 84,
    "Santana": 83, "Cream": 82,
    # R&B Soul Pack
    "Prince": 97, "Stevie Wonder": 96, "Aretha Franklin": 95,
    "Marvin Gaye": 94, "Whitney Houston": 93, "Lauryn Hill": 92,
    "Earth, Wind & Fire": 91, "Al Green": 90, "Luther Vandross": 88,
    "The Isley Brothers": 87, "Chaka Khan": 86, "Sade": 85,
    "D'Angelo": 84, "Erykah Badu": 83, "Anita Baker": 82,
    # Pop Hits 2024
    "Taylor Swift": 96, "Bruno Mars": 94, "The Weeknd": 93,
    "Ed Sheeran": 92, "Ariana Grande": 91, "Dua Lipa": 90,
    "Billie Eilish": 89, "Harry Styles": 88, "Post Malone": 87,
    "Justin Bieber": 86, "Doja Cat": 85, "SZA": 84,
    "Olivia Rodrigo": 83, "Sabrina Carpenter": 80, "Tate McRae": 78,
}

# Pack tier pricing
PACK_TIER_PRICING = {
    "community": {"price_cents": 299, "price_gold": 500},
    "gold":      {"price_cents": 499, "price_gold": 900},
}

# Genre → emoji for pack display
GENRE_EMOJI = {
    "EDM Bangers":           "🎧",
    "Rock Classics":         "🎸",
    "R&B Soul Pack":         "🎷",
    "Pop Hits 2024":         "🎤",
    "Hip Hop Legends":       "🎙️",
}

# Fallback song names when APIs are unavailable
FALLBACK_SONGS = {
    "Disclosure": ["Latch", "White Noise", "Omen", "When a Fire Starts to Burn", "Magnets"],
    "Eric Prydz": ["Call on Me", "Pjanoo", "Every Day", "Opus", "Generate"],
    "Bonobo": ["Kerala", "Cirrus", "Kong", "Black Sands", "Sapphire"],
    "Rüfüs Du Sol": ["Innerbloom", "Alive", "No Place", "Underwater", "On My Knees"],
    "Lane 8": ["Rise", "No Captain", "Fingerprint", "Little by Little", "Brightest Lights"],
    "Flume": ["Never Be Like You", "Say It", "Holdin On", "Sleepless", "Rushing Back"],
    "Odesza": ["A Moment Apart", "Say My Name", "Loyal", "Line of Sight", "Higher Ground"],
    "Deadmau5": ["Strobe", "Ghosts n Stuff", "I Remember", "The Veldt", "Raise Your Weapon"],
    "Calvin Harris": ["Feel So Close", "Summer", "This Is What You Came For", "Outside", "Sweet Nothing"],
    "Skrillex": ["Bangarang", "Scary Monsters and Nice Sprites", "Cinema", "First of the Year", "Make It Bun Dem"],
    "Martin Garrix": ["Animals", "Scared to Be Lonely", "In the Name of Love", "Tremor", "High on Life"],
    "Tiesto": ["Adagio for Strings", "Red Lights", "Traffic", "Elements of Life", "The Business"],
    "Avicii": ["Levels", "Wake Me Up", "Hey Brother", "Waiting for Love", "The Nights"],
    "Diplo": ["Revolution", "Lean On", "Get It Right", "Express Yourself", "Set It Off"],
    "Porter Robinson": ["Language", "Shelter", "Divinity", "Sad Machine", "Goodbye to a World"],
    "Led Zeppelin": ["Stairway to Heaven", "Kashmir", "Whole Lotta Love", "Black Dog", "Rock and Roll"],
    "Pink Floyd": ["Comfortably Numb", "Wish You Were Here", "Money", "Time", "Another Brick in the Wall"],
    "The Rolling Stones": ["Paint It Black", "Satisfaction", "Sympathy for the Devil", "Gimme Shelter", "Start Me Up"],
    "Queen": ["Bohemian Rhapsody", "We Will Rock You", "Don't Stop Me Now", "Somebody to Love", "Under Pressure"],
    "AC/DC": ["Back in Black", "Thunderstruck", "Highway to Hell", "T.N.T.", "You Shook Me All Night Long"],
    "Jimi Hendrix": ["Purple Haze", "All Along the Watchtower", "Voodoo Child", "Hey Joe", "The Wind Cries Mary"],
    "The Who": ["Baba O'Riley", "My Generation", "Won't Get Fooled Again", "Pinball Wizard", "Behind Blue Eyes"],
    "Fleetwood Mac": ["Dreams", "The Chain", "Go Your Own Way", "Everywhere", "Rhiannon"],
    "Eagles": ["Hotel California", "Take It Easy", "Desperado", "Life in the Fast Lane", "Heartache Tonight"],
    "Aerosmith": ["Dream On", "Walk This Way", "Sweet Emotion", "I Don't Want to Miss a Thing", "Crazy"],
    "Rush": ["Tom Sawyer", "Limelight", "The Spirit of Radio", "Closer to the Heart", "2112"],
    "Deep Purple": ["Smoke on the Water", "Highway Star", "Child in Time", "Hush", "Black Night"],
    "Cream": ["Sunshine of Your Love", "White Room", "Crossroads", "Badge", "Strange Brew"],
    "The Doors": ["Light My Fire", "Riders on the Storm", "Break On Through", "People Are Strange", "L.A. Woman"],
    "Santana": ["Black Magic Woman", "Smooth", "Oye Como Va", "Maria Maria", "Evil Ways"],
    "Stevie Wonder": ["Superstition", "Isn't She Lovely", "I Just Called to Say I Love You", "Sir Duke", "Signed Sealed Delivered"],
    "Aretha Franklin": ["Respect", "Natural Woman", "Chain of Fools", "Think", "I Say a Little Prayer"],
    "Marvin Gaye": ["What's Going On", "Let's Get It On", "Sexual Healing", "Ain't No Mountain High Enough", "I Heard It Through the Grapevine"],
    "Al Green": ["Let's Stay Together", "Tired of Being Alone", "Love and Happiness", "I'm Still in Love with You", "Here I Am"],
    "Luther Vandross": ["Never Too Much", "Here and Now", "Dance with My Father", "Always and Forever", "A House Is Not a Home"],
    "Earth, Wind & Fire": ["September", "Boogie Wonderland", "Shining Star", "Let's Groove", "Fantasy"],
    "The Isley Brothers": ["Shout", "It's Your Thing", "Between the Sheets", "Twist and Shout", "That Lady"],
    "Chaka Khan": ["I'm Every Woman", "Through the Fire", "Ain't Nobody", "I Feel for You", "Tell Me Something Good"],
    "Anita Baker": ["Sweet Love", "Giving You the Best That I Got", "Caught Up in the Rapture", "Angel", "Body and Soul"],
    "Sade": ["Smooth Operator", "No Ordinary Love", "By Your Side", "Sweetest Taboo", "Kiss of Life"],
    "D'Angelo": ["Untitled", "Brown Sugar", "Really Love", "Cruisin'", "Lady"],
    "Erykah Badu": ["On & On", "Tyrone", "Bag Lady", "Window Seat", "Didn't Cha Know"],
    "Lauryn Hill": ["Doo Wop (That Thing)", "Everything Is Everything", "Ex-Factor", "Lost Ones", "To Zion"],
    "Whitney Houston": ["I Will Always Love You", "I Wanna Dance with Somebody", "Greatest Love of All", "How Will I Know", "Run to You"],
    "Prince": ["Purple Rain", "When Doves Cry", "Kiss", "1999", "Little Red Corvette"],
    "Taylor Swift": ["Shake It Off", "Love Story", "Anti-Hero", "Blank Space", "Cruel Summer"],
    "Ariana Grande": ["Thank U Next", "7 Rings", "Positions", "No Tears Left to Cry", "Into You"],
    "The Weeknd": ["Blinding Lights", "Starboy", "Can't Feel My Face", "Save Your Tears", "The Hills"],
    "Billie Eilish": ["Bad Guy", "Happier Than Ever", "Lovely", "Everything I Wanted", "Ocean Eyes"],
    "Olivia Rodrigo": ["Drivers License", "Good 4 U", "Vampire", "Deja Vu", "Brutal"],
    "Harry Styles": ["As It Was", "Watermelon Sugar", "Sign of the Times", "Adore You", "Late Night Talking"],
    "Doja Cat": ["Say So", "Kiss Me More", "Need to Know", "Woman", "Streets"],
    "Post Malone": ["Circles", "Rockstar", "Sunflower", "Congratulations", "Better Now"],
    "Dua Lipa": ["Levitating", "Don't Start Now", "New Rules", "Physical", "One Kiss"],
    "Bruno Mars": ["Uptown Funk", "Just the Way You Are", "24K Magic", "Grenade", "Locked Out of Heaven"],
    "Ed Sheeran": ["Shape of You", "Thinking Out Loud", "Perfect", "Castle on the Hill", "Photograph"],
    "Justin Bieber": ["Peaches", "Stay", "Sorry", "Love Yourself", "Baby"],
    "Sabrina Carpenter": ["Espresso", "Nonsense", "Feather", "Because I Liked a Boy", "Fast Times"],
    "Tate McRae": ["Greedy", "You Broke Me First", "She's All I Wanna Be", "Exes", "Feel Like"],
    "SZA": ["Kill Bill", "Good Days", "Kiss Me More", "Love Galore", "Snooze"],
    "The Notorious B.I.G.": ["Juicy", "Big Poppa", "Hypnotize", "Mo Money Mo Problems", "Sky's the Limit"],
    "2Pac": ["Changes", "California Love", "Dear Mama", "Hit Em Up", "Ambitionz Az a Ridah"],
    "Jay-Z": ["Empire State of Mind", "99 Problems", "Hard Knock Life", "Run This Town", "Dirt Off Your Shoulder"],
    "Nas": ["N.Y. State of Mind", "If I Ruled the World", "One Mic", "The World Is Yours", "Illmatic"],
    "Wu-Tang Clan": ["C.R.E.A.M.", "Protect Ya Neck", "Triumph", "Da Mystery of Chessboxin'", "Method Man"],
    "Snoop Dogg": ["Gin and Juice", "Drop It Like It's Hot", "Still D.R.E.", "Who Am I", "Beautiful"],
    "Dr. Dre": ["Still D.R.E.", "Nuthin' but a G Thang", "Forgot About Dre", "The Next Episode", "I Need a Doctor"],
    "Eminem": ["Lose Yourself", "Stan", "Without Me", "The Real Slim Shady", "Not Afraid"],
    "OutKast": ["Hey Ya!", "Ms. Jackson", "Roses", "So Fresh So Clean", "The Way You Move"],
    "Kendrick Lamar": ["HUMBLE.", "DNA.", "Alright", "Swimming Pools", "Money Trees"],
    "Kanye West": ["Stronger", "Gold Digger", "Heartless", "Runaway", "Power"],
    "Ice Cube": ["It Was a Good Day", "Check Yo Self", "Friday", "No Vaseline", "You Can Do It"],
    "A Tribe Called Quest": ["Can I Kick It?", "Scenario", "Electric Relaxation", "Award Tour", "Check the Rhime"],
    "Public Enemy": ["Fight the Power", "Bring the Noise", "911 Is a Joke", "Don't Believe the Hype", "Black Steel in the Hour of Chaos"],
    "Rakim": ["Paid in Full", "I Ain't No Joke", "Follow the Leader", "Microphone Fiend", "Know the Ledge"],
}


def _deterministic_stat(artist_name: str, stat_name: str, lo: int, hi: int) -> int:
    """Generate a repeatable stat from the artist+stat name so values
    don't change across restarts."""
    seed = hashlib.md5(f"{artist_name}:{stat_name}".encode()).hexdigest()
    val = int(seed[:8], 16)
    return lo + (val % (hi - lo + 1))


def _merit_based_stats(artist_name: str, song_title: str, rarity: str) -> dict:
    """Generate merit-based stats using artist power ranking.

    Stronger artists produce stronger cards. A small MD5-derived offset
    per stat keeps individual stats from being identical.
    """
    power = ARTIST_POWER.get(artist_name, 50)
    lo, hi = RARITY_STAT_RANGES[rarity]
    range_size = hi - lo
    center = lo + int(range_size * (power / 100))

    stats = {}
    for stat_name in ("impact", "skill", "longevity", "culture", "hype"):
        md5_hex = hashlib.md5(f"{song_title}:{stat_name}".encode()).hexdigest()
        offset = (int(md5_hex[:4], 16) % 7) - 3  # -3 to +3
        value = max(lo, min(hi, center + offset))
        stats[stat_name] = value
    return stats


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


def _get_songs_for_artist(artist_name, yt, lastfm, audiodb):
    """Try APIs for song data, fall back to hardcoded songs if unavailable."""
    songs = []
    artist_info = None
    artist_videos = []

    # Try AudioDB for images
    if audiodb:
        try:
            artist_results = audiodb.search_artist(artist_name, limit=1)
            if artist_results:
                artist_info = artist_results[0]
                artist_id = artist_info.get('id')
                if artist_id:
                    artist_videos = audiodb.get_music_videos(artist_id)
        except Exception:
            pass

    # Try Last.fm for track names
    tracks = []
    if lastfm:
        try:
            tracks = lastfm.get_top_tracks(artist_name, limit=5)
        except Exception:
            tracks = []

    # Build song list from API data
    for idx, track in enumerate(tracks[:5]):
        song_name = track.get('name', '')
        song_data = {
            'title': f"{artist_name} - {song_name}",
            'song_name': song_name,
            'thumbnail_url': '',
            'youtube_url': ''
        }
        if artist_videos and idx < len(artist_videos):
            song_data['thumbnail_url'] = artist_videos[idx].get('thumbnail', '')

        if yt and song_name:
            try:
                videos = yt.search_music_video(artist_name, song_name, limit=1)
                if videos:
                    if not song_data['thumbnail_url']:
                        song_data['thumbnail_url'] = videos[0].get('thumbnail_url', '')
                    song_data['youtube_url'] = videos[0].get('youtube_url', '')
            except Exception:
                pass

        songs.append(song_data)

    # Fill remaining slots from fallback list
    if len(songs) < 5:
        fallback = FALLBACK_SONGS.get(artist_name, [f"Song {i+1}" for i in range(5)])
        fallback_image = artist_info.get('thumb', '') if artist_info else ''
        for i in range(len(songs), 5):
            song_name = fallback[i] if i < len(fallback) else f"Song {i+1}"
            songs.append({
                'title': f"{artist_name} - {song_name}",
                'song_name': song_name,
                'thumbnail_url': fallback_image,
                'youtube_url': ''
            })

    return songs[:5]


def seed_packs_into_db(db_path: str = "music_legends.db", force_reseed: bool = False) -> Dict[str, int]:
    """Insert seed packs into the database. Skips packs that already exist.

    Each pack is committed individually so API failures for one artist
    don't prevent other packs from being created.

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
    failed = 0

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

        # Clean up ALL old-style packs from before the seed system.
        # ADMIN_IMPORT packs (any creator_id) are from the old bulk import and
        # are fully replaced by the new 75 seed packs.  Also remove orphan
        # packs with no stripe_payment_id that aren't user-created drafts.
        try:
            cursor.execute(
                "DELETE FROM creator_packs "
                "WHERE stripe_payment_id = 'ADMIN_IMPORT' "
                "   OR (stripe_payment_id IS NULL AND creator_id = 0)"
            )
            old_deleted = cursor.rowcount
            if old_deleted > 0:
                conn.commit()
                print(f"🗑️ [SEED_PACKS] Removed {old_deleted} old-style packs (pre-seed system)")
        except Exception:
            pass

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
                    cards_data TEXT,
                    genre TEXT
                )
            """)
            # Ensure extra columns exist on old PostgreSQL tables
            for col, col_def in [("genre", "TEXT"), ("price_gold", "INTEGER DEFAULT 500"), ("pack_tier", "TEXT DEFAULT 'community'")]:
                try:
                    cursor.execute(f"ALTER TABLE creator_packs ADD COLUMN {col} {col_def}")
                except Exception:
                    pass  # column already exists
            conn.commit()
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
        else:
            # SQLite: ensure required columns exist (database.py usually handles this,
            # but be defensive in case seed_packs runs in isolation)
            cursor.execute("PRAGMA table_info(creator_packs)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            for col, col_def in [("genre", "TEXT"), ("price_gold", "INTEGER DEFAULT 500"), ("pack_tier", "TEXT DEFAULT 'community'")]:
                if col not in existing_cols:
                    cursor.execute(f"ALTER TABLE creator_packs ADD COLUMN {col} {col_def}")
            conn.commit()

        # Skip external API calls — all 75 artists have FALLBACK_SONGS with
        # hardcoded song names.  API calls (AudioDB, Last.fm, YouTube) only add
        # thumbnails/URLs and can hang for minutes on Railway, blocking startup.
        yt = None
        lastfm = None
        audiodb = None
        print("✅ [SEED_PACKS] Using fallback songs (no API calls — fast startup)")

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

                # Wrap each pack in its own try/except so one failure
                # doesn't prevent the remaining 74 packs from inserting
                try:
                    songs = _get_songs_for_artist(artist_name, yt, lastfm, audiodb)

                    # Determine pack tier from artist power ranking
                    power = ARTIST_POWER.get(artist_name, 50)
                    pack_tier = "gold" if power >= GOLD_TIER_THRESHOLD else "community"
                    slot_rarities = TIER_SLOT_RARITIES[pack_tier]

                    # Build 5 cards (1 per song) with tier-based rarities
                    cards = []
                    for slot_idx, song in enumerate(songs[:5]):
                        rarity = slot_rarities[slot_idx]
                        song_title = song.get('title', f"{artist_name} - Song {slot_idx+1}")
                        card_id = _deterministic_uuid(genre, artist_idx, song_title)
                        merit_stats = _merit_based_stats(artist_name, song_title, rarity)

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
                            "impact":        merit_stats["impact"],
                            "skill":         merit_stats["skill"],
                            "longevity":     merit_stats["longevity"],
                            "culture":       merit_stats["culture"],
                            "hype":          merit_stats["hype"],
                            "image_url":     song.get('thumbnail_url', ''),
                            "youtube_url":   song.get('youtube_url', ''),
                            "pack_id":       pack_id,
                        })

                    cards_json = json.dumps(cards)

                    # Pack tier already set from artist power above
                    tier_pricing = PACK_TIER_PRICING[pack_tier]
                    price_cents = tier_pricing["price_cents"]
                    price_gold = tier_pricing["price_gold"]

                    # Insert pack as LIVE
                    if db_type == "postgresql":
                        cursor.execute(f"""
                            INSERT INTO creator_packs
                            (pack_id, creator_id, name, description, pack_size,
                             status, cards_data, published_at, price_cents, price_gold,
                             pack_tier, stripe_payment_id, genre)
                            VALUES ({ph}, 0, {ph}, {ph}, {ph}, 'LIVE', {ph}, CURRENT_TIMESTAMP,
                                    {ph}, {ph}, {ph}, 'SEED_PACK', {ph})
                        """, (
                            pack_id,
                            pack_name,
                            f"Official {artist_name} pack from {genre} with 5 songs",
                            len(cards),
                            cards_json,
                            price_cents,
                            price_gold,
                            pack_tier,
                            genre,
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO creator_packs
                            (pack_id, creator_id, name, description, pack_size,
                             status, cards_data, published_at, price_cents, price_gold,
                             pack_tier, stripe_payment_id, genre)
                            VALUES (?, 0, ?, ?, ?, 'LIVE', ?, CURRENT_TIMESTAMP,
                                    ?, ?, ?, 'SEED_PACK', ?)
                        """, (
                            pack_id,
                            pack_name,
                            f"Official {artist_name} pack from {genre} with 5 songs",
                            len(cards),
                            cards_json,
                            price_cents,
                            price_gold,
                            pack_tier,
                            genre,
                        ))

                    # Insert each card into the master cards table
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

                    # Grant cards to dev account(s) so they have every pack
                    dev_ids_str = os.getenv("DEV_USER_IDS", "")
                    if dev_ids_str:
                        for dev_id_str in dev_ids_str.split(","):
                            dev_id_str = dev_id_str.strip()
                            if dev_id_str.isdigit():
                                dev_id = int(dev_id_str)
                                for card in cards:
                                    if db_type == "postgresql":
                                        cursor.execute(f"""
                                            INSERT INTO user_cards (user_id, card_id, acquired_from)
                                            VALUES ({ph}, {ph}, 'seed_grant')
                                            ON CONFLICT (user_id, card_id) DO NOTHING
                                        """, (dev_id, card["card_id"]))
                                    else:
                                        cursor.execute("""
                                            INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from)
                                            VALUES (?, ?, 'seed_grant')
                                        """, (dev_id, card["card_id"]))

                    # COMMIT after each pack so failures don't lose previous work
                    conn.commit()
                    inserted += 1
                    print(f"✅ [SEED_PACKS] Inserted: {pack_name} ({genre}) [{inserted} total]")

                except Exception as e:
                    # Roll back just this pack, continue with the next one
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    failed += 1
                    print(f"⚠️ [SEED_PACKS] Failed to insert {artist_name} ({genre}): {e}")
                    continue

        print(f"✅ [SEED_PACKS] Done: {inserted} inserted, {skipped} skipped, {failed} failed")

        # Always grant all seed-pack cards to DEV_USER_IDS (even if packs were
        # already in the DB and skipped).  This ensures new dev users get cards
        # without needing a force-reseed.  INSERT OR IGNORE makes it a fast no-op
        # for users who already have them.
        dev_ids_str = os.getenv("DEV_USER_IDS", "")
        if dev_ids_str:
            try:
                cursor.execute(
                    f"SELECT card_id FROM cards WHERE pack_id IN "
                    f"(SELECT pack_id FROM creator_packs WHERE stripe_payment_id = 'SEED_PACK')"
                )
                all_seed_card_ids = [row[0] for row in cursor.fetchall()]

                granted = 0
                for dev_id_str in dev_ids_str.split(","):
                    dev_id_str = dev_id_str.strip()
                    if not dev_id_str.isdigit():
                        continue
                    dev_id = int(dev_id_str)
                    for card_id in all_seed_card_ids:
                        if db_type == "postgresql":
                            cursor.execute(f"""
                                INSERT INTO user_cards (user_id, card_id, acquired_from)
                                VALUES ({ph}, {ph}, 'seed_grant')
                                ON CONFLICT (user_id, card_id) DO NOTHING
                            """, (dev_id, card_id))
                        else:
                            cursor.execute("""
                                INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from)
                                VALUES (?, ?, 'seed_grant')
                            """, (dev_id, card_id))
                    granted += 1
                conn.commit()
                if granted:
                    print(f"✅ [SEED_PACKS] Granted {len(all_seed_card_ids)} seed cards to {granted} dev user(s)")
            except Exception as e:
                print(f"⚠️ [SEED_PACKS] Dev grant error (non-critical): {e}")

    except Exception as e:
        print(f"❌ [SEED_PACKS] Error during insertion: {e}")
        import traceback
        traceback.print_exc()
        return {"inserted": inserted, "skipped": skipped, "failed": failed, "error": str(e)}
    finally:
        conn.close()

    return {"inserted": inserted, "skipped": skipped, "failed": failed}
