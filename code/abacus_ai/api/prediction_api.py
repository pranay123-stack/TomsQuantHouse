"""
Real-time Prediction API Integration with Error Handling and Retry Logic
"""

import logging
import time
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import redis
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionStatus(Enum):
    """Prediction status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class PredictionRequest:
    """Prediction request data structure"""
    symbol: str
    features: Dict[str, Any]
    timestamp: datetime
    request_id: str = None
    
    def __post_init__(self):
        if self.request_id is None:
            self.request_id = f"{self.symbol}_{int(time.time())}"


@dataclass
class PredictionResponse:
    """Prediction response data structure"""
    request_id: str
    symbol: str
    prediction: float
    confidence: float
    status: PredictionStatus
    timestamp: datetime
    processing_time: float
    cached: bool = False
    error: Optional[str] = None


class PredictionCache:
    """Redis-based prediction caching layer"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, 
                 redis_db: int = 0, ttl: int = 300):
        """
        Initialize Redis cache
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            redis_db: Redis database number
            ttl: Time to live in seconds
        """
        self.redis_client = redis.Redis(
            host=redis_host, port=redis_port, db=redis_db, decode_responses=True
        )
        self.ttl = ttl
    
    def _get_cache_key(self, symbol: str, features: Dict[str, Any]) -> str:
        """Generate cache key from symbol and features"""
        features_str = json.dumps(features, sort_keys=True)
        return f"prediction:{symbol}:{hash(features_str)}"
    
    def get(self, symbol: str, features: Dict[str, Any]) -> Optional[PredictionResponse]:
        """Get cached prediction"""
        cache_key = self._get_cache_key(symbol, features)
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return PredictionResponse(**data)
        except Exception as e:
            logger.warning(f"Cache read error: {str(e)}")
        return None
    
    def set(self, symbol: str, features: Dict[str, Any], 
           prediction: PredictionResponse) -> None:
        """Cache prediction"""
        cache_key = self._get_cache_key(symbol, features)
        try:
            prediction_dict = prediction.__dict__
            prediction_dict['timestamp'] = prediction.timestamp.isoformat()
            self.redis_client.setex(
                cache_key, self.ttl, json.dumps(prediction_dict, default=str)
            )
            logger.debug(f"Cached prediction with key: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache write error: {str(e)}")
    
    def invalidate(self, symbol: str = None) -> None:
        """Invalidate cache entries"""
        try:
            if symbol:
                pattern = f"prediction:{symbol}:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            else:
                # Clear all prediction caches
                pattern = "prediction:*"
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
        except Exception as e:
            logger.warning(f"Cache invalidation error: {str(e)}")


class AbacusAIPredictor:
    """Abacus.AI Real-time Prediction API Client"""
    
    def __init__(self, client, model_trainer, cache: PredictionCache = None):
        """
        Initialize predictor
        
        Args:
            client: Abacus.AI client instance
            model_trainer: Trained model instance
            cache: Prediction cache instance
        """
        self.client = client
        self.model_trainer = model_trainer
        self.cache = cache
        self.app = FastAPI(title="Abacus.AI Prediction API", version="1.0.0")
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/predict", response_model=PredictionResponse)
        async def predict(request: PredictionRequest):
            """Make real-time prediction"""
            return await self._make_prediction(request)
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "timestamp": datetime.utcnow()}
        
        @self.app.post("/batch_predict")
        async def batch_predict(requests: List[PredictionRequest]):
            """Batch prediction endpoint"""
            return await self._batch_predict(requests)
        
        @self.app.delete("/cache")
        async def clear_cache(symbol: Optional[str] = None):
            """Clear prediction cache"""
            if self.cache:
                self.cache.invalidate(symbol)
                return {"message": f"Cache cleared for {'all symbols' if symbol is None else symbol}"}
            return {"message": "Cache not enabled"}
    
    async def _make_prediction(self, request: PredictionRequest) -> PredictionResponse:
        """Make a single prediction with error handling and retry logic"""
        start_time = time.time()
        
        # Check cache first
        cached_result = None
        if self.cache:
            cached_result = self.cache.get(request.symbol, request.features)
            if cached_result:
                cached_result.cached = True
                cached_result.processing_time = time.time() - start_time
                logger.info(f"Cache hit for {request.request_id}")
                return cached_result
        
        try:
            # Validate input
            self._validate_request(request)
            
            # Prepare features
            features_df = self._prepare_features(request.features)
            
            # Make prediction with retry logic
            prediction = await self._predict_with_retry(features_df, request.symbol)
            
            # Calculate confidence (simplified - would be model-specific)
            confidence = self._calculate_confidence(features_df)
            
            # Create response
            response = PredictionResponse(
                request_id=request.request_id,
                symbol=request.symbol,
                prediction=float(prediction[0]) if isinstance(prediction, np.ndarray) else float(prediction),
                confidence=confidence,
                status=PredictionStatus.COMPLETED,
                timestamp=datetime.utcnow(),
                processing_time=time.time() - start_time
            )
            
            # Cache result
            if self.cache:
                self.cache.set(request.symbol, request.features, response)
            
            logger.info(f"Prediction completed for {request.request_id} in {response.processing_time:.3f}s")
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Prediction failed for {request.request_id}: {str(e)}")
            
            return PredictionResponse(
                request_id=request.request_id,
                symbol=request.symbol,
                prediction=0.0,
                confidence=0.0,
                status=PredictionStatus.FAILED,
                timestamp=datetime.utcnow(),
                processing_time=processing_time,
                error=str(e)
            )
    
    async def _batch_predict(self, requests: List[PredictionRequest]) -> List[PredictionResponse]:
        """Make batch predictions"""
        tasks = [self._make_prediction(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                final_responses.append(PredictionResponse(
                    request_id=requests[i].request_id,
                    symbol=requests[i].symbol,
                    prediction=0.0,
                    confidence=0.0,
                    status=PredictionStatus.FAILED,
                    timestamp=datetime.utcnow(),
                    processing_time=0.0,
                    error=str(response)
                ))
            else:
                final_responses.append(response)
        
        return final_responses
    
    async def _predict_with_retry(self, features_df: pd.DataFrame, symbol: str, 
                                 max_retries: int = 3) -> Union[float, np.ndarray]:
        """Make prediction with retry logic"""
        for attempt in range(max_retries):
            try:
                if hasattr(self.model_trainer, 'best_model') and self.model_trainer.best_model:
                    # Use local model
                    prediction = self.model_trainer.predict(features_df)
                    return prediction
                else:
                    # Use Abacus.AI API
                    return await self._call_abacus_api(features_df, symbol)
                    
            except Exception as e:
                logger.warning(f"Prediction attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def _call_abacus_api(self, features_df: pd.DataFrame, symbol: str) -> float:
        """Call Abacus.AI prediction API"""
        endpoint = "/predict"
        data = {
            "symbol": symbol,
            "features": features_df.iloc[0].to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            result = self.client._make_request('POST', endpoint, data=data)
            return result.get("prediction", 0.0)
        except Exception as e:
            logger.error(f"Abacus.AI API call failed: {str(e)}")
            raise
    
    def _validate_request(self, request: PredictionRequest):
        """Validate prediction request"""
        if not request.symbol:
            raise ValueError("Symbol is required")
        
        if not request.features:
            raise ValueError("Features are required")
        
        # Add more validation as needed
        required_features = ["open", "high", "low", "close", "volume"]
        missing_features = [f for f in required_features if f not in request.features]
        if missing_features:
            raise ValueError(f"Missing required features: {missing_features}")
    
    def _prepare_features(self, features: Dict[str, Any]) -> pd.DataFrame:
        """Prepare features for prediction"""
        # Convert to DataFrame and ensure numeric types
        df = pd.DataFrame([features])
        
        # Ensure numeric columns
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        return df
    
    def _calculate_confidence(self, features_df: pd.DataFrame) -> float:
        """Calculate prediction confidence (simplified)"""
        # This is a simplified confidence calculation
        # In practice, you'd use model-specific confidence metrics
        return 0.85  # Default confidence
    
    def start_server(self, host: str = "0.0.0.0", port: int = 8000, 
                    reload: bool = False):
        """Start the FastAPI server"""
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )


class PredictionMonitor:
    """Monitor prediction API performance and health"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.metrics = {
            "total_predictions": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "cache_hits": 0,
            "average_response_time": 0.0,
            "last_prediction": None
        }
    
    def record_prediction(self, response: PredictionResponse):
        """Record prediction metrics"""
        self.metrics["total_predictions"] += 1
        
        if response.status == PredictionStatus.COMPLETED:
            self.metrics["successful_predictions"] += 1
        elif response.status == PredictionStatus.FAILED:
            self.metrics["failed_predictions"] += 1
        
        if response.cached:
            self.metrics["cache_hits"] += 1
        
        # Update average response time
        total_time = (self.metrics["average_response_time"] * 
                     (self.metrics["total_predictions"] - 1) + 
                     response.processing_time)
        self.metrics["average_response_time"] = total_time / self.metrics["total_predictions"]
        
        self.metrics["last_prediction"] = response.timestamp.isoformat()
        
        # Store metrics in Redis if available
        if self.redis_client:
            try:
                self.redis_client.hset("prediction_metrics", mapping=self.metrics)
            except Exception as e:
                logger.warning(f"Failed to store metrics in Redis: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        # Update metrics from Redis if available
        if self.redis_client:
            try:
                stored_metrics = self.redis_client.hgetall("prediction_metrics")
                if stored_metrics:
                    # Convert string values to appropriate types
                    for key, value in stored_metrics.items():
                        if key in ["total_predictions", "successful_predictions", 
                                  "failed_predictions", "cache_hits"]:
                            self.metrics[key] = int(value)
                        elif key == "average_response_time":
                            self.metrics[key] = float(value)
            except Exception as e:
                logger.warning(f"Failed to load metrics from Redis: {str(e)}")
        
        # Calculate additional metrics
        if self.metrics["total_predictions"] > 0:
            self.metrics["success_rate"] = (
                self.metrics["successful_predictions"] / self.metrics["total_predictions"]
            )
            self.metrics["cache_hit_rate"] = (
                self.metrics["cache_hits"] / self.metrics["total_predictions"]
            )
        
        return self.metrics.copy()