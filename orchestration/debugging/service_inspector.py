#!/usr/bin/env python3
"""
Debugging and Troubleshooting Tools
Comprehensive debugging utilities for service orchestration
"""

import os
import sys
import json
import yaml
import time
import psutil
import logging
import subprocess
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import traceback

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class DebugSession:
    session_id: str
    start_time: datetime
    services: List[str]
    issues: List[str]
    diagnostics: Dict[str, Any]

class ServiceInspector:
    """Service inspection and analysis tool"""
    
    def __init__(self, config_path: str = "/workspace/orchestration/config/services.yaml"):
        self.config_path = config_path
        self.services = {}
        
        # Setup logging
        self.setup_logging()
        self.load_configuration()
    
    def setup_logging(self):
        """Setup logging for service inspector"""
        log_dir = Path("/workspace/orchestration/logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger('ServiceInspector')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_dir / 'service_inspector.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def load_configuration(self):
        """Load service configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.services = config.get('services', {})
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
    
    def inspect_service_processes(self, service_name: str) -> Dict[str, Any]:
        """Inspect all processes related to a service"""
        try:
            processes = []
            service_config = self.services.get(service_name, {})
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    # Match service processes
                    if (service_name in cmdline.lower() or 
                        any(service_name in arg for arg in pinfo['cmdline'])):
                        
                        proc_info = {
                            'pid': pinfo['pid'],
                            'name': pinfo['name'],
                            'cmdline': cmdline,
                            'cpu_percent': pinfo['cpu_percent'],
                            'memory_percent': pinfo['memory_percent'],
                            'status': pinfo['status'],
                            'create_time': datetime.fromtimestamp(proc.create_time()).isoformat(),
                            'connections': len(proc.connections()),
                            'open_files': len(proc.open_files()) if hasattr(proc, 'open_files') else 0
                        }
                        processes.append(proc_info)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'service_name': service_name,
                'process_count': len(processes),
                'processes': processes
            }
            
        except Exception as e:
            self.logger.error(f"Error inspecting service processes for {service_name}: {e}")
            return {'service_name': service_name, 'error': str(e)}
    
    def inspect_service_network(self, service_name: str) -> Dict[str, Any]:
        """Inspect network connections for a service"""
        try:
            connections = []
            service_config = self.services.get(service_name, {})
            
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    if (service_name in cmdline.lower() or 
                        any(service_name in arg for arg in pinfo['cmdline'])):
                        
                        proc_obj = psutil.Process(pinfo['pid'])
                        proc_connections = proc_obj.connections()
                        
                        for conn in proc_connections:
                            conn_info = {
                                'pid': pinfo['pid'],
                                'family': conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
                                'type': conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                                'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                                'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                                'status': conn.status
                            }
                            connections.append(conn_info)
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'service_name': service_name,
                'connection_count': len(connections),
                'connections': connections
            }
            
        except Exception as e:
            self.logger.error(f"Error inspecting service network for {service_name}: {e}")
            return {'service_name': service_name, 'error': str(e)}
    
    def inspect_service_files(self, service_name: str) -> Dict[str, Any]:
        """Inspect file handles for a service"""
        try:
            open_files = []
            service_config = self.services.get(service_name, {})
            
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    if (service_name in cmdline.lower() or 
                        any(service_name in arg for arg in pinfo['cmdline'])):
                        
                        proc_obj = psutil.Process(pinfo['pid'])
                        if hasattr(proc_obj, 'open_files'):
                            files = proc_obj.open_files()
                            for file_info in files:
                                open_files.append({
                                    'pid': pinfo['pid'],
                                    'path': file_info.path,
                                    'position': file_info.position if hasattr(file_info, 'position') else None
                                })
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'service_name': service_name,
                'open_file_count': len(open_files),
                'open_files': open_files
            }
            
        except Exception as e:
            self.logger.error(f"Error inspecting service files for {service_name}: {e}")
            return {'service_name': service_name, 'error': str(e)}

class NetworkAnalyzer:
    """Network connectivity and analysis tool"""
    
    def __init__(self):
        self.logger = logging.getLogger('NetworkAnalyzer')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler("/workspace/orchestration/logs/network_analyzer.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def check_port_connectivity(self, host: str, port: int, timeout: int = 5) -> Dict[str, Any]:
        """Check if a port is accessible"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return {
                'host': host,
                'port': port,
                'accessible': result == 0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'host': host,
                'port': port,
                'accessible': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_service_endpoints(self, services: Dict[str, Any]) -> Dict[str, Any]:
        """Check connectivity to all service endpoints"""
        results = {}
        
        for service_name, service_config in services.items():
            health_endpoint = service_config.get('health_endpoint')
            if health_endpoint:
                try:
                    # Parse URL
                    if health_endpoint.startswith('http'):
                        from urllib.parse import urlparse
                        parsed = urlparse(health_endpoint)
                        host = parsed.hostname
                        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                    else:
                        # Assume it's just a host:port
                        host, port = health_endpoint.split(':')
                        port = int(port)
                    
                    connectivity = self.check_port_connectivity(host, port)
                    results[service_name] = connectivity
                    
                except Exception as e:
                    results[service_name] = {
                        'service': service_name,
                        'error': f"Failed to parse endpoint: {e}",
                        'timestamp': datetime.now().isoformat()
                    }
        
        return results
    
    def analyze_network_topology(self) -> Dict[str, Any]:
        """Analyze network topology and connections"""
        try:
            connections = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    proc_obj = psutil.Process(pinfo['pid'])
                    proc_connections = proc_obj.connections()
                    
                    for conn in proc_connections:
                        if conn.laddr and conn.raddr:
                            connection_info = {
                                'pid': pinfo['pid'],
                                'process': pinfo['name'],
                                'command': cmdline[:100],  # Truncate for readability
                                'local': f"{conn.laddr.ip}:{conn.laddr.port}",
                                'remote': f"{conn.raddr.ip}:{conn.raddr.port}",
                                'status': conn.status
                            }
                            connections.append(connection_info)
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Analyze connections by remote address
            remote_addresses = {}
            for conn in connections:
                remote = conn['remote']
                if remote not in remote_addresses:
                    remote_addresses[remote] = []
                remote_addresses[remote].append(conn)
            
            return {
                'total_connections': len(connections),
                'unique_remote_addresses': len(remote_addresses),
                'top_remote_addresses': sorted(
                    [(addr, len(conns)) for addr, conns in remote_addresses.items()],
                    key=lambda x: x[1], reverse=True
                )[:10],
                'sample_connections': connections[:20]  # Sample for inspection
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing network topology: {e}")
            return {'error': str(e)}

class LogAnalyzer:
    """Log file analysis and pattern detection tool"""
    
    def __init__(self):
        self.logger = logging.getLogger('LogAnalyzer')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler("/workspace/orchestration/logs/log_analyzer.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def analyze_log_patterns(self, log_directory: Path, pattern: str = "ERROR") -> Dict[str, Any]:
        """Analyze log files for specific patterns"""
        try:
            matches = []
            error_count = 0
            warning_count = 0
            
            for log_file in log_directory.rglob("*.log"):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern in line.upper():
                                matches.append({
                                    'file': str(log_file),
                                    'line_number': line_num,
                                    'content': line.strip()
                                })
                                if 'ERROR' in line.upper():
                                    error_count += 1
                                elif 'WARNING' in line.upper():
                                    warning_count += 1
                                
                except Exception as e:
                    self.logger.warning(f"Error reading {log_file}: {e}")
            
            return {
                'pattern': pattern,
                'total_matches': len(matches),
                'error_count': error_count,
                'warning_count': warning_count,
                'matches': matches[-50:]  # Last 50 matches
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing log patterns: {e}")
            return {'error': str(e)}
    
    def analyze_performance_logs(self, log_directory: Path) -> Dict[str, Any]:
        """Analyze performance-related log entries"""
        try:
            performance_metrics = {
                'response_times': [],
                'memory_usage': [],
                'cpu_usage': []
            }
            
            for log_file in log_directory.rglob("*.log"):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # Extract response times
                            if 'response_time' in line.lower():
                                try:
                                    # Simple regex-like extraction
                                    import re
                                    match = re.search(r'response_time[\s:]+([\d.]+)', line, re.IGNORECASE)
                                    if match:
                                        performance_metrics['response_times'].append(float(match.group(1)))
                                except:
                                    pass
                            
                            # Extract memory usage
                            if 'memory' in line.lower() and ('mb' in line.lower() or '%' in line):
                                try:
                                    import re
                                    match = re.search(r'memory[\s:]+([\d.]+)', line, re.IGNORECASE)
                                    if match:
                                        performance_metrics['memory_usage'].append(float(match.group(1)))
                                except:
                                    pass
                            
                            # Extract CPU usage
                            if 'cpu' in line.lower() and '%' in line:
                                try:
                                    import re
                                    match = re.search(r'cpu[\s:]+([\d.]+)', line, re.IGNORECASE)
                                    if match:
                                        performance_metrics['cpu_usage'].append(float(match.group(1)))
                                except:
                                    pass
                                
                except Exception as e:
                    self.logger.warning(f"Error processing {log_file}: {e}")
            
            # Calculate statistics
            stats = {}
            for metric_name, values in performance_metrics.items():
                if values:
                    stats[metric_name] = {
                        'count': len(values),
                        'min': min(values),
                        'max': max(values),
                        'avg': sum(values) / len(values),
                        'recent_values': values[-10:]  # Last 10 values
                    }
                else:
                    stats[metric_name] = {'count': 0}
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance logs: {e}")
            return {'error': str(e)}
    
    def generate_log_report(self, log_directory: Path) -> Dict[str, Any]:
        """Generate comprehensive log analysis report"""
        try:
            # Count log files and sizes
            log_files = list(log_directory.rglob("*.log"))
            total_size = sum(f.stat().st_size for f in log_files if f.is_file())
            
            # Analyze error patterns
            error_analysis = self.analyze_log_patterns(log_directory, "ERROR")
            warning_analysis = self.analyze_log_patterns(log_directory, "WARNING")
            
            # Analyze performance
            performance_analysis = self.analyze_performance_logs(log_directory)
            
            # Recent activity (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_activity = []
            
            for log_file in log_files:
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time > cutoff_time:
                        recent_activity.append(str(log_file))
                except:
                    pass
            
            return {
                'timestamp': datetime.now().isoformat(),
                'log_summary': {
                    'total_files': len(log_files),
                    'total_size_mb': total_size / (1024 * 1024),
                    'recent_files_24h': len(recent_activity)
                },
                'error_analysis': error_analysis,
                'warning_analysis': warning_analysis,
                'performance_analysis': performance_analysis
            }
            
        except Exception as e:
            self.logger.error(f"Error generating log report: {e}")
            return {'error': str(e)}

class SystemDiagnostics:
    """System-level diagnostic tool"""
    
    def __init__(self):
        self.logger = logging.getLogger('SystemDiagnostics')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler("/workspace/orchestration/logs/system_diagnostics.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def run_system_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostics"""
        try:
            diagnostics = {
                'timestamp': datetime.now().isoformat(),
                'system_info': self.get_system_info(),
                'resource_usage': self.get_resource_usage(),
                'process_summary': self.get_process_summary(),
                'disk_health': self.check_disk_health(),
                'network_health': self.check_network_health(),
                'security_checks': self.run_security_checks()
            }
            
            return diagnostics
            
        except Exception as e:
            self.logger.error(f"Error running system diagnostics: {e}")
            return {'error': str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        try:
            return {
                'platform': sys.platform,
                'python_version': sys.version,
                'cpu_count': psutil.cpu_count(),
                'cpu_count_logical': psutil.cpu_count(logical=True),
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'hostname': socket.gethostname()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': dict(psutil.virtual_memory()._asdict()),
                'swap': dict(psutil.swap_memory()._asdict()),
                'disk_usage': dict(psutil.disk_usage('/workspace')._asdict())
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_process_summary(self) -> Dict[str, Any]:
        """Get process summary"""
        try:
            process_count = len(list(psutil.process_iter()))
            return {
                'total_processes': process_count,
                'running_processes': len([p for p in psutil.process_iter(['status']) 
                                        if p.info['status'] == psutil.STATUS_RUNNING]),
                'zombie_processes': len([p for p in psutil.process_iter(['status']) 
                                       if p.info['status'] == psutil.STATUS_ZOMBIE])
            }
        except Exception as e:
            return {'error': str(e)}
    
    def check_disk_health(self) -> Dict[str, Any]:
        """Check disk health indicators"""
        try:
            disk_usage = psutil.disk_usage('/workspace')
            return {
                'total_gb': disk_usage.total / (1024**3),
                'used_gb': disk_usage.used / (1024**3),
                'free_gb': disk_usage.free / (1024**3),
                'usage_percent': (disk_usage.used / disk_usage.total) * 100
            }
        except Exception as e:
            return {'error': str(e)}
    
    def check_network_health(self) -> Dict[str, Any]:
        """Check network health"""
        try:
            network_io = psutil.net_io_counters()
            return {
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv,
                'packets_sent': network_io.packets_sent,
                'packets_recv': network_io.packets_recv,
                'errin': network_io.errin,
                'errout': network_io.errout
            }
        except Exception as e:
            return {'error': str(e)}
    
    def run_security_checks(self) -> Dict[str, Any]:
        """Run basic security checks"""
        try:
            checks = {
                'directory_permissions': self.check_directory_permissions(),
                'file_permissions': self.check_file_permissions(),
                'process_ownership': self.check_process_ownership()
            }
            return checks
        except Exception as e:
            return {'error': str(e)}
    
    def check_directory_permissions(self) -> Dict[str, Any]:
        """Check critical directory permissions"""
        try:
            critical_dirs = [
                '/workspace/orchestration',
                '/workspace/code',
                '/workspace/orchestration/logs',
                '/workspace/orchestration/backup'
            ]
            
            permissions = {}
            for dir_path in critical_dirs:
                try:
                    stat_info = os.stat(dir_path)
                    permissions[dir_path] = {
                        'exists': True,
                        'mode': oct(stat_info.st_mode)[-3:],
                        'owner_uid': stat_info.st_uid
                    }
                except Exception as e:
                    permissions[dir_path] = {'exists': False, 'error': str(e)}
            
            return permissions
        except Exception as e:
            return {'error': str(e)}
    
    def check_file_permissions(self) -> Dict[str, Any]:
        """Check critical file permissions"""
        try:
            critical_files = [
                '/workspace/orchestration/config/services.yaml',
                '/workspace/orchestration/orchestrator.py'
            ]
            
            permissions = {}
            for file_path in critical_files:
                try:
                    stat_info = os.stat(file_path)
                    permissions[file_path] = {
                        'exists': True,
                        'mode': oct(stat_info.st_mode)[-3:],
                        'owner_uid': stat_info.st_uid,
                        'size': stat_info.st_size
                    }
                except Exception as e:
                    permissions[file_path] = {'exists': False, 'error': str(e)}
            
            return permissions
        except Exception as e:
            return {'error': str(e)}
    
    def check_process_ownership(self) -> Dict[str, Any]:
        """Check process ownership anomalies"""
        try:
            processes_by_user = {}
            for proc in psutil.process_iter(['uid', 'username']):
                try:
                    uid = proc.info['uid']
                    username = proc.info['username']
                    if uid not in processes_by_user:
                        processes_by_user[uid] = {'username': username, 'count': 0}
                    processes_by_user[uid]['count'] += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'unique_users': len(processes_by_user),
                'user_process_counts': processes_by_user
            }
        except Exception as e:
            return {'error': str(e)}

class DebugSessionManager:
    """Manage debugging sessions"""
    
    def __init__(self):
        self.sessions = {}
        self.active_sessions = {}
        
        self.logger = logging.getLogger('DebugSessionManager')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler("/workspace/orchestration/logs/debug_sessions.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def create_debug_session(self, session_id: str, services: List[str] = None) -> DebugSession:
        """Create a new debug session"""
        session = DebugSession(
            session_id=session_id,
            start_time=datetime.now(),
            services=services or [],
            issues=[],
            diagnostics={}
        )
        
        self.sessions[session_id] = session
        self.active_sessions[session_id] = session
        
        self.logger.info(f"Created debug session: {session_id}")
        return session
    
    def add_issue_to_session(self, session_id: str, issue: str):
        """Add an issue to a debug session"""
        if session_id in self.sessions:
            self.sessions[session_id].issues.append(issue)
            self.logger.info(f"Added issue to session {session_id}: {issue}")
    
    def add_diagnostic_to_session(self, session_id: str, diagnostic_name: str, diagnostic_data: Dict[str, Any]):
        """Add diagnostic data to a debug session"""
        if session_id in self.sessions:
            self.sessions[session_id].diagnostics[diagnostic_name] = diagnostic_data
            self.logger.info(f"Added diagnostic to session {session_id}: {diagnostic_name}")
    
    def generate_session_report(self, session_id: str) -> Dict[str, Any]:
        """Generate report for a debug session"""
        if session_id not in self.sessions:
            return {'error': f'Session {session_id} not found'}
        
        session = self.sessions[session_id]
        
        report = {
            'session_id': session_id,
            'start_time': session.start_time.isoformat(),
            'duration': str(datetime.now() - session.start_time),
            'services': session.services,
            'issues': session.issues,
            'diagnostics': session.diagnostics,
            'summary': {
                'total_issues': len(session.issues),
                'total_diagnostics': len(session.diagnostics)
            }
        }
        
        return report
    
    def save_session_report(self, session_id: str) -> Path:
        """Save session report to file"""
        report = self.generate_session_report(session_id)
        
        sessions_dir = Path("/workspace/orchestration/logs/debug_sessions")
        sessions_dir.mkdir(exist_ok=True)
        
        report_file = sessions_dir / f"debug_session_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Saved debug session report: {report_file}")
        return report_file

def main():
    """Main entry point for debugging tools"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debugging and Troubleshooting Tools")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Service inspection command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect service')
    inspect_parser.add_argument('service_name', help='Service name to inspect')
    inspect_parser.add_argument('--type', choices=['process', 'network', 'files', 'all'], 
                               default='all', help='Type of inspection')
    
    # Network analysis command
    network_parser = subparsers.add_parser('network', help='Network analysis')
    network_parser.add_argument('--check-endpoints', action='store_true', help='Check service endpoints')
    network_parser.add_argument('--topology', action='store_true', help='Analyze network topology')
    
    # Log analysis command
    log_parser = subparsers.add_parser('logs', help='Log analysis')
    log_parser.add_argument('--pattern', help='Pattern to search for')
    log_parser.add_argument('--performance', action='store_true', help='Analyze performance logs')
    log_parser.add_argument('--report', action='store_true', help='Generate comprehensive log report')
    
    # System diagnostics command
    system_parser = subparsers.add_parser('system', help='System diagnostics')
    
    # Debug session command
    session_parser = subparsers.add_parser('session', help='Debug session management')
    session_parser.add_argument('--create', help='Create new debug session')
    session_parser.add_argument('--report', help='Generate report for session')
    session_parser.add_argument('--services', nargs='+', help='Services to include in session')
    
    args = parser.parse_args()
    
    if args.command == 'inspect':
        inspector = ServiceInspector()
        if args.type == 'all':
            results = {
                'processes': inspector.inspect_service_processes(args.service_name),
                'network': inspector.inspect_service_network(args.service_name),
                'files': inspector.inspect_service_files(args.service_name)
            }
        elif args.type == 'process':
            results = inspector.inspect_service_processes(args.service_name)
        elif args.type == 'network':
            results = inspector.inspect_service_network(args.service_name)
        elif args.type == 'files':
            results = inspector.inspect_service_files(args.service_name)
        
        print(json.dumps(results, indent=2))
    
    elif args.command == 'network':
        analyzer = NetworkAnalyzer()
        results = {}
        
        if args.check_endpoints or args.topology:
            # Load services config
            config_path = "/workspace/orchestration/config/services.yaml"
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                services = config.get('services', {})
            except:
                services = {}
        
        if args.check_endpoints:
            results['endpoint_check'] = analyzer.check_service_endpoints(services)
        
        if args.topology:
            results['topology'] = analyzer.analyze_network_topology()
        
        print(json.dumps(results, indent=2))
    
    elif args.command == 'logs':
        log_dir = Path("/workspace/orchestration/logs")
        analyzer = LogAnalyzer()
        
        if args.report:
            results = analyzer.generate_log_report(log_dir)
        elif args.performance:
            results = analyzer.analyze_performance_logs(log_dir)
        elif args.pattern:
            results = analyzer.analyze_log_patterns(log_dir, args.pattern)
        else:
            results = analyzer.generate_log_report(log_dir)
        
        print(json.dumps(results, indent=2))
    
    elif args.command == 'system':
        diagnostics = SystemDiagnostics()
        results = diagnostics.run_system_diagnostics()
        print(json.dumps(results, indent=2))
    
    elif args.command == 'session':
        session_manager = DebugSessionManager()
        
        if args.create:
            session = session_manager.create_debug_session(args.create, args.services)
            print(f"Created debug session: {args.create}")
        
        elif args.report:
            report = session_manager.generate_session_report(args.report)
            print(json.dumps(report, indent=2))
            
            # Save to file
            report_file = session_manager.save_session_report(args.report)
            print(f"Report saved to: {report_file}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()