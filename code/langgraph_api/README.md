# LangGraph API Service

A comprehensive FastAPI-based REST API service for LangGraph workflow management with real-time monitoring, authentication, and visualization capabilities.

## 🌟 Features

### Core Functionality
- **Workflow Execution**: Single, batch, and async workflow execution
- **State Management**: Complete workflow state persistence and retrieval
- **Real-time Monitoring**: WebSocket-based real-time monitoring and alerts
- **Authentication**: JWT-based authentication with role-based access control
- **Visualization**: Workflow graphs and execution timelines
- **Metrics & Health**: System health checks and performance metrics
- **Documentation**: Comprehensive Swagger/OpenAPI documentation

### Architecture
- **FastAPI**: Modern, fast web framework for building APIs
- **WebSockets**: Real-time communication for monitoring updates
- **Prometheus**: Metrics collection and monitoring
- **PostgreSQL**: Primary database for workflow data
- **Redis**: Caching and session management
- **Docker**: Containerized deployinstall_dependenciesment

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL (via Docker)
- Redis (via Docker)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd langgraph_api
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start services with Docker**
   ```bash
   # Start all services
   docker-compose up -d
   
   # Start only in development mode
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

4. **Initialize database**
   ```bash
   python -m alembic upgrade head
   ```

5. **Run the service**
   ```bash
   python run.py
   ```

### Production Deployment

1. **Configure environment**
   ```bash
   cp .env.production .env
   # Edit .env with your production settings
   ```

2. **Deploy with Docker Compose**
   ```bash
   chmod +x deploy/deploy.sh
   ./deploy/deploy.sh production
   ```

## 📖 API Documentation

Once the service is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **ReDoc Documentation**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 🔐 Authentication

The API uses JWT token authentication. Include the token in the Authorization header:

```http
Authorization: Bearer your-jwt-token
```

### User Roles
- **Admin**: Full system access
- **Premium**: Enhanced workflow capabilities
- **Standard**: Basic workflow operations
- **Basic**: Read-only access

## 🏗️ API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user

### Workflow Management
- `POST /api/v1/workflows` - Create workflow
- `GET /api/v1/workflows` - List workflows
- `GET /api/v1/workflows/{id}` - Get workflow
- `PUT /api/v1/workflows/{id}` - Update workflow
- `DELETE /api/v1/workflows/{id}` - Delete workflow
- `POST /api/v1/workflows/{id}/execute` - Execute workflow
- `POST /api/v1/workflows/execute/batch` - Batch execution
- `POST /api/v1/workflows/{id}/cancel` - Cancel execution

### State Management
- `POST /api/v1/states` - Create state
- `GET /api/v1/states` - List states
- `GET /api/v1/states/{id}` - Get state
- `PUT /api/v1/states/{id}` - Update state
- `DELETE /api/v1/states/{id}` - Delete state
- `GET /api/v1/states/workflow/{id}` - Get workflow states
- `POST /api/v1/states/{id}/checkpoint` - Create checkpoint

### Monitoring
- `GET /api/v1/monitoring/health` - System health
- `GET /api/v1/monitoring/metrics` - Performance metrics
- `GET /api/v1/monitoring/alerts` - Active alerts
- `GET /api/v1/monitoring/performance` - Performance summary

### Visualization
- `GET /api/v1/visualization/graph/{id}` - Workflow graph
- `GET /api/v1/visualization/timeline/{id}` - Execution timeline
- `GET /api/v1/visualization/metrics/charts` - Metrics charts
- `GET /api/v1/visualization/heatmap` - Activity heatmap

## 🔄 WebSocket Support

Connect to real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/user-id');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## 📊 Monitoring & Metrics

### Health Checks
- Database connectivity
- Redis connectivity
- Workflow system status
- System resource usage

### Metrics Collection
- Workflow execution count
- Execution duration
- Success/failure rates
- System performance metrics

### Dashboard Integration
- Prometheus metrics at `/metrics`
- Grafana dashboards at `http://localhost:3000`
- Real-time WebSocket updates

## 🐳 Docker Deployment

### Development
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Production
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Services included:
- API Service (FastAPI)
- PostgreSQL Database
- Redis Cache
- Prometheus (Metrics)
- Grafana (Dashboards)
- Nginx (Reverse Proxy)

## 🔧 Configuration

Environment variables are configured in `.env` files:

### Key Settings
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key
- `ENVIRONMENT`: deployment environment
- `API_PORT`: API server port

### Rate Limiting
- Admin: 1000 requests/hour
- Premium: 500 requests/hour
- Standard: 200 requests/hour
- Basic: 100 requests/hour

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_workflows.py
```

## 📁 Project Structure

```
langgraph_api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── core/                   # Core configurations
│   │   ├── config.py
│   │   └── database.py
│   ├── auth/                   # Authentication
│   │   ├── auth_handler.py
│   │   └── auth_models.py
│   ├── api/
│   │   ├── api.py
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── workflows.py
│   │   │   ├── states.py
│   │   │   ├── monitoring.py
│   │   │   └── visualization.py
│   │   └── websocket/
│   │       └── manager.py
│   ├── models/                 # Database models
│   │   └── user.py
│   └── services/               # Business logic
│       ├── workflow_service.py
│       ├── state_service.py
│       ├── monitoring_service.py
│       ├── health_monitor.py
│       ├── metrics_collector.py
│       └── visualization_service.py
├── deploy/
│   └── deploy.sh
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── run.py
└── README.md
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support, please:
1. Check the documentation
2. Review the API examples
3. Open an issue on GitHub

## 🏃‍♂️ Performance

The API is designed for high performance with:
- Async/await throughout
- Connection pooling
- Redis caching
- Optimized database queries
- WebSocket compression

## 🔒 Security

Security features include:
- JWT token authentication
- Role-based access control
- Rate limiting
- Input validation
- SQL injection prevention
- CORS configuration
- Environment-based secrets

---

**LangGraph API Service** - Comprehensive workflow management with real-time monitoring 🚀