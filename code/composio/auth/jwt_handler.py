"""
JWT token handling for Composio MCP Server.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import jwt
import structlog
from cryptography.fernet import Fernet
from passlib.context import CryptContext

logger = structlog.get_logger()


class JWTHandler:
    """JWT token handler with encryption support."""
    
    def __init__(self, settings):
        """Initialize JWT handler with settings."""
        self.settings = settings
        self.secret_key = settings.auth.secret_key
        self.algorithm = settings.auth.algorithm
        self.access_token_expire_minutes = settings.auth.access_token_expire_minutes
        self.refresh_token_expire_days = settings.auth.refresh_token_expire_days
        
        # Initialize password hasher
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Initialize encryption
        self.cipher_suite = Fernet(self._get_encryption_key())
    
    def _get_encryption_key(self) -> bytes:
        """Get encryption key for sensitive data."""
        # In production, this should be properly managed (e.g., HashiCorp Vault, AWS KMS)
        return self.settings.auth.encryption_key.encode('utf-8')
    
    def create_access_token(
        self, 
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get("type") != token_type:
                logger.warning("Invalid token type", expected=token_type, actual=payload.get("type"))
                return None
            
            # Check expiration
            if "exp" in payload:
                exp = datetime.fromtimestamp(payload["exp"])
                if exp < datetime.utcnow():
                    logger.warning("Token expired", user_id=payload.get("sub"))
                    return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired", exc_info=True)
            return None
        except jwt.JWTError as e:
            logger.warning("JWT error", error=str(e))
            return None
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def encrypt_sensitive_data(self, data: Union[str, Dict[str, Any]]) -> str:
        """Encrypt sensitive data."""
        if isinstance(data, dict):
            data = json.dumps(data)
        
        encrypted_data = self.cipher_suite.encrypt(data.encode('utf-8'))
        return encrypted_data.decode('utf-8')
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> Union[str, Dict[str, Any]]:
        """Decrypt sensitive data."""
        try:
            decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode('utf-8'))
            decrypted_str = decrypted_data.decode('utf-8')
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted_str)
            except json.JSONDecodeError:
                return decrypted_str
                
        except Exception as e:
            logger.error("Decryption failed", error=str(e))
            raise ValueError("Failed to decrypt data")
    
    def create_user_token(
        self, 
        user_id: str, 
        username: str, 
        roles: list[str] = None, 
        permissions: list[str] = None
    ) -> Dict[str, str]:
        """Create complete token pair for user."""
        if roles is None:
            roles = ["user"]
        
        if permissions is None:
            permissions = ["read", "write"]
        
        # Create token payload
        token_data = {
            "sub": user_id,
            "username": username,
            "roles": roles,
            "permissions": permissions,
            "issued_at": datetime.utcnow().isoformat()
        }
        
        # Create access and refresh tokens
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": self.access_token_expire_minutes * 60
        }
    
    def extract_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Extract user information from token."""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
            "issued_at": payload.get("issued_at")
        }
    
    def is_token_valid(self, token: str) -> bool:
        """Check if token is valid."""
        return self.verify_token(token) is not None
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get token expiry datetime."""
        payload = self.verify_token(token)
        if not payload or "exp" not in payload:
            return None
        
        return datetime.fromtimestamp(payload["exp"])
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token using refresh token."""
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return None
        
        user_id = payload.get("sub")
        username = payload.get("username", "unknown")
        
        # Create new token with current timestamp
        token_data = {
            "sub": user_id,
            "username": username,
            "roles": payload.get("roles", ["user"]),
            "permissions": payload.get("permissions", ["read", "write"]),
            "issued_at": datetime.utcnow().isoformat()
        }
        
        return self.create_access_token(token_data)


class TokenBlacklist:
    """Token blacklist for logout functionality."""
    
    def __init__(self, redis_client=None):
        """Initialize with optional Redis client."""
        self.redis_client = redis_client
        self.local_blacklist = set()  # Fallback if Redis not available
    
    async def add_to_blacklist(self, token: str, expiry: datetime):
        """Add token to blacklist."""
        jti = jwt.decode(token, options={"verify_signature": False}).get("jti", "")
        
        if self.redis_client:
            # Use Redis for distributed blacklist
            await self.redis_client.setex(
                f"blacklist:{jti}",
                int((expiry - datetime.utcnow()).total_seconds()),
                "1"
            )
        else:
            # Use local fallback
            self.local_blacklist.add(jti)
    
    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted."""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            jti = payload.get("jti", "")
        except jwt.JWTError:
            return True  # Invalid tokens are considered blacklisted
        
        if self.redis_client:
            # Check Redis blacklist
            exists = await self.redis_client.exists(f"blacklist:{jti}")
            return bool(exists)
        else:
            # Check local blacklist
            return jti in self.local_blacklist