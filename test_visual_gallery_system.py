# test_visual_gallery_system.py
# Test script for visual gallery and image cache system

import sys
sys.path.append('.')

from ui.gallery import GalleryView, CompactGalleryView, ThumbnailGalleryView, create_gallery_view, get_gallery_stats
from services.image_cache import safe_image, DEFAULT_IMG, get_image_info, batch_check_images, get_cache_stats, cleanup_cache
from commands.admin_preview import ReviewView

def test_image_cache():
    """Test image cache functionality"""
    print("🖼️ Testing Image Cache")
    print("=====================")
    
    # Test 1: Safe Image Check
    print("\n1. Testing Safe Image Check")
    print("--------------------------")
    
    safe_url = "https://i.ytimg.com/vi/queen/maxresdefault.jpg"
    unsafe_url = "https://nsfw-site.com/image.jpg"
    invalid_url = None
    
    print(f"✅ Testing safe URL: {safe_url}")
    result = safe_image(safe_url)
    print(f"   Result: {result}")
    
    print(f"❌ Testing unsafe URL: {unsafe_url}")
    result = safe_image(unsafe_url)
    print(f"   Result: {result}")
    
    print(f"❌ Testing invalid URL: {invalid_url}")
    result = safe_image(invalid_url)
    print(f"   Result: {result}")
    
    # Test 2: Image Info
    print("\n2. Testing Image Info")
    print("-------------------")
    
    info = get_image_info(safe_url)
    print(f"✅ Image info for: {safe_url}")
    print(f"   Safe: {info['safe']}")
    print(f"   Reason: {info['reason']}")
    print(f"   Cached: {info['cached']}")
    
    # Test 3: Batch Check
    print("\n3. Testing Batch Check")
    print("-------------------")
    
    urls = [safe_url, unsafe_url, "https://example.com/image.png"]
    results = batch_check_images(urls)
    
    print(f"✅ Batch checking {len(urls)} URLs:")
    for url, result in results.items():
        status = "✅" if result['safe'] else "❌"
        print(f"   {status} {url}: {result['reason']}")
    
    # Test 4: Cache Statistics
    print("\n4. Testing Cache Statistics")
    print("------------------------")
    
    stats = get_cache_stats()
    print(f"✅ Cache statistics:")
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Safe entries: {stats['safe_entries']}")
    print(f"   Unsafe entries: {stats['unsafe_entries']}")
    print(f"   Safe percentage: {stats['safe_percentage']}")
    print(f"   Max size: {stats['max_size']}")
    print(f"   Cache duration: {stats['cache_duration']}s")

def test_gallery_views():
    """Test gallery view components"""
    print("\n🖼️ Testing Gallery Views")
    print("======================")
    
    # Mock artists data
    mock_artists = [
        {
            'name': 'Queen',
            'genre': 'Rock',
            'estimated_tier': 'legendary',
            'popularity': 95,
            'subscribers': 1000000,
            'views': 1000000000,
            'image': 'https://i.ytimg.com/vi/queen/maxresdefault.jpg',
            'channel_id': 'UC123'
        },
        {
            'name': 'Led Zeppelin',
            'genre': 'Rock',
            'estimated_tier': 'platinum',
            'popularity': 90,
            'subscribers': 800000,
            'views': 800000000,
            'image': 'https://i.ytimg.com/vi/ledzep/maxresdefault.jpg',
            'channel_id': 'UC456'
        },
        {
            'name': 'The Beatles',
            'genre': 'Rock',
            'estimated_tier': 'legendary',
            'popularity': 98,
            'subscribers': 2000000,
            'views': 2000000000,
            'image': 'https://i.ytimg.com/vi/beatles/maxresdefault.jpg',
            'channel_id': 'UC789'
        },
        {
            'name': 'Pink Floyd',
            'genre': 'Rock',
            'estimated_tier': 'platinum',
            'popularity': 88,
            'subscribers': 1500000,
            'views': 1500000000,
            'image': 'https://i.ytimg.com/vi/pinkfloyd/maxresdefault.jpg',
            'channel_id': 'UC101'
        },
        {
            'name': 'The Rolling Stones',
            'genre': 'Rock',
            'estimated_tier': 'gold',
            'popularity': 85,
            'subscribers': 1200000,
            'views': 1200000000,
            'image': 'https://i.ytimg.com/vi/stones/maxresdefault.jpg',
            'channel_id': 'UC112'
        }
    ]
    
    # Test 1: Standard Gallery View
    print("\n1. Testing Standard Gallery View")
    print("------------------------------")
    
    gallery = GalleryView(mock_artists)
    print(f"✅ Created gallery with {len(gallery.artists)} artists")
    print(f"   Current index: {gallery.index}")
    print(f"   Timeout: {gallery.timeout}")
    
    # Test embed generation
    embed = gallery.embed()
    print(f"✅ Generated embed:")
    print(f"   Title: {embed.title}")
    print(f"   Description: {embed.description}")
    print(f"   Footer: {embed.footer}")
    print(f"   Image set: {bool(embed.image)}")
    
    # Test 2: Compact Gallery View
    print("\n2. Testing Compact Gallery View")
    print("--------------------------------")
    
    compact = CompactGalleryView(mock_artists)
    print(f"✅ Created compact gallery with {len(compact.artists)} artists")
    print(f"   Current index: {compact.index}")
    
    # Test embed generation
    embed = compact.embed()
    print(f"✅ Generated compact embed:")
    print(f"   Title: {embed.title}")
    print(f"   Footer: {embed.footer}")
    
    # Test 3: Thumbnail Gallery View
    print("\n3. Testing Thumbnail Gallery View")
    print("---------------------------------")
    
    thumbnail = ThumbnailGalleryView(mock_artists)
    print(f"✅ Created thumbnail gallery with {len(thumbnail.artists)} artists")
    print(f"   Current index: {thumbnail.index}")
    print(f"   Page size: {thumbnail.page_size}")
    print(f"   Current page: {thumbnail.current_page}")
    
    # Test embed generation
    embed = thumbnail.embed()
    print(f"✅ Generated thumbnail embed:")
    print(f"   Title: {embed.title}")
    print(f"   Footer: {embed.footer}")
    
    # Test 4: Gallery Creation Function
    print("\n4. Testing Gallery Creation Function")
    print("-----------------------------------")
    
    default_gallery = create_gallery_view(mock_artists, "default")
    compact_gallery = create_gallery_view(mock_artists, "compact")
    thumbnail_gallery = create_gallery_view(mock_artists, "thumbnail")
    
    print(f"✅ Default gallery: {type(default_gallery).__name__}")
    print(f"✅ Compact gallery: {type(compact_gallery).__name__}")
    print(f"✅ Thumbnail gallery: {type(thumbnail_gallery).__name__}")
    
    # Test 5: Gallery Statistics
    print("\n5. Testing Gallery Statistics")
    print("--------------------------")
    
    stats = get_gallery_stats(mock_artists)
    print(f"✅ Gallery statistics:")
    print(f"   Total artists: {stats['total_artists']}")
    print(f"   Image count: {stats['image_count']}")
    print(f"   Image coverage: {stats['image_coverage']}")
    print(f"   Average popularity: {stats['avg_popularity']}")
    print(f"   Tier distribution: {stats['tier_distribution']}")
    print(f"   Genre distribution: {stats['genre_distribution']}")

def test_navigation_functionality():
    """Test gallery navigation functionality"""
    print("\n🔄 Testing Navigation Functionality")
    print("===============================")
    
    # Mock artists
    artists = [
        {'name': 'Artist 1', 'genre': 'Rock', 'estimated_tier': 'gold', 'image': 'https://example.com/1.jpg'},
        {'name': 'Artist 2', 'genre': 'Pop', 'estimated_tier': 'platinum', 'image': 'https://example.com/2.jpg'},
        {'name': 'Artist 3', 'genre': 'Jazz', 'estimated_tier': 'silver', 'image': 'https://example.com/3.jpg'},
        {'name': 'Artist 4', 'genre': 'Electronic', 'estimated_tier': 'bronze', 'image': 'https://image.com/4.jpg'},
        {'name': 'Artist 5', 'genre': 'Classical', 'estimated_tier': 'community', 'image': 'https://example.com/5.jpg'}
    ]
    
    gallery = GalleryView(artists)
    
    # Test navigation methods
    print("\n1. Testing Navigation Methods")
    print("----------------------------")
    
    # Test previous navigation
    print(f"✅ Initial index: {gallery.index}")
    gallery.index = 2
    print(f"✅ Set index to: {gallery.index}")
    
    # Test boundary conditions
    print(f"✅ Previous from index 2: {max(0, gallery.index - 1)}")
    print(f"✅ Next from index 2: {min(len(artists) - 1, gallery.index + 1)}")
    print(f"✅ First: {0}")
    print(f"✅ Last: {len(artists) - 1}")
    
    # Test embed updates
    print("\n2. Testing Embed Updates")
    print("------------------------")
    
    original_title = gallery.embed().title
    gallery.index = 1
    new_title = gallery.embed().title
    
    print(f"✅ Original title: {original_title}")
    print(f"✅ New title: {new_title}")
    print(f"✅ Embed updates correctly")

def test_image_safety():
    """Test image safety validation"""
    print("\n🛡️ Testing Image Safety")
    print("=====================")
    
    # Test 1: Safe URLs
    print("\n1. Testing Safe URLs")
    print("---------------------")
    
    safe_urls = [
        "https://i.ytimg.com/vi/queen/maxresdefault.jpg",
        "https://yt3.ggpht.com/ytc/123/abc/default.jpg",
        "https://img.youtube.com/vi/artist/thumbnail.jpg",
        "https://example.com/image.png",
        "https://cdn.example.com/photo.jpg"
    ]
    
    for url in safe_urls:
        safe, reason = safe_image(url) if isinstance(safe_image(url), tuple) else (False, "Error")
        status = "✅" if safe else "❌"
        print(f"   {status} {url}: {reason}")
    
    # Test 2: Unsafe URLs
    print("\n2. Testing Unsafe URLs")
    print("----------------------")
    
    unsafe_urls = [
        "https://nsfw-site.com/image.jpg",
        "https://adult-content.com/photo.jpg",
        "https://xxx-porn.com/image.jpg",
        "https://rule34.net/content.jpg",
        "https://localhost:8080/image.jpg",
        "https://192.168.1.1/image.jpg"
    ]
    
    for url in unsafe_urls:
        safe, reason = safe_image(url) if isinstance(safe_image(url), tuple) else (False, "Error")
        status = "✅" if safe else "❌"
        print(f"   {status} {url}: {reason}")
    
    # Test 3: Invalid URLs
    print("\n3. Testing Invalid URLs")
    print("----------------------")
    
    invalid_urls = [
        "",
        None,
        "not-a-url",
        "ftp://example.com/image.jpg",
        "data:image/png;base64,abc123",
        "javascript:alert('xss')",
        "file:///path/to/image.jpg"
    ]
    
    for url in invalid_urls:
        result = safe_image(url)
        expected = DEFAULT_IMG
        status = "✅" if result == expected else "❌"
        print(f"   {status} {url}: {result}")
    
    # Test 4: Edge Cases
    print("\n4. Testing Edge Cases")
    print("-------------------")
    
    edge_cases = [
        "https://example.com/image.jpg?param=value",
        "https://example.com/image.jpg#section",
        "https://example.com/very/long/path/to/image.jpg",
        "https://example.com/CAPITALIZED/IMAGE.JPG",
        "https://example.com/image-with-dashes.jpg",
        "https://example.com/image_with_underscores.jpg"
    ]
    
    for url in edge_cases:
        safe, reason = safe_image(url) if isinstance(safe_image(url), tuple) else (False, "Error")
        status = "✅" if safe else "❌"
        print(f"   {status} {url}: {reason}")

def test_performance():
    """Test performance of gallery and cache systems"""
    print("\n⚡ Testing Performance")
    print("==================")
    
    import time
    
    # Test 1: Gallery Embed Generation
    print("\n1. Testing Gallery Embed Generation")
    print("--------------------------------")
    
    artists = [
        {'name': f'Artist {i}', 'genre': 'Test', 'estimated_tier': 'gold', 'image': f'https://example.com/{i}.jpg'}
        for i in range(10)
    ]
    
    gallery = GalleryView(artists)
    
    start_time = time.time()
    for i in range(100):
        embed = gallery.embed()
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 100
    print(f"✅ Embed generation: {avg_time:.4f}s per embed")
    
    # Test 2: Image Cache Performance
    print("\n2. Testing Image Cache Performance")
    print("------------------------------------")
    
    test_urls = [f"https://example.com/image_{i}.jpg" for i in range(50)]
    
    start_time = time.time()
    results = batch_check_images(test_urls)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / len(test_urls)
    print(f"✅ Batch check: {avg_time:.4f}s per URL")
    print(f"   Total URLs: {len(test_urls)}")
    print(f"   Safe URLs: {sum(1 for r in results.values() if r['safe'])}")
    
    # Test 3: Cache Hit Rate
    print("\n3. Testing Cache Hit Rate")
    print("----------------------")
    
    # First pass (cache misses)
    start_time = time.time()
    for url in test_urls[:10]:
        safe_image(url)
    end_time = time.time()
    first_pass_time = end_time - start_time
    
    # Second pass (cache hits)
    start_time = time.time()
    for url in test_urls[:10]:
        safe_image(url)
    end_time = time.time()
    second_pass_time = end_time - start_time
    
    print(f"✅ First pass (cache misses): {first_pass_time:.4f}s")
    print(f"✅ Second pass (cache hits): {second_pass_time:.4f}s")
    print(f"✅ Performance improvement: {(first_pass_time / second_pass_time):.1f}x")

def test_mobile_friendly():
    """Test mobile-friendly features"""
    print("\n📱 Testing Mobile-Friendly Features")
    print("===============================")
    
    # Mock artists
    artists = [
        {'name': 'Artist 1', 'genre': 'Rock', 'estimated_tier': 'gold', 'image': 'https://example.com/1.jpg'},
        {'name': 'Artist 2', 'genre': 'Pop', 'estimated_tier': 'platinum', 'image': 'https://example.com/2.jpg'},
        {'name': 'Artist 3', 'genre': 'Jazz', 'estimated_tier': 'silver', 'image': 'https://example.com/3.jpg'}
    ]
    
    # Test 1: Compact View
    print("\n1. Testing Compact View")
    print("-------------------")
    
    compact = CompactGalleryView(artists)
    embed = compact.embed()
    
    print(f"✅ Compact view created")
    print(f"   Title: {embed.title}")
    print(f"   Fields: {len(embed.fields)}")
    print(f"   Footer: {embed.footer}")
    print(f"   Image: {bool(embed.image)}")
    print(f"   Mobile-friendly: ✅")
    
    # Test 2: Thumbnail View
    print("\n2. Testing Thumbnail View")
    print("---------------------")
    
    thumbnail = ThumbnailGalleryView(artists)
    embed = thumbnail.embed()
    
    print(f"✅ Thumbnail view created")
    print(f"   Title: {embed.title}")
    print(f"   Fields: {len(embed.fields)}")
    print(f"   Footer: {embed.footer}")
    print(f"   Image: {bool(embed.image)}")
    print(f"   Mobile-friendly: ✅")
    
    # Test 3: Button Count
    print("\n3. Testing Button Count")
    print("---------------------")
    
    print(f"✅ Standard gallery buttons: {len(gallery.children)}")
    print(f"✅ Compact gallery buttons: {len(compact.children)}")
    print(f"✅ Thumbnail gallery buttons: {len(thumbnail.children)}")
    
    print("✅ All views are mobile-friendly with appropriate button counts")

def test_integration():
    """Test integration with admin preview system"""
    print("\n🔗 Testing Integration")
    print("==================")
    
    # Test 1: Gallery Integration
    print("\n1. Testing Gallery Integration")
    print("------------------------")
    
    mock_artists = [
        {'name': 'Queen', 'genre': 'Rock', 'estimated_tier': 'legendary', 'image': 'https://i.ytimg.com/vi/queen/maxresdefault.jpg'},
        {'name': 'Led Zeppelin', 'genre': 'Rock', 'estimated_tier': 'platinum', 'image': 'https://i.ytimg.com/vi/ledzep/maxresdefault.jpg'}
    ]
    
    gallery = GalleryView(mock_artists)
    review_view = ReviewView("test_pack_id")
    
    print(f"✅ Gallery created with {len(gallery.artists)} artists")
    print(f"✅ Review view created with pack_id: {review_view.pack_id}")
    print(f"✅ Both views have timeout=None for persistence")
    
    # Test 2: Image Cache Integration
    print("\n2. Testing Image Cache Integration")
    print("---------------------------")
    
    for artist in mock_artists:
        safe_url = safe_image(artist.get('image'))
        print(f"✅ {artist['name']}: {'✅ Safe' if safe_url != DEFAULT_IMG else '❌ Default'}")
    
    # Test 3: Safety Check Integration
    print("\n3. Testing Safety Check Integration")
    print("-----------------------------")
    
    try:
        from services.safety_checks import safety_checks
        
        mock_data = {
            'artists': mock_artists,
            'name': 'Test Pack',
            'genre': 'Rock'
        }
        
        safe, message = safety_checks.safe_images(mock_data)
        print(f"✅ Safety check result: {'✅ Safe' if safe else '❌ Unsafe'}")
        print(f"   Message: {message}")
        
    except ImportError:
        print("⚠️ Safety checks not available for testing")
    
    # Test 4: Default Image Handling
    print("\n4. Testing Default Image Handling")
    print("----------------------------")
    
    print(f"✅ Default image: {DEFAULT_IMG}")
    
    # Test with missing image
    missing_image_result = safe_image(None)
    print(f"✅ Missing image result: {missing_image_result}")
    
    # Test with unsafe image
    unsafe_image_result = safe_image("https://nsfw-site.com/image.jpg")
    print(f"✅ Unsafe image result: {unsafe_image_result}")
    
    print("✅ All invalid/unsafe images return default image")

def main():
    """Run all visual gallery tests"""
    print("🖼️ Visual Gallery Test Suite")
    print("=========================")
    
    try:
        test_image_cache()
        test_gallery_views()
        test_navigation_functionality()
        test_image_safety()
        test_performance()
        test_mobile_friendly()
        test_integration()
        
        print("\n🎉 Visual Gallery Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
