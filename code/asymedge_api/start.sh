#!/bin/bash

# ASYMEdge Dashboard API Startup Script
# This script starts the ASYMEdge API server with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
WORKERS=${WORKERS:-4}
LOG_LEVEL=${LOG_LEVEL:-"INFO"}
RELOAD=${RELOAD:-"true"}

echo -e "${BLUE}🚀 Starting ASYMEdge Dashboard API${NC}"
echo -e "${BLUE}===================================${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Install/update dependencies
echo -e "${BLUE}📋 Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p logs
mkdir -p uploads
mkdir -p backups

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export LOG_LEVEL="$LOG_LEVEL"
export HOST="$HOST"
export PORT="$PORT"

# Check if .env file exists
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ Loading environment variables from .env${NC}"
    set -a
    source .env
    set +a
else
    echo -e "${YELLOW}⚠️  No .env file found, using default settings${NC}"
fi

# Validate database connection
echo -e "${BLUE}🗄️  Checking database connection...${NC}"
python -c "
import asyncio
import sys
sys.path.append('.')
from api.database.database import check_database_health

async def check_db():
    health = await check_database_health()
    if health['status'] == 'healthy':
        print('✅ Database connection successful')
    else:
        print('❌ Database connection failed')
        print(f'Error: {health.get(\"error\", \"Unknown error\")}')
        sys.exit(1)

asyncio.run(check_db())
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Database check failed${NC}"
    exit 1
fi

# Start the application
echo -e "${GREEN}🌟 Starting ASYMEdge API server...${NC}"
echo -e "${BLUE}Server Configuration:${NC}"
echo -e "  Host: $HOST"
echo -e "  Port: $PORT"
echo -e "  Workers: $WORKERS"
echo -e "  Log Level: $LOG_LEVEL"
echo -e "  Reload: $RELOAD"
echo ""

# Build uvicorn command
UVICORN_CMD="uvicorn main:app --host $HOST --port $PORT --workers $WORKERS --log-level $LOG_LEVEL"

if [ "$RELOAD" = "true" ]; then
    UVICORN_CMD="$UVICORN_CMD --reload"
fi

# Start server
eval $UVICORN_CMD