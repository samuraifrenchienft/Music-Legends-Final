# commands/admin_preview.py
"""
Discord Admin Commands for Creator Pack Preview
"""

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from discord import Interaction, Embed, ButtonStyle
from services.creator_preview import build_preview
from services.creator_moderation import review_pack
from ui.gallery import GalleryView
from services.image_cache import safe_image, DEFAULT_IMG

class ReviewView(View):
    """Review buttons for admin approval"""
    
    def __init__(self, pack_id):
        super().__init__(timeout=180)
        self.pack_id = pack_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: Interaction, button):
        review_pack(self.pack_id, interaction.user.id, True)
        await interaction.response.send_message(
            "✅ Pack approved and captured.",
            ephemeral=True
        )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: Interaction, button):
        await interaction.response.send_modal(RejectModal(self.pack_id))

    @discord.ui.button(label="View Gallery", style=discord.ButtonStyle.primary, emoji="🖼️")
    async def gallery(self, interaction: Interaction, button):
        data = build_preview(self.pack_id)
        if data and data.get("artists"):
            await interaction.response.send_message(
                view=GalleryView(data["artists"]),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ No artists available for gallery",
                ephemeral=True
            )

    @discord.ui.button(label="Message Creator", style=discord.ButtonStyle.secondary, emoji="💬")
    async def message_creator(self, interaction: Interaction, button):
        await interaction.response.send_modal(MessageCreatorModal(self.pack_id))

class RejectModal(Modal, title="Reject Pack"):
    def __init__(self, pack_id):
        super().__init__()
        self.pack_id = pack_id
        
        self.reason = TextInput(
            label="Rejection Reason",
            placeholder="Provide a clear reason for rejection...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: Interaction):
        reason = self.reason.value.strip()
        review_pack(self.pack_id, interaction.user.id, False, reason)
        await interaction.response.send_message(
            f"❌ Pack rejected and voided.\nReason: {reason}",
            ephemeral=True
        )

class MessageCreatorModal(Modal, title="Message Creator"):
    def __init__(self, pack_id):
        super().__init__()
        self.pack_id = pack_id
        
        self.message = TextInput(
            label="Message",
            placeholder="Enter your message to the pack creator...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: Interaction):
        # In a real implementation, this would send a message to the creator
        await interaction.response.send_message(
            f"💬 Message sent to creator: {self.message.value}",
            ephemeral=True
        )

@commands.hybrid_command(name="preview", description="Preview a creator pack")
@commands.has_permissions(manage_guild=True)
async def preview(ctx, pack_id: str):
    """Enhanced admin preview with visual layout"""
    
    try:
        data = build_preview(pack_id)
        
        if not data:
            await ctx.respond("❌ Pack not found or preview unavailable", ephemeral=True)
            return
        
        # Create main preview embed
        e = discord.Embed(
            title=f"🔍 Preview – {data['name']}",
            description=f"🎼 Genre: {data['genre']} | 🎵 {data['artist_count']} artists",
            color=discord.Color.blue()
        )
        
        # Add quality information
        if data.get('quality_score'):
            quality_color = {
                "Excellent": discord.Color.green(),
                "Good": discord.Color.blue(),
                "Fair": discord.Color.gold(),
                "Poor": discord.Color.orange(),
                "Very Poor": discord.Color.red()
            }.get(data['quality_rating'], discord.Color.grey())
            
            e.color = quality_color
            e.add_field(name="⭐ Quality", value=f"{data['quality_score']}/100 ({data['quality_rating']})", inline=True)
        
        # Add tier distribution
        tier_dist = data.get('tier_distribution', {})
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
                    tier_text.append(f"{tier_emoji}{count}")
            
            e.add_field(name="🎯 Tiers", value=" ".join(tier_text), inline=True)
        
        # Add payment status
        if data.get('payment_status'):
            payment_emoji = {
                "authorized": "💳",
                "captured": "💰",
                "failed": "❌",
                "refunded": "💸"
            }.get(data['payment_status'], "❓")
            
            e.add_field(name="💳 Payment", value=f"{payment_emoji} {data['payment_status'].title()}", inline=True)
        
        # Show first artist as hero image
        artists = data.get("artists", [])
        if artists:
            hero_artist = artists[0]
            safe_url = safe_image(hero_artist.get("image"))
            if safe_url:
                e.set_image(url=safe_url)
            
            # Add hero artist info
            tier_emoji = {
                "legendary": "🏆",
                "platinum": "💎",
                "gold": "🥇",
                "silver": "🥈",
                "bronze": "🥉",
                "community": "👥"
            }.get(hero_artist.get('estimated_tier', ''), "❓")
            
            e.add_field(
                name=f"🎴 Featured Artist: {tier_emoji} {hero_artist['name']}",
                value=f"🎼 {hero_artist['genre']} • 🏆 {hero_artist.get('estimated_tier', 'Unknown')}\n"
                f"👥 {hero_artist.get('popularity', 0)} popularity • 📺 {hero_artist.get('subscribers', 0):,} subs",
                inline=False
            )
        
        # Add additional artists (limit for embed size)
        additional_artists = artists[1:10]  # Show up to 10 total artists
        if additional_artists:
            artist_list = ""
            for i, artist in enumerate(additional_artists, 2):
                tier_emoji = {
                    "legendary": "🏆",
                    "platinum": "💎",
                    "gold": "🥇",
                    "silver": "🥈",
                    "bronze": "🥉",
                    "community": "👥"
                }.get(artist.get('estimated_tier', ''), "❓")
                
                artist_list += f"{i}. {tier_emoji} **{artist['name']}** ({artist.get('estimated_tier', 'Unknown')})\n"
            
            if len(artists) > 10:
                artist_list += f"... and {len(artists) - 10} more artists"
            
            e.add_field(name="🎵 Artist Roster", value=artist_list, inline=False)
        
        # Add safety check results
        try:
            from services.safety_checks import safety_checks
            safe, safety_message = safety_checks.safe_images(data)
            
            safety_emoji = "✅" if safe else "❌"
            e.add_field(name="🛡️ Safety Check", value=f"{safety_emoji} {safety_message}", inline=True)
        except:
            pass
        
        # Add pack statistics
        if artists:
            avg_popularity = sum(a.get('popularity', 0) for a in artists) / len(artists)
            total_subscribers = sum(a.get('subscribers', 0) for a in artists)
            
            e.add_field(name="📊 Statistics", value=f"📈 Avg Popularity: {avg_popularity:.1f}\n👥 Total Subscribers: {total_subscribers:,}", inline=True)
        
        # Add footer with gallery info
        if len(artists) > 1:
            e.set_footer(text=f"🖼️ Click 'View Gallery' to see all {len(artists)} artists")
        
        # Create view with buttons
        view = ReviewView(pack_id)
        
        await ctx.respond(embed=e, view=view, ephemeral=True)
        
    except Exception as e:
        await ctx.respond(f"❌ Error generating preview: {e}", ephemeral=True)
            print(f"❌ Error running moderation checklist: {e}")
        
        return checklist
    
    @commands.command()
    async def quick_check(self, ctx, pack_id: str):
        """
        Quick safety check for a pack
        Usage: !quick_check <pack_id>
        """
        # Check admin permissions
        if not ctx.author.guild_permissions.manage_guild:
            await ctx.send("❌ You don't have permission to use this command")
            return
        
        try:
            # Build preview data
            data = build_preview(pack_id)
            
            if not data:
                await ctx.send("❌ Pack not found")
                return
            
            # Run quick checks
            checklist = self._run_moderation_checklist(data)
            safe, safety_message = self._safe_images(data)
            
            # Count passed/failed
            passed = sum(1 for result in checklist.values() if result)
            failed = len(checklist) - passed
            
            # Create result embed
            color = discord.Color.green() if failed == 0 else discord.Color.orange() if failed <= 2 else discord.Color.red
            
            embed = discord.Embed(
                title=f"🔍 Quick Check: {data['name']}",
                description=f"Pack ID: {pack_id[:8]}",
                color=color
            )
            
            embed.add_field(name="📊 Results", value=f"✅ Passed: {passed}\n❌ Failed: {failed}", inline=True)
            embed.add_field(name="🛡️ Images", value=f"{'✅' if safe else '❌'} {safety_message}", inline=True)
            embed.add_field(name="⭐ Quality", value=f"{data['quality_score']}/100 ({data['quality_rating']})", inline=True)
            
            # Show failed items if any
            failed_items = [item for item, result in checklist.items() if not result]
            if failed_items:
                embed.add_field(name="❌ Issues", value="\n".join(f"• {item}" for item in failed_items[:5]), inline=False)
            
            # Recommendation
            if failed == 0:
                recommendation = "✅ **APPROVE** - All checks passed"
            elif failed <= 2:
                recommendation = "⚠️ **REVIEW** - Minor issues, review carefully"
            else:
                recommendation = "❌ **REJECT** - Multiple issues found"
            
            embed.add_field(name="💡 Recommendation", value=recommendation, inline=False)
            
            embed.set_footer(text=f"Use !preview {pack_id[:8]} for full details")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error running quick check: {e}")


async def setup(bot):
    await bot.add_cog(AdminPreviewCommands(bot))
