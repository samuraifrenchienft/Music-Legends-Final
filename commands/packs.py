# commands/packs.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from queue.redis import QUEUES
from queue.tasks import task_open_pack
from rate_limiter import rate_limiter
from rate_limiter import RateLimitMiddleware

class PackCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rate_limiter = RateLimitMiddleware(rate_limiter)

    @app_commands.command(name="open_pack")
    async def open_pack(self, ctx: Interaction, pack_type: str, genre: str = None):
        """Open a pack through queue system"""
        user_id = ctx.user.id
        
        # Check rate limit
        allowed, result = await self.rate_limiter.check_command(user_id, 'pack_open', ctx.guild.id)
        if not allowed:
            embed = await self.rate_limiter.create_error_embed(result)
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Enqueue pack opening
        try:
            job = QUEUES["pack"].enqueue(
                task_open_pack,
                user_id,
                pack_type,
                genre
            )
            
            embed = discord.Embed(
                title="🎁 Pack Opening",
                description=f"Your {pack_type} pack is being opened...",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Job ID",
                value=job.id,
                inline=False
            )
            embed.set_footer(text="You'll receive your cards shortly!")
            
            await ctx.response.send_message(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Queue Error",
                description=f"Failed to enqueue pack opening: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="burn_card")
    async def burn_card(self, ctx: Interaction, serial_number: str):
        """Burn a card for dust through queue system"""
        user_id = ctx.user.id
        
        # Check rate limit
        allowed, result = await self.rate_limiter.check_command(user_id, 'burn', ctx.guild.id)
        if not allowed:
            embed = await self.rate_limiter.create_error_embed(result)
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Find card by serial number
        card_id = await self._find_card_by_serial(user_id, serial_number)
        if not card_id:
            embed = discord.Embed(
                title="❌ Card Not Found",
                description=f"You don't have a card with serial number: {serial_number}",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Enqueue card burning
        try:
            job = QUEUES["burn"].enqueue(
                task_burn,
                card_id,
                user_id
            )
            
            embed = discord.Embed(
                title="🔥 Card Burning",
                description=f"Burning card {serial_number}...",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="📋 Job ID",
                value=job.id,
                inline=False
            )
            embed.set_footer(text="You'll receive dust shortly!")
            
            await ctx.response.send_message(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Queue Error",
                description=f"Failed to enqueue card burning: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.response.send_message(embed=embed, ephemeral=True)
    
    async def _find_card_by_serial(self, user_id: int, serial_number: str) -> str:
        """Find card ID by serial number"""
        # This would search your database for the card
        # Implementation depends on your database structure
        return f"card_{serial_number}"  # Placeholder

# Import required modules
import sqlite3
from database import DatabaseManager
