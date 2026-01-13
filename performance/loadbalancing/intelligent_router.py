#!/usr/bin/env python3
"""
Load Balancing and Intelligent Routing
Implements intelligent load balancing algorithms and routing strategies
"""

import asyncio
import time
import random
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import aiohttp
import aiofiles
import json
from urllib.parse import urljoin, urlparse

class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    LEAST_RESPONSE_TIME = "least_response_time"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"
    ADAPTIVE = "adaptive"

class HealthCheckStatus(Enum):
    """Health check statuses"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    WARNING = "warning"

class RoutingStrategy(Enum):
    """Traffic routing strategies"""
    GEOGRAPHIC = "geographic"
    CONTENT_AWARE = "content_aware"
    USER_BEHAVIOR = "user_behavior"
    LOAD_BASED = "load_based"
    FAILOVER = "failover"

@dataclass
class Server:
    """Backend server definition"""
    server_id: str
    host: str
    port: int
    weight: int
    max_connections: int = 1000
    current_connections: int = 0
    response_time_ms: float = 0.0
    error_count: int = 0
    success_count: int = 0
    last_health_check: Optional[datetime] = None
    status: HealthCheckStatus = HealthCheckStatus.UNKNOWN
    location: Optional[str] = None  # for geographic routing

@dataclass
class LoadBalancingMetrics:
    """Load balancing performance metrics"""
    timestamp: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    active_connections: int
    average_response_time: float
    requests_per_second: float
    server_utilization: Dict[str, float]
    algorithm: str
    status: str

@dataclass
class RoutingRule:
    """Traffic routing rule"""
    rule_id: str
    name: str
    strategy: RoutingStrategy
    condition: Dict[str, Any]  # rule condition
    target_servers: List[str]  # server IDs this rule applies to
    priority: int
    enabled: bool = True

class HealthChecker:
    """Backend server health monitoring"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.check_interval = config.get('check_interval', 30)  # seconds
        self.timeout = config.get('timeout', 5)
        self.max_failures = config.get('max_failures', 3)
        self.success_threshold = config.get('success_threshold', 2)
        
        self.health_check_urls = config.get('health_check_urls', {})
        self.is_monitoring = False
        self.monitor_task = None
    
    async def check_server_health(self, server: Server) -> HealthCheckStatus:
        """Check individual server health"""
        try:
            # Get health check URL
            health_url = self.health_check_urls.get(server.server_id)
            if not health_url:
                # Use default health endpoint
                health_url = f"http://{server.host}:{server.port}/health"
            
            # Perform HTTP health check
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(health_url) as response:
                    if response.status == 200:
                        server.success_count += 1
                        server.error_count = max(0, server.error_count - 1)
                        
                        # Check response time
                        start_time = time.time()
                        await response.read()
                        server.response_time_ms = (time.time() - start_time) * 1000
                        
                        return HealthCheckStatus.HEALTHY
                    else:
                        server.error_count += 1
                        return HealthCheckStatus.UNHEALTHY
                        
        except Exception as e:
            self.logger.debug(f"Health check failed for {server.server_id}: {e}")
            server.error_count += 1
            return HealthCheckStatus.UNHEALTHY
    
    async def check_all_servers(self, servers: List[Server]) -> Dict[str, HealthCheckStatus]:
        """Check health of all servers"""
        tasks = [self.check_server_health(server) for server in servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        server_statuses = {}
        for server, result in zip(servers, results):
            if isinstance(result, Exception):
                server_statuses[server.server_id] = HealthCheckStatus.UNHEALTHY
                server.error_count += 1
            else:
                server_statuses[server.server_id] = result
                server.last_health_check = datetime.now()
        
        return server_statuses
    
    async def start_monitoring(self, servers: List[Server]):
        """Start continuous health monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        
        async def monitor_loop():
            while self.is_monitoring:
                try:
                    await self.check_all_servers(servers)
                    await asyncio.sleep(self.check_interval)
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {e}")
                    await asyncio.sleep(self.check_interval)
        
        self.monitor_task = asyncio.create_task(monitor_loop())
        self.logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Health monitoring stopped")

class IntelligentLoadBalancer:
    """Intelligent load balancer with multiple algorithms and strategies"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Load balancing configuration
        self.algorithm = LoadBalancingAlgorithm(config.get('algorithm', 'round_robin'))
        self.sticky_sessions = config.get('sticky_sessions', False)
        self.session_timeout = config.get('session_timeout', 3600)
        
        # Server management
        self.servers = {}
        self.round_robin_index = 0
        self.consistent_hash_ring = {}
        self.hash_replicas = config.get('hash_replicas', 150)  # for consistent hashing
        
        # Session management
        self.sessions = {}  # session_id -> server_id
        self.session_timestamps = {}  # session_id -> last_access_time
        
        # Metrics and monitoring
        self.metrics = []
        self.health_checker = HealthChecker(config.get('health_check', {}))
        
        # Routing rules
        self.routing_rules = []
        self.load_routing_rules(config.get('routing_rules', []))
        
        # Performance tracking
        self.request_counts = defaultdict(int)
        self.connection_counts = defaultdict(int)
        
        # Initialize servers
        self._initialize_servers(config.get('backend_servers', []))
    
    def _initialize_servers(self, server_configs: List[Dict]):
        """Initialize backend servers"""
        for config in server_configs:
            server = Server(
                server_id=config['server_id'],
                host=config['host'],
                port=config['port'],
                weight=config.get('weight', 1),
                max_connections=config.get('max_connections', 1000),
                location=config.get('location')
            )
            self.servers[server.server_id] = server
        
        self.logger.info(f"Initialized {len(self.servers)} backend servers")
    
    def load_routing_rules(self, rules_config: List[Dict]):
        """Load traffic routing rules"""
        for rule_config in rules_config:
            rule = RoutingRule(
                rule_id=rule_config['rule_id'],
                name=rule_config['name'],
                strategy=RoutingStrategy(rule_config['strategy']),
                condition=rule_config['condition'],
                target_servers=rule_config.get('target_servers', []),
                priority=rule_config.get('priority', 0),
                enabled=rule_config.get('enabled', True)
            )
            self.routing_rules.append(rule)
        
        # Sort by priority
        self.routing_rules.sort(key=lambda x: x.priority, reverse=True)
    
    def _select_server(self, client_info: Dict[str, Any] = None) -> Optional[Server]:
        """Select server based on load balancing algorithm"""
        available_servers = [
            server for server in self.servers.values()
            if server.status == HealthCheckStatus.HEALTHY
        ]
        
        if not available_servers:
            self.logger.warning("No healthy servers available")
            return None
        
        # Apply routing rules first
        if client_info and self.routing_rules:
            server = self._apply_routing_rules(client_info, available_servers)
            if server:
                return server
        
        # Apply load balancing algorithm
        if self.algorithm == LoadBalancingAlgorithm.ROUND_ROBIN:
            return self._round_robin_select(available_servers)
        elif self.algorithm == LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(available_servers)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
            return self._least_connections_select(available_servers)
        elif self.algorithm == LoadBalancingAlgorithm.LEAST_RESPONSE_TIME:
            return self._least_response_time_select(available_servers)
        elif self.algorithm == LoadBalancingAlgorithm.IP_HASH:
            return self._ip_hash_select(available_servers, client_info)
        elif self.algorithm == LoadBalancingAlgorithm.RANDOM:
            return self._random_select(available_servers)
        elif self.algorithm == LoadBalancingAlgorithm.CONSISTENT_HASH:
            return self._consistent_hash_select(available_servers, client_info)
        elif self.algorithm == LoadBalancingAlgorithm.ADAPTIVE:
            return self._adaptive_select(available_servers, client_info)
        
        # Default fallback
        return random.choice(available_servers)
    
    def _apply_routing_rules(self, client_info: Dict, servers: List[Server]) -> Optional[Server]:
        """Apply traffic routing rules"""
        for rule in self.routing_rules:
            if not rule.enabled:
                continue
            
            if self._evaluate_routing_rule(rule, client_info):
                # Filter servers by rule's target servers
                target_servers = [s for s in servers if s.server_id in rule.target_servers]
                if target_servers:
                    # Apply the appropriate algorithm for this rule
                    return random.choice(target_servers)
        
        return None
    
    def _evaluate_routing_rule(self, rule: RoutingRule, client_info: Dict) -> bool:
        """Evaluate if a routing rule matches client info"""
        condition = rule.condition
        
        # Geographic routing
        if rule.strategy == RoutingStrategy.GEOGRAPHIC:
            client_country = client_info.get('country')
            return client_country == condition.get('country')
        
        # Content-aware routing
        elif rule.strategy == RoutingStrategy.CONTENT_AWARE:
            content_type = client_info.get('content_type')
            return content_type in condition.get('content_types', [])
        
        # User behavior routing
        elif rule.strategy == RoutingStrategy.USER_BEHAVIOR:
            user_agent = client_info.get('user_agent', '').lower()
            return any(ua in user_agent for ua in condition.get('user_agents', []))
        
        # Load-based routing
        elif rule.strategy == RoutingStrategy.LOAD_BASED:
            avg_load = sum(s.current_connections for s in self.servers.values()) / len(self.servers)
            return avg_load > condition.get('load_threshold', 100)
        
        return False
    
    def _round_robin_select(self, servers: List[Server]) -> Server:
        """Round robin server selection"""
        server = servers[self.round_robin_index % len(servers)]
        self.round_robin_index += 1
        return server
    
    def _weighted_round_robin_select(self, servers: List[Server]) -> Server:
        """Weighted round robin server selection"""
        total_weight = sum(server.weight for server in servers)
        if total_weight == 0:
            return random.choice(servers)
        
        random_weight = random.randint(1, total_weight)
        current_weight = 0
        
        for server in servers:
            current_weight += server.weight
            if random_weight <= current_weight:
                return server
        
        return servers[-1]
    
    def _least_connections_select(self, servers: List[Server]) -> Server:
        """Select server with least connections"""
        return min(servers, key=lambda x: x.current_connections)
    
    def _least_response_time_select(self, servers: List[Server]) -> Server:
        """Select server with least response time"""
        return min(servers, key=lambda x: x.response_time_ms)
    
    def _ip_hash_select(self, servers: List[Server], client_info: Dict) -> Server:
        """IP hash-based server selection"""
        client_ip = client_info.get('ip', '0.0.0.0')
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        return servers[hash_value % len(servers)]
    
    def _random_select(self, servers: List[Server]) -> Server:
        """Random server selection"""
        return random.choice(servers)
    
    def _consistent_hash_select(self, servers: List[Server], client_info: Dict) -> Server:
        """Consistent hash-based server selection"""
        if not self.consistent_hash_ring:
            self._build_consistent_hash_ring(servers)
        
        client_key = client_info.get('session_id') or client_info.get('ip', 'default')
        hash_value = int(hashlib.md5(str(client_key).encode()).hexdigest(), 16)
        
        # Find server in hash ring
        sorted_keys = sorted(self.consistent_hash_ring.keys())
        for key in sorted_keys:
            if hash_value <= key:
                server_id = self.consistent_hash_ring[key]
                return self.servers.get(server_id, servers[0])
        
        # Wrap around
        server_id = self.consistent_hash_ring[sorted_keys[0]]
        return self.servers.get(server_id, servers[0])
    
    def _build_consistent_hash_ring(self, servers: List[Server]):
        """Build consistent hash ring"""
        self.consistent_hash_ring = {}
        
        for server in servers:
            for i in range(self.hash_replicas):
                hash_value = int(hashlib.md5(f"{server.server_id}:{i}".encode()).hexdigest(), 16)
                self.consistent_hash_ring[hash_value] = server.server_id
    
    def _adaptive_select(self, servers: List[Server], client_info: Dict) -> Server:
        """Adaptive server selection based on real-time performance"""
        # Calculate composite scores for each server
        server_scores = []
        
        for server in servers:
            # Normalize metrics (lower is better for response time and connections)
            response_score = 1.0 / (1.0 + server.response_time_ms / 1000.0)  # normalize response time
            connection_score = 1.0 / (1.0 + server.current_connections / server.max_connections)
            success_rate = server.success_count / max(1, server.success_count + server.error_count)
            
            # Weighted composite score
            composite_score = (
                response_score * 0.4 +
                connection_score * 0.3 +
                success_rate * 0.3
            )
            
            server_scores.append((server, composite_score))
        
        # Select server with highest score
        return max(server_scores, key=lambda x: x[1])[0]
    
    async def route_request(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to appropriate server"""
        start_time = time.time()
        
        try:
            # Get or create session
            session_id = request_info.get('session_id')
            if self.sticky_sessions and session_id:
                server = self._get_session_server(session_id)
                if server and server.status == HealthCheckStatus.HEALTHY:
                    return await self._forward_request(server, request_info)
            
            # Select server using load balancing algorithm
            server = self._select_server(request_info)
            if not server:
                return {
                    'error': 'No healthy servers available',
                    'status_code': 503,
                    'response_time_ms': 0
                }
            
            # Update session mapping if sticky sessions enabled
            if self.sticky_sessions and session_id:
                self._set_session_server(session_id, server.server_id)
            
            # Forward request to selected server
            result = await self._forward_request(server, request_info)
            
            # Record metrics
            response_time = (time.time() - start_time) * 1000
            self._record_request_metric(server.server_id, True, response_time)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Request routing failed: {e}")
            response_time = (time.time() - start_time) * 1000
            if 'server' in locals():
                self._record_request_metric(server.server_id, False, response_time)
            
            return {
                'error': str(e),
                'status_code': 500,
                'response_time_ms': response_time
            }
    
    def _get_session_server(self, session_id: str) -> Optional[Server]:
        """Get server for existing session"""
        # Clean up expired sessions
        current_time = time.time()
        expired_sessions = [
            sid for sid, timestamp in self.session_timestamps.items()
            if current_time - timestamp > self.session_timeout
        ]
        for sid in expired_sessions:
            self.sessions.pop(sid, None)
            self.session_timestamps.pop(sid, None)
        
        server_id = self.sessions.get(session_id)
        return self.servers.get(server_id) if server_id else None
    
    def _set_session_server(self, session_id: str, server_id: str):
        """Set server for session"""
        self.sessions[session_id] = server_id
        self.session_timestamps[session_id] = time.time()
    
    async def _forward_request(self, server: Server, request_info: Dict) -> Dict[str, Any]:
        """Forward request to backend server"""
        # Increment connection counter
        server.current_connections += 1
        
        try:
            # Prepare request URL
            target_url = f"http://{server.host}:{server.port}{request_info.get('path', '/')}"
            
            # Prepare headers
            headers = request_info.get('headers', {})
            headers.update({
                'X-Forwarded-For': request_info.get('client_ip', 'unknown'),
                'X-Forwarded-Proto': request_info.get('protocol', 'http'),
                'X-Load-Balancer': 'intelligent-lb'
            })
            
            # Make request
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                method = request_info.get('method', 'GET')
                
                if method.upper() == 'GET':
                    async with session.get(target_url, headers=headers) as response:
                        content = await response.read()
                        return {
                            'status_code': response.status,
                            'headers': dict(response.headers),
                            'content': content,
                            'server_id': server.server_id,
                            'response_time_ms': server.response_time_ms
                        }
                else:
                    data = request_info.get('data')
                    async with session.request(method, target_url, headers=headers, data=data) as response:
                        content = await response.read()
                        return {
                            'status_code': response.status,
                            'headers': dict(response.headers),
                            'content': content,
                            'server_id': server.server_id,
                            'response_time_ms': server.response_time_ms
                        }
        
        finally:
            # Decrement connection counter
            server.current_connections = max(0, server.current_connections - 1)
    
    def _record_request_metric(self, server_id: str, success: bool, response_time: float):
        """Record request metrics"""
        self.request_counts[server_id] += 1
        if not success:
            self.servers[server_id].error_count += 1
        else:
            self.servers[server_id].success_count += 1
    
    async def start_health_monitoring(self):
        """Start backend server health monitoring"""
        servers_list = list(self.servers.values())
        await self.health_checker.start_monitoring(servers_list)
    
    async def stop_health_monitoring(self):
        """Stop backend server health monitoring"""
        await self.health_checker.stop_monitoring()
    
    def get_load_balancing_metrics(self) -> LoadBalancingMetrics:
        """Get current load balancing metrics"""
        total_requests = sum(self.request_counts.values())
        total_connections = sum(s.current_connections for s in self.servers.values())
        avg_response_time = sum(s.response_time_ms for s in self.servers.values()) / len(self.servers)
        
        # Calculate server utilization
        server_utilization = {}
        for server in self.servers.values():
            utilization = (server.current_connections / server.max_connections) * 100
            server_utilization[server.server_id] = utilization
        
        # Calculate requests per second (simplified)
        rps = total_requests / max(1, len(self.metrics))
        
        return LoadBalancingMetrics(
            timestamp=datetime.now(),
            total_requests=total_requests,
            successful_requests=sum(s.success_count for s in self.servers.values()),
            failed_requests=sum(s.error_count for s in self.servers.values()),
            active_connections=total_connections,
            average_response_time=avg_response_time,
            requests_per_second=rps,
            server_utilization=server_utilization,
            algorithm=self.algorithm.value,
            status='active'
        )
    
    def export_configuration(self, filepath: str):
        """Export load balancer configuration"""
        config = {
            'algorithm': self.algorithm.value,
            'sticky_sessions': self.sticky_sessions,
            'servers': [asdict(server) for server in self.servers.values()],
            'routing_rules': [asdict(rule) for rule in self.routing_rules],
            'metrics': [asdict(metric) for metric in self.metrics[-100:]],  # Last 100 metrics
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        self.logger.info(f"Load balancer configuration exported to {filepath}")

def create_sample_lb_config() -> Dict:
    """Create sample load balancer configuration"""
    return {
        'algorithm': 'adaptive',
        'sticky_sessions': True,
        'session_timeout': 3600,
        'hash_replicas': 150,
        'backend_servers': [
            {
                'server_id': 'web-1',
                'host': '192.168.1.10',
                'port': 8080,
                'weight': 1,
                'max_connections': 1000,
                'location': 'us-east-1'
            },
            {
                'server_id': 'web-2',
                'host': '192.168.1.11',
                'port': 8080,
                'weight': 1,
                'max_connections': 1000,
                'location': 'us-west-1'
            },
            {
                'server_id': 'api-1',
                'host': '192.168.1.20',
                'port': 8081,
                'weight': 2,
                'max_connections': 500,
                'location': 'us-central-1'
            }
        ],
        'health_check': {
            'check_interval': 30,
            'timeout': 5,
            'max_failures': 3,
            'success_threshold': 2,
            'health_check_urls': {
                'web-1': 'http://192.168.1.10:8080/health',
                'web-2': 'http://192.168.1.11:8080/health',
                'api-1': 'http://192.168.1.20:8081/health'
            }
        },
        'routing_rules': [
            {
                'rule_id': 'mobile_traffic',
                'name': 'Route mobile traffic',
                'strategy': 'user_behavior',
                'condition': {'user_agents': ['mobile', 'iphone', 'android']},
                'target_servers': ['web-1'],
                'priority': 10,
                'enabled': True
            },
            {
                'rule_id': 'api_traffic',
                'name': 'Route API traffic',
                'strategy': 'content_aware',
                'condition': {'content_types': ['application/json', 'application/xml']},
                'target_servers': ['api-1'],
                'priority': 5,
                'enabled': True
            }
        ]
    }

def main():
    """Example usage and testing"""
    async def demo_load_balancer():
        # Create sample configuration
        config = create_sample_lb_config()
        
        # Initialize load balancer
        load_balancer = IntelligentLoadBalancer(config)
        
        print("Intelligent Load Balancer Demo")
        print("=" * 50)
        
        # Start health monitoring
        await load_balancer.start_health_monitoring()
        
        # Test request routing
        test_requests = [
            {
                'method': 'GET',
                'path': '/api/users',
                'headers': {'User-Agent': 'Mozilla/5.0 (iPhone'},
                'client_ip': '192.168.1.100',
                'session_id': 'session_123'
            },
            {
                'method': 'GET',
                'path': '/api/stats',
                'headers': {'Content-Type': 'application/json'},
                'client_ip': '192.168.1.101',
                'session_id': 'session_456'
            },
            {
                'method': 'GET',
                'path': '/web/home',
                'headers': {'User-Agent': 'Mozilla/5.0 (Windows'},
                'client_ip': '192.168.1.102'
            }
        ]
        
        print("Testing request routing...")
        
        for i, request in enumerate(test_requests):
            try:
                print(f"\nRequest {i+1}: {request['method']} {request['path']}")
                
                result = await load_balancer.route_request(request)
                
                print(f"  Status Code: {result.get('status_code', 'N/A')}")
                print(f"  Server: {result.get('server_id', 'N/A')}")
                print(f"  Response Time: {result.get('response_time_ms', 0):.1f}ms")
                
                if 'error' in result:
                    print(f"  Error: {result['error']}")
                    
            except Exception as e:
                print(f"  Request failed: {e}")
        
        # Get metrics
        print("\nLoad Balancer Metrics:")
        metrics = load_balancer.get_load_balancing_metrics()
        print(f"  Total Requests: {metrics.total_requests}")
        print(f"  Active Connections: {metrics.active_connections}")
        print(f"  Average Response Time: {metrics.average_response_time:.1f}ms")
        print(f"  Algorithm: {metrics.algorithm}")
        
        # Export configuration
        load_balancer.export_configuration('/tmp/load_balancer_config.json')
        print(f"\nConfiguration exported")
        
        # Stop health monitoring
        await load_balancer.stop_health_monitoring()
    
    # Run the demo
    asyncio.run(demo_load_balancer())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()