"""
Application configuration settings
"""

from functools import lru_cache
from pydantic import BaseSettings, Field
from typing import List, Dict, Any
import os

class Settings(BaseSettings):
    """Application settings"""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment")
    
    # Security
    secret_key: str = Field(default="your-secret-key-here", description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiration time")
    
    # Database
    database_url: str = Field(default="sqlite:///./langgraph.db", description="Database URL")
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    
    # Allowed hosts for security
    allowed_hosts: List[str] = Field(
        default=["*"],
        description="Allowed hosts"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_config: Dict[str, Any] = Field(
        default={
            "admin": 1000,
            "premium": 500,
            "standard": 200,
            "basic": 100
        },
        description="Rate limits by user role"
    )
    
    # Workflow Configuration
    max_concurrent_workflows: int = Field(default=10, description="Max concurrent workflows")
    workflow_timeout_minutes: int = Field(default=60, description="Workflow timeout")
    checkpoint_retention_days: int = Field(default=30, description="Checkpoint retention")
    
    # Monitoring
    monitoring_enabled: bool = Field(default=True, description="Enable monitoring")
    metrics_retention_hours: int = Field(default=168, description="Metrics retention")
    alert_thresholds: Dict[str, float] = Field(
        default={
            "failure_rate": 0.10,
            "avg_execution_time": 300,
            "memory_usage": 0.80,
            "active_workflow_limit": 50
        },
        description="Alert thresholds"
    )
    
    # External Services
    sentry_dsn: str = Field(default="", description="Sentry DSN")
    prometheus_port: int = Field(default=9090, description="Prometheus metrics port")
    
    # Authentication
    password_min_length: int = Field(default=8, description="Minimum password length")
    max_login_attempts: int = Field(default=5, description="Max login attempts")
    lockout_duration_minutes: int = Field(default=15, description="Lockout duration")
    
    # Workflow Limits
    max_workflows_per_user: int = Field(default=100, description="Max workflows per user")
    max_batch_size: int = Field(default=50, description="Max batch size")
    max_state_size_mb: int = Field(default=10, description="Max state size in MB")
    
    # WebSocket
    websocket_ping_interval: int = Field(default=30, description="WebSocket ping interval")
    websocket_ping_timeout: int = Field(default=10, description="WebSocket ping timeout")
    max_websocket_connections: int = Field(default=1000, description="Max WebSocket connections")
    
    # Background Tasks
    celery_broker_url: str = Field(default="redis://localhost:6379", description="Celery broker URL")
    celery_result_backend: str = Field(default="redis://localhost:6379", description="Celery result backend")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Global settings instance
settings = get_settings()

# Override environment-specific settings
if settings.environment == "production":
    settings.debug = False
    settings.cors_origins = ["https://yourdomain.com"]
    settings.allowed_hosts = ["yourdomain.com", "api.yourdomain.com"]
elif settings.environment == "staging":
    settings.cors_origins = ["https://staging.yourdomain.com"]
    settings.allowed_hosts = ["staging.yourdomain.com"]