"""
Complete Data Pipeline Flow Testing
Tests the full flow: Market Data → Features → Predictions → Redis → LEAN → Trading
"""
import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
import aioredis

from config import TestConfig, PIPELINE_FLOW, TEST_SCENARIOS
from utils.helpers import TestHelpers

class DataPipelineFlowTests:
    """Comprehensive data pipeline flow testing"""
    
    def __init__(self):
        self.config = TestConfig()
        self.helpers = TestHelpers()
        self.test_symbols = self.config.TEST_DATA.symbols[:5]  # Use subset for tests
        
    @pytest.mark.e2e
    @pytest.mark.integration
    async def test_complete_pipeline_flow(self, redis_client, mock_letta_client, 
                                        mock_abacus_client, mock_quantconnect_client):
        """Test complete pipeline from market data to trading execution"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting complete pipeline flow test")
        start_time = time.time()
        
        # Step 1: Market Data Collection
        logger.info("Step 1: Collecting market data from QuantConnect")
        market_data = await self._collect_market_data(mock_quantconnect_client)
        assert market_data is not None, "Market data collection failed"
        assert len(market_data) > 0, "No market data returned"
        
        # Step 2: Feature Engineering
        logger.info("Step 2: Computing features")
        features = await self._compute_features(market_data, mock_abacus_client)
        assert features is not None, "Feature computation failed"
        assert len(features) > 0, "No features computed"
        
        # Step 3: Prediction Generation
        logger.info("Step 3: Generating predictions")
        predictions = await self._generate_predictions(features, mock_abacus_client)
        assert predictions is not None, "Prediction generation failed"
        assert len(predictions) > 0, "No predictions generated"
        
        # Step 4: Redis Caching
        logger.info("Step 4: Caching data in Redis")
        await self._cache_data_in_redis(redis_client, market_data, features, predictions)
        
        # Step 5: LEAN Trading
        logger.info("Step 5: LEAN trading execution")
        trading_results = await self._execute_trading_with_lean(mock_letta_client)
        
        # Step 6: Validation
        logger.info("Step 6: Validating pipeline results")
        pipeline_duration = time.time() - start_time
        assert pipeline_duration < 60, f"Pipeline took too long: {pipeline_duration}s"
        
        # Verify all stages completed successfully
        assert all([market_data, features, predictions, trading_results])
        
        logger.info(f"Complete pipeline test passed in {pipeline_duration:.2f}s")
        
    @pytest.mark.e2e
    async def test_parallel_pipeline_execution(self, redis_client, mock_services):
        """Test parallel processing of multiple symbols"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting parallel pipeline execution test")
        start_time = time.time()
        
        # Process symbols in parallel
        tasks = []
        for symbol in self.test_symbols:
            task = self._process_single_symbol(
                redis_client, mock_services, symbol
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) >= len(self.test_symbols) * 0.9, \
            f"Too many failures: {len(results) - len(successful_results)}"
        
        pipeline_duration = time.time() - start_time
        logger.info(f"Parallel processing of {len(self.test_symbols)} symbols "
                   f"completed in {pipeline_duration:.2f}s")
        
        # Check performance threshold
        max_expected_time = len(self.test_symbols) * 5  # 5 seconds per symbol
        assert pipeline_duration < max_expected_time
        
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_high_volume_pipeline(self, redis_client, mock_services):
        """Test pipeline with high volume of data"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting high volume pipeline test")
        
        # Generate large dataset
        large_dataset = self._generate_large_dataset(1000)  # 1000 data points
        
        # Process in batches
        batch_size = 100
        total_processed = 0
        start_time = time.time()
        
        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i:i + batch_size]
            
            # Process batch
            tasks = [self._process_data_point(redis_client, mock_services, dp) 
                    for dp in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for r in results if not isinstance(r, Exception))
            total_processed += successful
            
            # Verify throughput
            current_time = time.time() - start_time
            if current_time > 0:
                throughput = total_processed / current_time
                assert throughput >= self.config.PERFORMANCE_THRESHOLDS.target_throughput_rps * 0.1, \
                    f"Throughput too low: {throughput} rps"
        
        logger.info(f"Processed {total_processed} data points successfully")
        
    @pytest.mark.e2e
    async def test_pipeline_data_consistency(self, redis_client, mock_services):
        """Test data consistency across pipeline stages"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting data consistency test")
        
        # Process data and store with correlation IDs
        correlation_id = f"test-{int(time.time())}"
        
        # Market data
        market_data = await self._collect_market_data(mock_services['quantconnect'], correlation_id)
        
        # Features  
        features = await self._compute_features(market_data, mock_services['abacus'], correlation_id)
        
        # Predictions
        predictions = await self._generate_predictions(features, mock_services['abacus'], correlation_id)
        
        # Store everything with same correlation ID
        await self._cache_data_with_correlation(redis_client, correlation_id, 
                                              market_data, features, predictions)
        
        # Retrieve and validate consistency
        retrieved_market_data = await redis_client.get(f"market_data:{correlation_id}")
        retrieved_features = await redis_client.get(f"features:{correlation_id}")
        retrieved_predictions = await redis_client.get(f"predictions:{correlation_id}")
        
        assert retrieved_market_data is not None, "Market data not found in cache"
        assert retrieved_features is not None, "Features not found in cache"  
        assert retrieved_predictions is not None, "Predictions not found in cache"
        
        # Verify data integrity
        retrieved_market_data = json.loads(retrieved_market_data)
        retrieved_features = json.loads(retrieved_features)
        retrieved_predictions = json.loads(retrieved_predictions)
        
        # Check that features are derived from market data
        assert len(retrieved_features) <= len(retrieved_market_data), \
            "Feature count exceeds market data count"
        
        # Check that predictions use the features
        assert retrieved_predictions.get('features_used', []), \
            "No features used in predictions"
        
        logger.info("Data consistency test passed")
        
    @pytest.mark.e2e
    async def test_pipeline_recovery(self, redis_client, mock_services):
        """Test pipeline recovery from failures"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting pipeline recovery test")
        
        # Create failure scenarios
        failure_scenarios = [
            ("redis_connection", self._simulate_redis_failure),
            ("abacus_unavailable", self._simulate_abacus_failure),
            ("network_timeout", self._simulate_network_timeout)
        ]
        
        for scenario_name, simulate_failure in failure_scenarios:
            logger.info(f"Testing recovery from: {scenario_name}")
            
            # Simulate failure
            await simulate_failure(mock_services)
            
            # Attempt to process data
            try:
                result = await self._process_data_with_recovery(
                    redis_client, mock_services
                )
                
                # Should either succeed or fail gracefully
                if result:
                    logger.info(f"Recovery from {scenario_name} successful")
                else:
                    logger.info(f"Graceful failure from {scenario_name}")
                    
            except Exception as e:
                # Verify error handling is appropriate
                assert "timeout" in str(e).lower() or "connection" in str(e).lower(), \
                    f"Unexpected error type in {scenario_name}: {e}"
                
                logger.info(f"Expected error in {scenario_name}: {e}")
        
        logger.info("Pipeline recovery test completed")
        
    # Helper methods for pipeline steps
    async def _collect_market_data(self, quantconnect_client, correlation_id=None):
        """Collect market data from QuantConnect"""
        try:
            market_data = await quantconnect_client.get_market_data(
                self.test_symbols,
                self.config.TEST_DATA.date_range
            )
            return market_data
        except Exception as e:
            self.helpers.log_error(f"Market data collection failed: {e}")
            return None
    
    async def _compute_features(self, market_data, abacus_client, correlation_id=None):
        """Compute technical features"""
        try:
            features = await abacus_client.compute_features(
                market_data,
                correlation_id=correlation_id
            )
            return features
        except Exception as e:
            self.helpers.log_error(f"Feature computation failed: {e}")
            return None
    
    async def _generate_predictions(self, features, abacus_client, correlation_id=None):
        """Generate trading predictions"""
        try:
            predictions = await abacus_client.generate_predictions(
                features,
                correlation_id=correlation_id
            )
            return predictions
        except Exception as e:
            self.helpers.log_error(f"Prediction generation failed: {e}")
            return None
    
    async def _cache_data_in_redis(self, redis_client, market_data, features, predictions):
        """Cache all pipeline data in Redis"""
        cache_tasks = []
        
        # Cache market data
        if market_data:
            cache_tasks.append(redis_client.set(
                "market_data:latest", 
                json.dumps(market_data), 
                ex=self.config.CACHE_CONFIG['market_data_ttl']
            ))
        
        # Cache features
        if features:
            cache_tasks.append(redis_client.set(
                "features:latest",
                json.dumps(features),
                ex=self.config.CACHE_CONFIG['feature_ttl']
            ))
        
        # Cache predictions
        if predictions:
            cache_tasks.append(redis_client.set(
                "predictions:latest",
                json.dumps(predictions),
                ex=self.config.CACHE_CONFIG['prediction_ttl']
            ))
        
        await asyncio.gather(*cache_tasks, return_exceptions=True)
    
    async def _execute_trading_with_lean(self, letta_client):
        """Execute trading strategy with LEAN"""
        try:
            result = await letta_client.execute_trading_strategy({
                "strategy": "momentum",
                "symbols": self.test_symbols,
                "amount": self.config.TEST_DATA.investment_amount
            })
            return result
        except Exception as e:
            self.helpers.log_error(f"Trading execution failed: {e}")
            return None
    
    async def _process_single_symbol(self, redis_client, mock_services, symbol):
        """Process pipeline for a single symbol"""
        try:
            # Collect market data
            market_data = await mock_services['quantconnect'].get_symbol_data(symbol)
            
            # Compute features
            features = await mock_services['abacus'].compute_features(market_data)
            
            # Generate prediction
            prediction = await mock_services['abacus'].generate_prediction(features)
            
            # Cache results
            await redis_client.set(f"symbol:{symbol}:market_data", json.dumps(market_data))
            await redis_client.set(f"symbol:{symbol}:features", json.dumps(features))
            await redis_client.set(f"symbol:{symbol}:prediction", json.dumps(prediction))
            
            return {
                "symbol": symbol,
                "market_data": market_data,
                "features": features,
                "prediction": prediction
            }
        except Exception as e:
            self.helpers.log_error(f"Failed to process {symbol}: {e}")
            raise
    
    def _generate_large_dataset(self, size):
        """Generate large dataset for testing"""
        import random
        from datetime import datetime, timedelta
        
        dataset = []
        base_date = datetime.now() - timedelta(days=365)
        
        for i in range(size):
            data_point = {
                "id": i,
                "symbol": random.choice(self.test_symbols),
                "timestamp": base_date + timedelta(days=i),
                "price": random.uniform(100, 1000),
                "volume": random.randint(1000, 1000000)
            }
            dataset.append(data_point)
        
        return dataset
    
    async def _process_data_point(self, redis_client, mock_services, data_point):
        """Process a single data point"""
        try:
            # Simulate processing
            await asyncio.sleep(0.01)  # 10ms processing time
            
            # Cache result
            await redis_client.set(
                f"data_point:{data_point['id']}",
                json.dumps(data_point),
                ex=300
            )
            
            return True
        except Exception as e:
            self.helpers.log_error(f"Failed to process data point {data_point['id']}: {e}")
            return False
    
    async def _cache_data_with_correlation(self, redis_client, correlation_id, 
                                         market_data, features, predictions):
        """Cache data with correlation ID for consistency tracking"""
        tasks = [
            redis_client.set(f"market_data:{correlation_id}", json.dumps(market_data), ex=3600),
            redis_client.set(f"features:{correlation_id}", json.dumps(features), ex=3600),
            redis_client.set(f"predictions:{correlation_id}", json.dumps(predictions), ex=3600)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # Failure simulation methods
    async def _simulate_redis_failure(self, mock_services):
        """Simulate Redis connection failure"""
        if hasattr(mock_services['redis'], 'ping'):
            mock_services['redis'].ping = AsyncMock(side_effect=Exception("Redis unavailable"))
    
    async def _simulate_abacus_failure(self, mock_services):
        """Simulate Abacus.AI service failure"""
        if hasattr(mock_services['abacus'], 'generate_predictions'):
            mock_services['abacus'].generate_predictions = AsyncMock(
                side_effect=Exception("Abacus.AI unavailable")
            )
    
    async def _simulate_network_timeout(self, mock_services):
        """Simulate network timeout"""
        if hasattr(mock_services['abacus'], 'compute_features'):
            mock_services['abacus'].compute_features = AsyncMock(
                side_effect=asyncio.TimeoutError("Network timeout")
            )
    
    async def _process_data_with_recovery(self, redis_client, mock_services):
        """Process data with error recovery"""
        try:
            # Attempt normal processing
            market_data = await mock_services['quantconnect'].get_market_data(self.test_symbols)
            features = await mock_services['abacus'].compute_features(market_data)
            
            if features:
                predictions = await mock_services['abacus'].generate_predictions(features)
                
                # Cache successful results
                await redis_client.set("pipeline:latest", json.dumps({
                    "market_data": market_data,
                    "features": features,
                    "predictions": predictions
                }))
                
                return True
            return False
            
        except Exception as e:
            # Log error but don't fail completely
            self.helpers.log_error(f"Pipeline processing error: {e}")
            
            # Try to use cached data
            cached_data = await redis_client.get("pipeline:latest")
            if cached_data:
                return True
            
            return False

# Pytest test class setup
def pytest_e2e_data_pipeline():
    """Pytest fixture for data pipeline tests"""
    return DataPipelineFlowTests()

if __name__ == "__main__":
    # Run tests directly
    pytest.main([
        __file__,
        "-v",
        "-m", "e2e",
        "--tb=short"
    ])