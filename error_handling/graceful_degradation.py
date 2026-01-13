"""
Graceful Degradation for Critical System Failures
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from .error_types import StructuredError, ErrorCategory, ErrorSeverity
from .health_checks import HealthCheckManager, HealthStatus


class DegradationLevel(Enum):
    """Service degradation levels"""
    FULL_FUNCTION = "full_function"      # All services operational
    REDUCED_CAPACITY = "reduced_capacity"  # Some capacity reduced
    LIMITED_FEATURES = "limited_features"  # Non-essential features disabled
    ESSENTIAL_ONLY = "essential_only"      # Only essential functions
    EMERGENCY_MODE = "emergency_mode"      # Minimal functionality


class ServiceTier(Enum):
    """Service tiers for degradation"""
    CRITICAL = "critical"      # Must always be available
    IMPORTANT = "important"    # Should be available most of the time
    ENHANCED = "enhanced"      # Nice to have features
    LUXURY = "luxury"          # Non-essential features


@dataclass
class ServiceInfo:
    """Information about a service"""
    name: str
    tier: ServiceTier
    health_checker: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    weight: float = 1.0  # For capacity calculation
    description: str = ""
    fallback_enabled: bool = True


@dataclass
class DegradationRule:
    """Rule for degradation decisions"""
    trigger_condition: str  # e.g., "error_rate > 0.1" or "health_status == UNHEALTHY"
    target_level: DegradationLevel
    services_to_disable: List[str] = field(default_factory=list)
    capacity_reduction: float = 0.0  # 0.0 = no reduction, 1.0 = full reduction
    timeout_minutes: Optional[float] = None  # Auto-recovery timeout
    
    def should_trigger(self, metrics: Dict[str, Any]) -> bool:
        """Check if degradation rule should trigger"""
        try:
            # Simple condition evaluation (in production, use proper expression parser)
            condition = self.trigger_condition
            return eval(condition, {}, metrics)
        except Exception:
            return False


class GracefulDegradationManager:
    """Manages graceful degradation of services"""
    
    def __init__(self, health_manager: Optional[HealthCheckManager] = None):
        self.health_manager = health_manager
        self.logger = logging.getLogger("graceful_degradation")
        
        # Service registry
        self.services: Dict[str, ServiceInfo] = {}
        self.current_level = DegradationLevel.FULL_FUNCTION
        
        # Degradation rules
        self.degradation_rules: List[DegradationRule] = []
        
        # State tracking
        self._degradation_history: List[Dict[str, Any]] = []
        self._auto_recovery_tasks: Dict[str, asyncio.Task] = {}
        self._service_states: Dict[str, bool] = {}  # enabled/disabled
        
        # Configuration
        self.auto_recovery_enabled = True
        self.max_degradation_duration = timedelta(hours=2)
        self.recovery_check_interval = 30  # seconds
        
        # Degradation level configurations
        self._level_configs = {
            DegradationLevel.FULL_FUNCTION: {
                'enabled_services': 'all',
                'capacity': 1.0,
                'features': 'all'
            },
            DegradationLevel.REDUCED_CAPACITY: {
                'enabled_services': [ServiceTier.CRITICAL, ServiceTier.IMPORTANT],
                'capacity': 0.7,
                'features': 'standard'
            },
            DegradationLevel.LIMITED_FEATURES: {
                'enabled_services': [ServiceTier.CRITICAL],
                'capacity': 0.5,
                'features': 'essential'
            },
            DegradationLevel.ESSENTIAL_ONLY: {
                'enabled_services': [ServiceTier.CRITICAL],
                'capacity': 0.3,
                'features': 'minimal'
            },
            DegradationLevel.EMERGENCY_MODE: {
                'enabled_services': [ServiceTier.CRITICAL],
                'capacity': 0.1,
                'features': 'emergency'
            }
        }
    
    def register_service(self, service_info: ServiceInfo):
        """Register a service for degradation management"""
        self.services[service_info.name] = service_info
        self._service_states[service_info.name] = True
        self.logger.info(f"Registered service: {service_info.name} (tier: {service_info.tier.value})")
    
    def add_degradation_rule(self, rule: DegradationRule):
        """Add a degradation rule"""
        self.degradation_rules.append(rule)
        self.logger.info(f"Added degradation rule: {rule.trigger_condition} -> {rule.target_level.value}")
    
    async def evaluate_degradation(self, metrics: Dict[str, Any]) -> Optional[DegradationLevel]:
        """Evaluate if degradation should occur based on current metrics"""
        for rule in self.degradation_rules:
            if rule.should_trigger(metrics):
                self.logger.warning(f"Degradation rule triggered: {rule.trigger_condition}")
                return rule.target_level
        
        return None
    
    async def apply_degradation(self, target_level: DegradationLevel, reason: str = ""):
        """Apply degradation level"""
        if target_level == self.current_level:
            return
        
        old_level = self.current_level
        self.current_level = target_level
        
        self.logger.warning(
            f"Applying degradation: {old_level.value} -> {target_level.value}. Reason: {reason}"
        )
        
        # Update service states
        await self._update_service_states(target_level)
        
        # Record degradation
        self._record_degradation_event(old_level, target_level, reason)
        
        # Setup auto-recovery if enabled
        if self.auto_recovery_enabled:
            await self._setup_auto_recovery(target_level)
    
    async def _update_service_states(self, level: DegradationLevel):
        """Update service states based on degradation level"""
        config = self._level_configs[level]
        enabled_tiers = config['enabled_services']
        
        for service_name, service_info in self.services.items():
            should_enable = (
                enabled_tiers == 'all' or 
                service_info.tier in enabled_tiers or
                (isinstance(enabled_tiers, list) and service_info.tier.value in [t.value for t in enabled_tiers])
            )
            
            # Check dependencies
            if should_enable and service_info.dependencies:
                should_enable = all(
                    self._service_states.get(dep, True) 
                    for dep in service_info.dependencies
                )
            
            old_state = self._service_states.get(service_name, False)
            self._service_states[service_name] = should_enable
            
            if old_state != should_enable:
                status = "enabled" if should_enable else "disabled"
                self.logger.info(f"Service '{service_name}' {status} at degradation level {level.value}")
    
    def _record_degradation_event(
        self,
        old_level: DegradationLevel,
        new_level: DegradationLevel,
        reason: str
    ):
        """Record degradation event in history"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'old_level': old_level.value,
            'new_level': new_level.value,
            'reason': reason,
            'services_enabled': {
                name: enabled for name, enabled in self._service_states.items()
            }
        }
        
        self._degradation_history.append(event)
        
        # Keep only recent history
        if len(self._degradation_history) > 100:
            self._degradation_history.pop(0)
    
    async def _setup_auto_recovery(self, level: DegradationLevel):
        """Setup automatic recovery from degradation"""
        # Find rules that could trigger recovery
        recovery_rules = [r for r in self.degradation_rules if r.target_level == level]
        
        for rule in recovery_rules:
            if rule.timeout_minutes:
                task = asyncio.create_task(
                    self._auto_recovery_task(rule, level, rule.timeout_minutes)
                )
                self._auto_recovery_tasks[rule.trigger_condition] = task
    
    async def _auto_recovery_task(self, rule: DegradationRule, level: DegradationLevel, timeout_minutes: float):
        """Auto-recovery task"""
        try:
            await asyncio.sleep(timeout_minutes * 60)
            
            # Check if conditions have improved
            metrics = await self._collect_metrics()
            if not rule.should_trigger(metrics):
                await self.apply_degradation(DegradationLevel.FULL_FUNCTION, "Auto-recovery timeout")
                self.logger.info(f"Auto-recovery successful for level {level.value}")
            else:
                self.logger.warning(f"Auto-recovery conditions not met for level {level.value}")
                
        except asyncio.CancelledError:
            pass
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics for evaluation"""
        metrics = {}
        
        # Health metrics
        if self.health_manager:
            health_data = self.health_manager.get_health_dashboard_data()
            metrics['overall_health_status'] = health_data.get('overall_status', 'unknown')
            metrics['total_checks'] = health_data.get('total_checks', 0)
            
            # Error rate metrics from logger
            metrics['recent_errors'] = len([
                e for e in health_data.get('recent_history', [])
                if e.get('overall_status') == 'unhealthy'
            ])
        
        # Service availability
        metrics['services_enabled'] = sum(1 for enabled in self._service_states.values() if enabled)
        metrics['total_services'] = len(self._service_states)
        
        return metrics
    
    def get_service_status(self, service_name: str) -> bool:
        """Get status of a specific service"""
        return self._service_states.get(service_name, False)
    
    def get_enabled_services(self) -> List[str]:
        """Get list of currently enabled services"""
        return [
            name for name, enabled in self._service_states.items()
            if enabled
        ]
    
    def get_degradation_level(self) -> DegradationLevel:
        """Get current degradation level"""
        return self.current_level
    
    def get_degradation_info(self) -> Dict[str, Any]:
        """Get current degradation information"""
        return {
            'current_level': self.current_level.value,
            'enabled_services': self.get_enabled_services(),
            'disabled_services': [
                name for name, enabled in self._service_states.items()
                if not enabled
            ],
            'service_states': self._service_states.copy(),
            'degradation_history': self._degradation_history[-10:],  # Last 10 events
            'auto_recovery_enabled': self.auto_recovery_enabled
        }
    
    async def force_recovery(self, reason: str = "Manual recovery"):
        """Force recovery to full function mode"""
        await self.apply_degradation(DegradationLevel.FULL_FUNCTION, reason)
        
        # Cancel auto-recovery tasks
        for task in self._auto_recovery_tasks.values():
            task.cancel()
        self._auto_recovery_tasks.clear()


class ServiceProxy:
    """Proxy for service calls with graceful degradation"""
    
    def __init__(self, degradation_manager: GracefulDegradationManager):
        self.degradation_manager = degradation_manager
        self.logger = logging.getLogger("service_proxy")
    
    async def call_service(
        self,
        service_name: str,
        service_func: Callable,
        *args,
        fallback_func: Optional[Callable] = None,
        **kwargs
    ) -> Any:
        """Call service with graceful degradation support"""
        
        # Check if service is enabled
        if not self.degradation_manager.get_service_status(service_name):
            self.logger.warning(f"Service '{service_name}' is disabled, using fallback")
            
            if fallback_func:
                try:
                    if asyncio.iscoroutinefunction(fallback_func):
                        return await fallback_func(*args, **kwargs)
                    else:
                        return fallback_func(*args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Fallback for '{service_name}' failed: {e}")
                    raise ServiceDisabledError(f"Service '{service_name}' is disabled and fallback failed")
            else:
                raise ServiceDisabledError(f"Service '{service_name}' is disabled and no fallback provided")
        
        # Service is enabled, execute normally
        try:
            if asyncio.iscoroutinefunction(service_func):
                return await service_func(*args, **kwargs)
            else:
                return await asyncio.to_thread(service_func, *args, **kwargs)
                
        except Exception as e:
            # Log error and let it propagate
            self.logger.error(f"Service '{service_name}' call failed: {e}")
            raise


class CapacityManager:
    """Manages service capacity based on degradation level"""
    
    def __init__(self, degradation_manager: GracefulDegradationManager):
        self.degradation_manager = degradation_manager
        self.logger = logging.getLogger("capacity_manager")
        
        # Capacity tracking
        self._current_capacity = 1.0
        self._capacity_history = []
        
        # Queue management for reduced capacity
        self._request_queue = asyncio.Queue()
        self._processing_tasks: List[asyncio.Task] = []
    
    async def get_capacity_multiplier(self) -> float:
        """Get current capacity multiplier"""
        level = self.degradation_manager.get_degradation_level()
        config = self.degradation_manager._level_configs[level]
        return config['capacity']
    
    async def acquire_capacity(self, weight: float = 1.0) -> bool:
        """Acquire capacity for an operation"""
        multiplier = await self.get_capacity_multiplier()
        available_capacity = multiplier * 100  # Scale to percentage
        
        # Simple capacity check (in production, use more sophisticated logic)
        return weight <= available_capacity
    
    async def start_capacity_management(self):
        """Start capacity management for reduced capacity scenarios"""
        multiplier = await self.get_capacity_multiplier()
        if multiplier < 1.0:
            self.logger.info(f"Starting capacity management with multiplier {multiplier}")
            # Implement queue-based processing
            await self._start_request_queueing()
    
    async def _start_request_queueing(self):
        """Start queue-based request processing"""
        multiplier = await self.get_capacity_multiplier()
        max_concurrent = int(10 * multiplier)  # Base concurrency reduced by multiplier
        
        for _ in range(max_concurrent):
            task = asyncio.create_task(self._process_queue())
            self._processing_tasks.append(task)
    
    async def _process_queue(self):
        """Process requests from queue"""
        while True:
            try:
                request = await self._request_queue.get()
                await self._handle_request(request)
                self._request_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing queued request: {e}")
    
    async def _handle_request(self, request: Dict[str, Any]):
        """Handle a queued request"""
        # This would be implemented based on specific use case
        pass


class FeatureFlags:
    """Feature flags management for graceful degradation"""
    
    def __init__(self, degradation_manager: GracefulDegradationManager):
        self.degradation_manager = degradation_manager
        self.logger = logging.getLogger("feature_flags")
        
        # Feature flags
        self.flags: Dict[str, Dict[str, Any]] = {}
    
    def register_feature(self, feature_name: str, tier: ServiceTier, description: str = ""):
        """Register a feature flag"""
        self.flags[feature_name] = {
            'tier': tier,
            'enabled': True,
            'description': description
        }
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if feature is enabled based on current degradation level"""
        if feature_name not in self.flags:
            return False
        
        flag_info = self.flags[feature_name]
        level = self.degradation_manager.get_degradation_level()
        config = self.degradation_manager._level_configs[level]
        
        enabled_tiers = config['enabled_services']
        
        if enabled_tiers == 'all':
            return flag_info['enabled']
        elif isinstance(enabled_tiers, list):
            return flag_info['tier'] in enabled_tiers
        else:
            return False
    
    def enable_feature(self, feature_name: str):
        """Enable a feature"""
        if feature_name in self.flags:
            self.flags[feature_name]['enabled'] = True
            self.logger.info(f"Feature '{feature_name}' enabled")
    
    def disable_feature(self, feature_name: str):
        """Disable a feature"""
        if feature_name in self.flags:
            self.flags[feature_name]['enabled'] = False
            self.logger.info(f"Feature '{feature_name}' disabled")
    
    def get_enabled_features(self) -> List[str]:
        """Get list of currently enabled features"""
        return [
            name for name in self.flags.keys()
            if self.is_feature_enabled(name)
        ]


# Exceptions
class ServiceDisabledError(Exception):
    """Raised when service is disabled due to degradation"""
    pass


class DegradationError(Exception):
    """Raised when degradation prevents operation"""
    pass


# Default instances
default_degradation_manager = GracefulDegradationManager()
default_service_proxy = ServiceProxy(default_degradation_manager)
default_capacity_manager = CapacityManager(default_degradation_manager)
default_feature_flags = FeatureFlags(default_degradation_manager)


# Decorator for graceful degradation
def graceful_degradation(
    service_name: str,
    tier: ServiceTier,
    fallback: Optional[Callable] = None,
    degradation_manager: Optional[GracefulDegradationManager] = None
):
    """Decorator for graceful degradation support"""
    def decorator(func):
        dm = degradation_manager or default_degradation_manager
        
        # Register service if not already registered
        service_info = ServiceInfo(
            name=service_name,
            tier=tier,
            description=f"Function: {func.__name__}"
        )
        dm.register_service(service_info)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            proxy = ServiceProxy(dm)
            return await proxy.call_service(
                service_name, func, *args, fallback_func=fallback, **kwargs
            )
        
        return async_wrapper
    return decorator


# Example usage patterns
async def example_critical_service():
    """Example of a critical service with graceful degradation"""
    
    @graceful_degradation(
        service_name="payment_processing",
        tier=ServiceTier.CRITICAL,
        fallback=lambda: {"status": "queued", "message": "Payment queued for processing"}
    )
    async def process_payment(amount: float, user_id: str):
        # Primary payment processing logic
        # If service is degraded, fallback will be used
        return {"status": "processed", "amount": amount, "user_id": user_id}
    
    return await process_payment(100.0, "user123")


async def example_non_critical_service():
    """Example of a non-critical service"""
    
    @graceful_degradation(
        service_name="analytics_service",
        tier=ServiceTier.LUXURY,
        fallback=lambda: {"data": "cached_analytics", "source": "cache"}
    )
    async def generate_analytics():
        # Analytics generation logic
        return {"data": "fresh_analytics", "source": "live"}
    
    return await generate_analytics()