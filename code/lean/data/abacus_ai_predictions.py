"""
Abacus.AI ML Predictions Data Source for QuantConnect LEAN
Implements custom PythonData class to ingest machine learning predictions
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import redis
import json
from QuantumLeap.QuantConnect.PythonData import PythonData


class AbacusAIPredictionsData(PythonData):
    """Custom PythonData class for Abacus.AI ML predictions"""
    
    def __init__(self, symbol, algorithm, redis_host='localhost', redis_port=6379):
        """
        Initialize Abacus.AI predictions data source
        
        Args:
            symbol: Symbol to get predictions for
            algorithm: Reference to the main algorithm
            redis_host: Redis server host
            redis_port: Redis server port
        """
        super().__init__()
        self.symbol = symbol
        self.algorithm = algorithm
        
        # Redis connection for real-time predictions
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            self.redis_available = True
        except Exception as e:
            self.algorithm.Debug(f"Redis connection failed: {e}")
            self.redis_available = False
            
        # Prediction cache
        self.predictions_cache = {}
        self.last_update = {}
        
    @property
    def should_cache_predictions(self) -> bool:
        """Check if predictions should be cached to ObjectStore"""
        try:
            return hasattr(self.algorithm, 'object_store') and self.algorithm.object_store is not None
        except:
            return False
            
    def get_predictions(self, symbol: str, as_of_date: datetime, symbol_name: str = '') -> Optional[Dict[str, Any]]:
        """
        Get ML predictions for a symbol as of a specific date
        
        Args:
            symbol: Security symbol
            as_of_date: Date to get predictions for
            symbol_name: Optional symbol name
            
        Returns:
            Dictionary containing prediction data or None if not available
        """
        try:
            # Check cache first
            cache_key = f"{symbol}_{as_of_date.strftime('%Y%m%d_%H%M')}"
            if cache_key in self.predictions_cache:
                return self.predictions_cache[cache_key]
            
            # Try to get from ObjectStore cache
            if self.should_cache_predictions:
                cached_prediction = self._get_cached_prediction(symbol, as_of_date)
                if cached_prediction:
                    return cached_prediction
            
            # Get fresh predictions from Abacus.AI
            predictions = self._fetch_abacus_predictions(symbol, as_of_date)
            
            if predictions:
                # Cache the prediction
                self._cache_prediction(symbol, as_of_date, predictions)
                return predictions
                
            return None
            
        except Exception as e:
            self.algorithm.Debug(f"Error getting predictions for {symbol}: {e}")
            return None
    
    def _fetch_abacus_predictions(self, symbol: str, as_of_date: datetime) -> Optional[Dict[str, Any]]:
        """Fetch predictions from Abacus.AI via Redis or API"""
        
        # Try Redis first for real-time predictions
        if self.redis_available:
            try:
                redis_key = f"predictions:{symbol}:{as_of_date.strftime('%Y-%m-%d')}"
                redis_data = self.redis_client.get(redis_key)
                
                if redis_data:
                    prediction_data = json.loads(redis_data)
                    
                    # Validate prediction data structure
                    if self._validate_prediction_data(prediction_data):
                        return prediction_data
                        
            except Exception as e:
                self.algorithm.Debug(f"Redis prediction fetch failed: {e}")
        
        # Fallback to API call (implement based on Abacus.AI API)
        try:
            # This would be replaced with actual Abacus.AI API call
            return self._fetch_from_api(symbol, as_of_date)
            
        except Exception as e:
            self.algorithm.Debug(f"API prediction fetch failed: {e}")
            return None
    
    def _fetch_from_api(self, symbol: str, as_of_date: datetime) -> Optional[Dict[str, Any]]:
        """Fetch predictions from Abacus.AI API (placeholder implementation)"""
        
        # This is a placeholder - implement actual API integration
        # For now, generate synthetic data for demonstration
        
        base_price = 100.0 + np.random.normal(0, 5)
        
        predictions = {
            'symbol': symbol,
            'timestamp': as_of_date.isoformat(),
            'current_price': base_price,
            'prediction_1d': {
                'price': base_price * (1 + np.random.normal(0, 0.02)),
                'confidence': np.random.uniform(0.6, 0.95),
                'direction': 'up' if np.random.random() > 0.5 else 'down'
            },
            'prediction_5d': {
                'price': base_price * (1 + np.random.normal(0, 0.05)),
                'confidence': np.random.uniform(0.5, 0.85),
                'direction': 'up' if np.random.random() > 0.5 else 'down'
            },
            'prediction_30d': {
                'price': base_price * (1 + np.random.normal(0, 0.15)),
                'confidence': np.random.uniform(0.4, 0.75),
                'direction': 'up' if np.random.random() > 0.5 else 'down'
            },
            'volatility_prediction': np.random.uniform(0.15, 0.45),
            'sentiment_score': np.random.uniform(-1, 1),
            'features': {
                'momentum': np.random.normal(0, 1),
                'mean_reversion': np.random.normal(0, 1),
                'trend_strength': np.random.uniform(0, 1),
                'volume_anomaly': np.random.uniform(0, 1)
            }
        }
        
        return predictions
    
    def _validate_prediction_data(self, data: Dict[str, Any]) -> bool:
        """Validate prediction data structure"""
        required_fields = ['symbol', 'prediction_1d', 'confidence', 'direction']
        return all(field in data for field in required_fields)
    
    def _cache_prediction(self, symbol: str, as_of_date: datetime, prediction_data: Dict[str, Any]):
        """Cache prediction data in memory"""
        cache_key = f"{symbol}_{as_of_date.strftime('%Y%m%d_%H%M')}"
        self.predictions_cache[cache_key] = prediction_data
        
        # Cache to ObjectStore if available
        if self.should_cache_predictions:
            self._cache_to_object_store(symbol, as_of_date, prediction_data)
        
        # Limit cache size
        if len(self.predictions_cache) > 100:
            oldest_key = min(self.predictions_cache.keys())
            del self.predictions_cache[oldest_key]
    
    def _cache_to_object_store(self, symbol: str, as_of_date: datetime, prediction_data: Dict[str, Any]):
        """Cache prediction data to ObjectStore"""
        try:
            cache_key = f"abacus_predictions:{symbol}:{as_of_date.strftime('%Y%m%d')}"
            self.algorithm.object_store.SaveJson(cache_key, prediction_data)
        except Exception as e:
            self.algorithm.Debug(f"ObjectStore caching failed: {e}")
    
    def _get_cached_prediction(self, symbol: str, as_of_date: datetime) -> Optional[Dict[str, Any]]:
        """Get cached prediction from ObjectStore"""
        try:
            cache_key = f"abacus_predictions:{symbol}:{as_of_date.strftime('%Y%m%d')}"
            cached_data = self.algorithm.object_store.ReadJson(cache_key)
            return cached_data
        except:
            return None
    
    def get_recent_predictions(self, symbol: str, days: int = 7) -> pd.DataFrame:
        """
        Get recent prediction history for backtesting
        
        Args:
            symbol: Security symbol
            days: Number of days of history to retrieve
            
        Returns:
            DataFrame with prediction history
        """
        try:
            # Try to get from ObjectStore history
            return self._get_prediction_history_from_objectstore(symbol, days)
        except Exception as e:
            self.algorithm.Debug(f"Error getting prediction history: {e}")
            return pd.DataFrame()
    
    def _get_prediction_history_from_objectstore(self, symbol: str, days: int) -> pd.DataFrame:
        """Retrieve prediction history from ObjectStore"""
        try:
            history_data = []
            
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                cache_key = f"abacus_predictions:{symbol}:{date.strftime('%Y%m%d')}"
                
                try:
                    prediction = self.algorithm.object_store.ReadJson(cache_key)
                    if prediction:
                        history_data.append(prediction)
                except:
                    continue
            
            if history_data:
                return pd.DataFrame(history_data)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            self.algorithm.Debug(f"ObjectStore history retrieval failed: {e}")
            return pd.DataFrame()
    
    def clean_cache(self):
        """Clean old prediction cache entries"""
        try:
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # Clean memory cache
            keys_to_remove = []
            for key, value in self.predictions_cache.items():
                try:
                    timestamp = datetime.strptime(key.split('_')[-1], '%Y%m%d_%H%M')
                    if timestamp < cutoff_date:
                        keys_to_remove.append(key)
                except:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.predictions_cache[key]
                
            self.algorithm.Debug(f"Cleaned {len(keys_to_remove)} old cache entries")
            
        except Exception as e:
            self.algorithm.Debug(f"Cache cleanup failed: {e}")


# Global instance for easy access
_global_abacus_data = None

def get_abacus_data_instance(symbol: str, algorithm, **kwargs) -> AbacusAIPredictionsData:
    """Get or create global Abacus.AI data instance"""
    global _global_abacus_data
    if _global_abacus_data is None or _global_abacus_data.symbol != symbol:
        _global_abacus_data = AbacusAIPredictionsData(symbol, algorithm, **kwargs)
    return _global_abacus_data