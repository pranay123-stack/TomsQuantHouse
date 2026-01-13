"""
User service for user management operations
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt

from ..core.database import db_manager
from ..core.config import settings
from ..auth.auth_handler import pwd_context, auth_handler
from ..auth.auth_models import User, UserUpdate

logger = logging.getLogger(__name__)

class UserService:
    """Service for user operations"""
    
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user information"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            user_model = result.fetchone()
            
            if not user_model:
                return None
            
            # Update fields
            update_fields = []
            params = []
            
            for field, value in update_data.items():
                if field == "email":
                    update_fields.append("email = ?")
                    params.append(value)
                elif field == "username":
                    update_fields.append("username = ?")
                    params.append(value)
                elif field == "full_name":
                    update_fields.append("full_name = ?")
                    params.append(value)
            
            if update_fields:
                update_fields.append("updated_at = ?")
                params.append(datetime.now())
                params.append(user_id)
                
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
                await session.execute(query, params)
                await session.commit()
            
            return await self.get_user_by_id(user_id)
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,)
            )
            user_model = result.fetchone()
            
            if not user_model:
                return None
            
            return self._model_to_user(user_model)
    
    async def change_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """Change user password"""
        async with db_manager.get_session() as session:
            result = await session.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,)
            )
            user_data = result.fetchone()
            
            if not user_data or not pwd_context.verify(current_password, user_data[0]):
                return False
            
            new_hash = pwd_context.hash(new_password)
            await session.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (new_hash, datetime.now(), user_id)
            )
            await session.commit()
            
            return True
    
    async def verify_email(self, user_id: str, verification_token: str) -> bool:
        """Verify user email"""
        # Simplified email verification
        async with db_manager.get_session() as session:
            await session.execute(
                "UPDATE users SET is_verified = ?, updated_at = ? WHERE id = ?",
                (True, datetime.now(), user_id)
            )
            await session.commit()
            
            return True
    
    async def request_password_reset(self, email: str) -> bool:
        """Request password reset"""
        # In real implementation, generate reset token and send email
        logger.info(f"Password reset requested for {email}")
        return True
    
    async def reset_password(self, reset_token: str, new_password: str) -> bool:
        """Reset password using reset token"""
        # Simplified password reset
        async with db_manager.get_session() as session:
            # In real implementation, verify reset token
            new_hash = pwd_context.hash(new_password)
            
            # This is simplified - would need token validation
            await session.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (new_hash, datetime.now(), "user_id_from_token")  # Would get from token
            )
            await session.commit()
            
            return True
    
    def _model_to_user(self, user_model) -> User:
        """Convert database model to User"""
        return User(
            id=user_model[0],
            email=user_model[1],
            username=user_model[2],
            full_name=user_model[3] if user_model[3] else None,
            role=user_model[4],
            is_active=user_model[5],
            is_verified=user_model[6],
            created_at=user_model[7],
            updated_at=user_model[8],
            last_login=user_model[9],
            login_attempts=user_model[10],
            locked_until=user_model[11]
        )