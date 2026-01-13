"""
Example Usage Script for Abacus.AI Integration
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.helpers import load_config, setup_logging, validate_environment
from client.abacus_client import AbacusAIClient
from features.feature_engineering import FeatureEngineeringPipeline
from training.model_trainer import ModelTrainer, ModelEvaluator
from api.prediction_api import AbacusAIPredictor, PredictionCache
from api.prediction_api import PredictionRequest
from deployment.deploy import ModelDeployer, TokenManager


async def main():
    """Main example function demonstrating full Abacus.AI integration"""
    
    # 1. Setup and Configuration
    print("🚀 Starting Abacus.AI Integration Example")
    print("=" * 50)
    
    # Setup logging
    setup_logging('INFO', 'logs/example.log')
    
    # Validate environment
    env_status = validate_environment()
    if not env_status['valid']:
        print(f"❌ Environment validation failed: {env_status['errors']}")
        return
    
    print("✅ Environment validation passed")
    
    # Load configuration
    config_path = 'config/config.yaml'
    if not os.path.exists(config_path):
        print(f"⚠️  Configuration file not found at {config_path}")
        print("Creating sample configuration...")
        from utils.helpers import create_sample_config
        create_sample_config(config_path)
    
    config = load_config(config_path)
    print("✅ Configuration loaded")
    
    # 2. Initialize Components
    print("\n📡 Initializing Abacus.AI components...")
    
    # Initialize Abacus.AI client
    api_key = os.getenv('ABACUS_AI_API_KEY')
    if not api_key:
        print("❌ ABACUS_AI_API_KEY not found in environment")
        return
    
    abacus_client = AbacusAIClient(api_key, config['abacus_ai']['base_url'])
    print("✅ Abacus.AI client initialized")
    
    # Initialize feature engineering pipeline
    feature_pipeline = FeatureEngineeringPipeline()
    print("✅ Feature engineering pipeline initialized")
    
    # Initialize model trainer
    trainer = ModelTrainer(abacus_client, config['model'])
    print("✅ Model trainer initialized")
    
    # Initialize cache
    cache = PredictionCache(
        redis_config=config['redis'],
        cache_strategy=config['cache']['strategy'],
        max_memory=config['cache']['max_memory']
    )
    print("✅ Cache initialized")
    
    # 3. Feature Engineering Example
    print("\n🔧 Creating features for market data...")
    
    try:
        # Create sample market data
        import pandas as pd
        import numpy as np
        
        # Generate sample data for demonstration
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN']
        
        all_data = []
        for symbol in symbols:
            # Generate realistic price data
            np.random.seed(hash(symbol) % 2**32)  # Consistent seed per symbol
            base_price = 100 + np.random.randn() * 50
            
            price_changes = np.random.randn(len(dates)) * 0.02
            prices = [base_price]
            
            for change in price_changes:
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 0.1))  # Ensure positive prices
            
            symbol_data = pd.DataFrame({
                'date': dates,
                'symbol': symbol,
                'open': prices[:-1],
                'high': [p * (1 + abs(np.random.randn()) * 0.01) for p in prices[:-1]],
                'low': [p * (1 - abs(np.random.randn()) * 0.01) for p in prices[:-1]],
                'close': prices[1:],
                'volume': np.random.randint(100000, 10000000, len(dates))
            })
            
            all_data.append(symbol_data)
        
        combined_data = pd.concat(all_data, ignore_index=True)
        print(f"📊 Generated sample data: {combined_data.shape}")
        
        # Create features
        features = feature_pipeline.create_features(
            combined_data,
            symbols=symbols,
            include_sentiment=True
        )
        
        print(f"✅ Created {features.shape[1]} features for {features.shape[0]} samples")
        
        # Add target variable
        features = feature_pipeline.add_target_variable(
            features,
            periods_ahead=1
        )
        
        # Remove rows with NaN targets
        features = features.dropna(subset=['future_return'])
        print(f"📈 Final dataset shape: {features.shape}")
        
    except Exception as e:
        print(f"❌ Feature engineering failed: {str(e)}")
        return
    
    # 4. Model Training Example
    print("\n🤖 Training machine learning models...")
    
    try:
        # Train models
        training_results = trainer.train_models(features, validation_split=True)
        
        # Generate evaluation report
        evaluator = ModelEvaluator(trainer)
        report = evaluator.generate_report(training_results)
        
        # Save report
        from utils.helpers import save_data_quality_report
        report_path = 'reports/training_report.json'
        evaluator.save_report(report, report_path)
        print(f"📋 Training report saved to {report_path}")
        
        # Save best model
        model_path = 'models/trained/best_model.pkl'
        os.makedirs('models/trained', exist_ok=True)
        trainer.save_model(model_path)
        print(f"💾 Best model saved to {model_path}")
        
        # Display results
        from utils.helpers import format_model_comparison
        print("\n📊 Model Comparison:")
        print(format_model_comparison(training_results))
        
    except Exception as e:
        print(f"❌ Model training failed: {str(e)}")
        return
    
    # 5. Prediction API Example
    print("\n🔮 Testing prediction API...")
    
    try:
        # Initialize predictor
        predictor = AbacusAIPredictor(abacus_client, trainer, cache)
        
        # Create sample prediction request
        sample_features = {
            'open': 150.0,
            'high': 155.0,
            'low': 149.0,
            'close': 153.0,
            'volume': 1000000,
            'rsi': 65.0,
            'macd': 0.5,
            'bb_position': 0.7
        }
        
        prediction_request = PredictionRequest(
            symbol='AAPL',
            features=sample_features,
            timestamp=datetime.utcnow()
        )
        
        # Make prediction
        prediction_response = await predictor._make_prediction(prediction_request)
        
        print(f"✅ Prediction successful!")
        print(f"📈 Symbol: {prediction_response.symbol}")
        print(f"🎯 Prediction: {prediction_response.prediction:.6f}")
        print(f"📊 Confidence: {prediction_response.confidence:.2%}")
        print(f"⏱️  Processing time: {prediction_response.processing_time:.3f}s")
        print(f"💾 Cached: {prediction_response.cached}")
        
        if prediction_response.error:
            print(f"⚠️  Warning: {prediction_response.error}")
        
    except Exception as e:
        print(f"❌ Prediction failed: {str(e)}")
    
    # 6. Cache Management Example
    print("\n💾 Testing cache management...")
    
    try:
        # Get cache statistics
        cache_stats = cache.get_stats()
        print(f"📊 Cache Statistics:")
        print(f"   Hit Rate: {cache_stats['hit_rate']:.2%}")
        print(f"   Total Requests: {cache_stats['total_requests']}")
        print(f"   Memory Usage: {cache_stats['memory_usage_percent']:.1f}%")
        print(f"   Local Cache Size: {cache_stats['local_cache_size']}")
        
        # Test cache operations
        test_symbol = 'TEST'
        test_features = {'close': 100, 'volume': 1000000}
        test_result = {'prediction': 0.05, 'confidence': 0.8}
        
        # Set cache
        cache.set(test_symbol, test_features, test_result)
        print(f"✅ Cache set for {test_symbol}")
        
        # Get cache
        retrieved, is_cached = cache.get(test_symbol, test_features)
        print(f"✅ Cache get for {test_symbol}: {'HIT' if is_cached else 'MISS'}")
        
        # Clear test data
        cache.invalidate(test_symbol)
        print(f"🧹 Cache cleared for {test_symbol}")
        
    except Exception as e:
        print(f"❌ Cache management failed: {str(e)}")
    
    # 7. Deployment Example
    print("\n🚀 Testing deployment preparation...")
    
    try:
        # Initialize token manager
        token_manager = TokenManager()
        
        # Test API key retrieval (without actual deployment)
        try:
            test_api_key = token_manager.get_api_key('test')
            print("✅ Token management working")
        except Exception:
            print("⚠️  Token retrieval failed (expected if not configured)")
        
        print("📝 Deployment configuration prepared")
        print("   To deploy model, run:")
        print("   python deployment/deploy.py --model-path models/trained/best_model.pkl --config config/config.yaml --environment production")
        
    except Exception as e:
        print(f"❌ Deployment preparation failed: {str(e)}")
    
    # 8. Summary and Next Steps
    print("\n🎉 Abacus.AI Integration Example Completed!")
    print("=" * 50)
    
    print("\n📁 Generated Files:")
    print("   ├── config/config.yaml (configuration)")
    print("   ├── logs/example.log (logs)")
    print("   ├── reports/training_report.json (training report)")
    print("   └── models/trained/best_model.pkl (trained model)")
    
    print("\n🚀 Next Steps:")
    print("   1. Review the generated model and configuration")
    print("   2. Deploy the model using the deployment script")
    print("   3. Start the FastAPI server for real-time predictions")
    print("   4. Monitor performance using the caching and metrics")
    
    print("\n📚 Documentation:")
    print("   • Full documentation: docs/README.md")
    print("   • API reference: Use help() function on classes")
    print("   • Configuration: config/config.yaml")
    
    print("\n🔗 API Endpoints (when server is running):")
    print("   • GET /health - Health check")
    print("   • POST /predict - Make predictions")
    print("   • POST /batch_predict - Batch predictions")
    print("   • DELETE /cache - Clear cache")


def demo_cache_strategies():
    """Demonstrate different cache strategies"""
    print("\n🔧 Cache Strategy Comparison")
    print("=" * 30)
    
    from cache.prediction_cache import CacheStrategy
    
    strategies = [
        CacheStrategy.LRU,
        CacheStrategy.LFU,
        CacheStrategy.FIFO,
        CacheStrategy.TTL
    ]
    
    for strategy in strategies:
        print(f"Testing {strategy.value} strategy...")
        try:
            cache = PredictionCache(
                cache_strategy=strategy,
                max_memory=1024 * 1024,  # 1MB for demo
                default_ttl=60
            )
            
            # Simulate some cache operations
            for i in range(10):
                cache.set(f"symbol_{i}", {'price': 100 + i}, {'prediction': i * 0.01})
            
            stats = cache.get_stats()
            print(f"  ✅ {strategy.value}: Hit Rate {stats['hit_rate']:.2%}, Entries: {stats['local_cache_size']}")
            
        except Exception as e:
            print(f"  ❌ {strategy.value} failed: {str(e)}")


def demo_feature_engineering():
    """Demonstrate feature engineering capabilities"""
    print("\n🔧 Feature Engineering Demo")
    print("=" * 30)
    
    from features.feature_engineering import TechnicalIndicators
    
    # Create sample data
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    close_prices = 100 + np.cumsum(np.random.randn(100) * 0.02)
    high_prices = close_prices * (1 + np.abs(np.random.randn(100)) * 0.01)
    low_prices = close_prices * (1 - np.abs(np.random.randn(100)) * 0.01)
    volume = np.random.randint(100000, 1000000, 100)
    
    data = pd.DataFrame({
        'date': dates,
        'close': close_prices,
        'high': high_prices,
        'low': low_prices,
        'volume': volume
    })
    
    # Calculate technical indicators
    indicators = TechnicalIndicators()
    
    rsi = indicators.calculate_rsi(data['close'])
    macd = indicators.calculate_macd(data['close'])
    bb = indicators.calculate_bollinger_bands(data['close'])
    
    print(f"✅ Calculated technical indicators:")
    print(f"   • RSI (last 5): {rsi[-5:].values}")
    print(f"   • MACD (last 5): {macd['macd'][-5:].values}")
    print(f"   • Bollinger Bands width (last 5): {bb['bb_width'][-5:].values}")
    
    # Feature statistics
    print(f"\n📊 Feature Statistics:")
    print(f"   • RSI range: {rsi.min():.2f} - {rsi.max():.2f}")
    print(f"   • MACD range: {macd['macd'].min():.4f} - {macd['macd'].max():.4f}")
    print(f"   • BB width range: {bb['bb_width'].min():.4f} - {bb['bb_width'].max():.4f}")


if __name__ == "__main__":
    print("Abacus.AI Integration - Example Script")
    print("=====================================")
    
    # Run main example
    asyncio.run(main())
    
    # Run additional demos
    demo_cache_strategies()
    demo_feature_engineering()
    
    print("\n✅ All demonstrations completed successfully!")
    print("Check the generated files and logs for detailed information.")