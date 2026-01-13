# Trading System Docker Compose Stack

## Overview

This Docker Compose configuration provides a complete, production-ready deployment of the Trading System with all services integrated and properly configured for high-performance trading operations.

## Architecture

The system consists of the following major components:

### Core Infrastructure
- **PostgreSQL 15**: Primary database with optimized settings for trading applications
- **Redis 7**: Caching and pub/sub messaging with persistence
- **Eclipse Mosquitto**: MQTT broker for real-time message routing

### AI/ML Services
- **Letta Server**: AI agent orchestration and management
- **Abacus.AI Service**: Machine learning predictions and model management
- **LangGraph API**: Workflow orchestration and graph processing
- **ASYMEdge API**: Edge computing and real-time processing

### Integration Services
- **Composio MCP Server**: Multi-protocol tool integration (GitHub, Slack, Telegram, etc.)
- **Pub/Sub Router**: Message routing and event processing
- **Workflow Manager**: Agent handoff and decision-making workflows
- **Security Service**: Authentication, authorization, and security monitoring

### Monitoring & Observability
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Jaeger**: Distributed tracing
- **Elasticsearch/Logstash/Kibana (ELK)**: Centralized logging
- **Nginx**: Reverse proxy and load balancing

## Services Configuration

### API Gateway Routes
All external traffic goes through Nginx with the following routing:

- `/api/langgraph/*` → LangGraph API (Port 8000)
- `/api/asymedge/*` → ASYMEdge API (Port 8002)
- `/api/abacus/*` → Abacus.AI Service (Port 8001)
- `/composio/*` → Composio MCP Server (Port 3001)
- `/pubsub/*` → Pub/Sub Router (Port 8003)
- `/workflows/*` → Workflow Manager (Port 8004)
- `/security/*` → Security Service (Port 8005)

### Database Schemas
- `langgraph`: Workflow and graph data
- `asymedge`: Edge computing data
- `abacus`: ML model and prediction data
- `composio`: Tool integration data
- `pubsub`: Message routing data
- `workflows`: Workflow management data
- `security`: Authentication and security data
- `trading`: Trading session and market data
- `monitoring`: System monitoring and audit logs

### Networks
- `system-network`: Main communication network
- `database-network`: Internal database access
- `cache-network`: Internal cache access
- `ai-network`: AI/ML service communication
- `api-network`: API service communication
- `integration-network`: Integration service communication
- `messaging-network`: Pub/Sub messaging
- `workflow-network`: Workflow communication
- `security-network`: Security service communication
- `monitoring-network`: Monitoring service communication
- `logging-network`: Centralized logging

## Quick Start

### 1. Prerequisites

Ensure you have the following installed:
- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 8GB RAM
- At least 50GB disk space

### 2. Environment Setup

```bash
# Clone or navigate to the docker directory
cd /workspace/docker

# Copy and configure environment variables
cp .env.example .env
nano .env  # Edit with your configuration

# Important variables to configure:
# - POSTGRES_PASSWORD: Secure database password
# - REDIS_PASSWORD: Secure Redis password
# - SECRET_KEY: Application secret key
# - API keys for external services (OpenAI, Anthropic, etc.)
```

### 3. SSL Certificate Setup

For production deployment with HTTPS:

```bash
# Generate self-signed certificate (development)
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem -out ssl/fullchain.pem

# Or use Let's Encrypt for production
# certbot --nginx -d yourdomain.com
```

### 4. Deployment

```bash
# Make deploy script executable
chmod +x scripts/deploy.sh

# Start the entire system
./scripts/deploy.sh start

# Check system status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs

# Run health checks
./scripts/deploy.sh health
```

## Service Management

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d langgraph-api

# Start with service dependencies
docker-compose up -d postgres redis
sleep 60
docker-compose up -d
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: destroys data)
docker-compose down -v

# Stop specific service
docker-compose stop langgraph-api
```

### Scaling Services

```bash
# Scale API service to 3 replicas
docker-compose up -d --scale langgraph-api=3 langgraph-api

# Scale Letta server
docker-compose up -d --scale letta-server=2 letta-server
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f langgraph-api

# Last 100 lines
docker-compose logs --tail=100 langgraph-api
```

## Monitoring

### Access URLs

After deployment, access the following services:

- **Grafana Dashboards**: http://localhost:3000
  - Username: `admin`
  - Password: Check `$GRAFANA_PASSWORD` in .env file

- **Prometheus**: http://localhost:9090
  - View metrics and alerts configuration

- **Jaeger Tracing**: http://localhost:16686
  - View distributed traces across services

- **Kibana**: http://localhost:5601
  - Explore centralized logs and system events

- **API Endpoints**:
  - LangGraph API: http://localhost:8000
  - ASYMEdge API: http://localhost:8002
  - Abacus.AI: http://localhost:8001

### Health Monitoring

```bash
# Run comprehensive health checks
./scripts/deploy.sh health

# Check specific service health
docker-compose ps

# View service metrics
curl http://localhost:9090/api/v1/targets
```

### Alert Configuration

The system includes pre-configured alerts for:
- High CPU/Memory usage (>80%)
- Service downtime
- High HTTP error rates (>10%)
- Database connectivity issues
- SSL certificate expiry
- Trading algorithm performance degradation

## Performance Tuning

### Database Optimization

PostgreSQL is configured with:
- Optimized memory settings (shared_buffers, work_mem)
- Write-ahead logging (WAL) configuration
- Connection pooling support
- Automated vacuum and analyze
- Query performance monitoring

### Redis Configuration

Redis is optimized for:
- Memory management (maxmemory-policy allkeys-lru)
- Persistence (AOF and RDB)
- Pub/Sub performance
- Connection limits and timeouts

### Application Scaling

Each service includes resource limits:
- **CPU**: 1-2 cores per service
- **Memory**: 2-4GB per service
- **Replicas**: 2-3 for critical services

## Security

### Network Security
- Internal networks with restricted access
- Service-to-service authentication
- Rate limiting and DDoS protection
- Security headers in Nginx

### Data Security
- Encrypted passwords and API keys
- Secure database connections
- Audit logging for all operations
- Role-based access control

### SSL/TLS
- HTTPS enforcement via Nginx
- HSTS headers configured
- SSL certificate management
- Secure WebSocket connections

## Backup & Recovery

### Automated Backup

```bash
# Create backup
./scripts/deploy.sh backup

# Backup is stored in ./backups/ directory
# Includes: PostgreSQL data, Redis data, Docker volumes
```

### Manual Backup

```bash
# PostgreSQL backup
docker exec system-postgres pg_dumpall -U trading_user | gzip > backup.sql.gz

# Redis backup
docker exec system-redis redis-cli --rdb - | gzip > redis_backup.rdb.gz

# Volume backup
docker run --rm -v postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_data.tar.gz -C /data .
```

### Recovery

```bash
# Stop services
docker-compose down

# Restore PostgreSQL
gunzip -c backup.sql.gz | docker exec -i system-postgres psql -U trading_user

# Restore Redis
gunzip -c redis_backup.rdb.gz | docker exec -i system-redis redis-cli --pipe

# Restore volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/postgres_data.tar.gz -C /data

# Restart services
docker-compose up -d
```

## Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   # Check logs
   docker-compose logs [service-name]
   
   # Check resource usage
   docker stats
   
   # Verify environment variables
   docker-compose config
   ```

2. **Database connection errors**
   ```bash
   # Check PostgreSQL status
   docker exec system-postgres pg_isready -U trading_user
   
   # Check database logs
   docker-compose logs postgres
   ```

3. **High memory usage**
   ```bash
   # Check service memory usage
   docker stats --no-stream
   
   # Scale down non-critical services
   docker-compose up -d --scale composio=1 composio
   ```

4. **Port conflicts**
   ```bash
   # Check port usage
   netstat -tulpn | grep :8000
   
   # Change ports in docker-compose.yml if needed
   ```

### Log Analysis

```bash
# Search for errors in all logs
docker-compose logs | grep ERROR

# Follow specific service logs
docker-compose logs -f --tail=100 langgraph-api

# Export logs for analysis
docker-compose logs > system_logs.txt
```

## Maintenance

### Regular Tasks

1. **Update services** (weekly)
   ```bash
   ./scripts/deploy.sh stop
   docker-compose pull
   ./scripts/deploy.sh start
   ```

2. **Clean up old data** (monthly)
   ```bash
   # Clean Docker resources
   docker system prune -a
   
   # Clean old logs
   find ./logs -name "*.log" -mtime +30 -delete
   ```

3. **Security updates** (as needed)
   ```bash
   # Update base images
   docker-compose pull --ignore-pull-failures
   
   # Rebuild with security updates
   docker-compose build --no-cache
   ```

### Performance Monitoring

```bash
# Monitor resource usage
docker stats

# Check database performance
docker exec system-postgres psql -U trading_user -c "
  SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Monitor Redis memory
docker exec system-redis redis-cli info memory
```

## Development

### Local Development

For development environments:

```bash
# Start in development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Enable hot reload for development
# Modify volumes in docker-compose.dev.yml
```

### Adding New Services

1. Add service definition to `docker-compose.yml`
2. Create Dockerfile in service directory
3. Update nginx configuration for routing
4. Add monitoring configuration
5. Update deployment scripts

### Testing

```bash
# Run integration tests
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit

# Run specific service tests
docker-compose exec langgraph-api python -m pytest tests/
```

## Production Deployment

### High Availability Setup

1. **Multiple instances** of critical services
2. **Load balancing** via Nginx
3. **Database replication** (not included in this setup)
4. **Backup and disaster recovery** procedures

### Security Hardening

1. **Update all passwords** and secret keys
2. **Enable SSL certificates** from trusted CA
3. **Configure firewall** rules
4. **Implement monitoring** and alerting
5. **Regular security updates**

### Capacity Planning

- **Memory**: 32GB+ for production workloads
- **CPU**: 8+ cores for concurrent processing
- **Storage**: SSD storage for database and high I/O
- **Network**: 1Gbps+ for high-frequency trading

## Support

For issues and support:

1. Check logs: `./scripts/deploy.sh logs`
2. Run health checks: `./scripts/deploy.sh health`
3. Review documentation in this guide
4. Check service-specific documentation in `/workspace/code/[service]/`

## License

This Docker Compose configuration is part of the Trading System project.