"""
Monitoring and Analytics System for Message Flow Tracking
Provides comprehensive monitoring, metrics collection, and performance analytics
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import uuid
import statistics
import psutil
import threading
import logging
from pathlib import Path

from core.redis_client import RedisPubSubClient, MessagePriority
from protocols.message_schemas import ProtocolMessage, MessageStatus, MessageType


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PerformanceMetric(Enum):
    """Performance metrics to track"""
    MESSAGES_PER_SECOND = "messages_per_second"
    AVERAGE_LATENCY = "average_latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    CONNECTIONS_ACTIVE = "connections_active"
    QUEUE_SIZE = "queue_size"
    REPLAY_COUNT = "replay_count"


@dataclass
class Metric:
    """Individual metric measurement"""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)


@dataclass
class Alert:
    """System alert"""
    alert_id: str
    name: str
    description: str
    severity: AlertSeverity
    metric_name: str
    threshold: float
    current_value: float
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time"""
    timestamp: datetime
    system_metrics: Dict[str, float]
    application_metrics: Dict[str, float]
    message_metrics: Dict[str, float]
    agent_metrics: Dict[str, float]


@dataclass
class AnalyticsReport:
    """Analytics report"""
    report_id: str
    title: str
    period_start: datetime
    period_end: datetime
    metrics_summary: Dict[str, Any]
    trends: Dict[str, List[float]]
    alerts_summary: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime


class MetricsCollector:
    """Collects and stores system metrics"""
    
    def __init__(self, redis_client: RedisPubSubClient):
        self.redis = redis_client
        
        # Metric storage
        self.current_metrics: Dict[str, Metric] = {}
        self.metric_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Collection intervals
        self.collection_intervals = {
            PerformanceMetric.MESSAGES_PER_SECOND: 1,    # 1 second
            PerformanceMetric.AVERAGE_LATENCY: 10,       # 10 seconds
            PerformanceMetric.ERROR_RATE: 30,            # 30 seconds
            PerformanceMetric.THROUGHPUT: 60,            # 1 minute
            PerformanceMetric.CPU_USAGE: 5,              # 5 seconds
            PerformanceMetric.MEMORY_USAGE: 5,           # 5 seconds
            PerformanceMetric.DISK_USAGE: 30,            # 30 seconds
            PerformanceMetric.NETWORK_IO: 10,            # 10 seconds
            PerformanceMetric.CONNECTIONS_ACTIVE: 30,    # 30 seconds
            PerformanceMetric.QUEUE_SIZE: 1,             # 1 second
            PerformanceMetric.REPLAY_COUNT: 60           # 1 minute
        }
        
        # Collection tasks
        self.collection_tasks: Dict[PerformanceMetric, asyncio.Task] = {}
        
        # Statistics counters
        self.message_stats = {
            'sent': 0,
            'received': 0,
            'failed': 0,
            'retried': 0,
            'replayed': 0,
            'acknowledged': 0
        }
        
        # Latency tracking
        self.latency_samples = deque(maxlen=1000)
        
        # Thread safety
        self.metrics_lock = threading.RLock()
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start metrics collection"""
        # Start collection tasks for each metric
        for metric_type in PerformanceMetric:
            task = asyncio.create_task(self._collect_metric(metric_type))
            self.collection_tasks[metric_type] = task
        
        self.logger.info("Metrics collection started")
    
    async def stop(self):
        """Stop metrics collection"""
        # Cancel collection tasks
        for task in self.collection_tasks.values():
            task.cancel()
        
        self.logger.info("Metrics collection stopped")
    
    async def record_message_event(self, event_type: str, timestamp: datetime = None):
        """Record a message-related event"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        with self.metrics_lock:
            if event_type in self.message_stats:
                self.message_stats[event_type] += 1
    
    async def record_latency(self, latency_seconds: float):
        """Record message latency"""
        with self.metrics_lock:
            self.latency_samples.append(latency_seconds)
    
    async def get_metric(self, metric_name: str) -> Optional[Metric]:
        """Get current metric value"""
        return self.current_metrics.get(metric_name)
    
    async def get_metric_history(self, metric_name: str, 
                               limit: int = 100) -> List[Metric]:
        """Get metric history"""
        history = list(self.metric_history.get(metric_name, []))
        return history[-limit:] if limit > 0 else history
    
    async def _collect_metric(self, metric_type: PerformanceMetric):
        """Collect a specific metric"""
        interval = self.collection_intervals[metric_type]
        
        while True:
            try:
                if metric_type == PerformanceMetric.MESSAGES_PER_SECOND:
                    await self._collect_messages_per_second()
                elif metric_type == PerformanceMetric.AVERAGE_LATENCY:
                    await self._collect_average_latency()
                elif metric_type == PerformanceMetric.ERROR_RATE:
                    await self._collect_error_rate()
                elif metric_type == PerformanceMetric.THROUGHPUT:
                    await self._collect_throughput()
                elif metric_type == PerformanceMetric.CPU_USAGE:
                    await self._collect_cpu_usage()
                elif metric_type == PerformanceMetric.MEMORY_USAGE:
                    await self._collect_memory_usage()
                elif metric_type == PerformanceMetric.DISK_USAGE:
                    await self._collect_disk_usage()
                elif metric_type == PerformanceMetric.NETWORK_IO:
                    await self._collect_network_io()
                elif metric_type == PerformanceMetric.CONNECTIONS_ACTIVE:
                    await self._collect_connections_active()
                elif metric_type == PerformanceMetric.QUEUE_SIZE:
                    await self._collect_queue_size()
                elif metric_type == PerformanceMetric.REPLAY_COUNT:
                    await self._collect_replay_count()
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error collecting {metric_type.value} metric: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_messages_per_second(self):
        """Collect messages per second metric"""
        # Calculate messages per second over the last minute
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        
        # This would require storing message timestamps in a time-series data structure
        # For now, use the current stats as an approximation
        total_messages = sum(self.message_stats.values())
        
        metric = Metric(
            name=PerformanceMetric.MESSAGES_PER_SECOND.value,
            value=total_messages / 60,  # Approximate
            metric_type=MetricType.GAUGE,
            timestamp=now
        )
        
        self._store_metric(metric)
    
    async def _collect_average_latency(self):
        """Collect average latency metric"""
        if not self.latency_samples:
            return
        
        avg_latency = statistics.mean(self.latency_samples)
        
        metric = Metric(
            name=PerformanceMetric.AVERAGE_LATENCY.value,
            value=avg_latency,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_error_rate(self):
        """Collect error rate metric"""
        total_messages = sum(self.message_stats.values())
        failed_messages = self.message_stats['failed']
        
        error_rate = (failed_messages / total_messages * 100) if total_messages > 0 else 0
        
        metric = Metric(
            name=PerformanceMetric.ERROR_RATE.value,
            value=error_rate,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_throughput(self):
        """Collect throughput metric"""
        # Messages per minute
        total_messages = sum(self.message_stats.values())
        
        metric = Metric(
            name=PerformanceMetric.THROUGHPUT.value,
            value=total_messages,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_cpu_usage(self):
        """Collect CPU usage metric"""
        cpu_percent = psutil.cpu_percent(interval=1)
        
        metric = Metric(
            name=PerformanceMetric.CPU_USAGE.value,
            value=cpu_percent,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_memory_usage(self):
        """Collect memory usage metric"""
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        metric = Metric(
            name=PerformanceMetric.MEMORY_USAGE.value,
            value=memory_percent,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_disk_usage(self):
        """Collect disk usage metric"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        metric = Metric(
            name=PerformanceMetric.DISK_USAGE.value,
            value=disk_percent,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_network_io(self):
        """Collect network I/O metric"""
        network = psutil.net_io_counters()
        network_bytes = network.bytes_sent + network.bytes_recv
        
        metric = Metric(
            name=PerformanceMetric.NETWORK_IO.value,
            value=network_bytes,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_connections_active(self):
        """Collect active connections metric"""
        connections = len(psutil.net_connections())
        
        metric = Metric(
            name=PerformanceMetric.CONNECTIONS_ACTIVE.value,
            value=connections,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_queue_size(self):
        """Collect queue size metric"""
        # This would collect queue sizes from various components
        # For now, return a placeholder
        metric = Metric(
            name=PerformanceMetric.QUEUE_SIZE.value,
            value=0,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    async def _collect_replay_count(self):
        """Collect replay count metric"""
        replay_count = self.message_stats['replayed']
        
        metric = Metric(
            name=PerformanceMetric.REPLAY_COUNT.value,
            value=replay_count,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.utcnow()
        )
        
        self._store_metric(metric)
    
    def _store_metric(self, metric: Metric):
        """Store a metric in current metrics and history"""
        with self.metrics_lock:
            self.current_metrics[metric.name] = metric
            self.metric_history[metric.name].append(metric)


class AlertManager:
    """Manages system alerts based on metrics"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        
        # Alert configurations
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
        
        # Alert statistics
        self.alert_stats = {
            'alerts_triggered': 0,
            'alerts_resolved': 0,
            'alerts_acknowledged': 0,
            'false_positives': 0
        }
        
        # Thread safety
        self.alert_lock = threading.RLock()
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start alert monitoring"""
        # Start alert monitoring task
        asyncio.create_task(self._monitor_alerts())
        
        self.logger.info("Alert monitoring started")
    
    async def stop(self):
        """Stop alert monitoring"""
        self.logger.info("Alert monitoring stopped")
    
    def add_alert_rule(self, rule_name: str, rule_config: Dict[str, Any]):
        """Add an alert rule"""
        self.alert_rules[rule_name] = rule_config
        self.logger.info(f"Alert rule {rule_name} added")
    
    def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove an alert rule"""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            self.logger.info(f"Alert rule {rule_name} removed")
            return True
        return False
    
    def register_alert_handler(self, handler: Callable[[Alert], None]):
        """Register an alert handler"""
        self.alert_handlers.append(handler)
    
    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        with self.alert_lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.acknowledged = True
                self.alert_stats['alerts_acknowledged'] += 1
                
                self.logger.info(f"Alert {alert_id} acknowledged")
                return True
            return False
    
    async def _monitor_alerts(self):
        """Monitor metrics and trigger alerts"""
        while True:
            try:
                # Check each alert rule
                for rule_name, rule_config in self.alert_rules.items():
                    await self._check_alert_rule(rule_name, rule_config)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error monitoring alerts: {e}")
                await asyncio.sleep(30)
    
    async def _check_alert_rule(self, rule_name: str, rule_config: Dict[str, Any]):
        """Check an individual alert rule"""
        try:
            metric_name = rule_config['metric_name']
            condition = rule_config['condition']  # gt, lt, eq, ne
            threshold = rule_config['threshold']
            severity = AlertSeverity(rule_config.get('severity', 'warning'))
            
            # Get current metric value
            metric = await self.metrics_collector.get_metric(metric_name)
            if not metric:
                return
            
            current_value = metric.value
            
            # Check condition
            alert_triggered = False
            
            if condition == 'gt' and current_value > threshold:
                alert_triggered = True
            elif condition == 'lt' and current_value < threshold:
                alert_triggered = True
            elif condition == 'eq' and current_value == threshold:
                alert_triggered = True
            elif condition == 'ne' and current_value != threshold:
                alert_triggered = True
            
            # Handle alert state
            alert_key = f"{rule_name}:{metric_name}"
            
            if alert_triggered:
                if alert_key not in self.active_alerts:
                    # Create new alert
                    alert = Alert(
                        alert_id=str(uuid.uuid4()),
                        name=rule_name,
                        description=rule_config.get('description', ''),
                        severity=severity,
                        metric_name=metric_name,
                        threshold=threshold,
                        current_value=current_value,
                        triggered_at=datetime.utcnow()
                    )
                    
                    self.active_alerts[alert_key] = alert
                    self.alert_stats['alerts_triggered'] += 1
                    
                    # Notify handlers
                    for handler in self.alert_handlers:
                        try:
                            await handler(alert)
                        except Exception as e:
                            self.logger.error(f"Alert handler error: {e}")
                    
                    self.logger.warning(f"Alert triggered: {rule_name} - {current_value}")
                
                else:
                    # Update existing alert
                    self.active_alerts[alert_key].current_value = current_value
            
            else:
                # Resolve alert if it exists
                if alert_key in self.active_alerts:
                    alert = self.active_alerts[alert_key]
                    alert.resolved_at = datetime.utcnow()
                    
                    # Move to history
                    self.alert_history.append(alert)
                    del self.active_alerts[alert_key]
                    
                    self.alert_stats['alerts_resolved'] += 1
                    
                    self.logger.info(f"Alert resolved: {rule_name}")
        
        except Exception as e:
            self.logger.error(f"Error checking alert rule {rule_name}: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get list of active alerts"""
        return list(self.active_alerts.values())
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        with self.alert_lock:
            # Count alerts by severity
            severity_counts = defaultdict(int)
            for alert in self.active_alerts.values():
                severity_counts[alert.severity.value] += 1
            
            return {
                'alert_rules': len(self.alert_rules),
                'active_alerts': len(self.active_alerts),
                'alert_history_size': len(self.alert_history),
                'severity_counts': dict(severity_counts),
                'alert_stats': self.alert_stats.copy()
            }


class AnalyticsEngine:
    """Generates analytics reports and insights"""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        
        # Report storage
        self.reports: Dict[str, AnalyticsReport] = {}
        
        # Trend analysis
        self.trend_window = 24  # hours
        self.trend_cache: Dict[str, List[float]] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def generate_performance_report(self, period_hours: int = 1) -> AnalyticsReport:
        """Generate a performance report for the specified period"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=period_hours)
            
            # Collect metrics for the period
            metrics_data = await self._collect_period_metrics(start_time, end_time)
            
            # Analyze trends
            trends = await self._analyze_trends(metrics_data)
            
            # Generate insights and recommendations
            recommendations = await self._generate_recommendations(metrics_data, trends)
            
            # Create report
            report = AnalyticsReport(
                report_id=str(uuid.uuid4()),
                title=f"Performance Report - {period_hours}h",
                period_start=start_time,
                period_end=end_time,
                metrics_summary=self._summarize_metrics(metrics_data),
                trends=trends,
                alerts_summary=self._summarize_alerts(),
                recommendations=recommendations,
                generated_at=datetime.utcnow()
            )
            
            self.reports[report.report_id] = report
            
            self.logger.info(f"Generated performance report for {period_hours}h period")
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate performance report: {e}")
            raise
    
    async def analyze_message_flow(self, period_hours: int = 24) -> Dict[str, Any]:
        """Analyze message flow patterns"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=period_hours)
        
        # Get message metrics
        messages_per_sec_history = await self.metrics_collector.get_metric_history(
            PerformanceMetric.MESSAGES_PER_SECOND.value, limit=period_hours * 3600
        )
        
        latency_history = await self.metrics_collector.get_metric_history(
            PerformanceMetric.AVERAGE_LATENCY.value, limit=period_hours * 360
        )
        
        error_rate_history = await self.metrics_collector.get_metric_history(
            PerformanceMetric.ERROR_RATE.value, limit=period_hours * 120
        )
        
        # Analyze patterns
        analysis = {
            'period': f"{period_hours}h",
            'total_messages': sum(self.metrics_collector.message_stats.values()),
            'peak_hour': await self._find_peak_hour(messages_per_sec_history),
            'average_latency': self._calculate_average(latency_history),
            'error_rate': self._calculate_average(error_rate_history),
            'throughput_trend': await self._analyze_throughput_trend(messages_per_sec_history),
            'latency_trend': await self._analyze_latency_trend(latency_history),
            'quality_score': await self._calculate_quality_score(error_rate_history, latency_history)
        }
        
        return analysis
    
    async def _collect_period_metrics(self, start_time: datetime, end_time: datetime) -> Dict[str, List[Metric]]:
        """Collect metrics for a specific period"""
        metrics_data = {}
        
        # Collect all available metrics
        for metric_name in self.metrics_collector.current_metrics.keys():
            history = await self.metrics_collector.get_metric_history(metric_name, limit=0)
            
            # Filter by time period
            period_metrics = [
                metric for metric in history
                if start_time <= metric.timestamp <= end_time
            ]
            
            metrics_data[metric_name] = period_metrics
        
        return metrics_data
    
    async def _analyze_trends(self, metrics_data: Dict[str, List[Metric]]) -> Dict[str, List[float]]:
        """Analyze trends in metrics data"""
        trends = {}
        
        for metric_name, metrics in metrics_data.items():
            if len(metrics) < 2:
                continue
            
            # Extract values and timestamps
            values = [metric.value for metric in metrics]
            timestamps = [metric.timestamp for metric in metrics]
            
            # Calculate trend direction (simple linear regression)
            if len(values) >= 10:
                # Use last 10 points for trend calculation
                recent_values = values[-10:]
                recent_timestamps = timestamps[-10:]
                
                # Calculate slope
                n = len(recent_values)
                sum_x = sum(range(n))
                sum_y = sum(recent_values)
                sum_xy = sum(i * recent_values[i] for i in range(n))
                sum_x2 = sum(i * i for i in range(n))
                
                slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
                
                trends[metric_name] = [slope]
            else:
                trends[metric_name] = [0.0]
        
        return trends
    
    async def _generate_recommendations(self, metrics_data: Dict[str, List[Metric]], 
                                      trends: Dict[str, List[float]]) -> List[str]:
        """Generate recommendations based on metrics analysis"""
        recommendations = []
        
        # Analyze error rates
        error_rate_metrics = metrics_data.get(PerformanceMetric.ERROR_RATE.value, [])
        if error_rate_metrics:
            avg_error_rate = sum(m.value for m in error_rate_metrics) / len(error_rate_metrics)
            if avg_error_rate > 5:
                recommendations.append("High error rate detected. Investigate message failures and retry mechanisms.")
        
        # Analyze latency
        latency_metrics = metrics_data.get(PerformanceMetric.AVERAGE_LATENCY.value, [])
        if latency_metrics:
            avg_latency = sum(m.value for m in latency_metrics) / len(latency_metrics)
            if avg_latency > 1.0:  # 1 second
                recommendations.append("High message latency detected. Consider optimizing message routing and queue processing.")
        
        # Analyze CPU usage
        cpu_metrics = metrics_data.get(PerformanceMetric.CPU_USAGE.value, [])
        if cpu_metrics:
            avg_cpu = sum(m.value for m in cpu_metrics) / len(cpu_metrics)
            if avg_cpu > 80:
                recommendations.append("High CPU usage detected. Consider scaling resources or optimizing processing.")
        
        # Analyze memory usage
        memory_metrics = metrics_data.get(PerformanceMetric.MEMORY_USAGE.value, [])
        if memory_metrics:
            avg_memory = sum(m.value for m in memory_metrics) / len(memory_metrics)
            if avg_memory > 85:
                recommendations.append("High memory usage detected. Monitor for memory leaks and consider memory optimization.")
        
        return recommendations
    
    def _summarize_metrics(self, metrics_data: Dict[str, List[Metric]]) -> Dict[str, Any]:
        """Summarize metrics data"""
        summary = {}
        
        for metric_name, metrics in metrics_data.items():
            if not metrics:
                continue
            
            values = [m.value for m in metrics]
            
            summary[metric_name] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1]
            }
        
        return summary
    
    def _summarize_alerts(self) -> Dict[str, Any]:
        """Summarize alert information"""
        active_alerts = self.alert_manager.get_active_alerts()
        alert_stats = self.alert_manager.get_alert_stats()
        
        return {
            'active_count': len(active_alerts),
            'severity_breakdown': alert_stats['severity_counts'],
            'total_triggered': alert_stats['alert_stats']['alerts_triggered'],
            'total_resolved': alert_stats['alert_stats']['alerts_resolved']
        }
    
    async def _find_peak_hour(self, metrics_history: List[Metric]) -> Optional[str]:
        """Find the hour with peak activity"""
        if not metrics_history:
            return None
        
        # Group by hour
        hourly_totals = defaultdict(float)
        for metric in metrics_history:
            hour = metric.timestamp.strftime('%Y-%m-%d %H:00')
            hourly_totals[hour] += metric.value
        
        # Find peak hour
        if hourly_totals:
            peak_hour = max(hourly_totals, key=hourly_totals.get)
            return peak_hour
        
        return None
    
    def _calculate_average(self, metrics_history: List[Metric]) -> float:
        """Calculate average value from metrics history"""
        if not metrics_history:
            return 0.0
        
        return sum(m.value for m in metrics_history) / len(metrics_history)
    
    async def _analyze_throughput_trend(self, metrics_history: List[Metric]) -> str:
        """Analyze throughput trend"""
        if len(metrics_history) < 10:
            return "insufficient_data"
        
        recent_values = [m.value for m in metrics_history[-10:]]
        
        # Calculate trend
        if len(recent_values) >= 2:
            if recent_values[-1] > recent_values[0] * 1.1:
                return "increasing"
            elif recent_values[-1] < recent_values[0] * 0.9:
                return "decreasing"
            else:
                return "stable"
        
        return "stable"
    
    async def _analyze_latency_trend(self, metrics_history: List[Metric]) -> str:
        """Analyze latency trend"""
        if len(metrics_history) < 10:
            return "insufficient_data"
        
        recent_values = [m.value for m in metrics_history[-10:]]
        
        # Calculate trend
        if len(recent_values) >= 2:
            if recent_values[-1] > recent_values[0] * 1.1:
                return "increasing"
            elif recent_values[-1] < recent_values[0] * 0.9:
                return "decreasing"
            else:
                return "stable"
        
        return "stable"
    
    async def _calculate_quality_score(self, error_rate_history: List[Metric], 
                                     latency_history: List[Metric]) -> float:
        """Calculate overall quality score (0-100)"""
        avg_error_rate = self._calculate_average(error_rate_history)
        avg_latency = self._calculate_average(latency_history)
        
        # Score based on error rate (lower is better)
        error_score = max(0, 100 - avg_error_rate)
        
        # Score based on latency (lower is better)
        latency_score = max(0, 100 - (avg_latency * 100))
        
        # Combine scores
        quality_score = (error_score * 0.7) + (latency_score * 0.3)
        
        return round(quality_score, 2)
    
    def get_report(self, report_id: str) -> Optional[AnalyticsReport]:
        """Get a specific report"""
        return self.reports.get(report_id)
    
    def list_reports(self) -> List[AnalyticsReport]:
        """List all reports"""
        return list(self.reports.values())


class MonitoringDashboard:
    """Web-based monitoring dashboard"""
    
    def __init__(self, metrics_collector: MetricsCollector, 
                 alert_manager: AlertManager, analytics_engine: AnalyticsEngine):
        self.metrics_collector = metrics_collector
        self.alert_manager = alert_manager
        self.analytics_engine = analytics_engine
        
        self.logger = logging.getLogger(__name__)
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data for display"""
        try:
            # Current metrics
            current_metrics = {}
            for metric_name in self.metrics_collector.current_metrics.keys():
                metric = await self.metrics_collector.get_metric(metric_name)
                if metric:
                    current_metrics[metric_name] = {
                        'value': metric.value,
                        'timestamp': metric.timestamp.isoformat(),
                        'type': metric.metric_type.value
                    }
            
            # Active alerts
            active_alerts = []
            for alert in self.alert_manager.get_active_alerts():
                active_alerts.append({
                    'id': alert.alert_id,
                    'name': alert.name,
                    'severity': alert.severity.value,
                    'metric': alert.metric_name,
                    'threshold': alert.threshold,
                    'current_value': alert.current_value,
                    'triggered_at': alert.triggered_at.isoformat(),
                    'acknowledged': alert.acknowledged
                })
            
            # System health
            system_health = {
                'overall_status': self._calculate_overall_health(),
                'message_stats': self.metrics_collector.message_stats.copy(),
                'alert_summary': self.alert_manager.get_alert_stats()
            }
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'current_metrics': current_metrics,
                'active_alerts': active_alerts,
                'system_health': system_health,
                'recent_trends': await self._get_recent_trends()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get dashboard data: {e}")
            return {}
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall system health status"""
        active_alerts = self.alert_manager.get_active_alerts()
        
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        error_alerts = [a for a in active_alerts if a.severity == AlertSeverity.ERROR]
        warning_alerts = [a for a in active_alerts if a.severity == AlertSeverity.WARNING]
        
        if critical_alerts:
            return "critical"
        elif error_alerts:
            return "error"
        elif warning_alerts:
            return "warning"
        else:
            return "healthy"
    
    async def _get_recent_trends(self) -> Dict[str, Any]:
        """Get recent trend data"""
        trends = {}
        
        # Get recent metric values
        for metric_name in ['messages_per_second', 'average_latency', 'error_rate', 'cpu_usage']:
            history = await self.metrics_collector.get_metric_history(metric_name, limit=60)
            
            if history:
                trends[metric_name] = {
                    'values': [m.value for m in history],
                    'timestamps': [m.timestamp.isoformat() for m in history]
                }
        
        return trends


# Example usage and default configurations
async def create_monitoring_system(redis_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a complete monitoring system"""
    # Initialize Redis client
    redis_client = RedisPubSubClient(**redis_config)
    await redis_client.connect()
    
    # Create monitoring components
    metrics_collector = MetricsCollector(redis_client)
    alert_manager = AlertManager(metrics_collector)
    analytics_engine = AnalyticsEngine(metrics_collector, alert_manager)
    monitoring_dashboard = MonitoringDashboard(metrics_collector, alert_manager, analytics_engine)
    
    # Start monitoring
    await metrics_collector.start()
    await alert_manager.start()
    
    # Add default alert rules
    alert_manager.add_alert_rule("high_error_rate", {
        'metric_name': 'error_rate',
        'condition': 'gt',
        'threshold': 5.0,
        'severity': 'warning',
        'description': 'Error rate exceeds 5%'
    })
    
    alert_manager.add_alert_rule("high_latency", {
        'metric_name': 'average_latency',
        'condition': 'gt',
        'threshold': 1.0,
        'severity': 'warning',
        'description': 'Average latency exceeds 1 second'
    })
    
    alert_manager.add_alert_rule("high_cpu_usage", {
        'metric_name': 'cpu_usage',
        'condition': 'gt',
        'threshold': 80.0,
        'severity': 'error',
        'description': 'CPU usage exceeds 80%'
    })
    
    monitoring_system = {
        'metrics_collector': metrics_collector,
        'alert_manager': alert_manager,
        'analytics_engine': analytics_engine,
        'monitoring_dashboard': monitoring_dashboard
    }
    
    return monitoring_system