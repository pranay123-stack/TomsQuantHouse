"""
Authentication endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
import logging
from datetime import timedelta

from ...auth.auth_handler import auth_handler, get_current_user
from ...auth.auth_models import (
    User, Token, LoginRequest, UserCreate, UserUpdate, UserRole, APIResponse
)
from ...core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/login", response_model=Token)
async def login(
    login_request: LoginRequest
):
    """User login with username/email and password"""
    try:
        user = await auth_handler.authenticate_user(login_request)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(
            minutes=settings.access_token_expire_minutes if not login_request.remember_me else 1440
        )
        access_token = auth_handler.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            expires_delta=access_token_expires
        )
        
        # Create refresh token if remember_me
        refresh_token = None
        if login_request.remember_me:
            refresh_token = auth_handler.create_refresh_token(user.id)
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            refresh_token=refresh_token
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/register", response_model=User)
async def register(
    user_data: UserCreate
):
    """User registration"""
    try:
        # Validate password strength
        if len(user_data.password) < settings.password_min_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password must be at least {settings.password_min_length} characters long"
            )
        
        # Create user
        user = await auth_handler.create_user(user_data.dict())
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str
):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = auth_handler.verify_token(refresh_token)
        
        if not payload or payload.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user
        user = await auth_handler.get_user_by_id(payload.user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        access_token = auth_handler.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user profile"""
    try:
        from ...services.user_service import UserService
        user_service = UserService()
        
        updated_user = await user_service.update_user(
            current_user.id, user_update.dict(exclude_unset=True)
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return updated_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user)
):
    """Change user password"""
    try:
        # Validate new password
        if len(new_password) < settings.password_min_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password must be at least {settings.password_min_length} characters long"
            )
        
        from ...services.user_service import UserService
        user_service = UserService()
        
        success = await user_service.change_password(
            current_user.id, current_password, new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        return APIResponse(message="Password changed successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout user (invalidate current token)"""
    # In a production system, you would add the token to a blacklist
    # For now, we'll just return success
    return APIResponse(message="Logged out successfully")

@router.post("/verify-email")
async def verify_email(
    verification_token: str,
    current_user: User = Depends(get_current_user)
):
    """Verify user email address"""
    try:
        from ...services.user_service import UserService
        user_service = UserService()
        
        success = await user_service.verify_email(current_user.id, verification_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        return APIResponse(message="Email verified successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email"
        )

@router.post("/request-password-reset")
async def request_password_reset(
    email: str
):
    """Request password reset"""
    try:
        from ...services.user_service import UserService
        user_service = UserService()
        
        success = await user_service.request_password_reset(email)
        
        # Always return success to prevent email enumeration
        return APIResponse(
            message="If the email exists, a reset link has been sent"
        )
        
    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        return APIResponse(
            message="If the email exists, a reset link has been sent"
        )

@router.post("/reset-password")
async def reset_password(
    reset_token: str,
    new_password: str
):
    """Reset password using reset token"""
    try:
        # Validate new password
        if len(new_password) < settings.password_min_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password must be at least {settings.password_min_length} characters long"
            )
        
        from ...services.user_service import UserService
        user_service = UserService()
        
        success = await user_service.reset_password(reset_token, new_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        return APIResponse(message="Password reset successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )

@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_user)
):
    """Get user permissions"""
    return {
        "permissions": auth_handler._get_role_permissions(current_user.role),
        "role": current_user.role.value
    }

@router.post("/impersonate/{user_id}")
async def impersonate_user(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Admin endpoint to impersonate another user"""
    # Only admins can impersonate
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can impersonate users"
        )
    
    try:
        target_user = await auth_handler.get_user_by_id(user_id)
        
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Create impersonation token
        impersonation_token = auth_handler.create_access_token(
            user_id=target_user.id,
            username=target_user.username,
            role=target_user.role
        )
        
        return {
            "impersonation_token": impersonation_token,
            "impersonated_user": target_user,
            "original_user": current_user
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User impersonation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to impersonate user"
        )

@router.get("/health")
async def auth_health_check():
    """Authentication system health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": "2025-11-02T09:09:01Z"
    }