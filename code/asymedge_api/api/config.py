"""
ASYMEdge Dashboard API Configuration

Centralized configuration management for all API settings including:
- Database connections
- Authentication settings
- Rate limiting
- External service integrations
- Logging configuration
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseSettings, Field
import secrets

class Settings(BaseSettings):
    """Application settings configuration"""
    
    # Application
    APP_NAME: str = "ASYMEdge Dashboard API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Server
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # Security
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32), env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./asymedge_api.db",
        env="DATABASE_URL"
    )
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis (for caching and real-time features)
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        env="ALLOWED_ORIGINS"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )
    
    # Letta Integration
    LETTA_API_BASE_URL: str = Field(default="http://localhost:8283", env="LETTA_API_BASE_URL")
    LETTA_API_KEY: Optional[str] = Field(default=None, env="LETTA_API_KEY")
    LETTA_TIMEOUT: int = Field(default=30, env="LETTA_TIMEOUT")
    
    # Rate Limiting
    RATE_LIMIT_DEFAULT: int = Field(default=1000, env="RATE_LIMIT_DEFAULT")  # requests/hour
    RATE_LIMIT_PREMIUM: int = Field(default=5000, env="RATE_LIMIT_PREMIUM")
    RATE_LIMIT_ENTERPRISE: int = Field(default=-1, env="RATE_LIMIT_ENTERPRISE")  # unlimited
    RATE_LIMIT_WINDOW: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # seconds
    
    # WebSocket
    WEBSOCKET_HEARTBEAT_INTERVAL: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    WEBSOCKET_MAX_CONNECTIONS: int = Field(default=100, env="WEBSOCKET_MAX_CONNECTIONS")
    
    # Trading Data
    TRADING_DATA_PROVIDER: str = Field(default="mock", env="TRADING_DATA_PROVIDER")
    TRADING_API_KEYS: dict = Field(default_factory=dict, env="TRADING_API_KEYS")
    CACHE_TTL_SECONDS: int = Field(default=300, env="CACHE_TTL_SECONDS")
    
    # File Storage
    UPLOAD_DIR: Path = Field(default=Path("./uploads"), env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(default=10485760, env="MAX_FILE_SIZE")  # 10MB
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    LOG_FILE: Optional[str] = Field(default=None, env="LOG_FILE")
    
    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    
    # Background Tasks
    TASK_QUEUE_SIZE: int = Field(default=1000, env="TASK_QUEUE_SIZE")
    WORKER_PROCESSES: int = Field(default=4, env="WORKER_PROCESSES")
    
    # Agent Management
    MAX_AGENT_INSTANCES: int = Field(default=50, env="MAX_AGENT_INSTANCES")
    AGENT_TIMEOUT: int = Field(default=300, env="AGENT_TIMEOUT")
    AGENT_MEMORY_LIMIT: int = Field(default=512, env="AGENT_MEMORY_LIMIT")  # MB
    
    # Workflow Management
    MAX_WORKFLOW_INSTANCES: int = Field(default=100, env="MAX_WORKFLOW_INSTANCES")
    WORKFLOW_TIMEOUT: int = Field(default=3600, env="WORKFLOW_TIMEOUT")
    
    # Dashboard Configuration
    DEFAULT_WIDGET_CONFIG: dict = Field(default_factory=dict, env="DEFAULT_WIDGET_CONFIG")
    MAX_DASHBOARD_SAVES: int = Field(default=100, env="MAX_DASHBOARD_SAVES")
    
    # Email (for notifications)
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_USE_TLS: bool = Field(default=True, env="SMTP_USE_TLS")
    
    # External APIs
    EXTERNAL_API_TIMEOUT: int = Field(default=30, env="EXTERNAL_API_TIMEOUT")
    EXTERNAL_API_RETRIES: int = Field(default=3, env="EXTERNAL_API_RETRIES")
    
    # Feature Flags
    ENABLE_AGENT_QUERIES: bool = Field(default=True, env="ENABLE_AGENT_QUERIES")
    ENABLE_REAL_TIME_STREAMING: bool = Field(default=True, env="ENABLE_REAL_TIME_STREAMING")
    ENABLE_TRADING_METRICS: bool = Field(default=True, env="ENABLE_TRADING_METRICS")
    ENABLE_WORKFLOW_MONITORING: bool = Field(default=True, env="ENABLE_WORKFLOW_MONITORING")
    ENABLE_USER_MANAGEMENT: bool = Field(default=True, env="ENABLE_USER_MANAGEMENT")
    ENABLE_DASHBOARD_CONFIG: bool = Field(default=True, env="ENABLE_DASHBOARD_CONFIG")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_database_url(self) -> str:
        """Get database URL with proper formatting"""
        if self.DATABASE_URL.startswith("sqlite"):
            # Ensure sqlite database directory exists
            db_path = self.DATABASE_URL.replace("sqlite:///", "")
            if db_path != ":memory:":
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return self.DATABASE_URL
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.DEBUG
    
    def get_rate_limit(self, user_tier: str = "default") -> int:
        """Get rate limit for user tier"""
        tier_limits = {
            "default": self.RATE_LIMIT_DEFAULT,
            "premium": self.RATE_LIMIT_PREMIUM,
            "enterprise": self.RATE_LIMIT_ENTERPRISE
        }
        return tier_limits.get(user_tier, self.RATE_LIMIT_DEFAULT)

# Create global settings instance
settings = Settings()

# Derived configurations
settings_dict = {
    "app_name": settings.APP_NAME,
    "app_version": settings.APP_VERSION,
    "debug": settings.DEBUG,
    "host": settings.HOST,
    "port": settings.PORT,
    "database_url": settings.get_database_url(),
    "redis_url": settings.REDIS_URL,
    "letta_api_url": settings.LETTA_API_BASE_URL,
    "allowed_origins": settings.ALLOWED_ORIGINS,
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "rate_limits": {
        "default": settings.RATE_LIMIT_DEFAULT,
        "premium": settings.RATE_LIMIT_PREMIUM,
        "enterprise": settings.RATE_LIMIT_ENTERPRISE
    },
    "features": {
        "agent_queries": settings.ENABLE_AGENT_QUERIES,
        "real_time_streaming": settings.ENABLE_REAL_TIME_STREAMING,
        "trading_metrics": settings.ENABLE_TRADING_METRICS,
        "workflow_monitoring": settings.ENABLE_WORKFLOW_MONITORING,
        "user_management": settings.ENABLE_USER_MANAGEMENT,
        "dashboard_config": settings.ENABLE_DASHBOARD_CONFIG
    }
}