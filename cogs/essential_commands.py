"""
Essential Game Commands - No Duplicates
Only the core commands needed for gameplay
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import os
import sqlite3

class EssentialCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.economy = None
        self.stripe = None
        
        # Initialize database and economy lazily
        self._init_database()
        
    def _init_database(self):
        """Initialize database and economy managers"""
        try:
            from database import DatabaseManager
            self.db = DatabaseManager()
            print("✅ Database initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize database: {e}")
            self.db = None
            
        try:
            from card_economy import get_economy_manager
            self.economy = get_economy_manager()
            self.economy.initialize_economy_tables()
            print("✅ Economy tables initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize economy: {e}")
            self.economy = None
            
        try:
            from stripe_payments import StripePaymentManager
            self.stripe = StripePaymentManager()
            print("✅ Stripe initialized")
        except Exception as e:
            print(f"⚠️ Failed to initialize Stripe: {e}")
            self.stripe = None
    
        
    
    
async def setup(bot):
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(EssentialCommandsCog(bot))
    else:
        await bot.add_cog(
            EssentialCommandsCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
