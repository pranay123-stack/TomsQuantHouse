"""
Test Utilities and Helper Functions
Common utilities for all testing frameworks
"""
import asyncio
import json
import logging
import time
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from pathlib import Path
import aiofiles
import aiohttp
import psutil
from dataclasses import dataclass, asdict
import yaml

@dataclass
class TestResult:
    """Standard test result format"""
    test_name: str
    status: str  # PASS, FAIL, SKIP, ERROR
    duration: float
    timestamp: datetime
    message: str = ""
    details: Dict[str, Any] = None
    error: Optional[str] = None

class TestHelpers:
    """Comprehensive test helper utilities"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.test_data_dir = Path("test_data")
        self.test_data_dir.mkdir(exist_ok=True)
        
    def _setup_logger(self) -> logging.Logger:
        """Setup test-specific logger"""
        logger = logging.getLogger("test_framework")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """Get test logger with optional name"""
        if name:
            return logging.getLogger(f"test_framework.{name}")
        return self.logger
    
    def log_test_start(self, test_name: str, test_type: str = "unknown"):
        """Log test start with context"""
        self.logger.info(f"Starting {test_type} test: {test_name}")
    
    def log_test_end(self, test_name: str, status: str, duration: float):
        """Log test completion"""
        self.logger.info(f"Test {test_name} {status} - Duration: {duration:.2f}s")
    
    def log_error(self, message: str, error: Exception = None):
        """Log error with optional exception"""
        if error:
            self.logger.error(f"{message}: {error}")
        else:
            self.logger.error(message)
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
    
    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """Log performance metrics"""
        self.logger.info(f"Performance metrics: {json.dumps(metrics, indent=2)}")
    
    async def async_timer(self, func: Callable, *args, **kwargs) -> tuple:
        """Time async function execution"""
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        return result, duration
    
    def sync_timer(self, func: Callable, *args, **kwargs) -> tuple:
        """Time sync function execution"""
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        return result, duration
    
    async def retry_async(self, func: Callable, max_retries: int = 3, 
                         delay: float = 1.0, backoff: float = 2.0, 
                         exceptions: tuple = (Exception,)) -> Any:
        """Retry async function with exponential backoff"""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await func()
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = delay * (backoff ** attempt)
                    self.logger.info(f"Attempt {attempt + 1} failed, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries + 1} attempts failed")
        
        raise last_exception
    
    def retry_sync(self, func: Callable, max_retries: int = 3,
                   delay: float = 1.0, backoff: float = 2.0,
                   exceptions: tuple = (Exception,)) -> Any:
        """Retry sync function with exponential backoff"""
        import time
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func()
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    wait_time = delay * (backoff ** attempt)
                    self.logger.info(f"Attempt {attempt + 1} failed, retrying in {wait_time}s")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {max_retries + 1} attempts failed")
        
        raise last_exception
    
    def generate_test_data(self, data_type: str, count: int = 100) -> List[Dict[str, Any]]:
        """Generate test data based on type"""
        generators = {
            "market_data": self._generate_market_data,
            "trading_signals": self._generate_trading_signals,
            "user_data": self._generate_user_data,
            "api_responses": self._generate_api_responses,
            "performance_metrics": self._generate_performance_metrics
        }
        
        if data_type not in generators:
            raise ValueError(f"Unknown data type: {data_type}")
        
        return generators[data_type](count)
    
    def _generate_market_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate market data"""
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NFLX", "NVDA"]
        data = []
        
        for i in range(count):
            symbol = random.choice(symbols)
            base_price = random.uniform(50, 3000)
            
            data.append({
                "id": i,
                "symbol": symbol,
                "timestamp": datetime.utcnow() - timedelta(minutes=random.randint(0, 1440)),
                "open": round(base_price * random.uniform(0.95, 1.05), 2),
                "high": round(base_price * random.uniform(1.0, 1.1), 2),
                "low": round(base_price * random.uniform(0.9, 1.0), 2),
                "close": round(base_price * random.uniform(0.95, 1.05), 2),
                "volume": random.randint(1000, 10000000),
                "adj_close": round(base_price * random.uniform(0.95, 1.05), 2)
            })
        
        return data
    
    def _generate_trading_signals(self, count: int) -> List[Dict[str, Any]]:
        """Generate trading signals"""
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
        actions = ["BUY", "SELL", "HOLD"]
        data = []
        
        for i in range(count):
            data.append({
                "id": i,
                "symbol": random.choice(symbols),
                "action": random.choice(actions),
                "confidence": round(random.uniform(0.1, 1.0), 2),
                "price_target": round(random.uniform(100, 3000), 2),
                "stop_loss": round(random.uniform(50, 1500), 2),
                "timestamp": datetime.utcnow() - timedelta(minutes=random.randint(0, 10080)),
                "strategy": random.choice(["momentum", "mean_reversion", "ml_ensemble"]),
                "risk_level": random.choice(["low", "medium", "high"])
            })
        
        return data
    
    def _generate_user_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate user data"""
        data = []
        
        for i in range(count):
            data.append({
                "id": i,
                "username": f"user_{i}",
                "email": f"user_{i}@test.com",
                "role": random.choice(["trader", "admin", "analyst", "viewer"]),
                "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 365)),
                "last_login": datetime.utcnow() - timedelta(hours=random.randint(1, 168)),
                "portfolio_value": round(random.uniform(10000, 1000000), 2),
                "risk_tolerance": random.choice(["conservative", "moderate", "aggressive"])
            })
        
        return data
    
    def _generate_api_responses(self, count: int) -> List[Dict[str, Any]]:
        """Generate API response data"""
        data = []
        
        for i in range(count):
            data.append({
                "request_id": f"req_{i}",
                "timestamp": datetime.utcnow() - timedelta(seconds=random.randint(0, 3600)),
                "endpoint": random.choice(["/api/market", "/api/trade", "/api/portfolio"]),
                "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                "status_code": random.choice([200, 201, 400, 401, 403, 404, 500]),
                "response_time": round(random.uniform(0.1, 5.0), 3),
                "user_agent": random.choice([
                    "Mozilla/5.0", "Chrome/91.0", "Safari/14.0", "Firefox/89.0"
                ]),
                "ip_address": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
            })
        
        return data
    
    def _generate_performance_metrics(self, count: int) -> List[Dict[str, Any]]:
        """Generate performance metrics"""
        data = []
        
        for i in range(count):
            data.append({
                "timestamp": datetime.utcnow() - timedelta(minutes=random.randint(0, 1440)),
                "cpu_usage": round(random.uniform(10, 90), 1),
                "memory_usage": round(random.uniform(20, 80), 1),
                "disk_usage": round(random.uniform(30, 70), 1),
                "network_io": {
                    "bytes_sent": random.randint(1000000, 1000000000),
                    "bytes_recv": random.randint(1000000, 1000000000)
                },
                "active_connections": random.randint(10, 500),
                "response_time_p50": round(random.uniform(0.1, 1.0), 3),
                "response_time_p95": round(random.uniform(0.5, 3.0), 3),
                "response_time_p99": round(random.uniform(1.0, 5.0), 3),
                "throughput": round(random.uniform(100, 10000), 0)
            })
        
        return data
    
    def save_test_data(self, data: List[Dict[str, Any]], filename: str, 
                      format: str = "json") -> Path:
        """Save test data to file"""
        file_path = self.test_data_dir / filename
        
        if format.lower() == "json":
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif format.lower() == "yaml":
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
        elif format.lower() == "csv":
            import csv
            with open(file_path, 'w', newline='') as f:
                if data:
                    writer = csv.DictWriter(f, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        self.logger.info(f"Test data saved to {file_path}")
        return file_path
    
    async def load_test_data(self, filename: str, format: str = "json") -> List[Dict[str, Any]]:
        """Load test data from file"""
        file_path = self.test_data_dir / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"Test data file not found: {file_path}")
        
        try:
            if format.lower() == "json":
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
            elif format.lower() == "yaml":
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    return yaml.safe_load(content)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            self.logger.error(f"Error loading test data from {file_path}: {e}")
            raise
    
    def create_mock_response(self, status_code: int = 200, data: Dict[str, Any] = None,
                           headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Create mock response for testing"""
        response = {
            "status_code": status_code,
            "data": data or {},
            "headers": headers or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add common response fields
        if status_code == 200:
            response["success"] = True
            response["message"] = "Request successful"
        elif status_code in [400, 401, 403]:
            response["success"] = False
            response["error"] = "Client error"
        elif status_code in [500, 502, 503]:
            response["success"] = False
            response["error"] = "Server error"
        
        return response
    
    def create_mock_exception(self, exception_type: str = "ConnectionError", 
                            message: str = "Mock exception") -> Exception:
        """Create mock exception for testing"""
        exceptions = {
            "ConnectionError": ConnectionError,
            "TimeoutError": asyncio.TimeoutError,
            "ValueError": ValueError,
            "RuntimeError": RuntimeError,
            "KeyError": KeyError,
            "AttributeError": AttributeError
        }
        
        if exception_type in exceptions:
            return exceptions[exception_type](message)
        else:
            return Exception(message)
    
    def generate_random_string(self, length: int = 10, 
                              include_special: bool = False) -> str:
        """Generate random string for testing"""
        chars = string.ascii_letters + string.digits
        if include_special:
            chars += string.punctuation
        
        return ''.join(random.choice(chars) for _ in range(length))
    
    def generate_random_email(self) -> str:
        """Generate random email for testing"""
        domains = ["test.com", "example.org", "demo.net", "sample.co"]
        username = self.generate_random_string(8)
        domain = random.choice(domains)
        return f"{username}@{domain}"
    
    def generate_random_date(self, start_days: int = 365, 
                           end_days: int = 0) -> datetime:
        """Generate random date within range"""
        if start_days < end_days:
            start_days, end_days = end_days, start_days
        
        days_back = random.randint(end_days, start_days)
        return datetime.utcnow() - timedelta(days=days_back)
    
    def validate_test_data(self, data: List[Dict[str, Any]], 
                          required_fields: List[str]) -> Dict[str, Any]:
        """Validate test data structure"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {
                "total_items": len(data),
                "valid_items": 0,
                "invalid_items": 0
            }
        }
        
        for i, item in enumerate(data):
            item_errors = []
            
            # Check required fields
            for field in required_fields:
                if field not in item:
                    item_errors.append(f"Missing required field: {field}")
            
            # Field-specific validations
            if "email" in required_fields and "email" in item:
                if "@" not in item["email"]:
                    item_errors.append("Invalid email format")
            
            if "timestamp" in required_fields and "timestamp" in item:
                try:
                    datetime.fromisoformat(str(item["timestamp"]))
                except ValueError:
                    item_errors.append("Invalid timestamp format")
            
            if item_errors:
                validation_result["valid"] = False
                validation_result["errors"].extend([
                    f"Item {i}: {error}" for error in item_errors
                ])
                validation_result["stats"]["invalid_items"] += 1
            else:
                validation_result["stats"]["valid_items"] += 1
        
        return validation_result
    
    def calculate_test_coverage(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """Calculate test coverage metrics"""
        if not test_results:
            return {"coverage": 0, "metrics": {}}
        
        passed_tests = [r for r in test_results if r.status == "PASS"]
        failed_tests = [r for r in test_results if r.status == "FAIL"]
        skipped_tests = [r for r in test_results if r.status == "SKIP"]
        
        total_tests = len(test_results)
        total_duration = sum(r.duration for r in test_results)
        
        coverage = (len(passed_tests) / total_tests) * 100 if total_tests > 0 else 0
        
        metrics = {
            "total_tests": total_tests,
            "passed_tests": len(passed_tests),
            "failed_tests": len(failed_tests),
            "skipped_tests": len(skipped_tests),
            "success_rate": (len(passed_tests) / total_tests) * 100 if total_tests > 0 else 0,
            "failure_rate": (len(failed_tests) / total_tests) * 100 if total_tests > 0 else 0,
            "skip_rate": (len(skipped_tests) / total_tests) * 100 if total_tests > 0 else 0,
            "total_duration": total_duration,
            "average_duration": total_duration / total_tests if total_tests > 0 else 0
        }
        
        return {
            "coverage": coverage,
            "metrics": metrics
        }
    
    def format_test_report(self, test_results: List[TestResult]) -> str:
        """Format test results into readable report"""
        if not test_results:
            return "No test results to report."
        
        # Group by status
        passed = [r for r in test_results if r.status == "PASS"]
        failed = [r for r in test_results if r.status == "FAIL"]
        skipped = [r for r in test_results if r.status == "SKIP"]
        errors = [r for r in test_results if r.status == "ERROR"]
        
        report = ["=" * 60]
        report.append("TEST EXECUTION REPORT")
        report.append("=" * 60)
        report.append(f"Total Tests: {len(test_results)}")
        report.append(f"Passed: {len(passed)} ({len(passed)/len(test_results)*100:.1f}%)")
        report.append(f"Failed: {len(failed)} ({len(failed)/len(test_results)*100:.1f}%)")
        report.append(f"Skipped: {len(skipped)} ({len(skipped)/len(test_results)*100:.1f}%)")
        report.append(f"Errors: {len(errors)} ({len(errors)/len(test_results)*100:.1f}%)")
        
        total_duration = sum(r.duration for r in test_results)
        report.append(f"Total Duration: {total_duration:.2f}s")
        report.append("")
        
        if failed:
            report.append("FAILED TESTS:")
            report.append("-" * 40)
            for test in failed:
                report.append(f"  {test.test_name}: {test.message}")
                if test.error:
                    report.append(f"    Error: {test.error}")
            report.append("")
        
        if errors:
            report.append("ERRORS:")
            report.append("-" * 40)
            for test in errors:
                report.append(f"  {test.test_name}: {test.message}")
                if test.error:
                    report.append(f"    Error: {test.error}")
            report.append("")
        
        return "\n".join(report)
    
    async def monitor_system_resources(self, duration: int = 60) -> Dict[str, Any]:
        """Monitor system resources during test execution"""
        self.logger.info(f"Starting system resource monitoring for {duration} seconds")
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            sample = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_io": dict(psutil.net_io_counters()._asdict())
            }
            
            samples.append(sample)
            await asyncio.sleep(1)
        
        # Calculate statistics
        if samples:
            cpu_values = [s["cpu_percent"] for s in samples]
            memory_values = [s["memory_percent"] for s in samples]
            
            stats = {
                "monitoring_duration": duration,
                "samples_collected": len(samples),
                "cpu_stats": {
                    "avg": sum(cpu_values) / len(cpu_values),
                    "max": max(cpu_values),
                    "min": min(cpu_values)
                },
                "memory_stats": {
                    "avg": sum(memory_values) / len(memory_values),
                    "max": max(memory_values),
                    "min": min(memory_values)
                },
                "samples": samples
            }
        else:
            stats = {"error": "No samples collected"}
        
        self.logger.info("System resource monitoring completed")
        return stats
    
    def create_test_scenario(self, scenario_name: str, description: str,
                           steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create structured test scenario"""
        scenario = {
            "name": scenario_name,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "steps": [],
            "expected_results": [],
            "metadata": {}
        }
        
        for i, step in enumerate(steps, 1):
            scenario["steps"].append({
                "step_number": i,
                "action": step.get("action", ""),
                "input": step.get("input", {}),
                "expected_output": step.get("expected_output", {}),
                "timeout": step.get("timeout", 30),
                "critical": step.get("critical", False)
            })
        
        return scenario
    
    async def execute_test_scenario(self, scenario: Dict[str, Any]) -> TestResult:
        """Execute test scenario with structured steps"""
        start_time = time.time()
        scenario_name = scenario["name"]
        
        self.logger.info(f"Executing test scenario: {scenario_name}")
        
        try:
            for step in scenario["steps"]:
                self.logger.info(f"Step {step['step_number']}: {step['action']}")
                
                # Execute step logic here
                # This would be implemented based on specific test requirements
                await asyncio.sleep(0.1)  # Simulate step execution
                
                # Validate step result
                if not self._validate_step_result(step):
                    return TestResult(
                        test_name=scenario_name,
                        status="FAIL",
                        duration=time.time() - start_time,
                        timestamp=datetime.utcnow(),
                        message=f"Step {step['step_number']} validation failed"
                    )
            
            duration = time.time() - start_time
            return TestResult(
                test_name=scenario_name,
                status="PASS",
                duration=duration,
                timestamp=datetime.utcnow(),
                message="All scenario steps completed successfully"
            )
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Test scenario {scenario_name} failed: {e}")
            
            return TestResult(
                test_name=scenario_name,
                status="ERROR",
                duration=duration,
                timestamp=datetime.utcnow(),
                message="Test scenario execution error",
                error=str(e)
            )
    
    def _validate_step_result(self, step: Dict[str, Any]) -> bool:
        """Validate individual step result"""
        # This would contain actual validation logic
        # For demonstration, always return True
        return True
    
    def cleanup_test_resources(self):
        """Cleanup test resources and temporary files"""
        try:
            # Clean up test data directory
            if self.test_data_dir.exists():
                for file in self.test_data_dir.glob("*.tmp"):
                    file.unlink()
            
            self.logger.info("Test resources cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

# Additional utility classes

class APITestHelper:
    """Helper for API testing"""
    
    def __init__(self, base_url: str, auth_token: str = None):
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make GET request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        async with self.session.get(url, params=params, headers=headers) as response:
            return await self._process_response(response)
    
    async def post(self, endpoint: str, data: Dict[str, Any] = None, 
                   json_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make POST request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        async with self.session.post(url, data=data, json=json_data, headers=headers) as response:
            return await self._process_response(response)
    
    async def put(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make PUT request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        async with self.session.put(url, json=data, headers=headers) as response:
            return await self._process_response(response)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        async with self.session.delete(url, headers=headers) as response:
            return await self._process_response(response)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers
    
    async def _process_response(self, response) -> Dict[str, Any]:
        """Process HTTP response"""
        try:
            response_data = await response.json()
        except:
            response_data = {"text": await response.text()}
        
        return {
            "status_code": response.status,
            "data": response_data,
            "headers": dict(response.headers),
            "url": str(response.url)
        }

class DatabaseTestHelper:
    """Helper for database testing"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    async def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute database query"""
        # This would implement actual database queries
        # For demonstration, return mock results
        return []
    
    async def insert_test_data(self, table: str, data: List[Dict[str, Any]]) -> bool:
        """Insert test data into table"""
        # This would implement actual data insertion
        return True
    
    async def cleanup_test_data(self, tables: List[str]) -> bool:
        """Cleanup test data from tables"""
        # This would implement actual data cleanup
        return True

class PerformanceTestHelper:
    """Helper for performance testing"""
    
    def __init__(self):
        self.metrics = []
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        self.metrics = []
    
    async def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record performance metric"""
        metric = {
            "name": metric_name,
            "value": value,
            "tags": tags or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.metrics.append(metric)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        if not self.metrics:
            return {}
        
        # Group by metric name
        grouped = {}
        for metric in self.metrics:
            name = metric["name"]
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(metric["value"])
        
        # Calculate statistics
        summary = {}
        for name, values in grouped.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "sum": sum(values)
                }
        
        return summary

# Export main classes
__all__ = [
    'TestHelpers',
    'APITestHelper', 
    'DatabaseTestHelper',
    'PerformanceTestHelper',
    'TestResult'
]