"""
Basic tests for Abacus.AI integration
"""

import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
import tempfile
import os


class TestAbacusAIClient(unittest.TestCase):
    """Test Abacus.AI client functionality"""
    
    def setUp(self):
        self.api_key = "test-api-key"
        self.client = Mock()
        self.client.api_key = self.api_key
        self.client.base_url = "https://api.abacus.ai"
    
    def test_client_initialization(self):
        """Test client initialization"""
        from client.abacus_client import AbacusAIClient
        
        # Test with mock client
        client = AbacusAIClient(self.api_key)
        self.assertEqual(client.api_key, self.api_key)
        self.assertEqual(client.base_url, "https://api.abacus.ai")
    
    @patch('requests.Session')
    def test_make_request(self, mock_session):
        """Test API request functionality"""
        # This would test the actual HTTP request logic
        pass
    
    def test_feature_group_schema_validation(self):
        """Test feature group schema validation"""
        from client.abacus_client import AbacusAIClient
        
        # Create test data
        test_data = pd.DataFrame({
            'symbol': ['AAPL', 'GOOGL'],
            'price': [150.0, 2800.0],
            'volume': [1000000, 500000]
        })
        
        test_schema = [
            {"name": "symbol", "type": "string"},
            {"name": "price", "type": "float"},
            {"name": "volume", "type": "integer"}
        ]
        
        client = AbacusAIClient(self.api_key)
        result = client.validate_schema(test_data, test_schema)
        
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['issues']), 0)


class TestFeatureEngineering(unittest.TestCase):
    """Test feature engineering functionality"""
    
    def setUp(self):
        # Create sample data
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        self.sample_data = pd.DataFrame({
            'date': dates,
            'symbol': 'TEST',
            'open': np.random.randn(50).cumsum() + 100,
            'high': np.random.randn(50).cumsum() + 105,
            'low': np.random.randn(50).cumsum() + 95,
            'close': np.random.randn(50).cumsum() + 102,
            'volume': np.random.randint(100000, 1000000, 50)
        })
    
    def test_technical_indicators(self):
        """Test technical indicator calculations"""
        from features.feature_engineering import TechnicalIndicators
        
        indicators = TechnicalIndicators()
        
        # Test RSI
        rsi = indicators.calculate_rsi(self.sample_data['close'])
        self.assertEqual(len(rsi), len(self.sample_data))
        self.assertTrue(all(0 <= val <= 100 for val in rsi[~np.isnan(rsi)]))
        
        # Test MACD
        macd = indicators.calculate_macd(self.sample_data['close'])
        self.assertIn('macd', macd)
        self.assertIn('macd_signal', macd)
        self.assertIn('macd_histogram', macd)
    
    def test_feature_pipeline(self):
        """Test feature engineering pipeline"""
        from features.feature_engineering import FeatureEngineeringPipeline
        
        pipeline = FeatureEngineeringPipeline()
        features = pipeline.create_features(self.sample_data, symbols=['TEST'])
        
        self.assertIsInstance(features, pd.DataFrame)
        self.assertGreater(features.shape[1], self.sample_data.shape[1])  # More features than input
        
        # Check for expected feature types
        expected_features = ['rsi', 'macd', 'bb_upper', 'bb_lower']
        for feature in expected_features:
            if feature in features.columns:
                self.assertFalse(features[feature].isna().all())


class TestModelTraining(unittest.TestCase):
    """Test model training functionality"""
    
    def setUp(self):
        # Create sample feature data
        np.random.seed(42)
        n_samples = 100
        n_features = 10
        
        self.sample_features = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        self.sample_target = pd.Series(
            np.random.randn(n_samples),
            name='future_return'
        )
        
        # Combine features and target
        self.training_data = pd.concat([self.sample_features, self.sample_target], axis=1)
    
    @patch('training.model_trainer.ModelTrainer._get_model')
    def test_model_training(self, mock_get_model):
        """Test model training process"""
        from training.model_trainer import ModelTrainer
        from client.abacus_client import AbacusAIClient
        
        # Mock client
        mock_client = Mock()
        mock_client.api_key = "test-key"
        
        # Configure trainer
        config = {
            'test_size': 0.2,
            'random_state': 42,
            'cv_folds': 3,
            'models': {
                'test_model': {
                    'algorithm': 'linear_regression',
                    'params': {}
                }
            },
            'target_column': 'future_return'
        }
        
        trainer = ModelTrainer(mock_client, config)
        results = trainer.train_models(self.training_data)
        
        self.assertIsInstance(results, dict)
        self.assertIn('test_model', results)
        
        # Check that model was trained
        result = results['test_model']
        self.assertIn('train_metrics', result)
        self.assertIn('test_metrics', result)


class TestPredictionCache(unittest.TestCase):
    """Test prediction caching functionality"""
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        from cache.prediction_cache import PredictionCache
        
        cache = PredictionCache()
        
        symbol = "AAPL"
        features = {"price": 150, "volume": 1000000}
        
        key1 = cache._generate_cache_key(symbol, features)
        key2 = cache._generate_cache_key(symbol, features)
        
        # Same inputs should generate same key
        self.assertEqual(key1, key2)
        
        # Different features should generate different keys
        features_diff = {"price": 151, "volume": 1000000}
        key3 = cache._generate_cache_key(symbol, features_diff)
        
        self.assertNotEqual(key1, key3)
    
    def test_memory_estimation(self):
        """Test memory usage estimation"""
        from cache.prediction_cache import PredictionCache
        
        cache = PredictionCache()
        
        key = "test_key"
        value = {"prediction": 0.05, "confidence": 0.8}
        
        # This should not raise an exception
        memory_estimate = cache._estimate_memory_usage(key, value)
        self.assertGreater(memory_estimate, 0)


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_config_loading(self):
        """Test configuration loading"""
        from utils.helpers import load_config, save_config
        import tempfile
        
        test_config = {
            'abacus_ai': {
                'api_key': 'test-key',
                'base_url': 'https://api.test.com'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379
            }
        }
        
        # Test saving and loading
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            save_config(test_config, f.name)
            
            loaded_config = load_config(f.name)
            self.assertEqual(loaded_config, test_config)
            
            os.unlink(f.name)
    
    def test_environment_validation(self):
        """Test environment validation"""
        from utils.helpers import validate_environment
        
        # This should not raise an exception
        status = validate_environment()
        
        self.assertIn('timestamp', status)
        self.assertIn('checks', status)
        self.assertIn('valid', status)
        self.assertIsInstance(status['valid'], bool)
    
    def test_data_quality_validation(self):
        """Test data quality validation"""
        from utils.helpers import validate_data_quality
        
        # Create test data
        test_data = pd.DataFrame({
            'feature1': [1, 2, 3, None, 5],
            'feature2': ['a', 'b', 'c', 'd', 'e'],
            'target': [0.1, 0.2, 0.3, 0.4, 0.5]
        })
        
        report = validate_data_quality(test_data, 'target')
        
        self.assertIn('missing_values', report)
        self.assertIn('target_column_stats', report)
        self.assertEqual(report['missing_values']['feature1']['count'], 1)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)