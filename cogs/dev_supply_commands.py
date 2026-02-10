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


    @app_commands.command(name="dev_debug", description="[DEV] Diagnose why cards aren't showing in /collection")
    @app_commands.describe(user="User to check (defaults to yourself)")
    async def dev_debug(self, interaction: discord.Interaction, user: discord.Member = None):
        if not _is_dev(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        target = user or interaction.user
        ph = self.db._get_placeholder()

        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Live pack count
            cursor.execute("SELECT COUNT(*), COUNT(CASE WHEN pack_tier='community' THEN 1 END) FROM creator_packs WHERE status='LIVE'")
            total_live, community_live = cursor.fetchone()

            # 2. user_cards rows for this user
            cursor.execute(f"SELECT COUNT(*) FROM user_cards WHERE user_id = {ph}", (target.id,))
            user_cards_count = cursor.fetchone()[0]

            # 3. How many of those user_cards have a matching cards row (JOIN check)
            cursor.execute(f"""
                SELECT COUNT(*) FROM user_cards uc
                JOIN cards c ON c.card_id = uc.card_id
                WHERE uc.user_id = {ph}
            """, (target.id,))
            matched_count = cursor.fetchone()[0]

            # 4. Orphaned user_cards (in user_cards but NOT in cards table)
            cursor.execute(f"""
                SELECT uc.card_id FROM user_cards uc
                LEFT JOIN cards c ON c.card_id = uc.card_id
                WHERE uc.user_id = {ph} AND c.card_id IS NULL
                LIMIT 5
            """, (target.id,))
            orphans = [r[0] for r in cursor.fetchall()]

            # 5. Total cards in master table
            cursor.execute("SELECT COUNT(*) FROM cards")
            total_cards = cursor.fetchone()[0]

            # 6. pack_purchases for this user
            cursor.execute(f"SELECT COUNT(*) FROM pack_purchases WHERE buyer_id = {ph}", (target.id,))
            pack_purchases = cursor.fetchone()[0]

        lines = [
            f"**Target:** {target.mention}",
            f"",
            f"**Live Packs:** {total_live} total, {community_live} community tier",
            f"**Master cards table:** {total_cards} cards",
            f"",
            f"**{target.display_name}'s Data:**",
            f"• `user_cards` rows: **{user_cards_count}**",
            f"• Cards matched via JOIN: **{matched_count}**",
            f"• Orphaned (in user_cards, missing from cards): **{user_cards_count - matched_count}**",
            f"• Pack purchases recorded: **{pack_purchases}**",
        ]
        if orphans:
            lines.append(f"• Orphaned card IDs: `{'`, `'.join(orphans)}`")

        if user_cards_count == 0:
            lines.append(f"\n⚠️ **No cards in user_cards at all** — pack grants are failing or no packs exist")
        elif matched_count == 0:
            lines.append(f"\n⚠️ **Cards in user_cards but none in master cards table** — orphan bug")
        elif matched_count < user_cards_count:
            lines.append(f"\n⚠️ **Some orphans** — partial data issue")
        else:
            lines.append(f"\n✅ Data looks correct — check /collection again")

        embed = discord.Embed(title="🔍 Card Debug Info", description="\n".join(lines), color=discord.Color.orange())
        await interaction.followup.send(embed=embed, ephemeral=True)


    @app_commands.command(name="dev_seed_pack", description="[DEV] Seed a starter community pack so daily claim works")
    async def dev_seed_pack(self, interaction: discord.Interaction):
        if not _is_dev(interaction.user.id):
            await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        result = self.db.seed_starter_pack("Music Legends Starter Pack")

        if result["success"]:
            embed = discord.Embed(
                title="🌱 Starter Pack Seeded",
                description=(
                    f"Created **{result['pack_name']}** (`{result['pack_id']}`)\n"
                    f"{result['cards']} starter cards added\n\n"
                    "Daily claim will now grant packs to users."
                ),
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Seed Result",
                description=result["error"],
                color=discord.Color.blue()
            )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DevSupplyCog(bot))
