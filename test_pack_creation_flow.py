#!/usr/bin/env python3
"""
Test the pack creation workflow (no Spotify dependency)
"""

import asyncio
import sqlite3
from database import DatabaseManager

async def test_pack_creation():
    """Test complete pack creation flow using hardcoded sample data"""

    print("="*70)
    print("TESTING PACK CREATION WORKFLOW")
    print("="*70)

    db = DatabaseManager()
    test_creator_id = 123456789

    # Ensure test user exists
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (test_creator_id, "TestCreator"))
        conn.commit()

    # Sample data (no external API needed)
    artist_name = "Drake"
    rarity = "rare"
    stats = {"impact": 90, "skill": 85, "longevity": 94, "culture": 91, "hype": 89}
    tracks = [
        {"id": "t1", "name": "Hotline Bling"},
        {"id": "t2", "name": "God's Plan"},
        {"id": "t3", "name": "One Dance"},
        {"id": "t4", "name": "In My Feelings"},
        {"id": "t5", "name": "Nice For What"},
    ]

    # Test 1: Database Pack Creation
    print("\n[1/2] Creating pack in database...")
    pack_id = db.create_creator_pack(
        creator_id=test_creator_id,
        name="Test Drake Pack",
        description=f"Test pack featuring {artist_name}",
        pack_size=len(tracks)
    )

    if pack_id:
        print(f"✅ Pack created: {pack_id}")
    else:
        print("❌ Failed to create pack")
        return False

    # Test 2: Create cards for pack
    print("\n[2/2] Adding cards to pack...")
    cards_created = 0
    for track in tracks:
        card_data = {
            'card_id': f"{pack_id}_{track['id']}",
            'name': artist_name,
            'title': track['name'],
            'hero_artist': artist_name,
            'hero_song': track['name'],
            'rarity': rarity,
            'youtube_id': '',
            'image_url': '',
            'impact': stats['impact'],
            'skill': stats['skill'],
            'longevity': stats['longevity'],
            'culture': stats['culture'],
            'hype': stats['hype'],
        }

        success = db.add_card_to_master(card_data)
        if success:
            db.add_card_to_pack(pack_id, card_data)
            cards_created += 1

    print(f"✅ Created {cards_created}/{len(tracks)} cards")

    # Summary
    print("\n" + "="*70)
    print("PACK CREATION SUMMARY")
    print("="*70)
    print(f"Pack ID: {pack_id}")
    print(f"Artist: {artist_name}")
    print(f"Cards: {cards_created}")
    print(f"Rarity: {rarity}")
    print(f"Average Power: {sum(stats.values()) / len(stats):.1f}")
    print("\nSample Cards:")
    for i, track in enumerate(tracks[:5], 1):
        print(f"  {i}. {track['name']} ({rarity})")

    print("\n✅ PACK CREATION WORKFLOW COMPLETE!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_pack_creation())
    exit(0 if success else 1)
