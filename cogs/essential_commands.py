"""
Essential Game Commands - No Duplicates
Only the core commands needed for gameplay
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
import sqlite3
from database import DatabaseManager, db
from card_economy import CardEconomyManager, economy_manager
from stripe_payments import StripePaymentManager

class EssentialCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
        self.stripe = StripePaymentManager()
    
    @app_commands.command(name="collection", description="View your card collection")
    async def collection(self, interaction: Interaction):
        """View your card collection"""
        await interaction.response.send_message("📦 Collection feature coming soon!", ephemeral=True)
    
    @app_commands.command(name="drop", description="Create a card drop in this channel")
    async def drop(self, interaction: Interaction):
        """Create a card drop"""
        try:
            drop_result = self.economy.create_drop(
                interaction.channel_id,
                interaction.guild.id,
                interaction.user.id
            )
            
            if not drop_result['success']:
                await interaction.response.send_message(f"❌ {drop_result['error']}", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎴 CARD DROP! 🎴",
                description="React quickly to grab cards!",
                color=discord.Color.gold()
            )
            
            cards = drop_result['cards']
            for i, card in enumerate(cards, 1):
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card.get('tier', 'community'), "⚪")
                embed.add_field(
                    name=f"{tier_emoji} Card {i}",
                    value=f"{card.get('name', 'Unknown')}\nTier: {card.get('tier', 'community').title()}",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating drop: {e}", ephemeral=True)
    
    @app_commands.command(name="battle", description="Challenge someone to a card battle")
    async def battle(self, interaction: Interaction, opponent: discord.User):
        """Challenge someone to a battle"""
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't battle yourself!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{interaction.user.mention} has challenged {opponent.mention} to a card battle!",
            color=discord.Color.red()
        )
        embed.add_field(name="Status", value="⏳ Waiting for opponent to accept...")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="pack_add_artist_smart", description="Add artist card with YouTube integration")
    async def pack_add_artist_smart(self, interaction: Interaction, artist_name: str):
        """Add an artist card using YouTube data"""
        await interaction.response.defer()
        
        try:
            from services.game_integration import game_integration
            
            # Create artist from YouTube
            artist_data = await game_integration.create_artist_from_youtube(artist_name)
            
            if not artist_data:
                await interaction.followup.send(f"❌ Could not find artist '{artist_name}' on YouTube", ephemeral=True)
                return
            
            # Add to database
            card_data = {
                'card_id': f"artist_{artist_data['id']}",
                'name': artist_data['name'],
                'rarity': artist_data['tier'],
                'image_url': artist_data.get('image', ''),
                'spotify_url': f"https://youtube.com/channel/{artist_data['youtube_channel_id']}",
                'card_type': 'artist',
                'era': 'Modern',
                'impact': artist_data['game_data']['power_level'] // 5,
                'skill': artist_data['game_data']['power_level'] // 5,
                'longevity': artist_data['game_data']['power_level'] // 5,
                'culture': artist_data['game_data']['power_level'] // 5,
                'hype': artist_data['game_data']['power_level'] // 5
            }
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO cards 
                    (card_id, name, rarity, image_url, spotify_url, card_type, era, impact, skill, longevity, culture, hype)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    card_data['card_id'], card_data['name'], card_data['rarity'],
                    card_data['image_url'], card_data['spotify_url'], card_data['card_type'],
                    card_data['era'], card_data['impact'], card_data['skill'],
                    card_data['longevity'], card_data['culture'], card_data['hype']
                ))
                conn.commit()
            
            embed = discord.Embed(
                title="✅ Artist Card Created!",
                description=f"**{artist_data['name']}** has been added from YouTube",
                color=discord.Color.green()
            )
            embed.add_field(name="Tier", value=artist_data['tier'].title())
            embed.add_field(name="Power Level", value=artist_data['game_data']['power_level'])
            embed.set_thumbnail(url=artist_data.get('image', ''))
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating artist card: {e}", ephemeral=True)
    
    @app_commands.command(name="start_game", description="🎮 Start Music Legends in this server!")
    async def start_game(self, interaction: Interaction):
        """Initialize Music Legends with real artist cards from YouTube"""
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔒 Only server administrators can start the game!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🎵🎮 MUSIC LEGENDS IS NOW LIVE! 🎮🎵",
            description="""
**Welcome to Music Legends - The Ultimate Card Battle Game!**

🎴 **Collect cards** of your favorite music artists
⚔️ **Battle friends** with strategic card decks  
🎁 **Open daily packs** for rare cards
💰 **Trade & sell** cards in the marketplace

🚀 **Getting Started:**
• `/drop` - Create a card drop for the community
• `/collection` - View your card collection
• `/battle @friend` - Challenge someone to a card battle
• `/pack_add_artist_smart` - Add artists from YouTube

*Creating starter cards from YouTube... Please wait!*
            """,
            color=discord.Color.purple()
        )
        
        await interaction.followup.send(embed=embed)
        
        starter_artists = [
            "Taylor Swift", "Drake", "Bad Bunny", "The Weeknd", 
            "Ariana Grande", "Ed Sheeran", "Billie Eilish", "Post Malone",
            "Dua Lipa", "Olivia Rodrigo", "Doja Cat", "Harry Styles",
            "Bruno Mars", "Adele", "Justin Bieber", "Kendrick Lamar",
            "Rihanna", "Maroon 5", "Coldplay", "Imagine Dragons",
            "BTS", "Blackpink", "Travis Scott", "Cardi B",
            "Eminem", "Kanye West", "Lady Gaga", "Beyoncé"
        ]
        
        created_cards = []
        failed_artists = []
        
        from services.game_integration import game_integration
        
        for artist_name in starter_artists:
            try:
                artist_data = await game_integration.create_artist_from_youtube(artist_name)
                
                if artist_data:
                    card_data = {
                        'card_id': f"artist_{artist_data['id']}",
                        'name': artist_data['name'],
                        'rarity': artist_data['tier'],
                        'image_url': artist_data.get('image', ''),
                        'spotify_url': f"https://youtube.com/channel/{artist_data['youtube_channel_id']}",
                        'card_type': 'artist',
                        'era': 'Modern',
                        'impact': artist_data['game_data']['power_level'] // 5,
                        'skill': artist_data['game_data']['power_level'] // 5,
                        'longevity': artist_data['game_data']['power_level'] // 5,
                        'culture': artist_data['game_data']['power_level'] // 5,
                        'hype': artist_data['game_data']['power_level'] // 5
                    }
                    
                    with sqlite3.connect(self.db.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT OR IGNORE INTO cards 
                            (card_id, name, rarity, image_url, spotify_url, card_type, era, impact, skill, longevity, culture, hype)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            card_data['card_id'], card_data['name'], card_data['rarity'],
                            card_data['image_url'], card_data['spotify_url'], card_data['card_type'],
                            card_data['era'], card_data['impact'], card_data['skill'],
                            card_data['longevity'], card_data['culture'], card_data['hype']
                        ))
                        conn.commit()
                    
                    created_cards.append(card_data)
                else:
                    failed_artists.append(artist_name)
                    
            except Exception as e:
                print(f"Error creating card for {artist_name}: {e}")
                failed_artists.append(artist_name)
        
        if created_cards:
            success_embed = discord.Embed(
                title="✅ Game Successfully Started!",
                description=f"""
🎉 **Music Legends is ready to play!**

📊 **Cards Created:** {len(created_cards)} real artist cards
🎵 **Source:** YouTube music channels
⭐ **Tiers:** Community, Gold, Platinum, Legendary

🎮 **Try these commands:**
• `/drop` - Create a community drop
• `/collection` - View your cards
• `/battle @friend` - Start a card battle
• `/pack_add_artist_smart` - Add more artists from YouTube
                """,
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=success_embed)
            
            try:
                drop_result = economy_manager.create_drop(
                    interaction.channel_id,
                    interaction.guild.id, 
                    interaction.user.id
                )
                
                if drop_result['success']:
                    drop_embed = discord.Embed(
                        title="🎴 WELCOME DROP! 🎴",
                        description="First card drop created! React quickly to grab cards!",
                        color=discord.Color.gold()
                    )
                    
                    cards = drop_result['cards']
                    for i, card in enumerate(cards, 1):
                        tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card.get('tier', 'community'), "⚪")
                        drop_embed.add_field(
                            name=f"{tier_emoji} Card {i}",
                            value=f"{card.get('name', 'Unknown')}\nTier: {card.get('tier', 'community').title()}",
                            inline=True
                        )
                    
                    await interaction.followup.send(embed=drop_embed)
                    
            except Exception as e:
                print(f"Error creating welcome drop: {e}")
        
        else:
            error_embed = discord.Embed(
                title="❌ Game Start Failed",
                description="Could not create artist cards. Please check YouTube API configuration in .env.txt",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    @app_commands.command(name="pack", description="Buy and open a card pack with real money")
    @app_commands.describe(pack_name="Name of the pack to purchase")
    async def open_pack(self, interaction: Interaction, pack_name: str):
        """Buy a card pack with Stripe payment"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Find pack in database
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pack_id, pack_name, price, pack_size, creator_user_id
                    FROM creator_packs 
                    WHERE pack_name = ? AND status = 'live'
                    LIMIT 1
                """, (pack_name,))
                pack = cursor.fetchone()
            
            if not pack:
                await interaction.followup.send(f"❌ Pack '{pack_name}' not found. Use `/packs` to browse available packs.", ephemeral=True)
                return
            
            pack_id, name, price_gold, pack_size, creator_id = pack
            
            # Convert gold price to USD cents (100 gold = $1.00)
            price_cents = price_gold
            
            # Create Stripe checkout
            checkout = self.stripe.create_pack_purchase_checkout(
                pack_id=pack_id,
                buyer_id=interaction.user.id,
                pack_name=name,
                price_cents=price_cents
            )
            
            if not checkout['success']:
                await interaction.followup.send(f"❌ Payment error: {checkout['error']}", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="💳 Complete Your Purchase",
                description=f"**{name}**\n\n🎴 {pack_size} cards\n💰 ${price_cents/100:.2f} USD",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Next Steps",
                value=f"[Click here to pay with Stripe]({checkout['checkout_url']})\n\nAfter payment, your pack will be opened automatically!",
                inline=False
            )
            embed.set_footer(text=f"Creator earns 30% | You support the community!")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="pack_create", description="Create a new creator pack")
    @app_commands.describe(name="Pack name", description="Pack description", pack_size="Number of cards (5, 10, or 15)")
    async def pack_create(self, interaction: Interaction, name: str, description: str = "", pack_size: int = 10):
        """Create a new pack for sale"""
        if pack_size not in [5, 10, 15]:
            await interaction.response.send_message("❌ Pack size must be 5, 10, or 15 cards", ephemeral=True)
            return
        
        try:
            # Create draft pack
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO creator_packs 
                    (pack_id, creator_user_id, pack_name, description, pack_size, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'draft', CURRENT_TIMESTAMP)
                """, (f"pack_{interaction.user.id}_{name}", interaction.user.id, name, description, pack_size))
                conn.commit()
            
            embed = discord.Embed(
                title="✅ Pack Created!",
                description=f"**{name}** draft pack created!",
                color=discord.Color.green()
            )
            embed.add_field(name="Pack Size", value=f"{pack_size} cards")
            embed.add_field(name="Status", value="Draft")
            embed.add_field(name="Next Steps", value="Use `/pack_add_artist_smart` to add artists\nThen `/pack_publish` to publish for sale", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating pack: {e}", ephemeral=True)
    
    @app_commands.command(name="pack_preview", description="Preview your current draft pack")
    async def pack_preview(self, interaction: Interaction):
        """Preview draft pack"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pack_name, description, pack_size, status 
                    FROM creator_packs 
                    WHERE creator_user_id = ? AND status = 'draft'
                    LIMIT 1
                """, (interaction.user.id,))
                pack = cursor.fetchone()
            
            if not pack:
                await interaction.response.send_message("❌ You don't have a draft pack. Use `/pack_create` to create one!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📦 {pack[0]}",
                description=pack[1] or "No description",
                color=discord.Color.blue()
            )
            embed.add_field(name="Pack Size", value=f"{pack[2]} cards")
            embed.add_field(name="Status", value=pack[3].title())
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error previewing pack: {e}", ephemeral=True)
    
    @app_commands.command(name="pack_publish", description="Publish your pack for sale (requires Stripe payment)")
    @app_commands.describe(price_usd="Price in USD (e.g., 5 = $5.00)")
    async def pack_publish(self, interaction: Interaction, price_usd: int):
        """Publish pack for sale - requires Stripe payment for publishing fee"""
        if price_usd < 1 or price_usd > 100:
            await interaction.response.send_message("❌ Price must be between $1 and $100 USD", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if draft pack exists
                cursor.execute("""
                    SELECT pack_id, pack_name, pack_size 
                    FROM creator_packs 
                    WHERE creator_user_id = ? AND status = 'draft'
                    LIMIT 1
                """, (interaction.user.id,))
                pack = cursor.fetchone()
                
                if not pack:
                    await interaction.followup.send("❌ No draft pack found. Create one with `/pack_create`!", ephemeral=True)
                    return
                
                pack_id, pack_name, pack_size = pack
                
                # Create Stripe checkout for publishing fee
                checkout = self.stripe.create_pack_publish_checkout(
                    pack_id=pack_id,
                    creator_id=interaction.user.id,
                    pack_size=pack_size,
                    pack_name=pack_name
                )
                
                if not checkout['success']:
                    await interaction.followup.send(f"❌ Payment error: {checkout['error']}", ephemeral=True)
                    return
                
                # Store price in database (convert USD to cents)
                price_cents = price_usd * 100
                cursor.execute("""
                    UPDATE creator_packs 
                    SET price = ?, pending_payment_session = ?
                    WHERE pack_id = ?
                """, (price_cents, checkout['session_id'], pack_id))
                conn.commit()
            
            publish_fee = checkout['price_cents'] / 100
            
            embed = discord.Embed(
                title="💳 Complete Publishing Payment",
                description=f"**{pack_name}**\n\nTo publish your pack, pay the one-time publishing fee.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Publishing Fee", value=f"${publish_fee:.2f} USD", inline=True)
            embed.add_field(name="Pack Size", value=f"{pack_size} cards", inline=True)
            embed.add_field(name="Your Price", value=f"${price_usd:.2f} USD", inline=True)
            embed.add_field(
                name="💰 Your Earnings",
                value=f"You earn 30% of each sale = ${price_usd * 0.30:.2f} per pack sold",
                inline=False
            )
            embed.add_field(
                name="Next Steps",
                value=f"[Click here to pay publishing fee]({checkout['checkout_url']})\n\nAfter payment, your pack goes live immediately!",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    @app_commands.command(name="packs", description="Browse available creator packs")
    async def browse_packs(self, interaction: Interaction):
        """Browse available packs for purchase"""
        try:
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pack_name, description, price, pack_size, creator_user_id
                    FROM creator_packs 
                    WHERE status = 'live'
                    ORDER BY published_at DESC
                    LIMIT 10
                """)
                packs = cursor.fetchall()
            
            if not packs:
                await interaction.response.send_message("📦 No packs available yet! Creators can make packs with `/pack_create`", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🛍️ Available Card Packs",
                description="Browse and purchase creator packs!",
                color=discord.Color.purple()
            )
            
            for pack in packs[:5]:
                creator = await self.bot.fetch_user(pack[4])
                embed.add_field(
                    name=f"📦 {pack[0]}",
                    value=f"{pack[1] or 'No description'}\n💰 Price: {pack[2]} gold | 🎴 {pack[3]} cards\n👤 By: {creator.name}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error browsing packs: {e}", ephemeral=True)

async def setup(bot):
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(EssentialCommandsCog(bot))
    else:
        await bot.add_cog(
            EssentialCommandsCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
