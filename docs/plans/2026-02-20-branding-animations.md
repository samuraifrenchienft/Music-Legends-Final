# Music Legends Branding & Animations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Apply the Music Legends brand identity (colors, logo, banner) across all embeds and add multi-phase animations to pack opening, daily claim, drops, and the game info post command.

**Architecture:** Centralize all brand constants in `ui/brand.py` (single source of truth), then update all embed-producing code to import from it. Animation enhancements edit existing handlers in-place — no new views needed except a new `/post_game_info` admin command.

**Tech Stack:** discord.py, asyncio, existing `views/pack_opening.py` framework.

**Assets:**
- Logo: `https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeiehxk5zhdxidab4qtuxg6lblrasxcxb2bkj6a3ipyjue5f7pzo3qi`
- Banner: `https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeibftmlnx5rwio4jvxjimzvk3q5lq5vm2jl5aggmzaws5qgzzpsq6i`

---

### Task 1: Create `ui/brand.py` — brand constants and helpers

**Files:**
- Create: `ui/brand.py`

**Step 1: Create the file**

```python
# ui/brand.py
"""
Music Legends Brand Constants
Single source of truth for colors, assets, and embed decoration.
"""
import discord
from typing import Dict

# ── Color palette (from logo) ─────────────────────────────────────
GOLD    = 0xF4A800   # Crown / main text
PURPLE  = 0x6B2EBE   # Outer glow halo
BLUE    = 0x4488FF   # Neon ring highlight
NAVY    = 0x0D0B2E   # Dark interior
PINK    = 0xFF4E9A   # Sparkle accent / warnings
GREEN   = 0x2ECC71   # Success
RED     = 0xE74C3C   # Error / crit

# ── Assets ───────────────────────────────────────────────────────
LOGO_URL   = "https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeiehxk5zhdxidab4qtuxg6lblrasxcxb2bkj6a3ipyjue5f7pzo3qi"
BANNER_URL = "https://olive-generous-kangaroo-378.mypinata.cloud/ipfs/bafybeibftmlnx5rwio4jvxjimzvk3q5lq5vm2jl5aggmzaws5qgzzpsq6i"

# ── Rarity system ────────────────────────────────────────────────
RARITY = {
    "common":    {"color": 0x95A5A6, "emoji": "⚪", "badge": "⚪ Common",    "bar_color": "░"},
    "rare":      {"color": BLUE,     "emoji": "🔵", "badge": "🔵 Rare",      "bar_color": "▒"},
    "epic":      {"color": PURPLE,   "emoji": "🟣", "badge": "🟣 Epic",      "bar_color": "▓"},
    "legendary": {"color": GOLD,     "emoji": "👑", "badge": "👑 Legendary", "bar_color": "█"},
    "mythic":    {"color": PINK,     "emoji": "💎", "badge": "💎 Mythic",    "bar_color": "█"},
}

POWER_TIERS = [
    (120, "💫 S-Tier"),
    (100, "⚡ A-Tier"),
    (80,  "🔥 B-Tier"),
    (60,  "🎵 C-Tier"),
    (0,   "🎶 D-Tier"),
]

# ── Helpers ──────────────────────────────────────────────────────
def stat_bar(value: int, max_val: int = 100, length: int = 10) -> str:
    """Return emoji progress bar: ████████░░ 80"""
    filled = round((value / max_val) * length)
    filled = max(0, min(length, filled))
    return f"{'█' * filled}{'░' * (length - filled)} {value}"


def power_tier(power: int) -> str:
    for threshold, label in POWER_TIERS:
        if power >= threshold:
            return label
    return "🎶 D-Tier"


def rarity_color(rarity: str) -> int:
    return RARITY.get(rarity.lower(), RARITY["common"])["color"]


def rarity_badge(rarity: str) -> str:
    return RARITY.get(rarity.lower(), RARITY["common"])["badge"]


def rarity_emoji(rarity: str) -> str:
    return RARITY.get(rarity.lower(), RARITY["common"])["emoji"]


def brand_embed(title: str, description: str = "", color: int = PURPLE) -> discord.Embed:
    """Create a pre-branded embed with logo author."""
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name="Music Legends", icon_url=LOGO_URL)
    embed.set_footer(text="🎵 Music Legends")
    return embed


def apply_branding(embed: discord.Embed) -> discord.Embed:
    """Add author + footer to an existing embed."""
    embed.set_author(name="Music Legends", icon_url=LOGO_URL)
    if not embed.footer.text:
        embed.set_footer(text="🎵 Music Legends")
    return embed
```

**Step 2: Verify import works**

```bash
cd C:\Users\AbuBa\Desktop\Music-Legends
python -c "from ui.brand import GOLD, brand_embed, stat_bar; print(stat_bar(75))"
```
Expected: `████████░░ 75`

**Step 3: Commit**

```bash
git add ui/brand.py
git commit -m "feat: add brand constants and embed helpers (ui/brand.py)"
```

---

### Task 2: Apply brand colors to `views/pack_opening.py`

**Files:**
- Modify: `views/pack_opening.py`

**Step 1: Replace RARITY_CONFIG and all generic colors**

At the top of the file, add:
```python
from ui.brand import LOGO_URL, BANNER_URL, brand_embed, stat_bar, power_tier, rarity_color, rarity_badge, rarity_emoji, GOLD, PURPLE, BLUE, NAVY, PINK, GREEN
```

Replace `RARITY_CONFIG` dict entirely:
```python
RARITY_CONFIG = {
    'common':    {'color': 0x95A5A6, 'emoji': '⚪', 'effect': '',        'name': 'Common'},
    'rare':      {'color': BLUE,     'emoji': '🔵', 'effect': '✨',       'name': 'Rare'},
    'epic':      {'color': PURPLE,   'emoji': '🟣', 'effect': '✨✨',     'name': 'Epic'},
    'legendary': {'color': GOLD,     'emoji': '👑', 'effect': '⭐✨',     'name': 'Legendary'},
    'mythic':    {'color': PINK,     'emoji': '💎', 'effect': '🔥✨💎',   'name': 'Mythic'},
}
```

**Step 2: Update `create_loading_embed`**

Replace method body:
```python
def create_loading_embed(self) -> discord.Embed:
    embed = discord.Embed(
        title="🎁 Opening Pack...",
        description=(
            f"**{self.pack_name}**\n\n"
            "⏳ Shuffling cards...\n"
            "🔮 The universe is deciding your fate...\n"
            "✨ Preparing your rewards..."
        ),
        color=GOLD,
    )
    embed.set_author(name="Music Legends", icon_url=LOGO_URL)
    embed.set_image(url=BANNER_URL)
    embed.set_footer(text="🎵 Music Legends • Get ready!")
    return embed
```

**Step 3: Update `create_legendary_teaser_embed`**

```python
def create_legendary_teaser_embed(self) -> discord.Embed:
    embed = discord.Embed(
        title="👑 LEGENDARY PULL! 👑",
        description="🌟 Something incredible is incoming...\n\n⭐ **LEGENDARY CARD DETECTED!** ⭐\n\n💎💎💎💎💎",
        color=GOLD,
    )
    embed.set_author(name="Music Legends", icon_url=LOGO_URL)
    embed.set_image(url=self.CELEBRATION_GIFS['legendary'])
    embed.set_footer(text="🎵 Music Legends • Brace yourself!")
    return embed
```

**Step 4: Update `create_card_reveal_embed` — add stat bars and power tier**

Replace the stats_text and embed construction block:
```python
rarity = card.get('rarity', 'common').lower()
config = self.RARITY_CONFIG.get(rarity, self.RARITY_CONFIG['common'])

impact    = card.get('impact',    card.get('attack',  50))
skill     = card.get('skill',     card.get('defense', 50))
longevity = card.get('longevity', card.get('speed',   50))
culture   = card.get('culture',   50)
hype      = card.get('hype',      50)
power_val = (impact + skill + longevity + culture + hype) // 5

embed = discord.Embed(
    title=f"{config['emoji']} Card {card_number}/{total_cards} {config['effect']}",
    description=(
        f"**{card['name']}**\n"
        f"{rarity_badge(rarity)}\n\n"
        f"{'🔄 **DUPLICATE** — Added to collection' if is_duplicate else '🆕 **NEW CARD!**'}"
    ),
    color=config['color'],
)
embed.set_author(name="Music Legends", icon_url=LOGO_URL)

stats_text = (
    f"🎤 Impact:    {stat_bar(impact)}\n"
    f"🎸 Skill:     {stat_bar(skill)}\n"
    f"⏳ Longevity: {stat_bar(longevity)}\n"
    f"🌍 Culture:   {stat_bar(culture)}\n"
    f"🔥 Hype:      {stat_bar(hype)}"
)
embed.add_field(name="📊 Stats", value=f"```{stats_text}```", inline=False)
embed.add_field(name="⚡ Power", value=f"**{power_val}** — {power_tier(power_val)}", inline=True)

if card.get('image_url'):
    from services.image_cache import safe_image
    embed.set_image(url=safe_image(card['image_url']))

embed.set_footer(text=f"🎵 Music Legends • {card_number}/{total_cards} revealed")
```

**Step 5: Update `create_summary_embed`**

Replace color and branding in summary:
```python
embed = discord.Embed(
    title="✅ Pack Opened!",
    description=f"**{self.pack_name}**\n\nAll cards have been added to your collection!",
    color=GREEN,
)
embed.set_author(name="Music Legends", icon_url=LOGO_URL)
embed.set_thumbnail(url=LOGO_URL)
embed.set_footer(text="🎵 Music Legends • Check your collection via the User Hub!")
```

**Step 6: Add mythic phase to `animate_pack_opening`**

After the existing legendary teaser block, add a mythic teaser:
```python
elif rarity == 'mythic':
    mythic_embed = discord.Embed(
        title="💎 MYTHIC PULL! 💎",
        description="🔥 **BEYOND LEGENDARY...** 🔥\n\n💎 **MYTHIC CARD INCOMING!** 💎\n\n🔥💎🔥💎🔥",
        color=PINK,
    )
    mythic_embed.set_author(name="Music Legends", icon_url=LOGO_URL)
    mythic_embed.set_footer(text="🎵 Music Legends • The rarest of the rare!")
    try:
        await interaction.edit_original_response(embed=mythic_embed, view=skip_view)
    except discord.NotFound:
        pass
    await asyncio.sleep(2.5)
```

**Step 7: Verify**

```bash
python -c "from views.pack_opening import PackOpeningAnimator; print('OK')"
```

**Step 8: Commit**

```bash
git add views/pack_opening.py
git commit -m "feat: apply brand colors + stat bars + power tiers to pack opening animator"
```

---

### Task 3: Add multi-phase animation to daily claim (`cogs/menu_system.py`)

**Files:**
- Modify: `cogs/menu_system.py` (around line 499)

**Step 1: Add import at top of file**

```python
from ui.brand import GOLD, PURPLE, BLUE, PINK, GREEN, NAVY, LOGO_URL, BANNER_URL, brand_embed, stat_bar, power_tier, rarity_badge, rarity_emoji
```

**Step 2: Replace `daily_button` handler entirely**

Find the `daily_button` method (line ~497) and replace its body:

```python
async def daily_button(self, interaction: Interaction, button: discord.ui.Button):
    """Claim daily reward — multi-phase animation"""
    await interaction.response.defer(ephemeral=True)

    # ── Phase 1: suspense ──────────────────────────────────────
    phase1 = discord.Embed(
        title="🎁 Preparing Your Daily Reward...",
        description="✨ Checking your streak...\n🔮 Rolling your free pack...\n⏳ Almost ready!",
        color=PURPLE,
    )
    phase1.set_author(name="Music Legends", icon_url=LOGO_URL)
    phase1.set_image(url=BANNER_URL)
    phase1.set_footer(text="🎵 Music Legends • Daily claim")
    msg = await interaction.followup.send(embed=phase1, ephemeral=True, wait=True)

    await asyncio.sleep(2.0)

    # ── Fetch reward ───────────────────────────────────────────
    result = self.db.claim_daily_reward(interaction.user.id)

    if not result.get('success'):
        err = discord.Embed(
            title="⏰ Already Claimed!",
            description=result.get('error', 'You already claimed today. Come back tomorrow!'),
            color=PINK,
        )
        err.set_author(name="Music Legends", icon_url=LOGO_URL)
        err.set_footer(text="🎵 Music Legends")
        await msg.edit(embed=err)
        return

    # ── Phase 2: gold + streak reveal ─────────────────────────
    streak = result.get('streak', 1)
    gold   = result.get('gold', 0)
    tickets = result.get('tickets', 0)
    streak_bonus = "🔥 Streak Bonus!" if streak >= 7 else ""

    phase2 = discord.Embed(
        title="💰 Daily Reward Unlocked!",
        description=f"**{streak_bonus}**\n\n💰 **+{gold:,} Gold**\n🔥 **{streak} day streak**" +
                    (f"\n🎫 **+{tickets} Tickets**" if tickets else ""),
        color=GOLD,
    )
    phase2.set_author(name="Music Legends", icon_url=LOGO_URL)
    phase2.set_thumbnail(url=LOGO_URL)
    phase2.set_footer(text="🎵 Music Legends • And that's not all...")
    await msg.edit(embed=phase2)

    await asyncio.sleep(2.0)

    # ── Phase 3: free pack card reveal ────────────────────────
    cards = result.get('cards') or []
    pack_name = result.get('pack_name') or 'Daily Pack'

    phase3 = discord.Embed(
        title=f"🎴 {pack_name}",
        description=f"Your daily free pack contains **{len(cards)} card(s)**!" if cards
                    else "No cards available today — check back tomorrow!",
        color=BLUE,
    )
    phase3.set_author(name="Music Legends", icon_url=LOGO_URL)

    if cards:
        lines = []
        for card in cards[:5]:
            r = (card.get('rarity') or 'common').lower()
            lines.append(f"{rarity_emoji(r)} **{card.get('name', 'Unknown')}** — {rarity_badge(r)}")
        if len(cards) > 5:
            lines.append(f"...+{len(cards) - 5} more")
        phase3.add_field(name="🎴 Cards Received", value="\n".join(lines), inline=False)

    phase3.set_footer(text="🎵 Music Legends • See you tomorrow!")
    await msg.edit(embed=phase3)
```

**Step 3: Verify import**

```bash
python -c "import cogs.menu_system; print('OK')"
```

**Step 4: Commit**

```bash
git add cogs/menu_system.py
git commit -m "feat: 3-phase daily claim animation with brand colors"
```

---

### Task 4: Add countdown animation to drops (`cogs/gameplay.py`)

**Files:**
- Modify: `cogs/gameplay.py` (around line 354)

**Step 1: Add import at top**

```python
from ui.brand import GOLD, PURPLE, BLUE, PINK, GREEN, NAVY, LOGO_URL, BANNER_URL
```

**Step 2: Replace `drop_command` embed and add countdown**

Find the `drop_command` method body after the pack lookup and replace the embed + send block:

```python
tier_colors = {
    "community": BLUE,
    "gold":      GOLD,
    "platinum":  PURPLE,
}
tier_emoji = {"community": "⚪", "gold": "👑", "platinum": "💎"}.get(tier, "⚪")

# ── Phase 1: incoming drop alert ──────────────────────────────
alert_embed = discord.Embed(
    title=f"📦 PACK DROP INCOMING! {tier_emoji}",
    description=f"**{pack['name']}**\n{pack['pack_size']} cards up for grabs!\n\n**Dropping in...**",
    color=tier_colors.get(tier, GOLD),
)
alert_embed.set_author(name="Music Legends", icon_url=LOGO_URL)
alert_embed.set_image(url=BANNER_URL)
alert_embed.set_footer(text="🎵 Music Legends • Be ready!")
await interaction.response.send_message(embed=alert_embed)
msg = await interaction.original_response()

# ── Countdown 3 → 2 → 1 ──────────────────────────────────────
for count in ["3️⃣", "2️⃣", "1️⃣"]:
    await asyncio.sleep(1.0)
    cd = discord.Embed(
        title=f"📦 PACK DROP! {count}",
        description=f"**{pack['name']}**\n{pack['pack_size']} cards • First to click wins!",
        color=tier_colors.get(tier, GOLD),
    )
    cd.set_author(name="Music Legends", icon_url=LOGO_URL)
    cd.set_footer(text="🎵 Music Legends • Get ready!")
    await msg.edit(embed=cd)

# ── Phase 2: drop live ─────────────────────────────────────────
await asyncio.sleep(0.5)
drop_embed = discord.Embed(
    title=f"{tier_emoji} DROP IS LIVE! {tier_emoji}",
    description=f"**{pack['name']}**\nFirst to click claims all **{pack['pack_size']}** cards!",
    color=tier_colors.get(tier, GOLD),
)
drop_embed.set_author(name="Music Legends", icon_url=LOGO_URL)
drop_embed.set_thumbnail(url=LOGO_URL)
if pack.get("genre"):
    drop_embed.add_field(name="🎵 Genre", value=pack["genre"], inline=True)
drop_embed.add_field(name="📦 Tier", value=tier.title(), inline=True)
drop_embed.add_field(name="🎴 Cards", value=str(pack["pack_size"]), inline=True)
drop_embed.set_footer(text=f"🎵 Music Legends • Dropped by {interaction.user.display_name} • Expires in 5 min")

view = CardDropView(pack=pack, db=self.db, timeout=300)
await msg.edit(embed=drop_embed, view=view)
view.message = msg
```

**Step 3: Add asyncio import if missing**

```bash
grep -n "import asyncio" cogs/gameplay.py
```
If not present, add `import asyncio` at top.

**Step 4: Commit**

```bash
git add cogs/gameplay.py
git commit -m "feat: countdown drop animation with brand colors"
```

---

### Task 5: Apply brand colors to battle embeds (`cogs/battle_commands.py`)

**Files:**
- Modify: `cogs/battle_commands.py`

**Step 1: Add import**

```python
from ui.brand import GOLD, PURPLE, BLUE, PINK, GREEN, NAVY, LOGO_URL, stat_bar, power_tier, rarity_badge
```

**Step 2: Replace all hardcoded hex colors**

Find and replace:
- `color=0xf39c12` → `color=GOLD`
- `color=0x9b59b6` → `color=PURPLE`
- `color=0x3498db` → `color=BLUE`
- `color=0xe74c3c` → `color=PINK` (crit hit)
- `color=discord.Color.green()` → `color=GREEN`
- `color=discord.Color.red()` → `color=PINK`

**Step 3: Add author + footer to all battle embeds**

For each `discord.Embed(...)` in battle_commands.py that doesn't already have it, add after construction:
```python
embed.set_author(name="Music Legends", icon_url=LOGO_URL)
```

**Step 4: Enhance card reveal embeds with stat bars**

In the card reveal section of `execute_battle()`, where card stats are shown, replace raw number display with:
```python
embed.add_field(
    name="📊 Stats",
    value=f"```🎤 Impact:    {stat_bar(card.impact)}\n🎸 Skill:     {stat_bar(card.skill)}\n⏳ Longevity: {stat_bar(card.longevity)}\n🌍 Culture:   {stat_bar(card.culture)}\n🔥 Hype:      {stat_bar(card.hype)}```",
    inline=False,
)
embed.add_field(name="⚡ Power", value=f"**{power_val}** — {power_tier(power_val)}", inline=True)
```

**Step 5: Commit**

```bash
git add cogs/battle_commands.py
git commit -m "feat: brand colors + stat bars in battle embeds"
```

---

### Task 6: Apply brand colors to `cogs/menu_system.py` (non-daily embeds)

**Files:**
- Modify: `cogs/menu_system.py`

**Step 1: Bulk replace generic colors (already has brand import from Task 3)**

Find and replace all remaining generic colors:
- `discord.Color.blue()` → `discord.Color(BLUE)`
- `discord.Color.gold()` → `discord.Color(GOLD)`
- `discord.Color.purple()` → `discord.Color(PURPLE)`
- `discord.Color.green()` → `discord.Color(GREEN)`
- `discord.Color.red()` → `discord.Color(PINK)`
- `discord.Color.orange()` → `discord.Color(GOLD)`
- `discord.Color.greyple()` → `discord.Color(NAVY)`
- `discord.Color.light_grey()` → `discord.Color(NAVY)`

**Step 2: Add `apply_branding` to the main UserHubView embed**

Find where the main hub embed is created (around line 160) and add:
```python
embed.set_author(name="Music Legends", icon_url=LOGO_URL)
embed.set_image(url=BANNER_URL)
```

**Step 3: Add branding to start_game embed (`cogs/start_game.py`)**

In `start_game.py`, add import and update the embed:
```python
from ui.brand import PURPLE, LOGO_URL, BANNER_URL
# In the embed:
embed = discord.Embed(title="🎵🎮 MUSIC LEGENDS IS NOW LIVE! 🎮🎵", description=..., color=PURPLE)
embed.set_author(name="Music Legends", icon_url=LOGO_URL)
embed.set_image(url=BANNER_URL)
embed.set_footer(text="🎵 Music Legends • Use /help for all commands")
```

**Step 4: Commit**

```bash
git add cogs/menu_system.py cogs/start_game.py
git commit -m "feat: apply brand colors across menu_system and start_game embeds"
```

---

### Task 7: Create `/post_game_info` command — intro thread post

**Files:**
- Create: `cogs/game_info.py`
- Modify: `main.py` (add cog load)

**Step 1: Create the cog**

```python
# cogs/game_info.py
"""
/post_game_info — Posts a multi-embed intro thread in the current channel.
Admin-only. Covers: Welcome, How to Play, Packs, Battles, Season, Commands.
"""
import discord
from discord import app_commands, Interaction
from discord.ext import commands
from ui.brand import GOLD, PURPLE, BLUE, PINK, GREEN, NAVY, LOGO_URL, BANNER_URL


class GameInfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="post_game_info", description="📋 Post the full game guide in this channel (admin only)")
    async def post_game_info(self, interaction: Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("🔒 Admins only.", ephemeral=True)
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
                "**Everything starts with the User Hub — find it in this server and click Daily Claim to begin!**"
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

        # ── 3. Packs ───────────────────────────────────────────────
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
```

**Step 2: Load cog in `main.py`**

Find the cog loading list in `main.py` and add:
```python
"cogs.game_info",
```

**Step 3: Verify**

```bash
python -c "import cogs.game_info; print('OK')"
```

**Step 4: Commit**

```bash
git add cogs/game_info.py main.py
git commit -m "feat: /post_game_info command — branded multi-embed game guide"
```

---

### Task 8: Run tests and deploy

**Step 1: Run full test suite**

```bash
cd C:\Users\AbuBa\Desktop\Music-Legends
python -m pytest tests/test_bot_core.py -v --noconftest
```
Expected: All 34 tests pass.

**Step 2: Force Railway rebuild**

In `Dockerfile`, bump `CACHE_BUST`:
```dockerfile
ENV CACHE_BUST=9
```
Add a date comment to `railway.toml`:
```toml
# deploy: 2026-02-20 branding + animations
```

**Step 3: Final commit and push**

```bash
git add Dockerfile railway.toml
git commit -m "chore: bump cache bust for branding + animations deploy"
git push
```

**Step 4: Verify Railway logs**

Watch Railway logs for:
- `✅ Cog loaded: game_info`
- No import errors on `ui.brand`
- Bot comes online
