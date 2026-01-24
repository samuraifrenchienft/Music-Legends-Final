import json
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

# Load environment variables
if os.getenv("REDIS_URL") is None or os.getenv("BOT_TOKEN") is None:
    load_dotenv('.env.txt')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent for reactions
intents.guilds = True
intents.members = True
intents.presences = True  # Enable presence intent
intents.reactions = True  # Enable reaction intent

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix = "!",
            help_command = None,
            intents = intents,
            application_id = None
        )

    async def setup_hook(self):
        """Initialize infrastructure and load cogs"""
        print("🚀 Bot starting - loading cogs...")
        
        # Load cogs
        cogs = [
            'cogs.essential_commands',        # Core gameplay: collection, drop, battle, start_game
            'cogs.pack_creation',             # URL-based pack creation: /create_community_pack, /create_gold_pack
            'cogs.trading',                   # Trading system
            'cogs.founder_shop',              # Pack shop (Silver/Black packs)
            'cogs.server_revenue_commands',   # Server revenue tracking
            'cogs.wallet_connect_commands'    # Wallet connect with exact UX copy (NFT boosts disabled until ready)
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f'Loaded extension: {cog}')
            except Exception as e:
                print(f'Failed to load extension {cog}: {e}')

        test_server_id = os.getenv("TEST_SERVER_ID")
        print(f"TEST_SERVER_ID: {test_server_id}")
        
        # Clear old commands first
        print("🧹 Clearing old commands...")
        self.tree.clear_commands(guild=None)
        if test_server_id and test_server_id != "":
            self.tree.clear_commands(guild=discord.Object(id=int(test_server_id)))
        
        try:
            if test_server_id == "" or test_server_id is None:
                print("🔄 Syncing commands globally...")
                synced = await self.tree.sync()
                print(f"✅ Synced {len(synced)} commands globally")
            else:
                print(f"🔄 Syncing commands to test server {test_server_id}...")
                synced = await self.tree.sync(guild=discord.Object(id=int(test_server_id)))
                print(f"✅ Synced {len(synced)} commands to test server")
        except discord.Forbidden as e:
            print(f"❌ Command sync failed (Forbidden): {e}")
        except discord.HTTPException as e:
            print(f"❌ Command sync failed (HTTPException): {e}")

    async def on_ready(self):
        print(f'✅ Bot is ready!')
        print(f'Logged in as: {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print(f'Connected to {len(self.guilds)} servers')
        
        await self.change_presence(activity=discord.Activity(name="Music Legends"))

    async def close(self):
        """Cleanup when bot shuts down"""
        print("Bot shutdown complete")

if __name__ == "__main__":
    bot = Bot()
    bot.run(os.getenv("BOT_TOKEN").strip())
