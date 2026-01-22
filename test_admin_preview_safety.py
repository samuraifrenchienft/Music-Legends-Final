# test_admin_preview_safety.py
# Test script for admin preview and safety checks

import sys
sys.path.append('.')

from commands.admin_preview import AdminPreviewCommands
from services.safety_checks import safety_checks, safe_images
from services.moderator_checklist import moderator_checklist
from services.creator_preview import build_preview

def test_admin_preview_command():
    """Test admin preview command functionality"""
    print("👨‍💼 Testing Admin Preview Command")
    print("===================================")
    
    # Mock preview data
    mock_preview = {
        "pack_id": "pack_123",
        "name": "Rock Legends Pack",
        "genre": "Rock",
        "status": "pending",
        "payment_status": "authorized",
        "price_dollars": 9.99,
        "artist_count": 3,
        "quality_score": 75.5,
        "quality_rating": "Good",
        "has_youtube_data": True,
        "artists": [
            {
                "name": "Queen",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/queen/maxresdefault.jpg",
                "estimated_tier": "legendary",
                "popularity": 95,
                "subscribers": 1000000,
                "views": 1000000000
            },
            {
                "name": "Led Zeppelin",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/ledzep/maxresdefault.jpg",
                "estimated_tier": "platinum",
                "popularity": 90,
                "subscribers": 800000,
                "views": 800000000
            },
            {
                "name": "The Beatles",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/beatles/maxresdefault.jpg",
                "estimated_tier": "legendary",
                "popularity": 98,
                "subscribers": 2000000,
                "views": 2000000000
            }
        ],
        "tier_distribution": {
            "legendary": 2,
            "platinum": 1,
            "gold": 0,
            "silver": 0,
            "bronze": 0,
            "community": 0
        },
        "avg_popularity": 94.33,
        "total_subscribers": 3800000,
        "total_views": 3800000000
    }
    
    # Create admin preview commands instance
    commands = AdminPreviewCommands(None)
    
    # Test safe_images function
    print("\n1. Testing safe_images function...")
    
    safe, message = commands._safe_images(mock_preview)
    
    if safe:
        print("✅ All images safe and appropriate")
        print(f"   Message: {message}")
    else:
        print("❌ Image safety issues found")
        print(f"   Message: {message}")
    
    # Test moderation checklist
    print("\n2. Testing moderation checklist...")
    
    checklist_results = commands._run_moderation_checklist(mock_preview)
    
    passed = sum(1 for result in checklist_results.values() if result)
    total = len(checklist_results)
    
    print(f"✅ Checklist results: {passed}/{total} checks passed")
    
    for item, result in checklist_results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {item}")
    
    # Test with problematic data
    print("\n3. Testing with problematic data...")
    
    problematic_preview = {
        "artists": [
            {
                "name": "Queen Official VEVO",
                "genre": "Rock",
                "image": "",  # Missing image
                "estimated_tier": "legendary"
            },
            {
                "name": "Queen",  # Duplicate
                "genre": "Rock",
                "image": "https://example.com/queen.jpg",
                "estimated_tier": "legendary"
            },
            {
                "name": "XXX Artist",  # Inappropriate
                "genre": "Rock",
                "image": "https://nsfw-site.com/image.jpg",  # Unsafe domain
                "estimated_tier": "platinum"
            }
        ]
    }
    
    safe, message = commands._safe_images(problematic_preview)
    
    if not safe:
        print("✅ Problematic data correctly detected")
        print(f"   Issues: {message}")
    else:
        print("❌ Problematic data should have been detected")
    
    checklist_results = commands._run_moderation_checklist(problematic_preview)
    
    passed = sum(1 for result in checklist_results.values() if result)
    total = len(checklist_results)
    
    print(f"✅ Problematic checklist: {passed}/{total} checks passed")
    
    failed_items = [item for item, result in checklist_results.items() if not result]
    if failed_items:
        print(f"   Failed items: {', '.join(failed_items)}")

def test_safety_checks_service():
    """Test comprehensive safety checks service"""
    print("\n🛡️ Testing Safety Checks Service")
    print("=================================")
    
    # Test with safe data
    print("\n1. Testing with safe data...")
    
    safe_preview = {
        "artists": [
            {
                "name": "Queen",
                "image": "https://i.ytimg.com/vi/queen/maxresdefault.jpg",
                "subscribers": 1000000,
                "views": 1000000000,
                "channel_id": "UC123"
            },
            {
                "name": "Led Zeppelin",
                "image": "https://i.ytimg.com/vi/ledzep/maxresdefault.jpg",
                "subscribers": 800000,
                "views": 800000000,
                "channel_id": "UC456"
            }
        ]
    }
    
    results = safety_checks.comprehensive_safety_check(safe_preview)
    
    if results["overall_safe"]:
        print("✅ Comprehensive safety check passed")
    else:
        print("❌ Comprehensive safety check failed")
    
    print(f"   Total checks: {len(results['checks'])}")
    print(f"   Errors: {len(results['errors'])}")
    print(f"   Warnings: {len(results['warnings'])}")
    
    for check_name, check_result in results["checks"].items():
        status = "✅" if check_result["passed"] else "❌"
        print(f"   {status} {check_name}: {check_result['message']}")
    
    # Test with unsafe data
    print("\n2. Testing with unsafe data...")
    
    unsafe_preview = {
        "artists": [
            {
                "name": "Queen Official VEVO",
                "image": "https://nsfw-site.com/image.jpg",
                "subscribers": 100,  # Too low
                "views": 1000,  # Too low
                "channel_id": ""
            },
            {
                "name": "Test12345",  # Fake name pattern
                "image": "invalid_url",
                "subscribers": 999999999,  # Too high
                "views": 99999999999,  # Too high
                "channel_id": ""
            }
        ]
    }
    
    results = safety_checks.comprehensive_safety_check(unsafe_preview)
    
    if not results["overall_safe"]:
        print("✅ Unsafe data correctly detected")
    else:
        print("❌ Unsafe data should have been detected")
    
    print(f"   Critical failures: {len(results['critical_failures'])}")
    for failure in results["critical_failures"]:
        print(f"   • {failure}")

def test_moderator_checklist():
    """Test moderator checklist service"""
    print("\n📋 Testing Moderator Checklist Service")
    print("=====================================")
    
    # Test with good data
    print("\n1. Testing with good data...")
    
    good_preview = {
        "name": "Rock Legends Pack",
        "genre": "Rock",
        "payment_status": "authorized",
        "artist_count": 8,
        "quality_score": 75,
        "has_youtube_data": True,
        "artists": [
            {
                "name": "Queen",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/queen/maxresdefault.jpg",
                "channel_id": "UC123",
                "subscribers": 1000000
            },
            {
                "name": "Led Zeppelin",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/ledzep/maxresdefault.jpg",
                "channel_id": "UC456",
                "subscribers": 800000
            },
            {
                "name": "The Beatles",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/beatles/maxresdefault.jpg",
                "channel_id": "UC789",
                "subscribers": 2000000
            },
            {
                "name": "Pink Floyd",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/pinkfloyd/maxresdefault.jpg",
                "channel_id": "UC101",
                "subscribers": 1500000
            },
            {
                "name": "The Rolling Stones",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/stones/maxresdefault.jpg",
                "channel_id": "UC112",
                "subscribers": 1200000
            }
        ]
    }
    
    results = moderator_checklist.run_complete_checklist(good_preview)
    
    print(f"✅ Good data results:")
    print(f"   Overall Passed: {results['overall_passed']}")
    print(f"   Total Checks: {results['total_checks']}")
    print(f"   Passed: {results['passed_checks']}")
    print(f"   Failed: {results['failed_checks']}")
    print(f"   Recommendation: {results['recommendation']}")
    
    if results["critical_failures"]:
        print(f"   Critical Failures: {len(results['critical_failures'])}")
    
    # Test with bad data
    print("\n2. Testing with bad data...")
    
    bad_preview = {
        "name": "Official VEVO Pack",  # Bad name
        "genre": "Rock",
        "payment_status": "failed",  # Bad payment
        "artist_count": 3,  # Too few
        "quality_score": 10,  # Too low
        "has_youtube_data": False,
        "artists": [
            {
                "name": "Queen Official VEVO",  # Bad name
                "genre": "Pop",  # Genre mismatch
                "image": "",  # No image
                "channel_id": ""
            },
            {
                "name": "Queen Official VEVO",  # Duplicate
                "genre": "Pop",
                "image": "",
                "channel_id": ""
            },
            {
                "name": "XXX Artist",  # Inappropriate
                "genre": "Pop",
                "image": "https://nsfw-site.com/image.jpg",
                "channel_id": ""
            }
        ]
    }
    
    results = moderator_checklist.run_complete_checklist(bad_preview)
    
    print(f"✅ Bad data results:")
    print(f"   Overall Passed: {results['overall_passed']}")
    print(f"   Total Checks: {results['total_checks']}")
    print(f"   Passed: {results['passed_checks']}")
    print(f"   Failed: {results['failed_checks']}")
    print(f"   Recommendation: {results['recommendation']}")
    
    print(f"   Critical Failures: {len(results['critical_failures'])}")
    for failure in results["critical_failures"]:
        print(f"      • {failure}")
    
    # Test checklist summary
    print("\n3. Testing checklist summary...")
    
    summary = moderator_checklist.get_checklist_summary(good_preview)
    
    print("✅ Checklist summary generated:")
    print(f"   Length: {len(summary)} characters")
    print(f"   Contains recommendation: {'APPROVE' in summary or 'REJECT' in summary or 'REVIEW' in summary}")

def test_approval_flow_simulation():
    """Test complete approval flow simulation"""
    print("\n🔄 Testing Approval Flow Simulation")
    print("==================================")
    
    # Simulate admin workflow
    print("\n1. Admin runs !preview PACK123")
    
    # Mock preview data
    preview_data = {
        "pack_id": "PACK123",
        "name": "Test Pack",
        "genre": "Rock",
        "status": "pending",
        "payment_status": "authorized",
        "artist_count": 8,
        "quality_score": 75,
        "has_youtube_data": True,
        "artists": [
            {
                "name": "Queen",
                "genre": "Rock",
                "image": "https://i.ytimg.com/vi/queen/maxresdefault.jpg",
                "estimated_tier": "legendary",
                "popularity": 95,
                "subscribers": 1000000,
                "views": 1000000000
            }
        ]
    }
    
    print("✅ Preview data loaded")
    
    # Step 2: Admin verifies artists are real
    print("\n2. Admin verifies artists are real...")
    
    real, message = safety_checks.verify_artists_real(preview_data)
    
    if real:
        print(f"✅ Artists verified as real: {message}")
    else:
        print(f"❌ Artist verification failed: {message}")
    
    # Step 3: Admin checks no impersonation
    print("\n3. Admin checks no impersonation...")
    
    no_impersonation, message = safety_checks.verify_no_impersonation(preview_data)
    
    if no_impersonation:
        print(f"✅ No impersonation detected: {message}")
    else:
        print(f"❌ Impersonation detected: {message}")
    
    # Step 4: Admin checks tiers reasonable
    print("\n4. Admin checks tiers reasonable...")
    
    reasonable, message = safety_checks.verify_tiers_reasonable(preview_data)
    
    if reasonable:
        print(f"✅ Tiers are reasonable: {message}")
    else:
        print(f"❌ Tiers unreasonable: {message}")
    
    # Step 5: Admin checks images appropriate
    print("\n5. Admin checks images appropriate...")
    
    safe, message = safety_checks.safe_images(preview_data)
    
    if safe:
        print(f"✅ Images appropriate: {message}")
    else:
        print(f"❌ Images inappropriate: {message}")
    
    # Step 6: Run complete checklist
    print("\n6. Running complete moderator checklist...")
    
    checklist_results = moderator_checklist.run_complete_checklist(preview_data)
    
    print(f"✅ Checklist completed:")
    print(f"   Overall: {'PASSED' if checklist_results['overall_passed'] else 'FAILED'}")
    print(f"   Recommendation: {checklist_results['recommendation']}")
    print(f"   Critical Failures: {len(checklist_results['critical_failures'])}")
    
    # Step 7: Make decision
    print("\n7. Admin makes decision...")
    
    if checklist_results["recommendation"] == "APPROVE":
        print("✅ Decision: APPROVE - All checks passed")
        print("   Admin runs: !review PACK123 approve")
    elif checklist_results["recommendation"] == "REVIEW":
        print("⚠️ Decision: REVIEW - Some issues found")
        print("   Admin should review carefully before deciding")
    else:
        print("❌ Decision: REJECT - Critical issues found")
        print("   Admin runs: !review PACK123 reject <reason>")

def test_moderator_checklist_requirements():
    """Test specific moderator checklist requirements"""
    print("\n📋 Testing Moderator Checklist Requirements")
    print("=========================================")
    
    requirements = {
        "roster_matches_genre": False,
        "no_duplicates": False,
        "no_topic_auto_channels": False,
        "images_appropriate": False,
        "5_25_artists": False,
        "payment_authorized": False
    }
    
    # Test data that meets all requirements
    good_preview = {
        "name": "Rock Pack",
        "genre": "Rock",
        "payment_status": "authorized",
        "artist_count": 8,
        "artists": [
            {"name": "Queen", "genre": "Rock", "image": "https://example.com/1.jpg"},
            {"name": "Led Zeppelin", "genre": "Rock", "image": "https://example.com/2.jpg"},
            {"name": "Pink Floyd", "genre": "Rock", "image": "https://example.com/3.jpg"},
            {"name": "The Beatles", "genre": "Rock", "image": "https://example.com/4.jpg"},
            {"name": "The Rolling Stones", "genre": "Rock", "image": "https://example.com/5.jpg"},
            {"name": "AC/DC", "genre": "Rock", "image": "https://example.com/6.jpg"},
            {"name": "Metallica", "genre": "Rock", "image": "https://example.com/7.jpg"},
            {"name": "Nirvana", "genre": "Rock", "image": "https://example.com/8.jpg"}
        ]
    }
    
    print("\n1. Testing pack that meets all requirements...")
    
    results = moderator_checklist.run_complete_checklist(good_preview)
    
    # Check specific requirements
    checklist = results["check_results"]
    
    if checklist.get("roster_matches_genre", {}).get("passed"):
        requirements["roster_matches_genre"] = True
        print("✅ Roster matches genre")
    
    if checklist.get("no_duplicate_artists", {}).get("passed"):
        requirements["no_duplicates"] = True
        print("✅ No duplicate artists")
    
    if checklist.get("no_topic_auto_channels", {}).get("passed"):
        requirements["no_topic_auto_channels"] = True
        print("✅ No topic/auto channels")
    
    if checklist.get("images_appropriate", {}).get("passed"):
        requirements["images_appropriate"] = True
        print("✅ Images appropriate")
    
    if checklist.get("artist_count_valid", {}).get("passed"):
        requirements["5_25_artists"] = True
        print("✅ 5-25 artists")
    
    if checklist.get("payment_authorized", {}).get("passed"):
        requirements["payment_authorized"] = True
        print("✅ Payment authorized")
    
    # Summary
    print(f"\n📊 Requirements Summary:")
    passed = sum(requirements.values())
    total = len(requirements)
    
    for requirement, result in requirements.items():
        status = "✅" if result else "❌"
        print(f"   {status} {requirement}")
    
    print(f"\n📈 Overall: {passed}/{total} requirements met")
    
    if passed == total:
        print("🎉 All moderator checklist requirements met!")
    else:
        print("⚠️ Some requirements not met")

def main():
    """Run all tests"""
    print("🛡️ Admin Preview & Safety Test Suite")
    print("===================================")
    
    try:
        test_admin_preview_command()
        test_safety_checks_service()
        test_moderator_checklist()
        test_approval_flow_simulation()
        test_moderator_checklist_requirements()
        
        print("\n🎉 Admin Preview & Safety Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
