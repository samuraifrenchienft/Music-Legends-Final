# test_commands.py
"""
Test script to verify the rate limited commands work correctly
"""
import asyncio
from unittest.mock import Mock, AsyncMock
from cogs.founder_packs_commands import FounderPacksCommands

# Mock Discord context
class MockContext:
    def __init__(self, user_id: int, username: str):
        self.author = Mock()
        self.author.id = user_id
        self.author.name = username
        self.messages = []
        self.send = AsyncMock()
    
    async def send(self, message: str):
        self.messages.append(message)
        print(f"[{self.author.name}] Bot: {message}")

# Mock bot
class MockBot:
    def __init__(self):
        pass

async def test_commands():
    """Test the rate limited commands"""
    print("=== Testing Rate Limited Commands ===\n")
    
    # Create bot and cog
    bot = MockBot()
    cog = FounderPacksCommands(bot)
    
    # Create mock context
    ctx = MockContext(123, "TestUser")
    
    print("1. Testing drop command (1 per 30 minutes):")
    await cog.drop(ctx)
    print("   First drop: ✅ Should work")
    
    await cog.drop(ctx)
    print("   Second drop: ❌ Should be rate limited")
    
    print("\n2. Testing pack command (10 per minute):")
    for i in range(12):
        await cog.pack(ctx, "black")
        if i < 10:
            print(f"   Pack {i+1}: ✅ Should work")
        else:
            print(f"   Pack {i+1}: ❌ Should be rate limited")
    
    print("\n3. Testing trade command (20 per minute):")
    await cog.trade(ctx, "create", "card123 for card456")
    print("   Trade create: ✅ Should work")
    
    await cog.trade(ctx, "accept", "trade789")
    print("   Trade accept: ✅ Should work")
    
    print("\n4. Testing founder pack command (5 per minute):")
    for i in range(7):
        await cog.buy_founder_pack(ctx, "black")
        if i < 5:
            print(f"   Founder Pack {i+1}: ✅ Should work")
        else:
            print(f"   Founder Pack {i+1}: ❌ Should be rate limited")
    
    print("\n5. Testing daily reward command (1 per 24 hours):")
    await cog.daily(ctx)
    print("   Daily reward: ✅ Should work")
    
    await cog.daily(ctx)
    print("   Daily reward 2: ❌ Should be rate limited")
    
    print("\n6. Testing rate status command:")
    await cog.rate_status(ctx)
    print("   Rate status: ✅ Should work (not rate limited)")
    
    print("\n=== Commands Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_commands())
