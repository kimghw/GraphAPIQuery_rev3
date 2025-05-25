"""Database configuration and setup."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import structlog
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from config.settings import Settings, get_settings

logger = structlog.get_logger()


class DatabaseAdapter:
    """Database adapter for managing connections and sessions."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._async_engine = None
        self._sync_engine = None
        self._async_session_factory = None
        self._sync_session_factory = None
        self._initialized = False
    
    def _get_async_database_url(self) -> str:
        """Convert database URL to async version."""
        url = self.settings.DATABASE_URL
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        return url
    
    async def initialize(self) -> None:
        """Initialize database engines and session factories."""
        if self._initialized:
            return
        
        try:
            # Create async engine
            async_url = self._get_async_database_url()
            
            if "sqlite" in async_url:
                self._async_engine = create_async_engine(
                    async_url,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                    echo=self.settings.DATABASE_ECHO
                )
            else:
                self._async_engine = create_async_engine(
                    async_url,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    echo=self.settings.DATABASE_ECHO
                )
            
            # Create sync engine for migrations
            if "sqlite" in self.settings.DATABASE_URL:
                self._sync_engine = create_engine(
                    self.settings.DATABASE_URL,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                    echo=self.settings.DATABASE_ECHO
                )
            else:
                self._sync_engine = create_engine(
                    self.settings.DATABASE_URL,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    echo=self.settings.DATABASE_ECHO
                )
            
            # Create session factories
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                expire_on_commit=False
            )
            
            # Apply SQLite optimizations
            if "sqlite" in self.settings.DATABASE_URL:
                await self._apply_sqlite_optimizations()
            
            self._initialized = True
            
            logger.info(
                "Database adapter initialized",
                database_url=self.settings.DATABASE_URL,
                async_url=async_url
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize database adapter",
                error=str(e)
            )
            raise
    
    async def _apply_sqlite_optimizations(self) -> None:
        """Apply SQLite-specific optimizations."""
        try:
            async with self._async_engine.begin() as conn:
                await conn.execute(text("PRAGMA foreign_keys=ON"))
                await conn.execute(text("PRAGMA journal_mode=WAL"))
                await conn.execute(text("PRAGMA synchronous=NORMAL"))
                await conn.execute(text("PRAGMA temp_store=MEMORY"))
                await conn.execute(text("PRAGMA mmap_size=268435456"))  # 256MB
                
            logger.info("SQLite optimizations applied")
            
        except Exception as e:
            logger.warning(
                "Failed to apply SQLite optimizations",
                error=str(e)
            )
    
    @asynccontextmanager
    async def session_scope(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a transactional scope around a series of operations."""
        if not self._initialized:
            await self.initialize()
        
        async with self._async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def sync_session_scope(self):
        """Provide a synchronous transactional scope."""
        if not self._sync_session_factory:
            raise RuntimeError("Database adapter not initialized")
        
        session = self._sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def close(self) -> None:
        """Close database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        
        if self._sync_engine:
            self._sync_engine.dispose()
        
        self._initialized = False
        logger.info("Database adapter closed")
    
    @property
    def async_engine(self):
        """Get async engine."""
        return self._async_engine
    
    @property
    def sync_engine(self):
        """Get sync engine."""
        return self._sync_engine


# Global database adapter instance
_database_adapter: Optional[DatabaseAdapter] = None


def get_database_adapter(settings: Optional[Settings] = None) -> DatabaseAdapter:
    """Get or create database adapter instance."""
    global _database_adapter
    
    if _database_adapter is None:
        if settings is None:
            settings = get_settings()
        _database_adapter = DatabaseAdapter(settings)
    
    return _database_adapter


async def migrate_database(settings: Settings) -> None:
    """Run database migrations asynchronously."""
    try:
        # Import models to ensure they're registered
        from adapters.db.models import Base
        
        adapter = get_database_adapter(settings)
        await adapter.initialize()
        
        # Create all tables
        async with adapter.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database migration completed")
        
    except Exception as e:
        logger.error(
            "Database migration failed",
            error=str(e)
        )
        raise


def migrate_database_sync(settings: Settings) -> None:
    """Run database migrations synchronously."""
    try:
        # Import models to ensure they're registered
        from adapters.db.models import Base
        
        adapter = get_database_adapter(settings)
        
        # Initialize sync engine if not already done
        if adapter._sync_engine is None:
            if "sqlite" in settings.DATABASE_URL:
                adapter._sync_engine = create_engine(
                    settings.DATABASE_URL,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                    echo=settings.DATABASE_ECHO
                )
            else:
                adapter._sync_engine = create_engine(
                    settings.DATABASE_URL,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    echo=settings.DATABASE_ECHO
                )
        
        # Create all tables
        Base.metadata.create_all(bind=adapter._sync_engine)
        
        # Apply SQLite optimizations if needed
        if "sqlite" in settings.DATABASE_URL:
            with adapter._sync_engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.execute(text("PRAGMA temp_store=MEMORY"))
                conn.execute(text("PRAGMA mmap_size=268435456"))
                conn.commit()
        
        logger.info("Database migration completed (sync)")
        
    except Exception as e:
        logger.error(
            "Database migration failed (sync)",
            error=str(e)
        )
        raise


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    adapter = get_database_adapter()
    async with adapter.session_scope() as session:
        yield session
