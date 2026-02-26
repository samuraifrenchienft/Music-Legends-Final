"""
DEPRECATED - This cog is no longer used
All functionality has been moved to card_game.py
This file is kept for reference only
"""
import discord
from discord.ext import commands
import os

class EssentialCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("⚠️ EssentialCommandsCog is DEPRECATED - use card_game.py instead")
    
async def setup(bot):
    # This cog should not be loaded anymore
    print("⚠️ essential_commands.py is deprecated - not loading")
    pass
