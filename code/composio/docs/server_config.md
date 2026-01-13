# Server Configuration Guide

This guide covers configuring the Composio MCP Server for different environments and use cases.

## Configuration File Structure

The server uses a JSON configuration file with the following main sections:

```json
{
  "environment": "development",
  "debug": false,
  "server_host": "0.0.0.0",
  "server_port": 8000,
  "database": {...},
  "redis": {...},
  "auth": {...},
  "metrics": {...},
  "rate_limit": {...},
  "tools": {...},
  "health": {...},
  "logging": {...},
  "features": {...}
}
```

## Environment Configuration

### Development Environment

For development, use the default settings with minimal security:

```json
{
  "environment": "development",
  "debug": true,
  "database": {
    "url": "sqlite:///./composio.db",
    "echo": true
  },
  "auth": {
    "secret_key": "dev-secret-key-change-in-production",
    "access_token_expire_minutes": 60,
    "refresh_token_expire_days": 30
  },
  "logging": {
    "level": "DEBUG",
    "format": "text"
  }
}
```

### Production Environment

For production, ensure secure settings:

```json
{
  "environment": "production",
  "debug": false,
  "database": {
    "url": "postgresql://user:password@localhost/composio",
    "pool_size": 20,
    "max_overflow": 40
  },
  "redis": {
    "url": "redis://redis-server:6379/0",
    "password": "secure-redis-password"
  },
  "auth": {
    "secret_key": "use-environment-variable-for-secret",
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 7,
    "encryption_key": "use-environment-variable-for-encryption"
  },
  "rate_limit": {
    "enabled": true,
    "default_limits": {
      "requests_per_minute": 60,
      "requests_per_hour": 1000,
      "requests_per_day": 10000
    }
  },
  "logging": {
    "level": "INFO",
    "format": "json",
    "file_path": "/var/log/composio/server.log"
  }
}
```

## Database Configuration

### SQLite (Development)

```json
{
  "database": {
    "url": "sqlite:///./composio.db",
    "echo": false,
    "pool_size": 5,
    "max_overflow": 10
  }
}
```

### PostgreSQL (Production)

```json
{
  "database": {
    "url": "postgresql://username:password@localhost:5432/composio",
    "pool_size": 20,
    "max_overflow": 40,
    "echo": false
  }
}
```

### MySQL

```json
{
  "database": {
    "url": "mysql+pymysql://username:password@localhost:3306/composio",
    "pool_size": 15,
    "max_overflow": 30
  }
}
```

## Redis Configuration

### Single Redis Instance

```json
{
  "redis": {
    "url": "redis://localhost:6379/0",
    "db": 0,
    "max_connections": 50
  }
}
```

### Redis Cluster

```json
{
  "redis": {
    "url": "redis://redis-cluster:6379/0",
    "cluster_mode": true,
    "max_connections": 100
  }
}
```

## Authentication Configuration

### JWT Settings

```json
{
  "auth": {
    "secret_key": "your-secret-key",
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "password_salt": "your-salt",
    "encryption_key": "your-encryption-key"
  }
}
```

### Security Best Practices

1. **Never hardcode secrets** in configuration files
2. **Use environment variables** for sensitive data
3. **Rotate secrets regularly**
4. **Use strong encryption keys** (32+ characters)
5. **Set appropriate token expiration times**

Example using environment variables:

```bash
export COMPOSIO_SECRET_KEY="your-secret-from-env"
export COMPOSIO_ENCRYPTION_KEY="your-encryption-from-env"
export COMPOSIO_DB_PASSWORD="secure-password"
```

## Rate Limiting Configuration

### Default Limits

```json
{
  "rate_limit": {
    "enabled": true,
    "redis_url": "redis://localhost:6379/1",
    "default_limits": {
      "requests_per_minute": 100,
      "requests_per_hour": 1000,
      "requests_per_day": 10000
    }
  }
}
```

### Tool-Specific Limits

```json
{
  "rate_limit": {
    "tool_specific_limits": {
      "github": {
        "requests_per_hour": 5000
      },
      "slack": {
        "requests_per_hour": 100
      },
      "telegram": {
        "requests_per_hour": 30
      },
      "quantconnect": {
        "requests_per_minute": 10
      },
      "abacus_ai": {
        "requests_per_minute": 5
      }
    }
  }
}
```

## Tool Configuration

### GitHub Integration

```json
{
  "tools": {
    "github": {
      "enabled": true,
      "api_url": "https://api.github.com",
      "rate_limit": 5000,
      "timeout": 30,
      "user_agent": "YourApp/1.0"
    }
  }
}
```

### Slack Integration

```json
{
  "tools": {
    "slack": {
      "enabled": true,
      "api_url": "https://slack.com/api",
      "rate_limit": 100,
      "timeout": 30
    }
  }
}
```

### Trading Tools

```json
{
  "tools": {
    "quantconnect": {
      "enabled": true,
      "api_url": "https://www.quantconnect.com/api",
      "rate_limit": 10,
      "timeout": 60
    },
    "abacus_ai": {
      "enabled": true,
      "api_url": "https://api.abacus.ai",
      "rate_limit": 5,
      "timeout": 60
    }
  }
}
```

## Health Monitoring Configuration

```json
{
  "health": {
    "enabled": true,
    "check_interval": 30,
    "timeout": 10,
    "alert_thresholds": {
      "cpu_usage": 80,
      "memory_usage": 85,
      "disk_usage": 90,
      "response_time": 5000
    }
  }
}
```

## Metrics Configuration

```json
{
  "metrics": {
    "enabled": true,
    "port": 8000,
    "endpoint": "/metrics",
    "collection_interval": 60
  }
}
```

## Feature Flags

Control which features are enabled:

```json
{
  "features": {
    "authentication": true,
    "rate_limiting": true,
    "monitoring": true,
    "metrics": true,
    "trading_tools": true,
    "external_integrations": true
  }
}
```

## Security Configuration

### CORS Settings

```json
{
  "cors_origins": [
    "https://yourdomain.com",
    "https://app.yourdomain.com"
  ],
  "allowed_hosts": [
    "yourdomain.com",
    "localhost"
  ]
}
```

### Production Security

```json
{
  "environment": "production",
  "cors_origins": ["https://yourdomain.com"],
  "allowed_hosts": ["yourdomain.com"],
  "auth": {
    "access_token_expire_minutes": 15,
    "refresh_token_expire_days": 7
  }
}
```

## Logging Configuration

### Development Logging

```json
{
  "logging": {
    "level": "DEBUG",
    "format": "text",
    "output": "stdout",
    "structured": false
  }
}
```

### Production Logging

```json
{
  "logging": {
    "level": "INFO",
    "format": "json",
    "output": "file",
    "file_path": "/var/log/composio/server.log",
    "max_size": 100,
    "backup_count": 10,
    "structured": true
  }
}
```

## Configuration Validation

The server validates configuration on startup:

```python
from config.settings import Settings

# Load and validate configuration
settings = Settings.load("config/production.json")
issues = settings.validate()

if issues:
    print("Configuration issues:")
    for issue in issues:
        print(f"- {issue}")
```

## Environment Variables

Override configuration with environment variables:

```bash
# Server settings
export COMPOSIO_ENVIRONMENT=production
export COMPOSIO_DEBUG=false
export COMPOSIO_SERVER_PORT=8000

# Database
export COMPOSIO_DATABASE_URL=postgresql://user:pass@localhost/db

# Redis
export COMPOSIO_REDIS_URL=redis://localhost:6379/0

# Authentication
export COMPOSIO_SECRET_KEY=your-secret
export COMPOSIO_ENCRYPTION_KEY=your-encryption-key

# Tools
export GITHUB_TOKEN=your-github-token
export SLACK_BOT_TOKEN=your-slack-token
```

## Configuration File Best Practices

1. **Version control**: Don't commit production configs with secrets
2. **Environment-specific**: Use different configs for dev/staging/prod
3. **Documentation**: Comment complex configurations
4. **Validation**: Always validate configs before deployment
5. **Backup**: Keep backups of working configurations
6. **Monitoring**: Monitor configuration drift

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check database URL and credentials
   - Ensure database server is running
   - Verify network connectivity

2. **Redis connection failed**
   - Check Redis URL and credentials
   - Ensure Redis server is running
   - Verify network connectivity

3. **Rate limiting not working**
   - Verify Redis connection
   - Check rate limit configuration
   - Ensure rate limiting is enabled

4. **High memory usage**
   - Review cache settings
   - Check for memory leaks
   - Monitor tool usage patterns

### Configuration Debug Mode

Enable debug logging to troubleshoot:

```json
{
  "logging": {
    "level": "DEBUG",
    "format": "json"
  }
}
```

Then monitor logs for configuration issues.