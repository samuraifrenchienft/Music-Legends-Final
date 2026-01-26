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
from discord_cards import ArtistCard, build_artist_embed, PackDrop, build_pack_open_embed, PackOpenView
from battle_engine import ArtistCard as BattleCard, MatchState, PlayerState, resolve_round, apply_momentum, pick_category_option_a, STATS

class CardGameCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        from card_economy import get_economy_manager
        self.economy = get_economy_manager()
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

    # Pack Creation Commands
    @app_commands.command(name="create_pack", description="Create a new pack with artist cards")
    @app_commands.describe(pack_name="Name for your pack", artist_name="Main artist for the pack")
    async def create_pack(self, interaction: Interaction, pack_name: str, artist_name: str):
        """Create a new pack with artist cards"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create pack using database method
            pack_id = self.db.create_creator_pack(
                creator_id=interaction.user.id,
                name=pack_name,
                description=f"Artist pack featuring {artist_name}",
                pack_size=10
            )
            
            if pack_id:
                embed = discord.Embed(
                    title="✅ Pack Created!",
                    description=f"Pack '{pack_name}' has been created successfully.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Pack ID", value=pack_id, inline=False)
                embed.add_field(name="Artist", value=artist_name, inline=False)
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Failed to create pack", ephemeral=True)
                
        except Exception as e:
            print(f"❌ Error creating pack: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

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

    
    async def setup_hook(self):
        """Register the bot when it joins servers"""
        # Register this cog's commands
        self.bot.tree.add_command(self.creator_earnings)
        self.bot.tree.add_command(self.creator_connect)
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
    # Check if we should sync globally or to test server
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(CardGameCog(bot))
    else:
        await bot.add_cog(
            CardGameCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
