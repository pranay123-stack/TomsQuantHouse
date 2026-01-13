"""
Redis Memory Integration for CrewAI Trading Agents
Provides crew-wide memory storage and context sharing
"""
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from redis.asyncio import Redis
from redis.exceptions import RedisError
from config.settings import settings, RedisKeys


class CrewMemoryManager:
    """Manages shared memory across all agents in the crew"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        self.redis: Optional[Redis] = None
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """Establish Redis connection"""
        try:
            self.redis = Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            await self.redis.ping()
            self.logger.info("Connected to Redis successfully")
        except RedisError as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            self.logger.info("Disconnected from Redis")
    
    # Crew Memory Methods
    async def store_crew_memory(self, crew_id: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store data in crew shared memory"""
        try:
            if not self.redis:
                await self.connect()
            
            memory_key = RedisKeys.format_key(RedisKeys.CREW_MEMORY, crew_id=crew_id)
            field_key = f"{key}:{datetime.now().isoformat()}"
            
            serialized_value = json.dumps(value, default=str)
            
            # Use hash for organized storage
            await self.redis.hset(memory_key, field_key, serialized_value)
            
            # Set TTL if specified
            if ttl:
                await self.redis.expire(memory_key, ttl)
            else:
                await self.redis.expire(memory_key, settings.memory_retention)
            
            return True
        except RedisError as e:
            self.logger.error(f"Failed to store crew memory: {e}")
            return False
    
    async def get_crew_memory(self, crew_id: str, key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve data from crew shared memory"""
        try:
            if not self.redis:
                await self.connect()
            
            memory_key = RedisKeys.format_key(RedisKeys.CREW_MEMORY, crew_id=crew_id)
            
            if key:
                # Get specific field
                field_keys = await self.redis.hkeys(memory_key)
                matching_keys = [k for k in field_keys if k.startswith(key)]
                
                if not matching_keys:
                    return None
                
                # Get most recent entry
                latest_key = max(matching_keys)
                value = await self.redis.hget(memory_key, latest_key)
                
                if value:
                    return json.loads(value)
                return None
            else:
                # Get all fields
                all_data = await self.redis.hgetall(memory_key)
                return {k: json.loads(v) for k, v in all_data.items()}
                
        except RedisError as e:
            self.logger.error(f"Failed to get crew memory: {e}")
            return None
    
    async def clear_crew_memory(self, crew_id: str) -> bool:
        """Clear all crew memory"""
        try:
            if not self.redis:
                await self.connect()
            
            memory_key = RedisKeys.format_key(RedisKeys.CREW_MEMORY, crew_id=crew_id)
            await self.redis.delete(memory_key)
            return True
        except RedisError as e:
            self.logger.error(f"Failed to clear crew memory: {e}")
            return False
    
    # Agent Memory Methods
    async def store_agent_memory(self, crew_id: str, agent_id: str, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store data in agent-specific memory"""
        try:
            if not self.redis:
                await self.connect()
            
            memory_key = RedisKeys.format_key(RedisKeys.AGENT_MEMORY, agent_id=agent_id, crew_id=crew_id)
            field_key = f"{key}:{datetime.now().isoformat()}"
            
            serialized_value = json.dumps(value, default=str)
            await self.redis.hset(memory_key, field_key, serialized_value)
            
            if ttl:
                await self.redis.expire(memory_key, ttl)
            
            return True
        except RedisError as e:
            self.logger.error(f"Failed to store agent memory: {e}")
            return False
    
    async def get_agent_memory(self, crew_id: str, agent_id: str, key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve data from agent-specific memory"""
        try:
            if not self.redis:
                await self.connect()
            
            memory_key = RedisKeys.format_key(RedisKeys.AGENT_MEMORY, agent_id=agent_id, crew_id=crew_id)
            
            if key:
                field_keys = await self.redis.hkeys(memory_key)
                matching_keys = [k for k in field_keys if k.startswith(key)]
                
                if not matching_keys:
                    return None
                
                latest_key = max(matching_keys)
                value = await self.redis.hget(memory_key, latest_key)
                
                if value:
                    return json.loads(value)
                return None
            else:
                all_data = await self.redis.hgetall(memory_key)
                return {k: json.loads(v) for k, v in all_data.items()}
                
        except RedisError as e:
            self.logger.error(f"Failed to get agent memory: {e}")
            return None
    
    # Market Data Caching
    async def cache_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any], ttl: int = 300) -> bool:
        """Cache market data"""
        try:
            if not self.redis:
                await self.connect()
            
            cache_key = RedisKeys.format_key(RedisKeys.MARKET_DATA, symbol=symbol, timeframe=timeframe)
            serialized_data = json.dumps(data, default=str)
            
            await self.redis.setex(cache_key, ttl, serialized_data)
            return True
        except RedisError as e:
            self.logger.error(f"Failed to cache market data: {e}")
            return False
    
    async def get_cached_market_data(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get cached market data"""
        try:
            if not self.redis:
                await self.connect()
            
            cache_key = RedisKeys.format_key(RedisKeys.MARKET_DATA, symbol=symbol, timeframe=timeframe)
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
        except RedisError as e:
            self.logger.error(f"Failed to get cached market data: {e}")
            return None
    
    # Portfolio State Management
    async def store_portfolio_state(self, crew_id: str, state: Dict[str, Any]) -> bool:
        """Store current portfolio state"""
        return await self.store_crew_memory(crew_id, "portfolio_state", state)
    
    async def get_portfolio_state(self, crew_id: str) -> Optional[Dict[str, Any]]:
        """Get current portfolio state"""
        return await self.get_crew_memory(crew_id, "portfolio_state")
    
    # Risk Metrics Management
    async def store_risk_metrics(self, crew_id: str, metrics: Dict[str, Any]) -> bool:
        """Store risk metrics"""
        return await self.store_crew_memory(crew_id, "risk_metrics", metrics)
    
    async def get_risk_metrics(self, crew_id: str) -> Optional[Dict[str, Any]]:
        """Get risk metrics"""
        return await self.get_crew_memory(crew_id, "risk_metrics")
    
    # Approval Queue Management
    async def add_approval_request(self, crew_id: str, request: Dict[str, Any]) -> bool:
        """Add approval request to queue"""
        try:
            if not self.redis:
                await self.connect()
            
            queue_key = RedisKeys.format_key(RedisKeys.APPROVAL_QUEUE, crew_id=crew_id)
            request_id = f"req_{datetime.now().timestamp()}"
            
            serialized_request = json.dumps(request, default=str)
            await self.redis.hset(queue_key, request_id, serialized_request)
            
            return True
        except RedisError as e:
            self.logger.error(f"Failed to add approval request: {e}")
            return False
    
    async def get_approval_queue(self, crew_id: str) -> Dict[str, Any]:
        """Get all pending approval requests"""
        try:
            if not self.redis:
                await self.connect()
            
            queue_key = RedisKeys.format_key(RedisKeys.APPROVAL_QUEUE, crew_id=crew_id)
            queue_data = await self.redis.hgetall(queue_key)
            
            return {k: json.loads(v) for k, v in queue_data.items()}
        except RedisError as e:
            self.logger.error(f"Failed to get approval queue: {e}")
            return {}
    
    async def process_approval_request(self, crew_id: str, request_id: str, decision: str, notes: Optional[str] = None) -> bool:
        """Process approval request (approve/reject)"""
        try:
            if not self.redis:
                await self.connect()
            
            queue_key = RedisKeys.format_key(RedisKeys.APPROVAL_QUEUE, crew_id=crew_id)
            
            # Remove processed request
            await self.redis.hdel(queue_key, request_id)
            
            # Store decision in memory
            decision_data = {
                "request_id": request_id,
                "decision": decision,
                "timestamp": datetime.now().isoformat(),
                "notes": notes
            }
            
            await self.store_crew_memory(crew_id, f"approval_decision_{request_id}", decision_data)
            
            return True
        except RedisError as e:
            self.logger.error(f"Failed to process approval request: {e}")
            return False


# Global memory manager instance
memory_manager = CrewMemoryManager()