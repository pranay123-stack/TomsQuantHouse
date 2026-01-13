# API Integration Testing Suite

This comprehensive testing suite provides end-to-end testing for the Redis-QuantConnect-Abacus.AI-LEAN data pipeline with Letta agent integration.

## Overview

The test suite validates the complete data flow from market data ingestion through prediction generation to trading algorithm consumption, with comprehensive error handling and performance benchmarking.

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────┐
│   QuantConnect  │───▶│  Market Data │───▶│   Features  │───▶│   Abacus.AI │───▶│Pred. │
│   (Market Data) │    │    Cache     │    │ (Engineering)│    │(Predictions)│    │Cache │
└─────────────────┘    └──────────────┘    └─────────────┘    └─────────────┘    └──────┘
                                │                                                             │
                                ▼                                                             ▼
                       ┌──────────────┐                                              ┌─────────────┐
                       │    Redis     │                                              │    LEAN     │
                       │    Cache     │                                              │(Trading Algo)│
                       └──────────────┘                                              └─────────────┘
                                │                                                             │
                                ▼                                                             ▼
                       ┌──────────────┐                                              ┌─────────────┐
                       │    Letta     │                                              │  Decisions  │
                       │   (Agent)    │                                              │   & Trades  │
                       └──────────────┘                                              └─────────────┘
```

## Test Structure

```
tests/
├── conftest.py                 # Test configuration and fixtures
├── pytest.ini                 # Pytest configuration
├── integration/                # Integration tests
│   ├── test_health_checks.py      # Service health monitoring
│   ├── test_data_flow.py          # Redis-QuantConnect-Abacus.AI flow
│   ├── test_letta_memory.py       # Agent memory persistence
│   └── test_error_handling.py     # Error handling & fallbacks
├── performance/                # Performance benchmarks
│   └── test_prediction_caching.py # Cache performance tests
├── e2e/                       # End-to-end pipeline tests
│   └── test_complete_pipeline.py  # Full pipeline validation
├── fixtures/                  # Test data and utilities
├── mocks/                     # Mock implementations
├── reports/                   # Test reports and coverage
└── docs/                      # Test documentation
```

## Test Categories

### 1. Health Checks (`test_health_checks.py`)
Validates all services are operational:
- **Redis**: Connection, memory usage, latency
- **Letta**: API health, agent creation
- **Abacus.AI**: Model status, prediction latency
- **QuantConnect**: API connectivity, data freshness

### 2. Data Flow Integration (`test_data_flow.py`)
Tests the core data pipeline:
- Market data → Redis caching
- Feature computation and caching
- Prediction generation and caching
- Cache retrieval performance
- Multi-symbol processing
- Cache invalidation and expiration

### 3. Performance Benchmarking (`test_prediction_caching.py`)
Comprehensive performance tests:
- Cache hit/miss performance
- Concurrent access patterns
- Memory efficiency analysis
- TTL expiration behavior
- Cluster simulation

### 4. End-to-End Pipeline (`test_complete_pipeline.py`)
Complete workflow validation:
- Single symbol pipeline execution
- Multi-symbol parallel processing
- Cache consistency verification
- Stress testing with high load
- Error recovery scenarios

### 5. Letta Agent Memory (`test_letta_memory.py`)
Agent persistence testing:
- Memory creation and retrieval
- Multi-session persistence
- Memory size limits and eviction
- Backup and restore capabilities
- Concurrent access handling
- Performance benchmarks

### 6. Error Handling (`test_error_handling.py`)
Robustness testing:
- Service failure fallbacks
- Cascade failure recovery
- Timeout handling
- Rate limiting scenarios
- Data validation
- Circuit breaker patterns

## Configuration

### Environment Variables
```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Letta Configuration  
LETTA_BASE_URL=http://localhost:8283
LETTA_API_KEY=your-letta-api-key

# Abacus.AI Configuration
ABACUS_API_URL=https://api.abacus.ai
ABACUS_API_KEY=your-abacus-api-key

# QuantConnect Configuration
QUANTCONNECT_BASE_URL=https://www.quantconnect.com/api
QUANTCONNECT_API_KEY=your-quantconnect-api-key
```

### Performance Thresholds
```python
# Cache Operations
MAX_CACHE_RETRIEVAL_TIME = 0.1  # 100ms
PREDICTION_CACHE_TTL = 300      # 5 minutes
FEATURE_CACHE_TTL = 3600        # 1 hour

# Service Operations
MAX_PREDICTION_TIME = 5.0       # 5 seconds
MAX_HEALTH_CHECK_TIME = 2.0     # 2 seconds

# Test Data
TEST_SYMBOLS = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']
TEST_START_DATE = '2023-01-01'
TEST_END_DATE = '2023-12-31'
```

## Running Tests

### Prerequisites
```bash
pip install pytest pytest-asyncio pytest-cov httpx aioredis
```

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m integration        # Integration tests
pytest -m performance        # Performance benchmarks  
pytest -m e2e               # End-to-end tests

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/integration/test_health_checks.py
```

### Test Markers
- `integration`: Integration tests between services
- `performance`: Performance benchmarking tests
- `e2e`: End-to-end pipeline tests
- `slow`: Tests taking longer than 5 seconds
- `redis`: Tests requiring Redis service
- `letta`: Tests requiring Letta service
- `abacus`: Tests requiring Abacus.AI service
- `quantconnect`: Tests requiring QuantConnect service
- `live`: Tests using real services (not mocks)
- `mock`: Tests using mocks/fixtures

### Example Commands
```bash
# Quick smoke tests (no slow tests)
pytest -m "not slow"

# Full integration test suite
pytest -m integration --tb=short

# Performance benchmarking
pytest -m performance -v

# Health check validation
pytest tests/integration/test_health_checks.py -v

# Complete pipeline test
pytest tests/e2e/test_complete_pipeline.py -v

# Run with detailed output
pytest -v --tb=long --durations=10
```

## Mock Services

The test suite uses comprehensive mocks when real services aren't available:

### Redis Mock
- Simulates Redis operations when Redis is unavailable
- Tracks cache operations for verification
- Provides realistic latency simulation

### Letta Mock
- Agent creation and memory management
- Conversation persistence simulation
- Concurrent access handling

### Abacus.AI Mock
- Prediction generation with configurable responses
- Rate limiting simulation
- Error condition handling

### QuantConnect Mock
- Market data provision
- Historical and real-time data simulation
- API error handling

## Test Data Management

### Sample Data
- **Market Data**: OHLCV data for major symbols
- **Features**: Technical indicators (SMA, RSI, MACD, etc.)
- **Predictions**: BUY/SELL/HOLD decisions with confidence scores
- **Agent Memory**: Conversation histories and user preferences

### Test Fixtures
- Clean Redis database setup/teardown
- Mock service configuration
- Sample data generation
- Performance baseline establishment

## Performance Metrics

The test suite tracks and validates:

### Cache Performance
- **Hit Rate**: Percentage of cache hits vs misses
- **Latency**: Average, median, 95th, 99th percentile times
- **Throughput**: Operations per second
- **Memory Efficiency**: Cache size vs data volume

### Pipeline Performance
- **End-to-End Time**: Complete pipeline execution time
- **Component Times**: Individual step performance
- **Scalability**: Performance with increased load
- **Resource Usage**: Memory and CPU utilization

### Service Availability
- **Uptime**: Service availability percentage
- **Recovery Time**: Time to recover from failures
- **Error Rate**: Frequency of service errors

## Error Scenarios Tested

### Service Failures
- Redis connection loss
- Abacus.AI service unavailability
- QuantConnect API errors
- Network timeouts

### Data Issues
- Invalid market data formats
- Corrupted cache entries
- Malformed predictions
- Missing required fields

### Load Conditions
- High concurrent access
- Rate limiting responses
- Memory pressure scenarios
- Extended operation times

## Reporting and Analysis

### Test Reports
- JUnit XML format for CI/CD integration
- HTML coverage reports
- Performance benchmark results
- Failure analysis and recommendations

### Continuous Monitoring
- Health check dashboards
- Performance trend analysis
- Error rate monitoring
- Cache hit rate tracking

## Best Practices

### Test Development
1. **Isolation**: Each test should be independent
2. **Cleanup**: Always clean up test data and resources
3. **Realism**: Use realistic data volumes and patterns
4. **Documentation**: Clear test descriptions and assertions

### Performance Testing
1. **Baseline**: Establish performance baselines
2. **Trends**: Monitor performance over time
3. **Thresholds**: Set appropriate performance thresholds
4. **Real-world**: Test with production-like data volumes

### Error Handling
1. **Graceful Degradation**: System should work with partial failures
2. **Recovery**: Automatic recovery when services return
3. **Fallbacks**: Reasonable default behaviors
4. **Monitoring**: Clear error reporting and logging

## Troubleshooting

### Common Issues

#### Redis Connection Failed
```bash
# Start Redis locally
redis-server

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

#### Mock Services Not Working
- Ensure all dependencies are installed
- Check environment variable configuration
- Verify mock service implementations

#### Performance Test Failures
- Review performance thresholds in configuration
- Check system resources (CPU, memory)
- Analyze detailed timing reports

### Debug Mode
```bash
# Run with debug output
pytest --log-cli-level=DEBUG -v

# Run single test with full output
pytest tests/integration/test_data_flow.py::TestDataFlowIntegration::test_market_data_to_redis_flow -v -s
```

## Extensions and Customization

### Adding New Tests
1. Create test file in appropriate directory
2. Add test markers to pytest.ini
3. Include comprehensive documentation
4. Add performance benchmarks if applicable

### Custom Mock Services
1. Implement service-specific mocks
2. Add realistic delay simulation
3. Include error scenario handling
4. Document mock capabilities and limitations

### Performance Tuning
1. Adjust timeout values for slow systems
2. Modify test data volumes for resource constraints
3. Configure parallel execution for faster testing
4. Set appropriate performance thresholds

## CI/CD Integration

### GitHub Actions Example
```yaml
name: API Integration Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:alpine
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run integration tests
      run: |
        pytest -m integration --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

This testing suite provides comprehensive validation of the entire data pipeline while maintaining high performance standards and robust error handling capabilities.