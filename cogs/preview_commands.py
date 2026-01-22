# cogs/preview_commands.py
"""
Discord Commands for Creator Pack Preview System
"""

from discord.ext import commands
import discord
from services.creator_preview import creator_preview, build_preview
from models.creator_pack import CreatorPack

class PreviewCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def preview_pack(self, ctx, pack_id: str):
        """
        Show detailed preview of a creator pack
        Usage: !preview_pack <pack_id>
        """
        try:
            await ctx.trigger_typing()
            
            # Build preview
            preview = creator_preview.build_preview(pack_id)
            
            if not preview:
                await ctx.send("❌ Pack not found")
                return
            
            # Create main embed
            embed = discord.Embed(
                title=f"🎨 Pack Preview: {preview['name']}",
                description=f"Comprehensive preview for admin review",
                color=discord.Color.blue()
            )
            
            # Basic info
            embed.add_field(name="🆔 Pack ID", value=preview['pack_id'][:8], inline=True)
            embed.add_field(name="🎼 Genre", value=preview['genre'], inline=True)
            embed.add_field(name="📊 Status", value=preview['status'].title(), inline=True)
            embed.add_field(name="💳 Payment", value=preview['payment_status'].title(), inline=True)
            embed.add_field(name="💰 Price", value=f"${preview['price_dollars']:.2f}", inline=True)
            embed.add_field(name="👤 Owner", value=str(preview['owner_id']), inline=True)
            
            # Quality assessment
            quality_color = {
                "Excellent": discord.Color.green(),
                "Good": discord.Color.blue(),
                "Fair": discord.Color.gold(),
                "Poor": discord.Color.orange(),
                "Very Poor": discord.Color.red()
            }.get(preview['quality_rating'], discord.Color.grey())
            
            embed.add_field(name="⭐ Quality Score", value=f"{preview['quality_score']}/100", inline=True)
            embed.add_field(name="🏆 Quality Rating", value=preview['quality_rating'], inline=True)
            
            # Statistics
            embed.add_field(name="🎵 Artists", value=str(preview['artist_count']), inline=True)
            embed.add_field(name="📺 YouTube Data", value="✅" if preview['has_youtube_data'] else "❌", inline=True)
            embed.add_field(name="📊 Avg Popularity", value=str(preview['avg_popularity']), inline=True)
            
            # Tier distribution
            tier_dist = preview['tier_distribution']
            if any(tier_dist.values()):
                tier_text = []
                for tier, count in tier_dist.items():
                    if count > 0:
                        tier_emoji = {
                            "legendary": "🏆",
                            "platinum": "💎",
                            "gold": "🥇",
                            "silver": "🥈",
                            "bronze": "🥉",
                            "community": "👥"
                        }.get(tier, "❓")
                        tier_text.append(f"{tier_emoji} {tier.title()}: {count}")
                
                embed.add_field(name="🎯 Tier Distribution", value=" | ".join(tier_text), inline=False)
            
            # Genre distribution
            genre_dist = preview['genre_distribution']
            if len(genre_dist) > 1:
                genre_text = []
                for genre, count in list(genre_dist.items())[:3]:
                    genre_text.append(f"{genre}: {count}")
                
                embed.add_field(name="🎼 Genre Mix", value=" | ".join(genre_text), inline=False)
            
            # Timestamps
            embed.add_field(name="📅 Created", value=preview['created_at'][:10] if preview['created_at'] else "N/A", inline=True)
            if preview['reviewed_at']:
                embed.add_field(name="📅 Reviewed", value=preview['reviewed_at'][:10], inline=True)
            
            embed.set_footer(text=f"Preview generated at {preview['preview_generated_at'][:19]}")
            await ctx.send(embed=embed)
            
            # Show artist roster in separate embed if many artists
            if preview['artists'] and len(preview['artists']) > 0:
                await self._show_artist_roster(ctx, preview)
                
        except Exception as e:
            await ctx.send(f"❌ Error generating preview: {e}")
    
    async def _show_artist_roster(self, ctx, preview):
        """Show detailed artist roster"""
        artists = preview['artists']
        
        # Split into chunks if too many artists
        chunk_size = 10
        artist_chunks = [artists[i:i + chunk_size] for i in range(0, len(artists), chunk_size)]
        
        for i, chunk in enumerate(artist_chunks, 1):
            embed = discord.Embed(
                title=f"🎵 Artist Roster ({i}/{len(artist_chunks)})",
                description=f"Showing {len(chunk)} artists",
                color=discord.Color.purple()
            )
            
            for artist in chunk:
                # Artist name with tier
                tier_emoji = {
                    "legendary": "🏆",
                    "platinum": "💎",
                    "gold": "🥇",
                    "silver": "🥈",
                    "bronze": "🥉",
                    "community": "👥"
                }.get(artist['estimated_tier'], "❓")
                
                artist_info = f"{tier_emoji} **{artist['name']}** ({artist['estimated_tier'].title()})"
                
                # Add stats if available
                if artist['subscribers'] > 0:
                    artist_info += f"\n   👥 {artist['subscribers']:,} subscribers"
                
                if artist['views'] > 0:
                    artist_info += f"\n   📺 {artist['views']:,} views"
                
                # Add genre
                artist_info += f"\n   🎼 {artist['genre']}"
                
                embed.add_field(
                    name=f"🎵 {artist['name']}",
                    value=artist_info,
                    inline=False
                )
            
            embed.set_footer(text=f"Pack: {preview['name']} | Chunk {i}/{len(artist_chunks)}")
            await ctx.send(embed=embed)
    
    @commands.command()
    async def preview_summary(self, ctx, pack_id: str):
        """
        Show quick summary of pack preview
        Usage: !preview_summary <pack_id>
        """
        try:
            await ctx.trigger_typing()
            
            # Get summary
            summary = creator_preview.get_preview_summary(pack_id)
            
            if not summary:
                await ctx.send("❌ Pack not found")
                return
            
            # Create summary embed
            embed = discord.Embed(
                title=f"📋 Pack Summary: {summary['name']}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="🆔 Pack ID", value=summary['pack_id'][:8], inline=True)
            embed.add_field(name="🎼 Genre", value=summary['genre'], inline=True)
            embed.add_field(name="📊 Status", value=summary['status'].title(), inline=True)
            embed.add_field(name="💳 Payment", value=summary['payment_status'].title(), inline=True)
            embed.add_field(name="💰 Price", value=f"${summary['price_dollars']:.2f}", inline=True)
            embed.add_field(name="🎵 Artists", value=str(summary['artist_count']), inline=True)
            
            # Quality info
            quality_color = {
                "Excellent": discord.Color.green(),
                "Good": discord.Color.blue(),
                "Fair": discord.Color.gold(),
                "Poor": discord.Color.orange(),
                "Very Poor": discord.Color.red()
            }.get(summary['quality_rating'], discord.Color.grey())
            
            embed.color = quality_color
            embed.add_field(name="⭐ Quality", value=f"{summary['quality_score']}/100 ({summary['quality_rating']})", inline=True)
            
            # Top tiers
            if summary['top_tiers']:
                embed.add_field(name="🎯 Top Tiers", value=" | ".join(summary['top_tiers'][:3]), inline=False)
            
            # YouTube data
            embed.add_field(name="📺 YouTube", value="✅" if summary['has_youtube_data'] else "❌", inline=True)
            
            embed.set_footer(text=f"Summary generated at {summary['preview_generated_at'][:19]}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error generating summary: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def compare_packs(self, ctx, *pack_ids: str):
        """
        Compare multiple creator packs
        Usage: !compare_packs <pack_id1> <pack_id2> ...
        """
        try:
            await ctx.trigger_typing()
            
            if len(pack_ids) < 2:
                await ctx.send("❌ Please provide at least 2 pack IDs to compare")
                return
            
            if len(pack_ids) > 5:
                await ctx.send("❌ Cannot compare more than 5 packs at once")
                return
            
            # Build comparison
            comparison = creator_preview.build_comparison_preview(list(pack_ids))
            
            if not comparison:
                await ctx.send("❌ No valid packs found for comparison")
                return
            
            # Create comparison embed
            embed = discord.Embed(
                title="📊 Pack Comparison",
                description=f"Comparing {comparison['pack_count']} packs",
                color=discord.Color.gold()
            )
            
            # Overall stats
            embed.add_field(name="📦 Packs", value=str(comparison['pack_count']), inline=True)
            embed.add_field(name="🎵 Total Artists", value=str(comparison['total_artists']), inline=True)
            embed.add_field(name="⭐ Avg Quality", value=f"{comparison['avg_quality_score']:.1f}/100", inline=True)
            embed.add_field(name="💰 Avg Price", value=f"${comparison['avg_price'] / 100:.2f}", inline=True)
            
            # Best pack
            best_pack = comparison['best_quality_pack']
            embed.add_field(
                name="🏆 Best Quality",
                value=f"{best_pack['name']} ({best_pack['quality_score']}/100)",
                inline=True
            )
            
            # Most expensive
            most_expensive = comparison['most_expensive_pack']
            embed.add_field(
                name="💸 Most Expensive",
                value=f"{most_expensive['name']} (${most_expensive['price_dollars']:.2f})",
                inline=True
            )
            
            embed.set_footer(text=f"Comparison generated at {comparison['comparison_generated_at'][:19]}")
            await ctx.send(embed=embed)
            
            # Show individual pack summaries
            for pack in comparison['packs']:
                summary_embed = discord.Embed(
                    title=f"📋 {pack['name']}",
                    color=discord.Color.blue()
                )
                
                summary_embed.add_field(name="🆔 ID", value=pack['pack_id'][:8], inline=True)
                summary_embed.add_field(name="🎼 Genre", value=pack['genre'], inline=True)
                summary_embed.add_field(name="💰 Price", value=f"${pack['price_dollars']:.2f}", inline=True)
                summary_embed.add_field(name="🎵 Artists", value=str(pack['artist_count']), inline=True)
                summary_embed.add_field(name="⭐ Quality", value=f"{pack['quality_score']}/100", inline=True)
                summary_embed.add_field(name="📊 Status", value=pack['status'].title(), inline=True)
                
                # Top tiers
                tier_dist = pack['tier_distribution']
                if any(tier_dist.values()):
                    top_tiers = []
                    for tier, count in tier_dist.items():
                        if count > 0:
                            tier_emoji = {
                                "legendary": "🏆",
                                "platinum": "💎",
                                "gold": "🥇",
                                "silver": "🥈",
                                "bronze": "🥉",
                                "community": "👥"
                            }.get(tier, "❓")
                            top_tiers.append(f"{tier_emoji}{count}")
                    
                    summary_embed.add_field(name="🎯 Tiers", value=" ".join(top_tiers), inline=False)
                
                await ctx.send(embed=summary_embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error comparing packs: {e}")
    
    @commands.command()
    @commands.has_permissions(manage_guild=True)  # Admin only
    async def pending_previews(self, ctx, limit: int = 10):
        """
        Show previews for pending packs
        Usage: !pending_previews [limit]
        """
        try:
            await ctx.trigger_typing()
            
            # Get pending packs
            pending_packs = CreatorPack.get_pending(limit)
            
            if not pending_packs:
                await ctx.send("No pending packs to preview!")
                return
            
            # Build previews for pending packs
            previews = []
            for pack in pending_packs:
                summary = creator_preview.get_preview_summary(str(pack.id))
                if summary:
                    previews.append(summary)
            
            if not previews:
                await ctx.send("No valid previews found for pending packs")
                return
            
            # Create overview embed
            embed = discord.Embed(
                title="📋 Pending Pack Previews",
                description=f"Found {len(previews)} pending packs",
                color=discord.Color.orange()
            )
            
            # Show quick summaries
            for i, preview in enumerate(previews, 1):
                quality_emoji = {
                    "Excellent": "🟢",
                    "Good": "🔵",
                    "Fair": "🟡",
                    "Poor": "🟠",
                    "Very Poor": "🔴"
                }.get(preview['quality_rating'], "⚪")
                
                embed.add_field(
                    name=f"{i}. {preview['name']}",
                    value=f"ID: {preview['pack_id'][:8]} | 🎼 {preview['genre']} | 🎵 {preview['artist_count']} | {quality_emoji} {preview['quality_score']}/100 | 💰 ${preview['price_dollars']:.2f}",
                    inline=False
                )
            
            embed.set_footer(text=f"Use !preview_pack <id> for detailed view")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error getting pending previews: {e}")


async def setup(bot):
    await bot.add_cog(PreviewCommands(bot))
