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
    
    @app_commands.command(name="setup_user_hub", description="Post persistent User Hub in this channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_user_hub(self, interaction: Interaction):
        """Post persistent user hub in current channel"""
        from cogs.menu_system import UserHubView
        
        view = UserHubView(self.db)
        
        embed = discord.Embed(
            title="🎵 Music Legends - Main Menu",
            description=(
                "Welcome to Music Legends!\n\n"
                "**Get Started:**\n"
                "• Click 🏪 **Shop** to buy your first pack\n"
                "• Open packs to get cards\n"
                "• Click ⚔️ **Battle** to challenge players\n"
                "• Click 💰 **Daily Claim** for free rewards!\n\n"
                "**Premium Features:**\n"
                "• 🎵 **Battle Pass** - Exclusive rewards\n"
                "• 👑 **VIP** - Daily bonuses & perks\n\n"
                "Use the buttons below to navigate!"
            ),
            color=0x3498db
        )
        embed.set_footer(text="Tip: Click any button to get started!")
        
        await interaction.response.send_message(embed=embed, view=view)
    
    
    @app_commands.command(name="delete_pack", description="[ADMIN] Delete a pack by ID")
    @app_commands.describe(pack_id="Pack ID to delete")
    @app_commands.default_permissions(administrator=True)
    async def delete_pack(self, interaction: Interaction, pack_id: str):
        """Delete a pack - Admin only"""
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
            await interaction.followup.send("❌ Something went wrong. Please try again.", ephemeral=True)
    
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
