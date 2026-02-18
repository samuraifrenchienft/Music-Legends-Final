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
        # Acknowledge the select interaction FIRST, then stop the view.
        # If stop() fires before edit_message is awaited, _run_battle resumes
        # and could call followup methods before Discord has acknowledged this interaction.
        await interaction.response.edit_message(
            content=(
                f"✅ **{tier['emoji']} {tier['name']} wager selected!** ({tier['wager_cost']}g)\n\n"
                f"Challenge sent! **Watch the channel** — your opponent has 60s to accept."
            ),
            view=None
        )
        self.view.stop()


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
        self.interaction = None  # Saved from accept callback for ephemeral followup

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.opponent_id

    @ui.button(label="Accept", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept(self, interaction: Interaction, button: ui.Button):
        self.accepted = True
        self.interaction = interaction  # Save for ephemeral champion-select prompt
        # MUST defer BEFORE stop() so the interaction is acknowledged before
        # _run_battle continues and calls followup.send() on this interaction.
        await interaction.response.defer()
        self.stop()

    @ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline(self, interaction: Interaction, button: ui.Button):
        self.accepted = False
        await interaction.response.edit_message(
            content="❌ Battle declined.", embed=None, view=None
        )
        self.stop()


class PackSelectView(ui.View):
    """Let a player pick which pack (deck) to battle with"""

    RARITY_EMOJI = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}
    TIER_EMOJI   = {"community": "📦", "gold": "🥇", "platinum": "💎"}

    def __init__(self, user_id: int, packs: list):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.selected_pack = None   # The full pack dict chosen
        self.selected_cards = []    # Cards inside the chosen pack

        options = []
        for pack in packs[:25]:
            cards = pack.get('cards', [])
            card_count = len(cards)
            tier = (pack.get('pack_tier') or 'community').lower()
            tier_e = self.TIER_EMOJI.get(tier, "📦")
            name = pack.get('pack_name') or pack.get('name') or 'Pack'
            label = name[:50]
            options.append(discord.SelectOption(
                label=f"{tier_e} {label}",
                value=pack.get('purchase_id', '') or pack.get('pack_id', ''),
                description=f"{card_count} card(s) | {(pack.get('genre') or 'Music').title()}",
            ))

        if not options:
            return

        self._packs_by_id = {
            (p.get('purchase_id') or p.get('pack_id')): p for p in packs
        }

        select = ui.Select(
            placeholder="Choose your pack to battle with...",
            options=options,
            custom_id="pack_select"
        )
        select.callback = self._select_callback
        self.add_item(select)

    async def _select_callback(self, interaction: Interaction):
        pack_id = interaction.data['values'][0]
        self.selected_pack = self._packs_by_id.get(pack_id)
        self.selected_cards = self.selected_pack.get('cards', []) if self.selected_pack else []
        # Acknowledge BEFORE stop() so Discord confirms the select interaction
        # before _run_battle resumes and fires more messages.
        await interaction.response.defer()
        self.stop()

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
        """Make sure user row and inventory row both exist; always refresh username."""
        ph = self.db._get_placeholder()
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO users (user_id, username, discord_tag) VALUES ({ph}, {ph}, {ph}) "
                f"ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, discord_tag = EXCLUDED.discord_tag",
                (user.id, user.display_name, str(user))
            )
            cursor.execute(
                f"INSERT INTO user_inventory (user_id, gold) VALUES ({ph}, 500) ON CONFLICT (user_id) DO NOTHING",
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
        if amount <= 0:
            return
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_inventory (user_id, gold)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET gold = gold + ?
            """, (user_id, amount, amount))
            conn.commit()

    def _remove_gold(self, user_id: int, amount: int) -> bool:
        """Atomic gold deduction — deducts only if balance is sufficient (no TOCTOU)."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_inventory SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
                (amount, user_id, amount)
            )
            conn.commit()
            return cursor.rowcount > 0

    def _deduct_both_wagers(self, user1_id: int, user2_id: int, amount: int) -> tuple[bool, bool]:
        """Deduct wager from both players in one transaction.
        Returns (user1_ok, user2_ok). Rolls back both if either fails."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE user_inventory SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
                (amount, user1_id, amount)
            )
            u1_ok = cursor.rowcount > 0
            cursor.execute(
                "UPDATE user_inventory SET gold = gold - ? WHERE user_id = ? AND gold >= ?",
                (amount, user2_id, amount)
            )
            u2_ok = cursor.rowcount > 0
            if u1_ok and u2_ok:
                conn.commit()
            else:
                conn.rollback()
            return u1_ok, u2_ok

    def _add_xp(self, user_id: int, xp: int):
        if xp <= 0:
            return
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

    _RARITY_BONUS = {"common": 0, "rare": 5, "epic": 10, "legendary": 20, "mythic": 35}

    def _compute_card_power(self, card: dict) -> int:
        """Compute battle power directly from card DB stats (no lossy view_count conversion).
        Formula: average of 5 stats (0-100 each) + rarity bonus → range 0-135."""
        base = ((card.get('impact', 50) or 50) +
                (card.get('skill', 50) or 50) +
                (card.get('longevity', 50) or 50) +
                (card.get('culture', 50) or 50) +
                (card.get('hype', 50) or 50)) // 5
        rarity = (card.get('rarity') or 'common').lower()
        return base + self._RARITY_BONUS.get(rarity, 0)

    def _get_support_cards(self, cards: list, champion_card_id: str, n: int = 4) -> list:
        """Return top-n cards by power, excluding the chosen champion."""
        others = [c for c in cards if c.get('card_id') != champion_card_id]
        others.sort(key=lambda c: self._compute_card_power(c), reverse=True)
        return others[:n]

    def _compute_team_power(self, champ_power: int, support_powers: list) -> int:
        """Weighted team power: champion counts double, auto-supports fill the squad.
        Formula: (champ*2 + sum(supports)) / (2 + len(supports))"""
        if not support_powers:
            return champ_power
        return (champ_power * 2 + sum(support_powers)) // (2 + len(support_powers))

    def _card_dict_to_artist(self, card: dict) -> ArtistCard:
        """Convert a DB card dict to an ArtistCard for display metadata in the battle engine.
        Power is overridden via _compute_card_power() — view_count is a placeholder only."""
        return ArtistCard(
            card_id=card.get('card_id', ''),
            artist=card.get('name', 'Unknown'),
            song=card.get('title', '') or card.get('name', 'Unknown'),
            youtube_url=card.get('youtube_url', '') or '',
            youtube_id='',
            view_count=10_000_000,  # placeholder — power is overridden in execute_battle()
            thumbnail=card.get('image_url', '') or '',
            rarity=(card.get('rarity') or 'common').lower(),
        )

    # ------------------------------------------------------------------
    # /battle
    # ------------------------------------------------------------------

    @app_commands.command(name="battle", description="Challenge another player to a card battle")
    @app_commands.describe(opponent="The player you want to battle")
    @app_commands.checks.cooldown(1, 15.0, key=lambda i: i.user.id)
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
                "❌ Battle setup failed. Please try again.", ephemeral=True)
            return

        try:
            await self._run_battle(interaction, opponent)
        except Exception as e:
            import traceback
            print(f"[BATTLE] Unhandled error: {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    "⚔️ Something went wrong during the battle. Any gold wagered has been refunded.",
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
        # Use interaction.followup.send() — works even if bot lacks SEND_MESSAGES in the channel
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
            await interaction.followup.send(
                f"Battle {'timed out' if timed_out else 'declined'} by {opponent.display_name}.")
            return

        # Deduct wager from both players atomically — either both succeed or neither does
        c_ok, o_ok = self._deduct_both_wagers(interaction.user.id, opponent.id, wager_cost)
        if not c_ok:
            await interaction.followup.send("Insufficient gold — battle cancelled.")
            return
        if not o_ok:
            await interaction.followup.send(f"{opponent.display_name} doesn't have enough gold — battle cancelled.")
            return

        # Register both players in the battle manager so is_user_in_battle() works
        self.manager.create_match(
            match_id=match_id,
            player1_id=str(interaction.user.id),
            player1_name=interaction.user.display_name,
            player2_id=str(opponent.id),
            player2_name=opponent.display_name,
            wager_tier=tier_key,
        )

        rewards_distributed = False
        try:
            rewards_distributed = await self._run_card_selection_and_battle(
                interaction, opponent, match_id, tier_key, tier, wager_cost,
                accept_view
            )
        except Exception:
            # Unexpected crash after gold was deducted — refund both players
            if not rewards_distributed:
                self._add_gold(interaction.user.id, wager_cost)
                self._add_gold(opponent.id, wager_cost)
                try:
                    await interaction.followup.send(
                        f"{interaction.user.mention} {opponent.mention} An unexpected error occurred. Wagers have been refunded."
                    )
                except Exception:
                    pass
            raise
        finally:
            self.manager.complete_match(match_id)

    async def _run_card_selection_and_battle(
        self,
        interaction: Interaction,
        opponent: discord.User,
        match_id: str,
        tier_key: str,
        tier: dict,
        wager_cost: int,
        accept_view: 'AcceptBattleView',
    ):
        """Card selection + battle resolution.
        Returns True once rewards have been distributed (used by caller to skip emergency refund)."""

        # Step 3 — Both players pick a pack to battle with
        print(f"[BATTLE] Fetching packs for both players")
        challenger_packs = self.db.get_user_purchased_packs(interaction.user.id)
        opponent_packs = self.db.get_user_purchased_packs(opponent.id)

        # Fallback: if no pack_purchases records, build a synthetic pack from their collection
        def _synth_packs(user_id):
            cards = self.db.get_user_collection(user_id)
            if not cards:
                return []
            return [{"purchase_id": f"collection_{user_id}", "pack_id": "collection",
                     "pack_name": "My Collection", "pack_tier": "community",
                     "genre": "Music", "cards": cards}]

        if not challenger_packs:
            challenger_packs = _synth_packs(interaction.user.id)
        if not opponent_packs:
            opponent_packs = _synth_packs(opponent.id)

        print(f"[BATTLE] Packs: challenger={len(challenger_packs)}, opponent={len(opponent_packs)}")

        if not challenger_packs:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            await interaction.followup.send(f"{interaction.user.display_name} has no cards or packs! Battle cancelled, wagers refunded.")
            return True
        if not opponent_packs:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            await interaction.followup.send(f"{opponent.display_name} has no cards or packs! Battle cancelled, wagers refunded.")
            return True

        # Build pack-select views
        c_view = PackSelectView(interaction.user.id, challenger_packs)
        o_view = PackSelectView(opponent.id, opponent_packs)

        # Send challenger pack picker — ephemeral so only they see it
        await interaction.followup.send(
            "📦 **Choose your pack to battle with!** The strongest card leads your squad. (60s)",
            view=c_view,
            ephemeral=True
        )

        # Send opponent pack picker — use their Accept button interaction (ephemeral only to them)
        opponent_prompt_sent = False
        if accept_view.interaction is not None:
            try:
                await accept_view.interaction.followup.send(
                    "📦 **Choose your pack to battle with!** The strongest card leads your squad. (60s)",
                    view=o_view,
                    ephemeral=True
                )
                opponent_prompt_sent = True
            except Exception as e:
                print(f"[BATTLE] Ephemeral opponent pack prompt failed: {e}")

        if not opponent_prompt_sent:
            # Fallback: public channel message with mention
            await interaction.followup.send(
                f"{opponent.mention} **Choose your pack to battle with!** The strongest card leads your squad. (60s)",
                view=o_view,
            )

        # Wait for BOTH players to pick simultaneously
        c_timed_out, o_timed_out = await asyncio.gather(c_view.wait(), o_view.wait())

        # Check selections — refund if either player didn't pick
        if c_timed_out or c_view.selected_pack is None:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            await interaction.followup.send("Battle cancelled — challenger didn't pick a pack. Wagers refunded.")
            return True
        if o_timed_out or o_view.selected_pack is None:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            await interaction.followup.send("Battle cancelled — opponent didn't pick a pack. Wagers refunded.")
            return True

        # Resolve cards from each chosen pack
        challenger_cards = c_view.selected_cards
        opponent_cards   = o_view.selected_cards

        # Fallback: if pack has no card data, pull from full collection
        if not challenger_cards:
            challenger_cards = self.db.get_user_collection(interaction.user.id)
        if not opponent_cards:
            opponent_cards = self.db.get_user_collection(opponent.id)

        if not challenger_cards or not opponent_cards:
            self._add_gold(interaction.user.id, wager_cost)
            self._add_gold(opponent.id, wager_cost)
            await interaction.followup.send("Battle cancelled — a pack had no cards. Wagers refunded.")
            return True

        # Pick champion = strongest card in each pack; rest are squad
        challenger_cards_sorted = sorted(challenger_cards, key=self._compute_card_power, reverse=True)
        opponent_cards_sorted   = sorted(opponent_cards,   key=self._compute_card_power, reverse=True)

        c_card_data = challenger_cards_sorted[0]
        o_card_data = opponent_cards_sorted[0]

        card1 = self._card_dict_to_artist(c_card_data)
        card2 = self._card_dict_to_artist(o_card_data)

        # Squad = remaining pack cards (up to 4), sorted by power
        c_supports = challenger_cards_sorted[1:5]
        o_supports = opponent_cards_sorted[1:5]

        c_champ_power = self._compute_card_power(c_card_data)
        o_champ_power = self._compute_card_power(o_card_data)
        c_support_powers = [self._compute_card_power(c) for c in c_supports]
        o_support_powers = [self._compute_card_power(c) for c in o_supports]

        # Team power: champion counts double, supports contribute to weighted average
        c_power = self._compute_team_power(c_champ_power, c_support_powers)
        o_power = self._compute_team_power(o_champ_power, o_support_powers)

        # Step 4 — Execute battle (instant; animation below is theatrical reveal)
        print(f"[BATTLE] Executing: {c_card_data.get('name')} (champ={c_champ_power}, team={c_power}) vs {o_card_data.get('name')} (champ={o_champ_power}, team={o_power})")
        result = BattleEngine.execute_battle(card1, card2, tier_key, p1_override=c_power, p2_override=o_power)
        p1 = result["player1"]
        p2 = result["player2"]
        print(f"[BATTLE] Result: winner={result['winner']}, p1_final={p1['final_power']}, p2_final={p2['final_power']}")

        # Step 5 — Distribute rewards BEFORE animation so a Discord API failure
        # can't orphan rewards after gold has already been deducted.
        self._add_gold(interaction.user.id, p1["gold_reward"])
        self._add_gold(opponent.id, p2["gold_reward"])
        self._add_xp(interaction.user.id, p1["xp_reward"])
        self._add_xp(opponent.id, p2["xp_reward"])
        rewards_distributed = True  # Signal to caller: do NOT refund on any later exception

        try:
            if result["winner"] == 1:
                self._update_battle_stats(interaction.user.id, opponent.id)
            elif result["winner"] == 2:
                self._update_battle_stats(opponent.id, interaction.user.id)
            else:
                with self.db._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE users SET total_battles = total_battles + 1 WHERE user_id IN (?, ?)",
                                   (interaction.user.id, opponent.id))
                    conn.commit()
        except Exception as e:
            print(f"[BATTLE] Warning: battle stats update failed (non-critical): {e}")

        # --- Battle Animation ---
        _re = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "⭐", "mythic": "🔴"}
        c_rarity_e = _re.get((c_card_data.get('rarity') or 'common').lower(), "⚪")
        o_rarity_e = _re.get((o_card_data.get('rarity') or 'common').lower(), "⚪")
        c_name = c_card_data.get('name', 'Unknown')
        o_name = o_card_data.get('name', 'Unknown')
        c_title = c_card_data.get('title', '') or ''
        o_title = o_card_data.get('title', '') or ''
        c_pack_name = c_view.selected_pack.get('pack_name') or 'Pack' if c_view.selected_pack else 'Pack'
        o_pack_name = o_view.selected_pack.get('pack_name') or 'Pack' if o_view.selected_pack else 'Pack'

        def _squad_lines(supports: list) -> str:
            lines = []
            for s in supports:
                re = _re.get((s.get('rarity') or 'common').lower(), "⚪")
                lines.append(f"{re} {s.get('name', 'Unknown')} ({self._compute_card_power(s)})")
            return "\n".join(lines) if lines else "_No squad members_"

        # Phase 1 — Battle Start
        start_embed = discord.Embed(
            title="⚔️ Battle Commencing!",
            description=f"**{interaction.user.display_name}** vs **{opponent.display_name}**",
            color=0xf39c12,
        )
        start_embed.add_field(name=f"{tier['emoji']} Wager", value=f"{wager_cost}g ({tier['name']})", inline=True)
        start_embed.add_field(name="📦 Packs", value=f"{c_pack_name} vs {o_pack_name}", inline=True)
        start_embed.set_footer(text="Champions stepping forward...")
        anim_msg = await interaction.followup.send(embed=start_embed)
        await asyncio.sleep(1.5)

        # Phase 2a — Champion Reveal
        champ_embed = discord.Embed(title="🏆 Champions Revealed!", color=0x9b59b6)
        champ_embed.add_field(
            name=f"🔵 {interaction.user.display_name} — {c_pack_name}",
            value=f"{c_rarity_e} **{c_name}**" + (f" — {c_title}" if c_title else "") + f"\nPower: **{c_champ_power}**",
            inline=True,
        )
        champ_embed.add_field(name="⚡", value="**VS**", inline=True)
        champ_embed.add_field(
            name=f"🔴 {opponent.display_name} — {o_pack_name}",
            value=f"{o_rarity_e} **{o_name}**" + (f" — {o_title}" if o_title else "") + f"\nPower: **{o_champ_power}**",
            inline=True,
        )
        champ_embed.set_footer(text="Squads assembling...")
        await anim_msg.edit(embed=champ_embed)
        await asyncio.sleep(1.5)

        # Phase 2b — Full Squad Reveal
        squad_embed = discord.Embed(title="🎵 Full Squads!", color=0x3498db)
        squad_embed.add_field(
            name=f"🔵 {interaction.user.display_name} [{c_pack_name}] — Team Power: {c_power}",
            value=f"**Champion:** {c_rarity_e} {c_name} ({c_champ_power})\n**Squad:**\n{_squad_lines(c_supports)}",
            inline=True,
        )
        squad_embed.add_field(name="⚡", value="**VS**", inline=True)
        squad_embed.add_field(
            name=f"🔴 {opponent.display_name} [{o_pack_name}] — Team Power: {o_power}",
            value=f"**Champion:** {o_rarity_e} {o_name} ({o_champ_power})\n**Squad:**\n{_squad_lines(o_supports)}",
            inline=True,
        )
        squad_embed.set_footer(text="Powers clashing...")
        await anim_msg.edit(embed=squad_embed)
        await asyncio.sleep(2.0)

        # Phase 3 — Critical Hit reveal (if any)
        if p1['critical_hit'] or p2['critical_hit']:
            crit_embed = discord.Embed(title="💥 CRITICAL HIT!", color=0xe74c3c)
            crit_lines = []
            if p1['critical_hit']:
                crit_lines.append(f"🔵 **{interaction.user.display_name}**'s team lands a CRIT! {c_power} → **{p1['final_power']}** ⚡")
            if p2['critical_hit']:
                crit_lines.append(f"🔴 **{opponent.display_name}**'s team lands a CRIT! {o_power} → **{p2['final_power']}** ⚡")
            crit_embed.description = "\n".join(crit_lines)
            crit_embed.set_footer(text="Calculating winner...")
            await anim_msg.edit(embed=crit_embed)
            await asyncio.sleep(1.5)

        # Phase 4 — Final Result
        result_embed = BattleEngine.create_battle_embed(result, interaction.user.display_name, opponent.display_name)
        await anim_msg.edit(embed=result_embed)

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

        # Record to battle_history table
        try:
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
                'player1_critical': p1.get('critical_hit', False),
                'player2_critical': p2.get('critical_hit', False),
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

        return rewards_distributed  # True — tells caller not to issue an emergency refund

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

    async def on_app_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏱️ Slow down! You can battle again in **{error.retry_after:.0f}s**.",
                ephemeral=True
            )
        else:
            raise error


async def setup(bot):
    await bot.add_cog(BattleCommands(bot))
