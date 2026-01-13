"""
Error Dashboard and Monitoring Alerts
"""
import asyncio
import json
import time
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from .error_types import StructuredError, ErrorCategory, ErrorSeverity
from .error_logging import ErrorLogger, global_error_logger, LogContext
from .health_checks import HealthCheckManager, HealthStatus


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""
    PENDING = "pending"
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class MetricType(Enum):
    """Types of metrics for monitoring"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    condition: str  # e.g., "error_rate > 0.1" or "health_status == UNHEALTHY"
    severity: AlertSeverity
    description: str
    notification_channels: List[str] = field(default_factory=list)
    evaluation_interval: int = 30  # seconds
    cooldown_period: int = 300  # 5 minutes
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def should_trigger(self, metrics: Dict[str, Any]) -> bool:
        """Check if alert rule should trigger"""
        if not self.enabled:
            return False
        
        try:
            # Simple condition evaluation (in production, use proper expression parser)
            condition = self.condition
            return eval(condition, {}, metrics)
        except Exception:
            return False


@dataclass
class Alert:
    """Active alert instance"""
    id: str
    rule_name: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    status: AlertStatus = AlertStatus.PENDING
    triggered_count: int = 1
    last_triggered: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        data = asdict(self)
        data['status'] = self.status.value
        data['severity'] = self.severity.value
        return data


@dataclass
class MetricData:
    """Metric data point"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'labels': self.labels,
            'type': self.metric_type.value
        }


class MetricStore:
    """Store and manage metrics"""
    
    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.logger = logging.getLogger("metric_store")
    
    def record_metric(self, metric: MetricData):
        """Record a metric data point"""
        self.metrics[metric.name].append(metric)
    
    def get_metrics(
        self,
        name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricData]:
        """Get metric data points"""
        if name not in self.metrics:
            return []
        
        points = list(self.metrics[name])
        
        if start_time:
            points = [p for p in points if p.timestamp >= start_time]
        
        if end_time:
            points = [p for p in points if p.timestamp <= end_time]
        
        return points
    
    def get_latest_value(self, name: str) -> Optional[float]:
        """Get latest value of a metric"""
        if name not in self.metrics or not self.metrics[name]:
            return None
        
        return self.metrics[name][-1].value
    
    def calculate_rate(self, name: str, duration_minutes: int = 5) -> float:
        """Calculate rate of change for a metric"""
        points = self.get_metrics(name)
        if len(points) < 2:
            return 0.0
        
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=duration_minutes)
        
        recent_points = [p for p in points if start_time <= p.timestamp <= end_time]
        
        if len(recent_points) < 2:
            return 0.0
        
        # Calculate average rate
        time_diff = (recent_points[-1].timestamp - recent_points[0].timestamp).total_seconds()
        if time_diff <= 0:
            return 0.0
        
        value_diff = recent_points[-1].value - recent_points[0].value
        return value_diff / time_diff


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, metric_store: Optional[MetricStore] = None):
        self.metric_store = metric_store or MetricStore()
        self.logger = logging.getLogger("alert_manager")
        
        # Alert rules and active alerts
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Notification channels
        self.notification_channels: Dict[str, Callable] = {}
        
        # Monitoring
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_active = False
        
        # Register built-in notification channels
        self._register_default_channels()
    
    def _register_default_channels(self):
        """Register default notification channels"""
        self.register_channel("console", self._console_notification)
        self.register_channel("log", self._log_notification)
    
    def register_channel(self, name: str, callback: Callable):
        """Register a notification channel"""
        self.notification_channels[name] = callback
        self.logger.info(f"Registered notification channel: {name}")
    
    def add_alert_rule(self, rule: AlertRule):
        """Add alert rule"""
        self.alert_rules[rule.name] = rule
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str):
        """Remove alert rule"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            self.logger.info(f"Removed alert rule: {rule_name}")
    
    async def start_monitoring(self):
        """Start alert monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitor_alerts())
        self.logger.info("Started alert monitoring")
    
    async def stop_monitoring(self):
        """Stop alert monitoring"""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Stopped alert monitoring")
    
    async def _monitor_alerts(self):
        """Internal alert monitoring loop"""
        while self._monitoring_active:
            try:
                # Collect current metrics
                metrics = await self._collect_metrics()
                
                # Evaluate alert rules
                for rule in self.alert_rules.values():
                    await self._evaluate_rule(rule, metrics)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Alert monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect current system metrics"""
        metrics = {}
        
        # Error metrics from error logger
        if hasattr(global_error_logger, 'error_storage'):
            error_storage = global_error_logger.error_storage
            total_errors = len(error_storage)
            
            # Error rate calculation
            recent_errors = [
                e for e in error_storage
                if datetime.fromisoformat(e['timestamp']) >= datetime.now() - timedelta(minutes=5)
            ]
            
            metrics.update({
                'total_errors': total_errors,
                'recent_error_count': len(recent_errors),
                'error_rate': len(recent_errors) / 5.0,  # errors per minute
            })
            
            # Error by category
            categories = defaultdict(int)
            severities = defaultdict(int)
            
            for error in recent_errors:
                error_data = error.get('error', {})
                categories[error_data.get('category', 'unknown')] += 1
                severities[error_data.get('severity', 'unknown')] += 1
            
            metrics['errors_by_category'] = dict(categories)
            metrics['errors_by_severity'] = dict(severities)
        
        # Health metrics
        metrics['health_status'] = 'healthy'  # This would be updated by health check integration
        
        # Timestamp
        metrics['timestamp'] = datetime.now().isoformat()
        
        return metrics
    
    async def _evaluate_rule(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Evaluate an alert rule"""
        if rule.should_trigger(metrics):
            await self._trigger_alert(rule, metrics)
        else:
            await self._check_alert_recovery(rule, metrics)
    
    async def _trigger_alert(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Trigger an alert"""
        alert_id = f"{rule.name}:{int(time.time())}"
        
        # Check if we already have an active alert for this rule
        existing_alert = self._get_active_alert(rule.name)
        
        if existing_alert:
            # Update existing alert
            existing_alert.triggered_count += 1
            existing_alert.last_triggered = datetime.now()
            self.logger.warning(f"Alert '{rule.name}' re-triggered (count: {existing_alert.triggered_count})")
        else:
            # Create new alert
            alert = Alert(
                id=alert_id,
                rule_name=rule.name,
                severity=rule.severity,
                title=rule.name,
                message=rule.description,
                timestamp=datetime.now(),
                metadata=metrics
            )
            
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            self.logger.error(f"Alert triggered: {rule.name}")
            
            # Send notifications
            await self._send_notifications(alert, rule)
    
    async def _check_alert_recovery(self, rule: AlertRule, metrics: Dict[str, Any]):
        """Check if an alert should be resolved"""
        active_alert = self._get_active_alert(rule.name)
        
        if active_alert and active_alert.status == AlertStatus.ACTIVE:
            # Check if enough time has passed since last trigger (cooldown)
            time_since_trigger = (datetime.now() - active_alert.last_triggered).total_seconds()
            
            if time_since_trigger >= rule.cooldown_period:
                await self._resolve_alert(active_alert)
    
    def _get_active_alert(self, rule_name: str) -> Optional[Alert]:
        """Get active alert for a rule"""
        for alert in self.active_alerts.values():
            if alert.rule_name == rule_name and alert.status in [AlertStatus.PENDING, AlertStatus.ACTIVE]:
                return alert
        return None
    
    async def _send_notifications(self, alert: Alert, rule: AlertRule):
        """Send alert notifications"""
        for channel_name in rule.notification_channels:
            if channel_name in self.notification_channels:
                try:
                    callback = self.notification_channels[channel_name]
                    await callback(alert, rule)
                except Exception as e:
                    self.logger.error(f"Notification failed for channel '{channel_name}': {e}")
    
    async def _resolve_alert(self, alert: Alert):
        """Resolve an alert"""
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now()
        
        self.logger.info(f"Alert resolved: {alert.rule_name}")
        
        # Remove from active alerts
        if alert.id in self.active_alerts:
            del self.active_alerts[alert.id]
    
    async def _console_notification(self, alert: Alert, rule: AlertRule):
        """Console notification"""
        print(f"[ALERT] {alert.severity.value.upper()}: {alert.title}")
        print(f"Message: {alert.message}")
        print(f"Time: {alert.timestamp}")
        print("---")
    
    async def _log_notification(self, alert: Alert, rule: AlertRule):
        """Log notification"""
        log_message = f"Alert: {alert.title} - {alert.message}"
        
        if alert.severity == AlertSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif alert.severity == AlertSeverity.ERROR:
            self.logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get list of active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        active_alerts = len(self.active_alerts)
        
        by_severity = defaultdict(int)
        by_status = defaultdict(int)
        
        for alert in self.alert_history:
            by_severity[alert.severity.value] += 1
            by_status[alert.status.value] += 1
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'by_severity': dict(by_severity),
            'by_status': dict(by_status),
            'rules_count': len(self.alert_rules)
        }


class ErrorDashboard:
    """Error dashboard for monitoring and visualization"""
    
    def __init__(
        self,
        error_logger: Optional[ErrorLogger] = None,
        alert_manager: Optional[AlertManager] = None,
        health_manager: Optional[HealthCheckManager] = None
    ):
        self.error_logger = error_logger or global_error_logger
        self.alert_manager = alert_manager or AlertManager()
        self.health_manager = health_manager
        self.logger = logging.getLogger("error_dashboard")
        
        # Dashboard data cache
        self._dashboard_cache: Dict[str, Any] = {}
        self._last_cache_update = 0
        self._cache_ttl = 30  # seconds
    
    def get_dashboard_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get dashboard data"""
        now = time.time()
        
        if not force_refresh and (now - self._last_cache_update) < self._cache_ttl:
            return self._dashboard_cache
        
        # Collect data from various sources
        dashboard_data = {
            'timestamp': datetime.now().isoformat(),
            'errors': self._get_error_summary(),
            'alerts': self._get_alert_summary(),
            'health': self._get_health_summary(),
            'metrics': self._get_metrics_summary(),
            'trends': self._get_trend_analysis()
        }
        
        self._dashboard_cache = dashboard_data
        self._last_cache_update = now
        
        return dashboard_data
    
    def _get_error_summary(self) -> Dict[str, Any]:
        """Get error summary"""
        error_stats = self.error_logger.get_error_stats()
        
        # Recent errors with detailed information
        recent_errors = self.error_logger.get_recent_errors(limit=50)
        
        # Group errors by time windows
        time_windows = {
            'last_hour': datetime.now() - timedelta(hours=1),
            'last_day': datetime.now() - timedelta(days=1),
            'last_week': datetime.now() - timedelta(weeks=1)
        }
        
        window_counts = {}
        for window_name, window_start in time_windows.items():
            count = sum(
                1 for error in recent_errors
                if datetime.fromisoformat(error['timestamp']) >= window_start
            )
            window_counts[window_name] = count
        
        return {
            'total_errors': error_stats.get('total_errors', 0),
            'categories': error_stats.get('categories', {}),
            'severities': error_stats.get('severities', {}),
            'recent_errors': recent_errors[-10:],  # Last 10 for display
            'time_windows': window_counts,
            'error_rate': self._calculate_error_rate()
        }
    
    def _get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary"""
        active_alerts = self.alert_manager.get_active_alerts()
        alert_stats = self.alert_manager.get_alert_stats()
        
        # Group active alerts by severity
        by_severity = defaultdict(list)
        for alert in active_alerts:
            by_severity[alert.severity.value].append(alert.to_dict())
        
        return {
            'total_active': len(active_alerts),
            'stats': alert_stats,
            'by_severity': dict(by_severity),
            'recent_alerts': [
                alert.to_dict() for alert in active_alerts
            ][:10]  # Last 10 active alerts
        }
    
    def _get_health_summary(self) -> Dict[str, Any]:
        """Get health summary"""
        if not self.health_manager:
            return {'status': 'unknown', 'message': 'Health manager not configured'}
        
        health_data = self.health_manager.get_health_dashboard_data()
        overall_status = health_data.get('overall_status', 'unknown')
        
        # Health check breakdown
        checkers = health_data.get('checkers', {})
        healthy_count = sum(
            1 for checker in checkers.values()
            if checker.get('status') == 'healthy'
        )
        
        return {
            'overall_status': overall_status,
            'total_checks': len(checkers),
            'healthy_checks': healthy_count,
            'unhealthy_checks': len(checkers) - healthy_count,
            'check_details': checkers
        }
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        # Basic metrics from error logger
        error_storage = getattr(self.error_logger, 'error_storage', [])
        
        if not error_storage:
            return {'message': 'No metrics available'}
        
        # Calculate some basic metrics
        total_errors = len(error_storage)
        
        # Error rate over last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_errors = [
            e for e in error_storage
            if datetime.fromisoformat(e['timestamp']) >= one_hour_ago
        ]
        
        error_rate_per_hour = len(recent_errors)
        
        return {
            'total_errors': total_errors,
            'errors_last_hour': error_rate_per_hour,
            'error_rate_per_hour': error_rate_per_hour
        }
    
    def _get_trend_analysis(self) -> Dict[str, Any]:
        """Get trend analysis"""
        error_storage = getattr(self.error_logger, 'error_storage', [])
        
        if len(error_storage) < 10:
            return {'message': 'Insufficient data for trend analysis'}
        
        # Analyze trends over different time periods
        now = datetime.now()
        periods = {
            'last_hour': now - timedelta(hours=1),
            'last_6_hours': now - timedelta(hours=6),
            'last_24_hours': now - timedelta(days=1),
            'last_week': now - timedelta(weeks=1)
        }
        
        trends = {}
        prev_count = None
        
        for period_name, period_start in periods.items():
            count = sum(
                1 for error in error_storage
                if datetime.fromisoformat(error['timestamp']) >= period_start
            )
            
            trend = 'stable'
            if prev_count is not None and prev_count > 0:
                change_percent = ((count - prev_count) / prev_count) * 100
                if change_percent > 10:
                    trend = 'increasing'
                elif change_percent < -10:
                    trend = 'decreasing'
            
            trends[period_name] = {
                'count': count,
                'trend': trend
            }
            prev_count = count
        
        return trends
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        error_storage = getattr(self.error_logger, 'error_storage', [])
        
        if not error_storage:
            return 0.0
        
        # Count errors in last 5 minutes
        five_minutes_ago = datetime.now() - timedelta(minutes=5)
        recent_errors = [
            e for e in error_storage
            if datetime.fromisoformat(e['timestamp']) >= five_minutes_ago
        ]
        
        return len(recent_errors) / 5.0  # errors per minute
    
    def export_data(self, format: str = 'json') -> str:
        """Export dashboard data"""
        data = self.get_dashboard_data(force_refresh=True)
        
        if format.lower() == 'json':
            return json.dumps(data, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def generate_report(self, period_hours: int = 24) -> str:
        """Generate error report for specified period"""
        data = self.get_dashboard_data()
        
        period_start = datetime.now() - timedelta(hours=period_hours)
        
        report = f"""
Error Handling Report
====================
Period: Last {period_hours} hours
Generated: {datetime.now().isoformat()}

Summary:
--------
Overall Status: {data.get('health', {}).get('overall_status', 'unknown')}
Total Errors: {data.get('errors', {}).get('total_errors', 0)}
Active Alerts: {data.get('alerts', {}).get('total_active', 0)}

Error Breakdown:
---------------
"""
        
        categories = data.get('errors', {}).get('categories', {})
        for category, count in categories.items():
            report += f"  {category}: {count}\n"
        
        report += f"""
Severity Breakdown:
------------------
"""
        severities = data.get('errors', {}).get('severities', {})
        for severity, count in severities.items():
            report += f"  {severity}: {count}\n"
        
        report += f"""
Active Alerts:
-------------
"""
        active_alerts = data.get('alerts', {}).get('recent_alerts', [])
        if active_alerts:
            for alert in active_alerts:
                report += f"  - {alert.get('title', 'Unknown')} ({alert.get('severity', 'unknown')})\n"
        else:
            report += "  No active alerts\n"
        
        return report


# Default instances
default_metric_store = MetricStore()
default_alert_manager = AlertManager(default_metric_store)
default_dashboard = ErrorDashboard(
    error_logger=global_error_logger,
    alert_manager=default_alert_manager
)


# Pre-configured alert rules
def create_default_alert_rules() -> List[AlertRule]:
    """Create default alert rules for common scenarios"""
    return [
        AlertRule(
            name="high_error_rate",
            condition="error_rate > 10",
            severity=AlertSeverity.ERROR,
            description="Error rate exceeds 10 errors per minute",
            notification_channels=["console", "log"]
        ),
        AlertRule(
            name="critical_error_rate",
            condition="error_rate > 50",
            severity=AlertSeverity.CRITICAL,
            description="Critical error rate - exceeding 50 errors per minute",
            notification_channels=["console", "log"]
        ),
        AlertRule(
            name="unhealthy_system",
            condition="health_status == 'unhealthy'",
            severity=AlertSeverity.CRITICAL,
            description="System health status is unhealthy",
            notification_channels=["console", "log"]
        ),
        AlertRule(
            name="many_category_errors",
            condition="len(errors_by_category) > 5",
            severity=AlertSeverity.WARNING,
            description="Multiple error categories detected",
            notification_channels=["log"]
        )
    ]


# Initialize default alert rules
for rule in create_default_alert_rules():
    default_alert_manager.add_alert_rule(rule)


@asynccontextmanager
async def dashboard_context():
    """Context manager for dashboard initialization"""
    try:
        # Start alert monitoring
        await default_alert_manager.start_monitoring()
        yield default_dashboard
    finally:
        # Cleanup
        await default_alert_manager.stop_monitoring()