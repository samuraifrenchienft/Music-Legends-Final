import json
import os
import discord
from dotenv import load_dotenv
from discord import Interaction
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
        print(f"🔧 DEBUG: Deploying latest code with all fixes")
        
        # Temporarily disable async database to get basic bot working
        print("⚠️ Async database temporarily disabled - using existing database")
        # TODO: Re-enable async database after Railway dependencies are installed
        
        # Load cogs
        cogs = [
            'cogs.essential_commands',        # Core gameplay: collection, drop, battle, start_game
            'cogs.card_game',                 # Complete pack creation system with YouTube integration
            'cogs.pack_creation_simple',      # Simple pack creation without YouTube dependency
            'cogs.pack_creation',             # URL-based pack creation: /create_community_pack, /create_gold_pack
            'cogs.trading',                   # Trading system
            'cogs.founder_shop',              # Pack shop (Silver/Black packs)
            'cogs.server_revenue_commands',   # Server revenue tracking
            'cogs.wallet_connect_commands'    # Wallet connect with exact UX copy (NFT boosts disabled until ready)
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f'✅ Loaded extension: {cog}')
            except Exception as e:
                print(f'❌ Failed to load extension {cog}: {e}')
                print(f'⚠️ Continuing without {cog} - bot will still run')
                # Continue loading other cogs - don't break the whole bot

        test_server_id = os.getenv("TEST_SERVER_ID")
        print(f"TEST_SERVER_ID: {test_server_id}")
        
        # Add basic test command before sync
        try:
            from discord import Interaction
        except ImportError:
            Interaction = object  # Fallback for Railway environment issues
        
        @self.tree.command()
        async def basic_test(interaction: Interaction):
            await interaction.response.send_message("✅ Basic bot is working!")
        
        # Clear old commands first
        print("🧹 Clearing old commands...")
        self.tree.clear_commands(guild=None)
        if test_server_id and test_server_id != "":
            self.tree.clear_commands(guild=discord.Object(id=int(test_server_id)))
        
        # Debug: Show all commands before sync
        all_commands = list(self.tree.walk_commands())
        print(f"📋 Total commands to sync: {len(all_commands)}")
        for cmd in all_commands:
            print(f"  - {cmd.name} (from {cmd.cog.__class__.__name__ if cmd.cog else 'None'})")
        
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
            print("⚠️ Bot will still run with basic commands")
        except discord.HTTPException as e:
            print(f"❌ Command sync failed (HTTPException): {e}")
            print("⚠️ Bot will still run with basic commands")
        except Exception as e:
            print(f"❌ Unexpected error during sync: {e}")
            print("⚠️ Bot will still run with basic commands")

    async def on_ready(self):
        print(f'✅ Bot is ready!')
        print(f'Logged in as: {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print(f'Connected to {len(self.guilds)} servers')
        
        await self.change_presence(activity=discord.Activity(name="Music Legends"))

    async def close(self):
        """Cleanup when bot shuts down"""
        print("🔄 Cleaning up...")
        
        try:
            from db_manager import db_manager
            await db_manager.close()
            print("✅ Database closed")
        except ImportError:
            print("⚠️ Database manager not available")
        except Exception as e:
            print(f"⚠️ Error closing database: {e}")
        
        print("Bot shutdown complete")

if __name__ == "__main__":
    try:
        token = os.getenv("BOT_TOKEN")
        if not token:
            print("❌ No BOT_TOKEN found in environment variables")
            print("⚠️ Please set BOT_TOKEN and restart")
            exit(1)
        
        token = token.strip()
        if not token:
            print("❌ BOT_TOKEN is empty")
            print("⚠️ Please set valid BOT_TOKEN and restart")
            exit(1)
        
        print(f"🚀 Starting bot with token: {token[:10]}...")
        bot = Bot()
        bot.run(token)
    except Exception as e:
        print(f"❌ Bot startup failed: {e}")
        print("⚠️ Bot will attempt to restart...")
        # The container/service manager will restart the bot
