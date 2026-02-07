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
        
        # Check for database restore if needed
        restored = await db_manager.restore_database_if_needed()
        if restored:
            print("✅ Database restored from backup")
        
        # Run database integrity check on startup
        try:
            from database import DatabaseManager
            db = DatabaseManager()
            integrity_results = db.check_database_integrity()
            
            if integrity_results["valid"]:
                print(f"✅ Database integrity check passed ({integrity_results['tables_checked']} tables, {integrity_results['json_validated']} JSON fields validated)")
            else:
                print(f"⚠️ Database integrity check found issues:")
                for error in integrity_results["errors"]:
                    print(f"   ❌ {error}")
                for warning in integrity_results["warnings"][:5]:  # Show first 5 warnings
                    print(f"   ⚠️ {warning}")
                
                # Try to restore from backup if integrity check failed
                if integrity_results["errors"]:
                    print("🔄 Attempting to restore from latest backup...")
                    restored = await db_manager.restore_database_if_needed()
                    if restored:
                        print("✅ Database restored from backup after integrity check failure")
        except Exception as e:
            print(f"⚠️ Integrity check error (non-critical): {e}")
        
        # Initialize backup service and run cleanup
        try:
            from services.backup_service import backup_service
            backup_service.cleanup_old_backups()
            print("✅ Backup service initialized")
        except Exception as e:
            print(f"⚠️ Backup service initialization error: {e}")
            import traceback
            traceback.print_exc()
        
        # Create periodic backup task (every 20 minutes during active periods)
        import asyncio
        async def periodic_backup_loop():
            """Periodic backup task - runs every 20 minutes, only if bot is active"""
            await asyncio.sleep(300)  # Wait 5 minutes after startup before first backup
            
            while True:
                try:
                    # Check if bot is active (has guilds and is ready)
                    if hasattr(self, 'guilds') and len(self.guilds) > 0:
                        from services.backup_service import backup_service
                        backup_path = await backup_service.backup_periodic()
                        if backup_path:
                            print(f"⏰ Periodic backup created: {backup_path}")
                    else:
                        # Bot not ready yet, skip this cycle
                        pass
                except Exception as e:
                    print(f"⚠️ Periodic backup error (non-critical): {e}")
                
                # Wait 20 minutes (1200 seconds) before next backup
                await asyncio.sleep(1200)
        
        asyncio.create_task(periodic_backup_loop())
        print("⏰ Periodic backups enabled (every 20 minutes during active periods)")
        
        # Load essential cogs without duplicates
        cogs = [
            'cogs.start_game',                # Start game command
            'cogs.gameplay',                  # Drop, collection, viewing commands
            'cogs.card_game',                 # Collection and pack creation commands
            'cogs.menu_system',               # Persistent menu system (User Hub + Dev Panel)
            'cogs.marketplace',               # Marketplace commands
            'cogs.admin_bulk_import',         # Dev-only bulk pack import (TEST_SERVER)
            'cogs.admin_commands',            # Admin commands (all servers)
            'cogs.dev_webhook_commands',      # Dev webhook channel commands (TEST_SERVER)
            'cogs.battle_commands',           # Battle system (/battle, /battle_stats)
            'cogs.battlepass_commands',       # Battle Pass + Daily Quests
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
        
        # Sync commands
        test_server_id = os.getenv("TEST_SERVER_ID")

        try:
            # Always sync global commands (non-dev commands)
            print("🔄 Syncing global commands...")
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} commands globally")

            # Also sync to test guild so dev commands appear there immediately
            if test_server_id:
                try:
                    test_guild = discord.Object(id=int(test_server_id))
                    self.tree.copy_global_to(guild=test_guild)
                    guild_synced = await self.tree.sync(guild=test_guild)
                    print(f"✅ Synced {len(guild_synced)} commands to test guild {test_server_id}")
                except Exception as e:
                    print(f"⚠️ Could not sync to test guild: {e}")
        except Exception as e:
            print(f'❌ Unexpected error during sync: {e}')
            import traceback
            traceback.print_exc()

    async def on_ready(self):
        """Called when bot is ready"""
        print(f'✅ Bot is ready!')
        print(f'Logged in as: {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print(f'Connected to {len(self.guilds)} servers')
        
        # Commands should auto-sync, skip manual sync to avoid errors
        print("📋 Commands should auto-register with Discord")

        # Initialize bot logger so changelog webhook alerts work
        try:
            from services.bot_logger import get_bot_logger
            bot_logger = get_bot_logger(bot=self)
            bot_logger.log_major_event(
                'startup', f"Bot online — {len(self.guilds)} servers",
                severity='high', send_alert=True
            )
            print("📝 Bot logger initialized — changelogs active")
        except Exception as e:
            print(f"⚠️ Bot logger init failed (non-critical): {e}")

        # Seed packs synchronously — cleanup + insert runs in < 1 second
        # (API calls disabled, all songs are hardcoded in FALLBACK_SONGS)
        import asyncio
        try:
            print("[SEED] Starting seed_packs_into_db...")
            from services.seed_packs import seed_packs_into_db
            result = await asyncio.to_thread(seed_packs_into_db)
            print(f"[SEED] Done: {result.get('inserted', 0)} inserted, "
                  f"{result.get('skipped', 0)} skipped, {result.get('failed', 0)} failed")
        except Exception as e:
            print(f"[SEED] ERROR: {e}")
            import traceback
            traceback.print_exc()

        # Send any pending restart alerts that were queued during startup
        try:
            from services.system_monitor import get_system_monitor
            monitor = get_system_monitor(bot=self)
            await monitor.send_pending_alerts()
        except Exception as e:
            print(f"⚠️ Error sending pending alerts: {e}")
        
        await self.change_presence(activity=discord.Activity(name="Music Legends"))
        
        # Send startup notice to dev channel
        try:
            test_server_id = os.getenv('TEST_SERVER_ID')
            if test_server_id:
                test_server = self.get_guild(int(test_server_id))
                if test_server:
                    # Find #dev-controls channel
                    dev_channel = discord.utils.find(lambda c: c.name == 'dev-controls', test_server.channels)
                    if dev_channel and isinstance(dev_channel, discord.TextChannel):
                        startup_embed = discord.Embed(
                            title="🚀 Bot Restarted",
                            description="The bot has been restarted and is now online.",
                            color=discord.Color.green()
                        )
                        startup_embed.add_field(
                            name="⏰ Time",
                            value=f"<t:{int(__import__('time').time())}:F>",
                            inline=False
                        )
                        startup_embed.set_footer(text="All systems operational")
                        try:
                            await dev_channel.send(embed=startup_embed)
                        except Exception as e:
                            print(f"⚠️ Could not send startup notice: {e}")
        except Exception as e:
            print(f"⚠️ Startup notice error: {e}")

    async def close(self):
        """Cleanup when bot shuts down"""
        print("🔄 Cleaning up...")
        
        # Create backup before shutdown
        try:
            from services.backup_service import backup_service
            print("💾 Creating shutdown backup...")
            backup_path = await backup_service.backup_shutdown()
            if backup_path:
                print(f"✅ Shutdown backup created: {backup_path}")
            else:
                print("⚠️ Shutdown backup failed, but continuing with shutdown")
        except ImportError:
            print("⚠️ BackupService not available, skipping backup")
        except Exception as e:
            print(f"⚠️ Backup error (non-critical): {e}")
        
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
    print(f"🔧 DEPLOYMENT VERSION: 3.0 - SYNC SEED + DAILY CARD FIX - 2026-02-07")

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
