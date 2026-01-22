# cogs/collection_browser.py
"""
Collection Browser Cog
User flow for viewing and managing card collection
"""

from discord.ext import commands
import discord
from discord.ui import Button, Modal, InputText, View, Select
from discord import Interaction, Embed, ButtonStyle
from typing import List, Optional, Dict, Any
from models.card import Card
from models.creator_pack import CreatorPack

class CollectionBrowser(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_page = {}  # user_id -> page
        self.current_filters = {}  # user_id -> filters
        self.current_sort = {}  # user_id -> sort_option
    
    @commands.hybrid_command(name="collection", description="Browse your card collection")
    async def collection(self, ctx: Interaction):
        """Open collection browser"""
        try:
            await ctx.defer()
            await self.show_collection(ctx)
        except Exception as e:
            await ctx.respond(f"❌ Error loading collection: {e}", ephemeral=True)
    
    async def show_collection(self, interaction: Interaction, page: int = 0):
        """Show collection with grid view"""
        try:
            user_id = interaction.user.id
            
            # Get user's cards
            user_cards = Card.where(owner_id=user_id)
            
            if not user_cards:
                embed = Embed(
                    title="📚 Your Card Collection",
                    description="You don't have any cards yet!\nCreate and open creator packs to start collecting.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="🚀 Get Started", value="Use `/creator_dashboard` to create your first pack!")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            # Apply filters
            filtered_cards = self._apply_filters(user_cards, self.current_filters.get(user_id, {}))
            
            # Apply sorting
            sorted_cards = self._apply_sorting(filtered_cards, self.current_sort.get(user_id, "newest"))
            
            # Pagination
            cards_per_page = 8
            total_pages = (len(sorted_cards) + cards_per_page - 1) // cards_per_page
            
            if page >= total_pages:
                page = max(0, total_pages - 1)
            
            start_idx = page * cards_per_page
            end_idx = min(start_idx + cards_per_page, len(sorted_cards))
            page_cards = sorted_cards[start_idx:end_idx]
            
            # Create embed
            embed = Embed(
                title="📚 Your Card Collection",
                description=f"Showing {len(page_cards)} of {len(sorted_cards)} cards (Page {page + 1}/{total_pages})",
                color=discord.Color.blue()
            )
            
            # Add card fields
            for card in page_cards:
                tier_emoji = {
                    "legendary": "🏆",
                    "platinum": "💎",
                    "gold": "🥇",
                    "silver": "🥈",
                    "bronze": "🥉",
                    "community": "👥"
                }.get(card.tier, "❓")
                
                # Get pack name if available
                pack_name = "Unknown Pack"
                if card.source and card.source.startswith("creator:"):
                    pack_id = card.source.split(":")[1]
                    pack = CreatorPack.get_by_id(pack_id)
                    if pack:
                        pack_name = pack.name
                
                field_value = f"{tier_emoji} {card.tier.title()}\n"
                field_value += f"🔢 Serial: {card.serial}\n"
                field_value += f"📦 Source: {pack_name}"
                
                embed.add_field(
                    name=f"🎴 {card.artist_name}",
                    value=field_value,
                    inline=True
                )
            
            # Store current page
            self.current_page[user_id] = page
            
            # Create view with pagination and controls
            view = CollectionGridView(user_id, page, total_pages, len(sorted_cards))
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error loading collection: {e}", ephemeral=True)
    
    def _apply_filters(self, cards: List[Card], filters: Dict[str, Any]) -> List[Card]:
        """Apply filters to card list"""
        filtered = cards.copy()
        
        # Tier filter
        if filters.get("tier"):
            filtered = [card for card in filtered if card.tier == filters["tier"]]
        
        # Genre filter
        if filters.get("genre"):
            filtered = [card for card in filtered if card.artist_genre == filters["genre"]]
        
        # Pack source filter
        if filters.get("pack_source"):
            filtered = [card for card in filtered if card.source == filters["pack_source"]]
        
        # Ownership filter (for future expansion)
        if filters.get("ownership"):
            if filters["ownership"] == "owned":
                pass  # Already filtered by owner
            elif filters["ownership"] == "traded":
                # Would need to track trade status
                pass
        
        return filtered
    
    def _apply_sorting(self, cards: List[Card], sort_option: str) -> List[Card]:
        """Apply sorting to card list"""
        if sort_option == "newest":
            return sorted(cards, key=lambda x: x.created_at or 0, reverse=True)
        elif sort_option == "oldest":
            return sorted(cards, key=lambda x: x.created_at or 0)
        elif sort_option == "tier_high":
            tier_order = {"legendary": 5, "platinum": 4, "gold": 3, "silver": 2, "bronze": 1, "community": 0}
            return sorted(cards, key=lambda x: tier_order.get(x.tier, 0), reverse=True)
        elif sort_option == "tier_low":
            tier_order = {"legendary": 5, "platinum": 4, "gold": 3, "silver": 2, "bronze": 1, "community": 0}
            return sorted(cards, key=lambda x: tier_order.get(x.tier, 0))
        elif sort_option == "artist_name":
            return sorted(cards, key=lambda x: x.artist_name.lower())
        elif sort_option == "serial":
            return sorted(cards, key=lambda x: x.serial)
        else:
            return cards


class CollectionGridView(View):
    def __init__(self, user_id: int, current_page: int, total_pages: int, total_cards: int):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.current_page = current_page
        self.total_pages = total_pages
        self.total_cards = total_cards
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="◀", style=ButtonStyle.secondary)
    async def previous_page(self, interaction: Interaction, button: Button):
        if self.current_page > 0:
            await collection_browser.show_collection(interaction, self.current_page - 1)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="▶", style=ButtonStyle.secondary)
    async def next_page(self, interaction: Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            await collection_browser.show_collection(interaction, self.current_page + 1)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Filter", style=ButtonStyle.primary, emoji="🔍")
    async def filter_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Filter options coming soon!", ephemeral=True)
    
    @discord.ui.button(label="Sort", style=ButtonStyle.secondary, emoji="📊")
    async def sort_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(SortModal(self.user_id))
    
    @discord.ui.select(
        placeholder="View Card Details",
        options=[
            discord.SelectOption(label="Select a card to view details", value="placeholder", description="Choose a card from the current page")
        ],
        custom_id="card_select"
    )
    async def card_select(self, interaction: Interaction, select: Select):
        if select.values[0] == "placeholder":
            await interaction.response.defer()
            return
        
        # Get card details
        card_id = select.values[0]
        card = Card.get_by_id(card_id)
        
        if not card or card.owner_id != self.user_id:
            await interaction.response.send_message("❌ Card not found", ephemeral=True)
            return
        
        await self.show_card_detail(interaction, card)
    
    async def show_card_detail(self, interaction: Interaction, card: Card):
        """Show detailed card view"""
        try:
            tier_emoji = {
                "legendary": "🏆",
                "platinum": "💎",
                "gold": "🥇",
                "silver": "🥈",
                "bronze": "🥉",
                "community": "👥"
            }.get(card.tier, "❓")
            
            # Get pack information
            pack_name = "Unknown Pack"
            if card.source and card.source.startswith("creator:"):
                pack_id = card.source.split(":")[1]
                pack = CreatorPack.get_by_id(pack_id)
                if pack:
                    pack_name = pack.name
            
            embed = Embed(
                title=f"🎴 {card.artist_name}",
                description=f"{tier_emoji} {card.tier.title()} Card",
                color=discord.Color.gold()
            )
            
            # Add card image if available
            if hasattr(card, 'image_url') and card.image_url:
                embed.set_thumbnail(url=card.image_url)
            
            embed.add_field(name="🔢 Serial Number", value=card.serial, inline=True)
            embed.add_field(name="🎼 Artist", value=card.artist_name, inline=True)
            embed.add_field(name="🏆 Tier", value=f"{tier_emoji} {card.tier.title()}", inline=True)
            
            if card.artist_genre:
                embed.add_field(name="🎵 Genre", value=card.artist_genre, inline=True)
            
            embed.add_field(name="📦 Source Pack", value=pack_name, inline=True)
            
            if card.created_at:
                embed.add_field(name="📅 Obtained", value=card.created_at.strftime("%Y-%m-%d"), inline=True)
            
            # Add action buttons
            view = CardDetailView(card, self.user_id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error showing card details: {e}", ephemeral=True)


class SortModal(Modal):
    def __init__(self, user_id: int):
        super().__init__(title="Sort Collection")
        self.user_id = user_id
        
        self.add_item(InputText(
            label="Sort by",
            placeholder="newest, oldest, tier_high, tier_low, artist_name, serial",
            value="newest",
            required=True
        ))
    
    async def callback(self, interaction: Interaction):
        sort_option = self.children[0].value.strip().lower()
        
        valid_options = ["newest", "oldest", "tier_high", "tier_low", "artist_name", "serial"]
        
        if sort_option not in valid_options:
            await interaction.response.send_message(f"❌ Invalid sort option. Valid options: {', '.join(valid_options)}", ephemeral=True)
            return
        
        collection_browser.current_sort[self.user_id] = sort_option
        
        await collection_browser.show_collection(interaction, 0)


class CardDetailView(View):
    def __init__(self, card: Card, user_id: int):
        super().__init__(timeout=300)
        self.card = card
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Trade", style=ButtonStyle.primary, emoji="🔄")
    async def trade_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(TradeModal(self.card, self.user_id))
    
    @discord.ui.button(label="Burn", style=ButtonStyle.danger, emoji="🔥")
    async def burn_button(self, interaction: Interaction, button: Button):
        embed = Embed(
            title="🔥 Burn Card",
            description="Are you sure you want to burn this card? This action cannot be undone.",
            color=discord.Color.red()
        )
        
        embed.add_field(name="🎴 Card", value=f"{self.card.artist_name} ({self.card.tier})", inline=False)
        embed.add_field(name="⚠️ Warning", value="Burning will permanently remove this card from your collection", inline=False)
        
        view = BurnConfirmView(self.card, self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Back", style=ButtonStyle.secondary, emoji="◀️")
    async def back_button(self, interaction: Interaction, button: Button):
        await collection_browser.show_collection(interaction)


class BurnConfirmView(View):
    def __init__(self, card: Card, user_id: int):
        super().__init__(timeout=60)
        self.card = card
        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Confirm Burn", style=ButtonStyle.danger, emoji="🔥")
    async def confirm_burn(self, interaction: Interaction, button: Button):
        try:
            # Delete the card
            self.card.delete()
            
            embed = Embed(
                title="🔥 Card Burned",
                description=f"{self.card.artist_name} ({self.card.tier}) has been burned.",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error burning card: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=ButtonStyle.secondary)
    async def cancel_burn(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Card burn cancelled", ephemeral=True)


class TradeModal(Modal):
    def __init__(self, card: Card, user_id: int):
        super().__init__(title="Trade Card")
        self.card = card
        self.user_id = user_id
        
        self.add_item(InputText(
            label="Offer Cards",
            placeholder="List cards you want to offer",
            style=discord.InputTextStyle.long,
            required=False
        ))
        
        self.add_item(InputText(
            label="Request Cards",
            placeholder="List cards you want in return",
            style=discord.InputTextStyle.long,
            required=False
        ))
        
        self.add_item(InputText(
            label="Additional Gold",
            placeholder="Amount of gold to include in trade",
            required=False
        ))
    
    async def callback(self, interaction: Interaction):
        offer_cards = self.children[0].value.strip()
        request_cards = self.children[1].value.strip()
        gold_amount = self.children[2].value.strip()
        
        # In a real implementation, this would create a trade offer
        embed = Embed(
            title="🔄 Trade Offer Created",
            description="Your trade offer has been created (placeholder implementation)",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="🎴 Your Card", value=f"{self.card.artist_name} ({self.card.tier})", inline=False)
        
        if offer_cards:
            embed.add_field(name="📤 Offering", value=offer_cards, inline=False)
        
        if request_cards:
            embed.add_field(name="📥 Requesting", value=request_cards, inline=False)
        
        if gold_amount:
            embed.add_field(name="💰 Gold", value=gold_amount, inline=True)
        
        embed.add_field(
            name="📝 Note",
            value="This is a placeholder implementation. In production, this would create a real trade offer.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Global instance for access
collection_browser = CollectionBrowser(None)


async def setup(bot):
    await bot.add_cog(CollectionBrowser(bot))
