# Comprehensive End-to-End Testing Framework

A production-ready testing system for trading pipelines and multi-agent systems, providing automated testing for complete data flows, API integrations, performance validation, security assessment, and disaster recovery.

## 📋 Overview

This testing framework covers the entire data pipeline from market data ingestion to trading execution:

```
Market Data → Features → Predictions → Redis → LEAN → Trading
```

## 🏗️ Architecture

### Core Components

1. **Data Pipeline Flow Testing** (`automation/test_data_pipeline_flow.py`)
   - End-to-end pipeline validation
   - Market data → Features → Predictions flow testing
   - Redis caching and LEAN integration verification
   - Data transformation pipeline testing

2. **Agent Coordination Testing** (`agents/test_agent_coordination.py`)
   - Multi-agent communication protocols
   - Decision-making workflow testing
   - Conflict resolution and consensus mechanisms
   - Hierarchical escalation protocols

3. **API Integration Testing** (`api/test_api_integration.py`)
   - Redis API operations
   - Letta agent management APIs
   - Abacus.AI prediction services
   - QuantConnect/LEAN trading APIs
   - GraphQL and WebSocket testing
   - Rate limiting and error handling

4. **Load & Performance Testing** (`load/test_performance_validation.py`)
   - Concurrent request testing
   - Throughput benchmarking
   - Stress testing and resource monitoring
   - Performance regression detection

5. **Disaster Recovery Testing** (`disaster_recovery/test_recovery_validation.py`)
   - Backup and restore procedures
   - Failover scenario testing
   - Data corruption recovery
   - System resilience validation

6. **Security & Vulnerability Testing** (`security/test_vulnerability_assessment.py`)
   - OWASP Top 10 vulnerability scanning
   - Authentication and authorization testing
   - Encryption strength validation
   - Rate limiting and DDoS protection

7. **CI/CD Automation** (`ci_cd/test_automation.py`)
   - Parallel test execution
   - Test orchestration and reporting
   - Artifact management
   - Automated notifications

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Redis server
- Letta API access
- Abacus.AI API credentials
- QuantConnect account
- GitHub repository (for CI/CD)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd testing

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API credentials
```

### Environment Configuration

Create a `.env` file with the following variables:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=

# Letta Configuration
LETTA_BASE_URL=https://api.letta.com/v1
LETTA_API_KEY=your_letta_api_key

# Abacus.AI Configuration
ABACUS_API_URL=https://api.abacus.ai
ABACUS_API_KEY=your_abacus_api_key

# QuantConnect Configuration
QUANTCONNECT_API_KEY=your_qc_api_key
QUANTCONNECT_USER_ID=your_qc_user_id

# Test Configuration
TEST_MODE=mock  # Options: mock, live
PARALLEL_WORKERS=4
TEST_TIMEOUT=300
```

## 🧪 Running Tests

### Using Make Commands

```bash
# Run all tests
make test-all

# Run specific test suites
make test-pipeline      # Data pipeline flow tests
make test-agents        # Agent coordination tests
make test-api          # API integration tests
make test-load         # Load and performance tests
make test-recovery     # Disaster recovery tests
make test-security     # Security assessment tests
make test-automation   # CI/CD automation tests

# Run tests with coverage
make test-coverage

# Run tests in parallel
make test-parallel

# Run specific test categories
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-e2e         # End-to-end tests only

# Generate reports
make report-html       # HTML coverage report
make report-xml        # JUnit XML reports
make report-json       # JSON test results
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run with specific markers
pytest -m "pipeline"           # Pipeline tests only
pytest -m "integration"        # Integration tests only
pytest -m "security"           # Security tests only

# Run with coverage
pytest --cov=. --cov-report=html

# Run parallel tests
pytest -n auto

# Run specific test file
pytest automation/test_data_pipeline_flow.py

# Run with verbose output
pytest -v

# Run specific test
pytest -v -k "test_end_to_end_pipeline"
```

### Using Locust for Load Testing

```bash
# Run load tests
locust -f load/test_performance_validation.py --host=http://localhost

# Run with custom parameters
locust -f load/test_performance_validation.py --host=http://localhost \
    --headless -u 10 -r 2 -t 300s
```

## 📊 Test Reports

### Coverage Reports

- **HTML Report**: `htmlcov/index.html`
- **XML Report**: `coverage.xml`
- **Terminal Output**: Real-time coverage display

### Performance Reports

- **Load Test Results**: `load-test-results/`
- **Performance Metrics**: `performance-metrics/`
- **Benchmark Comparisons**: `benchmarks/`

### Security Reports

- **Vulnerability Scan**: `security-scan-results/`
- **Security Metrics**: `security-metrics.json`
- **Compliance Report**: `compliance-report.html`

## 🔧 Configuration

### Pytest Configuration (`pytest.ini`)

- Test discovery patterns
- Custom markers and categories
- Timeout settings
- Coverage thresholds
- Parallel execution settings

### Test Configuration (`config.py`)

- Service endpoints and credentials
- Performance thresholds
- Test data settings
- Security scanning parameters

## 📈 Monitoring and Alerts

### CI/CD Integration

The framework includes GitHub Actions workflows for:
- Automated test execution on push/PR
- Parallel test execution across multiple runners
- Automated reporting and notifications
- Performance regression detection
- Security vulnerability alerts

### Metrics Collection

- Test execution times
- Coverage metrics
- Performance benchmarks
- Security scan results
- Failure analysis and trending

## 🛠️ Development

### Adding New Tests

1. **Create test files** in appropriate directories:
   - `automation/` - Data pipeline tests
   - `agents/` - Agent coordination tests
   - `api/` - API integration tests
   - `load/` - Performance and load tests
   - `disaster_recovery/` - Recovery and backup tests
   - `security/` - Security and vulnerability tests
   - `ci_cd/` - CI/CD and automation tests

2. **Use appropriate markers**:
   ```python
   import pytest
   
   @pytest.mark.pipeline
   @pytest.mark.integration
   async def test_new_feature():
       # Test implementation
       pass
   ```

3. **Follow naming conventions**:
   - Test files: `test_*.py`
   - Test functions: `test_*`
   - Test classes: `Test*`

### Custom Utilities

The `utils/helpers.py` module provides:
- Mock data generators
- Test fixtures
- Service client mocks
- Timing and profiling utilities
- Cleanup and teardown helpers

## 🐛 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Start Redis server
   redis-server
   
   # Check Redis status
   redis-cli ping
   ```

2. **API Authentication Errors**
   ```bash
   # Verify API keys
   echo $LETTA_API_KEY
   echo $ABACUS_API_KEY
   ```

3. **Performance Test Timeouts**
   ```bash
   # Increase timeout in pytest.ini
   timeout = 600
   ```

4. **Parallel Test Failures**
   ```bash
   # Reduce parallel workers
   pytest -n 2
   ```

### Debug Mode

```bash
# Run with debug logging
pytest --log-cli-level=DEBUG -v

# Run specific test with pdb
pytest --pdb -k "test_end_to_end_pipeline"

# Run with verbose output
pytest -vv -s
```

## 📚 API Reference

### Test Configuration

```python
from testing.config import TestConfig, ServiceEndpoints

config = TestConfig()
endpoints = ServiceEndpoints()
```

### Mock Services

```python
from testing.utils.helpers import MockRedisClient, MockLettaClient

mock_redis = MockRedisClient()
mock_letta = MockLettaClient()
```

### Performance Testing

```python
from testing.utils.helpers import PerformanceTimer, ConcurrentExecutor

timer = PerformanceTimer()
executor = ConcurrentExecutor(max_workers=4)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

### Test Guidelines

- Write descriptive test names
- Include docstrings for complex tests
- Use appropriate test markers
- Maintain test isolation
- Clean up resources after tests

## 📄 License

This testing framework is part of the trading pipeline project and follows the same licensing terms.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review test logs and output
3. Create an issue with:
   - Test environment details
   - Error messages and logs
   - Steps to reproduce
   - Expected vs actual behavior

---

**Note**: This framework requires proper API credentials and service access for full functionality. Use mock mode for development and testing without live services.