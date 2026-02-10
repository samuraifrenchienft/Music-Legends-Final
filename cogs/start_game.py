"""
Start Game Command - Initialize Music Legends using pre-seeded packs
No YouTube API required - uses seed packs loaded on startup
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
import sqlite3
import os


class StartGameCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        from database import get_db
        self.db = get_db()

    @app_commands.command(name="start_game", description="🎮 Start Music Legends in this server!")
    async def start_game(self, interaction: Interaction):
        """Initialize Music Legends - announces the game and shows available packs"""

        # Check if user is admin/owner
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "🔒 Only server administrators can start the game!", ephemeral=True
            )
            return

        await interaction.response.defer()

        # Check how many seed packs exist
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM creator_packs WHERE status = 'LIVE'")
            pack_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT name, pack_size FROM creator_packs
                WHERE status = 'LIVE'
                ORDER BY name
                LIMIT 10
            """)
            sample_packs = cursor.fetchall()

        if pack_count == 0:
            # No packs - seed packs may not have loaded
            error_embed = discord.Embed(
                title="⚠️ No Packs Available",
                description=(
                    "Seed packs haven't loaded yet. This usually fixes itself on the next restart.\n\n"
                    "If this persists, check Railway logs for seed pack errors."
                ),
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        # Create announcement embed
        embed = discord.Embed(
            title="🎵🎮 MUSIC LEGENDS IS NOW LIVE! 🎮🎵",
            description=f"""
**Welcome to Music Legends - The Ultimate Card Battle Game!**

🎴 **Collect cards** of your favorite music artists
⚔️ **Battle friends** with strategic card decks
🎁 **Open packs** for rare cards
💰 **Trade & sell** cards in the marketplace

📦 **{pack_count} packs available** across multiple genres!

🚀 **Getting Started:**
• `/drop` - Claim cards from community drops
• `/deck` - View your battle deck and cards
• `/battle @friend` - Challenge someone to a card battle
• `/packs` - Browse available card packs
            """,
            color=discord.Color.purple()
        )

        # Show sample packs
        if sample_packs:
            pack_list = "\n".join([f"• **{name}** ({size} cards)" for name, size in sample_packs[:6]])
            embed.add_field(
                name="📦 Sample Packs",
                value=pack_list,
                inline=False
            )

        embed.add_field(
            name="🎯 Status",
            value="✅ **Game Ready!** All systems operational.",
            inline=False
        )

        embed.set_footer(text="Use /help for a full list of commands")

        await interaction.followup.send("@everyone", embed=embed)

        # Drop a welcome pack using the same mechanism as /drop
        try:
            from cogs.gameplay import CardDropView
            pack = self.db.get_random_live_pack_by_tier("community")
            if pack:
                drop_embed = discord.Embed(
                    title="⚪ WELCOME PACK DROP! ⚪",
                    description=f"**{pack['name']}**\nFirst to click claims all {pack['pack_size']} cards!",
                    color=discord.Color.light_gray()
                )
                drop_embed.add_field(name="Tier", value="Community", inline=True)
                drop_embed.add_field(name="Cards", value=str(pack['pack_size']), inline=True)
                if pack.get("genre"):
                    drop_embed.add_field(name="Genre", value=pack["genre"], inline=True)
                drop_embed.set_footer(text="Welcome drop! • Expires in 5 min")

                view = CardDropView(pack=pack, db=self.db, timeout=300)
                msg = await interaction.followup.send(embed=drop_embed, view=view)
                view.message = msg
        except Exception as e:
            print(f"⚠️ Welcome drop failed (non-critical): {e}")


async def setup(bot):
    await bot.add_cog(StartGameCog(bot))
