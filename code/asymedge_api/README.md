# ASYMEdge Dashboard API

A comprehensive FastAPI backend service for the ASYMEdge trading dashboard, providing agent query interfaces, real-time data streaming, trading analytics, workflow monitoring, and user management.

## Features

### 🤖 Agent Query Interfaces
- **Letta Integration**: Full support for Letta stateful agents
- **Agent Lifecycle Management**: Create, start, stop, and monitor agent instances
- **Query Processing**: Send queries to agents and track responses
- **Performance Analytics**: Monitor agent performance and execution metrics
- **Memory Management**: Track and update agent memory states

### 📊 Real-time Streaming
- **WebSocket Support**: Live data streaming via WebSocket connections
- **Multiple Subscription Types**: Agent activity, trading metrics, workflow status, market data
- **Real-time Updates**: Live dashboard updates with minimal latency
- **Connection Management**: Robust connection handling with automatic reconnection

### 📈 Trading Analytics
- **Portfolio Metrics**: Comprehensive portfolio analytics and performance tracking
- **Market Data**: Real-time and historical market data integration
- **Risk Management**: VaR, drawdown, Sharpe ratio, and other risk metrics
- **Technical Analysis**: Trading signals and technical indicators
- **Economic Indicators**: Key economic data and market sentiment

### 🔄 Workflow Monitoring
- **Workflow Execution**: Define and execute complex workflows
- **Step-by-step Tracking**: Monitor workflow progress and execution logs
- **Template Library**: Pre-built workflow templates for common tasks
- **Error Handling**: Comprehensive error tracking and recovery mechanisms
- **Scheduling**: Automated workflow execution and monitoring

### 👤 User Management
- **Authentication**: JWT-based authentication with session management
- **Authorization**: Role-based access control with user tiers
- **Profile Management**: User profiles with customizable settings
- **Session Control**: Session management with revocation capabilities
- **Password Management**: Secure password handling with reset functionality

### ⚙️ Dashboard Configuration
- **Layout Management**: Customizable dashboard layouts with widget positioning
- **Theme Support**: Multiple themes with color customization
- **Widget Library**: Extensive widget library for different data types
- **Template System**: Pre-defined dashboard templates
- **Real-time Updates**: Live configuration updates without restart

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Database      │    │   External      │
│   Application   │    │   (SQLAlchemy)  │    │   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
│                        │                        │
│  ┌──────────────┐    │  ┌──────────────┐    │  ┌──────────────┐
│  │ WebSocket    │    │  │ PostgreSQL   │    │  │ Letta API    │
│  │ Streaming    │    │  │ SQLite       │    │  │ Trading APIs │
│  └──────────────┘    │  └──────────────┘    │  └──────────────┘
│                        │                        │
│  ┌──────────────┐    │  ┌──────────────┐    │
│  │ Background   │    │  │ Redis        │    │
│  │ Tasks        │    │  │ (Caching)    │    │
│  └──────────────┘    │  └──────────────┘    │
└─────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd asymedge_api

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the project root:

```bash
# Database Configuration
DATABASE_URL=sqlite:///./asymedge_api.db
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Letta Integration
LETTA_API_BASE_URL=http://localhost:8283
LETTA_API_KEY=your-letta-api-key

# Feature Flags
ENABLE_AGENT_QUERIES=true
ENABLE_REAL_TIME_STREAMING=true
ENABLE_TRADING_METRICS=true
ENABLE_WORKFLOW_MONITORING=true
ENABLE_USER_MANAGEMENT=true
ENABLE_DASHBOARD_CONFIG=true

# Rate Limiting
RATE_LIMIT_DEFAULT=1000
RATE_LIMIT_PREMIUM=5000
RATE_LIMIT_ENTERPRISE=-1

# Development
DEBUG=true
LOG_LEVEL=INFO
```

### 3. Running the API

```bash
# Start the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use the startup script
./start.sh
```

### 4. API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

## API Endpoints

### Health & Monitoring
- `GET /api/v1/health` - System health status
- `GET /api/v1/health/detailed` - Detailed system metrics
- `GET /api/v1/health/database` - Database health check
- `GET /api/v1/health/ready` - Readiness probe
- `GET /api/v1/health/live` - Liveness probe

### Agent Management
- `GET /api/v1/agents/definitions` - List agent definitions
- `POST /api/v1/agents/definitions` - Create agent definition
- `GET /api/v1/agents/instances` - List agent instances
- `POST /api/v1/agents/instances` - Create agent instance
- `POST /api/v1/agents/instances/{id}/query` - Query agent
- `GET /api/v1/agents/instances/{id}/queries` - Query history

### Real-time Streaming
- `WebSocket /api/v1/streaming/ws` - Main WebSocket endpoint
- `WebSocket /api/v1/streaming/live` - Simplified streaming
- `GET /api/v1/streaming/subscriptions` - Get subscription types
- `POST /api/v1/streaming/publish/agent-update` - Publish agent update
- `GET /api/v1/streaming/stats` - Streaming statistics

### Trading Metrics
- `GET /api/v1/trading/market-data/{symbol}` - Get market data
- `GET /api/v1/trading/realtime-prices` - Get real-time prices
- `GET /api/v1/trading/portfolio/analytics` - Portfolio analytics
- `GET /api/v1/trading/symbol/{symbol}/analytics` - Symbol analytics
- `GET /api/v1/trading/symbol/{symbol}/signals` - Trading signals

### Workflow Monitoring
- `GET /api/v1/workflows/definitions` - List workflow definitions
- `POST /api/v1/workflows/definitions` - Create workflow definition
- `GET /api/v1/workflows/instances` - List workflow instances
- `POST /api/v1/workflows/instances` - Create workflow instance
- `POST /api/v1/workflows/instances/{id}/start` - Start workflow
- `POST /api/v1/workflows/instances/{id}/cancel` - Cancel workflow

### User Management
- `POST /api/v1/users/register` - Register new user
- `POST /api/v1/users/login` - User login
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update user profile
- `POST /api/v1/users/change-password` - Change password
- `GET /api/v1/users/sessions` - Get user sessions

### Dashboard Configuration
- `GET /api/v1/dashboard/configs` - List dashboard configs
- `POST /api/v1/dashboard/configs` - Create dashboard config
- `GET /api/v1/dashboard/default` - Get default dashboard
- `GET /api/v1/dashboard/widgets` - Get available widgets
- `GET /api/v1/dashboard/themes` - Get available themes
- `GET /api/v1/dashboard/templates` - Get dashboard templates

## Configuration

### Database Configuration

The API supports multiple database backends:

#### SQLite (Development)
```bash
DATABASE_URL=sqlite:///./asymedge_api.db
```

#### PostgreSQL (Production)
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/asymedge
```

#### MySQL (Production)
```bash
DATABASE_URL=mysql://user:password@localhost:3306/asymedge
```

### Redis Configuration

For caching and real-time features:

```bash
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password
```

### Letta Integration

Configure Letta agent integration:

```bash
LETTA_API_BASE_URL=http://localhost:8283
LETTA_API_KEY=your-letta-api-key
LETTA_TIMEOUT=30
```

### Rate Limiting

Configure rate limits per user tier:

```bash
RATE_LIMIT_DEFAULT=1000      # Requests per hour
RATE_LIMIT_PREMIUM=5000      # Premium tier limit
RATE_LIMIT_ENTERPRISE=-1     # Unlimited
RATE_LIMIT_WINDOW=3600       # Time window in seconds
```

### Feature Flags

Enable/disable features:

```bash
ENABLE_AGENT_QUERIES=true
ENABLE_REAL_TIME_STREAMING=true
ENABLE_TRADING_METRICS=true
ENABLE_WORKFLOW_MONITORING=true
ENABLE_USER_MANAGEMENT=true
ENABLE_DASHBOARD_CONFIG=true
```

## WebSocket Streaming

### Connection

Connect to WebSocket endpoint:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/streaming/live');

// Send authentication
ws.send(JSON.stringify({
    type: 'auth',
    user_id: 1,
    token: 'your-jwt-token'
}));
```

### Subscription Types

Subscribe to different data streams:

```javascript
// Subscribe to agent updates
ws.send(JSON.stringify({
    type: 'subscribe',
    subscription_type: 'agent_activity',
    filters: { agent_id: 1 }
}));

// Subscribe to trading metrics
ws.send(JSON.stringify({
    type: 'subscribe',
    subscription_type: 'trading_metrics',
    filters: { metric_type: 'portfolio_value' }
}));

// Subscribe to workflow status
ws.send(JSON.stringify({
    type: 'subscribe',
    subscription_type: 'workflow_status',
    filters: { workflow_id: 1 }
}));
```

### Message Format

WebSocket messages follow this format:

```json
{
    "type": "data_update",
    "subscription_type": "agent_activity",
    "data": {
        "agent_id": 1,
        "status": "running",
        "activity": "processing_query",
        "performance": {
            "queries_per_minute": 5.2,
            "average_response_time": 0.45
        }
    },
    "timestamp": "2025-11-02T09:09:04.123Z",
    "priority": "normal"
}
```

## Database Schema

### Core Tables

- **users** - User accounts and authentication
- **user_sessions** - User session tracking
- **agent_definitions** - Reusable agent templates
- **agent_instances** - Running agent instances
- **agent_queries** - Query history and responses
- **trading_metrics** - Stored trading metrics
- **market_data** - Market data points
- **workflow_definitions** - Reusable workflow templates
- **workflow_instances** - Running workflow instances
- **dashboard_configs** - User dashboard configurations
- **system_logs** - System logging and monitoring
- **streaming_subscriptions** - Real-time subscription tracking

### Database Initialization

The database is automatically initialized on startup. Default data includes:

- Admin user (admin@asymedge.com / admin123)
- Default agent definitions
- Default workflow templates
- Dashboard templates

## Authentication

### JWT Token Authentication

```bash
# Login to get token
curl -X POST "http://localhost:8000/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

### Using the Token

```bash
# Make authenticated request
curl -X GET "http://localhost:8000/api/v1/agents/instances" \
  -H "Authorization: Bearer your-jwt-token"
```

### API Key Authentication

```bash
# Alternative API key authentication
curl -X GET "http://localhost:8000/api/v1/agents/instances" \
  -H "X-API-Key: your-api-key"
```

## Development

### Code Quality

```bash
# Format code
black api/
isort api/

# Type checking
mypy api/

# Linting
flake8 api/

# Run tests
pytest tests/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Environment Variables

For development, create a `.env` file:

```bash
# Development settings
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite:///./asymedge_dev.db

# Disable some features for faster development
ENABLE_AGENT_QUERIES=false
ENABLE_REAL_TIME_STREAMING=false
ENABLE_WORKFLOW_MONITORING=false
ENABLE_TRADING_METRICS=false
```

## Deployment

### Production Deployment

1. **Environment Setup**:
   ```bash
   DEBUG=false
   DATABASE_URL=postgresql://user:pass@db:5432/asymedge
   SECRET_KEY=production-secret-key
   ```

2. **Database Setup**:
   ```bash
   # Run migrations
   alembic upgrade head
   ```

3. **Start Server**:
   ```bash
   # Using Gunicorn
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/asymedge
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=asymedge
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## Monitoring

### Health Checks

The API provides comprehensive health monitoring:

- **System Health**: Overall system status
- **Database Health**: Database connectivity and performance
- **Service Health**: Individual service status
- **Performance Metrics**: Request rates, response times, error rates

### Logging

Structured logging with JSON format:

```json
{
    "timestamp": "2025-11-02T09:09:04.123Z",
    "level": "INFO",
    "logger": "asymedge_api.agents",
    "message": "Agent query processed successfully",
    "agent_id": 1,
    "user_id": 1,
    "execution_time_ms": 245.5
}
```

### Metrics

Available metrics include:
- Request/response rates
- Database query performance
- Agent execution metrics
- WebSocket connection statistics
- System resource usage

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest tests/test_agents.py

# Run with verbose output
pytest -v
```

### Test Categories

- **Unit Tests**: Individual function and method testing
- **Integration Tests**: API endpoint testing
- **Database Tests**: Database operation testing
- **WebSocket Tests**: Real-time streaming testing
- **Authentication Tests**: Security and auth testing

### Example Test

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_agent_creation():
    # Test agent creation with authentication
    login_response = client.post("/api/v1/users/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/agents/definitions", 
                          json={
                              "name": "Test Agent",
                              "letta_agent_type": "test_type",
                              "configuration": {}
                          },
                          headers=headers)
    assert response.status_code == 201
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**:
   ```bash
   # Check database connectivity
   curl http://localhost:8000/api/v1/health/database
   ```

2. **Letta Integration Issues**:
   ```bash
   # Verify Letta service is running
   curl http://localhost:8283/api/v1/agents
   ```

3. **WebSocket Connection Issues**:
   ```bash
   # Test WebSocket connection
   # Open browser to http://localhost:8000/api/v1/streaming/test-stream
   ```

### Performance Optimization

1. **Database Indexing**: Ensure proper indexes on frequently queried columns
2. **Caching**: Enable Redis caching for frequently accessed data
3. **Rate Limiting**: Configure appropriate rate limits for your use case
4. **Connection Pooling**: Use connection pooling for database connections

### Error Handling

The API provides detailed error responses:

```json
{
    "error": {
        "code": 400,
        "message": "Invalid request parameters",
        "details": {
            "field": "agent_id",
            "reason": "Agent does not exist"
        }
    },
    "timestamp": "2025-11-02T09:09:04.123Z"
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure code quality checks pass
6. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Write comprehensive tests
- Document new features
- Use type hints where possible
- Follow semantic versioning for releases

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

For support and questions:

- **Documentation**: Check this README and inline code documentation
- **Issues**: Create GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas

## Changelog

### Version 1.0.0 (2025-11-02)
- Initial release with full feature set
- Agent query interfaces for Letta integration
- Real-time streaming via WebSocket
- Trading analytics and market data
- Workflow monitoring and automation
- User management and authentication
- Dashboard configuration system
- Comprehensive health monitoring
- Production-ready deployment support