# test_artist_pipeline.py
# Test script for artist pipeline system

import asyncio
import sys
sys.path.append('.')

from services.artist_pipeline import artist_pipeline

async def test_single_artist_import():
    """Test importing a single artist"""
    print("🎵 Testing Single Artist Import")
    print("================================")
    
    # Test with a well-known artist
    artist_name = "Taylor Swift"
    
    print(f"🔍 Importing: {artist_name}")
    card = await artist_pipeline.import_artist_to_card(artist_name)
    
    if card:
        print(f"✅ Successfully imported!")
        print(f"   Card Serial: {card.serial}")
        print(f"   Artist: {card.artist.name}")
        print(f"   Tier: {card.tier}")
        print(f"   Genre: {card.artist.genre}")
        print(f"   Power Level: {card.power_level}")
        print(f"   Stats: {card.stats}")
        print(f"   Abilities: {[a['name'] for a in card.abilities]}")
    else:
        print(f"❌ Failed to import {artist_name}")

async def test_multiple_artist_import():
    """Test importing multiple artists"""
    print("\n🎵 Testing Multiple Artist Import")
    print("=================================")
    
    artists = [
        "Ed Sheeran",
        "Billie Eilish", 
        "Drake",
        "Unknown Artist 12345"  # This should fail
    ]
    
    print(f"🔍 Importing {len(artists)} artists...")
    cards = await artist_pipeline.import_multiple_artists(artists)
    
    print(f"✅ Successfully imported {len(cards)} out of {len(artists)} artists")
    
    for card in cards:
        print(f"   {card.serial} - {card.artist.name} ({card.tier})")

async def test_trending_import():
    """Test importing trending artists"""
    print("\n🔥 Testing Trending Artists Import")
    print("==================================")
    
    print("🔍 Importing trending artists from US...")
    cards = await artist_pipeline.import_trending_artists("US", 3)
    
    print(f"✅ Imported {len(cards)} trending artists")
    
    for card in cards:
        print(f"   {card.serial} - {card.artist.name} ({card.tier})")

async def test_genre_import():
    """Test importing genre-specific artists"""
    print("\n🎼 Testing Genre Artists Import")
    print("==============================")
    
    genres = ["Rock", "Pop", "Hip-Hop"]
    
    for genre in genres:
        print(f"🔍 Importing {genre} artists...")
        cards = await artist_pipeline.import_genre_artists(genre, 2)
        
        print(f"   ✅ Imported {len(cards)} {genre} artists")
        for card in cards:
            print(f"      {card.serial} - {card.artist.name}")

async def test_artist_update():
    """Test updating artist statistics"""
    print("\n📊 Testing Artist Stats Update")
    print("===============================")
    
    # First import an artist
    card = await artist_pipeline.import_artist_to_card("Adele")
    
    if card:
        print(f"🔍 Updating stats for {card.artist.name}...")
        success = await artist_pipeline.update_artist_stats(card.artist.id)
        
        if success:
            print("✅ Artist stats updated successfully")
            print(f"   New popularity: {card.artist.popularity}")
            print(f"   Current tier: {card.artist.tier}")
        else:
            print("❌ Failed to update artist stats")
    else:
        print("❌ Could not import test artist")

async def test_error_handling():
    """Test error handling with invalid inputs"""
    print("\n🧪 Testing Error Handling")
    print("========================")
    
    # Test with non-existent artist
    print("🔍 Testing non-existent artist...")
    card = await artist_pipeline.import_artist_to_card("NonExistentArtist12345")
    
    if card is None:
        print("✅ Correctly handled non-existent artist")
    else:
        print("❌ Should have returned None for non-existent artist")
    
    # Test with empty string
    print("🔍 Testing empty artist name...")
    card = await artist_pipeline.import_artist_to_card("")
    
    if card is None:
        print("✅ Correctly handled empty artist name")
    else:
        print("❌ Should have returned None for empty artist name")

async def test_card_generation():
    """Test card generation features"""
    print("\n🃏 Testing Card Generation")
    print("==========================")
    
    # Import an artist to test card features
    card = await artist_pipeline.import_artist_to_card("Bruno Mars")
    
    if card:
        print(f"✅ Generated card: {card.serial}")
        print(f"   📊 Stats:")
        for stat, value in card.stats.items():
            print(f"      {stat.title()}: {value}")
        
        print(f"   ⚡ Abilities:")
        for ability in card.abilities:
            print(f"      {ability['name']}: {ability['description']}")
        
        print(f"   🎯 Rarity Score: {card.rarity_score}")
        print(f"   💪 Power Level: {card.power_level}")
        print(f"   🎨 Card Type: {card.card_type}")
    else:
        print("❌ Failed to import test artist")

async def test_pipeline_performance():
    """Test pipeline performance with multiple operations"""
    print("\n⚡ Testing Pipeline Performance")
    print("===============================")
    
    import time
    
    # Measure time for batch import
    start_time = time.time()
    
    artists = ["The Weeknd", "Ariana Grande", "Post Malone", "Dua Lipa", "Olivia Rodrigo"]
    cards = await artist_pipeline.import_multiple_artists(artists)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Imported {len(cards)} artists in {duration:.2f} seconds")
    print(f"   Average: {duration/len(artists):.2f} seconds per artist")
    
    # Test concurrent operations
    start_time = time.time()
    
    tasks = [
        artist_pipeline.import_artist_to_card("Sia"),
        artist_pipeline.import_artist_to_card("Coldplay"),
        artist_pipeline.import_artist_to_card("Maroon 5")
    ]
    
    results = await asyncio.gather(*tasks)
    successful_cards = [card for card in results if card is not None]
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✅ Concurrent import: {len(successful_cards)} cards in {duration:.2f} seconds")

async def main():
    """Run all tests"""
    print("🎵 Artist Pipeline Test Suite")
    print("============================")
    
    try:
        await test_single_artist_import()
        await test_multiple_artist_import()
        await test_trending_import()
        await test_genre_import()
        await test_artist_update()
        await test_error_handling()
        await test_card_generation()
        await test_pipeline_performance()
        
        print("\n🎉 Artist Pipeline Testing Complete!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
