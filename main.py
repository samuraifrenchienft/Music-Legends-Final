import os
import discord
from dotenv import load_dotenv
from discord.ext import commands

# Load environment variables
print("🔧 Loading environment variables...")
if os.getenv("REDIS_URL") is None or os.getenv("BOT_TOKEN") is None:
    print("📄 Loading from .env.txt file")
    load_dotenv('.env.txt')
else:
    print("✅ Environment variables already loaded")

# Check critical environment variables
bot_token = os.getenv("BOT_TOKEN")
app_id = os.getenv("DISCORD_APPLICATION_ID")
test_server = os.getenv("TEST_SERVER_ID")

print(f"🔍 BOT_TOKEN: {'✅ Set' if bot_token else '❌ MISSING'}")
print(f"🔍 DISCORD_APPLICATION_ID: {'✅ Set' if app_id else '❌ MISSING'}")
print(f"🔍 TEST_SERVER_ID: {'✅ Set' if test_server else '❌ MISSING'}")

if not bot_token:
    print("❌ CRITICAL: BOT_TOKEN is missing!")
    exit(1)

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
        
        # Load essential cogs without duplicates
        cogs = [
            'cogs.start_game',                # Start game command
            'cogs.gameplay',                  # Drop and battle commands
            'cogs.card_game',                 # Collection and pack creation commands
            'cogs.menu_system',               # Persistent menu system (User Hub + Dev Panel)
        ]
        
        print(f"📦 Attempting to load {len(cogs)} cogs...")
        
        for cog in cogs:
            try:
                print(f"🔄 Loading {cog}...")
                await self.load_extension(cog)
                print(f'✅ Loaded extension: {cog}')
            except Exception as e:
                print(f'❌ Failed to load extension {cog}: {e}')
                print(f'⚠️ Continuing without {cog} - bot will still run')
                # Continue loading other cogs - don't break the whole bot
        
        print("🔍 Checking loaded commands...")
        loaded_commands = []
        for cog_name in self.cogs:
            cog = self.get_cog(cog_name)
            if cog:
                for cmd in cog.walk_app_commands():
                    loaded_commands.append(f"/{cmd.name}")
        
        print(f"📋 Total commands loaded: {len(loaded_commands)}")
        print(f"📋 Commands: {loaded_commands}")

    async def on_ready(self):
        """Sync commands when bot is ready"""
        print(f'✅ Bot is ready!')
        print(f'Logged in as: {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print(f'Connected to {len(self.guilds)} servers')
        
        # Sync commands now that bot is ready
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
    print("🚀 Starting Discord bot...")
    print(f"🔍 Python version: {os.sys.version}")
    print(f"🔍 Current directory: {os.getcwd()}")
    print(f"🔍 Files in directory: {os.listdir('.')}")

    try:
        token = os.getenv("BOT_TOKEN")
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
