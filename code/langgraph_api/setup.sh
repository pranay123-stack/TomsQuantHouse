#!/bin/bash

# LangGraph API Service Setup Script
# This script sets up the development environment for the LangGraph API

set -e

# Configuration
VENV_NAME="langgraph-api-env"
PROJECT_NAME="LangGraph API"

echo "🚀 Setting up $PROJECT_NAME Development Environment"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Check Python installation
check_python() {
    log_step "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.11 or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python version: $PYTHON_VERSION"
    
    # Check if version is 3.11+
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
        log_warning "Python 3.11+ is recommended. Current version: $PYTHON_VERSION"
    fi
}

# Check pip installation
check_pip() {
    log_step "Checking pip installation..."
    
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed. Please install pip."
        exit 1
    fi
    
    PIP_VERSION=$(pip3 --version | cut -d' ' -f2)
    log_info "pip version: $PIP_VERSION"
}

# Create virtual environment
create_venv() {
    log_step "Creating virtual environment..."
    
    if [ -d "$VENV_NAME" ]; then
        log_warning "Virtual environment '$VENV_NAME' already exists"
        read -p "Do you want to recreate it? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Removing existing virtual environment..."
            rm -rf "$VENV_NAME"
        else
            log_info "Using existing virtual environment"
            return 0
        fi
    fi
    
    python3 -m venv "$VENV_NAME"
    log_success "Virtual environment created: $VENV_NAME"
}

# Activate virtual environment
activate_venv() {
    log_step "Activating virtual environment..."
    
    if [ ! -f "$VENV_NAME/bin/activate" ]; then
        log_error "Virtual environment activation script not found"
        exit 1
    fi
    
    source "$VENV_NAME/bin/activate"
    log_info "Virtual environment activated"
}

# Upgrade pip
upgrade_pip() {
    log_step "Upgrading pip..."
    
    pip install --upgrade pip
    log_success "pip upgraded"
}

# Install dependencies
install_dependencies() {
    log_step "Installing Python dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found"
        exit 1
    fi
    
    pip install -r requirements.txt
    log_success "Dependencies installed"
}

# Setup environment files
setup_env_files() {
    log_step "Setting up environment files..."
    
    # Copy example environment file
    if [ -f ".env.example" ] && [ ! -f ".env" ]; then
        cp .env.example .env
        log_info "Created .env file from .env.example"
        log_warning "Please edit .env file with your configuration"
    elif [ -f ".env" ]; then
        log_info ".env file already exists"
    else
        log_warning ".env.example not found, creating basic .env file"
        cat > .env << EOF
# Environment Configuration
ENVIRONMENT=development
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://langgraph:langgraph123@localhost:5432/langgraph_api
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0

# Rate Limiting
RATE_LIMIT_ENABLED=true

# Monitoring
METRICS_ENABLED=true
LOG_LEVEL=INFO
EOF
        log_info "Created basic .env file"
    fi
    
    # Create development environment file
    if [ ! -f ".env.development" ]; then
        cp .env .env.development 2>/dev/null || true
        log_info "Created .env.development file"
    fi
}

# Create necessary directories
create_directories() {
    log_step "Creating necessary directories..."
    
    directories=(
        "logs"
        "data/postgres"
        "data/redis"
        "backups"
        "tests/fixtures"
        "tests/output"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        log_info "Created directory: $dir"
    done
    
    # Set permissions
    chmod 755 logs data backups
    chmod -R 755 data/postgres data/redis
}

# Initialize Git hooks (if .git exists)
setup_git_hooks() {
    if [ -d ".git" ]; then
        log_step "Setting up Git hooks..."
        
        # Pre-commit hook
        cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Pre-commit hook for code quality checks

echo "Running pre-commit checks..."

# Check for Python syntax errors
python3 -m py_compile $(find . -name "*.py" -not -path "./.git/*")

# Run linting
if command -v flake8 >/dev/null 2>&1; then
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
fi

# Run tests
if command -v pytest >/dev/null 2>&1; then
    pytest tests/ --maxfail=1 --disable-warnings
fi

echo "Pre-commit checks completed"
EOF
        
        chmod +x .git/hooks/pre-commit
        log_success "Git hooks configured"
    fi
}

# Setup database (if needed)
setup_database() {
    log_step "Checking database setup..."
    
    log_info "Note: PostgreSQL and Redis should be running via Docker"
    log_info "Start services with: docker-compose up -d"
    
    # Check if we can connect to PostgreSQL
    if command -v pg_isready >/dev/null 2>&1; then
        if pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
            log_info "PostgreSQL is running"
        else
            log_warning "PostgreSQL is not running. Start it with: docker-compose up -d"
        fi
    fi
    
    # Check if we can connect to Redis
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli ping >/dev/null 2>&1; then
            log_info "Redis is running"
        else
            log_warning "Redis is not running. Start it with: docker-compose up -d"
        fi
    fi
}

# Run initial setup tasks
run_initial_tasks() {
    log_step "Running initial setup tasks..."
    
    # Check if we're in a virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        log_info "Running in virtual environment: $VIRTUAL_ENV"
        
        # Initialize database ( Alembic )
        if [ -d "alembic" ]; then
            log_info "Running initial database migration..."
            python -m alembic upgrade head || log_warning "Database migration failed (this is normal if DB is not running)"
        fi
        
        # Run tests to verify setup
        log_info "Running tests to verify setup..."
        python -m pytest tests/ --collect-only > /dev/null 2>&1 || log_warning "Test collection failed (this is normal if setup is incomplete)"
        
        log_success "Initial tasks completed"
    else
        log_warning "Not in virtual environment, skipping setup tasks"
    fi
}

# Show setup completion information
show_completion_info() {
    log_success "Setup completed successfully!"
    echo ""
    echo "=== $PROJECT_NAME Setup Complete ==="
    echo ""
    echo "📦 Project Structure:"
    echo "   ├── Virtual Environment: $VENV_NAME"
    echo "   ├── Source Code: ./app/"
    echo "   ├── Tests: ./tests/"
    echo "   ├── Documentation: ./docs/"
    echo "   └── Examples: ./examples/"
    echo ""
    echo "🔧 Next Steps:"
    echo "   1. Start database services:"
    echo "      docker-compose up -d"
    echo ""
    echo "   2. Activate virtual environment:"
    echo "      source $VENV_NAME/bin/activate"
    echo ""
    echo "   3. Configure environment:"
    echo "      nano .env"
    echo ""
    echo "   4. Run database migrations:"
    echo "      python -m alembic upgrade head"
    echo ""
    echo "   5. Start the API server:"
    echo "      python run.py"
    echo ""
    echo "🌐 Service URLs (when running):"
    echo "   API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo "   Health Check: http://localhost:8000/health"
    echo "   Metrics: http://localhost:8000/metrics"
    echo ""
    echo "🛠️ Useful Commands:"
    echo "   Run tests: pytest"
    echo "   Run with coverage: pytest --cov=app"
    echo "   Format code: black ."
    echo "   Lint code: flake8 ."
    echo "   Type check: mypy app"
    echo ""
    echo "📚 Documentation:"
    echo "   README: ./README.md"
    echo "   API Documentation: http://localhost:8000/docs"
    echo ""
}

# Main setup function
main() {
    echo "=== $PROJECT_NAME Development Environment Setup ==="
    echo "Timestamp: $(date)"
    echo ""
    
    # Execute setup steps
    check_python
    check_pip
    create_venv
    activate_venv
    upgrade_pip
    install_dependencies
    setup_env_files
    create_directories
    setup_git_hooks
    setup_database
    run_initial_tasks
    
    # Show completion information
    show_completion_info
    
    log_success "🎉 Development environment setup complete!"
}

# Handle script interruption
cleanup() {
    log_info "Setup interrupted. Cleaning up..."
    # Add any cleanup logic here if needed
}

trap cleanup INT

# Run main setup
main

# Deactivate virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    deactivate
fi

exit 0