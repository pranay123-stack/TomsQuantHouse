#!/usr/bin/env python3
"""
Letta-Redis Integration for Archival Memory Storage
Provides efficient archival storage for agent memory using Redis
"""

import json
import redis
import pickle
import gzip
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArchivalTier(Enum):
    """Archival tiers for memory blocks"""
    HOT = "hot"           # Recently accessed, high priority
    WARM = "warm"         # Moderately accessed, medium priority
    COLD = "cold"         # Infrequently accessed, low priority
    FROZEN = "frozen"     # Very old, archive only


class CompressionType(Enum):
    """Compression types for archival storage"""
    NONE = "none"
    GZIP = "gzip"
    LZ4 = "lz4"
    ZSTD = "zstd"


@dataclass
class ArchivalMetadata:
    """Metadata for archived memory blocks"""
    block_id: str
    agent_id: str
    tier: ArchivalTier
    original_size: int
    compressed_size: int
    compression_type: CompressionType
    created_at: datetime
    archived_at: datetime
    last_accessed: datetime
    access_count: int
    checksum: str
    dependencies: List[str]
    restore_priority: int


@dataclass
class ArchivalQuery:
    """Query for retrieving archived memory"""
    agent_id: str
    block_ids: List[str] = None
    time_range: Tuple[datetime, datetime] = None
    tiers: List[ArchivalTier] = None
    limit: int = 100
    include_metadata: bool = True


@dataclass
class ArchivalStats:
    """Statistics about archival storage"""
    total_blocks: int
    total_size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float
    tier_distribution: Dict[ArchivalTier, int]
    oldest_block: Optional[datetime]
    newest_block: Optional[datetime]
    avg_access_frequency: float


class RedisArchivalManager:
    """Manages archival storage of memory blocks in Redis"""
    
    def __init__(self, redis_config: Dict[str, Any]):
        """
        Initialize Redis archival manager
        
        Args:
            redis_config: Redis connection configuration
        """
        self.redis_config = redis_config
        self.redis_client = None
        self.connection_pool = None
        self._setup_redis()
        
        # Archival configuration
        self.compression_threshold = 1024  # Size in bytes to trigger compression
        self.tier_expiry = {
            ArchivalTier.HOT: timedelta(days=7),
            ArchivalTier.WARM: timedelta(days=30),
            ArchivalTier.COLD: timedelta(days=90),
            ArchivalTier.FROZEN: timedelta(days=365)
        }
        
        # Background processes
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.background_threads = []
        self.running = False
        
        # Archival tracking
        self.archival_queue = []
        self.restoration_queue = []
        
        # Metrics
        self.stats = {
            "archived_blocks": 0,
            "restored_blocks": 0,
            "compression_operations": 0,
            "total_archived_size": 0
        }
    
    def _setup_redis(self):
        """Setup Redis connection and configuration"""
        try:
            # Create connection pool
            self.connection_pool = redis.ConnectionPool(
                host=self.redis_config.get("host", "localhost"),
                port=self.redis_config.get("port", 6379),
                db=self.redis_config.get("db", 0),
                password=self.redis_config.get("password"),
                decode_responses=False,  # We'll handle encoding/decoding
                max_connections=self.redis_config.get("max_connections", 20),
                socket_timeout=self.redis_config.get("socket_timeout", 5),
                socket_connect_timeout=self.redis_config.get("socket_connect_timeout", 5)
            )
            
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup Redis connection: {e}")
            raise
    
    def start_background_processes(self):
        """Start background archival and maintenance processes"""
        self.running = True
        
        # Start archival thread
        archival_thread = threading.Thread(target=self._archival_worker, daemon=True)
        archival_thread.start()
        self.background_threads.append(archival_thread)
        
        # Start tier management thread
        tier_thread = threading.Thread(target=self._tier_management_worker, daemon=True)
        tier_thread.start()
        self.background_threads.append(tier_thread)
        
        # Start stats reporting thread
        stats_thread = threading.Thread(target=self._stats_worker, daemon=True)
        stats_thread.start()
        self.background_threads.append(stats_thread)
        
        logger.info("Background archival processes started")
    
    def stop_background_processes(self):
        """Stop background processes"""
        self.running = False
        
        for thread in self.background_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        logger.info("Background archival processes stopped")
    
    def archive_memory_block(self, 
                           agent_id: str, 
                           block_id: str, 
                           memory_block_data: Dict[str, Any],
                           tier: ArchivalTier = ArchivalTier.WARM) -> bool:
        """Archive a memory block to Redis"""
        
        try:
            logger.info(f"Archiving memory block {block_id} to tier {tier.value}")
            
            # Prepare archival metadata
            archival_metadata = ArchivalMetadata(
                block_id=block_id,
                agent_id=agent_id,
                tier=tier,
                original_size=len(json.dumps(memory_block_data)),
                compressed_size=0,
                compression_type=CompressionType.NONE,
                created_at=datetime.now(),
                archived_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
                checksum=self._calculate_checksum(memory_block_data),
                dependencies=memory_block_data.get("metadata", {}).get("related_blocks", [])
            )
            
            # Compress if beneficial
            compressed_data, compression_type = self._compress_data(memory_block_data)
            
            archival_metadata.compressed_size = len(compressed_data)
            archival_metadata.compression_type = compression_type
            
            # Store in Redis with appropriate keys
            self._store_archived_block(
                agent_id, block_id, compressed_data, archival_metadata
            )
            
            # Update tier index
            self._update_tier_index(agent_id, block_id, tier)
            
            # Update statistics
            self.stats["archived_blocks"] += 1
            self.stats["total_archived_size"] += archival_metadata.compressed_size
            
            if compression_type != CompressionType.NONE:
                self.stats["compression_operations"] += 1
            
            logger.info(f"Successfully archived block {block_id} ({archival_metadata.compressed_size} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive memory block {block_id}: {e}")
            return False
    
    def archive_batch(self, 
                     agent_id: str, 
                     memory_blocks: List[Dict[str, Any]],
                     tier: ArchivalTier = ArchivalTier.WARM) -> Dict[str, bool]:
        """Archive multiple memory blocks in batch"""
        
        results = {}
        
        # Process in batches to avoid overwhelming Redis
        batch_size = 50
        for i in range(0, len(memory_blocks), batch_size):
            batch = memory_blocks[i:i + batch_size]
            
            # Submit batch for processing
            future = self.executor.submit(self._process_batch_archive, agent_id, batch, tier)
            batch_results = future.result()
            
            results.update(batch_results)
        
        logger.info(f"Batch archival completed: {len(results)} blocks processed")
        return results
    
    def _process_batch_archive(self, 
                              agent_id: str, 
                              batch: List[Dict[str, Any]], 
                              tier: ArchivalTier) -> Dict[str, bool]:
        """Process a batch of memory blocks for archival"""
        
        results = {}
        
        for block_data in batch:
            block_id = block_data.get("block_id", "unknown")
            try:
                success = self.archive_memory_block(agent_id, block_id, block_data, tier)
                results[block_id] = success
            except Exception as e:
                logger.error(f"Error archiving block {block_id} in batch: {e}")
                results[block_id] = False
        
        return results
    
    def restore_memory_block(self, 
                           agent_id: str, 
                           block_id: str, 
                           tier: ArchivalTier = None) -> Optional[Dict[str, Any]]:
        """Restore a memory block from archival storage"""
        
        try:
            logger.info(f"Restoring memory block {block_id}")
            
            # Get archival metadata
            metadata_key = f"archival:metadata:{agent_id}:{block_id}"
            metadata_json = self.redis_client.get(metadata_key)
            
            if not metadata_json:
                logger.warning(f"No archival metadata found for block {block_id}")
                return None
            
            archival_metadata = ArchivalMetadata(**json.loads(metadata_json))
            
            # Get tier from metadata if not specified
            if tier is None:
                tier = archival_metadata.tier
            
            # Get archived data
            data_key = f"archival:data:{agent_id}:{block_id}"
            compressed_data = self.redis_client.get(data_key)
            
            if not compressed_data:
                logger.warning(f"No archived data found for block {block_id}")
                return None
            
            # Decompress data
            memory_block_data = self._decompress_data(compressed_data, archival_metadata.compression_type)
            
            # Update access statistics
            self._update_access_stats(agent_id, block_id, archival_metadata)
            
            # Update restoration statistics
            self.stats["restored_blocks"] += 1
            
            logger.info(f"Successfully restored block {block_id}")
            return memory_block_data
            
        except Exception as e:
            logger.error(f"Failed to restore memory block {block_id}: {e}")
            return None
    
    def query_archived_memory(self, query: ArchivalQuery) -> List[Dict[str, Any]]:
        """Query archived memory blocks"""
        
        try:
            logger.info(f"Querying archived memory for agent {query.agent_id}")
            
            # Get all matching block IDs
            block_ids = self._find_matching_blocks(query)
            
            results = []
            for block_id in block_ids[:query.limit]:
                # Restore block data
                restored_data = self.restore_memory_block(query.agent_id, block_id)
                
                if restored_data:
                    # Optionally exclude metadata for privacy
                    if not query.include_metadata:
                        if "metadata" in restored_data:
                            del restored_data["metadata"]
                    
                    results.append(restored_data)
            
            logger.info(f"Query completed: {len(results)} blocks restored")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query archived memory: {e}")
            return []
    
    def search_archived_content(self, 
                              agent_id: str, 
                              search_text: str,
                              tiers: List[ArchivalTier] = None,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """Search through archived memory content"""
        
        try:
            logger.info(f"Searching archived content for '{search_text}'")
            
            # Get all block IDs for the agent
            all_block_ids = self._get_agent_block_ids(agent_id, tiers)
            
            results = []
            for block_id in all_block_ids[:limit * 2]:  # Get more to filter
                # Restore block
                restored_data = self.restore_memory_block(agent_id, block_id)
                
                if restored_data:
                    # Check if search text matches
                    content_text = f"{restored_data.get('title', '')} {restored_data.get('content', '')}".lower()
                    
                    if search_text.lower() in content_text:
                        # Add relevance score
                        restored_data["relevance_score"] = self._calculate_relevance_score(
                            search_text, restored_data
                        )
                        results.append(restored_data)
            
            # Sort by relevance
            results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            logger.info(f"Search completed: {len(results)} matches found")
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Failed to search archived content: {e}")
            return []
    
    def manage_archival_tiers(self) -> Dict[str, int]:
        """Manage archival tiers based on access patterns"""
        
        logger.info("Managing archival tiers")
        
        results = {
            "blocks_promoted": 0,
            "blocks_demoted": 0,
            "blocks_deleted": 0,
            "tier_movements": {}
        }
        
        # Get all agents
        agent_patterns = self.redis_client.keys("archival:agents:*")
        
        for agent_pattern in agent_patterns:
            agent_id = agent_pattern.split(":")[-1]
            agent_blocks = self._get_agent_block_ids(agent_id)
            
            for block_id in agent_blocks:
                current_tier = self._get_block_tier(agent_id, block_id)
                new_tier = self._determine_optimal_tier(agent_id, block_id)
                
                if current_tier != new_tier:
                    # Move block to new tier
                    success = self._move_to_tier(agent_id, block_id, new_tier)
                    
                    if success:
                        if ArchivalTier(current_tier).value in ["hot", "warm"] and new_tier in ["cold", "frozen"]:
                            results["blocks_demoted"] += 1
                        elif current_tier in ["cold", "frozen"] and new_tier in ["hot", "warm"]:
                            results["blocks_promoted"] += 1
                        
                        movement_key = f"{current_tier}->{new_tier}"
                        results["tier_movements"][movement_key] = results["tier_movements"].get(movement_key, 0) + 1
        
        # Delete expired blocks
        expired_count = self._delete_expired_blocks()
        results["blocks_deleted"] = expired_count
        
        logger.info(f"Tier management completed: {results}")
        return results
    
    def get_archival_stats(self, agent_id: str = None) -> ArchivalStats:
        """Get archival storage statistics"""
        
        try:
            # Get all block IDs
            if agent_id:
                all_block_ids = self._get_agent_block_ids(agent_id)
            else:
                # Get all blocks across all agents
                all_block_ids = []
                agent_patterns = self.redis_client.keys("archival:agents:*")
                for agent_pattern in agent_patterns:
                    agent = agent_pattern.split(":")[-1]
                    all_block_ids.extend(self._get_agent_block_ids(agent))
            
            total_blocks = len(all_block_ids)
            total_size = 0
            compressed_size = 0
            tier_distribution = {tier: 0 for tier in ArchivalTier}
            oldest_block = None
            newest_block = None
            total_access_count = 0
            
            for block_id in all_block_ids:
                # Get metadata for this block
                agent_id_for_block = agent_id or self._get_block_agent(block_id)
                metadata_key = f"archival:metadata:{agent_id_for_block}:{block_id}"
                metadata_json = self.redis_client.get(metadata_key)
                
                if metadata_json:
                    metadata = ArchivalMetadata(**json.loads(metadata_json))
                    
                    total_size += metadata.original_size
                    compressed_size += metadata.compressed_size
                    tier_distribution[metadata.tier] += 1
                    total_access_count += metadata.access_count
                    
                    # Track time range
                    if oldest_block is None or metadata.created_at < oldest_block:
                        oldest_block = metadata.created_at
                    if newest_block is None or metadata.created_at > newest_block:
                        newest_block = metadata.created_at
            
            compression_ratio = total_size / compressed_size if compressed_size > 0 else 1.0
            avg_access_frequency = total_access_count / total_blocks if total_blocks > 0 else 0.0
            
            return ArchivalStats(
                total_blocks=total_blocks,
                total_size_bytes=total_size,
                compressed_size_bytes=compressed_size,
                compression_ratio=compression_ratio,
                tier_distribution=tier_distribution,
                oldest_block=oldest_block,
                newest_block=newest_block,
                avg_access_frequency=avg_access_frequency
            )
            
        except Exception as e:
            logger.error(f"Failed to get archival stats: {e}")
            return ArchivalStats(0, 0, 0, 1.0, {}, None, None, 0.0)
    
    def cleanup_expired_blocks(self) -> int:
        """Clean up expired blocks from all tiers"""
        
        logger.info("Cleaning up expired blocks")
        deleted_count = 0
        
        try:
            for tier in ArchivalTier:
                expiry_time = self.tier_expiry[tier]
                cutoff_date = datetime.now() - expiry_time
                
                # Find expired blocks in this tier
                expired_pattern = f"archival:tier:{tier.value}:*"
                expired_keys = self.redis_client.keys(expired_pattern)
                
                for key in expired_keys:
                    block_id = key.split(":")[-1]
                    agent_id = self._get_block_agent(block_id)
                    
                    # Check if block should be deleted
                    metadata_key = f"archival:metadata:{agent_id}:{block_id}"
                    metadata_json = self.redis_client.get(metadata_key)
                    
                    if metadata_json:
                        metadata = ArchivalMetadata(**json.loads(metadata_json))
                        
                        if metadata.archived_at < cutoff_date:
                            # Delete the block
                            self._delete_archived_block(agent_id, block_id)
                            deleted_count += 1
            
            logger.info(f"Cleanup completed: {deleted_count} expired blocks deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired blocks: {e}")
            return 0
    
    def export_archival_data(self, 
                           agent_id: str, 
                           output_path: str,
                           include_compressed: bool = True) -> bool:
        """Export archival data to file"""
        
        try:
            logger.info(f"Exporting archival data for agent {agent_id}")
            
            # Get all block IDs for the agent
            block_ids = self._get_agent_block_ids(agent_id)
            
            export_data = {
                "agent_id": agent_id,
                "export_timestamp": datetime.now().isoformat(),
                "total_blocks": len(block_ids),
                "blocks": []
            }
            
            for block_id in block_ids:
                # Restore block data
                restored_data = self.restore_memory_block(agent_id, block_id)
                
                if restored_data:
                    # Add archival metadata
                    metadata_key = f"archival:metadata:{agent_id}:{block_id}"
                    metadata_json = self.redis_client.get(metadata_key)
                    
                    if metadata_json:
                        archival_metadata = ArchivalMetadata(**json.loads(metadata_json))
                        restored_data["archival_metadata"] = asdict(archival_metadata)
                    
                    export_data["blocks"].append(restored_data)
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported {len(export_data['blocks'])} blocks to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export archival data: {e}")
            return False
    
    def import_archival_data(self, 
                           input_path: str, 
                           agent_id: str = None,
                           overwrite_existing: bool = False) -> bool:
        """Import archival data from file"""
        
        try:
            logger.info(f"Importing archival data from {input_path}")
            
            with open(input_path, 'r') as f:
                import_data = json.load(f)
            
            imported_agent_id = agent_id or import_data.get("agent_id")
            imported_blocks = import_data.get("blocks", [])
            
            imported_count = 0
            
            for block_data in imported_blocks:
                block_id = block_data.get("block_id")
                if not block_id:
                    continue
                
                # Check if block already exists
                if not overwrite_existing:
                    existing_metadata_key = f"archival:metadata:{imported_agent_id}:{block_id}"
                    if self.redis_client.exists(existing_metadata_key):
                        logger.warning(f"Block {block_id} already exists, skipping")
                        continue
                
                # Extract archival metadata if present
                archival_metadata = block_data.pop("archival_metadata", None)
                
                # Archive the block
                success = self.archive_memory_block(
                    imported_agent_id, 
                    block_id, 
                    block_data
                )
                
                if success and archival_metadata:
                    # Update with original archival metadata
                    metadata_key = f"archival:metadata:{imported_agent_id}:{block_id}"
                    self.redis_client.set(
                        metadata_key,
                        json.dumps(archival_metadata, default=str)
                    )
                    imported_count += 1
            
            logger.info(f"Imported {imported_count} blocks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import archival data: {e}")
            return False
    
    # Internal methods
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for data integrity"""
        import hashlib
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _compress_data(self, data: Dict[str, Any]) -> Tuple[bytes, CompressionType]:
        """Compress data for storage"""
        json_data = json.dumps(data, default=str).encode('utf-8')
        
        # Use gzip for compression
        compressed_data = gzip.compress(json_data)
        
        # Check if compression is beneficial
        if len(compressed_data) >= len(json_data):
            return json_data, CompressionType.NONE
        else:
            return compressed_data, CompressionType.GZIP
    
    def _decompress_data(self, compressed_data: bytes, compression_type: CompressionType) -> Dict[str, Any]:
        """Decompress data from storage"""
        if compression_type == CompressionType.NONE:
            return json.loads(compressed_data.decode('utf-8'))
        elif compression_type == CompressionType.GZIP:
            decompressed_data = gzip.decompress(compressed_data)
            return json.loads(decompressed_data.decode('utf-8'))
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
    
    def _store_archived_block(self, 
                            agent_id: str, 
                            block_id: str, 
                            data: bytes, 
                            metadata: ArchivalMetadata):
        """Store archived block in Redis"""
        
        # Data storage key
        data_key = f"archival:data:{agent_id}:{block_id}"
        
        # Metadata storage key
        metadata_key = f"archival:metadata:{agent_id}:{block_id}"
        
        # Tier index key
        tier_key = f"archival:tier:{metadata.tier.value}:{agent_id}:{block_id}"
        
        # Agent index key
        agent_key = f"archival:agents:{agent_id}"
        
        # Store data with TTL based on tier
        ttl = int(self.tier_expiry[metadata.tier].total_seconds())
        
        pipeline = self.redis_client.pipeline()
        pipeline.set(data_key, data, ex=ttl)
        pipeline.set(metadata_key, json.dumps(asdict(metadata), default=str), ex=ttl)
        pipeline.set(tier_key, "1", ex=ttl)
        pipeline.sadd(agent_key, block_id)
        pipeline.execute()
    
    def _update_tier_index(self, agent_id: str, block_id: str, tier: ArchivalTier):
        """Update tier index for block"""
        
        # Remove from old tier index
        for old_tier in ArchivalTier:
            old_key = f"archival:tier:{old_tier.value}:{agent_id}:{block_id}"
            self.redis_client.delete(old_key)
        
        # Add to new tier index
        new_key = f"archival:tier:{tier.value}:{agent_id}:{block_id}"
        ttl = int(self.tier_expiry[tier].total_seconds())
        self.redis_client.set(new_key, "1", ex=ttl)
    
    def _update_access_stats(self, agent_id: str, block_id: str, metadata: ArchivalMetadata):
        """Update access statistics for archived block"""
        
        metadata.last_accessed = datetime.now()
        metadata.access_count += 1
        
        # Update metadata in Redis
        metadata_key = f"archival:metadata:{agent_id}:{block_id}"
        self.redis_client.set(
            metadata_key,
            json.dumps(asdict(metadata), default=str)
        )
    
    def _find_matching_blocks(self, query: ArchivalQuery) -> List[str]:
        """Find block IDs matching the query criteria"""
        
        # Get base block list
        if query.agent_id:
            block_ids = self._get_agent_block_ids(query.agent_id, query.tiers)
        else:
            # Get all blocks
            block_ids = []
            agent_patterns = self.redis_client.keys("archival:agents:*")
            for agent_pattern in agent_patterns:
                agent_id = agent_pattern.split(":")[-1]
                agent_blocks = self._get_agent_block_ids(agent_id, query.tiers)
                block_ids.extend(agent_blocks)
        
        # Apply time range filter
        if query.time_range:
            filtered_ids = []
            for block_id in block_ids:
                agent_id = self._get_block_agent(block_id)
                metadata_key = f"archival:metadata:{agent_id}:{block_id}"
                metadata_json = self.redis_client.get(metadata_key)
                
                if metadata_json:
                    metadata = ArchivalMetadata(**json.loads(metadata_json))
                    if query.time_range[0] <= metadata.created_at <= query.time_range[1]:
                        filtered_ids.append(block_id)
            block_ids = filtered_ids
        
        # Apply tier filter
        if query.tiers:
            filtered_ids = []
            for block_id in block_ids:
                current_tier = self._get_block_tier(self._get_block_agent(block_id), block_id)
                if current_tier in [t.value for t in query.tiers]:
                    filtered_ids.append(block_id)
            block_ids = filtered_ids
        
        return block_ids
    
    def _get_agent_block_ids(self, agent_id: str, tiers: List[ArchivalTier] = None) -> List[str]:
        """Get all block IDs for an agent"""
        
        agent_key = f"archival:agents:{agent_id}"
        all_block_ids = self.redis_client.smembers(agent_key)
        all_block_ids = [bid.decode('utf-8') if isinstance(bid, bytes) else bid for bid in all_block_ids]
        
        # Filter by tiers if specified
        if tiers:
            tier_block_ids = set()
            for tier in tiers:
                pattern = f"archival:tier:{tier.value}:{agent_id}:*"
                tier_keys = self.redis_client.keys(pattern)
                tier_block_ids.update(key.split(":")[-1] for key in tier_keys)
            
            all_block_ids = [bid for bid in all_block_ids if bid in tier_block_ids]
        
        return all_block_ids
    
    def _get_block_tier(self, agent_id: str, block_id: str) -> str:
        """Get the current tier of a block"""
        
        for tier in ArchivalTier:
            key = f"archival:tier:{tier.value}:{agent_id}:{block_id}"
            if self.redis_client.exists(key):
                return tier.value
        
        return ArchivalTier.WARM.value  # Default tier
    
    def _get_block_agent(self, block_id: str) -> str:
        """Get the agent ID for a block (fallback)"""
        # This is a fallback - in practice, we'd want to store this more efficiently
        # For now, we'll try common patterns
        for tier in ArchivalTier:
            pattern = f"archival:tier:{tier.value}:*:{block_id}"
            keys = self.redis_client.keys(pattern)
            if keys:
                return keys[0].decode('utf-8').split(":")[3]
        
        return "unknown"
    
    def _determine_optimal_tier(self, agent_id: str, block_id: str) -> str:
        """Determine the optimal tier for a block based on access patterns"""
        
        metadata_key = f"archival:metadata:{agent_id}:{block_id}"
        metadata_json = self.redis_client.get(metadata_key)
        
        if not metadata_json:
            return ArchivalTier.WARM.value
        
        metadata = ArchivalMetadata(**json.loads(metadata_json))
        
        # Determine tier based on access frequency and age
        days_since_archived = (datetime.now() - metadata.archived_at).days
        access_frequency = metadata.access_count / max(1, days_since_archived)
        
        if access_frequency > 0.1 or days_since_archived < 7:
            return ArchivalTier.HOT.value
        elif access_frequency > 0.01 or days_since_archived < 30:
            return ArchivalTier.WARM.value
        elif access_frequency > 0.001 or days_since_archived < 90:
            return ArchivalTier.COLD.value
        else:
            return ArchivalTier.FROZEN.value
    
    def _move_to_tier(self, agent_id: str, block_id: str, new_tier: str) -> bool:
        """Move a block to a different tier"""
        
        try:
            # Get current data and metadata
            data_key = f"archival:data:{agent_id}:{block_id}"
            compressed_data = self.redis_client.get(data_key)
            
            if not compressed_data:
                return False
            
            metadata_key = f"archival:metadata:{agent_id}:{block_id}"
            metadata_json = self.redis_client.get(metadata_key)
            
            if not metadata_json:
                return False
            
            metadata = ArchivalMetadata(**json.loads(metadata_json))
            metadata.tier = ArchivalTier(new_tier)
            
            # Remove from old tier index
            self._update_tier_index(agent_id, block_id, ArchivalTier(new_tier))
            
            # Update TTL for new tier
            ttl = int(self.tier_expiry[ArchivalTier(new_tier)].total_seconds())
            
            # Update metadata with new tier
            self.redis_client.expire(data_key, ttl)
            self.redis_client.expire(metadata_key, ttl)
            
            logger.debug(f"Moved block {block_id} to tier {new_tier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move block {block_id} to tier {new_tier}: {e}")
            return False
    
    def _delete_archived_block(self, agent_id: str, block_id: str):
        """Delete an archived block completely"""
        
        # Delete all related keys
        keys_to_delete = [
            f"archival:data:{agent_id}:{block_id}",
            f"archival:metadata:{agent_id}:{block_id}",
            f"archival:agents:{agent_id}",
        ]
        
        # Add tier index keys
        for tier in ArchivalTier:
            keys_to_delete.append(f"archival:tier:{tier.value}:{agent_id}:{block_id}")
        
        pipeline = self.redis_client.pipeline()
        for key in keys_to_delete:
            pipeline.delete(key)
        pipeline.srem(f"archival:agents:{agent_id}", block_id)
        pipeline.execute()
    
    def _delete_expired_blocks(self) -> int:
        """Delete blocks that have exceeded their TTL"""
        
        deleted_count = 0
        
        # Get all data keys
        data_pattern = "archival:data:*"
        data_keys = self.redis_client.keys(data_pattern)
        
        for data_key in data_keys:
            if not self.redis_client.exists(data_key):
                # Block has expired, clean up related keys
                parts = data_key.decode('utf-8').split(":")
                agent_id = parts[2]
                block_id = parts[3]
                
                self._delete_archived_block(agent_id, block_id)
                deleted_count += 1
        
        return deleted_count
    
    def _calculate_relevance_score(self, search_text: str, block_data: Dict[str, Any]) -> float:
        """Calculate relevance score for search results"""
        
        score = 0.0
        search_words = search_text.lower().split()
        
        # Title match (higher weight)
        title = block_data.get("title", "").lower()
        for word in search_words:
            if word in title:
                score += 2.0
        
        # Content match (medium weight)
        content = str(block_data.get("content", "")).lower()
        for word in search_words:
            score += content.count(word) * 0.5
        
        # Metadata match (lower weight)
        metadata = block_data.get("metadata", {})
        metadata_text = f"{metadata.get('title', '')} {' '.join(metadata.get('tags', []))}".lower()
        
        for word in search_words:
            score += metadata_text.count(word) * 0.1
        
        return min(score, 10.0)  # Cap the score
    
    # Background worker methods
    
    def _archival_worker(self):
        """Background worker for processing archival queue"""
        
        while self.running:
            try:
                if self.archival_queue:
                    # Process next item in queue
                    job = self.archival_queue.pop(0)
                    
                    agent_id, block_id, data, tier = job
                    self.archive_memory_block(agent_id, block_id, data, tier)
                
                time.sleep(1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Archival worker error: {e}")
                time.sleep(5)
    
    def _tier_management_worker(self):
        """Background worker for managing archival tiers"""
        
        while self.running:
            try:
                # Run tier management every hour
                self.manage_archival_tiers()
                
                # Wait 1 hour
                for _ in range(3600):  # 1 hour in seconds
                    if not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"Tier management worker error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _stats_worker(self):
        """Background worker for updating statistics"""
        
        while self.running:
            try:
                # Update statistics every 5 minutes
                if hasattr(self, 'stats_last_update'):
                    time_since_update = time.time() - self.stats_last_update
                    if time_since_update < 300:  # 5 minutes
                        time.sleep(30)
                        continue
                
                # Update stats (could be expanded to send to monitoring systems)
                logger.info(f"Archival stats: {self.stats}")
                self.stats_last_update = time.time()
                
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Stats worker error: {e}")
                time.sleep(300)