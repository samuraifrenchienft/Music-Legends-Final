# views/pack_opening.py
"""
Pack Opening Animation System
Sequential card reveals with rarity-specific effects
"""

import discord
from discord import Interaction
import asyncio
from typing import List, Dict


class SkipView(discord.ui.View):
    """View with skip button for pack opening"""
    def __init__(self):
        super().__init__(timeout=30)
        self.skipped = False
    
    @discord.ui.button(label="Skip ⏩", style=discord.ButtonStyle.secondary)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip the animation and show all cards"""
        self.skipped = True
        await interaction.response.defer()
        self.stop()


class PackOpeningAnimator:
    """Handles animated pack opening with sequential card reveals"""
    
    # Rarity colors and emojis
    RARITY_CONFIG = {
        'common': {
            'color': discord.Color.light_gray(),
            'emoji': '⚪',
            'effect': '',
            'name': 'Common'
        },
        'rare': {
            'color': discord.Color.blue(),
            'emoji': '🔵',
            'effect': '✨',
            'name': 'Rare'
        },
        'epic': {
            'color': discord.Color.purple(),
            'emoji': '🟣',
            'effect': '✨✨',
            'name': 'Epic'
        },
        'legendary': {
            'color': discord.Color.gold(),
            'emoji': '🟡',
            'effect': '⭐✨',
            'name': 'Legendary'
        },
        'mythic': {
            'color': discord.Color.red(),
            'emoji': '🔴',
            'effect': '🔥✨',
            'name': 'Mythic'
        }
    }
    
    def __init__(self, pack_name: str, pack_type: str):
        self.pack_name = pack_name
        self.pack_type = pack_type
    
    def create_loading_embed(self) -> discord.Embed:
        """Create the initial loading embed with animation"""
        embed = discord.Embed(
            title="🎁 Opening Pack... 🎁",
            description=f"**{self.pack_name}**\n\n✨ Shuffling cards...\n🔮 The universe is deciding your fate...\n⏳ Preparing your rewards...",
            color=discord.Color.gold() if self.pack_type == 'gold' else discord.Color.blue()
        )
        embed.set_footer(text="✨ Get ready for your new cards!")
        return embed
    
    def create_legendary_teaser_embed(self) -> discord.Embed:
        """Create dramatic legendary teaser embed"""
        embed = discord.Embed(
            title="✨ LEGENDARY PULL! ✨",
            description="🌟 Something amazing is coming... 🌟\n\n⭐ **LEGENDARY CARD INCOMING!** ⭐",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Get ready for something special!")
        return embed
    
    def create_card_reveal_embed(
        self,
        card: Dict,
        card_number: int,
        total_cards: int,
        is_duplicate: bool = False
    ) -> discord.Embed:
        """Create embed for revealing a single card"""
        
        rarity = card.get('rarity', 'common')
        config = self.RARITY_CONFIG.get(rarity, self.RARITY_CONFIG['common'])
        
        # Title with rarity effect
        title = f"{config['emoji']} Card {card_number}/{total_cards} {config['effect']}"
        
        # Description with card info
        description = f"**{card['name']}** - {card.get('title', 'Unknown Track')}\n\n"
        
        if is_duplicate:
            description += "🔄 **DUPLICATE!** Added to your collection.\n\n"
        else:
            description += "🆕 **NEW CARD!** First time getting this one!\n\n"
        
        description += f"**Rarity:** {config['name']} {config['emoji']}\n"
        
        # Create embed
        embed = discord.Embed(
            title=title,
            description=description,
            color=config['color']
        )
        
        # Stats
        stats_text = (
            f"⚔️ **Attack:** {card.get('attack', card.get('impact', 50))}\n"
            f"🛡️ **Defense:** {card.get('defense', card.get('skill', 50))}\n"
            f"⚡ **Speed:** {card.get('speed', card.get('longevity', 50))}"
        )
        embed.add_field(name="📊 Stats", value=stats_text, inline=True)
        
        # Power rating
        power = (
            card.get('attack', card.get('impact', 50)) +
            card.get('defense', card.get('skill', 50)) +
            card.get('speed', card.get('longevity', 50))
        ) // 3
        
        power_text = f"💪 **{power}** Power"
        embed.add_field(name="⚡ Overall", value=power_text, inline=True)
        
        # Image if available
        if card.get('image_url'):
            embed.set_thumbnail(url=card['image_url'])
        
        # Progress footer
        embed.set_footer(text=f"Opening pack... {card_number}/{total_cards} cards revealed")
        
        return embed
    
    def create_summary_embed(
        self,
        cards: List[Dict],
        pack_id: str = None,
        new_cards_count: int = 0
    ) -> discord.Embed:
        """Create final summary embed showing all cards"""
        
        embed = discord.Embed(
            title="✅ Pack Opened Successfully!",
            description=f"**{self.pack_name}**\n\nAll cards have been added to your collection!",
            color=discord.Color.green()
        )
        
        # Pack info
        if pack_id:
            embed.add_field(
                name="📦 Pack Info",
                value=f"**Pack ID:** {pack_id}\n**Cards:** {len(cards)}",
                inline=False
            )
        
        # Card list with rarities
        card_list = []
        rarity_counts = {'common': 0, 'rare': 0, 'epic': 0, 'legendary': 0, 'mythic': 0}
        
        for card in cards:
            rarity = card.get('rarity', 'common')
            rarity_counts[rarity] += 1
            config = self.RARITY_CONFIG.get(rarity, self.RARITY_CONFIG['common'])
            
            power = (
                card.get('attack', card.get('impact', 50)) +
                card.get('defense', card.get('skill', 50)) +
                card.get('speed', card.get('longevity', 50))
            ) // 3
            
            card_list.append(
                f"{config['emoji']} **{card.get('title', card['name'])}** ({power} power)"
            )
        
        embed.add_field(
            name="🎴 Your Cards",
            value="\n".join(card_list),
            inline=False
        )
        
        # Rarity distribution
        rarity_text = " • ".join([
            f"{count} {rarity.title()}"
            for rarity, count in rarity_counts.items() if count > 0
        ])
        embed.add_field(
            name="📊 Rarity Breakdown",
            value=rarity_text,
            inline=False
        )
        
        # New cards info
        if new_cards_count > 0:
            embed.add_field(
                name="🆕 New Cards",
                value=f"You got **{new_cards_count}** new card(s)!",
                inline=True
            )
        
        duplicates = len(cards) - new_cards_count
        if duplicates > 0:
            embed.add_field(
                name="🔄 Duplicates",
                value=f"**{duplicates}** duplicate(s)",
                inline=True
            )
        
        embed.set_footer(text="Use /collection to view all your cards!")
        
        return embed
    
    async def animate_pack_opening(
        self,
        interaction: Interaction,
        cards: List[Dict],
        pack_id: str = None,
        check_duplicates: bool = True,
        delay: float = 2.0
    ):
        """
        Animate the pack opening with sequential card reveals
        
        Args:
            interaction: Discord interaction
            cards: List of card data dicts
            pack_id: Optional pack ID
            check_duplicates: Whether to check for duplicate cards
            delay: Delay between card reveals in seconds
        """
        
        try:
            # Create skip view
            skip_view = SkipView()
            
            # Show loading message with skip button
            loading_embed = self.create_loading_embed()
            message = await interaction.followup.send(embed=loading_embed, view=skip_view, ephemeral=False)
            
            # Wait a moment
            await asyncio.sleep(1.5)
            
            # Track new cards
            new_cards_count = 0
            
            # Check for legendary cards upfront
            legendary_indices = [i for i, c in enumerate(cards) if c.get('rarity') == 'legendary']
            
            # Reveal each card sequentially
            for i, card in enumerate(cards, 1):
                # Check if user skipped
                if skip_view.skipped:
                    break
                
                # Check if duplicate (simplified - would need DB check in real implementation)
                is_duplicate = False
                if not check_duplicates:
                    is_duplicate = False
                else:
                    # TODO: Check database for existing card
                    is_duplicate = False
                
                if not is_duplicate:
                    new_cards_count += 1
                
                # Get rarity for delay adjustment
                rarity = card.get('rarity', 'common')
                
                # Show legendary teaser if this is a legendary card
                if rarity == 'legendary':
                    legendary_teaser = self.create_legendary_teaser_embed()
                    await interaction.edit_original_response(embed=legendary_teaser, view=skip_view)
                    await asyncio.sleep(2.0)  # Dramatic pause
                
                # Create reveal embed
                reveal_embed = self.create_card_reveal_embed(
                    card,
                    i,
                    len(cards),
                    is_duplicate
                )
                
                # Update message with card reveal
                await interaction.edit_original_response(embed=reveal_embed, view=skip_view)
                
                # Rarity-specific delays
                if i < len(cards):
                    if rarity == 'legendary':
                        await asyncio.sleep(3.0)  # Longer for legendary
                    elif rarity == 'epic':
                        await asyncio.sleep(2.5)  # Longer for epic
                    elif rarity == 'rare':
                        await asyncio.sleep(2.0)  # Standard for rare
                    else:
                        await asyncio.sleep(1.0)  # Quick for common
            
            # Wait before showing summary
            await asyncio.sleep(1.5)
            
            # Show final summary
            summary_embed = self.create_summary_embed(
                cards,
                pack_id,
                new_cards_count
            )
            await interaction.edit_original_response(embed=summary_embed, view=None)
            
        except Exception as e:
            print(f"❌ Error in pack opening animation: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to simple message
            try:
                await interaction.followup.send(
                    f"✅ Pack opened! {len(cards)} cards added to your collection.",
                    ephemeral=True
                )
            except:
                pass


# Convenience function for quick pack opening
async def open_pack_with_animation(
    interaction: Interaction,
    pack_name: str,
    pack_type: str,
    cards: List[Dict],
    pack_id: str = None,
    delay: float = 2.0
):
    """
    Quick function to open a pack with animation
    
    Args:
        interaction: Discord interaction
        pack_name: Name of the pack
        pack_type: 'community' or 'gold'
        cards: List of card data
        pack_id: Optional pack ID
        delay: Delay between reveals (default 2 seconds)
    """
    animator = PackOpeningAnimator(pack_name, pack_type)
    await animator.animate_pack_opening(
        interaction,
        cards,
        pack_id,
        check_duplicates=True,
        delay=delay
    )
