"""
Metrics collection system for Composio MCP Server.
"""

import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import psutil
import structlog
from prometheus_client import (
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    Gauge,
    Summary,
)

logger = structlog.get_logger()


class MetricsCollector:
    """Metrics collection and reporting system."""
    
    def __init__(self, settings):
        """Initialize metrics collector."""
        self.settings = settings
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Metrics storage
        self.metrics_history = {}
        self.request_metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "requests_by_tool": {},
            "requests_by_user": {}
        }
        
        # Performance metrics
        self.performance_metrics = {
            "start_time": time.time(),
            "memory_usage_history": [],
            "cpu_usage_history": [],
            "response_time_history": []
        }
        
        logger.info("Metrics collector initialized")
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics."""
        # Request metrics
        self.request_counter = Counter('composio_requests_total', 'Total requests', ['tool', 'status'])
        self.response_time_histogram = Histogram('composio_request_duration_seconds', 'Request duration', ['tool'])
        self.active_connections_gauge = Gauge('composio_active_connections', 'Active connections')
        
        # System metrics
        self.cpu_usage_gauge = Gauge('composio_cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage_gauge = Gauge('composio_memory_usage_percent', 'Memory usage percentage')
        self.disk_usage_gauge = Gauge('composio_disk_usage_percent', 'Disk usage percentage')
        
        # Business metrics
        self.tools_used_counter = Counter('composio_tools_used_total', 'Tools usage', ['tool', 'user'])
        self.rate_limit_hits_counter = Counter('composio_rate_limit_hits_total', 'Rate limit hits', ['tool', 'user'])
        self.auth_failures_counter = Counter('composio_auth_failures_total', 'Authentication failures', ['reason'])
        
        # Performance metrics
        self.tool_execution_time = Summary('composio_tool_execution_seconds', 'Tool execution time', ['tool'])
    
    async def record_request(self, tool: str, user_id: str, status: str, response_time: float):
        """Record a request metric."""
        try:
            self.request_metrics["total_requests"] += 1
            
            if status == "success":
                self.request_metrics["successful_requests"] += 1
            else:
                self.request_metrics["failed_requests"] += 1
            
            # Update Prometheus metrics
            self.request_counter.labels(tool=tool, status=status).inc()
            self.response_time_histogram.labels(tool=tool).observe(response_time)
            
            # Track by tool
            if tool not in self.request_metrics["requests_by_tool"]:
                self.request_metrics["requests_by_tool"][tool] = 0
            self.request_metrics["requests_by_tool"][tool] += 1
            
            # Track by user
            if user_id not in self.request_metrics["requests_by_user"]:
                self.request_metrics["requests_by_user"][user_id] = 0
            self.request_metrics["requests_by_user"][user_id] += 1
            
            # Calculate moving average response time
            self.performance_metrics["response_time_history"].append(response_time)
            if len(self.performance_metrics["response_time_history"]) > 100:
                self.performance_metrics["response_time_history"].pop(0)
            
            self.request_metrics["average_response_time"] = sum(
                self.performance_metrics["response_time_history"]
            ) / len(self.performance_metrics["response_time_history"])
            
        except Exception as e:
            logger.error("Failed to record request metric", tool=tool, error=str(e))
    
    async def record_tool_usage(self, tool: str, user_id: str):
        """Record tool usage."""
        try:
            self.tools_used_counter.labels(tool=tool, user=user_id).inc()
        except Exception as e:
            logger.error("Failed to record tool usage", tool=tool, error=str(e))
    
    async def record_rate_limit_hit(self, tool: str, user_id: str):
        """Record rate limit hit."""
        try:
            self.rate_limit_hits_counter.labels(tool=tool, user=user_id).inc()
        except Exception as e:
            logger.error("Failed to record rate limit hit", tool=tool, error=str(e))
    
    async def record_auth_failure(self, reason: str):
        """Record authentication failure."""
        try:
            self.auth_failures_counter.labels(reason=reason).inc()
        except Exception as e:
            logger.error("Failed to record auth failure", reason=reason, error=str(e))
    
    async def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_usage_gauge.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_usage_gauge.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.disk_usage_gauge.set(disk_percent)
            
            # Store in history
            current_time = time.time()
            self.performance_metrics["cpu_usage_history"].append({
                "timestamp": current_time,
                "value": cpu_percent
            })
            
            self.performance_metrics["memory_usage_history"].append({
                "timestamp": current_time,
                "value": memory.percent
            })
            
            # Limit history size
            max_history = 1000
            for history_key in ["cpu_usage_history", "memory_usage_history"]:
                if len(self.performance_metrics[history_key]) > max_history:
                    self.performance_metrics[history_key] = self.performance_metrics[history_key][-max_history:]
            
        except Exception as e:
            logger.error("Failed to update system metrics", error=str(e))
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        try:
            # Get system metrics
            await self.update_system_metrics()
            
            # Calculate uptime
            uptime_seconds = time.time() - self.performance_metrics["start_time"]
            
            # Get error rate
            total_requests = self.request_metrics["total_requests"]
            failed_requests = self.request_metrics["failed_requests"]
            error_rate = (failed_requests / total_requests) if total_requests > 0 else 0
            
            # Get top tools
            top_tools = sorted(
                self.request_metrics["requests_by_tool"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Get top users
            top_users = sorted(
                self.request_metrics["requests_by_user"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Calculate system trends
            cpu_trend = self._calculate_trend("cpu_usage_history")
            memory_trend = self._calculate_trend("memory_usage_history")
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "server": {
                    "uptime_seconds": uptime_seconds,
                    "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
                    "version": "1.0.0",
                    "environment": self.settings.environment
                },
                "requests": {
                    "total": total_requests,
                    "successful": self.request_metrics["successful_requests"],
                    "failed": failed_requests,
                    "error_rate": round(error_rate * 100, 2),
                    "average_response_time": round(self.request_metrics["average_response_time"], 3),
                    "success_rate": round(((total_requests - failed_requests) / total_requests) * 100, 2) if total_requests > 0 else 100
                },
                "system": {
                    "cpu": {
                        "usage_percent": self._get_latest_value("cpu_usage_history"),
                        "trend": cpu_trend
                    },
                    "memory": {
                        "usage_percent": self._get_latest_value("memory_usage_history"),
                        "trend": memory_trend
                    },
                    "disk": {
                        "usage_percent": self._get_latest_value("disk_usage_history", default=0)
                    }
                },
                "top_tools": [{"tool": tool, "requests": count} for tool, count in top_tools],
                "top_users": [{"user": user, "requests": count} for user, count in top_users],
                "rate_limits": {
                    "total_hits": sum(
                        self.rate_limit_hits_counter._value.values()
                    ) if hasattr(self.rate_limit_hits_counter, '_value') else 0
                },
                "authentication": {
                    "total_failures": sum(
                        self.auth_failures_counter._value.values()
                    ) if hasattr(self.auth_failures_counter, '_value') else 0
                }
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get metrics", error=str(e))
            return {"error": str(e)}
    
    def _calculate_trend(self, history_key: str, window_size: int = 10) -> str:
        """Calculate trend direction for a metric."""
        try:
            history = self.performance_metrics.get(history_key, [])
            
            if len(history) < window_size:
                return "stable"
            
            recent_values = [entry["value"] for entry in history[-window_size:]]
            old_values = [entry["value"] for entry in history[-window_size*2:-window_size]]
            
            if not old_values:
                return "stable"
            
            recent_avg = sum(recent_values) / len(recent_values)
            old_avg = sum(old_values) / len(old_values)
            
            # Threshold for considering a trend significant
            threshold = 2.0
            
            if recent_avg > old_avg + threshold:
                return "increasing"
            elif recent_avg < old_avg - threshold:
                return "decreasing"
            else:
                return "stable"
                
        except Exception as e:
            logger.error("Failed to calculate trend", history_key=history_key, error=str(e))
            return "stable"
    
    def _get_latest_value(self, history_key: str, default: float = 0.0) -> float:
        """Get latest value from history."""
        try:
            history = self.performance_metrics.get(history_key, [])
            return history[-1]["value"] if history else default
        except Exception:
            return default
    
    async def get_detailed_analytics(self) -> Dict[str, Any]:
        """Get detailed analytics for the time period."""
        try:
            current_time = time.time()
            one_hour_ago = current_time - 3600
            one_day_ago = current_time - 86400
            
            # Calculate hourly stats
            hourly_requests = self.request_metrics["total_requests"]
            hourly_error_rate = (
                self.request_metrics["failed_requests"] / self.request_metrics["total_requests"]
                if self.request_metrics["total_requests"] > 0 else 0
            )
            
            # Calculate performance percentiles
            response_times = self.performance_metrics["response_time_history"]
            percentiles = {}
            
            if response_times:
                sorted_times = sorted(response_times)
                percentiles = {
                    "p50": round(sorted_times[int(len(sorted_times) * 0.5)], 3),
                    "p90": round(sorted_times[int(len(sorted_times) * 0.9)], 3),
                    "p95": round(sorted_times[int(len(sorted_times) * 0.95)], 3),
                    "p99": round(sorted_times[int(len(sorted_times) * 0.99)], 3)
                }
            
            # Tool performance analysis
            tool_performance = {}
            for tool, count in self.request_metrics["requests_by_tool"].items():
                tool_performance[tool] = {
                    "total_requests": count,
                    "usage_percentage": round((count / self.request_metrics["total_requests"]) * 100, 2) if self.request_metrics["total_requests"] > 0 else 0
                }
            
            # Resource utilization summary
            cpu_avg = self._calculate_average("cpu_usage_history")
            memory_avg = self._calculate_average("memory_usage_history")
            
            analytics = {
                "period": {
                    "start": datetime.fromtimestamp(one_day_ago).isoformat(),
                    "end": datetime.fromtimestamp(current_time).isoformat()
                },
                "requests": {
                    "total_last_24h": self.request_metrics["total_requests"],
                    "hourly_average": round(hourly_requests / 24, 1),
                    "peak_hourly": hourly_requests,  # Simplified - would track actual peaks
                    "error_rate_last_24h": round(hourly_error_rate * 100, 2)
                },
                "performance": {
                    "response_time_percentiles": percentiles,
                    "average_response_time": round(self.request_metrics["average_response_time"], 3)
                },
                "tools": {
                    "total_unique_tools": len(self.request_metrics["requests_by_tool"]),
                    "tool_performance": tool_performance,
                    "most_popular_tool": max(self.request_metrics["requests_by_tool"].items(), key=lambda x: x[1])[0] if self.request_metrics["requests_by_tool"] else None
                },
                "resources": {
                    "average_cpu_usage": round(cpu_avg, 2) if cpu_avg else 0,
                    "average_memory_usage": round(memory_avg, 2) if memory_avg else 0,
                    "peak_cpu_usage": max([entry["value"] for entry in self.performance_metrics["cpu_usage_history"]], default=0),
                    "peak_memory_usage": max([entry["value"] for entry in self.performance_metrics["memory_usage_history"]], default=0)
                },
                "security": {
                    "rate_limit_hits": sum(
                        self.rate_limit_hits_counter._value.values()
                    ) if hasattr(self.rate_limit_hits_counter, '_value') else 0,
                    "auth_failures": sum(
                        self.auth_failures_counter._value.values()
                    ) if hasattr(self.auth_failures_counter, '_value') else 0
                }
            }
            
            return analytics
            
        except Exception as e:
            logger.error("Failed to get detailed analytics", error=str(e))
            return {"error": str(e)}
    
    def _calculate_average(self, history_key: str) -> float:
        """Calculate average value from history."""
        try:
            history = self.performance_metrics.get(history_key, [])
            if not history:
                return 0.0
            
            values = [entry["value"] for entry in history]
            return sum(values) / len(values)
            
        except Exception as e:
            logger.error("Failed to calculate average", history_key=history_key, error=str(e))
            return 0.0
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        try:
            return generate_latest().decode('utf-8')
        except Exception as e:
            logger.error("Failed to export Prometheus metrics", error=str(e))
            return ""
    
    async def create_metrics_report(self) -> Dict[str, Any]:
        """Create a comprehensive metrics report."""
        try:
            basic_metrics = await self.get_metrics()
            detailed_analytics = await self.get_detailed_analytics()
            
            # Add recommendations based on metrics
            recommendations = await self._generate_recommendations(basic_metrics, detailed_analytics)
            
            report = {
                "report_id": f"metrics_report_{int(time.time())}",
                "generated_at": datetime.utcnow().isoformat(),
                "period": detailed_analytics.get("period", {}),
                "summary": {
                    "overall_health": self._assess_overall_health(basic_metrics),
                    "performance_score": self._calculate_performance_score(basic_metrics),
                    "security_status": self._assess_security_status(detailed_analytics)
                },
                "metrics": basic_metrics,
                "analytics": detailed_analytics,
                "recommendations": recommendations,
                "prometheus_format": self.export_prometheus_metrics()
            }
            
            return report
            
        except Exception as e:
            logger.error("Failed to create metrics report", error=str(e))
            return {"error": str(e)}
    
    async def _generate_recommendations(self, basic_metrics: Dict, detailed_analytics: Dict) -> List[str]:
        """Generate recommendations based on metrics analysis."""
        recommendations = []
        
        try:
            # Performance recommendations
            error_rate = basic_metrics.get("requests", {}).get("error_rate", 0)
            if error_rate > 5:
                recommendations.append("High error rate detected. Investigate failed requests and improve error handling.")
            
            avg_response_time = basic_metrics.get("requests", {}).get("average_response_time", 0)
            if avg_response_time > 2.0:
                recommendations.append("Slow response times detected. Consider optimizing tool implementations or scaling resources.")
            
            # System resource recommendations
            cpu_usage = basic_metrics.get("system", {}).get("cpu", {}).get("usage_percent", 0)
            if cpu_usage > 80:
                recommendations.append("High CPU usage detected. Consider scaling up or optimizing CPU-intensive operations.")
            
            memory_usage = basic_metrics.get("system", {}).get("memory", {}).get("usage_percent", 0)
            if memory_usage > 85:
                recommendations.append("High memory usage detected. Monitor for memory leaks and consider scaling.")
            
            # Security recommendations
            auth_failures = detailed_analytics.get("security", {}).get("auth_failures", 0)
            if auth_failures > 100:
                recommendations.append("High number of authentication failures detected. Review security policies and monitor for attacks.")
            
            rate_limit_hits = detailed_analytics.get("security", {}).get("rate_limit_hits", 0)
            if rate_limit_hits > 1000:
                recommendations.append("Frequent rate limit hits detected. Consider adjusting rate limits or optimizing client behavior.")
            
            # Tool usage recommendations
            tool_performance = detailed_analytics.get("tools", {}).get("tool_performance", {})
            for tool, stats in tool_performance.items():
                if stats.get("usage_percentage", 0) > 50:
                    recommendations.append(f"Tool '{tool}' is heavily used ({stats['usage_percentage']:.1f}%). Consider optimizing its performance.")
            
            if not recommendations:
                recommendations.append("System performance looks good. Continue monitoring and maintain current configuration.")
            
            return recommendations
            
        except Exception as e:
            logger.error("Failed to generate recommendations", error=str(e))
            return ["Unable to generate recommendations due to an error"]
    
    def _assess_overall_health(self, metrics: Dict[str, Any]) -> str:
        """Assess overall system health."""
        try:
            error_rate = metrics.get("requests", {}).get("error_rate", 0)
            cpu_usage = metrics.get("system", {}).get("cpu", {}).get("usage_percent", 0)
            memory_usage = metrics.get("system", {}).get("memory", {}).get("usage_percent", 0)
            
            # Define health criteria
            if error_rate > 10 or cpu_usage > 90 or memory_usage > 95:
                return "critical"
            elif error_rate > 5 or cpu_usage > 80 or memory_usage > 85:
                return "warning"
            elif error_rate > 1 or cpu_usage > 70 or memory_usage > 75:
                return "degraded"
            else:
                return "healthy"
                
        except Exception as e:
            logger.error("Failed to assess overall health", error=str(e))
            return "unknown"
    
    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)."""
        try:
            # Start with 100 points
            score = 100.0
            
            # Deduct for errors
            error_rate = metrics.get("requests", {}).get("error_rate", 0)
            score -= error_rate * 2  # -2 points per 1% error rate
            
            # Deduct for slow response times
            avg_response_time = metrics.get("requests", {}).get("average_response_time", 0)
            if avg_response_time > 1.0:
                score -= (avg_response_time - 1.0) * 10  # -10 points per second over 1s
            
            # Deduct for high resource usage
            cpu_usage = metrics.get("system", {}).get("cpu", {}).get("usage_percent", 0)
            if cpu_usage > 70:
                score -= (cpu_usage - 70) * 0.5
            
            memory_usage = metrics.get("system", {}).get("memory", {}).get("usage_percent", 0)
            if memory_usage > 70:
                score -= (memory_usage - 70) * 0.5
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error("Failed to calculate performance score", error=str(e))
            return 50.0
    
    def _assess_security_status(self, analytics: Dict[str, Any]) -> str:
        """Assess security status based on metrics."""
        try:
            auth_failures = analytics.get("security", {}).get("auth_failures", 0)
            rate_limit_hits = analytics.get("security", {}).get("rate_limit_hits", 0)
            
            if auth_failures > 1000 or rate_limit_hits > 10000:
                return "high_risk"
            elif auth_failures > 100 or rate_limit_hits > 1000:
                return "medium_risk"
            else:
                return "low_risk"
                
        except Exception as e:
            logger.error("Failed to assess security status", error=str(e))
            return "unknown"