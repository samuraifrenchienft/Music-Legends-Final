# cogs/seasons.py
import discord
from discord.ext import commands
from discord import Interaction, app_commands, ui
from typing import Dict, List, Optional
import json
from season_system import SeasonManager
from database import DatabaseManager
from card_economy import CardEconomyManager

class SeasonsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.season = SeasonManager(self.db)
        self.economy = CardEconomyManager(self.db)
        
        # Initialize season system
        self.season.initialize_season_tables()
        
        # Create first season if none exists
        if not self.season.get_current_season():
            self.season.create_new_season("Season 1: Genesis", "Music Legends Origins")
        
        # Link season manager to economy
        self.economy.season_manager = self.season

    @app_commands.command(name="season", description="View current season information")
    async def season_command(self, interaction: Interaction):
        """Display current season information"""
        current_season = self.season.get_current_season()
        
        if not current_season:
            await interaction.response.send_message("❌ No active season!", ephemeral=True)
            return
        
        # Calculate time remaining
        from datetime import datetime
        end_date = datetime.fromisoformat(current_season['end_date'])
        time_remaining = end_date - datetime.now()
        days_remaining = time_remaining.days
        
        # Get player's progress
        player_progress = self.season.get_player_season_progress(interaction.user.id)
        
        embed = discord.Embed(
            title=f"🌟 {current_season['season_name']}",
            description=f"Theme: {current_season.get('theme', 'Classic')}",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="⏰ Season Duration",
            value=f"Ends in {days_remaining} days\n"
                  f"Started: {current_season['start_date'][:10]}\n"
                  f"Ends: {current_season['end_date'][:10]}",
            inline=False
        )
        
        embed.add_field(
            name="📊 Your Progress",
            value=f"Level: {player_progress['season_level']}\n"
                  f"XP: {player_progress['season_xp']}/100\n"
                  f"Rank: {player_progress['season_rank']}\n"
                  f"Cards: {player_progress['cards_collected']}\n"
                  f"Unique Artists: {player_progress['unique_artists']}",
            inline=False
        )
        
        embed.add_field(
            name="🏆 Season Stats",
            value=f"Battles Won: {player_progress['battles_won']}\n"
                  f"Trades: {player_progress['trades_completed']}\n"
                  f"Season XP: {(player_progress['season_level'] * 100) + player_progress['season_xp']}",
            inline=False
        )
        
        embed.set_footer(text="Use `/season_rewards` to see available rewards!")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="season_rewards", description="View and claim season rewards")
    async def season_rewards_command(self, interaction: Interaction):
        """View available season rewards"""
        available_rewards = self.season.get_available_rewards(interaction.user.id)
        
        if not available_rewards:
            embed = discord.Embed(
                title="🎁 Season Rewards",
                description="No available rewards. Keep progressing to unlock more!",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        embed = discord.Embed(
            title="🎁 Available Season Rewards",
            description=f"You have {len(available_rewards)} rewards to claim!",
            color=discord.Color.gold()
        )
        
        for reward in available_rewards[:10]:  # Show up to 10 rewards
            reward_data = json.loads(reward['reward_data']) if reward['reward_data'] else {}
            
            # Format reward description
            if reward['reward_type'] == 'currency':
                description = ""
                if 'gold' in reward_data:
                    description += f"🟡 {reward_data['gold']} Gold\n"
                if 'dust' in reward_data:
                    description += f"💨 {reward_data['dust']} Dust\n"
                if 'tickets' in reward_data:
                    description += f"🎫 {reward_data['tickets']} Tickets\n"
                if 'gems' in reward_data:
                    description += f"💎 {reward_data['gems']} Gems"
            elif reward['reward_type'] == 'card':
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(reward_data.get('tier', 'community'), "⚪")
                description = f"{tier_emoji} {reward_data.get('tier', 'Community').title()} Card"
            elif reward['reward_type'] == 'title':
                description = f"🏅 {reward_data.get('title', 'Title')}"
            elif reward['reward_type'] == 'badge':
                badge_tier = reward_data.get('tier', 'bronze').title()
                description = f"🎖️ {reward_data.get('badge', 'Badge').title()} ({badge_tier})"
            else:
                description = "Special Reward"
            
            # Show requirements
            requirements = []
            if reward['required_level']:
                requirements.append(f"Level {reward['required_level']}")
            if reward['required_xp']:
                requirements.append(f"{reward['required_xp']} XP")
            if reward['required_cards']:
                requirements.append(f"{reward['required_cards']} Cards")
            if reward['required_rank']:
                requirements.append(f"{reward['required_rank']} Rank")
            
            req_text = " | ".join(requirements) if requirements else "No requirements"
            
            embed.add_field(
                name=f"{reward['reward_name']}",
                value=f"{description}\n*Requirements: {req_text}*",
                inline=False
            )
        
        if len(available_rewards) > 10:
            embed.add_field(
                name="📝 More Rewards",
                value=f"... and {len(available_rewards) - 10} more rewards available!",
                inline=False
            )
        
        embed.set_footer(text="Use `/claim_reward <reward_id>` to claim a reward!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="claim_reward", description="Claim a season reward")
    async def claim_reward_command(self, interaction: Interaction, reward_id: str):
        """Claim a specific season reward"""
        result = self.season.claim_reward(interaction.user.id, reward_id)
        
        if not result['success']:
            await interaction.response.send_message(f"❌ {result['error']}", ephemeral=True)
            return
        
        # Process the reward
        reward_data = result['reward_data']
        
        embed = discord.Embed(
            title="🎉 Reward Claimed!",
            description=f"You successfully claimed: {result['reward_name']}",
            color=discord.Color.green()
        )
        
        if result['reward_type'] == 'currency':
            # Award currency to user
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                gold = reward_data.get('gold', 0)
                dust = reward_data.get('dust', 0)
                tickets = reward_data.get('tickets', 0)
                gems = reward_data.get('gems', 0)
                
                if gold > 0 or dust > 0 or tickets > 0 or gems > 0:
                    cursor.execute("""
                        INSERT OR REPLACE INTO user_inventory 
                        (user_id, gold, dust, tickets, gems)
                        VALUES (?, 
                            COALESCE((SELECT gold FROM user_inventory WHERE user_id = ?), 0) + ?,
                            COALESCE((SELECT dust FROM user_inventory WHERE user_id = ?), 0) + ?,
                            COALESCE((SELECT tickets FROM user_inventory WHERE user_id = ?), 0) + ?,
                            COALESCE((SELECT gems FROM user_inventory WHERE user_id = ?), 0) + ?
                        )
                    """, (interaction.user.id, interaction.user.id, gold, 
                          interaction.user.id, dust, interaction.user.id, tickets, 
                          interaction.user.id, gems))
                    
                    conn.commit()
            
            reward_text = ""
            if gold > 0:
                reward_text += f"🟡 {gold} Gold\n"
            if dust > 0:
                reward_text += f"💨 {dust} Dust\n"
            if tickets > 0:
                reward_text += f"🎫 {tickets} Tickets\n"
            if gems > 0:
                reward_text += f"💎 {gems} Gems"
            
            embed.add_field(
                name="💰 You Received:",
                value=reward_text,
                inline=False
            )
        
        elif result['reward_type'] == 'card':
            # Create and award a special card
            artists = self.db.get_all_artists(limit=100)
            if artists:
                artist = artists[0]  # Use first artist for simplicity
                card = self.economy.create_card(artist, reward_data.get('tier', 'gold'), 'season_reward')
                self.economy._award_card_to_user(interaction.user.id, card)
                
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card['tier'], "⚪")
                
                embed.add_field(
                    name="🎴 You Received:",
                    value=f"{tier_emoji} {card['artist_name']} ({card['tier'].title()})\n"
                          f"Serial: {card['serial_number']}",
                    inline=False
                )
        
        elif result['reward_type'] == 'title':
            # Store title (would need user_titles table)
            embed.add_field(
                name="🏅 You Received:",
                value=f"Title: {reward_data.get('title', 'Special Title')}",
                inline=False
            )
        
        elif result['reward_type'] == 'badge':
            # Store badge (would need user_badges table)
            badge_tier = reward_data.get('tier', 'bronze').title()
            embed.add_field(
                name="🎖️ You Received:",
                value=f"Badge: {reward_data.get('badge', 'Special Badge')} ({badge_tier})",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="View season leaderboard")
    async def leaderboard_command(self, interaction: Interaction, category: str = "xp"):
        """View the season leaderboard"""
        leaderboard = self.season.get_season_leaderboard(limit=20)
        
        if not leaderboard:
            await interaction.response.send_message("📊 No leaderboard data available yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Season Leaderboard",
            description=f"Top players by {category.title()}",
            color=discord.Color.gold()
        )
        
        # Sort based on category
        if category == "xp":
            leaderboard.sort(key=lambda x: (x['season_level'] * 100 + x['season_xp']), reverse=True)
        elif category == "cards":
            leaderboard.sort(key=lambda x: x['cards_collected'], reverse=True)
        elif category == "battles":
            leaderboard.sort(key=lambda x: x['battles_won'], reverse=True)
        elif category == "trades":
            leaderboard.sort(key=lambda x: x['trades_completed'], reverse=True)
        
        # Display top 10
        leaderboard_text = ""
        for i, player in enumerate(leaderboard[:10], 1):
            if category == "xp":
                value = f"Lv.{player['season_level']} ({(player['season_level'] * 100) + player['season_xp']} XP)"
            elif category == "cards":
                value = f"{player['cards_collected']} cards"
            elif category == "battles":
                value = f"{player['battles_won']} wins"
            elif category == "trades":
                value = f"{player['trades_completed']} trades"
            
            rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            leaderboard_text += f"{rank_emoji} **{player['username']}** - {value}\n"
        
        embed.add_field(
            name="📊 Top Players",
            value=leaderboard_text,
            inline=False
        )
        
        embed.add_field(
            name="🔄 Categories",
            value="Available categories: xp, cards, battles, trades\n"
                  f"Use `/leaderboard <category>` to switch",
            inline=False
        )
        
        # Show user's rank
        user_rank = next((i for i, p in enumerate(leaderboard, 1) if p['user_id'] == interaction.user.id), None)
        if user_rank:
            embed.set_footer(text=f"Your rank: #{user_rank}")
        else:
            embed.set_footer(text="Keep playing to get on the leaderboard!")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="season_stats", description="View detailed season statistics")
    async def season_stats_command(self, interaction: Interaction):
        """View detailed season statistics"""
        current_season = self.season.get_current_season()
        
        if not current_season:
            await interaction.response.send_message("❌ No active season!", ephemeral=True)
            return
        
        # Get season-wide stats
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            
            # Player statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_players,
                    AVG(season_level) as avg_level,
                    MAX(season_level) as max_level,
                    AVG(season_xp) as avg_xp,
                    SUM(cards_collected) as total_cards,
                    SUM(battles_won) as total_battles,
                    SUM(trades_completed) as total_trades
                FROM player_season_progress 
                WHERE season_id = ?
            """, (current_season['season_id'],))
            
            player_stats = cursor.fetchone()
            
            # Rank distribution
            cursor.execute("""
                SELECT season_rank, COUNT(*) as count
                FROM player_season_progress 
                WHERE season_id = ?
                GROUP BY season_rank
                ORDER BY COUNT(*) DESC
            """, (current_season['season_id'],))
            
            rank_dist = cursor.fetchall()
        
        embed = discord.Embed(
            title=f"📊 {current_season['season_name']} Statistics",
            description="Season-wide performance metrics",
            color=discord.Color.blue()
        )
        
        if player_stats[0] > 0:  # total_players
            embed.add_field(
                name="👥 Player Statistics",
                value=f"Total Players: {player_stats[0]}\n"
                      f"Average Level: {player_stats[1]:.1f}\n"
                      f"Highest Level: {player_stats[2]}\n"
                      f"Average XP: {player_stats[3]:.0f}",
                inline=False
            )
            
            embed.add_field(
                name="🎮 Activity Statistics",
                value=f"Total Cards Collected: {player_stats[4]:,}\n"
                      f"Total Battles Won: {player_stats[5]:,}\n"
                      f"Total Trades Completed: {player_stats[6]:,}\n"
                      f"Avg Cards per Player: {player_stats[4] // player_stats[0]:,}",
                inline=False
            )
            
            # Rank distribution
            rank_text = ""
            for rank, count in rank_dist:
                rank_emoji = {"Bronze": "🥉", "Silver": "🥈", "Gold": "🥇", "Platinum": "💎", "Diamond": "💠"}.get(rank, "⚪")
                percentage = (count / player_stats[0]) * 100
                rank_text += f"{rank_emoji} {rank}: {count} ({percentage:.1f}%)\n"
            
            embed.add_field(
                name="🏅 Rank Distribution",
                value=rank_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📊 No Data Yet",
                value="Season statistics will appear as players become active!",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="card_prestige", description="View card prestige information")
    async def card_prestige_command(self, interaction: Interaction, serial_number: str = None):
        """View prestige information for cards"""
        if serial_number:
            # Show specific card prestige
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, p.prestige_score, p.seasons_active, p.original_season_id
                    FROM cards c
                    LEFT JOIN card_prestige p ON c.card_id = p.card_id
                    WHERE c.serial_number = ? AND c.owner_user_id = ?
                """, (serial_number, interaction.user.id))
                
                card = cursor.fetchone()
                
                if not card:
                    await interaction.response.send_message("❌ Card not found in your collection!", ephemeral=True)
                    return
                
                prestige_score = card[13] or 0  # prestige_score
                seasons_active = card[14] or 1  # seasons_active
                
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
                
                embed = discord.Embed(
                    title=f"✨ {card[2]} Prestige",
                    description=f"Serial: {card[4]}",
                    color=discord.Color.purple()
                )
                
                embed.add_field(
                    name="📊 Prestige Metrics",
                    value=f"Prestige Score: {prestige_score}\n"
                          f"Seasons Active: {seasons_active}\n"
                          f"Tier: {tier_emoji} {card[3].title()}\n"
                          f"Quality: {card[7].title()}",
                    inline=False
                )
                
                # Calculate prestige tier
                if prestige_score >= 100:
                    prestige_tier = "Mythic"
                elif prestige_score >= 50:
                    prestige_tier = "Legendary"
                elif prestige_score >= 25:
                    prestige_tier = "Epic"
                elif prestige_score >= 10:
                    prestige_tier = "Rare"
                else:
                    prestige_tier = "Common"
                
                embed.add_field(
                    name="🏆 Prestige Tier",
                    value=f"{prestige_tier}",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed)
        else:
            # Show user's most prestigious cards
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT c.*, p.prestige_score
                    FROM cards c
                    LEFT JOIN card_prestige p ON c.card_id = p.card_id
                    WHERE c.owner_user_id = ?
                    ORDER BY COALESCE(p.prestige_score, 0) DESC, c.tier DESC
                    LIMIT 10
                """, (interaction.user.id,))
                
                cards = cursor.fetchall()
                
                if not cards:
                    await interaction.response.send_message("📊 No cards in your collection yet!", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title="✨ Your Most Prestigious Cards",
                    description="Cards ranked by prestige score",
                    color=discord.Color.purple()
                )
                
                for card in cards[:10]:
                    prestige_score = card[13] or 0
                    tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card[3], "⚪")
                    
                    embed.add_field(
                        name=f"{tier_emoji} {card[2]}",
                        value=f"Serial: {card[4]}\n"
                              f"Prestige: {prestige_score}\n"
                              f"Tier: {card[3].title()}",
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)

# Import sqlite3 for database operations
import sqlite3

async def setup(bot):
    await bot.add_cog(SeasonsCog(bot))
