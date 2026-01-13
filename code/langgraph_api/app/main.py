"""
Main FastAPI application for LangGraph API Service
Provides comprehensive workflow management with authentication and monitoring
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from typing import Dict, Any

from .core.config import settings
from .core.database import DatabaseManager
from .auth.auth_handler import AuthHandler, get_current_user
from .auth.auth_models import User, UserRole
from .api.v1.api import api_router
from .api.websocket.manager import WebSocketManager
from .services.health_monitor import HealthMonitor
from .services.metrics_collector import MetricsCollector

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
db_manager = DatabaseManager()
auth_handler = AuthHandler()
ws_manager = WebSocketManager()
health_monitor = HealthMonitor()
metrics_collector = MetricsCollector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting LangGraph API Service...")
    
    try:
        # Initialize database connections
        await db_manager.initialize()
        
        # Initialize monitoring services
        health_monitor.start()
        metrics_collector.start()
        
        logger.info("LangGraph API Service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down LangGraph API Service...")
        
        health_monitor.stop()
        metrics_collector.stop()
        await db_manager.close()
        
        logger.info("LangGraph API Service shut down successfully")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    # Create FastAPI app with custom settings
    app = FastAPI(
        title="LangGraph API Service",
        description="""
        Comprehensive LangGraph API Service for workflow management with real-time monitoring.
        
        ## Features
        
        * **Workflow Execution**: Single, batch, and async workflow execution
        * **State Management**: Complete workflow state persistence and retrieval
        * **Real-time Monitoring**: WebSocket-based real-time monitoring and alerts
        * **Authentication**: JWT-based authentication with role-based access control
        * **Visualization**: Workflow graphs and execution timelines
        * **Metrics & Health**: System health checks and performance metrics
        * **Documentation**: Comprehensive Swagger/OpenAPI documentation
        
        ## Authentication
        
        Use Bearer token authentication in the Authorization header:
        ```
        Authorization: Bearer your-jwt-token
        ```
        
        ## Rate Limiting
        
        API endpoints have rate limiting based on user role:
        - Admin: 1000 requests/hour
        - Premium: 500 requests/hour  
        - Standard: 200 requests/hour
        - Basic: 100 requests/hour
        """,
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        lifespan=lifespan
    )
    
    # Security middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Root endpoint
    @app.get("/", tags=["System"])
    async def root():
        """API root endpoint"""
        return {
            "service": "LangGraph API Service",
            "version": "1.0.0",
            "status": "running",
            "timestamp": "2025-11-02T09:09:01Z",
            "docs": "/docs" if settings.environment != "production" else None,
            "health": "/health",
            "metrics": "/metrics"
        }
    
    # Health check endpoint (public)
    @app.get("/health", tags=["System"])
    async def health_check():
        """Comprehensive health check endpoint"""
        try:
            health_status = await health_monitor.get_comprehensive_health()
            
            if health_status["overall_status"] == "healthy":
                return JSONResponse(status_code=200, content=health_status)
            elif health_status["overall_status"] == "degraded":
                return JSONResponse(status_code=200, content=health_status)
            else:
                return JSONResponse(status_code=503, content=health_status)
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "overall_status": "unhealthy",
                    "error": str(e),
                    "timestamp": "2025-11-02T09:09:01Z"
                }
            )
    
    # Metrics endpoint (requires authentication)
    @app.get("/metrics", tags=["System"])
    async def get_metrics(current_user: User = Depends(get_current_user)):
        """Prometheus-compatible metrics endpoint"""
        try:
            metrics = await metrics_collector.get_metrics()
            return JSONResponse(content=metrics)
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # WebSocket connection endpoint
    @app.websocket("/ws/{user_id}")
    async def websocket_endpoint(websocket, user_id: str):
        """WebSocket endpoint for real-time updates"""
        await ws_manager.connect(websocket, user_id)
        try:
            while True:
                # Keep connection alive
                data = await websocket.receive_text()
                await websocket.send_text(f"Echo: {data}")
        except Exception as e:
            logger.info(f"WebSocket connection closed: {e}")
        finally:
            ws_manager.disconnect(user_id)
    
    # Include API router with authentication
    app.include_router(
        api_router,
        prefix="/api/v1",
        dependencies=[Depends(get_current_user)]
    )
    
    # Global exception handler
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        """Global HTTP exception handler"""
        logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "http_error",
                    "status_code": exc.status_code,
                    "message": exc.detail,
                    "timestamp": "2025-11-02T09:09:01Z"
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """Global exception handler"""
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "internal_error",
                    "message": "An unexpected error occurred",
                    "timestamp": "2025-11-02T09:09:01Z"
                }
            }
        )
    
    return app

# Create application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level
    )