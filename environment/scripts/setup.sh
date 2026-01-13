#!/bin/bash
# Environment Management System Setup Script

set -e

echo "🚀 Setting up Environment Management System..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ~/.env_mgmt/{backups,logs,history,secrets}
mkdir -p environment/templates
mkdir -p environment/tools
mkdir -p environment/docs
mkdir -p environment/scripts
mkdir -p environment/tests

# Set permissions for sensitive directories
chmod 700 ~/.env_mgmt
chmod 600 ~/.env_mgmt/* 2>/dev/null || true

# Initialize the system
echo "🔧 Initializing Environment Management System..."
python3 environment/environment_manager.py init

# Create sample configurations if they don't exist
if [ ! -f "environment/templates/development.yaml" ]; then
    echo "📝 Creating sample configuration templates..."
    # Templates will be created by the init process
fi

# Set up logging
echo "📋 Setting up logging..."
touch ~/.env_mgmt/logs/secrets.log
touch ~/.env_mgmt/logs/config.log
touch ~/.env_mgmt/logs/backup.log
touch ~/.env_mgmt/logs/deployment.log

# Run a health check
echo "🔍 Running system health check..."
python3 environment/environment_manager.py health-check

# Show system status
echo "📊 System status:"
python3 environment/environment_manager.py status

echo ""
echo "✅ Environment Management System setup completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Review configuration templates in environment/templates/"
echo "  2. Store your secrets: python3 environment/environment_manager.py secrets store --name <name> --value <value> --environment <env>"
echo "  3. Validate environments: python3 environment/environment_manager.py validate --environment <env>"
echo "  4. Create backups: python3 environment/environment_manager.py backup --environment <env>"
echo "  5. Deploy to environments: python3 environment/environment_manager.py deploy --environment <env> --version <version>"
echo ""
echo "For more information, see: environment/docs/README.md"
echo ""

# Make the main script executable
chmod +x environment/environment_manager.py
chmod +x environment/secrets_mgmt/secrets_manager.py
chmod +x environment/config_manager.py
chmod +x environment/tools/backup_migration.py
chmod +x environment/tools/testing_validation.py
chmod +x environment/tools/deployment_automation.py

echo "🔧 Made management scripts executable"
echo "🎉 Setup complete!"