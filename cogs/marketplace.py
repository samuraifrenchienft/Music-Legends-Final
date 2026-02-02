# cogs/marketplace.py
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3
import json

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
        
        # Trigger backup after marketplace listing
        try:
            from services.backup_service import backup_service
            backup_path = await backup_service.backup_critical('marketplace_listing', card_id)
            if backup_path:
                print(f"💾 Critical backup created after marketplace listing: {backup_path}")
        except Exception as e:
            print(f"⚠️ Backup trigger failed (non-critical): {e}")
        
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
    
    @app_commands.command(name="buy", description="Purchase a card from the marketplace")
    @app_commands.describe(card_id="Card ID to purchase")
    async def buy_command(self, interaction: Interaction, card_id: str):
        """Purchase a card from the marketplace"""
        # #region agent log
        with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"F","location":"marketplace.py:116","message":"Buy command entry","data":{"card_id":card_id,"user_id":interaction.user.id},"timestamp":int(__import__('time').time()*1000)})+'\n')
        # #endregion
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if card is listed
            cursor.execute("""
                SELECT c.card_id, c.name, c.rarity, c.image_url,
                       m.price, m.seller_id, m.status
                FROM cards c
                JOIN marketplace_listings m ON c.card_id = m.card_id
                WHERE c.card_id = ? AND m.status = 'active'
            """, (card_id,))
            listing = cursor.fetchone()
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"F","location":"marketplace.py:130","message":"Listing check","data":{"listing_found":listing is not None,"status":listing[6] if listing else None},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            
            if not listing:
                await interaction.response.send_message(
                    "❌ This card is not available for purchase! It may have been sold or removed.",
                    ephemeral=True
                )
                return
            
            card_id_db, card_name, rarity, image_url, price, seller_id, status = listing
            
            # Check if user is trying to buy their own card
            if seller_id == interaction.user.id:
                await interaction.response.send_message(
                    "❌ You can't buy your own card! Remove it from the marketplace first.",
                    ephemeral=True
                )
                return
            
            # Check if user has enough gold
            cursor.execute("""
                SELECT gold FROM users WHERE user_id = ?
            """, (interaction.user.id,))
            user_result = cursor.fetchone()
            # #region agent log
            with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"H","location":"marketplace.py:153","message":"User check","data":{"user_found":user_result is not None,"user_gold":user_result[0] if user_result else None},"timestamp":int(__import__('time').time()*1000)})+'\n')
            # #endregion
            
            if not user_result:
                await interaction.response.send_message(
                    "❌ User not found! Please use `/daily` first to register.",
                    ephemeral=True
                )
                return
            
            user_gold = user_result[0] or 0
            
            if user_gold < price:
                await interaction.response.send_message(
                    f"❌ Insufficient funds! You need {price:,} Gold but only have {user_gold:,} Gold.",
                    ephemeral=True
                )
                return
            
            # Process purchase
            try:
                # #region agent log
                with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"G","location":"marketplace.py:172","message":"Transaction start","data":{"price":price,"buyer_id":interaction.user.id,"seller_id":seller_id},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                # Transfer card ownership
                cursor.execute("""
                    DELETE FROM user_cards WHERE user_id = ? AND card_id = ?
                """, (seller_id, card_id))
                
                cursor.execute("""
                    INSERT INTO user_cards (user_id, card_id, source, acquired_at)
                    VALUES (?, ?, 'marketplace', datetime('now'))
                """, (interaction.user.id, card_id))
                
                # Transfer gold
                cursor.execute("""
                    UPDATE users SET gold = gold - ? WHERE user_id = ?
                """, (price, interaction.user.id))
                
                cursor.execute("""
                    UPDATE users SET gold = gold + ? WHERE user_id = ?
                """, (price, seller_id))
                
                # Update listing status
                cursor.execute("""
                    UPDATE marketplace_listings
                    SET status = 'sold', buyer_id = ?, sold_at = datetime('now')
                    WHERE card_id = ?
                """, (interaction.user.id, card_id))
                
                conn.commit()
                # #region agent log
                with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"G","location":"marketplace.py:199","message":"Transaction committed","data":{},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                
                # Trigger backup after marketplace purchase
                try:
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"I","location":"marketplace.py:202","message":"Before backup import","data":{},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    from services.backup_service import backup_service
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"I","location":"marketplace.py:204","message":"After backup import","data":{"backup_service_exists":backup_service is not None},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    backup_path = await backup_service.backup_critical('marketplace_buy', card_id)
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"I","location":"marketplace.py:205","message":"After backup call","data":{"backup_path":backup_path},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    if backup_path:
                        print(f"💾 Critical backup created after marketplace purchase: {backup_path}")
                except Exception as e:
                    # #region agent log
                    with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        import json
                        f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"I","location":"marketplace.py:208","message":"Backup error","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                    # #endregion
                    print(f"⚠️ Backup trigger failed (non-critical): {e}")
                
                rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}.get(rarity.lower(), "⚪")
                
                embed = discord.Embed(
                    title="✅ PURCHASE SUCCESSFUL",
                    description=f"{rarity_emoji} **{card_name}** has been added to your collection!",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="Card ID", value=f"`{card_id}`", inline=True)
                embed.add_field(name="Price Paid", value=f"{price:,} Gold", inline=True)
                embed.add_field(name="Remaining Gold", value=f"{user_gold - price:,} Gold", inline=True)
                
                if image_url:
                    embed.set_thumbnail(url=image_url)
                
                await interaction.response.send_message(embed=embed)
                
            except Exception as e:
                # #region agent log
                with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"G","location":"marketplace.py:225","message":"Transaction error","data":{"error":str(e)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                conn.rollback()
                # #region agent log
                with open(r'c:\Users\AbuBa\Downloads\discordpy-v2-bot-template-main\discordpy-v2-bot-template-main\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    import json
                    f.write(json.dumps({"sessionId":"debug-session","runId":"init","hypothesisId":"G","location":"marketplace.py:227","message":"After rollback","data":{},"timestamp":int(__import__('time').time()*1000)})+'\n')
                # #endregion
                await interaction.response.send_message(
                    f"❌ Purchase failed: {str(e)}",
                    ephemeral=True
                )
                print(f"Marketplace purchase error: {e}")
                import traceback
                traceback.print_exc()
    
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
                SELECT pack_id, name, status, created_at, cards_data
                FROM creator_packs
                WHERE creator_id = ? AND status = 'LIVE'
                ORDER BY created_at DESC
                LIMIT 10
            """, (interaction.user.id,))
            packs = cursor.fetchall()
        
        if packs:
            for pack in packs:
                pack_id, pack_name, status, created_at, cards_data = pack
                cards = json.loads(cards_data) if cards_data else []
                embed.add_field(
                    name=f"📦 {pack_name}",
                    value=f"Status: {status}\nCards: {len(cards)}\nCreated: {created_at}\nUse `/open_pack {pack_id}` to open",
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

    @app_commands.command(name="packs", description="Browse marketplace packs")
    async def packs_command(self, interaction: Interaction):
        """Browse all available marketplace packs"""
        
        embed = discord.Embed(
            title="🛍️ MARKETPLACE PACKS",
            description="Browse available packs from creators",
            color=discord.Color.gold()
        )
        
        # Get all live packs
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pack_id, name, creator_id, description, created_at, cards_data
                FROM creator_packs
                WHERE status = 'LIVE'
                ORDER BY created_at DESC
                LIMIT 20
            """)
            packs = cursor.fetchall()
        
        if packs:
            for pack in packs:
                pack_id, pack_name, creator_id, description, created_at, cards_data = pack
                cards = json.loads(cards_data) if cards_data else []
                
                # Get creator name
                cursor.execute("SELECT username FROM users WHERE user_id = ?", (creator_id,))
                creator_result = cursor.fetchone()
                creator_name = creator_result[0] if creator_result else f"User {creator_id}"
                
                embed.add_field(
                    name=f"📦 {pack_name}",
                    value=f"Creator: {creator_name}\nCards: {len(cards)}\n{description[:100]}...\nPack ID: `{pack_id}`",
                    inline=False
                )
        else:
            embed.add_field(
                name="📦 No Packs Available",
                value="No packs in marketplace yet. Be the first to create one!",
                inline=False
            )
        
        embed.set_footer(text="Marketplace • Use /create_pack to add your pack")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(MarketplaceCommands(bot))
