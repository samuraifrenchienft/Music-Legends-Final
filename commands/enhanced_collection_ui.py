# commands/enhanced_collection_ui.py
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from discord import Embed, ButtonStyle
from models.card import Card
from models.creator_pack import CreatorPack

PAGE_SIZE = 8

class EnhancedCollectionView(View):

    def __init__(self, user_id, page=0):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.page = page

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, button):
        self.page = max(0, self.page - 1)
        await interaction.response.edit_message(
            embed=collection_embed(self.user_id, self.page),
            view=self
        )

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        self.page += 1
        await interaction.response.edit_message(
            embed=collection_embed(self.user_id, self.page),
            view=self
        )

    @discord.ui.button(label="Filter", style=discord.ButtonStyle.primary, emoji="🔍")
    async def filter(self, interaction, button):
        await interaction.response.send_modal(FilterModal(self.user_id))

    @discord.ui.button(label="Sort", style=discord.ButtonStyle.secondary, emoji="📊")
    async def sort(self, interaction, button):
        await interaction.response.send_modal(SortModal(self.user_id))

    @discord.ui.select(
        placeholder="Select a card to view details...",
        custom_id="card_select"
    )
    async def card_select(self, interaction, select):
        card_id = select.values[0]
        card = Card.get_by_id(card_id)
        
        if not card or card.owner_id != self.user_id:
            await interaction.response.send_message("❌ Card not found", ephemeral=True)
            return
        
        await self.show_card_details(interaction, card)
    
    async def show_card_details(self, interaction, card):
        """Show detailed card information"""
        try:
            # Get pack information
            pack_name = "Unknown Pack"
            if card.source and card.source.startswith("creator:"):
                pack_id = card.source.split(":")[1]
                pack = CreatorPack.get_by_id(pack_id)
                if pack:
                    pack_name = pack.name
            
            # Tier emoji
            tier_emoji = {
                "legendary": "🏆",
                "platinum": "💎",
                "gold": "🥇",
                "silver": "🥈",
                "bronze": "🥉",
                "community": "👥"
            }.get(card.tier, "❓")
            
            embed = Embed(
                title=f"{tier_emoji} {card.artist_name}",
                description=f"**{card.tier.title()}** Card",
                color=discord.Color.gold()
            )
            
            # Add card image if available
            if hasattr(card, 'image_url') and card.image_url:
                embed.set_thumbnail(url=card.image_url)
            
            embed.add_field(name="🔢 Serial Number", value=card.serial, inline=True)
            embed.add_field(name="🎼 Artist", value=card.artist_name, inline=True)
            embed.add_field(name="🏆 Tier", value=f"{tier_emoji} {card.tier.title()}", inline=True)
            
            if hasattr(card, 'artist_genre') and card.artist_genre:
                embed.add_field(name="🎵 Genre", value=card.artist_genre, inline=True)
            
            embed.add_field(name="📦 Source Pack", value=pack_name, inline=True)
            
            if hasattr(card, 'created_at') and card.created_at:
                embed.add_field(name="📅 Obtained", value=card.created_at.strftime("%Y-%m-%d"), inline=True)
            
            # Add action buttons
            view = CardActionsView(card, self.user_id)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error showing card details: {e}", ephemeral=True)


class CardActionsView(View):
    def __init__(self, card, user_id: int):
        super().__init__(timeout=300)
        self.card = card
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Trade", style=discord.ButtonStyle.primary, emoji="🔄")
    async def trade(self, interaction, button):
        await interaction.response.send_modal(TradeModal(self.card))
    
    @discord.ui.button(label="Burn", style=discord.ButtonStyle.danger, emoji="🔥")
    async def burn(self, interaction, button):
        embed = Embed(
            title="🔥 Burn Card",
            description=f"Are you sure you want to burn **{self.card.artist_name}**?",
            color=discord.Color.red()
        )
        
        embed.add_field(name="⚠️ Warning", value="This action cannot be undone!", inline=False)
        embed.add_field(name="🎴 Card", value=f"{self.card.artist_name} ({self.card.tier})", inline=True)
        
        view = BurnConfirmView(self.card, self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="◀️")
    async def back(self, interaction, button):
        await interaction.response.edit_message(
            embed=collection_embed(self.user_id, 0),
            view=EnhancedCollectionView(self.user_id)
        )


class BurnConfirmView(View):
    def __init__(self, card, user_id: int):
        super().__init__(timeout=60)
        self.card = card
        self.user_id = user_id
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label="Confirm Burn", style=discord.ButtonStyle.danger, emoji="🔥")
    async def confirm_burn(self, interaction, button):
        try:
            # Delete the card
            self.card.delete()
            
            embed = Embed(
                title="🔥 Card Burned",
                description=f"**{self.card.artist_name}** has been burned.",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error burning card: {e}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.send_message("Card burn cancelled", ephemeral=True)


class FilterModal(Modal, title="Filter Collection"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        
        self.tier = TextInput(
            label="Tier (optional)",
            placeholder="legendary, platinum, gold, silver, bronze, community",
            required=False
        )
        self.genre = TextInput(
            label="Genre (optional)",
            placeholder="Rock, Pop, Jazz, etc.",
            required=False
        )
        
        self.add_item(self.tier)
        self.add_item(self.genre)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Store filters (in a real implementation, you'd store this in a database or cache)
        filters = {
            "tier": self.tier.value.strip().lower() if self.tier.value.strip() else None,
            "genre": self.genre.value.strip().lower() if self.genre.value.strip() else None
        }
        
        await interaction.response.send_message(
            f"✅ Filters applied!\n"
            f"🏆 Tier: {filters['tier'] or 'All'}\n"
            f"🎼 Genre: {filters['genre'] or 'All'}",
            ephemeral=True
        )


class SortModal(Modal, title="Sort Collection"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        
        self.sort_by = TextInput(
            label="Sort by",
            placeholder="newest, oldest, tier, artist, serial",
            default="newest",
            required=True
        )
        
        self.add_item(self.sort_by)
    
    async def on_submit(self, interaction: discord.Interaction):
        sort_option = self.sort_by.value.strip().lower()
        
        valid_options = ["newest", "oldest", "tier", "artist", "serial"]
        
        if sort_option not in valid_options:
            await interaction.response.send_message(
                f"❌ Invalid sort option. Valid options: {', '.join(valid_options)}",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            f"✅ Collection sorted by: {sort_option}",
            ephemeral=True
        )


class TradeModal(Modal, title="Trade Card"):
    def __init__(self, card):
        super().__init__()
        self.card = card
        
        self.offer = TextInput(
            label="Offer Cards",
            placeholder="List cards you want to offer...",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.request = TextInput(
            label="Request Cards",
            placeholder="List cards you want in return...",
            style=discord.TextStyle.paragraph,
            required=False
        )
        self.gold = TextInput(
            label="Gold (optional)",
            placeholder="Amount of gold to include...",
            required=False
        )
        
        self.add_item(self.offer)
        self.add_item(self.request)
        self.add_item(self.gold)
    
    async def on_submit(self, interaction: discord.Interaction):
        # In a real implementation, this would create a trade offer
        embed = Embed(
            title="🔄 Trade Offer Created",
            description="Your trade offer has been created (placeholder)",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="🎴 Your Card", value=f"{self.card.artist_name} ({self.card.tier})", inline=False)
        
        if self.offer.value.strip():
            embed.add_field(name="📤 Offering", value=self.offer.value.strip(), inline=False)
        
        if self.request.value.strip():
            embed.add_field(name="📥 Requesting", value=self.request.value.strip(), inline=False)
        
        if self.gold.value.strip():
            embed.add_field(name="💰 Gold", value=self.gold.value.strip(), inline=True)
        
        embed.add_field(
            name="📝 Note",
            value="This is a placeholder implementation. In production, this would create a real trade offer.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


def collection_embed(user_id, page, filters=None, sort_by="newest"):
    """Generate collection embed with filtering and sorting"""
    
    cards = Card.where(owner_id=user_id)
    
    # Apply filters (placeholder implementation)
    if filters:
        if filters.get("tier"):
            cards = [c for c in cards if c.tier == filters["tier"]]
        if filters.get("genre"):
            cards = [c for c in cards if hasattr(c, 'artist_genre') and c.artist_genre == filters["genre"]]
    
    # Apply sorting (placeholder implementation)
    if sort_by == "newest":
        cards = sorted(cards, key=lambda x: getattr(x, 'created_at', 0), reverse=True)
    elif sort_by == "oldest":
        cards = sorted(cards, key=lambda x: getattr(x, 'created_at', 0))
    elif sort_by == "tier":
        tier_order = {"legendary": 5, "platinum": 4, "gold": 3, "silver": 2, "bronze": 1, "community": 0}
        cards = sorted(cards, key=lambda x: tier_order.get(x.tier, 0), reverse=True)
    elif sort_by == "artist":
        cards = sorted(cards, key=lambda x: x.artist_name.lower())
    elif sort_by == "serial":
        cards = sorted(cards, key=lambda x: x.serial)
    
    # Pagination
    slice = cards[page*PAGE_SIZE:(page+1)*PAGE_SIZE]
    total_pages = (len(cards) + PAGE_SIZE - 1) // PAGE_SIZE if cards else 1

    e = Embed(title="📚 Your Collection", color=discord.Color.blue())

    if not cards:
        e.description = "You don't have any cards yet!\nCreate and open creator packs to start collecting."
        return e

    if not slice:
        e.description = "No cards found with current filters."
        return e

    for c in slice:
        tier_emoji = {
            "legendary": "🏆",
            "platinum": "💎",
            "gold": "🥇",
            "silver": "🥈",
            "bronze": "🥉",
            "community": "👥"
        }.get(c.tier, "❓")
        
        # Get pack name
        pack_name = "Unknown"
        if c.source and c.source.startswith("creator:"):
            pack_id = c.source.split(":")[1]
            pack = CreatorPack.get_by_id(pack_id)
            if pack:
                pack_name = pack.name
        
        value = f"🎼 {getattr(c, 'artist_genre', 'Unknown')}\n"
        value += f"📦 {pack_name}\n"
        value += f"🔢 {c.serial}"
        
        e.add_field(
            name=f"{tier_emoji} {c.artist_name}",
            value=value,
            inline=True
        )

    e.set_footer(text=f"Page {page+1}/{total_pages} | Total cards: {len(cards)}")
    
    # Add filter/sort info if applied
    filter_info = []
    if filters and filters.get("tier"):
        filter_info.append(f"🏆 {filters['tier']}")
    if filters and filters.get("genre"):
        filter_info.append(f"🎼 {filters['genre']}")
    if sort_by != "newest":
        filter_info.append(f"📊 {sort_by}")
    
    if filter_info:
        e.description = " | ".join(filter_info)

    return e


# ---------- ENHANCED COMMAND ----------

@bot.slash_command(name="collection")
async def collection(ctx):
    """Enhanced collection browser command"""
    
    await ctx.respond(
        embed=collection_embed(ctx.author.id, 0),
        view=EnhancedCollectionView(ctx.author.id),
        ephemeral=True
    )
