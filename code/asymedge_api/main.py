"""
ASYMEdge Dashboard API - Main FastAPI Application

Comprehensive backend service for the ASYMEdge dashboard providing:
- Agent query interfaces for Letta stateful agents
- Real-time data streaming endpoints
- Trading metrics and performance analytics
- Workflow monitoring and status tracking
- User management and authentication
- Dashboard configuration and customization
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
from pathlib import Path
import os

# Import API routers
from api.routes import (
    agents,
    streaming,
    trading_metrics,
    workflow_monitoring,
    user_management,
    dashboard_config,
    health
)
from api.middleware.auth import auth_middleware
from api.middleware.rate_limiter import rate_limiter_middleware
from api.database.database import init_database, get_database
from api.config import settings
from api.utils.logger import setup_logger

# Initialize logger
logger = setup_logger("asymedge_api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting ASYMEdge Dashboard API...")
    
    # Initialize database
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    logger.info("ASYMEdge Dashboard API started successfully")
    yield
    
    logger.info("Shutting down ASYMEdge Dashboard API...")

# Create FastAPI application
app = FastAPI(
    title="ASYMEdge Dashboard API",
    description="""
    Comprehensive backend service for ASYMEdge dashboard providing:
    
    ## Features
    - 🤖 **Agent Query Interfaces**: Integration with Letta stateful agents
    - 📊 **Real-time Streaming**: Live dashboard updates via WebSocket
    - 📈 **Trading Analytics**: Performance metrics and market data
    - 🔄 **Workflow Monitoring**: Status tracking and job management
    - 👤 **User Management**: Authentication and authorization
    - ⚙️ **Dashboard Config**: Customization and settings management
    
    ## API Structure
    - **Agents**: `/api/v1/agents/*` - Agent management and queries
    - **Streaming**: `/api/v1/streaming/*` - Real-time data updates
    - **Trading**: `/api/v1/trading/*` - Metrics and analytics
    - **Workflows**: `/api/v1/workflows/*` - Job monitoring
    - **Users**: `/api/v1/users/*` - User management
    - **Dashboard**: `/api/v1/dashboard/*` - Configuration
    
    ## Authentication
    All endpoints (except health checks) require authentication via:
    - JWT Bearer tokens
    - API keys for service-to-service communication
    
    ## Rate Limiting
    - Default: 1000 requests/hour per user
    - Premium: 5000 requests/hour per user
    - Enterprise: Unlimited (configurable)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Add custom middleware
app.middleware("http")(rate_limiter_middleware)
app.middleware("http")(auth_middleware)

# Include API routers
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(streaming.router, prefix="/api/v1/streaming", tags=["Streaming"])
app.include_router(trading_metrics.router, prefix="/api/v1/trading", tags=["Trading"])
app.include_router(workflow_monitoring.router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(user_management.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(dashboard_config.router, prefix="/api/v1/dashboard", tags=["Dashboard"])

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": exc.headers.get("timestamp", "unknown")
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global general exception handler"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "general_error"
            }
        }
    )

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "ASYMEdge Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/v1/health",
        "endpoints": {
            "agents": "/api/v1/agents",
            "streaming": "/api/v1/streaming",
            "trading": "/api/v1/trading",
            "workflows": "/api/v1/workflows",
            "users": "/api/v1/users",
            "dashboard": "/api/v1/dashboard"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )