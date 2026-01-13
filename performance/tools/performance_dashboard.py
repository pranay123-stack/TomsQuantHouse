#!/usr/bin/env python3
"""
Performance Monitoring Dashboard
Real-time monitoring and visualization of performance metrics
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import asdict
from pathlib import Path
import argparse
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

class PerformanceDashboard:
    """Real-time performance monitoring dashboard"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Data storage
        self.metrics_history = {
            'system': [],
            'application': [],
            'database': [],
            'cache': [],
            'load_balancer': [],
            'containers': []
        }
        
        # Import modules
        self._initialize_modules()
        
        # Dashboard settings
        self.update_interval = config.get('update_interval', 5)  # seconds
        self.history_retention = config.get('history_retention', 3600)  # seconds
        self.max_history_size = config.get('max_history_size', 1000)
    
    def _initialize_modules(self):
        """Initialize performance monitoring modules"""
        try:
            from analyzer.system_analyzer import SystemPerformanceAnalyzer
            from database.db_optimizer import DatabaseOptimizer
            from caching.cache_manager import MultiLevelCache
            from loadbalancing.intelligent_router import IntelligentLoadBalancer
            from containers.container_optimizer import ContainerOrchestrator
            
            self.system_analyzer = SystemPerformanceAnalyzer
            self.db_optimizer = DatabaseOptimizer
            self.cache_manager = MultiLevelCache
            self.load_balancer = IntelligentLoadBalancer
            self.container_optimizer = ContainerOrchestrator
            
        except ImportError as e:
            self.logger.warning(f"Some modules may not be available: {e}")
    
    async def start_monitoring(self):
        """Start continuous performance monitoring"""
        self.logger.info("Starting performance monitoring dashboard")
        
        monitoring_tasks = [
            asyncio.create_task(self._monitor_system_metrics()),
            asyncio.create_task(self._monitor_application_metrics()),
            asyncio.create_task(self._monitor_database_metrics()),
            asyncio.create_task(self._monitor_cache_metrics()),
            asyncio.create_task(self._monitor_load_balancer_metrics()),
            asyncio.create_task(self._monitor_container_metrics()),
            asyncio.create_task(self._display_dashboard())
        ]
        
        try:
            await asyncio.gather(*monitoring_tasks)
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
    
    async def _monitor_system_metrics(self):
        """Monitor system performance metrics"""
        try:
            config = self._get_system_config()
            analyzer = self.system_analyzer(config)
            
            while True:
                try:
                    # Collect system metrics
                    system_metrics = analyzer.collect_system_metrics()
                    app_metrics = analyzer.collect_application_metrics()
                    bottleneck_analysis = analyzer.analyze_bottlenecks(system_metrics, app_metrics)
                    
                    # Store metrics
                    metric_data = {
                        'timestamp': datetime.now(),
                        'cpu_percent': system_metrics.cpu_percent,
                        'memory_percent': system_metrics.memory_percent,
                        'disk_percent': system_metrics.disk_usage_percent,
                        'network_io': system_metrics.network_io_sent_mb + system_metrics.network_io_recv_mb,
                        'bottleneck_score': bottleneck_analysis.bottleneck_score,
                        'response_time_p95': app_metrics.response_time_p95,
                        'requests_per_second': app_metrics.requests_per_second,
                        'error_rate': app_metrics.error_rate
                    }
                    
                    self._store_metric('system', metric_data)
                    await asyncio.sleep(self.update_interval)
                    
                except Exception as e:
                    self.logger.error(f"System metrics collection error: {e}")
                    await asyncio.sleep(self.update_interval)
                    
        except Exception as e:
            self.logger.error(f"System monitoring initialization failed: {e}")
    
    async def _monitor_application_metrics(self):
        """Monitor application-specific metrics"""
        while True:
            try:
                # Simulate application metrics collection
                # In practice, this would integrate with your application
                metric_data = {
                    'timestamp': datetime.now(),
                    'active_sessions': 150 + int(time.time() % 100),
                    'queue_depth': int(time.time() % 50),
                    'worker_threads': 8,
                    'cache_hit_rate': 0.85 + (time.time() % 0.1),
                    'api_response_time': 150 + (time.time() % 200),
                    'business_metrics': {
                        'transactions_per_minute': int(time.time() % 60),
                        'success_rate': 0.95 + (time.time() % 0.05)
                    }
                }
                
                self._store_metric('application', metric_data)
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Application metrics error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _monitor_database_metrics(self):
        """Monitor database performance metrics"""
        while True:
            try:
                # Simulate database metrics
                metric_data = {
                    'timestamp': datetime.now(),
                    'active_connections': 20 + int(time.time() % 30),
                    'query_time_avg': 50 + (time.time() % 100),
                    'query_time_p95': 200 + (time.time() % 300),
                    'slow_queries': int(time.time() % 5),
                    'cache_hit_rate': 0.90 + (time.time() % 0.1),
                    'table_locks': int(time.time() % 10),
                    'deadlocks': int(time.time() % 2)
                }
                
                self._store_metric('database', metric_data)
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Database metrics error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _monitor_cache_metrics(self):
        """Monitor cache performance metrics"""
        while True:
            try:
                # Simulate cache metrics
                metric_data = {
                    'timestamp': datetime.now(),
                    'hit_rate': 0.85 + (time.time() % 0.15),
                    'miss_rate': 1 - (0.85 + (time.time() % 0.15)),
                    'memory_usage_mb': 100 + (time.time() % 200),
                    'evictions': int(time.time() % 10),
                    'cache_size': 10000 + int(time.time() % 1000),
                    'response_time_ms': 1 + (time.time() % 5)
                }
                
                self._store_metric('cache', metric_data)
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Cache metrics error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _monitor_load_balancer_metrics(self):
        """Monitor load balancer metrics"""
        while True:
            try:
                # Simulate load balancer metrics
                metric_data = {
                    'timestamp': datetime.now(),
                    'total_requests': int(time.time() * 100) % 10000,
                    'requests_per_second': 50 + int(time.time() % 200),
                    'response_time_avg': 100 + (time.time() % 50),
                    'active_connections': 20 + int(time.time() % 50),
                    'backend_health': [0.95, 0.98, 0.92][int(time.time()) % 3],
                    'error_rate': (time.time() % 0.02),
                    'algorithm': 'round_robin'
                }
                
                self._store_metric('load_balancer', metric_data)
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Load balancer metrics error: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _monitor_container_metrics(self):
        """Monitor container performance metrics"""
        while True:
            try:
                # Simulate container metrics
                metric_data = {
                    'timestamp': datetime.now(),
                    'container_count': 5 + int(time.time() % 3),
                    'total_cpu_cores': 16,
                    'cpu_utilization_percent': 60 + (time.time() % 30),
                    'memory_total_gb': 32,
                    'memory_utilization_percent': 70 + (time.time() % 20),
                    'disk_utilization_percent': 45 + (time.time() % 10),
                    'network_throughput_mbps': 100 + (time.time() % 200)
                }
                
                self._store_metric('containers', metric_data)
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Container metrics error: {e}")
                await asyncio.sleep(self.update_interval)
    
    def _store_metric(self, category: str, metric_data: Dict[str, Any]):
        """Store metric data with history management"""
        if category not in self.metrics_history:
            self.metrics_history[category] = []
        
        self.metrics_history[category].append(metric_data)
        
        # Maintain history size limit
        if len(self.metrics_history[category]) > self.max_history_size:
            self.metrics_history[category] = self.metrics_history[category][-self.max_history_size:]
    
    def _get_system_config(self) -> Dict[str, Any]:
        """Get system analyzer configuration"""
        return {
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
    
    async def _display_dashboard(self):
        """Display real-time performance dashboard"""
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')
        
        while True:
            try:
                self._clear_screen()
                self._print_header()
                
                # Display metrics for each category
                for category, metrics in self.metrics_history.items():
                    if metrics:
                        self._print_category_metrics(category, metrics[-1])
                
                # Display alerts and recommendations
                self._display_alerts()
                
                # Display system summary
                self._display_summary()
                
                await asyncio.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Dashboard display error: {e}")
                await asyncio.sleep(self.update_interval)
    
    def _clear_screen(self):
        """Clear the terminal screen"""
        if hasattr(os, 'system'):
            os.system('clear' if os.name == 'posix' else 'cls')
    
    def _print_header(self):
        """Print dashboard header"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print("=" * 80)
        print("🚀 PERFORMANCE OPTIMIZATION DASHBOARD 🚀")
        print(f"📅 Last Updated: {current_time}")
        print("=" * 80)
    
    def _print_category_metrics(self, category: str, metrics: Dict[str, Any]):
        """Print metrics for a specific category"""
        category_names = {
            'system': '🖥️  SYSTEM PERFORMANCE',
            'application': '⚡ APPLICATION METRICS',
            'database': '🗄️  DATABASE PERFORMANCE',
            'cache': '💾 CACHE PERFORMANCE',
            'load_balancer': '⚖️  LOAD BALANCER',
            'containers': '🐳 CONTAINER METRICS'
        }
        
        print(f"\n{category_names.get(category, category.upper())}")
        print("-" * 60)
        
        if category == 'system':
            self._print_metric_line("CPU Usage", f"{metrics.get('cpu_percent', 0):.1f}%")
            self._print_metric_line("Memory Usage", f"{metrics.get('memory_percent', 0):.1f}%")
            self._print_metric_line("Disk Usage", f"{metrics.get('disk_percent', 0):.1f}%")
            self._print_metric_line("Network I/O", f"{metrics.get('network_io', 0):.1f} MB")
            self._print_metric_line("Bottleneck Score", f"{metrics.get('bottleneck_score', 0):.1f}")
            
        elif category == 'application':
            self._print_metric_line("Active Sessions", str(metrics.get('active_sessions', 0)))
            self._print_metric_line("Queue Depth", str(metrics.get('queue_depth', 0)))
            self._print_metric_line("API Response Time", f"{metrics.get('api_response_time', 0):.1f} ms")
            self._print_metric_line("Cache Hit Rate", f"{metrics.get('cache_hit_rate', 0):.1%}")
            self._print_metric_line("Error Rate", f"{metrics.get('error_rate', 0):.2%}")
            
        elif category == 'database':
            self._print_metric_line("Active Connections", str(metrics.get('active_connections', 0)))
            self._print_metric_line("Avg Query Time", f"{metrics.get('query_time_avg', 0):.1f} ms")
            self._print_metric_line("P95 Query Time", f"{metrics.get('query_time_p95', 0):.1f} ms")
            self._print_metric_line("Slow Queries", str(metrics.get('slow_queries', 0)))
            self._print_metric_line("Cache Hit Rate", f"{metrics.get('cache_hit_rate', 0):.1%}")
            
        elif category == 'cache':
            self._print_metric_line("Hit Rate", f"{metrics.get('hit_rate', 0):.1%}")
            self._print_metric_line("Memory Usage", f"{metrics.get('memory_usage_mb', 0):.0f} MB")
            self._print_metric_line("Evictions", str(metrics.get('evictions', 0)))
            self._print_metric_line("Response Time", f"{metrics.get('response_time_ms', 0):.1f} ms")
            
        elif category == 'load_balancer':
            self._print_metric_line("Requests/Second", str(metrics.get('requests_per_second', 0)))
            self._print_metric_line("Avg Response Time", f"{metrics.get('response_time_avg', 0):.1f} ms")
            self._print_metric_line("Active Connections", str(metrics.get('active_connections', 0)))
            self._print_metric_line("Backend Health", f"{metrics.get('backend_health', 0):.1%}")
            self._print_metric_line("Error Rate", f"{metrics.get('error_rate', 0):.3%}")
            
        elif category == 'containers':
            self._print_metric_line("Container Count", str(metrics.get('container_count', 0)))
            self._print_metric_line("CPU Utilization", f"{metrics.get('cpu_utilization_percent', 0):.1f}%")
            self._print_metric_line("Memory Utilization", f"{metrics.get('memory_utilization_percent', 0):.1f}%")
            self._print_metric_line("Disk Utilization", f"{metrics.get('disk_utilization_percent', 0):.1f}%")
            self._print_metric_line("Network Throughput", f"{metrics.get('network_throughput_mbps', 0):.1f} Mbps")
    
    def _print_metric_line(self, label: str, value: str, status: str = None):
        """Print a formatted metric line"""
        if status is None:
            status = self._get_status_from_value(label, value)
        
        status_symbols = {
            'good': '✅',
            'warning': '⚠️',
            'critical': '🚨',
            'unknown': '❓'
        }
        
        symbol = status_symbols.get(status, '❓')
        print(f"  {symbol} {label:<20} : {value}")
    
    def _get_status_from_value(self, label: str, value: str) -> str:
        """Determine status based on metric value"""
        try:
            numeric_value = float(value.replace('%', '').replace('ms', '').replace('MB', '').replace('Mbps', ''))
            
            if 'CPU' in label or 'Memory' in label:
                if numeric_value > 85:
                    return 'critical'
                elif numeric_value > 70:
                    return 'warning'
                else:
                    return 'good'
            elif 'Response Time' in label:
                if numeric_value > 1000:
                    return 'critical'
                elif numeric_value > 500:
                    return 'warning'
                else:
                    return 'good'
            elif 'Error Rate' in label or 'hit_rate' in label.lower():
                if numeric_value > 0.05 or numeric_value < 0.8:
                    return 'critical'
                elif numeric_value > 0.02 or numeric_value < 0.9:
                    return 'warning'
                else:
                    return 'good'
            else:
                return 'good'
                
        except (ValueError, AttributeError):
            return 'unknown'
    
    def _display_alerts(self):
        """Display performance alerts and recommendations"""
        print(f"\n🚨 ALERTS & RECOMMENDATIONS")
        print("-" * 60)
        
        alerts = self._generate_alerts()
        
        if alerts:
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("  ✅ No critical alerts at this time")
    
    def _generate_alerts(self) -> List[str]:
        """Generate performance alerts based on current metrics"""
        alerts = []
        
        # Check system metrics
        if self.metrics_history['system']:
            latest_system = self.metrics_history['system'][-1]
            
            if latest_system.get('cpu_percent', 0) > 85:
                alerts.append("🔴 High CPU usage detected - Consider scaling horizontally")
            
            if latest_system.get('memory_percent', 0) > 85:
                alerts.append("🔴 High memory usage detected - Scale up or optimize memory usage")
            
            if latest_system.get('bottleneck_score', 0) > 70:
                alerts.append("🟡 System bottlenecks detected - Review performance optimization recommendations")
        
        # Check application metrics
        if self.metrics_history['application']:
            latest_app = self.metrics_history['application'][-1]
            
            if latest_app.get('error_rate', 0) > 0.02:
                alerts.append("🟡 High error rate detected - Investigate application errors")
            
            if latest_app.get('api_response_time', 0) > 1000:
                alerts.append("🟡 High API response time - Consider caching or optimization")
        
        # Check database metrics
        if self.metrics_history['database']:
            latest_db = self.metrics_history['database'][-1]
            
            if latest_db.get('slow_queries', 0) > 5:
                alerts.append("🟡 Multiple slow queries detected - Optimize database queries")
            
            if latest_db.get('query_time_avg', 0) > 200:
                alerts.append("🟡 High average query time - Consider database optimization")
        
        return alerts[:5]  # Limit to 5 alerts
    
    def _display_summary(self):
        """Display system summary"""
        print(f"\n📊 SYSTEM SUMMARY")
        print("-" * 60)
        
        total_metrics = sum(len(metrics) for metrics in self.metrics_history.values())
        
        # Calculate overall health score
        health_score = self._calculate_overall_health_score()
        
        status_emoji = "🟢" if health_score > 80 else "🟡" if health_score > 60 else "🔴"
        
        print(f"  {status_emoji} Overall Health Score: {health_score:.1f}/100")
        print(f"  📈 Total Metrics Collected: {total_metrics}")
        print(f"  🕐 Dashboard Uptime: {self._get_uptime()}")
        print(f"  🔄 Update Interval: {self.update_interval}s")
    
    def _calculate_overall_health_score(self) -> float:
        """Calculate overall system health score"""
        scores = []
        
        # System score
        if self.metrics_history['system']:
            latest = self.metrics_history['system'][-1]
            cpu_score = max(0, 100 - latest.get('cpu_percent', 0))
            memory_score = max(0, 100 - latest.get('memory_percent', 0))
            system_score = (cpu_score + memory_score) / 2
            scores.append(system_score)
        
        # Application score
        if self.metrics_history['application']:
            latest = self.metrics_history['application'][-1]
            response_score = max(0, 100 - (latest.get('api_response_time', 0) / 10))
            error_score = max(0, 100 - (latest.get('error_rate', 0) * 1000))
            app_score = (response_score + error_score) / 2
            scores.append(app_score)
        
        # Cache score
        if self.metrics_history['cache']:
            latest = self.metrics_history['cache'][-1]
            cache_score = latest.get('hit_rate', 0) * 100
            scores.append(cache_score)
        
        return sum(scores) / len(scores) if scores else 50.0
    
    def _get_uptime(self) -> str:
        """Get dashboard uptime"""
        # This would track actual start time in practice
        return "Unknown"  # Simplified for demo
    
    def export_metrics(self, filepath: str):
        """Export all collected metrics to file"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'metrics_history': self.metrics_history,
            'dashboard_config': self.config
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Metrics exported to {filepath}")

def create_dashboard_config() -> Dict[str, Any]:
    """Create default dashboard configuration"""
    return {
        'update_interval': 5,
        'history_retention': 3600,
        'max_history_size': 1000,
        'alert_thresholds': {
            'cpu_critical': 85,
            'memory_critical': 85,
            'response_time_critical': 1000,
            'error_rate_critical': 0.02
        },
        'display_options': {
            'show_alerts': True,
            'show_summary': True,
            'color_output': True
        }
    }

def main():
    """Main entry point for performance dashboard"""
    parser = argparse.ArgumentParser(description="Performance Monitoring Dashboard")
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--export', help='Export metrics to file')
    parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds')
    parser.add_argument('--duration', type=int, help='Run for specified duration (seconds)')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Load configuration
    config = create_dashboard_config()
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config.update(json.load(f))
        except Exception as e:
            logging.warning(f"Failed to load config: {e}")
    
    # Update config with command line arguments
    config['update_interval'] = args.interval
    
    # Initialize dashboard
    dashboard = PerformanceDashboard(config)
    
    async def run_dashboard():
        try:
            # Export metrics at the end if specified
            if args.export:
                def export_after_duration():
                    time.sleep(args.duration)
                    dashboard.export_metrics(args.export)
                
                import threading
                export_thread = threading.Thread(target=export_after_duration, daemon=True)
                export_thread.start()
            
            # Run dashboard
            await dashboard.start_monitoring()
            
        except KeyboardInterrupt:
            print("\nDashboard stopped by user")
        except Exception as e:
            logging.error(f"Dashboard error: {e}")
    
    # Run the dashboard
    asyncio.run(run_dashboard())

if __name__ == "__main__":
    main()