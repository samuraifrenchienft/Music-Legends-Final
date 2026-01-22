# test_creator_preview.py
# Test script for creator pack preview system

import sys
sys.path.append('.')

from services.creator_preview import creator_preview, build_preview
from models.creator_pack import CreatorPack
from models.artist import Artist

def test_preview_builder():
    """Test preview builder functionality"""
    print("🎨 Testing Preview Builder")
    print("==========================")
    
    # Mock pack for testing
    class MockPack:
        def __init__(self, pack_id):
            self.id = pack_id
            self.name = "Rock Legends Pack"
            self.genre = "Rock"
            self.status = "pending"
            self.payment_status = "authorized"
            self.price_cents = 999
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.owner_id = 123456789
            self.created_at = "2024-01-20T12:00:00"
            self.reviewed_at = None
            self.reviewed_by = None
            self.notes = ""
            self.rejection_reason = ""
    
    # Mock artists for testing
    class MockArtist:
        def __init__(self, artist_id, name, genre, popularity, subscribers, views):
            self.id = artist_id
            self.name = name
            self.genre = genre
            self.popularity = popularity
            self.subscribers = subscribers
            self.view_count = views
            self.video_count = 100
            self.channel_id = f"UC{artist_id}"
            self.image_url = f"https://example.com/{artist_id}.jpg"
            self.description = f"Description for {name}"
    
    # Test successful preview build
    print("\n1. Testing successful preview build...")
    
    # Temporarily replace model methods
    original_get_by_id = CreatorPack.get_by_id
    original_where_in = Artist.where_in
    
    CreatorPack.get_by_id = lambda pack_id: MockPack(pack_id)
    Artist.where_in = lambda field, ids: [
        MockArtist("artist_1", "Queen", "Rock", 95, 1000000, 1000000000),
        MockArtist("artist_2", "Led Zeppelin", "Rock", 90, 800000, 800000000),
        MockArtist("artist_3", "The Beatles", "Rock", 98, 2000000, 2000000000)
    ]
    
    try:
        preview = creator_preview.build_preview("pack_123")
        
        if preview:
            print("✅ Preview built successfully")
            print(f"   Pack Name: {preview['name']}")
            print(f"   Genre: {preview['genre']}")
            print(f"   Status: {preview['status']}")
            print(f"   Payment Status: {preview['payment_status']}")
            print(f"   Price: ${preview['price_dollars']:.2f}")
            print(f"   Artist Count: {preview['artist_count']}")
            print(f"   Quality Score: {preview['quality_score']}")
            print(f"   Quality Rating: {preview['quality_rating']}")
            print(f"   Has YouTube Data: {preview['has_youtube_data']}")
            
            # Check tier distribution
            tier_dist = preview['tier_distribution']
            print(f"   Tier Distribution: {tier_dist}")
            
            # Check artists
            artists = preview['artists']
            print(f"   Artists: {len(artists)}")
            for artist in artists:
                print(f"      • {artist['name']} ({artist['estimated_tier']}) - Popularity: {artist['popularity']}")
            
            # Check statistics
            print(f"   Avg Popularity: {preview['avg_popularity']}")
            print(f"   Total Subscribers: {preview['total_subscribers']:,}")
            print(f"   Total Views: {preview['total_views']:,}")
            
        else:
            print("❌ Failed to build preview")
            
    except Exception as e:
        print(f"❌ Error building preview: {e}")
    finally:
        # Restore original methods
        CreatorPack.get_by_id = original_get_by_id
        Artist.where_in = original_where_in
    
    # Test preview with missing pack
    print("\n2. Testing preview with missing pack...")
    
    CreatorPack.get_by_id = lambda pack_id: None
    
    try:
        preview = creator_preview.build_preview("nonexistent_pack")
        
        if preview is None:
            print("✅ Missing pack correctly handled")
        else:
            print("❌ Missing pack should return None")
            
    except Exception as e:
        print(f"❌ Error handling missing pack: {e}")
    finally:
        CreatorPack.get_by_id = original_get_by_id

def test_quality_score_calculation():
    """Test quality score calculation"""
    print("\n⭐ Testing Quality Score Calculation")
    print("===================================")
    
    # Test excellent pack
    print("\n1. Testing excellent pack...")
    
    tier_dist = {
        "legendary": 2,
        "platinum": 3,
        "gold": 2,
        "silver": 1,
        "bronze": 0,
        "community": 0
    }
    
    score = creator_preview._calculate_quality_score(tier_dist, 8, 85)
    print(f"✅ Excellent pack score: {score}")
    
    # Test good pack
    print("\n2. Testing good pack...")
    
    tier_dist = {
        "legendary": 1,
        "platinum": 2,
        "gold": 3,
        "silver": 2,
        "bronze": 1,
        "community": 0
    }
    
    score = creator_preview._calculate_quality_score(tier_dist, 9, 70)
    print(f"✅ Good pack score: {score}")
    
    # Test poor pack
    print("\n3. Testing poor pack...")
    
    tier_dist = {
        "legendary": 0,
        "platinum": 0,
        "gold": 1,
        "silver": 2,
        "bronze": 3,
        "community": 4
    }
    
    score = creator_preview._calculate_quality_score(tier_dist, 10, 30)
    print(f"✅ Poor pack score: {score}")
    
    # Test quality rating
    print("\n4. Testing quality rating...")
    
    ratings = [
        (95, "Excellent"),
        (75, "Good"),
        (50, "Fair"),
        (25, "Poor"),
        (10, "Very Poor")
    ]
    
    for score, expected_rating in ratings:
        rating = creator_preview._get_quality_rating(score)
        if rating == expected_rating:
            print(f"✅ Score {score} → {rating}")
        else:
            print(f"❌ Score {score} → Expected {expected_rating}, got {rating}")

def test_youtube_images():
    """Test YouTube image retrieval"""
    print("\n📺 Testing YouTube Images")
    print("========================")
    
    # Mock artists
    class MockArtist:
        def __init__(self, artist_id, image_url, channel_id):
            self.id = artist_id
            self.image_url = image_url
            self.channel_id = channel_id
    
    # Test with various image scenarios
    artists = [
        MockArtist("artist_1", "https://example.com/image1.jpg", "UC123"),
        MockArtist("artist_2", None, "UC456"),
        MockArtist("artist_3", None, None)
    ]
    
    images = creator_preview._get_youtube_images(artists)
    
    print(f"✅ Generated {len(images)} image mappings:")
    for artist_id, image_url in images.items():
        print(f"   {artist_id}: {image_url}")

def test_comparison_preview():
    """Test comparison preview functionality"""
    print("\n📊 Testing Comparison Preview")
    print("=============================")
    
    # Mock multiple packs
    class MockPack:
        def __init__(self, pack_id, name, quality_score, price):
            self.id = pack_id
            self.name = name
            self.genre = "Rock"
            self.status = "pending"
            self.payment_status = "authorized"
            self.price_cents = price
            self.artist_ids = [f"artist_{i}" for i in range(5)]
            self.owner_id = 123456789
            self.created_at = "2024-01-20T12:00:00"
            self.reviewed_at = None
            self.reviewed_by = None
            self.notes = ""
            self.rejection_reason = ""
    
    # Temporarily replace methods
    original_get_by_id = CreatorPack.get_by_id
    original_build_preview = creator_preview.build_preview
    
    def mock_build_preview(pack_id):
        pack_data = {
            "pack_123": {"name": "Excellent Pack", "quality_score": 85, "price_cents": 999},
            "pack_456": {"name": "Good Pack", "quality_score": 70, "price_cents": 1499},
            "pack_789": {"name": "Fair Pack", "quality_score": 50, "price_cents": 799}
        }
        
        data = pack_data.get(pack_id, {})
        if not data:
            return None
        
        return {
            "pack_id": pack_id,
            "name": data["name"],
            "quality_score": data["quality_score"],
            "price_cents": data["price_cents"],
            "price_dollars": data["price_cents"] / 100,
            "artist_count": 5,
            "preview_generated_at": "2024-01-20T12:00:00"
        }
    
    creator_preview.build_preview = mock_build_preview
    
    try:
        comparison = creator_preview.build_comparison_preview(["pack_123", "pack_456", "pack_789"])
        
        if comparison:
            print("✅ Comparison preview built successfully")
            print(f"   Pack Count: {comparison['pack_count']}")
            print(f"   Avg Quality Score: {comparison['avg_quality_score']:.1f}")
            print(f"   Avg Price: ${comparison['avg_price'] / 100:.2f}")
            print(f"   Total Artists: {comparison['total_artists']}")
            
            best_pack = comparison['best_quality_pack']
            print(f"   Best Quality: {best_pack['name']} ({best_pack['quality_score']})")
            
            most_expensive = comparison['most_expensive_pack']
            print(f"   Most Expensive: {most_expensive['name']} (${most_expensive['price_dollars']:.2f})")
        else:
            print("❌ Failed to build comparison preview")
            
    except Exception as e:
        print(f"❌ Error building comparison preview: {e}")
    finally:
        # Restore original methods
        creator_preview.build_preview = original_build_preview

def test_preview_summary():
    """Test preview summary functionality"""
    print("\n📋 Testing Preview Summary")
    print("=========================")
    
    # Mock full preview
    mock_preview = {
        "pack_id": "pack_123",
        "name": "Test Pack",
        "genre": "Rock",
        "status": "pending",
        "payment_status": "authorized",
        "price_dollars": 9.99,
        "artist_count": 5,
        "quality_score": 75.5,
        "quality_rating": "Good",
        "tier_distribution": {
            "legendary": 1,
            "platinum": 2,
            "gold": 2,
            "silver": 0,
            "bronze": 0,
            "community": 0
        },
        "has_youtube_data": True,
        "preview_generated_at": "2024-01-20T12:00:00"
    }
    
    # Temporarily replace build_preview
    original_build_preview = creator_preview.build_preview
    creator_preview.build_preview = lambda pack_id: mock_preview
    
    try:
        summary = creator_preview.get_preview_summary("pack_123")
        
        if summary:
            print("✅ Summary built successfully")
            print(f"   Name: {summary['name']}")
            print(f"   Genre: {summary['genre']}")
            print(f"   Status: {summary['status']}")
            print(f"   Payment: {summary['payment_status']}")
            print(f"   Price: ${summary['price_dollars']:.2f}")
            print(f"   Artists: {summary['artist_count']}")
            print(f"   Quality: {summary['quality_score']}/100 ({summary['quality_rating']})")
            print(f"   Top Tiers: {summary['top_tiers']}")
            print(f"   YouTube Data: {summary['has_youtube_data']}")
        else:
            print("❌ Failed to build summary")
            
    except Exception as e:
        print(f"❌ Error building summary: {e}")
    finally:
        creator_preview.build_preview = original_build_preview

def test_admin_view_requirements():
    """Test admin view requirements"""
    print("\n👨‍💼 Testing Admin View Requirements")
    print("===================================")
    
    requirements = {
        "pack_name": False,
        "genre": False,
        "artist_roster": False,
        "youtube_images": False,
        "estimated_tiers": False,
        "payment_status": False
    }
    
    # Mock preview with all required fields
    class MockPack:
        def __init__(self, pack_id):
            self.id = pack_id
            self.name = "Test Pack"
            self.genre = "Rock"
            self.status = "pending"
            self.payment_status = "authorized"
            self.price_cents = 999
            self.artist_ids = ["artist_1", "artist_2"]
            self.owner_id = 123456789
            self.created_at = "2024-01-20T12:00:00"
            self.reviewed_at = None
            self.reviewed_by = None
            self.notes = ""
            self.rejection_reason = ""
    
    class MockArtist:
        def __init__(self, artist_id, name, image_url):
            self.id = artist_id
            self.name = name
            self.genre = "Rock"
            self.popularity = 75
            self.subscribers = 500000
            self.view_count = 100000000
            self.video_count = 100
            self.channel_id = f"UC{artist_id}"
            self.image_url = image_url
            self.description = f"Description for {name}"
    
    # Temporarily replace methods
    original_get_by_id = CreatorPack.get_by_id
    original_where_in = Artist.where_in
    
    CreatorPack.get_by_id = lambda pack_id: MockPack(pack_id)
    Artist.where_in = lambda field, ids: [
        MockArtist("artist_1", "Queen", "https://example.com/queen.jpg"),
        MockArtist("artist_2", "Led Zeppelin", "https://example.com/led.jpg")
    ]
    
    try:
        preview = creator_preview.build_preview("pack_123")
        
        if preview:
            print("✅ Preview built with admin requirements")
            
            # Check each requirement
            if preview.get('name'):
                requirements["pack_name"] = True
                print("✅ Pack name included")
            
            if preview.get('genre'):
                requirements["genre"] = True
                print("✅ Genre included")
            
            if preview.get('artists') and len(preview['artists']) > 0:
                requirements["artist_roster"] = True
                print("✅ Artist roster included")
            
            if preview.get('youtube_images'):
                requirements["youtube_images"] = True
                print("✅ YouTube images included")
            
            if any(artist.get('estimated_tier') for artist in preview.get('artists', [])):
                requirements["estimated_tiers"] = True
                print("✅ Estimated tiers included")
            
            if preview.get('payment_status'):
                requirements["payment_status"] = True
                print("✅ Payment status included")
        else:
            print("❌ Failed to build preview")
            
    except Exception as e:
        print(f"❌ Error testing admin requirements: {e}")
    finally:
        # Restore original methods
        CreatorPack.get_by_id = original_get_by_id
        Artist.where_in = original_where_in
    
    # Summary
    print("\n📊 Admin Requirements Summary:")
    passed = sum(requirements.values())
    total = len(requirements)
    
    for requirement, result in requirements.items():
        status = "✅" if result else "❌"
        print(f"   {status} {requirement}")
    
    print(f"\n📈 Overall: {passed}/{total} requirements met")

def main():
    """Run all tests"""
    print("🎨 Creator Pack Preview Test Suite")
    print("================================")
    
    try:
        test_preview_builder()
        test_quality_score_calculation()
        test_youtube_images()
        test_comparison_preview()
        test_preview_summary()
        test_admin_view_requirements()
        
        print("\n🎉 Preview System Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
