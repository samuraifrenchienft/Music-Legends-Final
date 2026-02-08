"""Dev pack supply commands — view inventory and grant packs to users."""

import os
import discord
from discord import Interaction, app_commands
from discord.ext import commands
from database import DatabaseManager


def _is_dev(user_id: int) -> bool:
    dev_ids = os.getenv("DEV_USER_IDS", "").split(",")
    return str(user_id) in [uid.strip() for uid in dev_ids if uid.strip()]


class DevSupplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()

    @app_commands.command(name="dev_supply", description="[DEV] View dev pack supply inventory")
    async def dev_supply(self, interaction: Interaction):
        if not _is_dev(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        supply = self.db.get_dev_supply()

        if not supply:
            await interaction.followup.send("📦 Dev supply is empty.", ephemeral=True)
            return

        embed = discord.Embed(title="📦 Dev Pack Supply", color=discord.Color.blue())
        lines = []
        for item in supply:
            tier = item.get("pack_tier") or "?"
            lines.append(f"**{item['pack_name']}** (`{item['pack_id']}`)\n  Tier: {tier} | Qty: **{item['quantity']}**")
        embed.description = "\n".join(lines)
        embed.set_footer(text="Use /dev_grant_pack to send a pack to a user")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="dev_grant_pack", description="[DEV] Grant a pack from dev supply to a user")
    @app_commands.describe(pack_id="Pack ID to grant", user="Target user")
    async def dev_grant_pack(self, interaction: Interaction, pack_id: str, user: discord.Member):
        if not _is_dev(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        result = self.db.grant_pack_to_user(pack_id, user.id)

        if not result["success"]:
            await interaction.followup.send(f"❌ {result['error']}", ephemeral=True)
            return

        cards = result["cards"]
        pack_name = result["pack_name"]
        rarity_counts = {}
        for c in cards:
            r = c.get("rarity", "common")
            rarity_counts[r] = rarity_counts.get(r, 0) + 1

        rarity_text = " | ".join(f"{r.title()}: {n}" for r, n in sorted(rarity_counts.items()))
        embed = discord.Embed(
            title="🎁 Pack Granted!",
            description=f"**{pack_name}** sent to {user.mention}\n{len(cards)} cards: {rarity_text}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DevSupplyCog(bot))
