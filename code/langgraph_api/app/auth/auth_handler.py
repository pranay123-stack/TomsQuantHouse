"""
Authentication handler with JWT tokens and role-based access control
"""

import logging
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..core.database import db_manager
from ..core.config import settings
from .auth_models import User, UserRole, TokenData, LoginRequest
from ..models.user import User as UserModel

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthHandler:
    """Authentication and authorization handler"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash password"""
        return pwd_context.hash(password)
    
    def create_access_token(
        self, 
        user_id: str, 
        username: str, 
        role: UserRole,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=self.access_token_expire_minutes)
        )
        
        to_encode = {
            "sub": user_id,
            "username": username,
            "role": role.value,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=7)  # 7 days
        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            role: str = payload.get("role")
            token_type: str = payload.get("type")
            
            if user_id is None or role is None or token_type != "access":
                return None
            
            return TokenData(
                user_id=user_id,
                username=username,
                role=UserRole(role),
                permissions=self._get_role_permissions(UserRole(role))
            )
            
        except JWTError:
            return None
    
    def _get_role_permissions(self, role: UserRole) -> List[str]:
        """Get permissions for user role"""
        permissions = {
            UserRole.ADMIN: [
                "workflow.create",
                "workflow.read",
                "workflow.update",
                "workflow.delete",
                "workflow.execute",
                "workflow.batch_execute",
                "state.create",
                "state.read",
                "state.update",
                "state.delete",
                "monitoring.read",
                "monitoring.manage",
                "users.manage",
                "system.admin"
            ],
            UserRole.PREMIUM: [
                "workflow.create",
                "workflow.read",
                "workflow.update",
                "workflow.delete",
                "workflow.execute",
                "workflow.batch_execute",
                "state.create",
                "state.read",
                "state.update",
                "state.delete",
                "monitoring.read"
            ],
            UserRole.STANDARD: [
                "workflow.create",
                "workflow.read",
                "workflow.execute",
                "state.create",
                "state.read",
                "state.update",
                "monitoring.read"
            ],
            UserRole.BASIC: [
                "workflow.read",
                "workflow.execute",
                "state.read"
            ]
        }
        
        return permissions.get(role, [])
    
    def require_permission(self, required_permission: str):
        """Decorator to require specific permission"""
        def permission_dependency(current_user: User = Depends(get_current_user)):
            if required_permission not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required: {required_permission}"
                )
            return current_user
        return permission_dependency
    
    async def authenticate_user(self, login_request: LoginRequest) -> Optional[User]:
        """Authenticate user with username and password"""
        async with db_manager.get_session() as session:
            # Try to find user by username or email
            result = await session.execute(
                select(UserModel).where(
                    (UserModel.username == login_request.username) |
                    (UserModel.email == login_request.username)
                )
            )
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return None
            
            if not user_model.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User account is disabled"
                )
            
            # Check if user is locked
            if user_model.locked_until and user_model.locked_until > datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="User account is temporarily locked"
                )
            
            # Verify password
            if not self.verify_password(login_request.password, user_model.password_hash):
                # Increment login attempts
                user_model.login_attempts += 1
                
                # Lock account if too many attempts
                if user_model.login_attempts >= settings.max_login_attempts:
                    user_model.locked_until = datetime.utcnow() + timedelta(
                        minutes=settings.lockout_duration_minutes
                    )
                    logger.warning(f"User {login_request.username} locked due to failed login attempts")
                
                await session.commit()
                return None
            
            # Successful login - reset attempts and update last login
            user_model.login_attempts = 0
            user_model.locked_until = None
            user_model.last_login = datetime.utcnow()
            await session.commit()
            
            # Convert to User model
            return self._model_to_user(user_model)
    
    async def create_user(self, user_data: dict) -> User:
        """Create new user"""
        async with db_manager.get_session() as session:
            # Check if user already exists
            existing_user = await session.execute(
                select(UserModel).where(
                    (UserModel.username == user_data["username"]) |
                    (UserModel.email == user_data["email"])
                )
            )
            
            if existing_user.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User with this username or email already exists"
                )
            
            # Create new user
            user_model = UserModel(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=self.get_password_hash(user_data["password"]),
                full_name=user_data.get("full_name"),
                role=user_data.get("role", UserRole.BASIC),
                is_active=True,
                is_verified=False
            )
            
            session.add(user_model)
            await session.commit()
            await session.refresh(user_model)
            
            logger.info(f"Created new user: {user_data['username']}")
            return self._model_to_user(user_model)
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with db_manager.get_session() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user_model = result.scalar_one_or_none()
            
            if not user_model:
                return None
            
            return self._model_to_user(user_model)
    
    def _model_to_user(self, user_model) -> User:
        """Convert SQLAlchemy model to User model"""
        return User(
            id=user_model.id,
            email=user_model.email,
            username=user_model.username,
            full_name=user_model.full_name,
            role=UserRole(user_model.role),
            is_active=user_model.is_active,
            is_verified=user_model.is_verified,
            created_at=user_model.created_at,
            updated_at=user_model.updated_at,
            last_login=user_model.last_login,
            login_attempts=user_model.login_attempts,
            locked_until=user_model.locked_until
        )

# Global auth handler instance
auth_handler = AuthHandler()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user"""
    try:
        token_data = auth_handler.verify_token(credentials.credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = await auth_handler.get_user_by_id(token_data.user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is disabled"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    return current_user