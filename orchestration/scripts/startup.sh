#!/bin/bash
"""
Service Startup Script
Coordinates the initialization of all services in the correct order
"""

set -e

# Configuration
ORCHESTRATOR_DIR="/workspace/orchestration"
LOG_DIR="$ORCHESTRATOR_DIR/logs"
PID_FILE="$ORCHESTRATOR_DIR/orchestrator.pid"
CONFIG_FILE="$ORCHESTRATOR_DIR/config/services.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up startup process..."
    # Remove lock files if they exist
    rm -f "$ORCHESTRATOR_DIR/.startup.lock" 2>/dev/null || true
    # Stop services if we're interrupting
    if [ -f "$PID_FILE" ]; then
        log_warn "Orchestrator is running, shutting down gracefully..."
        ./scripts/graceful_shutdown.sh
    fi
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM EXIT

# Check if already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log_error "Orchestrator is already running (PID: $OLD_PID)"
        exit 1
    else
        log_warn "Stale PID file found, removing..."
        rm -f "$PID_FILE"
    fi
fi

# Create lock file
touch "$ORCHESTRATOR_DIR/.startup.lock"

# Initialize logging directory
mkdir -p "$LOG_DIR"
mkdir -p "$LOG_DIR/reports"
mkdir -p "$LOG_DIR/backups"

log_info "Starting Service Orchestration System"

# Validate configuration
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

log_info "Validating configuration..."
python3 -c "
import yaml
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
    
    if 'services' not in config:
        print('ERROR: No services defined in configuration')
        sys.exit(1)
    
    print(f'Configuration valid. Found {len(config[\"services\"])} services.')
    
    # Check for circular dependencies
    services = config['services']
    visited = set()
    temp_visited = set()
    
    def check_deps(service_name):
        if service_name in temp_visited:
            print(f'ERROR: Circular dependency detected involving {service_name}')
            sys.exit(1)
        if service_name in visited:
            return
        
        temp_visited.add(service_name)
        deps = services[service_name].get('dependencies', [])
        for dep in deps:
            check_deps(dep)
        temp_visited.remove(service_name)
        visited.add(service_name)
    
    for service_name in services:
        check_deps(service_name)
    
    print('No circular dependencies detected.')

except Exception as e:
    print(f'Configuration validation failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    log_error "Configuration validation failed"
    exit 1
fi

log_info "Configuration validation passed"

# Pre-flight checks
log_info "Running pre-flight checks..."

# Check Python dependencies
python3 -c "
import sys
missing_deps = []

try:
    import psutil
except ImportError:
    missing_deps.append('psutil')

try:
    import requests
except ImportError:
    missing_deps.append('requests')

try:
    import schedule
except ImportError:
    missing_deps.append('schedule')

try:
    import yaml
except ImportError:
    missing_deps.append('pyyaml')

if missing_deps:
    print(f'Missing dependencies: {missing_deps}')
    sys.exit(1)
else:
    print('All dependencies available')
"

if [ $? -ne 0 ]; then
    log_error "Missing Python dependencies. Installing..."
    pip install psutil requests schedule pyyaml
fi

# Check system resources
log_info "Checking system resources..."
TOTAL_MEM=$(free -m | awk 'NR==2{printf "%.0f", $2*0.8}')
AVAILABLE_MEM=$(free -m | awk 'NR==2{printf "%.0f", $7}')

if [ "$AVAILABLE_MEM" -lt "$TOTAL_MEM" ]; then
    log_warn "Low memory available: ${AVAILABLE_MEM}MB (threshold: ${TOTAL_MEM}MB)"
else
    log_info "Sufficient memory available: ${AVAILABLE_MEM}MB"
fi

# Check disk space
DISK_USAGE=$(df -h /workspace | awk 'NR==2{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    log_error "Disk usage critical: ${DISK_USAGE}%"
    exit 1
elif [ "$DISK_USAGE" -gt 80 ]; then
    log_warn "Disk usage high: ${DISK_USAGE}%"
else
    log_info "Disk usage acceptable: ${DISK_USAGE}%"
fi

# Initialize service directories
log_info "Initializing service directories..."
for service_dir in /workspace/code/*/; do
    service_name=$(basename "$service_dir")
    if [ -d "$service_dir" ] && [ "$service_name" != "tests" ]; then
        # Create logs directory for each service
        mkdir -p "$service_dir/logs"
        # Create data directory for services that need it
        mkdir -p "$service_dir/data"
        log_debug "Initialized directory for $service_name"
    fi
done

# Setup monitoring
log_info "Setting up monitoring..."
if [ ! -f "/workspace/orchestration/monitoring/monitoring.sh" ]; then
    log_warn "Monitoring script not found, creating basic monitoring..."
    mkdir -p /workspace/orchestration/monitoring
    cat > /workspace/orchestration/monitoring/monitoring.sh << 'EOF'
#!/bin/bash
# Basic monitoring script

LOG_FILE="/workspace/orchestration/logs/monitor.log"

log_monitor() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Monitor CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
log_monitor "CPU_USAGE:$CPU_USAGE"

# Monitor memory usage
MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
log_monitor "MEMORY_USAGE:$MEM_USAGE"

# Monitor disk usage
DISK_USAGE=$(df -h /workspace | awk 'NR==2{print $5}' | sed 's/%//')
log_monitor "DISK_USAGE:$DISK_USAGE"
EOF
    chmod +x /workspace/orchestration/monitoring/monitoring.sh
fi

# Create environment file
log_info "Setting up environment..."
cat > /workspace/orchestration/.env << EOF
# Service Orchestration Environment
ORCHESTRATOR_DIR=$ORCHESTRATOR_DIR
LOG_DIR=$LOG_DIR
PID_FILE=$PID_FILE
CONFIG_FILE=$CONFIG_FILE
PYTHONPATH=$PYTHONPATH:/workspace

# Service URLs
REDIS_URL=redis://localhost:6379
PUBSUB_URL=http://localhost:8080
SECURITY_URL=http://localhost:8000
LANGGRAPH_API_URL=http://localhost:9000
LETTA_API_URL=http://localhost:9001
ASYMEDGE_API_URL=http://localhost:9002
COMPOSIO_URL=http://localhost:9003
CREWAI_URL=http://localhost:9004
ABACUS_AI_URL=http://localhost:9005
WORKFLOWS_URL=http://localhost:9006
BROWSER_URL=http://localhost:9007

# Monitoring
MONITORING_ENABLED=true
METRICS_INTERVAL=60
EOF

# Load environment
set -a
source /workspace/orchestration/.env
set +a

# Start the orchestrator
log_info "Starting Service Orchestrator..."

# Start monitoring in background
/workspace/orchestration/monitoring/monitoring.sh &
MONITOR_PID=$!
echo $MONITOR_PID > /workspace/orchestration/monitoring.pid

# Start the main orchestrator
cd "$ORCHESTRATOR_DIR"
python3 orchestrator.py &
ORCHESTRATOR_PID=$!

# Save PIDs
echo $ORCHESTRATOR_PID > "$PID_FILE"

# Wait a moment for startup
sleep 3

# Check if orchestrator started successfully
if kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
    log_info "Service Orchestrator started successfully (PID: $ORCHESTRATOR_PID)"
    log_info "Monitoring started (PID: $MONITOR_PID)"
    
    # Generate initial status
    log_info "Generating initial status report..."
    sleep 2
    python3 -c "
import json
import time
import requests

try:
    # Wait a bit for services to initialize
    time.sleep(5)
    
    # Try to get status
    response = requests.get('http://localhost:9000/health', timeout=5)
    if response.status_code == 200:
        print('Services are responding to health checks')
    else:
        print(f'Health check returned: {response.status_code}')
except Exception as e:
    print(f'Status check failed (expected during startup): {e}')
"
    
    log_info "==============================================="
    log_info "Service Orchestration System Started Successfully"
    log_info "==============================================="
    log_info "Orchestrator PID: $ORCHESTRATOR_PID"
    log_info "Monitor PID: $MONITOR_PID"
    log_info "Logs: $LOG_DIR"
    log_info "Status reports: $LOG_DIR/reports"
    log_info "Configuration: $CONFIG_FILE"
    log_info ""
    log_info "Management Commands:"
    log_info "  Check status: ./scripts/check_status.sh"
    log_info "  Stop services: ./scripts/graceful_shutdown.sh"
    log_info "  Restart service: ./scripts/restart_service.sh <service_name>"
    log_info "  View logs: ./scripts/tail_logs.sh [service_name]"
    log_info "==============================================="
    
    # Remove startup lock
    rm -f "$ORCHESTRATOR_DIR/.startup.lock"
    
    # Keep script running for now
    log_info "Orchestrator is running. Press Ctrl+C to stop all services."
    
    # Wait for orchestrator
    wait "$ORCHESTRATOR_PID"
    
else
    log_error "Failed to start Service Orchestrator"
    
    # Clean up
    kill $MONITOR_PID 2>/dev/null || true
    rm -f "$PID_FILE" /workspace/orchestration/monitoring.pid
    
    exit 1
fi