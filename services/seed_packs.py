"""
Seed Pack Loader

Loads genre_seed_packs.json on startup so the marketplace always has
a baseline catalogue of packs.  Packs are idempotent — if a seed pack
already exists in the DB it is skipped, so this is safe to call every boot.

Each genre gets 5 packs (Vol. 1-5), each with 5 artist cards.
Card rarities per pack:  1 epic, 2 rare, 2 common.
Stats are deterministically seeded from the artist name so they stay
consistent across restarts.
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
    "Hip Hop Legends Vol. 1":"🎙️",
}


def _deterministic_stat(artist_name: str, stat_name: str, lo: int, hi: int) -> int:
    """Generate a repeatable stat from the artist+stat name so values
    don't change across restarts."""
    seed = hashlib.md5(f"{artist_name}:{stat_name}".encode()).hexdigest()
    # Use first 8 hex chars → 0..4294967295, then scale to range
    val = int(seed[:8], 16)
    return lo + (val % (hi - lo + 1))


def _deterministic_uuid(genre: str, artist: str, card_num: int) -> str:
    """Stable UUID so the same seed data always produces the same card_id."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"musiclegends:{genre}:{artist}:{card_num}"))


def _rarity_to_tier(rarity: str) -> str:
    """Map rarity to tier"""
    return {
        "common": "community",
        "rare": "gold",
        "epic": "platinum",
        "legendary": "legendary",
        "mythic": "legendary",
    }.get(rarity.lower(), "community")


# Card variations for each artist (5 cards per pack)
CARD_VARIATIONS = [
    {"suffix": "Prime Era", "rarity": "epic"},
    {"suffix": "Classic Hits", "rarity": "rare"},
    {"suffix": "Deep Cuts", "rarity": "rare"},
    {"suffix": "Live Performance", "rarity": "common"},
    {"suffix": "Legacy", "rarity": "common"},
]


def _build_artist_pack(artist_name: str, genre: str) -> List[Dict]:
    """Build 5 cards for a single artist pack."""
    cards = []
    for i, variation in enumerate(CARD_VARIATIONS):
        rarity = variation["rarity"]
        lo, hi = RARITY_STAT_RANGES[rarity]
        card_id = _deterministic_uuid(genre, artist_name, i)
        card_title = f"{artist_name} - {variation['suffix']}"

        cards.append({
            "card_id":       card_id,
            "name":          artist_name,
            "artist_name":   artist_name,
            "title":         variation["suffix"],
            "rarity":        rarity,
            "tier":          _rarity_to_tier(rarity),
            "serial_number": card_id,
            "print_number":  i + 1,
            "quality":       "standard",
            "impact":        _deterministic_stat(f"{artist_name}:{i}", "impact", lo, hi),
            "skill":         _deterministic_stat(f"{artist_name}:{i}", "skill", lo, hi),
            "longevity":     _deterministic_stat(f"{artist_name}:{i}", "longevity", lo, hi),
            "culture":       _deterministic_stat(f"{artist_name}:{i}", "culture", lo, hi),
            "hype":          _deterministic_stat(f"{artist_name}:{i}", "hype", lo, hi),
            "image_url":     "",
            "youtube_url":   "",
        })
    return cards


def _seed_pack_id(genre: str, artist_name: str) -> str:
    """Stable pack_id so we can detect if a seed pack already exists."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"musiclegends:pack:{genre}:{artist_name}"))


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

        for genre, artist_list in genre_data.items():
            emoji = GENRE_EMOJI.get(genre, "🎵")

            # Each artist in the list becomes their own pack with 5 cards
            for artist_name in artist_list:
                pack_id = _seed_pack_id(genre, artist_name)
                pack_name = f"{emoji} {artist_name}"

                # Check if this seed pack already exists (by pack_id only - safer)
                cursor.execute(
                    f"SELECT 1 FROM creator_packs WHERE pack_id = {ph}",
                    (pack_id,)
                )
                if cursor.fetchone():
                    skipped += 1
                    continue

                # Build 5 cards for this artist
                cards = _build_artist_pack(artist_name, genre)
                for card in cards:
                    card["pack_id"] = pack_id

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
                        f"Official {genre} pack featuring {artist_name}",
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
                        f"Official {genre} pack featuring {artist_name}",
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
                            card.get("artist_name", card["name"]),
                            card["title"],
                            card["rarity"],
                            card.get("tier", _rarity_to_tier(card["rarity"])),
                            card.get("serial_number", card["card_id"]),
                            card.get("print_number", 1),
                            card.get("quality", "standard"),
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
                            card.get("artist_name", card["name"]),
                            card["title"],
                            card["rarity"],
                            card.get("tier", _rarity_to_tier(card["rarity"])),
                            card.get("serial_number", card["card_id"]),
                            card.get("print_number", 1),
                            card.get("quality", "standard"),
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
