import discord
import os
import sqlite3
import json
from discord.ext import commands
from discord.ext.commands import Cog
from discord import Interaction, app_commands, ui
from discord_cards import ArtistCard, build_artist_embed, PackDrop, build_pack_open_embed, PackOpenView
from battle_engine import ArtistCard as BattleCard, MatchState, PlayerState, resolve_round, apply_momentum, pick_category_option_a, STATS
from database import DatabaseManager
from card_data import CardDataManager
from spotify_integration import spotify_integration
from stripe_payments import stripe_manager
import random
import uuid
from typing import List, Dict

class CardGameCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.card_manager = CardDataManager(self.db)
        self.active_matches = {}  # match_id: MatchState
        
        # Initialize database with sample cards
        self.card_manager.initialize_database_cards()

    def _get_user(self, user_id: int, username: str, discord_tag: str) -> Dict:
        """Get or create user in database"""
        return self.db.get_or_create_user(user_id, username, discord_tag)

    def _convert_to_artist_card(self, card_data: Dict) -> ArtistCard:
        """Convert database card data to ArtistCard object"""
        return ArtistCard(
            card_id=card_data['card_id'],
            name=card_data['name'],
            title=card_data.get('title', 'Artist'),
            rarity=card_data['rarity'],
            era=card_data.get('era', 'Unknown'),
            variant=card_data.get('variant', 'Classic'),
            impact=card_data.get('impact', 0),
            skill=card_data.get('skill', 0),
            longevity=card_data.get('longevity', 0),
            culture=card_data.get('culture', 0),
            hype=card_data.get('hype', 0),
            image_url=card_data.get('image_url'),
            spotify_url=card_data.get('spotify_url'),
            youtube_url=card_data.get('youtube_url')
        )

    def _convert_to_battle_card(self, card_data: Dict) -> BattleCard:
        """Convert database card data to BattleCard object"""
        return BattleCard(
            id=card_data['card_id'],
            name=card_data['name'],
            rarity=card_data['rarity'],
            impact=card_data.get('impact', 0),
            skill=card_data.get('skill', 0),
            longevity=card_data.get('longevity', 0),
            culture=card_data.get('culture', 0),
            hype=card_data.get('hype', 0)
        )

    @app_commands.command(name="card", description="View a specific card")
    @app_commands.describe(card_id="ID of the card to view")
    async def view_card(self, interaction: Interaction, card_id: str):
        # Get user
        user = self._get_user(
            interaction.user.id, 
            interaction.user.name, 
            str(interaction.user)
        )
        
        # Find card in database
        card_data = self.card_manager.get_card_by_id(card_id)
        if not card_data:
            await interaction.response.send_message("Card not found!", ephemeral=True)
            return

        # Convert to display card
        display_card = self._convert_to_artist_card(card_data)
        embed = build_artist_embed(display_card)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="collection", description="Show your card collection")
    async def show_collection(self, interaction: Interaction):
        # Get user
        user = self._get_user(
            interaction.user.id, 
            interaction.user.name, 
            str(interaction.user)
        )
        
        # Get user's collection
        collection = self.db.get_user_collection(interaction.user.id)
        
        if not collection:
            await interaction.response.send_message("You don't have any cards yet! Use `/pack` to open some packs.", ephemeral=True)
            return

        # Create embed with collection
        embed = discord.Embed(
            title=f"🎴 {interaction.user.name}'s Collection",
            description=f"Total cards: {len(collection)}",
            color=discord.Color.blue()
        )
        
        # Group by rarity
        rarity_groups = {}
        for card in collection:
            rarity = card['rarity']
            if rarity not in rarity_groups:
                rarity_groups[rarity] = []
            rarity_groups[rarity].append(card)
        
        # Add fields for each rarity
        rarity_emojis = {"Common": "🟩", "Rare": "🟦", "Epic": "🟪", "Legendary": "⭐", "Mythic": "🔴"}
        
        for rarity in ["Legendary", "Epic", "Rare", "Common"]:
            if rarity in rarity_groups:
                cards = rarity_groups[rarity][:5]  # Limit to 5 per rarity
                card_list = "\n".join([f"• {card['name']} ({card['card_id']})" for card in cards])
                if len(rarity_groups[rarity]) > 5:
                    card_list += f"\n... and {len(rarity_groups[rarity]) - 5} more"
                
                embed.add_field(
                    name=f"{rarity_emojis.get(rarity, '🎴')} {rarity} ({len(rarity_groups[rarity])})",
                    value=card_list,
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)

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
    @app_commands.describe(opponent="User to challenge")
    async def battle_challenge(self, interaction: Interaction, opponent: discord.User):
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)
            return

        # Get both users
        challenger = self._get_user(interaction.user.id, interaction.user.name, str(interaction.user))
        challenged = self._get_user(opponent.id, opponent.name, str(opponent))

        # Check if both have decks
        challenger_deck = self.db.get_user_deck(interaction.user.id, 3)
        challenged_deck = self.db.get_user_deck(opponent.id, 3)

        if len(challenger_deck) < 3:
            await interaction.response.send_message("You need at least 3 cards to battle! Use `/pack` to get more cards.", ephemeral=True)
            return

        if len(challenged_deck) < 3:
            await interaction.response.send_message(f"{opponent.name} doesn't have enough cards to battle!", ephemeral=True)
            return

        # Create match
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
        self.active_matches[match_id] = match

        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{interaction.user.mention} has challenged {opponent.mention} to a card battle!",
            color=discord.Color.red()
        )
        embed.add_field(name="Match ID", value=match_id, inline=False)
        embed.set_footer(text="Use /battle_accept to accept the challenge")

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
        """End the battle and show final results"""
        winner_id = match.a.user_id if match.a.score > match.b.score else match.b.user_id
        winner_name = "Player A" if match.a.score > match.b.score else "Player B"
        
        # Record match in database
        match_data = {
            'match_id': match.match_id,
            'player_a_id': match.a.user_id,
            'player_b_id': match.b.user_id,
            'winner_id': winner_id,
            'final_score_a': match.a.score,
            'final_score_b': match.b.score,
            'match_type': 'casual'
        }
        self.db.record_match(match_data)
        
        embed = discord.Embed(
            title="🏆 Battle Complete!",
            description=f"Winner: **{winner_name}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Final Score", value=f"A: {match.a.score} | B: {match.b.score}", inline=False)
        embed.add_field(name="Reward", value="+1 Victory Pack Token", inline=False)
        
        await interaction.followup.send(embed=embed)
        
        # Clean up match
        del self.active_matches[match.match_id]

    @app_commands.command(name="pack", description="Open a card pack")
    @app_commands.describe(pack_type="Type of pack to open")
    async def open_pack(self, interaction: Interaction, pack_type: str = "Daily"):
        # Get user
        user = self._get_user(
            interaction.user.id, 
            interaction.user.name, 
            str(interaction.user)
        )
        
        # Generate pack drop
        card_ids = self.card_manager.generate_pack_drop(pack_type)
        
        if not card_ids:
            await interaction.response.send_message("No cards available for this pack type!", ephemeral=True)
            return

        # Get card data for display
        cards_received = []
        for card_id in card_ids:
            card_data = self.card_manager.get_card_by_id(card_id)
            if card_data:
                cards_received.append(card_data)

        # Record pack opening
        self.db.record_pack_opening(interaction.user.id, pack_type, card_ids, 0)

        # Create display items
        items = []
        for card in cards_received:
            emoji = {"Legendary": "⭐", "Epic": "🟪", "Rare": "🟦", "Common": "🟩"}.get(card['rarity'], "🎴")
            items.append(f"{emoji} **{card['rarity']}** — {card['name']} *(Artist)*")

        drop = PackDrop(
            label=f"{pack_type} Pack",
            guaranteed="Rare+ Guaranteed" if pack_type == "Daily" else "Epic+ Guaranteed",
            items=items
        )

        embed = build_pack_open_embed(drop)
        view = PackOpenView(card_ids=card_ids, db_manager=self.db)
        
        await interaction.response.send_message(embed=embed, view=view)

    # Pack Creation Commands
    @app_commands.command(name="pack_create", description="Create a new creator pack")
    @app_commands.describe(name="Pack name", description="Pack description", pack_size="Number of cards (5, 10, or 15)")
    async def pack_create(self, interaction: Interaction, name: str, description: str = "", pack_size: int = 10):
        if pack_size not in [5, 10, 15]:
            await interaction.response.send_message("Pack size must be 5, 10, or 15 cards!", ephemeral=True)
            return
        
        user = self._get_user(
            interaction.user.id, 
            interaction.user.name, 
            str(interaction.user)
        )
        
        # Check if user already has a draft pack
        existing_draft = self.db.get_creator_draft_pack(interaction.user.id)
        if existing_draft:
            await interaction.response.send_message(
                f"You already have a draft pack: **{existing_draft['name']}**. "
                f"Use `/pack_cancel` to cancel it or `/pack_preview` to continue editing.",
                ephemeral=True
            )
            return
        
        # Create new pack
        pack_id = self.db.create_creator_pack(interaction.user.id, name, description, pack_size)
        
        embed = discord.Embed(
            title="📦 Pack Created",
            description=f"Pack **{name}** has been created in DRAFT status.\n\n"
                       f"**Pack Details:**\n"
                       f"• Size: {pack_size} cards\n"
                       f"• Status: DRAFT\n"
                       f"• Next: Use `/pack_add_artist` to add cards\n\n"
                       f"**Commands:**\n"
                       f"• `/pack_add_artist` - Add artist card\n"
                       f"• `/pack_preview` - Preview pack\n"
                       f"• `/pack_publish` - Publish (requires payment)\n"
                       f"• `/pack_cancel` - Cancel draft",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

    # Seamless Artist Selection
    @app_commands.command(name="pack_add_artist_smart", description="Add artist card with smart Spotify selection")
    async def pack_add_artist_smart(self, interaction: Interaction):
        """Start the smart artist selection process"""
        draft_pack = self.db.get_creator_draft_pack(interaction.user.id)
        if not draft_pack:
            await interaction.response.send_message("You don't have a draft pack. Use `/pack_create` first!", ephemeral=True)
            return
        
        # Check if pack is full
        cards = json.loads(draft_pack['cards_data'])
        if len(cards) >= draft_pack['pack_size']:
            await interaction.response.send_message("Your pack is full!", ephemeral=True)
            return
        
        # Show search modal
        modal = ArtistSearchModal(self)
        await interaction.response.send_modal(modal)

class ArtistSearchModal(ui.Modal, title="Search Spotify Artist"):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
        
    search_query = ui.TextInput(
        label="Artist Name",
        placeholder="Enter artist name to search...",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        """Handle artist search submission"""
        await interaction.response.defer()
        
        # Search for artists
        artists = spotify_integration.search_artists(self.search_query.value, limit=10)
        
        if not artists:
            await interaction.followup.send("No artists found. Try a different search term.", ephemeral=True)
            return
        
        # Create selection view
        view = ArtistSelectionView(artists, self.cog)
        
        embed = discord.Embed(
            title="🎵 Select Artist",
            description=f"Found {len(artists)} artists for **{self.search_query.value}**. Choose one to add to your pack:",
            color=discord.Color.green()
        )
        
        for i, artist in enumerate(artists[:5], 1):  # Show top 5
            followers_text = f"{artist['followers']:,}" if artist['followers'] > 0 else "N/A"
            embed.add_field(
                name=f"{i}. {artist['name']}",
                value=f"Popularity: {artist['popularity']}/100 | Followers: {followers_text}\n"
                      f"Genres: {', '.join(artist['genres'][:3]) if artist['genres'] else 'N/A'}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

class ArtistSelectionView(ui.View):
    def __init__(self, artists: List[Dict], cog):
        super().__init__(timeout=180)  # 3 minutes timeout
        self.artists = artists
        self.cog = cog
        
        # Add selection buttons for top 5 artists
        for i, artist in enumerate(artists[:5]):
            button = ui.Button(
                label=f"{i+1}. {artist['name']}",
                style=discord.ButtonStyle.primary,
                custom_id=f"select_artist_{i}"
            )
            button.callback = self.create_artist_callback(artist)
            self.add_item(button)
    
    def create_artist_callback(self, artist: Dict):
        async def callback(interaction: Interaction):
            # Generate stats and rarity automatically
            stats = spotify_integration.generate_card_stats(artist)
            rarity = spotify_integration.determine_rarity(artist)
            
            # Get draft pack
            draft_pack = self.cog.db.get_creator_draft_pack(interaction.user.id)
            if not draft_pack:
                await interaction.response.send_message("Draft pack not found!", ephemeral=True)
                return
            
            # Create card data
            card_data = {
                "name": artist['name'],
                "rarity": rarity,
                "spotify_url": artist['spotify_url'],
                "spotify_id": artist['id'],
                "genres": artist['genres'],
                "image_url": artist['image_url'],
                **stats,
                "card_type": "artist"
            }
            
            # Add to pack
            success = self.cog.db.add_card_to_pack(draft_pack['pack_id'], card_data)
            if not success:
                await interaction.response.send_message("Failed to add card to pack!", ephemeral=True)
                return
            
            # Show confirmation
            embed = discord.Embed(
                title="✅ Artist Added to Pack",
                description=f"**{artist['name']}** ({rarity}) has been added to your pack.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Generated Stats",
                value=f"💪 Impact: {stats['impact']}\n"
                      f"🎯 Skill: {stats['skill']}\n"
                      f"⏰ Longevity: {stats['longevity']}\n"
                      f"🌍 Culture: {stats['culture']}\n"
                      f"🔥 Hype: {stats['hype']}",
                inline=False
            )
            
            embed.add_field(
                name="Spotify Data",
                value=f"🎵 {artist['name']}\n"
                      f"👥 {artist['followers']:,} followers\n"
                      f"📈 {artist['popularity']}/100 popularity",
                inline=False
            )
            
            # Get updated pack info
            updated_pack = self.cog.db.get_creator_draft_pack(interaction.user.id)
            cards = json.loads(updated_pack['cards_data'])
            
            embed.add_field(
                name="Pack Progress",
                value=f"Cards: {len(cards)}/{updated_pack['pack_size']}\n"
                      f"Status: DRAFT",
                inline=False
            )
            
            embed.set_footer(text="Stats and rarity generated automatically based on Spotify data")
            
            await interaction.response.send_message(embed=embed)
            self.stop()  # Stop the view
            
        return callback

    @app_commands.command(name="pack_add_artist", description="Add an artist card to your pack")
    @app_commands.describe(
        artist_name="Artist name", 
        rarity="Card rarity", 
        spotify_url="Spotify URL (required)",
        impact="Impact stat (0-92)",
        skill="Skill stat (0-92)", 
        longevity="Longevity stat (0-92)",
        culture="Culture stat (0-92)",
        hype="Hype stat (0-92)"
    )
    async def pack_add_artist(self, interaction: Interaction, artist_name: str, rarity: str, 
                             spotify_url: str, impact: int = 50, skill: int = 50, 
                             longevity: int = 50, culture: int = 50, hype: int = 50):
        valid_rarities = ["Common", "Rare", "Epic", "Legendary"]
        if rarity not in valid_rarities:
            await interaction.response.send_message(f"Rarity must be one of: {', '.join(valid_rarities)}", ephemeral=True)
            return
        
        # Validate Spotify URL
        if not spotify_integration.validate_spotify_url(spotify_url):
            await interaction.response.send_message("Invalid Spotify URL! Must be a valid Spotify artist link.", ephemeral=True)
            return
        
        # Validate stats
        for stat_name, stat_value in [("Impact", impact), ("Skill", skill), ("Longevity", longevity), 
                                     ("Culture", culture), ("Hype", hype)]:
            if not (0 <= stat_value <= 92):
                await interaction.response.send_message(f"{stat_name} must be between 0 and 92!", ephemeral=True)
                return
        
        # Get draft pack
        draft_pack = self.db.get_creator_draft_pack(interaction.user.id)
        if not draft_pack:
            await interaction.response.send_message("You don't have a draft pack. Use `/pack_create` first!", ephemeral=True)
            return
        
        # Get Spotify info (optional - for validation/enrichment)
        spotify_info = spotify_integration.get_artist_info_from_url(spotify_url)
        
        # Create card data
        card_data = {
            "name": artist_name,
            "rarity": rarity,
            "spotify_url": spotify_url,
            "impact": impact,
            "skill": skill,
            "longevity": longevity,
            "culture": culture,
            "hype": hype,
            "card_type": "artist"
        }
        
        # Add Spotify enrichment if available
        if spotify_info:
            card_data["spotify_id"] = spotify_info.get('id')
            card_data["genres"] = spotify_info.get('genres', [])
        
        # Add to pack
        success = self.db.add_card_to_pack(draft_pack['pack_id'], card_data)
        if not success:
            await interaction.response.send_message("Pack is full or error occurred!", ephemeral=True)
            return
        
        # Get updated pack info
        updated_pack = self.db.get_creator_draft_pack(interaction.user.id)
        cards = json.loads(updated_pack['cards_data'])
        
        embed = discord.Embed(
            title="🎵 Artist Added to Pack",
            description=f"**{artist_name}** ({rarity}) has been added to your pack.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Card Stats",
            value=f"💪 Impact: {impact}\n"
                  f"🎯 Skill: {skill}\n"
                  f"⏰ Longevity: {longevity}\n"
                  f"🌍 Culture: {culture}\n"
                  f"🔥 Hype: {hype}",
            inline=False
        )
        
        embed.add_field(
            name="Spotify",
            value=f"✅ Valid URL\n🎵 {artist_name}",
            inline=False
        )
        
        embed.add_field(
            name="Pack Progress",
            value=f"Cards: {len(cards)}/{updated_pack['pack_size']}\n"
                  f"Status: DRAFT",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pack_preview", description="Preview your current draft pack")
    async def pack_preview(self, interaction: Interaction):
        draft_pack = self.db.get_creator_draft_pack(interaction.user.id)
        if not draft_pack:
            await interaction.response.send_message("You don't have a draft pack. Use `/pack_create` first!", ephemeral=True)
            return
        
        cards = json.loads(draft_pack['cards_data'])
        
        if not cards:
            await interaction.response.send_message("Your pack is empty. Use `/pack_add_artist` to add cards!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📦 Pack Preview: {draft_pack['name']}",
            description=draft_pack.get('description', 'No description'),
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Pack Info",
            value=f"Size: {len(cards)}/{draft_pack['pack_size']}\n"
                  f"Status: DRAFT\n"
                  f"Creator: {interaction.user.name}",
            inline=False
        )
        
        # Show cards
        card_list = []
        rarity_emoji = {"Common": "🟩", "Rare": "🟦", "Epic": "🟪", "Legendary": "⭐"}
        
        for i, card in enumerate(cards, 1):
            emoji = rarity_emoji.get(card['rarity'], "🎴")
            total_stats = card['impact'] + card['skill'] + card['longevity'] + card['culture'] + card['hype']
            card_list.append(f"{i}. {emoji} **{card['name']}** ({card['rarity']}) - Total: {total_stats}")
        
        if card_list:
            embed.add_field(
                name="Cards in Pack",
                value="\n".join(card_list),
                inline=False
            )
        
        # Validate pack
        validation = self.db.validate_pack_rules(draft_pack['pack_id'])
        
        if validation['valid']:
            embed.add_field(
                name="✅ Ready to Publish",
                value="Your pack meets all requirements! Use `/pack_publish` to continue.",
                inline=False
            )
        else:
            embed.add_field(
                name="❌ Issues Found",
                value="\n".join(validation['errors']),
                inline=False
            )
        
        if validation['warnings']:
            embed.add_field(
                name="⚠️ Warnings",
                value="\n".join(validation['warnings']),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pack_cancel", description="Cancel your current draft pack")
    async def pack_cancel(self, interaction: Interaction):
        draft_pack = self.db.get_creator_draft_pack(interaction.user.id)
        if not draft_pack:
            await interaction.response.send_message("You don't have a draft pack to cancel.", ephemeral=True)
            return
        
        # Delete the draft pack
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM creator_packs WHERE pack_id = ?", (draft_pack['pack_id'],))
            conn.commit()
        
        embed = discord.Embed(
            title="🗑️ Pack Cancelled",
            description=f"Draft pack **{draft_pack['name']}** has been deleted.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pack_publish", description="Publish your pack (requires Stripe payment)")
    async def pack_publish(self, interaction: Interaction):
        draft_pack = self.db.get_creator_draft_pack(interaction.user.id)
        if not draft_pack:
            await interaction.response.send_message("You don't have a draft pack. Use `/pack_create` first!", ephemeral=True)
            return
        
        # Validate pack
        validation = self.db.validate_pack_rules(draft_pack['pack_id'])
        if not validation['valid']:
            embed = discord.Embed(
                title="❌ Cannot Publish",
                description="Your pack has issues that must be fixed first:",
                color=discord.Color.red()
            )
            embed.add_field(
                name="Issues",
                value="\n".join(validation['errors']),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create Stripe checkout session
        pack_size = draft_pack['pack_size']
        result = stripe_manager.create_pack_publish_checkout(
            draft_pack['pack_id'], 
            interaction.user.id, 
            pack_size, 
            draft_pack['name']
        )
        
        if not result['success']:
            embed = discord.Embed(
                title="❌ Payment Error",
                description=f"Could not create payment session: {result['error']}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Calculate revenue split for display
        revenue_split = stripe_manager.calculate_revenue_split(result['price_cents'])
        
        embed = discord.Embed(
            title="💳 Payment Required",
            description=f"To publish your pack **{draft_pack['name']}**, complete the payment below:",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Pack Details",
            value=f"• Cards: {len(json.loads(draft_pack['cards_data']))}\n"
                  f"• Size: {pack_size} cards\n"
                  f"• Status: Ready for payment",
            inline=False
        )
        
        embed.add_field(
            name="💰 Pricing",
            value=f"• Total: ${result['price_cents']/100:.2f}\n"
                  f"• Platform (70%): ${revenue_split['platform_cents']/100:.2f}\n"
                  f"• Your Share (30%): ${revenue_split['creator_cents']/100:.2f}",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Payment Link",
            value=f"[Click here to pay]({result['checkout_url']})\n\n"
                  f"After payment, your pack will be automatically published!",
            inline=False
        )
        
        embed.set_footer(text="You'll be redirected back to Discord after payment")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Creator Dashboard Commands
    @app_commands.command(name="creator_earnings", description="View your creator earnings and balance")
    async def creator_earnings(self, interaction: Interaction):
        """Show creator earnings dashboard"""
        # Check if user is a creator
        creator_packs = self.db.get_live_packs(limit=100)
        user_packs = [p for p in creator_packs if p['creator_id'] == interaction.user.id]
        
        if not user_packs:
            await interaction.response.send_message("You don't have any published creator packs!", ephemeral=True)
            return
        
        # Get balance and earnings
        balance = self.db.get_creator_balance(interaction.user.id)
        earnings = self.db.get_creator_earnings(interaction.user.id)
        
        embed = discord.Embed(
            title="💰 Creator Earnings Dashboard",
            description=f"Earnings from your {len(user_packs)} published packs",
            color=discord.Color.gold()
        )
        
        # Balance information
        available = balance['available_balance_cents'] / 100
        pending = balance['pending_balance_cents'] / 100
        lifetime = balance['lifetime_earned_cents'] / 100
        
        embed.add_field(
            name="💳 Current Balance",
            value=f"• Available: ${available:.2f}\n"
                  f"• Pending: ${pending:.2f}\n"
                  f"• Lifetime: ${lifetime:.2f}",
            inline=False
        )
        
        # Earnings summary
        total = earnings['total_earnings']
        embed.add_field(
            name="📊 Earnings Summary",
            value=f"• Total Sales: ${total['total_gross']/100:.2f}\n"
                  f"• Your Share: ${total['total_creator']/100:.2f}\n"
                  f"• Platform Share: ${total['total_platform']/100:.2f}\n"
                  f"• Transactions: {total['transaction_count']}",
            inline=False
        )
        
        # Recent transactions
        if earnings['recent_transactions']:
            recent_text = ""
            for i, trans in enumerate(earnings['recent_transactions'][:5], 1):
                amount = trans['creator_amount_cents'] / 100
                recent_text += f"{i}. Pack sale: ${amount:.2f}\n"
            
            embed.add_field(
                name="📈 Recent Sales",
                value=recent_text,
                inline=False
            )
        
        embed.set_footer(text="Pending funds become available after 7-day refund window")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="creator_connect", description="Connect your Stripe account for automatic payouts")
    async def creator_connect(self, interaction: Interaction):
        """Start Stripe Connect onboarding"""
        # Check if user is a creator
        creator_packs = self.db.get_live_packs(limit=100)
        user_packs = [p for p in creator_packs if p['creator_id'] == interaction.user.id]
        
        if not user_packs:
            await interaction.response.send_message("You don't have any published creator packs!", ephemeral=True)
            return
        
        # Check if already connected
        existing = self.db.get_creator_stripe_account(interaction.user.id)
        if existing and existing['stripe_account_status'] == 'verified':
            await interaction.response.send_message("You already have a connected Stripe account!", ephemeral=True)
            return
        
        # TODO: Create Stripe Connect account and return onboarding link
        embed = discord.Embed(
            title="🔗 Stripe Connect Setup",
            description="Connect your Stripe account to receive automatic payouts",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📋 What you'll need:",
            value="• Bank account or debit card\n"
                  "• Business information (or use personal)\n"
                  "• 5-10 minutes to complete",
            inline=False
        )
        
        embed.add_field(
            name="💡 Benefits:",
            value="• Automatic weekly payouts\n"
                  "• No manual payment requests\n"
                  "• Professional payment processing",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Note:",
            value="Stripe Connect setup coming soon! For now, payouts will be processed manually.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="creator_payouts", description="View your payout history")
    async def creator_payouts(self, interaction: Interaction):
        """Show payout history"""
        # Check if user is a creator
        creator_packs = self.db.get_live_packs(limit=100)
        user_packs = [p for p in creator_packs if p['creator_id'] == interaction.user.id]
        
        if not user_packs:
            await interaction.response.send_message("You don't have any published creator packs!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="💸 Payout History",
            description="Your payout transactions and history",
            color=discord.Color.green()
        )
        
        # Get payout history from ledger
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT amount_gross_cents, creator_amount_cents, status, created_at
                FROM revenue_ledger 
                WHERE creator_user_id = ? AND event_type = 'PAYOUT'
                ORDER BY created_at DESC
                LIMIT 10
            """, (interaction.user.id,))
            
            payouts = cursor.fetchall()
        
        if payouts:
            payout_text = ""
            for i, payout in enumerate(payouts, 1):
                amount = payout[1] / 100  # creator_amount_cents
                status = payout[2]
                date = payout[3][:10]  # Just the date part
                payout_text += f"{i}. ${amount:.2f} - {status} ({date})\n"
            
            embed.add_field(
                name="📊 Recent Payouts",
                value=payout_text,
                inline=False
            )
        else:
            embed.add_field(
                name="💸 No Payouts Yet",
                value="You haven't received any payouts yet. Payouts are processed weekly.",
                inline=False
            )
        
        # Show next payout schedule
        import datetime
        today = datetime.date.today()
        days_until_friday = (4 - today.weekday()) % 7
        if days_until_friday == 0:
            next_payout = "Today"
        else:
            next_payout = f"In {days_until_friday} days"
        
        embed.add_field(
            name="📅 Next Payout",
            value=f"{next_payout} (Weekly payouts on Fridays)\n"
                  f"Minimum: $25.00",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def setup_hook(self):
        """Register the bot when it joins servers"""
        # Register this cog's commands
        self.bot.tree.add_command(self.creator_earnings)
        self.bot.tree.add_command(self.creator_connect)
        self.bot.tree.add_command(self.creator_payouts)
        self.bot.tree.add_command(self.browse_packs)
        self.bot.tree.add_command(self.premium_subscribe)
        self.bot.tree.add_command(self.server_info)
        self.bot.tree.add_command(self.server_analytics)

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
            cards = json.loads(pack['cards_data'])
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
    # Check if we should sync globally or to test server
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(CardGameCog(bot))
    else:
        await bot.add_cog(
            CardGameCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
