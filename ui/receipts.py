"""
Discord Receipt UI Components

Creates beautiful embeds for purchase confirmations, card deliveries, and refunds.
Provides visual feedback for all payment events.
"""

import discord
import logging
from typing import List, Optional
from datetime import datetime

from models.card import Card

# Configure logging
logger = logging.getLogger(__name__)

def purchase_embed(user: discord.User, pack_type: str, session_id: str, amount: int = None) -> discord.Embed:
    """
    Create purchase confirmation embed.
    
    Args:
        user: Discord user who made the purchase
        pack_type: Type of pack purchased
        session_id: Stripe checkout session ID
        amount: Purchase amount in cents (optional)
        
    Returns:
        Discord embed for purchase confirmation
    """
    try:
        embed = discord.Embed(
            title="🛒 Purchase Confirmed",
            description=f"Your {pack_type.title()} Pack purchase has been confirmed!",
            color=0x2ecc71  # Green
        )
        
        # Add purchase details
        embed.add_field(
            name="📦 Pack Type",
            value=pack_type.title(),
            inline=True
        )
        
        embed.add_field(
            name="🆔 Order ID",
            value=f"`{session_id}`",
            inline=True
        )
        
        if amount:
            embed.add_field(
                name="💰 Amount",
                value=f"${amount/100:.2f}",
                inline=True
            )
        
        # Add timestamp
        embed.add_field(
            name="📅 Purchase Time",
            value=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=False
        )
        
        # Add footer with delivery information
        embed.set_footer(
            text="Cards will appear in your collection momentarily ⏳"
        )
        
        # Add thumbnail
        embed.set_thumbnail(url="https://i.imgur.com/pack_icon.png")
        
        # Add author info
        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url if user.display_avatar else None
        )
        
        return embed
        
    except Exception as e:
        logger.error(f"Failed to create purchase embed: {e}")
        # Return basic embed on error
        return discord.Embed(
            title="Purchase Confirmed",
            description=f"Your {pack_type.title()} Pack purchase was confirmed!",
            color=0x2ecc71
        )

def delivery_embed(user: discord.User, session_id: str, cards: List[Card]) -> discord.Embed:
    """
    Create card delivery embed showing all received cards.
    
    Args:
        user: Discord user receiving the cards
        session_id: Purchase session ID
        cards: List of cards delivered
        
    Returns:
        Discord embed showing delivered cards
    """
    try:
        embed = discord.Embed(
            title="🎁 Pack Opened!",
            description=f"Your {len(cards)} cards have been delivered!",
            color=0xf1c40f  # Gold
        )
        
        # Add session info
        embed.add_field(
            name="🆔 Order ID",
            value=f"`{session_id}`",
            inline=False
        )
        
        # Add cards in a formatted way
        if cards:
            card_text = ""
            for i, card in enumerate(cards, 1):
                # Get artist info
                artist = card.artist()
                artist_name = artist.name if artist else "Unknown Artist"
                
                # Format card info
                tier_emoji = get_tier_emoji(card.tier)
                card_text += f"{i}. {tier_emoji} **{card.serial}** - {card.tier.title()} • {artist_name}\n"
            
            # Add cards field (split if too long)
            if len(card_text) > 1024:
                # Split into multiple fields if too long
                lines = card_text.split('\n')
                current_field = ""
                field_num = 1
                
                for line in lines:
                    if len(current_field + line + '\n') > 1024:
                        embed.add_field(
                            name=f"🎴 Cards Delivered ({field_num})",
                            value=current_field,
                            inline=False
                        )
                        current_field = line + '\n'
                        field_num += 1
                    else:
                        current_field += line + '\n'
                
                if current_field.strip():
                    embed.add_field(
                        name=f"🎴 Cards Delivered ({field_num})",
                        value=current_field,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="🎴 Cards Delivered",
                    value=card_text,
                    inline=False
                )
            
            # Set hero image (first card's artist image)
            if cards:
                first_card = cards[0]
                try:
                    artist = first_card.artist()
                    if artist and hasattr(artist, 'image_url') and artist.image_url:
                        embed.set_image(url=artist.image_url)
                except Exception as e:
                    logger.warning(f"Failed to get artist image for hero: {e}")
        
        # Add footer
        embed.set_footer(
            text=f"Thank you for your purchase! View your collection with /mycards"
        )
        
        # Add author info
        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url if user.display_avatar else None
        )
        
        return embed
        
    except Exception as e:
        logger.error(f"Failed to create delivery embed: {e}")
        # Return basic embed on error
        return discord.Embed(
            title="Pack Opened!",
            description=f"Your {len(cards)} cards have been delivered!",
            color=0xf1c40f
        )

def refund_embed(user: discord.User, session_id: str, refund_amount: int = None, cards_revoked: int = None) -> discord.Embed:
    """
    Create refund confirmation embed.
    
    Args:
        user: Discord user receiving the refund
        session_id: Original purchase session ID
        refund_amount: Refund amount in cents (optional)
        cards_revoked: Number of cards revoked (optional)
        
    Returns:
        Discord embed for refund confirmation
    """
    try:
        embed = discord.Embed(
            title="💳 Refund Processed",
            description="Your refund has been processed successfully.",
            color=0xe74c3c  # Red
        )
        
        # Add refund details
        embed.add_field(
            name="🆔 Original Order",
            value=f"`{session_id}`",
            inline=True
        )
        
        embed.add_field(
            name="📊 Status",
            value="Cards Revoked",
            inline=True
        )
        
        if refund_amount:
            embed.add_field(
                name="💰 Refund Amount",
                value=f"${refund_amount/100:.2f}",
                inline=True
            )
        
        if cards_revoked is not None:
            embed.add_field(
                name="🎴 Cards Revoked",
                value=f"{cards_revoked} card(s)",
                inline=True
            )
        
        # Add timestamp
        embed.add_field(
            name="📅 Refund Time",
            value=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=False
        )
        
        # Add footer
        embed.set_footer(
            text="Refunds typically take 5-7 business days to appear on your statement"
        )
        
        # Add author info
        embed.set_author(
            name=user.display_name,
            icon_url=user.display_avatar.url if user.display_avatar else None
        )
        
        return embed
        
    except Exception as e:
        logger.error(f"Failed to create refund embed: {e}")
        # Return basic embed on error
        return discord.Embed(
            title="Refund Processed",
            description="Your refund has been processed successfully.",
            color=0xe74c3c
        )

def admin_sale_embed(pack_type: str, session_id: str, user_id: int, amount: int) -> discord.Embed:
    """
    Create admin sales log embed.
    
    Args:
        pack_type: Type of pack sold
        session_id: Purchase session ID
        user_id: Discord user ID
        amount: Purchase amount in cents
        
    Returns:
        Discord embed for admin sales log
    """
    try:
        embed = discord.Embed(
            title="💰 New Sale",
            description="A new pack purchase has been completed",
            color=0x3498db  # Blue
        )
        
        # Add sale details
        embed.add_field(
            name="📦 Pack Type",
            value=pack_type.title(),
            inline=True
        )
        
        embed.add_field(
            name="🆔 Session ID",
            value=f"`{session_id}`",
            inline=True
        )
        
        embed.add_field(
            name="👤 User ID",
            value=f"`{user_id}`",
            inline=True
        )
        
        embed.add_field(
            name="💰 Amount",
            value=f"${amount/100:.2f}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Sale Time",
            value=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=True
        )
        
        # Add footer
        embed.set_footer(
            text="Automatic sales logging system"
        )
        
        return embed
        
    except Exception as e:
        logger.error(f"Failed to create admin sale embed: {e}")
        # Return basic embed on error
        return discord.Embed(
            title="New Sale",
            description=f"Pack: {pack_type.title()} | Session: {session_id}",
            color=0x3498db
        )

def admin_refund_embed(session_id: str, user_id: int, refund_amount: int, cards_revoked: int) -> discord.Embed:
    """
    Create admin refund log embed.
    
    Args:
        session_id: Original purchase session ID
        user_id: Discord user ID
        refund_amount: Refund amount in cents
        cards_revoked: Number of cards revoked
        
    Returns:
        Discord embed for admin refund log
    """
    try:
        embed = discord.Embed(
            title="💳 Refund Processed",
            description="A refund has been processed",
            color=0xe67e22  # Orange
        )
        
        # Add refund details
        embed.add_field(
            name="🆔 Original Session",
            value=f"`{session_id}`",
            inline=True
        )
        
        embed.add_field(
            name="👤 User ID",
            value=f"`{user_id}`",
            inline=True
        )
        
        embed.add_field(
            name="💰 Refund Amount",
            value=f"${refund_amount/100:.2f}",
            inline=True
        )
        
        embed.add_field(
            name="🎴 Cards Revoked",
            value=f"{cards_revoked}",
            inline=True
        )
        
        embed.add_field(
            name="📅 Refund Time",
            value=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
            inline=True
        )
        
        # Add footer
        embed.set_footer(
            text="Automatic refund logging system"
        )
        
        return embed
        
    except Exception as e:
        logger.error(f"Failed to create admin refund embed: {e}")
        # Return basic embed on error
        return discord.Embed(
            title="Refund Processed",
            description=f"Session: {session_id} | Cards Revoked: {cards_revoked}",
            color=0xe67e22
        )

# Utility functions

def get_tier_emoji(tier: str) -> str:
    """Get emoji for card tier."""
    tier_emojis = {
        "common": "⚪",
        "uncommon": "🟢", 
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
        "platinum": "⭐",
        "gold": "🏆",
        "diamond": "💎"
    }
    return tier_emojis.get(tier.lower(), "🎴")

def format_card_list(cards: List[Card]) -> str:
    """Format a list of cards for display."""
    if not cards:
        return "No cards"
    
    lines = []
    for i, card in enumerate(cards, 1):
        tier_emoji = get_tier_emoji(card.tier)
        artist_name = card.artist().name if card.artist() else "Unknown"
        lines.append(f"{i}. {tier_emoji} **{card.serial}** - {card.tier.title()} • {artist_name}")
    
    return "\n".join(lines)

def get_pack_emoji(pack_type: str) -> str:
    """Get emoji for pack type."""
    pack_emojis = {
        "starter": "📦",
        "silver": "🥈",
        "gold": "🥇",
        "black": "⚫",
        "founder_black": "🖤",
        "founder_gold": "👑"
    }
    return pack_emojis.get(pack_type.lower(), "📦")

# Error handling

class ReceiptUIError(Exception):
    """Custom exception for receipt UI errors."""
    pass

class EmbedCreationError(ReceiptUIError):
    """Exception for embed creation errors."""
    pass

# Logging helpers

def log_receipt_sent(user_id: int, session_id: str, receipt_type: str):
    """Log receipt sent to user."""
    logger.info(f"Receipt sent: user {user_id}, session {session_id}, type {receipt_type}")

def log_admin_sale_logged(pack_type: str, session_id: str, amount: int):
    """Log admin sale notification."""
    logger.info(f"Admin sale logged: pack {pack_type}, session {session_id}, amount ${amount/100:.2f}")

def log_admin_refund_logged(session_id: str, refund_amount: int, cards_revoked: int):
    """Log admin refund notification."""
    logger.info(f"Admin refund logged: session {session_id}, amount ${refund_amount/100:.2f}, cards {cards_revoked}")
