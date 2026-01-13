"""
ASYMEdge Dashboard API - Authentication Middleware

Authentication and authorization middleware providing:
- JWT token validation
- API key authentication
- User session management
- Rate limiting per user
- Permission checks
"""

from fastapi import Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any
import logging
import time
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from api.database.models import User, UserSession
from api.database.database import get_db_session
from api.config import settings

logger = logging.getLogger(__name__)

# Security setup
security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Rate limiting storage (in production, use Redis)
user_rate_limits: Dict[int, Dict[str, Any]] = {}

class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        
        if user_id is None:
            return None
        
        return {"user_id": user_id, "token_data": payload}
        
    except jwt.PyJWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token"""
    if not credentials:
        raise AuthenticationError("No authentication credentials provided")
    
    token = credentials.credentials
    token_data = verify_token(token)
    
    if not token_data:
        raise AuthenticationError("Invalid or expired token")
    
    user_id = token_data["user_id"]
    
    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        
        if not user:
            raise AuthenticationError("User not found or inactive")
        
        return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
    
    return current_user

async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise AuthorizationError("Superuser privileges required")
    
    return current_user

def check_user_tier(required_tier: str, user_tier: str) -> bool:
    """Check if user tier meets requirement"""
    tier_levels = {"default": 0, "premium": 1, "enterprise": 2}
    return tier_levels.get(user_tier, 0) >= tier_levels.get(required_tier, 0)

def require_user_tier(required_tier: str):
    """Decorator to require specific user tier"""
    def decorator(current_user: User = Depends(get_current_user)) -> User:
        if not check_user_tier(required_tier, current_user.tier):
            raise AuthorizationError(f"{required_tier.title()} tier required")
        return current_user
    return decorator

def rate_limit_user(user_id: int, endpoint: str = ""):
    """Check and update rate limit for user"""
    current_time = time.time()
    window_start = current_time - settings.RATE_LIMIT_WINDOW
    
    if user_id not in user_rate_limits:
        user_rate_limits[user_id] = {}
    
    user_limits = user_rate_limits[user_id]
    
    if endpoint not in user_limits:
        user_limits[endpoint] = []
    
    # Clean old requests
    user_limits[endpoint] = [
        req_time for req_time in user_limits[endpoint] 
        if req_time > window_start
    ]
    
    # Check limit
    max_requests = settings.get_rate_limit("default")  # Get user's actual limit in real implementation
    
    if len(user_limits[endpoint]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {max_requests} requests per hour",
                "retry_after": 3600  # 1 hour in seconds
            }
        )
    
    # Add current request
    user_limits[endpoint].append(current_time)
    
    return {
        "requests_made": len(user_limits[endpoint]),
        "requests_remaining": max_requests - len(user_limits[endpoint]),
        "reset_time": window_start + settings.RATE_LIMIT_WINDOW
    }

async def auth_middleware(request: Request, call_next):
    """Authentication middleware"""
    start_time = time.time()
    
    # Skip authentication for certain paths
    public_paths = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/health/",
        "/",
        "/favicon.ico"
    ]
    
    if request.url.path in public_paths or request.url.path.startswith("/api/v1/health"):
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Handle different authentication methods
    auth_header = request.headers.get("Authorization")
    api_key = request.headers.get("X-API-Key")
    
    if not auth_header and not api_key:
        # For demo purposes, allow unauthenticated access to most endpoints
        # In production, this should be removed
        logger.warning(f"Unauthenticated request to {request.url.path}")
        
        # Add a demo user for development
        user = User(
            id=1,
            email="demo@asymedge.com",
            username="demo",
            full_name="Demo User",
            is_active=True,
            is_verified=True,
            tier="enterprise"
        )
        
        request.state.user = user
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    try:
        user = None
        
        # API Key authentication
        if api_key:
            user = await authenticate_api_key(api_key)
        # JWT Token authentication
        elif auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user = await authenticate_token(token)
        
        if not user:
            raise AuthenticationError("Invalid authentication credentials")
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        # Add user to request state
        request.state.user = user
        
        # Rate limiting
        rate_limit_info = rate_limit_user(user.id, request.url.path)
        request.state.rate_limit = rate_limit_info
        
        # Process request
        response = await call_next(request)
        
        # Add headers
        response.headers["X-User-ID"] = str(user.id)
        response.headers["X-User-Tier"] = user.tier
        response.headers["X-Rate-Limit-Remaining"] = str(rate_limit_info["requests_remaining"])
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except AuthenticationError as e:
        logger.warning(f"Authentication failed for {request.url.path}: {e.detail}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": 401,
                    "message": "Authentication required",
                    "details": e.detail
                },
                "timestamp": datetime.now().isoformat()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    except Exception as e:
        logger.error(f"Authentication middleware error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": 500,
                    "message": "Authentication system error"
                },
                "timestamp": datetime.now().isoformat()
            }
        )

async def authenticate_api_key(api_key: str) -> Optional[User]:
    """Authenticate using API key"""
    with get_db_session() as db:
        # In a real implementation, you would have an API key table
        # For demo, check if API key matches a user's API key or use a default
        user = db.query(User).filter(
            User.is_active == True
        ).first()
        
        if user:
            # Demo: accept any non-empty API key as valid
            return user
        
        return None

async def authenticate_token(token: str) -> Optional[User]:
    """Authenticate using JWT token"""
    token_data = verify_token(token)
    
    if not token_data:
        return None
    
    user_id = token_data["user_id"]
    
    with get_db_session() as db:
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Update last login
        user.last_login = datetime.now()
        db.commit()
        
        return user

class RateLimitMiddleware:
    """Rate limiting middleware"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip rate limiting for health endpoints
        path = scope.get("path", "")
        if path.startswith("/api/v1/health"):
            await self.app(scope, receive, send)
            return
        
        # Apply rate limiting logic here if needed
        await self.app(scope, receive, send)

def create_user_session(user_id: int, token_hash: str, expires_at: datetime, 
                      ip_address: str = None, user_agent: str = None) -> UserSession:
    """Create a new user session"""
    session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    with get_db_session() as db:
        db.add(session)
        db.commit()
        db.refresh(session)
    
    return session

def revoke_user_session(session_id: int) -> bool:
    """Revoke a user session"""
    with get_db_session() as db:
        session = db.query(UserSession).filter(
            UserSession.id == session_id
        ).first()
        
        if session:
            session.is_active = False
            db.commit()
            return True
        
        return False

def cleanup_expired_sessions():
    """Clean up expired user sessions"""
    with get_db_session() as db:
        expired_sessions = db.query(UserSession).filter(
            UserSession.expires_at < datetime.now()
        ).all()
        
        for session in expired_sessions:
            db.delete(session)
        
        db.commit()
        
        logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

# Export authentication utilities
__all__ = [
    "verify_password",
    "get_password_hash", 
    "create_access_token",
    "verify_token",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "check_user_tier",
    "require_user_tier",
    "rate_limit_user",
    "auth_middleware",
    "create_user_session",
    "revoke_user_session",
    "cleanup_expired_sessions"
]