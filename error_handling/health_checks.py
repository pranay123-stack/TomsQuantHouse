"""
Health Checks with Automated Recovery
"""
import asyncio
import time
import logging
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from .error_types import StructuredError, ErrorContext
from .retry_mechanism import RetryManager, RetryConfig


class HealthStatus(Enum):
    """Health check status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckType(Enum):
    """Types of health checks"""
    HTTP = "http"                    # HTTP endpoint check
    DATABASE = "database"            # Database connectivity
    EXTERNAL_SERVICE = "external_service"  # External service check
    CUSTOM = "custom"                # Custom check function
    RESOURCE = "resource"            # System resource check
    DEPENDENCY = "dependency"        # Dependency service check


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime
    response_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if health status is healthy"""
        return self.status == HealthStatus.HEALTHY
    
    @property
    def is_degraded(self) -> bool:
        """Check if health status is degraded"""
        return self.status == HealthStatus.DEGRADED
    
    @property
    def is_unhealthy(self) -> bool:
        """Check if health status is unhealthy"""
        return self.status == HealthStatus.UNHEALTHY


@dataclass
class HealthCheckConfig:
    """Configuration for health checks"""
    timeout: float = 10.0
    interval: float = 30.0  # Check interval in seconds
    retries: int = 3
    retry_delay: float = 5.0
    failure_threshold: int = 3  # Consecutive failures before marking unhealthy
    recovery_threshold: int = 2  # Consecutive successes before marking healthy
    dependencies: List[str] = field(default_factory=list)
    critical: bool = True  # Whether this check is critical
    metadata: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """Base class for health checks"""
    
    def __init__(self, name: str, config: Optional[HealthCheckConfig] = None):
        self.name = name
        self.config = config or HealthCheckConfig()
        self.logger = logging.getLogger(f"health_check.{name}")
        
        # State tracking
        self._last_check: Optional[HealthCheckResult] = None
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._status = HealthStatus.UNKNOWN
        self._last_status_change = time.time()
        
        # Recovery actions
        self._recovery_actions: List[Callable] = []
    
    async def check(self) -> HealthCheckResult:
        """Perform health check"""
        start_time = time.time()
        
        try:
            result = await self._perform_check()
            response_time = time.time() - start_time
            
            result.response_time = response_time
            result.timestamp = datetime.utcnow()
            
            self._last_check = result
            self._update_status(result)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            result = HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                response_time=response_time,
                error=e
            )
            
            self._last_check = result
            self._update_status(result)
            
            return result
    
    async def _perform_check(self) -> HealthCheckResult:
        """Override this method to implement specific health check logic"""
        raise NotImplementedError("Subclasses must implement _perform_check")
    
    def _update_status(self, result: HealthCheckResult):
        """Update health check status based on result"""
        old_status = self._status
        
        if result.is_healthy:
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            
            if (self._status == HealthStatus.UNHEALTHY and 
                self._consecutive_successes >= self.config.recovery_threshold):
                self._status = HealthStatus.HEALTHY
                self._consecutive_successes = 0
                self._last_status_change = time.time()
                self.logger.info(f"Health check '{self.name}' recovered to HEALTHY")
        
        elif result.is_unhealthy:
            self._consecutive_successes = 0
            self._consecutive_failures += 1
            
            if (self._status != HealthStatus.UNHEALTHY and 
                self._consecutive_failures >= self.config.failure_threshold):
                self._status = HealthStatus.UNHEALTHY
                self._last_status_change = time.time()
                self.logger.warning(f"Health check '{self.name}' marked as UNHEALTHY")
                
                # Trigger recovery actions if unhealthy
                if self.config.critical:
                    asyncio.create_task(self._trigger_recovery_actions())
    
    async def _trigger_recovery_actions(self):
        """Trigger recovery actions for unhealthy state"""
        for action in self._recovery_actions:
            try:
                if asyncio.iscoroutinefunction(action):
                    await action(self)
                else:
                    action(self)
                self.logger.info(f"Recovery action executed for '{self.name}'")
            except Exception as e:
                self.logger.error(f"Recovery action failed for '{self.name}': {e}")
    
    def add_recovery_action(self, action: Callable):
        """Add recovery action for when health check fails"""
        self._recovery_actions.append(action)
    
    def get_status(self) -> HealthStatus:
        """Get current health status"""
        return self._status
    
    def get_last_check(self) -> Optional[HealthCheckResult]:
        """Get last health check result"""
        return self._last_check
    
    def get_info(self) -> Dict[str, Any]:
        """Get health check information"""
        return {
            'name': self.name,
            'status': self._status.value,
            'last_check': asdict(self._last_check) if self._last_check else None,
            'consecutive_failures': self._consecutive_failures,
            'consecutive_successes': self._consecutive_successes,
            'last_status_change': self._last_status_change,
            'config': asdict(self.config)
        }


class HTTPHealthChecker(HealthChecker):
    """HTTP endpoint health checker"""
    
    def __init__(
        self,
        name: str,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        expected_status: Optional[List[int]] = None,
        config: Optional[HealthCheckConfig] = None
    ):
        super().__init__(name, config)
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.expected_status = expected_status or [200, 201, 202]
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform HTTP health check"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as session:
                async with session.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers
                ) as response:
                    if response.status in self.expected_status:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.HEALTHY,
                            message=f"HTTP {response.status} - Service is healthy",
                            timestamp=datetime.utcnow(),
                            details={'status_code': response.status}
                        )
                    else:
                        return HealthCheckResult(
                            name=self.name,
                            status=HealthStatus.UNHEALTHY,
                            message=f"HTTP {response.status} - Unexpected status",
                            timestamp=datetime.utcnow(),
                            details={'status_code': response.status}
                        )
                        
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                error=e
            )


class DatabaseHealthChecker(HealthChecker):
    """Database connectivity health checker"""
    
    def __init__(
        self,
        name: str,
        connection_func: Callable[[], Any],
        query: str = "SELECT 1",
        config: Optional[HealthCheckConfig] = None
    ):
        super().__init__(name, config)
        self.connection_func = connection_func
        self.query = query
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform database health check"""
        try:
            connection = self.connection_func()
            
            if asyncio.iscoroutinefunction(connection.execute):
                result = await connection.execute(self.query)
            else:
                result = await asyncio.to_thread(connection.execute, self.query)
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.HEALTHY,
                message="Database connection is healthy",
                timestamp=datetime.utcnow(),
                details={'query': self.query, 'result': str(result)}
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                error=e
            )


class CustomHealthChecker(HealthChecker):
    """Custom health checker with user-provided function"""
    
    def __init__(
        self,
        name: str,
        check_func: Callable[[], Union[HealthCheckResult, Awaitable[HealthCheckResult]]],
        config: Optional[HealthCheckConfig] = None
    ):
        super().__init__(name, config)
        self.check_func = check_func
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform custom health check"""
        try:
            if asyncio.iscoroutinefunction(self.check_func):
                result = await self.check_func()
            else:
                result = await asyncio.to_thread(self.check_func)
            
            # Ensure result is a HealthCheckResult
            if isinstance(result, HealthCheckResult):
                result.name = self.name
                return result
            else:
                # Assume result is a boolean indicating health
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                return HealthCheckResult(
                    name=self.name,
                    status=status,
                    message="Custom check completed",
                    timestamp=datetime.utcnow()
                )
                
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Custom check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                error=e
            )


class ResourceHealthChecker(HealthChecker):
    """System resource health checker"""
    
    def __init__(
        self,
        name: str,
        memory_threshold: float = 0.85,  # 85% memory usage threshold
        disk_threshold: float = 0.90,    # 90% disk usage threshold
        cpu_threshold: float = 0.80,     # 80% CPU usage threshold
        config: Optional[HealthCheckConfig] = None
    ):
        super().__init__(name, config)
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
        self.cpu_threshold = cpu_threshold
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform resource health check"""
        try:
            import psutil
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent / 100.0
            
            # Check disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent / 100.0
            
            # Check CPU usage (average over 1 second)
            cpu_percent = psutil.cpu_percent(interval=1) / 100.0
            
            issues = []
            status = HealthStatus.HEALTHY
            
            if memory_percent > self.memory_threshold:
                issues.append(f"Memory usage ({memory_percent:.1%}) exceeds threshold ({self.memory_threshold:.1%})")
                status = HealthStatus.DEGRADED
            
            if disk_percent > self.disk_threshold:
                issues.append(f"Disk usage ({disk_percent:.1%}) exceeds threshold ({self.disk_threshold:.1%})")
                status = HealthStatus.DEGRADED
            
            if cpu_percent > self.cpu_threshold:
                issues.append(f"CPU usage ({cpu_percent:.1%}) exceeds threshold ({self.cpu_threshold:.1%})")
                status = HealthStatus.DEGRADED
            
            message = "Resource check passed"
            if issues:
                message = f"Resource issues detected: {', '.join(issues)}"
                if memory_percent > 0.95 or disk_percent > 0.95:
                    status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                timestamp=datetime.utcnow(),
                details={
                    'memory_percent': memory_percent,
                    'disk_percent': disk_percent,
                    'cpu_percent': cpu_percent,
                    'thresholds': {
                        'memory': self.memory_threshold,
                        'disk': self.disk_threshold,
                        'cpu': self.cpu_threshold
                    }
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Resource check failed: {str(e)}",
                timestamp=datetime.utcnow(),
                error=e
            )


class HealthCheckManager:
    """Manages multiple health checks with automated monitoring"""
    
    def __init__(self, config: Optional[HealthCheckConfig] = None):
        self.config = config
        self.checkers: Dict[str, HealthChecker] = {}
        self.logger = logging.getLogger("health_check.manager")
        
        # Monitoring
        self._monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Health history
        self._health_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
    
    def add_checker(self, checker: HealthChecker):
        """Add health checker"""
        self.checkers[checker.name] = checker
        self.logger.info(f"Added health checker: {checker.name}")
    
    def remove_checker(self, name: str):
        """Remove health checker"""
        if name in self.checkers:
            del self.checkers[name]
            self.logger.info(f"Removed health checker: {name}")
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """Run all health checks"""
        results = {}
        
        for name, checker in self.checkers.items():
            try:
                results[name] = await checker.check()
            except Exception as e:
                self.logger.error(f"Health check '{name}' failed with exception: {e}")
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check exception: {str(e)}",
                    timestamp=datetime.utcnow(),
                    error=e
                )
        
        # Store health history
        health_snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'results': {name: result.status.value for name, result in results.items()},
            'overall_status': self._get_overall_status(results).value
        }
        self._health_history.append(health_snapshot)
        
        # Maintain history size
        if len(self._health_history) > self._max_history_size:
            self._health_history.pop(0)
        
        return results
    
    def _get_overall_status(self, results: Dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall system health status"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results.values()]
        
        # If any critical checker is unhealthy, overall is unhealthy
        critical_unhealthy = any(
            result.status == HealthStatus.UNHEALTHY and checker.config.critical
            for name, result in results.items()
            for checker in [self.checkers[name]]
        )
        
        if critical_unhealthy:
            return HealthStatus.UNHEALTHY
        
        # If any checker is unhealthy (non-critical), overall is degraded
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.DEGRADED
        
        # If any checker is degraded, overall is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        # All checks are healthy
        return HealthStatus.HEALTHY
    
    def get_overall_status(self) -> HealthStatus:
        """Get overall system health status"""
        if not self.checkers:
            return HealthStatus.UNKNOWN
        
        # Get latest results
        latest_results = {}
        for name, checker in self.checkers.items():
            if checker.get_last_check():
                latest_results[name] = checker.get_last_check()
        
        return self._get_overall_status(latest_results)
    
    async def start_monitoring(self, interval: Optional[float] = None):
        """Start automated health monitoring"""
        if self._monitoring_active:
            self.logger.warning("Health monitoring is already active")
            return
        
        self._monitoring_active = True
        interval = interval or self.config.interval if self.config else 30.0
        
        self._monitor_task = asyncio.create_task(self._monitor_health(interval))
        self.logger.info(f"Started health monitoring with interval: {interval}s")
    
    async def stop_monitoring(self):
        """Stop automated health monitoring"""
        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped health monitoring")
    
    async def _monitor_health(self, interval: float):
        """Internal health monitoring loop"""
        while self._monitoring_active:
            try:
                results = await self.check_all()
                overall_status = self._get_overall_status(results)
                
                # Log status changes
                for name, result in results.items():
                    if result.is_unhealthy:
                        self.logger.warning(f"Health check '{name}' is UNHEALTHY: {result.message}")
                    elif result.is_degraded:
                        self.logger.info(f"Health check '{name}' is DEGRADED: {result.message}")
                
                # Check if overall status changed to unhealthy
                if overall_status == HealthStatus.UNHEALTHY:
                    self.logger.error(f"System health is UNHEALTHY")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def get_health_dashboard_data(self) -> Dict[str, Any]:
        """Get data for health dashboard"""
        results = {}
        for name, checker in self.checkers.items():
            results[name] = {
                'status': checker.get_status().value,
                'last_check': checker.get_last_check().to_dict() if checker.get_last_check() else None,
                'info': checker.get_info()
            }
        
        return {
            'overall_status': self.get_overall_status().value,
            'checkers': results,
            'recent_history': self._health_history[-50:],  # Last 50 entries
            'total_checks': len(self.checkers)
        }
    
    def get_recovery_actions(self) -> List[Dict[str, Any]]:
        """Get list of recovery actions for unhealthy checkers"""
        actions = []
        for name, checker in self.checkers.items():
            if checker.get_status() == HealthStatus.UNHEALTHY:
                actions.append({
                    'checker': name,
                    'recovery_actions': len(checker._recovery_actions),
                    'critical': checker.config.critical
                })
        return actions


# Default health check manager
default_health_manager = HealthCheckManager()


# Decorator for health check integration
def health_checkable(
    check_type: CheckType,
    name: Optional[str] = None,
    config: Optional[HealthCheckConfig] = None,
    health_manager: Optional[HealthCheckManager] = None
):
    """Decorator to make function health-checkable"""
    def decorator(func):
        checker_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Create custom health checker for this function
            async def check_func():
                try:
                    result = await func(*args, **kwargs)
                    return HealthCheckResult(
                        name=checker_name,
                        status=HealthStatus.HEALTHY,
                        message="Function executed successfully",
                        timestamp=datetime.utcnow()
                    )
                except Exception as e:
                    return HealthCheckResult(
                        name=checker_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Function failed: {str(e)}",
                        timestamp=datetime.utcnow(),
                        error=e
                    )
            
            checker = CustomHealthChecker(checker_name, check_func, config)
            
            # Add to health manager
            hm = health_manager or default_health_manager
            hm.add_checker(checker)
            
            # Execute function
            return await func(*args, **kwargs)
        
        return async_wrapper
    return decorator


# Helper functions
def asdict(obj):
    """Convert dataclass to dictionary"""
    if hasattr(obj, '__dataclass_fields__'):
        return {field.name: getattr(obj, field.name) for field in obj.__dataclass_fields__.values()}
    return obj.__dict__


# Common recovery actions
def restart_service_action(service_name: str):
    """Recovery action to restart a service"""
    async def action(checker: HealthChecker):
        # This would be implemented based on the service management system
        checker.logger.info(f"Would restart service: {service_name}")
        # Example: await restart_service(service_name)
    return action


def clear_cache_action(cache_name: str):
    """Recovery action to clear cache"""
    async def action(checker: HealthChecker):
        checker.logger.info(f"Would clear cache: {cache_name}")
        # Example: await clear_cache(cache_name)
    return action


def scale_service_action(service_name: str, scale_factor: int):
    """Recovery action to scale service"""
    async def action(checker: HealthChecker):
        checker.logger.info(f"Would scale service {service_name} by factor {scale_factor}")
        # Example: await scale_service(service_name, scale_factor)
    return action