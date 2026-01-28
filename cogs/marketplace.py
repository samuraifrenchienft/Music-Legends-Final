# cogs/marketplace.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3

class MarketplaceCommands(commands.Cog):
    """Marketplace commands for buying/selling cards"""
    
    def __init__(self, bot):
        self.bot = bot
        # Use working directory for database
        self.db_path = "music_legends.db"
    
    @app_commands.command(name="market", description="View the card marketplace")
    async def market_command(self, interaction: Interaction):
        """View cards available in the marketplace"""
        
        embed = discord.Embed(
            title="🏪 CARD MARKETPLACE",
            description="Browse and trade cards with other players!",
            color=discord.Color.gold()
        )
        
        # Get marketplace listings
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.card_id, c.name, c.rarity, c.image_url, 
                       m.price, m.seller_id, m.listed_at
                FROM cards c
                JOIN marketplace_listings m ON c.card_id = m.card_id
                WHERE m.status = 'active'
                ORDER BY m.listed_at DESC
                LIMIT 10
            """)
            listings = cursor.fetchall()
        
        if listings:
            for listing in listings[:5]:
                card_id, name, rarity, image_url, price, seller_id, listed_at = listing
                rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}.get(rarity.lower(), "⚪")
                
                embed.add_field(
                    name=f"{rarity_emoji} {name}",
                    value=f"Price: {price:,} Gold\nCard ID: `{card_id}`\nUse `/buy {card_id}` to purchase",
                    inline=True
                )
        else:
            embed.add_field(
                name="📦 No Listings",
                value="No cards are currently for sale. Use `/sell <card_id>` to list your cards!",
                inline=False
            )
        
        embed.set_footer(text="Marketplace • Use /sell to list cards • Use /buy to purchase")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="sell", description="List a card for sale")
    @app_commands.describe(card_id="Card ID to sell", price="Price in gold")
    async def sell_command(self, interaction: Interaction, card_id: str, price: int):
        """List a card for sale in the marketplace"""
        
        # Check if user owns the card
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.name, c.rarity FROM cards c
                JOIN user_cards uc ON c.card_id = uc.card_id
                WHERE c.card_id = ? AND uc.user_id = ?
            """, (card_id, interaction.user.id))
            card = cursor.fetchone()
        
        if not card:
            await interaction.response.send_message("❌ You don't own this card!", ephemeral=True)
            return
        
        card_name, rarity = card
        
        # List the card
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO marketplace_listings 
                (card_id, seller_id, price, status, listed_at)
                VALUES (?, ?, ?, 'active', datetime('now'))
            """, (card_id, interaction.user.id, price))
            conn.commit()
        
        rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}.get(rarity.lower(), "⚪")
        
        embed = discord.Embed(
            title="🏪 CARD LISTED",
            description=f"{rarity_emoji} **{card_name}** has been listed for {price:,} Gold!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Card ID", value=f"`{card_id}`", inline=True)
        embed.add_field(name="Price", value=f"{price:,} Gold", inline=True)
        embed.add_field(name="Status", value="📦 Listed", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="pack", description="View your available packs")
    async def pack_command(self, interaction: Interaction):
        """View packs you own"""
        
        embed = discord.Embed(
            title="🎴 YOUR PACKS",
            description="View and open your card packs",
            color=discord.Color.purple()
        )
        
        # Get user's packs
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pack_id, pack_name, pack_type, created_at
                FROM creator_packs
                WHERE creator_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (interaction.user.id,))
            packs = cursor.fetchone()
        
        if packs:
            pack_id, pack_name, pack_type, created_at = packs
            embed.add_field(
                name=f"📦 {pack_name}",
                value=f"Type: {pack_type}\nCreated: {created_at}\nUse `/open_pack {pack_id}` to open",
                inline=False
            )
        else:
            embed.add_field(
                name="📦 No Packs",
                value="You don't have any packs yet. Use `/create_pack` to make one!",
                inline=False
            )
        
        embed.set_footer(text="Packs • Use /create_pack to make new packs")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(MarketplaceCommands(bot))
