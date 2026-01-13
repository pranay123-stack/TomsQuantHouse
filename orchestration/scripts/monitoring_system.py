#!/usr/bin/env python3
"""
Monitoring and Alerting System
Real-time monitoring and alerting for service health and performance
"""

import os
import sys
import json
import yaml
import time
import psutil
import logging
import smtplib
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import threading
import schedule

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class AlertSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

class MetricType(Enum):
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"

@dataclass
class Alert:
    id: str
    severity: AlertSeverity
    service: str
    metric: MetricType
    message: str
    value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False

@dataclass
class ServiceMetrics:
    service_name: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    response_time: Optional[float]
    error_rate: Optional[float]
    throughput: Optional[float]
    timestamp: datetime

class MonitoringAlertingSystem:
    def __init__(self, config_path: str = "/workspace/orchestration/config/services.yaml"):
        self.config_path = config_path
        self.services = {}
        self.global_config = {}
        self.thresholds = {}
        self.alerts = []
        self.metrics_history = []
        self.running = False
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.load_configuration()
        
        # Initialize alerting channels
        self.email_config = self.global_config.get('email', {})
        self.webhook_config = self.global_config.get('webhook', {})
        
        self.logger.info("Monitoring and Alerting System initialized")

    def setup_logging(self):
        """Setup logging for monitoring system"""
        log_dir = Path("/workspace/orchestration/logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger('MonitoringAlertingSystem')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler(log_dir / 'monitoring.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def load_configuration(self):
        """Load monitoring configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            monitoring_config = config.get('monitoring', {})
            
            self.services = config.get('services', {})
            self.global_config = monitoring_config.get('global', {})
            self.thresholds = monitoring_config.get('thresholds', {})
            
            self.logger.info(f"Loaded monitoring configuration for {len(self.services)} services")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system metrics"""
        metrics = {}
        
        try:
            # CPU usage
            metrics['cpu_usage'] = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics['memory_usage'] = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/workspace')
            metrics['disk_usage'] = disk.used / disk.total * 100
            
            # Load average
            try:
                load_avg = os.getloadavg()[0]  # 1-minute load average
                metrics['load_average'] = load_avg
            except:
                metrics['load_average'] = 0.0
            
            # Network I/O
            network = psutil.net_io_counters()
            metrics['network_bytes_sent'] = network.bytes_sent
            metrics['network_bytes_recv'] = network.bytes_recv
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {}

    def get_service_metrics(self, service_name: str) -> ServiceMetrics:
        """Get metrics for a specific service"""
        try:
            service_config = self.services.get(service_name, {})
            
            # Get process metrics if service is running
            service_metrics = ServiceMetrics(
                service_name=service_name,
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                response_time=None,
                error_rate=None,
                throughput=None,
                timestamp=datetime.now()
            )
            
            # Try to find and measure the service process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    # Match service by command line or working directory
                    if (service_name in cmdline.lower() or 
                        any(service_name in arg for arg in pinfo['cmdline'])):
                        
                        proc_obj = psutil.Process(pinfo['pid'])
                        
                        # CPU usage
                        service_metrics.cpu_usage = proc_obj.cpu_percent()
                        
                        # Memory usage
                        service_metrics.memory_usage = proc_obj.memory_percent()
                        
                        # Disk I/O
                        service_metrics.disk_usage = proc_obj.io_counters().read_bytes / (1024*1024)  # MB
                        
                        break
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Try to get response time from health endpoint
            health_endpoint = service_config.get('health_endpoint')
            if health_endpoint:
                try:
                    start_time = time.time()
                    response = requests.get(health_endpoint, timeout=10)
                    service_metrics.response_time = (time.time() - start_time) * 1000  # ms
                    
                    # Calculate error rate based on status code
                    if response.status_code >= 400:
                        service_metrics.error_rate = 100.0
                    else:
                        service_metrics.error_rate = 0.0
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get health metrics for {service_name}: {e}")
                    service_metrics.response_time = None
                    service_metrics.error_rate = 100.0
            
            return service_metrics
            
        except Exception as e:
            self.logger.error(f"Error getting service metrics for {service_name}: {e}")
            return ServiceMetrics(
                service_name=service_name,
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                response_time=None,
                error_rate=None,
                throughput=None,
                timestamp=datetime.now()
            )

    def evaluate_thresholds(self, metrics: ServiceMetrics) -> List[Alert]:
        """Evaluate metrics against thresholds and generate alerts"""
        alerts = []
        
        # CPU usage threshold
        cpu_threshold = self.thresholds.get('cpu_usage', 80)
        if metrics.cpu_usage > cpu_threshold:
            alert = Alert(
                id=f"cpu_{metrics.service_name}_{int(time.time())}",
                severity=AlertSeverity.WARNING if metrics.cpu_usage < 95 else AlertSeverity.CRITICAL,
                service=metrics.service_name,
                metric=MetricType.CPU_USAGE,
                message=f"CPU usage {metrics.cpu_usage:.1f}% exceeds threshold {cpu_threshold}%",
                value=metrics.cpu_usage,
                threshold=cpu_threshold,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Memory usage threshold
        memory_threshold = self.thresholds.get('memory_usage', 85)
        if metrics.memory_usage > memory_threshold:
            alert = Alert(
                id=f"memory_{metrics.service_name}_{int(time.time())}",
                severity=AlertSeverity.WARNING if metrics.memory_usage < 95 else AlertSeverity.CRITICAL,
                service=metrics.service_name,
                metric=MetricType.MEMORY_USAGE,
                message=f"Memory usage {metrics.memory_usage:.1f}% exceeds threshold {memory_threshold}%",
                value=metrics.memory_usage,
                threshold=memory_threshold,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        # Response time threshold
        if metrics.response_time is not None:
            response_threshold = self.thresholds.get('response_time', 5000)  # milliseconds
            if metrics.response_time > response_threshold:
                alert = Alert(
                    id=f"response_{metrics.service_name}_{int(time.time())}",
                    severity=AlertSeverity.WARNING,
                    service=metrics.service_name,
                    metric=MetricType.RESPONSE_TIME,
                    message=f"Response time {metrics.response_time:.0f}ms exceeds threshold {response_threshold}ms",
                    value=metrics.response_time,
                    threshold=response_threshold,
                    timestamp=datetime.now()
                )
                alerts.append(alert)
        
        # Error rate threshold
        if metrics.error_rate is not None and metrics.error_rate > 0:
            alert = Alert(
                id=f"error_{metrics.service_name}_{int(time.time())}",
                severity=AlertSeverity.CRITICAL,
                service=metrics.service_name,
                metric=MetricType.ERROR_RATE,
                message=f"Error rate {metrics.error_rate:.1f}% detected",
                value=metrics.error_rate,
                threshold=0.0,
                timestamp=datetime.now()
            )
            alerts.append(alert)
        
        return alerts

    def send_email_alert(self, alert: Alert):
        """Send email alert"""
        if not self.email_config:
            return
        
        try:
            smtp_server = self.email_config.get('smtp_server', 'localhost')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            from_email = self.email_config.get('from_email')
            to_emails = self.email_config.get('to_emails', [])
            
            if not to_emails:
                return
            
            subject = f"[{alert.severity.value.upper()}] Service Alert - {alert.service}"
            body = f"""
            Alert Details:
            Service: {alert.service}
            Severity: {alert.severity.value.upper()}
            Metric: {alert.metric.value}
            Message: {alert.message}
            Value: {alert.value}
            Threshold: {alert.threshold}
            Timestamp: {alert.timestamp}
            """
            
            message = f"From: {from_email}\nTo: {', '.join(to_emails)}\nSubject: {subject}\n\n{body}"
            
            server = smtplib.SMTP(smtp_server, smtp_port)
            if username and password:
                server.starttls()
                server.login(username, password)
            
            server.sendmail(from_email, to_emails, message)
            server.quit()
            
            self.logger.info(f"Email alert sent for {alert.service}")
            
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    def send_webhook_alert(self, alert: Alert):
        """Send webhook alert"""
        if not self.webhook_config:
            return
        
        try:
            webhook_url = self.webhook_config.get('url')
            if not webhook_url:
                return
            
            payload = {
                'alert_id': alert.id,
                'severity': alert.severity.value,
                'service': alert.service,
                'metric': alert.metric.value,
                'message': alert.message,
                'value': alert.value,
                'threshold': alert.threshold,
                'timestamp': alert.timestamp.isoformat()
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            self.logger.info(f"Webhook alert sent for {alert.service}")
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")

    def process_alert(self, alert: Alert):
        """Process an alert"""
        self.logger.info(f"Processing alert: {alert.message}")
        
        # Add to alerts list
        self.alerts.append(alert)
        
        # Send notifications
        self.send_email_alert(alert)
        self.send_webhook_alert(alert)
        
        # Take automatic actions based on severity
        if alert.severity == AlertSeverity.CRITICAL:
            self.handle_critical_alert(alert)

    def handle_critical_alert(self, alert: Alert):
        """Handle critical alerts with automatic actions"""
        self.logger.warning(f"Handling critical alert for {alert.service}: {alert.message}")
        
        # Try to restart unhealthy services
        if alert.metric in [MetricType.ERROR_RATE, MetricType.RESPONSE_TIME]:
            try:
                from orchestration.scripts.graceful_shutdown import graceful_shutdown
                # This would integrate with the orchestrator to restart the service
                self.logger.info(f"Would restart service {alert.service} for critical alert")
            except Exception as e:
                self.logger.error(f"Failed to restart service {alert.service}: {e}")

    def save_metrics(self, metrics: List[ServiceMetrics]):
        """Save metrics to file"""
        try:
            metrics_dir = Path("/workspace/orchestration/logs/metrics")
            metrics_dir.mkdir(exist_ok=True)
            
            # Save current metrics
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            metrics_file = metrics_dir / f"metrics_{current_time}.json"
            
            metrics_data = []
            for metric in metrics:
                metrics_data.append({
                    'service_name': metric.service_name,
                    'cpu_usage': metric.cpu_usage,
                    'memory_usage': metric.memory_usage,
                    'disk_usage': metric.disk_usage,
                    'response_time': metric.response_time,
                    'error_rate': metric.error_rate,
                    'throughput': metric.throughput,
                    'timestamp': metric.timestamp.isoformat()
                })
            
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            # Update metrics history
            self.metrics_history.extend(metrics_data)
            
            # Keep only last 1000 entries in memory
            if len(self.metrics_history) > 1000:
                self.metrics_history = self.metrics_history[-1000:]
            
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def cleanup_old_files(self):
        """Clean up old log and metrics files"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            
            # Clean up log files
            log_dir = Path("/workspace/orchestration/logs")
            for log_file in log_dir.glob("*.log"):
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
            
            # Clean up metrics files
            metrics_dir = Path("/workspace/orchestration/logs/metrics")
            for metrics_file in metrics_dir.glob("*.json"):
                file_time = datetime.fromtimestamp(metrics_file.stat().st_mtime)
                if file_time < cutoff_date:
                    metrics_file.unlink()
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old files: {e}")

    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        try:
            # Get system metrics
            system_metrics = self.get_system_metrics()
            
            # Get service metrics
            service_metrics = []
            for service_name in self.services:
                metrics = self.get_service_metrics(service_name)
                service_metrics.append(metrics)
                
                # Evaluate thresholds
                alerts = self.evaluate_thresholds(metrics)
                for alert in alerts:
                    self.process_alert(alert)
            
            # Save metrics
            self.save_metrics(service_metrics)
            
            # Log summary
            self.logger.info(
                f"Monitoring cycle completed: {len(service_metrics)} services monitored, "
                f"{len([a for a in self.alerts if not a.acknowledged])} active alerts"
            )
            
        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {e}")

    def generate_status_report(self) -> Dict[str, Any]:
        """Generate monitoring status report"""
        try:
            # System metrics
            system_metrics = self.get_system_metrics()
            
            # Recent alerts (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_alerts = [
                alert for alert in self.alerts 
                if alert.timestamp > cutoff_time
            ]
            
            # Active alerts
            active_alerts = [
                alert for alert in self.alerts 
                if not alert.acknowledged and not alert.resolved
            ]
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'system_metrics': system_metrics,
                'active_alerts': [
                    {
                        'id': alert.id,
                        'severity': alert.severity.value,
                        'service': alert.service,
                        'metric': alert.metric.value,
                        'message': alert.message,
                        'timestamp': alert.timestamp.isoformat()
                    }
                    for alert in active_alerts
                ],
                'recent_alerts_count': len(recent_alerts),
                'total_alerts': len(self.alerts),
                'services_monitored': len(self.services)
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate status report: {e}")
            return {}

    def start_monitoring(self):
        """Start continuous monitoring"""
        self.running = True
        self.logger.info("Starting monitoring system")
        
        # Schedule tasks
        monitoring_interval = self.global_config.get('metrics_interval', 60)  # seconds
        schedule.every(monitoring_interval).seconds.do(self.run_monitoring_cycle)
        schedule.every(1).hours.do(self.cleanup_old_files)
        schedule.every(30).minutes.do(self.generate_dashboard_update)
        
        # Main monitoring loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)

    def generate_dashboard_update(self):
        """Generate dashboard update"""
        try:
            report = self.generate_status_report()
            
            dashboard_file = Path("/workspace/orchestration/logs/monitoring_dashboard.json")
            with open(dashboard_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info("Dashboard updated")
            
        except Exception as e:
            self.logger.error(f"Failed to update dashboard: {e}")

    def stop_monitoring(self):
        """Stop monitoring system"""
        self.running = False
        self.logger.info("Stopping monitoring system")

def main():
    """Main entry point for monitoring system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitoring and Alerting System")
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--once', action='store_true', help='Run monitoring cycle once')
    parser.add_argument('--report', action='store_true', help='Generate status report')
    
    args = parser.parse_args()
    
    monitoring_system = MonitoringAlertingSystem()
    
    if args.report:
        report = monitoring_system.generate_status_report()
        print(json.dumps(report, indent=2))
        return
    
    if args.once:
        monitoring_system.run_monitoring_cycle()
        return
    
    if args.daemon:
        monitoring_system.start_monitoring()
    else:
        # Run for a limited time
        monitoring_system.start_monitoring()
        try:
            time.sleep(300)  # Run for 5 minutes
        except KeyboardInterrupt:
            pass
        finally:
            monitoring_system.stop_monitoring()

if __name__ == "__main__":
    main()