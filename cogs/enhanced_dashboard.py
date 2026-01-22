# cogs/enhanced_dashboard.py
"""
Enhanced Creator Dashboard with Pack Selection
Interactive pack management with detailed views
"""

from discord.ext import commands
import discord
from discord.ui import Button, Modal, InputText, View, Select
from discord import Interaction, Embed, ButtonStyle
from typing import List, Optional, Dict, Any
from models.creator_pack import CreatorPack
from services.creator_pack_payment import creator_pack_payment
from services.creator_preview import creator_preview
from services.open_creator import open_creator_pack

class EnhancedDashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="creator_dashboard", description="Open your enhanced creator dashboard")
    async def creator_dashboard(self, ctx: Interaction):
        """Open enhanced creator dashboard with pack selection"""
        try:
            await ctx.defer()
            
            # Get user's creator packs
            user_packs = CreatorPack.get_by_owner(ctx.author.id)
            
            if not user_packs:
                embed = Embed(
                    title="🎨 Your Creator Packs",
                    description="You haven't created any packs yet!",
                    color=discord.Color.blue()
                )
                embed.add_field(name="🚀 Get Started", value="Click 'Create New Pack' to begin your creator journey!")
                await ctx.respond(embed=embed, view=EmptyDashboardView(ctx.author.id), ephemeral=True)
                return
            
            # Create dashboard with pack selection
            embed = Embed(
                title="🎨 Your Creator Packs",
                description=f"You have {len(user_packs)} pack(s). Select a pack to view details or create a new one.",
                color=discord.Color.blue()
            )
            
            # Create pack selection dropdown
            pack_options = []
            for pack in user_packs:
                status_emoji = {
                    "pending": "🟡",
                    "approved": "🟢",
                    "rejected": "🔴",
                    "disabled": "⚫"
                }.get(pack.status, "❓")
                
                payment_emoji = {
                    "authorized": "💳",
                    "captured": "💰",
                    "failed": "❌",
                    "refunded": "💸"
                }.get(pack.payment_status, "❓")
                
                description = f"{status_emoji} {pack.status.title()} | {payment_emoji} {pack.payment_status.title()} | {len(pack.artist_ids) if pack.artist_ids else 0} artists"
                
                pack_options.append(
                    discord.SelectOption(
                        label=f"{pack.name}",
                        description=description[:100],
                        value=str(pack.id),
                        emoji=status_emoji
                    )
                )
            
            view = EnhancedDashboardView(ctx.author.id, pack_options)
            await ctx.respond(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"❌ Error loading dashboard: {e}", ephemeral=True)


class EnhancedDashboardView(View):
    def __init__(self, user_id: int, pack_options: List[discord.SelectOption]):
        super().__init__(timeout=300)
        self.user_id = user_id
        
        # Add pack selection dropdown
        self.pack_select = Select(
            placeholder="📦 Select a pack to view details",
            options=pack_options[:25],  # Discord limit
            custom_id="pack_select"
        )
        self.pack_select.callback = self.pack_selected
        self.add_item(self.pack_select)
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    async def pack_selected(self, interaction: Interaction, select: Select):
        pack_id = select.values[0]
        pack = CreatorPack.get_by_id(pack_id)
        
        if not pack:
            await interaction.response.send_message("❌ Pack not found", ephemeral=True)
            return
        
        await self.show_pack_detail(interaction, pack)
    
    async def show_pack_detail(self, interaction: Interaction, pack: CreatorPack):
        """Show detailed pack view"""
        try:
            status_emoji = {
                "pending": "🟡",
                "approved": "🟢",
                "rejected": "🔴",
                "disabled": "⚫"
            }.get(pack.status, "❓")
            
            payment_emoji = {
                "authorized": "💳",
                "captured": "💰",
                "failed": "❌",
                "refunded": "💸"
            }.get(pack.payment_status, "❓")
            
            # Create detail embed
            embed = Embed(
                title=f"{status_emoji} {pack.name}",
                description=f"Pack ID: {str(pack.id)[:8]}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="🎼 Genre", value=pack.genre, inline=True)
            embed.add_field(name="📊 Status", value=f"{status_emoji} {pack.status.title()}", inline=True)
            embed.add_field(name="💳 Payment", value=f"{payment_emoji} {pack.payment_status.title()}", inline=True)
            embed.add_field(name="🎵 Artists", value=str(len(pack.artist_ids) if pack.artist_ids else 0), inline=True)
            embed.add_field(name="💰 Price", value=f"${pack.price_cents / 100:.2f}", inline=True)
            embed.add_field(name="📦 Purchases", value=str(pack.purchase_count), inline=True)
            
            # Add quality score if available
            preview = creator_preview.build_preview(str(pack.id))
            if preview:
                embed.add_field(name="⭐ Quality", value=f"{preview['quality_score']}/100 ({preview['quality_rating']})", inline=True)
                
                # Add tier distribution
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
                            tier_text.append(f"{tier_emoji}{count}")
                    
                    embed.add_field(name="🎯 Tiers", value=" ".join(tier_text), inline=True)
            
            # Add timestamps
            if pack.created_at:
                embed.add_field(name="📅 Created", value=pack.created_at.strftime("%Y-%m-%d"), inline=True)
            
            if pack.reviewed_at:
                embed.add_field(name="📅 Reviewed", value=pack.reviewed_at.strftime("%Y-%m-%d"), inline=True)
            
            # Add notes if any
            if pack.notes:
                embed.add_field(name="📝 Notes", value=pack.notes, inline=False)
            
            if pack.rejection_reason:
                embed.add_field(name="❌ Rejection Reason", value=pack.rejection_reason, inline=False)
            
            # Create action buttons based on status
            view = PackDetailActionsView(pack, interaction.user.id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error showing pack details: {e}", ephemeral=True)
    
    @discord.ui.button(label="Create New Pack", style=ButtonStyle.primary, emoji="➕", row=2)
    async def create_pack_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(CreatePackModal(interaction.user.id))
    
    @discord.ui.button(label="View Collection", style=ButtonStyle.secondary, emoji="📚", row=2)
    async def collection_button(self, interaction: Interaction, button: Button):
        # Import here to avoid circular imports
        from cogs.collection_browser import collection_browser
        await collection_browser.show_collection(interaction)
    
    @discord.ui.button(label="Help", style=ButtonStyle.secondary, emoji="❓", row=2)
    async def help_button(self, interaction: Interaction, button: Button):
        embed = Embed(
            title="📚 Creator Dashboard Help",
            description="How to use the creator dashboard",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🎨 Managing Packs",
            value="• Select packs from dropdown to view details\n• Create new packs with 'Create New Pack'\n• Edit pending or rejected packs\n• Open approved packs to get cards",
            inline=False
        )
        
        embed.add_field(
            name="💰 Payment & Status",
            value="• 🟡 Pending - Under admin review\n• 🟢 Approved - Available for opening\n• 🔴 Rejected - Not approved\n• 💳 Authorized - Payment held\n• 💰 Captured - Payment processed",
            inline=False
        )
        
        embed.add_field(
            name="📊 Quality Metrics",
            value="• Quality score (0-100) indicates pack quality\n• Tier distribution shows expected card rarities\n• Higher quality packs may have better cards",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PackDetailActionsView(View):
    def __init__(self, pack: CreatorPack, user_id: int):
        super().__init__(timeout=300)
        self.pack = pack
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Preview Artists", style=ButtonStyle.primary, emoji="👁️")
    async def preview_artists_button(self, interaction: Interaction, button: Button):
        preview = creator_preview.build_preview(str(self.pack.id))
        
        if not preview:
            await interaction.response.send_message("❌ Could not generate preview", ephemeral=True)
            return
        
        embed = Embed(
            title=f"👁️ Artist Preview: {self.pack.name}",
            description=f"Genre: {self.pack.genre} | Artists: {len(preview['artists'])} | Quality: {preview['quality_score']}/100",
            color=discord.Color.blue()
        )
        
        # Show artists in chunks
        artists_per_embed = 10
        artist_chunks = [preview['artists'][i:i+artists_per_embed] for i in range(0, len(preview['artists']), artists_per_embed)]
        
        for i, chunk in enumerate(artist_chunks, 1):
            if i > 1:  # Send additional embeds as follow-ups
                chunk_embed = Embed(
                    title=f"👁️ Artist Preview (continued)",
                    description=f"Artists {((i-1)*artists_per_embed)+1}-{min(i*artists_per_embed, len(preview['artists']))}",
                    color=discord.Color.blue()
                )
                
                for artist in chunk:
                    tier_emoji = {
                        "legendary": "🏆",
                        "platinum": "💎",
                        "gold": "🥇",
                        "silver": "🥈",
                        "bronze": "🥉",
                        "community": "👥"
                    }.get(artist['estimated_tier'], "❓")
                    
                    chunk_embed.add_field(
                        name=f"{tier_emoji} {artist['name']}",
                        value=f"Genre: {artist['genre']} | Tier: {artist['estimated_tier']}\nPopularity: {artist['popularity']} | Subscribers: {artist['subscribers']:,}",
                        inline=False
                    )
                
                await interaction.followup.send(embed=chunk_embed, ephemeral=True)
            else:
                for artist in chunk:
                    tier_emoji = {
                        "legendary": "🏆",
                        "platinum": "💎",
                        "gold": "🥇",
                        "silver": "🥈",
                        "bronze": "🥉",
                        "community": "👥"
                    }.get(artist['estimated_tier'], "❓")
                    
                    embed.add_field(
                        name=f"{tier_emoji} {artist['name']}",
                        value=f"Genre: {artist['genre']} | Tier: {artist['estimated_tier']}\nPopularity: {artist['popularity']} | Subscribers: {artist['subscribers']:,}",
                        inline=False
                    )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Open Pack", style=ButtonStyle.success, emoji="📦")
    async def open_pack_button(self, interaction: Interaction, button: Button):
        if self.pack.status != "approved" or self.pack.payment_status != "captured":
            await interaction.response.send_message("❌ Pack is not available for opening", ephemeral=True)
            return
        
        try:
            cards = open_creator_pack(self.pack)
            
            if cards:
                embed = Embed(
                    title="📦 Pack Opened!",
                    description=f"You got {len(cards)} cards from {self.pack.name}",
                    color=discord.Color.green()
                )
                
                # Show card details
                for card in cards:
                    tier_emoji = {
                        "legendary": "🏆",
                        "platinum": "💎",
                        "gold": "🥇",
                        "silver": "🥈",
                        "bronze": "🥉",
                        "community": "👥"
                    }.get(card.tier, "❓")
                    
                    embed.add_field(
                        name=f"🎴 {tier_emoji} {card.artist_name}",
                        value=f"Tier: {card.tier} | Serial: {card.serial}",
                        inline=False
                    )
                
                embed.set_footer(text=f"Pack purchases: {self.pack.purchase_count + 1}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to open pack", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error opening pack: {e}", ephemeral=True)
    
    @discord.ui.button(label="Edit", style=ButtonStyle.secondary, emoji="✏️")
    async def edit_button(self, interaction: Interaction, button: Button):
        if self.pack.status not in ["pending", "rejected"]:
            await interaction.response.send_message("❌ Can only edit pending or rejected packs", ephemeral=True)
            return
        
        await interaction.response.send_modal(EditPackModal(self.pack, self.user_id))
    
    @discord.ui.button(label="Delete", style=ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, interaction: Interaction, button: Button):
        if self.pack.status == "approved":
            await interaction.response.send_message("❌ Cannot delete approved packs", ephemeral=True)
            return
        
        # Confirmation embed
        embed = Embed(
            title="🗑️ Delete Pack",
            description=f"Are you sure you want to delete '{self.pack.name}'? This action cannot be undone.",
            color=discord.Color.red()
        )
        
        embed.add_field(name="📦 Pack Details", value=f"Genre: {self.pack.genre}\nArtists: {len(self.pack.artist_ids) if self.pack.artist_ids else 0}", inline=False)
        embed.add_field(name="⚠️ Warning", value="All pack data will be permanently deleted", inline=False)
        
        view = DeleteConfirmView(self.pack, self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class DeleteConfirmView(View):
    def __init__(self, pack: CreatorPack, user_id: int):
        super().__init__(timeout=60)
        self.pack = pack
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Confirm Delete", style=ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: Interaction, button: Button):
        try:
            pack_name = self.pack.name
            
            # Delete the pack
            self.pack.delete()
            
            embed = Embed(
                title="🗑️ Pack Deleted",
                description=f"Your pack '{pack_name}' has been permanently deleted.",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deleting pack: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel_delete(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Pack deletion cancelled", ephemeral=True)


# Re-use existing classes from creator_dashboard.py
class EmptyDashboardView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Create New Pack", style=ButtonStyle.primary, emoji="➕")
    async def create_pack_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(CreatePackModal(self.user_id))
    
    @discord.ui.button(label="View Collection", style=ButtonStyle.secondary, emoji="📚")
    async def collection_button(self, interaction: Interaction, button: Button):
        # Import here to avoid circular imports
        from cogs.collection_browser import collection_browser
        await collection_browser.show_collection(interaction)
    
    @discord.ui.button(label="Help", style=ButtonStyle.secondary, emoji="❓")
    async def help_button(self, interaction: Interaction, button: Button):
        embed = Embed(
            title="📚 Creator Dashboard Help",
            description="How to use the creator dashboard",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🎨 Creating Packs",
            value="1. Click 'Create New Pack'\n2. Fill in pack details\n3. Submit for review\n4. Authorize payment\n5. Wait for admin approval",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class CreatePackModal(Modal):
    def __init__(self, user_id: int):
        super().__init__(title="Create New Creator Pack")
        self.user_id = user_id
        
        self.add_item(InputText(
            label="Pack Name",
            placeholder="Enter your pack name (max 60 chars)",
            max_length=60,
            required=True
        ))
        
        self.add_item(InputText(
            label="Genre",
            placeholder="e.g., Rock, Pop, Jazz, Hip-Hop",
            max_length=20,
            required=True
        ))
        
        self.add_item(InputText(
            label="Artist List",
            placeholder="Enter artist names, separated by commas",
            style=discord.InputTextStyle.long,
            required=True
        ))
    
    async def callback(self, interaction: Interaction):
        try:
            pack_name = self.children[0].value.strip()
            genre = self.children[1].value.strip()
            artists_raw = self.children[2].value.strip()
            
            # Parse artists
            artists = [artist.strip() for artist in artists_raw.split(',') if artist.strip()]
            
            # Validation
            if not pack_name or not genre or not artists:
                await interaction.response.send_message("❌ All fields are required", ephemeral=True)
                return
            
            if len(artists) < 5 or len(artists) > 25:
                await interaction.response.send_message("❌ Artist count must be 5-25", ephemeral=True)
                return
            
            # Create pack
            pack = creator_pack_payment.create_pack_with_hold(
                user_id=self.user_id,
                name=pack_name,
                artists=artists,
                genre=genre,
                payment_id="pending_payment",
                price_cents=999
            )
            
            if pack:
                embed = Embed(
                    title="✅ Pack Submitted for Review",
                    description=f"Your pack '{pack_name}' has been submitted for admin review.",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="📦 Pack Details", value=f"Name: {pack_name}\nGenre: {genre}\nArtists: {len(artists)}", inline=False)
                embed.add_field(name="💰 Payment", value="Payment authorization required ($9.99)", inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to create pack", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating pack: {e}", ephemeral=True)


class EditPackModal(Modal):
    def __init__(self, pack: CreatorPack, user_id: int):
        super().__init__(title="Edit Creator Pack")
        self.pack = pack
        self.user_id = user_id
        
        self.add_item(InputText(
            label="Pack Name",
            value=pack.name,
            max_length=60,
            required=True
        ))
        
        self.add_item(InputText(
            label="Genre",
            value=pack.genre,
            max_length=20,
            required=True
        ))
        
        self.add_item(InputText(
            label="Artist List",
            value=", ".join(pack.artist_ids) if pack.artist_ids else "",
            style=discord.InputTextStyle.long,
            required=True
        ))
    
    async def callback(self, interaction: Interaction):
        try:
            pack_name = self.children[0].value.strip()
            genre = self.children[1].value.strip()
            artists_raw = self.children[2].value.strip()
            
            # Parse artists
            artists = [artist.strip() for artist in artists_raw.split(',') if artist.strip()]
            
            # Validation
            if not pack_name or not genre or not artists:
                await interaction.response.send_message("❌ All fields are required", ephemeral=True)
                return
            
            if len(artists) < 5 or len(artists) > 25:
                await interaction.response.send_message("❌ Artist count must be 5-25", ephemeral=True)
                return
            
            # Update pack
            self.pack.name = pack_name
            self.pack.genre = genre
            self.pack.artist_ids = artists
            self.pack.save()
            
            embed = Embed(
                title="✅ Pack Updated",
                description=f"Your pack '{pack_name}' has been updated.",
                color=discord.Color.green()
            )
            
            embed.add_field(name="📦 Updated Details", value=f"Name: {pack_name}\nGenre: {genre}\nArtists: {len(artists)}", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating pack: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(EnhancedDashboard(bot))
