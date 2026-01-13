#!/bin/bash

# ==================== TRADING SYSTEM HEALTH CHECK SCRIPT ====================
# Comprehensive health check for all services in the Docker Compose stack

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=30
RETRY_COUNT=3

# Health check results
declare -A health_results
total_checks=0
passed_checks=0

# Logging functions
log_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((passed_checks++))
    ((total_checks++))
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
    ((total_checks++))
}

log_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

log_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Service health checks
check_service_health() {
    local service_name=$1
    local health_url=$2
    local port=$3
    
    log_info "Checking $service_name..."
    
    # Check if service container is running
    if ! docker ps --format "table {{.Names}}" | grep -q "^$service_name$"; then
        log_error "$service_name: Container is not running"
        health_results[$service_name]="DOWN"
        return 1
    fi
    
    # Check container health status
    local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$service_name" 2>/dev/null || echo "no-healthcheck")
    case $health_status in
        "healthy")
            log_success "$service_name: Container is healthy"
            ;;
        "unhealthy")
            log_error "$service_name: Container health check failed"
            health_results[$service_name]="UNHEALTHY"
            return 1
            ;;
        "starting")
            log_warning "$service_name: Container is starting"
            health_results[$service_name]="STARTING"
            return 1
            ;;
        "no-healthcheck")
            log_info "$service_name: No health check configured"
            ;;
    esac
    
    # Check HTTP endpoint if provided
    if [ -n "$health_url" ]; then
        local url="http://localhost:$port$health_url"
        if curl -sf --max-time 10 "$url" > /dev/null 2>&1; then
            log_success "$service_name: HTTP endpoint responding"
            health_results[$service_name]="UP"
        else
            log_error "$service_name: HTTP endpoint not responding ($url)"
            health_results[$service_name]="DOWN"
            return 1
        fi
    else
        health_results[$service_name]="UP"
    fi
}

# Database health checks
check_postgres() {
    log_info "Checking PostgreSQL..."
    
    if docker exec system-postgres pg_isready -U trading_user > /dev/null 2>&1; then
        log_success "PostgreSQL: Database is ready"
        
        # Check connections
        local connections=$(docker exec system-postgres psql -U trading_user -t -c "SELECT count(*) FROM pg_stat_activity;" | tr -d ' ')
        log_info "PostgreSQL: Active connections: $connections"
        
        # Check database size
        local db_size=$(docker exec system-postgres psql -U trading_user -t -c "SELECT pg_size_pretty(pg_database_size('trading_system'));" | tr -d ' ')
        log_info "PostgreSQL: Database size: $db_size"
    else
        log_error "PostgreSQL: Database is not ready"
        return 1
    fi
}

check_redis() {
    log_info "Checking Redis..."
    
    if docker exec system-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis: Server is responding"
        
        # Check memory usage
        local memory_info=$(docker exec system-redis redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
        log_info "Redis: Memory usage: $memory_info"
        
        # Check connected clients
        local clients=$(docker exec system-redis redis-cli info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
        log_info "Redis: Connected clients: $clients"
    else
        log_error "Redis: Server is not responding"
        return 1
    fi
}

# External service checks
check_external_services() {
    log_info "Checking external services..."
    
    # Check Prometheus
    if curl -sf --max-time 10 http://localhost:9090/-/healthy > /dev/null 2>&1; then
        log_success "Prometheus: Service is healthy"
    else
        log_warning "Prometheus: Service may not be ready"
    fi
    
    # Check Grafana
    if curl -sf --max-time 10 http://localhost:3000/api/health > /dev/null 2>&1; then
        log_success "Grafana: Service is healthy"
    else
        log_warning "Grafana: Service may not be ready"
    fi
    
    # Check Kibana
    if curl -sf --max-time 10 http://localhost:5601/api/status > /dev/null 2>&1; then
        log_success "Kibana: Service is healthy"
    else
        log_warning "Kibana: Service may not be ready"
    fi
}

# Resource usage checks
check_resource_usage() {
    log_info "Checking resource usage..."
    
    # Check Docker system
    local docker_info=$(docker system df 2>/dev/null)
    if [ $? -eq 0 ]; then
        log_info "Docker system status:"
        echo "$docker_info"
    else
        log_warning "Unable to get Docker system information"
    fi
    
    # Check container resource usage
    log_info "Container resource usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" || true
}

# Performance checks
check_performance() {
    log_info "Running performance checks..."
    
    # Database query performance
    if docker exec system-postgres pg_isready -U trading_user > /dev/null 2>&1; then
        local query_time=$(docker exec system-postgres psql -U trading_user -c "SELECT 1;" 2>&1 | grep -o '[0-9]*\.[0-9]*ms' || echo "unknown")
        log_info "PostgreSQL query time: $query_time"
    fi
    
    # Redis latency
    if docker exec system-redis redis-cli ping > /dev/null 2>&1; then
        local latency=$(docker exec system-redis redis-cli --latency-history -i 1 -c 1 | grep "min:" | head -1 | awk '{print $2}' || echo "unknown")
        log_info "Redis latency: $latency"
    fi
}

# Main health check function
run_health_checks() {
    echo "======================================"
    echo "  Trading System Health Check"
    echo "======================================"
    echo
    
    # Check infrastructure services
    log_info "Checking infrastructure services..."
    echo
    check_postgres
    echo
    check_redis
    echo
    
    # Check API services
    log_info "Checking API services..."
    echo
    check_service_health "langgraph-api" "/health" "8000"
    check_service_health "asymedge-api" "/health" "8002"
    check_service_health "abacus-ai" "/health" "8001"
    echo
    
    # Check AI/ML services
    log_info "Checking AI/ML services..."
    echo
    check_service_health "letta-server" "/health" "8283"
    echo
    
    # Check integration services
    log_info "Checking integration services..."
    echo
    check_service_health "composio" "/health" "3000"
    check_service_health "pubsub" "/health" "8003"
    check_service_health "workflows" "/health" "8004"
    check_service_health "security" "/health" "8005"
    echo
    
    # Check external monitoring services
    check_external_services
    echo
    
    # Check resources and performance
    check_resource_usage
    echo
    check_performance
    echo
    
    # Summary
    echo "======================================"
    echo "  Health Check Summary"
    echo "======================================"
    
    local health_count=0
    local unhealthy_count=0
    local down_count=0
    
    for service in "${!health_results[@]}"; do
        case "${health_results[$service]}" in
            "UP"|"HEALTHY")
                ((health_count++))
                ;;
            "UNHEALTHY")
                ((unhealthy_count++))
                ;;
            "DOWN"|"STARTING")
                ((down_count++))
                ;;
        esac
    done
    
    echo "Total services checked: $total_checks"
    echo "Healthy services: $health_count"
    echo "Unhealthy services: $unhealthy_count"
    echo "Down services: $down_count"
    echo
    
    if [ $down_count -eq 0 ] && [ $unhealthy_count -eq 0 ]; then
        log_success "All services are healthy!"
        return 0
    elif [ $down_count -eq 0 ]; then
        log_warning "Some services are unhealthy but running"
        return 1
    else
        log_error "Some services are down!"
        return 2
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    # Add any cleanup tasks here
}

# Script entry point
main() {
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Run health checks
    if run_health_checks; then
        exit 0
    else
        exit 1
    fi
}

# Run if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi