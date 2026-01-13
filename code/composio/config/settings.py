"""
Configuration management for Composio MCP Server.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseSettings, Field
from pydantic_settings import SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    
    url: str = Field(default="sqlite:///./composio.db", description="Database connection URL")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")


class RedisConfig(BaseSettings):
    """Redis configuration."""
    
    url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    max_connections: int = Field(default=50, description="Max Redis connections")


class AuthConfig(BaseSettings):
    """Authentication configuration."""
    
    secret_key: str = Field(default="change-me-in-production", description="JWT secret key")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Token expiration time")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration")
    password_salt: str = Field(default="change-salt-in-production", description="Password hashing salt")
    encryption_key: str = Field(default="change-encryption-key-in-production", description="Encryption key")


class MetricsConfig(BaseSettings):
    """Metrics and monitoring configuration."""
    
    enabled: bool = Field(default=True, description="Enable metrics collection")
    port: int = Field(default=8000, description="Metrics server port")
    endpoint: str = Field(default="/metrics", description="Metrics endpoint")
    collection_interval: int = Field(default=60, description="Collection interval in seconds")


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    
    enabled: bool = Field(default=True, description="Enable rate limiting")
    redis_url: str = Field(default="redis://localhost:6379/1", description="Redis URL for rate limiting")
    default_limits: Dict[str, int] = Field(
        default={
            "requests_per_minute": 100,
            "requests_per_hour": 1000,
            "requests_per_day": 10000
        },
        description="Default rate limits"
    )
    tool_specific_limits: Dict[str, Dict[str, int]] = Field(
        default={
            "github": {"requests_per_hour": 5000},
            "slack": {"requests_per_hour": 100},
            "telegram": {"requests_per_hour": 30},
            "notion": {"requests_per_hour": 100},
            "quantconnect": {"requests_per_minute": 10},
            "abacus_ai": {"requests_per_minute": 5}
        },
        description="Tool-specific rate limits"
    )


class ToolConfig(BaseSettings):
    """Individual tool configuration."""
    
    # GitHub Configuration
    github: Dict[str, Any] = Field(
        default={
            "enabled": True,
            "api_url": "https://api.github.com",
            "rate_limit": 5000,
            "timeout": 30,
            "user_agent": "Composio-MCP-Server/1.0"
        },
        description="GitHub tool configuration"
    )
    
    # Slack Configuration
    slack: Dict[str, Any] = Field(
        default={
            "enabled": True,
            "api_url": "https://slack.com/api",
            "rate_limit": 100,
            "timeout": 30
        },
        description="Slack tool configuration"
    )
    
    # Telegram Configuration
    telegram: Dict[str, Any] = Field(
        default={
            "enabled": True,
            "api_url": "https://api.telegram.org",
            "rate_limit": 30,
            "timeout": 30
        },
        description="Telegram tool configuration"
    )
    
    # Notion Configuration
    notion: Dict[str, Any] = Field(
        default={
            "enabled": True,
            "api_url": "https://api.notion.com",
            "rate_limit": 100,
            "timeout": 30,
            "version": "2022-06-28"
        },
        description="Notion tool configuration"
    )
    
    # QuantConnect Configuration
    quantconnect: Dict[str, Any] = Field(
        default={
            "enabled": True,
            "api_url": "https://www.quantconnect.com/api",
            "rate_limit": 10,
            "timeout": 60
        },
        description="QuantConnect tool configuration"
    )
    
    # Abacus.AI Configuration
    abacus_ai: Dict[str, Any] = Field(
        default={
            "enabled": True,
            "api_url": "https://api.abacus.ai",
            "rate_limit": 5,
            "timeout": 60
        },
        description="Abacus.AI tool configuration"
    )


class HealthConfig(BaseSettings):
    """Health monitoring configuration."""
    
    enabled: bool = Field(default=True, description="Enable health monitoring")
    check_interval: int = Field(default=30, description="Health check interval in seconds")
    timeout: int = Field(default=10, description="Health check timeout")
    alert_thresholds: Dict[str, Any] = Field(
        default={
            "cpu_usage": 80,
            "memory_usage": 85,
            "disk_usage": 90,
            "response_time": 5000
        },
        description="Alert thresholds"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="json",
        description="Log format (json, text)"
    )
    output: str = Field(default="stdout", description="Log output (stdout, file)")
    file_path: str = Field(default="logs/composio.log", description="Log file path")
    max_size: int = Field(default=100, description="Max log file size in MB")
    backup_count: int = Field(default=5, description="Number of backup log files")
    structured: bool = Field(default=True, description="Use structured logging")


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Core settings
    environment: str = Field(default="development", description="Environment")
    debug: bool = Field(default=False, description="Debug mode")
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8000, description="Server port")
    
    # Component configurations
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    auth: AuthConfig = AuthConfig()
    metrics: MetricsConfig = MetricsConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    tools: ToolConfig = ToolConfig()
    health: HealthConfig = HealthConfig()
    logging: LoggingConfig = LoggingConfig()
    
    # Feature flags
    features: Dict[str, bool] = Field(
        default={
            "authentication": True,
            "rate_limiting": True,
            "monitoring": True,
            "metrics": True,
            "trading_tools": True,
            "external_integrations": True
        },
        description="Feature flags"
    )
    
    # Security settings
    cors_origins: list[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    allowed_hosts: list[str] = Field(
        default=["*"],
        description="Allowed hosts"
    )
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """Load settings from file or environment."""
        if config_path and Path(config_path).exists():
            return cls._load_from_file(config_path)
        return cls()
    
    @classmethod
    def _load_from_file(cls, config_path: str) -> "Settings":
        """Load settings from configuration file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load based on file extension
        with open(config_file, 'r') as f:
            if config_file.suffix.lower() in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            elif config_file.suffix.lower() == '.json':
                config_data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
        
        return cls(**config_data)
    
    def save(self, config_path: str):
        """Save current settings to file."""
        config_file = Path(config_path)
        
        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = self.model_dump()
        
        # Save based on file extension
        with open(config_file, 'w') as f:
            if config_file.suffix.lower() in ['.yaml', '.yml']:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            elif config_file.suffix.lower() == '.json':
                json.dump(config_data, f, indent=2)
            else:
                raise ValueError(f"Unsupported configuration file format: {config_file.suffix}")
    
    def validate(self) -> list[str]:
        """Validate configuration and return any issues."""
        issues = []
        
        # Check critical settings
        if self.environment == "production":
            if self.auth.secret_key == "change-me-in-production":
                issues.append("Production environment requires secure secret key")
            
            if self.auth.encryption_key == "change-encryption-key-in-production":
                issues.append("Production environment requires secure encryption key")
            
            if self.auth.password_salt == "change-salt-in-production":
                issues.append("Production environment requires secure password salt")
            
            if self.debug:
                issues.append("Debug mode should be disabled in production")
        
        # Check tool configurations
        for tool_name in ["github", "slack", "telegram", "notion"]:
            tool_config = getattr(self.tools, tool_name)
            if tool_config.get("enabled", False):
                # Add tool-specific validation
                pass
        
        return issues


# Global settings instance
settings = Settings()