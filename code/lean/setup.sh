#!/bin/bash

# Setup script for Abacus.AI LEAN Integration
# This script helps set up the development environment

set -e

echo "🚀 Abacus.AI LEAN Integration Setup"
echo "===================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "📦 Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if Redis is available
echo "🔍 Checking Redis availability..."
if command -v redis-server &> /dev/null; then
    echo "✅ Redis found: $(redis-server --version)"
    echo "💡 To start Redis: redis-server"
else
    echo "⚠️  Redis not found. Install Redis for real-time features:"
    echo "   - macOS: brew install redis"
    echo "   - Ubuntu: sudo apt-get install redis-server"
    echo "   - Windows: Download from https://redis.io/download"
fi

# Create data directories
echo "📁 Creating data directories..."
mkdir -p data/raw
mkdir -p data/processed
mkdir -p output/logs
mkdir -p output/reports

# Copy configuration template
if [ ! -f ".env" ]; then
    echo "📋 Creating environment configuration template..."
    cat > .env << EOF
# Abacus.AI Configuration
ABACUS_AI_API_KEY=your_api_key_here
ABACUS_AI_BASE_URL=https://api.abacus.ai

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# LEAN Configuration
LEAN_DATA_FOLDER=./data
LEAN_OUTPUT_FOLDER=./output

# Trading Configuration (Optional)
ALERT_EMAIL=your_email@company.com
ALERT_WEBHOOK=https://hooks.slack.com/your-webhook
EOF
    echo "✅ Created .env template"
    echo "⚠️  Please edit .env with your actual configuration"
else
    echo "✅ Configuration file .env already exists"
fi

# Create symbolic links for LEAN (if LEAN is installed)
if [ -d "$HOME/.quantconnect" ]; then
    echo "🔗 Setting up LEAN integration..."
    
    # Create algorithm directory
    LEAN_ALGO_DIR="$HOME/.quantconnect/Algorithms"
    if [ -d "$LEAN_ALGO_DIR" ]; then
        mkdir -p "$LEAN_ALGO_DIR/AbacusAI"
        cp -r algorithms/* "$LEAN_ALGO_DIR/AbacusAI/"
        echo "✅ LEAN algorithm copied to $LEAN_ALGO_DIR/AbacusAI"
    else
        echo "ℹ️  LEAN algorithms directory not found. Install LEAN for full integration."
    fi
else
    echo "ℹ️  LEAN not detected. Install LEAN CLI: pip install lean-cli"
fi

# Run initial test
echo "🧪 Running initial test..."
python3 -c "
try:
    import sys
    sys.path.append('.')
    from config.config import get_config
    config = get_config('development')
    print('✅ Configuration system working')
    
    from research.backtesting_framework import AbacusAIBacktestFramework
    backtester = AbacusAIBacktestFramework(['AAPL'], 10000)
    print('✅ Backtesting framework working')
    
    print('✅ All core components initialized successfully!')
except Exception as e:
    print(f'❌ Error during initialization: {e}')
    sys.exit(1)
"

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Start Redis: redis-server (if you want real-time features)"
echo "3. Run the example: python3 example_complete.py"
echo "4. For LEAN integration: lean cloud deploy"
echo ""
echo "Documentation: See README.md for detailed usage instructions"
echo "Example usage: python3 example_complete.py"
echo ""

# Make the script executable
chmod +x setup.sh