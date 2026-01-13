#!/usr/bin/env python3
"""
Network Analyzer
Advanced network connectivity and traffic analysis tool
"""

import os
import sys
import json
import logging
import socket
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import psutil

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class NetworkAnalyzer:
    def __init__(self):
        self.logger = self.setup_logging()
        self.monitoring_active = False
        self.traffic_monitor = {}
        
    def setup_logging(self):
        """Setup logging for network analyzer"""
        log_dir = Path("/workspace/orchestration/logs")
        log_dir.mkdir(exist_ok=True)
        
        logger = logging.getLogger('NetworkAnalyzer')
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(log_dir / 'network_analyzer.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
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
                'response_time_ms': None if result != 0 else timeout * 1000,
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
    
    def ping_host(self, host: str, count: int = 3) -> Dict[str, Any]:
        """Ping a host to check connectivity"""
        try:
            # Try different ping methods based on OS
            if sys.platform.startswith('win'):
                cmd = ['ping', '-n', str(count), host]
            else:
                cmd = ['ping', '-c', str(count), host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse ping results
                output_lines = result.stdout.split('\n')
                ping_times = []
                
                for line in output_lines:
                    if 'time=' in line.lower() or 'time<' in line.lower():
                        # Extract time value
                        import re
                        time_match = re.search(r'time[=<](\d+(?:\.\d+)?)', line, re.IGNORECASE)
                        if time_match:
                            ping_times.append(float(time_match.group(1)))
                
                return {
                    'host': host,
                    'accessible': True,
                    'packets_sent': count,
                    'packets_received': len(ping_times),
                    'packet_loss_percent': ((count - len(ping_times)) / count) * 100,
                    'ping_times_ms': ping_times,
                    'avg_ping_ms': sum(ping_times) / len(ping_times) if ping_times else None,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'host': host,
                    'accessible': False,
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'host': host,
                'accessible': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def trace_route(self, host: str) -> Dict[str, Any]:
        """Perform traceroute to a host"""
        try:
            # Try different traceroute methods
            if sys.platform.startswith('win'):
                cmd = ['tracert', host]
            else:
                cmd = ['traceroute', host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                hops = []
                output_lines = result.stdout.split('\n')
                
                for line in output_lines:
                    # Parse hop information
                    import re
                    hop_match = re.search(r'(\d+)\s+(.*)', line.strip())
                    if hop_match:
                        hop_num = int(hop_match.group(1))
                        hop_info = hop_match.group(2).strip()
                        
                        # Extract hostnames and times
                        times = re.findall(r'(\d+(?:\.\d+)?)\s*ms', hop_info)
                        times = [float(t) for t in times]
                        
                        hops.append({
                            'hop': hop_num,
                            'info': hop_info,
                            'response_times_ms': times,
                            'avg_response_time_ms': sum(times) / len(times) if times else None
                        })
                
                return {
                    'host': host,
                    'total_hops': len(hops),
                    'hops': hops,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'host': host,
                    'error': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'host': host,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def check_dns_resolution(self, hostname: str) -> Dict[str, Any]:
        """Check DNS resolution for a hostname"""
        try:
            start_time = time.time()
            ip_addresses = []
            
            # Try to resolve hostname
            try:
                info = socket.getaddrinfo(hostname, None)
                ip_addresses = list(set([addr[4][0] for addr in info]))
            except:
                # Fallback to single resolution
                ip_address = socket.gethostbyname(hostname)
                ip_addresses = [ip_address]
            
            resolution_time = (time.time() - start_time) * 1000  # milliseconds
            
            return {
                'hostname': hostname,
                'ip_addresses': ip_addresses,
                'resolution_time_ms': resolution_time,
                'successful': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'hostname': hostname,
                'ip_addresses': [],
                'resolution_time_ms': None,
                'successful': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def monitor_network_traffic(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Monitor network traffic for a period of time"""
        try:
            self.logger.info(f"Starting network traffic monitoring for {duration_seconds} seconds")
            
            # Get initial network stats
            initial_stats = psutil.net_io_counters()
            start_time = time.time()
            
            # Monitor for specified duration
            time.sleep(duration_seconds)
            
            # Get final network stats
            final_stats = psutil.net_io_counters()
            end_time = time.time()
            
            # Calculate traffic rates
            duration = end_time - start_time
            bytes_sent_rate = (final_stats.bytes_sent - initial_stats.bytes_sent) / duration
            bytes_recv_rate = (final_stats.bytes_recv - initial_stats.bytes_recv) / duration
            packets_sent_rate = (final_stats.packets_sent - initial_stats.packets_sent) / duration
            packets_recv_rate = (final_stats.packets_recv - initial_stats.packets_recv) / duration
            
            return {
                'duration_seconds': duration,
                'bytes_sent_rate_bps': bytes_sent_rate,
                'bytes_recv_rate_bps': bytes_recv_rate,
                'packets_sent_rate_pps': packets_sent_rate,
                'packets_recv_rate_pps': packets_recv_rate,
                'total_bytes_sent': final_stats.bytes_sent - initial_stats.bytes_sent,
                'total_bytes_recv': final_stats.bytes_recv - initial_stats.bytes_recv,
                'total_packets_sent': final_stats.packets_sent - initial_stats.packets_sent,
                'total_packets_recv': final_stats.packets_recv - initial_stats.packets_recv,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error monitoring network traffic: {e}")
            return {'error': str(e)}
    
    def analyze_service_connectivity(self, service_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze connectivity for a service"""
        try:
            service_config = config.get('services', {}).get(service_name, {})
            health_endpoint = service_config.get('health_endpoint')
            
            results = {
                'service_name': service_name,
                'analysis_results': {}
            }
            
            if health_endpoint:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(health_endpoint)
                    host = parsed.hostname
                    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
                    
                    # Test basic connectivity
                    port_check = self.check_port_connectivity(host, port)
                    results['analysis_results']['port_connectivity'] = port_check
                    
                    # Test DNS resolution
                    dns_check = self.check_dns_resolution(host)
                    results['analysis_results']['dns_resolution'] = dns_check
                    
                    # Test ping if host is not localhost
                    if host not in ['localhost', '127.0.0.1']:
                        ping_check = self.ping_host(host)
                        results['analysis_results']['ping'] = ping_check
                    
                except Exception as e:
                    results['analysis_results']['error'] = f"Failed to analyze service connectivity: {e}"
            else:
                results['analysis_results']['error'] = "No health endpoint configured"
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing service connectivity for {service_name}: {e}")
            return {'service_name': service_name, 'error': str(e)}
    
    def generate_network_report(self, config_path: str = "/workspace/orchestration/config/services.yaml") -> Dict[str, Any]:
        """Generate comprehensive network analysis report"""
        try:
            # Load service configuration
            try:
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                services = config.get('services', {})
            except:
                services = {}
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'network_interface_summary': self.get_network_interface_summary(),
                'service_connectivity': {},
                'traffic_analysis': self.monitor_network_traffic(30),
                'overall_health': 'unknown'
            }
            
            # Analyze each service
            healthy_services = 0
            total_services = 0
            
            for service_name in services:
                total_services += 1
                service_analysis = self.analyze_service_connectivity(service_name, config)
                report['service_connectivity'][service_name] = service_analysis
                
                # Check if service is healthy
                if 'analysis_results' in service_analysis:
                    results = service_analysis['analysis_results']
                    if 'error' not in results:
                        port_connectivity = results.get('port_connectivity', {})
                        if port_connectivity.get('accessible', False):
                            healthy_services += 1
            
            # Overall health assessment
            if total_services > 0:
                health_percentage = (healthy_services / total_services) * 100
                if health_percentage >= 90:
                    report['overall_health'] = 'excellent'
                elif health_percentage >= 75:
                    report['overall_health'] = 'good'
                elif health_percentage >= 50:
                    report['overall_health'] = 'fair'
                else:
                    report['overall_health'] = 'poor'
            
            report['health_summary'] = {
                'total_services': total_services,
                'healthy_services': healthy_services,
                'health_percentage': (healthy_services / max(total_services, 1)) * 100
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating network report: {e}")
            return {'error': str(e)}
    
    def get_network_interface_summary(self) -> Dict[str, Any]:
        """Get summary of network interfaces"""
        try:
            interfaces = {}
            
            for interface_name, interface_addresses in psutil.net_if_addrs().items():
                interface_info = {
                    'name': interface_name,
                    'addresses': []
                }
                
                for addr in interface_addresses:
                    address_info = {
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    }
                    interface_info['addresses'].append(address_info)
                
                interfaces[interface_name] = interface_info
            
            # Get interface statistics
            interface_stats = {}
            for interface_name, stats in psutil.net_if_stats().items():
                interface_stats[interface_name] = {
                    'is_up': stats.isup,
                    'mtu': stats.mtu,
                    'speed': stats.speed
                }
            
            return {
                'interfaces': interfaces,
                'interface_stats': interface_stats,
                'total_interfaces': len(interfaces)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting network interface summary: {e}")
            return {'error': str(e)}

def main():
    """Main entry point for network analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Network Connectivity Analyzer")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Port connectivity check
    port_parser = subparsers.add_parser('port', help='Check port connectivity')
    port_parser.add_argument('host', help='Host to check')
    port_parser.add_argument('port', type=int, help='Port number')
    port_parser.add_argument('--timeout', type=int, default=5, help='Timeout in seconds')
    
    # Ping command
    ping_parser = subparsers.add_parser('ping', help='Ping a host')
    ping_parser.add_argument('host', help='Host to ping')
    ping_parser.add_argument('--count', type=int, default=3, help='Number of pings')
    
    # Traceroute command
    trace_parser = subparsers.add_parser('trace', help='Traceroute to host')
    trace_parser.add_argument('host', help='Host to traceroute')
    
    # DNS resolution check
    dns_parser = subparsers.add_parser('dns', help='Check DNS resolution')
    dns_parser.add_argument('hostname', help='Hostname to resolve')
    
    # Traffic monitoring
    monitor_parser = subparsers.add_parser('monitor', help='Monitor network traffic')
    monitor_parser.add_argument('--duration', type=int, default=60, help='Monitoring duration in seconds')
    
    # Service connectivity analysis
    service_parser = subparsers.add_parser('service', help='Analyze service connectivity')
    service_parser.add_argument('service_name', help='Service name')
    
    # Comprehensive report
    report_parser = subparsers.add_parser('report', help='Generate network report')
    
    args = parser.parse_args()
    
    analyzer = NetworkAnalyzer()
    
    if args.command == 'port':
        result = analyzer.check_port_connectivity(args.host, args.port, args.timeout)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'ping':
        result = analyzer.ping_host(args.host, args.count)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'trace':
        result = analyzer.trace_route(args.host)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'dns':
        result = analyzer.check_dns_resolution(args.hostname)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'monitor':
        result = analyzer.monitor_network_traffic(args.duration)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'service':
        # Load config
        config_path = "/workspace/orchestration/config/services.yaml"
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except:
            config = {}
        
        result = analyzer.analyze_service_connectivity(args.service_name, config)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'report':
        result = analyzer.generate_network_report()
        print(json.dumps(result, indent=2))
        
        # Save report to file
        report_file = Path("/workspace/orchestration/logs/network_report.json")
        with open(report_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nReport saved to: {report_file}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()