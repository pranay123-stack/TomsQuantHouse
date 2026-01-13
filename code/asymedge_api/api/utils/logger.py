"""
ASYMEdge Dashboard API - Logging Configuration

Centralized logging setup providing:
- Structured logging with JSON format
- Log level configuration
- File and console output
- Log rotation and retention
- Error tracking and alerting
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import os

from api.config import settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        # Create base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        
        return json.dumps(log_entry, default=str)

class ColoredConsoleFormatter(logging.Formatter):
    """Colored console formatter for development"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to level name
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        record.levelname = f"{color}{record.levelname}{reset}"
        
        # Format the message
        formatted = super().format(record)
        return formatted

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Set up logger with proper configuration"""
    
    # Get log level
    log_level = level or settings.LOG_LEVEL.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if settings.is_production():
        # JSON formatter for production
        console_formatter = JSONFormatter()
    else:
        # Colored formatter for development
        console_formatter = ColoredConsoleFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler for errors (if log file is specified)
    if settings.LOG_FILE:
        # Ensure log directory exists
        log_file_path = Path(settings.LOG_FILE)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.WARNING)  # Only log warnings and errors to file
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
    
    # Prevent propagation to avoid duplicate logs
    logger.propagate = False
    
    return logger

def get_request_logger(request_id: str, user_id: Optional[int] = None) -> logging.LoggerAdapter:
    """Get logger with request context"""
    logger = logging.getLogger("api.requests")
    
    extra = {
        "request_id": request_id,
        "user_id": user_id
    }
    
    return logging.LoggerAdapter(logger, extra)

def log_api_request(logger: logging.Logger, method: str, path: str, 
                   status_code: int, response_time: float, user_id: Optional[int] = None):
    """Log API request details"""
    logger.info(
        "API Request",
        extra={
            "type": "api_request",
            "method": method,
            "path": path,
            "status_code": status_code,
            "response_time_ms": round(response_time * 1000, 2),
            "user_id": user_id
        }
    )

def log_db_operation(logger: logging.Logger, operation: str, table: str, 
                    duration: float, success: bool, rows_affected: Optional[int] = None):
    """Log database operation details"""
    logger.info(
        "Database Operation",
        extra={
            "type": "db_operation",
            "operation": operation,
            "table": table,
            "duration_ms": round(duration * 1000, 2),
            "success": success,
            "rows_affected": rows_affected
        }
    )

def log_external_api_call(logger: logging.Logger, service: str, endpoint: str,
                         duration: float, status_code: Optional[int] = None,
                         error: Optional[str] = None):
    """Log external API call details"""
    logger.info(
        "External API Call",
        extra={
            "type": "external_api",
            "service": service,
            "endpoint": endpoint,
            "duration_ms": round(duration * 1000, 2),
            "status_code": status_code,
            "error": error
        }
    )

def log_agent_activity(logger: logging.Logger, agent_id: int, activity: str,
                      status: str, user_id: Optional[int] = None,
                      details: Optional[Dict[str, Any]] = None):
    """Log agent activity"""
    logger.info(
        "Agent Activity",
        extra={
            "type": "agent_activity",
            "agent_id": agent_id,
            "activity": activity,
            "status": status,
            "user_id": user_id,
            "details": details or {}
        }
    )

def log_workflow_event(logger: logging.Logger, workflow_id: int, event: str,
                      status: str, user_id: Optional[int] = None,
                      details: Optional[Dict[str, Any]] = None):
    """Log workflow events"""
    logger.info(
        "Workflow Event",
        extra={
            "type": "workflow_event",
            "workflow_id": workflow_id,
            "event": event,
            "status": status,
            "user_id": user_id,
            "details": details or {}
        }
    )

def setup_loguru_logger():
    """Setup advanced logging with loguru (optional, for enhanced logging)"""
    try:
        from loguru import logger as loguru_logger
        
        # Remove default handler
        loguru_logger.remove()
        
        # Console output
        if settings.is_production():
            loguru_logger.add(
                sys.stdout,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
                level=settings.LOG_LEVEL,
                serialize=True  # JSON output
            )
        else:
            loguru_logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
                level=settings.LOG_LEVEL,
                colorize=True
            )
        
        # File output
        if settings.LOG_FILE:
            log_file_path = Path(settings.LOG_FILE)
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            loguru_logger.add(
                settings.LOG_FILE,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
                level="WARNING",
                rotation="10 MB",
                retention="5 files",
                compression="gz",
                serialize=True
            )
        
        return loguru_logger
        
    except ImportError:
        # Fallback to standard logging if loguru not available
        return None

# Create application loggers
api_logger = setup_logger("asymedge_api")
db_logger = setup_logger("asymedge_db")
auth_logger = setup_logger("asymedge_auth")
agent_logger = setup_logger("asymedge_agents")
workflow_logger = setup_logger("asymedge_workflows")
trading_logger = setup_logger("asymedge_trading")
stream_logger = setup_logger("asymedge_streaming")

# Initialize loguru if available
loguru = setup_loguru_logger()

# Export loggers
__all__ = [
    "setup_logger",
    "get_request_logger", 
    "log_api_request",
    "log_db_operation",
    "log_external_api_call",
    "log_agent_activity",
    "log_workflow_event",
    "setup_loguru_logger",
    "api_logger",
    "db_logger", 
    "auth_logger",
    "agent_logger",
    "workflow_logger",
    "trading_logger",
    "stream_logger",
    "loguru"
]