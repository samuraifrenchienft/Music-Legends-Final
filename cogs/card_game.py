import discord
import os
import sqlite3
from discord.ext import commands
from discord.ext.commands import Cog
from discord import Interaction, app_commands, ui
from database import DatabaseManager
from card_data import CardDataManager
from stripe_payments import stripe_manager
import random
import uuid
from typing import List, Dict

# Import required modules
# TEMPORARILY DISABLED - causing import issues
# from discord_cards import ArtistCard, Pack, CardCollection
# from battle_engine import BattleEngine, BattleHistory
# from card_economy import PlayerEconomy, EconomyDisplay
from youtube_integration import youtube_integration
from views.song_selection import SongSelectionView

class CardGameCog(Cog):
    def __init__(self, bot):
        print("🔥🔥🔥 CardGameCog INITIALIZING - COMMANDS SHOULD LOAD 🔥🔥🔥")
        self.bot = bot
        self.db = DatabaseManager()
        # Economy manager will be created per user
        self.card_manager = CardDataManager(self.db)
        self.active_matches = {}  # match_id: MatchState
        
        # Dev user IDs from environment
        dev_ids = os.getenv("DEV_USER_IDS", "")
        self.dev_users = [int(id.strip()) for id in dev_ids.split(",") if id.strip().isdigit()]
        
        # Initialize database with sample cards
        self.card_manager.initialize_database_cards()
        print("✅ CardGameCog LOADED SUCCESSFULLY - All commands should be available")

    def _get_user(self, user_id: int, username: str, discord_tag: str) -> Dict:
        """Get or create user in database"""
        return self.db.get_or_create_user(user_id, username, discord_tag)

    def _get_user_economy(self, user_id: int):
        """Get or create user economy from database"""
        # TEMPORARY: Return basic dict instead of PlayerEconomy
        return {"user_id": str(user_id), "gold": 500, "tickets": 0}
    
    def _convert_to_artist_card(self, card_data: Dict):
        """Convert database card data to ArtistCard object"""
        # TEMPORARY: Return basic dict instead of ArtistCard
        return {
            "card_id": card_data['card_id'],
            "artist": card_data['name'],
            "song": card_data.get('title', 'Unknown Song'),
            "youtube_url": card_data.get('youtube_url', ''),
            "youtube_id": card_data.get('youtube_id', ''),
            "view_count": card_data.get('view_count', 1000000),
            "thumbnail": card_data.get('image_url', ''),
            "rarity": card_data['rarity']
        }

    def _create_card_from_track(self, track: Dict, artist_name: str, rarity: str = "common"):
        """Create ArtistCard from YouTube track data"""
        import uuid
        
        # Extract video ID from URL
        video_id = track.get('video_id', '')
        if not video_id and 'youtube_url' in track:
            video_id = track['youtube_url'].split('v=')[-1].split('&')[0] if 'v=' in track['youtube_url'] else ''
        
        # TEMPORARY: Return basic dict instead of ArtistCard
        return {
            "card_id": str(uuid.uuid4()),
            "artist": artist_name,
            "song": track.get('title', 'Unknown Song'),
            "youtube_url": track.get('youtube_url', ''),
            "youtube_id": video_id,
            "view_count": track.get('view_count', 1000000),
            "thumbnail": track.get('thumbnail_url', ''),
            "rarity": rarity
        }

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
        
        # Get user's deck (first 3 cards from collection)
        deck_cards = self.db.get_user_deck(interaction.user.id, 3)
        
        if len(deck_cards) < 3:
            await interaction.response.send_message(f"You need at least 3 cards to make a deck! You currently have {len(deck_cards)} cards.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"⚔️ {interaction.user.name}'s Battle Deck",
            description="Your top 3 cards for battle",
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

    @app_commands.command(name="battle", description="Challenge someone to a card battle")
    @app_commands.describe(
        opponent="User to challenge",
        wager="Wager level (required)"
    )
    @app_commands.choices(wager=[
        app_commands.Choice(name="Casual (50 gold)", value="casual"),
        app_commands.Choice(name="Standard (100 gold)", value="standard"),
        app_commands.Choice(name="High Stakes (250 gold)", value="high"),
        app_commands.Choice(name="Extreme (500 gold)", value="extreme")
    ])
    async def battle_challenge(self, interaction: Interaction, opponent: discord.User, wager: str):
        from config.economy import BATTLE_WAGERS, FIRST_WIN_BONUS
        
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)
            return
        
        if opponent.bot:
            await interaction.response.send_message("You can't battle a bot!", ephemeral=True)
            return

        # Get wager config
        wager_config = BATTLE_WAGERS.get(wager, BATTLE_WAGERS["casual"])
        wager_amount = wager_config["wager"]

        # Check if challenger has enough gold
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT gold FROM user_inventory WHERE user_id = ?", (interaction.user.id,))
            challenger_gold = cursor.fetchone()
            challenger_gold = challenger_gold[0] if challenger_gold else 0
            
            cursor.execute("SELECT gold FROM user_inventory WHERE user_id = ?", (opponent.id,))
            opponent_gold = cursor.fetchone()
            opponent_gold = opponent_gold[0] if opponent_gold else 0

        if challenger_gold < wager_amount:
            await interaction.response.send_message(
                f"❌ You need {wager_amount} gold to wager! You have {challenger_gold} gold.", 
                ephemeral=True
            )
            return

        # Get both users
        challenger = self._get_user(interaction.user.id, interaction.user.name, str(interaction.user))
        challenged = self._get_user(opponent.id, opponent.name, str(opponent))

        # Check if both have at least 1 card (simplified battle)
        challenger_deck = self.db.get_user_deck(interaction.user.id, 1)
        challenged_deck = self.db.get_user_deck(opponent.id, 1)

        if len(challenger_deck) < 1:
            await interaction.response.send_message("You need at least 1 card to battle! Use `/drop` to get cards.", ephemeral=True)
            return

        if len(challenged_deck) < 1:
            await interaction.response.send_message(f"{opponent.name} doesn't have any cards to battle with!", ephemeral=True)
            return

        # Create match with wager info
        match_id = str(uuid.uuid4())[:8]
        player_a = PlayerState(
            user_id=interaction.user.id, 
            deck=[self._convert_to_battle_card(card) for card in challenger_deck]
        )
        player_b = PlayerState(
            user_id=opponent.id, 
            deck=[self._convert_to_battle_card(card) for card in challenged_deck]
        )
        
        match = MatchState(match_id=match_id, a=player_a, b=player_b)
        match.wager_type = wager
        match.wager_amount = wager_amount
        self.active_matches[match_id] = match

        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{interaction.user.mention} has challenged {opponent.mention} to a card battle!",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="💰 Wager",
            value=f"**{wager.title()}**: {wager_amount} gold\n"
                  f"Winner gets: {wager_amount + wager_config['win_bonus']} gold + {wager_config['win_xp']} XP",
            inline=False
        )
        
        embed.add_field(name="Match ID", value=f"`{match_id}`", inline=True)
        
        # Check if opponent has enough gold
        if opponent_gold < wager_amount:
            embed.add_field(
                name="⚠️ Warning",
                value=f"{opponent.name} only has {opponent_gold} gold (needs {wager_amount})",
                inline=False
            )
        
        embed.set_footer(text=f"Use /battle_accept {match_id} to accept the challenge")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="battle_accept", description="Accept a battle challenge")
    @app_commands.describe(match_id="Match ID to accept")
    async def battle_accept(self, interaction: Interaction, match_id: str):
        match = self.active_matches.get(match_id)
        if not match:
            await interaction.response.send_message("Match not found!", ephemeral=True)
            return

        if interaction.user.id not in [match.a.user_id, match.b.user_id]:
            await interaction.response.send_message("You're not part of this match!", ephemeral=True)
            return

        # Start the battle
        await self._start_battle_round(interaction, match, 0)

    async def _start_battle_round(self, interaction: Interaction, match: MatchState, round_index: int):
        """Start a specific round of battle"""
        if round_index >= 3:
            await self._end_battle(interaction, match)
            return

        card_a = match.a.deck[round_index]
        card_b = match.b.deck[round_index]

        # Determine category
        if round_index == 1 and match.last_round_loser:
            # Round 2: loser chooses - for now, random
            category = random.choice(STATS)
        else:
            category = pick_category_option_a(match)

        # Resolve round
        winner, debug = resolve_round(
            card_a, card_b, category, 
            match.a.hype_bonus, match.b.hype_bonus
        )

        # Apply momentum
        if winner == "A":
            match.a.score += 1
            apply_momentum(match.a, match.b)
            match.last_round_loser = match.b.user_id
            winner_id = match.a.user_id
            winner_name = "Player A"
        else:
            match.b.score += 1
            apply_momentum(match.b, match.a)
            match.last_round_loser = match.a.user_id
            winner_id = match.b.user_id
            winner_name = "Player B"

        # Create result embed
        embed = discord.Embed(
            title=f"🎯 Round {round_index + 1} Results",
            description=f"Category: **{category.title()}**",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name=f"Card A: {card_a.name}",
            value=f"Stat: {debug['a_stat']} + Bonus: {debug['a_hype_bonus']} = **{debug['a_power']}**",
            inline=True
        )
        
        embed.add_field(
            name=f"Card B: {card_b.name}",
            value=f"Stat: {debug['b_stat']} + Bonus: {debug['b_hype_bonus']} = **{debug['b_power']}**",
            inline=True
        )
        
        embed.add_field(
            name="Winner",
            value=f"🏆 {winner_name}",
            inline=False
        )

        embed.set_footer(text=f"Score: A={match.a.score} | B={match.b.score}")

        await interaction.response.send_message(embed=embed)

        # Check for match end or continue
        if match.a.score >= 2 or match.b.score >= 2:
            await self._end_battle(interaction, match)
        else:
            # Auto-continue to next round for now
            await self._start_battle_round(interaction, match, round_index + 1)

    async def _end_battle(self, interaction: Interaction, match: MatchState):
        """End the battle and distribute wager rewards"""
        from config.economy import BATTLE_WAGERS, FIRST_WIN_BONUS, calculate_battle_rewards
        from datetime import date
        
        is_tie = match.a.score == match.b.score
        winner_id = None
        loser_id = None
        
        if not is_tie:
            winner_id = match.a.user_id if match.a.score > match.b.score else match.b.user_id
            loser_id = match.b.user_id if match.a.score > match.b.score else match.a.user_id
        
        # Get wager info
        wager_type = getattr(match, 'wager_type', 'casual')
        wager_amount = getattr(match, 'wager_amount', 50)
        wager_config = BATTLE_WAGERS.get(wager_type, BATTLE_WAGERS["casual"])
        
        # Calculate rewards
        winner_gold = 0
        winner_xp = 0
        loser_gold = 0
        loser_xp = 0
        first_win_bonus = 0
        
        if is_tie:
            # Tie - both get wager back + tie bonus
            tie_gold = wager_config["tie_gold"]
            tie_xp = wager_config["tie_xp"]
            winner_gold = tie_gold  # Both players get this
            winner_xp = tie_xp
        else:
            # Winner gets wager + bonus
            win_rewards = calculate_battle_rewards(wager_type, "win")
            winner_gold = win_rewards["gold"]
            winner_xp = win_rewards["xp"]
            
            # Loser gets consolation
            loss_rewards = calculate_battle_rewards(wager_type, "loss")
            loser_gold = loss_rewards["gold"]
            loser_xp = loss_rewards["xp"]
        
        # Apply rewards to database
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            today = date.today().isoformat()
            
            if is_tie:
                # Both players get tie rewards (wager returned)
                for player_id in [match.a.user_id, match.b.user_id]:
                    cursor.execute("""
                        INSERT INTO user_inventory (user_id, gold, xp)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            gold = gold + ?,
                            xp = xp + ?
                    """, (player_id, winner_gold, winner_xp, winner_gold, winner_xp))
            else:
                # Check for first win bonus
                cursor.execute("""
                    SELECT first_win_today, last_first_win FROM user_inventory WHERE user_id = ?
                """, (winner_id,))
                first_win_row = cursor.fetchone()
                
                if first_win_row:
                    first_win_claimed, last_first_win = first_win_row
                    if last_first_win != today:
                        first_win_bonus = FIRST_WIN_BONUS["gold"]
                        winner_gold += first_win_bonus
                        winner_xp += FIRST_WIN_BONUS["xp"]
                else:
                    first_win_bonus = FIRST_WIN_BONUS["gold"]
                    winner_gold += first_win_bonus
                    winner_xp += FIRST_WIN_BONUS["xp"]
                
                # Winner: add gold and XP, deduct wager already happened at accept
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, gold, xp, first_win_today, last_first_win)
                    VALUES (?, ?, ?, 1, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        gold = gold + ?,
                        xp = xp + ?,
                        first_win_today = 1,
                        last_first_win = ?
                """, (winner_id, winner_gold, winner_xp, today, winner_gold, winner_xp, today))
                
                # Loser: deduct wager, add consolation
                net_loss = wager_amount - loser_gold
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, gold, xp)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        gold = MAX(0, gold - ?),
                        xp = xp + ?
                """, (loser_id, 0, loser_xp, net_loss, loser_xp))
            
            conn.commit()
        
        # Record match in database
        match_data = {
            'match_id': match.match_id,
            'player_a_id': match.a.user_id,
            'player_b_id': match.b.user_id,
            'winner_id': winner_id,
            'final_score_a': match.a.score,
            'final_score_b': match.b.score,
            'match_type': wager_type
        }
        self.db.record_match(match_data)
        
        # Create result embed
        if is_tie:
            embed = discord.Embed(
                title="🤝 Battle Tied!",
                description=f"Both players fought to a draw!",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Final Score", value=f"A: {match.a.score} | B: {match.b.score}", inline=False)
            embed.add_field(
                name="💰 Rewards (Each)",
                value=f"Gold: +{winner_gold} (wager returned)\nXP: +{winner_xp}",
                inline=False
            )
        else:
            winner_mention = f"<@{winner_id}>"
            loser_mention = f"<@{loser_id}>"
            
            embed = discord.Embed(
                title="🏆 Battle Complete!",
                description=f"**Winner:** {winner_mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Final Score", value=f"A: {match.a.score} | B: {match.b.score}", inline=False)
            
            winner_reward_text = f"💰 Gold: +{winner_gold}"
            if first_win_bonus > 0:
                winner_reward_text += f" (includes +{first_win_bonus} first win bonus!)"
            winner_reward_text += f"\n⭐ XP: +{winner_xp}"
            
            embed.add_field(
                name=f"🎉 Winner Rewards",
                value=winner_reward_text,
                inline=True
            )
            
            embed.add_field(
                name=f"😢 Loser",
                value=f"💰 Gold: -{wager_amount - loser_gold} (lost wager)\n⭐ XP: +{loser_xp} (consolation)",
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
        
        # Clean up match
        del self.active_matches[match.match_id]

    # Pack Commands
    @app_commands.command(name="open_pack", description="Open a pack and receive cards")
    @app_commands.describe(pack_id="Pack ID to open")
    async def open_pack(self, interaction: Interaction, pack_id: str):
        """Open a pack and show the cards received"""
        await interaction.response.defer(ephemeral=False)
        
        try:
            # Get pack details
            with sqlite3.connect(self.db.db_path) as conn:
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
            import json
            cards_data = json.loads(cards_data_json) if cards_data_json else []
            
            if not cards_data:
                await interaction.followup.send("❌ This pack has no cards", ephemeral=True)
                return
            
            # Add cards to user's collection
            received_cards = []
            for card_data in cards_data:
                # Add to master cards table
                card_id = self.db.add_card_to_master(card_data)
                # Add to user's collection
                self.db.add_card_to_collection(
                    user_id=interaction.user.id,
                    card_id=card_id,
                    acquired_from='pack_opening'
                )
                received_cards.append(card_data)
            
            # Create visual display
            embed = discord.Embed(
                title=f"🎉 Pack Opened: {pack_name}",
                description=f"You received {len(received_cards)} cards!",
                color=discord.Color.purple()
            )
            
            # Show all cards
            card_list = ""
            for i, card in enumerate(received_cards, 1):
                rarity = card.get('rarity', 'common')
                rarity_emoji = {"legendary": "🌟", "epic": "💜", "rare": "💙", "common": "⚪"}.get(rarity, "⚪")
                card_name = card.get('name', 'Unknown')
                card_title = card.get('title', '')
                display = f"{card_name} - {card_title}" if card_title else card_name
                card_list += f"{rarity_emoji} **{display}** ({rarity.title()})\n"
            
            embed.add_field(name="🎴 Cards Received", value=card_list or "No cards", inline=False)
            
            # Add stats
            rarity_counts = {}
            for card in received_cards:
                rarity = card.get('rarity', 'common')
                rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
            
            rarity_text = " | ".join([f"{r.title()}: {c}" for r, c in rarity_counts.items()])
            embed.add_field(name="📊 Rarity Breakdown", value=rarity_text, inline=False)
            
            embed.set_footer(text=f"Use /collection to view all your cards")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error opening pack: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error opening pack: {e}", ephemeral=True)

    @app_commands.command(name="create_pack", description="Create a new pack with artist cards")
    @app_commands.describe(pack_name="Name for your pack", artist_name="Main artist for the pack")
    async def create_pack(self, interaction: Interaction, pack_name: str, artist_name: str):
        """Create a new pack with artist cards - Interactive workflow"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Search for music videos on YouTube (the working way)
            from youtube_integration import youtube_integration
            videos = youtube_integration.search_music_video(artist_name, limit=50)
            
            if not videos:
                await interaction.followup.send(f"❌ Could not find videos for '{artist_name}'", ephemeral=True)
                return
            
            # Create artist data from first video
            artist = {
                'name': artist_name,
                'image_url': videos[0].get('thumbnail_url', '') if videos else '',
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
                selection_embed.set_thumbnail(url=artist['image_url'])
            
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
            view = SongSelectionView(tracks, max_selections=5, callback=on_songs_selected)
            await interaction.followup.send(embed=selection_embed, view=view, ephemeral=True)
                
        except Exception as e:
            print(f"❌ Error creating pack: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    async def _finalize_pack_creation(self, interaction: Interaction, pack_name: str, artist: Dict, selected_tracks: List[Dict], creator_id: int):
        """Finalize pack creation after song selection"""
        try:
            # Create pack in database
            pack_id = self.db.create_creator_pack(
                creator_id=creator_id,
                name=pack_name,
                description=f"Artist pack featuring {artist['name']}",
                pack_size=len(selected_tracks)
            )
            
            if not pack_id:
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
                    
                    # Convert to database format
                    card_data = {
                        'card_id': artist_card['card_id'],
                        'name': artist_card['artist'],
                        'title': artist_card['song'],
                        'rarity': artist_card['rarity'],
                        'youtube_url': artist_card['youtube_url'],
                        'image_url': artist_card['thumbnail'],
                        'view_count': artist_card['view_count'],
                        'power': 50,  # Default power
                        'tier': 1     # Default tier
                    }
                    
                    # Add card to master list
                    print(f"🔧 Creating card: {artist_card['song']} by {artist_card['artist']}")
                    print(f"   Rarity: {rarity}")
                    print(f"   Image URL: {artist_card['thumbnail'][:50] if artist_card['thumbnail'] else 'None'}...")
                    
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
            
            # Store cards in pack and publish to marketplace
            import sqlite3
            import json
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE creator_packs 
                    SET status = 'LIVE', published_at = CURRENT_TIMESTAMP, cards_data = ?
                    WHERE pack_id = ?
                """, (json.dumps(cards_created), pack_id))
                conn.commit()
            
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
                embed.set_thumbnail(url=artist['image_url'])
            
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
            
        except Exception as e:
            print(f"❌ Error finalizing pack: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="daily", description="Claim your daily reward")
    async def daily_claim(self, interaction: Interaction):
        """Claim daily reward with streak bonuses"""
        await interaction.response.defer()
        
        try:
            # TEMPORARY: Basic daily reward without database
            embed = discord.Embed(
                title="🎁 Daily Reward Claimed!",
                description="**Streak:** 1 day",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="💰 Rewards",
                value="+100 gold (base)",
                inline=False
            )
            
            embed.set_footer(text="Database economy coming soon!")
            
            await interaction.followup.send(embed=embed)
                
        except Exception as e:
            print(f"Error in daily claim: {e}")
            await interaction.followup.send("❌ Error claiming daily reward", ephemeral=True)

    @app_commands.command(name="balance", description="Check your gold and tickets")
    async def check_balance(self, interaction: Interaction):
        """Check user's balance"""
        await interaction.response.defer()
        
        try:
            # TEMPORARY: Basic balance without database
            embed = discord.Embed(
                title=f"💰 {interaction.user.name}'s Balance",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="💰 Gold",
                value="**500**",
                inline=True
            )
            
            embed.add_field(
                name="🎫 Tickets",
                value="**0**",
                inline=True
            )
            
            embed.add_field(
                name="🎁 Daily Claim",
                value="✅ Available!",
                inline=True
            )
            
            embed.set_footer(text="Database economy coming soon!")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"Error checking balance: {e}")
            await interaction.followup.send("❌ Error checking balance", ephemeral=True)


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
                    description="Thanks for adding Music Legends to your server!",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="🚀 Getting Started",
                    value="• `/claimpack` - Get your first free pack\n"
                          "• `/battle` - Challenge friends to card battles\n"
                          "• `/help` - See all available commands",
                    inline=False
                )
                
                embed.add_field(
                    name="💎 Premium Features",
                    value="• Custom pack creation\n"
                          "• Creator economy\n"
                          "• Advanced analytics\n"
                          "Use `/premium_subscribe` to upgrade",
                    inline=False
                )
                
                embed.set_footer(text="Type /help to see all commands!")
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
            await interaction.response.send_message(f"Error creating subscription: {str(e)}", ephemeral=True)

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

    @app_commands.command(name="delete_pack", description="[DEV ONLY] Delete a pack by ID")
    @app_commands.describe(pack_id="Pack ID to delete")
    async def delete_pack(self, interaction: Interaction, pack_id: str):
        """Delete a pack - DEV ONLY"""
        # Check if user is dev
        if interaction.user.id not in self.dev_users:
            await interaction.response.send_message("❌ This command is restricted to developers only.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if pack exists
                cursor.execute("SELECT name, creator_id FROM creator_packs WHERE pack_id = ?", (pack_id,))
                pack = cursor.fetchone()
                
                if not pack:
                    await interaction.followup.send(f"❌ Pack `{pack_id}` not found", ephemeral=True)
                    return
                
                pack_name, creator_id = pack
                
                # Delete pack
                cursor.execute("DELETE FROM creator_packs WHERE pack_id = ?", (pack_id,))
                deleted = cursor.rowcount
                
                conn.commit()
                
                if deleted > 0:
                    embed = discord.Embed(
                        title="🗑️ Pack Deleted",
                        description=f"Successfully deleted pack",
                        color=discord.Color.red()
                    )
                    embed.add_field(name="Pack ID", value=f"`{pack_id}`", inline=False)
                    embed.add_field(name="Name", value=pack_name, inline=True)
                    embed.add_field(name="Creator ID", value=creator_id, inline=True)
                    
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send("❌ Failed to delete pack", ephemeral=True)
                    
        except Exception as e:
            print(f"Error deleting pack: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="server_analytics", description="View server usage analytics")
    async def server_analytics(self, interaction: Interaction, days: int = 30):
        """Show server usage analytics"""
        # Check if server is premium
        if not self.db.is_server_premium(interaction.guild.id):
            await interaction.response.send_message("Analytics is a Premium feature! Use `/premium_subscribe` to upgrade.", ephemeral=True)
            return
        
        # Check if user is server admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only server administrators can view analytics!", ephemeral=True)
            return
        
        analytics = self.db.get_server_analytics(interaction.guild.id, days)
        
        embed = discord.Embed(
            title=f"📊 {interaction.guild.name} Analytics",
            description=f"Usage statistics for the last {days} days",
            color=discord.Color.gold()
        )
        
        metrics = analytics['metrics']
        
        embed.add_field(
            name="🎴 Pack Creation",
            value=f"{metrics.get('packs_created', 0)} packs created",
            inline=True
        )
        
        embed.add_field(
            name="⚔️ Battles",
            value=f"{metrics.get('battles_fought', 0)} battles fought",
            inline=True
        )
        
        embed.add_field(
            name="👥 Active Users",
            value=f"{metrics.get('users_active', 0)} active users",
            inline=True
        )
        
        embed.set_footer(text="Analytics updated daily")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="packs", description="Browse available creator packs")
    async def browse_packs(self, interaction: Interaction):
        live_packs = self.db.get_live_packs(limit=20)
        
        if not live_packs:
            await interaction.response.send_message("No creator packs available yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🛍️ Creator Packs Store",
            description="Browse and purchase packs created by the community!",
            color=discord.Color.blue()
        )
        
        for pack in live_packs[:10]:  # Show max 10 packs
            cards = eval(pack['cards_data'])
            rarity_count = {}
            for card in cards:
                rarity = card.get('rarity', 'Common')
                rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
            
            rarity_display = []
            for rarity, count in rarity_count.items():
                emoji = {"Common": "🟩", "Rare": "🟦", "Epic": "🟪", "Legendary": "⭐"}.get(rarity, "🎴")
                rarity_display.append(f"{emoji}{count}")
            
            embed.add_field(
                name=f"📦 {pack['name']} by {pack['creator_name']}",
                value=f"💰 ${pack['price_cents']/100:.2f} | 🎴 {len(cards)} cards | {' '.join(rarity_display)}\n"
                      f"🛒 {pack['total_purchases']} purchases",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CardGameCog(bot))
