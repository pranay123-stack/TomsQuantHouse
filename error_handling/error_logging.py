"""
Error Logging and Correlation ID Tracking
"""
import asyncio
import logging
import json
import uuid
import time
from typing import Any, Dict, Optional, List, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from contextlib import asynccontextmanager
from threading import local
from .error_types import StructuredError, ErrorContext, ErrorCategory


# Thread-local storage for correlation IDs
_thread_local = local()


@dataclass
class LogContext:
    """Extended logging context with correlation tracking"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_span_id: Optional[str] = None
    trace_flags: int = 0
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    service_name: str = "unknown"
    operation_name: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'correlation_id': self.correlation_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'trace_flags': self.trace_flags,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'request_id': self.request_id,
            'service_name': self.service_name,
            'operation_name': self.operation_name,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class CorrelationContext:
    """Manages correlation context across async operations"""
    
    def __init__(self):
        self._context_stack: List[LogContext] = []
        self._current_context: Optional[LogContext] = None
    
    def get_current_context(self) -> Optional[LogContext]:
        """Get current correlation context"""
        return getattr(_thread_local, 'correlation_context', None)
    
    def set_current_context(self, context: LogContext):
        """Set current correlation context"""
        setattr(_thread_local, 'correlation_context', context)
    
    def create_child_context(
        self,
        operation_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LogContext:
        """Create child context from current context"""
        current = self.get_current_context()
        if current:
            child = LogContext(
                correlation_id=current.correlation_id,
                span_id=str(uuid.uuid4()),
                parent_span_id=current.span_id,
                service_name=current.service_name,
                operation_name=operation_name,
                user_id=current.user_id,
                session_id=current.session_id,
                request_id=current.request_id,
                trace_flags=current.trace_flags,
                metadata=metadata or {}
            )
        else:
            child = LogContext(
                operation_name=operation_name,
                metadata=metadata or {},
                **kwargs
            )
        return child
    
    @asynccontextmanager
    async def context(self, context: LogContext):
        """Context manager for setting correlation context"""
        old_context = self.get_current_context()
        self.set_current_context(context)
        self._context_stack.append(context)
        
        try:
            yield context
        finally:
            self.set_current_context(old_context)
            if self._context_stack:
                self._context_stack.pop()


# Global correlation context manager
correlation_context = CorrelationContext()


class ErrorLogger:
    """Enhanced error logger with correlation tracking"""
    
    def __init__(
        self,
        name: str = "error_logger",
        level: int = logging.ERROR,
        format_string: Optional[str] = None,
        structured_logging: bool = True
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.structured_logging = structured_logging
        
        # Default format for structured logging
        self.format_string = format_string or (
            "%(correlation_id)s|%(levelname)s|%(name)s|%(message)s"
        )
        
        # Custom formatter for structured logging
        if structured_logging:
            self.formatter = self._StructuredFormatter()
        else:
            self.formatter = logging.Formatter(format_string)
        
        # Add console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(self.formatter)
            self.logger.addHandler(handler)
        
        # Error storage for dashboard
        self.error_storage: List[Dict[str, Any]] = []
        self.max_storage_size = 1000
    
    def _structured_record(self, level: int, message: str, 
                          error: Optional[StructuredError] = None,
                          context: Optional[LogContext] = None,
                          extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create structured log record"""
        context = context or correlation_context.get_current_context()
        extra = extra or {}
        
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': logging.getLevelName(level),
            'logger': self.logger.name,
            'message': message,
            'correlation_id': context.correlation_id if context else None,
            'span_id': context.span_id if context else None,
            'service_name': context.service_name if context else None,
            'operation_name': context.operation_name if context else None,
            'extra': extra
        }
        
        if error:
            record['error'] = {
                'message': str(error),
                'category': error.category.value,
                'severity': error.severity.value,
                'retry_policy': error.retry_policy.value,
                'original_error': str(error.original_error) if error.original_error else None,
                'cause': str(error.cause) if error.cause else None,
                'resolution_suggestions': error.resolution_suggestions,
                'context': asdict(error.context) if error.context else None
            }
        
        return record
    
    def _StructuredFormatter(logging.Formatter):
        """Custom formatter for structured logging"""
        
        def format(self, record):
            # Create structured log record
            if hasattr(record, 'structured_data'):
                log_data = record.structured_data
            else:
                log_data = {
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat()
                }
            
            return json.dumps(log_data)
    
    def log_error(
        self,
        error: StructuredError,
        message: Optional[str] = None,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Log structured error"""
        
        context = context or correlation_context.get_current_context()
        message = message or str(error)
        
        record_data = self._structured_record(
            level=logging.ERROR,
            message=message,
            error=error,
            context=context,
            extra=extra
        )
        
        # Store error for dashboard
        self._store_error(record_data)
        
        # Log the error
        if self.structured_logging:
            log_record = logging.LogRecord(
                name=self.logger.name,
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            log_record.structured_data = record_data
            
            self.logger.handle(log_record)
        else:
            self.logger.error(message, extra=record_data)
    
    def log_warning(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Log warning with context"""
        record_data = self._structured_record(
            level=logging.WARNING,
            message=message,
            context=context,
            extra=extra
        )
        
        if self.structured_logging:
            log_record = logging.LogRecord(
                name=self.logger.name,
                level=logging.WARNING,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            log_record.structured_data = record_data
            self.logger.handle(log_record)
        else:
            self.logger.warning(message, extra=record_data)
    
    def log_info(
        self,
        message: str,
        context: Optional[LogContext] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Log info with context"""
        record_data = self._structured_record(
            level=logging.INFO,
            message=message,
            context=context,
            extra=extra
        )
        
        if self.structured_logging:
            log_record = logging.LogRecord(
                name=self.logger.name,
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg=message,
                args=(),
                exc_info=None
            )
            log_record.structured_data = record_data
            self.logger.handle(log_record)
        else:
            self.logger.info(message, extra=record_data)
    
    def _store_error(self, error_record: Dict[str, Any]):
        """Store error record for dashboard access"""
        self.error_storage.append(error_record)
        
        # Maintain storage size limit
        if len(self.error_storage) > self.max_storage_size:
            self.error_storage.pop(0)
    
    def get_recent_errors(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent errors for dashboard"""
        return self.error_storage[-limit:]
    
    def get_errors_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get errors by correlation ID"""
        return [
            error for error in self.error_storage
            if error.get('correlation_id') == correlation_id
        ]
    
    def get_errors_by_category(self, category: ErrorCategory) -> List[Dict[str, Any]]:
        """Get errors by category"""
        return [
            error for error in self.error_storage
            if error.get('error', {}).get('category') == category.value
        ]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        total_errors = len(self.error_storage)
        if total_errors == 0:
            return {'total_errors': 0}
        
        # Category breakdown
        categories = {}
        severities = {}
        
        for error in self.error_storage:
            error_data = error.get('error', {})
            category = error_data.get('category', 'unknown')
            severity = error_data.get('severity', 'unknown')
            
            categories[category] = categories.get(category, 0) + 1
            severities[severity] = severities.get(severity, 0) + 1
        
        return {
            'total_errors': total_errors,
            'categories': categories,
            'severities': severities,
            'recent_errors': self.error_storage[-10:]  # Last 10 errors
        }
    
    def clear_errors(self):
        """Clear error storage"""
        self.error_storage.clear()


# Global error logger instance
global_error_logger = ErrorLogger()


class TracingLogger:
    """Logger with distributed tracing capabilities"""
    
    def __init__(self, service_name: str, error_logger: Optional[ErrorLogger] = None):
        self.service_name = service_name
        self.error_logger = error_logger or global_error_logger
        self.traces: Dict[str, List[Dict[str, Any]]] = {}
    
    async def trace_operation(
        self,
        operation_name: str,
        context: Optional[LogContext] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create tracing context for operation"""
        context = context or correlation_context.get_current_context()
        if not context:
            context = LogContext(
                service_name=self.service_name,
                operation_name=operation_name
            )
        
        return await correlation_context.context(context)
    
    def log_trace(
        self,
        operation_name: str,
        status: str,
        duration: float,
        context: Optional[LogContext] = None,
        error: Optional[Exception] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log operation trace"""
        context = context or correlation_context.get_current_context()
        
        trace_record = {
            'operation': operation_name,
            'status': status,
            'duration': duration,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'correlation_id': context.correlation_id if context else None,
            'service_name': self.service_name,
            'metadata': metadata or {}
        }
        
        if error:
            trace_record['error'] = str(error)
        
        # Store trace
        correlation_id = context.correlation_id if context else 'unknown'
        if correlation_id not in self.traces:
            self.traces[correlation_id] = []
        
        self.traces[correlation_id].append(trace_record)
    
    def get_trace(self, correlation_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get trace by correlation ID"""
        return self.traces.get(correlation_id)
    
    def get_all_traces(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all traces"""
        return self.traces.copy()


# Global tracing logger
tracing_logger = TracingLogger("default")


# Decorators for automatic logging and tracing
def with_logging(
    error_logger: Optional[ErrorLogger] = None,
    tracing_logger: Optional[TracingLogger] = None,
    log_level: int = logging.INFO
):
    """Decorator for automatic error logging and tracing"""
    def decorator(func):
        error_log = error_logger or global_error_logger
        trace_log = tracing_logger or tracing_logger
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                context = correlation_context.get_current_context()
                operation_name = f"{func.__name__}"
                
                start_time = time.time()
                
                try:
                    async with correlation_context.context(LogContext(
                        service_name="unknown",
                        operation_name=operation_name
                    )):
                        result = await func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    trace_log.log_trace(operation_name, "success", duration)
                    
                    if log_level <= logging.DEBUG:
                        error_log.log_info(
                            f"Operation {operation_name} completed successfully",
                            extra={'duration': duration}
                        )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    trace_log.log_trace(operation_name, "error", duration, error=e)
                    
                    # Convert to structured error
                    structured_error = create_error_from_exception(
                        e, context=context
                    )
                    
                    error_log.log_error(structured_error)
                    raise
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                context = correlation_context.get_current_context()
                operation_name = f"{func.__name__}"
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    duration = time.time() - start_time
                    trace_log.log_trace(operation_name, "success", duration)
                    
                    if log_level <= logging.DEBUG:
                        error_log.log_info(
                            f"Operation {operation_name} completed successfully",
                            extra={'duration': duration}
                        )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    trace_log.log_trace(operation_name, "error", duration, error=e)
                    
                    # Convert to structured error
                    structured_error = create_error_from_exception(
                        e, context=context
                    )
                    
                    error_log.log_error(structured_error)
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


# Context managers for manual correlation tracking
@asynccontextmanager
async def error_context(
    correlation_id: Optional[str] = None,
    operation_name: str = "unknown",
    service_name: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None
):
    """Create error context for correlation tracking"""
    context = LogContext(
        correlation_id=correlation_id or str(uuid.uuid4()),
        service_name=service_name,
        operation_name=operation_name,
        metadata=metadata or {}
    )
    
    async with correlation_context.context(context):
        yield context


# Helper functions for correlation ID propagation
def extract_correlation_id(headers: Dict[str, str]) -> Optional[str]:
    """Extract correlation ID from HTTP headers"""
    # Check common correlation ID header names
    correlation_headers = [
        'x-correlation-id',
        'x-request-id',
        'x-trace-id',
        'x-transaction-id',
        'correlation-id'
    ]
    
    for header_name in correlation_headers:
        if header_name.lower() in headers:
            return headers[header_name.lower()]
    
    return None


def inject_correlation_id(headers: Dict[str, str], correlation_id: str) -> Dict[str, str]:
    """Inject correlation ID into HTTP headers"""
    headers = headers.copy()
    headers['x-correlation-id'] = correlation_id
    return headers


# Function to create structured error from exception
def create_error_from_exception(
    exc: Exception,
    context: Optional[LogContext] = None,
    custom_message: Optional[str] = None
) -> StructuredError:
    """Factory function to create appropriate error from exception"""
    from .error_types import (
        NetworkError, DatabaseError, APIError, ValidationError, 
        TimeoutError, RateLimitError, SystemError, ErrorCategory
    )
    
    context = context or correlation_context.get_current_context()
    
    # Map common exception types to structured errors
    if isinstance(exc, ConnectionError):
        return NetworkError(
            custom_message or "Connection failed",
            context=context,
            original_error=exc
        )
    elif isinstance(exc, TimeoutError):
        return TimeoutError(
            custom_message or "Operation timed out",
            context=context,
            original_error=exc
        )
    elif isinstance(exc, ValueError):
        return ValidationError(
            custom_message or str(exc),
            context=context,
            original_error=exc
        )
    else:
        # Default to system error for unclassified exceptions
        return SystemError(
            custom_message or f"Unexpected error: {str(exc)}",
            context=context,
            original_error=exc
        )