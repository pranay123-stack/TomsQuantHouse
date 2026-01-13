#!/usr/bin/env python3
"""
LangGraph API Service Entry Point
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
from app.core.config import settings
from app.core.database import db_manager

async def init_database():
    """Initialize database tables"""
    try:
        await db_manager.initialize()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

async def main():
    """Main entry point"""
    import uvicorn
    
    # Initialize database
    await init_database()
    
    # Start the server
    print(f"""
🚀 LangGraph API Service Starting
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Service Information:
   Version: 1.0.0
   Environment: {settings.environment}
   Host: {settings.host}
   Port: {settings.port}
   Debug: {settings.debug}

🔗 Endpoints:
   API: http://{settings.host}:{settings.port}
   Docs: http://{settings.host}:{settings.port}/docs
   Health: http://{settings.host}:{settings.port}/health
   Metrics: http://{settings.host}:{settings.port}/metrics

📖 Features:
   ✅ JWT Authentication & Authorization
   ✅ Workflow Execution (Single/Batch/Async)
   ✅ State Management & Persistence
   ✅ Real-time Monitoring (WebSocket)
   ✅ Visualization & Analytics
   ✅ Comprehensive API Documentation
   ✅ Health Checks & Metrics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """)
    
    # Configure uvicorn
    config = {
        "app": app,
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level.lower(),
        "access_log": True,
    }
    
    if settings.debug:
        config["reload"] = True
        config["reload_dirs"] = ["app"]
    
    # Start server
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n👋 Shutting down LangGraph API Service...")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())