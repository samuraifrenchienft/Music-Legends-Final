import discord
import os
from discord.ext.commands import Cog
from discord import Interaction
from discord import app_commands

class ExampleCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name = "ping",
        description = "Pong!"
    )
    async def ping(self, ctx: Interaction):
        await ctx.response.send_message("Pong!")

async def setup(bot):
    # Check if we should sync globally or to test server
    test_server_id = os.getenv("TEST_SERVER_ID")
    if test_server_id == "" or test_server_id is None:
        await bot.add_cog(ExampleCog(bot))
    else:
        await bot.add_cog(
            ExampleCog(bot),
            guild=discord.Object(id=int(test_server_id))
        )
