# cogs/admin_commands.py
"""
Basic Admin Commands
Commands available to server administrators in all servers
"""

import discord
from discord.ext import commands
from discord import Interaction, app_commands
from database import DatabaseManager, get_db

from ..config import settings


class AdminCommandsCog(commands.Cog):
    """Basic admin commands for server administrators"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = get_db()

    @app_commands.command(name="server_analytics", description="View server usage analytics")
    @app_commands.default_permissions(administrator=True)
    async def server_analytics(self, interaction: Interaction, days: int = 30):
        """Show server usage analytics"""
        # Check if server is premium
        if not self.db.is_server_premium(interaction.guild.id):
            await interaction.response.send_message(
                "📊 Analytics is a Premium feature! Use `/premium_subscribe` to upgrade.",
                ephemeral=True
            )
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
        
        embed.set_footer(text="Analytics updated daily • Premium Feature")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="dev_grant_all_cards", description="[DEV ONLY] Grant all marketplace cards to yourself")
    async def dev_grant_all_cards(self, interaction: Interaction):
        """Dev-only command to grant all cards from cards table"""
        # Check if user is a dev
        if interaction.user.id not in settings.DEV_USER_IDS:
            await interaction.response.send_message("❌ This command is only available to developers.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Get all cards from cards table
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT card_id FROM cards")
            all_cards = [row[0] for row in cursor.fetchall()]

        if not all_cards:
            await interaction.followup.send(
                "❌ **Error:** Cards table is empty!\n"
                "The seed packs may not have been loaded properly.",
                ephemeral=True
            )
            return

        # Grant each card to the dev user
        granted = 0
        skipped = 0
        for card_id in all_cards:
            added = self.db.add_card_to_collection(
                user_id=interaction.user.id,
                card_id=card_id,
                acquired_from='dev_grant'
            )
            if added:
                granted += 1
            else:
                skipped += 1

        await interaction.followup.send(
            f"✅ **Dev Card Grant Complete**\n"
            f"• **Granted:** {granted} new cards\n"
            f"• **Already owned:** {skipped} cards\n"
            f"• **Total cards in database:** {len(all_cards)}",
            ephemeral=True
        )
        print(f"[DEV_GRANT] User {interaction.user.id} granted {granted} cards, skipped {skipped} already owned")


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommandsCog(bot))
