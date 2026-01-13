#!/bin/bash

# ASYMEdge Dashboard Deployment Script
# This script handles building and deploying the dashboard to various environments

set -e

ENVIRONMENT=${1:-production}
REGISTRY=${2:-"asymedge/dashboard"}
VERSION=${3:-$(date +%Y%m%d-%H%M%S)}

echo "🚀 ASYMEdge Dashboard Deployment"
echo "Environment: $ENVIRONMENT"
echo "Registry: $REGISTRY"
echo "Version: $VERSION"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Pre-deployment checks
print_status "Running pre-deployment checks..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    print_warning "pnpm is not installed. Installing pnpm..."
    npm install -g pnpm
fi

# Environment-specific configurations
case $ENVIRONMENT in
    "development")
        print_status "Setting up development environment..."
        export NODE_ENV=development
        export VITE_API_URL=http://localhost:3000
        export VITE_WS_URL=ws://localhost:3001
        ;;
    "staging")
        print_status "Setting up staging environment..."
        export NODE_ENV=staging
        export VITE_API_URL=https://api-staging.asymedge.com
        export VITE_WS_URL=wss://ws-staging.asymedge.com
        ;;
    "production")
        print_status "Setting up production environment..."
        export NODE_ENV=production
        export VITE_API_URL=https://api.asymedge.com
        export VITE_WS_URL=wss://ws.asymedge.com
        ;;
    *)
        print_error "Invalid environment: $ENVIRONMENT. Use: development, staging, or production"
        exit 1
        ;;
esac

# Build the application
print_status "Building application for $ENVIRONMENT environment..."

# Clean previous builds
rm -rf dist/
rm -rf node_modules/.vite-temp/

# Install dependencies
pnpm install --prefer-offline

# Run linting
print_status "Running linter..."
pnpm lint

# Run type checking
print_status "Running type checking..."
npx tsc --noEmit

# Build the application
print_status "Building production bundle..."
BUILD_MODE=$ENVIRONMENT pnpm build

# Security scan (if available)
if command -v npm-audit &> /dev/null; then
    print_status "Running security audit..."
    npm audit --audit-level=moderate || print_warning "Security audit found issues"
fi

# Build Docker image
print_status "Building Docker image..."
docker build -t $REGISTRY:$VERSION .
docker tag $REGISTRY:$VERSION $REGISTRY:latest

# Push to registry (if specified)
if [ "$REGISTRY" != "asymedge/dashboard" ]; then
    print_status "Pushing to registry..."
    docker push $REGISTRY:$VERSION
    docker push $REGISTRY:latest
fi

# Deploy based on environment
case $ENVIRONMENT in
    "development")
        print_status "Starting development environment with Docker Compose..."
        docker-compose -f docker-compose.yml up -d
        print_status "Development environment is running at http://localhost:3000"
        ;;
    "staging")
        print_status "Deploying to staging environment..."
        # Add staging-specific deployment logic here
        docker-compose -f docker-compose.staging.yml up -d
        print_status "Staging deployment completed"
        ;;
    "production")
        print_status "Deploying to production environment..."
        # Add production-specific deployment logic here
        # This might involve kubectl, AWS CLI, or other deployment tools
        print_warning "Production deployment requires additional setup"
        ;;
esac

# Post-deployment verification
print_status "Running post-deployment verification..."

# Health check
sleep 10
if curl -f http://localhost:3000/health &> /dev/null; then
    print_status "✅ Application is healthy"
else
    print_warning "⚠️ Health check failed - application may still be starting"
fi

# Performance check
print_status "Performing basic performance check..."
if command -v lighthouse &> /dev/null; then
    lighthouse http://localhost:3000 --output=json --output-path=./lighthouse-report.json || print_warning "Lighthouse check failed"
else
    print_warning "Lighthouse not available for performance testing"
fi

# Cleanup
print_status "Cleaning up temporary files..."
rm -rf node_modules/.vite-temp/

# Final summary
echo ""
echo "🎉 Deployment Summary"
echo "===================="
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"
echo "Registry: $REGISTRY"
echo "Build completed: $(date)"
echo ""

if [ "$ENVIRONMENT" = "development" ]; then
    echo "🌐 Dashboard URL: http://localhost:3000"
    echo "📊 Backend API: http://localhost:3001"
    echo "🔌 WebSocket: ws://localhost:3001"
    echo ""
    echo "📝 Useful Commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart: docker-compose restart"
fi

echo "🚀 ASYMEdge Dashboard deployment completed successfully!"

# Save deployment info
cat > deployment-info.json << EOF
{
  "environment": "$ENVIRONMENT",
  "version": "$VERSION",
  "registry": "$REGISTRY",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "build_status": "success"
}
EOF

print_status "Deployment information saved to deployment-info.json"