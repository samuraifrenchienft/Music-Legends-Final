# cogs/admin_commands.py
"""
Basic Admin Commands
Commands available to server administrators in all servers
"""

import discord
from discord.ext import commands
from discord import Interaction, app_commands
from database import DatabaseManager


class AdminCommandsCog(commands.Cog):
    """Basic admin commands for server administrators"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
    
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


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCommandsCog(bot))
