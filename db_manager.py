from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import os
import asyncio

class DatabaseManager:
    """
    Central async DB manager: one engine, one session factory.
    Provides a contextmanager for async sessions.
    """
    def __init__(self):
        self._engine = None
        self._session_factory = None

    def init_engine(self):
        """Initialize engine + session factory once."""
        if self._engine is not None:
            return

        # Use working directory on Railway (no /data permissions)
        if os.getenv("RAILWAY_ENVIRONMENT"):
            # Use working directory instead of /data
            database_url = "sqlite+aiosqlite:///music_legends.db"
        else:
            # Local development
            database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///music_legends.db")
        
        try:
            # Create Async engine — nonblocking
            self._engine = create_async_engine(
                database_url,
                future=True,
                echo=False  # Set to True for SQL debugging
            )
            
            print(f"🗄️ Database initialized: {database_url}")
            if os.getenv("RAILWAY_ENVIRONMENT"):
                print("📁 Using working directory on Railway")
            else:
                print("💻 Using local database")
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            # Create a fallback in-memory database
            self._engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                future=True,
                echo=False
            )
            print("📁 Using fallback in-memory database")

        # Create session factory
        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession
        )

    @asynccontextmanager
    async def get_session(self):
        """
        Async contextmanager you can use like:
            async with db.get_session() as session:
                <use session>
        Commits or rolls back automatically.
        """
        if self._session_factory is None:
            self.init_engine()

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_marketplace_table(self):
        """Create marketplace table if it doesn't exist"""
        import sqlite3
        if os.getenv("RAILWAY_ENVIRONMENT"):
            db_path = "music_legends.db"  # Working directory
        else:
            db_path = "music_legends.db"
        
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS marketplace_listings (
                        card_id TEXT PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        price INTEGER NOT NULL,
                        status TEXT DEFAULT 'active',
                        listed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        buyer_id INTEGER,
                        sold_at DATETIME,
                        FOREIGN KEY (seller_id) REFERENCES users(user_id),
                        FOREIGN KEY (buyer_id) REFERENCES users(user_id)
                    )
                """)
                conn.commit()
                print("✅ Marketplace table created/verified")
        except Exception as e:
            print(f"❌ Error creating marketplace table: {e}")
            # Don't crash the bot - continue without marketplace

    async def close(self):
        """Close the database engine"""
        if self._engine:
            await self._engine.dispose()
    
    async def backup_database(self):
        """Create a backup of the database to persistent storage"""
        if os.getenv("RAILWAY_ENVIRONMENT"):
            try:
                import shutil
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"/data/music_legends_backup_{timestamp}.db"
                shutil.copy2("/data/music_legends.db", backup_path)
                print(f"💾 Database backed up to: {backup_path}")
                
                # Keep only last 5 backups
                import glob
                backups = sorted(glob.glob("/data/music_legends_backup_*.db"))
                if len(backups) > 5:
                    for old_backup in backups[:-5]:
                        os.remove(old_backup)
                        print(f"🗑️ Removed old backup: {old_backup}")
                        
            except Exception as e:
                print(f"❌ Backup failed: {e}")
    
    async def restore_database_if_needed(self):
        """Restore from backup if main database doesn't exist"""
        if os.getenv("RAILWAY_ENVIRONMENT"):
            if not os.path.exists("/data/music_legends.db"):
                # Look for latest backup
                import glob
                backups = sorted(glob.glob("/data/music_legends_backup_*.db"))
                if backups:
                    latest_backup = backups[-1]
                    import shutil
                    shutil.copy2(latest_backup, "/data/music_legends.db")
                    print(f"🔄 Restored database from: {latest_backup}")
                    return True
        return False

# Single global instance
db_manager = DatabaseManager()
