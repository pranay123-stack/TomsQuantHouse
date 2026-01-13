#!/usr/bin/env python3
"""
Health Check Coordinator
Coordinates health checks between dependent services
"""

import os
import sys
import json
import time
import yaml
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"
    STARTING = "starting"
    STOPPING = "stopping"

@dataclass
class ServiceHealth:
    service_name: str
    status: HealthStatus
    url: str
    response_time: float
    last_check: datetime
    error_message: Optional[str] = None
    dependency_status: Dict[str, HealthStatus] = None

class HealthCheckCoordinator:
    def __init__(self, config_path: str = "/workspace/orchestration/config/services.yaml"):
        self.config_path = config_path
        self.services = {}
        self.health_status = {}
        self.dependency_graph = {}
        self.running = False
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.load_configuration()
        
        # Create health check session
        self.session = None
        
        self.logger.info("Health Check Coordinator initialized")

    def setup_logging(self):
        """Setup logging for health check coordinator"""
        log_dir = Path("/workspace/orchestration/logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger('HealthCheckCoordinator')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler(log_dir / 'health_check.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def load_configuration(self):
        """Load service configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.services = config.get('services', {})
            
            # Build dependency graph
            for service_name, service_config in self.services.items():
                deps = service_config.get('dependencies', [])
                self.dependency_graph[service_name] = deps
                
                # Initialize health status
                self.health_status[service_name] = ServiceHealth(
                    service_name=service_name,
                    status=HealthStatus.UNKNOWN,
                    url=service_config.get('health_endpoint', ''),
                    response_time=0.0,
                    last_check=None
                )
            
            self.logger.info(f"Loaded health check configuration for {len(self.services)} services")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    async def check_service_health(self, service_name: str) -> ServiceHealth:
        """Check health of a single service"""
        if service_name not in self.health_status:
            raise ValueError(f"Service {service_name} not found in configuration")
        
        health = self.health_status[service_name]
        start_time = time.time()
        
        try:
            if not health.url:
                # No health endpoint configured
                return health
            
            # Make HTTP request
            timeout = aiohttp.ClientTimeout(total=10)
            async with self.session.get(health.url, timeout=timeout) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    health.status = HealthStatus.HEALTHY
                    health.error_message = None
                else:
                    health.status = HealthStatus.UNHEALTHY
                    health.error_message = f"HTTP {response.status}"
                
                health.response_time = response_time
                health.last_check = datetime.now()
                
                # Try to parse response for additional health info
                try:
                    data = await response.json()
                    if 'status' in data:
                        status_value = data['status'].lower()
                        if status_value == 'degraded':
                            health.status = HealthStatus.DEGRADED
                        elif status_value == 'starting':
                            health.status = HealthStatus.STARTING
                        elif status_value == 'stopping':
                            health.status = HealthStatus.STOPPING
                except:
                    pass  # Ignore JSON parsing errors
                
                return health
                
        except asyncio.TimeoutError:
            health.status = HealthStatus.UNHEALTHY
            health.error_message = "Timeout"
            health.response_time = 10.0
            health.last_check = datetime.now()
            return health
            
        except Exception as e:
            health.status = HealthStatus.UNHEALTHY
            health.error_message = str(e)
            health.response_time = time.time() - start_time
            health.last_check = datetime.now()
            return health

    async def check_dependencies(self, service_name: str) -> Dict[str, HealthStatus]:
        """Check health of service dependencies"""
        dependencies = self.dependency_graph.get(service_name, [])
        dep_status = {}
        
        for dep_name in dependencies:
            if dep_name in self.health_status:
                dep_health = await self.check_service_health(dep_name)
                dep_status[dep_name] = dep_health.status
        
        return dep_status

    def evaluate_service_health(self, service_health: ServiceHealth, dep_status: Dict[str, HealthStatus]) -> HealthStatus:
        """Evaluate overall service health including dependencies"""
        # If service itself is unhealthy
        if service_health.status == HealthStatus.UNHEALTHY:
            return HealthStatus.UNHEALTHY
        
        # Check dependencies
        unhealthy_deps = [dep for dep, status in dep_status.items() if status == HealthStatus.UNHEALTHY]
        degraded_deps = [dep for dep, status in dep_status.items() if status == HealthStatus.DEGRADED]
        
        if unhealthy_deps:
            self.logger.warning(f"Service {service_health.service_name} has unhealthy dependencies: {unhealthy_deps}")
            return HealthStatus.DEGRADED
        
        if degraded_deps:
            self.logger.warning(f"Service {service_health.service_name} has degraded dependencies: {degraded_deps}")
            return HealthStatus.DEGRADED
        
        return service_health.status

    async def comprehensive_health_check(self) -> Dict[str, ServiceHealth]:
        """Perform comprehensive health check on all services"""
        self.logger.info("Starting comprehensive health check")
        
        # Check all services
        tasks = []
        for service_name in self.services:
            task = self.check_service_health(service_name)
            tasks.append(task)
        
        # Wait for all checks to complete
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update dependency status
        for service_name, result in zip(self.services.keys(), health_results):
            if isinstance(result, ServiceHealth):
                dep_status = await self.check_dependencies(service_name)
                result.dependency_status = dep_status
                
                # Evaluate overall health
                overall_status = self.evaluate_service_health(result, dep_status)
                if overall_status != result.status:
                    self.logger.info(f"Service {service_name} overall health adjusted to {overall_status.value}")
                    result.status = overall_status
        
        return dict(zip(self.services.keys(), health_results))

    async def check_service_graph(self) -> Dict[str, List[str]]:
        """Identify service dependency issues"""
        issues = {}
        
        for service_name, deps in self.dependency_graph.items():
            missing_deps = []
            unhealthy_deps = []
            
            for dep_name in deps:
                if dep_name not in self.services:
                    missing_deps.append(dep_name)
                elif self.health_status[dep_name].status == HealthStatus.UNHEALTHY:
                    unhealthy_deps.append(dep_name)
            
            if missing_deps or unhealthy_deps:
                issues[service_name] = {
                    'missing_dependencies': missing_deps,
                    'unhealthy_dependencies': unhealthy_deps
                }
        
        return issues

    async def generate_health_report(self) -> Dict:
        """Generate comprehensive health report"""
        health_results = await self.comprehensive_health_check()
        dependency_issues = await self.check_service_graph()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_services': len(self.services),
                'healthy_services': 0,
                'unhealthy_services': 0,
                'degraded_services': 0,
                'unknown_services': 0
            },
            'services': {},
            'dependency_issues': dependency_issues,
            'recommendations': []
        }
        
        for service_name, health in health_results.items():
            if isinstance(health, ServiceHealth):
                report['services'][service_name] = {
                    'status': health.status.value,
                    'url': health.url,
                    'response_time_ms': round(health.response_time * 1000, 2),
                    'last_check': health.last_check.isoformat() if health.last_check else None,
                    'error_message': health.error_message,
                    'dependencies': health.dependency_status or {}
                }
                
                # Update summary counts
                if health.status == HealthStatus.HEALTHY:
                    report['summary']['healthy_services'] += 1
                elif health.status == HealthStatus.UNHEALTHY:
                    report['summary']['unhealthy_services'] += 1
                elif health.status == HealthStatus.DEGRADED:
                    report['summary']['degraded_services'] += 1
                else:
                    report['summary']['unknown_services'] += 1
        
        # Generate recommendations
        if report['summary']['unhealthy_services'] > 0:
            report['recommendations'].append({
                'type': 'critical',
                'message': f"{report['summary']['unhealthy_services']} service(s) are unhealthy and require immediate attention"
            })
        
        if report['summary']['degraded_services'] > 0:
            report['recommendations'].append({
                'type': 'warning',
                'message': f"{report['summary']['degraded_services']} service(s) are degraded due to dependency issues"
            })
        
        # Check response times
        slow_services = [name for name, health in health_results.items() 
                        if isinstance(health, ServiceHealth) and health.response_time > 5.0]
        if slow_services:
            report['recommendations'].append({
                'type': 'performance',
                'message': f"Services with slow response times: {', '.join(slow_services)}"
            })
        
        return report

    async def run_continuous_monitoring(self, interval: int = 30):
        """Run continuous health monitoring"""
        self.logger.info(f"Starting continuous health monitoring (interval: {interval}s)")
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            while self.running:
                try:
                    report = await self.generate_health_report()
                    
                    # Save report
                    reports_dir = Path("/workspace/orchestration/logs/health_reports")
                    reports_dir.mkdir(exist_ok=True)
                    
                    report_file = reports_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(report_file, 'w') as f:
                        json.dump(report, f, indent=2)
                    
                    # Log summary
                    summary = report['summary']
                    self.logger.info(
                        f"Health Check Summary: {summary['healthy_services']} healthy, "
                        f"{summary['unhealthy_services']} unhealthy, "
                        f"{summary['degraded_services']} degraded, "
                        f"{summary['unknown_services']} unknown"
                    )
                    
                    # Handle alerts
                    await self.handle_alerts(report)
                    
                except Exception as e:
                    self.logger.error(f"Error during health check: {e}")
                
                await asyncio.sleep(interval)

    async def handle_alerts(self, health_report: Dict):
        """Handle health check alerts"""
        summary = health_report['summary']
        
        # Critical alerts
        if summary['unhealthy_services'] > 0:
            self.logger.error(f"CRITICAL: {summary['unhealthy_services']} unhealthy services detected")
            
            # Send alert (in real implementation, this would send to monitoring system)
            alert_message = {
                'type': 'critical',
                'timestamp': datetime.now().isoformat(),
                'message': f"Service Health Alert: {summary['unhealthy_services']} services are unhealthy",
                'services': [name for name, health in health_report['services'].items() 
                           if health['status'] == 'unhealthy']
            }
            
            alert_file = Path("/workspace/orchestration/logs/alerts") / f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            alert_file.parent.mkdir(exist_ok=True)
            
            with open(alert_file, 'w') as f:
                json.dump(alert_message, f, indent=2)

    def start(self):
        """Start the health check coordinator"""
        self.running = True
        self.logger.info("Starting Health Check Coordinator")

    def stop(self):
        """Stop the health check coordinator"""
        self.running = False
        self.logger.info("Stopping Health Check Coordinator")

async def main():
    """Main entry point for health check coordinator"""
    coordinator = HealthCheckCoordinator()
    
    try:
        coordinator.start()
        
        # Run a single comprehensive check
        print("Running comprehensive health check...")
        report = await coordinator.generate_health_report()
        
        print(json.dumps(report, indent=2))
        
        # Save the report
        report_file = Path("/workspace/orchestration/logs/health_reports") / "latest_health_report.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nHealth report saved to: {report_file}")
        
    except KeyboardInterrupt:
        print("\nShutting down health check coordinator...")
    finally:
        coordinator.stop()

if __name__ == "__main__":
    asyncio.run(main())