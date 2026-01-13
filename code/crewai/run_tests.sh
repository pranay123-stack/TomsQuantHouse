#!/bin/bash
# Test runner script for CrewAI Trading System
# Usage: ./run_tests.sh [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
RUN_UNIT=true
RUN_INTEGRATION=false
RUN_E2E=false
RUN_API=false
RUN_SLOW=false
RUN_REDIS=false
RUN_COVERAGE=false
RUN_PARALLEL=false
CLEANUP=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            shift
            ;;
        --e2e)
            RUN_E2E=true
            shift
            ;;
        --api)
            RUN_API=true
            shift
            ;;
        --slow)
            RUN_SLOW=true
            shift
            ;;
        --redis)
            RUN_REDIS=true
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --parallel)
            RUN_PARALLEL=true
            shift
            ;;
        --cleanup)
            CLEANUP=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

show_help() {
    echo -e "${BLUE}CrewAI Trading System Test Runner${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --unit          Run unit tests (default)"
    echo "  --integration   Run integration tests"
    echo "  --e2e          Run end-to-end tests"
    echo "  --api           Run API tests"
    echo "  --slow          Include slow tests"
    echo "  --redis         Include Redis-dependent tests"
    echo "  --coverage      Generate coverage report"
    echo "  --parallel      Run tests in parallel"
    echo "  --cleanup       Clean test data after running"
    echo "  --verbose, -v   Verbose output"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --unit                    # Run unit tests"
    echo "  $0 --integration --redis     # Run integration tests with Redis"
    echo "  $0 --e2e --coverage          # Run E2E tests with coverage"
    echo "  $0 --all --parallel          # Run all tests in parallel"
    echo ""
}

check_dependencies() {
    echo -e "${BLUE}Checking dependencies...${NC}"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is required${NC}"
        exit 1
    fi
    
    # Check pytest
    if ! python3 -c "import pytest" &> /dev/null; then
        echo -e "${YELLOW}Installing pytest...${NC}"
        pip install pytest pytest-asyncio
    fi
    
    # Check Redis (if needed)
    if [[ "$RUN_REDIS" == true ]] || [[ "$RUN_INTEGRATION" == true ]]; then
        if ! command -v redis-cli &> /dev/null; then
            echo -e "${YELLOW}Warning: Redis CLI not found. Starting Docker Redis...${NC}"
            if command -v docker &> /dev/null; then
                docker run -d -p 6379:6379 --name test-redis redis:7-alpine 2>/dev/null || true
                sleep 2
            else
                echo -e "${YELLOW}Warning: Docker not found. Redis tests may fail.${NC}"
            fi
        fi
    fi
}

setup_environment() {
    echo -e "${BLUE}Setting up test environment...${NC}"
    
    # Set test environment variables
    export TESTING=true
    export REDIS_URL="redis://localhost:6379/15"
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
    
    # Create test directories if they don't exist
    mkdir -p tests/reports
    mkdir -p tests/logs
    
    echo -e "${GREEN}Environment setup complete${NC}"
}

run_tests() {
    local test_marker=""
    local test_path=""
    
    # Build pytest command
    local cmd="python3 -m pytest"
    
    # Add markers
    local markers=()
    if [[ "$RUN_UNIT" == true ]]; then
        markers+=("unit")
    fi
    if [[ "$RUN_INTEGRATION" == true ]]; then
        markers+=("integration")
    fi
    if [[ "$RUN_E2E" == true ]]; then
        markers+=("e2e")
    fi
    if [[ "$RUN_API" == true ]]; then
        markers+=("api")
    fi
    
    # Build marker expression
    if [[ ${#markers[@]} -gt 0 ]]; then
        local marker_expr=$(IFS=" or "; echo "${markers[*]}")
        cmd="$cmd -m \"$marker_expr\""
    fi
    
    # Add options
    if [[ "$RUN_SLOW" == false ]]; then
        cmd="$cmd -m \"not slow\""
    fi
    
    if [[ "$RUN_REDIS" == false ]]; then
        cmd="$cmd -m \"not redis\""
    fi
    
    if [[ "$RUN_PARALLEL" == true ]]; then
        cmd="$cmd -n auto"
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        cmd="$cmd -v"
    fi
    
    if [[ "$RUN_COVERAGE" == true ]]; then
        cmd="$cmd --cov=orchestration --cov=agents --cov-report=html --cov-report=term-missing"
    fi
    
    # Add output options
    cmd="$cmd --html=tests/reports/report.html --self-contained-html"
    cmd="$cmd --junitxml=tests/reports/junit.xml"
    
    # Add test discovery
    cmd="$cmd tests/"
    
    echo -e "${BLUE}Running tests: $cmd${NC}"
    echo ""
    
    if eval "$cmd"; then
        echo -e "${GREEN}✓ Tests completed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        return 1
    fi
}

generate_reports() {
    echo -e "${BLUE}Generating reports...${NC}"
    
    # Generate additional reports if coverage was run
    if [[ "$RUN_COVERAGE" == true ]]; then
        echo -e "${GREEN}Coverage report generated at tests/reports/htmlcov/index.html${NC}"
        
        # Try to open coverage report (if possible)
        if command -v open &> /dev/null; then
            open tests/reports/htmlcov/index.html 2>/dev/null || true
        elif command -v xdg-open &> /dev/null; then
            xdg-open tests/reports/htmlcov/index.html 2>/dev/null || true
        fi
    fi
    
    # Show test report location
    echo -e "${GREEN}Test report generated at tests/reports/report.html${NC}"
    
    # Show JUnit XML for CI integration
    echo -e "${GREEN}JUnit XML report at tests/reports/junit.xml${NC}"
}

cleanup() {
    if [[ "$CLEANUP" == true ]]; then
        echo -e "${BLUE}Cleaning up test environment...${NC}"
        
        # Clean Redis test data
        if command -v redis-cli &> /dev/null; then
            redis-cli -p 6379 -n 15 FLUSHDB 2>/dev/null || true
        fi
        
        # Clean up Docker Redis if started by this script
        if [[ "$RUN_REDIS" == true ]] || [[ "$RUN_INTEGRATION" == true ]]; then
            docker stop test-redis 2>/dev/null || true
            docker rm test-redis 2>/dev/null || true
        fi
        
        echo -e "${GREEN}Cleanup complete${NC}"
    fi
}

print_summary() {
    echo ""
    echo -e "${BLUE}=== Test Run Summary ===${NC}"
    echo -e "${BLUE}Unit tests:${NC} $([ "$RUN_UNIT" == true ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
    echo -e "${BLUE}Integration tests:${NC} $([ "$RUN_INTEGRATION" == true ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
    echo -e "${BLUE}E2E tests:${NC} $([ "$RUN_E2E" == true ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
    echo -e "${BLUE}API tests:${NC} $([ "$RUN_API" == true ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
    echo -e "${BLUE}Coverage report:${NC} $([ "$RUN_COVERAGE" == true ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
    echo -e "${BLUE}Parallel execution:${NC} $([ "$RUN_PARALLEL" == true ] && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}")"
    echo ""
    echo -e "${BLUE}Reports location: tests/reports/${NC}"
    echo ""
}

# If no arguments provided, show help
if [[ $# -eq 0 ]]; then
    echo -e "${YELLOW}No options specified. Running unit tests by default.${NC}"
    echo -e "${YELLOW}Use --help for available options.${NC}"
    echo ""
    RUN_UNIT=true
fi

# Main execution
main() {
    echo -e "${BLUE}🧪 CrewAI Trading System Test Runner${NC}"
    echo ""
    
    # Check dependencies
    check_dependencies
    
    # Setup environment
    setup_environment
    
    # Run tests
    local start_time=$(date +%s)
    if run_tests; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo ""
        echo -e "${GREEN}✓ All tests completed in ${duration}s${NC}"
        
        # Generate reports
        if [[ "$RUN_COVERAGE" == true ]]; then
            generate_reports
        fi
        
        # Cleanup
        cleanup
        
        # Print summary
        print_summary
        
        exit 0
    else
        echo ""
        echo -e "${RED}✗ Test execution failed${NC}"
        
        # Cleanup even on failure
        cleanup
        
        # Print summary
        print_summary
        
        exit 1
    fi
}

# Run main function
main