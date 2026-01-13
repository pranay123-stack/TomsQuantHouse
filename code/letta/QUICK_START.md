# Letta Server - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### 1. Start Everything
```bash
cd /workspace/code/letta
docker-compose up -d
```

### 2. Wait for Services (30 seconds)
```bash
# Check status
docker-compose ps
```

### 3. Create Trading Agents
```bash
python3 create_agents.py
```

### 4. Test Installation
```bash
python3 test_letta_server.py
```

## 📋 Basic Commands

### Check Server Health
```bash
curl http://localhost:8283/health
```

### View All Agents
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8283/api/agents
```

### Test Agent Communication
```bash
python3 letta_client.py
```

## 🔧 Management

### View Logs
```bash
docker-compose logs -f letta-server
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Restart Services
```bash
docker-compose restart
```

### Stop Services
```bash
docker-compose down
```

### Clean Restart (removes data)
```bash
docker-compose down -v
docker-compose up -d
```

## 📁 Key Files

- `docker-compose.yml` - Service configuration
- `create_agents.py` - Agent creation script
- `letta_client.py` - Python client library
- `test_letta_server.py` - Test suite
- `agent_ids.json` - Created agent IDs
- `test_report.txt` - Test results
- `.env` - Configuration (copy from .env.example)

## 🌐 Access Points

- **Letta Server**: http://localhost:8283
- **Admin UI**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 🧠 Trading Agents

### Trading Strategist
- Focus: Strategy development and optimization
- Memory: Trading strategies, learned patterns
- Use for: Strategy recommendations, pattern analysis

### Market Analyst  
- Focus: Market condition assessment
- Memory: Market conditions, system context
- Use for: Market analysis, trend identification

### Risk Manager
- Focus: Portfolio protection
- Memory: Risk parameters, position sizing
- Use for: Risk assessment, trade validation

## 💡 Usage Examples

### Get Trading Strategies
```python
from letta_client import TradingAgentQuery

client = TradingAgentQuery()
strategies = client.get_trading_strategies()
for strategy in strategies:
    print(f"{strategy['title']}: {strategy['content'][:100]}...")
```

### Query Agent for Advice
```python
response = client.query_trading_advice(
    "market_analyst",
    "What are current market conditions?"
)
print(response['response'])
```

### Add New Memory
```python
from letta_client import LettaClient

client = LettaClient()
client.add_memory_block(agent_id, {
    "block_type": "learned_patterns",
    "title": "New Pattern",
    "content": "Pattern description",
    "metadata": {"confidence": 0.8}
})
```

## 🔍 Troubleshooting

### Server Not Starting
```bash
# Check logs
docker-compose logs letta-server

# Restart with clean state
docker-compose down -v
docker-compose up -d
```

### Database Connection Issues
```bash
# Check PostgreSQL
docker-compose logs postgres

# Verify connection
psql postgresql://letta:letta_password@localhost:5432/letta_db
```

### Agents Not Creating
```bash
# Check API keys in .env
cat .env | grep API_KEY

# Test manually
python3 create_agents.py
```

### Memory Not Persisting
```bash
# Check database
docker-compose exec postgres psql -U letta -d letta_db -c "SELECT COUNT(*) FROM memory_blocks;"
```

## 📊 Memory Block Types

- **trading_strategy**: Rules and principles
- **market_conditions**: Market state information  
- **risk_parameters**: Risk limits and rules
- **learned_patterns**: Identified patterns and success rates
- **system_context**: Session and system info
- **recent**: Recent activity and context
- **scratch**: Working memory

## 🔐 Security Notes

- Change default passwords in production
- Use environment variables for API keys
- Enable TLS for database connections
- Implement proper network isolation
- Regular security updates

## 📈 Performance Tips

- Monitor memory usage per agent
- Optimize database queries with indexes
- Use Redis caching for frequent data
- Set appropriate timeouts
- Scale horizontally for high load

---
For full documentation, see README.md