"""
Security Authentication System
Comprehensive security framework with JWT, RBAC, rate limiting, and more
"""

from .security_system import SecuritySystem
from .auth.jwt_auth import JWTManager, TokenType, PasswordManager, UserSession
from .rbac.rbac_manager import RBACManager, Role, Permission
from .api_keys.api_key_manager import APIKeyManager, APIKeyMiddleware, KeyType
from .rate_limiting.rate_limiter import RateLimitManager, RateLimitMiddleware
from .audit.audit_logger import AuditLogger, AuditEvent, AuditEventType, AuditSeverity
from .encryption.encryption_utils import KeyManager, DataProtector, SecureStorage
from .middleware.security_middleware import SecurityMiddleware
from .testing.security_scanner import SecurityScanner
from .config.security_config import SecurityConfig, EnvironmentConfig

__version__ = "1.0.0"
__author__ = "Security Team"
__email__ = "security@example.com"

__all__ = [
    # Main system
    "SecuritySystem",
    
    # Authentication
    "JWTManager",
    "TokenType", 
    "PasswordManager",
    "UserSession",
    
    # Authorization
    "RBACManager",
    "Role",
    "Permission",
    
    # API Key Management
    "APIKeyManager",
    "APIKeyMiddleware",
    "KeyType",
    
    # Rate Limiting
    "RateLimitManager",
    "RateLimitMiddleware",
    
    # Audit Logging
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    
    # Encryption
    "KeyManager",
    "DataProtector",
    "SecureStorage",
    
    # Security Middleware
    "SecurityMiddleware",
    
    # Security Testing
    "SecurityScanner",
    
    # Configuration
    "SecurityConfig",
    "EnvironmentConfig"
]
