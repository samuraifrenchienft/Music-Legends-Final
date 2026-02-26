"""
Trade Commands Cog — /trade @user

Flow:
  1. Initiator runs /trade @opponent
  2. Both players are shown a card-picker + optional gold offer
  3. Both must confirm before the atomic swap executes via db.complete_trade()
  4. Either player can cancel at any time during negotiation

Security:
  - Input validated: cards must be owned, gold must be ≤ balance, no self-trades
  - Atomic DB swap: either everything completes or nothing does
  - 5-minute timeout with auto-cancel
"""

import discord
from discord import app_commands, ui, Interaction
from discord.ext import commands
import asyncio
import json

from database import get_db

TRADE_TIMEOUT = 300  # 5 minutes


# ──────────────────────────────────────────────
# Helper: card label for select menus
# ──────────────────────────────────────────────

def _card_label(card: dict) -> str:
    rarity_icons = {
        'mythic': '🔮', 'legendary': '⭐', 'epic': '💜',
        'rare': '💙', 'common': '⚪'
    }
    icon = rarity_icons.get(card.get('rarity', 'common'), '🃏')
    name = card.get('name') or card.get('artist_name') or 'Unknown'
    return f"{icon} {name[:50]}"


# ──────────────────────────────────────────────
# Card-picker Select (up to 5 cards at once)
# ──────────────────────────────────────────────

class CardPickerSelect(ui.Select):
    def __init__(self, collection: list):
        options = [
            discord.SelectOption(
                label=_card_label(c),
                value=c['card_id'],
                description=f"Rarity: {c.get('rarity','?')} | ID: {c['card_id'][:8]}"
            )
            for c in collection[:25]  # Discord limit
        ]
        super().__init__(
            placeholder="Pick cards to offer (optional, up to 5)",
            min_values=0,
            max_values=min(5, len(options)),
            options=options
        )

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()


# ──────────────────────────────────────────────
# Trade Offer View (one per player)
# ──────────────────────────────────────────────

class TradeOfferView(ui.View):
    """Let a player choose cards + gold to offer, then confirm."""

    def __init__(self, user: discord.Member, collection: list, gold_balance: int):
        super().__init__(timeout=TRADE_TIMEOUT)
        self.user = user
        self.gold_balance = gold_balance
        self.selected_cards: list[str] = []
        self.gold_offer: int = 0
        self.confirmed: bool = False
        self.cancelled: bool = False

        if collection:
            self._picker = CardPickerSelect(collection)
            self.add_item(self._picker)
        else:
            self._picker = None

    # ── Confirm button ──────────────────────────
    @ui.button(label="Confirm Offer", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't your trade!", ephemeral=True)
            return
        # Capture selections
        if self._picker:
            self.selected_cards = self._picker.values or []
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    # ── Add gold button ──────────────────────────
    @ui.button(label="Add Gold", style=discord.ButtonStyle.primary, emoji="💰")
    async def add_gold(self, interaction: Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't your trade!", ephemeral=True)
            return
        await interaction.response.send_modal(GoldModal(self))

    # ── Cancel button ──────────────────────────
    @ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: Interaction, button: ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("This isn't your trade!", ephemeral=True)
            return
        self.cancelled = True
        await interaction.response.defer()
        self.stop()


# ──────────────────────────────────────────────
# Gold Modal
# ──────────────────────────────────────────────

class GoldModal(ui.Modal, title="Add Gold to Offer"):
    amount = ui.TextInput(
        label="Gold amount (0 to skip)",
        placeholder="e.g. 500",
        min_length=1,
        max_length=7,
        required=True
    )

    def __init__(self, parent_view: TradeOfferView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: Interaction):
        raw = self.amount.value.strip()
        if not raw.isdigit():
            await interaction.response.send_message("Enter a whole number.", ephemeral=True)
            return
        value = int(raw)
        if value < 0:
            await interaction.response.send_message("Gold must be 0 or more.", ephemeral=True)
            return
        if value > self.parent_view.gold_balance:
            await interaction.response.send_message(
                f"You only have {self.parent_view.gold_balance:,} gold.", ephemeral=True
            )
            return
        self.parent_view.gold_offer = value
        await interaction.response.send_message(
            f"Gold offer set to **{value:,}**.", ephemeral=True
        )


# ──────────────────────────────────────────────
# Final Confirmation View (both players see this)
# ──────────────────────────────────────────────

class FinalConfirmView(ui.View):
    """Both players must press Confirm to execute the trade."""

    def __init__(self, initiator_id: int, receiver_id: int):
        super().__init__(timeout=60)
        self.initiator_confirmed = False
        self.receiver_confirmed = False
        self.cancelled = False
        self.initiator_id = initiator_id
        self.receiver_id = receiver_id

    @property
    def both_confirmed(self):
        return self.initiator_confirmed and self.receiver_confirmed

    @ui.button(label="Confirm Trade", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: Interaction, button: ui.Button):
        uid = interaction.user.id
        if uid == self.initiator_id:
            self.initiator_confirmed = True
        elif uid == self.receiver_id:
            self.receiver_confirmed = True
        else:
            await interaction.response.send_message("You're not part of this trade.", ephemeral=True)
            return
        await interaction.response.defer()
        if self.both_confirmed:
            self.stop()

    @ui.button(label="Cancel Trade", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel(self, interaction: Interaction, button: ui.Button):
        uid = interaction.user.id
        if uid not in (self.initiator_id, self.receiver_id):
            await interaction.response.send_message("You're not part of this trade.", ephemeral=True)
            return
        self.cancelled = True
        await interaction.response.defer()
        self.stop()


# ──────────────────────────────────────────────
# Trade Cog
# ──────────────────────────────────────────────

class TradeCog(commands.Cog, name="Trade"):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _db(self):
        return get_db()

    def _get_gold(self, user_id: int) -> int:
        economy = self._db().get_user_economy(user_id)
        return economy.get('gold', 0) if economy else 0

    def _get_collection(self, user_id: int) -> list:
        return self._db().get_user_collection(user_id)

    def _ensure_user(self, user: discord.Member):
        db = self._db()
        db.ensure_user_exists(user.id, user.display_name)

    # ── /trade ───────────────────────────────────
    @app_commands.command(name="trade", description="Offer a trade to another player")
    @app_commands.describe(opponent="The player you want to trade with")
    async def trade(self, interaction: Interaction, opponent: discord.Member):
        initiator = interaction.user

        # ── Basic validation ──────────────────────
        if opponent.id == initiator.id:
            await interaction.response.send_message("You can't trade with yourself.", ephemeral=True)
            return
        if opponent.bot:
            await interaction.response.send_message("You can't trade with a bot.", ephemeral=True)
            return

        # ── Ensure both users exist in DB ─────────
        self._ensure_user(initiator)
        self._ensure_user(opponent)

        await interaction.response.send_message(
            f"⚙️ Setting up trade between {initiator.mention} and {opponent.mention}…",
            ephemeral=False
        )

        # ── Fetch collections & balances ──────────
        init_collection = self._get_collection(initiator.id)
        recv_collection = self._get_collection(opponent.id)
        init_gold = self._get_gold(initiator.id)
        recv_gold = self._get_gold(opponent.id)

        # ── Initiator offer view ──────────────────
        init_embed = discord.Embed(
            title="📦 Your Trade Offer",
            description=(
                f"Trading with **{opponent.display_name}**\n"
                f"Your gold: **{init_gold:,}**\n\n"
                "Select cards and/or add gold, then press **Confirm Offer**."
            ),
            color=discord.Color.blue()
        )
        init_view = TradeOfferView(initiator, init_collection, init_gold)

        try:
            await initiator.send(embed=init_embed, view=init_view)
        except discord.Forbidden:
            await interaction.followup.send(
                f"{initiator.mention}, I couldn't DM you. Please enable DMs to trade.", ephemeral=True
            )
            return

        # ── Receiver offer view ───────────────────
        recv_embed = discord.Embed(
            title="📦 Your Trade Offer",
            description=(
                f"**{initiator.display_name}** wants to trade with you!\n"
                f"Your gold: **{recv_gold:,}**\n\n"
                "Select cards and/or add gold, then press **Confirm Offer**."
            ),
            color=discord.Color.orange()
        )
        recv_view = TradeOfferView(opponent, recv_collection, recv_gold)

        try:
            await opponent.send(embed=recv_embed, view=recv_view)
        except discord.Forbidden:
            await interaction.followup.send(
                f"{opponent.mention} has DMs disabled — trade cancelled.", ephemeral=True
            )
            return

        await interaction.followup.send(
            f"📬 Both players have been DMed. Each player has {TRADE_TIMEOUT // 60} minutes to confirm their offer.",
            ephemeral=False
        )

        # ── Wait for both players (parallel) ─────
        await asyncio.gather(init_view.wait(), recv_view.wait())

        # ── Handle cancellations / timeouts ──────
        if init_view.cancelled or recv_view.cancelled:
            canceller = initiator if init_view.cancelled else opponent
            await interaction.followup.send(
                f"❌ Trade cancelled by {canceller.mention}."
            )
            return

        if not init_view.confirmed:
            await interaction.followup.send(
                f"⏰ Trade timed out — {initiator.mention} did not confirm in time."
            )
            return

        if not recv_view.confirmed:
            await interaction.followup.send(
                f"⏰ Trade timed out — {opponent.mention} did not confirm in time."
            )
            return

        # ── Validate card ownership (re-check from DB) ──
        init_owned_ids = {c['card_id'] for c in self._get_collection(initiator.id)}
        recv_owned_ids = {c['card_id'] for c in self._get_collection(opponent.id)}

        if any(cid not in init_owned_ids for cid in init_view.selected_cards):
            await interaction.followup.send(
                f"❌ {initiator.mention} no longer owns one of the offered cards. Trade cancelled."
            )
            return

        if any(cid not in recv_owned_ids for cid in recv_view.selected_cards):
            await interaction.followup.send(
                f"❌ {opponent.mention} no longer owns one of the offered cards. Trade cancelled."
            )
            return

        # ── Validate gold balances (re-check) ────
        init_gold_now = self._get_gold(initiator.id)
        recv_gold_now = self._get_gold(opponent.id)

        if init_view.gold_offer > init_gold_now:
            await interaction.followup.send(
                f"❌ {initiator.mention} no longer has enough gold. Trade cancelled."
            )
            return

        if recv_view.gold_offer > recv_gold_now:
            await interaction.followup.send(
                f"❌ {opponent.mention} no longer has enough gold. Trade cancelled."
            )
            return

        # ── Build summary embed ───────────────────
        def cards_summary(card_ids: list, collection: list) -> str:
            lookup = {c['card_id']: c for c in collection}
            if not card_ids:
                return "_No cards_"
            lines = []
            for cid in card_ids:
                card = lookup.get(cid)
                if card:
                    lines.append(f"• {_card_label(card)}")
                else:
                    lines.append(f"• {cid[:12]}…")
            return "\n".join(lines)

        init_cards_text = cards_summary(init_view.selected_cards, init_collection)
        recv_cards_text = cards_summary(recv_view.selected_cards, recv_collection)

        summary_embed = discord.Embed(
            title="🤝 Trade Summary — Final Confirmation",
            color=discord.Color.gold()
        )
        summary_embed.add_field(
            name=f"{initiator.display_name} offers:",
            value=f"{init_cards_text}\n💰 {init_view.gold_offer:,} gold",
            inline=True
        )
        summary_embed.add_field(
            name=f"{opponent.display_name} offers:",
            value=f"{recv_cards_text}\n💰 {recv_view.gold_offer:,} gold",
            inline=True
        )
        summary_embed.set_footer(text="Both players must confirm within 60 seconds.")

        confirm_view = FinalConfirmView(initiator.id, opponent.id)
        summary_msg = await interaction.followup.send(
            content=f"{initiator.mention} {opponent.mention}",
            embed=summary_embed,
            view=confirm_view
        )

        await confirm_view.wait()

        # ── Final cancel ──────────────────────────
        if confirm_view.cancelled or not confirm_view.both_confirmed:
            reason = "cancelled" if confirm_view.cancelled else "timed out"
            await summary_msg.edit(
                content=f"❌ Trade {reason}.",
                embed=None,
                view=None
            )
            return

        # ── Execute atomic swap ───────────────────
        db = self._db()
        trade_id = db.create_trade(
            initiator_user_id=initiator.id,
            receiver_user_id=opponent.id,
            initiator_cards=init_view.selected_cards,
            receiver_cards=recv_view.selected_cards,
            gold_from_initiator=init_view.gold_offer,
            gold_from_receiver=recv_view.gold_offer,
        )

        if not trade_id:
            await summary_msg.edit(
                content="❌ Failed to create trade record. Please try again.",
                embed=None,
                view=None
            )
            return

        success = db.complete_trade(trade_id)

        if success:
            result_embed = discord.Embed(
                title="✅ Trade Complete!",
                color=discord.Color.green()
            )
            result_embed.add_field(
                name=f"{initiator.display_name} received:",
                value=f"{recv_cards_text}\n💰 {recv_view.gold_offer:,} gold",
                inline=True
            )
            result_embed.add_field(
                name=f"{opponent.display_name} received:",
                value=f"{init_cards_text}\n💰 {init_view.gold_offer:,} gold",
                inline=True
            )
            await summary_msg.edit(
                content=f"🎉 {initiator.mention} {opponent.mention}",
                embed=result_embed,
                view=None
            )
        else:
            # Roll back trade status (already None or 'pending' — complete_trade handles rollback)
            db.cancel_trade(trade_id, reason="execution_failed")
            await summary_msg.edit(
                content="❌ Trade execution failed. No changes were made. Please try again.",
                embed=None,
                view=None
            )

    # ── /trade_history ────────────────────────
    @app_commands.command(name="trade_history", description="View your recent trade history")
    async def trade_history(self, interaction: Interaction):
        await interaction.response.defer()
        db = self._db()
        ph = db._get_placeholder()
        uid = interaction.user.id

        try:
            conn = db._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    f"""SELECT trade_id, initiator_user_id, receiver_user_id,
                               initiator_cards, receiver_cards,
                               gold_from_initiator, gold_from_receiver, trade_date
                        FROM trade_history
                        WHERE initiator_user_id = {ph} OR receiver_user_id = {ph}
                        ORDER BY trade_date DESC
                        LIMIT 10""",
                    (uid, uid)
                )
                rows = cursor.fetchall()
                columns = [d[0] for d in cursor.description]
                trades = [dict(zip(columns, r)) for r in rows]
            finally:
                conn.close()
        except Exception as e:
            print(f"[trade_history] DB error: {e}")
            await interaction.followup.send("Failed to fetch trade history.", ephemeral=True)
            return

        if not trades:
            await interaction.followup.send(
                "You have no completed trades yet.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📜 Your Trade History",
            color=discord.Color.blurple()
        )
        for t in trades:
            init_cards = json.loads(t['initiator_cards']) if t['initiator_cards'] else []
            recv_cards = json.loads(t['receiver_cards']) if t['receiver_cards'] else []
            if t['initiator_user_id'] == uid:
                direction = "You → Them"
                your_cards = len(init_cards)
                their_cards = len(recv_cards)
                your_gold = t['gold_from_initiator']
                their_gold = t['gold_from_receiver']
            else:
                direction = "Them → You"
                your_cards = len(recv_cards)
                their_cards = len(init_cards)
                your_gold = t['gold_from_receiver']
                their_gold = t['gold_from_initiator']

            partner_id = t['receiver_user_id'] if t['initiator_user_id'] == uid else t['initiator_user_id']
            embed.add_field(
                name=f"{direction} | <@{partner_id}>",
                value=(
                    f"You gave: {your_cards} card(s) + {your_gold:,}💰\n"
                    f"You got:  {their_cards} card(s) + {their_gold:,}💰\n"
                    f"*{str(t.get('trade_date',''))[:10]}*"
                ),
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TradeCog(bot))
