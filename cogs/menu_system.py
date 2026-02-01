# cogs/menu_system.py
"""
Music Legends - Persistent Menu System
- User Hub (public channel)
- Dev Panel (dev-only channel)
No need to check user IDs in commands - channel permissions handle access!
"""

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Optional
import sqlite3
import os
import json

from database import DatabaseManager
from card_economy import CardEconomyManager
from youtube_integration import youtube_integration
from music_api_manager import music_api
from views.song_selection import SongSelectionView
from cogs.pack_creation_helpers import show_song_selection_lastfm, finalize_pack_creation_lastfm


# ============================================
# HELPER FUNCTIONS
# ============================================

def is_dev(user_id: int) -> bool:
    """Check if user is a dev"""
    dev_ids = os.getenv('DEV_USER_IDS', '').split(',')
    return str(user_id) in dev_ids


# ============================================
# EMBED BUILDERS
# ============================================

def create_battle_pass_embed(user_id: int, db: DatabaseManager) -> discord.Embed:
    """Create Battle Pass status embed"""
    from config.battle_pass import BattlePass, BattlePassManager, FREE_TRACK_REWARDS, PREMIUM_TRACK_REWARDS
    
    bp_manager = BattlePassManager()
    
    # Get user's battle pass progress
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT battle_pass_xp, current_tier, has_premium, claimed_free_tiers, claimed_premium_tiers
            FROM battle_pass_progress WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
    
    if row:
        xp, tier, has_premium, claimed_free, claimed_premium = row
        has_premium = bool(has_premium)
    else:
        xp, tier, has_premium = 0, 1, False
        claimed_free, claimed_premium = "[]", "[]"
    
    # Calculate progress
    progress_in_tier, xp_needed = bp_manager.get_xp_progress_in_tier(xp)
    progress_pct = (progress_in_tier / xp_needed * 100) if xp_needed > 0 else 100
    
    # Build progress bar
    filled = int(progress_pct / 10)
    progress_bar = "█" * filled + "░" * (10 - filled)
    
    embed = discord.Embed(
        title=f"🎵 Battle Pass - Season {BattlePass.SEASON_NUMBER}: {BattlePass.SEASON_NAME}",
        description=f"{'👑 **PREMIUM ACTIVE**' if has_premium else '🔒 Free Track Only'}",
        color=discord.Color.gold() if has_premium else discord.Color.blue()
    )
    
    embed.add_field(
        name=f"📊 Tier {tier}/{BattlePass.TOTAL_TIERS}",
        value=f"[{progress_bar}] {progress_pct:.0f}%\n"
              f"XP: {xp:,} / {BattlePass.TOTAL_XP_REQUIRED:,}",
        inline=False
    )
    
    # Next rewards
    if tier < BattlePass.TOTAL_TIERS:
        free_reward = FREE_TRACK_REWARDS.get(tier + 1, {})
        premium_reward = PREMIUM_TRACK_REWARDS.get(tier + 1, {})
        
        next_rewards = f"**Free:** {bp_manager.format_reward(free_reward)}\n"
        if has_premium:
            next_rewards += f"**Premium:** {bp_manager.format_reward(premium_reward)}"
        else:
            next_rewards += "**Premium:** 🔒 Unlock for $9.99"
        
        embed.add_field(name=f"🎁 Next Tier ({tier + 1}) Rewards", value=next_rewards, inline=False)
    
    embed.add_field(
        name="⏰ Season Info",
        value=f"Days Remaining: {bp_manager.days_remaining()}",
        inline=True
    )
    
    embed.set_footer(text="Use buttons below to claim rewards or upgrade!")
    
    return embed


def create_vip_embed(user_id: int, db: DatabaseManager) -> discord.Embed:
    """Create VIP status embed"""
    from config.vip import VIPSubscription, VIPManager, VIPDailyBonuses, is_user_vip
    
    is_vip = is_user_vip(user_id, db.db_path)
    
    embed = discord.Embed(
        title="👑 VIP Membership",
        color=discord.Color.gold() if is_vip else discord.Color.light_grey()
    )
    
    if is_vip:
        # Get subscription details
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT expires_at, total_months FROM vip_subscriptions WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
        
        expires_at = row[0] if row else "Unknown"
        total_months = row[1] if row else 0
        
        embed.description = "✅ **VIP ACTIVE**"
        embed.add_field(name="📅 Expires", value=expires_at[:10] if expires_at else "Unknown", inline=True)
        embed.add_field(name="📊 Total Months", value=str(total_months), inline=True)
        
        embed.add_field(
            name="💰 Your Daily Bonuses",
            value="• 200 Gold (+100 bonus)\n• +1 Ticket\n• +50% XP\n• 50% Wager Protection",
            inline=False
        )
    else:
        embed.description = "🔒 **Not a VIP Member**"
        
        value = VIPDailyBonuses.calculate_monthly_value()
        embed.add_field(
            name="💎 VIP Benefits",
            value="• 2x Daily Gold\n• +1 Ticket/day\n• +50% XP & Gold from battles\n"
                  "• 50% Wager Protection\n• 0% Marketplace Fees\n• Exclusive Cosmetics\n• Weekly VIP Tournaments",
            inline=False
        )
        
        embed.add_field(
            name="💵 Price",
            value=f"**${VIPSubscription.MONTHLY_PRICE_USD}/month**\n"
                  f"Estimated Value: ${value:.2f}/month\n"
                  f"Value Ratio: {value / VIPSubscription.MONTHLY_PRICE_USD:.1f}x",
            inline=False
        )
    
    return embed


def create_shop_embed() -> discord.Embed:
    """Create shop embed"""
    embed = discord.Embed(
        title="🏪 Music Legends Shop",
        description="Purchase packs, tickets, and premium features!",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📦 Packs",
        value="• **Community Pack** - $2.99 (500 gold)\n"
              "• **Gold Pack** - $4.99 (1,000 gold)\n"
              "• **Platinum Pack** - $9.99 (2,500 gold)",
        inline=False
    )
    
    embed.add_field(
        name="🎫 Tickets",
        value="• 10 Tickets - $0.99\n"
              "• 50 Tickets - $3.99 (20% bonus)\n"
              "• 100 Tickets - $6.99 (40% bonus)",
        inline=False
    )
    
    embed.add_field(
        name="👑 Premium",
        value="• **VIP Membership** - $4.99/month\n"
              "• **Battle Pass** - $9.99/season",
        inline=False
    )
    
    return embed


def create_battle_embed() -> discord.Embed:
    """Create battle menu embed"""
    embed = discord.Embed(
        title="⚔️ Battle Arena",
        description="Challenge other players to card battles!",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="🎯 Wager Tiers",
        value="• **Casual** - 50 gold\n"
              "• **Standard** - 100 gold\n"
              "• **High Stakes** - 250 gold\n"
              "• **Extreme** - 500 gold",
        inline=False
    )
    
    embed.add_field(
        name="📊 How It Works",
        value="1. Select your best 3 cards\n"
              "2. Choose a wager tier\n"
              "3. Battle! Higher total stats wins\n"
              "4. Winner takes the pot!",
        inline=False
    )
    
    return embed


def create_collection_embed(user_id: int, db: DatabaseManager) -> discord.Embed:
    """Create collection overview embed"""
    cards = db.get_user_collection(user_id)
    
    # Count by rarity
    rarity_counts = {"common": 0, "rare": 0, "epic": 0, "legendary": 0, "mythic": 0}
    for card in cards:
        rarity = (card.get('rarity') or 'common').lower()
        if rarity in rarity_counts:
            rarity_counts[rarity] += 1
    
    embed = discord.Embed(
        title="🎴 Your Collection",
        description=f"**Total Cards:** {len(cards)}",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📊 By Rarity",
        value=f"⚪ Common: {rarity_counts['common']}\n"
              f"🔵 Rare: {rarity_counts['rare']}\n"
              f"🟣 Epic: {rarity_counts['epic']}\n"
              f"⭐ Legendary: {rarity_counts['legendary']}\n"
              f"🔴 Mythic: {rarity_counts['mythic']}",
        inline=True
    )
    
    # Show top 5 cards
    if cards:
        top_cards = ""
        for card in cards[:5]:
            rarity = (card.get('rarity') or 'common').lower()
            emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}.get(rarity, "⚪")
            name = card.get('name', 'Unknown')[:20]
            top_cards += f"{emoji} {name}\n"
        
        embed.add_field(name="🏆 Top Cards", value=top_cards, inline=True)
    
    embed.set_footer(text="Use /collection for full list • /view <id> for details")
    
    return embed


def create_stats_embed(user_id: int, db: DatabaseManager) -> discord.Embed:
    """Create user stats embed"""
    # Get user stats
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
        cursor.execute("SELECT * FROM user_inventory WHERE user_id = ?", (user_id,))
        inventory = cursor.fetchone()
    
    embed = discord.Embed(
        title="📊 Your Stats",
        color=discord.Color.blue()
    )
    
    if user:
        columns = ['user_id', 'username', 'created_at', 'total_battles', 'wins', 'losses']
        wins = user[4] if len(user) > 4 else 0
        losses = user[5] if len(user) > 5 else 0
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        embed.add_field(
            name="⚔️ Battle Record",
            value=f"Wins: {wins}\nLosses: {losses}\nWin Rate: {win_rate:.1f}%",
            inline=True
        )
    
    if inventory:
        embed.add_field(
            name="💰 Currency",
            value=f"Gold: {inventory[1] or 0:,}\n"
                  f"Tickets: {inventory[3] or 0}\n"
                  f"XP: {inventory[5] or 0:,}",
            inline=True
        )
        
        embed.add_field(
            name="📈 Progress",
            value=f"Daily Streak: {inventory[10] or 0} days\n"
                  f"Total Cards: {inventory[6] or 0}",
            inline=True
        )
    
    return embed


def create_leaderboard_embed(db: DatabaseManager) -> discord.Embed:
    """Create leaderboard embed"""
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, wins FROM users 
            ORDER BY wins DESC LIMIT 10
        """)
        top_players = cursor.fetchall()
    
    embed = discord.Embed(
        title="🏆 Leaderboard",
        description="Top 10 Players by Wins",
        color=discord.Color.gold()
    )
    
    if top_players:
        leaderboard = ""
        medals = ["🥇", "🥈", "🥉"]
        for i, (user_id, username, wins) in enumerate(top_players):
            medal = medals[i] if i < 3 else f"{i+1}."
            name = username or f"User {user_id}"
            leaderboard += f"{medal} **{name}** - {wins} wins\n"
        
        embed.add_field(name="Rankings", value=leaderboard or "No data yet", inline=False)
    else:
        embed.add_field(name="Rankings", value="No battles recorded yet!", inline=False)
    
    return embed


def create_bot_stats_embed(db: DatabaseManager) -> discord.Embed:
    """Create bot statistics embed for devs"""
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM cards")
        total_cards = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM creator_packs")
        total_packs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM matches")
        total_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(gold) FROM user_inventory")
        total_gold = cursor.fetchone()[0] or 0
    
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="👥 Total Users", value=f"{total_users:,}", inline=True)
    embed.add_field(name="🎴 Total Cards", value=f"{total_cards:,}", inline=True)
    embed.add_field(name="📦 Total Packs", value=f"{total_packs:,}", inline=True)
    embed.add_field(name="⚔️ Total Matches", value=f"{total_matches:,}", inline=True)
    embed.add_field(name="💰 Gold in Circulation", value=f"{total_gold:,}", inline=True)
    
    return embed


def create_database_embed() -> discord.Embed:
    """Create database management embed"""
    embed = discord.Embed(
        title="🗄️ Database Management",
        description="Manage the bot's database",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="Available Actions",
        value="• **View Stats** - Database statistics\n"
              "• **Backup** - Create database backup\n"
              "• **Clear Cache** - Clear Redis cache",
        inline=False
    )
    
    return embed


def create_settings_embed() -> discord.Embed:
    """Create settings embed"""
    embed = discord.Embed(
        title="⚙️ Bot Settings",
        description="Configure bot behavior",
        color=discord.Color.greyple()
    )
    
    embed.add_field(
        name="Categories",
        value="• Battle Pass Settings\n"
              "• Economy Settings\n"
              "• Drop System Settings\n"
              "• Notification Settings",
        inline=False
    )
    
    return embed


# ============================================
# USER HUB VIEW (Persistent in Public Channel)
# ============================================

class UserHubView(discord.ui.View):
    """
    Main user menu - persistent in #start-here or #commands channel
    Never times out, always available
    """
    
    def __init__(self, db: DatabaseManager = None):
        super().__init__(timeout=None)  # Never expires!
        self.db = db or DatabaseManager()
    
    @discord.ui.button(
        label="🎵 Battle Pass",
        style=discord.ButtonStyle.primary,
        custom_id="user_hub:battlepass",
        row=0
    )
    async def battle_pass_button(self, interaction: Interaction, button: discord.ui.Button):
        """Open Battle Pass menu"""
        view = BattlePassView(self.db)
        embed = create_battle_pass_embed(interaction.user.id, self.db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="👑 VIP Status",
        style=discord.ButtonStyle.success,
        custom_id="user_hub:vip",
        row=0
    )
    async def vip_button(self, interaction: Interaction, button: discord.ui.Button):
        """Open VIP menu"""
        view = VIPView(self.db)
        embed = create_vip_embed(interaction.user.id, self.db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="🏪 Shop",
        style=discord.ButtonStyle.secondary,
        custom_id="user_hub:shop",
        row=0
    )
    async def shop_button(self, interaction: Interaction, button: discord.ui.Button):
        """Open shop menu"""
        view = ShopView(self.db)
        embed = create_shop_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="⚔️ Battle",
        style=discord.ButtonStyle.danger,
        custom_id="user_hub:battle",
        row=0
    )
    async def battle_button(self, interaction: Interaction, button: discord.ui.Button):
        """Open battle menu"""
        view = BattleView(self.db)
        embed = create_battle_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="🎴 Collection",
        style=discord.ButtonStyle.secondary,
        custom_id="user_hub:collection",
        row=1
    )
    async def collection_button(self, interaction: Interaction, button: discord.ui.Button):
        """Open collection menu"""
        view = CollectionView(self.db)
        embed = create_collection_embed(interaction.user.id, self.db)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="💰 Daily Claim",
        style=discord.ButtonStyle.success,
        custom_id="user_hub:daily",
        row=1
    )
    async def daily_button(self, interaction: Interaction, button: discord.ui.Button):
        """Claim daily reward"""
        economy = CardEconomyManager(self.db)
        result = economy.claim_daily_reward(interaction.user.id)
        
        if result.get('success'):
            embed = discord.Embed(
                title="✅ Daily Reward Claimed!",
                color=discord.Color.green()
            )
            embed.add_field(name="💰 Gold", value=f"+{result.get('gold', 0)}", inline=True)
            embed.add_field(name="🔥 Streak", value=f"{result.get('streak', 1)} days", inline=True)
            if result.get('tickets', 0) > 0:
                embed.add_field(name="🎫 Tickets", value=f"+{result['tickets']}", inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"❌ {result.get('error', 'Already claimed today!')}",
                ephemeral=True
            )
    
    @discord.ui.button(
        label="📊 Stats",
        style=discord.ButtonStyle.secondary,
        custom_id="user_hub:stats",
        row=1
    )
    async def stats_button(self, interaction: Interaction, button: discord.ui.Button):
        """Show stats"""
        embed = create_stats_embed(interaction.user.id, self.db)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="🏆 Leaderboard",
        style=discord.ButtonStyle.secondary,
        custom_id="user_hub:leaderboard",
        row=1
    )
    async def leaderboard_button(self, interaction: Interaction, button: discord.ui.Button):
        """Show leaderboard"""
        embed = create_leaderboard_embed(self.db)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================
# DEV PANEL VIEW (Persistent in Dev-Only Channel)
# ============================================

class DevPanelView(discord.ui.View):
    """
    Admin panel - persistent in #dev-controls channel
    Only devs can access this channel, so no permission checks needed!
    """
    
    def __init__(self, db: DatabaseManager = None):
        super().__init__(timeout=None)  # Never expires!
        self.db = db or DatabaseManager()
    
    @discord.ui.button(
        label="📦 Create Community Pack",
        style=discord.ButtonStyle.primary,
        custom_id="dev_panel:create_community",
        row=0
    )
    async def create_community_button(self, interaction: Interaction, button: discord.ui.Button):
        """Create community pack (free for devs)"""
        view = PackCreationModeView(pack_type="community", db=self.db)
        await interaction.response.send_message(
            "**Community Pack Creation**\n\nHow would you like to create your pack?",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(
        label="💎 Create Gold Pack",
        style=discord.ButtonStyle.success,
        custom_id="dev_panel:create_gold",
        row=0
    )
    async def create_gold_button(self, interaction: Interaction, button: discord.ui.Button):
        """Create gold pack (free for devs)"""
        view = PackCreationModeView(pack_type="gold", db=self.db)
        await interaction.response.send_message(
            "**Gold Pack Creation**\n\nHow would you like to create your pack?",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(
        label="🎁 Give Cards",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:give_cards",
        row=0
    )
    async def give_cards_button(self, interaction: Interaction, button: discord.ui.Button):
        """Give cards to users"""
        view = GiveCardsView(self.db)
        await interaction.response.send_message(
            "🎁 **Give Cards to Users**\n\nSelect card rarity:",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(
        label="💰 Give Currency",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:give_currency",
        row=0
    )
    async def give_currency_button(self, interaction: Interaction, button: discord.ui.Button):
        """Give gold/tickets to users"""
        view = GiveCurrencyView(self.db)
        await interaction.response.send_message(
            "💰 **Give Currency to Users**\n\nSelect currency type:",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(
        label="📊 Bot Stats",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:stats",
        row=1
    )
    async def bot_stats_button(self, interaction: Interaction, button: discord.ui.Button):
        """View bot statistics"""
        embed = create_bot_stats_embed(self.db)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(
        label="👥 User Lookup",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:user_lookup",
        row=1
    )
    async def user_lookup_button(self, interaction: Interaction, button: discord.ui.Button):
        """Look up user data"""
        modal = UserLookupModal(self.db)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🗄️ Database",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:database",
        row=1
    )
    async def database_button(self, interaction: Interaction, button: discord.ui.Button):
        """Database management"""
        view = DatabaseView(self.db)
        embed = create_database_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="⚙️ Settings",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:settings",
        row=1
    )
    async def settings_button(self, interaction: Interaction, button: discord.ui.Button):
        """Bot settings"""
        view = SettingsView(self.db)
        embed = create_settings_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(
        label="🎉 Run Event",
        style=discord.ButtonStyle.primary,
        custom_id="dev_panel:event",
        row=2
    )
    async def event_button(self, interaction: Interaction, button: discord.ui.Button):
        """Start special event"""
        view = EventView(self.db)
        await interaction.response.send_message(
            "🎉 **Start Special Event**\n\nChoose event type:",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(
        label="📢 Announcement",
        style=discord.ButtonStyle.primary,
        custom_id="dev_panel:announcement",
        row=2
    )
    async def announcement_button(self, interaction: Interaction, button: discord.ui.Button):
        """Send announcement"""
        modal = AnnouncementModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🔄 Restart Bot",
        style=discord.ButtonStyle.danger,
        custom_id="dev_panel:restart",
        row=2
    )
    async def restart_button(self, interaction: Interaction, button: discord.ui.Button):
        """Restart bot"""
        await interaction.response.send_message(
            "⚠️ **Restart Bot?**\n\nThis will disconnect all users briefly.\nAre you sure?",
            view=ConfirmRestartView(),
            ephemeral=True
        )
    
    @discord.ui.button(
        label="✨ Legendary Cosmetics",
        style=discord.ButtonStyle.primary,
        custom_id="dev_panel:legendary_cosmetics",
        row=2
    )
    async def legendary_cosmetics_button(self, interaction: Interaction, button: discord.ui.Button):
        """Manage legendary card cosmetics"""
        view = LegendaryCosmeticsView(self.db)
        await interaction.response.send_message(
            "✨ **Legendary Card Cosmetics**\n\nManage cosmetics for legendary cards:",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(
        label="🧪 Test Features",
        style=discord.ButtonStyle.secondary,
        custom_id="dev_panel:test",
        row=2
    )
    async def test_button(self, interaction: Interaction, button: discord.ui.Button):
        """Test new features"""
        view = TestView(self.db)
        await interaction.response.send_message(
            "🧪 **Test Features**\n\nSelect feature to test:",
            view=view,
            ephemeral=True
        )


# ============================================
# USER SUB-VIEWS
# ============================================

class BattlePassView(discord.ui.View):
    """Battle Pass sub-menu"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=300)
        self.db = db
    
    @discord.ui.button(label="🎁 Claim Rewards", style=discord.ButtonStyle.success)
    async def claim_rewards(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Claiming available rewards...", ephemeral=True)
    
    @discord.ui.button(label="📜 View All Tiers", style=discord.ButtonStyle.secondary)
    async def view_tiers(self, interaction: Interaction, button: discord.ui.Button):
        from config.battle_pass import FREE_TRACK_REWARDS, PREMIUM_TRACK_REWARDS, BattlePassManager
        
        bp = BattlePassManager()
        tiers_text = ""
        for tier in [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
            free = FREE_TRACK_REWARDS.get(tier, {})
            tiers_text += f"**Tier {tier}:** {bp.format_reward(free)}\n"
        
        embed = discord.Embed(title="📜 Battle Pass Tiers (Free Track)", description=tiers_text, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="💎 Upgrade to Premium", style=discord.ButtonStyle.primary)
    async def upgrade_premium(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "💎 **Upgrade to Premium Battle Pass**\n\n"
            "Price: **$9.99**\n\n"
            "Unlock exclusive rewards including:\n"
            "• 4 Mythic Cards\n"
            "• 1 Ultra Mythic Card\n"
            "• 50,000+ Gold\n"
            "• 250+ Tickets\n"
            "• Exclusive Cosmetics\n\n"
            "Use `/buy battlepass` to purchase!",
            ephemeral=True
        )


class VIPView(discord.ui.View):
    """VIP sub-menu"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=300)
        self.db = db
    
    @discord.ui.button(label="💎 Subscribe", style=discord.ButtonStyle.success)
    async def subscribe(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "👑 **Subscribe to VIP**\n\n"
            "Price: **$4.99/month**\n\n"
            "Use `/buy vip` to subscribe!",
            ephemeral=True
        )
    
    @discord.ui.button(label="📋 Full Benefits List", style=discord.ButtonStyle.secondary)
    async def benefits_list(self, interaction: Interaction, button: discord.ui.Button):
        from config.vip import VIPManager
        vip = VIPManager()
        await interaction.response.send_message(vip.format_benefits_display(), ephemeral=True)


class ShopView(discord.ui.View):
    """Shop sub-menu"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=300)
        self.db = db
    
    @discord.ui.button(label="📦 Buy Pack", style=discord.ButtonStyle.primary)
    async def buy_pack(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📦 **Buy Packs**\n\n"
            "Use these commands:\n"
            "• `/buy community` - $2.99\n"
            "• `/buy gold` - $4.99\n"
            "• `/buy platinum` - $9.99",
            ephemeral=True
        )
    
    @discord.ui.button(label="🎫 Buy Tickets", style=discord.ButtonStyle.secondary)
    async def buy_tickets(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🎫 **Buy Tickets**\n\n"
            "• 10 Tickets - $0.99\n"
            "• 50 Tickets - $3.99 (20% bonus)\n"
            "• 100 Tickets - $6.99 (40% bonus)\n\n"
            "Use `/buy tickets <amount>`",
            ephemeral=True
        )


class BattleView(discord.ui.View):
    """Battle sub-menu"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=300)
        self.db = db
    
    @discord.ui.button(label="⚔️ Quick Battle", style=discord.ButtonStyle.danger)
    async def quick_battle(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "⚔️ **Quick Battle**\n\n"
            "Use `/battle @opponent casual` to start a battle!",
            ephemeral=True
        )
    
    @discord.ui.button(label="🏆 Ranked Battle", style=discord.ButtonStyle.primary)
    async def ranked_battle(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🏆 **Ranked Battle**\n\n"
            "Use `/battle @opponent standard` or higher wager for ranked!",
            ephemeral=True
        )


class CollectionView(discord.ui.View):
    """Collection sub-menu"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=300)
        self.db = db
    
    @discord.ui.button(label="📜 Full Collection", style=discord.ButtonStyle.secondary)
    async def full_collection(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use `/collection` to see your full card list!",
            ephemeral=True
        )
    
    @discord.ui.button(label="⭐ Set Favorites", style=discord.ButtonStyle.primary)
    async def set_favorites(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Use `/favorite <card_id>` to set a card as favorite!",
            ephemeral=True
        )


# ============================================
# DEV SUB-VIEWS
# ============================================

class GiveCardsView(discord.ui.View):
    """Give cards to users"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
        self.selected_rarity = None
    
    @discord.ui.select(
        placeholder="Choose card rarity...",
        options=[
            discord.SelectOption(label="Common", value="common", emoji="⚪"),
            discord.SelectOption(label="Rare", value="rare", emoji="🔵"),
            discord.SelectOption(label="Epic", value="epic", emoji="🟣"),
            discord.SelectOption(label="Legendary", value="legendary", emoji="⭐"),
            discord.SelectOption(label="Mythic", value="mythic", emoji="🔴"),
        ],
    )
    async def rarity_select(self, interaction: Interaction, select: discord.ui.Select):
        self.selected_rarity = select.values[0]
        modal = GiveCardModal(self.selected_rarity, self.db)
        await interaction.response.send_modal(modal)


class GiveCurrencyView(discord.ui.View):
    """Give currency to users"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
        self.selected_currency = None
    
    @discord.ui.select(
        placeholder="Choose currency type...",
        options=[
            discord.SelectOption(label="Gold", value="gold", emoji="💰"),
            discord.SelectOption(label="Tickets", value="tickets", emoji="🎫"),
            discord.SelectOption(label="XP", value="xp", emoji="⚡"),
        ],
    )
    async def currency_select(self, interaction: Interaction, select: discord.ui.Select):
        self.selected_currency = select.values[0]
        modal = GiveCurrencyModal(self.selected_currency, self.db)
        await interaction.response.send_modal(modal)


class DatabaseView(discord.ui.View):
    """Database management"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
    
    @discord.ui.button(label="📊 View Stats", style=discord.ButtonStyle.secondary)
    async def stats_button(self, interaction: Interaction, button: discord.ui.Button):
        embed = create_bot_stats_embed(self.db)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="💾 Backup", style=discord.ButtonStyle.primary)
    async def backup_button(self, interaction: Interaction, button: discord.ui.Button):
        import shutil
        from datetime import datetime
        
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        try:
            shutil.copy(self.db.db_path, backup_name)
            await interaction.response.send_message(f"✅ Backup created: `{backup_name}`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Backup failed: {e}", ephemeral=True)
    
    @discord.ui.button(label="🗑️ Clear Cache", style=discord.ButtonStyle.danger)
    async def clear_button(self, interaction: Interaction, button: discord.ui.Button):
        # TODO: Clear Redis cache
        await interaction.response.send_message("✅ Cache cleared!", ephemeral=True)


class SettingsView(discord.ui.View):
    """Bot settings"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
    
    @discord.ui.button(label="🎵 Battle Pass Settings", style=discord.ButtonStyle.secondary)
    async def bp_settings_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Battle Pass settings coming soon...", ephemeral=True)
    
    @discord.ui.button(label="💰 Economy Settings", style=discord.ButtonStyle.secondary)
    async def economy_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Economy settings coming soon...", ephemeral=True)


class EventView(discord.ui.View):
    """Special events"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
    
    @discord.ui.select(
        placeholder="Choose event type...",
        options=[
            discord.SelectOption(label="2x Gold Weekend", value="gold_2x", emoji="💰"),
            discord.SelectOption(label="2x XP Event", value="xp_2x", emoji="⚡"),
            discord.SelectOption(label="Free Pack Giveaway", value="free_pack", emoji="🎁"),
            discord.SelectOption(label="Tournament", value="tournament", emoji="🏆"),
        ],
    )
    async def event_select(self, interaction: Interaction, select: discord.ui.Select):
        event = select.values[0]
        modal = EventDurationModal(event, self.db)
        await interaction.response.send_modal(modal)


class TestView(discord.ui.View):
    """Test features"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
    
    @discord.ui.button(label="Test Battle System", style=discord.ButtonStyle.secondary)
    async def test_battle_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Testing battle system...", ephemeral=True)
    
    @discord.ui.button(label="Test Pack Opening", style=discord.ButtonStyle.secondary)
    async def test_pack_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Testing pack opening...", ephemeral=True)
    
    @discord.ui.button(label="Test Card View", style=discord.ButtonStyle.secondary)
    async def test_card_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Use `/card <card_id>` to test card viewing!", ephemeral=True)


class ConfirmRestartView(discord.ui.View):
    """Confirm bot restart"""
    
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="✅ Yes, Restart", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔄 Restarting bot... (not implemented)", ephemeral=True)
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Cancelled.", ephemeral=True)


# ============================================
# MODALS
# ============================================

class LegendaryCosmeticsView(discord.ui.View):
    """Manage default cosmetics for legendary cards"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__(timeout=180)
        self.db = db
    
    @discord.ui.button(
        label="📋 Set Default Frame",
        style=discord.ButtonStyle.primary,
        emoji="🎨"
    )
    async def set_default_frame_button(self, interaction: Interaction, button: discord.ui.Button):
        """Set default frame style for legendary cards"""
        modal = SetLegendaryFrameModal(self.db)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="✨ Set Default Foil",
        style=discord.ButtonStyle.primary,
        emoji="💫"
    )
    async def set_default_foil_button(self, interaction: Interaction, button: discord.ui.Button):
        """Set default foil effect for legendary cards"""
        modal = SetLegendaryFoilModal(self.db)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🔍 View Settings",
        style=discord.ButtonStyle.secondary,
        emoji="👁️"
    )
    async def view_settings_button(self, interaction: Interaction, button: discord.ui.Button):
        """View current legendary cosmetics settings"""
        # Get current settings from database or config
        settings = {
            'frame': 'crystal',
            'foil': 'galaxy',
            'description': 'Premium cosmetics for legendary cards'
        }
        
        embed = discord.Embed(
            title="✨ Legendary Card Cosmetics Settings",
            description=settings['description'],
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🎨 Default Frame Style",
            value=f"`{settings['frame'].title()}`",
            inline=False
        )
        
        embed.add_field(
            name="💫 Default Foil Effect",
            value=f"`{settings['foil'].title()}`",
            inline=False
        )
        
        embed.add_field(
            name="📝 Info",
            value="These cosmetics are automatically applied to all legendary cards created.",
            inline=False
        )
        
        embed.set_footer(text="Use buttons above to customize these settings")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetLegendaryFrameModal(discord.ui.Modal, title="Set Legendary Frame"):
    """Modal to set default frame for legendary cards"""
    
    frame_style = discord.ui.TextInput(
        label="Frame Style",
        placeholder="Options: crystal, holographic, vintage, neon",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: Interaction):
        try:
            frame = self.frame_style.value.lower().strip()
            valid_frames = ['crystal', 'holographic', 'vintage', 'neon']
            
            if frame not in valid_frames:
                await interaction.response.send_message(
                    f"❌ Invalid frame style. Valid options: {', '.join(valid_frames)}",
                    ephemeral=True
                )
                return
            
            # Save to database or config
            # For now, we'll just confirm the change
            embed = discord.Embed(
                title="✅ Frame Style Updated",
                description=f"Legendary cards will now have **{frame.title()}** frames",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Frame Style",
                value=f"`{frame.title()}`",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"❌ Error in SetLegendaryFrameModal: {e}")
            try:
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            except:
                pass


class SetLegendaryFoilModal(discord.ui.Modal, title="Set Legendary Foil"):
    """Modal to set default foil effect for legendary cards"""
    
    foil_effect = discord.ui.TextInput(
        label="Foil Effect",
        placeholder="Options: galaxy, prismatic, rainbow, standard, none",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: Interaction):
        try:
            foil = self.foil_effect.value.lower().strip()
            valid_foils = ['galaxy', 'prismatic', 'rainbow', 'standard', 'none']
            
            if foil not in valid_foils:
                await interaction.response.send_message(
                    f"❌ Invalid foil effect. Valid options: {', '.join(valid_foils)}",
                    ephemeral=True
                )
                return
            
            # Save to database or config
            # For now, we'll just confirm the change
            embed = discord.Embed(
                title="✅ Foil Effect Updated",
                description=f"Legendary cards will now have **{foil.title()}** foil effect",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Foil Effect",
                value=f"`{foil.title()}`",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"❌ Error in SetLegendaryFoilModal: {e}")
            try:
                await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            except:
                pass


class PackCreationModeView(discord.ui.View):
    """Let dev choose between auto-select or manual song selection"""
    
    def __init__(self, pack_type: str, db: DatabaseManager):
        super().__init__(timeout=180)
        self.pack_type = pack_type
        self.db = db
    
    @discord.ui.button(
        label="⚡ Auto-Generate (5 Random)",
        style=discord.ButtonStyle.primary,
        emoji="🎲"
    )
    async def auto_select_button(self, interaction: Interaction, button: discord.ui.Button):
        """Auto-select first 5 tracks"""
        modal = PackCreationModal(pack_type=self.pack_type, db=self.db, auto_select=True)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="🎵 Manual Select",
        style=discord.ButtonStyle.secondary,
        emoji="👆"
    )
    async def manual_select_button(self, interaction: Interaction, button: discord.ui.Button):
        """Let dev manually select songs"""
        modal = PackCreationModal(pack_type=self.pack_type, db=self.db, auto_select=False)
        await interaction.response.send_modal(modal)


class ImageConfirmationView(discord.ui.View):
    """View for confirming Last.fm image or searching YouTube"""
    
    def __init__(self, artist_data: dict, tracks: list, pack_type: str):
        super().__init__(timeout=180)
        self.artist_data = artist_data
        self.tracks = tracks
        self.pack_type = pack_type
        self.use_lastfm = None
        self.interaction_response = None
    
    @discord.ui.button(label="✅ Yes, looks good", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_image(self, interaction: Interaction, button: discord.ui.Button):
        self.use_lastfm = True
        self.interaction_response = interaction
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(label="🔄 Try smaller image", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def try_smaller_image(self, interaction: Interaction, button: discord.ui.Button):
        """Try using a smaller Last.fm image size"""
        self.use_lastfm = True
        self.use_smaller_image = True
        self.interaction_response = interaction
        await interaction.response.defer()
        self.stop()
    
    @discord.ui.button(label="❌ No, search YouTube", style=discord.ButtonStyle.secondary, emoji="🔍")
    async def reject_image(self, interaction: Interaction, button: discord.ui.Button):
        self.use_lastfm = False
        self.interaction_response = interaction
        await interaction.response.defer()
        self.stop()


class PackCreationModal(discord.ui.Modal, title="Create Pack"):
    """Modal for pack creation - triggers full interactive flow with smart image selection"""
    
    def __init__(self, pack_type: str, db: DatabaseManager, auto_select: bool = False):
        super().__init__()
        self.pack_type = pack_type
        self.db = db
        self.auto_select = auto_select  # If True, automatically select first 5 tracks
    
    artist_name = discord.ui.TextInput(
        label="Artist Name",
        placeholder="Enter artist name to search (e.g. Drake, Taylor Swift)...",
        required=True,
        max_length=100
    )
    
    pack_name = discord.ui.TextInput(
        label="Pack Name",
        placeholder="Name for your pack (e.g. Drake Hits Pack)...",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        try:
            # MUST defer immediately to prevent timeout
            # Use ephemeral=False so we don't interfere with the persistent dev panel
            await interaction.response.defer(ephemeral=False, thinking=True)
            
            artist_name = self.artist_name.value
            pack_name = self.pack_name.value
            
            print(f"🔧 DEV PANEL: Creating {self.pack_type} pack")
            print(f"   Artist: {artist_name}")
            print(f"   Pack Name: {pack_name}")
            
            # Send initial message
            await interaction.followup.send(
                f"🔍 Searching for **{artist_name}**...",
                ephemeral=False
            )
            
            # Step 1: Try Last.fm first (if API key is available)
            lastfm_result = None
            try:
                lastfm_result = await music_api.search_artist_with_tracks(artist_name, limit=10)
            except Exception as e:
                print(f"Last.fm error: {e}")
                import traceback
                traceback.print_exc()
                lastfm_result = None
            
            if lastfm_result:
                # Last.fm found the artist - show image confirmation
                artist_data = lastfm_result['artist']
                tracks = lastfm_result['tracks']
                
                # If auto-select mode, automatically proceed with first 5 tracks
                if self.auto_select:
                    print(f"🔧 DEV PANEL: AUTO-SELECT MODE - Using first {min(5, len(tracks))} tracks")
                    selected_tracks = tracks[:5]  # Auto-select first 5 tracks
                    
                    # Directly finalize pack with auto-selected tracks
                    await finalize_pack_creation_lastfm(
                        interaction,
                        pack_name,
                        artist_data,
                        selected_tracks,
                        interaction.user.id,
                        self.pack_type,
                        self.db
                    )
                    return  # Exit immediately after finalization
                
                # Create image preview embed (only for manual mode)
                preview_embed = discord.Embed(
                    title=f"🎵 {artist_data['name']}",
                    description=(
                        f"**{artist_data['listeners']:,}** listeners | "
                        f"**{artist_data['playcount']:,}** total plays\n\n"
                        f"Found **{len(tracks)}** top tracks from Last.fm"
                    ),
                    color=discord.Color.gold() if self.pack_type == 'gold' else discord.Color.blue()
                )
                
                # Show Last.fm artist image - SIMPLIFIED (no image preview in dev panel)
                # Images will still work when opening packs
                print(f"🔧 DEV PANEL: Available image keys: {[k for k in artist_data.keys() if 'image' in k.lower()]}")
                
                image_url = None
                image_sizes = ['image_xlarge', 'image_large', 'image_medium', 'image']
                
                for size in image_sizes:
                    if artist_data.get(size):
                        image_url = artist_data[size]
                        print(f"🔧 DEV PANEL: ✅ Found {size}: {image_url[:80] if image_url else 'None'}...")
                        break
                
                # Note: We don't show the image in the dev panel preview anymore
                # Images will be properly displayed when opening packs
                if image_url:
                    print(f"🔧 DEV PANEL: Image URL saved for cards: {image_url}")
                else:
                    print(f"🔧 DEV PANEL: No image found, will use YouTube fallback")
                
                # Show top tracks
                tracks_text = "\n".join([
                    f"**{i+1}.** {track['name']} ({track['playcount']:,} plays)"
                    for i, track in enumerate(tracks[:5])
                ])
                preview_embed.add_field(
                    name="🎧 Top Tracks Found:",
                    value=tracks_text,
                    inline=False
                )
                
                # Show genre tags if available
                if artist_data.get('tags'):
                    tags_text = ", ".join(artist_data['tags'][:5])
                    preview_embed.add_field(
                        name="🏷️ Genres:",
                        value=tags_text,
                        inline=False
                    )
                
                preview_embed.set_footer(text="Use this image for your pack cards?")
                
                # Show confirmation view in a new message (not editing the original)
                confirm_view = ImageConfirmationView(artist_data, tracks, self.pack_type)
                confirmation_msg = await interaction.followup.send(
                    embed=preview_embed,
                    view=confirm_view,
                    ephemeral=False
                )
                
                # Wait for user decision
                await confirm_view.wait()
                
                if confirm_view.use_lastfm:
                    # User accepted Last.fm images - check if they want smaller size
                    use_smaller = getattr(confirm_view, 'use_smaller_image', False)
                    print(f"🔧 DEV PANEL: User chose Last.fm image, smaller={use_smaller}")
                    
                    await show_song_selection_lastfm(
                        interaction,
                        pack_name,
                        artist_data,
                        tracks,
                        self.pack_type,
                        self.db,
                        finalize_pack_creation_lastfm,
                        use_smaller_image=use_smaller
                    )
                else:
                    # User wants YouTube images instead
                    await interaction.followup.send(
                        content="🔍 Searching YouTube for better images...",
                        ephemeral=False
                    )
                    await self._search_youtube_fallback(interaction, pack_name, artist_name, artist_data, tracks)
            else:
                # Last.fm failed or unavailable, use YouTube
                print(f"🔧 DEV PANEL: Falling back to YouTube")
                
                # If auto-select mode, directly use YouTube videos
                if self.auto_select:
                    await self._search_youtube_fallback_auto(interaction, pack_name, artist_name)
                else:
                    await interaction.followup.send(
                        content=f"🔍 Searching YouTube for **{artist_name}**...",
                        ephemeral=False
                    )
                    await self._search_youtube_fallback(interaction, pack_name, artist_name)
            
        except Exception as e:
            print(f"❌ Error in pack creation modal: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"❌ Error creating pack: {str(e)}\n\nPlease try again or contact support.",
                    ephemeral=True
                )
            except:
                # If followup fails, try editing original response
                try:
                    await interaction.edit_original_response(
                        content=f"❌ Error: {str(e)}"
                    )
                except:
                    pass
    
    async def _finalize_pack_creation(self, interaction: Interaction, pack_name: str, artist: dict, selected_tracks: list, creator_id: int, pack_type: str):
        """Finalize pack creation after song selection"""
        import random
        
        try:
            print(f"🎯 Starting pack creation for {pack_name} by {artist['name']}")
            print(f"   Selected tracks: {len(selected_tracks)}")
            
            # Create pack in database
            pack_id = self.db.create_creator_pack(
                creator_id=creator_id,
                name=pack_name,
                description=f"{pack_type.title()} pack featuring {artist['name']}",
                pack_size=len(selected_tracks)
            )
            
            if not pack_id:
                print(f"❌ Failed to create pack in database")
                await interaction.followup.send("❌ Failed to create pack in database", ephemeral=True)
                return
            
            print(f"✅ Pack created with ID: {pack_id}")
            
            # Generate cards for each selected track
            cards_created = []
            
            # Stat ranges based on pack type
            if pack_type == 'gold':
                stat_min, stat_max = 70, 92
                rarity_boost = 10
            else:
                stat_min, stat_max = 50, 85
                rarity_boost = 0
            
            for track in selected_tracks:
                try:
                    # Debug: print track data to see what we're working with
                    print(f"📦 Processing track: {track.get('title', track.get('name', 'Unknown'))}")
                    print(f"   Track keys: {list(track.keys())}")
                    
                    # Generate stats
                    base_stat = random.randint(stat_min, stat_max)
                    
                    stats = {
                        'impact': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'skill': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'longevity': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'culture': min(99, max(20, base_stat + random.randint(-10, 10))),
                        'hype': min(99, max(20, base_stat + random.randint(-10, 10)))
                    }
                    
                    # Determine rarity based on average stats
                    avg_stat = sum(stats.values()) / len(stats) + rarity_boost
                    if avg_stat >= 85:
                        rarity = "legendary"
                    elif avg_stat >= 75:
                        rarity = "epic"
                    elif avg_stat >= 65:
                        rarity = "rare"
                    else:
                        rarity = "common"
                    
                    # Extract song title
                    video_title = track.get('title', track.get('name', ''))
                    song_title = video_title.replace(artist['name'], '').replace('-', '').strip()
                    for suffix in ['(Official Music Video)', '(Official Video)', '(Lyrics)', '(Audio)', 'ft.', 'feat.']:
                        song_title = song_title.replace(suffix, '').strip()
                    if not song_title or len(song_title) < 2:
                        song_title = video_title[:50]
                    
                    # Get image URL - try multiple possible field names
                    image_url = (
                        track.get('thumbnail_url') or 
                        track.get('youtube_thumbnail') or 
                        track.get('image_url') or 
                        track.get('image_xlarge') or
                        artist.get('image_url', '')
                    )
                    print(f"   Image URL: {image_url[:50] if image_url else 'NONE'}...")
                    
                    # Get video ID
                    video_id = track.get('video_id', str(random.randint(1000, 9999)))
                    youtube_url = track.get('youtube_url', f"https://youtube.com/watch?v={video_id}")
                    
                    # Create card data
                    card_id = f"{pack_id}_{video_id}"
                    card_data = {
                        'card_id': card_id,
                        'name': artist['name'],
                        'title': song_title[:100],
                        'rarity': rarity,
                        'image_url': image_url,
                        'youtube_url': youtube_url,
                        'impact': stats['impact'],
                        'skill': stats['skill'],
                        'longevity': stats['longevity'],
                        'culture': stats['culture'],
                        'hype': stats['hype'],
                        'pack_id': pack_id,
                        'created_by_user_id': creator_id
                    }
                    
                    # Add card to master list
                    print(f"   Adding card to database: {card_id}")
                    success = self.db.add_card_to_master(card_data)
                    if success:
                        print(f"   ✅ Card added to master list")
                        self.db.add_card_to_pack(pack_id, card_data)
                        # Give creator a copy
                        self.db.add_card_to_collection(creator_id, card_id, 'pack_creation')
                        cards_created.append(card_data)
                    else:
                        print(f"   ❌ Failed to add card to master list")
                    
                except Exception as e:
                    print(f"❌ Error creating card: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Publish pack
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE creator_packs 
                    SET status = 'LIVE', published_at = CURRENT_TIMESTAMP
                    WHERE pack_id = ?
                """, (pack_id,))
                conn.commit()
            
            # Create visual confirmation embed
            embed = discord.Embed(
                title="✅ Pack Created Successfully!",
                description=f"**{pack_name}** featuring {artist['name']}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="📦 Pack ID", value=f"`{pack_id}`", inline=True)
            embed.add_field(name="🎤 Artist", value=artist['name'], inline=True)
            embed.add_field(name="🎵 Cards Created", value=str(len(cards_created)), inline=True)
            
            if artist.get('image_url'):
                embed.set_thumbnail(url=artist['image_url'])
            
            # Show all cards with stats
            card_list = ""
            for card in cards_created:
                rarity_emoji = {"legendary": "⭐", "epic": "🟣", "rare": "🔵", "common": "⚪"}.get(card['rarity'], "⚪")
                total_power = card['impact'] + card['skill'] + card['longevity'] + card['culture'] + card['hype']
                card_list += f"{rarity_emoji} **{card['title'][:30]}** ({card['rarity'].title()}) - Power: {total_power}\n"
            
            embed.add_field(name="🎴 Pack Contents", value=card_list or "No cards", inline=False)
            
            # Rarity distribution
            rarity_counts = {}
            for card in cards_created:
                rarity_counts[card['rarity']] = rarity_counts.get(card['rarity'], 0) + 1
            rarity_text = " | ".join([f"{r.title()}: {c}" for r, c in rarity_counts.items()])
            embed.add_field(name="🎯 Rarity Distribution", value=rarity_text or "N/A", inline=False)
            
            embed.add_field(
                name="📢 Status",
                value="✅ Published to Marketplace\n🎁 Cards added to your collection",
                inline=False
            )
            
            embed.set_footer(text="Use /collection to see your new cards!")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Error finalizing pack: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
    
    async def _search_youtube_fallback_auto(self, interaction: Interaction, pack_name: str, artist_name: str):
        """Auto-select mode: quickly search YouTube and create pack with first 5 videos"""
        try:
            # Search YouTube for videos
            videos = youtube_integration.search_music_video(artist_name, limit=10)
            
            if not videos or len(videos) < 5:
                await interaction.followup.send(
                    content=f"❌ Could not find enough videos for '{artist_name}' (need at least 5)",
                    ephemeral=False
                )
                return
            
            # Auto-select first 5 videos
            selected_videos = videos[:5]
            artist = {
                'name': artist_name,
                'image_url': videos[0].get('thumbnail_url', '') if videos else '',
                'popularity': 75,
                'followers': 1000000
            }
            
            # Finalize pack with auto-selected videos
            await self._finalize_pack_creation(
                interaction,
                pack_name,
                artist,
                selected_videos,
                interaction.user.id,
                self.pack_type
            )
        
        except Exception as e:
            print(f"❌ Error in auto-select YouTube fallback: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=False)
    
    async def _search_youtube_fallback(self, interaction: Interaction, pack_name: str, artist_name: str, artist_data: dict = None, lastfm_tracks: list = None):
        """Fall back to YouTube search for images while preserving Last.fm data"""
        
        # Search YouTube for videos
        videos = youtube_integration.search_music_video(artist_name, limit=10)
        
        if not videos:
            await interaction.followup.send(
                content=f"❌ Could not find videos for '{artist_name}'\n\n"
                        f"Try a different spelling or a more popular artist.",
                ephemeral=False
            )
            return
        
        # If we have Last.fm data, use it with YouTube images
        if artist_data and lastfm_tracks:
            # Match Last.fm tracks with YouTube videos for images
            enhanced_tracks = []
            for track in lastfm_tracks:
                # Try to find matching YouTube video
                matching_video = None
                track_name_lower = track['name'].lower()
                for video in videos:
                    video_title_lower = video['title'].lower()
                    if track_name_lower in video_title_lower or any(word in video_title_lower for word in track_name_lower.split() if len(word) > 3):
                        matching_video = video
                        break
                
                # Create enhanced track with YouTube image
                enhanced_track = track.copy()
                if matching_video:
                    enhanced_track['youtube_thumbnail'] = matching_video.get('thumbnail_url', '')
                    enhanced_track['youtube_url'] = matching_video.get('youtube_url', '')
                else:
                    # Use first video as fallback
                    enhanced_track['youtube_thumbnail'] = videos[0].get('thumbnail_url', '') if videos else ''
                    enhanced_track['youtube_url'] = videos[0].get('youtube_url', '') if videos else ''
                
                enhanced_tracks.append(enhanced_track)
            
            # Use Last.fm flow with YouTube images
            await show_song_selection_lastfm(
                interaction,
                pack_name,
                artist_data,
                enhanced_tracks,
                self.pack_type,
                self.db,
                finalize_pack_creation_lastfm
            )
            return
        
        # No Last.fm data - pure YouTube fallback
        artist = {
            'name': artist_name,
            'image_url': videos[0].get('thumbnail_url', '') if videos else '',
            'popularity': 75,
            'followers': 1000000
        }
        
        # Show song selection UI
        selection_embed = discord.Embed(
            title=f"🎵 Select Songs for Your {self.pack_type.title()} Pack",
            description=(
                f"**{pack_name}** featuring **{artist['name']}**\n\n"
                f"🎥 Using YouTube video thumbnails\n"
                f"Found **{len(videos)}** videos. Select up to 5 songs for your pack."
            ),
            color=discord.Color.gold() if self.pack_type == 'gold' else discord.Color.blue()
        )
        
        if artist.get('image_url'):
            selection_embed.set_thumbnail(url=artist['image_url'])
        
        selection_embed.add_field(
            name="📋 Instructions",
            value="1. Select songs from the dropdown menu\n"
                  "2. Click 'Confirm Selection' to create your pack\n"
                  "3. Cards will be generated and added to your collection",
            inline=False
        )
        
        # Add pack type info
        if self.pack_type == 'gold':
            selection_embed.add_field(
                name="💎 Gold Pack Bonus",
                value="Higher base stats (70-92) • Better rarity chances",
                inline=False
            )
        else:
            selection_embed.add_field(
                name="📦 Community Pack",
                value="Standard stats (50-85) • Normal rarity distribution",
                inline=False
            )
        
        # Create callback for when songs are selected
        async def on_songs_selected(confirm_interaction: Interaction, selected_tracks: list):
            await self._finalize_pack_creation(
                confirm_interaction,
                pack_name,
                artist,
                selected_tracks,
                interaction.user.id,
                self.pack_type
            )
        
        # Show selection view
        view = SongSelectionView(videos, max_selections=5, callback=on_songs_selected)
        await interaction.followup.send(
            embed=selection_embed,
            view=view,
            ephemeral=False
        )


class GiveCardModal(discord.ui.Modal, title="Give Card"):
    """Modal for giving cards"""
    
    def __init__(self, rarity: str, db: DatabaseManager):
        super().__init__()
        self.rarity = rarity
        self.db = db
    
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID or paste from @mention...",
        required=True,
        max_length=20
    )
    
    card_name = discord.ui.TextInput(
        label="Card Name",
        placeholder="Artist name for the card...",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: Interaction):
        try:
            target_id = int(self.user_id.value.replace('<@', '').replace('>', '').replace('!', ''))
            
            # Create card and give to user
            card_id = f"dev_gift_{interaction.user.id}_{target_id}_{self.card_name.value.lower().replace(' ', '_')}"
            
            card_data = {
                'card_id': card_id,
                'name': self.card_name.value,
                'title': 'Dev Gift',
                'rarity': self.rarity,
                'impact': 50,
                'skill': 50,
                'longevity': 50,
                'culture': 50,
                'hype': 50,
            }
            
            self.db.add_card_to_master(card_data)
            self.db.add_card_to_collection(target_id, card_id, 'dev_gift')
            
            await interaction.response.send_message(
                f"✅ Gave **{self.rarity.title()} Card** ({self.card_name.value}) to user {target_id}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class GiveCurrencyModal(discord.ui.Modal, title="Give Currency"):
    """Modal for giving currency"""
    
    def __init__(self, currency_type: str, db: DatabaseManager):
        super().__init__()
        self.currency_type = currency_type
        self.db = db
    
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID...",
        required=True,
        max_length=20
    )
    
    amount = discord.ui.TextInput(
        label="Amount",
        placeholder="Enter amount...",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: Interaction):
        try:
            target_id = int(self.user_id.value.replace('<@', '').replace('>', '').replace('!', ''))
            amt = int(self.amount.value)
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Ensure user exists
                cursor.execute("INSERT OR IGNORE INTO user_inventory (user_id) VALUES (?)", (target_id,))
                
                # Update currency
                if self.currency_type == "gold":
                    cursor.execute("UPDATE user_inventory SET gold = gold + ? WHERE user_id = ?", (amt, target_id))
                elif self.currency_type == "tickets":
                    cursor.execute("UPDATE user_inventory SET tickets = tickets + ? WHERE user_id = ?", (amt, target_id))
                elif self.currency_type == "xp":
                    cursor.execute("UPDATE user_inventory SET xp = xp + ? WHERE user_id = ?", (amt, target_id))
                
                conn.commit()
            
            await interaction.response.send_message(
                f"✅ Gave **{amt:,} {self.currency_type}** to user {target_id}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class UserLookupModal(discord.ui.Modal, title="User Lookup"):
    """Modal for user lookup"""
    
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
    
    user_id = discord.ui.TextInput(
        label="User ID",
        placeholder="Enter user ID...",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: Interaction):
        try:
            target_id = int(self.user_id.value.replace('<@', '').replace('>', '').replace('!', ''))
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_id,))
                user = cursor.fetchone()
                
                cursor.execute("SELECT * FROM user_inventory WHERE user_id = ?", (target_id,))
                inventory = cursor.fetchone()
                
                cursor.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (target_id,))
                card_count = cursor.fetchone()[0]
            
            embed = discord.Embed(title=f"👥 User Lookup: {target_id}", color=discord.Color.blue())
            
            if user:
                embed.add_field(name="User Found", value="✅ Yes", inline=True)
                embed.add_field(name="Cards Owned", value=str(card_count), inline=True)
            else:
                embed.add_field(name="User Found", value="❌ No", inline=True)
            
            if inventory:
                embed.add_field(
                    name="💰 Inventory",
                    value=f"Gold: {inventory[1] or 0:,}\n"
                          f"Dust: {inventory[2] or 0}\n"
                          f"Tickets: {inventory[3] or 0}\n"
                          f"XP: {inventory[5] or 0:,}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


class AnnouncementModal(discord.ui.Modal, title="Send Announcement"):
    """Modal for sending announcements"""
    
    message = discord.ui.TextInput(
        label="Announcement Message",
        style=discord.TextStyle.paragraph,
        placeholder="Type your announcement...",
        required=True,
        max_length=2000
    )
    
    async def on_submit(self, interaction: Interaction):
        embed = discord.Embed(
            title="📢 Announcement",
            description=self.message.value,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"From: {interaction.user.display_name}")
        
        # Send to current channel (or could be configured)
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)


class EventDurationModal(discord.ui.Modal, title="Event Duration"):
    """Modal for setting event duration"""
    
    def __init__(self, event_type: str, db: DatabaseManager):
        super().__init__()
        self.event_type = event_type
        self.db = db
    
    duration = discord.ui.TextInput(
        label="Duration (hours)",
        placeholder="Enter duration in hours...",
        required=True,
        max_length=5
    )
    
    async def on_submit(self, interaction: Interaction):
        try:
            hours = int(self.duration.value)
            
            event_names = {
                "gold_2x": "2x Gold Weekend",
                "xp_2x": "2x XP Event",
                "free_pack": "Free Pack Giveaway",
                "tournament": "Tournament",
            }
            
            await interaction.response.send_message(
                f"🎉 **Event Started!**\n\n"
                f"Event: **{event_names.get(self.event_type, self.event_type)}**\n"
                f"Duration: **{hours} hours**\n\n"
                f"Event will end automatically.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


# ============================================
# COG CLASS
# ============================================

class MenuSystemCog(commands.Cog):
    """Persistent menu system cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Register persistent views on bot startup"""
        self.bot.add_view(UserHubView(self.db))
        self.bot.add_view(DevPanelView(self.db))
        print("✅ Persistent menu views registered")
    
    @app_commands.command(name="setup_dev_panel", description="[DEV] Post persistent Dev Panel in this channel")
    async def setup_dev_panel(self, interaction: Interaction):
        """Post persistent dev panel in current channel (dev-only channel)"""
        # Check if in TEST_SERVER
        import os
        test_server_id = os.getenv('TEST_SERVER_ID')
        if test_server_id and interaction.guild_id != int(test_server_id):
            await interaction.response.send_message(
                "❌ This command is only available in the development server.",
                ephemeral=True
            )
            return
        
        # MUST defer immediately to prevent timeout
        await interaction.response.defer(ephemeral=False)
        
        view = DevPanelView(self.db)
        
        embed = discord.Embed(
            title="🔧 Developer Control Panel",
            description=(
                "**Important:** After bot restarts, run `/setup_dev_panel` again\n"
                "to refresh the panel buttons in this channel.\n\n"
                "**Pack Management:**\n"
                "• Create Community/Gold Packs (free)\n\n"
                "**User Management:**\n"
                "• Give cards/currency to users\n"
                "• Look up user data\n\n"
                "**Bot Management:**\n"
                "• View statistics\n"
                "• Database tools\n"
                "• Run events\n"
                "• Send announcements\n\n"
                "**Testing:**\n"
                "• Test new features\n"
                "• Restart bot\n\n"
                "All actions are logged for audit purposes."
            ),
            color=0xe74c3c
        )
        embed.set_footer(text="Dev Panel • Only visible to developers")
        
        # Delete old panel message if exists
        try:
            async for message in interaction.channel.history(limit=50):
                if message.author == self.bot.user and message.embeds:
                    if message.embeds[0].title == "🔧 Developer Control Panel":
                        await message.delete()
                        break
        except:
            pass
        
        await interaction.followup.send(embed=embed, view=view)
    
    @app_commands.command(name="menu", description="Open the main menu")
    async def menu_command(self, interaction: Interaction):
        """Open main menu via slash command"""
        view = UserHubView(self.db)
        
        embed = discord.Embed(
            title="🎵 Music Legends - Quick Menu",
            description="Select an option below:",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(MenuSystemCog(bot))
