"""
ASYMEdge Dashboard API - User Management Routes

User management endpoints providing:
- User registration and authentication
- Profile management and updates
- Password management
- Session management
- User tier and permissions
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.security import HTTPBearer
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from api.database.models import User, UserSession
from api.database.database import get_db_session
from api.schemas import (
    UserResponse, UserCreate, UserUpdate, UserLogin, TokenResponse, TokenRefresh,
    PasswordChange, PasswordReset, PasswordResetConfirm, APIResponse, ErrorResponse
)
from api.middleware.auth import (
    verify_password, get_password_hash, create_access_token, get_current_user,
    get_current_superuser, create_user_session, revoke_user_session
)
from api.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()

@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    try:
        with get_db_session() as db:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.email == user_data.email) | (User.username == user_data.username)
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "User with this email or username already exists"}
                )
            
            # Create new user
            hashed_password = get_password_hash(user_data.password)
            
            user = User(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                full_name=user_data.full_name,
                tier=user_data.tier,
                is_active=True,
                is_verified=False,  # In production, would send verification email
                is_superuser=False
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"User registered: {user.email}")
            
            return UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                tier=user.tier,
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin, background_tasks: BackgroundTasks):
    """Authenticate user and return access token"""
    try:
        with get_db_session() as db:
            # Find user by username or email
            user = db.query(User).filter(
                (User.username == login_data.username) | (User.email == login_data.username)
            ).first()
            
            if not user or not verify_password(login_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=401,
                    detail={"error": "Invalid username or password"}
                )
            
            if not user.is_active:
                raise HTTPException(
                    status_code=401,
                    detail={"error": "User account is disabled"}
                )
            
            # Create access token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": str(user.id), "username": user.username, "tier": user.tier},
                expires_delta=access_token_expires
            )
            
            # Create user session
            session = create_user_session(
                user_id=user.id,
                token_hash=access_token,  # In production, store hash
                expires_at=datetime.now() + access_token_expires
            )
            
            # Update last login
            user.last_login = datetime.now()
            db.commit()
            
            logger.info(f"User logged in: {user.email}")
            
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=int(access_token_expires.total_seconds()),
                user=UserResponse(
                    id=user.id,
                    email=user.email,
                    username=user.username,
                    full_name=user.full_name,
                    tier=user.tier,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    is_superuser=user.is_superuser,
                    last_login=user.last_login,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to login user: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/logout", response_model=APIResponse)
async def logout_user(current_user: User = Depends(get_current_user)):
    """Logout user and invalidate session"""
    try:
        with get_db_session() as db:
            # Find and revoke active sessions for this user
            sessions = db.query(UserSession).filter(
                UserSession.user_id == current_user.id,
                UserSession.is_active == True
            ).all()
            
            for session in sessions:
                session.is_active = False
            
            db.commit()
            
            logger.info(f"User logged out: {current_user.email}")
            
            return APIResponse(
                success=True,
                message="Logged out successfully",
                data={"user_id": current_user.id}
            )
            
    except Exception as e:
        logger.error(f"Failed to logout user: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        tier=current_user.tier,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
        last_login=current_user.last_login,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user profile"""
    try:
        with get_db_session() as db:
            user = db.query(User).filter(User.id == current_user.id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail={"error": "User not found"})
            
            # Check for username/email conflicts if being updated
            if user_data.username and user_data.username != user.username:
                existing_user = db.query(User).filter(
                    User.username == user_data.username,
                    User.id != user.id
                ).first()
                
                if existing_user:
                    raise HTTPException(
                        status_code=400,
                        detail={"error": "Username already taken"}
                    )
            
            if user_data.email and user_data.email != user.email:
                existing_user = db.query(User).filter(
                    User.email == user_data.email,
                    User.id != user.id
                ).first()
                
                if existing_user:
                    raise HTTPException(
                        status_code=400,
                        detail={"error": "Email already registered"}
                    )
            
            # Update fields
            update_data = user_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)
            
            user.updated_at = datetime.now()
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"User profile updated: {user.email}")
            
            return UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                tier=user.tier,
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/change-password", response_model=APIResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user)
):
    """Change user password"""
    try:
        with get_db_session() as db:
            user = db.query(User).filter(User.id == current_user.id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail={"error": "User not found"})
            
            # Verify current password
            if not verify_password(password_data.current_password, user.hashed_password):
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Current password is incorrect"}
                )
            
            # Update password
            user.hashed_password = get_password_hash(password_data.new_password)
            user.updated_at = datetime.now()
            
            db.commit()
            
            # Revoke all sessions (force re-login)
            sessions = db.query(UserSession).filter(
                UserSession.user_id == user.id,
                UserSession.is_active == True
            ).all()
            
            for session in sessions:
                session.is_active = False
            
            db.commit()
            
            logger.info(f"Password changed for user: {user.email}")
            
            return APIResponse(
                success=True,
                message="Password changed successfully. Please log in again.",
                data={"user_id": user.id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/request-password-reset", response_model=APIResponse)
async def request_password_reset(reset_data: PasswordReset):
    """Request password reset (in production, would send email)"""
    try:
        with get_db_session() as db:
            user = db.query(User).filter(User.email == reset_data.email).first()
            
            if not user:
                # Don't reveal if email exists
                return APIResponse(
                    success=True,
                    message="If the email exists, a reset link has been sent",
                    data={}
                )
            
            # In production, generate reset token and send email
            reset_token = create_access_token(
                data={"sub": str(user.id), "type": "password_reset"},
                expires_delta=timedelta(hours=1)
            )
            
            logger.info(f"Password reset requested for: {user.email}")
            logger.info(f"Reset token: {reset_token}")  # In production, don't log this
            
            return APIResponse(
                success=True,
                message="Password reset instructions sent to your email",
                data={"email": user.email}
            )
            
    except Exception as e:
        logger.error(f"Failed to request password reset: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/confirm-password-reset", response_model=APIResponse)
async def confirm_password_reset(reset_data: PasswordResetConfirm):
    """Confirm password reset with token"""
    try:
        # Verify reset token
        from api.middleware.auth import verify_token
        token_data = verify_token(reset_data.token)
        
        if not token_data or token_data.get("type") != "password_reset":
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid or expired reset token"}
            )
        
        user_id = token_data["user_id"]
        
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail={"error": "User not found"})
            
            # Update password
            user.hashed_password = get_password_hash(reset_data.new_password)
            user.updated_at = datetime.now()
            
            # Revoke all sessions
            sessions = db.query(UserSession).filter(
                UserSession.user_id == user.id,
                UserSession.is_active == True
            ).all()
            
            for session in sessions:
                session.is_active = False
            
            db.commit()
            
            logger.info(f"Password reset confirmed for: {user.email}")
            
            return APIResponse(
                success=True,
                message="Password reset successful. Please log in with your new password.",
                data={"user_id": user.id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm password reset: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_user_sessions(current_user: User = Depends(get_current_user)):
    """Get user active sessions"""
    try:
        with get_db_session() as db:
            sessions = db.query(UserSession).filter(
                UserSession.user_id == current_user.id,
                UserSession.is_active == True
            ).order_by(UserSession.created_at.desc()).all()
            
            return [
                {
                    "id": session.id,
                    "created_at": session.created_at.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "ip_address": session.ip_address,
                    "user_agent": session.user_agent[:100] if session.user_agent else None,  # Truncate for privacy
                    "is_active": session.is_active
                }
                for session in sessions
            ]
            
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/sessions/{session_id}", response_model=APIResponse)
async def revoke_user_session_endpoint(
    session_id: int,
    current_user: User = Depends(get_current_user)
):
    """Revoke a specific user session"""
    try:
        with get_db_session() as db:
            session = db.query(UserSession).filter(
                UserSession.id == session_id,
                UserSession.user_id == current_user.id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail={"error": "Session not found"})
            
            session.is_active = False
            db.commit()
            
            logger.info(f"Session {session_id} revoked for user {current_user.email}")
            
            return APIResponse(
                success=True,
                message="Session revoked successfully",
                data={"session_id": session_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke session: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/sessions", response_model=APIResponse)
async def revoke_all_sessions(current_user: User = Depends(get_current_user)):
    """Revoke all user sessions"""
    try:
        with get_db_session() as db:
            sessions = db.query(UserSession).filter(
                UserSession.user_id == current_user.id,
                UserSession.is_active == True
            ).all()
            
            for session in sessions:
                session.is_active = False
            
            db.commit()
            
            logger.info(f"All sessions revoked for user: {current_user.email}")
            
            return APIResponse(
                success=True,
                message="All sessions revoked successfully",
                data={"revoked_sessions": len(sessions)}
            )
            
    except Exception as e:
        logger.error(f"Failed to revoke all sessions: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

# Admin endpoints
@router.get("/", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    tier: Optional[str] = Query(None),
    current_user: User = Depends(get_current_superuser)
):
    """Get all users (admin only)"""
    try:
        with get_db_session() as db:
            query = db.query(User)
            
            # Apply filters
            if is_active is not None:
                query = query.filter(User.is_active == is_active)
            
            if tier:
                query = query.filter(User.tier == tier)
            
            users = query.offset(skip).limit(limit).all()
            
            return [
                UserResponse(
                    id=user.id,
                    email=user.email,
                    username=user.username,
                    full_name=user.full_name,
                    tier=user.tier,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    is_superuser=user.is_superuser,
                    last_login=user.last_login,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
                for user in users
            ]
            
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.put("/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_superuser)
):
    """Update user by admin"""
    try:
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail={"error": "User not found"})
            
            # Update fields
            update_data = user_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user, field, value)
            
            user.updated_at = datetime.now()
            
            db.commit()
            db.refresh(user)
            
            logger.info(f"User {user_id} updated by admin: {current_user.email}")
            
            return UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                tier=user.tier,
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_superuser=user.is_superuser,
                last_login=user.last_login,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user {user_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.delete("/{user_id}", response_model=APIResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser)
):
    """Delete user (admin only)"""
    try:
        with get_db_session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise HTTPException(status_code=404, detail={"error": "User not found"})
            
            if user.id == current_user.id:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Cannot delete your own account"}
                )
            
            # Soft delete by deactivating
            user.is_active = False
            user.updated_at = datetime.now()
            
            # Revoke all sessions
            sessions = db.query(UserSession).filter(
                UserSession.user_id == user.id
            ).all()
            
            for session in sessions:
                session.is_active = False
            
            db.commit()
            
            logger.info(f"User {user_id} deactivated by admin: {current_user.email}")
            
            return APIResponse(
                success=True,
                message="User deactivated successfully",
                data={"user_id": user_id}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})