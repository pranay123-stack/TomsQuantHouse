#!/bin/bash
"""
Service Status Check Script
Checks the status of all services and generates status reports
"""

set -e

# Configuration
ORCHESTRATOR_DIR="/workspace/orchestration"
LOG_DIR="$ORCHESTRATOR_DIR/logs"
PID_FILE="$ORCHESTRATOR_DIR/orchestrator.pid"
STATUS_FILE="$LOG_DIR/current_status.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_service() {
    local status=$1
    local service_name=$2
    local pid=$3
    local uptime=$4
    
    case $status in
        "running")
            echo -e "  ${GREEN}✓${NC} $service_name (PID: $pid) - $uptime"
            ;;
        "stopped")
            echo -e "  ${RED}✗${NC} $service_name - Stopped"
            ;;
        "starting")
            echo -e "  ${YELLOW}⟳${NC} $service_name (PID: $pid) - Starting"
            ;;
        "unhealthy")
            echo -e "  ${RED}⚠${NC} $service_name (PID: $pid) - Unhealthy"
            ;;
        *)
            echo -e "  ${BLUE}?${NC} $service_name - $status"
            ;;
    esac
}

# Check orchestrator status
check_orchestrator() {
    if [ -f "$PID_FILE" ]; then
        ORCHESTRATOR_PID=$(cat "$PID_FILE")
        if kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
            log_info "Service Orchestrator: Running (PID: $ORCHESTRATOR_PID)"
            return 0
        else
            log_warn "Service Orchestrator: PID file exists but process not running"
            return 1
        fi
    else
        log_error "Service Orchestrator: Not running (no PID file)"
        return 1
    fi
}

# Check individual service status
check_service() {
    local service_name=$1
    local service_dir="/workspace/code/$service_name"
    
    if [ ! -d "$service_dir" ]; then
        log_service "missing" "$service_name" "-" "-"
        return 1
    fi
    
    # Find Python processes for this service
    local pids=$(pgrep -f "python.*$service_dir" 2>/dev/null || true)
    
    if [ -z "$pids" ]; then
        log_service "stopped" "$service_name" "-" "-"
        return 1
    else
        # Get uptime for first process
        local pid=$(echo "$pids" | cut -d' ' -f1)
        local start_time=$(ps -p $pid -o lstart= 2>/dev/null || echo "unknown")
        local uptime="unknown"
        
        if [ "$start_time" != "unknown" ]; then
            # Calculate uptime (simplified)
            uptime="running"
        fi
        
        # Try health check
        if python3 -c "
import requests
try:
    response = requests.get('http://localhost:9000/health', timeout=2)
    print('healthy' if response.status_code == 200 else 'unhealthy')
except:
    print('no_endpoint')
" 2>/dev/null | grep -q "healthy"; then
            log_service "running" "$service_name" "$pid" "$uptime"
        else
            log_service "unhealthy" "$service_name" "$pid" "$uptime"
        fi
        
        return 0
    fi
}

# Generate detailed status report
generate_status_report() {
    log_info "Generating detailed status report..."
    
    local report_file="$STATUS_FILE"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Create JSON report
    cat > "$report_file" << EOF
{
  "timestamp": "$timestamp",
  "orchestrator": {
    "running": $([ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null && echo "true" || echo "false"),
    "pid": $([ -f "$PID_FILE" ] && echo "$(cat $PID_FILE)" || echo "null")
  },
  "services": [
EOF
    
    local first=true
    for service_dir in /workspace/code/*/; do
        service_name=$(basename "$service_dir")
        
        if [ "$first" = false ]; then
            echo "," >> "$report_file"
        fi
        first=false
        
        # Check service status
        local status="stopped"
        local pid="null"
        
        pids=$(pgrep -f "python.*$service_dir" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            status="running"
            pid=$(echo "$pids" | cut -d' ' -f1)
        fi
        
        cat >> "$report_file" << EOF
    {
      "name": "$service_name",
      "status": "$status",
      "pid": $pid,
      "directory": "$service_dir"
    }
EOF
    done
    
    cat >> "$report_file" << EOF

  ],
  "system": {
    "load_average": "$(uptime | awk -F'load average:' '{print $2}')",
    "memory_usage": "$(free -h | awk 'NR==2{printf "%.1f%%", $3/$2 * 100.0}')",
    "disk_usage": "$(df -h /workspace | awk 'NR==2{print $5}')"
  }
}
EOF
    
    log_info "Status report saved to: $report_file"
}

# Check system resources
check_system_resources() {
    log_info "System Resources:"
    
    # CPU Load
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    echo -e "  CPU Load Average: $load_avg"
    
    # Memory usage
    memory_info=$(free -h | awk 'NR==2{printf "Total: %s, Used: %s (%.1f%%), Available: %s", $2, $3, $3/$2 * 100.0, $7}')
    echo -e "  Memory: $memory_info"
    
    # Disk usage
    disk_info=$(df -h /workspace | awk 'NR==2{printf "Total: %s, Used: %s (%s), Available: %s", $2, $3, $5, $4}')
    echo -e "  Disk: $disk_info"
    
    # Network connections
    echo -e "  Network Connections: $(netstat -tn 2>/dev/null | grep ESTABLISHED | wc -l) established"
}

# Check logs for recent errors
check_recent_errors() {
    log_info "Recent Errors (last 100 lines):"
    
    local error_count=0
    
    for log_file in "$LOG_DIR"/*.log; do
        if [ -f "$log_file" ]; then
            errors=$(tail -100 "$log_file" | grep -i error | wc -l)
            if [ "$errors" -gt 0 ]; then
                error_count=$((error_count + errors))
                echo -e "  ${YELLOW}$(basename "$log_file")${NC}: $errors errors"
            fi
        fi
    done
    
    if [ "$error_count" -eq 0 ]; then
        echo -e "  ${GREEN}No recent errors found${NC}"
    fi
}

# Main status check function
main() {
    echo "=========================================="
    echo "Service Orchestration Status Check"
    echo "=========================================="
    echo "Timestamp: $(date)"
    echo ""
    
    # Check orchestrator
    check_orchestrator
    echo ""
    
    # Check system resources
    check_system_resources
    echo ""
    
    # Check services
    log_info "Service Status:"
    local running_count=0
    local total_count=0
    
    for service_dir in /workspace/code/*/; do
        service_name=$(basename "$service_dir")
        
        # Skip certain directories
        if [[ "$service_name" == "tests" || "$service_name" == "__pycache__" ]]; then
            continue
        fi
        
        total_count=$((total_count + 1))
        
        if check_service "$service_name"; then
            running_count=$((running_count + 1))
        fi
    done
    
    echo ""
    log_info "Service Summary: $running_count/$total_count services running"
    
    # Check recent errors
    echo ""
    check_recent_errors
    
    # Generate detailed report
    if [ "$1" = "--detailed" ]; then
        echo ""
        generate_status_report
    fi
    
    # Check orchestrator health if running
    if check_orchestrator; then
        echo ""
        log_info "Orchestrator Health Check:"
        
        # Check if orchestrator is responding
        if python3 -c "
import sys
import time
sys.path.append('$ORCHESTRATOR_DIR')
try:
    from orchestration.scripts.health_check_coordinator import HealthCheckCoordinator
    import asyncio
    async def quick_check():
        coordinator = HealthCheckCoordinator()
        report = await coordinator.generate_health_report()
        print('Health check coordinator responding')
        return True
    asyncio.run(quick_check())
except Exception as e:
    print(f'Health check error: {e}')
    sys.exit(1)
" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Health check coordinator responding"
        else
            echo -e "  ${YELLOW}!${NC} Health check coordinator not responding"
        fi
    fi
    
    echo ""
    echo "=========================================="
    echo "Status Check Complete"
    echo "=========================================="
    
    # Return appropriate exit code
    if [ "$running_count" -eq "$total_count" ] && check_orchestrator; then
        exit 0
    else
        exit 1
    fi
}

# Handle command line arguments
case "${1:-}" in
    "--help"|"-h")
        echo "Service Status Check Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --detailed    Generate detailed JSON status report"
        echo "  --help        Show this help message"
        echo ""
        echo "Without options, shows basic status summary"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac