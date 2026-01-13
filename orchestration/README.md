# Service Orchestration and Management System

A comprehensive service orchestration and management system for coordinating, monitoring, and maintaining distributed microservices.

## Overview

This system provides automated service orchestration, health monitoring, scaling, backup/restore capabilities, and debugging tools for managing complex service architectures.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Service Orchestrator                       │
│                     (orchestrator.py)                       │
├─────────────────────────────────────────────────────────────┤
│  • Service startup coordination                             │
│  • Health monitoring                                        │
│  • Graceful shutdown handling                               │
│  • Dependency management                                    │
│  • Automated scaling decisions                              │
└─────────────────────────────────────────────────────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
         ┌──────────▼─────┐  ┌───▼──────────────┐
         │  Health Check  │  │  Monitoring &    │
         │  Coordinator   │  │  Alerting        │
         └──────────┬─────┘  └─────┬────────────┘
                    │               │
         ┌──────────▼─────┐  ┌───▼──────────────┐
         │  Automated     │  │  Backup &        │
         │  Scaling       │  │  Restore         │
         └────────────────┘  └──────────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
         ┌──────────▼─────┐  ┌───▼──────────────┐
         │  Debugging     │  │  Management      │
         │  Tools         │  │  Scripts         │
         └────────────────┘  └──────────────────┘
```

## Directory Structure

```
orchestration/
├── orchestrator.py                 # Main orchestration engine
├── config/
│   └── services.yaml              # Service configuration
├── scripts/
│   ├── startup.sh                 # Service startup coordination
│   ├── graceful_shutdown.sh       # Graceful shutdown procedures
│   ├── health_check_coordinator.py # Health check management
│   ├── backup_restore.py          # Backup and restore system
│   ├── monitoring_system.py       # Monitoring and alerting
│   ├── automated_scaling.py       # Automated scaling system
│   ├── check_status.sh           # Status checking script
│   ├── restart_service.sh        # Service restart script
│   └── tail_logs.sh              # Log management script
├── debugging/
│   ├── service_inspector.py       # Service inspection tool
│   ├── network_analyzer.py        # Network analysis tool
│   └── log_analyzer.py            # Log analysis tool
├── logs/                          # Log files directory
│   ├── orchestrator.log           # Main orchestrator logs
│   ├── health_check.log           # Health check logs
│   ├── monitoring.log             # Monitoring system logs
│   ├── scaling.log                # Scaling system logs
│   ├── backup_restore.log         # Backup/restore logs
│   ├── debug_sessions/            # Debug session reports
│   ├── health_reports/            # Health check reports
│   ├── metrics/                   # Performance metrics
│   └── reports/                   # Status reports
└── backup/                        # Backup storage directory
```

## Core Components

### 1. Service Orchestrator (`orchestrator.py`)

The central orchestration engine that:
- Coordinates service startup in dependency order
- Monitors service health continuously
- Handles graceful shutdowns
- Manages service lifecycle
- Provides status reporting

**Key Features:**
- Dependency-aware startup
- Process management with PID tracking
- Health check integration
- Automatic service restart on failure
- Configuration-driven operation

### 2. Health Check Coordinator (`health_check_coordinator.py`)

Manages health checks between dependent services:
- HTTP health endpoint monitoring
- Dependency status tracking
- Service health aggregation
- Alert generation for unhealthy services
- Comprehensive health reporting

**Health Check Types:**
- HTTP endpoint availability
- Service dependency validation
- Process status verification
- Response time monitoring

### 3. Automated Scaling System (`automated_scaling.py`)

Intelligent scaling based on load metrics:
- CPU and memory usage monitoring
- Response time-based scaling decisions
- Configurable scaling policies
- Cooldown period management
- Scaling history tracking

**Scaling Policies:**
- Minimum/maximum instance limits
- CPU threshold triggers
- Memory threshold triggers
- Response time triggers
- Custom cooldown periods

### 4. Backup and Restore System (`backup_restore.py`)

Comprehensive data protection:
- Automated backup scheduling
- Multiple backup types (directories, databases, Redis)
- Compression and encryption support
- Integrity verification
- Point-in-time recovery

**Backup Types:**
- Directory backups (tar.gz compressed)
- Database backups (SQLite, custom)
- Redis data backups
- Configuration backups
- Log backups

### 5. Monitoring and Alerting (`monitoring_system.py`)

Real-time system monitoring:
- System resource monitoring
- Service performance metrics
- Threshold-based alerting
- Email and webhook notifications
- Dashboard generation

**Monitoring Metrics:**
- CPU usage
- Memory usage
- Disk usage
- Response times
- Error rates
- Network throughput

### 6. Debugging and Troubleshooting Tools

Comprehensive debugging toolkit:

#### Service Inspector (`debugging/service_inspector.py`)
- Process inspection and analysis
- Network connection monitoring
- File handle tracking
- Service dependency mapping

#### Network Analyzer (`debugging/network_analyzer.py`)
- Port connectivity testing
- DNS resolution checks
- Ping and traceroute analysis
- Traffic monitoring

#### Log Analyzer (`debugging/log_analyzer.py`)
- Pattern-based log searching
- Error pattern detection
- Performance metrics extraction
- Anomaly detection

## Configuration

### Service Configuration (`config/services.yaml`)

Defines all services, their dependencies, and operational parameters:

```yaml
services:
  redis:
    command: "cd /workspace/code/redis && python redis_server.py"
    dependencies: []
    health_endpoint: "http://localhost:6379"
    auto_restart: true
    ports:
      - "6379:6379"
  
  pubsub:
    command: "cd /workspace/code/pubsub && python pubsub_server.py"
    dependencies:
      - redis
    health_endpoint: "http://localhost:8080/health"
    auto_restart: true

scaling:
  policies:
    - service: "langgraph_api"
      min_instances: 1
      max_instances: 5
      cpu_threshold: 70
      memory_threshold: 80

backup:
  enabled: true
  schedule: "0 2 * * *"  # Daily at 2 AM
  targets:
    - name: redis_data
      path: "/workspace/code/redis/data"
      type: "directory"
```

## Usage

### Starting the System

```bash
# Start all services
./orchestration/scripts/startup.sh

# Check system status
./orchestration/scripts/check_status.sh --detailed
```

### Service Management

```bash
# List all services
./orchestration/scripts/restart_service.sh list

# Restart a specific service
./orchestration/scripts/restart_service.sh restart redis

# Restart all services
./orchestration/scripts/restart_service.sh restart-all

# Force restart a service
./orchestration/scripts/restart_service.sh force redis
```

### Log Management

```bash
# List all services and log files
./orchestration/scripts/tail_logs.sh list

# Tail logs for a specific service
./orchestration/scripts/tail_logs.sh tail redis -f

# Tail logs for all services
./orchestration/scripts/tail_logs.sh tail-all -f

# Analyze errors in logs
./orchestration/scripts/tail_logs.sh analyze redis errors

# Real-time monitoring with alerts
./orchestration/scripts/tail_logs.sh monitor redis
```

### Health Monitoring

```bash
# Run health check coordinator
python3 /workspace/orchestration/scripts/health_check_coordinator.py

# Generate health report
python3 /workspace/orchestration/scripts/health_check_coordinator.py --report
```

### Backup Operations

```bash
# Create backup for all services
python3 /workspace/orchestration/scripts/backup_restore.py --action backup

# Create backup for specific service
python3 /workspace/orchestration/scripts/backup_restore.py --action backup --target redis

# List available backups
python3 /workspace/orchestration/scripts/backup_restore.py --action list

# Restore from backup
python3 /workspace/orchestration/scripts/backup_restore.py --action restore \
  --backup-file /workspace/orchestration/backup/redis_20231102_143022.tar.gz \
  --restore-path /workspace/code/redis/data
```

### Scaling Operations

```bash
# Run scaling evaluation
python3 /workspace/orchestration/scripts/automated_scaling.py --evaluate

# Generate scaling report
python3 /workspace/orchestration/scripts/automated_scaling.py --report

# Start automated scaling daemon
python3 /workspace/orchestration/scripts/automated_scaling.py --daemon
```

### Monitoring and Alerting

```bash
# Run monitoring cycle
python3 /workspace/orchestration/scripts/monitoring_system.py --once

# Generate monitoring report
python3 /workspace/orchestration/scripts/monitoring_system.py --report

# Start monitoring daemon
python3 /workspace/orchestration/scripts/monitoring_system.py --daemon
```

### Debugging Operations

```bash
# Inspect service processes
python3 /workspace/orchestration/debugging/service_inspector.py inspect redis --type all

# Network connectivity analysis
python3 /workspace/orchestration/debugging/network_analyzer.py report

# Log pattern analysis
python3 /workspace/orchestration/debugging/log_analyzer.py summary --export

# System diagnostics
python3 /workspace/orchestration/debugging/service_inspector.py system
```

## Graceful Shutdown

```bash
# Stop all services gracefully
./orchestration/scripts/graceful_shutdown.sh
```

The shutdown script:
1. Sends SIGTERM to orchestrator
2. Waits for graceful shutdown (max 60 seconds)
3. Force kills if timeout exceeded
4. Stops all service processes
5. Cleans up PID files and lock files
6. Generates final status report

## Service Dependencies

Services are started in dependency order using topological sort:

```
Redis → PubSub → Security → LangGraph API → Letta API
                                      ↓
                           AsymEdge API → Composio
                                      ↓
                           CrewAI → Abacus AI → Workflows → Browser
```

## Monitoring Dashboards

The system generates various reports and dashboards:

- **Health Reports**: `/workspace/orchestration/logs/health_reports/`
- **Monitoring Dashboard**: `/workspace/orchestration/logs/monitoring_dashboard.json`
- **Scaling Reports**: `/workspace/orchestration/logs/scaling_trends.json`
- **Debug Sessions**: `/workspace/orchestration/logs/debug_sessions/`
- **Status Reports**: `/workspace/orchestration/logs/reports/`

## Alerting

The system supports multiple alerting channels:

1. **Email Alerts**: SMTP configuration in `services.yaml`
2. **Webhook Alerts**: HTTP POST to configured endpoints
3. **Log-based Alerts**: Error patterns in log files
4. **System Alerts**: Resource threshold violations

## Error Handling

### Service Failure Recovery
- Automatic restart on health check failure
- Configurable restart attempts
- Graceful degradation during restarts
- Dependency-aware restart sequencing

### Data Protection
- Automated daily backups
- Backup integrity verification
- Point-in-time recovery capability
- Backup retention policy (default: 30 days)

### System Resilience
- Process isolation and supervision
- Resource monitoring and limits
- Automatic scaling for load handling
- Network connectivity monitoring

## Performance Optimization

### Scaling Decisions
- CPU usage thresholds (configurable)
- Memory usage thresholds
- Response time monitoring
- Error rate tracking
- Cooldown periods to prevent thrashing

### Resource Management
- Automatic log rotation and cleanup
- Metrics data retention limits
- Efficient health check scheduling
- Optimized dependency checking

## Security Considerations

### Access Control
- File permission validation
- Process ownership verification
- Secure credential handling
- Service isolation

### Data Protection
- Backup encryption support
- Secure communication protocols
- Log file sanitization
- Audit trail maintenance

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   ```bash
   # Check service logs
   ./orchestration/scripts/tail_logs.sh tail <service_name> 100
   
   # Check system resources
   ./orchestration/scripts/check_status.sh
   ```

2. **Health Checks Failing**
   ```bash
   # Run health check coordinator
   python3 /workspace/orchestration/scripts/health_check_coordinator.py --report
   
   # Check network connectivity
   python3 /workspace/orchestration/debugging/network_analyzer.py service <service_name>
   ```

3. **Scaling Issues**
   ```bash
   # Check scaling decisions
   python3 /workspace/orchestration/scripts/automated_scaling.py --report
   
   # Analyze scaling trends
   python3 /workspace/orchestration/scripts/automated_scaling.py --evaluate
   ```

4. **Backup/Restore Problems**
   ```bash
   # Verify backup integrity
   python3 /workspace/orchestration/scripts/backup_restore.py --action verify \
     --backup-file <backup_path>
   ```

### Debug Mode

Enable debug logging by setting environment variable:
```bash
export ORCHESTRATION_DEBUG=1
./orchestration/scripts/startup.sh
```

### System Diagnostics

Run comprehensive system diagnostics:
```bash
python3 /workspace/orchestration/debugging/service_inspector.py system
```

## Integration with Existing Services

The system is designed to work with any Python-based services that:
1. Have a main entry point (server.py, main.py, etc.)
2. Can respond to health check HTTP requests
3. Follow the directory structure pattern
4. Are compatible with process management

## Extending the System

### Adding New Services

1. Add service definition to `config/services.yaml`
2. Implement health endpoint (optional)
3. Ensure proper startup script exists
4. Configure dependencies if needed

### Custom Scaling Policies

Add scaling policies to the configuration:
```yaml
scaling:
  policies:
    - service: "my_service"
      min_instances: 1
      max_instances: 10
      cpu_threshold: 75
      memory_threshold: 85
      response_time_threshold: 1000
```

### Custom Monitoring Metrics

Extend monitoring system by adding new metric types in `monitoring_system.py`

### Custom Alert Channels

Add new alert handlers by extending the `MonitoringAlertingSystem` class

## Development and Testing

### Development Mode

Run services in development mode with debug logging:
```bash
export ORCHESTRATION_DEBUG=1
export ORCHESTRATION_DEV_MODE=1
./orchestration/scripts/startup.sh
```

### Testing

Run individual component tests:
```bash
# Test health check coordinator
python3 /workspace/orchestration/scripts/health_check_coordinator.py

# Test backup system
python3 /workspace/orchestration/scripts/backup_restore.py --action backup --target redis

# Test monitoring system
python3 /workspace/orchestration/scripts/monitoring_system.py --once
```

### Debug Sessions

Create debug sessions for troubleshooting:
```bash
python3 /workspace/orchestration/debugging/service_inspector.py session --create debug_001 --services redis pubsub
```

## Best Practices

1. **Service Design**
   - Implement health check endpoints
   - Use proper logging with structured formats
   - Handle graceful shutdown signals
   - Design for horizontal scaling

2. **Configuration Management**
   - Use environment variables for sensitive data
   - Keep configuration in version control
   - Use semantic versioning for config changes
   - Validate configuration on startup

3. **Monitoring and Alerting**
   - Set appropriate thresholds
   - Configure multiple alert channels
   - Monitor business metrics in addition to technical metrics
   - Regular review of alert effectiveness

4. **Backup and Recovery**
   - Test backup restore procedures regularly
   - Monitor backup success rates
   - Keep multiple backup locations
   - Document recovery procedures

5. **Security**
   - Regular security audits
   - Keep dependencies updated
   - Use principle of least privilege
   - Monitor access patterns

## Contributing

When extending the orchestration system:

1. Follow the existing code structure
2. Add comprehensive logging
3. Include error handling
4. Write unit tests for new features
5. Update documentation
6. Consider backwards compatibility

## License

This orchestration system is designed to be used as part of the broader project infrastructure.