#!/bin/bash
# Letta Server Setup and Startup Script

set -e

echo "Letta Server Setup and Startup"
echo "==============================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p data logs config init-scripts

# Copy environment template if .env doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your actual API keys and configuration."
fi

# Start services
echo "Starting Letta services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Check if services are running
echo "Checking service status..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
else
    echo "❌ Some services failed to start. Check logs with: docker-compose logs"
    exit 1
fi

# Test server health
echo "Testing server health..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8283/health > /dev/null 2>&1; then
        echo "✅ Letta server is healthy!"
        break
    fi
    
    echo "Waiting for server to be ready... (attempt $attempt/$max_attempts)"
    sleep 10
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Server failed to start within timeout period."
    echo "Check logs with: docker-compose logs letta-server"
    exit 1
fi

# Create trading agents
echo "Creating trading agents..."
if python3 create_agents.py; then
    echo "✅ Trading agents created successfully!"
else
    echo "⚠️  Agent creation failed. You can run it manually later with: python3 create_agents.py"
fi

# Run functionality tests
echo "Running functionality tests..."
if python3 test_letta_server.py; then
    echo "✅ All tests passed!"
else
    echo "⚠️  Some tests failed. Check the test report for details."
fi

echo ""
echo "Letta Server Setup Complete!"
echo "============================"
echo ""
echo "Services running:"
echo "  - Letta Server: http://localhost:8283"
echo "  - Letta Admin UI: http://localhost:3000 (if admin profile is enabled)"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "Available endpoints:"
echo "  - Health check: http://localhost:8283/health"
echo "  - API docs: http://localhost:8283/docs"
echo "  - Agent management: POST http://localhost:8283/api/agents"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - Stop services: docker-compose down"
echo "  - Restart services: docker-compose restart"
echo "  - Test API: python3 test_letta_server.py"
echo "  - Create agents: python3 create_agents.py"
echo ""
echo "Agent IDs saved to: agent_ids.json"
echo "Test report saved to: test_report.txt"