# cogs/founder_shop.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ui
from typing import Dict, List, Optional
import json
import uuid
from packs.founder_packs import founder_packs
from rq_queue.redis_connection import QUEUES
from rq_queue.tasks import task_open_pack
from rate_limiter import rate_limiter
from rate_limiter import RateLimitMiddleware

class FounderShop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rate_limiter = RateLimitMiddleware(rate_limiter)
    
    @app_commands.command(name="founder_shop", description="View Founder Packs shop")
    async def founder_shop(self, interaction: Interaction):
        """Display Founder Packs shop"""
        embed = discord.Embed(
            title="🏛️ Founder Packs Shop",
            description="Limited edition Founder Packs with exclusive odds!",
            color=discord.Color.gold()
        )
        
        # Black Pack
        black_pack = founder_packs.get_pack_display_data(founder_packs.PACK_BLACK)
        if black_pack:
            embed.add_field(
                name=f"🖤 {black_pack['name']}",
                value=f"**{black_pack['primary_label']}**\n"
                      f"{black_pack['subtitle']}\n"
                      f"💰 **{black_pack['price']}**\n"
                      f"📝 {black_pack['description']}\n\n"
                      f"**Odds:**\n"
                      f"• Guaranteed: Gold+ (75% Gold, 22% Platinum, 3% Legendary)\n"
                      f"• Regular: 65% Community, 25% Gold, 8% Platinum, 2% Legendary",
                inline=False
            )
        
        # Silver Pack
        silver_pack = founder_packs.get_pack_display_data(founder_packs.PACK_SILVER)
        if silver_pack:
            embed.add_field(
                name=f"🩶 {silver_pack['name']}",
                value=f"**{silver_pack['primary_label']}**\n"
                      f"{silver_pack['subtitle']}\n"
                      f"💰 **{silver_pack['price']}**\n"
                      f"📝 {silver_pack['description']}\n\n"
                      f"**Odds:**\n"
                      f"• All Slots: 75% Community, 20% Gold, 4% Platinum, 1% Legendary",
                inline=False
            )
        
        embed.add_field(
            name="🛒 How to Purchase",
            value="Use `/buy_founder_pack` to purchase a pack!\n"
                  "All packs are processed through our secure queue system.",
            inline=False
        )
        
        embed.set_footer(text="Founder Packs • Limited Time • Queue Processing")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="buy_founder_pack", description="Purchase a Founder Pack")
    @app_commands.choices(pack_type=[
        app_commands.Choice(name="Black Pack", value="founder_black"),
        app_commands.Choice(name="Silver Pack", value="founder_silver")
    ])
    async def buy_founder_pack(self, interaction: Interaction, pack_type: str):
        """Purchase a Founder Pack"""
        user_id = interaction.user.id
        
        # Check rate limit
        allowed, result = await self.rate_limiter.check_command(user_id, 'pack_open', interaction.guild.id)
        if not allowed:
            embed = await self.rate_limiter.create_error_embed(result)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get pack config
        pack_config = founder_packs.get_pack_config(pack_type)
        if not pack_config:
            embed = discord.Embed(
                title="❌ Invalid Pack",
                description="This pack type is not available.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create Stripe checkout session (would integrate with Stripe)
        checkout_url = f"https://checkout.stripe.com/pay?pack={pack_type}&user={user_id}"
        
        embed = discord.Embed(
            title=f"🛒 Purchase {pack_config.name}",
            description=f"Complete your purchase to receive your pack!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📦 Pack Details",
            value=f"• Type: {pack_config.name}\n"
                  f"• Cards: {pack_config.card_count}\n"
                  f"• Price: ${pack_config.price_cents / 100:.2f}\n"
                  f"• Guarantee: {pack_config.guarantee or 'None'}",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Payment Link",
            value=f"[Click here to complete purchase]({checkout_url})\n\n"
                  f"After payment, your pack will be automatically processed!",
            inline=False
        )
        
        embed.set_footer(text="Secure payment via Stripe • Queue processing")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="open_founder_pack", description="Open a Founder Pack (requires purchase)")
    @app_commands.choices(pack_type=[
        app_commands.Choice(name="Black Pack", value="founder_black"),
        app_commands.Choice(name="Silver Pack", value="founder_silver")
    ])
    async def open_founder_pack(self, interaction: Interaction, pack_type: str):
        """Open a Founder Pack through queue system"""
        user_id = interaction.user.id
        
        # Check rate limit
        allowed, result = await self.rate_limiter.check_command(user_id, 'pack_open', interaction.guild.id)
        if not allowed:
            embed = await self.rate_limiter.create_error_embed(result)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if user has purchased this pack (would need database check)
        has_pack = await self._check_user_pack_ownership(user_id, pack_type)
        if not has_pack:
            embed = discord.Embed(
                title="❌ No Pack Available",
                description="You don't have this pack available to open.\n"
                          f"Use `/buy_founder_pack` to purchase a {pack_type.replace('_', ' ').title()}!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Enqueue pack opening
        try:
            job = QUEUES["pack"].enqueue(
                task_open_pack,
                user_id,
                pack_type
            )
            
            embed = discord.Embed(
                title="🎁 Opening Founder Pack",
                description=f"Your {pack_type.replace('_', ' ').title()} is being opened...",
                color=discord.Color.purple()
            )
            
            pack_config = founder_packs.get_pack_config(pack_type)
            embed.add_field(
                name="📋 Pack Details",
                value=f"• Type: {pack_config.name}\n"
                      f"• Cards: {pack_config.card_count}\n"
                      f"• Guarantee: {pack_config.guarantee or 'None'}",
                inline=False
            )
            
            embed.add_field(
                name="🔄 Processing",
                value=f"Job ID: {job.id}\n"
                      f"Your pack will be opened shortly through our secure queue system.",
                inline=False
            )
            
            embed.set_footer(text="Founder Pack • Queue Processing • Validated")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Queue Error",
                description=f"Failed to enqueue pack opening: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _check_user_pack_ownership(self, user_id: int, pack_type: str) -> bool:
        """Check if user owns this pack (would need database implementation)"""
        # This would check your database for purchased packs
        # For now, return False (no packs owned)
        return False
    
    @app_commands.command(name="founder_pack_info", description="Get detailed information about Founder Packs")
    @app_commands.choices(pack_type=[
        app_commands.Choice(name="Black Pack", value="founder_black"),
        app_commands.Choice(name="Silver Pack", value="founder_silver")
    ])
    async def founder_pack_info(self, interaction: Interaction, pack_type: str):
        """Get detailed information about a specific Founder Pack"""
        pack_data = founder_packs.get_pack_display_data(pack_type)
        
        if not pack_data:
            embed = discord.Embed(
                title="❌ Invalid Pack",
                description="This pack type is not available.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📦 {pack_data['name']} Details",
            description=pack_data['description'],
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="💰 Price",
            value=f"${pack_data['price']}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Cards",
            value=f"{pack_data['card_count']} Cards",
            inline=True
        )
        
        embed.add_field(
            name="🎯 Guarantee",
            value=pack_data['guarantee'] or "None",
            inline=True
        )
        
        # Detailed odds
        if pack_type == founder_packs.PACK_BLACK:
            embed.add_field(
                name="🎲 Odds - Guaranteed Slot",
                value="• Gold: 75%\n• Platinum: 22%\n• Legendary: 3%",
                inline=False
            )
            
            embed.add_field(
                name="🎲 Odds - Regular Slots (x4)",
                value="• Community: 65%\n• Gold: 25%\n• Platinum: 8%\n• Legendary: 2%",
                inline=False
            )
        else:
            embed.add_field(
                name="🎲 Odds - All Slots (x5)",
                value="• Community: 75%\n• Gold: 20%\n• Platinum: 4%\n• Legendary: 1%",
                inline=False
            )
        
        embed.add_field(
            name="🔒 Validation",
            value="• Queue processing only\n• Tier cap enforcement\n• Audit logging\n• Guaranteed results",
            inline=False
        )
        
        embed.set_footer(text="Founder Packs • Secure & Validated")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(FounderShop(bot))
