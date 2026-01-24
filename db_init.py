import asyncio
from sqlalchemy import text
from db_manager import db_manager
from models import Base

async def init_database():
    """Initialize database tables"""
    print("🗄️ Initializing database...")
    
    # Initialize the engine
    db_manager.init_engine()
    
    # Create all tables
    async with db_manager.get_session() as session:
        # Create tables
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR PRIMARY KEY,
                username VARCHAR,
                is_dev BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS youtube_videos (
                video_id VARCHAR PRIMARY KEY,
                title VARCHAR,
                thumbnail_url VARCHAR,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                channel_title VARCHAR,
                channel_id VARCHAR,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS card_definitions (
                card_def_id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_video_id VARCHAR,
                card_name VARCHAR NOT NULL,
                rarity VARCHAR DEFAULT 'Common',
                power INTEGER DEFAULT 50,
                attributes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_video_id) REFERENCES youtube_videos(video_id)
            )
        """))
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS card_instances (
                instance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_def_id INTEGER,
                owner_user_id VARCHAR,
                serial_number VARCHAR,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (card_def_id) REFERENCES card_definitions(card_def_id),
                FOREIGN KEY (owner_user_id) REFERENCES users(user_id)
            )
        """))
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS packs (
                pack_id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id VARCHAR,
                main_hero_instance_id INTEGER,
                pack_type VARCHAR DEFAULT 'gold',
                status VARCHAR DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (creator_id) REFERENCES users(user_id),
                FOREIGN KEY (main_hero_instance_id) REFERENCES card_instances(instance_id)
            )
        """))
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS pack_contents (
                pack_id INTEGER,
                instance_id INTEGER,
                position INTEGER,
                PRIMARY KEY (pack_id, instance_id),
                FOREIGN KEY (pack_id) REFERENCES packs(pack_id),
                FOREIGN KEY (instance_id) REFERENCES card_instances(instance_id)
            )
        """))
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS marketplace_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id INTEGER,
                price REAL DEFAULT 9.99,
                listed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                stock VARCHAR DEFAULT 'unlimited',
                FOREIGN KEY (pack_id) REFERENCES packs(pack_id)
            )
        """))
        
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                buyer_id VARCHAR,
                seller_id VARCHAR,
                tx_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                price REAL,
                FOREIGN KEY (item_id) REFERENCES marketplace_items(item_id),
                FOREIGN KEY (buyer_id) REFERENCES users(user_id),
                FOREIGN KEY (seller_id) REFERENCES users(user_id)
            )
        """))
        
        # Create indexes for performance
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_card_instances_owner ON card_instances(owner_user_id)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_pack_contents_pack ON pack_contents(pack_id)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_marketplace_active ON marketplace_items(is_active)"))
        await session.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_buyer ON transactions(buyer_id)"))
        
        print("✅ Database tables created successfully")

if __name__ == "__main__":
    asyncio.run(init_database())
