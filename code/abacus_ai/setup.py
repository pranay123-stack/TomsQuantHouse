#!/usr/bin/env python3
"""
Configuration creator for Abacus.AI Integration
"""

import os
from pathlib import Path
from utils.helpers import create_sample_config

# Create necessary directories
directories = [
    "config",
    "data/raw", 
    "data/processed",
    "data/features",
    "models/trained",
    "models/deployed",
    "logs", 
    "reports",
    "cache",
    "tests"
]

for directory in directories:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Create sample configuration
config_path = "config/config.yaml"
create_sample_config(config_path)

# Create environment file template
env_template = """# Abacus.AI Integration Environment Configuration
# Copy this to .env and fill in your actual values

# Required: Abacus.AI API Key
ABACUS_AI_API_KEY=your-abacus-ai-api-key-here

# Optional: Redis Configuration  
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Optional: News API for sentiment analysis
NEWS_API_KEY=your-news-api-key-here

# Optional: Docker Registry
DOCKER_REGISTRY=docker.io

# Optional: AWS Configuration (for deployments)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1

# Optional: Logging
LOG_LEVEL=INFO
LOG_FILE=logs/abacus_ai.log
"""

env_path = ".env.example"
with open(env_path, 'w') as f:
    f.write(env_template)

print("✅ Configuration files created successfully!")
print(f"📁 Sample configuration: {config_path}")
print(f"📁 Environment template: {env_path}")
print("\nNext steps:")
print("1. Copy .env.example to .env")
print("2. Fill in your API keys in .env")
print("3. Update config/config.yaml with your preferences")
print("4. Run: python example.py")