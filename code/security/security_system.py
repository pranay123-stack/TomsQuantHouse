"""
Security System Integration
Main integration module that brings together all security components
"""

import redis
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import json
import logging

from .auth.jwt_auth import JWTManager, TokenType, PasswordManager, UserSession
from .rbac.rbac_manager import RBACManager, Role, Permission
from .api_keys.api_key_manager import APIKeyManager, APIKeyMiddleware, KeyType
from .rate_limiting.rate_limiter import RateLimitManager, RateLimitMiddleware
from .audit.audit_logger import AuditLogger, AuditEvent, AuditEventType, AuditSeverity, log_login_success, log_login_failure
from .encryption.encryption_utils import KeyManager, DataProtector, SecureStorage
from .middleware.security_middleware import SecurityMiddleware
from .testing.security_scanner import SecurityScanner
from .config.security_config import SecurityConfig


class SecuritySystem:
    """Integrated Security System"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize core components
        self.jwt_manager = JWTManager()
        self.password_manager = PasswordManager()
        self.rbac_manager = RBACManager()
        
        # Initialize Redis connection
        self.redis_client = self._initialize_redis()
        
        # Initialize API key management
        self.api_key_manager = APIKeyManager()
        self.api_key_middleware = APIKeyMiddleware(self.api_key_manager)
        
        # Initialize rate limiting
        if self.redis_client:
            self.rate_limiter = RateLimitManager(
                redis_host=self.config.REDIS_HOST,
                redis_port=self.config.REDIS_PORT,
                redis_db=self.config.REDIS_DB,
                redis_password=self.config.REDIS_PASSWORD
            )
        else:
            self.rate_limiter = None
        
        self.rate_limit_middleware = RateLimitMiddleware(self.rate_limiter) if self.rate_limiter else None
        
        # Initialize audit logging
        self.audit_logger = AuditLogger(
            db_path=self.config.AUDIT_LOG_DB_PATH,
            retention_days=self.config.AUDIT_LOG_RETENTION_DAYS,
            enable_compression=self.config.AUDIT_LOG_COMPRESSION
        )
        
        # Initialize encryption
        self.key_manager = KeyManager(self.config.ENCRYPTION_KEY_PATH)
        self.data_protector = DataProtector(self.key_manager)
        self.secure_storage = SecureStorage(data_protector=self.data_protector)
        
        # Initialize security middleware
        self.security_middleware = SecurityMiddleware()
        
        # Initialize vulnerability scanner
        self.security_scanner = SecurityScanner()
        
        # Active sessions
        self.active_sessions = {}
        
        self.logger.info("Security system initialized successfully")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        self.logger = logging.getLogger('security_system')
        self.logger.setLevel(getattr(logging, self.config.LOGGING['level']))
        
        # File handler
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            self.config.LOGGING['file'],
            maxBytes=self.config.LOGGING['max_file_size'],
            backupCount=self.config.LOGGING['backup_count']
        )
        file_handler.setLevel(getattr(logging, self.config.LOGGING['level']))
        
        formatter = logging.Formatter(self.config.LOGGING['format'])
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _initialize_redis(self) -> Optional[redis.Redis]:
        """Initialize Redis connection"""
        try:
            redis_client = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                password=self.config.REDIS_PASSWORD,
                decode_responses=True
            )
            
            # Test connection
            redis_client.ping()
            self.logger.info("Redis connection established")
            return redis_client
            
        except Exception as e:
            self.logger.warning(f"Redis connection failed: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Dict[str, Any]:
        """Authenticate user and return tokens"""
        try:
            # Validate credentials (in production, this would check against a database)
            if not self._validate_credentials(username, password):
                # Log failed login
                log_login_failure(username, ip_address, "Invalid credentials")
                return {
                    'success': False,
                    'error': 'Invalid credentials',
                    'status': 401
                }
            
            # Get user role and permissions
            role = self.rbac_manager.get_user_role(username)
            if not role:
                role = Role.USER  # Default role
                self.rbac_manager.assign_role(username, role)
            
            permissions = self.rbac_manager.get_user_permissions(username)
            
            # Generate tokens
            access_token = self.jwt_manager.generate_token(
                user_id=username,
                role=role.value,
                token_type=TokenType.ACCESS,
                permissions=[p.value for p in permissions]
            )
            
            refresh_token = self.jwt_manager.generate_token(
                user_id=username,
                role=role.value,
                token_type=TokenType.REFRESH
            )
            
            # Create session
            session = UserSession(username, role.value)
            session.ip_address = ip_address
            session.user_agent = user_agent
            self.active_sessions[session.session_id] = session
            
            # Log successful login
            log_login_success(username, ip_address, user_agent)
            
            return {
                'success': True,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'session_id': session.session_id,
                'user_id': username,
                'role': role.value,
                'permissions': [p.value for p in permissions],
                'expires_in': self.config.JWT_ACCESS_TOKEN_EXPIRY
            }
            
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return {
                'success': False,
                'error': 'Authentication failed',
                'status': 500
            }
    
    def validate_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Validate JWT token"""
        try:
            payload = self.jwt_manager.validate_token(token)
            
            if not payload:
                return {
                    'valid': False,
                    'error': 'Invalid token'
                }
            
            return {
                'valid': True,
                'payload': payload,
                'user_id': payload.get('sub'),
                'role': payload.get('role'),
                'permissions': payload.get('permissions', [])
            }
            
        except Exception as e:
            self.logger.error(f"Token validation error: {e}")
            return {
                'valid': False,
                'error': 'Token validation failed'
            }
    
    def authorize_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Authorize incoming request"""
        try:
            # Check if it's an API key request
            if 'api_key' in request_data:
                return self._authorize_api_key_request(request_data)
            
            # Check if it's a JWT token request
            elif 'authorization' in request_data.get('headers', {}):
                return self._authorize_jwt_request(request_data)
            
            else:
                return {
                    'authorized': False,
                    'error': 'No authentication provided',
                    'status': 401
                }
                
        except Exception as e:
            self.logger.error(f"Authorization error: {e}")
            return {
                'authorized': False,
                'error': 'Authorization failed',
                'status': 500
            }
    
    def _authorize_api_key_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Authorize API key request"""
        api_key = request_data['api_key']
        method = request_data.get('method', 'GET')
        endpoint = request_data.get('path', '/')
        
        # Validate API key
        validation_result = self.api_key_middleware.validate_request(
            api_key, method, endpoint
        )
        
        if not validation_result['valid']:
            # Log API key usage failure
            self.audit_logger.log_event(AuditEvent(
                AuditEventType.API_KEY_USED,
                validation_result.get('key_id'),
                AuditSeverity.HIGH
            ))
            
            return {
                'authorized': False,
                'error': validation_result['error'],
                'status': validation_result['status']
            }
        
        return {
            'authorized': True,
            'key_id': validation_result['key_id'],
            'key_type': validation_result['key_type'],
            'scopes': validation_result['scopes']
        }
    
    def _authorize_jwt_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Authorize JWT token request"""
        auth_header = request_data['headers']['authorization']
        
        # Extract token from "Bearer <token>" format
        if not auth_header.startswith('Bearer '):
            return {
                'authorized': False,
                'error': 'Invalid authorization header format',
                'status': 401
            }
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Validate token
        validation_result = self.validate_token(token)
        
        if not validation_result['valid']:
            return {
                'authorized': False,
                'error': validation_result['error'],
                'status': 401
            }
        
        # Check permissions for specific resource
        endpoint = request_data.get('path', '/')
        method = request_data.get('method', 'GET')
        
        required_permission = self._get_required_permission(method, endpoint)
        if required_permission:
            user_permissions = validation_result['permissions']
            if required_permission not in user_permissions:
                return {
                    'authorized': False,
                    'error': 'Insufficient permissions',
                    'status': 403
                }
        
        return {
            'authorized': True,
            'user_id': validation_result['user_id'],
            'role': validation_result['role'],
            'permissions': validation_result['permissions']
        }
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request with all security checks"""
        # Step 1: Security middleware validation
        security_result = self.security_middleware.process_request(request_data)
        
        if not security_result['allowed']:
            return {
                'allowed': False,
                'status': 403,
                'errors': security_result['errors'],
                'risk_score': security_result['risk_score']
            }
        
        # Step 2: Rate limiting
        if self.rate_limit_middleware:
            rate_limit_result = self.rate_limit_middleware.check_request_limit(request_data)
            
            if not rate_limit_result['allowed']:
                return {
                    'allowed': False,
                    'status': 429,
                    'error': rate_limit_result['error'],
                    'retry_after': rate_limit_result.get('retry_after', 60)
                }
        
        # Step 3: Authorization
        auth_result = self.authorize_request(request_data)
        
        if not auth_result.get('authorized', False):
            return {
                'allowed': False,
                'status': auth_result.get('status', 401),
                'error': auth_result.get('error', 'Unauthorized')
            }
        
        # Step 4: Final security headers
        security_headers = self.security_middleware.process_response(
            {'headers': {}}, request_data
        )['headers']
        
        return {
            'allowed': True,
            'user_id': auth_result.get('user_id'),
            'auth_info': auth_result,
            'security_headers': security_headers,
            'sanitized_data': security_result.get('sanitized_data', {}),
            'risk_score': security_result.get('risk_score', 0)
        }
    
    def create_api_key(self, name: str, key_type: KeyType, scopes: List[str],
                      created_by: str, expiry_days: int = None) -> Dict[str, Any]:
        """Create new API key"""
        try:
            api_key = self.api_key_manager.create_api_key(
                name=name,
                key_type=key_type,
                scopes=scopes,
                created_by=created_by,
                expiry_days=expiry_days
            )
            
            # Log API key creation
            self.audit_logger.log_event(AuditEvent(
                AuditEventType.API_KEY_CREATED,
                created_by,
                AuditSeverity.MEDIUM
            ))
            
            return {
                'success': True,
                'api_key': api_key,
                'key_id': list(self.api_key_manager.api_keys.keys())[-1] if self.api_key_manager.api_keys else None
            }
            
        except Exception as e:
            self.logger.error(f"API key creation error: {e}")
            return {
                'success': False,
                'error': 'Failed to create API key'
            }
    
    def get_security_analytics(self) -> Dict[str, Any]:
        """Get comprehensive security analytics"""
        try:
            # API key analytics
            api_key_analytics = self.api_key_manager.get_key_analytics()
            
            # Rate limiting statistics
            rate_limit_stats = self.rate_limiter.get_rate_limit_stats() if self.rate_limiter else {}
            
            # Audit statistics
            audit_stats = self.audit_logger.get_statistics()
            
            # Active sessions
            active_sessions_count = len(self.active_sessions)
            
            # Redis info
            redis_info = self.rate_limiter.get_redis_info() if self.rate_limiter else {}
            
            return {
                'api_keys': api_key_analytics,
                'rate_limiting': rate_limit_stats,
                'audit_logs': audit_stats,
                'active_sessions': active_sessions_count,
                'redis_connection': redis_info,
                'system_health': {
                    'timestamp': datetime.utcnow().isoformat(),
                    'components': {
                        'jwt_manager': True,
                        'rbac_manager': True,
                        'api_key_manager': True,
                        'rate_limiter': self.rate_limiter is not None,
                        'audit_logger': True,
                        'encryption': True,
                        'security_middleware': True
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Analytics error: {e}")
            return {
                'error': 'Failed to get analytics',
                'details': str(e)
            }
    
    def run_security_scan(self, target_url: str, scan_types: List[str] = None) -> Dict[str, Any]:
        """Run security vulnerability scan"""
        try:
            scan_results = self.security_scanner.scan_target(target_url, scan_types)
            
            # Log scan initiation
            self.audit_logger.log_event(AuditEvent(
                AuditEventType.ADMIN_ACTION,
                "system",
                AuditSeverity.LOW
            ))
            
            return scan_results
            
        except Exception as e:
            self.logger.error(f"Security scan error: {e}")
            return {
                'error': 'Security scan failed',
                'details': str(e)
            }
    
    def rotate_encryption_keys(self) -> Dict[str, Any]:
        """Rotate encryption keys"""
        try:
            result = self.key_manager.rotate_keys()
            
            # Log key rotation
            self.audit_logger.log_event(AuditEvent(
                AuditEventType.CONFIG_CHANGE,
                "system",
                AuditSeverity.HIGH
            ))
            
            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            self.logger.error(f"Key rotation error: {e}")
            return {
                'success': False,
                'error': 'Key rotation failed'
            }
    
    def cleanup_expired_data(self) -> Dict[str, Any]:
        """Clean up expired data"""
        try:
            # Clean up expired API keys
            expired_api_keys = self.api_key_manager.cleanup_expired_keys()
            
            # Clean up expired audit logs
            cleaned_audit_logs = self.audit_logger.cleanup_old_logs()
            
            # Clean up rate limit keys
            cleaned_rate_limits = self.rate_limiter.cleanup_expired_keys() if self.rate_limiter else 0
            
            return {
                'success': True,
                'expired_api_keys_removed': expired_api_keys,
                'audit_logs_cleaned': cleaned_audit_logs,
                'rate_limit_keys_cleaned': cleaned_rate_limits
            }
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
            return {
                'success': False,
                'error': 'Cleanup failed'
            }
    
    def _validate_credentials(self, username: str, password: str) -> bool:
        """Validate user credentials"""
        # This is a simplified example - in production, this would check against a database
        # For demo purposes, accept any username with password "password123"
        return password == "password123"
    
    def _get_required_permission(self, method: str, endpoint: str) -> Optional[str]:
        """Get required permission for endpoint"""
        # Simplified permission mapping
        endpoint_permissions = {
            '/admin': 'admin:access',
            '/api/users': 'user:read',
            '/api/users/create': 'user:create',
            '/api/users/update': 'user:update',
            '/api/users/delete': 'user:delete',
            '/api/export': 'data:export',
            '/api/import': 'data:import'
        }
        
        for path, permission in endpoint_permissions.items():
            if endpoint.startswith(path):
                return permission
        
        return None
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security system status"""
        return {
            'status': 'operational',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'components': {
                'authentication': {
                    'status': 'operational',
                    'jwt_manager': True,
                    'password_manager': True
                },
                'authorization': {
                    'status': 'operational',
                    'rbac_manager': True,
                    'roles_defined': len(Role),
                    'permissions_defined': len(Permission)
                },
                'api_keys': {
                    'status': 'operational',
                    'total_keys': len(self.api_key_manager.api_keys),
                    'active_keys': len([k for k in self.api_key_manager.api_keys.values() 
                                       if k.status.value == 'active'])
                },
                'rate_limiting': {
                    'status': 'operational' if self.rate_limiter else 'disabled',
                    'redis_connected': self.redis_client is not None
                },
                'audit_logging': {
                    'status': 'operational',
                    'database': self.config.AUDIT_LOG_DB_PATH,
                    'retention_days': self.config.AUDIT_LOG_RETENTION_DAYS
                },
                'encryption': {
                    'status': 'operational',
                    'key_rotation_enabled': self.config.ENABLE_KEY_ROTATION,
                    'key_path': self.config.ENCRYPTION_KEY_PATH
                },
                'security_middleware': {
                    'status': 'operational',
                    'input_validation': True,
                    'headers_management': True
                },
                'monitoring': {
                    'status': 'operational',
                    'vulnerability_scanning': True,
                    'penetration_testing': False  # Disabled by default
                }
            },
            'configuration': {
                'environment': self.config.ENVIRONMENT,
                'debug_mode': self.config.DEBUG,
                'session_timeout': self.config.SESSION_TIMEOUT_MINUTES,
                'max_file_size': self.config.MAX_FILE_SIZE
            }
        }


# Example usage
if __name__ == "__main__":
    # Initialize security system
    security_system = SecuritySystem()
    
    # Test authentication
    print("=== Authentication Test ===")
    auth_result = security_system.authenticate_user(
        username="admin",
        password="password123",
        ip_address="192.168.1.1",
        user_agent="TestClient/1.0"
    )
    print(f"Authentication result: {auth_result['success']}")
    
    if auth_result['success']:
        # Test token validation
        print("\n=== Token Validation Test ===")
        token_validation = security_system.validate_token(auth_result['access_token'])
        print(f"Token valid: {token_validation['valid']}")
        
        # Test request processing
        print("\n=== Request Processing Test ===")
        request_data = {
            'method': 'GET',
            'path': '/api/users',
            'headers': {
                'authorization': f"Bearer {auth_result['access_token']}"
            },
            'ip_address': '192.168.1.1'
        }
        
        processing_result = security_system.process_request(request_data)
        print(f"Request allowed: {processing_result['allowed']}")
        print(f"User ID: {processing_result.get('user_id')}")
    
    # Test API key creation
    print("\n=== API Key Creation Test ===")
    api_key_result = security_system.create_api_key(
        name="Test API Key",
        key_type=KeyType.STANDARD,
        scopes=["read", "write"],
        created_by="admin"
    )
    print(f"API key created: {api_key_result['success']}")
    
    if api_key_result['success']:
        print(f"API key: {api_key_result['api_key'][:50]}...")
    
    # Get security analytics
    print("\n=== Security Analytics ===")
    analytics = security_system.get_security_analytics()
    print(f"Total API keys: {analytics['api_keys']['total_keys']}")
    print(f"Active sessions: {analytics['active_sessions']}")
    
    # Get security status
    print("\n=== Security Status ===")
    status = security_system.get_security_status()
    print(f"System status: {status['status']}")
    print(f"Environment: {status['configuration']['environment']}")
    
    print("\nSecurity system test completed!")
