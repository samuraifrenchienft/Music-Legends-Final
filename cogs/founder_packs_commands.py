# cogs/founder_packs_commands.py
import discord
from discord.ext import commands
from decorators.rate_guard import rate_guard
from services.minimal_purchase import handle_purchase_minimal
from rq_queue.redis_connection import QUEUES
from rq_queue.tasks import task_open_pack
import uuid

class FounderPacksCommands(commands.Cog):
    """Founder Packs commands with rate limiting"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @rate_guard("drop")
    async def drop(self, ctx):
        """Claim a drop (rate limited: 1 per 30 minutes)"""
        await ctx.send("🎯 **Drop System**\nSearching for available drops...")
        
        # Simulate drop finding
        await ctx.send("🎁 **Drop Found!**\nYou found a rare card drop!")
        
        # Queue drop processing
        try:
            QUEUES["drop-queue"].enqueue(
                "resolve_drop",
                ctx.author.id,
                "drop_123",
                1
            )
            await ctx.send("✅ Drop queued for processing!")
        except Exception as e:
            await ctx.send(f"❌ Error queueing drop: {e}")
    
    @commands.command()
    @rate_guard("pack")
    async def pack(self, ctx, pack_type: str = "black"):
        """Open a pack (rate limited: 10 per minute)"""
        
        # Validate pack type
        valid_packs = ["black", "silver", "bronze", "gold"]
        if pack_type.lower() not in valid_packs:
            await ctx.send(f"❌ Invalid pack type. Valid types: {', '.join(valid_packs)}")
            return
        
        await ctx.send(f"🎁 **Opening {pack_type.title()} Pack**\nProcessing your pack...")
        
        # Queue pack opening
        try:
            job_id = str(uuid.uuid4())
            QUEUES["pack-queue"].enqueue(
                task_open_pack,
                ctx.author.id,
                pack_type.lower(),
                None,
                job_id=job_id
            )
            await ctx.send(f"✅ Pack queued! Job ID: `{job_id}`")
        except Exception as e:
            await ctx.send(f"❌ Error opening pack: {e}")
    
    @commands.command()
    @rate_guard("trade")
    async def trade(self, ctx, action: str, *, details: str = ""):
        """Trade commands (rate limited: 20 per minute)"""
        
        action = action.lower()
        
        if action == "create":
            await ctx.send("🤝 **Create Trade**\nCreating new trade...")
            # Trade creation logic here
            await ctx.send("✅ Trade created successfully!")
            
        elif action == "accept":
            await ctx.send("🤝 **Accept Trade**\nAccepting trade...")
            # Trade acceptance logic here
            await ctx.send("✅ Trade accepted!")
            
        elif action == "cancel":
            await ctx.send("❌ **Cancel Trade**\nCancelling trade...")
            # Trade cancellation logic here
            await ctx.send("✅ Trade cancelled!")
            
        else:
            await ctx.send("❌ Invalid action. Use: `!trade create|accept|cancel [details]`")
    
    @commands.command()
    @rate_guard("founder_pack")
    async def buy_founder_pack(self, ctx, pack_type: str = "black"):
        """Buy a Founder Pack (rate limited: 5 per minute)"""
        
        if pack_type.lower() not in ["black", "silver"]:
            await ctx.send("❌ Invalid Founder Pack type. Use: black or silver")
            return
        
        # Simulate purchase processing
        await ctx.send(f"🏛️ **Founder Pack Purchase**\nProcessing {pack_type.title()} Founder Pack...")
        
        # Use minimal purchase handler
        try:
            key = f"founder_{ctx.author.id}_{uuid.uuid4()}"
            result = handle_purchase_minimal(ctx.author.id, f"founder_{pack_type.lower()}", key)
            
            if result == "QUEUED":
                await ctx.send(f"✅ **Founder Pack Purchased!**\nYour {pack_type.title()} Founder Pack is being opened!")
                await ctx.send(f"🎁 **Pack Contents**\nCheck your inventory for the cards!")
            elif result == "ALREADY_PROCESSED":
                await ctx.send("⚠️ Purchase already processed!")
            else:
                await ctx.send(f"❌ Purchase failed: {result}")
                
        except Exception as e:
            await ctx.send(f"❌ Error purchasing Founder Pack: {e}")
    
    @commands.command()
    @rate_guard("daily_reward")
    async def daily(self, ctx):
        """Claim daily reward (rate limited: 1 per 24 hours)"""
        
        await ctx.send("🎁 **Daily Reward**\nClaiming your daily reward...")
        
        # Simulate daily reward
        reward_amount = 1000  # Example: 1000 coins
        await ctx.send(f"✅ **Daily Reward Claimed!**\nYou received **{reward_amount}** coins!")
        await ctx.send("Come back tomorrow for your next reward!")
    
    @commands.command()
    async def rate_status(self, ctx):
        """Check your current rate limit status"""
        from rate_config import RateLimitManager
        
        manager = RateLimitManager(ctx.author.id)
        status = manager.get_all_status()
        
        embed = discord.Embed(
            title="⏱️ Rate Limit Status",
            color=discord.Color.blue()
        )
        
        for action, stats in status.items():
            remaining = stats['remaining']
            limit = stats['limit']
            current = stats['current']
            
            # Create status bar
            bar_length = 10
            filled = int((current / limit) * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            embed.add_field(
                name=f"🎯 {action.title()}",
                value=f"`{bar}` {current}/{limit} ({remaining} remaining)",
                inline=False
            )
        
        await ctx.send(embed=embed)

# Setup function
async def setup(bot):
    await bot.add_cog(FounderPacksCommands(bot))
