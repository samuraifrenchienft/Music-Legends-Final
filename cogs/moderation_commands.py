# cogs/moderation_commands.py
"""
Admin Commands for Creator Pack Moderation
"""

from discord.ext import commands
import discord
from services.creator_moderation import creator_moderation
from models.creator_pack import CreatorPack

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    @commands.is_owner()  # Admin only
    async def pending_packs(self, ctx, limit: int = 10):
        """Show pending creator packs for review"""
        try:
            pending = creator_moderation.get_pending_reviews(limit)
            
            if not pending:
                await ctx.send("No pending packs to review!")
                return
            
            embed = discord.Embed(
                title="📋 Pending Creator Packs",
                description=f"Found {len(pending)} pending packs",
                color=discord.Color.orange()
            )
            
            for i, review in enumerate(pending, 1):
                pack = CreatorPack.get_by_id(review["pack_id"])
                
                if pack:
                    embed.add_field(
                        name=f"{i}. {pack.name}",
                        value=f"ID: {review['pack_id'][:8]} | "
                              f"User: {review['user_id']} | "
                              f"Artists: {review['artist_count']} | "
                              f"Submitted: {review['submitted_at'].strftime('%Y-%m-%d')}",
                        inline=False
                    )
            
            embed.set_footer(text=f"Use !approve <pack_id> or !reject <pack_id> <reason>")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting pending packs: {e}")
    
    @commands.command()
    @commands.is_owner()  # Admin only
    async def approve_pack(self, ctx, pack_id: str, *, notes: str = ""):
        """Approve a pending creator pack"""
        try:
            # Get pack details first
            pack = CreatorPack.get_by_id(pack_id)
            
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            if pack.status != "pending":
                await ctx.send(f"❌ Pack is not pending (current status: {pack.status})")
                return
            
            # Approve the pack
            success = creator_moderation.approve_pack(pack_id, ctx.author.id, notes)
            
            if success:
                embed = discord.Embed(
                    title="✅ Pack Approved",
                    description=f"Successfully approved pack: {pack.name}",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📦 Pack ID", value=pack_id[:8], inline=True)
                embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids)), inline=True)
                
                if notes:
                    embed.add_field(name="📝 Notes", value=notes, inline=False)
                
                embed.set_footer(text=f"Approved by {ctx.author.name}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to approve pack")
                
        except Exception as e:
            await ctx.send(f"❌ Error approving pack: {e}")
    
    @commands.command()
    @commands.is_owner()  # Admin only
    async def reject_pack(self, ctx, pack_id: str, *, reason: str):
        """Reject a pending creator pack"""
        try:
            # Get pack details first
            pack = CreatorPack.get_by_id(pack_id)
            
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            if pack.status != "pending":
                await ctx.send(f"❌ Pack is not pending (current status: {pack.status})")
                return
            
            # Reject the pack
            success = creator_moderation.reject_pack(pack_id, ctx.author.id, reason)
            
            if success:
                embed = discord.Embed(
                    title="❌ Pack Rejected",
                    description=f"Rejected pack: {pack.name}",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="📦 Pack ID", value=pack_id[:8], inline=True)
                embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="📝 Reason", value=reason, inline=False)
                
                embed.set_footer(text=f"Rejected by {ctx.author.name}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to reject pack")
                
        except Exception as e:
            await ctx.send(f"❌ Error rejecting pack: {e}")
    
    @commands.command()
    @commands.is_owner()  # Admin only
    async def disable_pack(self, ctx, pack_id: str, *, reason: str):
        """Disable an approved creator pack"""
        try:
            # Get pack details first
            pack = CreatorPack.get_by_id(pack_id)
            
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            if pack.status != "approved":
                await ctx.send(f"❌ Pack is not approved (current status: {pack.status})")
                return
            
            # Disable the pack
            success = creator_moderation.disable_pack(pack_id, ctx.author.id, reason)
            
            if success:
                embed = discord.Embed(
                    title="🚫 Pack Disabled",
                    description=f"Disabled pack: {pack.name}",
                    color=discord.Color.dark_grey()
                )
                
                embed.add_field(name="📦 Pack ID", value=pack_id[:8], inline=True)
                embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
                embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
                embed.add_field(name="📝 Reason", value=reason, inline=False)
                
                embed.add_field(name="📊 Stats", value=f"Purchases: {pack.purchase_count}", inline=True)
                
                embed.set_footer(text=f"Disabled by {ctx.author.name}")
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ Failed to disable pack")
                
        except Exception as e:
            await ctx.send(f"❌ Error disabling pack: {e}")
    
    @commands.command()
    @commands.is_owner()  # Admin only
    async def moderation_stats(self, ctx):
        """Show moderation statistics"""
        try:
            stats = creator_moderation.get_moderation_stats()
            
            embed = discord.Embed(
                title="📊 Moderation Statistics",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="📦 Total Packs", value=str(stats['total_packs']), inline=True)
            embed.add_field(name="⏳ Pending", value=str(stats['pending_packs']), inline=True)
            embed.add_field(name="✅ Approved", value=str(stats['approved_packs']), inline=True)
            embed.add_field(name="❌ Rejected", value=str(stats['rejected_packs']), inline=True)
            embed.add_field(name="📈 Approval Rate", value=f"{stats['approval_rate']:.1f}%", inline=True)
            embed.add_field(name="👥 Approved Creators", value=str(stats['approved_creators']), inline=True)
            
            embed.set_footer(text=f"Requested by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting moderation stats: {e}")
    
    @commands.command()
    @commands.is_owner()  # Admin only
    async def pack_info(self, ctx, pack_id: str):
        """Show detailed information about a pack"""
        try:
            pack = CreatorPack.get_by_id(pack_id)
            
            if not pack:
                await ctx.send("❌ Pack not found")
                return
            
            embed = discord.Embed(
                title=f"📦 Pack Information: {pack.name}",
                color=discord.Color.blue()
            )
            
            # Basic info
            embed.add_field(name="🆔 Pack ID", value=str(pack.id)[:8], inline=True)
            embed.add_field(name="👤 Owner", value=str(pack.owner_id), inline=True)
            embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
            embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids)), inline=True)
            embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
            embed.add_field(name="📊 Status", value=pack.status.title(), inline=True)
            
            # Moderation info
            embed.add_field(name="👤 Reviewed By", value=str(pack.reviewed_by) if pack.reviewed_by else "Not reviewed", inline=True)
            embed.add_field(name="📅 Reviewed At", value=pack.reviewed_at.strftime('%Y-%m-%d %H:%M') if pack.reviewed_at else "Not reviewed", inline=True)
            embed.add_field(name="📝 Notes", value=pack.notes or "No notes", inline=True)
            
            if pack.rejection_reason:
                embed.add_field(name="❌ Rejection Reason", value=pack.rejection_reason, inline=False)
            
            # Stats
            embed.add_field(name="🛒 Purchases", value=str(pack.purchase_count), inline=True)
            embed.add_field(name="⭐ Rating", value=f"{pack.rating}/5", inline=True)
            embed.add_field(name="🌟 Featured", value="Yes" if pack.featured == "true" else "No", inline=True)
            
            # Timestamps
            embed.add_field(name="📅 Created", value=pack.created_at.strftime('%Y-%m-%d %H:%M'), inline=True)
            embed.add_field(name="📅 Updated", value=pack.updated_at.strftime('%Y-%m-%d %H:%M'), inline=True)
            
            # Artists
            artists = pack.get_artists()
            if artists:
                artist_list = []
                for artist in artists[:5]:
                    artist_list.append(f"🎵 {artist.name} ({artist.tier})")
                
                if len(artists) > 5:
                    artist_list.append(f"... and {len(artists) - 5} more")
                
                embed.add_field(name=f"🎵 Artists ({len(artists)})", value="\n".join(artist_list), inline=False)
            
            embed.set_footer(text=f"Pack ID: {pack_id[:8]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting pack info: {e}")
    
    @commands.command()
    @commands.is_owner()  # Admin only
    async def validate_pack_test(self, ctx, name: str, *, artists: str):
        """Test pack validation"""
        try:
            artist_list = [a.strip() for a in artists.split(',')]
            
            # Run validation
            is_valid, message = creator_moderation.validate_pack(name, artist_list, ctx.author.id)
            
            if is_valid:
                embed = discord.Embed(
                    title="✅ Pack Validation Passed",
                    description=f"Pack '{name}' with {len(artist_list)} artists is valid",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Pack Validation Failed",
                    description=f"Pack '{name}' failed validation",
                    color=discord.Color.red()
                )
                embed.add_field(name="Error", value=message, inline=False)
            
            # Show artists
            if artist_list:
                embed.add_field(name="🎵 Artists", value="\n".join([f"• {a}" for a in artist_list]), inline=False)
            
            embed.set_footer(text=f"Validation by {ctx.author.name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error validating pack: {e}")


async def setup(bot):
    await bot.add_cog(ModerationCommands(bot))
