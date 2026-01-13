"""
Redis Client Wrapper for Trading Framework
Provides methods for caching predictions, storing agent memory, and managing graph state
"""

import redis
import json
import pickle
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingRedisClient:
    """Redis client wrapper for trading framework"""
    
    def __init__(self, host='localhost', port=6379, password='trading_framework_2025', db=0):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=False,  # Keep binary for pickle serialization
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis successfully on {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except redis.AuthenticationError as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    # =============================================================================
    # DATABASE SEPARATION UTILITIES
    # =============================================================================
    
    def get_db_for_prediction(self) -> int:
        """Get database index for predictions cache (db0)"""
        return 0
    
    def get_db_for_agent_memory(self) -> int:
        """Get database index for agent memory (db1)"""
        return 1
    
    def get_db_for_graph_state(self) -> int:
        """Get database index for graph state (db2)"""
        return 2
    
    def get_db_for_entity_memory(self) -> int:
        """Get database index for entity memory (db3)"""
        return 3
    
    # =============================================================================
    # PREDICTIONS CACHE (db0) - ML models, market predictions, signals
    # =============================================================================
    
    def cache_prediction(self, prediction_id: str, prediction_data: Dict, 
                        ttl: int = 3600) -> bool:
        """
        Cache ML model predictions with TTL
        
        Args:
            prediction_id: Unique prediction identifier
            prediction_data: Dictionary containing prediction results
            ttl: Time to live in seconds (default 1 hour)
        
        Returns:
            bool: Success status
        """
        try:
            client = self.redis_client
            client.select(self.get_db_for_prediction())
            
            # Add timestamp and metadata
            prediction_data['cached_at'] = time.time()
            prediction_data['ttl'] = ttl
            
            serialized_data = pickle.dumps(prediction_data)
            result = client.setex(f"prediction:{prediction_id}", ttl, serialized_data)
            
            logger.info(f"Cached prediction {prediction_id} with TTL {ttl}s")
            return result
        except Exception as e:
            logger.error(f"Failed to cache prediction {prediction_id}: {e}")
            return False
    
    def get_prediction(self, prediction_id: str) -> Optional[Dict]:
        """Retrieve cached prediction"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_prediction())
            
            cached_data = client.get(f"prediction:{prediction_id}")
            if cached_data:
                prediction_data = pickle.loads(cached_data)
                logger.info(f"Retrieved prediction {prediction_id}")
                return prediction_data
            return None
        except Exception as e:
            logger.error(f"Failed to get prediction {prediction_id}: {e}")
            return None
    
    def cache_trading_signals(self, market_pair: str, signals: Dict, 
                            ttl: int = 300) -> bool:
        """Cache trading signals for a market pair"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_prediction())
            
            signals['cached_at'] = time.time()
            serialized_signals = pickle.dumps(signals)
            
            result = client.setex(f"signals:{market_pair}", ttl, serialized_signals)
            logger.info(f"Cached trading signals for {market_pair}")
            return result
        except Exception as e:
            logger.error(f"Failed to cache signals for {market_pair}: {e}")
            return False
    
    def get_trading_signals(self, market_pair: str) -> Optional[Dict]:
        """Retrieve cached trading signals"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_prediction())
            
            cached_signals = client.get(f"signals:{market_pair}")
            if cached_signals:
                signals = pickle.loads(cached_signals)
                return signals
            return None
        except Exception as e:
            logger.error(f"Failed to get signals for {market_pair}: {e}")
            return None
    
    # =============================================================================
    # AGENT MEMORY (db1) - AI agent states, conversations, decisions
    # =============================================================================
    
    def store_agent_memory(self, agent_id: str, memory_data: Dict, 
                          ttl: int = 86400) -> bool:
        """
        Store agent memory and state
        
        Args:
            agent_id: Unique agent identifier
            memory_data: Dictionary containing agent memory
            ttl: Time to live in seconds (default 24 hours)
        
        Returns:
            bool: Success status
        """
        try:
            client = self.redis_client
            client.select(self.get_db_for_agent_memory())
            
            memory_data['updated_at'] = time.time()
            serialized_memory = pickle.dumps(memory_data)
            
            result = client.setex(f"agent:{agent_id}", ttl, serialized_memory)
            logger.info(f"Stored memory for agent {agent_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store memory for agent {agent_id}: {e}")
            return False
    
    def get_agent_memory(self, agent_id: str) -> Optional[Dict]:
        """Retrieve agent memory"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_agent_memory())
            
            cached_memory = client.get(f"agent:{agent_id}")
            if cached_memory:
                memory_data = pickle.loads(cached_memory)
                return memory_data
            return None
        except Exception as e:
            logger.error(f"Failed to get memory for agent {agent_id}: {e}")
            return None
    
    def store_conversation_history(self, agent_id: str, conversation: List[Dict],
                                 ttl: int = 86400) -> bool:
        """Store conversation history for an agent"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_agent_memory())
            
            # Limit conversation history to last 100 messages
            if len(conversation) > 100:
                conversation = conversation[-100:]
            
            serialized_conversation = pickle.dumps(conversation)
            result = client.setex(f"conversation:{agent_id}", ttl, serialized_conversation)
            
            logger.info(f"Stored conversation history for agent {agent_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store conversation for agent {agent_id}: {e}")
            return False
    
    def get_conversation_history(self, agent_id: str) -> Optional[List[Dict]]:
        """Retrieve conversation history"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_agent_memory())
            
            cached_conversation = client.get(f"conversation:{agent_id}")
            if cached_conversation:
                conversation = pickle.loads(cached_conversation)
                return conversation
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation for agent {agent_id}: {e}")
            return None
    
    # =============================================================================
    # GRAPH STATE (db2) - Trading relationships, market data graph
    # =============================================================================
    
    def store_graph_node(self, node_id: str, node_data: Dict, 
                        ttl: int = 7200) -> bool:
        """Store graph node data (market entities, relationships)"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_graph_state())
            
            node_data['updated_at'] = time.time()
            serialized_node = pickle.dumps(node_data)
            
            result = client.setex(f"node:{node_id}", ttl, serialized_node)
            logger.info(f"Stored graph node {node_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to store graph node {node_id}: {e}")
            return False
    
    def get_graph_node(self, node_id: str) -> Optional[Dict]:
        """Retrieve graph node"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_graph_state())
            
            cached_node = client.get(f"node:{node_id}")
            if cached_node:
                node_data = pickle.loads(cached_node)
                return node_data
            return None
        except Exception as e:
            logger.error(f"Failed to get graph node {node_id}: {e}")
            return None
    
    def store_graph_edge(self, from_node: str, to_node: str, edge_data: Dict,
                        ttl: int = 3600) -> bool:
        """Store graph edge/relationship"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_graph_state())
            
            edge_data['updated_at'] = time.time()
            edge_data['from_node'] = from_node
            edge_data['to_node'] = to_node
            serialized_edge = pickle.dumps(edge_data)
            
            edge_key = f"edge:{from_node}:{to_node}"
            result = client.setex(edge_key, ttl, serialized_edge)
            
            # Also update adjacency list
            client.sadd(f"adjacent:{from_node}", to_node)
            client.expire(f"adjacent:{from_node}", ttl)
            
            logger.info(f"Stored graph edge {from_node} -> {to_node}")
            return result
        except Exception as e:
            logger.error(f"Failed to store graph edge {from_node} -> {to_node}: {e}")
            return False
    
    def get_adjacent_nodes(self, node_id: str) -> List[str]:
        """Get all adjacent nodes for a given node"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_graph_state())
            
            adjacent = client.smembers(f"adjacent:{node_id}")
            return [node.decode() for node in adjacent] if adjacent else []
        except Exception as e:
            logger.error(f"Failed to get adjacent nodes for {node_id}: {e}")
            return []
    
    # =============================================================================
    # ENTITY MEMORY (db3) - User profiles, market entities, metadata
    # =============================================================================
    
    def store_entity_data(self, entity_id: str, entity_type: str, 
                         entity_data: Dict, ttl: int = 604800) -> bool:
        """Store entity data (user profiles, market instruments, etc.)"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_entity_memory())
            
            entity_data['type'] = entity_type
            entity_data['updated_at'] = time.time()
            serialized_entity = pickle.dumps(entity_data)
            
            result = client.setex(f"entity:{entity_id}", ttl, serialized_entity)
            logger.info(f"Stored entity {entity_id} of type {entity_type}")
            return result
        except Exception as e:
            logger.error(f"Failed to store entity {entity_id}: {e}")
            return False
    
    def get_entity_data(self, entity_id: str) -> Optional[Dict]:
        """Retrieve entity data"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_entity_memory())
            
            cached_entity = client.get(f"entity:{entity_id}")
            if cached_entity:
                entity_data = pickle.loads(cached_entity)
                return entity_data
            return None
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None
    
    def get_entities_by_type(self, entity_type: str) -> List[str]:
        """Get all entities of a specific type"""
        try:
            client = self.redis_client
            client.select(self.get_db_for_entity_memory())
            
            pattern = f"entity:{entity_type}:*"
            keys = client.keys(pattern)
            return [key.decode().split(':')[-1] for key in keys] if keys else []
        except Exception as e:
            logger.error(f"Failed to get entities of type {entity_type}: {e}")
            return []
    
    # =============================================================================
    # GENERAL UTILITY METHODS
    # =============================================================================
    
    def delete_key(self, key: str, db: int = 0) -> bool:
        """Delete a specific key from specified database"""
        try:
            client = self.redis_client
            client.select(db)
            result = client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete key {key} from db {db}: {e}")
            return False
    
    def clear_database(self, db: int) -> bool:
        """Clear all data from specified database"""
        try:
            client = self.redis_client
            client.select(db)
            result = client.flushdb()
            logger.info(f"Cleared database {db}")
            return result
        except Exception as e:
            logger.error(f"Failed to clear database {db}: {e}")
            return False
    
    def get_db_info(self, db: int) -> Dict:
        """Get information about specific database"""
        try:
            client = self.redis_client
            client.select(db)
            info = client.info('keyspace')
            db_key = f"db{db}"
            return info.get(db_key, {})
        except Exception as e:
            logger.error(f"Failed to get info for database {db}: {e}")
            return {}
    
    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            result = self.redis_client.ping()
            logger.info("Redis connection test successful")
            return result
        except Exception as e:
            logger.error(f"Redis connection test failed: {e}")
            return False
    
    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")

# Example usage
if __name__ == "__main__":
    # Initialize client
    redis_client = TradingRedisClient()
    
    # Test prediction caching
    prediction = {
        "model": "LSTM_v2",
        "prediction": "BUY",
        "confidence": 0.85,
        "price_target": 150.25,
        "timestamp": datetime.now().isoformat()
    }
    redis_client.cache_prediction("BTCUSDT_2025_11_02", prediction)
    
    # Test agent memory
    agent_memory = {
        "state": "active",
        "strategy": "momentum",
        "positions": ["BTCUSDT", "ETHUSDT"],
        "last_decision": "hold"
    }
    redis_client.store_agent_memory("trading_agent_1", agent_memory)
    
    print("Redis client test completed successfully!")