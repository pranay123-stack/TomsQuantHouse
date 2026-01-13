"""
Configuration example for the Agent Communication System.
This file demonstrates how to configure all system components.
"""

from typing import Dict, Any
from dataclasses import dataclass
import asyncio
from datetime import timedelta

# Configuration classes
@dataclass
class SystemConfig:
    """Main system configuration"""
    system_id: str = "production_system"
    log_level: str = "INFO"
    storage_path: str = "./storage/production"
    enable_security: bool = True
    enable_monitoring: bool = True
    enable_persistence: bool = True


@dataclass
class MessageRouterConfig:
    """Message router configuration"""
    routing_strategies: list[str] = None
    load_balancer: str = "weighted_round_robin"
    delivery_guarantees: list[str] = None
    max_retries: int = 3
    retry_delay: float = 1.0
    queue_sizes: Dict[str, int] = None
    enable_priority_queuing: bool = True
    enable_load_balancing: bool = True
    
    def __post_init__(self):
        if self.routing_strategies is None:
            self.routing_strategies = ["round_robin", "least_connections", "priority_based"]
        if self.delivery_guarantees is None:
            self.delivery_guarantees = ["best_effort", "at_least_once", "exactly_once"]
        if self.queue_sizes is None:
            self.queue_sizes = {
                "high_priority": 10000,
                "normal_priority": 50000,
                "low_priority": 20000
            }


@dataclass
class AgentRegistryConfig:
    """Agent registry and discovery configuration"""
    heartbeat_interval: int = 30
    cleanup_timeout: int = 300
    discovery_timeout: int = 30
    max_agents_per_region: int = 1000
    enable_health_monitoring: bool = True
    enable_auto_cleanup: bool = True
    registry_backend: str = "memory"  # memory, redis, database


@dataclass
class MessagePersistenceConfig:
    """Message persistence configuration"""
    storage_backend: str = "sqlite"  # sqlite, redis, file
    compression: bool = True
    encryption_at_rest: bool = True
    retention_policy: str = "time_based"  # time_based, size_based, hybrid
    max_size_mb: int = 1024
    max_age_days: int = 30
    cleanup_batch_size: int = 1000
    enable_replay: bool = True
    replay_timeout: int = 3600


@dataclass
class MonitoringConfig:
    """Monitoring and analytics configuration"""
    metrics_enabled: bool = True
    alerting_enabled: bool = True
    metrics_retention_days: int = 30
    alert_evaluation_interval: int = 60
    performance_sampling_rate: float = 0.1
    enable_anomaly_detection: bool = True
    dashboard_update_interval: int = 30
    prometheus_port: int = 8090


@dataclass
class SecurityConfig:
    """Security and encryption configuration"""
    encryption_required: bool = True
    signature_required: bool = True
    default_security_level: str = "standard"  # none, basic, standard, high, critical
    encryption_algorithms: list[str] = None
    signature_algorithms: list[str] = None
    key_rotation_days: int = 30
    max_key_usage: int = 10000
    enable_security_audit: bool = True
    
    def __post_init__(self):
        if self.encryption_algorithms is None:
            self.encryption_algorithms = ["AES_256", "RSA_2048"]
        if self.signature_algorithms is None:
            self.signature_algorithms = ["HMAC_SHA256", "RSA_PSS_SHA256"]


@dataclass
class EventSystemConfig:
    """Event system configuration"""
    event_bus_backend: str = "memory"  # memory, redis, kafka
    event_retention_days: int = 7
    enable_coordination: bool = True
    enable_workflows: bool = True
    max_concurrent_coordinations: int = 100
    coordination_timeout: int = 300
    workflow_timeout: int = 3600


@dataclass
class TransportConfig:
    """Transport layer configuration"""
    primary_transport: str = "redis"  # redis, tcp, http, websocket
    backup_transports: list[str] = None
    redis_config: Dict[str, Any] = None
    tcp_config: Dict[str, Any] = None
    http_config: Dict[str, Any] = None
    enable_reconnection: bool = True
    connection_timeout: int = 30
    max_connections: int = 1000
    
    def __post_init__(self):
        if self.backup_transports is None:
            self.backup_transports = ["tcp"]
        if self.redis_config is None:
            self.redis_config = {
                "host": "localhost",
                "port": 6379,
                "password": "trading_framework_2025",
                "db": 0,
                "decode_responses": True
            }
        if self.tcp_config is None:
            self.tcp_config = {
                "host": "0.0.0.0",
                "port": 8000,
                "max_connections": 1000,
                "keepalive": True
            }
        if self.http_config is None:
            self.http_config = {
                "host": "0.0.0.0",
                "port": 8080,
                "enable_cors": True,
                "enable_swagger": True
            }


# Production configuration
PRODUCTION_CONFIG = {
    "system": SystemConfig(
        system_id="production_trading_system",
        log_level="INFO",
        storage_path="/var/lib/agent-communication/storage",
        enable_security=True,
        enable_monitoring=True,
        enable_persistence=True
    ),
    "message_router": MessageRouterConfig(
        routing_strategies=["priority_based", "least_connections", "weighted_round_robin"],
        load_balancer="weighted_round_robin",
        delivery_guarantees=["best_effort", "at_least_once"],
        max_retries=3,
        retry_delay=2.0,
        queue_sizes={
            "critical": 5000,
            "high_priority": 10000,
            "normal_priority": 50000,
            "low_priority": 20000
        }
    ),
    "agent_registry": AgentRegistryConfig(
        heartbeat_interval=30,
        cleanup_timeout=300,
        discovery_timeout=30,
        max_agents_per_region=500,
        enable_health_monitoring=True,
        enable_auto_cleanup=True,
        registry_backend="redis"
    ),
    "message_persistence": MessagePersistenceConfig(
        storage_backend="sqlite",
        compression=True,
        encryption_at_rest=True,
        retention_policy="hybrid",
        max_size_mb=10240,  # 10GB
        max_age_days=90,
        cleanup_batch_size=1000,
        enable_replay=True,
        replay_timeout=7200
    ),
    "monitoring": MonitoringConfig(
        metrics_enabled=True,
        alerting_enabled=True,
        metrics_retention_days=30,
        alert_evaluation_interval=60,
        performance_sampling_rate=0.1,
        enable_anomaly_detection=True,
        dashboard_update_interval=30,
        prometheus_port=8090
    ),
    "security": SecurityConfig(
        encryption_required=True,
        signature_required=True,
        default_security_level="high",
        encryption_algorithms=["AES_256_GCM", "RSA_2048"],
        signature_algorithms=["RSA_PSS_SHA256", "HMAC_SHA256"],
        key_rotation_days=30,
        max_key_usage=50000,
        enable_security_audit=True
    ),
    "event_system": EventSystemConfig(
        event_bus_backend="redis",
        event_retention_days=14,
        enable_coordination=True,
        enable_workflows=True,
        max_concurrent_coordinations=200,
        coordination_timeout=600,
        workflow_timeout=7200
    ),
    "transport": TransportConfig(
        primary_transport="redis",
        backup_transports=["tcp", "websocket"],
        enable_reconnection=True,
        connection_timeout=30,
        max_connections=2000
    )
}

# Development configuration
DEVELOPMENT_CONFIG = {
    "system": SystemConfig(
        system_id="dev_test_system",
        log_level="DEBUG",
        storage_path="./storage/dev",
        enable_security=True,
        enable_monitoring=True,
        enable_persistence=True
    ),
    "message_router": MessageRouterConfig(
        routing_strategies=["round_robin"],
        delivery_guarantees=["best_effort"],
        max_retries=2,
        queue_sizes={
            "high_priority": 1000,
            "normal_priority": 5000,
            "low_priority": 2000
        }
    ),
    "agent_registry": AgentRegistryConfig(
        heartbeat_interval=60,
        cleanup_timeout=600,
        discovery_timeout=60,
        max_agents_per_region=100
    ),
    "message_persistence": MessagePersistenceConfig(
        storage_backend="sqlite",
        compression=False,
        encryption_at_rest=False,
        max_size_mb=1024,
        max_age_days=7
    ),
    "monitoring": MonitoringConfig(
        metrics_enabled=True,
        alerting_enabled=False,
        metrics_retention_days=7,
        enable_anomaly_detection=False
    ),
    "security": SecurityConfig(
        encryption_required=True,
        signature_required=False,
        default_security_level="basic"
    ),
    "event_system": EventSystemConfig(
        event_bus_backend="memory",
        event_retention_days=3,
        enable_coordination=True,
        enable_workflows=False
    ),
    "transport": TransportConfig(
        primary_transport="tcp",
        backup_transports=[]
    )
}

# Testing configuration
TESTING_CONFIG = {
    "system": SystemConfig(
        system_id="test_system",
        log_level="ERROR",  # Reduce noise in tests
        storage_path=":memory:",  # In-memory for tests
        enable_security=False,
        enable_monitoring=False,
        enable_persistence=False
    ),
    "message_router": MessageRouterConfig(
        routing_strategies=["round_robin"],
        delivery_guarantees=["best_effort"],
        max_retries=1,
        queue_sizes={"high_priority": 100, "normal_priority": 500}
    ),
    "agent_registry": AgentRegistryConfig(
        heartbeat_interval=300,  # Longer intervals for tests
        cleanup_timeout=3600,
        discovery_timeout=10
    ),
    "message_persistence": MessagePersistenceConfig(
        storage_backend="memory",
        compression=False,
        encryption_at_rest=False,
        retention_policy="time_based",
        max_size_mb=10,
        max_age_days=1
    ),
    "monitoring": MonitoringConfig(
        metrics_enabled=False,
        alerting_enabled=False,
        enable_anomaly_detection=False
    ),
    "security": SecurityConfig(
        encryption_required=False,
        signature_required=False,
        default_security_level="none"
    ),
    "event_system": EventSystemConfig(
        event_bus_backend="memory",
        enable_coordination=False,
        enable_workflows=False
    ),
    "transport": TransportConfig(
        primary_transport="memory",
        backup_transports=[]
    )
}


def get_config(environment: str = "development") -> Dict[str, Any]:
    """Get configuration for specified environment"""
    configs = {
        "production": PRODUCTION_CONFIG,
        "development": DEVELOPMENT_CONFIG,
        "testing": TESTING_CONFIG
    }
    
    if environment not in configs:
        raise ValueError(f"Unknown environment: {environment}")
    
    return configs[environment]


def create_custom_config(**overrides) -> Dict[str, Any]:
    """Create custom configuration by overriding default values"""
    config = DEVELOPMENT_CONFIG.copy()
    
    # Deep merge overrides
    def deep_merge(base: Dict, override: Dict):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                deep_merge(base[key], value)
            else:
                base[key] = value
    
    deep_merge(config, overrides)
    return config


# Example usage
if __name__ == "__main__":
    import json
    
    # Print production configuration
    print("Production Configuration:")
    print(json.dumps(PRODUCTION_CONFIG, indent=2, default=str))
    
    print("\n" + "="*50 + "\n")
    
    # Print development configuration
    print("Development Configuration:")
    print(json.dumps(DEVELOPMENT_CONFIG, indent=2, default=str))
    
    print("\n" + "="*50 + "\n")
    
    # Example of custom configuration
    custom_config = create_custom_config(
        system={"system_id": "my_custom_system"},
        security={"encryption_required": True, "signature_required": True},
        monitoring={"alerting_enabled": True}
    )
    
    print("Custom Configuration:")
    print(json.dumps(custom_config, indent=2, default=str))