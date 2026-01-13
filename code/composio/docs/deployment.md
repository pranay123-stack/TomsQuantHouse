# Deployment Guide

This guide covers deploying the Composio MCP Server in various environments including development, staging, and production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Monitoring and Maintenance](#monitoring-and-maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **Memory**: 2GB minimum, 4GB recommended
- **Storage**: 10GB minimum
- **Network**: Internet access for external API calls

### External Dependencies

- **Database**: PostgreSQL (recommended) or SQLite
- **Redis**: For rate limiting and caching (optional but recommended)
- **External APIs**: GitHub, Slack, Telegram, Notion, QuantConnect, Abacus.AI

## Local Development

### Quick Setup

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd composio
   chmod +x setup.sh
   ./setup.sh --dev
   ```

2. **Configure environment**:
   ```bash
   # Edit configuration files
   nano config/config.json
   nano .env
   ```

3. **Start the server**:
   ```bash
   source venv/bin/activate
   python server/composio_server.py
   ```

4. **Test the installation**:
   ```bash
   python examples/demo.py
   ```

### Manual Setup

If you prefer manual setup:

1. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Copy configuration**:
   ```bash
   cp config/config.example.json config/config.json
   ```

3. **Edit configuration**:
   ```json
   {
     "environment": "development",
     "debug": true,
     "database": {
       "url": "sqlite:///./composio.db"
     }
   }
   ```

4. **Run the server**:
   ```bash
   python server/composio_server.py --config config/config.json --log-level DEBUG
   ```

## Docker Deployment

### Dockerfile

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash composio
RUN chown -R composio:composio /app
USER composio

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Start the server
CMD ["python", "server/composio_server.py"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  composio-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - COMPOSIO_ENVIRONMENT=production
      - COMPOSIO_DATABASE_URL=postgresql://composio:password@postgres:5432/composio
      - COMPOSIO_REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: composio
      POSTGRES_USER: composio
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - composio-server
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f composio-server

# Scale services
docker-compose up -d --scale composio-server=3

# Stop services
docker-compose down

# Clean up
docker-compose down -v
```

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/composio-server.service`:

```ini
[Unit]
Description=Composio MCP Server
After=network.target

[Service]
Type=simple
User=composio
WorkingDirectory=/opt/composio
Environment=PATH=/opt/composio/venv/bin
ExecStart=/opt/composio/venv/bin/python server/composio_server.py --config /opt/composio/config/production.json
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true

# Resource limits
LimitNOFILE=65536
MemoryMax=2G

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration

Create `/etc/nginx/sites-available/composio`:

```nginx
upstream composio_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/your-domain.crt;
    ssl_certificate_key /etc/nginx/ssl/your-domain.key;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://composio_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://composio_backend/health;
        access_log off;
    }

    # Metrics endpoint (restrict access)
    location /metrics {
        proxy_pass http://composio_backend/metrics;
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
        access_log off;
    }
}
```

### SSL Certificate with Let's Encrypt

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Production Configuration

Create `config/production.json`:

```json
{
  "environment": "production",
  "debug": false,
  "server_host": "127.0.0.1",
  "server_port": 8000,
  
  "database": {
    "url": "postgresql://composio:secure_password@localhost:5432/composio",
    "pool_size": 20,
    "max_overflow": 40,
    "echo": false
  },
  
  "redis": {
    "url": "redis://localhost:6379/0",
    "max_connections": 100
  },
  
  "auth": {
    "secret_key": "use-environment-variable",
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 7
  },
  
  "rate_limit": {
    "enabled": true,
    "redis_url": "redis://localhost:6379/1",
    "default_limits": {
      "requests_per_minute": 60,
      "requests_per_hour": 1000,
      "requests_per_day": 10000
    }
  },
  
  "logging": {
    "level": "INFO",
    "format": "json",
    "output": "file",
    "file_path": "/var/log/composio/server.log",
    "max_size": 100,
    "backup_count": 10
  },
  
  "health": {
    "enabled": true,
    "check_interval": 30,
    "alert_thresholds": {
      "cpu_usage": 80,
      "memory_usage": 85,
      "disk_usage": 90
    }
  }
}
```

### Environment Variables

Create `/opt/composio/.env`:

```bash
# Server
COMPOSIO_ENVIRONMENT=production
COMPOSIO_DEBUG=false

# Database
COMPOSIO_DATABASE_URL=postgresql://composio:secure_password@localhost:5432/composio

# Redis
COMPOSIO_REDIS_URL=redis://localhost:6379/0

# Authentication
COMPOSIO_SECRET_KEY=your-super-secure-secret-key
COMPOSIO_ENCRYPTION_KEY=your-super-secure-encryption-key

# External APIs
GITHUB_TOKEN=your-github-token
SLACK_BOT_TOKEN=your-slack-bot-token
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
NOTION_TOKEN=your-notion-token
QUANTCONNECT_TOKEN=your-quantconnect-token
ABACUS_AI_API_KEY=your-abacus-ai-key

# Logging
COMPOSIO_LOG_LEVEL=INFO
```

### Deployment Commands

```bash
# Install dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv postgresql redis-server nginx

# Create application user
sudo useradd --system --home /opt/composio --shell /bin/bash composio
sudo mkdir -p /opt/composio
sudo chown composio:composio /opt/composio

# Deploy application
sudo -u composio git clone <repository> /opt/composio
cd /opt/composio
sudo -u composio python3 -m venv venv
sudo -u composio venv/bin/pip install -r requirements.txt

# Setup database
sudo -u postgres createdb composio
sudo -u postgres createuser composio

# Setup systemd service
sudo cp deploy/composio-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable composio-server
sudo systemctl start composio-server

# Setup nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/composio
sudo ln -s /etc/nginx/sites-available/composio /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Cloud Deployment

### AWS Deployment

#### EC2 Instance

1. **Launch EC2 Instance**:
   - AMI: Ubuntu Server 22.04 LTS
   - Instance Type: t3.small or larger
   - Security Group: Allow SSH, HTTP, HTTPS

2. **Setup**:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install dependencies
   sudo apt install python3 python3-pip python3-venv postgresql redis-server nginx -y
   
   # Clone and deploy application
   git clone <repository> /opt/composio
   cd /opt/composio
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Database Setup**:
   ```bash
   # Install PostgreSQL
   sudo -u postgres createdb composio
   sudo -u postgres createuser composio
   ```

4. **Application Service**:
   ```bash
   sudo cp deploy/composio-server.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable composio-server
   sudo systemctl start composio-server
   ```

#### RDS and ElastiCache

For production, use managed services:

1. **RDS PostgreSQL**:
   ```json
   {
     "database": {
       "url": "postgresql://username:password@your-rds-endpoint:5432/composio"
     }
   }
   ```

2. **ElastiCache Redis**:
   ```json
   {
     "redis": {
       "url": "redis://your-elasticache-endpoint:6379/0"
     }
   }
   ```

### Google Cloud Platform

#### Cloud Run

1. **Create Dockerfile**:
   ```dockerfile
   # (Use the Dockerfile from earlier)
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy composio-server \
     --source . \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars COMPOSIO_ENVIRONMENT=production
   ```

#### Compute Engine

Similar to AWS EC2 deployment but using GCP commands.

### Microsoft Azure

#### Container Instances

```bash
# Create resource group
az group create --name composio-rg --location eastus

# Deploy container
az container create \
  --resource-group composio-rg \
  --name composio-server \
  --image your-registry/composio-server:latest \
  --dns-name-label composio-server \
  --ports 8000
```

## Monitoring and Maintenance

### Health Monitoring

1. **Systemd service monitoring**:
   ```bash
   systemctl status composio-server
   journalctl -u composio-server -f
   ```

2. **Health endpoint**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Metrics monitoring**:
   ```bash
   curl http://localhost:8000/metrics
   ```

### Log Management

1. **Application logs**:
   ```bash
   tail -f /var/log/composio/server.log
   ```

2. **System logs**:
   ```bash
   journalctl -u composio-server --since "1 hour ago"
   ```

3. **Nginx logs**:
   ```bash
   tail -f /var/log/nginx/access.log
   tail -f /var/log/nginx/error.log
   ```

### Performance Monitoring

1. **System metrics**:
   ```bash
   htop
   iotop
   netstat -tuln
   ```

2. **Database monitoring**:
   ```bash
   sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"
   ```

3. **Redis monitoring**:
   ```bash
   redis-cli info
   redis-cli monitor
   ```

### Backup Strategy

1. **Database backup**:
   ```bash
   # PostgreSQL backup
   pg_dump composio > backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Automated backup script
   #!/bin/bash
   DATE=$(date +%Y%m%d_%H%M%S)
   BACKUP_DIR="/opt/backups"
   mkdir -p $BACKUP_DIR
   
   pg_dump composio > $BACKUP_DIR/composio_$DATE.sql
   
   # Keep only last 7 days of backups
   find $BACKUP_DIR -name "composio_*.sql" -mtime +7 -delete
   ```

2. **Configuration backup**:
   ```bash
   # Backup configuration files
   tar -czf config_backup_$(date +%Y%m%d).tar.gz config/ .env
   ```

### Updates and Maintenance

1. **Application updates**:
   ```bash
   # Stop service
   sudo systemctl stop composio-server
   
   # Update code
   git pull origin main
   
   # Update dependencies
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Run migrations if needed
   python manage.py migrate
   
   # Restart service
   sudo systemctl start composio-server
   ```

2. **System updates**:
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Update Python packages
   source /opt/composio/venv/bin/activate
   pip install --upgrade -r requirements.txt
   ```

## Troubleshooting

### Common Issues

1. **Service won't start**:
   ```bash
   # Check service status
   systemctl status composio-server
   
   # Check logs
   journalctl -u composio-server -n 50
   
   # Check configuration
   python server/composio_server.py --config config/production.json --dry-run
   ```

2. **Database connection issues**:
   ```bash
   # Test database connection
   psql -h localhost -U composio -d composio -c "SELECT version();"
   
   # Check connection settings
   grep DATABASE_URL config/production.json
   ```

3. **Redis connection issues**:
   ```bash
   # Test Redis connection
   redis-cli ping
   
   # Check Redis status
   systemctl status redis
   ```

4. **High memory usage**:
   ```bash
   # Check memory usage
   free -h
   ps aux --sort=-%mem | head
   
   # Restart service if needed
   sudo systemctl restart composio-server
   ```

### Debug Mode

For debugging, enable debug mode:

```json
{
  "debug": true,
  "logging": {
    "level": "DEBUG"
  }
}
```

### Performance Issues

1. **Slow responses**:
   - Check system resources (CPU, memory, disk)
   - Review application logs for errors
   - Monitor database performance
   - Check external API response times

2. **High CPU usage**:
   - Profile the application
   - Optimize database queries
   - Check for infinite loops in code

3. **Memory leaks**:
   - Monitor memory usage over time
   - Use profiling tools
   - Check for unclosed connections

### Security Issues

1. **Unauthorized access**:
   - Check authentication logs
   - Review API keys and tokens
   - Verify firewall settings

2. **Rate limiting**:
   - Monitor rate limit hit counts
   - Adjust limits if needed
   - Check for abuse patterns

This deployment guide provides comprehensive instructions for deploying the Composio MCP Server in various environments. Choose the deployment method that best fits your requirements and infrastructure.