#!/usr/bin/env python3
"""
Performance Monitoring and Analytics Module for Letta API

Provides comprehensive monitoring, analytics, and insights for agent memory
and system performance, including real-time metrics, historical analysis,
and predictive analytics.
"""

import asyncio
import json
import logging
import time
import statistics
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from pathlib import Path

from letta_client import LettaAPIClient, MemoryBlockType, Priority
from memory_manager import AdvancedMemoryManager

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics"""
    MEMORY_USAGE = "memory_usage"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    QUERY_PERFORMANCE = "query_performance"
    AGENT_ACTIVITY = "agent_activity"
    WORKFLOW_EFFICIENCY = "workflow_efficiency"
    SYSTEM_HEALTH = "system_health"


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricAggregation(Enum):
    """Metric aggregation methods"""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    PERCENTILE = "percentile"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    metric_id: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    agent_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    unit: str = ""
    tags: List[str] = None


@dataclass
class MetricThreshold:
    """Metric threshold configuration"""
    metric_type: MetricType
    warning_threshold: float
    critical_threshold: float
    aggregation: MetricAggregation
    time_window_minutes: int
    consecutive_violations: int = 3
    enabled: bool = True


@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_id: str
    metric_type: MetricType
    alert_level: AlertLevel
    message: str
    current_value: float
    threshold_value: float
    agent_id: Optional[str]
    triggered_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None


@dataclass
class SystemMetrics:
    """System-wide metrics snapshot"""
    timestamp: datetime
    total_agents: int
    active_agents: int
    total_memory_blocks: int
    total_memory_size_bytes: int
    average_response_time: float
    requests_per_second: float
    error_rate: float
    cache_hit_rate: float
    system_utilization: float
    agent_metrics: Dict[str, Dict[str, float]]


@dataclass
class AgentMetrics:
    """Agent-specific metrics snapshot"""
    agent_id: str
    timestamp: datetime
    memory_blocks_count: int
    memory_size_bytes: int
    response_time_avg: float
    response_time_p95: float
    queries_per_hour: float
    error_rate: float
    cache_hit_rate: float
    workflow_success_rate: float
    activity_score: float


@dataclass
class TrendAnalysis:
    """Trend analysis result"""
    metric_type: MetricType
    time_period: str
    trend_direction: str  # "increasing", "decreasing", "stable", "volatile"
    trend_strength: float  # 0-1, correlation coefficient
    predicted_value: float
    confidence_interval: Tuple[float, float]
    insights: List[str]
    anomalies: List[Dict[str, Any]]


class PerformanceMonitor:
    """
    Comprehensive Performance Monitoring System for Letta API
    
    Features:
    - Real-time metrics collection and monitoring
    - Historical data analysis and trend detection
    - Alert generation and management
    - Predictive analytics and forecasting
    - Performance optimization recommendations
    - Comprehensive reporting and dashboards
    """
    
    def __init__(
        self,
        client: LettaAPIClient,
        monitoring_interval_seconds: int = 30,
        history_retention_hours: int = 168,  # 1 week
        alert_cooldown_minutes: int = 15
    ):
        self.client = client
        self.monitoring_interval = monitoring_interval_seconds
        self.history_retention = timedelta(hours=history_retention_hours)
        self.alert_cooldown = timedelta(minutes=alert_cooldown_minutes)
        
        # Metric storage
        self.metrics_history = defaultdict(deque)  # metric_type -> list of metrics
        self.metric_thresholds = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=10000)
        
        # Monitoring state
        self.is_monitoring = False
        self.monitoring_task = None
        self.last_monitoring_time = None
        
        # Configuration
        self._setup_default_thresholds()
        self._setup_metricCollectors()
    
    # === METRIC COLLECTION ===
    
    def start_monitoring(self):
        """Start the performance monitoring system"""
        
        if self.is_monitoring:
            logger.warning("Performance monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop the performance monitoring system"""
        
        if not self.is_monitoring:
            logger.warning("Performance monitoring is not running")
            return
        
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self.monitoring_task)
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        
        while self.is_monitoring:
            try:
                start_time = time.time()
                
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Collect agent metrics
                await self._collect_agent_metrics()
                
                # Check thresholds and generate alerts
                await self._check_thresholds()
                
                # Cleanup old data
                await self._cleanup_old_metrics()
                
                # Calculate monitoring duration
                loop_duration = time.time() - start_time
                sleep_time = max(0, self.monitoring_interval - loop_duration)
                
                self.last_monitoring_time = datetime.now()
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay on error
    
    async def _collect_system_metrics(self):
        """Collect system-wide performance metrics"""
        
        try:
            # Get system status
            system_status = self.client.get_system_status()
            
            # Get cache statistics
            cache_stats = self.client.get_cache_stats()
            
            # Calculate basic metrics
            total_agents = system_status.get("agents", {}).get("total_agents", 0)
            active_agents = system_status.get("agents", {}).get("active_agents", 0)
            
            memory_data = system_status.get("memory", {})
            total_memory_blocks = memory_data.get("total_blocks", 0)
            total_memory_size = memory_data.get("total_size_bytes", 0)
            
            # Response time metrics
            avg_response_time = self.client._monitoring_data.get("avg_response_time", 0.0)
            requests_count = self.client._monitoring_data.get("requests_count", 0)
            
            # Cache metrics
            cache_hit_rate = cache_stats.get("hit_rate", 0.0)
            cache_size = cache_stats.get("cache_size", 0)
            
            # Error rate (simplified calculation)
            errors_count = self.client._monitoring_data.get("errors_count", 0)
            error_rate = errors_count / max(1, requests_count) * 100
            
            # System utilization (estimated)
            memory_utilization = memory_data.get("utilization_percentage", 0.0)
            
            # Create system metrics
            system_metrics = SystemMetrics(
                timestamp=datetime.now(),
                total_agents=total_agents,
                active_agents=active_agents,
                total_memory_blocks=total_memory_blocks,
                total_memory_size_bytes=total_memory_size,
                average_response_time=avg_response_time,
                requests_per_second=requests_count / 60,  # Approximate
                error_rate=error_rate,
                cache_hit_rate=cache_hit_rate,
                system_utilization=memory_utilization,
                agent_metrics={}
            )
            
            # Store metrics
            self._store_metric(PerformanceMetric(
                metric_id=f"system_{int(time.time())}",
                metric_type=MetricType.SYSTEM_HEALTH,
                value=system_metrics.system_utilization,
                timestamp=datetime.now(),
                metadata=asdict(system_metrics),
                unit="percentage",
                tags=["system", "health"]
            ))
            
            self._store_metric(PerformanceMetric(
                metric_id=f"response_time_{int(time.time())}",
                metric_type=MetricType.RESPONSE_TIME,
                value=avg_response_time,
                timestamp=datetime.now(),
                unit="seconds",
                tags=["system", "performance"]
            ))
            
            self._store_metric(PerformanceMetric(
                metric_id=f"error_rate_{int(time.time())}",
                metric_type=MetricType.ERROR_RATE,
                value=error_rate,
                timestamp=datetime.now(),
                unit="percentage",
                tags=["system", "errors"]
            ))
            
            self._store_metric(PerformanceMetric(
                metric_id=f"cache_hit_rate_{int(time.time())}",
                metric_type=MetricType.CACHE_HIT_RATE,
                value=cache_hit_rate * 100,
                timestamp=datetime.now(),
                unit="percentage",
                tags=["system", "cache"]
            ))
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    async def _collect_agent_metrics(self):
        """Collect agent-specific performance metrics"""
        
        try:
            # Get all agents
            agents = self.client.get_agents()
            
            for agent in agents:
                try:
                    # Get agent memory metrics
                    memory_blocks = self.client.get_agent_memory(agent.id)
                    memory_size = sum(len(block.content) for block in memory_blocks)
                    
                    # Get agent performance metrics (simplified)
                    agent_performance = self.client.get_agent_performance(agent.id)
                    
                    # Response time (from communication stats if available)
                    comm_stats = self.client.get_communication_stats(agent.id) if hasattr(self.client, 'get_communication_stats') else {}
                    response_time = comm_stats.get("average_response_time", 0.0)
                    
                    # Create agent metrics
                    agent_metrics = AgentMetrics(
                        agent_id=agent.id,
                        timestamp=datetime.now(),
                        memory_blocks_count=len(memory_blocks),
                        memory_size_bytes=memory_size,
                        response_time_avg=response_time,
                        response_time_p95=response_time * 1.5,  # Approximation
                        queries_per_hour=comm_stats.get("messages_per_hour", 0),
                        error_rate=comm_stats.get("error_rate", 0),
                        cache_hit_rate=comm_stats.get("cache_hit_rate", 0),
                        workflow_success_rate=comm_stats.get("workflow_success_rate", 0),
                        activity_score=min(100.0, len(memory_blocks) + (agent.performance_score * 10))
                    )
                    
                    # Store metrics
                    self._store_metric(PerformanceMetric(
                        metric_id=f"agent_memory_{agent.id}_{int(time.time())}",
                        metric_type=MetricType.MEMORY_USAGE,
                        value=memory_size,
                        agent_id=agent.id,
                        timestamp=datetime.now(),
                        metadata={"blocks_count": len(memory_blocks)},
                        unit="bytes",
                        tags=["agent", "memory"]
                    ))
                    
                    self._store_metric(PerformanceMetric(
                        metric_id=f"agent_response_{agent.id}_{int(time.time())}",
                        metric_type=MetricType.RESPONSE_TIME,
                        value=response_time,
                        agent_id=agent.id,
                        timestamp=datetime.now(),
                        unit="seconds",
                        tags=["agent", "performance"]
                    ))
                    
                    self._store_metric(PerformanceMetric(
                        metric_id=f"agent_activity_{agent.id}_{int(time.time())}",
                        metric_type=MetricType.AGENT_ACTIVITY,
                        value=agent_metrics.activity_score,
                        agent_id=agent.id,
                        timestamp=datetime.now(),
                        unit="score",
                        tags=["agent", "activity"]
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to collect metrics for agent {agent.id}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to collect agent metrics: {e}")
    
    def _store_metric(self, metric: PerformanceMetric):
        """Store metric in history with automatic cleanup"""
        
        metric_type = metric.metric_type
        self.metrics_history[metric_type].append(metric)
        
        # Cleanup old metrics if we have too many
        max_metrics = 10000  # Limit per metric type
        if len(self.metrics_history[metric_type]) > max_metrics:
            # Remove oldest 20%
            remove_count = max_metrics // 5
            for _ in range(remove_count):
                self.metrics_history[metric_type].popleft()
    
    # === ALERT MANAGEMENT ===
    
    def _setup_default_thresholds(self):
        """Setup default alert thresholds"""
        
        default_thresholds = [
            MetricThreshold(
                metric_type=MetricType.SYSTEM_HEALTH,
                warning_threshold=80.0,
                critical_threshold=95.0,
                aggregation=MetricAggregation.AVERAGE,
                time_window_minutes=5
            ),
            MetricThreshold(
                metric_type=MetricType.RESPONSE_TIME,
                warning_threshold=1.0,
                critical_threshold=3.0,
                aggregation=MetricAggregation.AVERAGE,
                time_window_minutes=2
            ),
            MetricThreshold(
                metric_type=MetricType.ERROR_RATE,
                warning_threshold=5.0,
                critical_threshold=15.0,
                aggregation=MetricAggregation.AVERAGE,
                time_window_minutes=5
            ),
            MetricThreshold(
                metric_type=MetricType.CACHE_HIT_RATE,
                warning_threshold=60.0,
                critical_threshold=40.0,
                aggregation=MetricAggregation.AVERAGE,
                time_window_minutes=10
            ),
            MetricThreshold(
                metric_type=MetricType.MEMORY_USAGE,
                warning_threshold=500 * 1024 * 1024,  # 500MB
                critical_threshold=1024 * 1024 * 1024,  # 1GB
                aggregation=MetricAggregation.MAX,
                time_window_minutes=15
            )
        ]
        
        for threshold in default_thresholds:
            self.metric_thresholds[threshold.metric_type] = threshold
    
    def set_threshold(self, threshold: MetricThreshold):
        """Set custom threshold for a metric type"""
        self.metric_thresholds[threshold.metric_type] = threshold
        logger.info(f"Set threshold for {threshold.metric_type.value}")
    
    async def _check_thresholds(self):
        """Check all metrics against their thresholds"""
        
        current_time = datetime.now()
        
        for metric_type, threshold in self.metric_thresholds.items():
            if not threshold.enabled:
                continue
            
            try:
                # Get recent metrics
                recent_metrics = self._get_recent_metrics(
                    metric_type,
                    timedelta(minutes=threshold.time_window_minutes)
                )
                
                if not recent_metrics:
                    continue
                
                # Calculate aggregated value
                values = [m.value for m in recent_metrics]
                if threshold.aggregation == MetricAggregation.AVERAGE:
                    current_value = statistics.mean(values)
                elif threshold.aggregation == MetricAggregation.MAX:
                    current_value = max(values)
                elif threshold.aggregation == MetricAggregation.MIN:
                    current_value = min(values)
                elif threshold.aggregation == MetricAggregation.SUM:
                    current_value = sum(values)
                elif threshold.aggregation == MetricAggregation.COUNT:
                    current_value = len(values)
                else:
                    current_value = statistics.mean(values)
                
                # Check thresholds
                alert_level = None
                if current_value >= threshold.critical_threshold:
                    alert_level = AlertLevel.CRITICAL
                elif current_value >= threshold.warning_threshold:
                    alert_level = AlertLevel.WARNING
                
                # Special case for cache hit rate (lower is worse)
                if metric_type == MetricType.CACHE_HIT_RATE:
                    if current_value <= (100 - threshold.critical_threshold):
                        alert_level = AlertLevel.CRITICAL
                    elif current_value <= (100 - threshold.warning_threshold):
                        alert_level = AlertLevel.WARNING
                
                # Generate alert if threshold breached
                if alert_level:
                    await self._generate_alert(
                        metric_type=metric_type,
                        alert_level=alert_level,
                        current_value=current_value,
                        threshold_value=threshold.critical_threshold if alert_level == AlertLevel.CRITICAL else threshold.warning_threshold
                    )
            
            except Exception as e:
                logger.error(f"Error checking threshold for {metric_type.value}: {e}")
    
    async def _generate_alert(self, metric_type: MetricType, alert_level: AlertLevel, current_value: float, threshold_value: float):
        """Generate performance alert"""
        
        # Check cooldown period
        alert_key = f"{metric_type.value}_{alert_level.value}"
        last_alert_time = None
        
        for alert in reversed(self.alert_history):
            if (alert.metric_type == metric_type and 
                alert.alert_level == alert_level and
                alert.agent_id is None):  # System alerts only
                last_alert_time = alert.triggered_at
                break
        
        if last_alert_time and (datetime.now() - last_alert_time) < self.alert_cooldown:
            return  # Still in cooldown period
        
        # Create alert
        alert_id = f"alert_{metric_type.value}_{int(time.time())}"
        
        # Determine message
        if alert_level == AlertLevel.CRITICAL:
            message = f"CRITICAL: {metric_type.value} is {current_value:.2f}, exceeds critical threshold of {threshold_value:.2f}"
        else:
            message = f"WARNING: {metric_type.value} is {current_value:.2f}, exceeds warning threshold of {threshold_value:.2f}"
        
        alert = PerformanceAlert(
            alert_id=alert_id,
            metric_type=metric_type,
            alert_level=alert_level,
            message=message,
            current_value=current_value,
            threshold_value=threshold_value,
            agent_id=None,  # System-level alert
            triggered_at=datetime.now()
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        logger.warning(f"Performance alert generated: {alert.message}")
        
        # In a real implementation, you would send notifications here
        # (email, Slack, webhooks, etc.)
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_at = datetime.now()
        
        logger.info(f"Alert acknowledged: {alert_id}")
        return True
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.resolved_at = datetime.now()
        
        # Move to resolved state (could keep in separate collection)
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert resolved: {alert_id}")
        return True
    
    # === ANALYTICS AND INSIGHTS ===
    
    def get_current_system_metrics(self) -> SystemMetrics:
        """Get current system metrics snapshot"""
        
        # Get the most recent system metrics
        system_metric_type = MetricType.SYSTEM_HEALTH
        recent_metrics = self._get_recent_metrics(system_metric_type, timedelta(minutes=5))
        
        if not recent_metrics:
            # Return empty metrics if no data available
            return SystemMetrics(
                timestamp=datetime.now(),
                total_agents=0,
                active_agents=0,
                total_memory_blocks=0,
                total_memory_size_bytes=0,
                average_response_time=0.0,
                requests_per_second=0.0,
                error_rate=0.0,
                cache_hit_rate=0.0,
                system_utilization=0.0,
                agent_metrics={}
            )
        
        # Get the most recent system metrics
        latest_metric = max(recent_metrics, key=lambda x: x.timestamp)
        return SystemMetrics(**latest_metric.metadata)
    
    def get_agent_metrics(self, agent_id: str, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get detailed metrics for a specific agent"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        agent_metrics = {}
        
        # Get all metric types for this agent
        for metric_type in MetricType:
            metrics = [
                m for m in self.metrics_history[metric_type]
                if m.agent_id == agent_id and start_time <= m.timestamp <= end_time
            ]
            
            if metrics:
                values = [m.value for m in metrics]
                agent_metrics[metric_type.value] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "average": statistics.mean(values),
                    "latest": values[-1] if values else 0,
                    "trend": self._calculate_trend(values)
                }
        
        return {
            "agent_id": agent_id,
            "time_range_hours": time_range_hours,
            "metrics": agent_metrics,
            "generated_at": datetime.now().isoformat()
        }
    
    def analyze_trends(self, metric_type: MetricType, time_range_hours: int = 168) -> TrendAnalysis:
        """Analyze trends for a specific metric type"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # Get metrics for the time range
        metrics = [
            m for m in self.metrics_history[metric_type]
            if start_time <= m.timestamp <= end_time
        ]
        
        if len(metrics) < 2:
            return TrendAnalysis(
                metric_type=metric_type,
                time_period=f"{time_range_hours}h",
                trend_direction="insufficient_data",
                trend_strength=0.0,
                predicted_value=0.0,
                confidence_interval=(0.0, 0.0),
                insights=["Insufficient data for trend analysis"],
                anomalies=[]
            )
        
        # Prepare data for analysis
        timestamps = [(m.timestamp - start_time).total_seconds() / 3600 for m in metrics]  # Hours since start
        values = [m.value for m in metrics]
        
        # Calculate trend using linear regression
        if len(values) > 1:
            slope, intercept = np.polyfit(timestamps, values, 1)
            trend_strength = abs(slope)  # Simple trend strength
            
            # Determine trend direction
            if slope > 0.01:
                trend_direction = "increasing"
            elif slope < -0.01:
                trend_direction = "decreasing"
            else:
                trend_direction = "stable"
            
            # Calculate standard deviation for volatility
            volatility = statistics.stdev(values) if len(values) > 1 else 0
            if volatility > statistics.mean(values) * 0.5:
                trend_direction = "volatile"
            
            # Simple prediction (extend trend)
            last_timestamp = timestamps[-1]
            predicted_value = intercept + slope * (last_timestamp + 24)  # Predict 24 hours ahead
            
            # Confidence interval
            std_error = np.std(values) / np.sqrt(len(values))
            confidence_interval = (
                predicted_value - 1.96 * std_error,
                predicted_value + 1.96 * std_error
            )
            
            # Generate insights
            insights = []
            if trend_direction == "increasing":
                insights.append(f"{metric_type.value} is increasing over the time period")
            elif trend_direction == "decreasing":
                insights.append(f"{metric_type.value} is decreasing over the time period")
            elif trend_direction == "volatile":
                insights.append(f"{metric_type.value} shows high volatility")
            
            if trend_strength > 0.5:
                insights.append("Strong trend detected")
            elif trend_strength > 0.2:
                insights.append("Moderate trend detected")
            
            # Detect anomalies (simple method - outliers)
            anomalies = []
            if len(values) > 10:
                mean_val = statistics.mean(values)
                std_val = statistics.stdev(values)
                for i, (metric, value) in enumerate(zip(metrics, values)):
                    if abs(value - mean_val) > 2 * std_val:
                        anomalies.append({
                            "timestamp": metric.timestamp.isoformat(),
                            "value": value,
                            "deviation": abs(value - mean_val) / std_val
                        })
            
            return TrendAnalysis(
                metric_type=metric_type,
                time_period=f"{time_range_hours}h",
                trend_direction=trend_direction,
                trend_strength=trend_strength,
                predicted_value=predicted_value,
                confidence_interval=confidence_interval,
                insights=insights,
                anomalies=anomalies
            )
        
        else:
            return TrendAnalysis(
                metric_type=metric_type,
                time_period=f"{time_range_hours}h",
                trend_direction="stable",
                trend_strength=0.0,
                predicted_value=statistics.mean(values),
                confidence_interval=(min(values), max(values)),
                insights=["Insufficient data for detailed analysis"],
                anomalies=[]
            )
    
    def get_performance_summary(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # Get recent alerts
        recent_alerts = [
            alert for alert in self.alert_history
            if start_time <= alert.triggered_at <= end_time
        ]
        
        # Calculate metrics summary
        metrics_summary = {}
        for metric_type in MetricType:
            metrics = [
                m for m in self.metrics_history[metric_type]
                if start_time <= m.timestamp <= end_time
            ]
            
            if metrics:
                values = [m.value for m in metrics]
                metrics_summary[metric_type.value] = {
                    "count": len(values),
                    "average": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "latest": values[-1] if values else 0
                }
        
        # Alert summary
        alert_summary = {
            "total_alerts": len(recent_alerts),
            "by_level": {},
            "by_type": {}
        }
        
        for alert in recent_alerts:
            # By level
            level = alert.alert_level.value
            alert_summary["by_level"][level] = alert_summary["by_level"].get(level, 0) + 1
            
            # By type
            metric_type = alert.metric_type.value
            alert_summary["by_type"][metric_type] = alert_summary["by_type"].get(metric_type, 0) + 1
        
        # System health assessment
        system_health = "healthy"
        if recent_alerts:
            critical_alerts = [a for a in recent_alerts if a.alert_level == AlertLevel.CRITICAL]
            if critical_alerts:
                system_health = "critical"
            else:
                system_health = "degraded"
        
        return {
            "time_range_hours": time_range_hours,
            "system_health": system_health,
            "total_metrics_collected": sum(m["count"] for m in metrics_summary.values()),
            "metrics_summary": metrics_summary,
            "alert_summary": alert_summary,
            "active_alerts": len(self.active_alerts),
            "monitoring_status": "active" if self.is_monitoring else "inactive",
            "generated_at": datetime.now().isoformat()
        }
    
    def get_optimization_recommendations(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations"""
        
        recommendations = []
        
        # Get recent metrics
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)
        
        # Analyze response time
        response_time_metrics = [
            m for m in self.metrics_history[MetricType.RESPONSE_TIME]
            if start_time <= m.timestamp <= end_time and (not agent_id or m.agent_id == agent_id)
        ]
        
        if response_time_metrics:
            avg_response_time = statistics.mean([m.value for m in response_time_metrics])
            
            if avg_response_time > 2.0:
                recommendations.append({
                    "type": "performance",
                    "priority": "high",
                    "title": "High Response Time",
                    "description": f"Average response time is {avg_response_time:.2f}s, which exceeds optimal performance",
                    "recommendations": [
                        "Optimize database queries",
                        "Implement caching strategies",
                        "Consider scaling up resources"
                    ],
                    "estimated_impact": "medium"
                })
        
        # Analyze error rate
        error_rate_metrics = [
            m for m in self.metrics_history[MetricType.ERROR_RATE]
            if start_time <= m.timestamp <= end_time and (not agent_id or m.agent_id == agent_id)
        ]
        
        if error_rate_metrics:
            avg_error_rate = statistics.mean([m.value for m in error_rate_metrics])
            
            if avg_error_rate > 5.0:
                recommendations.append({
                    "type": "reliability",
                    "priority": "critical",
                    "title": "High Error Rate",
                    "description": f"Error rate is {avg_error_rate:.1f}%, indicating stability issues",
                    "recommendations": [
                        "Review error logs for patterns",
                        "Implement better error handling",
                        "Consider circuit breaker patterns"
                    ],
                    "estimated_impact": "high"
                })
        
        # Analyze cache performance
        cache_hit_rate_metrics = [
            m for m in self.metrics_history[MetricType.CACHE_HIT_RATE]
            if start_time <= m.timestamp <= end_time and (not agent_id or m.agent_id == agent_id)
        ]
        
        if cache_hit_rate_metrics:
            avg_cache_hit_rate = statistics.mean([m.value for m in cache_hit_rate_metrics])
            
            if avg_cache_hit_rate < 70.0:
                recommendations.append({
                    "type": "efficiency",
                    "priority": "medium",
                    "title": "Low Cache Hit Rate",
                    "description": f"Cache hit rate is {avg_cache_hit_rate:.1f}%, indicating caching inefficiencies",
                    "recommendations": [
                        "Review cache key strategies",
                        "Increase cache TTL",
                        "Optimize cache eviction policies"
                    ],
                    "estimated_impact": "medium"
                })
        
        return recommendations
    
    # === UTILITY METHODS ===
    
    def _get_recent_metrics(self, metric_type: MetricType, time_window: timedelta) -> List[PerformanceMetric]:
        """Get metrics from the specified time window"""
        
        cutoff_time = datetime.now() - time_window
        return [
            metric for metric in self.metrics_history[metric_type]
            if metric.timestamp >= cutoff_time
        ]
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate simple trend direction"""
        
        if len(values) < 3:
            return "stable"
        
        # Compare first third to last third
        first_third = values[:len(values)//3]
        last_third = values[-len(values)//3:]
        
        if not first_third or not last_third:
            return "stable"
        
        first_avg = statistics.mean(first_third)
        last_avg = statistics.mean(last_third)
        
        if last_avg > first_avg * 1.1:
            return "increasing"
        elif last_avg < first_avg * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent memory bloat"""
        
        cutoff_time = datetime.now() - self.history_retention
        
        for metric_type in self.metrics_history:
            # Remove old metrics
            while (self.metrics_history[metric_type] and 
                   self.metrics_history[metric_type][0].timestamp < cutoff_time):
                self.metrics_history[metric_type].popleft()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard"""
        
        current_metrics = self.get_current_system_metrics()
        performance_summary = self.get_performance_summary()
        
        # Get active alerts
        active_alerts = [
            {
                "alert_id": alert.alert_id,
                "metric_type": alert.metric_type.value,
                "alert_level": alert.alert_level.value,
                "message": alert.message,
                "current_value": alert.current_value,
                "triggered_at": alert.triggered_at.isoformat(),
                "acknowledged": alert.acknowledged
            }
            for alert in self.active_alerts.values()
        ]
        
        # Get recent trends
        trends = {}
        for metric_type in [MetricType.RESPONSE_TIME, MetricType.ERROR_RATE, MetricType.CACHE_HIT_RATE]:
            trends[metric_type.value] = asdict(self.analyze_trends(metric_type, 24))
        
        # Get optimization recommendations
        recommendations = self.get_optimization_recommendations()
        
        return {
            "system_metrics": asdict(current_metrics),
            "performance_summary": performance_summary,
            "active_alerts": active_alerts,
            "trends": trends,
            "recommendations": recommendations,
            "monitoring_status": {
                "is_active": self.is_monitoring,
                "last_update": self.last_monitoring_time.isoformat() if self.last_monitoring_time else None,
                "monitoring_interval": self.monitoring_interval
            }
        }


# === CONVENIENT FACTORY FUNCTIONS ===

def create_performance_monitor(
    client: LettaAPIClient,
    monitoring_interval: int = 30
) -> PerformanceMonitor:
    """Create a performance monitor instance"""
    return PerformanceMonitor(client, monitoring_interval)


if __name__ == "__main__":
    # Example usage
    import sys
    sys.path.append('/workspace/code/letta_api')
    
    from letta_client import LettaAPIClient
    
    # Configuration
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8283"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "your-secret-api-key"
    
    print("Performance Monitor Demo")
    print("=" * 50)
    
    client = LettaAPIClient(base_url, api_key)
    monitor = PerformanceMonitor(client, monitoring_interval=10)
    
    try:
        # Start monitoring
        print("1. Starting Performance Monitoring:")
        monitor.start_monitoring()
        print("   Monitoring started")
        
        # Wait a bit for metrics collection
        print("\n2. Collecting Metrics (waiting 15 seconds)...")
        import asyncio
        await asyncio.sleep(15)
        
        # Get dashboard data
        print("\n3. Dashboard Data:")
        dashboard = monitor.get_dashboard_data()
        print(f"   System Health: {dashboard['performance_summary']['system_health']}")
        print(f"   Active Alerts: {len(dashboard['active_alerts'])}")
        print(f"   Monitoring Active: {dashboard['monitoring_status']['is_active']}")
        
        # Get optimization recommendations
        print("\n4. Optimization Recommendations:")
        recommendations = monitor.get_optimization_recommendations()
        if recommendations:
            for rec in recommendations[:3]:  # Show first 3
                print(f"   - {rec['title']}: {rec['description']}")
        else:
            print("   No recommendations at this time")
        
        # Get trend analysis
        print("\n5. Trend Analysis (Response Time):")
        trend = monitor.analyze_trends(MetricType.RESPONSE_TIME, 1)  # 1 hour
        print(f"   Trend Direction: {trend.trend_direction}")
        print(f"   Trend Strength: {trend.trend_strength:.2f}")
        if trend.insights:
            print(f"   Insights: {trend.insights[0]}")
        
        # Stop monitoring
        print("\n6. Stopping Monitoring:")
        monitor.stop_monitoring()
        print("   Monitoring stopped")
        
        print("\nDemo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
    finally:
        client.close()