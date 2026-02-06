#!/usr/bin/env python3
"""
Database Setup Script for Music Legends Bot
Creates all necessary database tables and initializes default data
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

class DatabaseSetup:
    def __init__(self, db_path: str = "music_legends.db"):
        self.db_path = db_path
        self._database_url = os.getenv("DATABASE_URL")
        print(f"🗄️ Database Setup for Music Legends Bot")
        print(f"📁 Database Path: {db_path}")
        print("=" * 50)

    def _get_connection(self):
        """Get database connection - PostgreSQL if DATABASE_URL set, else SQLite."""
        if self._database_url:
            import psycopg2
            from database import _PgConnectionWrapper
            url = self._database_url
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return _PgConnectionWrapper(psycopg2.connect(url))
        return sqlite3.connect(self.db_path)

    def create_all_tables(self):
        """Create all database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            print("📋 Creating database tables...")
            
            # 1. Users table
            print("  📝 Creating users table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    discord_tag TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_battles INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    packs_opened INTEGER DEFAULT 0,
                    victory_tokens INTEGER DEFAULT 0
                )
            """)
            
            # 2. Cards table
            print("  🃏 Creating cards table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    type TEXT NOT NULL DEFAULT 'artist',
                    name TEXT NOT NULL,
                    title TEXT,
                    image_url TEXT,
                    youtube_url TEXT,
                    rarity TEXT NOT NULL,
                    variant TEXT DEFAULT 'Classic',
                    era TEXT,
                    impact INTEGER,
                    skill INTEGER,
                    longevity INTEGER,
                    culture INTEGER,
                    hype INTEGER,
                    power INTEGER,
                    serial TEXT,
                    owner_id INTEGER,
                    acquisition_source TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (owner_id) REFERENCES users(user_id)
                )
            """)
            
            # 3. User inventory table
            print("  🎒 Creating user_inventory table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_inventory (
                    user_id INTEGER PRIMARY KEY,
                    gold INTEGER DEFAULT 100,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    daily_streak INTEGER DEFAULT 0,
                    last_daily_claim TIMESTAMP,
                    premium_expires TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # 4. Card collections table
            print("  📚 Creating card_collections table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS card_collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    card_id TEXT,
                    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (card_id) REFERENCES cards(card_id),
                    UNIQUE(user_id, card_id)
                )
            """)
            
            # 5. Creator packs table
            print("  📦 Creating creator_packs table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS creator_packs (
                    pack_id TEXT PRIMARY KEY,
                    creator_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    pack_size INTEGER DEFAULT 5,
                    status TEXT DEFAULT 'draft',
                    cards_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP,
                    total_purchases INTEGER DEFAULT 0,
                    FOREIGN KEY (creator_id) REFERENCES users(user_id)
                )
            """)
            
            # 6. Pack purchases table
            print("  💳 Creating pack_purchases table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pack_purchases (
                    purchase_id TEXT PRIMARY KEY,
                    pack_id TEXT,
                    buyer_id INTEGER,
                    amount_cents INTEGER,
                    platform_cents INTEGER,
                    creator_cents INTEGER,
                    payment_id TEXT,
                    received_cards TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
                    FOREIGN KEY (buyer_id) REFERENCES users(user_id)
                )
            """)
            
            # 7. Battle matches table
            print("  ⚔️ Creating battle_matches table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS battle_matches (
                    match_id TEXT PRIMARY KEY,
                    player_a_id INTEGER,
                    player_b_id INTEGER,
                    wager_level TEXT,
                    wager_amount INTEGER,
                    status TEXT DEFAULT 'pending',
                    winner_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    battle_data TEXT,
                    FOREIGN KEY (player_a_id) REFERENCES users(user_id),
                    FOREIGN KEY (player_b_id) REFERENCES users(user_id),
                    FOREIGN KEY (winner_id) REFERENCES users(user_id)
                )
            """)
            
            # 8. Audit logs table
            print("  📋 Creating audit_logs table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event TEXT,
                    user_id INTEGER,
                    target_id TEXT,
                    payload TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # 9. Server settings table
            print("  ⚙️ Creating server_settings table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS server_settings (
                    server_id INTEGER PRIMARY KEY,
                    premium_expires TIMESTAMP,
                    settings TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 10. Drops table
            print("  🎁 Creating drops table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS drops (
                    drop_id TEXT PRIMARY KEY,
                    channel_id INTEGER,
                    server_id INTEGER,
                    initiator_user_id INTEGER,
                    cards TEXT,
                    drop_type TEXT DEFAULT 'random',
                    expires_at TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (initiator_user_id) REFERENCES users(user_id)
                )
            """)
            
            conn.commit()
            print("✅ All database tables created successfully!")
    
    def create_indexes(self):
        """Create database indexes for better performance"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            print("🔍 Creating database indexes...")
            
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_cards_owner ON cards(owner_id)",
                "CREATE INDEX IF NOT EXISTS idx_cards_rarity ON cards(rarity)",
                "CREATE INDEX IF NOT EXISTS idx_card_collections_user ON card_collections(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_battle_matches_players ON battle_matches(player_a_id, player_b_id)",
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_audit_logs_event ON audit_logs(event)",
                "CREATE INDEX IF NOT EXISTS idx_pack_purchases_buyer ON pack_purchases(buyer_id)",
                "CREATE INDEX IF NOT EXISTS idx_creator_packs_creator ON creator_packs(creator_id)",
                "CREATE INDEX IF NOT EXISTS idx_creator_packs_status ON creator_packs(status)",
                "CREATE INDEX IF NOT EXISTS idx_drops_server ON drops(server_id)",
                "CREATE INDEX IF NOT EXISTS idx_drops_expires ON drops(expires_at)"
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            print("✅ Database indexes created successfully!")
    
    def insert_default_data(self):
        """Insert default/initial data"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            print("📊 Inserting default data...")
            
            # Check if data already exists
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] > 0:
                print("ℹ️ Database already contains data. Skipping default data insertion.")
                return
            
            print("  💰 Creating default bot user...")
            # Create a bot user for system operations
            cursor.execute("""
                INSERT OR IGNORE INTO users (user_id, username, discord_tag)
                VALUES (0, 'MusicLegendsBot', 'MusicLegendsBot')
            """)
            
            print("  🎵 Inserting sample cards...")
            # Insert some sample cards for testing
            sample_cards = [
                {
                    'card_id': 'sample_001',
                    'name': 'Drake',
                    'title': 'Hotline Bling',
                    'rarity': 'common',
                    'impact': 75,
                    'skill': 80,
                    'longevity': 70,
                    'culture': 85,
                    'hype': 90,
                    'power': 80,
                    'image_url': 'https://i.ytimg.com/vi/uxpDa-c-4Mc/hqdefault.jpg'
                },
                {
                    'card_id': 'sample_002', 
                    'name': 'Taylor Swift',
                    'title': 'Shake It Off',
                    'rarity': 'rare',
                    'impact': 90,
                    'skill': 85,
                    'longevity': 88,
                    'culture': 92,
                    'hype': 87,
                    'power': 88,
                    'image_url': 'https://i.ytimg.com/vi/nfWlot6h_JM/hqdefault.jpg'
                },
                {
                    'card_id': 'sample_003',
                    'name': 'Eminem',
                    'title': 'Lose Yourself',
                    'rarity': 'epic',
                    'impact': 95,
                    'skill': 92,
                    'longevity': 94,
                    'culture': 96,
                    'hype': 85,
                    'power': 92,
                    'image_url': 'https://i.ytimg.com/vi/_Yhyp-_hX2s/hqdefault.jpg'
                }
            ]
            
            for card in sample_cards:
                cursor.execute("""
                    INSERT OR IGNORE INTO cards (
                        card_id, name, title, rarity, impact, skill, longevity, 
                        culture, hype, power, image_url, type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    card['card_id'], card['name'], card['title'], card['rarity'],
                    card['impact'], card['skill'], card['longevity'], card['culture'],
                    card['hype'], card['power'], card['image_url'], 'artist'
                ))
            
            conn.commit()
            print("✅ Default data inserted successfully!")
    
    def verify_setup(self):
        """Verify that all tables were created correctly"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            print("🔍 Verifying database setup...")
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [
                'users', 'cards', 'user_inventory', 'card_collections',
                'creator_packs', 'pack_purchases', 'battle_matches',
                'audit_logs', 'server_settings', 'drops'
            ]
            
            print(f"  📋 Found {len(tables)} tables:")
            for table in sorted(tables):
                status = "✅" if table in expected_tables else "⚠️"
                print(f"    {status} {table}")
            
            # Check table counts
            print("\n📊 Table record counts:")
            for table in sorted(tables):
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  📝 {table}: {count} records")
                except sqlite3.Error as e:
                    print(f"  ❌ {table}: Error - {e}")
            
            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                print(f"\n❌ Missing tables: {missing_tables}")
                return False
            else:
                print(f"\n✅ All {len(expected_tables)} expected tables created successfully!")
                return True
    
    def run_full_setup(self):
        """Run the complete database setup"""
        print("🚀 Starting complete database setup...\n")
        
        try:
            self.create_all_tables()
            print()
            self.create_indexes()
            print()
            self.insert_default_data()
            print()
            success = self.verify_setup()
            
            if success:
                print("\n🎉 Database setup completed successfully!")
                print(f"📍 Database file: {os.path.abspath(self.db_path)}")
                print("🎯 Your Music Legends bot is ready to run!")
            else:
                print("\n❌ Database setup completed with errors!")
                return False
                
        except Exception as e:
            print(f"\n❌ Database setup failed: {e}")
            return False
        
        return True

def main():
    """Main setup function"""
    db_path = os.getenv("DB_PATH", "music_legends.db")
    
    print("🎵 Music Legends Bot - Database Setup")
    print("=" * 50)
    
    # Check if database file exists
    if os.path.exists(db_path):
        print(f"⚠️ Database file already exists: {db_path}")
        response = input("Do you want to recreate it? This will delete all data. (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ Setup cancelled.")
            return
        
        # Remove existing database
        os.remove(db_path)
        print(f"🗑️ Removed existing database: {db_path}")
    
    # Run setup
    setup = DatabaseSetup(db_path)
    success = setup.run_full_setup()
    
    if success:
        print("\n✅ Setup completed! You can now run the bot with:")
        print("   python main.py")
    else:
        print("\n❌ Setup failed! Please check the error messages above.")

if __name__ == "__main__":
    main()
