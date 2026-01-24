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

        # Use SQLite with async driver for Railway compatibility
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///music_legends.db")
        
        # Create Async engine — nonblocking
        self._engine = create_async_engine(
            database_url,
            future=True,
            echo=False  # Set to True for SQL debugging
        )

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

    async def close(self):
        """Close the engine when shutting down."""
        if self._engine:
            await self._engine.dispose()

# Single global instance
db_manager = DatabaseManager()
