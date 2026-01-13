#!/bin/bash
# Composio MCP Server - Setup Script
# Automated setup for development and production environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Composio MCP Server Setup"
echo "============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if [[ "$(python3 -c 'import sys; print(sys.version_info >= (3, 8))')" == "True" ]]; then
            print_status "Python $PYTHON_VERSION found"
            return 0
        else
            print_error "Python 3.8+ required, found $PYTHON_VERSION"
            return 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.8+"
        return 1
    fi
}

# Function to check pip
check_pip() {
    if command_exists pip3; then
        print_status "pip3 found"
        return 0
    else
        print_error "pip3 not found. Please install pip"
        return 1
    fi
}

# Function to check Redis
check_redis() {
    if command_exists redis-cli; then
        print_status "Redis CLI found"
        return 0
    else
        print_warning "Redis CLI not found. You'll need Redis for rate limiting"
        return 1
    fi
}

# Function to create virtual environment
create_venv() {
    local venv_path="$ROOT_DIR/venv"
    
    if [ -d "$venv_path" ]; then
        print_info "Virtual environment already exists at $venv_path"
    else
        print_info "Creating virtual environment..."
        python3 -m venv "$venv_path"
        print_status "Virtual environment created"
    fi
    
    # Activate virtual environment
    source "$venv_path/bin/activate"
    print_status "Virtual environment activated"
}

# Function to install dependencies
install_dependencies() {
    print_info "Installing Python dependencies..."
    
    # Upgrade pip first
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "$ROOT_DIR/requirements.txt" ]; then
        pip install -r "$ROOT_DIR/requirements.txt"
        print_status "Dependencies installed successfully"
    else
        print_error "requirements.txt not found"
        return 1
    fi
}

# Function to create configuration
create_config() {
    local config_file="$ROOT_DIR/config/config.json"
    local example_file="$ROOT_DIR/config/config.example.json"
    
    if [ ! -f "$config_file" ]; then
        if [ -f "$example_file" ]; then
            print_info "Creating configuration from example..."
            cp "$example_file" "$config_file"
            print_status "Configuration created at $config_file"
            print_warning "Please edit $config_file with your settings before running the server"
        else
            print_error "Configuration example file not found"
            return 1
        fi
    else
        print_info "Configuration file already exists"
    fi
}

# Function to create logs directory
create_logs_dir() {
    local logs_dir="$ROOT_DIR/logs"
    
    if [ ! -d "$logs_dir" ]; then
        mkdir -p "$logs_dir"
        print_status "Logs directory created at $logs_dir"
    else
        print_info "Logs directory already exists"
    fi
}

# Function to generate sample environment file
create_env_file() {
    local env_file="$ROOT_DIR/.env"
    
    if [ ! -f "$env_file" ]; then
        print_info "Creating sample environment file..."
        cat > "$env_file" << EOF
# Composio MCP Server Environment Variables
# Copy this file to .env and fill in your actual values

# Server Configuration
COMPOSIO_ENVIRONMENT=development
COMPOSIO_DEBUG=true
COMPOSIO_SERVER_PORT=8000

# Database Configuration
COMPOSIO_DATABASE_URL=sqlite:///./composio.db

# Redis Configuration
COMPOSIO_REDIS_URL=redis://localhost:6379/0

# Authentication Secrets (CHANGE IN PRODUCTION!)
COMPOSIO_SECRET_KEY=your-secret-key-change-in-production
COMPOSIO_ENCRYPTION_KEY=your-encryption-key-change-in-production
COMPOSIO_PASSWORD_SALT=your-salt-change-in-production

# External Service Tokens (Add your actual tokens)
GITHUB_TOKEN=your-github-personal-access-token
SLACK_BOT_TOKEN=your-slack-bot-token
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
NOTION_TOKEN=your-notion-integration-token
QUANTCONNECT_TOKEN=your-quantconnect-token
ABACUS_AI_API_KEY=your-abacus-ai-api-key

# Logging
COMPOSIO_LOG_LEVEL=INFO
EOF
        print_status "Environment file created at $env_file"
        print_warning "Please edit $env_file with your actual values"
    else
        print_info "Environment file already exists"
    fi
}

# Function to run tests
run_tests() {
    print_info "Running basic tests..."
    
    # Test configuration loading
    if python3 -c "
import sys
sys.path.append('$ROOT_DIR')
from config.settings import Settings
settings = Settings.load('$ROOT_DIR/config/config.json')
print('Configuration loaded successfully')
"; then
        print_status "Configuration test passed"
    else
        print_error "Configuration test failed"
        return 1
    fi
    
    # Test imports
    if python3 -c "
import sys
sys.path.append('$ROOT_DIR')
from server.composio_server import ComposioMCPServer
from tools.base import BaseToolHandler
from auth.manager import AuthManager
from monitoring.health import HealthMonitor
print('All imports successful')
"; then
        print_status "Import test passed"
    else
        print_error "Import test failed"
        return 1
    fi
    
    return 0
}

# Function to display next steps
show_next_steps() {
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next Steps:"
    echo "1. Edit configuration files:"
    echo "   - $ROOT_DIR/config/config.json"
    echo "   - $ROOT_DIR/.env"
    echo ""
    echo "2. Set up external service credentials:"
    echo "   - GitHub: Create a personal access token"
    echo "   - Slack: Create a bot token"
    echo "   - Telegram: Create a bot token"
    echo "   - Notion: Create an integration token"
    echo "   - QuantConnect: Get API credentials"
    echo "   - Abacus.AI: Get API key"
    echo ""
    echo "3. Start the server:"
    echo "   cd $ROOT_DIR"
    echo "   source venv/bin/activate"
    echo "   python server/composio_server.py"
    echo ""
    echo "4. Run the demo:"
    echo "   python examples/demo.py"
    echo ""
    echo "5. Run usage examples:"
    echo "   python examples/usage_examples.py"
    echo ""
    echo "Documentation:"
    echo "   - $ROOT_DIR/docs/server_config.md"
    echo "   - $ROOT_DIR/docs/tool_integration.md"
    echo ""
    echo "For production deployment, see $ROOT_DIR/docs/deployment.md"
}

# Function to show help
show_help() {
    echo "Composio MCP Server Setup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --dev               Setup for development (default)"
    echo "  --prod              Setup for production"
    echo "  --no-deps           Skip dependency installation"
    echo "  --no-tests          Skip running tests"
    echo "  --quick             Quick setup (minimal steps)"
    echo ""
    echo "Examples:"
    echo "  $0                  # Full development setup"
    echo "  $0 --dev            # Development setup"
    echo "  $0 --prod           # Production setup"
    echo "  $0 --quick          # Quick setup"
}

# Parse command line arguments
ENVIRONMENT="dev"
SKIP_DEPS=false
SKIP_TESTS=false
QUICK_SETUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --dev)
            ENVIRONMENT="dev"
            shift
            ;;
        --prod)
            ENVIRONMENT="prod"
            shift
            ;;
        --no-deps)
            SKIP_DEPS=true
            shift
            ;;
        --no-tests)
            SKIP_TESTS=true
            shift
            ;;
        --quick)
            QUICK_SETUP=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

echo "Setup Mode: $ENVIRONMENT"
echo ""

# Main setup process
echo "🔍 Checking system requirements..."

# Check Python
if ! check_python; then
    exit 1
fi

# Check pip
if ! check_pip; then
    exit 1
fi

# Check Redis (optional)
check_redis

echo ""
echo "📦 Setting up environment..."

# Create virtual environment (skip for production)
if [ "$ENVIRONMENT" = "dev" ]; then
    create_venv
fi

# Install dependencies (skip if requested)
if [ "$SKIP_DEPS" = false ]; then
    install_dependencies
else
    print_warning "Skipping dependency installation"
fi

# Create configuration
create_config

# Create logs directory
create_logs_dir

# Create environment file
create_env_file

# Run tests (skip if requested)
if [ "$SKIP_TESTS" = false ] && [ "$QUICK_SETUP" = false ]; then
    echo ""
    echo "🧪 Running tests..."
    if run_tests; then
        print_status "All tests passed"
    else
        print_warning "Some tests failed, but setup can continue"
    fi
else
    print_warning "Skipping tests"
fi

# Quick setup - just show next steps
if [ "$QUICK_SETUP" = true ]; then
    show_next_steps
    exit 0
fi

echo ""
echo "🎯 Setup Summary:"
echo "  - Environment: $ENVIRONMENT"
echo "  - Python dependencies: $([ "$SKIP_DEPS" = false ] && echo "Installed" || echo "Skipped")"
echo "  - Configuration: $([ -f "$ROOT_DIR/config/config.json" ] && echo "Created" || echo "Exists")"
echo "  - Environment file: $([ -f "$ROOT_DIR/.env" ] && echo "Created" || echo "Exists")"
echo "  - Tests: $([ "$SKIP_TESTS" = false ] && echo "Passed" || echo "Skipped")"

show_next_steps

# Create a simple start script
cat > "$ROOT_DIR/start.sh" << EOF
#!/bin/bash
# Simple start script for the Composio MCP Server

cd "$(dirname "\$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
fi

python server/composio_server.py "\$@"
EOF

chmod +x "$ROOT_DIR/start.sh"
print_status "Start script created at $ROOT_DIR/start.sh"

echo ""
echo "To start the server, run:"
echo "  ./start.sh"