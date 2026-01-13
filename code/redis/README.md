# Redis Infrastructure for Trading Framework

This directory contains a complete Redis infrastructure setup for a trading framework, including database separation, pub/sub functionality, and comprehensive monitoring.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- 2GB+ available RAM

### 1. Start Redis Infrastructure

```bash
cd code/redis
docker-compose up -d
```

This will start:
- Redis server with multiple database support
- Redis Commander for web-based Redis management

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Test the Setup

```bash
# Test Redis connection
python redis_client.py

# Test Pub/Sub functionality
python pubsub_client.py

# Run health check
python health_check.py
```

## 📊 Database Architecture

The Redis infrastructure uses separate databases for different data types:

### Database Separation
- **db0 (Predictions Cache)**: ML model predictions, trading signals, market analysis
- **db1 (Agent Memory)**: AI agent states, conversation history, decision logs
- **db2 (Graph State)**: Trading relationships, market data graphs, entity connections
- **db3 (Entity Memory)**: User profiles, market instruments, metadata

### Storage Patterns
- **Keys**: Uses descriptive prefixes (`prediction:`, `agent:`, `node:`, `entity:`)
- **TTL**: Time-based expiration for different data types
- **Serialization**: Pickle for complex objects, JSON for simple data

## 🐍 Python Client Usage

### Basic Redis Client

```python
from redis_client import TradingRedisClient

# Initialize client
redis_client = TradingRedisClient()

# Cache predictions
prediction = {
    "model": "LSTM_v2",
    "prediction": "BUY",
    "confidence": 0.85,
    "price_target": 150.25
}
redis_client.cache_prediction("BTCUSDT_2025_11_02", prediction)

# Store agent memory
agent_memory = {
    "state": "active",
    "strategy": "momentum",
    "positions": ["BTCUSDT", "ETHUSDT"]
}
redis_client.store_agent_memory("trading_agent_1", agent_memory)
```

### Pub/Sub Client

```python
from pubsub_client import TradingPubSub

# Initialize Pub/Sub client
pubsub = TradingPubSub()

# Define signal handler
def handle_signal(signal_data):
    print(f"Received: {signal_data['signal_type']} {signal_data['symbol']}")

# Subscribe to trade signals
subscription = pubsub.subscribe_to_trade_signals(handle_signal, 'BTCUSDT')

# Publish trading signal
signal = {
    'signal_type': 'BUY',
    'symbol': 'BTCUSDT',
    'price': 45000,
    'timestamp': datetime.now().isoformat()
}
pubsub.publish_trade_signal(signal)
```

## 📈 Monitoring & Health Checks

### Run Health Check

```bash
# Single health check
python health_check.py

# Export health report
python health_check.py --export health_report.json

# Continuous monitoring
python health_check.py --monitor --check-interval 300
```

### Health Check Features
- Connection status and response time
- Memory usage and fragmentation
- Database statistics and key counts
- Performance metrics (hit ratios, ops/sec)
- Persistence status (RDB/AOF)
- System resource monitoring

### Alert System
- Configurable alert thresholds
- Email notifications for critical issues
- Duplicate alert prevention
- Log-based alerting

## 🔧 Configuration

### Redis Configuration (`redis.conf`)
- Multiple database support (16 databases)
- Memory management and LRU eviction
- Persistence configuration (RDB + AOF)
- Keyspace event notifications for pub/sub

### Docker Compose Configuration
```yaml
services:
  redis:
    image: redis:7.2-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    environment:
      - REDIS_PASSWORD=trading_framework_2025
```

### Environment Variables
Copy `.env.example` to `.env` and customize:
- Redis connection settings
- Database naming
- Monitoring thresholds
- Alert configurations

## 📚 API Reference

### TradingRedisClient Methods

#### Predictions (db0)
- `cache_prediction(prediction_id, prediction_data, ttl)`
- `get_prediction(prediction_id)`
- `cache_trading_signals(market_pair, signals, ttl)`
- `get_trading_signals(market_pair)`

#### Agent Memory (db1)
- `store_agent_memory(agent_id, memory_data, ttl)`
- `get_agent_memory(agent_id)`
- `store_conversation_history(agent_id, conversation, ttl)`
- `get_conversation_history(agent_id)`

#### Graph State (db2)
- `store_graph_node(node_id, node_data, ttl)`
- `get_graph_node(node_id)`
- `store_graph_edge(from_node, to_node, edge_data, ttl)`
- `get_adjacent_nodes(node_id)`

#### Entity Memory (db3)
- `store_entity_data(entity_id, entity_type, entity_data, ttl)`
- `get_entity_data(entity_id)`
- `get_entities_by_type(entity_type)`

#### Utilities
- `delete_key(key, db)`
- `clear_database(db)`
- `get_db_info(db)`
- `ping()`

### TradingPubSub Methods

#### Publishing
- `publish_trade_signal(signal_data)`
- `publish_market_update(market_data)`
- `publish_alert(alert_data)`
- `publish_strategy_update(strategy_data)`

#### Subscribing
- `subscribe_to_trade_signals(callback, symbol)`
- `subscribe_to_market_updates(callback, symbol)`
- `subscribe_to_alerts(callback)`
- `subscribe_to_strategy_updates(callback)`

#### Utilities
- `unsubscribe(subscription_id)`
- `get_subscription_count()`
- `ping()`

## 🔍 Monitoring Dashboard

Access Redis Commander web interface:
- URL: http://localhost:8081
- Purpose: Visual Redis management and monitoring

Features:
- Browse all databases
- View key/value pairs
- Execute Redis commands
- Monitor connection statistics

## 🛠️ Development

### Adding New Data Types
1. Choose appropriate database based on data type
2. Follow naming conventions with prefixes
3. Set appropriate TTL values
4. Add corresponding methods to TradingRedisClient

### Custom Pub/Sub Channels
1. Define new channel names in `.env`
2. Add publish/subscribe methods to TradingPubSub
3. Update documentation

### Health Check Extensions
1. Add new check methods to RedisHealthMonitor
2. Integrate into `run_full_health_check()`
3. Configure alert thresholds

## 📊 Performance Optimization

### Memory Management
- Use appropriate TTL values for different data types
- Monitor memory usage with health checks
- Consider Redis clustering for high availability

### Connection Pooling
- The Python client uses connection pooling by default
- Configure pool size based on application needs

### Serialization
- Pickle for complex objects (Python-specific)
- JSON for simple data structures
- Consider message size limits for pub/sub

## 🔒 Security Considerations

### Authentication
- Redis password required in production
- Use environment variables for sensitive data
- Consider TLS encryption for external connections

### Access Control
- Limit Redis exposure to internal networks
- Use Redis ACL for granular permissions
- Monitor connection attempts

### Data Protection
- Regular backup procedures
- Monitor for unauthorized access
- Implement data retention policies

## 🐛 Troubleshooting

### Common Issues

#### Connection Refused
```bash
# Check Redis container status
docker ps

# Check Redis logs
docker logs trading-redis

# Test connection
redis-cli -h localhost -p 6379 -a trading_framework_2025 ping
```

#### Memory Issues
```bash
# Monitor memory usage
python health_check.py

# Check keyspace
redis-cli -h localhost -p 6379 -a trading_framework_2025 info keyspace

# Clear specific database
python -c "from redis_client import TradingRedisClient; client = TradingRedisClient(); client.clear_database(0)"
```

#### Pub/Sub Issues
```bash
# Test pub/sub manually
redis-cli -h localhost -p 6379 -a trading_framework_2025
127.0.0.1:6379> subscribe trade_signals
127.0.0.1:6379> publish trade_signals '{"test": "data"}'
```

### Debug Mode
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python health_check.py
```

## 📈 Scaling Considerations

### Horizontal Scaling
- Redis Cluster for automatic sharding
- Master-replica setup for read scalability
- Consider Redis Sentinel for high availability

### Vertical Scaling
- Increase Redis memory allocation
- Optimize data structures and TTL
- Monitor performance metrics

### Load Balancing
- Use Redis connection pooling
- Implement circuit breaker patterns
- Monitor connection saturation

## 📝 Examples

See example scripts in this directory:
- `redis_client.py` - Complete usage examples
- `pubsub_client.py` - Real-time communication examples
- `health_check.py` - Monitoring and alerting examples

## 🤝 Contributing

1. Follow existing code patterns and naming conventions
2. Add comprehensive documentation for new features
3. Include health checks for critical functionality
4. Update tests for new methods
5. Maintain backward compatibility when possible

## 📄 License

This Redis infrastructure setup is provided as-is for the trading framework project.

## 🔗 Related Documentation

- [Redis Documentation](https://redis.io/documentation)
- [Redis Python Client](https://redis-py.readthedocs.io/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)