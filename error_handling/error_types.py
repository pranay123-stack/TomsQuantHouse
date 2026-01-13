"""
Structured Error Types for Centralized Error Handling
"""
from enum import Enum
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    DATABASE = "database"
    API = "api"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    CONFIGURATION = "configuration"
    EXTERNAL_SERVICE = "external_service"


class ErrorRetryPolicy(Enum):
    """Retry policy types"""
    NO_RETRY = "no_retry"
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    CUSTOM = "custom"


@dataclass
class ErrorContext:
    """Context information for error tracking"""
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    service_name: str = "unknown"
    operation_name: str = "unknown"
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    error_code: Optional[str] = None


@dataclass
class StructuredError:
    """Structured error representation"""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    retry_policy: ErrorRetryPolicy
    context: ErrorContext
    original_error: Optional[Exception] = None
    cause: Optional['StructuredError'] = None
    resolution_suggestions: List[str] = field(default_factory=list)
    escalate: bool = False
    
    def __str__(self) -> str:
        return f"[{self.category.value.upper()}] {self.message}"


class BaseError(StructuredError):
    """Base error class with common functionality"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retry_policy: ErrorRetryPolicy = ErrorRetryPolicy.NO_RETRY,
        context: Optional[ErrorContext] = None,
        original_error: Optional[Exception] = None,
        resolution_suggestions: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            category=category,
            severity=severity,
            retry_policy=retry_policy,
            context=context or ErrorContext(),
            original_error=original_error,
            resolution_suggestions=resolution_suggestions or []
        )


class NetworkError(BaseError):
    """Network-related errors"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None, 
                 original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            retry_policy=ErrorRetryPolicy.EXPONENTIAL_BACKOFF,
            context=context,
            original_error=original_error,
            resolution_suggestions=[
                "Check network connectivity",
                "Verify firewall settings",
                "Check DNS resolution",
                "Verify SSL/TLS certificates"
            ]
        )


class DatabaseError(BaseError):
    """Database-related errors"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            retry_policy=ErrorRetryPolicy.EXPONENTIAL_BACKOFF,
            context=context,
            original_error=original_error,
            resolution_suggestions=[
                "Check database connection",
                "Verify database credentials",
                "Check database server status",
                "Verify query syntax"
            ]
        )


class APIError(BaseError):
    """API-related errors"""
    
    def __init__(self, message: str, status_code: Optional[int] = None,
                 context: Optional[ErrorContext] = None,
                 original_error: Optional[Exception] = None):
        severity = ErrorSeverity.HIGH if status_code >= 500 else ErrorSeverity.MEDIUM
        retry_policy = ErrorRetryPolicy.EXPONENTIAL_BACKOFF if status_code >= 500 else ErrorRetryPolicy.NO_RETRY
        
        super().__init__(
            message=message,
            category=ErrorCategory.API,
            severity=severity,
            retry_policy=retry_policy,
            context=context,
            original_error=original_error,
            resolution_suggestions=[
                "Check API endpoint URL",
                "Verify API key or authentication",
                "Check rate limits",
                "Review API documentation"
            ]
        )


class ValidationError(BaseError):
    """Validation errors"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            retry_policy=ErrorRetryPolicy.NO_RETRY,
            context=context,
            original_error=original_error,
            resolution_suggestions=[
                "Review input data format",
                "Check required fields",
                "Verify data types",
                "Review validation rules"
            ]
        )


class TimeoutError(BaseError):
    """Timeout errors"""
    
    def __init__(self, message: str, timeout_duration: Optional[float] = None,
                 context: Optional[ErrorContext] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.TIMEOUT,
            severity=ErrorSeverity.MEDIUM,
            retry_policy=ErrorRetryPolicy.EXPONENTIAL_BACKOFF,
            context=context,
            original_error=original_error,
            resolution_suggestions=[
                "Increase timeout duration",
                "Check system performance",
                "Optimize slow operations",
                "Consider async operations"
            ]
        )


class RateLimitError(BaseError):
    """Rate limit errors"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None,
                 context: Optional[ErrorContext] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.MEDIUM,
            retry_policy=ErrorRetryPolicy.LINEAR_BACKOFF,
            context=context,
            original_error=original_error,
            resolution_suggestions=[
                "Implement exponential backoff",
                "Use request queuing",
                "Implement rate limiting",
                "Consider service scaling"
            ]
        )


class SystemError(BaseError):
    """System-level errors"""
    
    def __init__(self, message: str, context: Optional[ErrorContext] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.CRITICAL,
            retry_policy=ErrorRetryPolicy.NO_RETRY,
            context=context,
            original_error=original_error,
            resolution_suggestions=[
                "Check system resources",
                "Review application logs",
                "Verify configuration",
                "Contact system administrator"
            ],
            escalate=True
        )


# Error factory functions
def create_error_from_exception(
    exc: Exception,
    context: Optional[ErrorContext] = None,
    custom_message: Optional[str] = None
) -> StructuredError:
    """Factory function to create appropriate error from exception"""
    
    context = context or ErrorContext()
    
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


# Decorator for error context enrichment
def with_error_context(**context_kwargs):
    """Decorator to enrich error context"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            # Update context with provided kwargs
            context = ErrorContext(**context_kwargs)
            # This would need to be integrated with the error handling system
            return func(*args, **kwargs)
        return wrapper
    return decorator