"""
User database model
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum as SQLEnum, Integer
from sqlalchemy.sql import func
from ..core.database import Base
import enum
import uuid

class UserRole(enum.Enum):
    """User roles for authorization"""
    ADMIN = "admin"
    PREMIUM = "premium"
    STANDARD = "standard"
    BASIC = "basic"

class User(Base):
    """User database model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.BASIC, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime)
    login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    
    def __repr__(self):
        return f"<User(id='{self.id}', username='{self.username}', role='{self.role}')>"