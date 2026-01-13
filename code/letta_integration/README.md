# Letta Stateful Agents Integration

A comprehensive integration system for Letta stateful agents with advanced memory management, multi-agent communication, and intelligent optimization capabilities.

## 🚀 Features

### Advanced Memory Block Management
- **Structured Memory Types**: Trading strategies, market conditions, risk parameters, learned patterns, performance metrics, and more
- **Smart Prioritization**: Critical, high, medium, low, and archive priority levels
- **Retention Policies**: Permanent, long-term, medium-term, short-term, and temporary retention
- **Memory Block Integrity**: Checksum validation and integrity verification
- **Pattern Learning**: Structured trading pattern recognition and learning

### Persistent Learning Across Sessions
- **Workflow Automation**: Trade analysis, strategy evolution, risk assessment, and market learning workflows
- **Scheduled Execution**: Automatic workflow scheduling with cron-like expressions
- **Trade Event Processing**: Automated analysis of trade outcomes and strategy performance
- **Adaptive Learning**: Market adaptation and strategy evolution tracking
- **Performance Analytics**: Comprehensive performance insight generation

### Strategic Decision Making
- **Advanced Query Engine**: Multiple query types including text search, pattern matching, performance analysis
- **Semantic Similarity**: Intelligent content-based search and retrieval
- **Strategic Insights**: Automated generation of actionable trading recommendations
- **Risk Assessment**: Real-time risk evaluation and alert generation
- **Market Context**: Dynamic market regime analysis and correlation tracking

### Redis Archival Storage
- **Tiered Storage**: Hot, warm, cold, and frozen archival tiers
- **Intelligent Tier Management**: Automatic promotion/demotion based on access patterns
- **Compression**: Gzip compression for efficient storage
- **Fast Retrieval**: Quick access to archived memory blocks
- **Retention Policies**: TTL-based cleanup with configurable retention

### Multi-Agent Communication
- **Agent Registry**: Dynamic agent registration and capability tracking
- **Message Routing**: Intelligent message routing based on content and recipient
- **Memory Sharing**: Secure inter-agent memory sharing with access controls
- **Coordination Requests**: Agent coordination and collaboration workflows
- **Risk Alerts**: Automated risk alert distribution to appropriate agents
- **Performance Updates**: Real-time performance data sharing between agents

### Memory Optimization
- **Multiple Strategies**: LRU, LFU, size-based, frequency-based, time-based, and hybrid optimization
- **Predictive Optimization**: AI-driven memory pressure prediction and proactive optimization
- **Automated Cleanup**: Background cleanup scheduling and execution
- **Performance Monitoring**: Real-time memory usage analysis and recommendations
- **Fragmentation Management**: Memory defragmentation and reorganization

### Backup and Restore
- **Multiple Backup Types**: Full, incremental, differential, selective, and archival backups
- **Compressed Storage**: Gzipped backup files for efficient storage
- **Integrity Validation**: Checksum verification and data corruption detection
- **Flexible Restore**: Merge, replace, append, and validate-only restore modes
- **Backup Catalog**: Complete backup inventory and metadata management

## 📦 Installation

### Prerequisites
- Python 3.8+
- Letta server running (default: http://localhost:8283)
- PostgreSQL database (for Letta persistence)
- Redis server (optional, for archival storage)

### Dependencies
```bash
pip install redis requests asyncio aiohttp numpy
```

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
│ Memory Manager │ │ Workflows │ │   Communication │
│                │ │           │ │                 │
│ • Block Mgmt   │ │ • Executor│ │ • Agent Registry│
│ • Pattern Learn│ │ • Scheduler│ │ • Message Router│
│ • Performance  │ │ • Automation│ │ • Memory Share │
└────────────────┘ └───────────┘ └─────────────────┘
        │
┌───────▼────────┐ ┌───────────┐ ┌───────────────┐
│ Query Engine   │ │ Optimizer │ │ Backup Manager│
│                │ │           │ │               │
│ • Text Search  │ │ • LRU/LFU │ │ • Full/Inc.   │
│ • Pattern Match│ │ • Size    │ │ • Restore     │
│ • Semantic Sim │ │ • Hybrid  │ │ • Validation  │
└────────────────┘ └───────────┘ └───────────────┘
        │
┌───────▼────────┐
│Redis Archival  │
│                │
│ • Tier Mgmt    │
│ • Compression  │
│ • Fast Access  │
└────────────────┘
```

## 🚀 Quick Start

### Basic Usage

```python
from letta_integration_api import LettaIntegrationAPI

# Configuration
letta_config = {
    "base_url": "http://localhost:8283",
    "api_key": "your-api-key-here"
}

redis_config = {
    "host": "localhost",
    "port": 6379,
    "db": 1
}

# Initialize API
api = LettaIntegrationAPI(letta_config, redis_config)

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

# Search memory
results = api.search_memory(
    agent_id="trading_strategist",
    query="strategy",
    limit=10
)

# Stop the system
api.stop()
```

### Trading-Focused Setup

```python
from letta_integration_api import create_trading_integration

# Create trading-focused integration
api = create_trading_integration(letta_config, redis_config)
api.start()

# Register agents
api.register_agent("trading_strategist", "strategist", ["strategy", "pattern_analysis"])
api.register_agent("market_analyst", "analyst", ["market_analysis", "data_processing"])
api.register_agent("risk_manager", "risk_manager", ["risk_assessment", "risk_management"])
```

## 📚 Core Components

### Memory Management

```python
# Create trading pattern
pattern_id = api.create_trading_pattern(
    agent_id="trading_strategist",
    symbol="AAPL",
    pattern_type="bullish_breakout",
    success_rate=0.75,
    confidence=0.8,
    conditions={"volume_spike": True, "rsi_oversold": False},
    entry_signals=["price_breaks_resistance", "volume_confirmation"],
    exit_signals=["stop_loss", "profit_target"],
    risk_metrics={"max_risk": 0.02, "position_size": 0.1}
)

# Get performance insights
insights = api.get_performance_insights("trading_strategist")
for insight in insights:
    print(f"Insight: {insight.title} - {insight.description}")

# Get trading opportunities
opportunities = api.get_trading_opportunities("trading_strategist", symbol="AAPL")
```

### Workflow Automation

```python
# Execute trade analysis workflow
trade_event = {
    "trade_id": "trade_001",
    "symbol": "AAPL",
    "action": "buy",
    "quantity": 100,
    "entry_price": 150.00,
    "exit_price": 155.50,
    "pnl": 5.50,
    "strategy": "moving_average_crossover",
    "confidence": 0.8,
    "outcome": "win"
}

workflow_id = api.execute_trade_analysis_workflow("trading_strategist", trade_event)

# Schedule periodic performance review
schedule_id = api.schedule_workflow(
    workflow_type="performance_review",
    agent_id="trading_strategist",
    schedule_time=datetime.now() + timedelta(hours=1),
    recurring=True,
    interval_hours=24
)

# Check workflow status
status = api.get_workflow_status(workflow_id)
print(f"Workflow {workflow_id}: {status['status']}")
```

### Multi-Agent Communication

```python
# Send direct message
message_id = api.send_message(
    sender_agent_id="trading_strategist",
    receiver_agent_id="risk_manager",
    subject="Strategy Update",
    content="New high-confidence pattern identified",
    priority="high"
)

# Broadcast to multiple agents
recipients = api.broadcast_message(
    sender_agent_id="trading_strategist",
    subject="Market Alert",
    content="Volatility spike detected in tech sector",
    target_roles=["analyst", "risk_manager"]
)

# Share memory between agents
share_id = api.share_memory(
    sharing_agent_id="trading_strategist",
    recipient_agent_id="market_analyst",
    memory_block_ids=["block_1", "block_2"],
    access_level="read",
    duration_hours=24
)

# Send risk alert
alert_id = api.send_risk_alert(
    agent_id="risk_manager",
    risk_level="high",
    description="Unusual volatility detected",
    risk_data={"volatility": 0.85, "positions_at_risk": ["AAPL", "TSLA"]}
)
```

### Archival Storage

```python
# Archive memory blocks to Redis
results = api.archive_memory_blocks(
    agent_id="trading_strategist",
    block_ids=["old_block_1", "old_block_2"],
    tier="cold"
)

# Restore archived blocks
restored = api.restore_archived_memory(
    agent_id="trading_strategist",
    block_ids=["old_block_1", "old_block_2"]
)

# Search archived content
archived_results = api.search_archived_content(
    agent_id="trading_strategist",
    search_text="strategy performance",
    limit=20
)
```

### Memory Optimization

```python
# Optimize memory usage
report = api.optimize_memory(
    agent_id="trading_strategist",
    strategy="hybrid",
    aggressive=True
)

print(f"Optimized {report['blocks_processed']} blocks")
print(f"Freed {report['space_freed_bytes']} bytes")

# Schedule automatic optimization
schedule_id = api.schedule_optimization(
    agent_id="trading_strategist",
    strategy="lru_caching",
    interval_hours=6,
    aggressive=False
)

# Get optimization recommendations
recommendations = api.get_optimization_recommendations("trading_strategist")
for recommendation in recommendations["optimization_opportunities"]:
    print(f"Opportunity: {recommendation['description']}")
    print(f"Recommendation: {recommendation['recommendation']}")
```

### Backup and Restore

```python
# Create full backup
backup_id = api.create_backup(
    agent_id="trading_strategist",
    backup_type="full"
)

# Create incremental backup
inc_backup_id = api.create_backup(
    agent_id="trading_strategist",
    backup_type="incremental"
)

# Create selective backup
selective_backup = api.create_backup(
    agent_id="trading_strategist",
    backup_type="selective",
    block_types=["trading_strategy", "learned_patterns"]
)

# List available backups
backups = api.list_backups(agent_id="trading_strategist")
for backup in backups:
    print(f"Backup: {backup['backup_id']} - {backup['total_blocks']} blocks")

# Restore from backup
restore_report = api.restore_backup(
    backup_id=backup_id,
    agent_id="trading_strategist",
    restore_mode="merge"
)

print(f"Restored {restore_report['blocks_restored']} blocks")

# Validate backup
validation = api.validate_backup(backup_id)
print(f"Backup valid: {validation['valid']}")
```

### Strategic Decision Making

```python
# Get trading advice
advice = api.get_trading_advice("trading_strategist", "current market conditions")

# Get market context
context = api.get_market_context("trading_strategist")
print(f"Current regime: {context['current_regime']}")
print(f"Volatility: {context['recent_volatility']}")

# Get risk assessment
risk_insights = api.get_risk_assessment("trading_strategist")
for insight in risk_insights:
    print(f"Risk: {insight['title']} - {insight['description']}")

# Compare strategies
comparison = api.compare_strategies("trading_strategist", ["ma_strategy", "rsi_strategy"])
for strategy, data in comparison.items():
    print(f"{strategy}: {data['success_rate']} success rate")

# Get adaptive recommendations
recommendations = api.get_adaptive_recommendations("trading_strategist")
for rec in recommendations:
    print(f"Recommendation: {rec['title']}")
    print(f"Actions: {rec['actionable_recommendations']}")
```

## 🔧 Configuration

### Auto-Optimization
```python
# Enable automatic memory optimization
api.configure_auto_optimization(enabled=True, interval_hours=6)

# This will automatically optimize memory every 6 hours based on usage patterns
```

### Auto-Backup
```python
# Enable automatic backups
api.configure_auto_backup(enabled=True, interval_hours=24)

# This will automatically create incremental backups every 24 hours
```

### System Monitoring
```python
# Get system status
status = api.get_system_status()
print(f"Active agents: {status['communication']['active_agents']}")
print(f"Messages sent: {status['communication']['messages_sent']}")
print(f"Cache size: {status['memory_manager']['cache_size']}")

# Get memory usage
usage = api.get_memory_usage("trading_strategist")
print(f"Memory utilization: {usage['metrics']['memory_utilization']:.2%}")

# Get communication stats
comm_stats = api.get_communication_stats()
print(f"Average response time: {comm_stats['average_response_time']:.2f}s")

# Get recent messages
recent_messages = api.get_recent_messages(agent_id="trading_strategist", time_range_hours=24)
```

## 🏃‍♂️ Running the Complete System

### Complete Example
```python
import asyncio
from datetime import datetime, timedelta
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

try:
    # Start the system
    api.start()
    
    print("Letta Integration System Started")
    print("=" * 50)
    
    # Create some trading patterns
    pattern1 = api.create_trading_pattern(
        agent_id="trading_strategist",
        symbol="AAPL",
        pattern_type="bullish_breakout",
        success_rate=0.75,
        confidence=0.8,
        conditions={"volume_spike": True, "rsi_oversold": False},
        entry_signals=["price_breaks_resistance"],
        exit_signals=["stop_loss", "profit_target"]
    )
    
    pattern2 = api.create_trading_pattern(
        agent_id="trading_strategist",
        symbol="TSLA",
        pattern_type="reversal_pattern",
        success_rate=0.65,
        confidence=0.7,
        conditions={"oversold": True, "volume_divergence": True},
        entry_signals=["reversal_signal"],
        exit_signals=["stop_loss"]
    )
    
    print(f"Created patterns: {pattern1}, {pattern2}")
    
    # Simulate trade execution
    trade_events = [
        {
            "trade_id": "trade_001",
            "symbol": "AAPL",
            "action": "buy",
            "quantity": 100,
            "entry_price": 150.00,
            "exit_price": 155.50,
            "pnl": 5.50,
            "strategy": "bullish_breakout",
            "confidence": 0.8,
            "outcome": "win"
        },
        {
            "trade_id": "trade_002", 
            "symbol": "TSLA",
            "action": "buy",
            "quantity": 50,
            "entry_price": 200.00,
            "exit_price": 195.00,
            "pnl": -5.00,
            "strategy": "reversal_pattern",
            "confidence": 0.7,
            "outcome": "loss"
        }
    ]
    
    # Execute trade analysis workflows
    for trade in trade_events:
        workflow_id = api.execute_trade_analysis_workflow("trading_strategist", trade)
        print(f"Started workflow for {trade['trade_id']}: {workflow_id}")
    
    # Schedule optimization
    schedule_id = api.schedule_optimization(
        agent_id="trading_strategist",
        strategy="hybrid",
        interval_hours=1,  # Every hour for demo
        aggressive=False
    )
    
    print(f"Scheduled optimization: {schedule_id}")
    
    # Create backup
    backup_id = api.create_backup(
        agent_id="trading_strategist",
        backup_type="full"
    )
    
    print(f"Created backup: {backup_id}")
    
    # Send communication between agents
    message_id = api.send_message(
        sender_agent_id="trading_strategist",
        receiver_agent_id="risk_manager",
        subject="Strategy Performance Update",
        content="Two trades analyzed with mixed results. Please review risk parameters.",
        priority="normal"
    )
    
    print(f"Sent message: {message_id}")
    
    # Get trading opportunities
    opportunities = api.get_trading_opportunities("trading_strategist")
    print(f"Found {len(opportunities)} trading opportunities")
    
    # Get market context
    context = api.get_market_context("trading_strategist")
    print(f"Market context: {context}")
    
    # Get system status
    status = api.get_system_status()
    print(f"System status: {status}")
    
    # Keep running for demo
    print("\nSystem is running. Press Ctrl+C to stop...")
    try:
        while True:
            import time
            time.sleep(10)
            
            # Show periodic updates
            recent_messages = api.get_recent_messages(time_range_hours=1)
            print(f"Recent messages: {len(recent_messages)}")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        
finally:
    # Clean shutdown
    api.stop()
    print("Letta Integration System stopped")
```

## 📊 Monitoring and Analytics

### System Health Dashboard
```python
# Comprehensive system monitoring
def print_dashboard():
    status = api.get_system_status()
    
    print("🚀 LETTA INTEGRATION DASHBOARD")
    print("=" * 60)
    
    # Memory Statistics
    memory = status["memory_manager"]
    print(f"📦 Memory Management:")
    print(f"   Cache Size: {memory['cache_size']} blocks")
    print(f"   Hit Rate: {memory['cache_hit_rate']:.1%}")
    
    # Communication Statistics
    comm = status["communication"]
    print(f"💬 Communication:")
    print(f"   Active Agents: {comm['active_agents']}")
    print(f"   Messages Sent: {comm['messages_sent']}")
    print(f"   Messages Received: {comm['messages_received']}")
    
    # Workflow Statistics
    workflows = status.get("workflow_scheduler", {})
    print(f"⚙️  Workflows:")
    print(f"   Scheduled: {len(workflows)}")
    
    # Backup Statistics
    backup = status["backup_manager"]
    print(f"💾 Backup:")
    print(f"   Total Backups: {backup['backups_created']}")
    print(f"   Total Size: {backup['total_backup_size'] / 1024 / 1024:.1f} MB")
    
    print("=" * 60)

# Update dashboard periodically
import threading
def update_dashboard():
    while True:
        try:
            print_dashboard()
            time.sleep(30)  # Update every 30 seconds
        except:
            break
```

## 🔧 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```python
   # Check Redis configuration
   redis_config = {
       "host": "localhost",
       "port": 6379,
       "db": 1,
       "decode_responses": False
   }
   ```

2. **Letta Server Not Responding**
   ```python
   # Verify Letta server is running
   client = LettaClient(base_url="http://localhost:8283")
   agents = client.get_agents()
   ```

3. **Memory Optimization Errors**
   ```python
   # Check memory manager status
   metrics = api.get_memory_usage("agent_id")
   print(f"Memory utilization: {metrics['metrics']['memory_utilization']}")
   ```

### Debug Mode
```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("letta_integration")

# This will show detailed operation logs
```

## 🎯 Best Practices

### Performance Optimization
1. **Regular Cleanup**: Schedule automatic optimization every 6-24 hours
2. **Archive Old Data**: Move infrequently accessed blocks to archival storage
3. **Monitor Memory**: Keep cache hit rate above 70%
4. **Backup Strategy**: Use incremental backups with weekly full backups

### Memory Management
1. **Tag Usage**: Use descriptive tags for easy searching
2. **Priority Setting**: Set appropriate priorities for critical memory blocks
3. **Retention Policies**: Use appropriate retention policies for different data types
4. **Pattern Learning**: Regularly update and validate trading patterns

### Multi-Agent Communication
1. **Agent Roles**: Define clear roles and capabilities for each agent
2. **Message Prioritization**: Use appropriate priority levels for different message types
3. **Memory Sharing**: Share memory selectively with appropriate access controls
4. **Coordination**: Use coordination requests for complex multi-agent tasks

## 🔄 API Reference

### MemoryBlockType
- `TRADING_STRATEGY`: Trading rules and strategies
- `MARKET_CONDITIONS`: Current market states and conditions
- `RISK_PARAMETERS`: Risk limits and position sizing rules
- `LEARNED_PATTERNS`: Identified trading patterns and success rates
- `PERFORMANCE_METRICS`: Trading performance data
- `TRADE_OUTCOMES`: Individual trade results
- `MARKET_REGIME`: Market regime identification
- `CORRELATION_MATRICES`: Asset correlation data

### WorkflowType
- `TRADE_ANALYSIS`: Analyze individual trade outcomes
- `STRATEGY_EVOLUTION`: Evolve trading strategies based on performance
- `RISK_ASSESSMENT`: Assess and learn from risk events
- `MARKET_LEARNING`: Learn from market events and conditions
- `PERFORMANCE_REVIEW`: Comprehensive performance analysis

### AgentRole
- `STRATEGIST`: Trading strategy development and optimization
- `ANALYST`: Market analysis and data processing
- `RISK_MANAGER`: Risk assessment and management
- `COORDINATOR`: Agent coordination and orchestration
- `SPECIALIST`: Domain-specific expertise
- `OBSERVER`: Monitoring and data collection

## 📈 Performance Metrics

### Key Performance Indicators
- **Memory Utilization**: Target < 80%
- **Cache Hit Rate**: Target > 70%
- **Query Response Time**: Target < 500ms
- **Workflow Success Rate**: Target > 95%
- **Communication Latency**: Target < 100ms

### Monitoring Commands
```python
# Check system health
health = api.get_system_status()

# Get performance metrics
metrics = api.get_memory_usage("agent_id")

# Monitor communication
comm_stats = api.get_communication_stats()

# Get optimization history
history = api.memory_optimizer.get_optimization_history()
```

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
- Check the troubleshooting section above
- Review system logs for error messages
- Use debug mode for detailed operation logs
- Monitor system status endpoints

---

**Letta Integration System** - Advanced stateful agent memory management with intelligent optimization, multi-agent communication, and comprehensive backup/restore capabilities.