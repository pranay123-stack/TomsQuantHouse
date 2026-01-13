# Letta REST API Integration

Comprehensive Letta REST API integration with advanced features for memory queries, agent management, trading insights, and dashboard integration.

## 🚀 Features

### 1. Comprehensive Letta API Client
- **Advanced Memory Management**: Query, search, and optimize agent memory with intelligent algorithms
- **Agent Management**: Create, update, and manage AI agents with role-based capabilities
- **Trading Pattern Learning**: Automated pattern discovery and validation from trade outcomes
- **Performance Monitoring**: Real-time metrics collection and historical analysis
- **Caching & Rate Limiting**: Built-in caching and intelligent rate limiting for optimal performance

### 2. Advanced Memory Query System
- **Intelligent Search**: Multiple search strategies (semantic, pattern, temporal, performance)
- **Query Optimization**: Advanced filtering, sorting, and relevance scoring
- **Memory Analytics**: Comprehensive usage statistics and optimization recommendations
- **Pattern Recognition**: Automatic discovery of trading patterns and market correlations

### 3. Trading Workflows & Insights
- **Automated Trade Analysis**: Comprehensive workflow for trade outcome analysis
- **Strategy Evolution**: Automated strategy optimization based on performance data
- **Risk Assessment**: Real-time risk evaluation and mitigation recommendations
- **Market Learning**: Adaptive learning from market conditions and regimes
- **Performance Analytics**: Deep insights into trading performance and patterns

### 4. Agent Communication & Coordination
- **Multi-Agent Communication**: Advanced messaging system with priority routing
- **Memory Sharing**: Secure inter-agent memory sharing with access controls
- **Coordination Requests**: Automated coordination for complex multi-agent tasks
- **Risk Alert Distribution**: Intelligent risk alert routing to relevant agents
- **Communication Analytics**: Comprehensive communication patterns and performance metrics

### 5. Backup & Restore System
- **Multiple Backup Types**: Full, incremental, differential, selective, and archival backups
- **Compression & Encryption**: Built-in compression with optional encryption support
- **Backup Validation**: Integrity checking and corruption detection
- **Flexible Restore Modes**: Merge, replace, append, and validate-only restore options
- **Automated Scheduling**: Cron-based backup scheduling with retention policies

### 6. Performance Monitoring & Analytics
- **Real-time Metrics**: System and agent-level performance monitoring
- **Alert Management**: Intelligent threshold-based alerting with cooldown periods
- **Trend Analysis**: Predictive analytics and anomaly detection
- **Optimization Recommendations**: AI-driven performance optimization suggestions
- **Comprehensive Dashboards**: Real-time performance dashboards and reporting

## 📦 Installation

### Prerequisites
- Python 3.8+
- Letta server running (default: http://localhost:8283)
- PostgreSQL database (for Letta persistence)
- Redis server (optional, for caching and archival storage)

### Dependencies
```bash
pip install -r requirements.txt
```

### Core Dependencies
- `requests>=2.31.0` - HTTP client for API communication
- `aiohttp>=3.8.5` - Async HTTP client for concurrent operations
- `pydantic>=2.4.0` - Data validation and serialization
- `redis>=5.0.0` - Redis client for caching and storage
- `numpy>=1.24.0` - Numerical computing for analytics
- `pandas>=2.0.0` - Data analysis and manipulation
- `fastapi>=0.104.0` - API framework for web integration
- `sqlalchemy>=2.0.0` - Database ORM for backup management
- `tenacity>=8.2.0` - Retry mechanism for robust operations

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Letta Integration API                       │
│                    (Main Entry Point)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼────────┐ ┌─────▼─────┐ ┌───────▼────────┐
│ Memory Manager │ │ Workflows │ │ Communication  │
│                │ │           │ │                 │
│ • Block Mgmt   │ │ • Trade   │ │ • Agent Registry│
│ • Intelligent  │ │   Analysis│ │ • Message Router│
│   Search       │ │ • Strategy│ │ • Memory Share │
│ • Analytics    │ │   Evolve  │ │ • Coordination │
└────────────────┘ └───────────┘ └─────────────────┘
        │
┌───────▼────────┐ ┌───────────┐ ┌───────────────┐
│ Backup Manager │ │ Monitor   │ │   Letta API   │
│                │ │           │ │               │
│ • Full/Inc.    │ │ • Metrics │ │ • Agents      │
│ • Restore      │ │ • Alerts  │ │ • Memory      │
│ • Validation   │ │ • Trends  │ │ • Messages    │
└────────────────┘ └───────────┘ └───────────────┘
```

## 🚀 Quick Start

### Basic Usage

```python
from letta_integration_api import create_trading_integration

# Configuration
letta_config = {
    "base_url": "http://localhost:8283",
    "api_key": "your-secret-api-key"
}

redis_config = {
    "host": "localhost",
    "port": 6379,
    "db": 1
}

# Create trading integration
api = create_trading_integration(letta_config, redis_config)

# Start the system
api.start()

# Create memory block
block_id = api.create_memory_block(
    agent_id="trading_strategist",
    block_type="trading_strategy",
    title="Moving Average Strategy",
    content="Strategy details...",
    priority="high",
    tags=["strategy", "moving_average"]
)

# Search memory intelligently
results = api.search_memory_intelligent(
    agent_id="trading_strategist",
    query="strategy performance",
    search_options={"limit": 10}
)

# Get trading opportunities
opportunities = api.get_trading_opportunities("trading_strategist", confidence_threshold=0.7)

# Stop the system
api.stop()
```

### Advanced Memory Management

```python
from letta_integration_api import LettaIntegrationAPI
from memory_manager import create_memory_manager

# Initialize components
api = LettaIntegrationAPI(letta_config)
memory_manager = create_memory_manager(api.client)

# Get comprehensive analytics
analytics = memory_manager.get_comprehensive_analytics("trading_strategist")
print(f"Memory utilization: {analytics.utilization_percentage:.1%}")

# Intelligent memory search
results = memory_manager.intelligent_search(
    agent_id="trading_strategist",
    query="volume confirmation patterns",
    context={"market_regime": "bull_trending"}
)

# Optimize memory
report = memory_manager.optimize_memory_intelligent(
    agent_id="trading_strategist",
    strategy="hybrid"
)
print(f"Optimized {report.blocks_processed} blocks")
```

### Trading Workflows

```python
from trading_workflows import create_trading_workflows

# Initialize workflows
workflows = create_trading_workflows(api.client)

# Record trade outcome
trade_event = TradeEvent(
    trade_id="trade_001",
    symbol="AAPL",
    action="buy",
    quantity=100,
    entry_price=150.00,
    exit_price=155.50,
    pnl=5.50,
    strategy="bullish_breakout",
    confidence=0.8,
    outcome="win",
    timestamp=datetime.now(),
    metadata={}
)

# Execute trade analysis workflow
workflow_id = workflows.execute_trade_analysis_workflow("trading_strategist", trade_event)

# Get comprehensive performance analysis
performance = workflows.get_comprehensive_performance_analysis("trading_strategist", period_days=30)
print(f"Win rate: {performance['basic_metrics']['win_rate']:.1%}")
```

### Agent Communication

```python
from agent_communication import create_communication_hub

# Initialize communication hub
hub = create_communication_hub(api.client)

# Register agents
hub.register_agent(
    agent_id="trading_strategist",
    name="Trading Strategist",
    role=AgentRole.STRATEGIST,
    capabilities=[
        AgentCapability("strategy_development", "Develop trading strategies", 5, ["strategy"]),
        AgentCapability("pattern_recognition", "Identify trading patterns", 4, ["patterns"])
    ]
)

# Send message between agents
message_id = hub.send_direct_message(
    sender_agent_id="trading_strategist",
    receiver_agent_id="risk_manager",
    subject="High Confidence Setup",
    content="Identified high-confidence breakout pattern",
    priority=MessagePriority.HIGH
)

# Share memory blocks
share_id = hub.share_memory_blocks(
    sharing_agent_id="trading_strategist",
    recipient_agent_id="market_analyst",
    memory_block_ids=["block_1", "block_2"],
    access_level=AccessLevel.READ_ONLY,
    duration_hours=24
)
```

### Backup and Restore

```python
from backup_restore import create_backup_manager

# Initialize backup manager
backup_manager = create_backup_manager(api.client, "./backups")

# Create full backup
backup_id = backup_manager.create_backup(
    agent_id="trading_strategist",
    backup_type=BackupType.FULL,
    description="Daily backup",
    tags=["daily", "full"]
)

# List available backups
backups = backup_manager.list_backups(agent_id="trading_strategist")
print(f"Found {len(backups)} backups")

# Restore backup
restore_id = backup_manager.restore_backup(
    backup_id=backup_id,
    agent_id="trading_strategist",
    restore_mode=RestoreMode.MERGE
)
```

### Performance Monitoring

```python
from performance_monitor import create_performance_monitor

# Initialize performance monitor
monitor = create_performance_monitor(api.client, monitoring_interval=30)

# Start monitoring
monitor.start_monitoring()

# Wait for metrics collection
await asyncio.sleep(60)

# Get dashboard data
dashboard = monitor.get_dashboard_data()
print(f"System health: {dashboard['performance_summary']['system_health']}")

# Get optimization recommendations
recommendations = monitor.get_optimization_recommendations()
for rec in recommendations:
    print(f"Recommendation: {rec['title']} - {rec['description']}")
```

## 📚 API Reference

### Core Classes

#### LettaAPIClient
Main API client for Letta server communication.

**Methods:**
- `get_agents()` - Get all agents
- `get_agent_memory(agent_id)` - Get agent memory blocks
- `search_memory(...)` - Search memory with filters
- `create_trading_pattern(...)` - Create trading pattern
- `record_trade_outcome(...)` - Record trade outcome
- `create_backup(...)` - Create backup
- `health_check()` - System health check

#### AdvancedMemoryManager
Advanced memory management with intelligent operations.

**Methods:**
- `intelligent_search(...)` - Intelligent memory search
- `get_comprehensive_analytics(...)` - Memory analytics
- `optimize_memory_intelligent(...)` - Memory optimization
- `generate_memory_insights(...)` - Generate insights

#### TradingWorkflows
Automated trading workflow engine.

**Methods:**
- `execute_trade_analysis_workflow(...)` - Trade analysis
- `execute_strategy_evolution_workflow(...)` - Strategy evolution
- `execute_risk_assessment_workflow(...)` - Risk assessment
- `get_comprehensive_performance_analysis(...)` - Performance analysis

#### AgentCommunicationHub
Multi-agent communication and coordination system.

**Methods:**
- `register_agent(...)` - Register agent
- `send_direct_message(...)` - Send message
- `broadcast_message(...)` - Broadcast message
- `share_memory_blocks(...)` - Share memory

#### BackupManager
Comprehensive backup and restore system.

**Methods:**
- `create_backup(...)` - Create backup
- `restore_backup(...)` - Restore backup
- `list_backups(...)` - List backups
- `validate_backup(...)` - Validate backup

#### PerformanceMonitor
Real-time performance monitoring and analytics.

**Methods:**
- `start_monitoring()` - Start monitoring
- `get_dashboard_data()` - Get dashboard data
- `analyze_trends(...)` - Trend analysis
- `get_optimization_recommendations(...)` - Get recommendations

### LettaIntegrationAPI
Main integration API combining all functionality.

**Methods:**
- `start()` / `stop()` - System lifecycle
- `create_memory_block(...)` - Create memory block
- `search_memory_intelligent(...)` - Intelligent search
- `create_trading_pattern(...)` - Create pattern
- `record_trade_outcome(...)` - Record trade
- `execute_trade_analysis_workflow(...)` - Execute workflow
- `send_message(...)` - Send message
- `create_backup(...)` - Create backup
- `get_system_status()` - Get system status

## 🔧 Configuration

### Letta Configuration
```python
letta_config = {
    "base_url": "http://localhost:8283",
    "api_key": "your-secret-api-key",
    "session_timeout": 30,
    "max_retries": 3,
    "cache_ttl": 300,
    "rate_limit": 10.0,
    "enable_caching": True,
    "enable_monitoring": True
}
```

### Redis Configuration
```python
redis_config = {
    "host": "localhost",
    "port": 6379,
    "db": 1,
    "decode_responses": False
}
```

### System Configuration
```python
api = LettaIntegrationAPI(
    letta_config=letta_config,
    redis_config=redis_config,
    backup_directory="./backups",
    enable_monitoring=True,
    enable_communication=True,
    enable_workflows=True,
    auto_optimization=True,
    auto_backup=False,
    optimization_interval_hours=6,
    backup_interval_hours=24
)
```

## 📊 Monitoring and Analytics

### Dashboard Data
Get comprehensive dashboard data:
```python
dashboard = api.performance_monitor.get_dashboard_data()
```

**Dashboard includes:**
- System metrics and health status
- Active alerts and notifications
- Performance trends and predictions
- Optimization recommendations
- Agent activity metrics

### Memory Analytics
```python
analytics = api.get_memory_analytics("trading_strategist")
```

**Analytics include:**
- Memory utilization and fragmentation
- Access patterns and hot blocks
- Priority distribution and age analysis
- Cache performance metrics

### Performance Metrics
```python
metrics = api.get_performance_metrics("trading_strategist")
```

**Metrics include:**
- Response time distributions
- Query performance statistics
- Error rates and availability
- Workflow efficiency metrics

## 🛠️ Best Practices

### Performance Optimization
1. **Regular Cleanup**: Schedule automatic optimization every 6-24 hours
2. **Archive Old Data**: Move infrequently accessed blocks to archival storage
3. **Monitor Memory**: Keep memory utilization below 80%
4. **Cache Tuning**: Optimize cache TTL based on access patterns

### Memory Management
1. **Tag Usage**: Use descriptive tags for easy searching
2. **Priority Setting**: Set appropriate priorities for critical memory blocks
3. **Retention Policies**: Use appropriate retention policies for different data types
4. **Pattern Learning**: Regularly update and validate trading patterns

### Agent Communication
1. **Agent Roles**: Define clear roles and capabilities for each agent
2. **Message Prioritization**: Use appropriate priority levels for different message types
3. **Memory Sharing**: Share memory selectively with appropriate access controls
4. **Coordination**: Use coordination requests for complex multi-agent tasks

### Backup Strategy
1. **Incremental Backups**: Use incremental backups for daily operations
2. **Full Backups**: Schedule weekly full backups
3. **Retention Policy**: Keep daily backups for 7 days, weekly for 30 days
4. **Validation**: Regularly validate backup integrity

## 🔍 Troubleshooting

### Common Issues

1. **Connection Failed**
   ```python
   # Verify Letta server is running
   health = api.client.health_check()
   print(f"Health: {health['overall_status']}")
   ```

2. **Memory Issues**
   ```python
   # Check memory utilization
   analytics = api.get_memory_usage("agent_id")
   if analytics.utilization_percentage > 90:
       api.optimize_memory("agent_id")
   ```

3. **Performance Degradation**
   ```python
   # Get performance recommendations
   recommendations = api.get_optimization_recommendations("agent_id")
   for rec in recommendations:
       print(f"Issue: {rec['description']}")
   ```

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks
```python
# Comprehensive health check
health = api.health_check()
print(f"Overall status: {health['overall_status']}")

# Component-specific health
letta_health = api.client.health_check()
memory_health = api.get_memory_usage("agent_id")
```

## 🎯 Examples

### Complete Trading Integration
See `examples/complete_trading_integration.py` for a full trading system example.

### Memory Management Demo
See `examples/memory_management_demo.py` for comprehensive memory management examples.

### Multi-Agent Communication
See `examples/agent_communication_demo.py` for multi-agent communication examples.

### Performance Monitoring
See `examples/performance_monitoring_demo.py` for performance monitoring examples.

## 🤝 Contributing

To contribute to the Letta Integration system:

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
1. Check the troubleshooting section
2. Review system logs for error messages
3. Use debug mode for detailed operation logs
4. Monitor system status endpoints

---

**Letta Integration API** - Comprehensive REST API integration for advanced memory management, agent communication, trading workflows, and performance analytics.