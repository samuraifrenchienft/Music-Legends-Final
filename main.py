import json
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from infrastructure import infrastructure
from scheduler.jobs import init_cron

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
        # Initialize infrastructure
        await infrastructure.initialize()
        
        # Initialize and start cron service
        job_status = await init_cron()
        print(f"Cron jobs initialized: {list(job_status.keys())}")
        
        # Start queue processors
        await infrastructure.start_queue_processors()
        
        # Load cogs
        cogs = [
            'cogs.card_game',
            'cogs.gameplay',
            'cogs.packs',
            'cogs.trading',
            'cogs.founder_shop'
        ]
        
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f'Loaded extension: {cog}')
            except Exception as e:
                print(f'Failed to load extension {cog}: {e}')

        test_server_id = os.getenv("TEST_SERVER_ID")
        try:
            if test_server_id == "" or test_server_id is None:
                await self.tree.sync()
            else:
                await self.tree.sync(guild=discord.Object(id=int(test_server_id)))
        except discord.Forbidden as e:
            print(f"Command sync failed (Forbidden): {e}")
        except discord.HTTPException as e:
            print(f"Command sync failed (HTTPException): {e}")

    async def on_ready(self):
        print(f'Bot is ready!')
        print(f'Logged in as: {self.user.name}')
        print(f'Bot ID: {self.user.id}')
        print(f'Connected to {len(self.guilds)} servers')
        print("Bot is ready!")
        
        # Show infrastructure status
        status = infrastructure.get_status()
        print(f'Infrastructure status: {status}')
        
        # Show cron job status
        from scheduler.cron import cron_service
        cron_status = cron_service.get_job_status()
        print(f'Cron jobs status: {cron_status}')
        
        await self.change_presence(activity=discord.Activity(name="with slash commands."))

    async def close(self):
        """Cleanup when bot shuts down"""
        await infrastructure.shutdown()
        
        # Stop cron service
        from scheduler.cron import cron_service
        cron_service.stop()
        
        print("Bot shutdown complete")

if __name__ == "__main__":
    bot = Bot()
    bot.run(os.getenv("BOT_TOKEN").strip())
