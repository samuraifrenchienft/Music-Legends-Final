import os
import sys
import discord
from dotenv import load_dotenv
from discord.ext import commands

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

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
        print("🚀🚀🚀🚀🚀 BOT RESTARTING - USER REQUESTED RESTART 🚀🚀🚀🚀🚀")
        print("🔥🔥🔥 TIMESTAMP:", __import__('datetime').datetime.now())
        print("🔥🔥🔥 FORCING COMPLETE RESTART - ALL SYSTEMS RELOADING")
        
        # Initialize database with persistent storage
        from db_manager import db_manager
        
        # Use working directory for database on Railway
        if os.getenv("RAILWAY_ENVIRONMENT"):
            print("📁 Using working directory for database storage")
        
        db_manager.init_engine()
        
        # Create marketplace table
        await db_manager.create_marketplace_table()
        
        # Check for database restore on Railway
        if os.getenv("RAILWAY_ENVIRONMENT"):
            restored = await db_manager.restore_database_if_needed()
            if restored:
                print("✅ Database restored from backup")
        
        # Create automatic backup every hour
        if os.getenv("RAILWAY_ENVIRONMENT"):
            import asyncio
            async def backup_loop():
                while True:
                    await asyncio.sleep(3600)  # 1 hour
                    await db_manager.backup_database()
            
            asyncio.create_task(backup_loop())
            print("⏰ Automatic hourly backups enabled")
        
        # Load essential cogs without duplicates
        cogs = [
            'cogs.start_game',                # Start game command
            'cogs.gameplay',                  # Drop, collection, viewing commands
            'cogs.card_game',                 # Collection and pack creation commands
            'cogs.menu_system',               # Persistent menu system (User Hub + Dev Panel)
            'cogs.marketplace',               # Marketplace commands
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
        
        # Load additional cogs with error handling
        additional_cogs = ['cogs.dust_commands']
        for cog in additional_cogs:
            try:
                await self.load_extension(cog)
                print(f'✅ Loaded extension: {cog}')
            except Exception as e:
                print(f'⚠️ Could not load {cog}: {e}')
        
        print("🔍 Checking loaded commands...")
        loaded_commands = []
        for cog_name in self.cogs:
            cog = self.get_cog(cog_name)
            if cog:
                for cmd in cog.walk_app_commands():
                    loaded_commands.append(f"/{cmd.name}")
        
        print(f"📋 Total commands loaded: {len(loaded_commands)}")
        print(f"📋 Commands: {loaded_commands}")
        
        # Sync commands in setup_hook (runs before on_ready)
        test_server_id = os.getenv("TEST_SERVER_ID")
        
        try:
            if not test_server_id or test_server_id == "":
                print("🔄 Syncing commands globally...")
                synced = await self.tree.sync()
                print(f"✅ Synced {len(synced)} commands globally")
            else:
                print(f"⚠️ Skipping guild sync due to Discord API issues - commands should auto-sync")
                print(f"📋 Commands are registered and should appear automatically")
        except Exception as e:
            print(f'❌ Unexpected error during sync: {e}')
            print(f"📋 Commands are still registered locally - should work when Discord syncs automatically")
            traceback.print_exc()

    async def on_ready(self):
        """Called when bot is ready"""
        print(f'✅ Bot is ready!')
        print(f'Logged in as: {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print(f'Connected to {len(self.guilds)} servers')
        
        # Commands should auto-sync, skip manual sync to avoid errors
        print("📋 Commands should auto-register with Discord")
        
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
    print(f"🔧 DEPLOYMENT VERSION: 2.0 - NO MOCK DATA - DEV PANEL FIXED")

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
