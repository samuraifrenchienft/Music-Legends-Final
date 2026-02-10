"""Dev pack supply commands — view inventory and grant packs to users."""

import os
import discord
from discord import Interaction, app_commands
from discord.ext import commands
from database import DatabaseManager, get_db


def _is_dev(user_id: int) -> bool:
    dev_ids = os.getenv("DEV_USER_IDS", "").split(",")
    return str(user_id) in [uid.strip() for uid in dev_ids if uid.strip()]


class DevSupplyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = get_db()

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


    @app_commands.command(name="dev_reset_daily", description="[DEV] Reset a user's daily claim for testing")
    @app_commands.describe(user="User to reset (defaults to yourself)")
    async def dev_reset_daily(self, interaction: Interaction, user: discord.Member = None):
        if not _is_dev(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            return

        target = user or interaction.user
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_inventory SET last_daily_claim = NULL, daily_streak = 0 WHERE user_id = ?",
                (target.id,)
            )
            conn.commit()
            changed = cursor.rowcount

        if changed:
            await interaction.response.send_message(
                f"✅ Daily claim reset for {target.mention}. They can claim again now.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ No inventory row found for {target.mention}. They may not have played yet.", ephemeral=True
            )


    @app_commands.command(name="give_gold", description="[DEV] Give gold to a user for testing")
    @app_commands.describe(user="Target user", amount="Amount of gold to give")
    async def give_gold(self, interaction: Interaction, user: discord.Member, amount: int):
        if not _is_dev(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive.", ephemeral=True)
            return

        ph = self.db._get_placeholder()
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            # Ensure user_inventory row exists first
            cursor.execute(
                f"INSERT INTO user_inventory (user_id, gold) VALUES ({ph}, 0) ON CONFLICT DO NOTHING",
                (user.id,)
            )
            # Add gold
            cursor.execute(
                f"UPDATE user_inventory SET gold = gold + {ph} WHERE user_id = {ph}",
                (amount, user.id)
            )
            # Get new balance
            cursor.execute(
                f"SELECT gold FROM user_inventory WHERE user_id = {ph}",
                (user.id,)
            )
            row = cursor.fetchone()
            new_balance = row[0] if row else amount

        embed = discord.Embed(
            title="💰 Gold Given",
            description=f"Gave **{amount:,}** gold to {user.mention}\nNew balance: **{new_balance:,}** gold",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DevSupplyCog(bot))
