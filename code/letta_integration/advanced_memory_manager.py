#!/usr/bin/env python3
"""
Advanced Memory Block Management System for Trading Agents
Provides sophisticated memory management for trading patterns and market learning
"""

import json
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryBlockType(Enum):
    """Types of memory blocks for trading agents"""
    TRADING_STRATEGY = "trading_strategy"
    MARKET_CONDITIONS = "market_conditions"
    RISK_PARAMETERS = "risk_parameters"
    LEARNED_PATTERNS = "learned_patterns"
    PERFORMANCE_METRICS = "performance_metrics"
    MARKET_ANALYSIS = "market_analysis"
    TRADE_OUTCOMES = "trade_outcomes"
    RISK_EVENTS = "risk_events"
    STRATEGY_EVOLUTION = "strategy_evolution"
    MARKET_REGIME = "market_regime"
    CORRELATION_MATRICES = "correlation_matrices"
    VOLATILITY_CLUSTERS = "volatility_clusters"
    LIQUIDITY_PATTERNS = "liquidity_patterns"
    SENTIMENT_INDICATORS = "sentiment_indicators"
    SYSTEM_CONTEXT = "system_context"
    RECENT_ACTIVITY = "recent_activity"
    SCRATCH_MEMORY = "scratch_memory"
    LONG_TERM = "long_term"


class MemoryPriority(Enum):
    """Priority levels for memory blocks"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    ARCHIVE = 5


class MemoryRetentionPolicy(Enum):
    """Retention policies for memory blocks"""
    PERMANENT = "permanent"
    LONG_TERM = "long_term"  # 90 days
    MEDIUM_TERM = "medium_term"  # 30 days
    SHORT_TERM = "short_term"  # 7 days
    TEMPORARY = "temporary"  # 1 day


@dataclass
class MemoryMetadata:
    """Enhanced metadata for memory blocks"""
    created_at: datetime
    last_accessed: datetime
    access_count: int
    priority: MemoryPriority
    retention_policy: MemoryRetentionPolicy
    confidence_score: float
    source_agent: str
    related_blocks: List[str]
    tags: List[str]
    data_type: str  # json, text, numeric, etc.
    compression_ratio: float
    checksum: str
    version: int = 1


@dataclass
class TradingPattern:
    """Structured representation of trading patterns"""
    pattern_id: str
    symbol: str
    timeframe: str
    pattern_type: str  # bullish, bearish, neutral, complex
    success_rate: float
    confidence: float
    conditions: Dict[str, Any]
    entry_signals: List[str]
    exit_signals: List[str]
    risk_metrics: Dict[str, float]
    performance_history: List[Dict[str, Any]]
    last_validated: datetime


@dataclass
class MarketLearning:
    """Market learning and adaptation data"""
    learning_id: str
    market_regime: str
    adaptation_type: str  # strategy, risk, timing, etc.
    changes_made: Dict[str, Any]
    performance_impact: float
    confidence: float
    rollback_data: Dict[str, Any]


@dataclass
class PerformanceInsight:
    """Performance insights and analytics"""
    insight_id: str
    insight_type: str  # pattern_recognition, risk_awareness, strategy_gap
    title: str
    description: str
    data: Dict[str, Any]
    recommendations: List[str]
    urgency: str
    related_strategies: List[str]


class MemoryBlock:
    """Enhanced memory block with trading-specific features"""
    
    def __init__(self, 
                 block_id: str,
                 block_type: MemoryBlockType,
                 title: str,
                 content: Any,
                 metadata: MemoryMetadata,
                 trading_data: Optional[Dict[str, Any]] = None):
        self.block_id = block_id
        self.block_type = block_type
        self.title = title
        self.content = content
        self.metadata = metadata
        self.trading_data = trading_data or {}
        self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate content checksum for integrity verification"""
        content_str = str(self.content)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]
    
    def validate_integrity(self) -> bool:
        """Validate memory block integrity"""
        return self.checksum == self._calculate_checksum()
    
    def update_last_accessed(self):
        """Update last accessed timestamp"""
        self.metadata.last_accessed = datetime.now()
        self.metadata.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "block_id": self.block_id,
            "block_type": self.block_type.value,
            "title": self.title,
            "content": self.content,
            "metadata": asdict(self.metadata),
            "trading_data": self.trading_data,
            "checksum": self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryBlock':
        """Create from dictionary"""
        metadata = MemoryMetadata(**data["metadata"])
        return cls(
            block_id=data["block_id"],
            block_type=MemoryBlockType(data["block_type"]),
            title=data["title"],
            content=data["content"],
            metadata=metadata,
            trading_data=data.get("trading_data", {})
        )


class AdvancedMemoryManager:
    """Advanced memory management system for trading agents"""
    
    def __init__(self, base_client, redis_client=None):
        self.base_client = base_client
        self.redis_client = redis_client
        self.memory_cache = {}  # In-memory cache for frequently accessed blocks
        self.pattern_index = {}  # Index for pattern-based searches
        self.performance_tracker = {}  # Track memory usage patterns
        
        # Memory management rules
        self.max_cache_size = 1000  # Maximum blocks in cache
        self.archive_threshold = 10000  # When to move to Redis
        self.compression_enabled = True
        
        # Load persisted memory structures
        self._load_memory_structures()
    
    def create_memory_block(self, 
                          agent_id: str,
                          block_type: MemoryBlockType,
                          title: str,
                          content: Any,
                          priority: MemoryPriority = MemoryPriority.MEDIUM,
                          retention_policy: MemoryRetentionPolicy = MemoryRetentionPolicy.MEDIUM_TERM,
                          tags: List[str] = None,
                          trading_data: Dict[str, Any] = None) -> str:
        """Create a new memory block with enhanced metadata"""
        
        block_id = self._generate_block_id(agent_id, block_type, title)
        
        # Create enhanced metadata
        metadata = MemoryMetadata(
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=1,
            priority=priority,
            retention_policy=retention_policy,
            confidence_score=0.8,  # Default confidence
            source_agent=agent_id,
            related_blocks=[],
            tags=tags or [],
            data_type=type(content).__name__,
            compression_ratio=1.0,
            checksum=""
        )
        
        # Create memory block
        memory_block = MemoryBlock(
            block_id=block_id,
            block_type=block_type,
            title=title,
            content=content,
            metadata=metadata,
            trading_data=trading_data
        )
        
        # Store in cache initially
        self._cache_block(memory_block)
        
        # Persist to database
        result = self._persist_block(memory_block)
        
        if result.get("success"):
            logger.info(f"Created memory block {block_id} for agent {agent_id}")
            return block_id
        else:
            logger.error(f"Failed to create memory block {block_id}: {result.get('error')}")
            return None
    
    def _generate_block_id(self, agent_id: str, block_type: MemoryBlockType, title: str) -> str:
        """Generate unique block ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_hash = hashlib.md5(f"{title}_{block_type.value}".encode()).hexdigest()[:8]
        return f"{agent_id}_{block_type.value}_{timestamp}_{content_hash}"
    
    def _cache_block(self, memory_block: MemoryBlock):
        """Cache memory block for fast access"""
        if len(self.memory_cache) >= self.max_cache_size:
            self._evict_cache()
        
        self.memory_cache[memory_block.block_id] = memory_block
        self._update_pattern_index(memory_block)
    
    def _persist_block(self, memory_block: MemoryBlock) -> Dict[str, Any]:
        """Persist memory block to database and optionally Redis"""
        try:
            # Convert to Letta format
            letta_block = {
                "block_type": memory_block.block_type.value,
                "title": memory_block.title,
                "content": json.dumps(memory_block.content) if not isinstance(memory_block.content, str) else memory_block.content,
                "value_type": memory_block.metadata.data_type,
                "metadata": {
                    "memory_block_id": memory_block.block_id,
                    "priority": memory_block.metadata.priority.value,
                    "retention_policy": memory_block.metadata.retention_policy.value,
                    "confidence_score": memory_block.metadata.confidence_score,
                    "source_agent": memory_block.metadata.source_agent,
                    "tags": memory_block.metadata.tags,
                    "trading_data": memory_block.trading_data,
                    "checksum": memory_block.checksum,
                    "created_at": memory_block.metadata.created_at.isoformat(),
                    "last_accessed": memory_block.metadata.last_accessed.isoformat(),
                    "access_count": memory_block.metadata.access_count
                }
            }
            
            # Persist to Letta database
            result = self.base_client.add_memory_block(memory_block.metadata.source_agent, letta_block)
            
            # Archive to Redis if needed
            if len(self.memory_cache) > self.archive_threshold and self.redis_client:
                self._archive_to_redis(memory_block)
            
            return {"success": True, "block_id": memory_block.block_id}
            
        except Exception as e:
            logger.error(f"Error persisting memory block: {e}")
            return {"success": False, "error": str(e)}
    
    def get_memory_block(self, agent_id: str, block_id: str) -> Optional[MemoryBlock]:
        """Retrieve memory block by ID"""
        # Check cache first
        if block_id in self.memory_cache:
            block = self.memory_cache[block_id]
            block.update_last_accessed()
            return block
        
        # Retrieve from database
        try:
            # Get from Letta
            memory_data = self.base_client.get_agent_memory(agent_id)
            
            for block_data in memory_data.get("blocks", []):
                if block_data.get("metadata", {}).get("memory_block_id") == block_id:
                    # Reconstruct MemoryBlock object
                    memory_block = self._reconstruct_block(block_data)
                    if memory_block:
                        self._cache_block(memory_block)
                        memory_block.update_last_accessed()
                        return memory_block
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving memory block {block_id}: {e}")
            return None
    
    def search_memory_blocks(self, 
                           agent_id: str,
                           query: str = None,
                           block_type: MemoryBlockType = None,
                           priority: MemoryPriority = None,
                           tags: List[str] = None,
                           date_range: Tuple[datetime, datetime] = None,
                           limit: int = 50) -> List[MemoryBlock]:
        """Advanced memory search with multiple filters"""
        
        # Use Letta search API for initial filtering
        all_blocks = self._get_all_agent_blocks(agent_id)
        filtered_blocks = []
        
        for block_data in all_blocks:
            memory_block = self._reconstruct_block(block_data)
            if not memory_block:
                continue
            
            # Apply filters
            if block_type and memory_block.block_type != block_type:
                continue
            
            if priority and memory_block.metadata.priority != priority:
                continue
            
            if tags and not any(tag in memory_block.metadata.tags for tag in tags):
                continue
            
            if date_range:
                created_at = memory_block.metadata.created_at
                if not (date_range[0] <= created_at <= date_range[1]):
                    continue
            
            if query:
                # Text search in title, content, and tags
                search_text = f"{memory_block.title} {str(memory_block.content)} {' '.join(memory_block.metadata.tags)}"
                if query.lower() not in search_text.lower():
                    continue
            
            filtered_blocks.append(memory_block)
        
        # Sort by priority and recency
        filtered_blocks.sort(key=lambda x: (x.metadata.priority.value, -x.metadata.access_count))
        
        return filtered_blocks[:limit]
    
    def update_memory_block(self, 
                          agent_id: str, 
                          block_id: str, 
                          content: Any = None,
                          metadata_updates: Dict[str, Any] = None) -> bool:
        """Update existing memory block"""
        
        memory_block = self.get_memory_block(agent_id, block_id)
        if not memory_block:
            logger.error(f"Memory block {block_id} not found")
            return False
        
        # Update content
        if content is not None:
            memory_block.content = content
            memory_block.metadata.checksum = memory_block._calculate_checksum()
        
        # Update metadata
        if metadata_updates:
            for key, value in metadata_updates.items():
                if hasattr(memory_block.metadata, key):
                    setattr(memory_block.metadata, key, value)
        
        memory_block.metadata.last_accessed = datetime.now()
        
        # Persist changes
        return self._persist_block(memory_block).get("success", False)
    
    def delete_memory_block(self, agent_id: str, block_id: str) -> bool:
        """Delete memory block"""
        try:
            # Remove from cache
            if block_id in self.memory_cache:
                del self.memory_cache[block_id]
            
            # Remove from database
            result = self.base_client.delete_memory_block(agent_id, block_id)
            
            # Remove from Redis if exists
            if self.redis_client:
                redis_key = f"memory:block:{block_id}"
                self.redis_client.delete(redis_key)
            
            logger.info(f"Deleted memory block {block_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting memory block {block_id}: {e}")
            return False
    
    def create_trading_pattern(self, 
                             agent_id: str,
                             pattern: TradingPattern) -> str:
        """Create a structured trading pattern memory block"""
        
        content = {
            "pattern_id": pattern.pattern_id,
            "symbol": pattern.symbol,
            "timeframe": pattern.timeframe,
            "pattern_type": pattern.pattern_type,
            "success_rate": pattern.success_rate,
            "confidence": pattern.confidence,
            "conditions": pattern.conditions,
            "entry_signals": pattern.entry_signals,
            "exit_signals": pattern.exit_signals,
            "risk_metrics": pattern.risk_metrics,
            "performance_history": pattern.performance_history,
            "last_validated": pattern.last_validated.isoformat()
        }
        
        return self.create_memory_block(
            agent_id=agent_id,
            block_type=MemoryBlockType.LEARNED_PATTERNS,
            title=f"Pattern: {pattern.pattern_type} - {pattern.symbol}",
            content=content,
            priority=MemoryPriority.HIGH,
            retention_policy=MemoryRetentionPolicy.LONG_TERM,
            tags=["trading_pattern", pattern.pattern_type, pattern.symbol],
            trading_data={"pattern": "structured", "success_rate": pattern.success_rate}
        )
    
    def create_market_learning(self, 
                             agent_id: str,
                             learning: MarketLearning) -> str:
        """Create market learning and adaptation memory block"""
        
        content = {
            "learning_id": learning.learning_id,
            "market_regime": learning.market_regime,
            "adaptation_type": learning.adaptation_type,
            "changes_made": learning.changes_made,
            "performance_impact": learning.performance_impact,
            "confidence": learning.confidence,
            "rollback_data": learning.rollback_data
        }
        
        return self.create_memory_block(
            agent_id=agent_id,
            block_type=MemoryBlockType.STRATEGY_EVOLUTION,
            title=f"Learning: {learning.adaptation_type} - {learning.market_regime}",
            content=content,
            priority=MemoryPriority.MEDIUM,
            retention_policy=MemoryRetentionPolicy.MEDIUM_TERM,
            tags=["market_learning", learning.adaptation_type, learning.market_regime],
            trading_data={"learning": "adaptive", "impact": learning.performance_impact}
        )
    
    def get_performance_insights(self, agent_id: str) -> List[PerformanceInsight]:
        """Extract performance insights from memory blocks"""
        
        insights = []
        blocks = self._get_all_agent_blocks(agent_id)
        
        for block_data in blocks:
            memory_block = self._reconstruct_block(block_data)
            if not memory_block:
                continue
            
            # Extract insights from different block types
            if memory_block.block_type == MemoryBlockType.PERFORMANCE_METRICS:
                insight = self._analyze_performance_metrics(memory_block)
                if insight:
                    insights.append(insight)
            
            elif memory_block.block_type == MemoryBlockType.TRADE_OUTCOMES:
                insights.extend(self._analyze_trade_outcomes(memory_block))
            
            elif memory_block.block_type == MemoryBlockType.LEARNED_PATTERNS:
                insight = self._analyze_pattern_performance(memory_block)
                if insight:
                    insights.append(insight)
        
        # Sort by urgency and confidence
        insights.sort(key=lambda x: (x.urgency, x.data.get("confidence", 0)), reverse=True)
        
        return insights
    
    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage by cleaning up old blocks and compressing"""
        
        stats = {
            "blocks_processed": 0,
            "blocks_deleted": 0,
            "blocks_archived": 0,
            "blocks_compressed": 0,
            "cache_size_before": len(self.memory_cache),
            "cache_size_after": 0
        }
        
        # Clean up expired blocks
        current_time = datetime.now()
        
        for block_id, memory_block in list(self.memory_cache.items()):
            stats["blocks_processed"] += 1
            
            # Check retention policy
            age_days = (current_time - memory_block.metadata.created_at).days
            
            if self._should_expire(memory_block, age_days):
                # Delete from cache and database
                self.delete_memory_block(memory_block.metadata.source_agent, block_id)
                stats["blocks_deleted"] += 1
            
            elif age_days > 30:  # Archive older blocks
                if self.redis_client:
                    self._archive_to_redis(memory_block)
                    stats["blocks_archived"] += 1
            
            # Compress if beneficial
            if self.compression_enabled and memory_block.metadata.compression_ratio > 1.5:
                self._compress_block(memory_block)
                stats["blocks_compressed"] += 1
        
        stats["cache_size_after"] = len(self.memory_cache)
        
        logger.info(f"Memory optimization completed: {stats}")
        return stats
    
    def export_memory(self, agent_id: str, output_path: str) -> bool:
        """Export agent memory to file for backup"""
        
        try:
            all_blocks = self._get_all_agent_blocks(agent_id)
            
            export_data = {
                "agent_id": agent_id,
                "export_timestamp": datetime.now().isoformat(),
                "total_blocks": len(all_blocks),
                "blocks": []
            }
            
            for block_data in all_blocks:
                memory_block = self._reconstruct_block(block_data)
                if memory_block:
                    export_data["blocks"].append(memory_block.to_dict())
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Exported {len(export_data['blocks'])} memory blocks to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting memory: {e}")
            return False
    
    def import_memory(self, agent_id: str, input_path: str) -> bool:
        """Import agent memory from file"""
        
        try:
            with open(input_path, 'r') as f:
                import_data = json.load(f)
            
            imported_count = 0
            
            for block_data in import_data["blocks"]:
                memory_block = MemoryBlock.from_dict(block_data)
                
                # Override agent ID for safety
                memory_block.metadata.source_agent = agent_id
                memory_block.metadata.last_accessed = datetime.now()
                
                # Store the block
                if self._persist_block(memory_block).get("success"):
                    imported_count += 1
            
            logger.info(f"Imported {imported_count} memory blocks from {input_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error importing memory: {e}")
            return False
    
    def _reconstruct_block(self, block_data: Dict[str, Any]) -> Optional[MemoryBlock]:
        """Reconstruct MemoryBlock from storage format"""
        try:
            metadata_dict = block_data.get("metadata", {})
            
            # Create metadata
            metadata = MemoryMetadata(
                created_at=datetime.fromisoformat(metadata_dict.get("created_at", datetime.now().isoformat())),
                last_accessed=datetime.fromisoformat(metadata_dict.get("last_accessed", datetime.now().isoformat())),
                access_count=metadata_dict.get("access_count", 0),
                priority=MemoryPriority(metadata_dict.get("priority", MemoryPriority.MEDIUM.value)),
                retention_policy=MemoryRetentionPolicy(metadata_dict.get("retention_policy", MemoryRetentionPolicy.MEDIUM_TERM.value)),
                confidence_score=metadata_dict.get("confidence_score", 0.5),
                source_agent=metadata_dict.get("source_agent", ""),
                related_blocks=metadata_dict.get("related_blocks", []),
                tags=metadata_dict.get("tags", []),
                data_type=block_data.get("value_type", "text"),
                compression_ratio=1.0,
                checksum=metadata_dict.get("checksum", "")
            )
            
            return MemoryBlock(
                block_id=metadata_dict.get("memory_block_id", ""),
                block_type=MemoryBlockType(block_data.get("block_type", "")),
                title=block_data.get("title", ""),
                content=self._parse_content(block_data.get("content", ""), block_data.get("value_type", "text")),
                metadata=metadata,
                trading_data=metadata_dict.get("trading_data", {})
            )
            
        except Exception as e:
            logger.error(f"Error reconstructing block: {e}")
            return None
    
    def _parse_content(self, content: str, content_type: str) -> Any:
        """Parse content based on type"""
        if content_type == "json":
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return content
        return content
    
    def _get_all_agent_blocks(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all memory blocks for an agent"""
        try:
            memory_data = self.base_client.get_agent_memory(agent_id)
            return memory_data.get("blocks", [])
        except Exception as e:
            logger.error(f"Error getting agent memory: {e}")
            return []
    
    def _should_expire(self, memory_block: MemoryBlock, age_days: int) -> bool:
        """Check if memory block should expire based on retention policy"""
        policy = memory_block.metadata.retention_policy
        priority = memory_block.metadata.priority
        
        # Critical and high priority blocks never expire
        if priority in [MemoryPriority.CRITICAL, MemoryPriority.HIGH]:
            return False
        
        # Check retention policy
        if policy == MemoryRetentionPolicy.PERMANENT:
            return False
        elif policy == MemoryRetentionPolicy.LONG_TERM:
            return age_days > 90
        elif policy == MemoryRetentionPolicy.MEDIUM_TERM:
            return age_days > 30
        elif policy == MemoryRetentionPolicy.SHORT_TERM:
            return age_days > 7
        elif policy == MemoryRetentionPolicy.TEMPORARY:
            return age_days > 1
        
        return False
    
    def _archive_to_redis(self, memory_block: MemoryBlock):
        """Archive memory block to Redis"""
        if not self.redis_client:
            return
        
        try:
            redis_key = f"memory:block:{memory_block.block_id}"
            redis_value = json.dumps(memory_block.to_dict(), default=str)
            
            # Store with TTL based on retention policy
            ttl_map = {
                MemoryRetentionPolicy.PERMANENT: None,
                MemoryRetentionPolicy.LONG_TERM: 90 * 24 * 3600,
                MemoryRetentionPolicy.MEDIUM_TERM: 30 * 24 * 3600,
                MemoryRetentionPolicy.SHORT_TERM: 7 * 24 * 3600,
                MemoryRetentionPolicy.TEMPORARY: 1 * 24 * 3600
            }
            
            ttl = ttl_map.get(memory_block.metadata.retention_policy)
            
            if ttl:
                self.redis_client.setex(redis_key, ttl, redis_value)
            else:
                self.redis_client.set(redis_key, redis_value)
            
            # Remove from cache to save memory
            if memory_block.block_id in self.memory_cache:
                del self.memory_cache[memory_block.block_id]
            
            logger.debug(f"Archived memory block {memory_block.block_id} to Redis")
            
        except Exception as e:
            logger.error(f"Error archiving to Redis: {e}")
    
    def _compress_block(self, memory_block: MemoryBlock):
        """Compress memory block content"""
        try:
            if isinstance(memory_block.content, str) and len(memory_block.content) > 1000:
                # Simple compression by removing extra whitespace
                import re
                compressed_content = re.sub(r'\s+', ' ', memory_block.content)
                memory_block.content = compressed_content
                memory_block.metadata.compression_ratio = len(memory_block.content) / len(compressed_content)
                
                logger.debug(f"Compressed memory block {memory_block.block_id}")
                
        except Exception as e:
            logger.error(f"Error compressing block: {e}")
    
    def _evict_cache(self):
        """Evict least recently used blocks from cache"""
        # Sort by last accessed time
        sorted_blocks = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].metadata.last_accessed
        )
        
        # Remove oldest 10% of blocks
        evict_count = max(1, len(sorted_blocks) // 10)
        for block_id, _ in sorted_blocks[:evict_count]:
            del self.memory_cache[block_id]
    
    def _load_memory_structures(self):
        """Load persisted memory structures"""
        try:
            # Load pattern index if exists
            if self.redis_client:
                pattern_index_data = self.redis_client.get("memory:pattern_index")
                if pattern_index_data:
                    self.pattern_index = json.loads(pattern_index_data)
        except Exception as e:
            logger.error(f"Error loading memory structures: {e}")
    
    def _update_pattern_index(self, memory_block: MemoryBlock):
        """Update pattern index for fast searches"""
        if memory_block.block_type == MemoryBlockType.LEARNED_PATTERNS:
            # Index by pattern type, symbol, and success rate
            if isinstance(memory_block.content, dict):
                pattern_type = memory_block.content.get("pattern_type", "")
                symbol = memory_block.content.get("symbol", "")
                success_rate = memory_block.content.get("success_rate", 0)
                
                if pattern_type not in self.pattern_index:
                    self.pattern_index[pattern_type] = {}
                if symbol not in self.pattern_index[pattern_type]:
                    self.pattern_index[pattern_type][symbol] = []
                
                self.pattern_index[pattern_type][symbol].append({
                    "block_id": memory_block.block_id,
                    "success_rate": success_rate,
                    "confidence": memory_block.metadata.confidence_score
                })
    
    def _analyze_performance_metrics(self, memory_block: MemoryBlock) -> Optional[PerformanceInsight]:
        """Analyze performance metrics for insights"""
        if not isinstance(memory_block.content, dict):
            return None
        
        performance_data = memory_block.content
        
        # Generate insight based on performance metrics
        return PerformanceInsight(
            insight_id=f"perf_{memory_block.block_id}",
            insight_type="performance_analysis",
            title="Performance Metrics Analysis",
            description="Analysis of trading performance metrics",
            data=performance_data,
            recommendations=["Review underperforming strategies", "Optimize risk management"],
            urgency="medium"
        )
    
    def _analyze_trade_outcomes(self, memory_block: MemoryBlock) -> List[PerformanceInsight]:
        """Analyze trade outcomes for patterns"""
        insights = []
        
        if not isinstance(memory_block.content, dict):
            return insights
        
        # Analyze trade patterns
        if "success_rate" in memory_block.content:
            rate = memory_block.content["success_rate"]
            if rate < 0.6:
                insights.append(PerformanceInsight(
                    insight_id=f"trade_{memory_block.block_id}",
                    insight_type="low_success_rate",
                    title="Low Success Rate Detected",
                    description=f"Trade success rate is {rate:.1%}, below threshold",
                    data={"success_rate": rate},
                    recommendations=["Review strategy parameters", "Consider strategy modification"],
                    urgency="high"
                ))
        
        return insights
    
    def _analyze_pattern_performance(self, memory_block: MemoryBlock) -> Optional[PerformanceInsight]:
        """Analyze pattern performance"""
        if not isinstance(memory_block.content, dict):
            return None
        
        pattern_data = memory_block.content
        success_rate = pattern_data.get("success_rate", 0)
        
        if success_rate > 0.8:
            return PerformanceInsight(
                insight_id=f"pattern_{memory_block.block_id}",
                insight_type="high_performance_pattern",
                title="High Performance Pattern Identified",
                description=f"Pattern has {success_rate:.1%} success rate",
                data=pattern_data,
                recommendations=["Consider increasing position size", "Apply to other symbols"],
                urgency="medium"
            )
        
        return None