# CrewAI Trading System - Test Suite

Comprehensive test suite for the CrewAI Trading Agent System covering unit tests, integration tests, API tests, and end-to-end workflows.

## 📋 Test Overview

The test suite is organized into four main categories:

- **Unit Tests** (`tests/unit/`): Test individual components in isolation
- **Integration Tests** (`tests/integration/`): Test component interactions and workflows
- **End-to-End Tests** (`tests/e2e/`): Test complete trading scenarios
- **API Tests** (`tests/integration/`): Test REST API endpoints

## 🏗️ Test Structure

```
tests/
├── conftest.py          # Shared fixtures and configuration
├── pytest.ini          # Pytest configuration and markers
├── unit/                # Unit tests for individual components
│   ├── test_market_research_analyst.py
│   ├── test_chief_risk_officer.py
│   ├── test_ml_prediction_engineer.py
│   └── test_execution_trader.py
├── integration/         # Integration and API tests
│   ├── test_crew_orchestrator.py
│   ├── test_memory_cache_managers.py
│   ├── test_approval_workflow.py
│   └── test_api_endpoints.py
└── e2e/                 # End-to-end workflow tests
    └── test_workflows.py
```

## 🚀 Quick Start

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-benchmark

# Optional: Redis for integration tests
docker run -d -p 6379:6379 redis:7-alpine
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests only  
pytest -m e2e                     # End-to-end tests only
pytest -m api                     # API tests only

# Run with coverage
pytest --cov=. --cov-report=html
```

### Advanced Test Options

```bash
# Run slow tests (disabled by default)
pytest --run-slow

# Run Redis-dependent tests (disabled by default)
pytest --run-redis

# Run API tests
pytest --run-api

# Run performance tests
pytest --performance

# Parallel test execution
pytest -n 4

# Generate coverage report
pytest --cov=orchestration --cov=agents --cov-report=html

# Run specific test file
pytest tests/unit/test_market_research_analyst.py

# Run specific test
pytest tests/unit/test_market_research_analyst.py::TestMarketResearchAnalyst::test_agent_initialization
```

## 🎯 Test Categories

### Unit Tests

Test individual components with mocked dependencies:

- **Market Research Analyst**: Market data, technical analysis, sentiment analysis
- **Chief Risk Officer**: Risk calculations, compliance checks, position sizing
- **ML Prediction Engineer**: Feature engineering, model training, predictions
- **Execution Trader**: Order execution, market impact, liquidity analysis

```bash
# Run all unit tests
pytest -m unit

# Run specific agent tests
pytest tests/unit/test_market_research_analyst.py
pytest tests/unit/test_chief_risk_officer.py
```

### Integration Tests

Test component interactions and workflows:

- **Crew Orchestrator**: Agent coordination, task chaining, error handling
- **Memory Manager**: Redis operations, context sharing, data persistence
- **Cache Manager**: Caching strategies, TTL management, cache invalidation
- **Approval Workflow**: Request processing, approval logic, escalation
- **API Endpoints**: REST API functionality, request/response validation

```bash
# Run all integration tests
pytest -m integration

# Run specific integration tests
pytest tests/integration/test_crew_orchestrator.py
pytest tests/integration/test_memory_cache_managers.py
```

### End-to-End Tests

Test complete trading scenarios:

- **Market Analysis Workflow**: Full analysis from data gathering to recommendations
- **Trading Workflow**: Signal generation through trade execution
- **Portfolio Rebalancing**: Multi-position optimization and execution
- **Emergency Scenarios**: Market stress handling and risk mitigation
- **Long-Running Analysis**: Persistent workflows with state management

```bash
# Run all E2E tests (may take longer)
pytest -m e2e

# Run specific workflow tests
pytest tests/e2e/test_workflows.py::TestEndToEndWorkflows::test_complete_market_analysis_workflow
```

### API Tests

Test REST API endpoints:

- **Analysis Endpoint**: `/analyze` - Market analysis requests
- **Trading Endpoint**: `/execute-trade` - Trade execution requests
- **Portfolio Endpoint**: `/review-portfolio` - Portfolio review requests
- **Workflows Endpoint**: `/workflows` - Workflow status and management
- **Approvals Endpoint**: `/approvals` - Approval request handling

```bash
# Run API tests (requires API server running)
pytest -m api

# Run specific API tests
pytest tests/integration/test_api_endpoints.py
```

## 📊 Test Markers

Use markers to categorize and select tests:

```bash
# Available markers
pytest -m unit                    # Individual component tests
pytest -m integration             # Component interaction tests
pytest -m e2e                     # Complete workflow tests
pytest -m api                     # REST API tests
pytest -m slow                    # Long-running tests
pytest -m redis                   # Tests requiring Redis
pytest -m ml                      # ML-related tests
pytest -m risk                    # Risk management tests
pytest -m trading                 # Trading execution tests
pytest -m performance             # Performance and stress tests

# Combine markers
pytest -m "unit and not slow"     # Unit tests, exclude slow ones
pytest -m "integration or e2e"    # Either integration or E2E tests
pytest -m "not redis"             # All tests except Redis-dependent ones
```

## 🔧 Test Configuration

### Environment Variables

```bash
# Test environment settings
TESTING=true
REDIS_URL=redis://localhost:6379/15
API_HOST=localhost
API_PORT=8000
API_SECRET_KEY=test_secret_key_123

# Optional test settings
TEST_TIMEOUT=30
TEST_PARALLEL_WORKERS=4
TEST_LOG_LEVEL=INFO
TEST_ENABLE_COVERAGE=false
```

### Redis Setup

Some tests require Redis. Start Redis in a separate terminal:

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Using local Redis (if installed)
redis-server --port 6379
```

### API Testing

For API tests, start the FastAPI server:

```bash
# From the project root
python -m api.server

# Or run the demo
python demo.py
```

## 📈 Performance Testing

### Benchmark Tests

```bash
# Run performance benchmarks
pytest --benchmark-only

# Run with detailed benchmarks
pytest --benchmark-verbose --benchmark-json=benchmark_results.json

# Compare performance across runs
pytest --benchmark-compare=baseline --benchmark-compare-fail=min:5%
```

### Stress Testing

```bash
# Run stress tests (may be resource intensive)
pytest -m performance --run-slow

# Run specific stress tests
pytest tests/e2e/test_workflows.py::TestEndToEndWorkflows::test_end_to_end_system_resilience
```

## 🐛 Debugging Tests

### Verbose Output

```bash
# Show detailed test output
pytest -v

# Show local variables on failure
pytest --tb=long -vv

# Show print statements
pytest -s
```

### Debug Specific Tests

```bash
# Run single test with debug output
pytest -v -s tests/unit/test_market_research_analyst.py::TestMarketResearchAnalyst::test_analyze_market_basic

# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest --pdbcls=IPython.terminal.debugger:Pdb
```

### Test Data Inspection

```bash
# Show test data structure
pytest --collect-only

# Show fixture information
pytest --fixtures

# Show markers
pytest --markers
```

## 📊 Coverage Reports

### Generate Coverage Report

```bash
# Basic coverage
pytest --cov=. --cov-report=term-missing

# HTML coverage report
pytest --cov=. --cov-report=html --cov-report=xml

# Coverage for specific modules
pytest --cov=orchestration --cov=agents --cov-report=html
```

### Coverage Configuration

Coverage is configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["."]
omit = [
    "tests/*",
    "venv/*",
    "__pycache__/*",
    "setup.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Start Redis
      uses: supercharge/redis-github-action@1.4.0
      with:
        redis-version: 7
    
    - name: Run unit tests
      run: pytest -m unit --cov=orchestration --cov-report=xml
    
    - name: Run integration tests  
      run: pytest -m integration --cov=orchestration --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest -m unit --cov=orchestration
        language: system
        pass_filenames: false
        always_run: true
EOF

# Install hooks
pre-commit install
```

## 🛠️ Test Development

### Writing New Tests

1. **Choose the appropriate test type**:
   - Unit tests for individual components
   - Integration tests for component interactions
   - E2E tests for complete workflows

2. **Follow naming conventions**:
   - Test files: `test_component_name.py`
   - Test classes: `TestComponentName`
   - Test methods: `test_method_name`

3. **Use appropriate fixtures**:
   - Create fixtures in `conftest.py` for shared setup
   - Use async fixtures for async operations
   - Mock external dependencies

4. **Add appropriate markers**:
   - `@pytest.mark.unit` for unit tests
   - `@pytest.mark.integration` for integration tests
   - `@pytest.mark.slow` for long-running tests

### Test Structure Example

```python
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

class TestMyComponent:
    """Test cases for MyComponent"""
    
    @pytest.fixture
    def my_component(self):
        """Create component instance"""
        from my_module import MyComponent
        return MyComponent()
    
    @pytest.mark.asyncio
    async def test_basic_functionality(self, my_component):
        """Test basic functionality"""
        # Arrange
        test_input = "test_data"
        expected_output = "processed_test_data"
        
        # Act
        result = await my_component.process(test_input)
        
        # Assert
        assert result == expected_output
    
    @pytest.mark.integration
    @pytest.mark.redis
    async def test_with_redis_integration(self, my_component, mock_redis):
        """Test integration with Redis"""
        # Test with actual Redis operations
        pass
    
    @pytest.mark.slow
    async def test_performance(self, my_component, performance_timer):
        """Test performance characteristics"""
        with performance_timer:
            result = await my_component.heavy_operation()
        assert performance_timer.duration < 5.0  # Should complete in 5 seconds
```

### Mock Best Practices

1. **Mock at the appropriate level**:
   - Mock external APIs and services
   - Don't mock internal business logic
   - Use real implementations for testing core logic

2. **Configure realistic mock behavior**:
   - Return realistic data structures
   - Simulate failure scenarios
   - Mock timing and delays

3. **Clean up mocks**:
   - Use context managers when possible
   - Reset mocks between tests
   - Avoid mock leakage between tests

### Test Data Management

1. **Use factories for test data**:
   ```python
   @pytest.fixture
   def sample_trade_data():
       return {
           'symbol': 'AAPL',
           'side': 'buy',
           'quantity': 100,
           'price': 105.50
       }
   ```

2. **Generate realistic test data**:
   ```python
   def generate_realistic_price_data(length=252):
       import numpy as np
       returns = np.random.normal(0.001, 0.02, length)
       prices = [100.0]
       for ret in returns[1:]:
           prices.append(prices[-1] * (1 + ret))
       return prices
   ```

3. **Parametrize tests for multiple scenarios**:
   ```python
   @pytest.mark.parametrize("side,quantity,expected", [
       ("buy", 100, "buy_order"),
       ("sell", 50, "sell_order"),
   ])
   async def test_order_types(self, side, quantity, expected):
       result = await create_order(side, quantity)
       assert result.type == expected
   ```

## 📝 Test Documentation

### Test Documentation Standards

1. **Document test purpose**:
   - What component/feature is being tested
   - What scenarios are covered
   - What edge cases are tested

2. **Document test dependencies**:
   - External services required
   - Test data dependencies
   - Setup requirements

3. **Document expected behavior**:
   - What the test should pass/fail
   - Performance expectations
   - Error handling expectations

### Example Documentation

```python
class TestRiskAssessment:
    """
    Tests for risk assessment functionality.
    
    Tests cover:
    - Basic risk score calculation
    - Portfolio impact assessment
    - Compliance checking
    - Edge cases (empty portfolios, extreme values)
    
    Dependencies:
    - Requires mock market data
    - Uses simulated portfolio state
    - Tests both individual and portfolio-level risk
    
    Performance:
    - Should complete within 100ms
    - Memory usage should be < 10MB
    """
    
    @pytest.mark.unit
    @pytest.mark.risk
    async def test_basic_risk_calculation(self):
        """Test basic risk score calculation with valid input data."""
        pass
```

## 🚨 Troubleshooting

### Common Issues

1. **Redis connection errors**:
   ```bash
   # Check Redis is running
   redis-cli ping
   
   # Check Redis connection
   python -c "import redis; r = redis.Redis(); print(r.ping())"
   ```

2. **Async test issues**:
   ```python
   # Ensure async tests are properly marked
   @pytest.mark.asyncio
   async def test_async_function():
       pass
   ```

3. **Import errors**:
   ```bash
   # Check Python path
   python -c "import sys; print(sys.path)"
   
   # Ensure project root is in path
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

4. **Memory issues in tests**:
   ```bash
   # Run tests with memory monitoring
   pytest --maxfail=1 --tb=short
   
   # Run fewer tests in parallel
   pytest -n 2
   ```

### Debug Mode

```bash
# Run tests with full debug output
pytest -vvv --tb=long --capture=no

# Drop into debugger on assertion failure
pytest --pdb

# Run tests with logging
pytest --log-level=DEBUG
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [AsyncIO Testing](https://docs.python.org/3/library/asyncio-dev.html#testing)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage Documentation](https://coverage.readthedocs.io/)

## 🤝 Contributing

When adding new tests:

1. Follow the existing test structure and naming conventions
2. Add appropriate markers and documentation
3. Ensure tests are isolated and can run independently
4. Include both success and failure scenarios
5. Test edge cases and error conditions
6. Verify tests work with the CI/CD pipeline

For questions or issues with the test suite, please check existing tests or create new tests following the established patterns.