#!/bin/bash

# Redis Infrastructure Startup Script
# Sets up and manages the complete Redis infrastructure for trading framework

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are available"
}

# Check if Python is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
    print_status "Python $python_version is available"
}

# Install Python dependencies
install_dependencies() {
    print_header "Installing Python Dependencies"
    
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found. Please run this script from the redis directory."
        exit 1
    fi
    
    print_status "Installing Python packages..."
    pip3 install -r requirements.txt --quiet
    
    if [ $? -eq 0 ]; then
        print_status "Python dependencies installed successfully"
    else
        print_error "Failed to install Python dependencies"
        exit 1
    fi
}

# Start Redis infrastructure
start_redis() {
    print_header "Starting Redis Infrastructure"
    
    print_status "Starting Redis containers..."
    docker-compose up -d
    
    # Wait for Redis to be ready
    print_status "Waiting for Redis to be ready..."
    for i in {1..30}; do
        if docker exec trading-redis redis-cli -a trading_framework_2025 ping > /dev/null 2>&1; then
            print_status "Redis is ready!"
            break
        fi
        
        if [ $i -eq 30 ]; then
            print_error "Redis failed to start within 30 seconds"
            exit 1
        fi
        
        sleep 1
    done
    
    print_status "Redis infrastructure started successfully"
}

# Stop Redis infrastructure
stop_redis() {
    print_header "Stopping Redis Infrastructure"
    
    print_status "Stopping Redis containers..."
    docker-compose down
    
    print_status "Redis infrastructure stopped"
}

# Run health check
run_health_check() {
    print_header "Running Redis Health Check"
    
    print_status "Running comprehensive health check..."
    python3 health_check.py
    
    print_status "Health check completed"
}

# Run integration tests
run_tests() {
    print_header "Running Integration Tests"
    
    if [ ! -f "test_redis_infrastructure.py" ]; then
        print_error "Test file not found"
        exit 1
    fi
    
    print_status "Running Redis infrastructure tests..."
    python3 test_redis_infrastructure.py
    
    if [ $? -eq 0 ]; then
        print_status "All tests passed!"
    else
        print_error "Some tests failed"
        exit 1
    fi
}

# Show status
show_status() {
    print_header "Redis Infrastructure Status"
    
    print_status "Checking container status..."
    docker-compose ps
    
    echo ""
    print_status "Redis connection test..."
    if docker exec trading-redis redis-cli -a trading_framework_2025 ping > /dev/null 2>&1; then
        print_status "Redis is responding to ping"
    else
        print_error "Redis is not responding"
    fi
    
    echo ""
    print_status "Container logs (last 10 lines):"
    docker-compose logs --tail=10 redis
}

# Show usage information
show_usage() {
    echo "Redis Infrastructure Management Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start       Start Redis infrastructure (default)"
    echo "  stop        Stop Redis infrastructure"
    echo "  restart     Restart Redis infrastructure"
    echo "  status      Show status of all components"
    echo "  health      Run health check"
    echo "  test        Run integration tests"
    echo "  setup       Complete setup (install deps + start Redis)"
    echo "  logs        Show Redis logs"
    echo "  shell       Open Redis CLI shell"
    echo "  web         Open Redis Commander web interface"
    echo "  clean       Stop and remove all containers and volumes"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup        # First time setup"
    echo "  $0 start        # Start infrastructure"
    echo "  $0 status       # Check status"
    echo "  $0 test         # Run tests"
}

# Open Redis CLI shell
open_shell() {
    print_header "Opening Redis CLI"
    
    if ! docker exec -it trading-redis redis-cli -a trading_framework_2025; then
        print_error "Failed to open Redis CLI"
        exit 1
    fi
}

# Show logs
show_logs() {
    print_header "Redis Logs"
    
    docker-compose logs -f redis
}

# Open web interface
open_web() {
    print_header "Redis Commander Web Interface"
    
    url="http://localhost:8081"
    print_status "Opening $url in your default browser..."
    
    if command -v xdg-open > /dev/null; then
        xdg-open "$url"
    elif command -v open > /dev/null; then
        open "$url"
    else
        print_warning "Please open $url in your browser manually"
    fi
}

# Clean up everything
clean_up() {
    print_header "Cleaning Up Redis Infrastructure"
    
    print_warning "This will stop and remove all containers and volumes!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Stopping and removing containers..."
        docker-compose down -v
        
        print_status "Removing network..."
        docker network rm trading-redis-network 2>/dev/null || true
        
        print_status "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Main execution
main() {
    # Check if we're in the right directory
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found. Please run this script from the redis directory."
        exit 1
    fi
    
    # Default command
    command=${1:-start}
    
    case $command in
        "start")
            check_docker
            check_python
            start_redis
            ;;
        "stop")
            stop_redis
            ;;
        "restart")
            stop_redis
            start_redis
            ;;
        "status")
            check_docker
            show_status
            ;;
        "health")
            check_python
            run_health_check
            ;;
        "test")
            check_python
            run_tests
            ;;
        "setup")
            check_docker
            check_python
            install_dependencies
            start_redis
            run_tests
            ;;
        "logs")
            check_docker
            show_logs
            ;;
        "shell")
            check_docker
            open_shell
            ;;
        "web")
            check_docker
            open_web
            ;;
        "clean")
            check_docker
            clean_up
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Operation cancelled by user${NC}"; exit 130' INT

# Run main function
main "$@"