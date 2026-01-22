# test_creator_pack_payment.py
# Test script for creator pack payment integration

import sys
sys.path.append('.')

from services.creator_pack_payment import creator_pack_payment, create_pack_with_hold
from models.creator_pack import CreatorPack

def test_pack_creation_with_hold():
    """Test pack creation with payment authorization"""
    print("💳 Testing Pack Creation with Payment Hold")
    print("========================================")
    
    # Test successful creation
    print("\n1. Testing successful pack creation...")
    
    try:
        pack = creator_pack_payment.create_pack_with_hold(
            user_id=123456789,
            name="Rock Legends",
            artists=["Queen", "Led Zeppelin", "The Beatles", "Pink Floyd", "The Rolling Stones"],
            genre="Rock",
            payment_id="pi_1234567890_abcdef",
            price_cents=999
        )
        
        if pack:
            print("✅ Pack created successfully")
            print(f"   Pack ID: {pack.id}")
            print(f"   Name: {pack.name}")
            print(f"   Payment ID: {pack.payment_id}")
            print(f"   Payment Status: {pack.payment_status}")
            print(f"   Pack Status: {pack.status}")
            print(f"   Price: ${pack.price_cents / 100:.2f}")
        else:
            print("❌ Pack creation failed")
            
    except ValueError as e:
        print(f"❌ Validation error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test validation failure
    print("\n2. Testing validation failure...")
    
    try:
        pack = creator_pack_payment.create_pack_with_hold(
            user_id=123456789,
            name="Official VEVO Channel",
            artists=["Queen Official", "Led Zeppelin VEVO"],
            genre="Rock",
            payment_id="pi_invalid_123",
            price_cents=999
        )
        
        print("❌ Pack should have failed validation")
        
    except ValueError as e:
        print(f"✅ Validation correctly failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_payment_capture_on_approval():
    """Test payment capture on pack approval"""
    print("\n💰 Testing Payment Capture on Approval")
    print("======================================")
    
    # Mock approved pack
    class MockPack:
        def __init__(self, pack_id):
            self.id = pack_id
            self.name = "Test Pack"
            self.owner_id = 123456789
            self.payment_id = "pi_1234567890"
            self.payment_status = "authorized"
            self.price_cents = 999
            self.status = "approved"
            self.reviewed_by = None
            self.reviewed_at = None
        
        def save(self):
            pass
        
        def can_be_captured(self):
            return self.payment_status == "authorized" and self.status == "approved"
        
        def capture_payment(self):
            self.payment_status = "captured"
    
    # Temporarily replace CreatorPack.get_by_id
    original_get_by_id = CreatorPack.get_by_id
    CreatorPack.get_by_id = lambda pack_id: MockPack(pack_id)
    
    try:
        success = creator_pack_payment.capture_payment_on_approval("pack_123", 999999999)
        
        if success:
            print("✅ Payment captured successfully on approval")
        else:
            print("❌ Payment capture failed")
            
    except Exception as e:
        print(f"❌ Error capturing payment: {e}")
    finally:
        # Restore original method
        CreatorPack.get_by_id = original_get_by_id

def test_payment_refund_on_rejection():
    """Test payment refund on pack rejection"""
    print("\n💸 Testing Payment Refund on Rejection")
    print("=====================================")
    
    # Mock rejected pack
    class MockPack:
        def __init__(self, pack_id):
            self.id = pack_id
            self.name = "Test Pack"
            self.owner_id = 123456789
            self.payment_id = "pi_1234567890"
            self.payment_status = "captured"
            self.price_cents = 999
            self.status = "rejected"
            self.reviewed_by = None
            self.reviewed_at = None
        
        def save(self):
            pass
        
        def can_be_refunded(self):
            return self.payment_status == "captured"
        
        def refund_payment(self):
            self.payment_status = "refunded"
    
    # Temporarily replace CreatorPack.get_by_id
    original_get_by_id = CreatorPack.get_by_id
    CreatorPack.get_by_id = lambda pack_id: MockPack(pack_id)
    
    try:
        success = creator_pack_payment.refund_payment_on_rejection("pack_456", 999999999, "Invalid content")
        
        if success:
            print("✅ Payment refunded successfully on rejection")
        else:
            print("❌ Payment refund failed")
            
    except Exception as e:
        print(f"❌ Error refunding payment: {e}")
    finally:
        # Restore original method
        CreatorPack.get_by_id = original_get_by_id

def test_payment_failure_handling():
    """Test payment failure handling"""
    print("\n❌ Testing Payment Failure Handling")
    print("==================================")
    
    # Mock pack for failure
    class MockPack:
        def __init__(self, pack_id):
            self.id = pack_id
            self.name = "Test Pack"
            self.owner_id = 123456789
            self.payment_id = "pi_1234567890"
            self.payment_status = "authorized"
            self.price_cents = 999
            self.status = "pending"
        
        def save(self):
            pass
        
        def fail_payment(self):
            self.payment_status = "failed"
    
    # Temporarily replace CreatorPack.get_by_id
    original_get_by_id = CreatorPack.get_by_id
    CreatorPack.get_by_id = lambda pack_id: MockPack(pack_id)
    
    try:
        success = creator_pack_payment.fail_payment_on_error("pack_789", "Payment processing error")
        
        if success:
            print("✅ Payment marked as failed successfully")
        else:
            print("❌ Failed to mark payment as failed")
            
    except Exception as e:
        print(f"❌ Error marking payment as failed: {e}")
    finally:
        # Restore original method
        CreatorPack.get_by_id = original_get_by_id

def test_payment_status_retrieval():
    """Test payment status retrieval"""
    print("\n📊 Testing Payment Status Retrieval")
    print("==================================")
    
    # Mock pack with payment info
    class MockPack:
        def __init__(self, pack_id):
            self.id = pack_id
            self.name = "Test Pack"
            self.payment_id = "pi_1234567890"
            self.payment_status = "captured"
            self.price_cents = 999
        
        def get_payment_info(self):
            return {
                "payment_id": self.payment_id,
                "payment_status": self.payment_status,
                "price_cents": self.price_cents,
                "price_dollars": self.price_cents / 100,
                "can_be_captured": False,
                "can_be_refunded": True,
                "is_authorized": False,
                "is_captured": True,
                "is_failed": False,
                "is_refunded": False
            }
    
    # Temporarily replace CreatorPack.get_by_id
    original_get_by_id = CreatorPack.get_by_id
    CreatorPack.get_by_id = lambda pack_id: MockPack(pack_id)
    
    try:
        payment_info = creator_pack_payment.get_payment_status("pack_123")
        
        if payment_info:
            print("✅ Payment status retrieved successfully")
            print(f"   Payment ID: {payment_info['payment_id']}")
            print(f"   Status: {payment_info['payment_status']}")
            print(f"   Amount: ${payment_info['price_dollars']:.2f}")
            print(f"   Can be refunded: {payment_info['can_be_refunded']}")
        else:
            print("❌ Failed to retrieve payment status")
            
    except Exception as e:
        print(f"❌ Error retrieving payment status: {e}")
    finally:
        # Restore original method
        CreatorPack.get_by_id = original_get_by_id

def test_user_payment_history():
    """Test user payment history"""
    print("\n📋 Testing User Payment History")
    print("==============================")
    
    # Mock user packs
    class MockPack:
        def __init__(self, pack_id, name, payment_status, status):
            self.id = pack_id
            self.name = name
            self.owner_id = 123456789
            self.payment_id = f"pi_{pack_id}"
            self.payment_status = payment_status
            self.price_cents = 999
            self.status = status
            self.created_at = "2024-01-20T12:00:00"
            self.reviewed_at = "2024-01-20T12:05:00"
        
        def get_payment_info(self):
            return {
                "payment_id": self.payment_id,
                "payment_status": self.payment_status,
                "price_cents": self.price_cents,
                "price_dollars": self.price_cents / 100
            }
    
    # Temporarily replace CreatorPack.get_by_owner
    original_get_by_owner = CreatorPack.get_by_owner
    CreatorPack.get_by_owner = lambda user_id: [
        MockPack("pack_1", "Rock Pack", "captured", "approved"),
        MockPack("pack_2", "Pop Pack", "refunded", "rejected"),
        MockPack("pack_3", "Jazz Pack", "authorized", "pending")
    ]
    
    try:
        history = creator_pack_payment.get_user_payment_history(123456789)
        
        if history:
            print(f"✅ Payment history retrieved: {len(history)} packs")
            for pack_info in history:
                print(f"   {pack_info['pack_name']} - {pack_info['payment_status']} - ${pack_info['price_cents'] / 100:.2f}")
        else:
            print("❌ No payment history found")
            
    except Exception as e:
        print(f"❌ Error retrieving payment history: {e}")
    finally:
        # Restore original method
        CreatorPack.get_by_owner = original_get_by_owner

def test_payment_statistics():
    """Test payment statistics"""
    print("\n📊 Testing Payment Statistics")
    print("=============================")
    
    # Mock all packs
    class MockPack:
        def __init__(self, payment_status, price_cents):
            self.payment_status = payment_status
            self.price_cents = price_cents
    
    # Temporarily replace CreatorPack.all
    original_all = CreatorPack.all
    CreatorPack.all = lambda: [
        MockPack("authorized", 999),
        MockPack("captured", 999),
        MockPack("captured", 1999),
        MockPack("failed", 999),
        MockPack("refunded", 999)
    ]
    
    try:
        stats = creator_pack_payment.get_payment_statistics()
        
        print(f"✅ Payment statistics retrieved:")
        print(f"   Total packs: {stats['total_packs']}")
        print(f"   Authorized: {stats['authorized']}")
        print(f"   Captured: {stats['captured']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Refunded: {stats['refunded']}")
        print(f"   Total revenue: ${stats['total_revenue_dollars']:.2f}")
        print(f"   Average price: ${stats['average_price_dollars']:.2f}")
        
    except Exception as e:
        print(f"❌ Error retrieving payment statistics: {e}")
    finally:
        # Restore original method
        CreatorPack.all = original_all

def main():
    """Run all tests"""
    print("💳 Creator Pack Payment Integration Test Suite")
    print("============================================")
    
    try:
        test_pack_creation_with_hold()
        test_payment_capture_on_approval()
        test_payment_refund_on_rejection()
        test_payment_failure_handling()
        test_payment_status_retrieval()
        test_user_payment_history()
        test_payment_statistics()
        
        print("\n🎉 Payment Integration Test Suite Completed!")
        print("📊 All tests completed - check results above")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
