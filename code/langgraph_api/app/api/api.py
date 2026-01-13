"""
Main API router with all endpoints
"""

from fastapi import APIRouter
from .v1 import workflows, states, monitoring, visualization, auth

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(states.router, prefix="/states", tags=["States"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
api_router.include_router(visualization.router, prefix="/visualization", tags=["Visualization"])