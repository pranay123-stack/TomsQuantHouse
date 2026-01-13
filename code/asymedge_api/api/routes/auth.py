"""
ASYMEdge Dashboard API - Authentication Routes

Authentication routes providing:
- User login and token generation
- Token refresh functionality
- Logout and session management
- Password reset functionality
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from api.database.models import User
from api.middleware.auth import get_current_user, get_current_active_user, get_current_superuser

router = APIRouter()

# Re-export authentication dependencies for convenience
get_current_user = get_current_user
get_current_active_user = get_current_active_user  
get_current_superuser = get_current_superuser