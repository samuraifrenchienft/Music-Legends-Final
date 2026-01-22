# test_admin_review_system.py
# Test script for admin review system and open guard

import sys
sys.path.append('.')

from services.admin_review import admin_review, review_pack
from services.open_creator import open_creator_pack
from services.creator_moderation import creator_moderation
from models.creator_pack import CreatorPack

def test_admin_review_service():
    """Test admin review service"""
    print("🛡️ Testing Admin Review Service")
    print("==========================")
    
    # Mock pack for testing
    class MockPack:
        def __init__(self, pack_id, status="pending"):
            self.id = pack_id
            self.name = f"Test Pack {pack_id}"
            self.genre = "Rock"
            self.owner_id = 123456789
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.price_cents = 999
            self.status = status
            self.reviewed_by = None
            self.reviewed_at = None
            self.notes = ""
            self.rejection_reason = ""
        
        def save(self):
            pass  # Mock save
        
        def increment_purchases(self):
            pass  # Mock increment
    
    # Test approval
    print("\n1. Testing pack approval...")
    mock_pack = MockPack("pack_123", "pending")
    
    result = admin_review.review_pack(
        pack_id="pack_123",
        admin_id=999999999,
        approve=True,
        note="Good quality pack"
    )
    
    if result == "approved":
        print("✅ Pack approval successful")
        print(f"   Status: {mock_pack.status}")
        print(f"   Reviewed by: {mock_pack.reviewed_by}")
        print(f"   Reviewed at: {mock_pack.reviewed_at}")
    else:
        print(f"❌ Pack approval failed: {result}")
    
    # Test rejection
    print("\n2. Testing pack rejection...")
    mock_pack2 = MockPack("pack_456", "pending")
    
    result = admin_review.review_pack(
        pack_id="pack_456",
        admin_id=999999999,
        approve=False,
        note="Contains duplicate artists"
    )
    
    if result == "rejected":
        print("✅ Pack rejection successful")
        print(f"   Status: {mock_pack2.status}")
        print(f"   Rejection reason: {mock_pack2.rejection_reason}")
        print(f"   Reviewed by: {mock_pack2.reviewed_by}")
    else:
        print(f"❌ Pack rejection failed: {result}")
    
    # Test invalid pack ID
    print("\n3. Testing invalid pack ID...")
    result = admin_review.review_pack(
        pack_id="invalid_pack",
        admin_id=999999999,
        approve=True,
        note="Test invalid pack"
    )
    
    if result is None:
        print("✅ Invalid pack ID correctly handled")
    else:
        print(f"❌ Invalid pack ID should return None: {result}")
    
    # Test non-reviewable pack
    print("\n4. Testing non-reviewable pack...")
    mock_pack3 = MockPack("pack_789", "approved")
    
    result = admin_review.review_pack(
        pack_id="pack_789",
        admin_id=999999999,
        approve=True,
        note="Test approved pack"
    )
    
    if result == "approved":
        print("❌ Approved pack should not be reviewable")
    else:
        print("✅ Non-reviewable pack correctly handled")

def test_final_validation():
    """Test final validation before approval"""
    print("\n🔍 Testing Final Validation")
    print("=========================")
    
    # Test valid pack
    print("\n1. Testing valid pack...")
    
    class MockArtist:
        def __init__(self, name, tier):
            self.name = name
            self.tier = tier
            self.id = f"artist_{name.lower().replace(' ', '_')}"
            self.genre = "Rock"
    
    class MockPack:
        def __init__(self, pack_id, status="pending"):
            self.id = pack_id
            self.name = f"Test Pack {pack_id}"
            self.genre = "Rock"
            self.owner_id = 123456789
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.price_cents = 999
            self.status = status
            self.reviewed_by = None
            self.reviewed_at = None
            self.notes = ""
            self.rejection_reason = ""
        
        def get_artists(self):
            return [
                MockArtist("Queen", "legendary"),
                MockArtist("Led Zeppelin", "platinum"),
                MockArtist("The Beatles", "gold")
            ]
        
        def save(self):
            pass  # Mock save
        
        def increment_purchases(self):
            pass  # Mock increment
    
    mock_pack = MockPack("pack_123", "pending")
    
    result = admin_review._final_validation(mock_pack)
    
    if result["valid"]:
        print("✅ Valid pack passed final validation")
    else:
        print(f"❌ Valid pack failed validation: {result['reason']}")
        if result["warnings"]:
            print(f"   Warnings: {result['warnings']}")
    
    # Test pack with duplicates
    print("\n2. Testing pack with duplicates...")
    mock_pack2 = MockPack("pack_456", "pending")
    mock_pack2.artist_ids = ["artist_1", "artist_1"]  # Duplicate
    
    result = admin_review._final_validation(mock_pack2)
    
    if not result["valid"]:
        print("✅ Pack with duplicates correctly rejected")
        print(f"   Reason: {result['reason']}")
    else:
        print("❌ Pack with duplicates should be rejected")
    
    # Test pack with too few artists
    print("\n3. Testing pack with too few artists...")
    mock_pack3 = MockPack("pack_789", "pending")
    mock_pack3.artist_ids = ["artist_1"]  # Only 1 artist
    
    result = admin_review._final_validation(mock_pack3)
    
    if not result["valid"]:
        print("✅ Pack with too few artists correctly rejected")
        print(f"   Reason: {result['reason']}")
    else:
        print("❌ Pack with too few artists should be rejected")

def test_open_guard():
    """Test open guard functionality"""
    print("\n🛡️ Testing Open Guard")
    print("====================")
    
    # Test approved pack
    print("\n1. Testing approved pack...")
    
    class MockApprovedPack:
        def __init__(self):
            self.status = "approved"
            self.name = "Approved Pack"
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.price_cents = 999
            self.owner_id = 123456789
        
        def save(self):
            pass
        
        def increment_purchases(self):
            pass
    
    approved_pack = MockApprovedPack()
    
    try:
        cards = open_creator_pack(approved_pack)
        print(f"✅ Approved pack opened successfully: {len(cards)} cards")
    except ValueError as e:
        print(f"❌ Approved pack correctly opened: {e}")
    
    # Test pending pack
    print("\n2. Testing pending pack...")
    
    class MockPendingPack:
        def __init__(self):
            self.status = "pending"
            self.name = "Pending Pack"
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.price_cents = 999
            self.owner_id = 123456789
        
        def save(self):
            pass
        
        def increment_purchases(self):
            pass
    
    pending_pack = MockPendingPack()
    
    try:
        cards = open_creator_pack(pending_pack)
        print(f"❌ Pending pack correctly rejected: {e}")
    except ValueError as e:
        print(f"✅ Pending pack correctly rejected: {e}")
    
    # Test rejected pack
    print("\n3. Testing rejected pack...")
    
    class MockRejectedPack:
        def __init__(self):
            self.status = "rejected"
            self.name = "Rejected Pack"
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.price_cents = 999
            self.owner_id = 123456789
        
        def save(self):
            pass
        
        def increment_purchases(self):
            pass
    
    rejected_pack = MockRejectedPack()
    
    try:
        cards = open_creator_pack(rejected_pack)
        print(f"❌ Rejected pack correctly rejected: {e}")
    except ValueError as e:
        print(f"✅ Rejected pack correctly rejected: {e}")

def test_review_history():
    """Test review history tracking"""
    print("\n📋 Testing Review History")
    print("========================")
    
    # Mock audit logs
    class MockAuditLog:
        @classmethod
        def query(cls):
            return MockAuditQuery()
    
    class MockAuditQuery:
        def __init__(self):
            self.logs = [
                {
                    "event": "creator_pack_submitted",
                    "user_id": 123456789,
                    "target_id": "pack_123",
                    "payload": {"pack_name": "Test Pack"},
                    "created_at": "2024-01-20T12:00:00"
                },
                {
                    "event": "creator_pack_approved",
                    "user_id": 999999999,
                    "target_id": "patch_123",
                    "payload": {"decision": "approved", "note": "Good pack"},
                    "created_at": "2024-01-20T12:05:00"
                }
            ]
        
        def filter(self, **kwargs):
            return MockAuditQuery()
        
        def order_by(self, field):
            return self
        
        def all(self):
            return self.logs
        
        def first(self):
            return self.logs[0]
    
    # Temporarily replace AuditLog
    import services.admin_review
    original_audit_log = services.admin_review.AuditLog
    services.admin_review.AuditLog = MockAuditLog
    
    try:
        history = admin_review.get_review_history("pack_123")
        
        if history:
            print(f"✅ Review history retrieved: {history['pack_name']}")
            print(f"   Current status: {history['current_status']}")
            print(f"   Review events: {len(history['review_history'])}")
            
            # Show last event
            if history['review_history']:
                last_event = history['review_history'][-1]
                print(f"   Last event: {last_event['event']}")
                print(f"   Timestamp: {last_event['timestamp']}")
                print(f"   Payload: {last_event['payload']}")
        else:
            print("⚠️ No review history found")
            
    except Exception as e:
        print(f"❌ Error getting review history: {e}")
    finally:
        # Restore original AuditLog
        services.admin_review.AuditLog = original_audit_log

def test_admin_stats():
    """Test admin statistics"""
    print("\n📊 Testing Admin Statistics")
    print("========================")
    
    # Mock audit logs
    class MockAuditLog:
        @classmethod
        def query(cls):
            return MockAuditQuery()
    
    class MockAuditQuery:
        def __init__(self):
            self.logs = [
                {
                    "event": "creator_pack_approved",
                    "user_id": 999999999,
                    "target_id": "pack_123",
                    "payload": {"decision": "approved", "note": "Good pack"},
                    "created_at": "2024-01-20T12:00:00"
                },
                {
                    "event": "creator_pack_rejected",
                    "user_id": 999999999,
                    "target_id": "pack_456",
                    "payload": {"decision": "rejected", "note": "Bad pack"},
                    "created_at": "2024-01-20T12:05:00"
                },
                {
                    "event": "creator_pack_approved",
                    "user_id": 999999999,
                    "target_id": "pack_789",
                    "pending": {"decision": "approved", "note": "Good pack"},
                    "created_at": "2024-01-20T12:10:00"
                }
            ]
        
        def filter(self, **kwargs):
            return MockAuditQuery()
        
        def order_by(self, field):
            return self
        
        def all(self):
            return self.logs
        
        def count(self):
            return len(self.logs)
    
    # Temporarily replace AuditLog
    import services.admin_review
    original_audit_log = services.admin_review.AuditLog
    services.admin_review.AuditLog = MockAuditLog
    
    try:
        stats = admin_review.get_admin_stats(999999999)
        
        print(f"✅ Admin stats retrieved:")
        print(f"   Total reviews: {stats['total_reviews']}")
        print(f"   Approvals: {stats['approvals']}")
        print(f"   Rejections: {stats['rejections']}")
        print(f"   Approval rate: {stats['approval_rate']:.1f}%")
        print(f"   Recent reviews: {len(stats['recent_reviews'])}")
        
    except Exception as e:
        print(f"❌ Error getting admin stats: {e}")
    finally:
        # Restore original AuditLog
        services.admin_review.AuditLog = original_audit_log

def test_queue_stats():
    """Test queue statistics"""
    print("\n📋 Testing Queue Statistics")
    print("========================")
    
    # Mock pending reviews
    class MockModeration:
        def __init__(self):
            self.pending_reviews = [
                {
                    "pack_id": "pack_123",
                    "user_id": 123456789,
                    "submitted_at": "2024-01-20T12:00:00",
                    "pack_name": "Test Pack 1",
                    "artist_count": 3
                },
                {
                    "pack_id": "pack_456",
                    "user_id": 987654321,
                    "submitted_at": "2024-01-20T12:05:00",
                    "pack_name": "Test Pack 2",
                    "artist_count": 5
                }
            ]
        
        def get_pending_reviews(self, limit=None):
            return self.pending_reviews[:limit] if limit else self.pending_reviews
        
        def _count_pending_by_genre(self, pending_reviews):
            return {"rock": 1, "pop": 1}  # Mock data
    
    # Temporarily replace moderation
    import services.admin_review
    original_moderation = services.admin_review.moderation
    services.admin_review.moderation = MockModeration()
    
    try:
        stats = admin_review.get_queue_stats()
        
        print(f"✅ Queue stats retrieved:")
        print(f"   Pending count: {stats['pending_count']}")
        print(f"   Oldest pending: {stats['oldest_pending']}")
        print(f" Newest pending: {stats['newest_pending']}")
        print(f"   Pending by genre: {stats['pending_by_genre']}")
        
    except Exception as e:
        print(f"❌ Error getting queue stats: {e}")
    finally:
        # Restore original moderation
        services.admin_review.moderation = original_moderation

def main():
    """Run all tests"""
    print("🛡️ Admin Review System Test Suite")
    print("================================")
    
    try:
        test_admin_review_service()
        test_final_validation()
        test_open_guard()
        test_review_history()
        test_admin_stats()
        test_queue_stats()
        
        print("\n🎉 Admin Review System Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
