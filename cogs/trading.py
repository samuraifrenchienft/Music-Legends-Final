# cogs/trading.py
import discord
import asyncio
import uuid
from discord.ext import commands
from discord import Interaction, app_commands, ui
from typing import Dict, List, Optional
import json
import sqlite3
from card_economy import CardEconomyManager
from database import DatabaseManager

class TradingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
        self.active_trades = {}  # trade_id -> trade_data

    @app_commands.command(name="trade", description="Initiate a trade with another user")
    async def trade_command(self, interaction: Interaction, user: discord.User):
        """Initiate a trade with another user"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't trade with yourself!", ephemeral=True)
            return
        
        # Create trade view
        view = TradeView(self.economy, interaction.user.id, user.id)
        
        embed = discord.Embed(
            title="🤝 Trade Initiated",
            description=f"{interaction.user.mention} wants to trade with {user.mention}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 Instructions",
            value="1. Both users select cards to trade\n"
                  "2. Add currency if desired\n"
                  "3. Both users must confirm\n"
                  "4. Trade will execute automatically",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="multitrade", description="Initiate a multi-item trade")
    async def multitrade_command(self, interaction: Interaction, user: discord.User):
        """Initiate a multi-item trade (same as regular trade for now)"""
        # For now, this is the same as regular trade
        # Could be expanded later for more complex multi-user trades
        await self.trade_command(interaction, user)

    @app_commands.command(name="market", description="View the card market")
    async def market_command(self, interaction: Interaction, action: str = "browse"):
        """Browse or interact with the card market"""
        if action == "browse":
            await self._browse_market(interaction)
        elif action == "my_listings":
            await self._my_listings(interaction)
        else:
            await interaction.response.send_message("❌ Invalid action! Use 'browse' or 'my_listings'", ephemeral=True)

    async def _browse_market(self, interaction: Interaction):
        """Browse available market listings"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM market_listings 
                WHERE status = 'active'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            listings = cursor.fetchall()
        
        if not listings:
            await interaction.response.send_message("🏪 No cards are currently listed on the market!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏪 Card Market",
            description="Browse available cards for sale:",
            color=discord.Color.gold()
        )
        
        for listing in listings[:10]:  # Show up to 10 listings
            listing_id, seller_id, card_id, asking_gold, asking_dust, status, created_at = listing[:7]
            
            # Get card details
            cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
            card = cursor.fetchone()
            
            if card:
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
                
                price_text = ""
                if asking_gold > 0:
                    price_text += f"🟡 {asking_gold} Gold"
                if asking_dust > 0:
                    if price_text:
                        price_text += " + "
                    price_text += f"💨 {asking_dust} Dust"
                
                embed.add_field(
                    name=f"{tier_emoji} {card[2]} - {card[3].title()}",
                    value=f"Serial: {card[4]}\n"
                          f"Seller: <@{seller_id}>\n"
                          f"Price: {price_text}\n"
                          f"Listing ID: `{listing_id[:8]}...`",
                    inline=False
                )
        
        embed.add_field(
            name="🛒 How to Buy",
            value="Use `/market buy <listing_id>` to purchase a card",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    async def _my_listings(self, interaction: Interaction):
        """View user's own market listings"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM market_listings 
                WHERE seller_user_id = ? AND status = 'active'
                ORDER BY created_at DESC
            """, (interaction.user.id,))
            listings = cursor.fetchall()
        
        if not listings:
            await interaction.response.send_message("🏪 You don't have any active listings!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏪 Your Market Listings",
            description=f"You have {len(listings)} active listings:",
            color=discord.Color.blue()
        )
        
        for listing in listings:
            listing_id, seller_id, card_id, asking_gold, asking_dust, status, created_at = listing[:7]
            
            # Get card details
            cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
            card = cursor.fetchone()
            
            if card:
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
                
                price_text = ""
                if asking_gold > 0:
                    price_text += f"🟡 {asking_gold} Gold"
                if asking_dust > 0:
                    price_text += f"💨 {asking_dust} Dust"
                
                embed.add_field(
                    name=f"{tier_emoji} {card[2]}",
                    value=f"Serial: {card[4]}\n"
                          f"Price: {price_text}\n"
                          f"Listed: {created_at[:10]}\n"
                          f"ID: `{listing_id[:8]}...`",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="list", description="List a card on the market")
    async def list_command(self, interaction: Interaction, serial_number: str, gold_price: int = 0, dust_price: int = 0):
        """List a card on the market for sale"""
        if gold_price <= 0 and dust_price <= 0:
            await interaction.response.send_message("❌ You must set at least one price (gold or dust)!", ephemeral=True)
            return
        
        # Find the card
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM cards 
                WHERE serial_number = ? AND owner_user_id = ?
            """, (serial_number, interaction.user.id))
            card = cursor.fetchone()
        
        if not card:
            await interaction.response.send_message("❌ Card not found in your collection!", ephemeral=True)
            return
        
        # Create market listing
        listing_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO market_listings 
            (listing_id, seller_user_id, card_id, asking_gold, asking_dust)
            VALUES (?, ?, ?, ?, ?)
        """, (listing_id, interaction.user.id, card[0], gold_price, dust_price))
        
        conn.commit()
        
        # Move card to market ownership (optional - could keep with seller until sold)
        # For now, we'll keep it with seller and transfer on sale
        
        tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
        
        embed = discord.Embed(
            title="🏪 Card Listed!",
            description=f"Your {card[2]} has been listed on the market",
            color=discord.Color.green()
        )
        
        price_text = ""
        if gold_price > 0:
            price_text += f"🟡 {gold_price} Gold"
        if dust_price > 0:
            if price_text:
                price_text += " + "
            price_text += f"💨 {dust_price} Dust"
        
        embed.add_field(
            name="📋 Listing Details",
            value=f"{tier_emoji} {card[2]} ({card[3].title()})\n"
                  f"Serial: {card[4]}\n"
                  f"Price: {price_text}\n"
                  f"Listing ID: `{listing_id[:8]}...`",
            inline=False
        )
        
        embed.set_footer(text="Use `/market my_listings` to manage your listings")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="buy", description="Buy a card from the market")
    async def buy_command(self, interaction: Interaction, listing_id: str):
        """Buy a card from the market"""
        # Find the listing
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM market_listings 
                WHERE listing_id LIKE ? AND status = 'active'
            """, (f"{listing_id}%",))
            listing = cursor.fetchone()
        
        if not listing:
            await interaction.response.send_message("❌ Listing not found or not active!", ephemeral=True)
            return
        
        listing_id, seller_id, card_id, asking_gold, asking_dust, status, created_at = listing[:7]
        
        # Check if user is trying to buy their own listing
        if seller_id == interaction.user.id:
            await interaction.response.send_message("❌ You can't buy your own listing!", ephemeral=True)
            return
        
        # Check if user has enough currency
        cursor.execute("SELECT gold, dust FROM user_inventory WHERE user_id = ?", (interaction.user.id,))
        buyer_inventory = cursor.fetchone()
        
        if not buyer_inventory or (buyer_inventory[0] < asking_gold or buyer_inventory[1] < asking_dust):
            await interaction.response.send_message("❌ You don't have enough currency for this purchase!", ephemeral=True)
            return
        
        # Get card details
        cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
        card = cursor.fetchone()
        
        if not card:
            await interaction.response.send_message("❌ Card not found!", ephemeral=True)
            return
        
        # Process the transaction
        try:
            # Remove currency from buyer
            cursor.execute("""
                UPDATE user_inventory 
                SET gold = gold - ?, dust = dust - ?
                WHERE user_id = ?
            """, (asking_gold, asking_dust, interaction.user.id))
            
            # Add currency to seller
            cursor.execute("""
                UPDATE user_inventory 
                SET gold = COALESCE(gold, 0) + ?, dust = COALESCE(dust, 0) + ?
                WHERE user_id = ?
            """, (asking_gold, asking_dust, seller_id))
            
            # Transfer card ownership
            cursor.execute("""
                UPDATE cards 
                SET owner_user_id = ?, owner_history = COALESCE(owner_history, '[]') || ?
                WHERE card_id = ?
            """, (interaction.user.id, json.dumps([seller_id]), card_id))
            
            # Mark listing as sold
            cursor.execute("""
                UPDATE market_listings 
                SET status = 'sold', buyer_user_id = ?, sold_at = CURRENT_TIMESTAMP
                WHERE listing_id = ?
            """, (interaction.user.id, listing_id))
            
            # Record trade history
            trade_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO trade_history 
                (trade_id, initiator_user_id, receiver_user_id, gold_from_receiver, dust_from_receiver)
                VALUES (?, ?, ?, ?, ?)
            """, (trade_id, seller_id, interaction.user.id, asking_gold, asking_dust))
            
            conn.commit()
            
            # Success message
            tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
            
            embed = discord.Embed(
                title="🎉 Purchase Successful!",
                description=f"You bought {card[2]} from <@{seller_id}>",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="💰 Transaction Details",
                value=f"Card: {tier_emoji} {card[2]} ({card[3].title()})\n"
                      f"Serial: {card[4]}\n"
                      f"Price Paid: 🟡 {asking_gold} Gold + 💨 {asking_dust} Dust",
                inline=False
            )
            
            embed.set_footer(text="The card has been added to your collection!")
            
            await interaction.response.send_message(embed=embed)
            
            # Notify seller (optional - could send DM)
            try:
                seller = self.bot.get_user(seller_id)
                if seller:
                    await seller.send(f"🎉 Your {card[2]} has been sold for 🟡 {asking_gold} Gold + 💨 {asking_dust} Dust!")
            except:
                pass  # Seller has DMs disabled
            
        except Exception as e:
            conn.rollback()
            await interaction.response.send_message(f"❌ Transaction failed: {str(e)}", ephemeral=True)

class TradeView(ui.View):
    def __init__(self, economy_manager: CardEconomyManager, initiator_id: int, target_id: int):
        super().__init__(timeout=300)  # 5 minutes
        self.economy = economy_manager
        self.initiator_id = initiator_id
        self.target_id = target_id
        
        self.initiator_cards = []
        self.target_cards = []
        self.initiator_gold = 0
        self.target_gold = 0
        self.initiator_dust = 0
        self.target_dust = 0
        
        self.initiator_confirmed = False
        self.target_confirmed = False
        
        # Add card selection buttons
        self.add_item(ui.Button(
            label="Add Card (Max 5)",
            style=discord.ButtonStyle.secondary,
            custom_id="add_card_initiator"
        ))
        
        self.add_item(ui.Button(
            label="Add Currency",
            style=discord.ButtonStyle.secondary,
            custom_id="add_currency"
        ))
        
        self.add_item(ui.Button(
            label="Confirm Trade",
            style=discord.ButtonStyle.primary,
            custom_id="confirm_trade",
            disabled=True
        ))
        
        self.add_item(ui.Button(
            label="Cancel Trade",
            style=discord.ButtonStyle.danger,
            custom_id="cancel_trade"
        ))

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id in [self.initiator_id, self.target_id]

# Import uuid for listing IDs
import uuid

async def setup(bot):
    await bot.add_cog(TradingCog(bot))
