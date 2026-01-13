#!/bin/bash

# LangGraph API Production Deployment Script
set -e

ENVIRONMENT=${1:-production}
PROJECT_NAME="langgraph-api"
VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_error ".env file not found. Please create it from .env.production"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Load environment variables
load_env() {
    log_info "Loading environment configuration..."
    
    if [ -f ".env" ]; then
        export $(cat .env | grep -v ^# | xargs)
    else
        log_error ".env file not found"
        exit 1
    fi
}

# Create necessary directories
setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p logs
    mkdir -p data/postgres
    mkdir -p data/redis
    mkdir -p backups
    
    # Set permissions
    chmod 755 logs data backups
    chmod -R 755 data/postgres data/redis
    
    log_success "Directories created"
}

# Build and deploy services
deploy_services() {
    log_info "Deploying services for environment: $ENVIRONMENT"
    
    case $ENVIRONMENT in
        "production")
            COMPOSE_FILE="docker-compose.yml:docker-compose.prod.yml"
            log_info "Deploying production environment"
            ;;
        "development")
            COMPOSE_FILE="docker-compose.yml:docker-compose.dev.yml"
            log_info "Deploying development environment"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            log_info "Valid environments: production, development"
            exit 1
            ;;
    esac
    
    # Build and start services
    docker-compose -f $COMPOSE_FILE build --no-cache
    docker-compose -f $COMPOSE_FILE up -d
    
    log_success "Services deployed"
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be healthy..."
    
    # Wait for database
    log_info "Waiting for PostgreSQL..."
    timeout=60
    while ! docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "PostgreSQL failed to start"
            exit 1
        fi
    done
    
    # Wait for Redis
    log_info "Waiting for Redis..."
    timeout=30
    while ! docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            log_error "Redis failed to start"
            exit 1
        fi
    done
    
    # Wait for API
    log_info "Waiting for API service..."
    timeout=120
    while ! curl -f http://localhost:8000/health > /dev/null 2>&1; do
        sleep 5
        timeout=$((timeout-5))
        if [ $timeout -le 0 ]; then
            log_error "API service failed to start"
            exit 1
        fi
    done
    
    log_success "All services are healthy"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    
    # Wait a bit more for the API to be fully ready
    sleep 10
    
    # Run migrations
    docker-compose exec api python -m alembic upgrade head
    
    log_success "Database migrations completed"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    # Check API health
    API_HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status // "unknown"')
    
    # Check database connection
    DB_HEALTH=$(docker-compose exec -T postgres pg_isready -U postgres)
    
    # Check Redis connection
    REDIS_HEALTH=$(docker-compose exec -T redis redis-cli ping)
    
    if [ "$API_HEALTH" = "healthy" ] && [ "$DB_HEALTH" = "accepting connections" ] && [ "$REDIS_HEALTH" = "PONG" ]; then
        log_success "Health check passed"
        return 0
    else
        log_error "Health check failed"
        log_error "API: $API_HEALTH"
        log_error "Database: $DB_HEALTH"
        log_error "Redis: $REDIS_HEALTH"
        return 1
    fi
}

# Display deployment information
show_deployment_info() {
    log_success "Deployment completed successfully!"
    echo ""
    echo "=== Deployment Information ==="
    echo "Environment: $ENVIRONMENT"
    echo "Version: $VERSION"
    echo "Project: $PROJECT_NAME"
    echo ""
    echo "=== Service URLs ==="
    echo "API: http://localhost:8000"
    echo "API Docs: http://localhost:8000/docs"
    echo "Health Check: http://localhost:8000/health"
    echo "Metrics: http://localhost:8000/metrics"
    echo ""
    echo "=== Docker Services ==="
    docker-compose ps
    echo ""
    echo "=== Useful Commands ==="
    echo "View logs: docker-compose logs -f"
    echo "Stop services: docker-compose down"
    echo "Restart services: docker-compose restart"
    echo "Scale API: docker-compose up -d --scale api=3"
}

# Cleanup function
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Deployment failed. Cleaning up..."
        docker-compose -f $COMPOSE_FILE down --remove-orphans
    fi
}

# Main deployment function
main() {
    echo "=== LangGraph API Deployment ==="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $(date)"
    echo ""
    
    # Set trap for cleanup
    trap cleanup EXIT
    
    # Execute deployment steps
    check_prerequisites
    load_env
    setup_directories
    deploy_services
    wait_for_services
    run_migrations
    
    # Final health check
    if health_check; then
        show_deployment_info
        log_success "Deployment completed successfully!"
        trap - EXIT
    else
        log_error "Deployment completed but health check failed"
        exit 1
    fi
}

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 [environment]"
    echo ""
    echo "Environments:"
    echo "  production  - Deploy production environment"
    echo "  development - Deploy development environment"
    echo ""
    echo "Example:"
    echo "  $0 production"
    exit 1
fi

# Run main function
main