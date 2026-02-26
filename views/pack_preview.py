# views/pack_preview.py
"""
Pack Preview View - Shows card previews before finalization
Allows users to re-roll stats or change song selection
"""

import discord
from discord import Interaction
from typing import List, Dict, Callable
import random


class PackPreviewView(discord.ui.View):
    """View for previewing pack cards before finalization"""
    
    def __init__(
        self,
        pack_name: str,
        artist_name: str,
        cards_preview: List[Dict],
        pack_type: str,
        on_confirm: Callable,
        on_reroll: Callable,
        on_change_songs: Callable
    ):
        super().__init__(timeout=300)
        self.pack_name = pack_name
        self.artist_name = artist_name
        self.cards_preview = cards_preview
        self.pack_type = pack_type
        self.on_confirm = on_confirm
        self.on_reroll = on_reroll
        self.on_change_songs = on_change_songs
        self.reroll_count = 0
        self.max_rerolls = 3
    
    def create_preview_embed(self) -> discord.Embed:
        """Create the preview embed showing all cards"""
        
        embed = discord.Embed(
            title=f"🎴 Pack Preview: {self.pack_name}",
            description=f"**Artist:** {self.artist_name}\n**Type:** {self.pack_type.title()} Pack\n\n"
                       f"Review your cards before finalizing. You can re-roll stats up to {self.max_rerolls} times.",
            color=discord.Color.gold() if self.pack_type == 'gold' else discord.Color.blue()
        )
        
        # Rarity emoji mapping
        rarity_emoji = {
            'common': '⚪',
            'rare': '🔵',
            'epic': '🟣',
            'legendary': '🟡',
            'mythic': '🔴'
        }
        
        # Show each card
        for i, card in enumerate(self.cards_preview, 1):
            emoji = rarity_emoji.get(card['rarity'], '⚪')
            stats_avg = (card['attack'] + card['defense'] + card['speed']) // 3
            
            card_info = (
                f"{emoji} **{card['rarity'].upper()}**\n"
                f"⚔️ ATK: {card['attack']} | 🛡️ DEF: {card['defense']} | ⚡ SPD: {card['speed']}\n"
                f"💪 Power: {stats_avg}"
            )
            
            embed.add_field(
                name=f"{i}. {card['name']}",
                value=card_info,
                inline=False
            )
        
        # Rarity distribution
        rarity_counts = {}
        for card in self.cards_preview:
            rarity = card['rarity']
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        rarity_text = " • ".join([
            f"{count} {rarity.title()}"
            for rarity, count in sorted(rarity_counts.items())
        ])
        
        embed.add_field(
            name="📊 Rarity Distribution",
            value=rarity_text,
            inline=False
        )
        
        # Total power
        total_power = sum((c['attack'] + c['defense'] + c['speed']) // 3 for c in self.cards_preview)
        avg_power = total_power // len(self.cards_preview)
        
        embed.add_field(
            name="💎 Pack Stats",
            value=f"Total Power: {total_power} | Average: {avg_power}",
            inline=False
        )
        
        # Re-roll counter
        if self.reroll_count > 0:
            embed.set_footer(text=f"🎲 Re-rolled {self.reroll_count}/{self.max_rerolls} times")
        else:
            embed.set_footer(text="💡 Tip: Re-roll to get different stats, or confirm to create your pack!")
        
        return embed
    
    @discord.ui.button(label="✅ Confirm & Create", style=discord.ButtonStyle.success, row=0)
    async def confirm_button(self, interaction: Interaction, button: discord.ui.Button):
        """Confirm and finalize pack creation"""
        await interaction.response.defer()
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(
            content="✨ Creating your pack...",
            view=self
        )
        
        # Call the confirm callback
        await self.on_confirm(interaction, self.cards_preview)
        self.stop()
    
    @discord.ui.button(label="🎲 Re-roll Stats", style=discord.ButtonStyle.primary, row=0)
    async def reroll_button(self, interaction: Interaction, button: discord.ui.Button):
        """Re-roll card stats"""
        
        if self.reroll_count >= self.max_rerolls:
            await interaction.response.send_message(
                f"❌ You've reached the maximum of {self.max_rerolls} re-rolls!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        self.reroll_count += 1
        
        # Re-roll stats for all cards
        self.cards_preview = await self.on_reroll(self.cards_preview)
        
        # Update the embed
        embed = self.create_preview_embed()
        
        # Disable re-roll button if max reached
        if self.reroll_count >= self.max_rerolls:
            button.disabled = True
            button.label = "🎲 Max Re-rolls Reached"
        
        await interaction.edit_original_response(
            embed=embed,
            view=self
        )
    
    @discord.ui.button(label="🔄 Change Songs", style=discord.ButtonStyle.secondary, row=0)
    async def change_songs_button(self, interaction: Interaction, button: discord.ui.Button):
        """Go back to song selection"""
        await interaction.response.defer()
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(
            content="🔄 Going back to song selection...",
            view=self
        )
        
        # Call the change songs callback
        await self.on_change_songs(interaction)
        self.stop()
    
    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger, row=1)
    async def cancel_button(self, interaction: Interaction, button: discord.ui.Button):
        """Cancel pack creation"""
        await interaction.response.send_message(
            "❌ Pack creation cancelled.",
            ephemeral=True
        )
        self.stop()


def reroll_card_stats(card: Dict, pack_type: str = 'community') -> Dict:
    """
    Re-roll stats for a single card
    
    Args:
        card: Card data dict
        pack_type: 'community' or 'gold'
    
    Returns:
        Card with new stats
    """
    # Stat ranges based on pack type
    if pack_type == 'gold':
        stat_min, stat_max = 70, 92
        rarity_boost = 10
    else:
        stat_min, stat_max = 50, 85
        rarity_boost = 0
    
    # Generate new stats
    base_stat = random.randint(stat_min, stat_max)
    
    new_stats = {
        'attack': max(stat_min, min(stat_max, base_stat + random.randint(-10, 10))),
        'defense': max(stat_min, min(stat_max, base_stat + random.randint(-10, 10))),
        'speed': max(stat_min, min(stat_max, base_stat + random.randint(-10, 10)))
    }
    
    # Determine new rarity
    avg_stat = (new_stats['attack'] + new_stats['defense'] + new_stats['speed']) / 3 + rarity_boost
    
    if avg_stat >= 85:
        new_rarity = "mythic"
    elif avg_stat >= 75:
        new_rarity = "legendary"
    elif avg_stat >= 65:
        new_rarity = "epic"
    elif avg_stat >= 55:
        new_rarity = "rare"
    else:
        new_rarity = "common"
    
    # Update card
    card['attack'] = new_stats['attack']
    card['defense'] = new_stats['defense']
    card['speed'] = new_stats['speed']
    card['rarity'] = new_rarity
    
    return card


async def reroll_all_cards(cards: List[Dict], pack_type: str = 'community') -> List[Dict]:
    """
    Re-roll stats for all cards in the pack
    
    Args:
        cards: List of card data dicts
        pack_type: 'community' or 'gold'
    
    Returns:
        List of cards with new stats
    """
    return [reroll_card_stats(card.copy(), pack_type) for card in cards]
