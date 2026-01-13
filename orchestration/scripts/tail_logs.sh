#!/bin/bash
"""
Log Tailing Script
Follow and analyze service logs in real-time
"""

set -e

# Configuration
ORCHESTRATOR_DIR="/workspace/orchestration"
LOG_DIR="$ORCHESTRATOR_DIR/logs"
SERVICE_LOG_DIR="/workspace/code"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Colorize log lines based on content
colorize_line() {
    local line="$1"
    
    if [[ "$line" =~ ERROR ]]; then
        echo -e "${RED}$line${NC}"
    elif [[ "$line" =~ WARN ]]; then
        echo -e "${YELLOW}$line${NC}"
    elif [[ "$line" =~ INFO ]]; then
        echo -e "${GREEN}$line${NC}"
    elif [[ "$line" =~ DEBUG ]]; then
        echo -e "${BLUE}$line${NC}"
    elif [[ "$line" =~ CRITICAL ]]; then
        echo -e "${RED}$line${NC}"
    elif [[ "$line" =~ FATAL ]]; then
        echo -e "${RED}$line${NC}"
    else
        echo "$line"
    fi
}

# Filter log lines
filter_logs() {
    local filter="$1"
    local lines="$2"
    
    if [ -n "$filter" ]; then
        grep -i "$filter" || true
    else
        cat
    fi
}

# Tail orchestrator logs
tail_orchestrator_logs() {
    local follow=$1
    local lines=$2
    local filter=$3
    
    local log_file="$LOG_DIR/orchestrator.log"
    
    if [ ! -f "$log_file" ]; then
        log_error "Orchestrator log file not found: $log_file"
        return 1
    fi
    
    if [ "$follow" = "true" ]; then
        log_info "Following orchestrator logs (Ctrl+C to stop)..."
        tail -f "$log_file" | while IFS= read -r line; do
            if [ -n "$filter" ]; then
                echo "$line" | grep -i "$filter" | while IFS= read -r filtered_line; do
                    colorize_line "$filtered_line"
                done
            else
                colorize_line "$line"
            fi
        done
    else
        log_info "Last $lines lines of orchestrator logs:"
        head -n "$lines" "$log_file" | while IFS= read -r line; do
            colorize_line "$line"
        done
    fi
}

# Tail service logs
tail_service_logs() {
    local service_name=$1
    local follow=$2
    local lines=$3
    local filter=$4
    
    # Check if service exists
    local service_dir="$SERVICE_LOG_DIR/$service_name"
    if [ ! -d "$service_dir" ]; then
        log_error "Service not found: $service_name"
        log_info "Available services:"
        list_services
        return 1
    fi
    
    # Try different log file locations
    local log_files=(
        "$LOG_DIR/${service_name}.log"
        "$service_dir/logs/${service_name}.log"
        "$service_dir/logs/app.log"
        "$service_dir/${service_name}.log"
    )
    
    local log_file=""
    for file in "${log_files[@]}"; do
        if [ -f "$file" ]; then
            log_file="$file"
            break
        fi
    done
    
    if [ -z "$log_file" ]; then
        log_error "No log file found for service: $service_name"
        return 1
    fi
    
    log_info "Tailing logs for $service_name from: $log_file"
    
    if [ "$follow" = "true" ]; then
        log_info "Following logs (Ctrl+C to stop)..."
        tail -f "$log_file" | while IFS= read -r line; do
            if [ -n "$filter" ]; then
                echo "$line" | grep -i "$filter" | while IFS= read -r filtered_line; do
                    colorize_line "$filtered_line"
                done
            else
                colorize_line "$line"
            fi
        done
    else
        log_info "Last $lines lines of $service_name logs:"
        head -n "$lines" "$log_file" | while IFS= read -r line; do
            colorize_line "$line"
        done
    fi
}

# Tail all service logs
tail_all_logs() {
    local follow=$1
    local lines=$2
    local filter=$3
    
    log_info "Tailing logs for all services..."
    
    if [ "$follow" = "true" ]; then
        # Follow all logs
        {
            for service_dir in "$SERVICE_LOG_DIR"/*/; do
                service_name=$(basename "$service_dir")
                
                # Skip certain directories
                if [[ "$service_name" == "tests" || "$service_name" == "__pycache__" ]]; then
                    continue
                fi
                
                # Try to find log file
                local log_files=(
                    "$LOG_DIR/${service_name}.log"
                    "$service_dir/logs/${service_name}.log"
                    "$service_dir/logs/app.log"
                    "$service_dir/${service_name}.log"
                )
                
                local log_file=""
                for file in "${log_files[@]}"; do
                    if [ -f "$file" ]; then
                        log_file="$file"
                        break
                    fi
                done
                
                if [ -n "$log_file" ]; then
                    echo -e "${CYAN}=== $service_name logs ===${NC}"
                    tail -f "$log_file" 2>/dev/null | while IFS= read -r line; do
                        echo "[$service_name] $(colorize_line "$line")"
                    done &
                fi
            done
        } | {
            if [ -n "$filter" ]; then
                grep -i "$filter" || true
            else
                cat
            fi
        }
        
        # Wait for user interrupt
        log_info "Following all service logs (Ctrl+C to stop)..."
        wait
    else
        # Show last lines from all services
        for service_dir in "$SERVICE_LOG_DIR"/*/; do
            service_name=$(basename "$service_dir")
            
            # Skip certain directories
            if [[ "$service_name" == "tests" || "$service_name" == "__pycache__" ]]; then
                continue
            fi
            
            # Try to find log file
            local log_files=(
                "$LOG_DIR/${service_name}.log"
                "$service_dir/logs/${service_name}.log"
                "$service_dir/logs/app.log"
                "$service_dir/${service_name}.log"
            )
            
            local log_file=""
            for file in "${log_files[@]}"; do
                if [ -f "$file" ]; then
                    log_file="$file"
                    break
                fi
            done
            
            if [ -n "$log_file" ]; then
                echo -e "${CYAN}=== $service_name logs ===${NC}"
                head -n "$lines" "$log_file" | while IFS= read -r line; do
                    echo "[$service_name] $(colorize_line "$line")"
                done
                echo ""
            fi
        done
    fi
}

# List services and their log files
list_services() {
    log_info "Available services and log files:"
    
    for service_dir in "$SERVICE_LOG_DIR"/*/; do
        if [ -d "$service_dir" ]; then
            service_name=$(basename "$service_dir")
            
            # Skip certain directories
            if [[ "$service_name" == "tests" || "$service_name" == "__pycache__" ]]; then
                continue
            fi
            
            # Try to find log file
            local log_files=(
                "$LOG_DIR/${service_name}.log"
                "$service_dir/logs/${service_name}.log"
                "$service_dir/logs/app.log"
                "$service_dir/${service_name}.log"
            )
            
            local log_file="[no log file found]"
            for file in "${log_files[@]}"; do
                if [ -f "$file" ]; then
                    log_file="$file"
                    break
                fi
            done
            
            # Check if service is running
            local status="stopped"
            if pgrep -f "python.*$service_dir" > /dev/null; then
                status="running"
            fi
            
            echo -e "  ${GREEN}$service_name${NC} - $status - $log_file"
        fi
    done
}

# Analyze logs for errors and patterns
analyze_logs() {
    local service_name=$1
    local analysis_type=$2
    
    case "$analysis_type" in
        "errors")
            log_info "Analyzing errors in $service_name logs..."
            
            local log_files=(
                "$LOG_DIR/${service_name}.log"
                "$SERVICE_LOG_DIR/$service_name/logs/${service_name}.log"
                "$SERVICE_LOG_DIR/$service_name/logs/app.log"
                "$SERVICE_LOG_DIR/$service_name/${service_name}.log"
            )
            
            local error_count=0
            for log_file in "${log_files[@]}"; do
                if [ -f "$log_file" ]; then
                    local errors=$(grep -i "error" "$log_file" | wc -l)
                    error_count=$((error_count + errors))
                    
                    if [ "$errors" -gt 0 ]; then
                        echo -e "${RED}Errors in $log_file: $errors${NC}"
                        echo "Recent errors:"
                        grep -i "error" "$log_file" | tail -5 | while IFS= read -r line; do
                            echo -e "${RED}  $line${NC}"
                        done
                    fi
                fi
            done
            
            if [ "$error_count" -eq 0 ]; then
                echo -e "${GREEN}No errors found${NC}"
            else
                echo -e "${YELLOW}Total errors: $error_count${NC}"
            fi
            ;;
        "patterns")
            log_info "Analyzing patterns in $service_name logs..."
            
            local log_files=(
                "$LOG_DIR/${service_name}.log"
                "$SERVICE_LOG_DIR/$service_name/logs/${service_name}.log"
                "$SERVICE_LOG_DIR/$service_name/logs/app.log"
                "$SERVICE_LOG_DIR/$service_name/${service_name}.log"
            )
            
            for log_file in "${log_files[@]}"; do
                if [ -f "$log_file" ]; then
                    echo -e "${CYAN}Patterns in $log_file:${NC}"
                    echo "Top log levels:"
                    grep -oP '\[\K\w+' "$log_file" | sort | uniq -c | sort -nr | head -10
                    echo ""
                fi
            done
            ;;
        "recent")
            log_info "Recent activity in $service_name logs..."
            
            local log_files=(
                "$LOG_DIR/${service_name}.log"
                "$SERVICE_LOG_DIR/$service_name/logs/${service_name}.log"
                "$SERVICE_LOG_DIR/$service_name/logs/app.log"
                "$SERVICE_LOG_DIR/$service_name/${service_name}.log"
            )
            
            for log_file in "${log_files[@]}"; do
                if [ -f "$log_file" ]; then
                    echo -e "${CYAN}Recent activity in $log_file:${NC}"
                    tail -10 "$log_file" | while IFS= read -r line; do
                        colorize_line "  $line"
                    done
                    echo ""
                fi
            done
            ;;
    esac
}

# Real-time log monitoring with alerts
monitor_logs() {
    local service_name=$1
    
    log_info "Starting real-time log monitoring for $service_name..."
    log_info "Press Ctrl+C to stop monitoring"
    echo ""
    
    local log_files=(
        "$LOG_DIR/${service_name}.log"
        "$SERVICE_LOG_DIR/$service_name/logs/${service_name}.log"
        "$SERVICE_LOG_DIR/$service_name/logs/app.log"
        "$SERVICE_LOG_DIR/$service_name/${service_name}.log"
    )
    
    for log_file in "${log_files[@]}"; do
        if [ -f "$log_file" ]; then
            echo -e "${CYAN}Monitoring: $log_file${NC}"
            tail -f "$log_file" | while IFS= read -r line; do
                # Alert on critical messages
                if [[ "$line" =~ (ERROR|CRITICAL|FATAL) ]]; then
                    echo -e "${RED}[ALERT] $line${NC}"
                elif [[ "$line" =~ WARNING ]]; then
                    echo -e "${YELLOW}[WARNING] $line${NC}"
                else
                    colorize_line "$line"
                fi
            done &
        fi
    done
    
    wait
}

# Main function
main() {
    local command="${1:-help}"
    local service_name="${2:-}"
    local lines="${3:-50}"
    local filter="$4"
    local follow="false"
    
    # Check for -f or --follow flag
    for arg in "$@"; do
        if [[ "$arg" == "-f" || "$arg" == "--follow" ]]; then
            follow="true"
            break
        fi
    done
    
    case "$command" in
        "--help"|"-h"|"help")
            echo "Log Tailing Script"
            echo ""
            echo "Usage: $0 <command> [service_name] [options]"
            echo ""
            echo "Commands:"
            echo "  list                           List all services and their log files"
            echo "  tail <service_name> [-f]       Tail logs for a specific service"
            echo "  tail-all [-f]                  Tail logs for all services"
            echo "  tail-orchestrator [-f]         Tail orchestrator logs"
            echo "  analyze <service_name> errors  Analyze errors in service logs"
            echo "  analyze <service_name> patterns Analyze patterns in service logs"
            echo "  analyze <service_name> recent  Show recent activity"
            echo "  monitor <service_name>         Real-time monitoring with alerts"
            echo ""
            echo "Options:"
            echo "  -f, --follow                   Follow logs in real-time"
            echo "  <number>                       Number of lines to show (default: 50)"
            echo "  <filter>                       Filter logs by pattern"
            echo ""
            echo "Examples:"
            echo "  $0 list"
            echo "  $0 tail redis -f"
            echo "  $0 tail redis 100"
            echo "  $0 tail redis 50 error"
            echo "  $0 analyze redis errors"
            echo "  $0 monitor redis"
            echo ""
            exit 0
            ;;
        "list")
            list_services
            ;;
        "tail")
            if [ -z "$service_name" ]; then
                log_error "Service name required"
                exit 1
            fi
            if [ "$service_name" = "orchestrator" ]; then
                tail_orchestrator_logs "$follow" "$lines" "$filter"
            else
                tail_service_logs "$service_name" "$follow" "$lines" "$filter"
            fi
            ;;
        "tail-all")
            tail_all_logs "$follow" "$lines" "$filter"
            ;;
        "tail-orchestrator")
            tail_orchestrator_logs "$follow" "$lines" "$filter"
            ;;
        "analyze")
            if [ -z "$service_name" ]; then
                log_error "Service name required"
                exit 1
            fi
            local analysis_type="${3:-errors}"
            analyze_logs "$service_name" "$analysis_type"
            ;;
        "monitor")
            if [ -z "$service_name" ]; then
                log_error "Service name required"
                exit 1
            fi
            monitor_logs "$service_name"
            ;;
        *)
            log_error "Unknown command: $command"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"