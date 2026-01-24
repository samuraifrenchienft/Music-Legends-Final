import discord
from discord.ext import commands
import os

class TestBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix='!',
            intents=intents,
            application_id=None
        )
    
    async def setup_hook(self):
        print("🚀 Minimal bot starting...")
        
        # Test basic command
        @self.tree.command()
        async def test(interaction: discord.Interaction):
            await interaction.response.send_message("✅ Bot is working!")
        
        print("✅ Test command registered")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} commands")
        except Exception as e:
            print(f"❌ Sync failed: {e}")
    
    async def on_ready(self):
        print(f'✅ Bot is ready! Logged in as {self.user.name}')

if __name__ == "__main__":
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ No BOT_TOKEN found")
        exit()
    
    bot = TestBot()
    bot.run(token)
