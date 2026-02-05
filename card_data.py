# card_data.py - Master card data and management
import json
from typing import List, Dict
from database import DatabaseManager

class CardDataManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.sample_cards = self._get_sample_cards()
    
    def _get_sample_cards(self) -> List[Dict]:
        """Get sample card data for initial setup"""
        return [
            {
                "card_id": "ART-001",
                "name": "Kendrick Lamar",
                "title": "CULTURE KING",
                "rarity": "Legendary",
                "era": "2010s",
                "variant": "Classic",
                "impact": 92,
                "skill": 95,
                "longevity": 88,
                "culture": 99,
                "hype": 86,
                "image_url": "https://i.imgur.com/kendrick_example.png",

                "youtube_url": "https://www.youtube.com/watch?v=JKbIMxf3d3U",
                "card_type": "artist"
            },
            {
                "card_id": "ART-002",
                "name": "Drake",
                "title": "CHART MASTER",
                "rarity": "Legendary",
                "era": "2010s",
                "variant": "Classic",
                "impact": 90,
                "skill": 85,
                "longevity": 94,
                "culture": 91,
                "hype": 89,
                "image_url": "https://i.imgur.com/drake_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=xpVfcn0CV5c",
                "card_type": "artist"
            },
            {
                "card_id": "ART-003",
                "name": "Taylor Swift",
                "title": "POP SENSATION",
                "rarity": "Epic",
                "era": "2020s",
                "variant": "Classic",
                "impact": 85,
                "skill": 88,
                "longevity": 92,
                "culture": 95,
                "hype": 87,
                "image_url": "https://i.imgur.com/taylor_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=BWW4Ea5_3pU",
                "card_type": "artist"
            },
            {
                "card_id": "ART-004",
                "name": "The Weeknd",
                "title": "DARK POP",
                "rarity": "Epic",
                "era": "2020s",
                "variant": "Classic",
                "impact": 87,
                "skill": 83,
                "longevity": 89,
                "culture": 85,
                "hype": 91,
                "image_url": "https://i.imgur.com/weeknd_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=4Cd0XKzqEy4",
                "card_type": "artist"
            },
            {
                "card_id": "ART-005",
                "name": "Billie Eilish",
                "title": "GEN Z ICON",
                "rarity": "Rare",
                "era": "2020s",
                "variant": "Classic",
                "impact": 82,
                "skill": 86,
                "longevity": 85,
                "culture": 88,
                "hype": 84,
                "image_url": "https://i.imgur.com/billie_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=DyDfgMOUjCI",
                "card_type": "artist"
            },
            {
                "card_id": "ART-006",
                "name": "Post Malone",
                "title": "CROSSOVER KING",
                "rarity": "Rare",
                "era": "2020s",
                "variant": "Classic",
                "impact": 80,
                "skill": 82,
                "longevity": 86,
                "culture": 83,
                "hype": 88,
                "image_url": "https://i.imgur.com/postmalone_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=U-AYl_ObySQ",
                "card_type": "artist"
            },
            {
                "card_id": "ART-007",
                "name": "Travis Scott",
                "title": "ASTROWORLD",
                "rarity": "Epic",
                "era": "2020s",
                "variant": "Classic",
                "impact": 84,
                "skill": 81,
                "longevity": 87,
                "culture": 89,
                "hype": 93,
                "image_url": "https://i.imgur.com/travis_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=6ONRf7H3pic",
                "card_type": "artist"
            },
            {
                "card_id": "ART-008",
                "name": "Ariana Grande",
                "title": "VOCAL POWERHOUSE",
                "rarity": "Epic",
                "era": "2020s",
                "variant": "Classic",
                "impact": 83,
                "skill": 90,
                "longevity": 88,
                "culture": 86,
                "hype": 85,
                "image_url": "https://i.imgur.com/ariana_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=gl1aHtxXcng",
                "card_type": "artist"
            },
            {
                "card_id": "ART-009",
                "name": "Ed Sheeran",
                "title": "SONGWRITER",
                "rarity": "Rare",
                "era": "2010s",
                "variant": "Classic",
                "impact": 78,
                "skill": 85,
                "longevity": 90,
                "culture": 82,
                "hype": 80,
                "image_url": "https://i.imgur.com/edsheeran_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
                "card_type": "artist"
            },
            {
                "card_id": "ART-010",
                "name": "Doja Cat",
                "title": "POP FUSION",
                "rarity": "Rare",
                "era": "2020s",
                "variant": "Classic",
                "impact": 81,
                "skill": 84,
                "longevity": 83,
                "culture": 87,
                "hype": 86,
                "image_url": "https://i.imgur.com/doja_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=kOq85cYmF9Q",
                "card_type": "artist"
            },
            {
                "card_id": "ART-011",
                "name": "Lil Nas X",
                "title": "GENRE BENDER",
                "rarity": "Rare",
                "era": "2020s",
                "variant": "Classic",
                "impact": 79,
                "skill": 82,
                "longevity": 84,
                "culture": 90,
                "hype": 88,
                "image_url": "https://i.imgur.com/lilnasx_example.png",
                "youtube_url": "https://www.youtube.com/watch?v=7ysqg2L38OA",
                "card_type": "artist"
            },
            {
                "card_id": "ART-012",
                "name": "Olivia Rodrigo",
                "title": "TEEN DREAM",
                "rarity": "Common",
                "era": "2020s",
                "variant": "Classic",
                "impact": 75,
                "skill": 78,
                "longevity": 80,
                "culture": 82,
                "hype": 85,
                "image_url": "https://i.imgur.com/olivia_example.png",
                "youtube_url": "https://www.youtube.com/watch?v/ppgOKCTYm1A",
                "card_type": "artist"
            }
        ]
    
    def initialize_database_cards(self):
        """Load all sample cards into the database"""
        success_count = 0
        for card in self.sample_cards:
            if self.db.add_card_to_master(card):
                success_count += 1
        
        print(f"✅ Loaded {success_count}/{len(self.sample_cards)} cards into database")
        return success_count
    
    def get_card_by_id(self, card_id: str) -> Dict:
        """Get card data by ID"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cards WHERE card_id = ?", (card_id,))
        card = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        if card:
            return dict(zip(columns, card))
        return None
    
    def get_all_cards(self) -> List[Dict]:
        """Get all cards from database"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cards ORDER BY rarity DESC, name")
        cards = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        return [dict(zip(columns, card)) for card in cards]
    
    def get_cards_by_rarity(self, rarity: str) -> List[Dict]:
        """Get cards filtered by rarity"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cards WHERE rarity = ? ORDER BY name", (rarity,))
        cards = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()

        return [dict(zip(columns, card)) for card in cards]
    
    def generate_pack_drop(self, pack_type: str = "Daily") -> List[str]:
        """Generate a pack drop with guaranteed rarities"""
        import random
        
        # Define pack composition
        pack_configs = {
            "Daily": {
                "guaranteed_rarity": "Rare",
                "total_cards": 5,
                "distribution": {"Common": 2, "Rare": 2, "Epic": 1}
            },
            "Victory": {
                "guaranteed_rarity": "Epic", 
                "total_cards": 3,
                "distribution": {"Rare": 1, "Epic": 1, "Legendary": 0.2}
            },
            "Premium": {
                "guaranteed_rarity": "Epic",
                "total_cards": 7,
                "distribution": {"Common": 2, "Rare": 2, "Epic": 2, "Legendary": 1}
            }
        }
        
        config = pack_configs.get(pack_type, pack_configs["Daily"])
        cards_received = []
        
        # Get cards by rarity
        rarity_pools = {}
        for rarity in ["Common", "Rare", "Epic", "Legendary"]:
            rarity_pools[rarity] = self.get_cards_by_rarity(rarity)
        
        # Generate pack
        for rarity, count in config["distribution"].items():
            available_cards = rarity_pools.get(rarity, [])
            if available_cards:
                if isinstance(count, float):
                    # Handle probability (e.g., 0.2 = 20% chance)
                    if random.random() < count:
                        cards_received.append(random.choice(available_cards)["card_id"])
                else:
                    # Handle guaranteed count
                    for _ in range(count):
                        cards_received.append(random.choice(available_cards)["card_id"])
        
        # Ensure guaranteed rarity is included
        guaranteed_cards = rarity_pools.get(config["guaranteed_rarity"], [])
        if guaranteed_cards:
            # Check if any received card has the guaranteed rarity
            guaranteed_rarity_ids = {c["card_id"] for c in guaranteed_cards}
            has_guaranteed = any(cid in guaranteed_rarity_ids for cid in cards_received)
            if not has_guaranteed and cards_received:
                cards_received[0] = random.choice(guaranteed_cards)["card_id"]
        
        return cards_received[:config["total_cards"]]
    
    def import_cards_from_json(self, file_path: str) -> int:
        """Import cards from JSON file"""
        try:
            with open(file_path, 'r') as f:
                cards = json.load(f)
            
            success_count = 0
            for card in cards:
                if self.db.add_card_to_master(card):
                    success_count += 1
            
            print(f"✅ Imported {success_count}/{len(cards)} cards from {file_path}")
            return success_count
        except Exception as e:
            print(f"❌ Error importing cards: {e}")
            return 0
    
    def export_cards_to_json(self, file_path: str) -> bool:
        """Export all cards to JSON file"""
        try:
            cards = self.get_all_cards()
            with open(file_path, 'w') as f:
                json.dump(cards, f, indent=2)
            print(f"✅ Exported {len(cards)} cards to {file_path}")
            return True
        except Exception as e:
            print(f"❌ Error exporting cards: {e}")
            return False
