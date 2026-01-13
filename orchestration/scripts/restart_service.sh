#!/bin/bash
"""
Service Restart Script
Restarts individual services or all services
"""

set -e

# Configuration
ORCHESTRATOR_DIR="/workspace/orchestration"
LOG_DIR="$ORCHESTRATOR_DIR/logs"
PID_FILE="$ORCHESTRATOR_DIR/orchestrator.pid"

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

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if orchestrator is running
check_orchestrator() {
    if [ ! -f "$PID_FILE" ]; then
        return 1
    fi
    
    ORCHESTRATOR_PID=$(cat "$PID_FILE")
    if kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Restart orchestrator
restart_orchestrator() {
    log_info "Restarting Service Orchestrator..."
    
    if check_orchestrator; then
        log_info "Stopping orchestrator gracefully..."
        "$ORCHESTRATOR_DIR/scripts/graceful_shutdown.sh" > /dev/null 2>&1 || true
        sleep 3
    fi
    
    log_info "Starting orchestrator..."
    cd "$ORCHESTRATOR_DIR"
    python3 orchestrator.py &
    ORCHESTRATOR_PID=$!
    echo $ORCHESTRATOR_PID > "$PID_FILE"
    
    # Wait for startup
    sleep 5
    
    if kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
        log_success "Orchestrator restarted successfully (PID: $ORCHESTRATOR_PID)"
        return 0
    else
        log_error "Failed to restart orchestrator"
        return 1
    fi
}

# Stop a service
stop_service() {
    local service_name=$1
    local service_dir="/workspace/code/$service_name"
    
    if [ ! -d "$service_dir" ]; then
        log_error "Service directory not found: $service_dir"
        return 1
    fi
    
    log_info "Stopping service: $service_name"
    
    # Find and kill processes
    pids=$(pgrep -f "python.*$service_dir" 2>/dev/null || true)
    
    if [ -z "$pids" ]; then
        log_warn "Service $service_name is not running"
        return 0
    fi
    
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Terminating process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "Graceful shutdown timeout, forcing termination..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
        fi
    done
    
    # Clean up any remaining processes
    pkill -f "python.*$service_dir" 2>/dev/null || true
    
    log_success "Service $service_name stopped"
    return 0
}

# Start a service
start_service() {
    local service_name=$1
    local service_dir="/workspace/code/$service_name"
    
    if [ ! -d "$service_dir" ]; then
        log_error "Service directory not found: $service_dir"
        return 1
    fi
    
    # Check if service is already running
    if pgrep -f "python.*$service_dir" > /dev/null; then
        log_warn "Service $service_name is already running"
        return 0
    fi
    
    log_info "Starting service: $service_name"
    
    # Look for service startup script
    local startup_script=""
    for script in "server.py" "main.py" "app.py" "__main__.py"; do
        if [ -f "$service_dir/$script" ]; then
            startup_script="$script"
            break
        fi
    done
    
    if [ -z "$startup_script" ]; then
        log_error "No startup script found for service $service_name"
        return 1
    fi
    
    # Start the service
    cd "$service_dir"
    nohup python3 "$startup_script" > "$LOG_DIR/${service_name}.log" 2>&1 &
    local pid=$!
    
    # Wait a moment to see if it starts successfully
    sleep 3
    
    if kill -0 "$pid" 2>/dev/null; then
        log_success "Service $service_name started successfully (PID: $pid)"
        
        # Log the PID for reference
        echo "$service_name:$pid" >> "$LOG_DIR/service_pids.log"
        return 0
    else
        log_error "Service $service_name failed to start"
        return 1
    fi
}

# Restart a single service
restart_service() {
    local service_name=$1
    
    if [ -z "$service_name" ]; then
        log_error "Service name is required"
        return 1
    fi
    
    log_info "Restarting service: $service_name"
    
    # Stop the service
    if ! stop_service "$service_name"; then
        return 1
    fi
    
    # Wait a moment before starting
    sleep 2
    
    # Start the service
    if ! start_service "$service_name"; then
        return 1
    fi
    
    log_success "Service $service_name restarted successfully"
    return 0
}

# List available services
list_services() {
    log_info "Available services:"
    
    for service_dir in /workspace/code/*/; do
        if [ -d "$service_dir" ]; then
            service_name=$(basename "$service_dir")
            
            # Skip certain directories
            if [[ "$service_name" == "tests" || "$service_name" == "__pycache__" ]]; then
                continue
            fi
            
            # Check if service is running
            local status="stopped"
            if pgrep -f "python.*$service_dir" > /dev/null; then
                status="running"
            fi
            
            echo -e "  $service_name - $status"
        fi
    done
}

# Restart all services
restart_all_services() {
    log_info "Restarting all services..."
    
    local failed_services=()
    
    # Get list of services
    local services=()
    for service_dir in /workspace/code/*/; do
        if [ -d "$service_dir" ]; then
            service_name=$(basename "$service_dir")
            
            # Skip certain directories
            if [[ "$service_name" == "tests" || "$service_name" == "__pycache__" ]]; then
                continue
            fi
            
            services+=("$service_name")
        fi
    done
    
    # Stop all services
    log_info "Stopping all services..."
    for service in "${services[@]}"; do
        stop_service "$service" || true
    done
    
    # Wait for cleanup
    sleep 3
    
    # Start all services
    log_info "Starting all services..."
    for service in "${services[@]}"; do
        if ! start_service "$service"; then
            failed_services+=("$service")
        fi
    done
    
    # Report results
    if [ ${#failed_services[@]} -eq 0 ]; then
        log_success "All services restarted successfully"
        return 0
    else
        log_error "Failed to restart services: ${failed_services[*]}"
        return 1
    fi
}

# Force restart (ignore errors)
force_restart() {
    local service_name=$1
    
    log_warn "Force restarting service: $service_name"
    
    # Kill all processes for this service
    pkill -9 -f "python.*$service_name" 2>/dev/null || true
    pkill -9 -f "$service_name" 2>/dev/null || true
    
    # Wait and start
    sleep 2
    start_service "$service_name"
}

# Get service logs
show_logs() {
    local service_name=$1
    local lines=${2:-50}
    
    local log_file="$LOG_DIR/${service_name}.log"
    
    if [ ! -f "$log_file" ]; then
        log_error "Log file not found: $log_file"
        return 1
    fi
    
    log_info "Showing last $lines lines of $service_name logs:"
    echo ""
    
    if command -v tail > /dev/null; then
        tail -n "$lines" "$log_file"
    else
        head -n "$lines" "$log_file"
    fi
}

# Main function
main() {
    case "${1:-}" in
        "--help"|"-h")
            echo "Service Restart Script"
            echo ""
            echo "Usage: $0 <command> [service_name] [options]"
            echo ""
            echo "Commands:"
            echo "  list                           List all available services"
            echo "  restart <service_name>         Restart a specific service"
            echo "  restart-all                    Restart all services"
            echo "  restart-orchestrator           Restart the orchestrator"
            echo "  force <service_name>           Force restart (kill and start)"
            echo "  logs <service_name> [lines]    Show service logs"
            echo "  stop <service_name>            Stop a service"
            echo "  start <service_name>           Start a service"
            echo ""
            echo "Examples:"
            echo "  $0 list"
            echo "  $0 restart redis"
            echo "  $0 restart-all"
            echo "  $0 logs redis 100"
            echo ""
            exit 0
            ;;
        "list")
            list_services
            ;;
        "restart")
            if [ -z "$2" ]; then
                log_error "Service name required"
                exit 1
            fi
            restart_service "$2"
            ;;
        "restart-all")
            restart_all_services
            ;;
        "restart-orchestrator")
            restart_orchestrator
            ;;
        "force")
            if [ -z "$2" ]; then
                log_error "Service name required"
                exit 1
            fi
            force_restart "$2"
            ;;
        "logs")
            if [ -z "$2" ]; then
                log_error "Service name required"
                exit 1
            fi
            show_logs "$2" "${3:-50}"
            ;;
        "stop")
            if [ -z "$2" ]; then
                log_error "Service name required"
                exit 1
            fi
            stop_service "$2"
            ;;
        "start")
            if [ -z "$2" ]; then
                log_error "Service name required"
                exit 1
            fi
            start_service "$2"
            ;;
        *)
            echo "Unknown command: ${1:-}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"