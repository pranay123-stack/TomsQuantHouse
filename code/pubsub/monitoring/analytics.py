"""
Monitoring and analytics system for message flow.
Provides real-time monitoring, performance metrics, and alerting capabilities.
"""

from typing import Dict, Any, List, Optional, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import logging
import threading
import time
import statistics
from collections import defaultdict, deque
from pathlib import Path
import sqlite3
import pickle

from schemas.message_schemas import BaseMessage, MessageType, Priority

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(Enum):
    """Alert states"""
    PENDING = "pending"
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Metric:
    """System metric representation"""
    metric_id: str
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class Alert:
    """Alert definition and state"""
    alert_id: str
    name: str
    description: str
    condition: Dict[str, Any]  # Alert condition
    severity: AlertSeverity
    source: str
    created_at: datetime
    state: AlertState = AlertState.PENDING
    triggered_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    current_value: Any = None
    threshold_value: Any = None
    occurrences: int = 1
    last_occurrence: Optional[datetime] = None


@dataclass
class PerformanceStats:
    """Performance statistics"""
    component_id: str
    timestamp: datetime
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_io: Dict[str, float] = field(default_factory=dict)
    active_connections: int = 0
    queue_sizes: Dict[str, int] = field(default_factory=dict)
    throughput: Dict[str, float] = field(default_factory=dict)


@dataclass
class MessageFlowStats:
    """Message flow statistics"""
    time_window: timedelta
    messages_total: int = 0
    messages_by_type: Dict[str, int] = field(default_factory=dict)
    messages_by_priority: Dict[str, int] = field(default_factory=dict)
    messages_by_channel: Dict[str, int] = field(default_factory=dict)
    messages_by_agent: Dict[str, int] = field(default_factory=dict)
    average_latency: float = 0.0
    throughput_per_second: float = 0.0
    error_rate: float = 0.0
    retry_rate: float = 0.0


class MetricCollector:
    """Collects and stores system metrics"""
    
    def __init__(self, collector_id: str, storage_path: str = "./metrics"):
        self.collector_id = collector_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.metrics_db = MetricsDB(self.storage_path / "metrics.db")
        self.metrics_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Real-time metric aggregators
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Thread safety
        self.lock = threading.RLock()
        
        logger.info(f"Metric collector {collector_id} initialized")
    
    def start(self):
        """Start the metric collector"""
        self.metrics_db.connect()
        logger.info(f"Metric collector {collector_id} started")
    
    def stop(self):
        """Stop the metric collector"""
        self.metrics_db.disconnect()
        logger.info(f"Metric collector {collector_id} stopped")
    
    def record_metric(self, metric: Metric):
        """Record a metric"""
        try:
            with self.lock:
                # Store in database
                self.metrics_db.store_metric(metric)
                
                # Cache for real-time access
                self.metrics_cache[metric.name].append(metric)
                
                # Update aggregators
                if metric.metric_type == MetricType.COUNTER:
                    self.counters[metric.name] = metric.value
                elif metric.metric_type == MetricType.GAUGE:
                    self.gauges[metric.name] = metric.value
                elif metric.metric_type in [MetricType.HISTOGRAM, MetricType.TIMER]:
                    self.histograms[metric.name].append(metric.value)
            
        except Exception as e:
            logger.error(f"Failed to record metric {metric.name}: {e}")
    
    def increment_counter(self, name: str, value: float = 1.0, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        metric = Metric(
            metric_id=str(uuid.uuid4()),
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        self.record_metric(metric)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        metric = Metric(
            metric_id=str(uuid.uuid4()),
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        self.record_metric(metric)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram metric"""
        metric = Metric(
            metric_id=str(uuid.uuid4()),
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            timestamp=datetime.now(),
            labels=labels or {}
        )
        self.record_metric(metric)
    
    def get_current_value(self, metric_name: str) -> Optional[float]:
        """Get current value of a metric"""
        with self.lock:
            if metric_name in self.gauges:
                return self.gauges[metric_name]
            elif metric_name in self.counters:
                return self.counters[metric_name]
            elif metric_name in self.histograms:
                histogram = self.histograms[metric_name]
                return statistics.mean(histogram) if histogram else None
        
        return None
    
    def get_histogram_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a histogram metric"""
        with self.lock:
            if metric_name not in self.histograms:
                return {}
            
            values = list(self.histograms[metric_name])
            if not values:
                return {}
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'p95': statistics.quantiles(values, n=20)[18] if len(values) > 20 else max(values),
                'p99': statistics.quantiles(values, n=100)[98] if len(values) > 100 else max(values)
            }
    
    def query_metrics(self, metric_name: str, start_time: datetime, 
                     end_time: datetime = None) -> List[Metric]:
        """Query metrics by name and time range"""
        if not end_time:
            end_time = datetime.now()
        
        return self.metrics_db.query_metrics(metric_name, start_time, end_time)
    
    def get_collector_stats(self) -> Dict[str, Any]:
        """Get collector statistics"""
        with self.lock:
            return {
                'collector_id': self.collector_id,
                'metrics_cached': {name: len(deque_) for name, deque_ in self.metrics_cache.items()},
                'active_counters': len(self.counters),
                'active_gauges': len(self.gauges),
                'active_histograms': len(self.histograms),
                'database_stats': self.metrics_db.get_statistics()
            }


class MetricsDB:
    """Database for storing metrics"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = None
        self.write_lock = threading.Lock()
    
    def connect(self):
        """Connect to metrics database"""
        try:
            self.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            
            # Enable WAL mode for better performance
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA cache_size=10000")
            
            self._create_tables()
            logger.info(f"Connected to metrics database: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to connect to metrics database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from metrics database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from metrics database")
    
    def store_metric(self, metric: Metric):
        """Store a metric in the database"""
        try:
            with self.write_lock:
                cursor = self.connection.cursor()
                cursor.execute("""
                    INSERT INTO metrics (
                        metric_id, name, value, metric_type, timestamp,
                        labels, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    metric.metric_id,
                    metric.name,
                    metric.value,
                    metric.metric_type.value,
                    metric.timestamp.isoformat(),
                    json.dumps(metric.labels),
                    json.dumps(metric.tags)
                ))
                
                self.connection.commit()
                
        except Exception as e:
            logger.error(f"Failed to store metric: {e}")
            raise
    
    def query_metrics(self, metric_name: str, start_time: datetime, 
                     end_time: datetime) -> List[Metric]:
        """Query metrics by name and time range"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT metric_id, name, value, metric_type, timestamp, labels, tags
                FROM metrics
                WHERE name = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
                LIMIT 1000
            """, (
                metric_name,
                start_time.isoformat(),
                end_time.isoformat()
            ))
            
            metrics = []
            for row in cursor.fetchall():
                try:
                    metric = Metric(
                        metric_id=row[0],
                        name=row[1],
                        value=row[2],
                        metric_type=MetricType(row[3]),
                        timestamp=datetime.fromisoformat(row[4]),
                        labels=json.loads(row[5]),
                        tags=json.loads(row[6])
                    )
                    metrics.append(metric)
                except Exception as e:
                    logger.error(f"Failed to parse metric row: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to query metrics: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Get record counts
            cursor.execute("SELECT COUNT(*) FROM metrics")
            total_metrics = cursor.fetchone()[0]
            
            # Get metric counts by type
            cursor.execute("""
                SELECT metric_type, COUNT(*)
                FROM metrics
                GROUP BY metric_type
            """)
            type_counts = dict(cursor.fetchall())
            
            # Get storage size
            cursor.execute("SELECT SUM(LENGTH(name) + LENGTH(value) + LENGTH(labels)) FROM metrics")
            storage_size = cursor.fetchone()[0] or 0
            
            return {
                'total_metrics': total_metrics,
                'metrics_by_type': type_counts,
                'storage_size_bytes': storage_size,
                'storage_size_mb': storage_size / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Failed to get database statistics: {e}")
            return {}
    
    def _create_tables(self):
        """Create metrics database tables"""
        try:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    metric_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    metric_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    labels TEXT,
                    tags TEXT,
                    INDEX idx_name_timestamp (name, timestamp),
                    INDEX idx_timestamp (timestamp)
                )
            """)
            
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to create metrics tables: {e}")
            raise


class AlertManager:
    """Manages alerts and notifications"""
    
    def __init__(self, manager_id: str):
        self.manager_id = manager_id
        self.alerts: Dict[str, Alert] = {}
        self.alert_rules: List[Dict[str, Any]] = []
        self.alert_handlers: Dict[AlertSeverity, List[Callable]] = defaultdict(list)
        self.alert_history: deque = deque(maxlen=10000)
        self.notification_channels: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            'alerts_created': 0,
            'alerts_resolved': 0,
            'alerts_suppressed': 0
        }
        
        logger.info(f"Alert manager {manager_id} initialized")
    
    def create_alert(self, name: str, description: str, condition: Dict[str, Any],
                    severity: AlertSeverity, source: str) -> str:
        """Create an alert rule"""
        alert_id = str(uuid.uuid4())
        
        alert = Alert(
            alert_id=alert_id,
            name=name,
            description=description,
            condition=condition,
            severity=severity,
            source=source,
            created_at=datetime.now()
        )
        
        self.alerts[alert_id] = alert
        self.alert_rules.append({
            'alert_id': alert_id,
            'condition': condition,
            'severity': severity.value
        })
        
        self.stats['alerts_created'] += 1
        
        logger.info(f"Created alert: {name} ({severity.value})")
        return alert_id
    
    def evaluate_alerts(self, metric_collector: MetricCollector):
        """Evaluate alert conditions against current metrics"""
        for rule in self.alert_rules:
            try:
                alert = self.alerts[rule['alert_id']]
                
                # Skip if alert is suppressed or resolved
                if alert.state in [AlertState.SUPPRESSED, AlertState.RESOLVED]:
                    continue
                
                # Evaluate condition
                triggered = self._evaluate_condition(rule['condition'], metric_collector)
                
                if triggered:
                    self._trigger_alert(alert, metric_collector)
                elif alert.state == AlertState.ACTIVE:
                    self._resolve_alert(alert)
                
            except Exception as e:
                logger.error(f"Error evaluating alert {rule['alert_id']}: {e}")
    
    def _evaluate_condition(self, condition: Dict[str, Any], 
                          metric_collector: MetricCollector) -> bool:
        """Evaluate an alert condition"""
        try:
            metric_name = condition['metric']
            operator = condition.get('operator', '>')
            threshold = condition['threshold']
            
            current_value = metric_collector.get_current_value(metric_name)
            if current_value is None:
                return False
            
            # Evaluate based on operator
            if operator == '>':
                return current_value > threshold
            elif operator == '>=':
                return current_value >= threshold
            elif operator == '<':
                return current_value < threshold
            elif operator == '<=':
                return current_value <= threshold
            elif operator == '==':
                return current_value == threshold
            elif operator == '!=':
                return current_value != threshold
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _trigger_alert(self, alert: Alert, metric_collector: MetricCollector):
        """Trigger an alert"""
        if alert.state != AlertState.PENDING:
            alert.occurrences += 1
        
        alert.state = AlertState.ACTIVE
        alert.triggered_at = datetime.now()
        alert.last_occurrence = datetime.now()
        
        # Get current metric value
        try:
            metric_name = alert.condition['metric']
            alert.current_value = metric_collector.get_current_value(metric_name)
            alert.threshold_value = alert.condition['threshold']
        except Exception as e:
            logger.error(f"Failed to get current metric value: {e}")
        
        # Add to history
        self.alert_history.append(copy.deepcopy(alert))
        
        # Notify handlers
        self._notify_alert_handlers(alert)
        
        logger.warning(f"Alert triggered: {alert.name} (severity: {alert.severity.value})")
    
    def _resolve_alert(self, alert: Alert):
        """Resolve an alert"""
        alert.state = AlertState.RESOLVED
        alert.resolved_at = datetime.now()
        
        self.stats['alerts_resolved'] += 1
        
        logger.info(f"Alert resolved: {alert.name}")
        
        # Notify handlers
        self._notify_alert_handlers(alert)
    
    def suppress_alert(self, alert_id: str, duration_minutes: int = 60) -> bool:
        """Suppress an alert for a duration"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            alert.state = AlertState.SUPPRESSED
            self.stats['alerts_suppressed'] += 1
            
            # Schedule unsuppression
            asyncio.create_task(self._unsuppress_alert(alert_id, duration_minutes))
            
            logger.info(f"Alert {alert_id} suppressed for {duration_minutes} minutes")
            return True
        
        return False
    
    async def _unsuppress_alert(self, alert_id: str, duration_minutes: int):
        """Unsuppress an alert after duration"""
        await asyncio.sleep(duration_minutes * 60)
        
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            if alert.state == AlertState.SUPPRESSED:
                alert.state = AlertState.PENDING
                logger.info(f"Alert {alert_id} unsuppressed")
    
    def add_alert_handler(self, severity: AlertSeverity, handler: Callable):
        """Add an alert notification handler"""
        self.alert_handlers[severity].append(handler)
    
    def _notify_alert_handlers(self, alert: Alert):
        """Notify alert handlers"""
        handlers = self.alert_handlers.get(alert.severity, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(alert))
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        return [alert for alert in self.alerts.values() 
                if alert.state == AlertState.ACTIVE]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        return {
            'manager_id': self.manager_id,
            'total_alerts': len(self.alerts),
            'active_alerts': len(self.get_active_alerts()),
            'suppressed_alerts': len([a for a in self.alerts.values() if a.state == AlertState.SUPPRESSED]),
            'statistics': self.stats.copy(),
            'handlers_registered': sum(len(handlers) for handlers in self.alert_handlers.values())
        }


class MessageFlowAnalyzer:
    """Analyzes message flow patterns and performance"""
    
    def __init__(self, analyzer_id: str):
        self.analyzer_id = analyzer_id
        self.message_flows: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.flow_stats: Dict[str, MessageFlowStats] = {}
        self.latency_tracker: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.throughput_tracker: deque = deque(maxlen=1000)
        
        # Pattern detection
        self.pattern_detectors: List[Callable] = []
        self.anomaly_detectors: List[Callable] = []
        
        logger.info(f"Message flow analyzer {analyzer_id} initialized")
    
    def track_message(self, message: BaseMessage, processing_time: float = 0.0):
        """Track a message through the system"""
        try:
            # Add to flow tracking
            flow_entry = {
                'message_id': message.metadata.message_id,
                'message_type': message.message_type.value,
                'sender_id': message.sender_id,
                'recipient_id': message.recipient_id,
                'channel': message.channel,
                'priority': message.metadata.priority.value,
                'timestamp': message.metadata.timestamp,
                'processing_time': processing_time,
                'size': len(message.to_json())
            }
            
            # Track by different dimensions
            self.message_flows['all'].append(flow_entry)
            self.message_flows[message.message_type.value].append(flow_entry)
            self.message_flows[f"sender_{message.sender_id}"].append(flow_entry)
            if message.recipient_id:
                self.message_flows[f"recipient_{message.recipient_id}"].append(flow_entry)
            if message.channel:
                self.message_flows[f"channel_{message.channel}"].append(flow_entry)
            
            # Track latency
            if processing_time > 0:
                self.latency_tracker[message.message_type.value].append(processing_time)
                self.latency_tracker['all'].append(processing_time)
            
            # Update throughput tracking
            self.throughput_tracker.append(datetime.now())
            
        except Exception as e:
            logger.error(f"Failed to track message: {e}")
    
    def analyze_flow_patterns(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Analyze message flow patterns"""
        try:
            cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
            
            # Analyze overall patterns
            recent_messages = [msg for msg in self.message_flows['all'] 
                             if msg['timestamp'] >= cutoff_time]
            
            if not recent_messages:
                return {}
            
            # Calculate statistics
            stats = MessageFlowStats(
                time_window=timedelta(minutes=time_window_minutes),
                messages_total=len(recent_messages)
            )
            
            # Group by different dimensions
            for msg in recent_messages:
                # By type
                msg_type = msg['message_type']
                stats.messages_by_type[msg_type] = stats.messages_by_type.get(msg_type, 0) + 1
                
                # By priority
                priority = msg['priority']
                stats.messages_by_priority[priority] = stats.messages_by_priority.get(priority, 0) + 1
                
                # By channel
                if msg['channel']:
                    channel = msg['channel']
                    stats.messages_by_channel[channel] = stats.messages_by_channel.get(channel, 0) + 1
                
                # By agent
                stats.messages_by_agent[msg['sender_id']] = stats.messages_by_agent.get(msg['sender_id'], 0) + 1
                if msg['recipient_id']:
                    stats.messages_by_agent[msg['recipient_id']] = stats.messages_by_agent.get(msg['recipient_id'], 0) + 1
            
            # Calculate metrics
            processing_times = [msg['processing_time'] for msg in recent_messages if msg['processing_time'] > 0]
            if processing_times:
                stats.average_latency = statistics.mean(processing_times)
            
            # Calculate throughput
            stats.throughput_per_second = len(recent_messages) / (time_window_minutes * 60)
            
            # Calculate error rate (simplified)
            # In a real implementation, you'd track error messages separately
            stats.error_rate = 0.0
            
            return stats.__dict__
            
        except Exception as e:
            logger.error(f"Failed to analyze flow patterns: {e}")
            return {}
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalies in message flow"""
        anomalies = []
        
        try:
            # Simple anomaly detection
            current_stats = self.analyze_flow_patterns(15)  # Last 15 minutes
            previous_stats = self.analyze_flow_patterns(30)  # Last 30 minutes
            
            if current_stats and previous_stats:
                current_throughput = current_stats.get('throughput_per_second', 0)
                previous_throughput = previous_stats.get('throughput_per_second', 0)
                
                # Detect throughput anomalies
                if previous_throughput > 0:
                    throughput_change = abs(current_throughput - previous_throughput) / previous_throughput
                    if throughput_change > 0.5:  # 50% change
                        anomalies.append({
                            'type': 'throughput_anomaly',
                            'severity': 'warning' if throughput_change < 2.0 else 'error',
                            'description': f'Throughput changed by {throughput_change:.1%}',
                            'current_value': current_throughput,
                            'previous_value': previous_throughput,
                            'timestamp': datetime.now()
                        })
            
            # Detect message type distribution changes
            current_types = current_stats.get('messages_by_type', {})
            previous_types = previous_stats.get('messages_by_type', {})
            
            for msg_type in current_types:
                current_count = current_types[msg_type]
                previous_count = previous_types.get(msg_type, 0)
                
                if previous_count > 0:
                    distribution_change = current_count / previous_count
                    if distribution_change > 2.0 or distribution_change < 0.5:  # 2x change
                        anomalies.append({
                            'type': 'message_distribution_anomaly',
                            'severity': 'warning',
                            'description': f'{msg_type} message count changed significantly',
                            'message_type': msg_type,
                            'current_count': current_count,
                            'previous_count': previous_count,
                            'timestamp': datetime.now()
                        })
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
        
        return anomalies
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Get performance insights and recommendations"""
        insights = {
            'timestamp': datetime.now(),
            'recommendations': [],
            'performance_metrics': {},
            'bottlenecks': [],
            'optimization_opportunities': []
        }
        
        try:
            # Analyze latency patterns
            for metric_name, latencies in self.latency_tracker.items():
                if len(latencies) >= 10:
                    avg_latency = statistics.mean(latencies)
                    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies)
                    
                    insights['performance_metrics'][metric_name] = {
                        'average_latency': avg_latency,
                        'p95_latency': p95_latency,
                        'sample_size': len(latencies)
                    }
                    
                    # Generate recommendations
                    if avg_latency > 1.0:  # > 1 second
                        insights['recommendations'].append({
                            'type': 'latency_optimization',
                            'target': metric_name,
                            'recommendation': f'Consider optimizing {metric_name} processing (avg: {avg_latency:.2f}s)'
                        })
                    
                    if p95_latency > avg_latency * 3:  # High variance
                        insights['bottlenecks'].append({
                            'type': 'high_latency_variance',
                            'target': metric_name,
                            'severity': 'warning',
                            'details': f'P95 latency ({p95_latency:.2f}s) much higher than average ({avg_latency:.2f}s)'
                        })
            
            # Analyze throughput
            if self.throughput_tracker:
                recent_throughput = len([t for t in self.throughput_tracker 
                                       if t >= datetime.now() - timedelta(minutes=5)])
                insights['throughput'] = {
                    'messages_per_minute': recent_throughput / 5.0,
                    'peak_capacity_estimate': recent_throughput * 2  # Rough estimate
                }
                
                if recent_throughput < 10:  # Low throughput
                    insights['recommendations'].append({
                        'type': 'throughput_investigation',
                        'recommendation': 'Low message throughput detected - investigate system utilization'
                    })
        
        except Exception as e:
            logger.error(f"Failed to generate performance insights: {e}")
        
        return insights
    
    def get_analyzer_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        return {
            'analyzer_id': self.analyzer_id,
            'tracked_flows': len(self.message_flows),
            'total_messages_tracked': len(self.message_flows['all']),
            'latency_metrics': len(self.latency_tracker),
            'throughput_samples': len(self.throughput_tracker),
            'pattern_detectors': len(self.pattern_detectors),
            'anomaly_detectors': len(self.anomaly_detectors)
        }


class MonitoringDashboard:
    """Real-time monitoring dashboard"""
    
    def __init__(self, dashboard_id: str, metric_collector: MetricCollector,
                 alert_manager: AlertManager, flow_analyzer: MessageFlowAnalyzer):
        self.dashboard_id = dashboard_id
        self.metric_collector = metric_collector
        self.alert_manager = alert_manager
        self.flow_analyzer = flow_analyzer
        
        self.dashboard_data: Dict[str, Any] = {}
        self.update_interval = 30  # seconds
        self.running = False
        self.update_task = None
        
        logger.info(f"Monitoring dashboard {dashboard_id} initialized")
    
    async def start(self):
        """Start the monitoring dashboard"""
        self.running = True
        self.update_task = asyncio.create_task(self._update_loop())
        logger.info(f"Monitoring dashboard {self.dashboard_id} started")
    
    async def stop(self):
        """Stop the monitoring dashboard"""
        self.running = False
        if self.update_task:
            self.update_task.cancel()
        logger.info(f"Monitoring dashboard {self.dashboard_id} stopped")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return self.dashboard_data.copy()
    
    async def _update_loop(self):
        """Background loop for updating dashboard data"""
        while self.running:
            try:
                # Update all monitoring data
                await self._update_dashboard_data()
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating dashboard data: {e}")
                await asyncio.sleep(5)
    
    async def _update_dashboard_data(self):
        """Update dashboard data"""
        try:
            # Get current metrics
            collector_stats = self.metric_collector.get_collector_stats()
            
            # Get alert status
            alert_stats = self.alert_manager.get_alert_stats()
            active_alerts = self.alert_manager.get_active_alerts()
            
            # Get flow analysis
            flow_stats = self.flow_analyzer.analyze_flow_patterns()
            performance_insights = self.flow_analyzer.get_performance_insights()
            anomalies = self.flow_analyzer.detect_anomalies()
            
            # Compile dashboard data
            self.dashboard_data = {
                'timestamp': datetime.now(),
                'system_status': 'healthy' if not active_alerts else 'warning',
                'metrics': {
                    'collector_stats': collector_stats,
                    'alert_stats': alert_stats,
                    'flow_stats': flow_stats
                },
                'alerts': {
                    'active_count': len(active_alerts),
                    'active_alerts': [
                        {
                            'name': alert.name,
                            'severity': alert.severity.value,
                            'description': alert.description,
                            'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None,
                            'current_value': alert.current_value,
                            'threshold_value': alert.threshold_value
                        }
                        for alert in active_alerts
                    ]
                },
                'performance': performance_insights,
                'anomalies': anomalies,
                'flow_analysis': flow_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to update dashboard data: {e}")
    
    def generate_report(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Generate monitoring report for time range"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=time_range_hours)
            
            # Get metrics for time range
            key_metrics = ['messages_processed', 'system_cpu_usage', 'system_memory_usage', 'error_rate']
            metrics_data = {}
            
            for metric_name in key_metrics:
                metrics = self.metric_collector.query_metrics(metric_name, start_time, end_time)
                if metrics:
                    values = [m.value for m in metrics]
                    metrics_data[metric_name] = {
                        'count': len(values),
                        'average': statistics.mean(values),
                        'min': min(values),
                        'max': max(values),
                        'latest': values[-1] if values else 0
                    }
            
            # Get flow analysis
            flow_stats = self.flow_analyzer.analyze_flow_patterns(time_range_hours * 60)
            
            # Get alerts in time range
            relevant_alerts = [alert for alert in self.alert_manager.alert_history
                             if alert.created_at >= start_time]
            
            return {
                'report_id': str(uuid.uuid4()),
                'time_range': {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_hours': time_range_hours
                },
                'summary': {
                    'total_messages': flow_stats.get('messages_total', 0),
                    'average_throughput': flow_stats.get('throughput_per_second', 0),
                    'alerts_raised': len(relevant_alerts),
                    'system_uptime_percentage': 99.9  # Placeholder
                },
                'metrics': metrics_data,
                'flow_analysis': flow_stats,
                'alerts': [
                    {
                        'name': alert.name,
                        'severity': alert.severity.value,
                        'created_at': alert.created_at.isoformat(),
                        'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                        'duration_minutes': (
                            (alert.resolved_at - alert.created_at).total_seconds() / 60
                            if alert.resolved_at else None
                        )
                    }
                    for alert in relevant_alerts
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {}


# Factory functions
def create_monitoring_system(system_id: str = "default",
                           storage_path: str = "./monitoring") -> Tuple[MetricCollector, AlertManager, MessageFlowAnalyzer, MonitoringDashboard]:
    """Create complete monitoring system"""
    metric_collector = MetricCollector(f"collector_{system_id}", storage_path)
    alert_manager = AlertManager(f"alerts_{system_id}")
    flow_analyzer = MessageFlowAnalyzer(f"analyzer_{system_id}")
    dashboard = MonitoringDashboard(f"dashboard_{system_id}", metric_collector, alert_manager, flow_analyzer)
    
    # Create default alert rules
    alert_manager.create_alert(
        name="High Error Rate",
        description="Error rate exceeds threshold",
        condition={
            'metric': 'error_rate',
            'operator': '>',
            'threshold': 0.05
        },
        severity=AlertSeverity.ERROR,
        source="system"
    )
    
    alert_manager.create_alert(
        name="High CPU Usage",
        description="CPU usage is too high",
        condition={
            'metric': 'system_cpu_usage',
            'operator': '>',
            'threshold': 80.0
        },
        severity=AlertSeverity.WARNING,
        source="system"
    )
    
    alert_manager.create_alert(
        name="Low Throughput",
        description="Message throughput is very low",
        condition={
            'metric': 'messages_per_second',
            'operator': '<',
            'threshold': 1.0
        },
        severity=AlertSeverity.WARNING,
        source="system"
    )
    
    # Add default alert handlers
    def log_alert_handler(alert: Alert):
        logger.warning(f"ALERT: {alert.name} - {alert.description}")
    
    def email_alert_handler(alert: Alert):
        # Placeholder for email notification
        print(f"Email alert: {alert.name} - {alert.description}")
    
    alert_manager.add_alert_handler(AlertSeverity.CRITICAL, log_alert_handler)
    alert_manager.add_alert_handler(AlertSeverity.ERROR, log_alert_handler)
    alert_manager.add_alert_handler(AlertSeverity.WARNING, email_alert_handler)
    
    return metric_collector, alert_manager, flow_analyzer, dashboard