"""
Comprehensive Test Configuration for End-to-End Testing System
"""
import os
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ServiceConfig:
    """Configuration for each service in the pipeline"""
    name: str
    base_url: str
    api_key: str
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    enabled: bool = True

@dataclass
class PerformanceThresholds:
    """Performance thresholds for system validation"""
    # API Response Times (seconds)
    max_api_response_time: float = 2.0
    max_prediction_time: float = 5.0
    max_data_flow_time: float = 1.0
    max_cache_retrieval_time: float = 0.1
    
    # System Metrics
    max_memory_usage_mb: int = 2048
    max_cpu_usage_percent: int = 80
    min_cache_hit_ratio: float = 0.85
    max_error_rate: float = 0.01
    
    # Load Testing
    max_concurrent_requests: int = 100
    target_throughput_rps: float = 1000.0
    max_response_time_p95: float = 5.0
    max_response_time_p99: float = 10.0

@dataclass
class TestData:
    """Test data configuration"""
    symbols: List[str]
    date_range: Dict[str, str]
    risk_tolerance: str = "medium"
    investment_amount: float = 100000.0
    portfolio_size: int = 10

class TestConfig:
    """Master configuration for all tests"""
    
    # Environment
    ENVIRONMENT = os.getenv('TEST_ENVIRONMENT', 'staging')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Service Configurations
    REDIS_CONFIG = ServiceConfig(
        name="Redis",
        base_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        api_key="",
        timeout=10.0,
        max_retries=3
    )
    
    LETTA_CONFIG = ServiceConfig(
        name="Letta",
        base_url=os.getenv('LETTA_BASE_URL', 'http://localhost:8283'),
        api_key=os.getenv('LETTA_API_KEY', 'test-key'),
        timeout=60.0,
        max_retries=3
    )
    
    ABACUS_CONFIG = ServiceConfig(
        name="Abacus.AI",
        base_url=os.getenv('ABACUS_API_URL', 'https://api.abacus.ai'),
        api_key=os.getenv('ABACUS_API_KEY', 'test-abacus-key'),
        timeout=120.0,
        max_retries=5
    )
    
    QUANTCONNECT_CONFIG = ServiceConfig(
        name="QuantConnect",
        base_url=os.getenv('QUANTCONNECT_BASE_URL', 'https://www.quantconnect.com/api'),
        api_key=os.getenv('QUANTCONNECT_API_KEY', 'test-qc-key'),
        timeout=30.0,
        max_retries=3
    )
    
    LEAN_CONFIG = ServiceConfig(
        name="LEAN",
        base_url=os.getenv('LEAN_BASE_URL', 'http://localhost:8080'),
        api_key=os.getenv('LEAN_API_KEY', 'test-lean-key'),
        timeout=30.0,
        max_retries=3
    )
    
    ABACUS_AI_CONFIG = ServiceConfig(
        name="Abacus.AI ML Platform",
        base_url=os.getenv('ABACUS_AI_API_URL', 'https://ml.abacus.ai'),
        api_key=os.getenv('ABACUS_AI_API_KEY', 'test-ml-key'),
        timeout=180.0,
        max_retries=5
    )
    
    # Test Data
    TEST_DATA = TestData(
        symbols=[
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", 
            "META", "NFLX", "NVDA", "CRM", "AMD",
            "JPM", "JNJ", "V", "PG", "UNH",
            "HD", "MA", "BAC", "ADBE", "CMCSA"
        ],
        date_range={
            "start": "2024-01-01",
            "end": "2024-12-01",
            "granularity": "1d"
        },
        risk_tolerance="medium",
        investment_amount=1000000.0,
        portfolio_size=10
    )
    
    # Performance Thresholds
    PERFORMANCE_THRESHOLDS = PerformanceThresholds()
    
    # Cache Settings
    CACHE_CONFIG = {
        "prediction_ttl": 300,  # 5 minutes
        "feature_ttl": 1800,    # 30 minutes
        "market_data_ttl": 300, # 5 minutes
        "model_ttl": 3600,      # 1 hour
        "portfolio_ttl": 600    # 10 minutes
    }
    
    # Security Testing
    SECURITY_CONFIG = {
        "rate_limit_threshold": 1000,
        "auth_timeout": 30,
        "max_failed_attempts": 5,
        "sql_injection_payloads": [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin'--",
            "1' UNION SELECT NULL,NULL--"
        ],
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ]
    }
    
    # Load Testing Configuration
    LOAD_TEST_CONFIG = {
        "warmup_duration": 30,
        "ramp_up_duration": 60,
        "sustained_duration": 300,
        "ramp_down_duration": 30,
        "concurrent_users": [10, 50, 100, 200, 500],
        "ramp_up_rps": [10, 50, 100, 200, 500]
    }
    
    # Disaster Recovery
    DISASTER_RECOVERY_CONFIG = {
        "backup_frequency": "daily",
        "retention_period_days": 30,
        "rto_minutes": 60,  # Recovery Time Objective
        "rpo_minutes": 15,  # Recovery Point Objective
        "failure_scenarios": [
            "service_down",
            "database_corruption",
            "cache_failure",
            "network_partition",
            "memory_exhaustion",
            "disk_full"
        ]
    }
    
    # CI/CD Configuration
    CI_CD_CONFIG = {
        "github_actions": {
            "python_versions": ["3.8", "3.9", "3.10", "3.11"],
            "test_types": ["unit", "integration", "e2e", "performance"],
            "coverage_threshold": 80
        },
        "jenkins": {
            "build_timeout": 3600,
            "parallel_execution": True,
            "artifact_retention_days": 30
        }
    }
    
    @classmethod
    def get_all_services(cls) -> Dict[str, ServiceConfig]:
        """Get all service configurations"""
        return {
            "redis": cls.REDIS_CONFIG,
            "letta": cls.LETTA_CONFIG,
            "abacus": cls.ABACUS_CONFIG,
            "quantconnect": cls.QUANTCONNECT_CONFIG,
            "lean": cls.LEAN_CONFIG,
            "abacus_ai": cls.ABACUS_AI_CONFIG
        }
    
    @classmethod
    def get_required_env_vars(cls) -> List[str]:
        """Get list of required environment variables"""
        return [
            "REDIS_URL",
            "LETTA_API_KEY", 
            "ABACUS_API_KEY",
            "QUANTCONNECT_API_KEY",
            "LEAN_API_KEY",
            "ABACUS_AI_API_KEY"
        ]
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration"""
        required_vars = cls.get_required_env_vars()
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        logger.info("Configuration validation successful")
        return True

# Test Markers
TEST_MARKERS = {
    "integration": "Integration tests between services",
    "e2e": "End-to-end pipeline tests", 
    "performance": "Performance benchmarking tests",
    "load": "Load and stress testing",
    "security": "Security and vulnerability tests",
    "disaster_recovery": "DR and backup tests",
    "agent": "Agent coordination tests",
    "api": "API endpoint tests",
    "slow": "Tests taking longer than 5 seconds",
    "live": "Tests using real services",
    "mock": "Tests using mocks/fixtures",
    "ci": "CI/CD pipeline tests"
}

# Pipeline Flow Configuration
PIPELINE_FLOW = {
    "market_data": {
        "source": "quantconnect",
        "processing": "abacus_ai",
        "cache": "redis",
        "validation": True
    },
    "features": {
        "source": "market_data",
        "processing": "abacus_ai", 
        "cache": "redis",
        "validation": True
    },
    "predictions": {
        "source": "features",
        "processing": "abacus_ai",
        "cache": "redis",
        "validation": True
    },
    "redis": {
        "persistence": True,
        "clustering": False,
        "backup": True
    },
    "lean": {
        "source": "predictions",
        "execution": True,
        "backtest": True
    },
    "trading": {
        "source": "lean",
        "execution": True,
        "validation": True
    },
    "agents": {
        "coordination": True,
        "decision_making": True,
        "monitoring": True
    }
}

# Test Scenarios
TEST_SCENARIOS = {
    "happy_path": {
        "description": "Normal flow with all services healthy",
        "services_healthy": True,
        "data_available": True,
        "load": "normal"
    },
    "partial_failure": {
        "description": "Some services down but system continues",
        "services_healthy": False,
        "failed_services": ["abacus_ai"],
        "data_available": True,
        "load": "normal"
    },
    "high_load": {
        "description": "System under high load",
        "services_healthy": True,
        "data_available": True,
        "load": "high"
    },
    "data_corruption": {
        "description": "Data corruption scenarios",
        "services_healthy": True,
        "data_available": False,
        "corrupted_data": True
    },
    "network_partition": {
        "description": "Network partition between services",
        "services_healthy": True,
        "network_partition": True,
        "data_available": True
    }
}