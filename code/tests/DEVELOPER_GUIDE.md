# Developer Guide - API Integration Testing Suite

This guide explains how to extend, maintain, and customize the comprehensive testing suite for the Redis-QuantConnect-Abacus.AI-LEAN data pipeline.

## Architecture Overview

The testing suite follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Test Layers   │    │   Test Types     │    │   Execution     │
├─────────────────┤    ├──────────────────┤    ├─────────────────┤
│ • Integration   │───▶│ • Health Checks  │───▶│ • Sequential    │
│ • Performance   │    │ • Data Flow      │    │ • Parallel      │
│ • End-to-End    │    │ • Memory Tests   │    │ • Continuous    │
│ • Error Handling│    │ • Error Scenarios│    │ • Custom        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Core Components

### 1. Test Configuration (`conftest.py`)
Central configuration and shared fixtures for all tests.

**Key Components:**
- `TestConfig`: Environment and performance thresholds
- `redis_client`: Redis connection fixture with fallback
- Mock clients for external services
- Sample data fixtures

**Extending Configuration:**
```python
# Add new environment variable
NEW_SERVICE_URL = os.getenv('NEW_SERVICE_URL', 'http://localhost:8000')

# Add new performance threshold
MAX_NEW_OPERATION_TIME = 2.0  # seconds

# Add new test symbols
NEW_TEST_SYMBOLS = ['NVDA', 'AMD', 'INTC']
```

### 2. Health Check Tests (`test_health_checks.py`)
Validates service availability and performance.

**Adding New Service Health Check:**
```python
@pytest.mark.integration
@pytest.mark.new_service
class TestNewServiceHealthChecks:
    async def test_new_service_api_health(self, mock_new_service_client):
        """Test new service API health endpoint"""
        try:
            status = await mock_new_service_client.get_status()
            assert status["status"] == "healthy"
            print("New service is healthy")
        except Exception as e:
            pytest.fail(f"New service health check failed: {e}")
    
    async def test_new_service_performance(self, mock_new_service_client):
        """Test new service performance metrics"""
        start_time = time.time()
        response = await mock_new_service_client.process_request()
        response_time = time.time() - start_time
        
        assert response_time < TestConfig.MAX_NEW_OPERATION_TIME
        print(f"New service response time: {response_time:.3f}s")
```

### 3. Data Flow Tests (`test_data_flow.py`)
Tests integration between services and data pipeline.

**Adding New Data Flow Test:**
```python
@pytest.mark.integration
@pytest.mark.new_service
class TestNewDataFlow:
    async def test_new_service_integration(self, redis_client, mock_new_service, clean_redis):
        """Test integration with new service"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        # Step 1: Get data from new service
        data = await mock_new_service.get_data("test_symbol")
        
        # Step 2: Process data
        processed_data = await self._process_new_data(data)
        
        # Step 3: Cache processed data
        cache_key = f"new_service:{data['symbol']}:processed"
        await redis_client.setex(cache_key, 300, json.dumps(processed_data))
        
        # Step 4: Verify caching
        cached_data = await redis_client.get(cache_key)
        assert cached_data is not None
        
        print("New service integration successful")
    
    async def _process_new_data(self, data: Dict) -> Dict:
        """Process data from new service"""
        # Custom processing logic
        return {"processed": True, "original": data}
```

### 4. Performance Tests (`test_prediction_caching.py`)
Benchmarking cache and service performance.

**Adding Performance Benchmark:**
```python
@pytest.mark.performance
class TestNewServicePerformance:
    async def test_new_service_cache_performance(self, redis_client, clean_redis):
        """Benchmark new service cache operations"""
        if not hasattr(redis_client, 'setex'):
            pytest.skip("Redis not available - using mock")
        
        operation_times = []
        num_operations = 50
        
        for i in range(num_operations):
            cache_key = f"perf_test:new_service:{i}"
            data = {"operation": i, "timestamp": datetime.utcnow().isoformat()}
            
            start_time = time.time()
            await redis_client.setex(cache_key, 60, json.dumps(data))
            operation_time = time.time() - start_time
            
            operation_times.append(operation_time)
        
        # Calculate and log statistics
        avg_time = sum(operation_times) / len(operation_times)
        max_time = max(operation_times)
        
        print(f"New service cache performance:")
        print(f"  Average: {avg_time:.4f}s")
        print(f"  Max: {max_time:.4f}s")
        
        # Performance assertions
        assert avg_time < TestConfig.MAX_NEW_OPERATION_TIME
```

### 5. End-to-End Tests (`test_complete_pipeline.py`)
Complete workflow validation.

**Adding New Pipeline Step:**
```python
async def test_new_pipeline_step(self, redis_client, mock_new_service, clean_redis):
    """Test adding new step to pipeline"""
    symbol = "PIPELINE_TEST"
    
    # Existing pipeline steps
    market_data = await mock_quantconnect_client.get_market_data(symbol)
    features = await self._compute_features(market_data, symbol)
    
    # NEW STEP: Process with new service
    new_service_result = await mock_new_service.process(features)
    
    # Cache new service result
    cache_key = f"new_service:result:{symbol}"
    await redis_client.setex(cache_key, 300, json.dumps(new_service_result))
    
    # Verify pipeline continues to work
    assert new_service_result["status"] == "success"
    print("New pipeline step integrated successfully")
```

### 6. Memory Persistence Tests (`test_letta_memory.py`)
Agent memory and conversation handling.

**Adding Memory Feature Test:**
```python
async def test_new_memory_feature(self, mock_letta_client):
    """Test new Letta memory feature"""
    agent_config = {
        "name": "memory_feature_agent",
        "memory_features": {
            "episodic_memory": True,
            "semantic_memory": True,
            "working_memory": True
        }
    }
    
    create_result = await mock_letta_client.create_agent(agent_config)
    agent_id = create_result["agent_id"]
    
    # Test episodic memory
    episodic_memory = {
        "episodes": [
            {
                "event": "User asked about AAPL",
                "context": "trading discussion",
                "importance": 0.8
            }
        ]
    }
    
    await mock_letta_client.update_memory(agent_id, episodic_memory)
    
    # Verify memory persistence
    retrieved_memory = await mock_letta_client.get_memory(agent_id)
    assert "episodes" in retrieved_memory
    assert len(retrieved_memory["episodes"]) == 1
```

### 7. Error Handling Tests (`test_error_handling.py`)
Robustness and fallback testing.

**Adding New Error Scenario:**
```python
async def test_new_service_error_handling(self, mock_new_service):
    """Test error handling for new service"""
    
    # Simulate various failure modes
    error_scenarios = [
        ("timeout", asyncio.TimeoutError("Request timeout")),
        ("rate_limit", Exception("429 Too Many Requests")),
        ("server_error", Exception("500 Internal Server Error")),
        ("invalid_data", Exception("Invalid response format"))
    ]
    
    for scenario_name, error in error_scenarios:
        mock_new_service.process.side_effect = error
        
        try:
            await mock_new_service.process({"test": "data"})
            assert False, f"Should have failed for {scenario_name}"
        except Exception as e:
            # Verify error is handled gracefully
            assert str(e) == str(error)
            print(f"✅ {scenario_name} error handled correctly")
    
    # Test fallback behavior
    mock_new_service.process.side_effect = None
    mock_new_service.process.return_value = {"fallback": True}
    
    fallback_result = await mock_new_service.process({"test": "data"})
    assert fallback_result["fallback"] is True
    print("✅ Fallback behavior working correctly")
```

## Test Markers and Categories

### Custom Markers
Add new markers in `pytest.ini`:

```ini
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance benchmarking tests
    e2e: End-to-end pipeline tests
    slow: Tests that take longer than 5 seconds
    redis: Tests requiring Redis service
    new_service: Tests requiring new service
    critical: Critical path tests
    regression: Regression tests
```

### Marker Usage
```python
@pytest.mark.new_service
@pytest.mark.integration
async def test_new_service_feature(self):
    pass

# Run with marker
pytest -m "new_service and integration"
```

## Mock Implementation Guide

### Creating Realistic Mocks
```python
class MockNewServiceClient:
    def __init__(self):
        self.call_count = 0
        self.latency = 0.1  # Simulate realistic latency
    
    async def process(self, data: Dict) -> Dict:
        self.call_count += 1
        await asyncio.sleep(self.latency)  # Realistic delay
        
        # Simulate occasional failures
        if self.call_count % 10 == 0:
            raise Exception("Simulated service error")
        
        return {
            "processed": True,
            "result": "success",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def reset(self):
        """Reset mock state"""
        self.call_count = 0
```

### Mock Configuration in Fixtures
```python
@pytest.fixture
def mock_new_service():
    """Configure mock new service client"""
    client = MockNewServiceClient()
    
    # Configure specific behaviors
    client.latency = 0.05  # Faster for tests
    client.process = AsyncMock(return_value={"mock": True})
    
    return client
```

## Performance Testing Guidelines

### Benchmarking Best Practices
1. **Warm-up Runs**: Include warm-up iterations
2. **Statistical Analysis**: Calculate mean, median, percentiles
3. **Resource Monitoring**: Track memory and CPU usage
4. **Baseline Comparison**: Compare against known good performance

### Performance Test Template
```python
async def test_performance_template(self, redis_client, clean_redis):
    """Template for performance testing"""
    
    # Setup
    num_operations = 100
    warmup_operations = 10
    
    # Warm-up
    for _ in range(warmup_operations):
        await self._perform_operation(redis_client)
    
    # Actual test
    operation_times = []
    
    for i in range(num_operations):
        start_time = time.time()
        await self._perform_operation(redis_client)
        operation_time = time.time() - start_time
        operation_times.append(operation_time)
    
    # Analysis
    stats = self._calculate_statistics(operation_times)
    self._log_performance_stats("Operation", stats)
    
    # Assertions
    assert stats["mean"] < self.threshold
    assert stats["p95"] < self.threshold * 1.5

def _calculate_statistics(self, times: List[float]) -> Dict:
    """Calculate performance statistics"""
    return {
        "mean": statistics.mean(times),
        "median": statistics.median(times),
        "p95": self._percentile(times, 95),
        "p99": self._percentile(times, 99),
        "max": max(times),
        "min": min(times),
        "std": statistics.stdev(times) if len(times) > 1 else 0
    }

def _percentile(self, data: List[float], p: int) -> float:
    """Calculate percentile"""
    sorted_data = sorted(data)
    index = int(len(sorted_data) * p / 100)
    return sorted_data[min(index, len(sorted_data) - 1)]
```

## Continuous Integration

### GitHub Actions Configuration
```yaml
name: API Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11]
    
    services:
      redis:
        image: redis:alpine
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r tests/requirements.txt
    
    - name: Run integration tests
      run: |
        python tests/run_tests.py integration --coverage
    
    - name: Run performance tests
      run: |
        python tests/run_tests.py performance --verbose
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./reports/coverage.xml
    
    - name: Upload test reports
      uses: actions/upload-artifact@v3
      with:
        name: test-reports-${{ matrix.python-version }}
        path: reports/
```

### Jenkins Pipeline
```groovy
pipeline {
    agent any
    
    stages {
        stage('Test') {
            parallel {
                stage('Integration Tests') {
                    steps {
                        sh 'python tests/run_tests.py integration --coverage'
                    }
                    post {
                        always {
                            publishHTML([
                                allowMissing: false,
                                alwaysLinkToLastBuild: true,
                                keepAll: true,
                                reportDir: 'reports',
                                reportFiles: 'report.html',
                                reportName: 'Integration Test Report'
                            ])
                        }
                    }
                }
                
                stage('Performance Tests') {
                    steps {
                        sh 'python tests/run_tests.py performance --verbose'
                    }
                }
            }
        }
    }
    
    post {
        always {
            junit 'reports/junit.xml'
            publishCoverage adapters: [coberturaAdapter('reports/coverage.xml')]
        }
    }
}
```

## Debugging and Troubleshooting

### Debug Mode
```bash
# Run with detailed logging
pytest --log-cli-level=DEBUG -v

# Run single test with debugger
pytest tests/integration/test_data_flow.py::TestClass::test_method -v -s --pdb

# Profile test execution
pytest --profile tests/integration/test_data_flow.py
```

### Common Issues and Solutions

#### Redis Connection Issues
```python
# Test Redis availability
async def test_redis_connection(self, redis_client):
    try:
        result = await redis_client.ping()
        print("Redis is available")
    except Exception as e:
        print(f"Redis not available: {e}")
        pytest.skip("Redis service not available")
```

#### Mock Service Configuration
```python
# Reset mocks between tests
@pytest.fixture(autouse=True)
def reset_mocks():
    """Automatically reset mocks after each test"""
    yield
    # Reset any global mock state
```

#### Performance Test Failures
```python
# Adjust thresholds for slow systems
@pytest.mark.slow
async def test_performance_on_slow_system(self):
    # Use environment variable for threshold adjustment
    threshold = float(os.getenv('PERFORMANCE_THRESHOLD', '0.1'))
    assert operation_time < threshold
```

## Adding New Test Categories

### 1. Create Test File
```python
# tests/integration/test_new_category.py
import pytest
from conftest import TestConfig

@pytest.mark.new_category
class TestNewCategory:
    async def test_new_feature(self):
        """Test description"""
        # Test implementation
        pass
```

### 2. Update Configuration
```ini
# pytest.ini
markers =
    new_category: New test category
```

### 3. Add to Test Runner
```python
# run_tests.py
elif args.category == "new_category":
    print("🆕 Running NEW CATEGORY tests...")
    category_cmd = cmd + ["-m", "new_category", "-v"] + test_paths
    success = run_command(category_cmd, "New Category Tests")
```

### 4. Update Documentation
- Add category to README.md
- Update developer guide
- Add examples and best practices

## Best Practices

### Test Organization
1. **Clear Naming**: Use descriptive test and method names
2. **Single Responsibility**: Each test should test one thing
3. **Independent Tests**: Tests should not depend on each other
4. **Documentation**: Document complex test logic

### Performance Testing
1. **Realistic Data**: Use production-like data volumes
2. **Statistical Analysis**: Report meaningful statistics
3. **Trend Monitoring**: Track performance over time
4. **Threshold Setting**: Set appropriate performance thresholds

### Error Handling
1. **Graceful Degradation**: Test system behavior with failures
2. **Recovery Testing**: Verify automatic recovery
3. **Fallback Validation**: Test fallback mechanisms
4. **Error Reporting**: Ensure clear error messages

### Mock Implementation
1. **Realistic Behavior**: Mocks should behave like real services
2. **Configurable**: Allow mocking different scenarios
3. **Performance**: Mocks should not significantly slow tests
4. **Validation**: Verify mock interactions

This developer guide provides the foundation for extending and maintaining the comprehensive testing suite. Follow these patterns and practices to ensure high-quality, maintainable tests that provide valuable feedback about system performance and reliability.