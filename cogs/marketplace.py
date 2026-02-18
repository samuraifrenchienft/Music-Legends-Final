# cogs/marketplace.py
from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import sqlite3
import json
import uuid
import os
import math
from database import DatabaseManager, get_db

# Genre metadata
GENRE_EMOJI = {
    "EDM Bangers":      "🎧",
    "Rock Classics":    "🎸",
    "R&B Soul Pack":    "🎷",
    "Pop Hits 2024":    "🎤",
    "Hip Hop Legends":  "🎙️",
}

RARITY_EMOJI = {
    "common": "⚪", "rare": "🔵", "epic": "🟣",
    "legendary": "⭐", "mythic": "🔴",
}

PACKS_PER_PAGE = 5


# ─── Helper: fetch packs for a genre (or all) with pagination ───────────────

def _fetch_packs(db, genre: str | None, offset: int, limit: int):
    """Return (packs_list, total_count) for the given genre filter."""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        if genre:
            cursor.execute(
                "SELECT COUNT(*) FROM creator_packs WHERE status = 'LIVE' AND genre = ?",
                (genre,),
            )
            total = cursor.fetchone()[0]
            cursor.execute("""
                SELECT pack_id, name, description, cards_data, genre
                FROM creator_packs
                WHERE status = 'LIVE' AND genre = ?
                ORDER BY name
                LIMIT ? OFFSET ?
            """, (genre, limit, offset))
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM creator_packs WHERE status = 'LIVE'"
            )
            total = cursor.fetchone()[0]
            cursor.execute("""
                SELECT pack_id, name, description, cards_data, genre
                FROM creator_packs
                WHERE status = 'LIVE'
                ORDER BY name
                LIMIT ? OFFSET ?
            """, (limit, offset))
        packs = cursor.fetchall()
    return packs, total


def _fetch_pack_detail(db, pack_id: str):
    """Return a single pack row or None."""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pack_id, name, description, cards_data, genre,
                   COALESCE(price_cents, 299) AS price_cents,
                   COALESCE(price_gold, 500) AS price_gold,
                   COALESCE(pack_tier, 'community') AS pack_tier
            FROM creator_packs
            WHERE pack_id = ? AND status = 'LIVE'
        """, (pack_id,))
        return cursor.fetchone()


# ─── Helper: build embed for pack list page ─────────────────────────────────

def _build_pack_list_embed(packs, genre, page, total_pages, total_count):
    genre_label = genre or "All Genres"
    emoji = GENRE_EMOJI.get(genre, "🎵")

    embed = discord.Embed(
        title=f"{emoji} {genre_label} — Packs",
        description=f"Showing page **{page}/{total_pages}** ({total_count} packs total)",
        color=discord.Color.gold(),
    )

    for pack_id, name, description, cards_data, pack_genre in packs:
        cards = json.loads(cards_data) if cards_data else []
        pack_emoji = GENRE_EMOJI.get(pack_genre, "📦")
        desc_short = (description[:80] + "...") if description and len(description) > 80 else (description or "No description")
        embed.add_field(
            name=f"{pack_emoji} {name}",
            value=f"{len(cards)} cards | {desc_short}",
            inline=False,
        )

    embed.set_footer(text="Select a pack below to view details")
    return embed


def _build_pack_detail_embed(pack_row):
    pack_id, name, description, cards_data, genre = pack_row[:5]
    price_cents = pack_row[5] if len(pack_row) > 5 else 299
    price_gold = pack_row[6] if len(pack_row) > 6 else 500
    pack_tier = pack_row[7] if len(pack_row) > 7 else "community"
    cards = json.loads(cards_data) if cards_data else []
    emoji = GENRE_EMOJI.get(genre, "📦")

    price_usd = f"${price_cents / 100:.2f}"
    embed = discord.Embed(
        title=f"{emoji} {name}",
        description=(
            f"{description or 'No description'}\n\n"
            f"**Price:** {price_gold:,} Gold or {price_usd}\n"
            f"**Tier:** {pack_tier.title()}"
        ),
        color=discord.Color.purple(),
    )

    for card in cards[:5]:
        rarity = card.get("rarity", "common")
        r_emoji = RARITY_EMOJI.get(rarity.lower(), "⚪")
        stats = (
            f"Impact: {card.get('impact', '?')} | "
            f"Skill: {card.get('skill', '?')} | "
            f"Longevity: {card.get('longevity', '?')}\n"
            f"Culture: {card.get('culture', '?')} | "
            f"Hype: {card.get('hype', '?')}"
        )
        embed.add_field(
            name=f"{r_emoji} {card.get('name', 'Unknown')} [{rarity.title()}]",
            value=stats,
            inline=False,
        )

    embed.set_footer(text=f"Pack ID: {pack_id} | {len(cards)} cards")
    return embed


# ─── View: Genre Select (entry point) ──────────────────────────────────────

class GenreSelectView(discord.ui.View):
    def __init__(self, db: DatabaseManager, author_id: int):
        super().__init__(timeout=120)
        self.db = db
        self.author_id = author_id
        self._add_dropdown()

    def _add_dropdown(self):
        options = [
            discord.SelectOption(label="All Genres", value="__all__", emoji="🎵", description="Browse every pack"),
        ]
        for genre, emoji in GENRE_EMOJI.items():
            options.append(discord.SelectOption(label=genre, value=genre, emoji=emoji))

        select = discord.ui.Select(
            placeholder="Choose a genre...",
            options=options,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        try:
            value = interaction.data["values"][0]
            genre = None if value == "__all__" else value

            packs, total = _fetch_packs(self.db, genre, 0, PACKS_PER_PAGE)
            total_pages = max(1, math.ceil(total / PACKS_PER_PAGE))

            if not packs:
                embed = discord.Embed(
                    title="No Creator Packs Yet",
                    description=(
                        f"No community packs in **{genre or 'All Genres'}** yet.\n\n"
                        "Be the first! Use `/create_pack` to publish your pack."
                    ),
                    color=discord.Color.greyple(),
                )
                view = GenreSelectView(self.db, self.author_id)
                return await interaction.response.edit_message(embed=embed, view=view)

            embed = _build_pack_list_embed(packs, genre, 1, total_pages, total)
            view = PackBrowserView(self.db, self.author_id, genre, packs, page=1, total_pages=total_pages, total_count=total)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"[PACKS] Genre select error: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"Error loading packs: {e}", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"Error loading packs: {e}", ephemeral=True)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.author_id


# ─── View: Pack Browser (paginated list + pack select) ─────────────────────

class PackBrowserView(discord.ui.View):
    def __init__(self, db: DatabaseManager, author_id: int, genre: str | None,
                 packs: list, page: int, total_pages: int, total_count: int):
        super().__init__(timeout=120)
        self.db = db
        self.author_id = author_id
        self.genre = genre
        self.packs = packs
        self.page = page
        self.total_pages = total_pages
        self.total_count = total_count
        self._build_items()

    def _build_items(self):
        # Pack select dropdown (row 0)
        if self.packs:
            options = []
            for pack_id, name, desc, cards_data, genre in self.packs:
                cards = json.loads(cards_data) if cards_data else []
                label = name[:100] if name else "Unknown Pack"
                options.append(discord.SelectOption(
                    label=label,
                    value=pack_id,
                    description=f"{len(cards)} cards",
                    emoji=GENRE_EMOJI.get(genre, "📦"),
                ))

            select = discord.ui.Select(
                placeholder="Select a pack to view details...",
                options=options,
                row=0,
            )
            select.callback = self._on_pack_select
            self.add_item(select)

        # Prev button (row 1)
        prev_btn = discord.ui.Button(
            label="← Prev",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page <= 1),
            row=1,
        )
        prev_btn.callback = self._on_prev
        self.add_item(prev_btn)

        # Page indicator (row 1)
        page_btn = discord.ui.Button(
            label=f"Page {self.page}/{self.total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
            row=1,
        )
        self.add_item(page_btn)

        # Next button (row 1)
        next_btn = discord.ui.Button(
            label="Next →",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page >= self.total_pages),
            row=1,
        )
        next_btn.callback = self._on_next
        self.add_item(next_btn)

        # Back to genres (row 1)
        back_btn = discord.ui.Button(
            label="Back to Genres",
            style=discord.ButtonStyle.primary,
            row=1,
        )
        back_btn.callback = self._on_back
        self.add_item(back_btn)

    async def _go_to_page(self, interaction: Interaction, new_page: int):
        offset = (new_page - 1) * PACKS_PER_PAGE
        packs, total = _fetch_packs(self.db, self.genre, offset, PACKS_PER_PAGE)
        total_pages = max(1, math.ceil(total / PACKS_PER_PAGE))

        embed = _build_pack_list_embed(packs, self.genre, new_page, total_pages, total)
        view = PackBrowserView(self.db, self.author_id, self.genre, packs,
                               page=new_page, total_pages=total_pages, total_count=total)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _on_prev(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
        try:
            await self._go_to_page(interaction, self.page - 1)
        except Exception as e:
            print(f"[PACKS] Prev page error: {e}")
            import traceback; traceback.print_exc()
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    async def _on_next(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)
        try:
            await self._go_to_page(interaction, self.page + 1)
        except Exception as e:
            print(f"[PACKS] Next page error: {e}")
            import traceback; traceback.print_exc()
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    async def _on_back(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        embed = discord.Embed(
            title="MARKETPLACE PACKS",
            description="Select a genre to browse packs",
            color=discord.Color.gold(),
        )
        view = GenreSelectView(self.db, self.author_id)
        await interaction.response.edit_message(embed=embed, view=view)

    async def _on_pack_select(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        try:
            pack_id = interaction.data["values"][0]
            pack_row = _fetch_pack_detail(self.db, pack_id)
            if not pack_row:
                return await interaction.response.send_message("Pack not found or no longer available.", ephemeral=True)

            embed = _build_pack_detail_embed(pack_row)
            view = PackDetailView(self.db, self.author_id, pack_id, self.genre,
                                  self.page, self.total_pages, self.total_count)
            await interaction.response.edit_message(embed=embed, view=view)
        except Exception as e:
            print(f"[PACKS] Pack select error: {e}")
            import traceback; traceback.print_exc()
            try:
                await interaction.response.send_message(f"Error: {e}", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"Error: {e}", ephemeral=True)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.author_id


# ─── View: Pack Detail (card stats + open) ─────────────────────────────────

class PackDetailView(discord.ui.View):
    def __init__(self, db: DatabaseManager, author_id: int, pack_id: str,
                 genre: str | None, page: int, total_pages: int, total_count: int):
        super().__init__(timeout=120)
        self.db = db
        self.author_id = author_id
        self.pack_id = pack_id
        self.genre = genre
        self.page = page
        self.total_pages = total_pages
        self.total_count = total_count

    def _grant_pack_cards(self, user_id: int, pack_row) -> list:
        """Grant all cards from a pack to a user atomically.

        All cards are inserted in a single transaction so either all
        are granted or none are (no partial inventory on failure).
        """
        cards_data_json = pack_row[3]
        cards_data = json.loads(cards_data_json) if cards_data_json else []
        import random

        # Prepare card data before touching DB
        for card_data in cards_data:
            if card_data.get('rarity') in ['legendary', 'epic']:
                if random.random() < 0.1:
                    variant_frames = ['holographic', 'crystal', 'neon']
                    card_data['frame_style'] = random.choice(variant_frames)
                    card_data['foil'] = True
                    card_data['foil_effect'] = 'rainbow'
            if 'card_id' not in card_data:
                card_data['card_id'] = str(uuid.uuid4())

        # Single atomic transaction for all cards + purchase counter
        conn = self.db._get_connection()
        try:
            cursor = conn.cursor()

            for card_data in cards_data:
                # Upsert into master cards table
                rarity = card_data.get('rarity', 'common').lower()
                tier_map = {'common': 'community', 'rare': 'gold', 'epic': 'platinum',
                            'legendary': 'legendary', 'mythic': 'legendary'}
                tier = card_data.get('tier') or tier_map.get(rarity, 'community')

                cursor.execute("""
                    INSERT OR REPLACE INTO cards
                    (card_id, name, artist_name, title, rarity, tier, serial_number, print_number,
                     quality, impact, skill, longevity, culture, hype, image_url, youtube_url, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    card_data['card_id'], card_data.get('name', ''),
                    card_data.get('artist_name', card_data.get('name', '')),
                    card_data.get('title', ''), rarity, tier,
                    card_data.get('serial_number', card_data['card_id']),
                    card_data.get('print_number', 1), card_data.get('quality', 'standard'),
                    card_data.get('impact', 0), card_data.get('skill', 0),
                    card_data.get('longevity', 0), card_data.get('culture', 0),
                    card_data.get('hype', 0), card_data.get('image_url'),
                    card_data.get('youtube_url'), card_data.get('type', 'artist'),
                ))

                # Add to user collection
                cursor.execute("""
                    INSERT OR IGNORE INTO user_cards (user_id, card_id, acquired_from)
                    VALUES (?, ?, 'pack_purchase')
                """, (user_id, card_data['card_id']))

            # Increment total_purchases
            cursor.execute(
                "UPDATE creator_packs SET total_purchases = total_purchases + 1 WHERE pack_id = ?",
                (self.pack_id,),
            )

            # Record in pack_purchases so pack appears in /pack and /battle
            pp_id = f"purchase_{uuid.uuid4().hex[:12]}"
            card_ids = [c.get('card_id') for c in cards_data if c.get('card_id')]
            cursor.execute(
                "INSERT INTO pack_purchases (purchase_id, pack_id, buyer_id, cards_received) VALUES (?, ?, ?, ?)",
                (pp_id, self.pack_id, user_id, json.dumps(card_ids))
            )

            conn.commit()
            return cards_data

        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            conn.close()

    @discord.ui.button(label="Buy with Gold", style=discord.ButtonStyle.success, emoji="🪙", row=0)
    async def buy_gold_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        try:
            pack_row = _fetch_pack_detail(self.db, self.pack_id)
            if not pack_row:
                return await interaction.followup.send("Pack not found or no longer available.", ephemeral=True)

            price_gold = pack_row[6] if len(pack_row) > 6 else 500

            # Check user gold
            economy = self.db.get_user_economy(interaction.user.id)
            user_gold = economy.get('gold', 0)

            if user_gold < price_gold:
                return await interaction.followup.send(
                    f"Insufficient gold! You need **{price_gold:,}** Gold but only have **{user_gold:,}**.",
                    ephemeral=True,
                )

            # Deduct gold
            self.db.update_user_economy(interaction.user.id, gold_change=-price_gold)

            # Grant cards
            received_cards = self._grant_pack_cards(interaction.user.id, pack_row)

            if not received_cards:
                return await interaction.followup.send("This pack has no cards.", ephemeral=True)

            # Grant pack purchase bonuses (gold + tickets)
            from config.economy import PACK_PRICING as ECON_PRICING
            pack_tier = pack_row[7] if len(pack_row) > 7 else 'community'
            pack_bonus = ECON_PRICING.get(pack_tier, {})
            bonus_gold = pack_bonus.get('bonus_gold', 0)
            bonus_tickets = pack_bonus.get('bonus_tickets', 0)
            if bonus_gold or bonus_tickets:
                self.db.update_user_economy(interaction.user.id, gold_change=bonus_gold, tickets_change=bonus_tickets)

            # Record purchase
            purchase_id = str(uuid.uuid4())
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO purchases (purchase_id, user_id, pack_id, amount_cents, payment_method, status)
                       VALUES (?, ?, ?, 0, 'gold', 'completed')""",
                    (purchase_id, interaction.user.id, self.pack_id),
                )
                conn.commit()

            pack_name = pack_row[1]
            pack_type = 'gold' if any(c.get('rarity') in ['legendary', 'epic'] for c in received_cards) else 'community'

            # Build bonus text for the opening animation
            bonus_text = ""
            if bonus_gold:
                bonus_text += f"+{bonus_gold:,} Gold "
            if bonus_tickets:
                bonus_text += f"+{bonus_tickets} Tickets"

            from views.pack_opening import open_pack_with_animation
            await open_pack_with_animation(
                interaction=interaction,
                pack_name=pack_name,
                pack_type=pack_type,
                cards=received_cards,
                pack_id=self.pack_id,
                delay=2.0,
            )
            if bonus_text:
                await interaction.followup.send(f"**Bonus rewards:** {bonus_text.strip()}", ephemeral=True)
        except Exception as e:
            print(f"Error buying pack with gold: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"Failed to purchase pack: {e}", ephemeral=True)

    @discord.ui.button(label="Buy Pack", style=discord.ButtonStyle.primary, emoji="💳", row=0)
    async def buy_stripe_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        try:
            pack_row = _fetch_pack_detail(self.db, self.pack_id)
            if not pack_row:
                return await interaction.response.send_message("Pack not found.", ephemeral=True)

            pack_name = pack_row[1]
            price_cents = pack_row[5] if len(pack_row) > 5 else 299

            from stripe_payments import stripe_manager
            result = stripe_manager.create_pack_purchase_checkout(
                pack_id=self.pack_id,
                buyer_id=interaction.user.id,
                pack_name=pack_name,
                price_cents=price_cents,
            )

            if result.get('success'):
                checkout_url = result['checkout_url']
                embed = discord.Embed(
                    title="Checkout",
                    description=f"[Click here to pay ${price_cents/100:.2f}]({checkout_url})\n\nYour cards will be delivered automatically after payment.",
                    color=discord.Color.blue(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Failed to create checkout: {result.get('error', 'Unknown error')}",
                    ephemeral=True,
                )
        except Exception as e:
            print(f"Error creating Stripe checkout: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"Failed to create checkout: {e}", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"Failed to create checkout: {e}", ephemeral=True)

    @discord.ui.button(label="Back to Browse", style=discord.ButtonStyle.secondary, emoji="🔙", row=0)
    async def back_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        offset = (self.page - 1) * PACKS_PER_PAGE
        packs, total = _fetch_packs(self.db, self.genre, offset, PACKS_PER_PAGE)
        total_pages = max(1, math.ceil(total / PACKS_PER_PAGE))

        embed = _build_pack_list_embed(packs, self.genre, self.page, total_pages, total)
        view = PackBrowserView(self.db, self.author_id, self.genre, packs,
                               page=self.page, total_pages=total_pages, total_count=total)
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.author_id


# ─── Tier Pack Definitions (for /buy_pack) ─────────────────────────────────

TIER_PACKS = {
    "community": {"label": "Community Pack", "emoji": "📦", "color": 0x2ECC71},
    "gold":      {"label": "Gold Pack",      "emoji": "🥇", "color": 0xFFD700},
    "platinum":  {"label": "Platinum Pack",   "emoji": "💎", "color": 0xE5E4E2},
}


# ─── View: Tier Pack Confirm (purchase buttons) ───────────────────────────

class BuyPackConfirmView(discord.ui.View):
    """Shows tier pack details + Buy with Gold / Buy with Stripe buttons."""

    def __init__(self, db: DatabaseManager, author_id: int, tier: str):
        super().__init__(timeout=120)
        self.db = db
        self.author_id = author_id
        self.tier = tier

    @discord.ui.button(label="Buy with Gold", style=discord.ButtonStyle.success, emoji="🪙", row=0)
    async def buy_gold(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        await interaction.response.defer(ephemeral=False)
        try:
            from config.economy import PACK_PRICING
            pricing = PACK_PRICING.get(self.tier)
            if not pricing:
                return await interaction.followup.send("Invalid tier.", ephemeral=True)

            gold_price = pricing.get('buy_gold')
            if gold_price is None:
                return await interaction.followup.send(
                    f"The **{TIER_PACKS[self.tier]['label']}** cannot be purchased with gold. Use Stripe or tickets instead.",
                    ephemeral=True,
                )

            economy = self.db.get_user_economy(interaction.user.id)
            user_gold = economy.get('gold', 0)

            if user_gold < gold_price:
                return await interaction.followup.send(
                    f"Insufficient gold! You need **{gold_price:,}** Gold but only have **{user_gold:,}**.",
                    ephemeral=True,
                )

            # Deduct gold
            self.db.update_user_economy(interaction.user.id, gold_change=-gold_price)

            # Generate random cards for this tier
            cards = self.db.generate_tier_pack_cards(interaction.user.id, self.tier)
            if not cards:
                # Refund on failure
                self.db.update_user_economy(interaction.user.id, gold_change=gold_price)
                return await interaction.followup.send("No cards available to generate. Gold refunded.", ephemeral=True)

            # Grant bonuses
            bonus_gold = pricing.get('bonus_gold', 0)
            bonus_tickets = pricing.get('bonus_tickets', 0)
            if bonus_gold or bonus_tickets:
                self.db.update_user_economy(interaction.user.id, gold_change=bonus_gold, tickets_change=bonus_tickets)

            # Record purchase
            purchase_id = str(uuid.uuid4())
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO purchases (purchase_id, user_id, pack_id, amount_cents, payment_method, status)
                       VALUES (?, ?, ?, 0, 'gold', 'completed')""",
                    (purchase_id, interaction.user.id, f'tier_{self.tier}'),
                )
                conn.commit()

            # Pack opening animation
            pack_name = TIER_PACKS[self.tier]['label']
            pack_type = 'gold' if self.tier in ('gold', 'platinum') else 'community'

            from views.pack_opening import open_pack_with_animation
            await open_pack_with_animation(
                interaction=interaction,
                pack_name=pack_name,
                pack_type=pack_type,
                cards=cards,
                delay=2.0,
            )

            bonus_text = ""
            if bonus_gold:
                bonus_text += f"+{bonus_gold:,} Gold "
            if bonus_tickets:
                bonus_text += f"+{bonus_tickets} Tickets"
            if bonus_text:
                await interaction.followup.send(f"**Bonus rewards:** {bonus_text.strip()}", ephemeral=True)

        except Exception as e:
            print(f"Error buying tier pack with gold: {e}")
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"Failed to purchase pack: {e}", ephemeral=True)

    @discord.ui.button(label="Buy Pack", style=discord.ButtonStyle.primary, emoji="💳", row=0)
    async def buy_stripe(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        try:
            from config.economy import PACK_PRICING
            pricing = PACK_PRICING.get(self.tier)
            if not pricing:
                return await interaction.response.send_message("Invalid tier.", ephemeral=True)

            price_cents = pricing['buy_usd_cents']
            pack_name = TIER_PACKS[self.tier]['label']

            from stripe_payments import stripe_manager
            result = stripe_manager.create_tier_pack_checkout(
                tier=self.tier,
                buyer_id=interaction.user.id,
                pack_name=pack_name,
                price_cents=price_cents,
            )

            if result.get('success'):
                checkout_url = result['checkout_url']
                embed = discord.Embed(
                    title="Checkout",
                    description=f"[Click here to pay ${price_cents/100:.2f}]({checkout_url})\n\nYour cards will be delivered automatically after payment.",
                    color=discord.Color.blue(),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"Failed to create checkout: {result.get('error', 'Unknown error')}",
                    ephemeral=True,
                )
        except Exception as e:
            print(f"Error creating tier pack Stripe checkout: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"Failed to create checkout: {e}", ephemeral=True)
            except Exception:
                await interaction.followup.send(f"Failed to create checkout: {e}", ephemeral=True)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.author_id


# ─── View: Tier Pack Select (dropdown) ────────────────────────────────────

class BuyPackTierView(discord.ui.View):
    """Dropdown to choose Community / Gold / Platinum tier pack."""

    def __init__(self, db: DatabaseManager, author_id: int):
        super().__init__(timeout=120)
        self.db = db
        self.author_id = author_id
        self._add_dropdown()

    def _add_dropdown(self):
        from config.economy import PACK_PRICING
        options = []
        for tier, meta in TIER_PACKS.items():
            pricing = PACK_PRICING.get(tier, {})
            price_str = f"${pricing.get('buy_usd', 0):.2f}"
            gold_str = f"{pricing.get('buy_gold', 'N/A'):,}" if pricing.get('buy_gold') else "N/A"
            cards = pricing.get('cards_per_pack', '?')
            options.append(discord.SelectOption(
                label=meta['label'],
                value=tier,
                emoji=meta['emoji'],
                description=f"{cards} cards | {price_str} or {gold_str} gold",
            ))

        select = discord.ui.Select(placeholder="Choose a pack tier...", options=options)
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, interaction: Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This menu isn't for you.", ephemeral=True)

        tier = interaction.data["values"][0]
        from config.economy import PACK_PRICING
        from schemas.pack_definition import PACK_DEFINITIONS

        # Map PACK_PRICING tier names to PACK_DEFINITIONS keys
        TIER_TO_DEF = {"community": "starter", "gold": "gold", "platinum": "platinum"}

        pricing = PACK_PRICING.get(tier, {})
        pack_def = PACK_DEFINITIONS.get(TIER_TO_DEF.get(tier, tier))
        meta = TIER_PACKS[tier]

        # Build detail embed
        embed = discord.Embed(
            title=f"{meta['emoji']} {meta['label']}",
            description=pricing.get('description', ''),
            color=meta['color'],
        )

        embed.add_field(
            name="Cards",
            value=f"**{pricing.get('cards_per_pack', '?')}** random cards",
            inline=True,
        )

        # Odds breakdown from pack definition
        if pack_def:
            odds_lines = [f"{r.title()}: {int(o*100)}%" for r, o in pack_def.odds.items()]
            embed.add_field(name="Rarity Odds", value="\n".join(odds_lines), inline=True)

        # Bonuses
        bonus_parts = []
        if pricing.get('bonus_gold'):
            bonus_parts.append(f"+{pricing['bonus_gold']:,} Gold")
        if pricing.get('bonus_tickets'):
            bonus_parts.append(f"+{pricing['bonus_tickets']} Tickets")
        if bonus_parts:
            embed.add_field(name="Bonuses", value="\n".join(bonus_parts), inline=True)

        # Price
        price_lines = [f"**${pricing.get('buy_usd', 0):.2f}** USD"]
        if pricing.get('buy_gold'):
            price_lines.append(f"**{pricing['buy_gold']:,}** Gold")
        if pricing.get('buy_tickets'):
            price_lines.append(f"**{pricing['buy_tickets']:,}** Tickets")
        embed.add_field(name="Price", value=" / ".join(price_lines), inline=False)

        view = BuyPackConfirmView(self.db, self.author_id, tier)
        await interaction.response.edit_message(embed=embed, view=view)

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.author_id


# ─── View: Pack Contents ────────────────────────────────────────────────────

class PackContentsView(discord.ui.View):
    """View for displaying purchased pack contents with video links"""

    def __init__(self, db, user_id: int, purchases: list):
        super().__init__(timeout=180)
        self.db = db
        self.user_id = user_id
        self.purchases = purchases
        self.current_pack = None

        # Add pack selection dropdown
        options = [
            discord.SelectOption(
                label=p['pack_name'][:100] if p['pack_name'] else 'Unnamed Pack',
                description=f"{len(p['cards'])} cards • {p['purchased_at'][:10] if p['purchased_at'] else 'Unknown date'}",
                value=str(i)
            )
            for i, p in enumerate(purchases[:25])
        ]

        select = discord.ui.Select(
            placeholder="Select a pack to view",
            options=options
        )
        select.callback = self.on_pack_select
        self.add_item(select)

    def create_pack_list_embed(self) -> discord.Embed:
        """Create embed showing list of acquired packs"""
        embed = discord.Embed(
            title="📦 Your Pack Collection",
            description=f"You own {len(self.purchases)} pack(s)\nSelect a pack from the dropdown to view cards and YouTube links",
            color=discord.Color.purple()
        )

        # Show recent acquisitions
        for i, pack in enumerate(self.purchases[:5]):
            tier_emoji = {
                'community': '⚪',
                'gold': '🟡',
                'platinum': '⚫',
                'legendary': '⭐'
            }.get(pack.get('pack_tier', '').lower(), '📦')

            pack_name = pack.get('pack_name', 'Unnamed Pack')
            card_count = len(pack.get('cards', []))
            purchased_at = pack.get('purchased_at', 'Unknown date')[:10]

            embed.add_field(
                name=f"{tier_emoji} {pack_name}",
                value=f"{card_count} cards • Acquired {purchased_at}",
                inline=False
            )

        embed.set_footer(text="Use dropdown above to view pack contents")
        return embed

    async def on_pack_select(self, interaction: Interaction):
        """Handle pack selection from dropdown"""
        pack_index = int(interaction.data['values'][0])
        self.current_pack = self.purchases[pack_index]

        embed = self.create_pack_contents_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def create_pack_contents_embed(self) -> discord.Embed:
        """Create embed showing all cards in selected pack"""
        pack = self.current_pack

        tier_colors = {
            'community': discord.Color.light_gray(),
            'gold': discord.Color.gold(),
            'platinum': discord.Color.dark_gray(),
            'legendary': discord.Color.orange()
        }
        color = tier_colors.get(pack.get('pack_tier', '').lower(), discord.Color.purple())

        pack_name = pack.get('pack_name', 'Unnamed Pack')
        purchased_at = pack.get('purchased_at', 'Unknown date')[:10]
        cards = pack.get('cards', [])

        embed = discord.Embed(
            title=f"📦 {pack_name}",
            description=f"Purchased on {purchased_at} • {len(cards)} cards",
            color=color
        )

        # Show each card with stats and YouTube link
        for card in cards[:10]:  # Limit to 10 cards per page
            rarity_emoji = RARITY_EMOJI.get(
                card.get('rarity', 'common').lower(),
                '⚪'
            )

            name = card.get('name', 'Unknown Artist')
            title = card.get('title', '')
            display = f"{name} — \"{title}\"" if title else name

            stats = (
                f"Impact {card.get('impact', 50)} • "
                f"Skill {card.get('skill', 50)} • "
                f"Longevity {card.get('longevity', 50)} • "
                f"Culture {card.get('culture', 50)} • "
                f"Hype {card.get('hype', 50)}"
            )

            # Build links
            links = []
            if card.get('youtube_url'):
                links.append(f"[▶️ Watch on YouTube]({card['youtube_url']})")
            links.append(f"`/view {card.get('card_id', 'unknown')}`")

            embed.add_field(
                name=f"{rarity_emoji} {display}",
                value=f"{stats}\n{' • '.join(links)}",
                inline=False
            )

        if len(cards) > 10:
            embed.set_footer(text=f"Showing first 10 of {len(cards)} cards")
        else:
            embed.set_footer(text="Music Legends • Use /collection to see all your cards")

        return embed

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user.id == self.user_id


# ─── Cog: Marketplace Commands ─────────────────────────────────────────────

class MarketplaceCommands(commands.Cog):
    """Marketplace commands for buying/selling cards"""

    def __init__(self, bot):
        self.bot = bot
        self.db = get_db()

    @app_commands.command(name="sell", description="List a card for sale")
    @app_commands.describe(card_id="Card ID to sell", price="Price in gold")
    async def sell_command(self, interaction: Interaction, card_id: str, price: int):
        """List a card for sale in the marketplace"""

        conn = self.db._get_connection()
        db_type = self.db._db_type
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.name, c.rarity FROM cards c
                JOIN user_cards uc ON c.card_id = uc.card_id
                WHERE c.card_id = ? AND uc.user_id = ?
            """, (card_id, interaction.user.id))
            card = cursor.fetchone()

            if not card:
                conn.close()
                await interaction.response.send_message("You don't own this card!", ephemeral=True)
                return

            card_name, rarity = card

            # List the card - use correct table name and columns
            listing_id = f"listing_{uuid.uuid4().hex[:8]}"

            if db_type == "postgresql":
                cursor.execute("""
                    INSERT INTO market_listings
                    (listing_id, card_id, seller_user_id, asking_gold, status, created_at)
                    VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
                    ON CONFLICT (listing_id) DO UPDATE SET asking_gold = EXCLUDED.asking_gold
                """, (listing_id, card_id, interaction.user.id, price))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_listings
                    (listing_id, card_id, seller_user_id, asking_gold, status, created_at)
                    VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
                """, (listing_id, card_id, interaction.user.id, price))
            conn.commit()
        finally:
            conn.close()

        # Trigger backup after marketplace listing
        try:
            from services.backup_service import backup_service
            backup_path = await backup_service.backup_critical('marketplace_listing', card_id)
            if backup_path:
                print(f"Critical backup created after marketplace listing: {backup_path}")
        except Exception as e:
            print(f"Backup trigger failed (non-critical): {e}")

        rarity_emoji = RARITY_EMOJI.get(rarity.lower(), "⚪")

        embed = discord.Embed(
            title="CARD LISTED",
            description=f"{rarity_emoji} **{card_name}** has been listed for {price:,} Gold!",
            color=discord.Color.green()
        )

        embed.add_field(name="Card ID", value=f"`{card_id}`", inline=True)
        embed.add_field(name="Price", value=f"{price:,} Gold", inline=True)
        embed.add_field(name="Status", value="Listed", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="buy", description="Purchase a card from the marketplace")
    @app_commands.describe(card_id="Card ID to purchase")
    async def buy_command(self, interaction: Interaction, card_id: str):
        """Purchase a card from the marketplace"""

        conn = self.db._get_connection()
        db_type = self.db._db_type
        try:
            cursor = conn.cursor()

            # Check if card is listed - use correct table and column names
            cursor.execute("""
                SELECT c.card_id, c.name, c.rarity, c.image_url,
                       m.asking_gold, m.seller_user_id, m.status, m.listing_id
                FROM cards c
                JOIN market_listings m ON c.card_id = m.card_id
                WHERE c.card_id = ? AND m.status = 'active'
            """, (card_id,))
            listing = cursor.fetchone()

            if not listing:
                conn.close()
                await interaction.response.send_message(
                    "This card is not available for purchase! It may have been sold or removed.",
                    ephemeral=True
                )
                return

            card_id_db, card_name, rarity, image_url, price, seller_id, status, listing_id = listing

            # Check if user is trying to buy their own card
            if seller_id == interaction.user.id:
                conn.close()
                await interaction.response.send_message(
                    "You can't buy your own card! Remove it from the marketplace first.",
                    ephemeral=True
                )
                return

            # Check if user has enough gold - from user_inventory table
            cursor.execute("""
                SELECT gold FROM user_inventory WHERE user_id = ?
            """, (interaction.user.id,))
            user_result = cursor.fetchone()

            if not user_result:
                # Create user inventory if not exists
                cursor.execute("""
                    INSERT INTO user_inventory (user_id, gold, dust, tickets, gems, xp, level)
                    VALUES (?, 500, 0, 0, 0, 0, 1)
                """, (interaction.user.id,))
                conn.commit()
                user_gold = 500
            else:
                user_gold = user_result[0] or 0

            if user_gold < price:
                conn.close()
                await interaction.response.send_message(
                    f"Insufficient funds! You need {price:,} Gold but only have {user_gold:,} Gold.",
                    ephemeral=True
                )
                return

            # Process purchase
            try:
                # Transfer card ownership
                cursor.execute("""
                    DELETE FROM user_cards WHERE user_id = ? AND card_id = ?
                """, (seller_id, card_id))

                cursor.execute("""
                    INSERT INTO user_cards (user_id, card_id, acquired_from, acquired_at)
                    VALUES (?, ?, 'marketplace', CURRENT_TIMESTAMP)
                """, (interaction.user.id, card_id))

                # Transfer gold - use user_inventory table
                cursor.execute("""
                    UPDATE user_inventory SET gold = gold - ? WHERE user_id = ?
                """, (price, interaction.user.id))

                # Ensure seller has inventory record (PostgreSQL vs SQLite syntax)
                if db_type == "postgresql":
                    cursor.execute("""
                        INSERT INTO user_inventory (user_id, gold)
                        VALUES (?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET gold = user_inventory.gold + EXCLUDED.gold
                    """, (seller_id, price))
                else:
                    cursor.execute("""
                        INSERT INTO user_inventory (user_id, gold)
                        VALUES (?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET gold = user_inventory.gold + EXCLUDED.gold
                    """, (seller_id, price))

                # Update listing status
                cursor.execute("""
                    UPDATE market_listings
                    SET status = 'sold', buyer_user_id = ?, sold_at = CURRENT_TIMESTAMP
                    WHERE listing_id = ?
                """, (interaction.user.id, listing_id))

                conn.commit()

                # Trigger backup after marketplace purchase
                try:
                    from services.backup_service import backup_service
                    backup_path = await backup_service.backup_critical('marketplace_buy', card_id)
                    if backup_path:
                        print(f"Critical backup created after marketplace purchase: {backup_path}")
                except Exception as e:
                    print(f"Backup trigger failed (non-critical): {e}")

                rarity_emoji = RARITY_EMOJI.get(rarity.lower(), "⚪")

                embed = discord.Embed(
                    title="PURCHASE SUCCESSFUL",
                    description=f"{rarity_emoji} **{card_name}** has been added to your collection!",
                    color=discord.Color.green()
                )

                embed.add_field(name="Card ID", value=f"`{card_id}`", inline=True)
                embed.add_field(name="Price Paid", value=f"{price:,} Gold", inline=True)
                embed.add_field(name="Remaining Gold", value=f"{user_gold - price:,} Gold", inline=True)

                if image_url:
                    embed.set_thumbnail(url=image_url)

                await interaction.response.send_message(embed=embed)

            except Exception as e:
                conn.rollback()
                await interaction.response.send_message(
                    "Purchase failed. Please try again.",
                    ephemeral=True
                )
                print(f"Marketplace purchase error: {e}")
                import traceback
                traceback.print_exc()
        finally:
            conn.close()

    @app_commands.command(name="market", description="View marketplace listings")
    async def market_command(self, interaction: Interaction):
        """View all active marketplace listings"""

        embed = discord.Embed(
            title="CARD MARKETPLACE",
            description="Browse cards for sale",
            color=discord.Color.gold()
        )

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.card_id, c.name, c.rarity, m.asking_gold, m.seller_user_id
                FROM cards c
                JOIN market_listings m ON c.card_id = m.card_id
                WHERE m.status = 'active'
                ORDER BY m.created_at DESC
                LIMIT 20
            """)
            listings = cursor.fetchall()

        if listings:
            for card_id, card_name, rarity, price, seller_id in listings:
                rarity_emoji = RARITY_EMOJI.get((rarity or "common").lower(), "⚪")
                embed.add_field(
                    name=f"{rarity_emoji} {card_name}",
                    value=f"Price: {price:,} Gold\nID: `{card_id}`\nUse `/buy {card_id}` to purchase",
                    inline=True
                )
        else:
            embed.add_field(
                name="No Listings",
                value="No cards for sale yet. Use `/sell <card_id> <price>` to list yours!",
                inline=False
            )

        embed.set_footer(text="Use /sell to list your cards | Use /buy to purchase")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pack", description="View packs you've acquired")
    async def pack_command(self, interaction: Interaction):
        """View all packs you've acquired (purchased, claimed, picked up)"""

        await interaction.response.defer(ephemeral=False)

        try:
            purchases = self.db.get_user_purchased_packs(interaction.user.id, limit=25)
            print(f"[PACK] User {interaction.user.id} ({interaction.user.display_name}): found {len(purchases)} pack(s)")
        except Exception as e:
            import traceback
            print(f"[PACK] ERROR for user {interaction.user.id}: {e}")
            traceback.print_exc()
            embed = discord.Embed(
                title="❌ Error Loading Packs",
                description="Something went wrong loading your packs. Please try again.",
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        if not purchases:
            # Fallback: user may have cards from before pack_purchases was tracked
            all_cards = self.db.get_user_collection(interaction.user.id)
            if not all_cards:
                embed = discord.Embed(
                    title="📦 No Packs Yet",
                    description=(
                        "You haven't acquired any packs yet!\n\n"
                        "🛒 Use `/packs` to browse marketplace\n"
                        "🎁 Check daily rewards\n"
                        "✨ Watch for drops in channels"
                    ),
                    color=discord.Color.blue()
                )
                return await interaction.followup.send(embed=embed)
            # Synthesize a single "My Collection" pack from existing cards
            purchases = [{
                'purchase_id': 'synth_collection',
                'pack_id': 'collection',
                'pack_name': 'My Collection',
                'pack_tier': 'community',
                'purchased_at': 'Before tracking',
                'description': None,
                'genre': None,
                'cards': all_cards,
            }]
            print(f"[PACK] No pack_purchases for {interaction.user.id} — synthesized collection pack ({len(all_cards)} cards)")

        # Create pack selection view
        view = PackContentsView(self.db, interaction.user.id, purchases)
        embed = view.create_pack_list_embed()
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="packs", description="Browse marketplace packs by genre")
    async def packs_command(self, interaction: Interaction):
        """Browse all available marketplace packs with genre filtering"""

        embed = discord.Embed(
            title="MARKETPLACE PACKS",
            description="Select a genre to browse packs",
            color=discord.Color.gold(),
        )

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT genre, COUNT(*) FROM creator_packs
                WHERE status = 'LIVE' AND genre IS NOT NULL
                GROUP BY genre ORDER BY genre
            """)
            genre_counts = cursor.fetchall()
            cursor.execute(
                "SELECT COUNT(*) FROM creator_packs WHERE status = 'LIVE'"
            )
            total = cursor.fetchone()[0]

        if genre_counts:
            lines = []
            for genre_name, count in genre_counts:
                emoji = GENRE_EMOJI.get(genre_name, "🎵")
                lines.append(f"{emoji} **{genre_name}** — {count} packs")
            embed.add_field(
                name="Available Genres",
                value="\n".join(lines),
                inline=False,
            )
        embed.set_footer(text=f"{total} packs total | Select a genre below")

        view = GenreSelectView(self.db, interaction.user.id)
        try:
            await interaction.response.send_message(embed=embed, view=view)
        except discord.errors.HTTPException:
            await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="buy_pack", description="Purchase a pack by tier (Community, Gold, Platinum)")
    async def buy_pack_command(self, interaction: Interaction):
        """Show tier selection dropdown for buying built-in packs."""
        embed = discord.Embed(
            title="📦 Buy a Pack",
            description="Select a tier below to see details and purchase.",
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="Available Tiers",
            value="📦 **Community Pack** — $2.99 / 500 Gold\n"
                  "🥇 **Gold Pack** — $4.99 / 100 Tickets\n"
                  "💎 **Platinum Pack** — $6.99 / 2,500 Gold",
            inline=False,
        )
        view = BuyPackTierView(self.db, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="delist", description="Remove your card listing from the marketplace")
    @app_commands.describe(listing_id="Listing ID to remove (shown in /market or /sell confirmation)")
    async def delist_command(self, interaction: Interaction, listing_id: str):
        """Cancel an active marketplace listing and return the card to the owner."""
        conn = self.db._get_connection()
        try:
            cursor = conn.cursor()
            # Verify the listing belongs to this user and is active
            cursor.execute("""
                SELECT listing_id, card_id, asking_gold
                FROM market_listings
                WHERE listing_id = ? AND seller_user_id = ? AND status = 'active'
            """, (listing_id, interaction.user.id))
            row = cursor.fetchone()

            if not row:
                await interaction.response.send_message(
                    "Listing not found or it's not yours / already sold.", ephemeral=True
                )
                return

            _, card_id, price = row

            # Cancel the listing
            cursor.execute("""
                UPDATE market_listings SET status = 'cancelled'
                WHERE listing_id = ?
            """, (listing_id,))
            conn.commit()
        except Exception as e:
            print(f"Delist error: {e}")
            await interaction.response.send_message(
                "Failed to remove listing. Please try again.", ephemeral=True
            )
            return
        finally:
            conn.close()

        embed = discord.Embed(
            title="✅ Listing Removed",
            description=f"Listing `{listing_id}` has been cancelled.\nYour card is still in your collection.",
            color=discord.Color.green()
        )
        embed.add_field(name="Card ID", value=f"`{card_id}`", inline=True)
        embed.add_field(name="Listed Price Was", value=f"{price:,} Gold", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(MarketplaceCommands(bot))
