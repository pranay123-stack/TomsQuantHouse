"""
Message persistence and replay system.
Provides reliable message storage, recovery, and replay capabilities for critical messages.
"""

from typing import Dict, Any, List, Optional, Callable, Iterator, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import hashlib
import logging
import sqlite3
import pickle
import gzip
import os
import threading
import time
from pathlib import Path
from collections import defaultdict, deque

from schemas.message_schemas import BaseMessage, MessageType, DeliveryGuarantee

logger = logging.getLogger(__name__)


class StorageType(Enum):
    """Message storage types"""
    PERSISTENT = "persistent"      # Always persisted
    VOLATILE = "volatile"          # Never persisted (except for retries)
    CONDITIONAL = "conditional"    # Persisted based on criteria
    CACHED = "cached"             # Stored temporarily for quick access


class RetentionPolicy(Enum):
    """Message retention policies"""
    FOREVER = "forever"           # Never delete
    TIME_BASED = "time_based"     # Delete after time limit
    SIZE_BASED = "size_based"     # Delete when storage limit reached
    USAGE_BASED = "usage_based"   # Delete based on usage patterns
    HYBRID = "hybrid"            # Combination of above


class ReplayMode(Enum):
    """Message replay modes"""
    EXACT = "exact"               # Replay in exact order
    TIME_ORDERED = "time_ordered" # Replay by timestamp
    PRIORITY = "priority"         # Replay by priority
    SELECTIVE = "selective"       # Replay based on criteria
    INCREMENTAL = "incremental"   # Replay new messages only


@dataclass
class MessageRecord:
    """Persistent message record"""
    record_id: str
    message_id: str
    message_type: str
    sender_id: str
    recipient_id: Optional[str]
    channel: Optional[str]
    payload: bytes  # Compressed message data
    metadata: bytes  # Serialized metadata
    storage_type: StorageType
    retention_policy: RetentionPolicy
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    checksum: Optional[str] = None
    compression_ratio: float = 1.0


@dataclass
class ReplaySession:
    """Message replay session"""
    session_id: str
    query: Dict[str, Any]
    replay_mode: ReplayMode
    started_at: datetime
    status: str = "running"  # running, completed, paused, error
    total_messages: int = 0
    replayed_messages: int = 0
    failed_messages: int = 0
    callback: Optional[Callable] = None
    progress_callback: Optional[Callable] = None


@dataclass
class StorageQuota:
    """Storage quota configuration"""
    max_size_mb: int = 1024  # 1GB default
    max_messages: int = 1000000  # 1M messages default
    max_age_days: int = 30  # 30 days default
    cleanup_batch_size: int = 1000


class MessagePersistor:
    """Message persistence manager with multiple storage backends"""
    
    def __init__(self, persistor_id: str, storage_path: str = "./storage"):
        self.persistor_id = persistor_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Storage backends
        self.sqlite_backend = SQLiteBackend(self.storage_path / "messages.db")
        self.file_backend = FileBackend(self.storage_path / "files")
        
        # In-memory caches
        self.message_cache: Dict[str, MessageRecord] = {}
        self.hot_messages: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Retention policies
        self.retention_policies: Dict[str, RetentionPolicy] = {}
        self.storage_quotas: Dict[str, StorageQuota] = defaultdict(lambda: StorageQuota())
        
        # Session management
        self.active_sessions: Dict[str, ReplaySession] = {}
        self.session_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'messages_stored': 0,
            'messages_replayed': 0,
            'storage_size_mb': 0.0,
            'cache_hit_rate': 0.0,
            'compression_ratio': 1.0
        }
        
        # Background cleanup task
        self.cleanup_running = False
        self.cleanup_thread = None
        
        logger.info(f"Message persistor {persistor_id} initialized")
    
    def start(self):
        """Start the persistor"""
        self.sqlite_backend.connect()
        self.cleanup_running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info(f"Message persistor {self.persistor_id} started")
    
    def stop(self):
        """Stop the persistor"""
        self.cleanup_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        self.sqlite_backend.disconnect()
        logger.info(f"Message persistor {self.persistor_id} stopped")
    
    def store_message(self, message: BaseMessage, 
                     storage_type: StorageType = StorageType.PERSISTENT,
                     retention_policy: RetentionPolicy = RetentionPolicy.TIME_BASED,
                     ttl_seconds: Optional[int] = None) -> str:
        """Store a message persistently"""
        try:
            # Compress message data
            message_data = message.to_json().encode('utf-8')
            compressed_data, compression_ratio = self._compress_data(message_data)
            
            # Create checksum for integrity
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            # Calculate expiry time
            expires_at = None
            if ttl_seconds:
                expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            elif retention_policy == RetentionPolicy.TIME_BASED:
                expires_at = datetime.now() + timedelta(days=30)
            
            # Create record
            record = MessageRecord(
                record_id=str(uuid.uuid4()),
                message_id=message.metadata.message_id,
                message_type=message.message_type.value,
                sender_id=message.sender_id,
                recipient_id=message.recipient_id,
                channel=message.channel,
                payload=compressed_data,
                metadata=pickle.dumps(message.metadata),
                storage_type=storage_type,
                retention_policy=retention_policy,
                created_at=message.metadata.timestamp,
                expires_at=expires_at,
                checksum=checksum,
                compression_ratio=compression_ratio
            )
            
            # Store in backend
            success = self.sqlite_backend.store_record(record)
            if not success:
                raise Exception("Failed to store message in backend")
            
            # Cache hot messages
            if message.metadata.priority.value >= 3:  # High priority or above
                self.message_cache[record.message_id] = record
                self.hot_messages[message.sender_id].append(record)
            
            # Update statistics
            self.stats['messages_stored'] += 1
            self.stats['compression_ratio'] = compression_ratio
            
            logger.debug(f"Stored message {record.message_id} with record {record.record_id}")
            return record.record_id
            
        except Exception as e:
            logger.error(f"Failed to store message {message.metadata.message_id}: {e}")
            raise
    
    def retrieve_message(self, message_id: str) -> Optional[BaseMessage]:
        """Retrieve a stored message"""
        try:
            # Check cache first
            if message_id in self.message_cache:
                record = self.message_cache[message_id]
                record.access_count += 1
                record.last_accessed = datetime.now()
                self.stats['cache_hit_rate'] += 1
                return self._deserialize_message(record)
            
            # Retrieve from backend
            record = self.sqlite_backend.retrieve_record(message_id)
            if not record:
                return None
            
            # Update access tracking
            record.access_count += 1
            record.last_accessed = datetime.now()
            self.sqlite_backend.update_record_access(record)
            
            # Add to cache if it's frequently accessed
            if record.access_count > 10:
                self.message_cache[message_id] = record
            
            return self._deserialize_message(record)
            
        except Exception as e:
            logger.error(f"Failed to retrieve message {message_id}: {e}")
            return None
    
    def retrieve_messages_by_criteria(self, criteria: Dict[str, Any]) -> List[BaseMessage]:
        """Retrieve messages matching criteria"""
        try:
            records = self.sqlite_backend.retrieve_records_by_criteria(criteria)
            messages = []
            
            for record in records:
                try:
                    message = self._deserialize_message(record)
                    if message:
                        messages.append(message)
                except Exception as e:
                    logger.error(f"Failed to deserialize message {record.message_id}: {e}")
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to retrieve messages by criteria: {e}")
            return []
    
    def start_replay_session(self, query: Dict[str, Any], 
                           replay_mode: ReplayMode = ReplayMode.EXACT,
                           callback: Optional[Callable] = None,
                           progress_callback: Optional[Callable] = None) -> str:
        """Start a message replay session"""
        session_id = str(uuid.uuid4())
        
        session = ReplaySession(
            session_id=session_id,
            query=query,
            replay_mode=replay_mode,
            started_at=datetime.now(),
            callback=callback,
            progress_callback=progress_callback
        )
        
        with self.session_lock:
            self.active_sessions[session_id] = session
        
        # Start replay in background
        asyncio.create_task(self._run_replay_session(session))
        
        logger.info(f"Started replay session {session_id}")
        return session_id
    
    def get_replay_session_status(self, session_id: str) -> Optional[ReplaySession]:
        """Get status of a replay session"""
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def pause_replay_session(self, session_id: str) -> bool:
        """Pause a replay session"""
        with self.session_lock:
            session = self.active_sessions.get(session_id)
            if session and session.status == "running":
                session.status = "paused"
                return True
        return False
    
    def resume_replay_session(self, session_id: str) -> bool:
        """Resume a paused replay session"""
        with self.session_lock:
            session = self.active_sessions.get(session_id)
            if session and session.status == "paused":
                session.status = "running"
                return True
        return False
    
    def stop_replay_session(self, session_id: str) -> bool:
        """Stop a replay session"""
        with self.session_lock:
            session = self.active_sessions.get(session_id)
            if session:
                session.status = "completed"
                return True
        return False
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            backend_stats = self.sqlite_backend.get_statistics()
            cache_stats = {
                'cached_messages': len(self.message_cache),
                'cache_size_mb': sum(len(pickle.dumps(r)) for r in self.message_cache.values()) / (1024 * 1024),
                'hot_message_queues': {k: len(v) for k, v in self.hot_messages.items()}
            }
            
            return {
                'persistor_id': self.persistor_id,
                'storage_backend': 'sqlite',
                'messages_stored': self.stats['messages_stored'],
                'messages_replayed': self.stats['messages_replayed'],
                'storage_size_mb': backend_stats.get('storage_size_mb', 0),
                'record_count': backend_stats.get('record_count', 0),
                'cache_hit_rate': self.stats['cache_hit_rate'] / max(1, self.stats['messages_stored']),
                'compression_ratio': self.stats['compression_ratio'],
                'active_sessions': len(self.active_sessions),
                'backend_statistics': backend_stats,
                'cache_statistics': cache_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
    
    def cleanup_expired_messages(self) -> int:
        """Clean up expired messages"""
        try:
            expired_records = self.sqlite_backend.get_expired_records()
            cleaned_count = 0
            
            for record in expired_records:
                try:
                    self.sqlite_backend.delete_record(record.record_id)
                    self.message_cache.pop(record.message_id, None)
                    cleaned_count += 1
                except Exception as e:
                    logger.error(f"Failed to clean up record {record.record_id}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} expired messages")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired messages: {e}")
            return 0
    
    def _compress_data(self, data: bytes) -> tuple[bytes, float]:
        """Compress data and return compressed data with ratio"""
        try:
            compressed = gzip.compress(data)
            ratio = len(compressed) / len(data) if len(data) > 0 else 1.0
            return compressed, ratio
        except Exception:
            return data, 1.0
    
    def _deserialize_message(self, record: MessageRecord) -> Optional[BaseMessage]:
        """Deserialize message from record"""
        try:
            # Verify checksum
            if record.checksum:
                current_checksum = hashlib.sha256(record.payload).hexdigest()
                if current_checksum != record.checksum:
                    logger.error(f"Checksum mismatch for message {record.message_id}")
                    return None
            
            # Decompress data
            try:
                decompressed_data = gzip.decompress(record.payload)
            except Exception:
                # Assume data is not compressed
                decompressed_data = record.payload
            
            # Deserialize message
            message_json = decompressed_data.decode('utf-8')
            return BaseMessage.from_json(message_json)
            
        except Exception as e:
            logger.error(f"Failed to deserialize message {record.message_id}: {e}")
            return None
    
    async def _run_replay_session(self, session: ReplaySession):
        """Run a replay session"""
        try:
            logger.info(f"Starting replay session {session.session_id}")
            
            # Get messages to replay
            criteria = session.query.copy()
            criteria['replay_mode'] = session.replay_mode.value
            
            records = self.sqlite_backend.retrieve_records_by_criteria(criteria)
            session.total_messages = len(records)
            
            # Sort records based on replay mode
            records = self._sort_records_for_replay(records, session.replay_mode)
            
            # Replay messages
            for i, record in enumerate(records):
                if session.status == "completed":
                    break
                
                # Pause if needed
                while session.status == "paused":
                    await asyncio.sleep(0.1)
                
                if session.status != "running":
                    break
                
                try:
                    message = self._deserialize_message(record)
                    if message and session.callback:
                        await self._safe_callback(session.callback, message)
                    
                    session.replayed_messages += 1
                    
                    # Progress callback
                    if session.progress_callback:
                        await self._safe_callback(
                            session.progress_callback,
                            session.replayed_messages,
                            session.total_messages
                        )
                    
                except Exception as e:
                    logger.error(f"Failed to replay message {record.message_id}: {e}")
                    session.failed_messages += 1
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.001)
            
            session.status = "completed"
            self.stats['messages_replayed'] += session.replayed_messages
            
            logger.info(f"Replay session {session.session_id} completed. "
                       f"Replayed: {session.replayed_messages}, "
                       f"Failed: {session.failed_messages}")
            
        except Exception as e:
            logger.error(f"Replay session {session.session_id} failed: {e}")
            session.status = "error"
        finally:
            # Clean up session
            with self.session_lock:
                self.active_sessions.pop(session.session_id, None)
    
    def _sort_records_for_replay(self, records: List[MessageRecord], 
                               replay_mode: ReplayMode) -> List[MessageRecord]:
        """Sort records for replay based on mode"""
        if replay_mode == ReplayMode.EXACT:
            return sorted(records, key=lambda r: (r.created_at, r.record_id))
        elif replay_mode == ReplayMode.TIME_ORDERED:
            return sorted(records, key=lambda r: r.created_at)
        elif replay_mode == ReplayMode.PRIORITY:
            # Priority would need to be extracted from metadata
            return sorted(records, key=lambda r: pickle.loads(r.metadata).priority.value, reverse=True)
        else:
            return records
    
    async def _safe_callback(self, callback: Callable, *args, **kwargs):
        """Safely execute callback with error handling"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args, **kwargs)
            else:
                callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Callback execution failed: {e}")
    
    def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.cleanup_running:
            try:
                self.cleanup_expired_messages()
                time.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                time.sleep(60)


class SQLiteBackend:
    """SQLite-based storage backend for message persistence"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.connection = None
        self.write_lock = threading.Lock()
        
    def connect(self):
        """Connect to SQLite database"""
        try:
            self.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            
            # Enable WAL mode for better concurrency
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA synchronous=NORMAL")
            self.connection.execute("PRAGMA cache_size=10000")
            self.connection.execute("PRAGMA temp_store=memory")
            
            self._create_tables()
            logger.info(f"Connected to SQLite database: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to connect to SQLite database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from SQLite database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from SQLite database")
    
    def store_record(self, record: MessageRecord) -> bool:
        """Store a message record"""
        try:
            with self.write_lock:
                cursor = self.connection.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO message_records (
                        record_id, message_id, message_type, sender_id, recipient_id,
                        channel, payload, metadata, storage_type, retention_policy,
                        created_at, expires_at, access_count, last_accessed,
                        checksum, compression_ratio
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.record_id, record.message_id, record.message_type,
                    record.sender_id, record.recipient_id, record.channel,
                    record.payload, record.metadata, record.storage_type.value,
                    record.retention_policy.value, record.created_at.isoformat(),
                    record.expires_at.isoformat() if record.expires_at else None,
                    record.access_count, record.last_accessed.isoformat() 
                    if record.last_accessed else None,
                    record.checksum, record.compression_ratio
                ))
                
                self.connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to store record: {e}")
            return False
    
    def retrieve_record(self, message_id: str) -> Optional[MessageRecord]:
        """Retrieve a message record by message ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM message_records WHERE message_id = ?
            """, (message_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve record: {e}")
            return None
    
    def retrieve_records_by_criteria(self, criteria: Dict[str, Any]) -> List[MessageRecord]:
        """Retrieve message records matching criteria"""
        try:
            where_conditions = []
            params = []
            
            # Build WHERE clause
            if 'message_type' in criteria:
                where_conditions.append("message_type = ?")
                params.append(criteria['message_type'])
            
            if 'sender_id' in criteria:
                where_conditions.append("sender_id = ?")
                params.append(criteria['sender_id'])
            
            if 'recipient_id' in criteria:
                where_conditions.append("recipient_id = ?")
                params.append(criteria['recipient_id'])
            
            if 'channel' in criteria:
                where_conditions.append("channel = ?")
                params.append(criteria['channel'])
            
            if 'start_time' in criteria:
                where_conditions.append("created_at >= ?")
                params.append(criteria['start_time'].isoformat())
            
            if 'end_time' in criteria:
                where_conditions.append("created_at <= ?")
                params.append(criteria['end_time'].isoformat())
            
            if 'storage_type' in criteria:
                where_conditions.append("storage_type = ?")
                params.append(criteria['storage_type'])
            
            # Build query
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            limit = criteria.get('limit', 1000)
            offset = criteria.get('offset', 0)
            
            query = f"""
                SELECT * FROM message_records 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            
            records = []
            for row in cursor.fetchall():
                record = self._row_to_record(row)
                if record:
                    records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to retrieve records by criteria: {e}")
            return []
    
    def get_expired_records(self) -> List[MessageRecord]:
        """Get expired message records"""
        try:
            cursor = self.connection.cursor()
            current_time = datetime.now().isoformat()
            
            cursor.execute("""
                SELECT * FROM message_records 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (current_time,))
            
            records = []
            for row in cursor.fetchall():
                record = self._row_to_record(row)
                if record:
                    records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get expired records: {e}")
            return []
    
    def delete_record(self, record_id: str) -> bool:
        """Delete a message record"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM message_records WHERE record_id = ?", (record_id,))
            self.connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to delete record: {e}")
            return False
    
    def update_record_access(self, record: MessageRecord):
        """Update record access information"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE message_records 
                SET access_count = ?, last_accessed = ?
                WHERE record_id = ?
            """, (
                record.access_count,
                record.last_accessed.isoformat() if record.last_accessed else None,
                record.record_id
            ))
            
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to update record access: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Get basic counts
            cursor.execute("SELECT COUNT(*) FROM message_records")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM message_records WHERE expires_at IS NOT NULL")
            expirable_records = cursor.fetchone()[0]
            
            # Get storage size (approximate)
            cursor.execute("SELECT SUM(LENGTH(payload) + LENGTH(metadata)) FROM message_records")
            total_size = cursor.fetchone()[0] or 0
            
            # Get records by storage type
            cursor.execute("""
                SELECT storage_type, COUNT(*) 
                FROM message_records 
                GROUP BY storage_type
            """)
            type_counts = dict(cursor.fetchall())
            
            return {
                'record_count': total_records,
                'expirable_records': expirable_records,
                'storage_size_bytes': total_size,
                'storage_size_mb': total_size / (1024 * 1024),
                'records_by_type': type_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def _create_tables(self):
        """Create database tables"""
        try:
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS message_records (
                    record_id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    recipient_id TEXT,
                    channel TEXT,
                    payload BLOB NOT NULL,
                    metadata BLOB NOT NULL,
                    storage_type TEXT NOT NULL,
                    retention_policy TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    checksum TEXT,
                    compression_ratio REAL DEFAULT 1.0,
                    INDEX idx_message_id (message_id),
                    INDEX idx_sender_id (sender_id),
                    INDEX idx_recipient_id (recipient_id),
                    INDEX idx_channel (channel),
                    INDEX idx_created_at (created_at),
                    INDEX idx_expires_at (expires_at)
                )
            """)
            
            self.connection.execute("""
                CREATE TABLE IF NOT EXISTS replay_sessions (
                    session_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    replay_mode TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_messages INTEGER DEFAULT 0,
                    replayed_messages INTEGER DEFAULT 0,
                    failed_messages INTEGER DEFAULT 0
                )
            """)
            
            self.connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def _row_to_record(self, row) -> Optional[MessageRecord]:
        """Convert database row to MessageRecord"""
        try:
            return MessageRecord(
                record_id=row[0],
                message_id=row[1],
                message_type=row[2],
                sender_id=row[3],
                recipient_id=row[4],
                channel=row[5],
                payload=row[6],
                metadata=row[7],
                storage_type=StorageType(row[8]),
                retention_policy=RetentionPolicy(row[9]),
                created_at=datetime.fromisoformat(row[10]),
                expires_at=datetime.fromisoformat(row[11]) if row[11] else None,
                access_count=row[12] or 0,
                last_accessed=datetime.fromisoformat(row[13]) if row[13] else None,
                checksum=row[14],
                compression_ratio=row[15] or 1.0
            )
            
        except Exception as e:
            logger.error(f"Failed to convert row to record: {e}")
            return None


class FileBackend:
    """File-based storage backend for large messages"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def store_file(self, file_id: str, data: bytes) -> bool:
        """Store large file data"""
        try:
            file_path = self.storage_path / f"{file_id}.dat"
            with open(file_path, 'wb') as f:
                f.write(data)
            return True
        except Exception as e:
            logger.error(f"Failed to store file: {e}")
            return False
    
    def retrieve_file(self, file_id: str) -> Optional[bytes]:
        """Retrieve large file data"""
        try:
            file_path = self.storage_path / f"{file_id}.dat"
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve file: {e}")
            return None


# Example usage and factory functions
def create_default_persistor(persistor_id: str, storage_path: str = "./storage") -> MessagePersistor:
    """Create default persistor with configuration"""
    persistor = MessagePersistor(persistor_id, storage_path)
    
    # Configure retention policies
    persistor.retention_policies['high_priority'] = RetentionPolicy.FOREVER
    persistor.retention_policies['normal_priority'] = RetentionPolicy.TIME_BASED
    persistor.retention_policies['low_priority'] = RetentionPolicy.SIZE_BASED
    
    # Configure storage quotas
    persistor.storage_quotas['global'] = StorageQuota(
        max_size_mb=1024,
        max_messages=1000000,
        max_age_days=30
    )
    
    return persistor