# discord_cards.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Literal
import discord

Rarity = Literal["Common", "Rare", "Epic", "Legendary", "Mythic"]

RARITY_COLOR = {
    "Common": discord.Color.light_grey(),
    "Rare": discord.Color.blue(),
    "Epic": discord.Color.purple(),
    "Legendary": discord.Color.gold(),
    "Mythic": discord.Color.red(),
}

RARITY_EMOJI = {
    "Common": "🟩",
    "Rare": "🟦",
    "Epic": "🟪",
    "Legendary": "⭐",
    "Mythic": "🔴",
}

@dataclass
class ArtistCard:
    card_id: str
    name: str
    title: str
    rarity: Rarity
    era: str
    variant: str
    image_url: Optional[str] = None
    impact: int = 0
    skill: int = 0
    longevity: int = 0
    culture: int = 0
    hype: int = 0
    spotify_url: Optional[str] = None
    youtube_url: Optional[str] = None

@dataclass
class SongCard:
    card_id: str
    title: str
    artist_name: str
    rarity: Rarity
    effect_name: str
    effect_text: str
    image_url: Optional[str] = None
    spotify_url: Optional[str] = None
    youtube_url: Optional[str] = None

@dataclass
class PackDrop:
    label: str  # e.g., "Daily Pack"
    guaranteed: str  # e.g., "Rare+ Guaranteed"
    items: List[str]  # preformatted lines

def _stat_block(a: ArtistCard) -> str:
    return (
        f"**Impact:** {a.impact}\n"
        f"**Skill:** {a.skill}\n"
        f"**Longevity:** {a.longevity}\n"
        f"**Culture:** {a.culture}\n"
        f"**Hype:** {a.hype} *(tiebreaker)*"
    )

def build_artist_embed(card: ArtistCard) -> discord.Embed:
    emoji = RARITY_EMOJI.get(card.rarity, "🎴")
    e = discord.Embed(
        title=f"{emoji} {card.rarity} — ARTIST CARD",
        description=f"**{card.name} — \"{card.title}\"**\n`ID: {card.card_id} • Variant: {card.variant} • Era: {card.era}`",
        color=RARITY_COLOR.get(card.rarity, discord.Color.dark_grey()),
    )
    e.add_field(name="Stats", value=_stat_block(card), inline=False)

    links = []
    if card.spotify_url:
        links.append(f"🎧 Spotify: {card.spotify_url}")
    if card.youtube_url:
        links.append(f"▶️ YouTube: {card.youtube_url}")
    if links:
        e.add_field(name="Links", value="\n".join(links), inline=False)

    if card.image_url:
        e.set_thumbnail(url=card.image_url)

    e.set_footer(text="Music Legends • Stats-based duels (Option A)")
    return e

def build_song_embed(card: SongCard) -> discord.Embed:
    emoji = RARITY_EMOJI.get(card.rarity, "🎵")
    e = discord.Embed(
        title=f"{emoji} {card.rarity} — SONG CARD",
        description=f"**\"{card.title}\" — {card.artist_name}**\n`ID: {card.card_id}`",
        color=RARITY_COLOR.get(card.rarity, discord.Color.dark_grey()),
    )
    e.add_field(name=f"Ability: {card.effect_name}", value=card.effect_text, inline=False)

    links = []
    if card.spotify_url:
        links.append(f"🎧 Spotify: {card.spotify_url}")
    if card.youtube_url:
        links.append(f"▶️ YouTube: {card.youtube_url}")
    if links:
        e.add_field(name="Links", value="\n".join(links), inline=False)

    if card.image_url:
        e.set_thumbnail(url=card.image_url)

    e.set_footer(text="Song cards are optional support (1 use per match).")
    return e

class PackOpenView(discord.ui.View):
    def __init__(self, card_ids: List[str] = None, db_manager=None, *, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.card_ids = card_ids or []
        self.db_manager = db_manager

    @discord.ui.button(label="Save to Collection", style=discord.ButtonStyle.success)
    async def save(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.db_manager and self.card_ids:
            # Cards are already saved to database via record_pack_opening
            await interaction.response.send_message("✅ Cards saved to your collection!", ephemeral=True)
        else:
            await interaction.response.send_message("Cards automatically saved to collection!", ephemeral=True)

    @discord.ui.button(label="Share Pull", style=discord.ButtonStyle.primary)
    async def share(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.card_ids:
            # Create share text
            card_list = ", ".join(self.card_ids[:3])
            if len(self.card_ids) > 3:
                card_list += f" and {len(self.card_ids) - 3} more"
            
            await interaction.response.send_message(
                f"🎴 Just pulled: {card_list}! #MusicLegends",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Share feature coming soon!", ephemeral=True)

    @discord.ui.button(label="Open Another Pack", style=discord.ButtonStyle.secondary)
    async def open_more(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Use `/pack` to open more packs!", ephemeral=True)

def build_pack_open_embed(drop: PackDrop) -> discord.Embed:
    e = discord.Embed(
        title=f"📦 Pack Opened: {drop.label}",
        description=f"Drop Rule: **{drop.guaranteed}**",
        color=discord.Color.blurple(),
    )
    e.add_field(name="You received", value="\n".join(drop.items), inline=False)
    e.set_footer(text="Tip: PvP wins grant Victory Pack Tokens.")
    return e

def build_pvp_result_embed(
    player_a_name: str,
    player_b_name: str,
    winner_name: str,
    rounds_text: str,
    reward_text: str = "+1 Victory Pack Token"
) -> discord.Embed:
    e = discord.Embed(
        title=f"⚔️ Duel Result: {player_a_name} vs {player_b_name}",
        description="Mode: **Best of 3** • Rule: **Option A**",
        color=discord.Color.green(),
    )
    e.add_field(name="Rounds", value=rounds_text, inline=False)
    e.add_field(name="Winner", value=f"🏆 **{winner_name}**\n🎁 Reward: **{reward_text}**", inline=False)
    e.set_footer(text="Option A: R1 random • R2 loser chooses • R3 random")
    return e
