#!/usr/bin/env python3
"""
Test the new pack creation workflow
"""

import asyncio
from spotify_integration import spotify_integration
from database import DatabaseManager

async def test_pack_creation():
    """Test complete pack creation flow"""
    
    print("="*70)
    print("TESTING PACK CREATION WORKFLOW")
    print("="*70)
    
    # Test 1: Artist Search
    print("\n[1/4] Testing Artist Search...")
    artists = spotify_integration.search_artists("Drake", limit=5)
    
    if artists:
        print(f"✅ Found {len(artists)} artists")
        artist = artists[0]
        print(f"   Selected: {artist['name']}")
        print(f"   Popularity: {artist['popularity']}")
        print(f"   Followers: {artist['followers']:,}")
    else:
        print("❌ No artists found")
        return False
    
    # Test 2: Track Search
    print("\n[2/4] Testing Track Search...")
    tracks = spotify_integration.search_tracks(artist['name'], artist_id=artist['id'], limit=10)
    
    if tracks:
        print(f"✅ Found {len(tracks)} tracks")
        for i, track in enumerate(tracks[:3], 1):
            print(f"   {i}. {track['name']}")
    else:
        print("❌ No tracks found")
        return False
    
    # Test 3: Card Stats Generation
    print("\n[3/4] Testing Card Stats Generation...")
    stats = spotify_integration.generate_card_stats(artist)
    rarity = spotify_integration.determine_rarity(artist)
    
    print(f"✅ Generated stats for {artist['name']}")
    print(f"   Rarity: {rarity}")
    print(f"   Impact: {stats['impact']}")
    print(f"   Skill: {stats['skill']}")
    print(f"   Longevity: {stats['longevity']}")
    print(f"   Culture: {stats['culture']}")
    print(f"   Hype: {stats['hype']}")
    
    # Test 4: Database Pack Creation
    print("\n[4/4] Testing Database Pack Creation...")
    db = DatabaseManager()
    
    pack_id = db.create_creator_pack(
        creator_id=123456789,
        name="Test Drake Pack",
        description=f"Test pack featuring {artist['name']}",
        pack_size=len(tracks)
    )
    
    if pack_id:
        print(f"✅ Pack created: {pack_id}")
        
        # Create cards for pack
        cards_created = 0
        for track in tracks:
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
                cards_created += 1
        
        print(f"✅ Created {cards_created}/{len(tracks)} cards")
        
        # Show pack summary
        print("\n" + "="*70)
        print("PACK CREATION SUMMARY")
        print("="*70)
        print(f"Pack ID: {pack_id}")
        print(f"Artist: {artist['name']}")
        print(f"Cards: {cards_created}")
        print(f"Rarity: {rarity}")
        print(f"Average Power: {sum(stats.values()) / len(stats):.1f}")
        print("\nSample Cards:")
        for i, track in enumerate(tracks[:5], 1):
            print(f"  {i}. {track['name']} ({rarity})")
        
        if len(tracks) > 5:
            print(f"  ...and {len(tracks) - 5} more")
        
        print("\n✅ PACK CREATION WORKFLOW COMPLETE!")
        return True
    else:
        print("❌ Failed to create pack")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pack_creation())
    exit(0 if success else 1)
