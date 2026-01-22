# services/open_creator.py
"""
Creator Pack Opening Service
Open creator packs and generate cards with tier rolls
"""

import random
from typing import List, Optional
from services.pack_service import roll_tier, SILVER_ODDS
from services.card_factory import create_from_artist
from models.artist import Artist
from models.creator_pack import CreatorPack

def open_creator_pack(pack: CreatorPack, pack_size: int = 5, odds_override: Optional[dict] = None) -> List:
    """
    Open a creator pack and generate cards
    
    Args:
        pack: CreatorPack object
        pack_size: Number of cards to generate
        odds_override: Custom tier odds (optional)
        
    Returns:
        List of generated cards
        
    Raises:
        ValueError: If pack is not approved or payment not captured
    """
    try:
        # Open Guard: Check if pack is approved
        if pack.status != "approved":
            raise ValueError(f"Pack not approved (current status: {pack.status})")
        
        # Open Guard: Check if payment is captured
        if pack.payment_status != "captured":
            raise ValueError(f"Payment not captured (current status: {pack.payment_status})")
        
        # Guard Rule: No approved pack without payment
        if not pack.is_active():
            raise ValueError("Pack is not active for opening")
        
        cards = []
        
        # Use provided odds or default to Silver baseline
        tier_odds = odds_override or SILVER_ODDS
        
        # Get artists from pack
        artist_ids = pack.artist_ids or []
        
        if not artist_ids:
            print(f"❌ No artists in pack {pack.id}")
            return []
        
        # Get artist objects
        artists = Artist.where_in("id", artist_ids)
        
        if not artists:
            print(f"❌ No valid artists found for pack {pack.id}")
            return []
        
        # Generate cards
        for i in range(pack_size):
            # Roll for tier
            tier = roll_tier(tier_odds)
            
            # Select random artist from pack
            artist = random.choice(artists)
            
            # Create card
            card = create_from_artist(
                artist=artist,
                tier=tier,
                source=f"creator:{pack.id}"
            )
            
            if card:
                cards.append(card)
                print(f"✅ Created card: {card.serial} ({tier}) - {artist.name}")
            else:
                print(f"❌ Failed to create card for artist {artist.name}")
        
        # Increment pack purchase count
        pack.increment_purchases()
        
        print(f"📦 Opened creator pack '{pack.name}': {len(cards)} cards generated")
        return cards
        
    except Exception as e:
        print(f"❌ Error opening creator pack: {e}")
        raise


def open_premium_creator_pack(pack: CreatorPack, guaranteed_tiers: List[str] = None) -> List:
    """
    Open a premium creator pack with guaranteed tiers
    
    Args:
        pack: CreatorPack object
        guaranteed_tiers: List of guaranteed tiers (e.g., ["gold", "platinum"])
        
    Returns:
        List of generated cards
    """
    try:
        cards = []
        pack_size = 5
        
        # Get artists from pack
        artist_ids = pack.artist_ids or []
        artists = Artist.where_in("id", artist_ids)
        
        if not artists:
            return []
        
        # Premium odds (better than standard)
        premium_odds = {
            "legendary": 5,      # 5% (vs 1% standard)
            "platinum": 15,     # 15% (vs 5% standard)
            "gold": 30,         # 30% (vs 15% standard)
            "silver": 30,       # 30% (vs 35% standard)
            "bronze": 15,       # 15% (vs 25% standard)
            "community": 5      # 5% (vs 19% standard)
        }
        
        # Ensure we have guaranteed tiers
        if guaranteed_tiers:
            # Create guaranteed cards first
            for tier in guaranteed_tiers[:pack_size]:
                artist = random.choice(artists)
                card = create_from_artist(
                    artist=artist,
                    tier=tier,
                    source=f"premium_creator:{pack.id}"
                )
                if card:
                    cards.append(card)
            
            # Fill remaining slots with premium odds
            remaining_slots = pack_size - len(cards)
            for _ in range(remaining_slots):
                tier = roll_tier(premium_odds)
                artist = random.choice(artists)
                
                card = create_from_artist(
                    artist=artist,
                    tier=tier,
                    source=f"premium_creator:{pack.id}"
                )
                if card:
                    cards.append(card)
        else:
            # No guaranteed tiers, just use premium odds
            for _ in range(pack_size):
                tier = roll_tier(premium_odds)
                artist = random.choice(artists)
                
                card = create_from_artist(
                    artist=artist,
                    tier=tier,
                    source=f"premium_creator:{pack.id}"
                )
                if card:
                    cards.append(card)
        
        # Increment pack purchase count
        pack.increment_purchases()
        
        print(f"📦 Opened premium creator pack '{pack.name}': {len(cards)} cards")
        return cards
        
    except Exception as e:
        print(f"❌ Error opening premium creator pack: {e}")
        return []


def open_genre_focused_pack(pack: CreatorPack, focus_genre: str = None) -> List:
    """
    Open a creator pack with genre-focused odds
    
    Args:
        pack: CreatorPack object
        focus_genre: Genre to focus on for better odds
        
    Returns:
        List of generated cards
    """
    try:
        cards = []
        pack_size = 5
        
        # Get artists from pack
        artist_ids = pack.artist_ids or []
        artists = Artist.where_in("id", artist_ids)
        
        if not artists:
            return []
        
        # Filter artists by focus genre if specified
        if focus_genre:
            focused_artists = [a for a in artists if a.genre == focus_genre]
            other_artists = [a for a in artists if a.genre != focus_genre]
            
            # 70% chance for focused genre, 30% for others
            artist_pool = focused_artists * 7 + other_artists * 3
        else:
            artist_pool = artists
        
        # Genre-focused odds (slightly better for matching genre)
        genre_odds = SILVER_ODDS.copy()
        
        # Boost odds for pack's primary genre
        if pack.genre:
            genre_odds["gold"] = min(genre_odds.get("gold", 15) + 5, 40)
            genre_odds["platinum"] = min(genre_odds.get("platinum", 5) + 3, 20)
        
        # Generate cards
        for _ in range(pack_size):
            tier = roll_tier(genre_odds)
            artist = random.choice(artist_pool)
            
            card = create_from_artist(
                artist=artist,
                tier=tier,
                source=f"genre_creator:{pack.id}"
            )
            
            if card:
                cards.append(card)
        
        # Increment pack purchase count
        pack.increment_purchases()
        
        print(f"📦 Opened genre-focused creator pack '{pack.name}': {len(cards)} cards")
        return cards
        
    except Exception as e:
        print(f"❌ Error opening genre-focused creator pack: {e}")
        return []


def calculate_pack_value(cards: List) -> dict:
    """
    Calculate the value of opened cards
    
    Args:
        cards: List of generated cards
        
    Returns:
        Value breakdown dictionary
    """
    try:
        tier_values = {
            "legendary": 5000,    # $50.00
            "platinum": 2000,     # $20.00
            "gold": 1000,         # $10.00
            "silver": 500,        # $5.00
            "bronze": 200,        # $2.00
            "community": 100      # $1.00
        }
        
        tier_counts = {}
        total_value = 0
        
        for card in cards:
            tier = card.tier
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            total_value += tier_values.get(tier, 0)
        
        return {
            "tier_counts": tier_counts,
            "total_value_cents": total_value,
            "total_value_dollars": total_value / 100,
            "card_count": len(cards),
            "average_value_per_card": total_value / len(cards) if cards else 0
        }
        
    except Exception as e:
        print(f"❌ Error calculating pack value: {e}")
        return {
            "tier_counts": {},
            "total_value_cents": 0,
            "total_value_dollars": 0,
            "card_count": 0,
            "average_value_per_card": 0
        }


def simulate_pack_opening(pack: CreatorPack, simulations: int = 100) -> dict:
    """
    Simulate multiple pack openings to analyze odds
    
    Args:
        pack: CreatorPack object
        simulations: Number of simulations to run
        
    Returns:
        Simulation results
    """
    try:
        all_results = []
        tier_distribution = {
            "legendary": 0,
            "platinum": 0,
            "gold": 0,
            "silver": 0,
            "bronze": 0,
            "community": 0
        }
        
        total_value = 0
        
        print(f"🎲 Simulating {simulations} pack openings...")
        
        for i in range(simulations):
            # Simulate opening pack
            cards = open_creator_pack(pack)
            
            if cards:
                # Calculate value
                value = calculate_pack_value(cards)
                all_results.append(value)
                total_value += value["total_value_cents"]
                
                # Track tier distribution
                for tier, count in value["tier_counts"].items():
                    tier_distribution[tier] += count
        
        # Calculate statistics
        if all_results:
            average_value = total_value / len(all_results)
            min_value = min(r["total_value_cents"] for r in all_results)
            max_value = max(r["total_value_cents"] for r in all_results)
            
            # Calculate hit rates
            legendary_hit_rate = tier_distribution["legendary"] / (simulations * 5) * 100
            platinum_hit_rate = tier_distribution["platinum"] / (simulations * 5) * 100
            gold_hit_rate = tier_distribution["gold"] / (simulations * 5) * 100
        else:
            average_value = min_value = max_value = 0
            legendary_hit_rate = platinum_hit_rate = gold_hit_rate = 0
        
        results = {
            "simulations": simulations,
            "average_value_cents": average_value,
            "average_value_dollars": average_value / 100,
            "min_value_cents": min_value,
            "max_value_cents": max_value,
            "tier_distribution": tier_distribution,
            "hit_rates": {
                "legendary": legendary_hit_rate,
                "platinum": platinum_hit_rate,
                "gold": gold_hit_rate
            }
        }
        
        print(f"✅ Simulation complete:")
        print(f"   Average value: ${average_value / 100:.2f}")
        print(f"   Legendary hit rate: {legendary_hit_rate:.1f}%")
        print(f"   Platinum hit rate: {platinum_hit_rate:.1f}%")
        print(f"   Gold hit rate: {gold_hit_rate:.1f}%")
        
        return results
        
    except Exception as e:
        print(f"❌ Error simulating pack openings: {e}")
        return {}


# Example usage
def example_usage():
    """Example of creator pack opening usage"""
    
    # Mock pack for testing
    class MockPack:
        def __init__(self):
            self.id = "test_pack_123"
            self.name = "Test Rock Pack"
            self.artist_ids = ["artist_1", "artist_2", "artist_3"]
            self.genre = "Rock"
            self.price_cents = 999
        
        def increment_purchases(self):
            print("📊 Purchase count incremented")
    
    mock_pack = MockPack()
    
    # Test standard pack opening
    print("📦 Testing standard pack opening...")
    cards = open_creator_pack(mock_pack)
    
    if cards:
        value = calculate_pack_value(cards)
        print(f"   Generated {len(cards)} cards worth ${value['total_value_dollars']:.2f}")
    
    # Test premium pack opening
    print("\n📦 Testing premium pack opening...")
    premium_cards = open_premium_creator_pack(mock_pack, guaranteed_tiers=["gold"])
    
    if premium_cards:
        premium_value = calculate_pack_value(premium_cards)
        print(f"   Generated {len(premium_cards)} cards worth ${premium_value['total_value_dollars']:.2f}")
    
    # Test simulation
    print("\n🎲 Testing pack simulation...")
    simulation_results = simulate_pack_opening(mock_pack, simulations=50)
    print(f"   Average pack value: ${simulation_results['average_value_dollars']:.2f}")


if __name__ == "__main__":
    example_usage()
