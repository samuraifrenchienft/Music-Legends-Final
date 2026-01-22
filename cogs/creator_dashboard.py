# cogs/creator_dashboard.py
"""
Creator Dashboard Cog
User flow for creator pack management
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

class CreatorDashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="creator_dashboard", description="Open your creator dashboard")
    async def creator_dashboard(self, ctx: Interaction):
        """Open creator dashboard"""
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
            
            # Create dashboard embed
            embed = Embed(
                title="🎨 Your Creator Packs",
                description=f"You have {len(user_packs)} pack(s)",
                color=discord.Color.blue()
            )
            
            # Add pack fields
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
                
                field_value = f"Status: {status_emoji} {pack.status.title()}\n"
                field_value += f"Payment: {payment_emoji} {pack.payment_status.title()}\n"
                field_value += f"Artists: {len(pack.artist_ids) if pack.artist_ids else 0}\n"
                field_value += f"Price: ${pack.price_cents / 100:.2f}"
                
                embed.add_field(
                    name=f"{status_emoji} {pack.name}",
                    value=field_value,
                    inline=False
                )
            
            await ctx.respond(embed=embed, view=DashboardView(ctx.author.id), ephemeral=True)
            
        except Exception as e:
            await ctx.respond(f"❌ Error loading dashboard: {e}", ephemeral=True)


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
        
        embed.add_field(
            name="💰 Payment Process",
            value="• $9.99 per pack\n• Payment authorized on creation\n• Captured only if approved\n• Refunded if rejected",
            inline=False
        )
        
        embed.add_field(
            name="📊 Pack Status",
            value="🟡 Pending - Under review\n🟢 Approved - Available for opening\n🔴 Rejected - Not approved\n⚫ Disabled - Previously approved but disabled",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DashboardView(View):
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
            name="🎨 Managing Packs",
            value="• Click on pack names to view details\n• Edit packs that are pending/rejected\n• Open approved packs to get cards\n• Delete unwanted packs",
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
            if not pack_name:
                await interaction.response.send_message("❌ Pack name is required", ephemeral=True)
                return
            
            if not genre:
                await interaction.response.send_message("❌ Genre is required", ephemeral=True)
                return
            
            if not artists or len(artists) < 5:
                await interaction.response.send_message("❌ Minimum 5 artists required", ephemeral=True)
                return
            
            if len(artists) > 25:
                await interaction.response.send_message("❌ Maximum 25 artists allowed", ephemeral=True)
                return
            
            # Create pack (without payment for now)
            pack = creator_pack_payment.create_pack_with_hold(
                user_id=self.user_id,
                name=pack_name,
                artists=artists,
                genre=genre,
                payment_id="pending_payment",  # Will be updated later
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
                embed.add_field(name="📊 Status", value="Your pack is now pending admin review", inline=False)
                
                await interaction.response.send_message(embed=embed, view=PackActionsView(pack.id, self.user_id), ephemeral=True)
            else:
                await interaction.response.send_message("❌ Failed to create pack", ephemeral=True)
                
        except ValueError as e:
            await interaction.response.send_message(f"❌ Validation error: {e}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating pack: {e}", ephemeral=True)


class PackActionsView(View):
    def __init__(self, pack_id: str, user_id: int):
        super().__init__(timeout=300)
        self.pack_id = pack_id
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Authorize Payment", style=ButtonStyle.primary, emoji="💳")
    async def authorize_payment_button(self, interaction: Interaction, button: Button):
        # In a real implementation, this would integrate with Stripe
        embed = Embed(
            title="💳 Payment Authorization",
            description="Payment integration would be handled here",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="💰 Amount", value="$9.99", inline=True)
        embed.add_field(name="📦 Pack ID", value=self.pack_id[:8], inline=True)
        embed.add_field(name="🔄 Status", value="Ready for authorization", inline=True)
        
        embed.add_field(
            name="📝 Note",
            value="In production, this would open a Stripe payment modal",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Edit Artists", style=ButtonStyle.secondary, emoji="✏️")
    async def edit_artists_button(self, interaction: Interaction, button: Button):
        pack = CreatorPack.get_by_id(self.pack_id)
        if not pack:
            await interaction.response.send_message("❌ Pack not found", ephemeral=True)
            return
        
        if pack.status not in ["pending", "rejected"]:
            await interaction.response.send_message("❌ Can only edit pending or rejected packs", ephemeral=True)
            return
        
        await interaction.response.send_modal(EditPackModal(pack, self.user_id))
    
    @discord.ui.button(label="Cancel", style=ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Pack creation cancelled", ephemeral=True)


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


class PackDetailView(View):
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
            description=f"Genre: {self.pack.genre} | Artists: {len(preview['artists'])}",
            color=discord.Color.blue()
        )
        
        for i, artist in enumerate(preview['artists'][:10], 1):
            tier_emoji = {
                "legendary": "🏆",
                "platinum": "💎",
                "gold": "🥇",
                "silver": "🥈",
                "bronze": "🥉",
                "community": "👥"
            }.get(artist['estimated_tier'], "❓")
            
            embed.add_field(
                name=f"{i}. {tier_emoji} {artist['name']}",
                value=f"Genre: {artist['genre']} | Tier: {artist['estimated_tier']}\nPopularity: {artist['popularity']}",
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
                
                for card in cards[:5]:  # Show first 5 cards
                    embed.add_field(
                        name=f"🎴 {card.artist_name}",
                        value=f"Tier: {card.tier} | Serial: {card.serial}",
                        inline=False
                    )
                
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
        
        # Delete the pack
        self.pack.delete()
        
        embed = Embed(
            title="🗑️ Pack Deleted",
            description=f"Your pack '{self.pack.name}' has been deleted.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(CreatorDashboard(bot))
