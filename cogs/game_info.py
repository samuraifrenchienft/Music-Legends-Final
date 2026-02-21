# cogs/game_info.py
"""
/post_game_info — Posts a multi-embed game guide in the current channel.
Admin-only. Covers: Welcome, Getting Started, Packs, Battles, Commands.
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from ui.brand import GOLD, PURPLE, BLUE, PINK, GREEN, NAVY, LOGO_URL, BANNER_URL


class GameInfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="post_game_info", description="Post the full game guide in this channel (admin only)")
    async def post_game_info(self, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only admins can post the game guide.", ephemeral=True)
            return

        await interaction.response.send_message("📋 Posting game guide...", ephemeral=True)
        ch = interaction.channel

        # ── 1. Welcome ─────────────────────────────────────────────
        e1 = discord.Embed(
            title="🎵 Welcome to Music Legends!",
            description=(
                "**Music Legends** is the ultimate music artist card battle game.\n\n"
                "🎴 Collect cards of your favourite artists\n"
                "⚔️ Battle friends in strategic card duels\n"
                "📦 Open packs to discover rare cards\n"
                "🏆 Climb the leaderboard every season\n\n"
                "**Everything starts with the User Hub — find it in this server "
                "and click Daily Claim to begin!**"
            ),
            color=PURPLE,
        )
        e1.set_author(name="Music Legends", icon_url=LOGO_URL)
        e1.set_image(url=BANNER_URL)
        e1.set_footer(text="🎵 Music Legends")
        await ch.send(embed=e1)

        # ── 2. Getting Started ──────────────────────────────────────
        e2 = discord.Embed(
            title="🚀 Getting Started",
            description=(
                "**Step 1** — Find the **User Hub** (posted by an admin with `/setup_user_hub`)\n"
                "**Step 2** — Click **💰 Daily Claim** every day for free gold + a card pack\n"
                "**Step 3** — Click **📦 Buy Pack** to purchase a card pack with gold or real money\n"
                "**Step 4** — Click **⚔️ Battle** to challenge another player\n"
                "**Step 5** — Check **🏆 Leaderboard** to see where you rank"
            ),
            color=GOLD,
        )
        e2.set_author(name="Music Legends", icon_url=LOGO_URL)
        e2.set_thumbnail(url=LOGO_URL)
        e2.set_footer(text="🎵 Music Legends • Tip: claim daily every day for streak bonuses!")
        await ch.send(embed=e2)

        # ── 3. Packs & Cards ───────────────────────────────────────
        e3 = discord.Embed(
            title="📦 Packs & Cards",
            description="There are two types of packs:",
            color=BLUE,
        )
        e3.set_author(name="Music Legends", icon_url=LOGO_URL)
        e3.add_field(
            name="🏪 Built-In Tier Packs (`/buy_pack`)",
            value=(
                "⚪ **Community** — 500 Gold or $2.99 • 5 cards\n"
                "👑 **Gold** — 100 Tickets or $4.99 • 5 cards\n"
                "💎 **Platinum** — 2,500 Gold or $6.99 • 10 cards"
            ),
            inline=False,
        )
        e3.add_field(
            name="🎨 Creator Packs (`/packs`)",
            value="Hand-curated packs by the community. Browse by genre: EDM, Rock, R&B, Pop, Hip Hop.",
            inline=False,
        )
        e3.add_field(
            name="✨ Rarity Tiers",
            value="⚪ Common → 🔵 Rare → 🟣 Epic → 👑 Legendary → 💎 Mythic",
            inline=False,
        )
        e3.set_footer(text="🎵 Music Legends • Higher rarity = more battle power!")
        await ch.send(embed=e3)

        # ── 4. Battles ─────────────────────────────────────────────
        e4 = discord.Embed(
            title="⚔️ Battles",
            description="Challenge any player to a card battle for gold and XP.",
            color=PINK,
        )
        e4.set_author(name="Music Legends", icon_url=LOGO_URL)
        e4.add_field(
            name="How to Battle",
            value=(
                "1. Run `/battle @opponent` or use the Battle button in the User Hub\n"
                "2. Pick a wager tier\n"
                "3. Each player selects a card from their collection\n"
                "4. Stats are compared — highest wins the round\n"
                "5. Best of 3 wins the match"
            ),
            inline=False,
        )
        e4.add_field(
            name="💰 Wager Tiers",
            value=(
                "🟢 **Casual** 50g → Winner gets 100g + 25 XP\n"
                "🔵 **Standard** 100g → Winner gets 175g + 38 XP\n"
                "🟣 **High Stakes** 250g → Winner gets 350g + 50 XP\n"
                "🔴 **Extreme** 500g → Winner gets 650g + 75 XP"
            ),
            inline=False,
        )
        e4.add_field(
            name="⚡ Card Power",
            value=(
                "Power = average of Impact, Skill, Longevity, Culture, Hype stats\n"
                "Rarity bonuses: Common +0 • Rare +5 • Epic +10 • Legendary +20 • Mythic +35"
            ),
            inline=False,
        )
        e4.set_footer(text="🎵 Music Legends • 15% chance of critical hits for 1.5x damage!")
        await ch.send(embed=e4)

        # ── 5. Commands Quick Reference ────────────────────────────
        e5 = discord.Embed(
            title="📋 Quick Command Reference",
            color=GOLD,
        )
        e5.set_author(name="Music Legends", icon_url=LOGO_URL)
        e5.add_field(
            name="🎴 Cards",
            value=(
                "`/collection` — Browse your cards\n"
                "`/view <id>` — Inspect a specific card\n"
                "`/deck` — See your battle deck\n"
                "`/pack` — Open a pack you own"
            ),
            inline=True,
        )
        e5.add_field(
            name="⚔️ Battles",
            value=(
                "`/battle @user` — Challenge someone\n"
                "`/battle_stats` — Your win/loss record\n"
                "`/leaderboard` — Global rankings\n"
                "`/stats` — Overall stats"
            ),
            inline=True,
        )
        e5.add_field(
            name="📦 Packs & Economy",
            value=(
                "`/packs` — Browse creator packs\n"
                "`/buy_pack` — Buy a tier pack\n"
                "`/daily` — Claim daily reward\n"
                "`/season_progress` — Season rank"
            ),
            inline=True,
        )
        e5.set_footer(text="🎵 Music Legends • Good luck, Legend! 👑")
        await ch.send(embed=e5)


async def setup(bot):
    await bot.add_cog(GameInfoCog(bot))
