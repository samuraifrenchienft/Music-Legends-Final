#!/usr/bin/env python3
"""
Test pack creation with marketplace publishing and creator copy
"""

import asyncio
import sqlite3
from spotify_integration import spotify_integration
from database import DatabaseManager

async def test_pack_marketplace():
    """Test complete pack creation flow with marketplace and creator copy"""
    
    print("="*70)
    print("TESTING PACK CREATION WITH MARKETPLACE & CREATOR COPY")
    print("="*70)
    
    db = DatabaseManager()
    test_creator_id = 999888777
    
    # Test 1: Create pack
    print("\n[1/5] Creating pack...")
    artists = spotify_integration.search_artists("Drake", limit=1)
    artist = artists[0]
    tracks = spotify_integration.search_tracks(artist['name'], artist_id=artist['id'], limit=5)
    
    pack_id = db.create_creator_pack(
        creator_id=test_creator_id,
        name="Test Marketplace Pack",
        description=f"Test pack featuring {artist['name']}",
        pack_size=len(tracks)
    )
    print(f"✅ Pack created: {pack_id}")
    
    # Test 2: Add cards to pack
    print("\n[2/5] Adding cards to pack...")
    cards_created = []
    for track in tracks:
        stats = spotify_integration.generate_card_stats(artist)
        rarity = spotify_integration.determine_rarity(artist)
        
        card_data = {
            'card_id': f"{pack_id}_{track['id']}",
            'name': artist['name'],
            'title': track['name'],
            'hero_artist': artist['name'],
            'hero_song': track['name'],
            'rarity': rarity.lower(),
            'spotify_id': track['id'],
            'spotify_url': track.get('spotify_url', ''),
            'youtube_id': '',
            'image_url': track.get('image_url', ''),
            'impact': stats['impact'],
            'skill': stats['skill'],
            'longevity': stats['longevity'],
            'culture': stats['culture'],
            'hype': stats['hype']
        }
        
        success = db.add_card_to_master(card_data)
        if success:
            db.add_card_to_pack(pack_id, card_data)
            cards_created.append(card_data)
    
    print(f"✅ Added {len(cards_created)} cards to pack")
    
    # Test 3: Publish pack to marketplace
    print("\n[3/5] Publishing pack to marketplace...")
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE creator_packs 
            SET status = 'LIVE', published_at = CURRENT_TIMESTAMP
            WHERE pack_id = ?
        """, (pack_id,))
        conn.commit()
    print("✅ Pack published to LIVE status")
    
    # Test 4: Give creator free copy
    print("\n[4/5] Giving creator free copy...")
    for card in cards_created:
        db.add_card_to_collection(
            user_id=test_creator_id,
            card_id=card['card_id'],
            acquired_from='pack_creation'
        )
    print(f"✅ Added {len(cards_created)} cards to creator's collection")
    
    # Test 5: Verify pack is in marketplace
    print("\n[5/5] Verifying pack in marketplace...")
    live_packs = db.get_live_packs(limit=100)
    pack_in_marketplace = any(p['pack_id'] == pack_id for p in live_packs)
    
    if pack_in_marketplace:
        print(f"✅ Pack found in marketplace!")
        pack = next(p for p in live_packs if p['pack_id'] == pack_id)
        print(f"   Name: {pack['name']}")
        print(f"   Status: {pack['status']}")
        print(f"   Cards: {pack['pack_size']}")
    else:
        print("❌ Pack NOT found in marketplace")
        return False
    
    # Verify creator has cards
    print("\n[BONUS] Verifying creator collection...")
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM user_cards 
            WHERE user_id = ? AND acquired_from = 'pack_creation'
        """, (test_creator_id,))
        card_count = cursor.fetchone()[0]
    
    if card_count == len(cards_created):
        print(f"✅ Creator has {card_count} cards in collection")
    else:
        print(f"❌ Creator has {card_count} cards, expected {len(cards_created)}")
        return False
    
    # Summary
    print("\n" + "="*70)
    print("PACK CREATION FLOW COMPLETE")
    print("="*70)
    print(f"✅ Pack created: {pack_id}")
    print(f"✅ Cards created: {len(cards_created)}")
    print(f"✅ Published to marketplace: LIVE")
    print(f"✅ Creator received free copy: {card_count} cards")
    print("\n🎉 ALL TESTS PASSED - PACK CREATION WORKING!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_pack_marketplace())
    exit(0 if success else 1)
