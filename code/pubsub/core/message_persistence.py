"""
Message Persistence and Replay System
Provides message storage, recovery, and replay capabilities for missed communications
"""

import asyncio
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict, deque
import uuid
import hashlib
import logging
import sqlite3
import aiosqlite
import os
from pathlib import Path

from core.redis_client import RedisPubSubClient, MessagePriority
from protocols.message_schemas import ProtocolMessage, MessageStatus, MessageType


class StorageBackend(Enum):
    """Message storage backends"""
    REDIS = "redis"
    SQLITE = "sqlite"
    REDIS_WITH_SQLITE = "redis_with_sqlite"
    FILE_SYSTEM = "file_system"


class MessageRetention(Enum):
    """Message retention policies"""
    SHORT_TERM = "short_term"     # 1 hour
    MEDIUM_TERM = "medium_term"   # 24 hours  
    LONG_TERM = "long_term"       # 7 days
    PERMANENT = "permanent"


@dataclass
class StoredMessage:
    """Stored message representation"""
    message_id: str
    original_message: ProtocolMessage
    stored_at: datetime
    storage_backend: StorageBackend
    storage_location: str  # Key/path to the stored data
    retention_policy: MessageRetention
    replay_count: int = 0
    access_count: int = 0
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageReplayRequest:
    """Message replay request"""
    request_id: str
    requester_id: str
    message_ids: List[str] = field(default_factory=list)
    channel_pattern: Optional[str] = None
    sender_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    message_types: List[MessageType] = field(default_factory=list)
    limit: int = 100
    delivered: bool = False
    replay_count: int = 0
    max_replays: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MessageArchive:
    """Message archive for long-term storage"""
    archive_id: str
    name: str
    storage_path: str
    retention_period: int  # days
    compression_enabled: bool = False
    encryption_enabled: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    total_messages: int = 0
    total_size_bytes: int = 0


class MessagePersistence:
    """Message persistence and storage manager"""
    
    def __init__(self, redis_client: RedisPubSubClient, 
                 storage_backend: StorageBackend = StorageBackend.REDIS_WITH_SQLITE,
                 storage_path: str = "./pubsub_storage"):
        self.redis = redis_client
        self.storage_backend = storage_backend
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Message storage
        self.stored_messages: Dict[str, StoredMessage] = {}
        self.message_channels: Dict[str, List[str]] = defaultdict(list)  # channel -> message_ids
        self.message_senders: Dict[str, List[str]] = defaultdict(list)  # sender_id -> message_ids
        
        # Replay management
        self.active_replays: Dict[str, MessageReplayRequest] = {}
        self.replay_handlers: Dict[str, Callable] = {}
        
        # Archive management
        self.archives: Dict[str, MessageArchive] = {}
        
        # Retention policies
        self.retention_policies = {
            MessageRetention.SHORT_TERM: timedelta(hours=1),
            MessageRetention.MEDIUM_TERM: timedelta(hours=24),
            MessageRetention.LONG_TERM: timedelta(days=7)
        }
        
        # Storage statistics
        self.stats = {
            'messages_stored': 0,
            'messages_replayed': 0,
            'storage_operations': 0,
            'storage_errors': 0,
            'total_storage_size': 0,
            'archive_count': 0
        }
        
        # Thread safety
        self.storage_lock = asyncio.Lock()
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.archive_task: Optional[asyncio.Task] = None
        
        # Database setup
        self.db_path = self.storage_path / "persistence.db"
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the persistence service"""
        # Initialize database
        await self._initialize_database()
        
        # Load existing messages
        await self._load_stored_messages()
        
        # Start background tasks
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        self.archive_task = asyncio.create_task(self._archive_old_messages())
        
        self.logger.info(f"Message persistence service started with {self.storage_backend.value} backend")
    
    async def stop(self):
        """Stop the persistence service"""
        # Cancel background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
        if self.archive_task:
            self.archive_task.cancel()
        
        # Save pending messages
        await self._save_pending_messages()
        
        self.logger.info("Message persistence service stopped")
    
    async def store_message(self, message: ProtocolMessage, 
                          retention_policy: MessageRetention = MessageRetention.MEDIUM_TERM,
                          force_store: bool = False) -> bool:
        """Store a message for persistence"""
        try:
            # Only store messages that require acknowledgment or are explicitly marked for storage
            if not (message.requires_acknowledgment or force_store):
                return False
            
            async with self.storage_lock:
                # Create stored message
                stored_message = StoredMessage(
                    message_id=message.message_id,
                    original_message=message,
                    stored_at=datetime.utcnow(),
                    storage_backend=self.storage_backend,
                    storage_location=f"message:{message.message_id}",
                    retention_policy=retention_policy
                )
                
                # Calculate checksum
                message_json = json.dumps(message.to_dict(), default=str)
                stored_message.checksum = hashlib.sha256(message_json.encode()).hexdigest()
                
                # Store based on backend
                if self.storage_backend == StorageBackend.REDIS:
                    await self._store_in_redis(stored_message)
                elif self.storage_backend == StorageBackend.SQLITE:
                    await self._store_in_sqlite(stored_message)
                elif self.storage_backend == StorageBackend.REDIS_WITH_SQLITE:
                    await self._store_in_redis_and_sqlite(stored_message)
                
                # Update indexes
                self.stored_messages[message.message_id] = stored_message
                self.message_channels[message.channel].append(message.message_id)
                self.message_senders[message.sender_id].append(message.message_id)
                
                # Update statistics
                self.stats['messages_stored'] += 1
                self.stats['storage_operations'] += 1
                
                self.logger.debug(f"Message {message.message_id} stored with {retention_policy.value} retention")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store message {message.message_id}: {e}")
            self.stats['storage_errors'] += 1
            return False
    
    async def retrieve_message(self, message_id: str) -> Optional[StoredMessage]:
        """Retrieve a stored message"""
        try:
            stored_message = self.stored_messages.get(message_id)
            
            if stored_message:
                # Update access count
                stored_message.access_count += 1
                
                # Load message data if not cached
                if not stored_message.original_message:
                    stored_message = await self._load_message_data(message_id)
                
                return stored_message
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve message {message_id}: {e}")
            return None
    
    async def replay_messages(self, replay_request: MessageReplayRequest) -> List[StoredMessage]:
        """Replay missed messages"""
        try:
            async with self.storage_lock:
                # Find matching messages
                matching_messages = await self._find_matching_messages(replay_request)
                
                if not matching_messages:
                    self.logger.info(f"No messages found for replay request {replay_request.request_id}")
                    return []
                
                # Apply limit
                if len(matching_messages) > replay_request.limit:
                    matching_messages = matching_messages[:replay_request.limit]
                
                # Replay messages
                replayed_messages = []
                for stored_message in matching_messages:
                    if stored_message.replay_count < replay_request.max_replays:
                        # Create replay message
                        replay_message = ProtocolMessage(
                            message_id=f"replay_{stored_message.message_id}_{uuid.uuid4().hex[:8]}",
                            sender_id="persistence_system",
                            recipient_id=replay_request.requester_id,
                            channel=stored_message.original_message.channel,
                            message_type=stored_message.original_message.message_type,
                            title=f"[REPLAY] {stored_message.original_message.title}",
                            content=stored_message.original_message.content,
                            payload=stored_message.original_message.payload,
                            correlation_id=stored_message.message_id,
                            priority=MessagePriority.LOW,
                            requires_acknowledgment=False
                        )
                        
                        # Mark as replayed
                        stored_message.replay_count += 1
                        replayed_messages.append(stored_message)
                        
                        # Publish replay message
                        await self.redis.publish(replay_message)
                
                # Update statistics
                self.stats['messages_replayed'] += len(replayed_messages)
                
                # Mark replay as completed
                replay_request.delivered = True
                replay_request.replay_count += 1
                
                self.logger.info(f"Replayed {len(replayed_messages)} messages for request {replay_request.request_id}")
                return replayed_messages
                
        except Exception as e:
            self.logger.error(f"Failed to replay messages: {e}")
            return []
    
    async def search_messages(self, criteria: Dict[str, Any]) -> List[StoredMessage]:
        """Search stored messages by criteria"""
        try:
            matching_messages = []
            
            for stored_message in self.stored_messages.values():
                if self._matches_criteria(stored_message, criteria):
                    matching_messages.append(stored_message)
            
            # Apply sorting and limits
            limit = criteria.get('limit', 100)
            if len(matching_messages) > limit:
                matching_messages = matching_messages[:limit]
            
            return matching_messages
            
        except Exception as e:
            self.logger.error(f"Failed to search messages: {e}")
            return []
    
    async def create_archive(self, archive_name: str, retention_days: int = 30,
                           compression: bool = False, encryption: bool = False) -> str:
        """Create a message archive"""
        try:
            archive_id = str(uuid.uuid4())
            archive_path = self.storage_path / f"archive_{archive_id}"
            archive_path.mkdir(exist_ok=True)
            
            archive = MessageArchive(
                archive_id=archive_id,
                name=archive_name,
                storage_path=str(archive_path),
                retention_period=retention_days,
                compression_enabled=compression,
                encryption_enabled=encryption
            )
            
            self.archives[archive_id] = archive
            
            # Save archive metadata
            archive_file = archive_path / "archive.json"
            with open(archive_file, 'w') as f:
                json.dump(asdict(archive), f, default=str, indent=2)
            
            self.stats['archive_count'] += 1
            
            self.logger.info(f"Archive {archive_name} created with ID {archive_id}")
            return archive_id
            
        except Exception as e:
            self.logger.error(f"Failed to create archive: {e}")
            raise
    
    async def archive_messages(self, archive_id: str, 
                             message_criteria: Dict[str, Any]) -> bool:
        """Archive messages based on criteria"""
        try:
            if archive_id not in self.archives:
                raise ValueError(f"Archive {archive_id} not found")
            
            archive = self.archives[archive_id]
            
            # Find messages to archive
            messages_to_archive = await self.search_messages(message_criteria)
            
            # Archive messages
            archive_path = Path(archive.storage_path)
            archived_count = 0
            
            for stored_message in messages_to_archive:
                # Copy message to archive
                archive_file = archive_path / f"{stored_message.message_id}.json"
                
                message_data = {
                    **asdict(stored_message),
                    'original_message': stored_message.original_message.to_dict(),
                    'archived_at': datetime.utcnow().isoformat()
                }
                
                with open(archive_file, 'w') as f:
                    json.dump(message_data, f, default=str, indent=2)
                
                # Remove from active storage
                await self._remove_from_storage(stored_message.message_id)
                
                archived_count += 1
            
            # Update archive stats
            archive.total_messages += archived_count
            archive.total_size_bytes += archived_count * 1000  # Approximate
            
            # Save updated archive metadata
            archive_file = archive_path / "archive.json"
            with open(archive_file, 'w') as f:
                json.dump(asdict(archive), f, default=str, indent=2)
            
            self.logger.info(f"Archived {archived_count} messages to archive {archive_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to archive messages: {e}")
            return False
    
    async def _initialize_database(self):
        """Initialize SQLite database for message storage"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Create stored messages table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS stored_messages (
                        message_id TEXT PRIMARY KEY,
                        original_message TEXT NOT NULL,
                        stored_at TEXT NOT NULL,
                        storage_backend TEXT NOT NULL,
                        storage_location TEXT NOT NULL,
                        retention_policy TEXT NOT NULL,
                        replay_count INTEGER DEFAULT 0,
                        access_count INTEGER DEFAULT 0,
                        checksum TEXT,
                        metadata TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_stored_at ON stored_messages(stored_at)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_storage_backend ON stored_messages(storage_backend)
                """)
                
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_retention_policy ON stored_messages(retention_policy)
                """)
                
                # Create message replay requests table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS replay_requests (
                        request_id TEXT PRIMARY KEY,
                        requester_id TEXT NOT NULL,
                        message_ids TEXT,
                        channel_pattern TEXT,
                        sender_id TEXT,
                        start_time TEXT,
                        end_time TEXT,
                        message_types TEXT,
                        limit INTEGER DEFAULT 100,
                        delivered BOOLEAN DEFAULT FALSE,
                        replay_count INTEGER DEFAULT 0,
                        max_replays INTEGER DEFAULT 3,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _store_in_redis(self, stored_message: StoredMessage):
        """Store message in Redis"""
        message_key = f"stored_message:{stored_message.message_id}"
        message_data = {
            'original_message': stored_message.original_message.to_dict(),
            'stored_at': stored_message.stored_at.isoformat(),
            'storage_backend': stored_message.storage_backend.value,
            'storage_location': stored_message.storage_location,
            'retention_policy': stored_message.retention_policy.value,
            'replay_count': stored_message.replay_count,
            'access_count': stored_message.access_count,
            'checksum': stored_message.checksum,
            'metadata': stored_message.metadata
        }
        
        # Calculate expiration time based on retention policy
        expiration = int(self.retention_policies[stored_message.retention_policy].total_seconds())
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.redis.connection.setex(
                message_key,
                expiration,
                json.dumps(message_data, default=str)
            )
        )
    
    async def _store_in_sqlite(self, stored_message: StoredMessage):
        """Store message in SQLite"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO stored_messages (
                    message_id, original_message, stored_at, storage_backend,
                    storage_location, retention_policy, replay_count, access_count,
                    checksum, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stored_message.message_id,
                json.dumps(stored_message.original_message.to_dict(), default=str),
                stored_message.stored_at.isoformat(),
                stored_message.storage_backend.value,
                stored_message.storage_location,
                stored_message.retention_policy.value,
                stored_message.replay_count,
                stored_message.access_count,
                stored_message.checksum,
                json.dumps(stored_message.metadata, default=str)
            ))
            
            await db.commit()
    
    async def _store_in_redis_and_sqlite(self, stored_message: StoredMessage):
        """Store message in both Redis and SQLite"""
        await self._store_in_redis(stored_message)
        await self._store_in_sqlite(stored_message)
    
    async def _load_stored_messages(self):
        """Load stored messages from storage backends"""
        try:
            # Load from Redis
            redis_keys = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.keys("stored_message:*")
            )
            
            for key in redis_keys:
                message_json = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.get(key)
                )
                
                if message_json:
                    message_data = json.loads(message_json)
                    stored_message = await self._create_stored_message_from_data(message_data)
                    if stored_message:
                        self.stored_messages[stored_message.message_id] = stored_message
            
            # Load from SQLite
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT * FROM stored_messages") as cursor:
                    async for row in cursor:
                        stored_message = await self._create_stored_message_from_row(row)
                        if stored_message:
                            self.stored_messages[stored_message.message_id] = stored_message
            
            self.logger.info(f"Loaded {len(self.stored_messages)} stored messages")
            
        except Exception as e:
            self.logger.error(f"Failed to load stored messages: {e}")
    
    async def _create_stored_message_from_data(self, data: Dict[str, Any]) -> Optional[StoredMessage]:
        """Create StoredMessage from data dictionary"""
        try:
            return StoredMessage(
                message_id=data['message_id'],
                original_message=ProtocolMessage.from_dict(data['original_message']),
                stored_at=datetime.fromisoformat(data['stored_at']),
                storage_backend=StorageBackend(data['storage_backend']),
                storage_location=data['storage_location'],
                retention_policy=MessageRetention(data['retention_policy']),
                replay_count=data.get('replay_count', 0),
                access_count=data.get('access_count', 0),
                checksum=data.get('checksum'),
                metadata=data.get('metadata', {})
            )
        except Exception as e:
            self.logger.error(f"Failed to create stored message from data: {e}")
            return None
    
    async def _create_stored_message_from_row(self, row) -> Optional[StoredMessage]:
        """Create StoredMessage from database row"""
        try:
            return StoredMessage(
                message_id=row[0],
                original_message=ProtocolMessage.from_dict(json.loads(row[1])),
                stored_at=datetime.fromisoformat(row[2]),
                storage_backend=StorageBackend(row[3]),
                storage_location=row[4],
                retention_policy=MessageRetention(row[5]),
                replay_count=row[6] or 0,
                access_count=row[7] or 0,
                checksum=row[8],
                metadata=json.loads(row[9]) if row[9] else {}
            )
        except Exception as e:
            self.logger.error(f"Failed to create stored message from row: {e}")
            return None
    
    async def _find_matching_messages(self, replay_request: MessageReplayRequest) -> List[StoredMessage]:
        """Find messages matching replay request criteria"""
        matching_messages = []
        
        for stored_message in self.stored_messages.values():
            if self._matches_replay_criteria(stored_message, replay_request):
                matching_messages.append(stored_message)
        
        # Sort by stored_at (oldest first)
        matching_messages.sort(key=lambda m: m.stored_at)
        
        return matching_messages
    
    def _matches_replay_criteria(self, stored_message: StoredMessage, 
                               replay_request: MessageReplayRequest) -> bool:
        """Check if message matches replay criteria"""
        message = stored_message.original_message
        
        # Check specific message IDs
        if replay_request.message_ids:
            if message.message_id not in replay_request.message_ids:
                return False
        
        # Check channel pattern
        if replay_request.channel_pattern:
            if replay_request.channel_pattern not in message.channel:
                return False
        
        # Check sender ID
        if replay_request.sender_id:
            if message.sender_id != replay_request.sender_id:
                return False
        
        # Check message types
        if replay_request.message_types:
            if message.message_type not in replay_request.message_types:
                return False
        
        # Check time range
        if replay_request.start_time and stored_message.stored_at < replay_request.start_time:
            return False
        
        if replay_request.end_time and stored_message.stored_at > replay_request.end_time:
            return False
        
        return True
    
    def _matches_criteria(self, stored_message: StoredMessage, criteria: Dict[str, Any]) -> bool:
        """Check if stored message matches search criteria"""
        message = stored_message.original_message
        
        # Check message type
        if 'message_type' in criteria:
            if message.message_type != MessageType(criteria['message_type']):
                return False
        
        # Check channel
        if 'channel' in criteria:
            if criteria['channel'] not in message.channel:
                return False
        
        # Check sender
        if 'sender_id' in criteria:
            if message.sender_id != criteria['sender_id']:
                return False
        
        # Check time range
        if 'start_time' in criteria:
            if stored_message.stored_at < criteria['start_time']:
                return False
        
        if 'end_time' in criteria:
            if stored_message.stored_at > criteria['end_time']:
                return False
        
        # Check retention policy
        if 'retention_policy' in criteria:
            if stored_message.retention_policy != MessageRetention(criteria['retention_policy']):
                return False
        
        return True
    
    async def _remove_from_storage(self, message_id: str):
        """Remove message from all storage backends"""
        try:
            # Remove from local cache
            self.stored_messages.pop(message_id, None)
            
            # Remove from Redis
            message_key = f"stored_message:{message_id}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.delete(message_key)
            )
            
            # Remove from SQLite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM stored_messages WHERE message_id = ?", (message_id,))
                await db.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to remove message {message_id} from storage: {e}")
    
    async def _load_message_data(self, message_id: str) -> Optional[StoredMessage]:
        """Load message data from storage"""
        # Try Redis first
        message_key = f"stored_message:{message_id}"
        message_json = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.redis.connection.get(message_key)
        )
        
        if message_json:
            message_data = json.loads(message_json)
            return await self._create_stored_message_from_data(message_data)
        
        # Try SQLite if Redis fails
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM stored_messages WHERE message_id = ?", 
                (message_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return await self._create_stored_message_from_row(row)
        
        return None
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                current_time = datetime.utcnow()
                expired_messages = []
                
                for message_id, stored_message in self.stored_messages.items():
                    retention_period = self.retention_policies[stored_message.retention_policy]
                    
                    if current_time - stored_message.stored_at > retention_period:
                        expired_messages.append(message_id)
                
                # Remove expired messages
                for message_id in expired_messages:
                    await self._remove_from_storage(message_id)
                    self.logger.debug(f"Removed expired message {message_id}")
                
                if expired_messages:
                    self.logger.info(f"Cleaned up {len(expired_messages)} expired messages")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)
    
    async def _archive_old_messages(self):
        """Archive old messages periodically"""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                # Archive messages older than long-term retention
                cutoff_time = datetime.utcnow() - timedelta(days=30)
                
                messages_to_archive = []
                for stored_message in self.stored_messages.values():
                    if (stored_message.stored_at < cutoff_time and
                        stored_message.retention_policy != MessageRetention.PERMANENT):
                        messages_to_archive.append(stored_message.message_id)
                
                if messages_to_archive:
                    # Find or create default archive
                    default_archive_id = None
                    for archive_id, archive in self.archives.items():
                        if archive.name == "default_archive":
                            default_archive_id = archive_id
                            break
                    
                    if not default_archive_id:
                        default_archive_id = await self.create_archive(
                            "default_archive", retention_days=365
                        )
                    
                    # Archive messages
                    await self.archive_messages(
                        default_archive_id,
                        {'message_ids': messages_to_archive}
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in archive task: {e}")
                await asyncio.sleep(3600)
    
    async def _save_pending_messages(self):
        """Save pending messages before shutdown"""
        try:
            # This would save any in-memory messages to persistent storage
            # Implementation depends on specific requirements
            pass
        except Exception as e:
            self.logger.error(f"Failed to save pending messages: {e}")
    
    def get_persistence_stats(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        return {
            'stored_messages': len(self.stored_messages),
            'active_replays': len(self.active_replays),
            'archives': len(self.archives),
            'statistics': self.stats.copy(),
            'storage_backend': self.storage_backend.value,
            'message_channels': len(self.message_channels),
            'message_senders': len(self.message_senders)
        }


# Example usage
async def create_persistence_service(redis_config: Dict[str, Any],
                                  storage_backend: StorageBackend = StorageBackend.REDIS_WITH_SQLITE,
                                  storage_path: str = "./pubsub_storage") -> MessagePersistence:
    """Create a message persistence service"""
    redis_client = RedisPubSubClient(**redis_config)
    await redis_client.connect()
    
    persistence = MessagePersistence(
        redis_client, 
        storage_backend=storage_backend,
        storage_path=storage_path
    )
    
    await persistence.start()
    return persistence