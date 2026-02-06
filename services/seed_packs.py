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


def _deterministic_uuid(genre: str, vol: int, artist: str) -> str:
    """Stable UUID so the same seed data always produces the same card_id."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"musiclegends:{genre}:{vol}:{artist}"))


def _rarity_to_tier(rarity: str) -> str:
    """Map rarity to tier"""
    return {
        "common": "community",
        "rare": "gold",
        "epic": "platinum",
        "legendary": "legendary",
        "mythic": "legendary",
    }.get(rarity.lower(), "community")


def _build_card(artist_name: str, rarity: str, genre: str, vol: int) -> Dict:
    lo, hi = RARITY_STAT_RANGES[rarity]
    card_id = _deterministic_uuid(genre, vol, artist_name)
    return {
        "card_id":       card_id,
        "name":          artist_name,
        "artist_name":   artist_name,           # ADD: alias for display
        "title":         "",
        "rarity":        rarity,
        "tier":          _rarity_to_tier(rarity), # ADD: mapped from rarity
        "serial_number": card_id,               # ADD: use card_id as serial
        "print_number":  1,                     # ADD: print sequence
        "quality":       "standard",            # ADD: card quality
        "impact":        _deterministic_stat(artist_name, "impact",    lo, hi),
        "skill":         _deterministic_stat(artist_name, "skill",     lo, hi),
        "longevity":     _deterministic_stat(artist_name, "longevity", lo, hi),
        "culture":       _deterministic_stat(artist_name, "culture",   lo, hi),
        "hype":          _deterministic_stat(artist_name, "hype",      lo, hi),
        "image_url":     "",
        "youtube_url":   "",
    }


def _seed_pack_id(genre: str, vol: int) -> str:
    """Stable pack_id so we can detect if a seed pack already exists."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"musiclegends:pack:{genre}:{vol}"))


def load_seed_data() -> Dict[str, List[List[str]]]:
    """Load the genre seed JSON file."""
    seed_path = Path(__file__).resolve().parent.parent / "data" / "genre_seed_packs.json"
    if not seed_path.exists():
        print(f"⚠️  Seed file not found: {seed_path}")
        return {}
    with open(seed_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_packs_into_db(db_path: str = "music_legends.db") -> Dict[str, int]:
    """Insert seed packs into the database. Skips packs that already exist.

    Returns dict with counts: {"inserted": N, "skipped": N}
    """
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

        for genre, pack_lists in genre_data.items():
            emoji = GENRE_EMOJI.get(genre, "🎵")

            for vol_idx, artist_list in enumerate(pack_lists):
                vol = vol_idx + 1
                pack_id = _seed_pack_id(genre, vol)
                pack_name = f"{emoji} {genre} Vol. {vol}"

                # Check if this seed pack already exists (by ID or by name)
                cursor.execute(
                    f"SELECT 1 FROM creator_packs WHERE pack_id = {ph} OR name = {ph}",
                    (pack_id, pack_name)
                )
                if cursor.fetchone():
                    skipped += 1
                    continue

                # Build cards
                cards = []
                for slot_idx, artist_name in enumerate(artist_list):
                    rarity = SLOT_RARITIES[slot_idx] if slot_idx < len(SLOT_RARITIES) else "common"
                    card = _build_card(artist_name, rarity, genre, vol)
                    card["pack_id"] = pack_id
                    cards.append(card)

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
                        f"Official {genre} pack — Volume {vol}",
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
                        f"Official {genre} pack — Volume {vol}",
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
