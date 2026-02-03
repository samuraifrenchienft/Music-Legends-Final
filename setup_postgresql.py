#!/usr/bin/env python3
"""
PostgreSQL Database Setup for Music Legends Bot on Railway
Creates all necessary PostgreSQL tables and initializes default data
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json

class PostgreSQLSetup:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        print("🗄️ PostgreSQL Setup for Music Legends Bot (Railway)")
        print(f"🔗 Database URL: {self.db_url.split('@')[1] if '@' in self.db_url else 'configured'}")
        print("=" * 60)
    
    def get_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(self.db_url)
    
    def create_all_tables(self):
        """Create all PostgreSQL tables"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                print("📋 Creating PostgreSQL tables...")
                
                # 1. Users table
                print("  📝 Creating users table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username VARCHAR(255),
                        discord_tag VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
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
                        card_id VARCHAR(255) PRIMARY KEY,
                        type VARCHAR(50) NOT NULL DEFAULT 'artist',
                        spotify_artist_id VARCHAR(255),
                        spotify_track_id VARCHAR(255),
                        name VARCHAR(255) NOT NULL,
                        title VARCHAR(255),
                        image_url TEXT,
                        spotify_url TEXT,
                        youtube_url TEXT,
                        rarity VARCHAR(50) NOT NULL,
                        variant VARCHAR(100) DEFAULT 'Classic',
                        era VARCHAR(100),
                        impact INTEGER,
                        skill INTEGER,
                        longevity INTEGER,
                        culture INTEGER,
                        hype INTEGER,
                        power INTEGER,
                        serial VARCHAR(255),
                        owner_id BIGINT,
                        acquisition_source VARCHAR(100),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (owner_id) REFERENCES users(user_id)
                    )
                """)
                
                # 3. User inventory table
                print("  🎒 Creating user_inventory table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_inventory (
                        user_id BIGINT PRIMARY KEY,
                        gold INTEGER DEFAULT 100,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        daily_streak INTEGER DEFAULT 0,
                        last_daily_claim TIMESTAMP WITH TIME ZONE,
                        premium_expires TIMESTAMP WITH TIME ZONE,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # 4. Card collections table
                print("  📚 Creating card_collections table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS card_collections (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT,
                        card_id VARCHAR(255),
                        acquired_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (card_id) REFERENCES cards(card_id),
                        UNIQUE(user_id, card_id)
                    )
                """)
                
                # 5. Creator packs table
                print("  📦 Creating creator_packs table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS creator_packs (
                        pack_id VARCHAR(255) PRIMARY KEY,
                        creator_id BIGINT,
                        pack_name VARCHAR(255) NOT NULL,
                        description TEXT,
                        pack_size INTEGER DEFAULT 5,
                        status VARCHAR(50) DEFAULT 'draft',
                        cards_data TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        published_at TIMESTAMP WITH TIME ZONE,
                        total_purchases INTEGER DEFAULT 0,
                        FOREIGN KEY (creator_id) REFERENCES users(user_id)
                    )
                """)
                
                # 6. Pack purchases table
                print("  💳 Creating pack_purchases table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pack_purchases (
                        purchase_id VARCHAR(255) PRIMARY KEY,
                        pack_id VARCHAR(255),
                        buyer_id BIGINT,
                        amount_cents INTEGER,
                        platform_cents INTEGER,
                        creator_cents INTEGER,
                        payment_id VARCHAR(255),
                        received_cards TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (pack_id) REFERENCES creator_packs(pack_id),
                        FOREIGN KEY (buyer_id) REFERENCES users(user_id)
                    )
                """)
                
                # 7. Battle matches table
                print("  ⚔️ Creating battle_matches table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS battle_matches (
                        match_id VARCHAR(255) PRIMARY KEY,
                        player_a_id BIGINT,
                        player_b_id BIGINT,
                        wager_level VARCHAR(50),
                        wager_amount INTEGER,
                        status VARCHAR(50) DEFAULT 'pending',
                        winner_id BIGINT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP WITH TIME ZONE,
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
                        id BIGSERIAL PRIMARY KEY,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        event VARCHAR(255),
                        user_id BIGINT,
                        target_id VARCHAR(255),
                        payload TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                """)
                
                # 9. Server settings table
                print("  ⚙️ Creating server_settings table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS server_settings (
                        server_id BIGINT PRIMARY KEY,
                        premium_expires TIMESTAMP WITH TIME ZONE,
                        settings TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 10. Drops table
                print("  🎁 Creating drops table...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS drops (
                        drop_id VARCHAR(255) PRIMARY KEY,
                        channel_id BIGINT,
                        server_id BIGINT,
                        initiator_user_id BIGINT,
                        cards TEXT,
                        drop_type VARCHAR(50) DEFAULT 'random',
                        expires_at TIMESTAMP WITH TIME ZONE,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (initiator_user_id) REFERENCES users(user_id)
                    )
                """)
                
                conn.commit()
                print("✅ All PostgreSQL tables created successfully!")
    
    def create_indexes(self):
        """Create PostgreSQL indexes for better performance"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                
                print("🔍 Creating PostgreSQL indexes...")
                
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
                    "CREATE INDEX IF NOT EXISTS idx_drops_expires ON drops(expires_at)",
                    "CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)",
                    "CREATE INDEX IF NOT EXISTS idx_cards_created_at ON cards(created_at)"
                ]
                
                for index_sql in indexes:
                    try:
                        cursor.execute(index_sql)
                    except Exception as e:
                        print(f"  ⚠️ Index creation warning: {e}")
                
                conn.commit()
                print("✅ PostgreSQL indexes created successfully!")
    
    def insert_default_data(self):
        """Insert default/initial data"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                print("📊 Inserting default data...")
                
                # Check if data already exists
                cursor.execute("SELECT COUNT(*) as count FROM users")
                if cursor.fetchone()['count'] > 0:
                    print("ℹ️ Database already contains data. Skipping default data insertion.")
                    return
                
                print("  💰 Creating default bot user...")
                # Create a bot user for system operations
                cursor.execute("""
                    INSERT INTO users (user_id, username, discord_tag)
                    VALUES (0, 'MusicLegendsBot', 'Bot#0000')
                    ON CONFLICT (user_id) DO NOTHING
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
                        INSERT INTO cards (
                            card_id, name, title, rarity, impact, skill, longevity, 
                            culture, hype, power, image_url, type
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (card_id) DO NOTHING
                    """, (
                        card['card_id'], card['name'], card['title'], card['rarity'],
                        card['impact'], card['skill'], card['longevity'], card['culture'],
                        card['hype'], card['power'], card['image_url'], 'artist'
                    ))
                
                conn.commit()
                print("✅ Default data inserted successfully!")
    
    def verify_setup(self):
        """Verify that all tables were created correctly"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                
                print("🔍 Verifying PostgreSQL setup...")
                
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = [row['table_name'] for row in cursor.fetchall()]
                
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
                        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                        count = cursor.fetchone()['count']
                        print(f"  📝 {table}: {count} records")
                    except Exception as e:
                        print(f"  ❌ {table}: Error - {e}")
                
                missing_tables = set(expected_tables) - set(tables)
                if missing_tables:
                    print(f"\n❌ Missing tables: {missing_tables}")
                    return False
                else:
                    print(f"\n✅ All {len(expected_tables)} expected tables created successfully!")
                    return True
    
    def run_full_setup(self):
        """Run the complete PostgreSQL setup"""
        print("🚀 Starting complete PostgreSQL setup on Railway...\n")
        
        try:
            # Test connection first
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                    print(f"🔗 Connected to PostgreSQL: {version.split(',')[0]}")
            
            self.create_all_tables()
            print()
            self.create_indexes()
            print()
            self.insert_default_data()
            print()
            success = self.verify_setup()
            
            if success:
                print("\n🎉 PostgreSQL setup completed successfully!")
                print("🎯 Your Music Legends bot is ready to run on Railway!")
            else:
                print("\n❌ PostgreSQL setup completed with errors!")
                return False
                
        except Exception as e:
            print(f"\n❌ PostgreSQL setup failed: {e}")
            return False
        
        return True

def main():
    """Main setup function"""
    print("🎵 Music Legends Bot - PostgreSQL Setup (Railway)")
    print("=" * 60)
    
    # Check DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL environment variable not set!")
        print("📝 Please set DATABASE_URL in your Railway environment variables")
        print("🔗 Format: postgresql://username:password@host:port/database")
        return
    
    # Run setup
    setup = PostgreSQLSetup()
    success = setup.run_full_setup()
    
    if success:
        print("\n✅ Setup completed! Your bot can now use PostgreSQL on Railway!")
        print("🚀 Restart your bot to start using the new database.")
    else:
        print("\n❌ Setup failed! Please check the error messages above.")

if __name__ == "__main__":
    main()
