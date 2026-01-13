"""
JWT-based Authentication System
Handles token generation, validation, and refresh mechanisms
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import secrets
import hashlib
import base64


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class JWTConfig:
    """JWT Configuration settings"""
    ACCESS_TOKEN_EXPIRY = timedelta(minutes=15)
    REFRESH_TOKEN_EXPIRY = timedelta(days=7)
    ALGORITHM = "HS256"
    ISSUER = "security_auth_system"
    AUDIENCE = "api_users"
    SECRET_KEY_MIN_LENGTH = 32
    
    # Key rotation settings
    ENABLE_KEY_ROTATION = True
    KEY_ROTATION_DAYS = 90
    ACTIVE_KEY_ID = None  # Set dynamically
    
    @classmethod
    def get_secret_key(cls, key_id: str = None) -> str:
        """Get secret key for signing tokens"""
        # In production, retrieve from secure key management system
        base_key = "your-super-secret-key-change-in-production"
        if key_id:
            return hashlib.sha256(f"{base_key}:{key_id}".encode()).hexdigest()
        return base_key


class TokenPayload:
    """Token payload structure"""
    def __init__(self, user_id: str, role: str, permissions: list = None):
        self.sub = user_id
        self.role = role
        self.permissions = permissions or []
        self.iat = datetime.utcnow()
        self.exp = None
        self.aud = JWTConfig.AUDIENCE
        self.iss = JWTConfig.ISSUER
        self.jti = secrets.token_hex(16)  # Unique token ID
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sub': self.sub,
            'role': self.role,
            'permissions': self.permissions,
            'iat': self.iat,
            'exp': self.exp,
            'aud': self.aud,
            'iss': self.iss,
            'jti': self.jti
        }


class JWTManager:
    """JWT Token Manager"""
    
    def __init__(self):
        self.active_keys = self._initialize_keys()
    
    def _initialize_keys(self) -> Dict[str, str]:
        """Initialize signing keys for key rotation"""
        keys = {}
        if JWTConfig.ENABLE_KEY_ROTATION:
            # Generate multiple keys for rotation
            for i in range(3):
                key_id = f"key_{i}"
                keys[key_id] = JWTConfig.get_secret_key(key_id)
            JWTConfig.ACTIVE_KEY_ID = "key_0"
        else:
            keys["default"] = JWTConfig.get_secret_key()
            JWTConfig.ACTIVE_KEY_ID = "default"
        return keys
    
    def generate_token(self, user_id: str, role: str, 
                      token_type: TokenType, 
                      permissions: list = None,
                      additional_claims: Dict[str, Any] = None) -> str:
        """Generate JWT token"""
        payload = TokenPayload(user_id, role, permissions)
        
        # Set expiry based on token type
        if token_type == TokenType.ACCESS:
            payload.exp = datetime.utcnow() + JWTConfig.ACCESS_TOKEN_EXPIRY
        elif token_type == TokenType.REFRESH:
            payload.exp = datetime.utcnow() + JWTConfig.REFRESH_TOKEN_EXPIRY
        
        # Add additional claims
        if additional_claims:
            payload.to_dict().update(additional_claims)
        
        # Create token with current key
        token_data = payload.to_dict()
        token_data['key_id'] = JWTConfig.ACTIVE_KEY_ID
        
        secret_key = self.active_keys[JWTConfig.ACTIVE_KEY_ID]
        token = jwt.encode(token_data, secret_key, algorithm=JWTConfig.ALGORITHM)
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token"""
        try:
            # Try each active key
            for key_id, secret_key in self.active_keys.items():
                try:
                    payload = jwt.decode(
                        token, 
                        secret_key, 
                        algorithms=[JWTConfig.ALGORITHM],
                        audience=JWTConfig.AUDIENCE,
                        issuer=JWTConfig.ISSUER
                    )
                    return payload
                except jwt.InvalidTokenError:
                    continue
            
            return None
        except Exception as e:
            print(f"Token validation error: {e}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        payload = self.validate_token(refresh_token)
        
        if not payload or payload.get('token_type') != TokenType.REFRESH.value:
            return None
        
        # Generate new access token
        new_token = self.generate_token(
            user_id=payload['sub'],
            role=payload['role'],
            token_type=TokenType.ACCESS,
            permissions=payload.get('permissions', [])
        )
        
        return new_token
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token (add to blacklist)"""
        # In production, store in Redis or database
        # For now, just return True
        return True
    
    def blacklist_token(self, jti: str, expiry: datetime) -> None:
        """Add token to blacklist"""
        # In production, store in Redis with expiry
        pass


class PasswordManager:
    """Secure password management"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        errors = []
        
        if len(password) < 12:
            errors.append("Password must be at least 12 characters long")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }


class UserSession:
    """User session management"""
    
    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role
        self.session_id = secrets.token_urlsafe(32)
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.ip_address = None
        self.user_agent = None
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session is expired"""
        delta = datetime.utcnow() - self.last_activity
        return delta.total_seconds() > (timeout_minutes * 60)


# Example usage and testing
if __name__ == "__main__":
    # Initialize JWT manager
    jwt_manager = JWTManager()
    
    # Test password hashing
    password_manager = PasswordManager()
    
    # Generate tokens
    access_token = jwt_manager.generate_token(
        user_id="user123",
        role="admin",
        token_type=TokenType.ACCESS,
        permissions=["read", "write", "delete"]
    )
    
    refresh_token = jwt_manager.generate_token(
        user_id="user123",
        role="admin", 
        token_type=TokenType.REFRESH
    )
    
    print(f"Access Token: {access_token[:50]}...")
    print(f"Refresh Token: {refresh_token[:50]}...")
    
    # Validate token
    payload = jwt_manager.validate_token(access_token)
    print(f"Token payload: {payload}")
    
    # Test password
    password = "SecurePass123!"
    hashed = password_manager.hash_password(password)
    print(f"Password valid: {password_manager.verify_password(password, hashed)}")
    
    # Password strength validation
    strength = password_manager.validate_password_strength("weak")
    print(f"Password strength: {strength}")
