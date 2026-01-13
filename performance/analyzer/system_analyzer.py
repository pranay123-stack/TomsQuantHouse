#!/usr/bin/env python3
"""
System Performance Analyzer
Analyzes system bottlenecks, performance metrics, and resource utilization
"""

import psutil
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import gc
from pathlib import Path

@dataclass
class SystemMetrics:
    """System performance metrics container"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    load_average: List[float]
    process_count: int
    thread_count: int
    open_files: int
    connections: int

@dataclass
class ApplicationMetrics:
    """Application-specific performance metrics"""
    timestamp: datetime
    response_time_p50: float
    response_time_p95: float
    response_time_p99: float
    requests_per_second: float
    error_rate: float
    active_connections: int
    cache_hit_rate: float
    database_query_time: float
    memory_usage_mb: float
    gc_collections: int
    gc_time_ms: float

@dataclass
class BottleneckAnalysis:
    """System bottleneck analysis results"""
    timestamp: datetime
    cpu_bottleneck: bool
    memory_bottleneck: bool
    disk_bottleneck: bool
    network_bottleneck: bool
    database_bottleneck: bool
    bottleneck_score: float
    recommendations: List[str]

class SystemPerformanceAnalyzer:
    """Comprehensive system performance analyzer"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics_history = []
        self.app_metrics_history = []
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        # Thresholds for bottleneck detection
        self.thresholds = config.get('thresholds', {
            'cpu_critical': 90,
            'cpu_warning': 75,
            'memory_critical': 85,
            'memory_warning': 70,
            'disk_critical': 90,
            'disk_warning': 80,
            'network_mbps_critical': 900,
            'network_mbps_warning': 700,
            'response_time_ms_critical': 5000,
            'response_time_ms_warning': 2000,
            'error_rate_critical': 0.05,
            'error_rate_warning': 0.02
        })
        
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read_mb = disk_io.read_bytes / (1024**2) if disk_io else 0
            disk_write_mb = disk_io.write_bytes / (1024**2) if disk_io else 0
            
            # Network I/O
            network_io = psutil.net_io_counters()
            network_sent_mb = network_io.bytes_sent / (1024**2) if network_io else 0
            network_recv_mb = network_io.bytes_recv / (1024**2) if network_io else 0
            
            # Process metrics
            process_count = len(psutil.pids())
            
            # Get current process info
            current_process = psutil.Process()
            thread_count = current_process.num_threads()
            open_files = len(current_process.open_files())
            
            # Network connections
            connections = len(psutil.net_connections())
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_gb=memory_used_gb,
                memory_available_gb=memory_available_gb,
                disk_usage_percent=disk_percent,
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_io_sent_mb=network_sent_mb,
                network_io_recv_mb=network_recv_mb,
                load_average=load_avg,
                process_count=process_count,
                thread_count=thread_count,
                open_files=open_files,
                connections=connections
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            raise
    
    def collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-specific metrics"""
        try:
            # Simulated application metrics - in production, these would come
            # from your application monitoring system (Prometheus, StatsD, etc.)
            
            # Import application-specific collectors if available
            try:
                from code.asymedge_api.api.routes import health
                from code.asymedge_api.api.services import streaming_service
                # Get actual metrics from your application
            except ImportError:
                pass
            
            # For now, generate realistic metrics based on system state
            system_metrics = self.get_latest_system_metrics()
            
            # Calculate derived metrics
            base_response_time = 100  # ms
            load_factor = (system_metrics.cpu_percent + system_metrics.memory_percent) / 200
            
            response_time_p50 = base_response_time * (1 + load_factor * 0.5)
            response_time_p95 = response_time_p50 * (2 + load_factor)
            response_time_p99 = response_time_p95 * (1.5 + load_factor)
            
            # Requests per second based on CPU load
            max_rps = 1000
            current_rps = max(0, max_rps - (load_factor * max_rps * 0.7))
            
            # Error rate based on system stress
            base_error_rate = 0.001
            error_rate = base_error_rate + (load_factor * 0.01)
            
            # Cache hit rate (inverse relationship with load)
            cache_hit_rate = max(0.5, 0.95 - load_factor * 0.3)
            
            # Database query time increases with load
            db_query_time = 50 * (1 + load_factor * 2)
            
            # Memory usage
            memory_usage_mb = system_metrics.memory_used_gb * 1024 * 0.1  # Assume 10% is app
            
            # Garbage collection metrics
            gc_collections = gc.get_count()[0]
            gc_time = 0  # Would need gc module metrics
            
            return ApplicationMetrics(
                timestamp=datetime.now(),
                response_time_p50=response_time_p50,
                response_time_p95=response_time_p95,
                response_time_p99=response_time_p99,
                requests_per_second=current_rps,
                error_rate=error_rate,
                active_connections=system_metrics.connections,
                cache_hit_rate=cache_hit_rate,
                database_query_time=db_query_time,
                memory_usage_mb=memory_usage_mb,
                gc_collections=gc_collections,
                gc_time_ms=gc_time
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting application metrics: {e}")
            raise
    
    def analyze_bottlenecks(self, system_metrics: SystemMetrics, 
                          app_metrics: ApplicationMetrics) -> BottleneckAnalysis:
        """Analyze system bottlenecks and generate recommendations"""
        
        bottlenecks = {
            'cpu': system_metrics.cpu_percent > self.thresholds['cpu_critical'],
            'memory': system_metrics.memory_percent > self.thresholds['memory_critical'],
            'disk': system_metrics.disk_usage_percent > self.thresholds['disk_critical'],
            'network': (system_metrics.network_io_sent_mb > self.thresholds['network_mbps_critical'] or
                       system_metrics.network_io_recv_mb > self.thresholds['network_mbps_critical']),
            'database': app_metrics.database_query_time > 1000,  # 1 second threshold
            'response_time': app_metrics.response_time_p95 > self.thresholds['response_time_ms_critical'],
            'error_rate': app_metrics.error_rate > self.thresholds['error_rate_critical']
        }
        
        # Calculate bottleneck score (0-100)
        active_bottlenecks = sum(bottlenecks.values())
        bottleneck_score = (active_bottlenecks / len(bottlenecks)) * 100
        
        # Generate recommendations
        recommendations = []
        
        if bottlenecks['cpu']:
            recommendations.append("Scale horizontally - add more CPU cores or instances")
            recommendations.append("Optimize CPU-intensive operations")
            recommendations.append("Consider vertical scaling - upgrade to higher CPU instances")
        
        if bottlenecks['memory']:
            recommendations.append("Scale vertically - increase RAM allocation")
            recommendations.append("Implement memory-efficient algorithms")
            recommendations.append("Add more memory instances or increase memory per instance")
            recommendations.append("Enable memory optimization in application settings")
        
        if bottlenecks['disk']:
            recommendations.append("Migrate to faster storage (SSD/NVMe)")
            recommendations.append("Implement disk optimization strategies")
            recommendations.append("Add more disk space or move to higher-tier storage")
        
        if bottlenecks['network']:
            recommendations.append("Optimize network-intensive operations")
            recommendations.append("Consider CDN for static content")
            recommendations.append("Upgrade network bandwidth")
            recommendations.append("Implement connection pooling")
        
        if bottlenecks['database']:
            recommendations.append("Optimize database queries")
            recommendations.append("Add database indexes")
            recommendations.append("Scale database vertically or horizontally")
            recommendations.append("Implement database connection pooling")
        
        if bottlenecks['response_time']:
            recommendations.append("Implement caching strategies")
            recommendations.append("Optimize application code")
            recommendations.append("Scale horizontally to distribute load")
        
        if bottlenecks['error_rate']:
            recommendations.append("Investigate and fix application errors")
            recommendations.append("Implement circuit breakers")
            recommendations.append("Add health checks and monitoring")
        
        return BottleneckAnalysis(
            timestamp=datetime.now(),
            cpu_bottleneck=bottlenecks['cpu'],
            memory_bottleneck=bottlenecks['memory'],
            disk_bottleneck=bottlenecks['disk'],
            network_bottleneck=bottlenecks['network'],
            database_bottleneck=bottlenecks['database'],
            bottleneck_score=bottleneck_score,
            recommendations=recommendations
        )
    
    def get_performance_trends(self, hours: int = 24) -> Dict:
        """Analyze performance trends over time"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter recent metrics
        recent_system = [m for m in self.metrics_history if m.timestamp > cutoff_time]
        recent_app = [m for m in self.app_metrics_history if m.timestamp > cutoff_time]
        
        if not recent_system or not recent_app:
            return {"error": "Insufficient historical data"}
        
        # Calculate trends
        trends = {
            'cpu_trend': self._calculate_trend([m.cpu_percent for m in recent_system]),
            'memory_trend': self._calculate_trend([m.memory_percent for m in recent_system]),
            'response_time_trend': self._calculate_trend([m.response_time_p95 for m in recent_app]),
            'error_rate_trend': self._calculate_trend([m.error_rate for m in recent_app]),
            'throughput_trend': self._calculate_trend([m.requests_per_second for m in recent_app])
        }
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for a series of values"""
        if len(values) < 2:
            return "stable"
        
        # Simple linear trend calculation
        recent_avg = sum(values[-5:]) / min(len(values), 5)  # Last 5 values
        older_avg = sum(values[:5]) / min(len(values), 5) if len(values) > 5 else values[0]
        
        change_percent = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
        
        if change_percent > 10:
            return "increasing"
        elif change_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    def start_monitoring(self, interval: int = 60):
        """Start continuous performance monitoring"""
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        
        def monitor_loop():
            while self.monitoring_active:
                try:
                    system_metrics = self.collect_system_metrics()
                    app_metrics = self.collect_application_metrics()
                    
                    with self.lock:
                        self.metrics_history.append(system_metrics)
                        self.app_metrics_history.append(app_metrics)
                        
                        # Keep only last 1000 entries to prevent memory issues
                        if len(self.metrics_history) > 1000:
                            self.metrics_history = self.metrics_history[-1000:]
                        if len(self.app_metrics_history) > 1000:
                            self.app_metrics_history = self.app_metrics_history[-1000:]
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(interval)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous performance monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Performance monitoring stopped")
    
    def get_latest_system_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recent system metrics"""
        with self.lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_latest_app_metrics(self) -> Optional[ApplicationMetrics]:
        """Get the most recent application metrics"""
        with self.lock:
            return self.app_metrics_history[-1] if self.app_metrics_history else None
    
    def get_current_bottleneck_analysis(self) -> Optional[BottleneckAnalysis]:
        """Get current bottleneck analysis"""
        system_metrics = self.get_latest_system_metrics()
        app_metrics = self.get_latest_app_metrics()
        
        if not system_metrics or not app_metrics:
            return None
        
        return self.analyze_bottlenecks(system_metrics, app_metrics)
    
    def export_metrics(self, filepath: str, format: str = 'json'):
        """Export metrics to file"""
        with self.lock:
            data = {
                'system_metrics': [asdict(m) for m in self.metrics_history],
                'application_metrics': [asdict(m) for m in self.app_metrics_history],
                'export_timestamp': datetime.now().isoformat()
            }
        
        if format.lower() == 'json':
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        self.logger.info(f"Metrics exported to {filepath}")

def main():
    """Example usage and testing"""
    import yaml
    
    # Load configuration
    config_path = Path(__file__).parent.parent / 'config' / 'performance_config.yaml'
    if config_path.exists():
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {
            'thresholds': {
                'cpu_critical': 90,
                'cpu_warning': 75,
                'memory_critical': 85,
                'memory_warning': 70,
                'disk_critical': 90,
                'disk_warning': 80,
                'response_time_ms_critical': 5000,
                'response_time_ms_warning': 2000,
                'error_rate_critical': 0.05,
                'error_rate_warning': 0.02
            }
        }
    
    # Initialize analyzer
    analyzer = SystemPerformanceAnalyzer(config)
    
    print("System Performance Analyzer")
    print("=" * 50)
    
    # Collect single metrics sample
    try:
        print("Collecting system metrics...")
        system_metrics = analyzer.collect_system_metrics()
        print(f"CPU Usage: {system_metrics.cpu_percent:.1f}%")
        print(f"Memory Usage: {system_metrics.memory_percent:.1f}%")
        print(f"Disk Usage: {system_metrics.disk_usage_percent:.1f}%")
        
        print("\nCollecting application metrics...")
        app_metrics = analyzer.collect_application_metrics()
        print(f"Response Time P95: {app_metrics.response_time_p95:.1f}ms")
        print(f"Requests/Second: {app_metrics.requests_per_second:.1f}")
        print(f"Error Rate: {app_metrics.error_rate:.2%}")
        
        print("\nAnalyzing bottlenecks...")
        bottleneck_analysis = analyzer.analyze_bottlenecks(system_metrics, app_metrics)
        print(f"Bottleneck Score: {bottleneck_analysis.bottleneck_score:.1f}")
        print("Recommendations:")
        for rec in bottleneck_analysis.recommendations:
            print(f"  - {rec}")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    # Start monitoring for a short period (demo)
    print("\nStarting monitoring for 30 seconds...")
    analyzer.start_monitoring(interval=5)
    time.sleep(30)
    analyzer.stop_monitoring()
    
    # Export metrics
    export_path = Path(__file__).parent / 'exports' / 'metrics_export.json'
    export_path.parent.mkdir(exist_ok=True)
    analyzer.export_metrics(str(export_path))
    print(f"\nMetrics exported to {export_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()