# views/pack_opening.py
"""
Pack Opening Animation System
Sequential card reveals with rarity-specific effects
Enhanced with audio feedback and visual celebrations
"""

import discord
from discord import Interaction
import asyncio
import os
from pathlib import Path
from typing import List, Dict, Optional
from services.image_cache import safe_image


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
    
    # Animated GIF URLs for effects (using Tenor API)
    CELEBRATION_GIFS = {
        'legendary': 'https://media.tenor.com/Cvx2qeKmAOEAAAAC/fireworks-celebration.gif',
        'epic': 'https://media.tenor.com/XVXk9vHkRgEAAAAC/confetti.gif',
        'purchase': 'https://media.tenor.com/xkv5rN7gKC0AAAAC/money-cash.gif',
    }
    
    # Audio file paths
    AUDIO_DIR = Path('assets/sounds')
    AUDIO_FILES = {
        'pack_opening': AUDIO_DIR / 'pack_opening.mp3',  # Sound when pack starts opening
        'legendary_pull': AUDIO_DIR / 'legendary_pull.mp3',  # Triumphant sound for legendary
        'card_pickup': AUDIO_DIR / 'card_pickup.mp3',
    }
    
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
        """Create dramatic legendary teaser embed with GIF"""
        embed = discord.Embed(
            title="✨ LEGENDARY PULL! ✨",
            description="🌟 Something amazing is coming... 🌟\n\n⭐ **LEGENDARY CARD INCOMING!** ⭐\n\n💎💎💎💎💎",
            color=discord.Color.gold()
        )
        # Add celebration GIF
        embed.set_image(url=self.CELEBRATION_GIFS['legendary'])
        embed.set_footer(text="Get ready for something special!")
        return embed
    
    async def send_emoji_fireworks(self, interaction: Interaction, message):
        """Send emoji fireworks celebration"""
        fireworks_emojis = "✨🎊💎🌟⭐🎉✨💫🎊🌟💎✨⭐🎉💫🎊"
        try:
            await message.add_reaction("💎")
            await message.add_reaction("⭐")
            await message.add_reaction("✨")
        except:
            pass  # Ignore if reactions fail
    
    def get_audio_file(self, audio_type: str) -> Optional[discord.File]:
        """Get audio file for attachment if it exists"""
        if audio_type not in self.AUDIO_FILES:
            return None
        
        audio_path = self.AUDIO_FILES[audio_type]
        if audio_path.exists():
            return discord.File(str(audio_path), filename=audio_path.name)
        return None
    
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
        
        # Image if available - use safe_image to validate and get fallback
        if card.get('image_url'):
            safe_url = safe_image(card['image_url'])
            embed.set_image(url=safe_url)  # Use set_image for full-size instead of thumbnail
        
        # Progress footer with logo
        embed.set_footer(text=f"🎵 Music Legends • Opening pack... {card_number}/{total_cards} cards revealed")
        
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
        
        embed.set_footer(text="🎵 Music Legends • Check your collection with the Collection button in the User Hub!")
        
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
        Animate the pack opening with sequential card reveals.

        IMPORTANT: This is called AFTER the interaction has already been responded to
        (e.g. via edit_message on a button click).  All messages here use
        interaction.followup.send() and message.edit() — NEVER edit_original_response
        (which would clobber the claim button) or channel.send (which needs perms).
        """

        try:
            # Create skip view
            skip_view = SkipView()

            # Send the loading/"shuffling" message as a followup — this is the
            # message we'll .edit() for the entire animation sequence.
            loading_embed = self.create_loading_embed()
            audio_file = self.get_audio_file('pack_opening')

            try:
                if audio_file:
                    anim_msg = await interaction.followup.send(
                        embed=loading_embed, view=skip_view, wait=True, file=audio_file
                    )
                else:
                    anim_msg = await interaction.followup.send(
                        embed=loading_embed, view=skip_view, wait=True
                    )
            except Exception as e:
                print(f"[PACK_ANIM] Could not send loading message: {e}")
                # Last-resort fallback — just confirm cards were granted
                try:
                    await interaction.followup.send(
                        f"✅ Pack opened! {len(cards)} cards added to your collection."
                    )
                except Exception:
                    pass
                return

            await asyncio.sleep(1.5)

            # Track new cards
            new_cards_count = len(cards)  # All are new from a fresh pack open

            # Reveal each card sequentially by editing the animation message
            for i, card in enumerate(cards, 1):
                if skip_view.skipped:
                    break

                rarity = card.get('rarity', 'common')

                # Legendary teaser
                if rarity == 'legendary':
                    try:
                        legendary_teaser = self.create_legendary_teaser_embed()
                        await anim_msg.edit(embed=legendary_teaser, view=skip_view)
                        # Celebration reactions
                        try:
                            await self.send_emoji_fireworks(interaction, anim_msg)
                        except Exception:
                            pass
                        await asyncio.sleep(2.0)
                    except Exception as e:
                        print(f"[PACK_ANIM] Legendary teaser edit failed: {e}")

                # Card reveal
                reveal_embed = self.create_card_reveal_embed(card, i, len(cards), False)
                try:
                    await anim_msg.edit(embed=reveal_embed, view=skip_view)
                except Exception as e:
                    print(f"[PACK_ANIM] Card {i} reveal edit failed: {e}")

                # Rarity-specific delays
                if i < len(cards):
                    if rarity == 'legendary':
                        await asyncio.sleep(3.0)
                    elif rarity == 'epic':
                        await asyncio.sleep(2.5)
                    elif rarity == 'rare':
                        await asyncio.sleep(2.0)
                    else:
                        await asyncio.sleep(1.0)

            # Final summary
            await asyncio.sleep(1.5)
            summary_embed = self.create_summary_embed(cards, pack_id, new_cards_count)
            try:
                await anim_msg.edit(embed=summary_embed, view=None)
            except Exception as e:
                print(f"[PACK_ANIM] Summary edit failed: {e}")

            # Trigger backup if rare cards were received
            rare_rarities = ['legendary', 'epic', 'mythic']
            if any(card.get('rarity') in rare_rarities for card in cards):
                try:
                    from services.backup_service import backup_service
                    user_id = interaction.user.id if hasattr(interaction, 'user') else None
                    backup_path = await backup_service.backup_critical(
                        'pack_opening', f"user_{user_id}" if user_id else ""
                    )
                    if backup_path:
                        print(f"💾 Critical backup after rare card pull: {backup_path}")
                except Exception as e:
                    print(f"⚠️ Backup trigger failed (non-critical): {e}")

        except Exception as e:
            print(f"❌ Error in pack opening animation: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    f"✅ Pack opened! {len(cards)} cards added to your collection."
                )
            except Exception:
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
