#!/usr/bin/env python3
"""
Service Orchestration and Management System
Coordinates service initialization, health checks, scaling, and operations
"""

import os
import sys
import json
import yaml
import time
import signal
import subprocess
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import psutil
import requests
import schedule

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ServiceOrchestrator:
    def __init__(self, config_path: str = "/workspace/orchestration/config/services.yaml"):
        self.config_path = config_path
        self.services = {}
        self.service_status = {}
        self.running = False
        self.orchestrator_pid = os.getpid()
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.load_configuration()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
        
        self.logger.info(f"Service Orchestrator initialized with PID {self.orchestrator_pid}")

    def setup_logging(self):
        """Setup comprehensive logging for the orchestrator"""
        log_dir = Path("/workspace/orchestration/logs")
        log_dir.mkdir(exist_ok=True)
        
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create logger
        self.logger = logging.getLogger('ServiceOrchestrator')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(log_dir / 'orchestrator.log')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(log_format)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def load_configuration(self):
        """Load service configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.services = config.get('services', {})
            self.global_config = config.get('global', {})
            
            # Initialize service status tracking
            for service_name in self.services:
                self.service_status[service_name] = {
                    'status': 'stopped',
                    'pid': None,
                    'last_health_check': None,
                    'restarts': 0,
                    'uptime': None
                }
            
            self.logger.info(f"Loaded configuration for {len(self.services)} services")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

    def start_service(self, service_name: str) -> bool:
        """Start a single service with dependency checking"""
        if service_name not in self.services:
            self.logger.error(f"Service {service_name} not found in configuration")
            return False
        
        service = self.services[service_name]
        
        # Check dependencies
        if not self.check_dependencies(service_name):
            self.logger.error(f"Dependencies not satisfied for service {service_name}")
            return False
        
        # Start the service
        try:
            self.logger.info(f"Starting service: {service_name}")
            
            # Prepare command
            command = service.get('command', '')
            if not command:
                self.logger.error(f"No command specified for service {service_name}")
                return False
            
            # Start process
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=service.get('working_dir', '/workspace')
            )
            
            # Update status
            self.service_status[service_name]['status'] = 'starting'
            self.service_status[service_name]['pid'] = process.pid
            
            # Wait a moment to see if it starts successfully
            time.sleep(2)
            
            if process.poll() is None:  # Still running
                self.service_status[service_name]['status'] = 'running'
                self.service_status[service_name]['start_time'] = datetime.now()
                self.logger.info(f"Service {service_name} started successfully (PID: {process.pid})")
                return True
            else:  # Process exited
                stdout, stderr = process.communicate()
                self.logger.error(f"Service {service_name} failed to start: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error starting service {service_name}: {e}")
            self.service_status[service_name]['status'] = 'failed'
            return False

    def stop_service(self, service_name: str, graceful: bool = True) -> bool:
        """Stop a service gracefully or forcefully"""
        if service_name not in self.service_status:
            return False
        
        status = self.service_status[service_name]
        if status['pid'] is None:
            self.logger.warning(f"Service {service_name} is not running")
            return True
        
        try:
            self.logger.info(f"Stopping service: {service_name}")
            
            # Get process
            try:
                process = psutil.Process(status['pid'])
            except psutil.NoSuchProcess:
                self.logger.warning(f"Process {status['pid']} for service {service_name} not found")
                status['status'] = 'stopped'
                return True
            
            if graceful:
                # Try graceful shutdown
                process.terminate()
                try:
                    process.wait(timeout=10)
                    self.logger.info(f"Service {service_name} stopped gracefully")
                except psutil.TimeoutExpired:
                    # Force kill
                    self.logger.warning(f"Graceful shutdown timeout for {service_name}, forcing...")
                    process.kill()
            else:
                process.kill()
            
            # Update status
            status['status'] = 'stopped'
            status['pid'] = None
            status['start_time'] = None
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping service {service_name}: {e}")
            return False

    def restart_service(self, service_name: str) -> bool:
        """Restart a service"""
        self.logger.info(f"Restarting service: {service_name}")
        
        # Stop the service
        self.stop_service(service_name)
        time.sleep(2)
        
        # Start the service
        success = self.start_service(service_name)
        if success:
            self.service_status[service_name]['restarts'] += 1
        
        return success

    def check_dependencies(self, service_name: str) -> bool:
        """Check if service dependencies are running"""
        service = self.services[service_name]
        dependencies = service.get('dependencies', [])
        
        for dep in dependencies:
            if dep not in self.service_status:
                self.logger.error(f"Dependency {dep} not found in configuration")
                return False
            
            if self.service_status[dep]['status'] != 'running':
                self.logger.warning(f"Dependency {dep} is not running for {service_name}")
                return False
        
        return True

    def check_service_health(self, service_name: str) -> bool:
        """Check health of a single service"""
        if service_name not in self.service_status:
            return False
        
        status = self.service_status[service_name]
        
        if status['pid'] is None:
            return False
        
        try:
            # Check if process is still alive
            process = psutil.Process(status['pid'])
            if not process.is_running():
                return False
            
            # Check health endpoint if available
            service = self.services[service_name]
            health_endpoint = service.get('health_endpoint')
            if health_endpoint:
                try:
                    response = requests.get(health_endpoint, timeout=5)
                    if response.status_code != 200:
                        self.logger.warning(f"Service {service_name} health check failed: {response.status_code}")
                        return False
                except Exception as e:
                    self.logger.warning(f"Health check error for {service_name}: {e}")
                    return False
            
            # Update last health check
            status['last_health_check'] = datetime.now()
            return True
            
        except psutil.NoSuchProcess:
            return False
        except Exception as e:
            self.logger.error(f"Error checking health for {service_name}: {e}")
            return False

    def health_check_loop(self):
        """Continuous health check loop"""
        self.logger.info("Starting health check loop")
        
        while self.running:
            for service_name in self.services:
                if service_name in self.service_status:
                    is_healthy = self.check_service_health(service_name)
                    
                    if not is_healthy and self.service_status[service_name]['status'] == 'running':
                        self.logger.error(f"Service {service_name} health check failed")
                        self.service_status[service_name]['status'] = 'unhealthy'
                        
                        # Attempt restart if configured
                        service = self.services[service_name]
                        if service.get('auto_restart', False):
                            self.logger.info(f"Auto-restarting unhealthy service {service_name}")
                            self.restart_service(service_name)
            
            time.sleep(30)  # Check every 30 seconds

    def start_all_services(self):
        """Start all services in dependency order"""
        self.logger.info("Starting all services")
        
        # Sort services by dependencies
        sorted_services = self.topological_sort()
        
        for service_name in sorted_services:
            if self.service_status[service_name]['status'] != 'running':
                success = self.start_service(service_name)
                if success:
                    self.logger.info(f"Started {service_name}")
                else:
                    self.logger.error(f"Failed to start {service_name}")
        
        self.logger.info("All services startup sequence completed")

    def stop_all_services(self, graceful: bool = True):
        """Stop all services in reverse dependency order"""
        self.logger.info("Stopping all services")
        
        # Sort services by dependencies in reverse
        sorted_services = reversed(self.topological_sort())
        
        for service_name in sorted_services:
            self.stop_service(service_name, graceful)
        
        self.logger.info("All services stopped")

    def topological_sort(self):
        """Sort services by dependencies using topological sort"""
        # Simple implementation for services with dependencies
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(service_name):
            if service_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {service_name}")
            
            if service_name in visited:
                return
            
            temp_visited.add(service_name)
            
            service = self.services[service_name]
            dependencies = service.get('dependencies', [])
            
            for dep in dependencies:
                visit(dep)
            
            temp_visited.remove(service_name)
            visited.add(service_name)
            result.append(service_name)
        
        for service_name in self.services:
            if service_name not in visited:
                visit(service_name)
        
        return result

    def scale_service(self, service_name: str, instances: int) -> bool:
        """Scale service to specified number of instances"""
        # This is a simplified scaling implementation
        # In a real system, this would integrate with container orchestration
        self.logger.info(f"Scaling service {service_name} to {instances} instances")
        
        current_instances = len([s for s in self.service_status if s.startswith(service_name)])
        
        if instances > current_instances:
            # Scale up
            for i in range(instances - current_instances):
                instance_name = f"{service_name}_{i + 1}"
                self.start_service(instance_name)
        elif instances < current_instances:
            # Scale down
            instances_to_stop = current_instances - instances
            for i in range(instances_to_stop):
                instance_name = f"{service_name}_{current_instances - i}"
                self.stop_service(instance_name)
        
        return True

    def get_service_status(self) -> Dict[str, Any]:
        """Get current status of all services"""
        status_report = {
            'timestamp': datetime.now().isoformat(),
            'orchestrator_pid': self.orchestrator_pid,
            'services': {}
        }
        
        for service_name, status in self.service_status.items():
            service_info = self.services.get(service_name, {})
            status_info = {
                'status': status['status'],
                'pid': status['pid'],
                'last_health_check': status['last_health_check'].isoformat() if status['last_health_check'] else None,
                'restarts': status['restarts'],
                'uptime': None
            }
            
            if status.get('start_time'):
                uptime = datetime.now() - status['start_time']
                status_info['uptime'] = str(uptime)
            
            status_report['services'][service_name] = status_info
        
        return status_report

    def run(self):
        """Main orchestrator loop"""
        self.running = True
        
        try:
            self.logger.info("Starting Service Orchestrator")
            
            # Start all services
            self.start_all_services()
            
            # Start health check loop in separate thread
            health_thread = threading.Thread(target=self.health_check_loop)
            health_thread.daemon = True
            health_thread.start()
            
            # Schedule monitoring tasks
            schedule.every(1).hours.do(self.perform_maintenance_tasks)
            schedule.every(30).minutes.do(self.generate_status_report)
            
            # Main monitoring loop
            while self.running:
                schedule.run_pending()
                time.sleep(10)
                
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
        finally:
            self.handle_shutdown()

    def perform_maintenance_tasks(self):
        """Perform periodic maintenance tasks"""
        self.logger.info("Performing maintenance tasks")
        
        # Clean up logs
        log_dir = Path("/workspace/orchestration/logs")
        if log_dir.exists():
            cutoff_date = datetime.now() - timedelta(days=7)
            for log_file in log_dir.glob("*.log"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    self.logger.info(f"Cleaned up old log file: {log_file}")

    def generate_status_report(self):
        """Generate and save status report"""
        status_report = self.get_service_status()
        
        reports_dir = Path("/workspace/orchestration/logs/reports")
        reports_dir.mkdir(exist_ok=True)
        
        report_file = reports_dir / f"status_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(status_report, f, indent=2)
        
        self.logger.info(f"Generated status report: {report_file}")

    def handle_shutdown(self, signum=None, frame=None):
        """Handle graceful shutdown"""
        self.logger.info("Initiating graceful shutdown")
        self.running = False
        
        # Stop all services
        self.stop_all_services(graceful=True)
        
        self.logger.info("Service Orchestrator shutdown complete")
        sys.exit(0)

def main():
    """Main entry point"""
    orchestrator = ServiceOrchestrator()
    orchestrator.run()

if __name__ == "__main__":
    main()