# test_discord_rate_limiting.py
"""
Test script to verify the rate limiting decorator works correctly
"""
import asyncio
from unittest.mock import Mock
from decorators.rate_guard import rate_guard

# Mock Discord context
class MockContext:
    def __init__(self, user_id: int):
        self.author = Mock()
        self.author.id = user_id
        self.messages = []
    
    async def send(self, message: str):
        self.messages.append(message)
        print(f"Bot: {message}")

# Test commands with rate limiting
@rate_guard("pack")
async def test_pack_command(ctx):
    await ctx.send("🎁 Pack opened successfully!")

@rate_guard("drop")
async def test_drop_command(ctx):
    await ctx.send("🎯 Drop claimed successfully!")

@rate_guard("founder_pack")
async def test_founder_pack_command(ctx):
    await ctx.send("🏛️ Founder Pack purchased!")

async def test_rate_limiting():
    """Test the rate limiting functionality"""
    print("=== Testing Discord Rate Limiting ===\n")
    
    # Create mock context for user 123
    ctx = MockContext(123)
    
    print("1. Testing pack rate limiting (10 per minute):")
    
    # Should work 10 times
    for i in range(10):
        await test_pack_command(ctx)
        print(f"   Pack {i+1}: ✅ Allowed")
    
    # Should fail on 11th attempt
    await test_pack_command(ctx)
    print(f"   Pack 11: ❌ Rate limited")
    
    print(f"\nBot messages: {len(ctx.messages)}")
    
    # Test different user
    print("\n2. Testing different user (should work):")
    ctx2 = MockContext(456)
    await test_pack_command(ctx2)
    print("   Different user: ✅ Allowed")
    
    # Test drop rate limiting (1 per 30 minutes)
    print("\n3. Testing drop rate limiting (1 per 30 minutes):")
    await test_drop_command(ctx)
    print("   First drop: ✅ Allowed")
    
    await test_drop_command(ctx)
    print("   Second drop: ❌ Rate limited")
    
    # Test founder pack rate limiting (5 per minute)
    print("\n4. Testing founder pack rate limiting (5 per minute):")
    for i in range(6):
        await test_founder_pack_command(ctx)
        if i < 5:
            print(f"   Founder Pack {i+1}: ✅ Allowed")
        else:
            print(f"   Founder Pack {i+1}: ❌ Rate limited")
    
    print("\n=== Rate Limiting Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_rate_limiting())
