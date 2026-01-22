"""
Professional Card System Test

Tests the complete canonical card system including:
- Canonical card schema
- Pack definitions
- Serial system
- Hero slot system
- Payment processing
- Card rendering
"""

import pytest
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.card_canonical import CanonicalCard, CardTier, ArtistSource, FrameStyle
from schemas.pack_definition import get_pack_definition, PackDefinition, PackTier
from services.serial_system import generate_serial, get_serial_info, get_scarcity_info
from services.hero_slot_system import get_hero_artist, get_standard_artist, generate_pack_artists
from services.payment_service import handle_payment, generate_canonical_cards
from services.card_rendering_system import create_card_embed
from models.card import Card
from models.purchase import Purchase

class TestCanonicalCard:
    """Test canonical card schema"""
    
    def test_card_creation(self):
        """Test creating a canonical card"""
        card = CanonicalCard(
            artist_id="artist_001",
            artist_name="Luna Echo",
            primary_genre="Electronic",
            artist_image_url="https://example.com/luna.jpg",
            artist_source=ArtistSource.SPOTIFY,
            tier=CardTier.LEGENDARY,
            print_number=1,
            print_cap=250,
            season=1,
            pack_key="black",
            opened_by="123456789"
        )
        
        assert card.card_id is not None
        assert card.artist["name"] == "Luna Echo"
        assert card.rarity["tier"] == CardTier.LEGENDARY.value
        assert card.identity["serial"].startswith("ML-S1-L-")
        assert card.origin["pack_key"] == "black"
        assert card.presentation["frame_style"] == FrameStyle.LUX_BLACK.value
        assert card.is_hero_card() == True  # Legendary cards are hero cards
    
    def test_serial_generation(self):
        """Test serial number generation"""
        serial = generate_serial(CardTier.LEGENDARY)
        assert serial.startswith("ML-S1-L-")
        assert len(serial) == 13  # ML-S1-L-XXXX
        
        # Test serial info
        info = get_serial_info(serial)
        assert info is not None
        assert info["tier"] == CardTier.LEGENDARY
        assert info["season"] == 1
        assert info["print_number"] > 0
    
    def test_scarcity_info(self):
        """Test scarcity information"""
        scarcity = get_scarcity_info(CardTier.LEGENDARY)
        assert "tier" in scarcity
        assert "print_count" in scarcity
        assert "scarcity" in scarcity
        assert scarcity["tier"] == CardTier.LEGENDARY.value

class TestPackDefinition:
    """Test pack definition system"""
    
    def test_pack_definition_loading(self):
        """Test loading pack definitions"""
        black_pack = get_pack_definition("black")
        assert black_pack is not None
        assert black_pack.key == "black"
        assert black_pack.display_name == "Black Pack"
        assert black_pack.tier == PackTier.PREMIUM
        assert black_pack.cards_per_pack == 5
        assert black_pack.has_hero_slot() == True
        assert black_pack.get_min_rarity() == "gold"
        assert black_pack.validate_odds() == True
    
    def test_pack_odds_validation(self):
        """Test pack odds validation"""
        black_pack = get_pack_definition("black")
        odds = black_pack.get_odds_list()
        
        # Check that odds sum to 1.0
        total_probability = sum(probability for _, probability in odds)
        assert abs(total_probability - 1.0) < 0.01
        
        # Check that all required tiers are present
        tier_names = [tier for tier, _ in odds]
        assert "community" in tier_names
        assert "gold" in tier_names
        assert "platinum" in tier_names
        assert "legendary" in tier_names

class TestHeroSlotSystem:
    """Test hero slot system"""
    
    def test_hero_artist_selection(self):
        """Test hero artist selection"""
        hero_artist = get_hero_artist(CardTier.PLATINUM)
        assert hero_artist is not None
        assert hero_artist.hero_score >= 70.0
        assert hero_artist.is_hero_eligible() == True
    
    def test_standard_artist_selection(self):
        """Test standard artist selection"""
        standard_artist = get_standard_artist(CardTier.GOLD)
        assert standard_artist is not None
        assert standard_artist.artist_id is not None
        assert standard_artist.name is not None
    
    def test_pack_artist_generation(self):
        """Test generating artists for a pack"""
        black_pack = get_pack_definition("black")
        artists = generate_pack_artists(black_pack)
        
        assert len(artists) == black_pack.cards_per_pack
        
        # First artist should be hero eligible (hero slot)
        hero_artist = artists[0]
        assert hero_artist.is_hero_eligible() == True

class TestPaymentProcessing:
    """Test payment processing with canonical cards"""
    
    def test_payment_processing(self):
        """Test complete payment processing"""
        result = handle_payment(123456789, "black", "sess_test_payment")
        
        assert result["status"] == "completed"
        assert result["cards_created"] == 5
        assert "canonical_cards" in result
        assert len(result["canonical_cards"]) == 5
        
        # Check canonical cards
        canonical_cards = result["canonical_cards"]
        for card_data in canonical_cards:
            card = CanonicalCard.from_dict(card_data)
            assert card.card_id is not None
            assert card.rarity["tier"] in ["community", "gold", "platinum", "legendary"]
            assert card.identity["serial"].startswith("ML-S1-")
    
    def test_idempotency(self):
        """Test payment idempotency"""
        # First payment
        result1 = handle_payment(123456789, "black", "sess_test_idempotent")
        assert result1["status"] == "completed"
        
        # Second payment with same ID
        result2 = handle_payment(123456789, "black", "sess_test_idempotent")
        assert result2["status"] == "ALREADY_PROCESSED"
        assert result2["cards_created"] == result1["cards_created"]
    
    def test_canonical_card_generation(self):
        """Test canonical card generation"""
        black_pack = get_pack_definition("black")
        canonical_cards = generate_canonical_cards(black_pack, 123456789, "sess_test_gen")
        
        assert len(canonical_cards) == black_pack.cards_per_pack
        
        # Check hero slot
        hero_card = canonical_cards[0]
        assert hero_card.is_hero_card() == True
        
        # Check minimum rarity guarantee
        min_rarity = black_pack.get_min_rarity()
        has_min_rarity = any(
            card.rarity["tier"] == min_rarity or 
            (card.rarity["tier"] == "platinum" and min_rarity == "gold") or
            (card.rarity["tier"] == "legendary" and min_rarity in ["gold", "platinum"])
            for card in canonical_cards
        )
        assert has_min_rarity == True

class TestCardRendering:
    """Test card rendering system"""
    
    def test_card_embed_creation(self):
        """Test creating Discord embed for card"""
        card = CanonicalCard(
            artist_id="artist_001",
            artist_name="Luna Echo",
            primary_genre="Electronic",
            artist_image_url="https://example.com/luna.jpg",
            artist_source=ArtistSource.SPOTIFY,
            tier=CardTier.LEGENDARY,
            print_number=1,
            print_cap=250,
            season=1,
            pack_key="black",
            opened_by="123456789"
        )
        
        embed_data = create_card_embed(card)
        
        assert "title" in embed_data
        assert "color" in embed_data
        assert "fields" in embed_data
        assert len(embed_data["fields"]) >= 2
        
        # Check field content
        field_names = [field["name"] for field in embed_data["fields"]]
        assert "📊 Card Info" in field_names
        assert "🎨 Artist" in field_names

class TestIntegration:
    """Integration tests for the complete system"""
    
    def test_complete_pack_opening_flow(self):
        """Test complete pack opening flow"""
        # Process payment
        result = handle_payment(123456789, "black", "sess_test_integration")
        assert result["status"] == "completed"
        
        # Check purchase was created
        purchase = Purchase.get_by_payment_id("sess_test_integration")
        assert purchase is not None
        assert purchase.pack_type == "black"
        assert purchase.user_id == 123456789
        
        # Check cards were created
        cards = Card.from_purchase("sess_test_integration")
        assert len(cards) == 5
        
        # Check canonical cards
        canonical_cards = result["canonical_cards"]
        assert len(canonical_cards) == 5
        
        # Verify hero card
        hero_card = CanonicalCard.from_dict(canonical_cards[0])
        assert hero_card.is_hero_card() == True
        
        # Verify serial uniqueness
        serials = [card.identity["serial"] for card in canonical_cards]
        assert len(serials) == len(set(serials))  # All serials unique
    
    def test_pack_varieties(self):
        """Test different pack types"""
        pack_types = ["starter", "silver", "gold", "black"]
        
        for pack_type in pack_types:
            result = handle_payment(123456789, pack_type, f"sess_test_{pack_type}")
            assert result["status"] == "completed"
            
            pack_def = get_pack_definition(pack_type)
            assert result["cards_created"] == pack_def.cards_per_pack
    
    def test_error_handling(self):
        """Test error handling"""
        # Invalid pack type
        result = handle_payment(123456789, "invalid_pack", "sess_test_error")
        assert result["status"] == "error"
        assert "Unknown pack type" in result["error"]

def run_all_tests():
    """Run all tests and return results"""
    test_classes = [
        TestCanonicalCard,
        TestPackDefinition,
        TestHeroSlotSystem,
        TestPaymentProcessing,
        TestCardRendering,
        TestIntegration
    ]
    
    results = {}
    
    for test_class in test_classes:
        class_name = test_class.__name__
        results[class_name] = {"passed": 0, "failed": 0, "errors": []}
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith("test_")]
        
        for method_name in test_methods:
            try:
                test_instance = test_class()
                method = getattr(test_instance, method_name)
                method()
                results[class_name]["passed"] += 1
                print(f"✅ {class_name}.{method_name}")
            except Exception as e:
                results[class_name]["failed"] += 1
                results[class_name]["errors"].append(f"{method_name}: {str(e)}")
                print(f"❌ {class_name}.{method_name}: {str(e)}")
    
    return results

if __name__ == "__main__":
    print("🧪 Running Professional Card System Tests")
    print("=" * 50)
    
    results = run_all_tests()
    
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    total_passed = 0
    total_failed = 0
    
    for class_name, result in results.items():
        passed = result["passed"]
        failed = result["failed"]
        total_passed += passed
        total_failed += failed
        
        status = "✅ PASS" if failed == 0 else "❌ FAIL"
        print(f"{status} {class_name}: {passed} passed, {failed} failed")
        
        if result["errors"]:
            for error in result["errors"]:
                print(f"    - {error}")
    
    print(f"\n🎯 Overall: {total_passed} passed, {total_failed} failed")
    
    if total_failed == 0:
        print("🎉 All tests passed! Professional card system is working perfectly!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
