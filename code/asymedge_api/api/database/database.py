"""
ASYMEdge Dashboard API - Database Management

Database connection management, initialization, and utilities for:
- Database connection handling
- Session management
- Database initialization and migrations
- Connection pooling
- Database health checks
"""

from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator, Optional
import asyncio
import logging

from api.config import settings
from api.database.models import Base

logger = logging.getLogger(__name__)

# Database engine configuration
engine = None
SessionLocal = None

def get_database_url() -> str:
    """Get properly formatted database URL"""
    return settings.get_database_url()

def create_engine_config():
    """Create database engine with appropriate configuration"""
    database_url = get_database_url()
    
    # Configure engine based on database type
    if database_url.startswith("sqlite"):
        # SQLite configuration
        engine_config = {
            "echo": settings.DATABASE_ECHO,
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 30
            },
            "future": True
        }
    else:
        # PostgreSQL/MySQL configuration
        engine_config = {
            "echo": settings.DATABASE_ECHO,
            "pool_size": 20,
            "max_overflow": 30,
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "future": True
        }
    
    return create_engine(database_url, **engine_config)

def get_session_factory():
    """Get session factory for database operations"""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False
    )

async def init_database():
    """Initialize database and create all tables"""
    global engine, SessionLocal
    
    try:
        # Create engine
        engine = create_engine_config()
        
        # Create session factory
        SessionLocal = get_session_factory()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database initialized successfully")
        
        # Insert default data if needed
        await seed_default_data()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def close_database():
    """Close database connections"""
    global engine
    
    if engine:
        engine.dispose()
        logger.info("Database connections closed")

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        db.close()

async def get_database() -> Session:
    """Get database session for FastAPI dependency injection"""
    async with get_db_session() as session:
        yield session

async def check_database_health() -> dict:
    """Check database health and connectivity"""
    try:
        with get_db_session() as db:
            # Test basic connectivity
            result = db.execute(text("SELECT 1")).scalar()
            
            # Get database info
            db_info = {}
            if get_database_url().startswith("sqlite"):
                db_info["type"] = "SQLite"
                db_info["file"] = get_database_url().replace("sqlite:///", "")
            else:
                db_info["type"] = "PostgreSQL/MySQL"
            
            # Get table counts
            table_counts = {}
            for table_name in ['users', 'agent_instances', 'workflow_instances', 'trading_metrics']:
                try:
                    count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                    table_counts[table_name] = count
                except:
                    table_counts[table_name] = 0
            
            return {
                "status": "healthy",
                "connectivity": result == 1,
                "database": db_info,
                "tables": table_counts,
                "timestamp": result
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connectivity": False,
            "error": str(e),
            "timestamp": None
        }

async def backup_database(backup_path: Optional[str] = None) -> str:
    """Create database backup"""
    if not backup_path:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_asymedge_{timestamp}.db"
    
    try:
        import shutil
        
        # For SQLite, simply copy the database file
        if get_database_url().startswith("sqlite"):
            db_path = get_database_url().replace("sqlite:///", "")
            shutil.copy2(db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
        else:
            # For PostgreSQL/MySQL, use database-specific backup commands
            logger.warning("Database backup not implemented for PostgreSQL/MySQL")
            raise NotImplementedError("Database backup only implemented for SQLite")
        
        return backup_path
        
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        raise

async def restore_database(backup_path: str):
    """Restore database from backup"""
    try:
        import shutil
        import os
        
        if get_database_url().startswith("sqlite"):
            db_path = get_database_url().replace("sqlite:///", "")
            
            # Close existing connections
            await close_database()
            
            # Backup current database
            if os.path.exists(db_path):
                backup_current = f"{db_path}.backup"
                shutil.copy2(db_path, backup_current)
                logger.info(f"Current database backed up to {backup_current}")
            
            # Restore from backup
            shutil.copy2(backup_path, db_path)
            
            # Reinitialize
            await init_database()
            
            logger.info(f"Database restored from {backup_path}")
        else:
            logger.warning("Database restore not implemented for PostgreSQL/MySQL")
            raise NotImplementedError("Database restore only implemented for SQLite")
        
    except Exception as e:
        logger.error(f"Database restore failed: {e}")
        raise

async def get_table_info() -> dict:
    """Get information about database tables"""
    try:
        with get_db_session() as db:
            table_info = {}
            
            # Get all table names
            result = db.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ))
            
            tables = [row[0] for row in result.fetchall()]
            
            for table_name in tables:
                # Get table schema
                schema_result = db.execute(text(
                    f"PRAGMA table_info({table_name})"
                ))
                columns = []
                for row in schema_result.fetchall():
                    columns.append({
                        "name": row[1],
                        "type": row[2],
                        "nullable": not row[3],
                        "primary_key": bool(row[5])
                    })
                
                # Get row count
                try:
                    count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    row_count = count_result.scalar()
                except:
                    row_count = 0
                
                table_info[table_name] = {
                    "columns": columns,
                    "row_count": row_count
                }
            
            return table_info
            
    except Exception as e:
        logger.error(f"Failed to get table info: {e}")
        return {}

async def vacuum_database():
    """Optimize database by running VACUUM (SQLite only)"""
    if not get_database_url().startswith("sqlite"):
        logger.warning("VACUUM operation only available for SQLite")
        return
    
    try:
        with get_db_session() as db:
            db.execute(text("VACUUM"))
            db.commit()
        logger.info("Database vacuumed successfully")
    except Exception as e:
        logger.error(f"Database vacuum failed: {e}")
        raise

async def analyze_database():
    """Analyze database statistics (SQLite only)"""
    if not get_database_url().startswith("sqlite"):
        logger.warning("ANALYZE operation only available for SQLite")
        return
    
    try:
        with get_db_session() as db:
            db.execute(text("ANALYZE"))
            db.commit()
        logger.info("Database analyzed successfully")
    except Exception as e:
        logger.error(f"Database analyze failed: {e}")
        raise

async def seed_default_data():
    """Seed database with default data"""
    try:
        with get_db_session() as db:
            # Check if we already have data
            user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
            if user_count > 0:
                logger.info("Database already seeded with data")
                return
            
            # Create default admin user (for demonstration)
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            admin_user = Base.metadata.tables['users'].insert().values({
                'email': 'admin@asymedge.com',
                'username': 'admin',
                'hashed_password': pwd_context.hash('admin123'),
                'full_name': 'System Administrator',
                'is_active': True,
                'is_verified': True,
                'is_superuser': True,
                'tier': 'enterprise'
            })
            db.execute(admin_user)
            
            # Create default agent definitions
            agent_definitions = [
                {
                    'name': 'Trading Analyst',
                    'description': 'Analyzes market data and provides trading insights',
                    'letta_agent_type': 'trading_analyst',
                    'configuration': {
                        'model': 'gpt-4',
                        'tools': ['market_data', 'portfolio_analysis'],
                        'memory_type': 'conversation'
                    },
                    'version': '1.0.0'
                },
                {
                    'name': 'Risk Monitor',
                    'description': 'Monitors portfolio risk and alerts on anomalies',
                    'letta_agent_type': 'risk_monitor',
                    'configuration': {
                        'model': 'gpt-4',
                        'tools': ['risk_analysis', 'alert_system'],
                        'memory_type': 'persistent'
                    },
                    'version': '1.0.0'
                }
            ]
            
            for agent_def in agent_definitions:
                insert_stmt = Base.metadata.tables['agent_definitions'].insert().values(agent_def)
                db.execute(insert_stmt)
            
            # Create default workflow definitions
            workflow_definitions = [
                {
                    'name': 'Daily Portfolio Analysis',
                    'description': 'Comprehensive daily portfolio analysis and reporting',
                    'workflow_type': 'analysis',
                    'configuration': {
                        'schedule': 'daily',
                        'steps': ['data_collection', 'analysis', 'reporting']
                    },
                    'version': '1.0.0'
                },
                {
                    'name': 'Risk Alert Workflow',
                    'description': 'Monitors and alerts on risk thresholds',
                    'workflow_type': 'monitoring',
                    'configuration': {
                        'schedule': 'continuous',
                        'steps': ['monitoring', 'alerting', 'notification']
                    },
                    'version': '1.0.0'
                }
            ]
            
            for workflow_def in workflow_definitions:
                insert_stmt = Base.metadata.tables['workflow_definitions'].insert().values(workflow_def)
                db.execute(insert_stmt)
            
            db.commit()
            logger.info("Default data seeded successfully")
            
    except Exception as e:
        logger.error(f"Failed to seed default data: {e}")
        # Don't raise - seed failure shouldn't prevent API startup

# Export database utilities
__all__ = [
    "engine",
    "SessionLocal", 
    "init_database",
    "close_database",
    "get_db_session",
    "get_database",
    "check_database_health",
    "backup_database",
    "restore_database",
    "get_table_info",
    "vacuum_database",
    "analyze_database",
    "seed_default_data"
]