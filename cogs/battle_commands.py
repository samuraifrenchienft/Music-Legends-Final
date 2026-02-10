# cogs/battle_commands.py
"""
Battle Commands - /battle, /battle_stats
Lets users challenge each other to card battles with wagers
"""

import asyncio
import discord
import sqlite3
import random
import uuid
from datetime import datetime
from discord.ext import commands
from discord import Interaction, app_commands, ui
from typing import Optional

from battle_engine import (
    BattleManager, BattleEngine, BattleWagerConfig,
    BattleCard, PlayerState, MatchState, BattleStatus
)
from discord_cards import ArtistCard
from database import DatabaseManager, get_db
from config.economy import BATTLE_WAGERS, calculate_battle_rewards


# Shared battle manager (per-bot instance)
_battle_manager = BattleManager()


class WagerSelect(ui.Select):
    """Dropdown to pick wager tier"""

    def __init__(self):
        options = []
        for key, tier in BattleWagerConfig.TIERS.items():
            options.append(discord.SelectOption(
                label=f"{tier['emoji']} {tier['name']} — {tier['wager_cost']}g",
                value=key,
                description=f"Win: {tier['winner_gold']}g | Lose: {tier['loser_gold']}g"
            ))
        super().__init__(placeholder="Choose wager tier...", options=options, custom_id="wager_select")

    async def callback(self, interaction: Interaction):
        self.view.selected_tier = self.values[0]
        tier = BattleWagerConfig.get_tier(self.values[0])
        self.view.stop()
        # Update the ephemeral message so challenger knows what happens next
        await interaction.response.edit_message(
            content=(
                f"✅ **{tier['emoji']} {tier['name']} wager selected!** ({tier['wager_cost']}g)\n\n"
                f"Challenge sent! **Watch the channel** — your opponent has 60s to accept."
            ),
            view=None
        )


class WagerSelectView(ui.View):
    """View containing wager dropdown"""

    def __init__(self, challenger_id: int):
        super().__init__(timeout=30)
        self.challenger_id = challenger_id
        self.selected_tier = None
        self.add_item(WagerSelect())

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.challenger_id


class AcceptBattleView(ui.View):
    """Accept / Decline buttons shown to the opponent"""

    def __init__(self, opponent_id: int, match_id: str):
        super().__init__(timeout=60)
        self.opponent_id = opponent_id
        self.match_id = match_id
        self.accepted = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.opponent_id

    @ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept(self, interaction: Interaction, button: ui.Button):
        self.accepted = True
        self.stop()
        await interaction.response.defer()

    @ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline(self, interaction: Interaction, button: ui.Button):
        self.accepted = False
        self.stop()
        await interaction.response.defer()


class CardSelectView(ui.View):
    """Let a player pick a card from their collection"""

    def __init__(self, user_id: int, cards: list):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.selected_card = None

        options = []
        for card in cards[:25]:  # Discord limit
            rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣",
                            "legendary": "⭐", "mythic": "🔴"}.get(
                (card.get('rarity') or 'common').lower(), "⚪")
            name = card.get('name', 'Unknown')
            title = card.get('title', '')
            label = f"{name} — {title}" if title else name
            if len(label) > 50:
                label = label[:47] + "..."
            power = (card.get('impact', 50) or 50) + (card.get('skill', 50) or 50) + \
                    (card.get('longevity', 50) or 50) + (card.get('culture', 50) or 50) + \
                    (card.get('hype', 50) or 50)
            power_avg = power // 5
            options.append(discord.SelectOption(
                label=label,
                value=card.get('card_id', ''),
                description=f"{rarity_emoji} {(card.get('rarity') or 'common').title()} • Power: {power_avg}",
            ))

        if not options:
            return

        select = ui.Select(placeholder="Choose your battle card...", options=options, custom_id="card_select")
        select.callback = self._select_callback
        self.add_item(select)

    async def _select_callback(self, interaction: Interaction):
        self.selected_card = interaction.data['values'][0]
        self.stop()
        await interaction.response.defer()

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id


class BattleCommands(commands.Cog):
    """Battle system commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = get_db()
        self.manager = _battle_manager

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_user(self, user: discord.User):
        """Make sure user row and inventory row both exist"""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, discord_tag) VALUES (?, ?, ?)",
                (user.id, user.display_name, str(user))
            )
            # Ensure inventory row exists with 500 starting gold (schema default)
            cursor.execute(
                "INSERT OR IGNORE INTO user_inventory (user_id, gold) VALUES (?, 500)",
                (user.id,)
            )
            conn.commit()

    def _get_gold(self, user_id: int) -> int:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT gold FROM user_inventory WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row and row[0] else 0

    def _add_gold(self, user_id: int, amount: int):
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_inventory (user_id, gold)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET gold = gold + ?
            """, (user_id, amount, amount))
            conn.commit()

    def _remove_gold(self, user_id: int, amount: int) -> bool:
        gold = self._get_gold(user_id)
        if gold < amount:
            return False
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_inventory SET gold = gold - ? WHERE user_id = ?",
                (amount, user_id)
            )
            conn.commit()
        return True

    def _add_xp(self, user_id: int, xp: int):
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_inventory (user_id, xp)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET xp = COALESCE(xp, 0) + ?
            """, (user_id, xp, xp))
            conn.commit()

    def _update_battle_stats(self, winner_id: int, loser_id: int):
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET total_battles = total_battles + 1, wins = wins + 1 WHERE user_id = ?",
                (winner_id,)
            )
            cursor.execute(
                "UPDATE users SET total_battles = total_battles + 1, losses = losses + 1 WHERE user_id = ?",
                (loser_id,)
            )
            conn.commit()

    def _card_dict_to_artist(self, card: dict) -> ArtistCard:
        """Convert a DB card dict to an ArtistCard for the battle engine"""
        power_avg = ((card.get('impact', 50) or 50) +
                     (card.get('skill', 50) or 50) +
                     (card.get('longevity', 50) or 50) +
                     (card.get('culture', 50) or 50) +
                     (card.get('hype', 50) or 50)) // 5
        # Map power_avg to a fake view_count so ArtistCard._calculate_power works
        view_map = {90: 1_500_000_000, 80: 700_000_000, 70: 200_000_000,
                    60: 80_000_000, 50: 30_000_000}
        fake_views = 5_000_000
        for threshold, views in sorted(view_map.items(), reverse=True):
            if power_avg >= threshold:
                fake_views = views
                break
        return ArtistCard(
            card_id=card.get('card_id', ''),
            artist=card.get('name', 'Unknown'),
            song=card.get('title', '') or card.get('name', 'Unknown'),
            youtube_url=card.get('youtube_url', '') or '',
            youtube_id='',
            view_count=fake_views,
            thumbnail=card.get('image_url', '') or '',
            rarity=(card.get('rarity') or 'common').lower(),
        )

    # ------------------------------------------------------------------
    # /battle
    # ------------------------------------------------------------------

    @app_commands.command(name="battle", description="Challenge another player to a card battle")
    @app_commands.describe(opponent="The player you want to battle")
    async def battle_command(self, interaction: Interaction, opponent: discord.User):
        """Full battle flow: choose wager -> opponent accepts -> both pick cards -> resolve"""

        # Validation
        if opponent.id == interaction.user.id:
            return await interaction.response.send_message("You can't battle yourself!", ephemeral=True)
        if opponent.bot:
            return await interaction.response.send_message("You can't battle a bot!", ephemeral=True)
        if self.manager.is_user_in_battle(str(interaction.user.id)):
            return await interaction.response.send_message("You're already in a battle!", ephemeral=True)
        if self.manager.is_user_in_battle(str(opponent.id)):
            return await interaction.response.send_message(f"{opponent.display_name} is already in a battle!", ephemeral=True)

        try:
            self._ensure_user(interaction.user)
            self._ensure_user(opponent)
        except Exception as e:
            import traceback
            print(f"[BATTLE] _ensure_user failed: {e}")
            traceback.print_exc()
            await interaction.response.send_message(
                f"❌ Battle setup failed: `{type(e).__name__}: {str(e)[:100]}`", ephemeral=True)
            return

        try:
            await self._run_battle(interaction, opponent)
        except Exception as e:
            import traceback
            print(f"[BATTLE] Unhandled error: {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"⚔️ Battle encountered an error: `{type(e).__name__}: {str(e)[:150]}`\n"
                    f"Any gold wagered has been refunded.",
                    ephemeral=True
                )
            except Exception:
                pass

    async def _run_battle(self, interaction: Interaction, opponent: discord.User):
        """Inner battle logic — wrapped by battle_command for error handling"""

        # Step 1 — Challenger picks wager tier
        print(f"[BATTLE] Starting battle: {interaction.user} vs {opponent}")
        wager_view = WagerSelectView(interaction.user.id)
        await interaction.response.send_message("Choose a wager tier:", view=wager_view, ephemeral=True)
        timed_out = await wager_view.wait()
        if timed_out or wager_view.selected_tier is None:
            return await interaction.followup.send("Battle cancelled — no tier selected.", ephemeral=True)

        tier_key = wager_view.selected_tier
        tier = BattleWagerConfig.get_tier(tier_key)
        wager_cost = tier["wager_cost"]
        print(f"[BATTLE] Tier selected: {tier_key} (wager={wager_cost}g)")

        # Check both players have enough gold
        challenger_gold = self._get_gold(interaction.user.id)
        opponent_gold = self._get_gold(opponent.id)
        print(f"[BATTLE] Gold check: challenger={challenger_gold}g, opponent={opponent_gold}g, need={wager_cost}g")
        if challenger_gold < wager_cost:
            return await interaction.followup.send(
                f"You don't have enough gold! Need {wager_cost}g, you have {challenger_gold}g.", ephemeral=True)
        if opponent_gold < wager_cost:
            return await interaction.followup.send(
                f"{opponent.display_name} doesn't have enough gold ({wager_cost}g required).", ephemeral=True)

        # Step 2 — Send challenge to opponent
        match_id = f"battle_{uuid.uuid4().hex[:8]}"
        accept_view = AcceptBattleView(opponent.id, match_id)

        challenge_embed = discord.Embed(
            title=f"{tier['emoji']} Battle Challenge!",
            description=(
                f"**{interaction.user.display_name}** challenges **{opponent.display_name}**!\n\n"
                f"**Wager:** {wager_cost}g ({tier['name']})\n"
                f"**Winner gets:** {tier['winner_gold']}g + {tier['winner_xp']} XP\n"
                f"**Loser gets:** {tier['loser_gold']}g + {tier['loser_xp']} XP"
            ),
            color=0xf39c12
        )
        challenge_embed.set_footer(text=f"{opponent.display_name} — accept or decline within 60s")

        await interaction.followup.send(
            content=f"{opponent.mention}",
            embed=challenge_embed,
            view=accept_view
        )

        timed_out = await accept_view.wait()
        if timed_out or not accept_view.accepted:
            return await interaction.followup.send(
                f"Battle {'timed out' if timed_out else 'declined'} by {opponent.display_name}.")

        # Deduct wager from both
        if not self._remove_gold(interaction.user.id, wager_cost):
            return await interaction.followup.send("Insufficient gold — battle cancelled.")
        if not self._remove_gold(opponent.id, wager_cost):
            self._add_gold(interaction.user.id, wager_cost)  # refund
            return await interaction.followup.send(f"{opponent.display_name} has insufficient gold — battle cancelled.")

        # Step 3 — Both players pick cards
        print(f"[BATTLE] Fetching collections for both players")
        challenger_cards = self.db.get_user_collection(interaction.user.id)
        opponent_cards = self.db.get_user_collection(opponent.id)
        print(f"[BATTLE] Collections: challenger={len(challenger_cards)} cards, opponent={len(opponent_cards)} cards")

        if not challenger_cards:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            return await interaction.followup.send(f"{interaction.user.display_name} has no cards! Battle cancelled, wagers refunded.")
        if not opponent_cards:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            return await interaction.followup.send(f"{opponent.display_name} has no cards! Battle cancelled, wagers refunded.")

        # Send BOTH card select prompts at the same time (non-ephemeral so each player can see theirs)
        c_view = CardSelectView(interaction.user.id, challenger_cards)
        o_view = CardSelectView(opponent.id, opponent_cards)

        await interaction.followup.send(
            f"{interaction.user.mention} ⚔️ **You have 60s to pick your battle card!**",
            view=c_view
        )
        await interaction.followup.send(
            f"{opponent.mention} ⚔️ **You have 60s to pick your battle card!**",
            view=o_view
        )

        # Wait for BOTH players to pick simultaneously
        c_timed_out, o_timed_out = await asyncio.gather(c_view.wait(), o_view.wait())

        # Check selections
        if c_timed_out or c_view.selected_card is None:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            return await interaction.followup.send("Battle cancelled — challenger didn't pick a card. Wagers refunded.")
        if o_timed_out or o_view.selected_card is None:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            return await interaction.followup.send("Battle cancelled — opponent didn't pick a card. Wagers refunded.")

        # Resolve card data
        c_card_data = next((c for c in challenger_cards if c.get('card_id') == c_view.selected_card), challenger_cards[0])
        o_card_data = next((c for c in opponent_cards if c.get('card_id') == o_view.selected_card), opponent_cards[0])

        card1 = self._card_dict_to_artist(c_card_data)
        card2 = self._card_dict_to_artist(o_card_data)

        # Step 4 — Execute battle
        print(f"[BATTLE] Executing: {c_card_data.get('name')} vs {o_card_data.get('name')}")
        result = BattleEngine.execute_battle(card1, card2, tier_key)
        print(f"[BATTLE] Result: winner={result['winner']}, p1_power={result['player1']['final_power']}, p2_power={result['player2']['final_power']}")
        result_embed = BattleEngine.create_battle_embed(
            result, interaction.user.display_name, opponent.display_name)

        # Step 5 — Distribute rewards
        p1 = result["player1"]
        p2 = result["player2"]

        self._add_gold(interaction.user.id, p1["gold_reward"])
        self._add_gold(opponent.id, p2["gold_reward"])
        self._add_xp(interaction.user.id, p1["xp_reward"])
        self._add_xp(opponent.id, p2["xp_reward"])

        # Update win/loss stats
        if result["winner"] == 1:
            self._update_battle_stats(interaction.user.id, opponent.id)
        elif result["winner"] == 2:
            self._update_battle_stats(opponent.id, interaction.user.id)
        else:
            # Tie — just increment total_battles for both
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET total_battles = total_battles + 1 WHERE user_id IN (?, ?)",
                               (interaction.user.id, opponent.id))
                conn.commit()

        # Record match in DB
        winner_id = interaction.user.id if result["winner"] == 1 else (
            opponent.id if result["winner"] == 2 else None)
        try:
            self.db.record_match({
                'match_id': match_id,
                'player_a_id': interaction.user.id,
                'player_b_id': opponent.id,
                'winner_id': winner_id or 0,
                'final_score_a': p1["final_power"],
                'final_score_b': p2["final_power"],
                'match_type': tier_key
            })
        except Exception as e:
            print(f"Warning: could not record match: {e}")

        await interaction.followup.send(embed=result_embed)

        # Record to battle_history table
        try:
            import uuid
            battle_id = f"battle_{uuid.uuid4().hex[:8]}"
            self.db.record_battle({
                'battle_id': battle_id,
                'player1_id': interaction.user.id,
                'player2_id': opponent.id,
                'player1_card_id': c_card_data.get('card_id', ''),
                'player2_card_id': o_card_data.get('card_id', ''),
                'winner': result['winner'],  # 0=tie, 1=player1, 2=player2
                'player1_power': p1['final_power'],
                'player2_power': p2['final_power'],
                'player1_critical': p1.get('critical', False),
                'player2_critical': p2.get('critical', False),
                'wager_tier': tier_key,
                'wager_amount': wager_cost,
                'player1_gold_reward': p1['gold_reward'],
                'player2_gold_reward': p2['gold_reward'],
                'player1_xp_reward': p1['xp_reward'],
                'player2_xp_reward': p2['xp_reward'],
            })
        except Exception as e:
            print(f"Warning: could not record battle history: {e}")

        # Log to changelog
        try:
            from services.changelog_manager import log_user_action
            log_user_action(
                f"battle_{tier_key}",
                interaction.user.id,
                {'opponent': opponent.id, 'winner': winner_id, 'tier': tier_key}
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # /battle_stats
    # ------------------------------------------------------------------

    @app_commands.command(name="battle_stats", description="View your battle record")
    @app_commands.describe(user="Player to view stats for (default: yourself)")
    async def battle_stats_command(self, interaction: Interaction, user: Optional[discord.User] = None):
        target = user or interaction.user
        stats = self.db.get_user_stats(target.id)

        if not stats:
            return await interaction.response.send_message(
                f"{target.display_name} hasn't played yet!", ephemeral=True)

        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        total = stats.get('total_battles', 0)
        win_rate = stats.get('win_rate', 0)

        embed = discord.Embed(
            title=f"⚔️ Battle Stats — {target.display_name}",
            color=0x3498db
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🏆 Wins", value=str(wins), inline=True)
        embed.add_field(name="💀 Losses", value=str(losses), inline=True)
        embed.add_field(name="🎮 Total", value=str(total), inline=True)
        embed.add_field(name="📈 Win Rate", value=f"{win_rate:.1f}%", inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(BattleCommands(bot))
