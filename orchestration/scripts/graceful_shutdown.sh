#!/bin/bash
"""
Graceful Shutdown Script
Safely stops all services in reverse dependency order
"""

set -e

# Configuration
ORCHESTRATOR_DIR="/workspace/orchestration"
PID_FILE="$ORCHESTRATOR_DIR/orchestrator.pid"
MONITOR_PID_FILE="$ORCHESTRATOR_DIR/monitoring.pid"
SHUTDOWN_LOG="$ORCHESTRATOR_DIR/logs/shutdown.log"
MAX_SHUTDOWN_TIME=60  # Maximum seconds to wait for graceful shutdown

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log_shutdown() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$SHUTDOWN_LOG"
    echo -e "${GREEN}[SHUTDOWN]${NC} $1"
}

log_error_shutdown() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" >> "$SHUTDOWN_LOG"
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if orchestrator is running
if [ ! -f "$PID_FILE" ]; then
    log_shutdown "No orchestrator PID file found. Nothing to shutdown."
    exit 0
fi

ORCHESTRATOR_PID=$(cat "$PID_FILE")

if ! kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
    log_shutdown "Orchestrator process $ORCHESTRATOR_PID is not running. Cleaning up PID file."
    rm -f "$PID_FILE"
    exit 0
fi

log_shutdown "Initiating graceful shutdown of Service Orchestrator (PID: $ORCHESTRATOR_PID)"

# Send SIGTERM for graceful shutdown
log_shutdown "Sending SIGTERM to orchestrator..."
kill -TERM "$ORCHESTRATOR_PID"

# Wait for graceful shutdown with timeout
SHUTDOWN_START=$(date +%s)
SHUTDOWN_TIMEOUT=$((SHUTDOWN_START + MAX_SHUTDOWN_TIME))

while [ $(date +%s) -lt $SHUTDOWN_TIMEOUT ]; do
    if ! kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
        log_shutdown "Orchestrator shutdown gracefully completed"
        break
    fi
    
    sleep 2
    ELAPSED=$(( $(date +%s) - SHUTDOWN_START ))
    log_shutdown "Waiting for graceful shutdown... ($ELAPSED seconds elapsed)"
done

# Force kill if still running
if kill -0 "$ORCHESTRATOR_PID" 2>/dev/null; then
    log_error_shutdown "Graceful shutdown timeout exceeded. Force killing orchestrator..."
    kill -9 "$ORCHESTRATOR_PID"
    sleep 2
fi

# Clean up PID files
rm -f "$PID_FILE"

# Stop monitoring process
if [ -f "$MONITOR_PID_FILE" ]; then
    MONITOR_PID=$(cat "$MONITOR_PID_FILE")
    if kill -0 "$MONITOR_PID" 2>/dev/null; then
        log_shutdown "Stopping monitoring process (PID: $MONITOR_PID)..."
        kill -TERM "$MONITOR_PID" 2>/dev/null || true
        sleep 2
        kill -9 "$MONITOR_PID" 2>/dev/null || true
    fi
    rm -f "$MONITOR_PID_FILE"
fi

# Clean up any remaining service processes
log_shutdown "Cleaning up any remaining service processes..."

# Get all Python processes running from our services
for service_dir in /workspace/code/*/; do
    service_name=$(basename "$service_dir")
    
    # Skip certain directories
    if [[ "$service_name" == "tests" ]]; then
        continue
    fi
    
    # Find processes running from this service directory
    pids=$(pgrep -f "python.*$service_dir" 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        log_shutdown "Stopping remaining processes for $service_name..."
        for pid in $pids; do
            if kill -0 "$pid" 2>/dev/null; then
                log_shutdown "Terminating process $pid (service: $service_name)..."
                kill -TERM "$pid" 2>/dev/null || true
                sleep 1
                
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    log_shutdown "Force killing process $pid..."
                    kill -9 "$pid" 2>/dev/null || true
                fi
            fi
        done
    fi
done

# Additional cleanup for any remaining Python processes
log_shutdown "Performing final cleanup..."

# Find and clean up any remaining Python processes that might be related to services
remaining_pids=$(pgrep -f "python.*server.py" 2>/dev/null || true)

if [ -n "$remaining_pids" ]; then
    log_shutdown "Found additional service processes, cleaning up..."
    for pid in $remaining_pids; do
        if kill -0 "$pid" 2>/dev/null; then
            log_shutdown "Terminating process $pid..."
            kill -TERM "$pid" 2>/dev/null || true
            sleep 1
            kill -9 "$pid" 2>/dev/null || true
        fi
    done
fi

# Clean up lock files
rm -f "$ORCHESTRATOR_DIR/.startup.lock" 2>/dev/null || true

# Save shutdown timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S')" > "$ORCHESTRATOR_DIR/logs/last_shutdown"

log_shutdown "Graceful shutdown completed successfully"

# Optional: Generate final status report
if [ -f "/workspace/orchestration/scripts/generate_report.py" ]; then
    log_shutdown "Generating final status report..."
    python3 /workspace/orchestration/scripts/generate_report.py --final
fi

echo ""
echo "========================================"
echo "Service Orchestration System Stopped"
echo "========================================"
echo "Shutdown completed: $(date)"
echo "Final log: $SHUTDOWN_LOG"
echo "========================================"