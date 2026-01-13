#!/usr/bin/env python3
"""
Environment Testing and Validation System

This module provides:
- Environment health checks and validation
- Configuration testing across environments
- Security validation and compliance checks
- Performance testing and monitoring
- Automated testing procedures
"""

import os
import json
import yaml
import subprocess
import socket
import ssl
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import logging
from dataclasses import dataclass, field
from enum import Enum
import concurrent.futures
import threading
import time

logger = logging.getLogger(__name__)

class TestResult(Enum):
    """Test result types"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"

@dataclass
class ValidationCheck:
    """Configuration validation check"""
    name: str
    description: str
    check_type: str  # connectivity, security, config, performance, etc.
    severity: str  # critical, high, medium, low
    timeout: int = 30
    retries: int = 1
    
@dataclass
class TestResult:
    """Test execution result"""
    check_name: str
    result: TestResult
    message: str
    execution_time: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

class EnvironmentValidator:
    """Environment validation engine"""
    
    def __init__(self):
        self.checks: List[ValidationCheck] = []
        self.test_results: List[TestResult] = []
        self._load_default_checks()
    
    def _load_default_checks(self):
        """Load default validation checks"""
        # Configuration checks
        self.add_check(ValidationCheck(
            name="config_syntax",
            description="Validate YAML configuration syntax",
            check_type="config",
            severity="critical"
        ))
        
        self.add_check(ValidationCheck(
            name="required_fields",
            description="Check for required configuration fields",
            check_type="config",
            severity="critical"
        ))
        
        self.add_check(ValidationCheck(
            name="secret_references",
            description="Validate secret references are properly defined",
            check_type="security",
            severity="high"
        ))
        
        # Connectivity checks
        self.add_check(ValidationCheck(
            name="database_connectivity",
            description="Test database connectivity",
            check_type="connectivity",
            severity="critical",
            timeout=10
        ))
        
        self.add_check(ValidationCheck(
            name="redis_connectivity",
            description="Test Redis connectivity",
            check_type="connectivity",
            severity="high",
            timeout=10
        ))
        
        self.add_check(ValidationCheck(
            name="external_apis",
            description="Test external API connectivity",
            check_type="connectivity",
            severity="medium",
            timeout=30,
            retries=3
        ))
        
        # Security checks
        self.add_check(ValidationCheck(
            name="ssl_certificates",
            description="Validate SSL certificates",
            check_type="security",
            severity="high",
            timeout=15
        ))
        
        self.add_check(ValidationCheck(
            name="jwt_validation",
            description="Validate JWT configuration",
            check_type="security",
            severity="medium"
        ))
        
        self.add_check(ValidationCheck(
            name="cors_configuration",
            description="Validate CORS settings",
            check_type="security",
            severity="medium"
        ))
        
        # Performance checks
        self.add_check(ValidationCheck(
            name="response_time",
            description="Test application response time",
            check_type="performance",
            severity="medium",
            timeout=20
        ))
        
        self.add_check(ValidationCheck(
            name="memory_usage",
            description="Check memory usage",
            check_type="performance",
            severity="low",
            timeout=15
        ))
        
        self.add_check(ValidationCheck(
            name="disk_space",
            description="Check available disk space",
            check_type="performance",
            severity="medium",
            timeout=10
        ))
    
    def add_check(self, check: ValidationCheck):
        """Add validation check"""
        self.checks.append(check)
    
    def run_validation(self, environment: str, config_data: Dict[str, Any], 
                      environment_vars: Dict[str, str] = None) -> List[TestResult]:
        """Run all validation checks for an environment"""
        self.test_results = []
        environment_vars = environment_vars or {}
        
        # Set environment variables
        old_env = {}
        for key, value in environment_vars.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            # Run checks in parallel for better performance
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                
                for check in self.checks:
                    if self._should_run_check(check, environment):
                        future = executor.submit(
                            self._run_single_check, check, environment, config_data
                        )
                        futures[future] = check
                
                # Collect results
                for future in concurrent.futures.as_completed(futures, timeout=300):
                    check = futures[future]
                    try:
                        result = future.result(timeout=check.timeout)
                        self.test_results.append(result)
                        logger.info(f"Check '{check.name}' completed: {result.result.value}")
                    except Exception as e:
                        error_result = TestResult(
                            check_name=check.name,
                            result=TestResult.FAIL,
                            message=f"Check execution failed: {e}",
                            execution_time=check.timeout,
                            timestamp=datetime.now()
                        )
                        self.test_results.append(error_result)
                        logger.error(f"Check '{check.name}' failed: {e}")
            
            return self.test_results
            
        finally:
            # Restore environment variables
            for key, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value
    
    def _should_run_check(self, check: ValidationCheck, environment: str) -> bool:
        """Determine if check should run for environment"""
        # Skip performance checks in development
        if environment == "development" and check.check_type == "performance":
            return False
        
        # Skip SSL checks in development
        if environment == "development" and check.name == "ssl_certificates":
            return False
        
        return True
    
    def _run_single_check(self, check: ValidationCheck, environment: str, 
                         config_data: Dict[str, Any]) -> TestResult:
        """Run a single validation check"""
        start_time = time.time()
        timestamp = datetime.now()
        
        try:
            if check.check_type == "config":
                return self._run_config_check(check, config_data, environment, start_time, timestamp)
            elif check.check_type == "connectivity":
                return self._run_connectivity_check(check, config_data, environment, start_time, timestamp)
            elif check.check_type == "security":
                return self._run_security_check(check, config_data, environment, start_time, timestamp)
            elif check.check_type == "performance":
                return self._run_performance_check(check, config_data, environment, start_time, timestamp)
            else:
                return TestResult(
                    check_name=check.name,
                    result=TestResult.SKIP,
                    message=f"Unknown check type: {check.check_type}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
        except Exception as e:
            return TestResult(
                check_name=check.name,
                result=TestResult.FAIL,
                message=f"Check failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _run_config_check(self, check: ValidationCheck, config_data: Dict[str, Any], 
                         environment: str, start_time: float, timestamp: datetime) -> TestResult:
        """Run configuration validation checks"""
        
        if check.name == "config_syntax":
            try:
                # Test YAML parsing
                yaml.safe_load(json.dumps(config_data))  # Test if can be parsed
                return TestResult(
                    check_name=check.name,
                    result=TestResult.PASS,
                    message="Configuration syntax is valid",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            except Exception as e:
                return TestResult(
                    check_name=check.name,
                    result=TestResult.FAIL,
                    message=f"Configuration syntax error: {e}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
        
        elif check.name == "required_fields":
            required_fields = [
                "environment.name",
                "environment.type",
                "app.host",
                "app.port",
                "app.database.host",
                "security.jwt.secret"
            ]
            
            missing_fields = []
            for field_path in required_fields:
                if not self._config_has_field(config_data, field_path):
                    missing_fields.append(field_path)
            
            if missing_fields:
                return TestResult(
                    check_name=check.name,
                    result=TestResult.FAIL,
                    message=f"Missing required fields: {', '.join(missing_fields)}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Add all required fields to configuration"]
                )
            else:
                return TestResult(
                    check_name=check.name,
                    result=TestResult.PASS,
                    message="All required fields are present",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
        
        elif check.name == "secret_references":
            secret_refs = self._find_secret_references(config_data)
            validation_errors = []
            
            for ref in secret_refs:
                if ref.startswith("${") and ref.endswith("}"):
                    var_name = ref[2:-1]
                    if var_name not in os.environ:
                        validation_errors.append(f"Environment variable not set: {var_name}")
            
            if validation_errors:
                return TestResult(
                    check_name=check.name,
                    result=TestResult.FAIL,
                    message=f"Secret reference validation failed: {'; '.join(validation_errors)}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Set all required environment variables"]
                )
            else:
                return TestResult(
                    check_name=check.name,
                    result=TestResult.PASS,
                    message="All secret references are valid",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
        
        # Default for unknown config checks
        return TestResult(
            check_name=check.name,
            result=TestResult.SKIP,
            message="Check not implemented",
            execution_time=time.time() - start_time,
            timestamp=timestamp
        )
    
    def _run_connectivity_check(self, check: ValidationCheck, config_data: Dict[str, Any], 
                               environment: str, start_time: float, timestamp: datetime) -> TestResult:
        """Run connectivity validation checks"""
        
        if check.name == "database_connectivity":
            return self._test_database_connectivity(config_data, start_time, timestamp)
        
        elif check.name == "redis_connectivity":
            return self._test_redis_connectivity(config_data, start_time, timestamp)
        
        elif check.name == "external_apis":
            return self._test_external_apis(config_data, start_time, timestamp)
        
        # Default
        return TestResult(
            check_name=check.name,
            result=TestResult.SKIP,
            message="Connectivity check not implemented",
            execution_time=time.time() - start_time,
            timestamp=timestamp
        )
    
    def _run_security_check(self, check: ValidationCheck, config_data: Dict[str, Any], 
                           environment: str, start_time: float, timestamp: datetime) -> TestResult:
        """Run security validation checks"""
        
        if check.name == "ssl_certificates":
            return self._test_ssl_certificates(config_data, start_time, timestamp)
        
        elif check.name == "jwt_validation":
            return self._test_jwt_config(config_data, start_time, timestamp)
        
        elif check.name == "cors_configuration":
            return self._test_cors_config(config_data, start_time, timestamp)
        
        # Default
        return TestResult(
            check_name=check.name,
            result=TestResult.SKIP,
            message="Security check not implemented",
            execution_time=time.time() - start_time,
            timestamp=timestamp
        )
    
    def _run_performance_check(self, check: ValidationCheck, config_data: Dict[str, Any], 
                              environment: str, start_time: float, timestamp: datetime) -> TestResult:
        """Run performance validation checks"""
        
        if check.name == "response_time":
            return self._test_response_time(config_data, start_time, timestamp)
        
        elif check.name == "memory_usage":
            return self._test_memory_usage(start_time, timestamp)
        
        elif check.name == "disk_space":
            return self._test_disk_space(start_time, timestamp)
        
        # Default
        return TestResult(
            check_name=check.name,
            result=TestResult.SKIP,
            message="Performance check not implemented",
            execution_time=time.time() - start_time,
            timestamp=timestamp
        )
    
    def _config_has_field(self, config: Dict[str, Any], field_path: str) -> bool:
        """Check if configuration has a field by path"""
        keys = field_path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return False
        
        return True
    
    def _find_secret_references(self, config: Dict[str, Any]) -> List[str]:
        """Find all secret references in configuration"""
        refs = []
        
        def traverse(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    traverse(value)
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item)
            elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
                refs.append(obj)
        
        traverse(config)
        return refs
    
    def _test_database_connectivity(self, config_data: Dict[str, Any], 
                                   start_time: float, timestamp: datetime) -> TestResult:
        """Test database connectivity"""
        try:
            db_config = config_data.get('app', {}).get('database', {})
            host = db_config.get('host')
            port = db_config.get('port', 5432)
            
            if not host:
                return TestResult(
                    check_name="database_connectivity",
                    result=TestResult.FAIL,
                    message="Database host not configured",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            
            # Test basic connectivity with socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return TestResult(
                    check_name="database_connectivity",
                    result=TestResult.PASS,
                    message=f"Database connection successful to {host}:{port}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            else:
                return TestResult(
                    check_name="database_connectivity",
                    result=TestResult.FAIL,
                    message=f"Cannot connect to database at {host}:{port}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
                
        except Exception as e:
            return TestResult(
                check_name="database_connectivity",
                result=TestResult.FAIL,
                message=f"Database connectivity test failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_redis_connectivity(self, config_data: Dict[str, Any], 
                                start_time: float, timestamp: datetime) -> TestResult:
        """Test Redis connectivity"""
        try:
            redis_config = config_data.get('app', {}).get('redis', {})
            host = redis_config.get('host')
            port = redis_config.get('port', 6379)
            
            if not host:
                return TestResult(
                    check_name="redis_connectivity",
                    result=TestResult.WARNING,
                    message="Redis not configured",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            
            # Test basic connectivity
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return TestResult(
                    check_name="redis_connectivity",
                    result=TestResult.PASS,
                    message=f"Redis connection successful to {host}:{port}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            else:
                return TestResult(
                    check_name="redis_connectivity",
                    result=TestResult.FAIL,
                    message=f"Cannot connect to Redis at {host}:{port}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
                
        except Exception as e:
            return TestResult(
                check_name="redis_connectivity",
                result=TestResult.FAIL,
                message=f"Redis connectivity test failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_external_apis(self, config_data: Dict[str, Any], 
                           start_time: float, timestamp: datetime) -> TestResult:
        """Test external API connectivity"""
        try:
            apis = config_data.get('app', {}).get('external_apis', {})
            
            if not apis:
                return TestResult(
                    check_name="external_apis",
                    result=TestResult.WARNING,
                    message="No external APIs configured",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            
            failed_apis = []
            successful_apis = []
            
            for api_name, api_config in apis.items():
                try:
                    url = api_config.get('url')
                    timeout = api_config.get('timeout', 30)
                    
                    if not url:
                        failed_apis.append(f"{api_name}: URL not configured")
                        continue
                    
                    # Test connectivity with HEAD request
                    response = requests.head(url, timeout=timeout)
                    
                    if response.status_code < 500:  # Accept 2xx, 3xx, 4xx
                        successful_apis.append(api_name)
                    else:
                        failed_apis.append(f"{api_name}: HTTP {response.status_code}")
                        
                except Exception as e:
                    failed_apis.append(f"{api_name}: {str(e)}")
            
            if not failed_apis:
                return TestResult(
                    check_name="external_apis",
                    result=TestResult.PASS,
                    message=f"All {len(successful_apis)} external APIs are reachable",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            else:
                return TestResult(
                    check_name="external_apis",
                    result=TestResult.FAIL,
                    message=f"Some APIs failed: {'; '.join(failed_apis)}",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
                
        except Exception as e:
            return TestResult(
                check_name="external_apis",
                result=TestResult.FAIL,
                message=f"External API test failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_ssl_certificates(self, config_data: Dict[str, Any], 
                              start_time: float, timestamp: datetime) -> TestResult:
        """Test SSL certificate validity"""
        try:
            base_url = config_data.get('app', {}).get('base_url', '')
            
            if not base_url.startswith('https://'):
                return TestResult(
                    check_name="ssl_certificates",
                    result=TestResult.WARNING,
                    message="SSL not enabled for this environment",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            
            import urllib.parse
            parsed_url = urllib.parse.urlparse(base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            # Test SSL certificate
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=15) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Check expiration
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                    days_until_expiry = (not_after - datetime.now()).days
                    
                    if days_until_expiry < 30:
                        return TestResult(
                            check_name="ssl_certificates",
                            result=TestResult.WARNING,
                            message=f"SSL certificate expires in {days_until_expiry} days",
                            execution_time=time.time() - start_time,
                            timestamp=timestamp,
                            recommendations=["Renew SSL certificate"]
                        )
                    else:
                        return TestResult(
                            check_name="ssl_certificates",
                            result=TestResult.PASS,
                            message=f"SSL certificate is valid (expires in {days_until_expiry} days)",
                            execution_time=time.time() - start_time,
                            timestamp=timestamp
                        )
                        
        except Exception as e:
            return TestResult(
                check_name="ssl_certificates",
                result=TestResult.FAIL,
                message=f"SSL certificate test failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_jwt_config(self, config_data: Dict[str, Any], 
                        start_time: float, timestamp: datetime) -> TestResult:
        """Test JWT configuration"""
        try:
            jwt_config = config_data.get('security', {}).get('jwt', {})
            
            if not jwt_config.get('secret'):
                return TestResult(
                    check_name="jwt_validation",
                    result=TestResult.FAIL,
                    message="JWT secret not configured",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            
            secret = jwt_config.get('secret')
            if len(secret) < 32:
                return TestResult(
                    check_name="jwt_validation",
                    result=TestResult.WARNING,
                    message="JWT secret is shorter than recommended 32 characters",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Use a longer JWT secret for better security"]
                )
            
            expiration = jwt_config.get('expiration', '24h')
            
            return TestResult(
                check_name="jwt_validation",
                result=TestResult.PASS,
                message="JWT configuration is valid",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
            
        except Exception as e:
            return TestResult(
                check_name="jwt_validation",
                result=TestResult.FAIL,
                message=f"JWT validation failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_cors_config(self, config_data: Dict[str, Any], 
                         start_time: float, timestamp: datetime) -> TestResult:
        """Test CORS configuration"""
        try:
            cors_config = config_data.get('security', {}).get('cors', {})
            
            if not cors_config.get('enabled', False):
                return TestResult(
                    check_name="cors_configuration",
                    result=TestResult.PASS,
                    message="CORS is disabled (appropriate for this configuration)",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            
            origins = cors_config.get('origins', [])
            
            if not origins:
                return TestResult(
                    check_name="cors_configuration",
                    result=TestResult.WARNING,
                    message="CORS is enabled but no origins are specified",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Specify allowed origins for CORS"]
                )
            
            return TestResult(
                check_name="cors_configuration",
                result=TestResult.PASS,
                message=f"CORS is properly configured with {len(origins)} allowed origins",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
            
        except Exception as e:
            return TestResult(
                check_name="cors_configuration",
                result=TestResult.FAIL,
                message=f"CORS validation failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_response_time(self, config_data: Dict[str, Any], 
                           start_time: float, timestamp: datetime) -> TestResult:
        """Test application response time"""
        try:
            base_url = config_data.get('app', {}).get('base_url', '')
            health_endpoint = config_data.get('monitoring', {}).get('health_checks', {}).get('endpoint', '/health')
            
            if not base_url:
                return TestResult(
                    check_name="response_time",
                    result=TestResult.WARNING,
                    message="No base URL configured for response time test",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
            
            url = f"{base_url.rstrip('/')}{health_endpoint}"
            
            start_request = time.time()
            response = requests.get(url, timeout=20)
            response_time = (time.time() - start_request) * 1000  # Convert to milliseconds
            
            if response_time > 5000:  # 5 seconds
                return TestResult(
                    check_name="response_time",
                    result=TestResult.FAIL,
                    message=f"Response time too high: {response_time:.0f}ms",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Optimize application performance", "Check database connectivity"]
                )
            elif response_time > 2000:  # 2 seconds
                return TestResult(
                    check_name="response_time",
                    result=TestResult.WARNING,
                    message=f"Response time is elevated: {response_time:.0f}ms",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Monitor performance trends"]
                )
            else:
                return TestResult(
                    check_name="response_time",
                    result=TestResult.PASS,
                    message=f"Response time is good: {response_time:.0f}ms",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
                
        except Exception as e:
            return TestResult(
                check_name="response_time",
                result=TestResult.FAIL,
                message=f"Response time test failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_memory_usage(self, start_time: float, timestamp: datetime) -> TestResult:
        """Test system memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            if memory_percent > 90:
                return TestResult(
                    check_name="memory_usage",
                    result=TestResult.FAIL,
                    message=f"Memory usage too high: {memory_percent:.1f}%",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Increase available memory", "Optimize application memory usage"]
                )
            elif memory_percent > 80:
                return TestResult(
                    check_name="memory_usage",
                    result=TestResult.WARNING,
                    message=f"Memory usage elevated: {memory_percent:.1f}%",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Monitor memory usage trends"]
                )
            else:
                return TestResult(
                    check_name="memory_usage",
                    result=TestResult.PASS,
                    message=f"Memory usage is normal: {memory_percent:.1f}%",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
                
        except ImportError:
            return TestResult(
                check_name="memory_usage",
                result=TestResult.SKIP,
                message="psutil not available for memory testing",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
        except Exception as e:
            return TestResult(
                check_name="memory_usage",
                result=TestResult.FAIL,
                message=f"Memory test failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def _test_disk_space(self, start_time: float, timestamp: datetime) -> TestResult:
        """Test available disk space"""
        try:
            import psutil
            
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            if disk_percent > 90:
                return TestResult(
                    check_name="disk_space",
                    result=TestResult.FAIL,
                    message=f"Disk space critically low: {disk_percent:.1f}% used",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Clean up disk space", "Move data to additional storage"]
                )
            elif disk_percent > 80:
                return TestResult(
                    check_name="disk_space",
                    result=TestResult.WARNING,
                    message=f"Disk space running low: {disk_percent:.1f}% used",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp,
                    recommendations=["Monitor disk usage", "Plan for cleanup"]
                )
            else:
                return TestResult(
                    check_name="disk_space",
                    result=TestResult.PASS,
                    message=f"Disk space is adequate: {disk_percent:.1f}% used",
                    execution_time=time.time() - start_time,
                    timestamp=timestamp
                )
                
        except ImportError:
            return TestResult(
                check_name="disk_space",
                result=TestResult.SKIP,
                message="psutil not available for disk testing",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
        except Exception as e:
            return TestResult(
                check_name="disk_space",
                result=TestResult.FAIL,
                message=f"Disk space test failed: {e}",
                execution_time=time.time() - start_time,
                timestamp=timestamp
            )
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get test execution summary"""
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r.result == TestResult.PASS])
        failed = len([r for r in self.test_results if r.result == TestResult.FAIL])
        warnings = len([r for r in self.test_results if r.result == TestResult.WARNING])
        skipped = len([r for r in self.test_results if r.result == TestResult.SKIP])
        
        return {
            'total_tests': total_tests,
            'passed': passed,
            'failed': failed,
            'warnings': warnings,
            'skipped': skipped,
            'success_rate': (passed / total_tests * 100) if total_tests > 0 else 0,
            'execution_time': sum(r.execution_time for r in self.test_results),
            'timestamp': datetime.now().isoformat()
        }

class EnvironmentTester:
    """Main environment testing orchestrator"""
    
    def __init__(self):
        self.validator = EnvironmentValidator()
        self.test_history = []
    
    def run_full_validation(self, environment: str, config_data: Dict[str, Any], 
                           environment_vars: Dict[str, str] = None) -> Dict[str, Any]:
        """Run complete environment validation"""
        
        logger.info(f"Starting full validation for {environment}")
        
        # Run all validation checks
        results = self.validator.run_validation(environment, config_data, environment_vars)
        
        # Create test record
        test_record = {
            'environment': environment,
            'timestamp': datetime.now(),
            'results': [self._result_to_dict(result) for result in results],
            'summary': self.validator.get_test_summary()
        }
        
        self.test_history.append(test_record)
        
        # Log summary
        summary = test_record['summary']
        logger.info(f"Validation complete for {environment}: "
                   f"{summary['passed']}/{summary['total_tests']} tests passed "
                   f"({summary['success_rate']:.1f}% success rate)")
        
        return test_record
    
    def run_environment_comparison(self, env1: str, config1: Dict[str, Any], 
                                  env2: str, config2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two environments and identify differences"""
        
        results = {
            'comparison_timestamp': datetime.now().isoformat(),
            'environments': {
                env1: self._analyze_environment_config(config1),
                env2: self._analyze_environment_config(config2)
            },
            'differences': []
        }
        
        # Identify key differences
        differences = []
        
        # Compare database configurations
        db1 = config1.get('app', {}).get('database', {})
        db2 = config2.get('app', {}).get('database', {})
        
        for key in ['host', 'port', 'name', 'ssl_mode']:
            if db1.get(key) != db2.get(key):
                differences.append({
                    'category': 'database',
                    'property': key,
                    'environment1_value': db1.get(key),
                    'environment2_value': db2.get(key)
                })
        
        # Compare security settings
        sec1 = config1.get('security', {})
        sec2 = config2.get('security', {})
        
        jwt1 = sec1.get('jwt', {})
        jwt2 = sec2.get('jwt', {})
        
        for key in ['expiration', 'algorithm']:
            if jwt1.get(key) != jwt2.get(key):
                differences.append({
                    'category': 'security',
                    'property': f"jwt.{key}",
                    'environment1_value': jwt1.get(key),
                    'environment2_value': jwt2.get(key)
                })
        
        results['differences'] = differences
        return results
    
    def _analyze_environment_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze configuration for an environment"""
        analysis = {
            'environment_type': config.get('environment', {}).get('type', 'unknown'),
            'has_database': 'app' in config and 'database' in config['app'],
            'has_redis': 'app' in config and 'redis' in config['app'],
            'has_external_apis': 'app' in config and 'external_apis' in config['app'],
            'security_enabled': 'security' in config,
            'monitoring_enabled': 'monitoring' in config,
            'feature_flags': config.get('features', {})
        }
        
        return analysis
    
    def _result_to_dict(self, result: TestResult) -> Dict[str, Any]:
        """Convert TestResult to dictionary"""
        return {
            'check_name': result.check_name,
            'result': result.result.value,
            'message': result.message,
            'execution_time': result.execution_time,
            'timestamp': result.timestamp.isoformat(),
            'details': result.details,
            'recommendations': result.recommendations
        }

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Environment Testing and Validation')
    parser.add_argument('--action', choices=['validate', 'compare'], required=True, help='Action to perform')
    parser.add_argument('--environment', help='Environment name')
    parser.add_argument('--config-file', help='Configuration file path')
    parser.add_argument('--env1', help='First environment for comparison')
    parser.add_argument('--env2', help='Second environment for comparison')
    parser.add_argument('--config1', help='First configuration file')
    parser.add_argument('--config2', help='Second configuration file')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    tester = EnvironmentTester()
    
    if args.action == 'validate':
        if not args.environment or not args.config_file:
            print("Error: environment and config-file are required for validate action")
            return
        
        # Load configuration
        try:
            with open(args.config_file) as f:
                config_data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return
        
        # Run validation
        results = tester.run_full_validation(args.environment, config_data)
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Validation results saved to {args.output}")
        else:
            print(f"Validation results for {args.environment}:")
            print(json.dumps(results, indent=2, default=str))
    
    elif args.action == 'compare':
        if not all([args.env1, args.env2, args.config1, args.config2]):
            print("Error: env1, env2, config1, and config2 are required for compare action")
            return
        
        # Load configurations
        try:
            with open(args.config1) as f:
                config1 = yaml.safe_load(f)
            with open(args.config2) as f:
                config2 = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return
        
        # Run comparison
        results = tester.run_environment_comparison(args.env1, config1, args.env2, config2)
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Comparison results saved to {args.output}")
        else:
            print(f"Environment comparison results:")
            print(json.dumps(results, indent=2, default=str))

if __name__ == '__main__':
    main()