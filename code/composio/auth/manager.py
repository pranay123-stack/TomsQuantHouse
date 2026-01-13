"""
Authentication and authorization manager for Composio MCP Server.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import aiosqlite
import redis.asyncio as redis
import structlog
from auth.jwt_handler import JWTHandler, TokenBlacklist
from pydantic import BaseModel

logger = structlog.get_logger()


class User(BaseModel):
    """User model."""
    id: str
    username: str
    email: Optional[str] = None
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    roles: List[str] = ["user"]
    permissions: List[str] = ["read", "write"]
    created_at: datetime
    last_login: Optional[datetime] = None
    profile: Optional[Dict[str, Any]] = None


class UserCredentials(BaseModel):
    """User credentials model."""
    username: str
    password: str
    tool_credentials: Optional[Dict[str, Any]] = {}


class AuthManager:
    """Authentication and authorization manager."""
    
    def __init__(self, settings):
        """Initialize authentication manager."""
        self.settings = settings
        self.jwt_handler = JWTHandler(settings)
        self.token_blacklist = None
        
        # Initialize Redis for user sessions and credentials
        self.redis_client = None
        self._setup_redis()
        
        # User permission cache
        self._permission_cache = {}
        self._cache_expiry = 300  # 5 minutes
        
        logger.info("Authentication manager initialized")
    
    def _setup_redis(self):
        """Setup Redis client for authentication data."""
        try:
            redis_url = self.settings.redis.url.replace("redis://", "redis://")
            self.redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.token_blacklist = TokenBlacklist(self.redis_client)
            logger.info("Redis authentication store initialized")
        except Exception as e:
            logger.warning("Failed to initialize Redis", error=str(e))
            self.redis_client = None
            self.token_blacklist = TokenBlacklist()
    
    async def create_database(self):
        """Create authentication database tables."""
        async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    hashed_password TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    roles TEXT DEFAULT '["user"]',
                    permissions TEXT DEFAULT '["read", "write"]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    profile TEXT
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_tool_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    encrypted_credentials TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, tool_name),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            await db.commit()
            logger.info("Authentication database initialized")
    
    async def register_user(self, credentials: UserCredentials) -> Dict[str, Any]:
        """Register new user."""
        try:
            # Check if user already exists
            if await self.get_user_by_username(credentials.username):
                return {
                    "success": False,
                    "error": "User already exists"
                }
            
            # Create user
            user_id = f"user_{int(time.time())}_{len(credentials.username)}"
            hashed_password = self.jwt_handler.hash_password(credentials.password)
            
            user = User(
                id=user_id,
                username=credentials.username,
                email=f"{credentials.username}@composio.local",  # Default email
                hashed_password=hashed_password,
                created_at=datetime.utcnow(),
                profile={}
            )
            
            # Store in database
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                await db.execute("""
                    INSERT INTO users (
                        id, username, email, hashed_password, is_active, is_admin,
                        roles, permissions, created_at, profile
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.id, user.username, user.email, user.hashed_password,
                    user.is_active, user.is_admin, json.dumps(user.roles),
                    json.dumps(user.permissions), user.created_at, json.dumps(user.profile)
                ))
                await db.commit()
            
            # Store tool credentials if provided
            if credentials.tool_credentials:
                await self.store_tool_credentials(user_id, credentials.tool_credentials)
            
            logger.info("User registered", username=credentials.username, user_id=user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "username": user.username
            }
            
        except Exception as e:
            logger.error("User registration failed", username=credentials.username, error=str(e))
            return {
                "success": False,
                "error": "Registration failed"
            }
    
    async def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password."""
        try:
            user = await self.get_user_by_username(username)
            if not user or not user.is_active:
                return None
            
            # Verify password
            if not self.jwt_handler.verify_password(password, user.hashed_password):
                return None
            
            # Update last login
            await self.update_user_last_login(user.id)
            
            # Create tokens
            tokens = self.jwt_handler.create_user_token(
                user_id=user.id,
                username=user.username,
                roles=user.roles,
                permissions=user.permissions
            )
            
            # Store session
            await self.create_user_session(user.id, tokens["access_token"])
            
            # Cache user info
            await self._cache_user_permissions(user.id, user.roles, user.permissions)
            
            logger.info("User authenticated", username=username, user_id=user.id)
            
            return {
                "success": True,
                "user": user.dict(),
                "tokens": tokens
            }
            
        except Exception as e:
            logger.error("Authentication failed", username=username, error=str(e))
            return None
    
    async def logout_user(self, access_token: str) -> bool:
        """Logout user and invalidate token."""
        try:
            # Add token to blacklist
            expiry = self.jwt_handler.get_token_expiry(access_token)
            if expiry:
                await self.token_blacklist.add_to_blacklist(access_token, expiry)
            
            # Invalidate session
            user_info = self.jwt_handler.extract_user_info(access_token)
            if user_info:
                await self.invalidate_user_session(access_token)
            
            logger.info("User logged out", user_id=user_info.get("user_id") if user_info else None)
            return True
            
        except Exception as e:
            logger.error("Logout failed", error=str(e))
            return False
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM users WHERE id = ?", (user_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return User(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    hashed_password=row["hashed_password"],
                    is_active=bool(row["is_active"]),
                    is_admin=bool(row["is_admin"]),
                    roles=json.loads(row["roles"]),
                    permissions=json.loads(row["permissions"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
                    profile=json.loads(row["profile"]) if row["profile"] else {}
                )
                
        except Exception as e:
            logger.error("Failed to get user by ID", user_id=user_id, error=str(e))
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return User(
                    id=row["id"],
                    username=row["username"],
                    email=row["email"],
                    hashed_password=row["hashed_password"],
                    is_active=bool(row["is_active"]),
                    is_admin=bool(row["is_admin"]),
                    roles=json.loads(row["roles"]),
                    permissions=json.loads(row["permissions"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_login=datetime.fromisoformat(row["last_login"]) if row["last_login"] else None,
                    profile=json.loads(row["profile"]) if row["profile"] else {}
                )
                
        except Exception as e:
            logger.error("Failed to get user by username", username=username, error=str(e))
            return None
    
    async def store_tool_credentials(self, user_id: str, credentials: Dict[str, Any]) -> bool:
        """Store encrypted tool credentials for user."""
        try:
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                for tool_name, tool_credentials in credentials.items():
                    encrypted_data = self.jwt_handler.encrypt_sensitive_data(tool_credentials)
                    
                    await db.execute("""
                        INSERT OR REPLACE INTO user_tool_credentials 
                        (user_id, tool_name, encrypted_credentials, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, tool_name, encrypted_data, datetime.utcnow()))
                
                await db.commit()
                logger.info("Tool credentials stored", user_id=user_id, tools=list(credentials.keys()))
                return True
                
        except Exception as e:
            logger.error("Failed to store tool credentials", user_id=user_id, error=str(e))
            return False
    
    async def get_tool_credentials(self, user_id: str, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get decrypted tool credentials for user."""
        try:
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT encrypted_credentials FROM user_tool_credentials WHERE user_id = ? AND tool_name = ?",
                    (user_id, tool_name)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return self.jwt_handler.decrypt_sensitive_data(row["encrypted_credentials"])
                
        except Exception as e:
            logger.error("Failed to get tool credentials", user_id=user_id, tool=tool_name, error=str(e))
            return None
    
    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get user permissions with caching."""
        # Check cache first
        cache_key = f"permissions:{user_id}"
        if cache_key in self._permission_cache:
            cache_time, permissions = self._permission_cache[cache_key]
            if time.time() - cache_time < self._cache_expiry:
                return set(permissions)
        
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return set()
            
            permissions = set(user.permissions)
            
            # Add role-based permissions
            role_permissions = {
                "admin": {"read", "write", "delete", "manage_users", "manage_tools"},
                "trader": {"read", "write", "execute_strategies", "view_portfolio"},
                "user": {"read", "write"}
            }
            
            for role in user.roles:
                if role in role_permissions:
                    permissions.update(role_permissions[role])
            
            # Cache permissions
            self._permission_cache[cache_key] = (time.time(), list(permissions))
            
            return permissions
            
        except Exception as e:
            logger.error("Failed to get user permissions", user_id=user_id, error=str(e))
            return set()
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return user info."""
        try:
            # Check blacklist
            if await self.token_blacklist.is_blacklisted(token):
                logger.warning("Token is blacklisted")
                return None
            
            # Verify and extract token data
            payload = self.jwt_handler.verify_token(token)
            if not payload:
                return None
            
            user_id = payload.get("sub")
            user = await self.get_user_by_id(user_id)
            
            if not user or not user.is_active:
                return None
            
            return {
                "user_id": user_id,
                "username": user.username,
                "roles": user.roles,
                "permissions": list(await self.get_user_permissions(user_id))
            }
            
        except Exception as e:
            logger.error("Token verification failed", error=str(e))
            return None
    
    async def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions
    
    async def update_user_last_login(self, user_id: str):
        """Update user's last login timestamp."""
        try:
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                await db.execute(
                    "UPDATE users SET last_login = ? WHERE id = ?",
                    (datetime.utcnow(), user_id)
                )
                await db.commit()
        except Exception as e:
            logger.error("Failed to update last login", user_id=user_id, error=str(e))
    
    async def create_user_session(self, user_id: str, token: str):
        """Create user session record."""
        try:
            session_id = f"session_{int(time.time())}_{user_id}"
            expiry = datetime.utcnow() + timedelta(minutes=self.settings.auth.access_token_expire_minutes)
            
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                await db.execute("""
                    INSERT INTO user_sessions (session_id, user_id, token_hash, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (session_id, user_id, token, expiry))
                await db.commit()
                
        except Exception as e:
            logger.error("Failed to create user session", user_id=user_id, error=str(e))
    
    async def invalidate_user_session(self, token: str):
        """Invalidate user session."""
        try:
            user_info = self.jwt_handler.extract_user_info(token)
            if not user_info:
                return
            
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                await db.execute(
                    "UPDATE user_sessions SET is_active = FALSE WHERE user_id = ? AND is_active = TRUE",
                    (user_info["user_id"],)
                )
                await db.commit()
                
        except Exception as e:
            logger.error("Failed to invalidate session", error=str(e))
    
    async def _cache_user_permissions(self, user_id: str, roles: List[str], permissions: List[str]):
        """Cache user permissions."""
        cache_key = f"permissions:{user_id}"
        self._permission_cache[cache_key] = (time.time(), permissions)
    
    async def cleanup_expired_sessions(self):
        """Clean up expired user sessions."""
        try:
            async with aiosqlite.connect(self.settings.database.url.replace("sqlite:///", "")) as db:
                await db.execute(
                    "DELETE FROM user_sessions WHERE expires_at < ? OR is_active = FALSE",
                    (datetime.utcnow(),)
                )
                await db.commit()
                
                # Clear permission cache entries older than expiry
                current_time = time.time()
                expired_keys = [
                    key for key, (cache_time, _) in self._permission_cache.items()
                    if current_time - cache_time > self._cache_expiry
                ]
                for key in expired_keys:
                    del self._permission_cache[key]
                
                logger.info("Cleaned up expired sessions", sessions_cleaned=len(expired_keys))
                
        except Exception as e:
            logger.error("Failed to cleanup expired sessions", error=str(e))