#!/bin/bash

# LangGraph API Service - Quick Start Script

echo "🚀 LangGraph API Service Quick Start"
echo "===================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Start services
echo "📦 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if API is running
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API Service is running!"
else
    echo "❌ API Service failed to start"
    echo "Check logs with: docker-compose logs api"
    exit 1
fi

echo ""
echo "🎉 LangGraph API Service is ready!"
echo ""
echo "📍 Service URLs:"
echo "   API:          http://localhost:8000"
echo "   Documentation: http://localhost:8000/docs"
echo "   Health Check:  http://localhost:8000/health"
echo "   Metrics:       http://localhost:8000/metrics"
echo ""
echo "📊 Additional Services:"
echo "   Prometheus:   http://localhost:9090"
echo "   Grafana:      http://localhost:3000 (admin/admin123)"
echo "   Adminer:      http://localhost:8080"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs:    docker-compose logs -f api"
echo "   Stop services: docker-compose down"
echo "   Restart:      docker-compose restart api"
echo ""
echo "🔐 Default Admin User:"
echo "   Register via: http://localhost:8000/docs#/Authentication/register"
echo ""
echo "Happy coding! 🚀"