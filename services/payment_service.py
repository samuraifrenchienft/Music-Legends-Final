"""
Payment Service (Updated for Professional Card System)

Handles payment processing and card creation for completed purchases.
Integrates with canonical card system and pack definitions.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from models.card import Card
from models.purchase import Purchase
from schemas.card_canonical import CanonicalCard, CardTier, ArtistSource, FrameStyle
from schemas.pack_definition import get_pack_definition, PackDefinition
from services.serial_system import generate_serial
from services.hero_slot_system import generate_pack_artists, Artist
from services.season_supply_system import can_mint_card, mint_card, get_serial_value_tier
from services.physical_card_system import generate_print_file_data

# Configure logging
logger = logging.getLogger(__name__)

def handle_payment(user_id: int, pack_type: str, payment_id: str) -> Dict[str, Any]:
    """
    Process payment and create canonical cards.
    
    Args:
        user_id: Discord user ID
        pack_type: Type of pack purchased
        payment_id: Payment session ID (idempotency key)
        
    Returns:
        Result dictionary with status and card information
    """
    try:
        logger.info(f"Processing payment: user {user_id}, pack {pack_type}, payment {payment_id}")
        
        # Check for existing purchase (idempotency)
        existing_purchase = Purchase.get_by_payment_id(payment_id)
        if existing_purchase:
            existing_cards = Card.from_purchase(payment_id)
            return {
                "status": "ALREADY_PROCESSED",
                "purchase_id": existing_purchase.id,
                "cards_created": len(existing_cards),
                "cards": [card.id for card in existing_cards]
            }
        
        # Get pack definition
        pack_def = get_pack_definition(pack_type)
        if not pack_def:
            return {
                "status": "error",
                "error": f"Unknown pack type: {pack_type}",
                "cards_created": 0
            }
        
        # Create purchase record
        purchase = Purchase.create(
            user_id=user_id,
            pack_type=pack_type,
            payment_id=payment_id,
            amount=pack_def.price_cents
        )
        # Set status after creation
        purchase.status = "completed"
        
        # Generate canonical cards
        canonical_cards = generate_canonical_cards(pack_def, user_id, payment_id)
        
        # Create card records in database
        created_cards = []
        for card_data in canonical_cards:
            card = Card.create(
                user_id=user_id,
                artist_id=card_data["artist_id"],
                tier=card_data["tier"],
                serial=card_data["serial"],
                purchase_id=purchase.id
            )
            created_cards.append(card)
        
        logger.info(f"Created {len(created_cards)} canonical cards for purchase {purchase.id}")
        
        return {
            "status": "completed",
            "purchase_id": purchase.id,
            "cards_created": len(created_cards),
            "cards": [card.id for card in created_cards],
            "canonical_cards": [card.to_dict() for card in canonical_cards]
        }
        
    except Exception as e:
        logger.error(f"Payment processing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "cards_created": 0
        }

def generate_canonical_cards(pack_def: PackDefinition, user_id: int, payment_id: str) -> list:
    """
    Generate canonical cards using the professional card system.
    Enforces Season 1 supply rules and scarcity.
    
    Args:
        pack_def: Pack definition
        user_id: User ID
        payment_id: Payment ID for tracking
        
    Returns:
        List of CanonicalCard objects
    """
    # Generate artists for the pack (hero slot logic included)
    artists = generate_pack_artists(pack_def)
    
    # Generate card tiers based on pack odds and supply constraints
    card_tiers = generate_card_tiers_with_supply(pack_def, artists)
    
    # Create canonical cards
    canonical_cards = []
    
    for i, (artist, tier) in enumerate(zip(artists, card_tiers)):
        # Check if we can mint this card according to Season 1 supply rules
        pack_source = get_pack_source(pack_def.key)
        mint_check = can_mint_card(tier.value, artist.artist_id, pack_source)
        
        if not mint_check["can_mint"]:
            logger.warning(f"Cannot mint {tier.value} card for artist {artist.artist_id}: {mint_check['reason']}")
            # Downgrade to next available tier
            tier = downgrade_to_available_tier(tier, artist.artist_id, pack_source)
            mint_check = can_mint_card(tier.value, artist.artist_id, pack_source)
            
            if not mint_check["can_mint"]:
                logger.error(f"Cannot mint any card for artist {artist.artist_id}")
                continue
        
        # Record the mint in Season 1 supply system
        mint_result = mint_card(tier.value, artist.artist_id, pack_source)
        
        if not mint_result["success"]:
            logger.error(f"Failed to mint card: {mint_result}")
            continue
        
        # Use the serial number from the supply system
        serial_number = mint_result["serial_number"]
        
        # Generate canonical serial format
        canonical_serial = f"ML-S{1}-{get_tier_letter(tier)}-{serial_number:04d}"
        
        # Determine print number and cap
        print_number = serial_number
        print_cap = get_print_cap_for_tier(tier)
        
        # Determine frame style and presentation
        frame_style = get_frame_style_for_tier(tier, pack_def)
        foil = should_be_foil(tier, pack_def)
        badge_icons = get_badge_icons(tier, print_number, i == 0 and pack_def.has_hero_slot())
        accent_color = get_accent_color_for_tier(tier)
        
        # Add serial value tier to badges
        serial_value_tier = get_serial_value_tier(serial_number)
        if serial_value_tier.value != "tradeable":
            badge_icons.append(serial_value_tier.value)
        
        # Create canonical card
        canonical_card = CanonicalCard(
            artist_id=artist.artist_id,
            artist_name=artist.name,
            primary_genre=artist.primary_genre,
            artist_image_url=artist.image_url,
            artist_source=artist.source,
            tier=tier,
            print_number=print_number,
            print_cap=print_cap,
            season=1,  # Season 1
            pack_key=pack_def.key,
            opened_by=str(user_id),
            frame_style=frame_style,
            foil=foil,
            badge_icons=badge_icons,
            accent_color=accent_color
        )
        
        # Override the serial with our canonical format
        canonical_card.identity["serial"] = canonical_serial
        
        # Add print file data for physical redemption
        canonical_card.print_file_data = generate_print_file_data(canonical_card.to_dict())
        
        canonical_cards.append(canonical_card)
    
    logger.info(f"Generated {len(canonical_cards)} canonical cards respecting Season 1 supply rules")
    return canonical_cards

def generate_card_tiers_with_supply(pack_def: PackDefinition, artists: List[Artist]) -> List[CardTier]:
    """
    Generate card tiers respecting Season 1 supply constraints.
    Attempts to honor pack odds but respects global caps.
    """
    import random
    
    tiers = []
    pack_source = get_pack_source(pack_def.key)
    
    for slot in range(pack_def.cards_per_pack):
        if slot == 0 and pack_def.has_hero_slot():
            # Hero slot - try for high tiers first
            min_rarity = pack_def.get_min_rarity()
            if min_rarity in ["platinum", "legendary"]:
                # Boosted odds for hero slot, but check supply
                hero_odds = [
                    ("legendary", 0.3),
                    ("platinum", 0.6),
                    ("gold", 0.1)
                ]
                
                # Try tiers in order of preference
                for tier_name, probability in hero_odds:
                    tier = CardTier(tier_name)
                    mint_check = can_mint_card(tier_name, artists[slot].artist_id, pack_source)
                    
                    if mint_check["can_mint"]:
                        tiers.append(tier)
                        break
                else:
                    # Fallback to gold if nothing else available
                    tiers.append(CardTier.GOLD)
            else:
                # Standard hero slot for lower min rarity
                tier = select_tier_by_odds(pack_def.odds)
                mint_check = can_mint_card(tier, artists[slot].artist_id, pack_source)
                
                if mint_check["can_mint"]:
                    tiers.append(CardTier(tier))
                else:
                    # Fallback to available tier
                    tiers.append(CardTier.GOLD)
        else:
            # Standard slot - use pack odds with supply awareness
            tier_name = select_tier_by_odds(pack_def.odds)
            tier = CardTier(tier_name)
            mint_check = can_mint_card(tier_name, artists[slot].artist_id, pack_source)
            
            if mint_check["can_mint"]:
                tiers.append(tier)
            else:
                # Downgrade to available tier
                available_tier = downgrade_to_available_tier(tier, artists[slot].artist_id, pack_source)
                tiers.append(available_tier)
    
    # Ensure minimum rarity guarantee
    min_rarity = pack_def.get_min_rarity()
    if min_rarity != "community":
        # Check if we have at least one card meeting minimum
        min_tier = CardTier(min_rarity)
        has_min_tier = any(tier.value == min_rarity or is_higher_tier(tier, min_rarity) for tier in tiers)
        
        if not has_min_tier:
            # Upgrade the lowest tier card that can be upgraded
            for i, tier in enumerate(tiers):
                if tier.value == "community":
                    # Try to upgrade to minimum rarity
                    mint_check = can_mint_card(min_rarity, artists[i].artist_id, pack_source)
                    if mint_check["can_mint"]:
                        tiers[i] = min_tier
                        break
    
    return tiers

def downgrade_to_available_tier(tier: CardTier, artist_id: str, pack_source: str) -> CardTier:
    """Find the next available tier for minting"""
    tier_hierarchy = [CardTier.LEGENDARY, CardTier.PLATINUM, CardTier.GOLD, CardTier.COMMUNITY]
    
    # Find current tier position
    current_index = tier_hierarchy.index(tier)
    
    # Try lower tiers until we find one that can be minted
    for i in range(current_index + 1, len(tier_hierarchy)):
        test_tier = tier_hierarchy[i]
        mint_check = can_mint_card(test_tier.value, artist_id, pack_source)
        
        if mint_check["can_mint"]:
            return test_tier
    
    # Fallback to community tier
    return CardTier.COMMUNITY

def get_pack_source(pack_key: str) -> str:
    """Convert pack key to pack source for supply tracking"""
    pack_source_map = {
        "starter": "drops",
        "silver": "silver_packs",
        "gold": "black_packs",  # Treat gold packs as black packs for supply
        "black": "black_packs",
        "founder_gold": "creator_packs",
        "founder_black": "creator_packs"
    }
    return pack_source_map.get(pack_key, "black_packs")

def get_tier_letter(tier: CardTier) -> str:
    """Get tier letter for serial format"""
    tier_letters = {
        CardTier.COMMUNITY: "C",
        CardTier.GOLD: "G",
        CardTier.PLATINUM: "P",
        CardTier.LEGENDARY: "L"
    }
    return tier_letters.get(tier, "C")

def generate_card_tiers(pack_def: PackDefinition) -> list:
    """
    Generate card tiers based on pack odds and guarantees.
    Implements hero slot logic and minimum rarity guarantees.
    """
    import random
    
    tiers = []
    
    for slot in range(pack_def.cards_per_pack):
        if slot == 0 and pack_def.has_hero_slot():
            # Hero slot - guaranteed high tier
            min_rarity = pack_def.get_min_rarity()
            if min_rarity in ["platinum", "legendary"]:
                # Boosted odds for hero slot
                hero_odds = {
                    "platinum": 0.6,
                    "legendary": 0.3,
                    "gold": 0.1
                }
                tier = select_tier_by_odds(hero_odds)
            else:
                tier = select_tier_by_odds(pack_def.odds)
        else:
            # Standard slot - use pack odds
            tier = select_tier_by_odds(pack_def.odds)
        
        tiers.append(CardTier(tier))
    
    # Ensure minimum rarity guarantee
    min_rarity = pack_def.get_min_rarity()
    if min_rarity != "community":
        # Check if we have at least one card meeting minimum
        min_tier = CardTier(min_rarity)
        has_min_tier = any(tier.value == min_rarity or is_higher_tier(tier, min_tier) for tier in tiers)
        
        if not has_min_tier:
            # Upgrade the lowest tier card
            lowest_tier = min(tiers, key=lambda t: get_tier_rank(t))
            lowest_index = tiers.index(lowest_tier)
            tiers[lowest_index] = min_tier
    
    return tiers

def select_tier_by_odds(odds: Dict[str, float]) -> str:
    """Select tier based on probability distribution"""
    import random
    
    tiers = list(odds.keys())
    weights = list(odds.values())
    
    return random.choices(tiers, weights=weights)[0]

def is_higher_tier(tier: CardTier, min_tier: str) -> bool:
    """Check if tier is higher than minimum"""
    tier_rank = get_tier_rank(tier)
    min_rank = get_tier_rank(CardTier(min_tier))
    
    return tier_rank >= min_rank

def get_tier_rank(tier: CardTier) -> int:
    """Get numeric rank for tier comparison"""
    ranks = {
        CardTier.COMMUNITY: 0,
        CardTier.GOLD: 1,
        CardTier.PLATINUM: 2,
        CardTier.LEGENDARY: 3
    }
    return ranks.get(tier, 0)

def get_print_number_for_serial(serial: str) -> int:
    """Extract print number from serial"""
    try:
        # Serial format: ML-S{season}-{tier_letter}-{print_number}
        parts = serial.split('-')
        if len(parts) >= 3:
            return int(parts[2])
    except:
        pass
    return 1  # Default

def get_print_cap_for_tier(tier: CardTier) -> int:
    """Get print cap for tier"""
    caps = {
        CardTier.COMMUNITY: 10000,
        CardTier.GOLD: 5000,
        CardTier.PLATINUM: 1000,
        CardTier.LEGENDARY: 250
    }
    return caps.get(tier, 10000)

def get_frame_style_for_tier(tier: CardTier, pack_def: PackDefinition) -> FrameStyle:
    """Get frame style based on tier and pack"""
    if pack_def.tier.value in ["premium", "founder"]:
        return FrameStyle.LUX_BLACK
    elif tier in [CardTier.PLATINUM, CardTier.LEGENDARY]:
        return FrameStyle.LUX_BLACK
    else:
        return FrameStyle.LUX_WHITE

def should_be_foil(tier: CardTier, pack_def: PackDefinition) -> bool:
    """Determine if card should be foil"""
    # Premium packs always have foil
    if pack_def.tier.value in ["premium", "founder"]:
        return True
    
    # High tiers are foil
    if tier in [CardTier.PLATINUM, CardTier.LEGENDARY]:
        return True
    
    # Random chance for gold
    if tier == CardTier.GOLD:
        import random
        return random.random() < 0.5
    
    return False

def get_badge_icons(tier: CardTier, print_number: int, is_hero: bool) -> list:
    """Get badge icons for card"""
    badges = [tier.value]
    
    # First print badge
    if print_number <= 10:
        badges.append("first_print")
    
    # Hero badge
    if is_hero:
        badges.append("hero")
    
    # Special badges for high tiers
    if tier == CardTier.LEGENDARY:
        badges.append("legendary")
    elif tier == CardTier.PLATINUM:
        badges.append("platinum")
    
    return badges

def get_accent_color_for_tier(tier: CardTier) -> str:
    """Get accent color for tier"""
    colors = {
        CardTier.COMMUNITY: "#C0C0C0",
        CardTier.GOLD: "#FFD700",
        CardTier.PLATINUM: "#E5E4E2",
        CardTier.LEGENDARY: "#9400D3"
    }
    return colors.get(tier, "#C0C0C0")

def get_pack_price(pack_type: str) -> int:
    """
    Get pack price in cents.
    
    Args:
        pack_type: Type of pack
        
    Returns:
        Price in cents
    """
    pack_def = get_pack_definition(pack_type)
    return pack_def.price_cents if pack_def else 0

# Utility functions

def validate_pack_type(pack_type: str) -> bool:
    """Validate pack type."""
    valid_packs = ["starter", "silver", "gold", "black", "founder_gold", "founder_black"]
    return pack_type in valid_packs

def get_purchase_summary(payment_id: str) -> Optional[Dict[str, Any]]:
    """
    Get summary of a purchase including cards.
    
    Args:
        payment_id: Payment ID
        
    Returns:
        Purchase summary or None if not found
    """
    try:
        purchase = Purchase.get_by_payment_id(payment_id)
        if not purchase:
            return None
        
        cards = Card.from_purchase(payment_id)
        
        return {
            "purchase": purchase.to_dict(),
            "cards": [card.to_dict() for card in cards],
            "card_count": len(cards),
            "tiers": {card.tier: cards.count(card) for card in cards}
        }
        
    except Exception as e:
        logger.error(f"Failed to get purchase summary: {e}")
        return None

# Error handling

class PaymentServiceError(Exception):
    """Custom exception for payment service errors."""
    pass

class InvalidPackError(PaymentServiceError):
    """Exception for invalid pack types."""
    pass

class DuplicatePaymentError(PaymentServiceError):
    """Exception for duplicate payment attempts."""
    pass

# Logging helpers

def log_payment_processed(user_id: int, pack_type: str, payment_id: str, card_count: int):
    """Log successful payment processing."""
    logger.info(f"Payment processed: user {user_id}, pack {pack_type}, payment {payment_id}, cards {card_count}")

def log_payment_failed(user_id: int, pack_type: str, payment_id: str, error: str):
    """Log payment processing failure."""
    logger.error(f"Payment failed: user {user_id}, pack {pack_type}, payment {payment_id}, error {error}")

def log_duplicate_payment(payment_id: str):
    """Log duplicate payment attempt."""
    logger.warning(f"Duplicate payment attempt: {payment_id}")
