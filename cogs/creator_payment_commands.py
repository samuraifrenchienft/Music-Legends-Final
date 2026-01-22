# cogs/creator_payment_commands.py
"""
Discord Commands for Creator Pack Payment Integration
"""

from discord.ext import commands
import discord
from services.creator_pack_payment import creator_pack_payment, create_pack_with_hold
from models.creator_pack import CreatorPack

class CreatorPaymentCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def createpack_with_payment(self, ctx, name: str, genre: str, payment_id: str, *, artists: str):
        """
        Create a creator pack with payment authorization
        Usage: !createpack_with_payment "Pack Name" "Genre" payment_id artist1, artist2, artist3
        """
        try:
            # Parse artists
            artist_list = [a.strip() for a in artists.split(',')]
            
            # Validate inputs
            if not name or len(name) > 60:
                await ctx.send("❌ Pack name must be 1-60 characters")
                return
            
            if not genre or len(genre) > 20:
                await ctx.send("❌ Genre must be 1-20 characters")
                return
            
            if not artist_list or len(artist_list) > 25:
                await ctx.send("❌ Please provide 1-25 artists")
                return
            
            if not payment_id or len(payment_id) > 80:
                await ctx.send("❌ Invalid payment ID")
                return
            
            await ctx.trigger_typing()
            
            # Create pack with payment hold
            pack = create_pack_with_hold(
                user_id=ctx.author.id,
                name=name,
                artists=artist_list,
                genre=genre,
                payment_id=payment_id
            )
            
            if pack:
                # Create success embed
                embed = discord.Embed(
                    title="💳 Creator Pack Created!",
                    description="Your pack has been created and submitted for review",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="🆔 Pack ID", value=str(pack.id)[:8], inline=True)
                embed.add_field(name="📦 Name", value=pack.name, inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids)), inline=True)
                embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
                embed.add_field(name="💳 Payment", value=pack.payment_status.title(), inline=True)
                embed.add_field(name="📊 Status", value=pack.status.title(), inline=True)
                embed.add_field(name="💳 Payment ID", value=payment_id[:20] + "...", inline=True)
                
                embed.add_field(name="📝 Note", value="Payment authorized and pack pending review", inline=False)
                
                embed.set_footer(text=f"Created by {ctx.author.name}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to create creator pack")
                
        except ValueError as e:
            await ctx.send(f"❌ Validation error: {e}")
        except Exception as e:
            await ctx.send(f"❌ Error creating pack: {e}")
    
    @commands.command()
    async def my_payment_packs(self, ctx):
        """Show your creator packs with payment status"""
        try:
            payment_history = creator_pack_payment.get_user_payment_history(ctx.author.id)
            
            if not payment_history:
                await ctx.send("You haven't created any packs yet!")
                return
            
            embed = discord.Embed(
                title="💳 Your Creator Packs",
                description=f"You have {len(payment_history)} pack(s)",
                color=discord.Color.blue()
            )
            
            for pack_info in payment_history:
                # Determine status emoji
                status_emoji = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "disabled": "🚫"
                }.get(pack_info["status"], "❓")
                
                # Determine payment emoji
                payment_emoji = {
                    "authorized": "💳",
                    "captured": "💰",
                    "failed": "❌",
                    "refunded": "💸"
                }.get(pack_info["payment_status"], "❓")
                
                embed.add_field(
                    name=f"{status_emoji} {payment_emoji} {pack_info['pack_name']}",
                    value=f"ID: {pack_info['pack_id'][:8]} | 🎼 {pack_info['genre']} | 💰 ${pack_info['price_cents'] / 100:.2f} | 📊 {pack_info['status']} | 💳 {pack_info['payment_status']}",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting your payment packs: {e}")
    
    @commands.command()
    async def pack_payment_status(self, ctx, pack_id: str):
        """Show payment status for a pack"""
        try:
            payment_info = creator_pack_payment.get_payment_status(pack_id)
            
            if not payment_info:
                await ctx.send("❌ Pack not found")
                return
            
            pack = CreatorPack.get_by_id(pack_id)
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            # Check if user owns the pack or is admin
            if pack.owner_id != ctx.author.id and not ctx.author.guild_permissions.manage_guild:
                await ctx.send("❌ You don't have permission to view this pack's payment status")
                return
            
            embed = discord.Embed(
                title=f"💳 Payment Status: {pack.name}",
                color=discord.Color.purple()
            )
            
            embed.add_field(name="🆔 Pack ID", value=pack_id[:8], inline=True)
            embed.add_field(name="💳 Payment ID", value=payment_info["payment_id"][:20] + "...", inline=True)
            embed.add_field(name="💰 Amount", value=f"${payment_info['price_dollars']:.2f}", inline=True)
            embed.add_field(name="📊 Status", value=payment_info["payment_status"].title(), inline=True)
            embed.add_field(name="📦 Pack Status", value=pack.status.title(), inline=True)
            embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
            
            # Payment status details
            status_details = []
            if payment_info["is_authorized"]:
                status_details.append("✅ Payment Authorized")
            if payment_info["is_captured"]:
                status_details.append("💰 Payment Captured")
            if payment_info["is_failed"]:
                status_details.append("❌ Payment Failed")
            if payment_info["is_refunded"]:
                status_details.append("💸 Payment Refunded")
            
            if status_details:
                embed.add_field(name="📋 Status Details", value="\n".join(status_details), inline=False)
            
            # Actions available
            actions = []
            if payment_info["can_be_captured"]:
                actions.append("🔄 Can be captured")
            if payment_info["can_be_refunded"]:
                actions.append("💸 Can be refunded")
            
            if actions:
                embed.add_field(name="🔧 Available Actions", value="\n".join(actions), inline=False)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting payment status: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def payment_stats(self, ctx):
        """Show payment statistics"""
        try:
            stats = creator_pack_payment.get_payment_statistics()
            
            embed = discord.Embed(
                title="💳 Payment Statistics",
                color=discord.Color.gold()
            )
            
            embed.add_field(name="📦 Total Packs", value=str(stats["total_packs"]), inline=True)
            embed.add_field(name="💳 Authorized", value=str(stats["authorized"]), inline=True)
            embed.add_field(name="💰 Captured", value=str(stats["captured"]), inline=True)
            embed.add_field(name="❌ Failed", value=str(stats["failed"]), inline=True)
            embed.add_field(name="💸 Refunded", value=str(stats["refunded"]), inline=True)
            embed.add_field(name="💰 Total Revenue", value=f"${stats['total_revenue_dollars']:.2f}", inline=True)
            embed.add_field(name="💵 Average Price", value=f"${stats['average_price_dollars']:.2f}", inline=True)
            
            # Calculate success rate
            if stats["total_packs"] > 0:
                success_rate = (stats["captured"] / stats["total_packs"]) * 100
                embed.add_field(name="📈 Success Rate", value=f"{success_rate:.1f}%", inline=True)
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting payment stats: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def find_pack_by_payment(self, ctx, payment_id: str):
        """Find pack by payment ID"""
        try:
            pack = creator_pack_payment.get_pack_by_payment_id(payment_id)
            
            if not pack:
                await ctx.send("❌ No pack found with that payment ID")
                return
            
            embed = discord.Embed(
                title=f"💳 Pack Found: {pack.name}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="🆔 Pack ID", value=str(pack.id)[:8], inline=True)
            embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
            embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
            embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
            embed.add_field(name="📊 Status", value=pack.status.title(), inline=True)
            embed.add_field(name="💳 Payment Status", value=pack.payment_status.title(), inline=True)
            embed.add_field(name="📅 Created", value=pack.created_at.strftime('%Y-%m-%d %H:%M'), inline=True)
            
            if pack.reviewed_at:
                embed.add_field(name="📅 Reviewed", value=pack.reviewed_at.strftime('%Y-%m-%d %H:%M'), inline=True)
            
            embed.set_footer(text=f"Payment ID: {payment_id[:20]}...")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error finding pack: {e}")


async def setup(bot):
    await bot.add_cog(CreatorPaymentCommands(bot))
