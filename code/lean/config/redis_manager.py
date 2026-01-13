"""
Redis Communication Module for Abacus.AI and QuantConnect LEAN Integration
Handles real-time prediction streaming and communication
"""

import redis
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional
import logging
from dataclasses import dataclass, asdict


@dataclass
class PredictionMessage:
    """Structure for prediction messages"""
    symbol: str
    timestamp: str
    current_price: float
    prediction_1d: Dict[str, Any]
    prediction_5d: Dict[str, Any]
    prediction_30d: Dict[str, Any]
    confidence: float
    direction: str
    volatility_prediction: float
    sentiment_score: float
    features: Dict[str, float]
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PredictionMessage':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls(**data)


class AbacusRedisManager:
    """Manager for Redis-based communication with Abacus.AI"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0, **kwargs):
        """
        Initialize Redis connection and communication manager
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            **kwargs: Additional Redis client parameters
        """
        self.host = host
        self.port = port
        self.db = db
        self.redis_client = None
        self.is_connected = False
        self.subscribers = []
        self.running = False
        
        # Initialize connection
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                **kwargs
            )
            
            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            
            logging.info(f"Redis connection established: {self.host}:{self.port}")
            
        except Exception as e:
            self.is_connected = False
            logging.error(f"Redis connection failed: {e}")
            raise
    
    def publish_prediction(self, prediction: PredictionMessage) -> bool:
        """
        Publish prediction message to Redis
        
        Args:
            prediction: Prediction message to publish
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            logging.error("Redis not connected")
            return False
        
        try:
            channel = f"predictions:{prediction.symbol}"
            message = prediction.to_json()
            
            result = self.redis_client.publish(channel, message)
            
            # Also store in prediction history
            self._store_prediction_history(prediction)
            
            logging.debug(f"Published prediction for {prediction.symbol} to {channel}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to publish prediction: {e}")
            return False
    
    def _store_prediction_history(self, prediction: PredictionMessage):
        """Store prediction in history list"""
        try:
            history_key = f"history:{prediction.symbol}"
            timestamp = prediction.timestamp
            
            # Store in a time-series list with max 1000 entries
            pipeline = self.redis_client.pipeline()
            
            # Add new prediction
            pipeline.lpush(history_key, prediction.to_json())
            pipeline.ltrim(history_key, 0, 999)  # Keep only last 1000 entries
            pipeline.expire(history_key, 86400 * 7)  # Expire after 7 days
            
            pipeline.execute()
            
        except Exception as e:
            logging.error(f"Failed to store prediction history: {e}")
    
    def subscribe_to_predictions(self, symbols: list, callback: Callable[[PredictionMessage], None]) -> bool:
        """
        Subscribe to prediction updates for specific symbols
        
        Args:
            symbols: List of symbols to subscribe to
            callback: Function to call when prediction is received
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            logging.error("Redis not connected")
            return False
        
        try:
            # Create subscriber
            subscriber = self.redis_client.pubsub()
            
            # Subscribe to prediction channels
            for symbol in symbols:
                channel = f"predictions:{symbol}"
                subscriber.subscribe(channel)
                logging.info(f"Subscribed to channel: {channel}")
            
            # Store subscriber info
            self.subscribers.append({
                'subscriber': subscriber,
                'symbols': symbols,
                'callback': callback,
                'thread': None
            })
            
            # Start listening thread
            self._start_subscriber_thread(subscriber, callback)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to subscribe to predictions: {e}")
            return False
    
    def _start_subscriber_thread(self, subscriber, callback: Callable):
        """Start background thread for handling subscriber messages"""
        def listener():
            while self.running:
                try:
                    message = subscriber.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        prediction = PredictionMessage.from_json(message['data'])
                        callback(prediction)
                except Exception as e:
                    logging.error(f"Subscriber message handling error: {e}")
                    time.sleep(0.1)
        
        thread = threading.Thread(target=listener, daemon=True)
        thread.start()
        
        # Store thread reference
        for sub_info in self.subscribers:
            if sub_info['subscriber'] == subscriber:
                sub_info['thread'] = thread
                break
    
    def get_latest_prediction(self, symbol: str) -> Optional[PredictionMessage]:
        """
        Get the latest prediction for a symbol
        
        Args:
            symbol: Symbol to get prediction for
            
        Returns:
            Latest prediction or None if not found
        """
        if not self.is_connected:
            return None
        
        try:
            # Try to get from real-time cache first
            cache_key = f"prediction_cache:{symbol}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                return PredictionMessage.from_json(cached_data)
            
            # Fallback to history
            history_key = f"history:{symbol}"
            latest_data = self.redis_client.lindex(history_key, 0)
            
            if latest_data:
                return PredictionMessage.from_json(latest_data)
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to get latest prediction for {symbol}: {e}")
            return None
    
    def get_prediction_history(self, symbol: str, limit: int = 100) -> list:
        """
        Get prediction history for a symbol
        
        Args:
            symbol: Symbol to get history for
            limit: Maximum number of predictions to return
            
        Returns:
            List of prediction messages
        """
        if not self.is_connected:
            return []
        
        try:
            history_key = f"history:{symbol}"
            history_data = self.redis_client.lrange(history_key, 0, limit - 1)
            
            predictions = []
            for data in history_data:
                try:
                    prediction = PredictionMessage.from_json(data)
                    predictions.append(prediction)
                except Exception as e:
                    logging.error(f"Failed to parse prediction data: {e}")
            
            return predictions
            
        except Exception as e:
            logging.error(f"Failed to get prediction history for {symbol}: {e}")
            return []
    
    def cache_prediction(self, symbol: str, prediction: PredictionMessage, ttl: int = 3600):
        """
        Cache a prediction with TTL
        
        Args:
            symbol: Symbol to cache prediction for
            prediction: Prediction data to cache
            ttl: Time to live in seconds
        """
        if not self.is_connected:
            return
        
        try:
            cache_key = f"prediction_cache:{symbol}"
            self.redis_client.setex(
                cache_key,
                ttl,
                prediction.to_json()
            )
        except Exception as e:
            logging.error(f"Failed to cache prediction: {e}")
    
    def get_symbol_metrics(self, symbol: str) -> Dict[str, Any]:
        """
        Get trading metrics for a symbol
        
        Args:
            symbol: Symbol to get metrics for
            
        Returns:
            Dictionary with metrics data
        """
        if not self.is_connected:
            return {}
        
        try:
            metrics_key = f"metrics:{symbol}"
            metrics_data = self.redis_client.get(metrics_key)
            
            if metrics_data:
                return json.loads(metrics_data)
            
            return {
                'symbol': symbol,
                'last_prediction_time': None,
                'prediction_count': 0,
                'avg_confidence': 0.0,
                'direction_accuracy': 0.0,
                'sentiment_trend': 'neutral'
            }
            
        except Exception as e:
            logging.error(f"Failed to get metrics for {symbol}: {e}")
            return {}
    
    def update_symbol_metrics(self, symbol: str, metrics: Dict[str, Any]):
        """
        Update trading metrics for a symbol
        
        Args:
            symbol: Symbol to update metrics for
            metrics: Metrics data to update
        """
        if not self.is_connected:
            return
        
        try:
            metrics_key = f"metrics:{symbol}"
            self.redis_client.setex(
                metrics_key,
                86400,  # 24 hour TTL
                json.dumps(metrics)
            )
        except Exception as e:
            logging.error(f"Failed to update metrics for {symbol}: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Redis connection
        
        Returns:
            Dictionary with health status
        """
        try:
            if not self.is_connected:
                return {'status': 'disconnected', 'error': 'No Redis connection'}
            
            # Test basic operations
            test_key = f"health_check:{int(time.time())}"
            self.redis_client.setex(test_key, 60, "OK")
            result = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            if result == "OK":
                return {
                    'status': 'healthy',
                    'connected': True,
                    'host': self.host,
                    'port': self.port,
                    'db': self.db,
                    'subscriber_count': len(self.subscribers)
                }
            else:
                return {'status': 'unhealthy', 'connected': False, 'error': 'Basic operation failed'}
                
        except Exception as e:
            return {'status': 'error', 'connected': False, 'error': str(e)}
    
    def cleanup(self):
        """Cleanup resources and close connections"""
        self.running = False
        
        try:
            # Unsubscribe from all channels
            for sub_info in self.subscribers:
                sub_info['subscriber'].unsubscribe()
                sub_info['subscriber'].close()
            
            # Close Redis connection
            if self.redis_client:
                self.redis_client.close()
            
            logging.info("Redis manager cleanup completed")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


# Singleton instance
_global_redis_manager = None

def get_redis_manager(**kwargs) -> AbacusRedisManager:
    """Get or create global Redis manager instance"""
    global _global_redis_manager
    if _global_redis_manager is None:
        _global_redis_manager = AbacusRedisManager(**kwargs)
    return _global_redis_manager