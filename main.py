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
        app_id = os.getenv("DISCORD_APPLICATION_ID")
        if app_id:
            try:
                app_id = int(app_id)
            except ValueError:
                app_id = None
        
        super().__init__(
            command_prefix="!",
            help_command=None,
            intents=intents,
            application_id=app_id
        )

    async def setup_hook(self):
        """Initialize infrastructure and load cogs"""
        print("🚀 Bot starting - loading cogs...")
        
        # Load only essential cogs
        cogs = [
            'cogs.start_game',                # Start game command
            'cogs.gameplay',                  # Drop and battle commands
            'cogs.card_game',                 # Collection and pack creation commands
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
        
        try:
            if not test_server_id or test_server_id == "":
                print("🔄 Syncing commands globally...")
                synced = await self.tree.sync()
                print(f"✅ Synced {len(synced)} commands globally")
            else:
                guild = discord.Object(id=int(test_server_id))
                print(f"🔄 Syncing commands to test server {test_server_id}...")
                synced = await self.tree.sync(guild=guild)
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
