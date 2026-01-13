"""
Configuration Examples for Error Handling System

This file demonstrates various configuration patterns for different use cases
and deployment environments.
"""
from typing import Dict, Any
from error_handling import (
    RetryConfig, CircuitBreakerConfig, HealthCheckConfig,
    AlertRule, DegradationRule, FailureMode, AlertSeverity,
    DegradationLevel, ServiceTier
)


# Development Environment Configuration
DEVELOPMENT_CONFIG = {
    'health_checks': {
        'checks': [
            {
                'name': 'local_database',
                'type': 'database',
                'config': {
                    'interval': 30,
                    'critical': True,
                    'failure_threshold': 5,
                    'recovery_threshold': 2
                }
            }
        ]
    },
    'circuit_breakers': {
        'services': [
            {
                'name': 'local_service',
                'config': {
                    'failure_threshold': 10,
                    'timeout': 30.0,
                    'success_threshold': 3,
                    'failure_mode': 'count_based'
                }
            }
        ]
    },
    'alerts': {
        'rules': [
            {
                'name': 'development_errors',
                'condition': 'error_rate > 1',
                'severity': 'warning',
                'description': 'Development environment has errors',
                'notification_channels': ['console'],
                'evaluation_interval': 60
            }
        ]
    },
    'degradation': {
        'services': [
            {
                'name': 'dev_features',
                'tier': 'luxury',
                'description': 'Development features'
            }
        ],
        'rules': [
            {
                'condition': 'error_rate > 2',
                'target_level': 'limited_features',
                'timeout_minutes': 10
            }
        ]
    }
}


# Production Environment Configuration
PRODUCTION_CONFIG = {
    'health_checks': {
        'checks': [
            {
                'name': 'primary_database',
                'type': 'database',
                'config': {
                    'interval': 30,
                    'critical': True,
                    'failure_threshold': 3,
                    'recovery_threshold': 2,
                    'timeout': 10.0
                },
                'recovery_actions': [
                    {
                        'type': 'restart_service',
                        'service_name': 'database_connection_pool'
                    }
                ]
            },
            {
                'name': 'redis_cache',
                'type': 'http',
                'url': 'http://redis:6379/health',
                'config': {
                    'interval': 60,
                    'critical': True,
                    'failure_threshold': 2,
                    'timeout': 5.0
                },
                'recovery_actions': [
                    {
                        'type': 'clear_cache',
                        'cache_name': 'application_cache'
                    }
                ]
            },
            {
                'name': 'external_payment_gateway',
                'type': 'http',
                'url': 'https://api.stripe.com/health',
                'config': {
                    'interval': 120,
                    'critical': False,
                    'failure_threshold': 3,
                    'timeout': 15.0
                }
            },
            {
                'name': 'system_resources',
                'type': 'resource',
                'config': {
                    'interval': 60,
                    'critical': True,
                    'memory_threshold': 0.85,
                    'disk_threshold': 0.90,
                    'cpu_threshold': 0.80
                }
            },
            {
                'name': 'message_queue',
                'type': 'http',
                'url': 'http://rabbitmq:15672/api/health',
                'config': {
                    'interval': 60,
                    'critical': True,
                    'failure_threshold': 3
                }
            }
        ]
    },
    'circuit_breakers': {
        'services': [
            {
                'name': 'payment_gateway',
                'config': {
                    'failure_threshold': 3,
                    'timeout': 30.0,
                    'success_threshold': 2,
                    'failure_mode': 'count_based',
                    'slow_call_duration_threshold': 5.0,
                    'slow_call_rate_threshold': 50.0
                }
            },
            {
                'name': 'email_service',
                'config': {
                    'failure_threshold': 5,
                    'timeout': 60.0,
                    'success_threshold': 3,
                    'failure_mode': 'percentage_based',
                    'window_size': 100,
                    'failure_percentage_threshold': 80.0
                }
            },
            {
                'name': 'analytics_service',
                'config': {
                    'failure_threshold': 10,
                    'timeout': 120.0,
                    'success_threshold': 5,
                    'failure_mode': 'percentage_based',
                    'window_size': 50,
                    'failure_percentage_threshold': 90.0
                }
            },
            {
                'name': 'user_auth_service',
                'config': {
                    'failure_threshold': 2,
                    'timeout': 15.0,
                    'success_threshold': 1,
                    'failure_mode': 'count_based'
                }
            }
        ]
    },
    'degradation': {
        'services': [
            {
                'name': 'payment_processing',
                'tier': 'critical',
                'description': 'Core payment processing - must be always available',
                'dependencies': ['database', 'message_queue']
            },
            {
                'name': 'user_authentication',
                'tier': 'critical',
                'description': 'User login and authentication',
                'dependencies': ['database']
            },
            {
                'name': 'order_management',
                'tier': 'important',
                'description': 'Order processing and fulfillment',
                'dependencies': ['database', 'payment_processing']
            },
            {
                'name': 'inventory_management',
                'tier': 'important',
                'description': 'Product inventory tracking',
                'dependencies': ['database']
            },
            {
                'name': 'email_notifications',
                'tier': 'enhanced',
                'description': 'Order confirmations and marketing emails',
                'dependencies': ['email_service']
            },
            {
                'name': 'analytics_dashboard',
                'tier': 'luxury',
                'description': 'Business intelligence and reporting',
                'dependencies': ['analytics_service', 'database']
            },
            {
                'name': 'personalization_engine',
                'tier': 'luxury',
                'description': 'Product recommendations and personalization',
                'dependencies': ['analytics_service']
            },
            {
                'name': 'social_features',
                'tier': 'luxury',
                'description': 'Social sharing and community features',
                'dependencies': ['analytics_service']
            }
        ],
        'rules': [
            {
                'condition': 'error_rate > 5',
                'target_level': 'limited_features',
                'services_to_disable': [
                    'analytics_dashboard',
                    'personalization_engine',
                    'social_features'
                ],
                'capacity_reduction': 0.0,
                'timeout_minutes': 15
            },
            {
                'condition': 'error_rate > 10',
                'target_level': 'limited_features',
                'services_to_disable': [
                    'analytics_dashboard',
                    'personalization_engine',
                    'social_features',
                    'email_notifications'
                ],
                'capacity_reduction': 0.0,
                'timeout_minutes': 30
            },
            {
                'condition': 'overall_health_status == "unhealthy"',
                'target_level': 'essential_only',
                'services_to_disable': [
                    'analytics_dashboard',
                    'personalization_engine',
                    'social_features',
                    'email_notifications',
                    'inventory_management',
                    'order_management'
                ],
                'capacity_reduction': 0.3,
                'timeout_minutes': 60
            },
            {
                'condition': 'total_errors > 100 and recent_error_count > 20',
                'target_level': 'emergency_mode',
                'services_to_disable': [
                    'analytics_dashboard',
                    'personalization_engine',
                    'social_features',
                    'email_notifications',
                    'inventory_management',
                    'order_management',
                    'user_authentication'
                ],
                'capacity_reduction': 0.5,
                'timeout_minutes': 120
            }
        ]
    },
    'alerts': {
        'rules': [
            {
                'name': 'critical_error_rate',
                'condition': 'error_rate > 20',
                'severity': 'critical',
                'description': 'Critical error rate - exceeding 20 errors per minute',
                'notification_channels': ['console', 'log', 'email'],
                'evaluation_interval': 30,
                'cooldown_period': 300
            },
            {
                'name': 'high_error_rate',
                'condition': 'error_rate > 10',
                'severity': 'error',
                'description': 'High error rate - exceeding 10 errors per minute',
                'notification_channels': ['console', 'log'],
                'evaluation_interval': 60,
                'cooldown_period': 600
            },
            {
                'name': 'service_unavailable',
                'condition': 'overall_health_status == "unhealthy"',
                'severity': 'critical',
                'description': 'Service health is critical - immediate attention required',
                'notification_channels': ['console', 'log', 'email', 'slack'],
                'evaluation_interval': 30,
                'cooldown_period': 180
            },
            {
                'name': 'database_connectivity_issues',
                'condition': 'errors_by_category.get("database", 0) > 5',
                'severity': 'critical',
                'description': 'Multiple database connectivity issues detected',
                'notification_channels': ['console', 'log', 'email'],
                'evaluation_interval': 60,
                'cooldown_period': 300
            },
            {
                'name': 'high_memory_usage',
                'condition': 'system_memory_usage > 90',
                'severity': 'warning',
                'description': 'System memory usage is high',
                'notification_channels': ['console', 'log'],
                'evaluation_interval': 120,
                'cooldown_period': 600
            },
            {
                'name': 'circuit_breaker_opened',
                'condition': 'circuit_breaker_failures > 10',
                'severity': 'warning',
                'description': 'Multiple circuit breakers are open - services are failing',
                'notification_channels': ['console', 'log'],
                'evaluation_interval': 90,
                'cooldown_period': 600
            },
            {
                'name': 'degraded_service_mode',
                'condition': 'degradation_level in ["limited_features", "essential_only", "emergency_mode"]',
                'severity': 'warning',
                'description': 'Service is running in degraded mode',
                'notification_channels': ['console', 'log'],
                'evaluation_interval': 180,
                'cooldown_period': 900
            }
        ]
    },
    'fallbacks': {
        'custom_fallbacks': {
            'cache': lambda key: {"data": f"cached_data_for_{key}", "source": "cache"},
            'default_user': lambda: {
                "id": "0",
                "name": "Default User",
                "email": "default@example.com",
                "source": "fallback"
            },
            'empty_response': lambda: {"items": [], "total": 0, "source": "fallback"},
            'queued_payment': lambda amount: {
                "status": "queued",
                "amount": amount,
                "message": "Payment queued for processing",
                "source": "fallback"
            }
        }
    }
}


# Microservices Configuration
MICROSERVICE_CONFIG = {
    'health_checks': {
        'checks': [
            {
                'name': 'service_discovery',
                'type': 'http',
                'url': 'http://consul:8500/v1/health/service/app',
                'config': {
                    'interval': 30,
                    'critical': True,
                    'failure_threshold': 3,
                    'timeout': 10.0
                }
            },
            {
                'name': 'message_broker',
                'type': 'http',
                'url': 'http://rabbitmq:15672/api/overview',
                'config': {
                    'interval': 60,
                    'critical': True,
                    'failure_threshold': 2,
                    'timeout': 5.0
                }
            },
            {
                'name': 'distributed_cache',
                'type': 'http',
                'url': 'http://redis:6379/info',
                'config': {
                    'interval': 30,
                    'critical': False,
                    'failure_threshold': 5,
                    'timeout': 3.0
                }
            }
        ]
    },
    'circuit_breakers': {
        'services': [
            {
                'name': 'upstream_service_a',
                'config': {
                    'failure_threshold': 3,
                    'timeout': 30.0,
                    'success_threshold': 2,
                    'failure_mode': 'percentage_based',
                    'window_size': 50,
                    'failure_percentage_threshold': 75.0
                }
            },
            {
                'name': 'upstream_service_b',
                'config': {
                    'failure_threshold': 5,
                    'timeout': 60.0,
                    'success_threshold': 3,
                    'failure_mode': 'percentage_based',
                    'window_size': 100,
                    'failure_percentage_threshold': 80.0
                }
            }
        ]
    },
    'degradation': {
        'services': [
            {
                'name': 'core_api',
                'tier': 'critical',
                'description': 'Core API functionality',
                'dependencies': ['service_discovery']
            },
            {
                'name': 'data_sync',
                'tier': 'important',
                'description': 'Data synchronization between services',
                'dependencies': ['message_broker', 'distributed_cache']
            },
            {
                'name': 'analytics_export',
                'tier': 'luxury',
                'description': 'Analytics data export functionality',
                'dependencies': ['distributed_cache']
            }
        ],
        'rules': [
            {
                'condition': 'error_rate > 8',
                'target_level': 'limited_features',
                'services_to_disable': ['analytics_export'],
                'timeout_minutes': 20
            },
            {
                'condition': 'overall_health_status == "unhealthy"',
                'target_level': 'essential_only',
                'services_to_disable': ['analytics_export', 'data_sync'],
                'capacity_reduction': 0.4,
                'timeout_minutes': 30
            }
        ]
    },
    'alerts': {
        'rules': [
            {
                'name': 'microservice_unavailable',
                'condition': 'overall_health_status == "unhealthy"',
                'severity': 'critical',
                'description': 'Microservice health is critical',
                'notification_channels': ['console', 'log', 'pagerduty'],
                'evaluation_interval': 30,
                'cooldown_period': 300
            },
            {
                'name': 'service_mesh_issues',
                'condition': 'errors_by_category.get("network", 0) > 10',
                'severity': 'warning',
                'description': 'Network errors detected - possible service mesh issues',
                'notification_channels': ['console', 'log'],
                'evaluation_interval': 60,
                'cooldown_period': 600
            }
        ]
    }
}


# High-Frequency Trading Configuration
HFT_CONFIG = {
    'health_checks': {
        'checks': [
            {
                'name': 'market_data_feed',
                'type': 'custom',
                'config': {
                    'interval': 5,
                    'critical': True,
                    'failure_threshold': 1,
                    'recovery_threshold': 1,
                    'timeout': 2.0
                }
            },
            {
                'name': 'order_execution_engine',
                'type': 'custom',
                'config': {
                    'interval': 10,
                    'critical': True,
                    'failure_threshold': 1,
                    'recovery_threshold': 1,
                    'timeout': 1.0
                }
            },
            {
                'name': 'risk_management_system',
                'type': 'custom',
                'config': {
                    'interval': 15,
                    'critical': True,
                    'failure_threshold': 1,
                    'recovery_threshold': 1,
                    'timeout': 3.0
                }
            },
            {
                'name': 'latency_monitor',
                'type': 'resource',
                'config': {
                    'interval': 30,
                    'critical': True,
                    'memory_threshold': 0.70,
                    'cpu_threshold': 0.70,
                    'disk_threshold': 0.80
                }
            }
        ]
    },
    'circuit_breakers': {
        'services': [
            {
                'name': 'market_data_provider',
                'config': {
                    'failure_threshold': 1,
                    'timeout': 5.0,
                    'success_threshold': 1,
                    'failure_mode': 'count_based'
                }
            },
            {
                'name': 'order_gateway',
                'config': {
                    'failure_threshold': 2,
                    'timeout': 2.0,
                    'success_threshold': 1,
                    'failure_mode': 'count_based'
                }
            },
            {
                'name': 'risk_calculation_engine',
                'config': {
                    'failure_threshold': 1,
                    'timeout': 1.0,
                    'success_threshold': 1,
                    'failure_mode': 'count_based'
                }
            }
        ]
    },
    'degradation': {
        'services': [
            {
                'name': 'trade_execution',
                'tier': 'critical',
                'description': 'Core trade execution - highest priority',
                'dependencies': ['market_data_feed', 'order_execution_engine']
            },
            {
                'name': 'risk_management',
                'tier': 'critical',
                'description': 'Risk management - must be operational',
                'dependencies': ['risk_management_system']
            },
            {
                'name': 'portfolio_optimization',
                'tier': 'important',
                'description': 'Portfolio optimization algorithms',
                'dependencies': ['market_data_feed']
            },
            {
                'name': 'reporting_system',
                'tier': 'luxury',
                'description': 'Real-time reporting and analytics',
                'dependencies': ['market_data_feed', 'trade_execution']
            }
        ],
        'rules': [
            {
                'condition': 'error_rate > 1',
                'target_level': 'limited_features',
                'services_to_disable': ['reporting_system'],
                'timeout_minutes': 5
            },
            {
                'condition': 'error_rate > 2',
                'target_level': 'essential_only',
                'services_to_disable': ['reporting_system', 'portfolio_optimization'],
                'capacity_reduction': 0.1,
                'timeout_minutes': 10
            },
            {
                'condition': 'overall_health_status == "unhealthy"',
                'target_level': 'emergency_mode',
                'services_to_disable': ['reporting_system', 'portfolio_optimization'],
                'capacity_reduction': 0.05,
                'timeout_minutes': 2
            }
        ]
    },
    'alerts': {
        'rules': [
            {
                'name': 'trade_execution_failure',
                'condition': 'errors_by_category.get("trading", 0) > 0',
                'severity': 'critical',
                'description': 'Trade execution failure detected - immediate action required',
                'notification_channels': ['console', 'log', 'phone', 'sms'],
                'evaluation_interval': 10,
                'cooldown_period': 60
            },
            {
                'name': 'high_latency',
                'condition': 'average_latency > 100',
                'severity': 'critical',
                'description': 'High latency detected in trading system',
                'notification_channels': ['console', 'log', 'phone'],
                'evaluation_interval': 30,
                'cooldown_period': 120
            },
            {
                'name': 'risk_system_down',
                'condition': 'errors_by_category.get("risk", 0) > 0',
                'severity': 'critical',
                'description': 'Risk management system failure',
                'notification_channels': ['console', 'log', 'phone', 'sms'],
                'evaluation_interval': 15,
                'cooldown_period': 90
            }
        ]
    }
}


# Batch Processing Configuration
BATCH_CONFIG = {
    'health_checks': {
        'checks': [
            {
                'name': 'data_source',
                'type': 'http',
                'url': 'https://data-warehouse:8080/health',
                'config': {
                    'interval': 300,
                    'critical': True,
                    'failure_threshold': 3,
                    'timeout': 30.0
                }
            },
            {
                'name': 'storage_system',
                'type': 'http',
                'url': 'https://storage:9000/minio/health/live',
                'config': {
                    'interval': 180,
                    'critical': True,
                    'failure_threshold': 2,
                    'timeout': 20.0
                }
            }
        ]
    },
    'circuit_breakers': {
        'services': [
            {
                'name': 'data_warehouse',
                'config': {
                    'failure_threshold': 5,
                    'timeout': 120.0,
                    'success_threshold': 3,
                    'failure_mode': 'percentage_based',
                    'window_size': 20,
                    'failure_percentage_threshold': 80.0
                }
            },
            {
                'name': 'notification_service',
                'config': {
                    'failure_threshold': 10,
                    'timeout': 60.0,
                    'success_threshold': 5,
                    'failure_mode': 'percentage_based',
                    'window_size': 50,
                    'failure_percentage_threshold': 90.0
                }
            }
        ]
    },
    'degradation': {
        'services': [
            {
                'name': 'data_processing',
                'tier': 'critical',
                'description': 'Core data processing pipeline',
                'dependencies': ['data_source', 'storage_system']
            },
            {
                'name': 'data_validation',
                'tier': 'important',
                'description': 'Data quality validation',
                'dependencies': ['data_processing']
            },
            {
                'name': 'report_generation',
                'tier': 'important',
                'description': 'Batch report generation',
                'dependencies': ['data_processing', 'data_validation']
            },
            {
                'name': 'data_archiving',
                'tier': 'luxury',
                'description': 'Historical data archiving',
                'dependencies': ['storage_system']
            }
        ],
        'rules': [
            {
                'condition': 'error_rate > 3',
                'target_level': 'limited_features',
                'services_to_disable': ['data_archiving'],
                'timeout_minutes': 60
            },
            {
                'condition': 'error_rate > 5',
                'target_level': 'essential_only',
                'services_to_disable': ['data_archiving', 'report_generation'],
                'capacity_reduction': 0.5,
                'timeout_minutes': 120
            }
        ]
    },
    'alerts': {
        'rules': [
            {
                'name': 'batch_job_failure',
                'condition': 'errors_by_category.get("batch", 0) > 1',
                'severity': 'error',
                'description': 'Batch job failures detected',
                'notification_channels': ['console', 'log', 'email'],
                'evaluation_interval': 300,
                'cooldown_period': 1800
            }
        ]
    }
}


# Edge/IoT Configuration
EDGE_CONFIG = {
    'health_checks': {
        'checks': [
            {
                'name': 'device_connectivity',
                'type': 'custom',
                'config': {
                    'interval': 30,
                    'critical': True,
                    'failure_threshold': 5,
                    'timeout': 10.0
                }
            },
            {
                'name': 'edge_storage',
                'type': 'resource',
                'config': {
                    'interval': 60,
                    'critical': True,
                    'memory_threshold': 0.80,
                    'disk_threshold': 0.85,
                    'cpu_threshold': 0.75
                }
            }
        ]
    },
    'circuit_breakers': {
        'services': [
            {
                'name': 'cloud_sync',
                'config': {
                    'failure_threshold': 8,
                    'timeout': 300.0,
                    'success_threshold': 3,
                    'failure_mode': 'time_based',
                    'window_size': 100,
                    'failure_percentage_threshold': 90.0
                }
            }
        ]
    },
    'degradation': {
        'services': [
            {
                'name': 'local_processing',
                'tier': 'critical',
                'description': 'Local data processing and analysis'
            },
            {
                'name': 'device_control',
                'tier': 'critical',
                'description': 'Device control and monitoring'
            },
            {
                'name': 'cloud_synchronization',
                'tier': 'important',
                'description': 'Sync with cloud services',
                'dependencies': ['cloud_sync']
            },
            {
                'name': 'advanced_analytics',
                'tier': 'luxury',
                'description': 'Advanced analytics features',
                'dependencies': ['cloud_sync']
            }
        ],
        'rules': [
            {
                'condition': 'error_rate > 2',
                'target_level': 'limited_features',
                'services_to_disable': ['advanced_analytics'],
                'timeout_minutes': 30
            },
            {
                'condition': 'overall_health_status == "unhealthy"',
                'target_level': 'essential_only',
                'services_to_disable': ['advanced_analytics', 'cloud_synchronization'],
                'capacity_reduction': 0.3,
                'timeout_minutes': 60
            }
        ]
    },
    'alerts': {
        'rules': [
            {
                'name': 'edge_device_offline',
                'condition': 'health_status == "unhealthy"',
                'severity': 'error',
                'description': 'Edge device appears to be offline',
                'notification_channels': ['console', 'log'],
                'evaluation_interval': 60,
                'cooldown_period': 600
            }
        ]
    }
}


# Helper functions to get configurations
def get_config(environment: str) -> Dict[str, Any]:
    """Get configuration for specified environment"""
    configs = {
        'development': DEVELOPMENT_CONFIG,
        'production': PRODUCTION_CONFIG,
        'microservice': MICROSERVICE_CONFIG,
        'hft': HFT_CONFIG,
        'batch': BATCH_CONFIG,
        'edge': EDGE_CONFIG
    }
    
    if environment not in configs:
        raise ValueError(f"Unknown environment: {environment}. Available: {list(configs.keys())}")
    
    return configs[environment]


def create_custom_config(
    environment: str,
    custom_rules: Dict[str, Any] = None,
    custom_services: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Create custom configuration based on environment with custom overrides"""
    base_config = get_config(environment).copy()
    
    if custom_rules:
        if 'degradation' not in base_config:
            base_config['degradation'] = {}
        if 'rules' not in base_config['degradation']:
            base_config['degradation']['rules'] = []
        base_config['degradation']['rules'].extend(custom_rules)
    
    if custom_services:
        if 'degradation' not in base_config:
            base_config['degradation'] = {}
        if 'services' not in base_config['degradation']:
            base_config['degradation']['services'] = []
        base_config['degradation']['services'].extend(custom_services)
    
    return base_config


# Example usage
if __name__ == "__main__":
    # Get production configuration
    prod_config = get_config('production')
    print("Production config loaded with", len(prod_config), "sections")
    
    # Create custom configuration
    custom_config = create_custom_config(
        'production',
        custom_rules=[
            {
                'condition': 'error_rate > 15',
                'target_level': 'emergency_mode',
                'services_to_disable': ['all_non_critical'],
                'timeout_minutes': 5
            }
        ],
        custom_services=[
            {
                'name': 'new_feature',
                'tier': 'luxury',
                'description': 'New experimental feature'
            }
        ]
    )
    
    print("Custom configuration created successfully")