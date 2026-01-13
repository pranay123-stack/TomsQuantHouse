"""
Core package initialization
"""

from .config import settings
from .database import db_manager

__all__ = ["settings", "db_manager"]