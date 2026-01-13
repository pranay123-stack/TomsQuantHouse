"""
Redis Pub/Sub Client for Agent Communication System
Provides connection management, pub/sub capabilities, and message handling
"""

import json
import redis
import asyncio
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from enum import Enum
import ssl


class MessagePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class AgentType(Enum):
    TRADER = "trader"
    PREDICTOR = "predictor"
    ALERT_HANDLER = "alert_handler"
    COORDINATOR = "coordinator"
    MONITOR = "monitor"
    ANALYZER = "analyzer"


@dataclass
class Message:
    id: str
    sender_id: str
    recipient_id: Optional[str]
    channel: str
    message_type: str
    priority: MessagePriority
    timestamp: datetime
    payload: Dict[str, Any]
    requires_acknowledgment: bool = False
    encrypted: bool = False
    retry_count: int = 0


class RedisPubSubClient:
    """Redis Pub/Sub client with advanced features for agent coordination"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None, 
                 ssl=False, max_connections=10):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ssl = ssl
        self.max_connections = max_connections
        self.redis_pool = None
        self.connection = None
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.priority_handlers: Dict[MessagePriority, List[Callable]] = {
            priority: [] for priority in MessagePriority
        }
        
        # Connection and monitoring
        self.is_connected = False
        self.connection_stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'errors': 0,
            'last_error': None,
            'uptime': 0
        }
        
        self.logger = logging.getLogger(__name__)
        
    async def connect(self):
        """Establish connection to Redis"""
        try:
            connection_params = {
                'host': self.host,
                'port': self.port,
                'db': self.db,
                'max_connections': self.max_connections,
                'decode_responses': True
            }
            
            if self.password:
                connection_params['password'] = self.password
                
            if self.ssl:
                connection_params['ssl'] = ssl.SSLContext()
                
            # Create connection pool
            self.redis_pool = redis.ConnectionPool(**connection_params)
            self.connection = redis.Redis(connection_pool=self.redis_pool)
            
            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, self.connection.ping
            )
            
            self.is_connected = True
            self.logger.info(f"Connected to Redis at {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        try:
            if self.connection:
                self.connection.close()
            if self.redis_pool:
                self.redis_pool.disconnect()
            self.is_connected = False
            self.logger.info("Disconnected from Redis")
        except Exception as e:
            self.logger.error(f"Error disconnecting from Redis: {e}")
    
    async def publish(self, message: Message) -> bool:
        """Publish a message to a channel"""
        if not self.is_connected:
            raise ConnectionError("Not connected to Redis")
            
        try:
            # Serialize message
            message_dict = asdict(message)
            message_dict['timestamp'] = message.timestamp.isoformat()
            
            # Store in persistence layer if needed
            if hasattr(self, '_message_store'):
                await self._store_message(message)
            
            # Publish to channel
            channel_name = self._get_channel_name(message.channel, message.priority)
            
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: self.connection.publish(
                    channel_name, 
                    json.dumps(message_dict)
                )
            )
            
            self.connection_stats['messages_sent'] += 1
            self.logger.debug(f"Published message {message.id} to {channel_name}")
            
            return True
            
        except Exception as e:
            self.connection_stats['errors'] += 1
            self.connection_stats['last_error'] = str(e)
            self.logger.error(f"Failed to publish message {message.id}: {e}")
            return False
    
    async def subscribe(self, channels: List[str], handler: Callable[[Message], None]):
        """Subscribe to channels with message handler"""
        if not self.is_connected:
            raise ConnectionError("Not connected to Redis")
            
        try:
            # Create pubsub instance
            pubsub = self.connection.pubsub()
            
            # Subscribe to all priority variants of channels
            all_channels = []
            for channel in channels:
                for priority in MessagePriority:
                    all_channels.append(self._get_channel_name(channel, priority))
            
            pubsub.subscribe(*all_channels)
            
            # Store handler
            for channel in channels:
                self.message_handlers[channel] = handler
            
            # Start listening for messages
            asyncio.create_task(self._listen_to_messages(pubsub))
            
            self.logger.info(f"Subscribed to channels: {channels}")
            
        except Exception as e:
            self.logger.error(f"Failed to subscribe to channels {channels}: {e}")
            raise
    
    async def _listen_to_messages(self, pubsub):
        """Listen for messages and route to appropriate handlers"""
        try:
            while self.is_connected:
                try:
                    message = await asyncio.get_event_loop().run_in_executor(
                        None, pubsub.get_message, 1.0
                    )
                    
                    if message and message['type'] == 'message':
                        await self._process_message(message)
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"Error in message listener: {e}")
                    self.connection_stats['errors'] += 1
                    
        except Exception as e:
            self.logger.error(f"Message listener error: {e}")
        finally:
            pubsub.close()
    
    async def _process_message(self, message_data: Dict):
        """Process incoming message and route to handler"""
        try:
            # Deserialize message
            message_dict = json.loads(message_data['data'])
            message_dict['timestamp'] = datetime.fromisoformat(message_dict['timestamp'])
            
            # Create Message object
            message = Message(**message_dict)
            
            # Route to appropriate priority handlers first
            for handler in self.priority_handlers[message.priority]:
                await handler(message)
            
            # Route to channel-specific handler
            channel = message.channel
            if channel in self.message_handlers:
                await self.message_handlers[channel](message)
            
            self.connection_stats['messages_received'] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.connection_stats['errors'] += 1
    
    def _get_channel_name(self, base_channel: str, priority: MessagePriority) -> str:
        """Get channel name with priority suffix"""
        priority_suffix = {
            MessagePriority.LOW: 'low',
            MessagePriority.NORMAL: 'normal', 
            MessagePriority.HIGH: 'high',
            MessagePriority.CRITICAL: 'critical'
        }
        return f"{base_channel}:{priority_suffix[priority]}"
    
    def register_priority_handler(self, priority: MessagePriority, handler: Callable[[Message], None]):
        """Register handler for messages of specific priority"""
        self.priority_handlers[priority].append(handler)
        self.logger.debug(f"Registered priority handler for {priority.name}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return self.connection_stats.copy()
    
    async def _store_message(self, message: Message):
        """Store message for persistence"""
        try:
            if not hasattr(self, '_message_store'):
                return
                
            # Store in Redis with expiration for message replay
            message_key = f"message:{message.id}"
            message_dict = asdict(message)
            message_dict['timestamp'] = message.timestamp.isoformat()
            
            self.connection.setex(
                message_key,
                3600,  # 1 hour expiration
                json.dumps(message_dict)
            )
        except Exception as e:
            self.logger.error(f"Failed to store message {message.id}: {e}")


# Connection factory
class RedisConnectionFactory:
    """Factory for creating Redis connections"""
    
    @staticmethod
    def create_client(config: Dict[str, Any]) -> RedisPubSubClient:
        """Create Redis client from configuration"""
        return RedisPubSubClient(
            host=config.get('host', 'localhost'),
            port=config.get('port', 6379),
            db=config.get('db', 0),
            password=config.get('password'),
            ssl=config.get('ssl', False),
            max_connections=config.get('max_connections', 10)
        )