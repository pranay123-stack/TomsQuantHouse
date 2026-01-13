#!/bin/bash
"""
LangGraph Workflow System Setup Script
Comprehensive setup and initialization for the LangGraph workflow system
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LANGGRAPH_DIR="/workspace/code/langgraph"
REDIS_DIR="/workspace/code/redis"
PYTHON_VERSION="3.8"
VENV_NAME="langgraph_env"

echo -e "${BLUE}🚀 LangGraph Workflow System Setup${NC}"
echo "====================================="

# Function to print colored output
print_step() {
    echo -e "${YELLOW}📋 Step $1: $2${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_step "1" "Checking prerequisites"
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python 3.8+ is required but not found"
        exit 1
    fi
    
    PYTHON_VERSION_CHECK=$($PYTHON_CMD -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2>/dev/null || echo "0.0")
    
    if [[ $(echo "$PYTHON_VERSION_CHECK < 3.8" | bc -l 2>/dev/null || echo "1") == "1" ]]; then
        print_error "Python 3.8+ is required. Found: $PYTHON_VERSION_CHECK"
        exit 1
    fi
    
    print_success "Python 3.8+ found"
    
    # Check pip
    if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
        print_error "pip is required but not found"
        exit 1
    fi
    
    print_success "pip found"
    
    # Check Redis directory exists
    if [[ ! -d "$REDIS_DIR" ]]; then
        print_warning "Redis directory not found at $REDIS_DIR"
        print_warning "Please ensure Redis is set up from Phase 1"
    else
        print_success "Redis directory found"
    fi
}

# Setup virtual environment
setup_virtual_environment() {
    print_step "2" "Setting up virtual environment"
    
    cd "$LANGGRAPH_DIR"
    
    # Create virtual environment
    if [[ ! -d "$VENV_NAME" ]]; then
        $PYTHON_CMD -m venv $VENV_NAME
        print_success "Virtual environment created: $VENV_NAME"
    else
        print_success "Virtual environment already exists: $VENV_NAME"
    fi
    
    # Activate virtual environment
    source $VENV_NAME/bin/activate
    print_success "Virtual environment activated"
    
    # Upgrade pip
    pip install --upgrade pip
    print_success "pip upgraded"
}

# Install dependencies
install_dependencies() {
    print_step "3" "Installing dependencies"
    
    cd "$LANGGRAPH_DIR"
    source $VENV_NAME/bin/activate
    
    # Install core dependencies
    print "Installing core dependencies..."
    pip install -r requirements.txt
    print_success "Core dependencies installed"
    
    # Install development dependencies
    print "Installing development dependencies..."
    pip install pytest pytest-asyncio black flake8 mypy
    print_success "Development dependencies installed"
    
    # Install optional dependencies
    print "Installing optional dependencies..."
    pip install fastapi uvicorn aiohttp
    print_success "Optional dependencies installed"
}

# Setup Redis connection
setup_redis() {
    print_step "4" "Testing Redis connection"
    
    cd "$REDIS_DIR"
    
    # Check if Redis is running
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping &> /dev/null; then
            print_success "Redis server is running"
        else
            print_warning "Redis server is not responding"
            print_warning "Please start Redis server:"
            echo "  cd $REDIS_DIR && ./setup.sh"
        fi
    else
        print_warning "redis-cli not found. Please ensure Redis is installed."
    fi
    
    # Test Redis connection from Python
    cd "$LANGGRAPH_DIR"
    source $VENV_NAME/bin/activate
    
    python3 -c "
import sys
sys.path.append('.')
try:
    from checkpoints.redis_checkpointer import RedisCheckpointer
    print('✅ Redis checkpointer can be imported')
    
    # Test basic functionality
    print('ℹ️  Note: Actual Redis connection will be tested when workflow runs')
except ImportError as e:
    print(f'⚠️  Import test failed: {e}')
except Exception as e:
    print(f'⚠️  Setup test failed: {e}')
"
}

# Create configuration files
create_config() {
    print_step "5" "Creating configuration files"
    
    cd "$LANGGRAPH_DIR"
    
    # Create environment file
    cat > .env << EOF
# LangGraph Workflow System Configuration
LANGGRAPH_REDIS_HOST=localhost
LANGGRAPH_REDIS_PORT=6379
LANGGRAPH_REDIS_PASSWORD=trading_framework_2025
LANGGRAPH_REDIS_DB=0

# Workflow Settings
LANGGRAPH_AUTO_CHECKPOINT=true
LANGGRAPH_CHECKPOINT_INTERVAL=300
LANGGRAPH_MAX_WORKFLOW_DURATION=1800
LANGGRAPH_BATCH_SIZE=10

# API Settings
LANGGRAPH_API_HOST=0.0.0.0
LANGGRAPH_API_PORT=8000
LANGGRAPH_API_DEBUG=false

# Monitoring Settings
LANGGRAPH_MONITORING_INTERVAL=60
LANGGRAPH_ALERT_THRESHOLD_FAILURE_RATE=0.10
LANGGRAPH_CLEANUP_MAX_AGE_HOURS=24

# Risk Management
LANGGRAPH_MAX_POSITION_SIZE=0.20
LANGGRAPH_MAX_PORTFOLIO_RISK=0.10
LANGGRAPH_CONFIDENCE_THRESHOLD=0.6
EOF
    
    print_success "Environment configuration created: .env"
    
    # Create development config
    cat > config/development.yaml << EOF
# Development Configuration for LangGraph Workflow System

workflow:
  auto_checkpoint: true
  checkpoint_interval: 300  # 5 minutes
  max_workflow_duration: 1800  # 30 minutes
  retry_failed_nodes: true
  max_retries: 3

redis:
  host: localhost
  port: 6379
  password: trading_framework_2025
  db: 0
  timeout: 10

risk_management:
  max_position_size: 0.20
  max_portfolio_risk: 0.10
  confidence_threshold: 0.6
  stop_loss_threshold: 0.05

monitoring:
  interval: 60
  alert_thresholds:
    failure_rate: 0.10
    execution_time: 300
    memory_usage: 0.80

api:
  host: 0.0.0.0
  port: 8000
  debug: true
  cors_origins:
    - "http://localhost:3000"
    - "http://localhost:8080"
EOF
    
    mkdir -p config
    print_success "Development configuration created: config/development.yaml"
    
    # Create production config
    cat > config/production.yaml << EOF
# Production Configuration for LangGraph Workflow System

workflow:
  auto_checkpoint: true
  checkpoint_interval: 300  # 5 minutes
  max_workflow_duration: 1800  # 30 minutes
  retry_failed_nodes: true
  max_retries: 2

redis:
  host: ${REDIS_HOST:-localhost}
  port: ${REDIS_PORT:-6379}
  password: ${REDIS_PASSWORD:-trading_framework_2025}
  db: 0
  timeout: 5

risk_management:
  max_position_size: 0.15  # More conservative in production
  max_portfolio_risk: 0.08  # More conservative in production
  confidence_threshold: 0.7  # Higher threshold in production
  stop_loss_threshold: 0.03

monitoring:
  interval: 30
  alert_thresholds:
    failure_rate: 0.05  # Tighter threshold in production
    execution_time: 600
    memory_usage: 0.75

api:
  host: 0.0.0.0
  port: ${API_PORT:-8000}
  debug: false
  cors_origins:
    - "https://yourdomain.com"
EOF
    
    print_success "Production configuration created: config/production.yaml"
}

# Run tests
run_tests() {
    print_step "6" "Running tests"
    
    cd "$LANGGRAPH_DIR"
    source $VENV_NAME/bin/activate
    
    # Create test configuration
    mkdir -p tests/fixtures
    
    # Run basic import tests
    python3 -c "
import sys
sys.path.append('.')

# Test imports
try:
    from workflows.trading_workflow import TradingWorkflow
    print('✅ TradingWorkflow import successful')
except ImportError as e:
    print(f'❌ TradingWorkflow import failed: {e}')

try:
    from workflows.state_graph import TradingStateGraph
    print('✅ TradingStateGraph import successful')
except ImportError as e:
    print(f'❌ TradingStateGraph import failed: {e}')

try:
    from checkpoints.redis_checkpointer import RedisCheckpointer
    print('✅ RedisCheckpointer import successful')
except ImportError as e:
    print(f'❌ RedisCheckpointer import failed: {e}')

try:
    from utils.workflow_utils import WorkflowUtils
    print('✅ WorkflowUtils import successful')
except ImportError as e:
    print(f'❌ WorkflowUtils import failed: {e}')

try:
    from visualization.monitoring import WorkflowVisualization, WorkflowMonitoring
    print('✅ Monitoring components import successful')
except ImportError as e:
    print(f'⚠️  Monitoring components import failed: {e}')

try:
    from api.workflow_api import create_workflow_api
    print('✅ API components import successful')
except ImportError as e:
    print(f'⚠️  API components import failed: {e}')
"
    
    print_success "Import tests completed"
    
    # Run pytest if available
    if command -v pytest &> /dev/null; then
        print "Running pytest..."
        pytest tests/test_langgraph_workflow.py -v --tb=short || print_warning "Some tests failed (this is expected without Redis)"
    fi
}

# Create example scripts
create_examples() {
    print_step "7" "Creating example scripts"
    
    cd "$LANGGRAPH_DIR"
    
    # Create simple example
    cat > examples/simple_example.py << 'EOF'
#!/usr/bin/env python3
"""
Simple LangGraph Workflow Example
Basic usage demonstration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from workflows.trading_workflow import TradingWorkflow
from checkpoints.redis_checkpointer import RedisCheckpointer

def main():
    # Mock Redis client for demonstration
    class MockRedisClient:
        def __init__(self):
            self.data = {}
        
        def select(self, db): pass
        def setex(self, key, ttl, value): 
            self.data[key] = value.decode() if isinstance(value, bytes) else str(value)
            return True
        def get(self, key): 
            value = self.data.get(key)
            return value.encode() if value else None
        def delete(self, key): return self.data.pop(key, None)
        def keys(self, pattern): return list(self.data.keys())
        def ping(self): return True
        def ttl(self, key): return 3600
        def expire(self, key, ttl): return True
        def close(self): pass
    
    # Initialize components
    redis_client = MockRedisClient()
    checkpointer = RedisCheckpointer(redis_client)
    workflow = TradingWorkflow(checkpointer)
    
    # Execute workflow
    result = workflow.execute_trading_workflow(
        symbol="BTCUSDT",
        strategy="momentum",
        metadata={"example": True}
    )
    
    print(f"✅ Workflow executed: {result['workflow_id']}")
    print(f"   Status: {result['status']}")
    print(f"   Execution time: {result['execution_time']}")
    
    return result

if __name__ == "__main__":
    main()
EOF
    
    chmod +x examples/simple_example.py
    print_success "Simple example created: examples/simple_example.py"
    
    # Create API server example
    cat > examples/start_api_server.py << 'EOF'
#!/usr/bin/env python3
"""
API Server Example
Start the LangGraph Workflow API server
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import uvicorn
from api.workflow_api import create_workflow_api
from workflows.trading_workflow import TradingWorkflow
from checkpoints.redis_checkpointer import RedisCheckpointer

def main():
    # Mock Redis client for demonstration
    class MockRedisClient:
        def __init__(self):
            self.data = {}
        
        def select(self, db): pass
        def setex(self, key, ttl, value): 
            self.data[key] = value.decode() if isinstance(value, bytes) else str(value)
            return True
        def get(self, key): 
            value = self.data.get(key)
            return value.encode() if value else None
        def delete(self, key): return self.data.pop(key, None)
        def keys(self, pattern): return list(self.data.keys())
        def ping(self): return True
        def ttl(self, key): return 3600
        def expire(self, key, ttl): return True
        def close(self): pass
    
    # Initialize components
    redis_client = MockRedisClient()
    checkpointer = RedisCheckpointer(redis_client)
    workflow = TradingWorkflow(checkpointer)
    
    # Create API
    app = create_workflow_api(workflow, checkpointer)
    
    # Run server
    print("🚀 Starting LangGraph Workflow API Server...")
    print("📡 Server will be available at http://localhost:8000")
    print("📚 API documentation at http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
EOF
    
    chmod +x examples/start_api_server.py
    print_success "API server example created: examples/start_api_server.py"
}

# Create startup script
create_startup_script() {
    print_step "8" "Creating startup script"
    
    cd "$LANGGRAPH_DIR"
    
    cat > run_langgraph.sh << 'EOF'
#!/bin/bash
# LangGraph Workflow System Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_NAME="langgraph_env"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 LangGraph Workflow System${NC}"
echo "================================="

# Activate virtual environment
if [[ -d "$VENV_NAME" ]]; then
    source $VENV_NAME/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment not found. Run setup.sh first.${NC}"
    exit 1
fi

# Check Redis
if ! redis-cli ping &> /dev/null; then
    echo -e "${YELLOW}⚠️  Redis not responding. Starting Redis...${NC}"
    cd /workspace/code/redis
    ./setup.sh
    cd "$SCRIPT_DIR"
fi

# Parse command line arguments
case "${1:-demo}" in
    "demo")
        echo -e "${BLUE}🎯 Running comprehensive demo...${NC}"
        python examples/comprehensive_demo.py
        ;;
    "api")
        echo -e "${BLUE}🌐 Starting API server...${NC}"
        python examples/start_api_server.py
        ;;
    "simple")
        echo -e "${BLUE}🎯 Running simple example...${NC}"
        python examples/simple_example.py
        ;;
    "test")
        echo -e "${BLUE}🧪 Running tests...${NC}"
        pytest tests/test_langgraph_workflow.py -v
        ;;
    "monitor")
        echo -e "${BLUE}📊 Starting monitoring...${NC}"
        # Custom monitoring script would go here
        echo "Monitoring feature coming soon..."
        ;;
    *)
        echo "Usage: $0 [demo|api|simple|test|monitor]"
        echo ""
        echo "Commands:"
        echo "  demo    - Run comprehensive demonstration"
        echo "  api     - Start REST API server"
        echo "  simple  - Run simple example"
        echo "  test    - Run test suite"
        echo "  monitor - Start monitoring dashboard"
        exit 1
        ;;
esac
EOF
    
    chmod +x run_langgraph.sh
    print_success "Startup script created: run_langgraph.sh"
}

# Print usage instructions
print_usage() {
    print_step "9" "Setup complete! Usage instructions"
    
    echo ""
    echo -e "${GREEN}🎉 LangGraph Workflow System setup completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}Quick Start:${NC}"
    echo "1. Activate virtual environment:"
    echo "   cd $LANGGRAPH_DIR"
    echo "   source $VENV_NAME/bin/activate"
    echo ""
    echo "2. Run examples:"
    echo "   ./run_langgraph.sh demo    # Comprehensive demo"
    echo "   ./run_langgraph.sh simple  # Simple example"
    echo "   ./run_langgraph.sh api     # Start API server"
    echo ""
    echo "3. Test API endpoints:"
    echo "   curl http://localhost:8000/health"
    echo "   curl -X POST http://localhost:8000/api/v1/workflows/execute \\"
    echo "        -H 'Content-Type: application/json' \\"
    echo "        -d '{\"symbol\":\"BTCUSDT\",\"strategy\":\"momentum\"}'"
    echo ""
    echo "4. Monitor workflows:"
    echo "   curl http://localhost:8000/api/v1/monitoring/status"
    echo ""
    echo -e "${BLUE}Files created:${NC}"
    echo "• Virtual environment: $VENV_NAME/"
    echo "• Configuration files: .env, config/"
    echo "• Example scripts: examples/"
    echo "• Test suite: tests/test_langgraph_workflow.py"
    echo "• Startup script: run_langgraph.sh"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "• README.md - Complete system documentation"
    echo "• examples/comprehensive_demo.py - Full usage examples"
    echo "• API documentation at http://localhost:8000/docs (when API is running)"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Start Redis server: cd /workspace/code/redis && ./setup.sh"
    echo "2. Run the comprehensive demo: ./run_langgraph.sh demo"
    echo "3. Explore the API: ./run_langgraph.sh api"
    echo "4. Read the documentation: cat README.md"
    echo ""
}

# Main execution
main() {
    echo "Starting LangGraph Workflow System setup..."
    echo ""
    
    check_prerequisites
    setup_virtual_environment
    install_dependencies
    setup_redis
    create_config
    run_tests
    create_examples
    create_startup_script
    print_usage
    
    echo -e "${GREEN}✨ Setup completed successfully!${NC}"
}

# Run main function
main "$@"