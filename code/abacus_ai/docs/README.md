# Abacus.AI Integration Documentation

This directory contains a complete integration solution for Abacus.AI ML pipeline, featuring automated model training, real-time prediction API, and comprehensive feature engineering.

## 🚀 Overview

The Abacus.AI integration provides:

- **Feature Group Management**: Create and manage feature groups with automatic schema validation
- **Automated Model Training**: Train multiple ML models and select the best performer
- **Real-time Predictions**: Fast API with caching and error handling
- **Feature Engineering**: Technical indicators and sentiment analysis
- **Model Deployment**: Automated deployment with token management
- **Caching Layer**: Redis-based prediction caching with smart eviction

## 📁 Directory Structure

```
code/abacus_ai/
├── client/                  # Abacus.AI API client
│   └── abacus_client.py    # Main client implementation
├── training/                # Model training pipeline
│   └── model_trainer.py    # Automated training and evaluation
├── api/                    # Real-time prediction API
│   └── prediction_api.py   # FastAPI-based prediction service
├── deployment/              # Model deployment scripts
│   └── deploy.py           # Deployment automation
├── features/                # Feature engineering
│   └── feature_engineering.py  # Technical indicators & sentiment
├── cache/                   # Caching layer
│   └── prediction_cache.py # Redis caching implementation
├── utils/                   # Utility functions
│   └── helpers.py          # Helper utilities
├── tests/                   # Test files
└── docs/                    # Documentation
```

## 🛠️ Installation

### Prerequisites

```bash
# Python packages
pip install pandas numpy scikit-learn joblib redis fastapi uvicorn
pip install yfinance textblob requests boto3 docker

# Optional ML packages
pip install xgboost lightgbm talib

# System dependencies
sudo apt-get update
sudo apt-get install redis-server redis-tools
```

### Environment Setup

```bash
# Create environment file
cp .env.example .env

# Set required environment variables
export ABACUS_AI_API_KEY=your-api-key-here
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
```

## 🚦 Quick Start

### 1. Configure Environment

```python
from code.abacus_ai.utils.helpers import load_config, setup_logging

# Load configuration
config = load_config('config/config.yaml')

# Setup logging
setup_logging('INFO', 'logs/abacus_ai.log')
```

### 2. Initialize Client

```python
from code.abacus_ai.client.abacus_client import AbacusAIClient

# Initialize client
client = AbacusAIClient(api_key=os.getenv('ABACUS_AI_API_KEY'))

# Create feature group
feature_schema = [
    {"name": "symbol", "type": "string", "description": "Stock symbol"},
    {"name": "price", "type": "float", "description": "Stock price"},
    {"name": "volume", "type": "integer", "description": "Trading volume"}
]

feature_group = client.create_feature_group(
    name="market_data",
    description="Market data features",
    schema=feature_schema
)
```

### 3. Feature Engineering

```python
from code.abacus_ai.features.feature_engineering import FeatureEngineeringPipeline

# Initialize pipeline
feature_pipeline = FeatureEngineeringPipeline()

# Create prediction dataset
features, scaler = feature_pipeline.create_prediction_dataset(
    symbols=['AAPL', 'GOOGL'],
    start_date='2023-01-01',
    end_date='2023-12-31',
    periods_ahead=1,
    include_sentiment=True
)

print(f"Created {features.shape[1]} features for {features.shape[0]} samples")
```

### 4. Model Training

```python
from code.abacus_ai.training.model_trainer import ModelTrainer, ModelEvaluator

# Initialize trainer
trainer = ModelTrainer(client, config['model'])

# Train models
results = trainer.train_models(features)

# Evaluate and select best model
evaluator = ModelEvaluator(trainer)
report = evaluator.generate_report(results)
evaluator.save_report(report, 'reports/model_evaluation.json')

# Save best model
trainer.save_model('models/trained/best_model.pkl')
```

### 5. Real-time Predictions

```python
from code.abacus_ai.api.prediction_api import AbacusAIPredictor, PredictionCache

# Initialize cache
cache = PredictionCache()

# Create predictor
predictor = AbacusAIPredictor(client, trainer, cache)

# Make prediction
from code.abacus_ai.api.prediction_api import PredictionRequest

request = PredictionRequest(
    symbol='AAPL',
    features={'open': 150, 'high': 155, 'low': 149, 'close': 153, 'volume': 1000000},
    timestamp=datetime.utcnow()
)

response = await predictor._make_prediction(request)
print(f"Prediction: {response.prediction}, Confidence: {response.confidence}")
```

### 6. Start API Server

```python
# Start FastAPI server
predictor.start_server(host='0.0.0.0', port=8000)
```

### 7. Deploy Model

```python
from code.abacus_ai.deployment.deploy import ModelDeployer, TokenManager

# Initialize deployer
token_manager = TokenManager()
deployer = ModelDeployer(token_manager)

# Deploy model
deployment_result = deployer.deploy_model(
    model_path='models/trained/best_model.pkl',
    model_config=config['model'],
    environment='production'
)

print(f"Deployed model: {deployment_result['deployment_id']}")
```

## 📊 Components

### Abacus.AI Client (`client/abacus_client.py`)

Handles communication with Abacus.AI API:

```python
# Feature group operations
client.create_feature_group(name, description, schema)
client.upload_data(feature_group_id, data)
client.validate_schema(data, schema)

# Data validation and error handling
validation_result = client.validate_schema(data, schema)
if not validation_result['is_valid']:
    print(f"Validation issues: {validation_result['issues']}")
```

### Model Training (`training/model_trainer.py`)

Automated training pipeline with multiple algorithms:

```python
# Configure training
config = {
    "models": {
        "random_forest": {"algorithm": "random_forest", "params": {...}},
        "xgboost": {"algorithm": "xgboost", "params": {...}},
        "lightgbm": {"algorithm": "lightgbm", "params": {...}}
    },
    "test_size": 0.2,
    "cv_folds": 5
}

# Train and evaluate
trainer = ModelTrainer(client, config)
results = trainer.train_models(data)

# Get best model
best_model = trainer.best_model
best_score = trainer.best_score
```

### Feature Engineering (`features/feature_engineering.py`)

Comprehensive market data feature engineering:

```python
# Technical indicators
feature_pipeline = FeatureEngineeringPipeline()

# RSI, MACD, Bollinger Bands
features = feature_pipeline.create_features(data)

# Sentiment analysis
features = feature_pipeline.create_features(
    data, 
    include_sentiment=True,
    sentiment_lookback=7
)

# Custom indicators
indicators = TechnicalIndicators()
features['rsi'] = indicators.calculate_rsi(price_series, period=14)
features['macd'] = indicators.calculate_macd(price_series)
```

### Prediction API (`api/prediction_api.py`)

FastAPI-based real-time prediction service:

```python
# Initialize with caching
cache = PredictionCache(ttl=300)
predictor = AbacusAIPredictor(client, model, cache)

# REST endpoints
# POST /predict - Single prediction
# GET /health - Health check
# POST /batch_predict - Batch predictions
# DELETE /cache - Clear cache

# Automatic caching and retry logic
response = await predictor._make_prediction(request)
print(f"Response: {response.prediction}, Cached: {response.cached}")
```

### Deployment (`deployment/deploy.py`)

Automated model deployment with token management:

```python
# Token management
token_manager = TokenManager()
api_key = token_manager.get_api_key('production')

# Model deployment
deployer = ModelDeployer(token_manager)
result = deployer.deploy_model(model_path, config, environment='production')

# Scaling and monitoring
deployer.scale_deployment(deployment_id, min_instances=1, max_instances=10)
status = deployer._get_deployment_status(deployment_id)
```

### Caching Layer (`cache/prediction_cache.py`)

Redis-based caching with smart eviction:

```python
# Initialize cache
cache = PredictionCache(
    redis_config={'host': 'localhost', 'port': 6379},
    cache_strategy=CacheStrategy.LRU,
    max_memory=100 * 1024 * 1024  # 100MB
)

# Cache predictions
cache.set(symbol, features, result, ttl=300)

# Retrieve with automatic caching
prediction, is_cached = cache.get(symbol, features)

# Smart caching with prediction
smart_cache = PredictiveCache()
ttl = smart_cache.get_smart_ttl(symbol, features)
```

## ⚙️ Configuration

### Main Configuration (`config/config.yaml`)

```yaml
abacus_ai:
  api_key: your-api-key-here
  base_url: https://api.abacus.ai
  timeout: 30
  retries: 3

redis:
  host: localhost
  port: 6379
  db: 0

model:
  algorithms: [random_forest, xgboost, lightgbm]
  test_size: 0.2
  target_column: future_return
  scaler: standard

features:
  technical_indicators:
    rsi_period: 14
    macd_fast: 12
    macd_slow: 26
  sentiment:
    enabled: true
    lookback_days: 7

deployment:
  environment: production
  scaling:
    min_instances: 1
    max_instances: 10

cache:
  strategy: ttl
  max_memory: 104857600
  default_ttl: 300
```

### Environment Variables

```bash
# Required
ABACUS_AI_API_KEY=your-api-key

# Optional
REDIS_HOST=localhost
REDIS_PORT=6379
NEWS_API_KEY=your-news-api-key
DOCKER_REGISTRY=docker.io
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_client.py -v

# Run with coverage
python -m pytest tests/ --cov=code.abacus_ai --cov-report=html
```

### Integration Tests

```python
# Test full pipeline
from code.abacus_ai.tests.integration import test_full_pipeline

def test_full_pipeline():
    # Test data fetching, feature engineering, training, and prediction
    pass
```

## 📈 Monitoring and Logging

### Log Configuration

```python
from code.abacus_ai.utils.helpers import setup_logging

# Setup structured logging
setup_logging(
    log_level="INFO",
    log_file="logs/abacus_ai.log"
)

# Monitor API health
from code.abacus_ai.utils.helpers import monitor_api_health

health = monitor_api_health("https://api.abacus.ai")
print(f"API Status: {health['status']}")
```

### Metrics Collection

```python
# Cache metrics
cache_stats = cache.get_stats()
print(f"Cache Hit Rate: {cache_stats['hit_rate']:.2%}")
print(f"Memory Usage: {cache_stats['memory_usage_percent']:.1f}%")

# Prediction metrics
monitor = PredictionMonitor()
monitor.record_prediction(response)
metrics = monitor.get_metrics()
```

## 🚀 Deployment Options

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: abacus-ai-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: abacus-ai-service
  template:
    metadata:
      labels:
        app: abacus-ai-service
    spec:
      containers:
      - name: abacus-ai
        image: abacus-ai:latest
        ports:
        - containerPort: 8000
        env:
        - name: ABACUS_AI_API_KEY
          valueFrom:
            secretKeyRef:
              name: abacus-secrets
              key: api-key
```

## 🔧 Advanced Usage

### Custom Feature Engineering

```python
class CustomFeaturePipeline(FeatureEngineeringPipeline):
    def create_custom_features(self, data):
        # Add your custom features
        features = {}
        
        # Custom momentum indicator
        features['custom_momentum'] = self._calculate_momentum(data['close'])
        
        # Custom volatility measure
        features['custom_volatility'] = self._calculate_volatility(data)
        
        return features

# Use custom pipeline
custom_pipeline = CustomFeaturePipeline()
features = custom_pipeline.create_features(data)
```

### Custom Model Algorithms

```python
# Add new algorithm to model trainer
class CustomModelTrainer(ModelTrainer):
    def _get_model(self, algorithm):
        if algorithm == "custom_algo":
            return CustomAlgorithm()
        return super()._get_model(algorithm)

# Use in configuration
config = {
    "models": {
        "custom_model": {
            "algorithm": "custom_algo",
            "params": {"param1": [1, 2, 3]}
        }
    }
}
```

### Advanced Caching Strategies

```python
# Predictive caching
smart_cache = PredictiveCache(
    cache_strategy=CacheStrategy.LRU,
    max_memory=200 * 1024 * 1024  # 200MB
)

# Warm-up cache with popular predictions
smart_cache.warm_up(
    popular_symbols=['AAPL', 'GOOGL', 'MSFT'],
    sample_features=[
        {'open': 150, 'high': 155, 'low': 149, 'close': 153},
        {'open': 100, 'high': 105, 'low': 99, 'close': 103}
    ]
)
```

## 🐛 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis service
   redis-cli ping
   
   # Start Redis if not running
   sudo systemctl start redis
   ```

2. **Abacus.AI API Authentication**
   ```bash
   # Verify API key
   export ABACUS_AI_API_KEY=your-key
   python -c "from code.abacus_ai.utils.helpers import validate_environment; print(validate_environment())"
   ```

3. **Missing Dependencies**
   ```bash
   # Install all requirements
   pip install -r requirements.txt
   
   # For TA-Lib (Ubuntu/Debian)
   sudo apt-get install ta-lib-dev
   pip install TA-Lib
   ```

### Debug Mode

```python
import logging
logging.getLogger('code.abacus_ai').setLevel(logging.DEBUG)

# Enable detailed logging
from code.abacus_ai.utils.helpers import setup_logging
setup_logging('DEBUG', 'logs/debug.log')
```

## 📚 API Reference

### AbacusAIClient

```python
client = AbacusAIClient(api_key, base_url)

# Feature groups
feature_group = client.create_feature_group(name, description, schema)
feature_groups = client.list_feature_groups()
feature_group = client.get_feature_group(feature_group_id)

# Data upload
result = client.upload_data(feature_group_id, data, operation="UPSERT")

# Schema validation
validation = client.validate_schema(data, schema)
```

### ModelTrainer

```python
trainer = ModelTrainer(client, config)

# Training
results = trainer.train_models(data)
trainer.save_model('model.pkl')

# Predictions
predictions = trainer.predict(features)
importance = trainer.get_feature_importance()
```

### PredictionCache

```python
cache = PredictionCache(redis_config, strategy, max_memory)

# Operations
result, is_cached = cache.get(symbol, features)
cache.set(symbol, features, result, ttl=300)

# Management
cache.invalidate(symbol)
stats = cache.get_stats()
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@abacus-ai.com
- 📖 Documentation: https://docs.abacus-ai.com
- 🐛 Issues: https://github.com/abacus-ai/integration/issues

---

Built with ❤️ by the Abacus.AI team