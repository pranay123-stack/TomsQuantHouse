# Letta Server Integration with PostgreSQL and Redis

This repository contains a complete setup for the Letta AI agent server with PostgreSQL database persistence and Redis caching integration, specifically configured for trading applications.

## Overview

The Letta server provides a powerful platform for creating and managing stateful AI agents with persistent memory. This setup includes:

- **Letta Server**: Core AI agent server with REST API
- **PostgreSQL**: Persistent storage for agent data and memory blocks
- **Redis**: Caching and session management
- **Trading Agents**: Pre-configured agents for trading strategy, market analysis, and risk management
- **Memory Management**: Structured memory blocks for different types of agent knowledge

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │    │  Letta Server   │    │ PostgreSQL DB   │
│                 │    │                 │    │                 │
│ - Trading Bot   │◄──►│ - Agents        │◄──►│ - Agents        │
│ - Web Dashboard │    │ - Memory Blocks │    │ - Memory Blocks │
│ - API Client    │    │ - Tools         │    │ - Persistence   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │                 │
                       │ - Cache         │
                       │ - Sessions      │
                       │ - Real-time     │
                       └─────────────────┘
```

## Components

### 1. Docker Services

- **letta-server**: Main Letta server application
- **postgres**: PostgreSQL database for persistence
- **redis**: Redis for caching and session management
- **letta-admin**: Admin UI for monitoring (optional)

### 2. Database Schema

The PostgreSQL database includes:
- **agents**: Store agent configurations and metadata
- **memory_blocks**: Persistent memory for agent knowledge
- **Indexes**: Optimized for fast queries and memory retrieval

### 3. Trading Agents

#### Trading Strategist Agent
- **Purpose**: Develop and optimize trading strategies
- **Memory Types**: Trading strategies, learned patterns
- **Specialization**: Technical analysis, strategy optimization

#### Market Analyst Agent  
- **Purpose**: Real-time market condition assessment
- **Memory Types**: Market conditions, system context, recent activity
- **Specialization**: Trend analysis, market indicators

#### Risk Manager Agent
- **Purpose**: Portfolio protection and risk assessment
- **Memory Types**: Risk parameters, position sizing rules
- **Specialization**: Risk management, portfolio protection

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- API keys for AI models (OpenAI, Anthropic)

### 1. Setup Environment

```bash
cd code/letta
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 2. Start Services

```bash
# Make setup script executable
chmod +x setup.sh

# Run full setup
./setup.sh
```

Or manually:
```bash
docker-compose up -d
```

### 3. Verify Installation

```bash
python3 test_letta_server.py
```

### 4. Create Trading Agents

```bash
python3 create_agents.py
```

## Usage Examples

### Agent Creation

```python
from letta_client import LettaClient, TradingAgentQuery

# Initialize client
client = LettaClient(api_key="your-api-key")
trading_queries = TradingAgentQuery(client)

# Get trading strategies
strategies = trading_queries.get_trading_strategies()

# Query for advice
response = trading_queries.query_trading_advice(
    "trading_strategist", 
    "What are the current high-probability setups?"
)
```

### Memory Management

```python
# Add new memory block
memory_block = {
    "block_type": "learned_patterns",
    "title": "New Trade Pattern",
    "content": "Identified pattern: Double bottom with volume confirmation",
    "metadata": {"confidence": 0.75}
}

client.add_memory_block(agent_id, memory_block)

# Search memory
results = client.search_memory(agent_id, "volume confirmation patterns")
```

### Agent Communication

```python
# Send message to agent
response = client.send_message(
    agent_id,
    "Analyze current SPY trend and provide trading recommendation"
)

print(response.get("messages", [])[-1]["content"])
```

## API Endpoints

### Core Endpoints

- `GET /health` - Server health check
- `GET /api/agents` - List all agents
- `POST /api/agents` - Create new agent
- `GET /api/agents/{id}` - Get agent details
- `POST /api/agents/{id}/message` - Send message to agent
- `GET /api/agents/{id}/memory` - Get agent memory
- `POST /api/agents/{id}/memory` - Add memory block
- `PUT /api/agents/{id}/memory/{block_id}` - Update memory block
- `DELETE /api/agents/{id}/memory/{block_id}` - Delete memory block

### Memory Block Types

- **trading_strategy**: Trading rules and principles
- **market_conditions**: Current and historical market states
- **risk_parameters**: Risk limits and position sizing rules
- **learned_patterns**: Identified trading patterns and their success rates
- **user_context**: User-specific preferences and settings
- **system_context**: System and session information
- **long_term**: Long-term memory and permanent knowledge
- **recent**: Recent activity and temporary context
- **scratch**: Working memory for calculations

## Configuration

### Environment Variables

See `.env.example` for all available configuration options:

#### Server Configuration
- `LETTA_SERVER_HOST`: Server host address
- `LETTA_SERVER_PORT`: Server port (default: 8283)
- `LETTA_API_KEY`: Server API key for authentication

#### Database Configuration
- `LETTA_PERSIST_TYPE`: Storage type (postgres)
- `LETTA_POSTGRES_URL`: PostgreSQL connection URL

#### Redis Configuration
- `LETTA_REDIS_URL`: Redis connection URL

#### AI Model Configuration
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key

### Docker Compose Configuration

The `docker-compose.yml` file configures:
- Service networking
- Volume mounts for data persistence
- Port mappings
- Health checks
- Restart policies

## Testing

The test suite (`test_letta_server.py`) verifies:

1. **Server Health**: Basic server responsiveness
2. **Database Connection**: PostgreSQL connectivity
3. **Agent Creation**: Dynamic agent creation
4. **Memory Operations**: CRUD operations on memory blocks
5. **Agent Communication**: Message passing and responses
6. **Data Persistence**: Data survival across restarts
7. **Trading Agents**: Specialized trading agent functionality

Run tests with:
```bash
python3 test_letta_server.py
```

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f letta-server
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Health Checks

```bash
# Server health
curl http://localhost:8283/health

# Database connectivity
curl -H "Authorization: Bearer your-api-key" http://localhost:8283/api/agents
```

### Metrics

The server provides metrics endpoints for monitoring:
- Agent count and status
- Memory usage
- Request rates
- Response times

## Troubleshooting

### Common Issues

1. **Server won't start**
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

2. **Database connection fails**
   ```bash
   docker-compose logs postgres
   # Check PostgreSQL configuration in docker-compose.yml
   ```

3. **Agent creation fails**
   ```bash
   python3 test_letta_server.py
   # Check API keys in .env file
   ```

4. **Memory not persisting**
   ```bash
   docker-compose logs letta-server
   # Check PostgreSQL connection and data volume mounts
   ```

### Performance Optimization

1. **Increase memory limits** in docker-compose.yml
2. **Optimize database queries** with proper indexes
3. **Use Redis caching** for frequently accessed data
4. **Monitor memory usage** in agent configurations

## Development

### Adding New Agent Types

1. Extend agent creation in `create_agents.py`
2. Add memory block types in database schema
3. Update client queries in `letta_client.py`
4. Add tests in `test_letta_server.py`

### Custom Memory Types

1. Add enum value to `memory_block_type` in database schema
2. Update agent creation scripts
3. Modify client to handle new memory type
4. Add validation and tests

## Security Considerations

1. **API Key Management**: Store API keys securely in environment variables
2. **Database Access**: Use strong passwords and network isolation
3. **Network Security**: Configure firewall rules for service ports
4. **Data Encryption**: Enable TLS for database connections
5. **Access Control**: Implement proper authentication for API endpoints

## License

This setup is provided for educational and development purposes. Please ensure compliance with all relevant service terms and licenses.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs with `docker-compose logs`
3. Run diagnostics with `test_letta_server.py`
4. Consult Letta documentation: https://docs.letta.dev