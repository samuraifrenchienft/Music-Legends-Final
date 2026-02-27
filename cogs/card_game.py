import discord
import sqlite3
import json
from discord.ext import commands
from discord.ext.commands import Cog
from discord import Interaction, app_commands, ui
from database import DatabaseManager, get_db
from card_data import CardDataManager
import stripe
from stripe_payments import stripe_manager
import random
import uuid
from typing import List, Dict

from ..config import settings

# Import required modules
from discord_cards import ArtistCard, Pack, CardCollection
from card_economy import PlayerEconomy, EconomyDisplay
from youtube_integration import youtube_integration
from views.song_selection import SongSelectionView
from services.image_cache import safe_image
from views.pack_opening import PackOpeningAnimator, open_pack_with_animation

class CardGameCog(Cog):
    def __init__(self, bot):
        print("🔥🔥🔥 CardGameCog INITIALIZING - COMMANDS SHOULD LOAD 🔥🔥🔥")
        self.bot = bot
        self.db = get_db()
        # Economy manager will be created per user
        self.card_manager = CardDataManager(self.db)
        # Dev user IDs from environment
        self.dev_users = settings.DEV_USER_IDS
        
        # Initialize database with sample cards
        self.card_manager.initialize_database_cards()
        print("✅ CardGameCog LOADED SUCCESSFULLY - All commands should be available")

    def _get_user(self, user_id: int, username: str, discord_tag: str) -> Dict:
        """Get or create user in database"""
        return self.db.get_or_create_user(user_id, username, discord_tag)

    def _get_user_economy(self, user_id: int) -> PlayerEconomy:
        """Get or create user economy from database"""
        # Use your PlayerEconomy class
        return PlayerEconomy(user_id=str(user_id), gold=500, tickets=0)
    
    def _convert_to_artist_card(self, card_data: Dict) -> ArtistCard:
        """Convert database card data to ArtistCard object"""
        # Use your ArtistCard class
        return ArtistCard(
            card_id=card_data['card_id'],
            artist=card_data['name'],
            song=card_data.get('title', 'Unknown Song'),
            youtube_url=card_data.get('youtube_url', ''),
            youtube_id=card_data.get('youtube_id', ''),
            view_count=card_data.get('view_count', 1000000),
            thumbnail=card_data.get('image_url', ''),
            rarity=card_data['rarity']
        )

    def _create_card_from_track(self, track: Dict, artist_name: str, rarity: str = "common") -> ArtistCard:
        """Create ArtistCard from YouTube track data"""
        import uuid
        
        # Extract video ID from URL
        video_id = track.get('video_id', '')
        if not video_id and 'youtube_url' in track:
            video_id = track['youtube_url'].split('v=')[-1].split('&')[0] if 'v=' in track['youtube_url'] else ''
        
        # Use your ArtistCard class
        return ArtistCard(
            card_id=str(uuid.uuid4()),
            artist=artist_name,
            song=track.get('title', 'Unknown Song'),
            youtube_url=track.get('youtube_url', ''),
            youtube_id=video_id,
            view_count=track.get('view_count', 1000000),
            thumbnail=track.get('thumbnail_url', ''),
            rarity=rarity
        )

    # Card viewing removed - use /view from gameplay.py

    # Collection command removed - use /my_collection from gameplay.py

    @app_commands.command(name="deck", description="Show your battle deck")
    async def show_deck(self, interaction: Interaction):
        # Get user
        user = self._get_user(
            interaction.user.id, 
            interaction.user.name, 
            str(interaction.user)
        )
        
        # Get user's deck (top 5 cards from collection)
        deck_cards = self.db.get_user_deck(interaction.user.id, 5)

        if len(deck_cards) < 5:
            await interaction.response.send_message(f"You need at least 5 cards to make a deck! You currently have {len(deck_cards)} cards.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"⚔️ {interaction.user.name}'s Battle Deck",
            description="Your top 5 cards for battle",
            color=discord.Color.red()
        )
        
        for i, card in enumerate(deck_cards, 1):
            total_power = card['impact'] + card['skill'] + card['longevity'] + card['culture']
            embed.add_field(
                name=f"Slot {i}: {card['rarity']} {card['name']}",
                value=f"ID: {card['card_id']} | Power: {total_power}\nImpact: {card['impact']} | Skill: {card['skill']} | Longevity: {card['longevity']} | Culture: {card['culture']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="View your battle statistics")
    async def show_stats(self, interaction: Interaction):
        # Get user
        user = self._get_user(
            interaction.user.id, 
            interaction.user.name, 
            str(interaction.user)
        )
        
        # Get user stats
        stats = self.db.get_user_stats(interaction.user.id)
        
        if not stats:
            await interaction.response.send_message("No stats found! Start battling to build your record.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📊 {interaction.user.name}'s Battle Stats",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="Total Battles", value=stats['total_battles'], inline=True)
        embed.add_field(name="Wins", value=stats['wins'], inline=True)
        embed.add_field(name="Losses", value=stats['losses'], inline=True)
        embed.add_field(name="Win Rate", value=f"{stats['win_rate']:.1f}%", inline=True)
        embed.add_field(name="Cards Collected", value=stats['total_cards'], inline=True)
        embed.add_field(name="Packs Opened", value=stats['packs_opened'], inline=True)
        embed.add_field(name="Victory Tokens", value=stats['victory_tokens'], inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the leaderboard")
    @app_commands.describe(metric="Leaderboard metric to view")
    async def show_leaderboard(self, interaction: Interaction, metric: str = "wins"):
        valid_metrics = ["wins", "total_battles", "win_rate", "total_cards", "packs_opened"]
        if metric not in valid_metrics:
            metric = "wins"
        
        leaderboard = self.db.get_leaderboard(metric, 10)
        
        if not leaderboard:
            await interaction.response.send_message("No leaderboard data available yet!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🏆 Leaderboard - {metric.replace('_', ' ').title()}",
            color=discord.Color.purple()
        )
        
        for i, entry in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            
            if metric == "win_rate":
                value = f"{entry['win_rate']:.1f}%"
            else:
                value = entry[metric]
            
            embed.add_field(
                name=f"{medal} {entry['username']}",
                value=value,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    # Battle commands are in cogs/battle_commands.py

    # Pack Commands
    @app_commands.command(name="open_pack", description="Open a pack and receive cards")
    @app_commands.describe(pack_id="Pack ID to open")
    async def open_pack(self, interaction: Interaction, pack_id: str):
        """Open a pack and show the cards received"""
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Get pack details
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pack_id, name, creator_id, pack_size, cards_data
                    FROM creator_packs 
                    WHERE pack_id = ? AND status = 'LIVE'
                """, (pack_id,))
                pack = cursor.fetchone()
            
            if not pack:
                await interaction.followup.send("❌ Pack not found or not available", ephemeral=True)
                return
            
            pack_id, pack_name, creator_id, pack_size, cards_data_json = pack
            
            # Parse cards data
            cards_data = json.loads(cards_data_json) if cards_data_json else []
            
            if not cards_data:
                await interaction.followup.send("❌ This pack has no cards", ephemeral=True)
                return
            
            # Add cards to user's collection
            received_cards = []
            for card_data in cards_data:
                # Check rarity for variant eligibility
                if card_data.get('rarity') in ['legendary', 'epic']:
                    # 10% chance for special variant
                    if random.random() < 0.1:
                        variant_frames = ['holographic', 'crystal', 'neon']
                        card_data['frame_style'] = random.choice(variant_frames)
                        card_data['foil'] = True
                        card_data['foil_effect'] = 'rainbow'
                        print(f"✨ Special variant generated: {card_data.get('name')} with {card_data['frame_style']} frame!")
                
                # Ensure card has an ID
                if 'card_id' not in card_data:
                    card_data['card_id'] = str(uuid.uuid4())
                # Add to master cards table
                self.db.add_card_to_master(card_data)
                # Add to user's collection
                self.db.add_card_to_collection(
                    user_id=interaction.user.id,
                    card_id=card_data['card_id'],
                    acquired_from='pack_opening'
                )
                received_cards.append(card_data)
            
            # Determine pack type based on pack data
            pack_type = 'gold' if any(c.get('rarity') in ['legendary', 'epic'] for c in received_cards) else 'community'
            
            # Use animation system for pack opening
            await open_pack_with_animation(
                interaction=interaction,
                pack_name=pack_name,
                pack_type=pack_type,
                cards=received_cards,
                pack_id=pack_id,
                delay=2.0  # 2 seconds between cards
            )

            # Log to changelog
            try:
                from services.changelog_manager import log_pack_creation
                log_pack_creation(pack_id, pack_name, interaction.user.id, 'opened')
            except Exception:
                pass

        except Exception as e:
            print(f"Error opening pack: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ Error opening pack. Please try again.", ephemeral=True)

    @app_commands.command(name="create_pack", description="Create a new pack with artist cards")
    @app_commands.describe(artist_name="Artist name (becomes pack name)")
    async def create_pack(self, interaction: Interaction, artist_name: str):
        """Create a new pack with artist cards - Interactive workflow"""
        pack_name = artist_name  # Pack name automatically equals artist name
        print(f"🔥 DEBUG: create_pack called by {interaction.user.name} - artist/pack: {artist_name}")
        
        # CRITICAL: Defer IMMEDIATELY before any async operations
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception as e:
            print(f"❌ Failed to defer interaction: {e}")
            return
        
        try:
            # Check if YouTube API key is configured
            youtube_api_key = settings.YOUTUBE_API_KEY
            if not youtube_api_key:
                await interaction.followup.send(
                    "❌ YouTube API is not configured. Please contact an administrator.\n"
                    "**For admins**: Set `YOUTUBE_API_KEY` in environment variables.",
                    ephemeral=True
                )
                return
            
            # Search for music videos on YouTube (the working way)
            from youtube_integration import youtube_integration
            print(f"🔥 DEBUG: Searching YouTube for {artist_name}")
            videos = youtube_integration.search_music_video(artist_name, limit=50)
            print(f"🔥 DEBUG: Found {len(videos) if videos else 0} videos")
            
            if not videos:
                await interaction.followup.send(
                    f"❌ Could not find videos for '{artist_name}'\n"
                    f"Please try:\n"
                    f"• Checking the artist name spelling\n"
                    f"• Using a different variation of the artist name\n"
                    f"• Trying a more popular artist", 
                    ephemeral=True
                )
                return
            
            # Create artist data from first video
            thumbnail_url = videos[0].get('thumbnail_url', '') if videos else ''
            print(f"🔥 DEBUG: Artist thumbnail URL: {thumbnail_url[:50] if thumbnail_url else 'None'}...")
            artist = {
                'name': artist_name,
                'image_url': thumbnail_url,
                'popularity': 75,  # Default for pack creation
                'followers': 1000000
            }
            
            tracks = videos
            
            # Show song selection UI
            selection_embed = discord.Embed(
                title="🎵 Select Songs for Your Pack",
                description=f"**{pack_name}** featuring **{artist['name']}**\n\nFound **{len(tracks)}** videos. Select up to 5 songs for your pack.",
                color=discord.Color.blue()
            )
            
            if artist.get('image_url'):
                safe_thumbnail = safe_image(artist['image_url'])
                if safe_thumbnail != artist['image_url']:
                    print(f"🖼️ Using fallback image for artist {artist['name']}: {artist['image_url'][:50]}...")
                selection_embed.set_thumbnail(url=safe_thumbnail)
            
            selection_embed.add_field(
                name="📋 Instructions",
                value="1. Select songs from the dropdown menu\n2. Click 'Confirm Selection' to create your pack\n3. Your pack will be published to the marketplace",
                inline=False
            )
            
            # Create callback for when songs are selected
            async def on_songs_selected(confirm_interaction: Interaction, selected_tracks: List[Dict]):
                await self._finalize_pack_creation(
                    confirm_interaction,
                    pack_name,
                    artist,
                    selected_tracks,
                    interaction.user.id
                )
            
            # Show selection view
            print(f"🔥 DEBUG: Creating SongSelectionView with {len(tracks)} tracks")
            view = SongSelectionView(tracks, max_selections=5, callback=on_songs_selected)
            print(f"🔥 DEBUG: Sending selection embed with view")
            await interaction.followup.send(embed=selection_embed, view=view, ephemeral=True)
            print(f"🔥 DEBUG: Selection UI sent successfully")
                
        except Exception as e:
            print(f"❌ Error creating pack: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ Something went wrong creating the pack. Please try again.", ephemeral=True)
    
    async def _finalize_pack_creation(self, interaction: Interaction, pack_name: str, artist: Dict, selected_tracks: List[Dict], creator_id: int):
        """Finalize pack creation after song selection"""
        print(f"🔥 DEBUG: Finalizing pack creation - {len(selected_tracks)} tracks selected")
        try:
            # Create pack in database
            print(f"🔥 DEBUG: Creating pack in database for {creator_id}")
            pack_id = self.db.create_creator_pack(
                creator_id=creator_id,
                name=pack_name,
                description=f"Artist pack featuring {artist['name']}",
                pack_size=len(selected_tracks)
            )
            print(f"🔥 DEBUG: Pack created with ID: {pack_id}")
            
            if not pack_id:
                print("❌ DEBUG: Pack creation failed - no pack_id returned")
                await interaction.followup.send("❌ Failed to create pack in database", ephemeral=True)
                return
            
            # Generate cards for each selected track
            cards_created = []
            for track in selected_tracks:
                try:
                    # Determine rarity randomly for better distribution
                    import random
                    rarity_roll = random.random()
                    if rarity_roll < 0.05:  # 5% legendary
                        rarity = "legendary"
                    elif rarity_roll < 0.15:  # 10% epic
                        rarity = "epic"
                    elif rarity_roll < 0.40:  # 25% rare
                        rarity = "rare"
                    else:  # 60% common
                        rarity = "common"
                    
                    # Create card from track data
                    artist_card = self._create_card_from_track(track, artist['name'], rarity)
                    
                    # Generate battle stats for the card
                    import random
                    base_stat = random.randint(15, 35)
                    battle_stats = {
                        'impact': base_stat + random.randint(-5, 10),
                        'skill': base_stat + random.randint(-5, 10),
                        'longevity': base_stat + random.randint(-5, 10),
                        'culture': base_stat + random.randint(-5, 10),
                        'hype': base_stat + random.randint(-5, 10)  # Add hype stat
                    }
                    
                    # Map rarity to tier
                    tier_map = {'common': 'community', 'rare': 'gold', 'epic': 'platinum',
                                'legendary': 'legendary', 'mythic': 'legendary'}
                    tier = tier_map.get(rarity.lower(), 'community')

                    # Convert to database format - include all required fields
                    card_data = {
                        'card_id': artist_card.card_id,
                        'name': artist_card.artist,
                        'artist_name': artist_card.artist,  # ADD: alias for display
                        'title': artist_card.song,
                        'rarity': artist_card.rarity,
                        'tier': tier,                       # ADD: mapped from rarity
                        'serial_number': artist_card.card_id,  # ADD: use card_id as serial
                        'print_number': 1,                  # ADD: print sequence
                        'quality': 'standard',              # ADD: card quality
                        'youtube_url': artist_card.youtube_url,
                        'image_url': artist_card.thumbnail,
                        'view_count': artist_card.view_count,
                        # Battle stats (required by database)
                        'impact': battle_stats['impact'],
                        'skill': battle_stats['skill'],
                        'longevity': battle_stats['longevity'],
                        'culture': battle_stats['culture'],
                        'hype': battle_stats['hype']
                    }
                    
                    # Add card to master list
                    print(f"🔧 Creating card: {artist_card.song} by {artist_card.artist}")
                    print(f"   Rarity: {rarity} | Power: {artist_card.power}")
                    print(f"   Image URL: {artist_card.thumbnail[:50] if artist_card.thumbnail else 'None'}...")
                    
                    success = self.db.add_card_to_master(card_data)
                    if success:
                        cards_created.append(card_data)
                        print(f"✅ Created card: {card_data['card_id']}")
                    else:
                        print(f"❌ Failed to create card: {card_data['card_id']}")
                    
                except Exception as e:
                    print(f"Error creating card for {track.get('title', 'Unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Update pack status to LIVE and add cards data
            print(f"🔥 DEBUG: Updating pack {pack_id} status to LIVE with {len(cards_created)} cards")
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE creator_packs 
                    SET status = 'LIVE', published_at = CURRENT_TIMESTAMP, cards_data = ?
                    WHERE pack_id = ?
                """, (json.dumps(cards_created), pack_id))
                conn.commit()
                print(f"🔥 DEBUG: Pack status updated to LIVE successfully")
            self.db.add_to_dev_supply(pack_id)
            
            # Trigger backup after pack is published to marketplace
            try:
                from services.backup_service import backup_service
                backup_path = await backup_service.backup_critical('pack_published', pack_id)
                if backup_path:
                    print(f"💾 Critical backup created after pack publication: {backup_path}")
            except Exception as e:
                print(f"⚠️ Backup trigger failed (non-critical): {e}")
            
            # Give creator a free copy of the pack
            for card in cards_created:
                self.db.add_card_to_collection(
                    user_id=creator_id,
                    card_id=card['card_id'],
                    acquired_from='pack_creation'
                )
            
            # Create visual confirmation embed
            embed = discord.Embed(
                title="✅ Pack Created Successfully!",
                description=f"**{pack_name}** featuring {artist['name']}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="📦 Pack ID", value=f"`{pack_id}`", inline=False)
            embed.add_field(name="🎤 Artist", value=artist['name'], inline=True)
            embed.add_field(name="🎵 Cards Created", value=str(len(cards_created)), inline=True)
            
            if artist.get('image_url'):
                safe_thumbnail = safe_image(artist['image_url'])
                if safe_thumbnail != artist['image_url']:
                    print(f"🖼️ Using fallback image for pack confirmation: {artist['image_url'][:50]}...")
                embed.set_thumbnail(url=safe_thumbnail)
            
            # Show all selected cards
            card_list = ""
            for i, card in enumerate(cards_created, 1):
                rarity_emoji = {"legendary": "🌟", "epic": "💜", "rare": "💙", "common": "⚪"}.get(card['rarity'], "⚪")
                card_list += f"{rarity_emoji} **{card['title']}** ({card['rarity'].title()})\n"
            
            embed.add_field(name="🎴 Pack Contents", value=card_list or "No cards", inline=False)
            
            # Add pack stats
            avg_power = sum(c['impact'] + c['skill'] + c['longevity'] + c['culture'] for c in cards_created) / len(cards_created) if cards_created else 0
            embed.add_field(name="📊 Average Power", value=f"{avg_power:.1f}", inline=True)
            
            rarity_counts = {}
            for card in cards_created:
                rarity_counts[card['rarity']] = rarity_counts.get(card['rarity'], 0) + 1
            rarity_text = " | ".join([f"{r.title()}: {c}" for r, c in rarity_counts.items()])
            embed.add_field(name="🎯 Rarity Distribution", value=rarity_text, inline=False)
            
            embed.add_field(
                name="📢 Status",
                value="✅ Published to Marketplace\n🎁 Free copy added to your collection",
                inline=False
            )
            
            embed.set_footer(text=f"Use /packs to browse marketplace | Use /collection to see your cards")
            await interaction.followup.send(embed=embed)

            # Log to changelog
            try:
                from services.changelog_manager import log_pack_creation
                log_pack_creation(pack_id, artist['name'], creator_id, 'creator')
            except Exception:
                pass

        except Exception as e:
            print(f"❌ Error finalizing pack: {e}")
            await interaction.followup.send("❌ An error occurred creating the pack. Please try again.", ephemeral=True)

    # /daily is in cogs/gameplay.py — /balance uses /collection or /rank

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Handle bot joining a new server"""
        # Register the server in database
        self.db.register_server(guild.id, guild.name, guild.owner_id)
        
        # Send welcome message to server owner
        try:
            owner = await self.bot.fetch_user(guild.owner_id)
            if owner:
                embed = discord.Embed(
                    title="🎵 Music Legends Bot Added!",
                    description=(
                        f"Thanks for adding Music Legends to **{guild.name}**!\n\n"
                        f"**Your Server ID:** `{guild.id}`"
                    ),
                    color=discord.Color.blue()
                )

                # REVENUE SHARING INFO (PRIMARY)
                embed.add_field(
                    name="💰 Server Revenue Sharing - FREE BOT!",
                    value=(
                        "**Earn 10-30% of ALL transactions in your server!**\n\n"
                        "📍 **Setup Process (Required for Payouts):**\n"
                        "1. Join Music Legends support server: [Support Server Link]\n"
                        "2. Create a ticket in #tickets channel\n"
                        "3. Provide this info:\n"
                        f"   • Server ID: `{guild.id}`\n"
                        f"   • Server Name: `{guild.name}`\n"
                        "   • Your Discord username\n"
                        "   • (Optional) NFT wallet for bonus share\n"
                        "4. Complete Stripe Connect verification\n"
                        "5. Start earning weekly payouts!\n\n"
                        "💵 **Revenue Share:**\n"
                        "• Base: **10%** of all transactions\n"
                        "• +1 NFT: **20%** total (+10% boost)\n"
                        "• +2 NFTs: **30%** MAX (+20% boost)\n\n"
                        "💳 **Payout Info:**\n"
                        "• Weekly payouts via Stripe\n"
                        "• $25 minimum threshold\n"
                        "• PayPal support coming soon!"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="🚀 Getting Started",
                    value="• Run `/setup_user_hub` in your main channel\n"
                          "• Players use `/claimpack` for free starter packs\n"
                          "• Use `/help` to see all commands",
                    inline=False
                )

                embed.set_footer(
                    text=f"Server ID: {guild.id} | Keep this ID for revenue setup ticket!"
                )
                await owner.send(embed=embed)
        except:
            pass  # Owner might have DMs disabled

    @app_commands.command(name="premium_subscribe", description="Upgrade your server to Premium")
    async def premium_subscribe(self, interaction: Interaction):
        """Subscribe to Premium features"""
        # Check if user is server admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only server administrators can manage subscriptions!", ephemeral=True)
            return
        
        server_info = self.db.get_server_info(interaction.guild.id)
        
        if server_info and server_info['subscription_tier'] == 'premium':
            await interaction.response.send_message("Your server is already Premium! 🎉", ephemeral=True)
            return
        
        # Create Stripe Checkout for subscription
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product': {
                            'name': 'Music Legends Premium',
                            'description': 'Unlock all premium features for your server',
                        },
                        'unit_amount': 1500,  # $15.00
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                }],
                success_url=f'https://discord.com/channels/{interaction.guild.id}',
                cancel_url=f'https://discord.com/channels/{interaction.guild.id}',
                customer_email=None,
                metadata={
                    'server_id': str(interaction.guild.id),
                    'server_name': interaction.guild.name,
                    'user_id': str(interaction.user.id),
                    'type': 'server_subscription'
                }
            )
            
            embed = discord.Embed(
                title="💎 Upgrade to Premium",
                description="Unlock all premium features for your server",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🌟 Premium Features",
                value="✅ Custom pack creation\n"
                      "✅ Creator economy (earn money!)\n"
                      "✅ Advanced battle modes\n"
                      "✅ Server analytics\n"
                      "✅ Priority support",
                inline=False
            )
            
            embed.add_field(
                name="💰 Pricing",
                value="$15.00 per month\nCancel anytime",
                inline=False
            )
            
            embed.add_field(
                name="🔗 Subscribe Now",
                value=f"[Click here to subscribe]({checkout_session.url})",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message("❌ Could not create subscription. Please try again later.", ephemeral=True)

    @app_commands.command(name="server_info", description="View server subscription status")
    async def server_info(self, interaction: Interaction):
        """Show server information and subscription status"""
        server_info = self.db.get_server_info(interaction.guild.id)
        
        if not server_info:
            await interaction.response.send_message("Server not found in database!", ephemeral=True)
            return
        
        is_premium = self.db.is_server_premium(interaction.guild.id)
        
        embed = discord.Embed(
            title=f"📊 {interaction.guild.name} Server Info",
            description=f"Status: {'💎 Premium' if is_premium else '🆓 Free'}",
            color=discord.Color.gold() if is_premium else discord.Color.blue()
        )
        
        embed.add_field(
            name="📈 Subscription Status",
            value=f"Tier: {server_info['subscription_tier'].title()}\n"
                  f"Status: {server_info['subscription_status'].title()}\n"
                  f"Owner: <@{server_info['server_owner_id']}>",
            inline=False
        )
        
        if not is_premium:
            embed.add_field(
                name="💎 Upgrade to Premium",
                value="Use `/premium_subscribe` to unlock:\n"
                      "• Custom pack creation\n"
                      "• Creator economy\n"
                      "• Advanced features",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # NOTE: "packs" command is handled by cogs/marketplace.py
    # This duplicate has been removed to avoid CommandAlreadyRegistered error

async def setup(bot):
    print("🔥🔥🔥 SETTING UP CARDCOG - REGISTERING COMMANDS 🔥🔥🔥")
    cog = CardGameCog(bot)
    await bot.add_cog(cog)
    print("✅ CARDCOG ADDED SUCCESSFULLY - All commands should be registered")
