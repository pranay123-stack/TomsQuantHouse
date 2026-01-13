"""
Redis Health Check and Monitoring Script
Provides comprehensive monitoring for Redis infrastructure
"""

import redis
import time
import psutil
import json
import logging
import smtplib
import threading
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Any, Optional
import argparse
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('redis_health.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RedisHealthMonitor:
    """Redis health monitoring and alerting system"""
    
    def __init__(self, host='localhost', port=6379, password='trading_framework_2025'):
        """Initialize health monitor"""
        self.host = host
        self.port = port
        self.password = password
        self.redis_client = None
        self.alerts_sent = {}
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Connect to Redis
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=False,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def check_connection(self) -> Dict[str, Any]:
        """Check Redis connection status"""
        try:
            start_time = time.time()
            response = self.redis_client.ping()
            response_time = time.time() - start_time
            
            return {
                'status': 'healthy' if response else 'unhealthy',
                'response_time_ms': round(response_time * 1000, 2),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Check Redis memory usage"""
        try:
            info = self.redis_client.info('memory')
            memory_usage = {
                'used_memory': info.get('used_memory', 0),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_rss': info.get('used_memory_rss', 0),
                'maxmemory': info.get('maxmemory', 0),
                'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0)
            }
            
            # Calculate usage percentage
            if memory_usage['maxmemory'] > 0:
                usage_percent = (memory_usage['used_memory'] / memory_usage['maxmemory']) * 100
            else:
                usage_percent = 0
            
            return {
                'status': 'healthy' if usage_percent < 80 else 'warning' if usage_percent < 90 else 'critical',
                'usage_percent': round(usage_percent, 2),
                'memory_details': memory_usage,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_database_stats(self) -> Dict[str, Any]:
        """Check individual database statistics"""
        db_stats = {}
        total_keys = 0
        
        try:
            # Check keyspace info for all databases
            keyspace_info = self.redis_client.info('keyspace')
            
            for db_num in range(16):  # Check all 16 possible databases
                db_key = f"db{db_num}"
                if db_key in keyspace_info:
                    db_info = keyspace_info[db_key]
                    keys = int(db_info.get('keys', 0))
                    expires = int(db_info.get('expires', 0))
                    total_keys += keys
                    
                    db_stats[db_num] = {
                        'keys': keys,
                        'expires': expires,
                        'avg_ttl': db_info.get('avg_ttl', 0)
                    }
            
            return {
                'status': 'healthy',
                'total_keys': total_keys,
                'database_stats': db_stats,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_performance_metrics(self) -> Dict[str, Any]:
        """Check Redis performance metrics"""
        try:
            info = self.redis_client.info()
            
            metrics = {
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'total_connections_received': info.get('total_connections_received', 0),
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'expired_keys': info.get('expired_keys', 0),
                'evicted_keys': info.get('evicted_keys', 0)
            }
            
            # Calculate hit ratio
            total_requests = metrics['keyspace_hits'] + metrics['keyspace_misses']
            hit_ratio = (metrics['keyspace_hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'status': 'healthy' if hit_ratio > 80 else 'warning' if hit_ratio > 60 else 'critical',
                'hit_ratio_percent': round(hit_ratio, 2),
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_persistence_status(self) -> Dict[str, Any]:
        """Check Redis persistence status"""
        try:
            rdb_info = self.redis_client.info('persistence')
            
            return {
                'status': 'healthy',
                'rdb_bgsave_in_progress': rdb_info.get('rdb_bgsave_in_progress', 0),
                'rdb_last_save_time': rdb_info.get('rdb_last_save_time', 0),
                'rdb_last_bgsave_status': rdb_info.get('rdb_last_bgsave_status', 'unknown'),
                'aof_enabled': rdb_info.get('aof_enabled', 0),
                'aof_rewrite_in_progress': rdb_info.get('aof_rewrite_in_progress', 0),
                'aof_last_write_status': rdb_info.get('aof_last_write_status', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """Check system resources"""
        try:
            # Get system memory and CPU usage
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'status': 'healthy',
                'system_memory': {
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'used_percent': memory.percent
                },
                'system_disk': {
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'used_percent': round((disk.used / disk.total) * 100, 2)
                },
                'cpu_usage_percent': psutil.cpu_percent(interval=1),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_full_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check"""
        logger.info("Running full Redis health check...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        # Run all health checks
        health_report['checks']['connection'] = self.check_connection()
        health_report['checks']['memory'] = self.check_memory_usage()
        health_report['checks']['database'] = self.check_database_stats()
        health_report['checks']['performance'] = self.check_performance_metrics()
        health_report['checks']['persistence'] = self.check_persistence_status()
        health_report['checks']['system'] = self.check_system_resources()
        
        # Determine overall status
        statuses = [check.get('status') for check in health_report['checks'].values()]
        if 'error' in statuses:
            health_report['overall_status'] = 'error'
        elif 'critical' in statuses:
            health_report['overall_status'] = 'critical'
        elif 'warning' in statuses:
            health_report['overall_status'] = 'warning'
        
        # Log health report
        logger.info(f"Health check completed - Overall status: {health_report['overall_status']}")
        
        # Check if alerts need to be sent
        self._check_alert_conditions(health_report)
        
        return health_report
    
    def _check_alert_conditions(self, health_report: Dict[str, Any]):
        """Check if alert conditions are met"""
        # Memory usage alert
        memory_check = health_report['checks'].get('memory', {})
        if memory_check.get('status') in ['critical', 'warning']:
            self._send_alert(
                'Memory Usage Alert',
                f"Redis memory usage is {memory_check.get('usage_percent', 0)}%",
                memory_check.get('status')
            )
        
        # Connection issues
        connection_check = health_report['checks'].get('connection', {})
        if connection_check.get('status') != 'healthy':
            self._send_alert(
                'Connection Alert',
                f"Redis connection issue: {connection_check.get('error', 'Unknown error')}",
                'critical'
            )
        
        # Performance issues
        performance_check = health_report['checks'].get('performance', {})
        if performance_check.get('status') in ['critical', 'warning']:
            self._send_alert(
                'Performance Alert',
                f"Redis performance degraded - Hit ratio: {performance_check.get('hit_ratio_percent', 0)}%",
                performance_check.get('status')
            )
    
    def _send_alert(self, subject: str, message: str, severity: str):
        """Send alert notification"""
        alert_key = f"{subject}:{severity}"
        
        # Don't send duplicate alerts within 1 hour
        if alert_key in self.alerts_sent:
            last_sent = self.alerts_sent[alert_key]
            if datetime.now() - last_sent < timedelta(hours=1):
                return
        
        try:
            # Log alert
            logger.warning(f"ALERT [{severity.upper()}]: {message}")
            
            # Send email alert if configured
            if hasattr(self, 'email_config') and self.email_config:
                self._send_email_alert(subject, message, severity)
            
            # Record alert sent time
            self.alerts_sent[alert_key] = datetime.now()
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _send_email_alert(self, subject: str, message: str, severity: str):
        """Send email alert"""
        try:
            email_config = self.email_config
            
            msg = MimeMultipart()
            msg['From'] = email_config['from']
            msg['To'] = ', '.join(email_config['to'])
            msg['Subject'] = f"[{severity.upper()}] {subject}"
            
            body = f"""
            Alert Details:
            - Severity: {severity.upper()}
            - Timestamp: {datetime.now().isoformat()}
            - Message: {message}
            
            This is an automated alert from the Redis Health Monitor.
            Please investigate the issue immediately.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def start_monitoring(self, check_interval: int = 300, email_config: Optional[Dict] = None):
        """Start continuous monitoring"""
        if email_config:
            self.email_config = email_config
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Started Redis monitoring with {check_interval}s interval")
    
    def _monitoring_loop(self, check_interval: int):
        """Continuous monitoring loop"""
        while self.is_monitoring:
            try:
                self.run_full_health_check()
                time.sleep(check_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait before retrying
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=10)
        logger.info("Stopped Redis monitoring")
    
    def export_health_report(self, filepath: str):
        """Export health report to file"""
        try:
            health_report = self.run_full_health_check()
            with open(filepath, 'w') as f:
                json.dump(health_report, f, indent=2)
            logger.info(f"Health report exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export health report: {e}")

# CLI Interface
def main():
    parser = argparse.ArgumentParser(description='Redis Health Monitor')
    parser.add_argument('--host', default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--password', default='trading_framework_2025', help='Redis password')
    parser.add_argument('--check-interval', type=int, default=300, help='Monitoring check interval in seconds')
    parser.add_argument('--export', help='Export health report to file')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--email-config', help='Path to email configuration file')
    
    args = parser.parse_args()
    
    # Load email config if provided
    email_config = None
    if args.email_config:
        try:
            with open(args.email_config, 'r') as f:
                email_config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load email config: {e}")
    
    # Initialize monitor
    monitor = RedisHealthMonitor(args.host, args.port, args.password)
    
    try:
        if args.monitor:
            # Start continuous monitoring
            monitor.start_monitoring(args.check_interval, email_config)
            print(f"Monitoring started. Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
        else:
            # Run single health check
            health_report = monitor.run_full_health_check()
            
            # Print results
            print(f"\n=== Redis Health Report ===")
            print(f"Overall Status: {health_report['overall_status'].upper()}")
            print(f"Timestamp: {health_report['timestamp']}")
            
            for check_name, check_result in health_report['checks'].items():
                status = check_result.get('status', 'unknown')
                print(f"\n{check_name.capitalize()}: {status.upper()}")
                
                if check_name == 'memory':
                    print(f"  Usage: {check_result.get('usage_percent', 0)}%")
                elif check_name == 'performance':
                    print(f"  Hit Ratio: {check_result.get('hit_ratio_percent', 0)}%")
                elif check_name == 'connection':
                    print(f"  Response Time: {check_result.get('response_time_ms', 0)}ms")
            
            # Export if requested
            if args.export:
                monitor.export_health_report(args.export)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        if args.monitor:
            monitor.stop_monitoring()

if __name__ == "__main__":
    main()