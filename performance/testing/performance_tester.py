#!/usr/bin/env python3
"""
Performance Testing and Benchmark Validation
Implements comprehensive performance testing, benchmarking, and validation tools
"""

import asyncio
import time
import statistics
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import aiofiles
import numpy as np
from pathlib import Path
import concurrent.futures
import threading
from urllib.parse import urljoin
import csv
import yaml

class TestType(Enum):
    """Performance test types"""
    LOAD_TEST = "load_test"
    STRESS_TEST = "stress_test"
    SPIKE_TEST = "spike_test"
    ENDURANCE_TEST = "endurance_test"
    VOLUME_TEST = "volume_test"
    BENCHMARK = "benchmark"

class MetricType(Enum):
    """Performance metric types"""
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    CONCURRENT_USERS = "concurrent_users"

@dataclass
class TestConfiguration:
    """Performance test configuration"""
    test_id: str
    test_type: TestType
    target_url: str
    concurrent_users: int
    test_duration: int  # seconds
    ramp_up_time: int  # seconds
    ramp_down_time: int  # seconds
    max_requests_per_second: Optional[int] = None
    request_delay: float = 0  # seconds between requests
    timeout: float = 30  # seconds
    headers: Dict[str, str] = None
    payload: Dict[str, Any] = None
    endpoints: List[str] = None

@dataclass
class TestResult:
    """Individual test result"""
    timestamp: datetime
    url: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    bytes_sent: int = 0
    bytes_received: int = 0

@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics"""
    test_id: str
    test_type: TestType
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    average_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    peak_concurrent_users: int
    error_rate: float
    total_bytes_transferred: int

@dataclass
class BenchmarkResult:
    """Benchmark comparison result"""
    metric_name: str
    current_value: float
    baseline_value: float
    improvement_percent: float
    status: str  # 'improved', 'degraded', 'unchanged'
    threshold_percent: float = 5.0

class PerformanceTester:
    """Comprehensive performance testing framework"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Test tracking
        self.active_tests = {}
        self.test_results = {}
        self.benchmarks = {}
        
        # Performance tracking
        self.request_semaphore = asyncio.Semaphore(100)  # Max concurrent requests
        
        # System monitoring during tests
        self.system_monitor = SystemMonitor()
    
    async def run_load_test(self, test_config: TestConfiguration) -> PerformanceMetrics:
        """Run a load test"""
        self.logger.info(f"Starting load test: {test_config.test_id}")
        
        # Initialize test tracking
        self.active_tests[test_config.test_id] = {
            'start_time': datetime.now(),
            'config': test_config,
            'status': 'running'
        }
        
        try:
            # Start system monitoring
            await self.system_monitor.start_monitoring()
            
            # Prepare test endpoints
            endpoints = test_config.endpoints or ['/']
            methods = ['GET'] * len(endpoints)
            
            # Calculate request distribution
            total_test_time = test_config.test_duration + test_config.ramp_up_time + test_config.ramp_down_time
            requests_per_endpoint = (test_config.concurrent_users * total_test_time) // len(endpoints)
            
            # Start load generation
            tasks = []
            for i in range(test_config.concurrent_users):
                task = asyncio.create_task(
                    self._load_test_worker(
                        test_config,
                        endpoints,
                        methods,
                        test_config.ramp_up_time,
                        test_config.test_duration,
                        test_config.ramp_down_time
                    )
                )
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Calculate metrics
            test_results = self.test_results.get(test_config.test_id, [])
            metrics = self._calculate_performance_metrics(test_config, test_results)
            
            # Stop system monitoring
            await self.system_monitor.stop_monitoring()
            
            # Store results
            self.test_results[test_config.test_id] = test_results
            
            self.logger.info(f"Load test completed: {test_config.test_id}")
            return metrics
            
        except Exception as e:
            self.logger.error(f"Load test failed: {e}")
            raise
        finally:
            self.active_tests[test_config.test_id]['status'] = 'completed'
    
    async def _load_test_worker(self, config: TestConfiguration, endpoints: List[str], 
                               methods: List[str], ramp_up: int, test_duration: int, 
                               ramp_down: int):
        """Individual load test worker"""
        worker_id = id(threading.current_thread())
        
        # Ramp up phase
        if ramp_up > 0:
            await asyncio.sleep(ramp_up)
        
        # Test phase
        start_time = time.time()
        end_time = start_time + test_duration
        
        while time.time() < end_time:
            try:
                # Select random endpoint
                endpoint = np.random.choice(endpoints)
                method = methods[endpoints.index(endpoint)]
                
                # Make request
                result = await self._make_request(
                    config.target_url,
                    endpoint,
                    method,
                    config.headers,
                    config.payload,
                    config.timeout
                )
                
                # Store result
                if config.test_id not in self.test_results:
                    self.test_results[config.test_id] = []
                self.test_results[config.test_id].append(result)
                
                # Delay between requests if specified
                if config.request_delay > 0:
                    await asyncio.sleep(config.request_delay)
                    
            except Exception as e:
                self.logger.debug(f"Request failed in worker {worker_id}: {e}")
            
        # Ramp down phase
        if ramp_down > 0:
            await asyncio.sleep(ramp_down)
    
    async def _make_request(self, base_url: str, endpoint: str, method: str, 
                          headers: Dict[str, str] = None, payload: Dict[str, Any] = None,
                          timeout: float = 30) -> TestResult:
        """Make a single HTTP request and measure performance"""
        url = urljoin(base_url, endpoint)
        
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                if method.upper() == 'GET':
                    async with session.get(url, headers=headers) as response:
                        content = await response.read()
                        response_time = (time.time() - start_time) * 1000
                        
                        return TestResult(
                            timestamp=datetime.now(),
                            url=url,
                            method=method,
                            status_code=response.status,
                            response_time_ms=response_time,
                            success=200 <= response.status < 400,
                            bytes_sent=len(method) + len(url),  # Simplified
                            bytes_received=len(content)
                        )
                        
                elif method.upper() == 'POST':
                    async with session.post(url, headers=headers, json=payload) as response:
                        content = await response.read()
                        response_time = (time.time() - start_time) * 1000
                        
                        return TestResult(
                            timestamp=datetime.now(),
                            url=url,
                            method=method,
                            status_code=response.status,
                            response_time_ms=response_time,
                            success=200 <= response.status < 400,
                            bytes_sent=len(json.dumps(payload)) if payload else 0,
                            bytes_received=len(content)
                        )
                        
                else:
                    # For other methods, simplify
                    response_time = (time.time() - start_time) * 1000
                    return TestResult(
                        timestamp=datetime.now(),
                        url=url,
                        method=method,
                        status_code=200,
                        response_time_ms=response_time,
                        success=True,
                        bytes_sent=len(method) + len(url),
                        bytes_received=0
                    )
                    
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return TestResult(
                timestamp=datetime.now(),
                url=url,
                method=method,
                status_code=408,
                response_time_ms=response_time,
                success=False,
                error_message="Request timeout"
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return TestResult(
                timestamp=datetime.now(),
                url=url,
                method=method,
                status_code=0,
                response_time_ms=response_time,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_performance_metrics(self, config: TestConfiguration, 
                                     results: List[TestResult]) -> PerformanceMetrics:
        """Calculate aggregated performance metrics"""
        
        if not results:
            return PerformanceMetrics(
                test_id=config.test_id,
                test_type=config.test_type,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                success_rate=0,
                average_response_time=0,
                median_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                min_response_time=0,
                max_response_time=0,
                requests_per_second=0,
                peak_concurrent_users=0,
                error_rate=1.0,
                total_bytes_transferred=0
            )
        
        # Basic counts
        total_requests = len(results)
        successful_requests = len([r for r in results if r.success])
        failed_requests = total_requests - successful_requests
        
        # Success and error rates
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0
        
        # Response time statistics
        response_times = [r.response_time_ms for r in results if r.success]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = np.percentile(response_times, 95)
            p99_response_time = np.percentile(response_times, 99)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
            min_response_time = max_response_time = 0
        
        # Throughput
        test_duration = config.test_duration
        requests_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        # Peak concurrent users (estimated)
        peak_concurrent_users = config.concurrent_users
        
        # Total bytes transferred
        total_bytes_transferred = sum(r.bytes_sent + r.bytes_received for r in results)
        
        return PerformanceMetrics(
            test_id=config.test_id,
            test_type=config.test_type,
            start_time=min(r.timestamp for r in results),
            end_time=max(r.timestamp for r in results),
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            average_response_time=avg_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            requests_per_second=requests_per_second,
            peak_concurrent_users=peak_concurrent_users,
            error_rate=error_rate,
            total_bytes_transferred=total_bytes_transferred
        )
    
    async def run_stress_test(self, test_config: TestConfiguration) -> PerformanceMetrics:
        """Run a stress test with increasing load"""
        self.logger.info(f"Starting stress test: {test_config.test_id}")
        
        # Stress test configuration
        initial_users = test_config.concurrent_users // 4
        max_users = test_config.concurrent_users
        step_size = test_config.concurrent_users // 10
        step_duration = test_config.test_duration // 5
        
        stress_results = []
        
        current_users = initial_users
        while current_users <= max_users:
            # Create test config for this step
            step_config = TestConfiguration(
                test_id=f"{test_config.test_id}_step_{current_users}",
                test_type=TestType.STRESS_TEST,
                target_url=test_config.target_url,
                concurrent_users=current_users,
                test_duration=step_duration,
                ramp_up_time=30,
                ramp_down_time=15,
                endpoints=test_config.endpoints,
                headers=test_config.headers,
                payload=test_config.payload,
                timeout=test_config.timeout
            )
            
            # Run the step
            step_metrics = await self.run_load_test(step_config)
            stress_results.append(step_metrics)
            
            # Check if system is still stable
            if step_metrics.error_rate > 0.1:  # 10% error rate threshold
                self.logger.warning(f"High error rate detected at {current_users} users: {step_metrics.error_rate:.2%}")
                break
            
            # Increase load
            current_users += step_size
        
        # Return the last step's metrics
        return stress_results[-1] if stress_results else PerformanceMetrics(
            test_id=test_config.test_id,
            test_type=TestType.STRESS_TEST,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            success_rate=0,
            average_response_time=0,
            median_response_time=0,
            p95_response_time=0,
            p99_response_time=0,
            min_response_time=0,
            max_response_time=0,
            requests_per_second=0,
            peak_concurrent_users=0,
            error_rate=1.0,
            total_bytes_transferred=0
        )
    
    async def run_spike_test(self, test_config: TestConfiguration) -> PerformanceMetrics:
        """Run a spike test with sudden traffic increases"""
        self.logger.info(f"Starting spike test: {test_config.test_id}")
        
        # Spike test phases
        baseline_users = test_config.concurrent_users // 4
        spike_users = test_config.concurrent_users
        recovery_users = baseline_users
        
        baseline_duration = test_config.test_duration // 3
        spike_duration = test_config.test_duration // 6
        recovery_duration = test_config.test_duration // 3
        
        spike_config = TestConfiguration(
            test_id=f"{test_config.test_id}_spike",
            test_type=TestType.SPIKE_TEST,
            target_url=test_config.target_url,
            concurrent_users=spike_users,
            test_duration=baseline_duration + spike_duration + recovery_duration,
            ramp_up_time=60,
            ramp_down_time=30,
            endpoints=test_config.endpoints,
            headers=test_config.headers,
            payload=test_config.payload,
            timeout=test_config.timeout
        )
        
        return await self.run_load_test(spike_config)
    
    async def run_endurance_test(self, test_config: TestConfiguration) -> PerformanceMetrics:
        """Run an endurance test for extended periods"""
        self.logger.info(f"Starting endurance test: {test_config.test_id}")
        
        # Endurance test with moderate load over extended period
        endurance_config = TestConfiguration(
            test_id=f"{test_config.test_id}_endurance",
            test_type=TestType.ENDURANCE_TEST,
            target_url=test_config.target_url,
            concurrent_users=test_config.concurrent_users // 2,
            test_duration=test_config.test_duration * 3,  # 3x longer
            ramp_up_time=120,  # 2 minutes
            ramp_down_time=120,
            endpoints=test_config.endpoints,
            headers=test_config.headers,
            payload=test_config.payload,
            timeout=test_config.timeout
        )
        
        return await self.run_load_test(endurance_config)

class SystemMonitor:
    """System resource monitoring during performance tests"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.monitoring = False
        self.metrics = []
        self.monitor_task = None
    
    async def start_monitoring(self, interval: int = 5):
        """Start system monitoring"""
        self.monitoring = True
        
        async def monitor_loop():
            import psutil
            while self.monitoring:
                try:
                    # Collect system metrics
                    metrics = {
                        'timestamp': datetime.now(),
                        'cpu_percent': psutil.cpu_percent(interval=1),
                        'memory_percent': psutil.virtual_memory().percent,
                        'memory_used_gb': psutil.virtual_memory().used / (1024**3),
                        'disk_percent': psutil.disk_usage('/').percent,
                        'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                        'network_connections': len(psutil.net_connections())
                    }
                    
                    self.metrics.append(metrics)
                    
                    # Keep only last 1000 metrics
                    if len(self.metrics) > 1000:
                        self.metrics = self.metrics[-1000:]
                    
                    await asyncio.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"System monitoring error: {e}")
                    await asyncio.sleep(interval)
        
        self.monitor_task = asyncio.create_task(monitor_loop())
        self.logger.info("System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("System monitoring stopped")
    
    def get_system_metrics(self) -> List[Dict]:
        """Get collected system metrics"""
        return self.metrics.copy()

class BenchmarkValidator:
    """Benchmark validation and comparison framework"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.benchmarks = {}
        self.baselines = {}
    
    def create_baseline(self, baseline_name: str, metrics: PerformanceMetrics):
        """Create a performance baseline"""
        self.baselines[baseline_name] = {
            'created_at': datetime.now(),
            'metrics': asdict(metrics),
            'test_config': {
                'test_type': metrics.test_type.value,
                'test_duration': (metrics.end_time - metrics.start_time).total_seconds(),
                'concurrent_users': metrics.peak_concurrent_users
            }
        }
        
        self.logger.info(f"Baseline created: {baseline_name}")
    
    def validate_performance(self, current_metrics: PerformanceMetrics, 
                           baseline_name: str, thresholds: Dict[str, float]) -> List[BenchmarkResult]:
        """Validate current performance against baseline"""
        
        if baseline_name not in self.baselines:
            self.logger.warning(f"Baseline {baseline_name} not found")
            return []
        
        baseline = self.baselines[baseline_name]
        baseline_metrics = baseline['metrics']
        
        validation_results = []
        
        # Response time validation
        current_response_time = current_metrics.average_response_time
        baseline_response_time = baseline_metrics['average_response_time']
        
        if baseline_response_time > 0:
            response_time_change = ((current_response_time - baseline_response_time) / baseline_response_time) * 100
            
            status = 'improved' if response_time_change < -thresholds.get('response_time', 5) else \
                    'degraded' if response_time_change > thresholds.get('response_time', 5) else 'unchanged'
            
            validation_results.append(BenchmarkResult(
                metric_name='response_time',
                current_value=current_response_time,
                baseline_value=baseline_response_time,
                improvement_percent=-response_time_change,
                status=status
            ))
        
        # Throughput validation
        current_throughput = current_metrics.requests_per_second
        baseline_throughput = baseline_metrics['requests_per_second']
        
        if baseline_throughput > 0:
            throughput_change = ((current_throughput - baseline_throughput) / baseline_throughput) * 100
            
            status = 'improved' if throughput_change > thresholds.get('throughput', 5) else \
                    'degraded' if throughput_change < -thresholds.get('throughput', 5) else 'unchanged'
            
            validation_results.append(BenchmarkResult(
                metric_name='throughput',
                current_value=current_throughput,
                baseline_value=baseline_throughput,
                improvement_percent=throughput_change,
                status=status
            ))
        
        # Error rate validation
        current_error_rate = current_metrics.error_rate
        baseline_error_rate = baseline_metrics['error_rate']
        
        error_rate_change = ((current_error_rate - baseline_error_rate) / max(baseline_error_rate, 0.001)) * 100
        
        status = 'improved' if error_rate_change < -thresholds.get('error_rate', 10) else \
                'degraded' if error_rate_change > thresholds.get('error_rate', 10) else 'unchanged'
        
        validation_results.append(BenchmarkResult(
            metric_name='error_rate',
            current_value=current_error_rate,
            baseline_value=baseline_error_rate,
            improvement_percent=-error_rate_change,
            status=status
        ))
        
        return validation_results
    
    def export_benchmarks(self, filepath: str):
        """Export all benchmarks and baselines"""
        export_data = {
            'benchmarks': self.benchmarks,
            'baselines': self.baselines,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Benchmarks exported to {filepath}")

class PerformanceReportGenerator:
    """Generate comprehensive performance reports"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_test_report(self, metrics: PerformanceMetrics, 
                           system_metrics: List[Dict] = None,
                           output_path: str = None) -> str:
        """Generate detailed performance test report"""
        
        if output_path is None:
            output_path = f"/tmp/performance_report_{metrics.test_id}_{int(time.time())}.html"
        
        html_content = self._generate_html_report(metrics, system_metrics)
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        self.logger.info(f"Performance report generated: {output_path}")
        return output_path
    
    def _generate_html_report(self, metrics: PerformanceMetrics, 
                            system_metrics: List[Dict] = None) -> str:
        """Generate HTML performance report"""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Performance Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .metric {{ background-color: #ffffff; margin: 10px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric-label {{ font-weight: bold; color: #333; }}
        .metric-value {{ font-size: 1.2em; color: #0066cc; }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .error {{ color: #dc3545; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Performance Test Report</h1>
        <p><strong>Test ID:</strong> {test_id}</p>
        <p><strong>Test Type:</strong> {test_type}</p>
        <p><strong>Start Time:</strong> {start_time}</p>
        <p><strong>End Time:</strong> {end_time}</p>
        <p><strong>Duration:</strong> {duration_seconds:.1f} seconds</p>
    </div>
    
    <h2>Key Metrics</h2>
    
    <div class="metric">
        <div class="metric-label">Total Requests</div>
        <div class="metric-value">{total_requests:,}</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">Success Rate</div>
        <div class="metric-value {success_class}">{success_rate:.2%}</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">Average Response Time</div>
        <div class="metric-value">{average_response_time:.2f} ms</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">95th Percentile Response Time</div>
        <div class="metric-value">{p95_response_time:.2f} ms</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">Requests Per Second</div>
        <div class="metric-value">{requests_per_second:.2f}</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">Error Rate</div>
        <div class="metric-value {error_class}">{error_rate:.2%}</div>
    </div>
    
    <h2>Response Time Distribution</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value (ms)</th>
        </tr>
        <tr>
            <td>Minimum</td>
            <td>{min_response_time:.2f}</td>
        </tr>
        <tr>
            <td>Median</td>
            <td>{median_response_time:.2f}</td>
        </tr>
        <tr>
            <td>95th Percentile</td>
            <td>{p95_response_time:.2f}</td>
        </tr>
        <tr>
            <td>99th Percentile</td>
            <td>{p99_response_time:.2f}</td>
        </tr>
        <tr>
            <td>Maximum</td>
            <td>{max_response_time:.2f}</td>
        </tr>
    </table>
    
    <h2>System Resources</h2>
    {system_metrics_section}
    
</body>
</html>
        """
        
        # Determine CSS classes for metrics
        success_class = "success" if metrics.success_rate > 0.95 else "warning" if metrics.success_rate > 0.90 else "error"
        error_class = "success" if metrics.error_rate < 0.01 else "warning" if metrics.error_rate < 0.05 else "error"
        
        # Format system metrics section
        system_section = ""
        if system_metrics:
            if system_metrics:
                cpu_values = [m['cpu_percent'] for m in system_metrics]
                memory_values = [m['memory_percent'] for m in system_metrics]
                
                system_section = f"""
    <div class="metric">
        <div class="metric-label">Average CPU Usage</div>
        <div class="metric-value">{statistics.mean(cpu_values):.1f}%</div>
    </div>
    
    <div class="metric">
        <div class="metric-label">Average Memory Usage</div>
        <div class="metric-value">{statistics.mean(memory_values):.1f}%</div>
    </div>
    """
        
        # Format HTML
        duration_seconds = (metrics.end_time - metrics.start_time).total_seconds()
        
        html_content = html_template.format(
            test_id=metrics.test_id,
            test_type=metrics.test_type.value,
            start_time=metrics.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=metrics.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            duration_seconds=duration_seconds,
            total_requests=metrics.total_requests,
            success_rate=metrics.success_rate,
            success_class=success_class,
            average_response_time=metrics.average_response_time,
            p95_response_time=metrics.p95_response_time,
            requests_per_second=metrics.requests_per_second,
            error_rate=metrics.error_rate,
            error_class=error_class,
            min_response_time=metrics.min_response_time,
            median_response_time=metrics.median_response_time,
            p99_response_time=metrics.p99_response_time,
            max_response_time=metrics.max_response_time,
            system_metrics_section=system_section
        )
        
        return html_content
    
    def generate_csv_report(self, test_results: List[TestResult], output_path: str):
        """Generate CSV report of individual test results"""
        
        with open(output_path, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'url', 'method', 'status_code', 
                'response_time_ms', 'success', 'error_message',
                'bytes_sent', 'bytes_received'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in test_results:
                writer.writerow({
                    'timestamp': result.timestamp.isoformat(),
                    'url': result.url,
                    'method': result.method,
                    'status_code': result.status_code,
                    'response_time_ms': result.response_time_ms,
                    'success': result.success,
                    'error_message': result.error_message,
                    'bytes_sent': result.bytes_sent,
                    'bytes_received': result.bytes_received
                })
        
        self.logger.info(f"CSV report generated: {output_path}")

def create_sample_test_config() -> TestConfiguration:
    """Create sample performance test configuration"""
    return TestConfiguration(
        test_id="sample_load_test",
        test_type=TestType.LOAD_TEST,
        target_url="http://localhost:8080",
        concurrent_users=50,
        test_duration=300,  # 5 minutes
        ramp_up_time=60,   # 1 minute
        ramp_down_time=30, # 30 seconds
        max_requests_per_second=100,
        request_delay=0.1,
        timeout=30,
        headers={'Content-Type': 'application/json'},
        endpoints=['/api/users', '/api/stats', '/health']
    )

def main():
    """Example usage and testing"""
    async def demo_performance_testing():
        # Create sample configuration
        config = create_sample_test_config()
        
        # Initialize performance tester
        tester = PerformanceTester({})
        
        # Initialize benchmark validator
        benchmark_validator = BenchmarkValidator()
        
        # Initialize report generator
        report_generator = PerformanceReportGenerator()
        
        print("Performance Testing Demo")
        print("=" * 50)
        
        try:
            # Create baseline (in practice, this would be from a previous test)
            baseline_metrics = PerformanceMetrics(
                test_id="baseline",
                test_type=TestType.LOAD_TEST,
                start_time=datetime.now() - timedelta(hours=1),
                end_time=datetime.now() - timedelta(hours=1) + timedelta(seconds=300),
                total_requests=1500,
                successful_requests=1450,
                failed_requests=50,
                success_rate=0.9667,
                average_response_time=125.0,
                median_response_time=110.0,
                p95_response_time=200.0,
                p99_response_time=350.0,
                min_response_time=50.0,
                max_response_time=800.0,
                requests_per_second=50.0,
                peak_concurrent_users=50,
                error_rate=0.0333,
                total_bytes_transferred=1024000
            )
            
            benchmark_validator.create_baseline("production_baseline", baseline_metrics)
            
            # Run load test
            print("Running load test...")
            metrics = await tester.run_load_test(config)
            
            print(f"\nTest Results:")
            print(f"  Total Requests: {metrics.total_requests}")
            print(f"  Success Rate: {metrics.success_rate:.2%}")
            print(f"  Average Response Time: {metrics.average_response_time:.2f}ms")
            print(f"  P95 Response Time: {metrics.p95_response_time:.2f}ms")
            print(f"  Requests/Second: {metrics.requests_per_second:.2f}")
            print(f"  Error Rate: {metrics.error_rate:.2%}")
            
            # Validate performance against baseline
            print(f"\nBenchmark Validation:")
            validation_results = benchmark_validator.validate_performance(
                metrics, 
                "production_baseline",
                {'response_time': 10, 'throughput': 10, 'error_rate': 25}
            )
            
            for result in validation_results:
                print(f"  {result.metric_name}: {result.status} "
                      f"({result.improvement_percent:+.1f}%)")
            
            # Generate reports
            print(f"\nGenerating reports...")
            
            system_metrics = tester.system_monitor.get_system_metrics()
            html_report = report_generator.generate_test_report(metrics, system_metrics)
            csv_report = "/tmp/test_results.csv"
            
            test_results = tester.test_results.get(config.test_id, [])
            report_generator.generate_csv_report(test_results, csv_report)
            
            print(f"HTML Report: {html_report}")
            print(f"CSV Report: {csv_report}")
            
        except Exception as e:
            print(f"Performance test failed: {e}")
    
    # Run the demo
    asyncio.run(demo_performance_testing())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()