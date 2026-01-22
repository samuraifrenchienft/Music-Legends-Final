# cogs/rate_limited_commands.py
import discord
from discord.ext import commands
from decorators.rate_guard import rate_guard

class RateLimitedCommands(commands.Cog):
    """Example cog showing rate limiting usage"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @rate_guard("pack")
    async def buy_pack(self, ctx, pack_type: str = "black"):
        """Buy a pack (rate limited)"""
        await ctx.send(f"🎁 **Pack Purchased**\nYou bought a **{pack_type}** pack!")
    
    @commands.command()
    @rate_guard("drop")
    async def claim_drop(self, ctx):
        """Claim a drop (rate limited)"""
        await ctx.send("🎯 **Drop Claimed**\nYou claimed a rare drop!")
    
    @commands.command()
    @rate_guard("founder_pack")
    async def buy_founder_pack(self, ctx, pack_type: str = "black"):
        """Buy a Founder Pack (rate limited)"""
        await ctx.send(f"🏛️ **Founder Pack Purchased**\nYou bought a **{pack_type}** Founder Pack!")
    
    @commands.command()
    @rate_guard("daily_reward")
    async def daily(self, ctx):
        """Claim daily reward (rate limited)"""
        await ctx.send("🎁 **Daily Reward**\nYou claimed your daily reward!")
    
    @commands.command()
    @rate_guard("trade")
    async def create_trade(self, ctx, card_id: str):
        """Create a trade (rate limited)"""
        await ctx.send(f"🤝 **Trade Created**\nTrade for card **{card_id}** created!")
    
    @commands.command()
    async def no_limit(self, ctx):
        """Command without rate limiting"""
        await ctx.send("✅ **No Rate Limit**\nThis command has no rate limit!")

# Setup function for the bot
async def setup(bot):
    await bot.add_cog(RateLimitedCommands(bot))
