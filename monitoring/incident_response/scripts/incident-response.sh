#!/bin/bash
# Automated Incident Response Script for Trading System

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"
TEMPLATES_DIR="$SCRIPT_DIR/templates"
LOG_FILE="/var/log/incident-response.log"

# Load configuration
source "$CONFIG_DIR/incident-response.conf"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Send notification function
send_notification() {
    local severity="$1"
    local title="$2"
    local message="$3"
    local details="${4:-}"
    
    log "Sending notification: $severity - $title"
    
    # Send to Slack
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local color="good"
        case "$severity" in
            "critical") color="danger" ;;
            "warning") color="warning" ;;
            "info") color="good" ;;
        esac
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"$color\",\"title\":\"$title\",\"text\":\"$message\",\"fields\":[$(if [[ -n "$details" ]]; then echo "{\"title\":\"Details\",\"value\":\"$details\",\"short\":false}"; fi)}],\"footer\":\"Incident Response System\",\"ts\":$(date +%s)}]" \
            "$SLACK_WEBHOOK_URL" || log "Failed to send Slack notification"
    fi
    
    # Send to PagerDuty
    if [[ -n "${PAGERDUTY_API_KEY:-}" && "$severity" == "critical" ]]; then
        local event_type="trigger"
        if [[ "${INCIDENT_STATUS:-}" == "resolved" ]]; then
            event_type="resolve"
        fi
        
        curl -X POST -H "Content-type: application/json" \
            -d "{
                \"event_type\": \"$event_type\",
                \"dedup_key\": \"${INCIDENT_ID:-trading-system-alert}\",
                \"payload\": {
                    \"summary\": \"$title\",
                    \"source\": \"${HOSTNAME:-trading-system}\",
                    \"severity\": \"$severity\",
                    \"custom_details\": {
                        \"message\": \"$message\",
                        \"details\": \"$details\"
                    }
                }
            }" \
            "https://events.pagerduty.com/v2/enqueue" || log "Failed to send PagerDuty notification"
    fi
    
    # Send to email
    if [[ -n "${EMAIL_SMTP_SERVER:-}" ]]; then
        local subject="[$severity] $title"
        local body="Alert: $title\n\nMessage: $message\n\nDetails: $details\n\nTimestamp: $(date)\n\nHostname: ${HOSTNAME:-unknown}"
        
        if command -v mail >/dev/null 2>&1; then
            echo "$body" | mail -s "$subject" "$EMAIL_RECIPIENTS" || log "Failed to send email notification"
        fi
    fi
    
    # Send to Microsoft Teams
    if [[ -n "${TEAMS_WEBHOOK_URL:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"@type\": \"MessageCard\",
                \"@context\": \"http://schema.org/extensions\",
                \"themeColor\": \"$([ \"$severity\" = \"critical\" ] && echo \"FF0000\" || echo \"FFFF00\")\",
                \"summary\": \"$title\",
                \"sections\": [{
                    \"activityTitle\": \"$title\",
                    \"text\": \"$message\",
                    \"facts\": [{
                        \"name\": \"Severity\",
                        \"value\": \"$severity\"
                    }, {
                        \"name\": \"Timestamp\",
                        \"value\": \"$(date)\"
                    }]
                }]
            }" \
            "$TEAMS_WEBHOOK_URL" || log "Failed to send Teams notification"
    fi
}

# Check system health
check_system_health() {
    local service="$1"
    local max_attempts="${2:-3}"
    local timeout="${3:-30}"
    
    log "Checking health for service: $service"
    
    for attempt in $(seq 1 "$max_attempts"); do
        if curl -f -s --max-time "$timeout" "http://$service/health" >/dev/null 2>&1; then
            log "Service $service is healthy"
            return 0
        else
            log "Health check failed for $service (attempt $attempt/$max_attempts)"
            sleep 5
        fi
    done
    
    log "Service $service is unhealthy after $max_attempts attempts"
    return 1
}

# Restart service
restart_service() {
    local service="$1"
    log "Attempting to restart service: $service"
    
    if command -v docker >/dev/null 2>&1; then
        # Docker service restart
        if docker ps --format '{{.Names}}' | grep -q "$service"; then
            docker restart "$service" || {
                log "Failed to restart Docker service $service"
                return 1
            }
            log "Successfully restarted Docker service $service"
            return 0
        fi
    fi
    
    if command -v systemctl >/dev/null 2>&1; then
        # Systemd service restart
        systemctl restart "$service" || {
            log "Failed to restart systemd service $service"
            return 1
        }
        log "Successfully restarted systemd service $service"
        return 0
    fi
    
    log "No supported service manager found for $service"
    return 1
}

# Scale service
scale_service() {
    local service="$1"
    local replicas="$2"
    log "Scaling service $service to $replicas replicas"
    
    if command -v kubectl >/dev/null 2>&1; then
        # Kubernetes scaling
        kubectl scale deployment "$service" --replicas="$replicas" || {
            log "Failed to scale Kubernetes deployment $service"
            return 1
        }
        log "Successfully scaled deployment $service to $replicas replicas"
        return 0
    fi
    
    log "Kubernetes not available for scaling"
    return 1
}

# Collect diagnostics
collect_diagnostics() {
    local output_dir="$1"
    local timestamp="$(date +%Y%m%d_%H%M%S)"
    local diag_dir="$output_dir/diagnostics_$timestamp"
    
    log "Collecting diagnostics to $diag_dir"
    mkdir -p "$diag_dir"
    
    # System information
    {
        echo "=== System Information ==="
        uname -a
        uptime
        df -h
        free -m
        ps aux --sort=-%mem | head -20
        netstat -tuln
    } > "$diag_dir/system_info.txt"
    
    # Docker containers
    if command -v docker >/dev/null 2>&1; then
        echo "=== Docker Containers ===" > "$diag_dir/docker_info.txt"
        docker ps -a >> "$diag_dir/docker_info.txt"
        echo "=== Docker Stats ===" >> "$diag_dir/docker_info.txt"
        docker stats --no-stream >> "$diag_dir/docker_info.txt"
    fi
    
    # Service logs (last 100 lines)
    for service in langgraph-api asymedge-api abacus-ai letta-server postgres redis nginx prometheus grafana; do
        if command -v docker >/dev/null 2>&1 && docker ps --format '{{.Names}}' | grep -q "$service"; then
            echo "=== Logs for $service ===" > "$diag_dir/${service}_logs.txt"
            docker logs --tail 100 "$service" 2>&1 >> "$diag_dir/${service}_logs.txt"
        fi
    done
    
    # Application metrics
    if curl -f -s "http://localhost:9090/api/v1/query?query=up" >/dev/null 2>&1; then
        echo "=== Prometheus Metrics ===" > "$diag_dir/prometheus_metrics.txt"
        curl -s "http://localhost:9090/api/v1/query?query=up" >> "$diag_dir/prometheus_metrics.txt"
    fi
    
    # Database connections
    if command -v psql >/dev/null 2>&1; then
        echo "=== PostgreSQL Connections ===" > "$diag_dir/postgres_connections.txt"
        PGPASSWORD="${POSTGRES_PASSWORD:-changeme}" psql -h "${POSTGRES_HOST:-localhost}" -U postgres -c "SELECT * FROM pg_stat_activity;" >> "$diag_dir/postgres_connections.txt" 2>/dev/null || echo "Failed to connect to PostgreSQL" >> "$diag_dir/postgres_connections.txt"
    fi
    
    # Redis info
    if command -v redis-cli >/dev/null 2>&1; then
        echo "=== Redis Info ===" > "$diag_dir/redis_info.txt"
        redis-cli info >> "$diag_dir/redis_info.txt" 2>/dev/null || echo "Failed to connect to Redis" >> "$diag_dir/redis_info.txt"
    fi
    
    # Compress diagnostics
    tar -czf "$output_dir/diagnostics_$timestamp.tar.gz" -C "$output_dir" "diagnostics_$timestamp"
    rm -rf "$diag_dir"
    
    log "Diagnostics collected: $output_dir/diagnostics_$timestamp.tar.gz"
    echo "$output_dir/diagnostics_$timestamp.tar.gz"
}

# Execute automated remediation
execute_remediation() {
    local alert_name="$1"
    local alert_labels="$2"
    local alert_annotations="$3"
    
    log "Executing remediation for alert: $alert_name"
    
    case "$alert_name" in
        "ServiceDown")
            local service=$(echo "$alert_labels" | grep -o 'job="[^"]*"' | cut -d'"' -f2)
            if [[ -n "$service" ]]; then
                if restart_service "$service"; then
                    send_notification "info" "Service Restarted" "Successfully restarted $service"
                    return 0
                else
                    send_notification "critical" "Restart Failed" "Failed to restart $service"
                    return 1
                fi
            fi
            ;;
        "HighCPUUsage")
            if [[ "${AUTO_SCALING_ENABLED:-true}" == "true" ]]; then
                local service="trading-api"
                if scale_service "$service" 3; then
                    send_notification "info" "Auto-scaling triggered" "Scaled up $service due to high CPU usage"
                    return 0
                fi
            fi
            ;;
        "DatabaseConnectionPoolExhaustion")
            restart_service postgres
            ;;
        "HighMemoryUsage")
            if [[ "${AUTO_SCALING_ENABLED:-true}" == "true" ]]; then
                restart_service "${SERVICE_TO_RESTART:-trading-api}"
            fi
            ;;
        "RedisConnectionFailure")
            restart_service redis
            ;;
        "ContainerRestartLoop")
            send_notification "critical" "Container Restart Loop" "Multiple restarts detected, manual intervention required"
            ;;
        "TradingServiceDown")
            send_notification "critical" "Trading Service Down" "Critical trading service is down - immediate attention required"
            # Collect immediate diagnostics
            collect_diagnostics "/tmp"
            ;;
        *)
            log "No automated remediation defined for alert: $alert_name"
            return 1
            ;;
    esac
}

# Escalate incident
escalate_incident() {
    local alert_name="$1"
    local severity="$2"
    local message="$3"
    local escalation_level="${4:-1}"
    
    log "Escalating incident: $alert_name (Level $escalation_level)"
    
    case "$escalation_level" in
        1)
            # First level: Operations team
            send_notification "$severity" "INCIDENT ESCALATION" "Level 1: $message"
            ;;
        2)
            # Second level: Engineering team
            send_notification "critical" "INCIDENT ESCALATION" "Level 2: $message"
            ;;
        3)
            # Third level: Management
            send_notification "critical" "MAJOR INCIDENT" "Level 3: $message"
            ;;
    esac
    
    # Update incident tracking
    echo "$(date),$alert_name,$severity,$escalation_level,$message" >> "$CONFIG_DIR/incident_history.csv"
}

# Main incident handler
handle_incident() {
    local alert_json="$1"
    
    # Parse alert JSON
    local alert_name=$(echo "$alert_json" | jq -r '.labels.alertname')
    local alert_status=$(echo "$alert_json" | jq -r '.status')
    local alert_severity=$(echo "$alert_json" | jq -r '.labels.severity')
    local alert_description=$(echo "$alert_json" | jq -r '.annotations.description')
    local alert_instance=$(echo "$alert_json" | jq -r '.labels.instance')
    
    log "Processing incident: $alert_name (Status: $alert_status, Severity: $alert_severity)"
    
    case "$alert_status" in
        "firing")
            # New incident
            if [[ "$alert_severity" == "critical" ]]; then
                # Collect immediate diagnostics for critical alerts
                local diag_file=$(collect_diagnostics "/tmp")
                
                # Attempt automated remediation
                if ! execute_remediation "$alert_name" "$(echo "$alert_json" | jq -r '.labels')" "$(echo "$alert_json" | jq -r '.annotations')"; then
                    # Escalate if remediation failed
                    escalate_incident "$alert_name" "$alert_severity" "$alert_description" 1
                fi
            else
                # Warning level - attempt remediation but don't escalate
                execute_remediation "$alert_name" "$(echo "$alert_json" | jq -r '.labels')" "$(echo "$alert_json" | jq -r '.annotations')" || true
            fi
            ;;
        "resolved")
            # Incident resolved
            send_notification "info" "Incident Resolved" "$alert_name has been resolved"
            ;;
    esac
}

# Webhook handler for Prometheus AlertManager
handle_alertmanager_webhook() {
    local payload
    if [[ $# -eq 0 ]]; then
        # Read from stdin
        payload=$(cat)
    else
        payload="$1"
    fi
    
    log "Received AlertManager webhook"
    
    # Process alerts
    echo "$payload" | jq -c '.alerts[]' | while read -r alert; do
        handle_incident "$alert"
    done
}

# Health check for incident response system
health_check() {
    local status="healthy"
    local issues=()
    
    # Check log file permissions
    if [[ ! -w "$LOG_FILE" ]] && ! touch "$LOG_FILE" 2>/dev/null; then
        issues+=("Cannot write to log file: $LOG_FILE")
    fi
    
    # Check required tools
    for tool in curl jq; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            issues+=("Missing required tool: $tool")
        fi
    done
    
    # Check configuration
    if [[ -f "$CONFIG_DIR/incident-response.conf" ]]; then
        source "$CONFIG_DIR/incident-response.conf"
    else
        issues+=("Configuration file not found: $CONFIG_DIR/incident-response.conf")
    fi
    
    if [[ ${#issues[@]} -gt 0 ]]; then
        status="unhealthy"
        echo "Status: $status"
        printf "Issues:\n%s\n" "${issues[@]}"
        return 1
    else
        echo "Status: $status"
        return 0
    fi
}

# Show usage
usage() {
    cat << EOF
Usage: $0 <command> [options]

Commands:
    webhook <payload>      Handle AlertManager webhook
    check-health          Run health check
    test-notification     Send test notification
    collect-diagnostics   Collect system diagnostics
    restart-service <name> Restart specific service
    scale-service <name> <replicas> Scale service
    escalate <alert> <severity> <message> <level> Escalate incident

Examples:
    $0 webhook '{"alerts":[{"labels":{"alertname":"ServiceDown"},"status":"firing"}]}'
    $0 check-health
    $0 collect-diagnostics
    $0 restart-service trading-api
    $0 scale-service trading-api 3
EOF
}

# Main execution
case "${1:-}" in
    webhook)
        if [[ $# -gt 1 ]]; then
            handle_alertmanager_webhook "$2"
        else
            handle_alertmanager_webhook
        fi
        ;;
    check-health)
        health_check
        ;;
    test-notification)
        send_notification "info" "Test Notification" "This is a test notification from incident response system"
        ;;
    collect-diagnostics)
        collect_diagnostics "${2:-/tmp}"
        ;;
    restart-service)
        if [[ -z "${2:-}" ]]; then
            echo "Service name required"
            exit 1
        fi
        restart_service "$2"
        ;;
    scale-service)
        if [[ -z "${2:-}" || -z "${3:-}" ]]; then
            echo "Service name and replicas required"
            exit 1
        fi
        scale_service "$2" "$3"
        ;;
    escalate)
        if [[ $# -lt 4 ]]; then
            echo "Alert name, severity, message, and level required"
            exit 1
        fi
        escalate_incident "$2" "$3" "$4" "$5"
        ;;
    *)
        usage
        exit 1
        ;;
esac