"""
Database management system
"""

import logging
import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import redis.asyncio as redis

from .config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self):
        self.engine = None
        self.async_session_factory = None
        self.redis_client = None
        
    async def initialize(self):
        """Initialize database connections"""
        try:
            # Initialize SQLAlchemy
            self.engine = create_async_engine(
                settings.database_url,
                echo=settings.debug,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            self.async_session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Initialize Redis
            self.redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connections
            await self._test_connections()
            
            logger.info("Database connections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _test_connections(self):
        """Test database connections"""
        # Test SQLAlchemy
        async with self.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Test Redis
        await self.redis_client.ping()
        
        logger.info("Database connections test passed")
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized")
            
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis client"""
        if not self.redis_client:
            raise RuntimeError("Redis not initialized")
        return self.redis_client
    
    async def close(self):
        """Close all database connections"""
        try:
            if self.engine:
                await self.engine.dispose()
            if self.redis_client:
                await self.redis_client.close()
            logger.info("Database connections closed")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")

# Global database manager instance
db_manager = DatabaseManager()