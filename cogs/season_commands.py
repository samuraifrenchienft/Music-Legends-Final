# cogs/season_commands.py
"""
Season System Commands
Commands for viewing season info, progress, rewards, and leaderboards
"""

import discord
from discord.ext import commands
from discord import app_commands, Interaction
import json
from datetime import datetime
from season_system import SeasonManager
from database import DatabaseManager


class SeasonCommandsCog(commands.Cog):
    """Season progression and rewards commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.season_manager = SeasonManager(self.db)
    
    @app_commands.command(name="season_info", description="View current season details")
    async def season_info(self, interaction: Interaction):
        """Display current season details, time remaining, and theme"""
        await interaction.response.defer(ephemeral=True)
        
        season = self.season_manager.get_current_season()
        
        if not season:
            await interaction.followup.send(
                "❌ No active season found! Contact an administrator.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"🎮 Season {season['season_number']}: {season['season_name']}",
            description=f"**{season['theme']}**",
            color=discord.Color.purple()
        )
        
        # Parse dates
        start_date = datetime.fromisoformat(season['start_date'])
        end_date = datetime.fromisoformat(season['end_date'])
        now = datetime.now()
        
        # Calculate time remaining
        days_remaining = (end_date - now).days
        total_days = (end_date - start_date).days
        progress_pct = int(((total_days - days_remaining) / total_days) * 100)
        
        # Time info
        embed.add_field(
            name="📅 Season Duration",
            value=f"Start: {start_date.strftime('%B %d, %Y')}\n"
                  f"End: {end_date.strftime('%B %d, %Y')}\n"
                  f"**{days_remaining} days remaining**",
            inline=True
        )
        
        # Progress bar
        filled = int(progress_pct / 10)
        bar = "█" * filled + "░" * (10 - filled)
        embed.add_field(
            name="⏳ Progress",
            value=f"{bar} {progress_pct}%",
            inline=True
        )
        
        # Exclusive content
        special_cards = json.loads(season['special_cards']) if season['special_cards'] else []
        if special_cards:
            embed.add_field(
                name="⭐ Season-Exclusive Cards",
                value="\n".join(f"• {card}" for card in special_cards[:5]),
                inline=False
            )
        
        # Quick stats
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM player_season_progress 
                WHERE season_id = ?
            """, (season['season_id'],))
            player_count = cursor.fetchone()[0]
        
        embed.add_field(
            name="👥 Active Players",
            value=f"{player_count:,} players participating",
            inline=True
        )
        
        embed.set_footer(text="Use /season_progress to view your progress")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="season_progress", description="View your season progress")
    async def season_progress(self, interaction: Interaction):
        """Show user's season level, XP, rank, and rewards"""
        await interaction.response.defer(ephemeral=True)
        
        progress = self.season_manager.get_player_season_progress(interaction.user.id)
        
        if 'error' in progress:
            await interaction.followup.send(
                f"❌ {progress['error']}",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"🎮 {interaction.user.display_name}'s Season Progress",
            color=discord.Color.gold()
        )
        
        # Level and XP
        level = progress['season_level']
        xp = progress['season_xp']
        xp_for_next = 100  # 100 XP per level
        xp_progress = int((xp / xp_for_next) * 100)
        
        xp_bar = "█" * int(xp_progress / 10) + "░" * (10 - int(xp_progress / 10))
        
        embed.add_field(
            name="⭐ Level & XP",
            value=f"**Level {level}**\n{xp_bar} {xp}/{xp_for_next} XP\n({xp_progress}% to next level)",
            inline=False
        )
        
        # Rank
        rank = progress['season_rank']
        rank_emojis = {
            'Bronze': '🥉',
            'Silver': '🥈',
            'Gold': '🥇',
            'Platinum': '💎',
            'Diamond': '💠'
        }
        rank_emoji = rank_emojis.get(rank, '🏅')
        
        embed.add_field(
            name=f"{rank_emoji} Rank",
            value=f"**{rank}**",
            inline=True
        )
        
        # Stats
        embed.add_field(
            name="📊 Season Stats",
            value=f"🎴 Cards: {progress['cards_collected']}\n"
                  f"🎨 Unique Artists: {progress['unique_artists']}\n"
                  f"⚔️ Battles Won: {progress['battles_won']}\n"
                  f"🔄 Trades: {progress['trades_completed']}",
            inline=True
        )
        
        # Rewards claimed
        claimed_rewards = json.loads(progress['rewards_claimed']) if progress['rewards_claimed'] else []
        embed.add_field(
            name="🎁 Rewards Claimed",
            value=f"**{len(claimed_rewards)}** rewards unlocked",
            inline=True
        )
        
        embed.set_footer(text="Use /season_rewards to view available rewards")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="season_rewards", description="View available season rewards")
    async def season_rewards(self, interaction: Interaction):
        """Browse available and upcoming rewards"""
        await interaction.response.defer(ephemeral=True)
        
        available_rewards = self.season_manager.get_available_rewards(interaction.user.id)
        
        if not available_rewards:
            await interaction.followup.send(
                "🎁 No rewards available right now! Keep playing to unlock more.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🎁 Available Season Rewards",
            description="Claim these rewards now!",
            color=discord.Color.green()
        )
        
        for reward in available_rewards[:10]:  # Show first 10
            reward_data = json.loads(reward['reward_data']) if reward['reward_data'] else {}
            
            # Format reward info
            if reward['reward_type'] == 'currency':
                value = f"💰 {reward_data.get('gold', 0)} Gold"
                if reward_data.get('tickets'):
                    value += f" + 🎫 {reward_data['tickets']} Tickets"
            elif reward['reward_type'] == 'card':
                tier = reward_data.get('tier', 'common').title()
                value = f"🎴 {tier} Card (Guaranteed)"
            elif reward['reward_type'] == 'title':
                value = f"🏆 Title: {reward_data.get('title', 'Unknown')}"
            elif reward['reward_type'] == 'badge':
                badge = reward_data.get('badge', 'Unknown').title()
                value = f"🎖️ {badge} Badge"
            else:
                value = "Special Reward"
            
            # Requirements
            reqs = []
            if reward['required_level']:
                reqs.append(f"Level {reward['required_level']}")
            if reward['required_rank']:
                reqs.append(f"{reward['required_rank']} Rank")
            req_text = " • ".join(reqs) if reqs else "Available now!"
            
            embed.add_field(
                name=f"{reward['reward_name']}",
                value=f"{value}\nRequires: {req_text}\nID: `{reward['reward_id']}`",
                inline=False
            )
        
        if len(available_rewards) > 10:
            embed.set_footer(text=f"Showing 10 of {len(available_rewards)} rewards. Use /claim_reward <id> to claim!")
        else:
            embed.set_footer(text="Use /claim_reward <id> to claim a reward!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="season_leaderboard", description="View top players this season")
    async def season_leaderboard(self, interaction: Interaction):
        """Top 50 players in current season"""
        await interaction.response.defer(ephemeral=False)
        
        leaderboard = self.season_manager.get_season_leaderboard(limit=25)
        
        if not leaderboard:
            await interaction.followup.send(
                "📊 Leaderboard is empty! Be the first to participate!",
                ephemeral=False
            )
            return
        
        embed = discord.Embed(
            title="🏆 Season Leaderboard - Top 25",
            description="The season's elite players",
            color=discord.Color.gold()
        )
        
        # Top 3 with special formatting
        medals = ["🥇", "🥈", "🥉"]
        for i, player in enumerate(leaderboard[:3]):
            total_xp = (player['season_level'] * 100) + player['season_xp']
            embed.add_field(
                name=f"{medals[i]} #{player['rank']} - {player['username']}",
                value=f"Level {player['season_level']} • {total_xp:,} Total XP\n"
                      f"{player['season_rank']} Rank • {player['cards_collected']} Cards",
                inline=False
            )
        
        # Rest of top 25
        if len(leaderboard) > 3:
            others = "\n".join([
                f"**#{p['rank']}** {p['username']} - Level {p['season_level']} ({p['season_rank']})"
                for p in leaderboard[3:25]
            ])
            embed.add_field(
                name="📋 Rankings 4-25",
                value=others or "No other players yet",
                inline=False
            )
        
        embed.set_footer(text="Keep playing to climb the ranks!")
        
        await interaction.followup.send(embed=embed, ephemeral=False)
    
    @app_commands.command(name="claim_reward", description="Claim a season reward")
    @app_commands.describe(reward_id="The reward ID to claim")
    async def claim_reward(self, interaction: Interaction, reward_id: str):
        """Claim a specific season reward"""
        await interaction.response.defer(ephemeral=True)
        
        result = self.season_manager.claim_reward(interaction.user.id, reward_id)
        
        if not result['success']:
            await interaction.followup.send(
                f"❌ {result['error']}",
                ephemeral=True
            )
            return
        
        # Award the rewards through economy system
        reward_type = result['reward_type']
        reward_data = result['reward_data']
        
        embed = discord.Embed(
            title="🎁 Reward Claimed!",
            description=f"**{result['reward_name']}**",
            color=discord.Color.green()
        )
        
        if reward_type == 'currency':
            # Add gold/tickets to user
            if reward_data.get('gold'):
                self.db.add_gold(interaction.user.id, reward_data['gold'])
                embed.add_field(name="💰 Gold", value=f"+{reward_data['gold']}", inline=True)
            if reward_data.get('tickets'):
                self.db.add_tickets(interaction.user.id, reward_data['tickets'])
                embed.add_field(name="🎫 Tickets", value=f"+{reward_data['tickets']}", inline=True)
        
        elif reward_type == 'card':
            embed.add_field(
                name="🎴 Card Reward",
                value=f"A {reward_data.get('tier', 'special')} card has been added to your collection!",
                inline=False
            )
        
        elif reward_type == 'title' or reward_type == 'badge':
            embed.add_field(
                name="🏆 Cosmetic Unlocked",
                value="Check your profile for your new reward!",
                inline=False
            )
        
        embed.set_footer(text="Keep progressing to unlock more rewards!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SeasonCommandsCog(bot))
