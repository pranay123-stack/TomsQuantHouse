"""
Security Configuration
Centralized configuration for all security components
"""

import os
from typing import Dict, Any, List
from datetime import timedelta
from enum import Enum


class SecurityConfig:
    """Main security configuration class"""
    
    # General settings
    DEBUG = os.getenv('SECURITY_DEBUG', 'False').lower() == 'true'
    ENVIRONMENT = os.getenv('SECURITY_ENVIRONMENT', 'development')
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRY = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRY', '900'))  # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRY = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRY', '604800'))  # 7 days
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_ISSUER = os.getenv('JWT_ISSUER', 'security_auth_system')
    JWT_AUDIENCE = os.getenv('JWT_AUDIENCE', 'api_users')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///security.db')
    
    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_URL = os.getenv('REDIS_URL', f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}')
    
    # API Key Configuration
    API_KEY_PREFIXES = {
        'standard': 'ak',
        'read_only': 'ak_ro',
        'admin': 'ak_admin',
        'batch': 'ak_batch',
        'webhook': 'ak_webhook'
    }
    
    # Rate Limiting Configuration
    RATE_LIMITS = {
        'api_requests': {
            'algorithm': 'sliding_window',
            'limit': int(os.getenv('API_RATE_LIMIT', '100')),
            'window': int(os.getenv('API_RATE_LIMIT_WINDOW', '60'))
        },
        'login_attempts': {
            'algorithm': 'sliding_window',
            'limit': int(os.getenv('LOGIN_RATE_LIMIT', '5')),
            'window': int(os.getenv('LOGIN_RATE_LIMIT_WINDOW', '300'))
        },
        'api_key_requests': {
            'algorithm': 'token_bucket',
            'capacity': int(os.getenv('API_KEY_CAPACITY', '50')),
            'refill_rate': float(os.getenv('API_KEY_REFILL_RATE', '0.8')),
            'window': int(os.getenv('API_KEY_WINDOW', '3600'))
        }
    }
    
    # Audit Configuration
    AUDIT_LOG_RETENTION_DAYS = int(os.getenv('AUDIT_LOG_RETENTION', '90'))
    AUDIT_LOG_DB_PATH = os.getenv('AUDIT_LOG_DB_PATH', 'audit_logs.db')
    AUDIT_LOG_ENABLED = os.getenv('AUDIT_LOG_ENABLED', 'True').lower() == 'true'
    AUDIT_LOG_COMPRESSION = os.getenv('AUDIT_LOG_COMPRESSION', 'True').lower() == 'true'
    
    # Encryption Configuration
    ENCRYPTION_KEY_PATH = os.getenv('ENCRYPTION_KEY_PATH', '.crypto_keys')
    ENCRYPTION_KEY_ROTATION_DAYS = int(os.getenv('ENCRYPTION_KEY_ROTATION', '90'))
    ENABLE_KEY_ROTATION = os.getenv('ENABLE_KEY_ROTATION', 'True').lower() == 'true'
    
    # Security Headers Configuration
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=()'
        ),
        'Cache-Control': 'no-store, no-cache, must-revalidate, private',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    # CORS Configuration
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '*').split(',')
    CORS_ALLOWED_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
    CORS_ALLOWED_HEADERS = ['Content-Type', 'Authorization', 'X-Requested-With']
    CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'True').lower() == 'true'
    CORS_MAX_AGE = 86400
    
    # Input Validation Configuration
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
    ALLOWED_EXTENSIONS = {
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'document': ['.pdf', '.doc', '.docx', '.txt'],
        'data': ['.json', '.csv', '.xml', '.yaml', '.yml']
    }
    ALLOWED_CONTENT_TYPES = {
        'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'document': ['application/pdf', 'application/msword', 'text/plain'],
        'data': ['application/json', 'text/csv', 'application/xml']
    }
    
    # RBAC Configuration
    ROLE_PERMISSIONS = {
        'super_admin': [
            'user:create', 'user:read', 'user:update', 'user:delete', 'user:list',
            'admin:access', 'admin:logs', 'admin:config',
            'api:create', 'api:read', 'api:update', 'api:delete',
            'data:export', 'data:import', 'data:backup',
            'system:status', 'system:metrics', 'system:maintenance'
        ],
        'admin': [
            'user:create', 'user:read', 'user:update', 'user:delete', 'user:list',
            'admin:access', 'api:create', 'api:read', 'api:update', 'api:delete',
            'data:export', 'data:import', 'data:backup',
            'system:status', 'system:metrics'
        ],
        'user': [
            'user:read', 'auth:login', 'auth:refresh', 'auth:logout', 'api:read'
        ],
        'guest': ['auth:login'],
        'api_client': ['api:read'],
        'auditor': ['admin:logs', 'admin:access', 'system:status']
    }
    
    # Session Configuration
    SESSION_TIMEOUT_MINUTES = int(os.getenv('SESSION_TIMEOUT', '30'))
    SESSION_CLEANUP_INTERVAL = int(os.getenv('SESSION_CLEANUP_INTERVAL', '300'))  # 5 minutes
    
    # Security Monitoring
    SECURITY_MONITORING = {
        'enable_vulnerability_scanning': os.getenv('ENABLE_VULN_SCANNING', 'True').lower() == 'true',
        'scan_interval_hours': int(os.getenv('SCAN_INTERVAL', '24')),
        'enable_penetration_testing': os.getenv('ENABLE_PENTEST', 'False').lower() == 'true',
        'alert_thresholds': {
            'failed_logins': int(os.getenv('ALERT_FAILED_LOGINS', '5')),
            'rate_limit_violations': int(os.getenv('ALERT_RATE_LIMITS', '10')),
            'suspicious_requests': int(os.getenv('ALERT_SUSPICIOUS', '3'))
        }
    }
    
    # Notification Configuration
    NOTIFICATIONS = {
        'email_enabled': os.getenv('EMAIL_NOTIFICATIONS', 'False').lower() == 'true',
        'smtp_host': os.getenv('SMTP_HOST'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'smtp_username': os.getenv('SMTP_USERNAME'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'alert_email': os.getenv('ALERT_EMAIL'),
        'slack_enabled': os.getenv('SLACK_NOTIFICATIONS', 'False').lower() == 'true',
        'slack_webhook': os.getenv('SLACK_WEBHOOK_URL')
    }
    
    # Logging Configuration
    LOGGING = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': os.getenv('LOG_FILE', 'security.log'),
        'max_file_size': int(os.getenv('LOG_MAX_SIZE', '10485760')),  # 10MB
        'backup_count': int(os.getenv('LOG_BACKUP_COUNT', '5')),
        'log_requests': os.getenv('LOG_REQUESTS', 'True').lower() == 'true',
        'log_responses': os.getenv('LOG_RESPONSES', 'False').lower() == 'true'
    }
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'url': cls.DATABASE_URL,
            'pool_size': int(os.getenv('DB_POOL_SIZE', '10')),
            'max_overflow': int(os.getenv('DB_MAX_OVERFLOW', '20')),
            'pool_timeout': int(os.getenv('DB_POOL_TIMEOUT', '30'))
        }
    
    @classmethod
    def get_redis_config(cls) -> Dict[str, Any]:
        """Get Redis configuration"""
        return {
            'host': cls.REDIS_HOST,
            'port': cls.REDIS_PORT,
            'db': cls.REDIS_DB,
            'password': cls.REDIS_PASSWORD,
            'decode_responses': True,
            'socket_connect_timeout': 10,
            'socket_timeout': 10,
            'socket_keepalive': True,
            'connection_pool_kwargs': {
                'max_connections': 50,
                'retry_on_timeout': True
            }
        }
    
    @classmethod
    def get_email_config(cls) -> Dict[str, Any]:
        """Get email configuration"""
        return {
            'host': cls.NOTIFICATIONS['smtp_host'],
            'port': cls.NOTIFICATIONS['smtp_port'],
            'username': cls.NOTIFICATIONS['smtp_username'],
            'password': cls.NOTIFICATIONS['smtp_password'],
            'use_tls': True,
            'timeout': 30
        }
    
    @classmethod
    def get_cors_config(cls) -> Dict[str, Any]:
        """Get CORS configuration"""
        return {
            'origins': cls.CORS_ALLOWED_ORIGINS,
            'methods': cls.CORS_ALLOWED_METHODS,
            'headers': cls.CORS_ALLOWED_HEADERS,
            'credentials': cls.CORS_ALLOW_CREDENTIALS,
            'max_age': cls.CORS_MAX_AGE
        }
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Check required environment variables
        required_vars = [
            ('JWT_SECRET_KEY', 'your-secret-key-change-in-production'),
            ('DATABASE_URL', 'sqlite:///security.db')
        ]
        
        for var, default in required_vars:
            if var not in os.environ and default == 'your-secret-key-change-in-production':
                issues.append(f"Environment variable {var} should be set for production")
        
        # Check development vs production settings
        if cls.ENVIRONMENT == 'production':
            production_issues = [
                (cls.DEBUG, False, "DEBUG should be False in production"),
                (cls.JWT_SECRET_KEY != 'your-secret-key-change-in-production', True, 
                 "JWT_SECRET_KEY should be changed in production"),
                (cls.ENABLE_KEY_ROTATION, True, "Key rotation should be enabled in production"),
                (cls.AUDIT_LOG_ENABLED, True, "Audit logging should be enabled in production")
            ]
            
            for condition, expected, message in production_issues:
                if condition != expected:
                    issues.append(message)
        
        # Check Redis connection in production
        if cls.ENVIRONMENT == 'production' and not cls.REDIS_PASSWORD:
            issues.append("Redis password should be set in production")
        
        return issues
    
    @classmethod
    def load_from_file(cls, config_file: str) -> None:
        """Load configuration from file"""
        import yaml
        
        if not os.path.exists(config_file):
            return
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Update class attributes from config file
        for key, value in config.items():
            if hasattr(cls, key.upper()):
                setattr(cls, key.upper(), value)
    
    @classmethod
    def save_to_file(cls, config_file: str) -> None:
        """Save current configuration to file"""
        import yaml
        
        config_dict = {
            'debug': cls.DEBUG,
            'environment': cls.ENVIRONMENT,
            'jwt': {
                'secret_key': cls.JWT_SECRET_KEY,
                'access_token_expiry': cls.JWT_ACCESS_TOKEN_EXPIRY,
                'refresh_token_expiry': cls.JWT_REFRESH_TOKEN_EXPIRY
            },
            'redis': {
                'host': cls.REDIS_HOST,
                'port': cls.REDIS_PORT,
                'db': cls.REDIS_DB
            },
            'rate_limits': cls.RATE_LIMITS,
            'security_headers': cls.SECURITY_HEADERS,
            'session_timeout': cls.SESSION_TIMEOUT_MINUTES
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)


class EnvironmentConfig:
    """Environment-specific configurations"""
    
    @staticmethod
    def development_config() -> Dict[str, Any]:
        """Development environment configuration"""
        return {
            'debug': True,
            'database_url': 'sqlite:///dev_security.db',
            'redis_host': 'localhost',
            'enable_vulnerability_scanning': False,
            'enable_penetration_testing': False,
            'log_level': 'DEBUG',
            'audit_log_retention_days': 7,
            'max_file_size': 50 * 1024 * 1024,  # 50MB
        }
    
    @staticmethod
    def staging_config() -> Dict[str, Any]:
        """Staging environment configuration"""
        return {
            'debug': False,
            'database_url': os.getenv('STAGING_DATABASE_URL', 'sqlite:///staging_security.db'),
            'redis_host': os.getenv('STAGING_REDIS_HOST', 'staging-redis'),
            'enable_vulnerability_scanning': True,
            'enable_penetration_testing': False,
            'log_level': 'INFO',
            'audit_log_retention_days': 30,
            'max_file_size': 20 * 1024 * 1024,  # 20MB
        }
    
    @staticmethod
    def production_config() -> Dict[str, Any]:
        """Production environment configuration"""
        return {
            'debug': False,
            'database_url': os.getenv('PRODUCTION_DATABASE_URL'),
            'redis_host': os.getenv('PRODUCTION_REDIS_HOST', 'prod-redis'),
            'redis_password': os.getenv('PRODUCTION_REDIS_PASSWORD'),
            'enable_vulnerability_scanning': True,
            'enable_penetration_testing': True,
            'log_level': 'WARNING',
            'audit_log_retention_days': 365,
            'max_file_size': 10 * 1024 * 1024,  # 10MB
            'enable_key_rotation': True,
            'enable_security_monitoring': True,
            'email_notifications': True,
            'slack_notifications': True
        }


# Example configuration files
DEVELOPMENT_CONFIG = """
# Development Security Configuration
DEBUG: True
ENVIRONMENT: development

JWT_SECRET_KEY: "dev-secret-key-change-me"
JWT_ACCESS_TOKEN_EXPIRY: 900
JWT_REFRESH_TOKEN_EXPIRY: 604800

DATABASE_URL: "sqlite:///dev_security.db"
REDIS_HOST: localhost
REDIS_PORT: 6379
REDIS_DB: 0

RATE_LIMITS:
  api_requests:
    limit: 1000
    window: 60
  login_attempts:
    limit: 10
    window: 300

SECURITY_HEADERS:
  X-Content-Type-Options: "nosniff"
  X-Frame-Options: "DENY"
  X-XSS-Protection: "1; mode=block"

SESSION_TIMEOUT: 60
MAX_FILE_SIZE: 52428800  # 50MB

LOG_LEVEL: DEBUG
ENABLE_VULN_SCANNING: false
ENABLE_PENTEST: false
"""

PRODUCTION_CONFIG = """
# Production Security Configuration
DEBUG: False
ENVIRONMENT: production

JWT_SECRET_KEY: "${JWT_SECRET_KEY}"
JWT_ACCESS_TOKEN_EXPIRY: 900
JWT_REFRESH_TOKEN_EXPIRY: 604800

DATABASE_URL: "${DATABASE_URL}"
REDIS_HOST: "${REDIS_HOST}"
REDIS_PORT: 6379
REDIS_DB: 0
REDIS_PASSWORD: "${REDIS_PASSWORD}"

RATE_LIMITS:
  api_requests:
    limit: 100
    window: 60
  login_attempts:
    limit: 5
    window: 300
  api_key_requests:
    capacity: 50
    refill_rate: 0.8
    window: 3600

SECURITY_HEADERS:
  X-Content-Type-Options: "nosniff"
  X-Frame-Options: "DENY"
  X-XSS-Protection: "1; mode=block"
  Strict-Transport-Security: "max-age=31536000; includeSubDomains"
  Content-Security-Policy: "default-src 'self'; script-src 'self'; style-src 'self'"
  Referrer-Policy: "strict-origin-when-cross-origin"

SESSION_TIMEOUT: 30
MAX_FILE_SIZE: 10485760  # 10MB

LOG_LEVEL: WARNING
ENABLE_VULN_SCANNING: true
ENABLE_PENTEST: true
ENABLE_KEY_ROTATION: true
ENABLE_SECURITY_MONITORING: true

EMAIL_NOTIFICATIONS: true
SMTP_HOST: "${SMTP_HOST}"
SMTP_USERNAME: "${SMTP_USERNAME}"
SMTP_PASSWORD: "${SMTP_PASSWORD}"
ALERT_EMAIL: "${ALERT_EMAIL}"

SLACK_NOTIFICATIONS: true
SLACK_WEBHOOK_URL: "${SLACK_WEBHOOK_URL}"
"""


if __name__ == "__main__":
    # Configuration validation example
    issues = SecurityConfig.validate_config()
    
    if issues:
        print("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Configuration is valid!")
    
    # Example: Get environment-specific configuration
    env_config = EnvironmentConfig.development_config()
    print(f"\nDevelopment config: {env_config}")
    
    # Example: Save configuration to file
    SecurityConfig.save_to_file('security_config.yaml')
    print("\nConfiguration saved to security_config.yaml")
