# cogs/battlepass_commands.py
"""
Battle Pass & Daily Quests commands
/battlepass — view tier progress, rewards, claim
/quests    — view and track daily quests
"""

import discord
import sqlite3
from datetime import datetime, timedelta
from discord.ext import commands
from discord import Interaction, app_commands
from typing import Optional

from config.battle_pass import (
    BattlePass, BattlePassManager, FREE_TRACK_REWARDS,
    PREMIUM_TRACK_REWARDS, get_battle_pass_manager,
)
from config.economy import DAILY_QUESTS
from database import DatabaseManager


class BattlePassCommands(commands.Cog):
    """Battle Pass and Daily Quests"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.bp = get_battle_pass_manager()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _get_user_bp_data(self, user_id: int) -> dict:
        """Return battle-pass relevant data from DB"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # XP from user_inventory
            cursor.execute("SELECT xp FROM user_inventory WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            xp = row[0] if row and row[0] else 0

            # Check premium status
            cursor.execute("SELECT premium_expires FROM user_inventory WHERE user_id = ?", (user_id,))
            prem = cursor.fetchone()
            has_premium = False
            if prem and prem[0]:
                try:
                    has_premium = datetime.fromisoformat(prem[0]) > datetime.now()
                except Exception:
                    pass

            # Claimed tiers (stored as JSON list in season_progress)
            cursor.execute("""
                SELECT claimed_tiers FROM season_progress WHERE user_id = ?
            """, (user_id,))
            claimed_row = cursor.fetchone()
            claimed_tiers = []
            if claimed_row and claimed_row[0]:
                import json
                try:
                    claimed_tiers = json.loads(claimed_row[0])
                except Exception:
                    pass

        return {
            'xp': xp,
            'has_premium': has_premium,
            'claimed_tiers': claimed_tiers,
        }

    def _save_claimed_tiers(self, user_id: int, claimed: list):
        import json
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO season_progress (user_id, claimed_tiers)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET claimed_tiers = ?
            """, (user_id, json.dumps(claimed), json.dumps(claimed)))
            conn.commit()

    def _ensure_season_table(self):
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS season_progress (
                    user_id INTEGER PRIMARY KEY,
                    claimed_tiers TEXT DEFAULT '[]',
                    quest_progress TEXT DEFAULT '{}',
                    last_quest_reset TEXT
                )
            """)
            conn.commit()

    # ------------------------------------------------------------------
    # /battlepass
    # ------------------------------------------------------------------

    @app_commands.command(name="battlepass", description="View your Battle Pass progress and rewards")
    async def battlepass_command(self, interaction: Interaction):
        self._ensure_season_table()
        data = self._get_user_bp_data(interaction.user.id)
        xp = data['xp']
        has_premium = data['has_premium']
        claimed = data['claimed_tiers']

        tier = self.bp.calculate_tier_from_xp(xp)
        progress_in_tier = self.bp.get_xp_progress_in_tier(xp)
        xp_to_next = self.bp.xp_to_next_tier(xp)
        days_left = self.bp.days_remaining()

        # Build embed
        premium_badge = " **[PREMIUM]**" if has_premium else ""
        embed = discord.Embed(
            title=f"🎵 Battle Pass — {BattlePass.SEASON_NAME}{premium_badge}",
            description=f"Season {BattlePass.SEASON_NUMBER} • {days_left} days remaining",
            color=0x9b59b6 if has_premium else 0x3498db,
        )

        # Progress bar
        pct = min(tier / BattlePass.TOTAL_TIERS * 100, 100)
        bar_filled = int(pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        embed.add_field(
            name=f"📊 Tier {tier} / {BattlePass.TOTAL_TIERS}",
            value=f"`{bar}` {pct:.0f}%\n**XP:** {xp:,} / {BattlePass.TOTAL_XP_REQUIRED:,}",
            inline=False,
        )

        if xp_to_next > 0:
            cur, needed = progress_in_tier
            embed.add_field(
                name="⏭️ Next Tier",
                value=f"{cur}/{needed} XP ({xp_to_next} XP to go)",
                inline=True,
            )

        # Show current + next 2 tiers of rewards
        for t in range(tier, min(tier + 3, BattlePass.TOTAL_TIERS + 1)):
            free_r = FREE_TRACK_REWARDS.get(t)
            prem_r = PREMIUM_TRACK_REWARDS.get(t) if has_premium else None
            claimed_tag = " ✅" if t in claimed else ""
            reward_text = self.bp.format_reward(free_r) if free_r else "—"
            if prem_r:
                reward_text += f"\n🔒 {self.bp.format_reward(prem_r)}"
            embed.add_field(
                name=f"Tier {t}{claimed_tag}",
                value=reward_text,
                inline=True,
            )

        unclaimed = self.bp.get_unclaimed_rewards(tier, claimed, has_premium)
        if unclaimed:
            embed.add_field(
                name="🎁 Unclaimed Rewards",
                value=f"You have **{len(unclaimed)}** unclaimed tier(s)! Use `/claim_bp <tier>` to collect.",
                inline=False,
            )

        if not has_premium:
            embed.set_footer(text=f"Unlock Premium for ${BattlePass.PREMIUM_PRICE_USD} to get bonus rewards every tier!")

        await interaction.response.send_message(embed=embed)

    # ------------------------------------------------------------------
    # /claim_bp
    # ------------------------------------------------------------------

    @app_commands.command(name="claim_bp", description="Claim a Battle Pass tier reward")
    @app_commands.describe(tier="The tier number to claim")
    async def claim_bp_command(self, interaction: Interaction, tier: int):
        self._ensure_season_table()
        data = self._get_user_bp_data(interaction.user.id)
        current_tier = self.bp.calculate_tier_from_xp(data['xp'])

        if tier < 1 or tier > BattlePass.TOTAL_TIERS:
            return await interaction.response.send_message("Invalid tier number.", ephemeral=True)
        if tier > current_tier:
            return await interaction.response.send_message(
                f"You haven't reached tier {tier} yet! (Current: {current_tier})", ephemeral=True)
        if tier in data['claimed_tiers']:
            return await interaction.response.send_message(
                f"You already claimed tier {tier}!", ephemeral=True)

        # Get rewards
        free_reward = FREE_TRACK_REWARDS.get(tier)
        prem_reward = PREMIUM_TRACK_REWARDS.get(tier) if data['has_premium'] else None

        rewards_given = []

        def apply_reward(reward):
            if not reward:
                return
            rtype = reward.get('type', '')
            if rtype == 'gold':
                amt = reward.get('amount', 0)
                with self.db._get_connection() as conn:
                    conn.cursor().execute("""
                        INSERT INTO user_inventory (user_id, gold) VALUES (?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET gold = gold + ?
                    """, (interaction.user.id, amt, amt))
                    conn.commit()
                rewards_given.append(f"💰 {amt:,} Gold")
            elif rtype == 'tickets':
                amt = reward.get('amount', 0)
                with self.db._get_connection() as conn:
                    conn.cursor().execute("""
                        INSERT INTO user_inventory (user_id, tickets) VALUES (?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET tickets = COALESCE(tickets,0) + ?
                    """, (interaction.user.id, amt, amt))
                    conn.commit()
                rewards_given.append(f"🎫 {amt} Tickets")
            else:
                # Cards, packs, cosmetics, XP boosts — log for manual claim
                rewards_given.append(self.bp.format_reward(reward))

        apply_reward(free_reward)
        if prem_reward:
            apply_reward(prem_reward)

        # Mark claimed
        data['claimed_tiers'].append(tier)
        self._save_claimed_tiers(interaction.user.id, data['claimed_tiers'])

        embed = discord.Embed(
            title=f"🎁 Tier {tier} Claimed!",
            description="\n".join(rewards_given) or "Reward noted!",
            color=0x2ecc71,
        )
        await interaction.response.send_message(embed=embed)



async def setup(bot):
    await bot.add_cog(BattlePassCommands(bot))
