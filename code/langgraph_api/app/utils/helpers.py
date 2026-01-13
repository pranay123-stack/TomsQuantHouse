"""
Utility functions for LangGraph API
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from ..core.database import db_manager

logger = logging.getLogger(__name__)

class LangGraphUtils:
    """Utility class for LangGraph operations"""
    
    @staticmethod
    def generate_workflow_id() -> str:
        """Generate unique workflow ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_execution_id() -> str:
        """Generate unique execution ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def sanitize_workflow_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize workflow configuration"""
        # Remove potentially dangerous keys
        dangerous_keys = ['__import__', 'exec', 'eval', 'open', 'file', 'subprocess']
        sanitized = {}
        
        for key, value in config.items():
            if isinstance(key, str) and any(dk in key.lower() for dk in dangerous_keys):
                logger.warning(f"Removing dangerous key from config: {key}")
                continue
            
            if isinstance(value, dict):
                sanitized[key] = LangGraphUtils.sanitize_workflow_config(value)
            elif isinstance(value, list):
                sanitized[key] = [LangGraphUtils.sanitize_workflow_config(item) 
                                if isinstance(item, dict) else item 
                                for item in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def validate_workflow_structure(workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow structure"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = ["nodes", "edges"]
        for field in required_fields:
            if field not in workflow_config:
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["valid"] = False
        
        # Validate nodes
        if "nodes" in workflow_config:
            if not isinstance(workflow_config["nodes"], list):
                validation_result["errors"].append("Nodes must be a list")
                validation_result["valid"] = False
            else:
                node_ids = set()
                for i, node in enumerate(workflow_config["nodes"]):
                    if not isinstance(node, dict):
                        validation_result["errors"].append(f"Node {i} must be an object")
                        validation_result["valid"] = False
                        continue
                    
                    if "id" not in node:
                        validation_result["errors"].append(f"Node {i} missing 'id' field")
                        validation_result["valid"] = False
                    elif node["id"] in node_ids:
                        validation_result["errors"].append(f"Duplicate node ID: {node['id']}")
                        validation_result["valid"] = False
                    else:
                        node_ids.add(node["id"])
        
        # Validate edges
        if "edges" in workflow_config:
            if not isinstance(workflow_config["edges"], list):
                validation_result["errors"].append("Edges must be a list")
                validation_result["valid"] = False
            else:
                for i, edge in enumerate(workflow_config["edges"]):
                    if not isinstance(edge, dict):
                        validation_result["errors"].append(f"Edge {i} must be an object")
                        validation_result["valid"] = False
                        continue
                    
                    required_edge_fields = ["from", "to"]
                    for field in required_edge_fields:
                        if field not in edge:
                            validation_result["errors"].append(f"Edge {i} missing '{field}' field")
                            validation_result["valid"] = False
        
        return validation_result
    
    @staticmethod
    def format_execution_time(seconds: float) -> str:
        """Format execution time in human readable format"""
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.2f} hours"

class DatabaseUtils:
    """Database utility functions"""
    
    @staticmethod
    async def create_tables():
        """Create all database tables"""
        try:
            from ..models.database_models import Base
            async with db_manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    @staticmethod
    async def drop_tables():
        """Drop all database tables"""
        try:
            from ..models.database_models import Base
            async with db_manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @staticmethod
    async def get_table_info() -> Dict[str, Any]:
        """Get database table information"""
        try:
            async with db_manager.get_session() as session:
                # Get table names
                result = await session.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = [row[0] for row in result.fetchall()]
                
                table_info = {}
                for table in tables:
                    # Get row count
                    count_result = await session.execute(f"SELECT COUNT(*) FROM {table}")
                    row_count = count_result.fetchone()[0]
                    
                    table_info[table] = {
                        "row_count": row_count,
                        "columns": []  # Would get column info in real implementation
                    }
                
                return {
                    "tables": table_info,
                    "total_tables": len(tables)
                }
                
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {"error": str(e)}

class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """Validate API key format"""
        import re
        
        # Basic API key validation (adjust regex based on your key format)
        pattern = r'^[a-zA-Z0-9]{32}$'
        return bool(re.match(pattern, api_key))
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file operations"""
        # Remove or replace dangerous characters
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*']
        sanitized = filename
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            sanitized = f"{name[:250]}.{ext}" if ext else name[:255]
        
        return sanitized
    
    @staticmethod
    def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in dictionary"""
        sensitive_keys = ['password', 'token', 'secret', 'key', 'api_key', 'auth']
        masked_data = {}
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                masked_data[key] = "***MASKED***"
            elif isinstance(value, dict):
                masked_data[key] = SecurityUtils.mask_sensitive_data(value)
            else:
                masked_data[key] = value
        
        return masked_data

class PerformanceUtils:
    """Performance monitoring utilities"""
    
    @staticmethod
    async def measure_execution_time(func, *args, **kwargs):
        """Measure execution time of a function"""
        start_time = datetime.now()
        
        try:
            result = await func(*args, **kwargs)
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "result": result,
                "execution_time_seconds": execution_time,
                "status": "success"
            }
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "error": str(e),
                "execution_time_seconds": execution_time,
                "status": "error"
            }

class CacheUtils:
    """Caching utilities"""
    
    @staticmethod
    async def get_from_cache(key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        try:
            redis_client = await db_manager.get_redis()
            value = await redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Failed to get from cache: {e}")
            return None
    
    @staticmethod
    async def set_to_cache(key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """Set value in Redis cache"""
        try:
            redis_client = await db_manager.get_redis()
            serialized_value = json.dumps(value, default=str)
            await redis_client.setex(key, expire_seconds, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set cache: {e}")
            return False
    
    @staticmethod
    async def delete_from_cache(key: str) -> bool:
        """Delete value from Redis cache"""
        try:
            redis_client = await db_manager.get_redis()
            await redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete from cache: {e}")
            return False

# Utility functions for common operations
async def cleanup_old_data(days_to_keep: int = 30) -> Dict[str, int]:
    """Clean up old data from database"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        async with db_manager.get_session() as session:
            # Clean up old workflow executions
            result = await session.execute(
                "DELETE FROM workflow_executions WHERE completed_at < ?",
                (cutoff_date.isoformat(),)
            )
            executions_deleted = result.rowcount
            
            # Clean up old audit logs
            result = await session.execute(
                "DELETE FROM audit_logs WHERE timestamp < ?",
                (cutoff_date.isoformat(),)
            )
            audit_logs_deleted = result.rowcount
            
            await session.commit()
        
        return {
            "executions_deleted": executions_deleted,
            "audit_logs_deleted": audit_logs_deleted,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        return {"error": str(e)}

def get_health_status_color(status: str) -> str:
    """Get color for health status"""
    colors = {
        "healthy": "#4CAF50",
        "degraded": "#FF9800", 
        "unhealthy": "#F44336",
        "unknown": "#9E9E9E"
    }
    return colors.get(status.lower(), colors["unknown"])

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

# Export utility functions
__all__ = [
    "LangGraphUtils",
    "DatabaseUtils", 
    "SecurityUtils",
    "PerformanceUtils",
    "CacheUtils",
    "cleanup_old_data",
    "get_health_status_color",
    "format_file_size"
]