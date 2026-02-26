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

        # Check for DATABASE_URL from Railway or environment
        database_url = os.getenv("DATABASE_URL")
        
        if database_url:
            # PostgreSQL connection detected
            # Convert postgresql:// to postgresql+asyncpg:// for async SQLAlchemy
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
            # If already in asyncpg format, use as-is
            elif "postgresql+asyncpg://" not in database_url:
                # Assume it's PostgreSQL and add asyncpg driver
                if "://" in database_url:
                    parts = database_url.split("://", 1)
                    database_url = f"postgresql+asyncpg://{parts[1]}"
            
            print(f"🗄️ Database initialized: PostgreSQL (Railway)")
            print(f"📡 Connection: {database_url.split('@')[-1] if '@' in database_url else 'configured'}")
        else:
            # Fallback to SQLite
            if os.getenv("RAILWAY_ENVIRONMENT"):
                # Use working directory instead of /data
                database_url = "sqlite+aiosqlite:///music_legends.db"
                print(f"🗄️ Database initialized: SQLite (Railway working directory)")
            else:
                # Local development
                database_url = "sqlite+aiosqlite:///music_legends.db"
                print(f"🗄️ Database initialized: SQLite (local)")
        
        try:
            # Create Async engine with connection pooling
            self._engine = create_async_engine(
                database_url,
                future=True,
                echo=False,  # Set to True for SQL debugging
                # Connection pool configuration for Railway PostgreSQL
                pool_size=20,              # 20 persistent connections
                max_overflow=10,           # +10 during spikes (30 max)
                pool_timeout=30,           # Wait 30s before error
                pool_recycle=3600,         # Recycle connections after 1 hour
                pool_pre_ping=True,        # Health check before use
            )
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            # Don't use in-memory database - it would lose all data on restart
            # Instead, raise the error so it can be fixed
            raise RuntimeError(f"Database initialization failed: {e}. Cannot use in-memory database as it would lose all user data.")

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
        database_url = os.getenv("DATABASE_URL")

        try:
            if database_url and ("postgresql://" in database_url or "postgres://" in database_url):
                import psycopg2
                from database import _PgConnectionWrapper
                url = database_url
                if url.startswith("postgres://"):
                    url = url.replace("postgres://", "postgresql://", 1)
                conn = _PgConnectionWrapper(psycopg2.connect(url))
            else:
                db_path = "music_legends.db"
                conn = sqlite3.connect(db_path)

            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS marketplace_listings (
                        card_id TEXT PRIMARY KEY,
                        seller_id INTEGER NOT NULL,
                        price INTEGER NOT NULL,
                        status TEXT DEFAULT 'active',
                        listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        buyer_id INTEGER,
                        sold_at TIMESTAMP,
                        FOREIGN KEY (seller_id) REFERENCES users(user_id),
                        FOREIGN KEY (buyer_id) REFERENCES users(user_id)
                    )
                """)
                conn.commit()
                print("Marketplace table created/verified")
        except Exception as e:
            print(f"Error creating marketplace table: {e}")
            # Don't crash the bot - continue without marketplace

    async def close(self):
        """Close the database engine"""
        if self._engine:
            await self._engine.dispose()
    
    async def backup_database(self, backup_type: str = "periodic"):
        """Create a backup of the database using BackupService"""
        try:
            from services.backup_service import backup_service
            
            # Use working directory for database path
            db_path = "music_legends.db"
            if not os.path.exists(db_path):
                print(f"⚠️ Database file not found: {db_path}")
                return False
            
            # Update backup service with correct path
            backup_service.db_path = db_path
            
            # Create backup
            backup_path = await backup_service.backup_to_local(backup_type)
            
            if backup_path:
                print(f"💾 Database backed up to: {backup_path}")
                return True
            else:
                print("⚠️ Backup creation returned None")
                return False
                
        except ImportError:
            # Fallback to simple backup if BackupService not available
            try:
                import shutil
                from datetime import datetime
                from pathlib import Path
                
                db_path = "music_legends.db"
                if not os.path.exists(db_path):
                    return False
                
                backup_dir = Path("backups")
                backup_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"music_legends_backup_{timestamp}.db"
                shutil.copy2(db_path, backup_path)
                print(f"💾 Database backed up to: {backup_path}")
                return True
            except Exception as e:
                print(f"❌ Backup failed: {e}")
                return False
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def restore_database_if_needed(self):
        """Restore from backup if main database doesn't exist"""
        db_path = "music_legends.db"
        
        if not os.path.exists(db_path):
            try:
                from services.backup_service import backup_service
                from pathlib import Path
                import shutil
                import gzip
                
                # Look for latest backup
                backup_dir = Path("backups")
                backups = []
                
                # Check all backup subdirectories
                for subdir in ["shutdown", "critical", "daily", ""]:
                    backup_subdir = backup_dir / subdir if subdir else backup_dir
                    if backup_subdir.exists():
                        backups.extend(backup_subdir.glob("*.db.gz"))
                        backups.extend(backup_subdir.glob("*.db"))
                
                if backups:
                    # Sort by modification time, newest first
                    backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                    latest_backup = backups[0]
                    
                    # Decompress if needed
                    if latest_backup.suffix == '.gz':
                        with gzip.open(latest_backup, 'rb') as f_in:
                            with open(db_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                    else:
                        shutil.copy2(latest_backup, db_path)
                    
                    print(f"🔄 Restored database from: {latest_backup}")
                    return True
            except Exception as e:
                print(f"❌ Restore failed: {e}")
                import traceback
                traceback.print_exc()
        
        return False

# Single global instance
db_manager = DatabaseManager()
