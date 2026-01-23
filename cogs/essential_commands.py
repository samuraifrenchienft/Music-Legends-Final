"""
Essential Game Commands - No Duplicates
Only the core commands needed for gameplay
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
from database import DatabaseManager
from card_economy import CardEconomyManager

class EssentialCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.economy = CardEconomyManager(self.db)
    
    @app_commands.command(name="collection", description="View your card collection")
    async def collection(self, interaction: Interaction):
        """View your card collection"""
        await interaction.response.send_message("📦 Collection feature coming soon!", ephemeral=True)
    
    @app_commands.command(name="drop", description="Create a card drop in this channel")
    async def drop(self, interaction: Interaction):
        """Create a card drop"""
        try:
            drop_result = self.economy.create_drop(
                interaction.channel_id,
                interaction.guild.id,
                interaction.user.id
            )
            
            if not drop_result['success']:
                await interaction.response.send_message(f"❌ {drop_result['error']}", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🎴 CARD DROP! 🎴",
                description="React quickly to grab cards!",
                color=discord.Color.gold()
            )
            
            cards = drop_result['cards']
            for i, card in enumerate(cards, 1):
                tier_emoji = {"community": "⚪", "gold": "🟡", "platinum": "🟣", "legendary": "🔴"}.get(card.get('tier', 'community'), "⚪")
                embed.add_field(
                    name=f"{tier_emoji} Card {i}",
                    value=f"{card.get('name', 'Unknown')}\nTier: {card.get('tier', 'community').title()}",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating drop: {e}", ephemeral=True)
    
    @app_commands.command(name="battle", description="Challenge someone to a card battle")
    async def battle(self, interaction: Interaction, opponent: discord.User):
        """Challenge someone to a battle"""
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't battle yourself!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚔️ Battle Challenge!",
            description=f"{interaction.user.mention} has challenged {opponent.mention} to a card battle!",
            color=discord.Color.red()
        )
        embed.add_field(name="Status", value="⏳ Waiting for opponent to accept...")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(EssentialCommandsCog(bot))
    else:
        await bot.add_cog(
            EssentialCommandsCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
