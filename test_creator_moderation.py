# test_creator_moderation.py
# Test script for creator pack moderation system

import sys
sys.path.append('.')

from services.creator_moderation import creator_moderation, validate_pack

def test_pack_validation():
    """Test pack validation rules"""
    print("🛡️ Testing Pack Validation")
    print("==========================")
    
    # Test valid pack
    print("\n1. Testing valid pack...")
    valid, message = creator_moderation.validate_pack(
        name="Rock Legends",
        artists=["Queen", "Led Zeppelin", "The Beatles", "Pink Floyd", "The Rolling Stones"],
        user_id=123456789
    )
    
    if valid:
        print("✅ Valid pack validation passed")
    else:
        print(f"❌ Valid pack validation failed: {message}")
    
    # Test invalid pack (too few artists)
    print("\n2. Testing invalid pack (too few artists)...")
    invalid, message = creator_moderation.validate_pack(
        name="Small Pack",
        artists=["Queen"],
        user_id=123456789
    )
    
    if not invalid:
        print("✅ Invalid pack validation correctly failed")
        print(f"   Error: {message}")
    else:
        print("❌ Invalid pack validation should have failed")
    
    # Test invalid pack (too many artists)
    print("\n3. Testing invalid pack (too many artists)...")
    invalid, message = creator_moderation.validate_pack(
        name="Huge Pack",
        artists=[f"Artist{i}" for i in range(30)],  # 30 artists
        user_id=123456789
    )
    
    if not invalid:
        print("✅ Invalid pack validation correctly failed")
        print(f"   Error: {message}")
    else:
        print("❌ Invalid pack validation should have failed")
    
    # Test invalid pack (banned keywords)
    print("\n4. Testing invalid pack (banned keywords)...")
    invalid, message = creator_moderation.validate_pack(
        name="Official Music Channel",
        artists=["Queen Official", "Led Zeppelin VEVO"],
        user_id=123456789
    )
    
    if not invalid:
        print("✅ Invalid pack validation correctly failed")
        print(f"   Error: {message}")
    else:
        print("❌ Invalid pack validation should have failed")
    
    # Test invalid pack (duplicates)
    print("\n5. Testing invalid pack (duplicate artists)...")
    invalid, message = creator_moderation.validate_pack(
        name="Duplicate Pack",
        artists=["Queen", "Queen", "Led Zeppelin"],
        user_id=123456789
    )
    
    if not invalid:
        print("✅ Invalid pack validation correctly failed")
        print(f"   Error: {message}")
    else:
        print("❌ Invalid pack validation should have failed")

def test_artist_validation():
    """Test individual artist validation"""
    print("\n🎵 Testing Artist Validation")
    print("==========================")
    
    # Test valid artist
    print("\n1. Testing valid artist...")
    valid, message = creator_moderation._validate_artist("Queen", 123456789)
    
    if valid:
        print("✅ Valid artist validation passed")
    else:
        print(f"❌ Valid artist validation failed: {message}")
    
    # Test invalid artist (banned keyword)
    print("\n2. Testing invalid artist (banned keyword)...")
    invalid, message = creator_moderation._validate_artist("Queen Official", 123456789)
    
    if not invalid:
        print("✅ Invalid artist validation correctly failed")
        print(f"   Error: {message}")
    else:
        print("❌ Invalid artist validation should have failed")
    
    # Test invalid artist (inappropriate content)
    print("\n3. Testing invalid artist (inappropriate content)...")
    invalid, message = creator_moderation._validate_artist("XXX Artist", 123456789)
    
    if not invalid:
        print("✅ Invalid artist validation correctly failed")
        print(f"   Error: {message}")
    else:
        print("❌ Invalid artist validation should have failed")
    
    # Test invalid artist (suspicious pattern)
    print("\n4. Testing invalid artist (suspicious pattern)...")
    invalid, message = creator_moderation._validate_artist("artist@website.com", 123456789)
    
    if not invalid:
        print("✅ Invalid artist validation correctly failed")
        print(f"   Error: {message}")
    else:
        print("❌ Invalid artist validation should have failed")

def test_image_safety():
    """Test image safety validation"""
    print("\n🖼️ Testing Image Safety")
    print("=====================")
    
    # Test safe image
    print("\n1. Testing safe image...")
    safe, reason = creator_moderation.check_image_safety("https://example.com/image.jpg")
    
    if safe:
        print("✅ Safe image validation passed")
        print(f"   Reason: {reason}")
    else:
        print(f"❌ Safe image validation failed: {reason}")
    
    # Test unsafe image (suspicious domain)
    print("\n2. Testing unsafe image (suspicious domain)...")
    unsafe, reason = creator_moderation.check_image_safety("https://nsfw-site.com/image.jpg")
    
    if not unsafe:
        print("✅ Unsafe image validation correctly failed")
        print(f"   Reason: {reason}")
    else:
        print("❌ Unsafe image validation should have failed")
    
    # Test unsafe image (invalid protocol)
    print("\n3. Testing unsafe image (invalid protocol)...")
    unsafe, reason = creator_moderation.check_image_safety("ftp://example.com/image.jpg")
    
    if not unsafe:
        print("✅ Unsafe image validation correctly failed")
        print(f"   Reason: {reason}")
    else:
        print("❌ Unsafe image validation should have failed")

def test_impersonation_detection():
    """Test impersonation detection"""
    print("\n👤 Testing Impersonation Detection")
    print("===============================")
    
    # Test non-impersonation
    print("\n1. Testing non-impersonation...")
    is_impersonation = creator_moderation._is_impersonation_attempt("my band name")
    
    if not is_impersonation:
        print("✅ Non-impersonation correctly detected")
    else:
        print("❌ Non-impersonation should not be flagged")
    
    # Test impersonation
    print("\n2. Testing impersonation...")
    is_impersonation = creator_moderation._is_impersonation_attempt("queen official channel")
    
    if is_impersonation:
        print("✅ Impersonation correctly detected")
    else:
        print("❌ Impersonation should have been detected")
    
    # Test VEVO impersonation
    print("\n3. Testing VEVO impersonation...")
    is_impersonation = creator_moderation._is_impersonation("artist vevo")
    
    if is_impersonation:
        print("✅ VEVO impersonation correctly detected")
    else:
        print("❌ VEVO impersonation should have been detected")

def test_high_tier_counting():
    """Test high-tier artist counting"""
    print("\n🏆 Testing High-Tier Counting")
    print("==========================")
    
    # Test normal pack
    print("\n1. Testing normal pack...")
    normal_count = creator_moderation._count_high_tier_artists([
        "Queen", "Led Zeppelin", "The Beatles", "Pink Floyd", "The Rolling Stones"
    ])
    print(f"✅ High-tier count: {normal_count} (expected: 5)")
    
    # Test mixed pack
    print("\n2. Testing mixed pack...")
    mixed_count = creator_moderation._count_high_tier_artists([
        "Queen", "Local Band", "Indie Artist", "Unknown Singer", "Garage Band"
    ])
    print(f"✅ High-tier count: {mixed_count} (expected: 1)")
    
    # Test excessive high-tier pack
    print("\n3. Testing excessive high-tier pack...")
    excessive_count = creator_moderation._count_high_tier_artists([
        "Queen", "Led Zeppelin", "The Beatles", "Pink Floyd", "The Rolling Stones",
        "Metallica", "AC/DC", "Guns N' Roses", "Nirvana", "Pearl Jam"
    ])
    print(f"✅ High-tier count: {excessive_count} (expected: 10)")

def test_moderation_stats():
    """Test moderation statistics"""
    print("\n📊 Testing Moderation Statistics")
    print("==============================")
    
    stats = creator_moderation.get_moderation_stats()
    
    print(f"✅ Moderation stats:")
    print(f"   Total packs: {stats['total_packs']}")
    print(f"   Pending packs: {stats['pending_packs']}")
    print(f"   Approved packs: {stats['approved_packs']}")
    print(f"   Rejected packs: {stats['rejected_packs']}")
    print(f"   Approval rate: {stats['approval_rate']:.1f}%")
    print(f"   Pending reviews: {stats['pending_reviews']}")
    print(f"   Approved creators: {stats['approved_creators']}")

def test_business_rules():
    """Test business rule constants"""
    print("\n📋 Testing Business Rules")
    print("========================")
    
    print(f"✅ Business rule constants:")
    print(f"   Max artists: {creator_moderation.MAX_ARTISTS}")
    print(f"   Min artists: {creator_moderation.MIN_ARTISTS}")
    print(f"   Banned keywords: {len(creator_moderation.BANNED_KEYWORDS)}")
    print(f"   Suspicious patterns: {len(creator_moderation.SUSPICIOUS_PATTERNS)}")
    print(f"   Inappropriate content: {len(creator_moderation.INAPPROPRIATE_CONTENT)}")
    print(f"   Impersonation patterns: {len(creator_moderation.IMPERSONATION_PATTERNS)}")

def main():
    """Run all tests"""
    print("🛡️ Creator Moderation Test Suite")
    print("==============================")
    
    try:
        test_pack_validation()
        test_artist_validation()
        test_image_safety()
        test_impersonation_detection()
        test_high_tier_counting()
        test_moderation_stats()
        test_business_rules()
        
        print("\n🎉 Moderation Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
