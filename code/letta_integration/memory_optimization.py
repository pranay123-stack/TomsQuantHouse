#!/usr/bin/env python3
"""
Agent Memory Optimization and Cleanup Routines
Provides intelligent memory management, optimization, and cleanup for agent memory
"""

import json
import time
import threading
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import defaultdict, Counter
import statistics
import heapq
from concurrent.futures import ThreadPoolExecutor

from advanced_memory_manager import (
    AdvancedMemoryManager,
    MemoryBlockType,
    MemoryPriority,
    MemoryRetentionPolicy,
    MemoryBlock
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Memory optimization strategies"""
    LRU_CACHING = "lru_caching"      # Least Recently Used
    LFU_CACHING = "lfu_caching"      # Least Frequently Used
    SIZE_BASED = "size_based"        # Size-based optimization
    FREQUENCY_BASED = "frequency_based"  # Access frequency-based
    TIME_BASED = "time_based"        # Time-based cleanup
    PREDICTIVE = "predictive"        # Predictive optimization
    HYBRID = "hybrid"                # Combination of strategies


class CleanupAction(Enum):
    """Types of cleanup actions"""
    DELETE = "delete"
    ARCHIVE = "archive"
    COMPRESS = "compress"
    MOVE_TO_SLOW_STORAGE = "move_to_slow_storage"
    MERGE_SIMILAR = "merge_similar"
    CONVERT_TYPE = "convert_type"
    INDEX_OPTIMIZE = "index_optimize"
    VALIDATE_INTEGRITY = "validate_integrity"


@dataclass
class MemoryMetrics:
    """Memory usage metrics"""
    total_blocks: int
    total_size_bytes: int
    average_block_size: float
    cache_hit_rate: float
    access_frequency: float
    memory_utilization: float
    fragmentation_ratio: float
    tier_distribution: Dict[str, int]


@dataclass
class OptimizationRule:
    """Rule for memory optimization"""
    rule_id: str
    name: str
    description: str
    strategy: OptimizationStrategy
    conditions: Dict[str, Any]
    actions: List[CleanupAction]
    priority: int
    enabled: bool
    last_executed: Optional[datetime]
    execution_count: int


@dataclass
class CleanupReport:
    """Report of cleanup operations"""
    timestamp: datetime
    strategy: OptimizationStrategy
    blocks_processed: int
    actions_taken: Dict[CleanupAction, int]
    space_freed_bytes: int
    performance_improvement: float
    errors: List[str]
    execution_time_seconds: float


class MemoryAnalyzer:
    """Analyzes memory usage patterns"""
    
    def __init__(self, memory_manager: AdvancedMemoryManager):
        self.memory_manager = memory_manager
        self.access_patterns = defaultdict(list)
        self.size_distribution = defaultdict(int)
        self.age_distribution = defaultdict(int)
        self.frequency_distribution = defaultdict(int)
        self.analysis_cache = {}
    
    def analyze_memory_usage(self, agent_id: str) -> MemoryMetrics:
        """Analyze memory usage for an agent"""
        
        try:
            # Get all memory blocks
            all_blocks = self.memory_manager.search_memory_blocks(agent_id, limit=10000)
            
            total_blocks = len(all_blocks)
            total_size = 0
            access_counts = []
            cache_hits = 0
            cache_total = 0
            
            block_sizes = []
            
            # Analyze each block
            for block in all_blocks:
                # Size analysis
                content_size = len(str(block.content))
                block_sizes.append(content_size)
                total_size += content_size
                
                # Access frequency
                access_counts.append(block.metadata.access_count)
                
                # Cache statistics
                cache_total += 1
                if block.block_id in self.memory_manager.memory_cache:
                    cache_hits += 1
                
                # Age distribution
                age_days = (datetime.now() - block.metadata.created_at).days
                age_bucket = f"{(age_days // 7) * 7}-{(age_days // 7) * 7 + 6}"  # Weekly buckets
                self.age_distribution[age_bucket] += 1
                
                # Size distribution
                if content_size < 1024:
                    size_bucket = "< 1KB"
                elif content_size < 10240:
                    size_bucket = "1-10KB"
                elif content_size < 102400:
                    size_bucket = "10-100KB"
                else:
                    size_bucket = "> 100KB"
                
                self.size_distribution[size_bucket] += 1
                
                # Frequency distribution
                if block.metadata.access_count == 0:
                    freq_bucket = "never"
                elif block.metadata.access_count == 1:
                    freq_bucket = "once"
                elif block.metadata.access_count <= 5:
                    freq_bucket = "2-5 times"
                elif block.metadata.access_count <= 20:
                    freq_bucket = "6-20 times"
                else:
                    freq_bucket = "> 20 times"
                
                self.frequency_distribution[freq_bucket] += 1
                
                # Access pattern analysis
                self.access_patterns[block.block_id].append({
                    "timestamp": block.metadata.last_accessed,
                    "access_count": block.metadata.access_count,
                    "block_type": block.block_type.value,
                    "size": content_size
                })
            
            # Calculate metrics
            avg_block_size = total_size / total_blocks if total_blocks > 0 else 0
            cache_hit_rate = cache_hits / cache_total if cache_total > 0 else 0
            avg_access_frequency = statistics.mean(access_counts) if access_counts else 0
            memory_utilization = total_size / (1024 * 1024 * 100)  # Assuming 100MB total budget
            
            # Calculate fragmentation (simplified)
            unique_types = len(set(block.block_type for block in all_blocks))
            fragmentation_ratio = 1 - (unique_types / len(set(str(b.block_type) for b in all_blocks)))
            
            # Tier distribution
            tier_distribution = {}
            for tier in ["hot", "warm", "cold", "frozen"]:
                # Simplified tier distribution based on access patterns
                if tier == "hot":
                    tier_distribution[tier] = len([b for b in all_blocks if b.metadata.access_count > 10])
                elif tier == "warm":
                    tier_distribution[tier] = len([b for b in all_blocks if 5 < b.metadata.access_count <= 10])
                elif tier == "cold":
                    tier_distribution[tier] = len([b for b in all_blocks if 0 < b.metadata.access_count <= 5])
                else:
                    tier_distribution[tier] = len([b for b in all_blocks if b.metadata.access_count == 0])
            
            return MemoryMetrics(
                total_blocks=total_blocks,
                total_size_bytes=total_size,
                average_block_size=avg_block_size,
                cache_hit_rate=cache_hit_rate,
                access_frequency=avg_access_frequency,
                memory_utilization=memory_utilization,
                fragmentation_ratio=fragmentation_ratio,
                tier_distribution=tier_distribution
            )
            
        except Exception as e:
            logger.error(f"Error analyzing memory usage: {e}")
            return MemoryMetrics(0, 0, 0, 0, 0, 0, 0, {})
    
    def identify_optimization_opportunities(self, agent_id: str) -> List[Dict[str, Any]]:
        """Identify optimization opportunities"""
        
        opportunities = []
        metrics = self.analyze_memory_usage(agent_id)
        
        # Low cache hit rate
        if metrics.cache_hit_rate < 0.7:
            opportunities.append({
                "type": "cache_optimization",
                "description": f"Cache hit rate ({metrics.cache_hit_rate:.2%}) is below optimal threshold",
                "recommendation": "Increase cache size or improve caching strategy",
                "potential_savings": "20-30% performance improvement",
                "priority": "high"
            })
        
        # High memory utilization
        if metrics.memory_utilization > 0.8:
            opportunities.append({
                "type": "memory_pressure",
                "description": f"Memory utilization ({metrics.memory_utilization:.2%}) is high",
                "recommendation": "Implement aggressive cleanup or increase memory allocation",
                "potential_savings": "15-25% memory savings",
                "priority": "high"
            })
        
        # Large number of unaccessed blocks
            unaccessed = metrics.tier_distribution.get("frozen", 0)
            if unaccessed > metrics.total_blocks * 0.5:
                opportunities.append({
                    "type": "inactive_cleanup",
                    "description": f"Large number ({unaccessed}) of unaccessed memory blocks",
                    "recommendation": "Archive or delete inactive blocks",
                    "potential_savings": "30-50% space savings",
                    "priority": "medium"
                })
        
        # High fragmentation
        if metrics.fragmentation_ratio > 0.7:
            opportunities.append({
                "type": "defragmentation",
                "description": f"High memory fragmentation ({metrics.fragmentation_ratio:.2%})",
                "recommendation": "Compact and reorganize memory blocks",
                "potential_savings": "10-20% space efficiency",
                "priority": "medium"
            })
        
        # Large average block size
        if metrics.average_block_size > 10000:  # 10KB
            opportunities.append({
                "type": "compression",
                "description": f"Average block size ({metrics.average_block_size:.0f} bytes) is large",
                "recommendation": "Implement compression for large blocks",
                "potential_savings": "40-60% space savings",
                "priority": "medium"
            })
        
        return opportunities
    
    def predict_memory_pressure(self, agent_id: str, horizon_hours: int = 24) -> Dict[str, Any]:
        """Predict future memory pressure"""
        
        try:
            # Get historical access patterns
            all_blocks = self.memory_manager.search_memory_blocks(agent_id, limit=1000)
            
            current_time = datetime.now()
            predictions = {
                "estimated_growth_rate": 0,
                "projected_memory_usage": 0,
                "pressure_level": "low",
                "recommendations": []
            }
            
            if not all_blocks:
                return predictions
            
            # Calculate growth rate based on creation patterns
            recent_blocks = [b for b in all_blocks 
                           if (current_time - b.metadata.created_at).total_seconds() < 3600]  # Last hour
            
            if recent_blocks:
                hourly_creation_rate = len(recent_blocks)
                predictions["estimated_growth_rate"] = hourly_creation_rate
            
            # Project memory usage
            total_size = sum(len(str(b.content)) for b in all_blocks)
            predicted_size = total_size + (hourly_creation_rate * 10)  # Assume 10 bytes per new block
            
            predictions["projected_memory_usage"] = predicted_size
            
            # Determine pressure level
            memory_budget = 100 * 1024 * 1024  # 100MB budget
            projected_utilization = predicted_size / memory_budget
            
            if projected_utilization > 0.9:
                predictions["pressure_level"] = "critical"
                predictions["recommendations"].append("Implement immediate cleanup")
            elif projected_utilization > 0.7:
                predictions["pressure_level"] = "high"
                predictions["recommendations"].append("Schedule aggressive cleanup")
            elif projected_utilization > 0.5:
                predictions["pressure_level"] = "medium"
                predictions["recommendations"].append("Monitor and plan cleanup")
            else:
                predictions["pressure_level"] = "low"
                predictions["recommendations"].append("Current usage is optimal")
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting memory pressure: {e}")
            return {"estimated_growth_rate": 0, "projected_memory_usage": 0, "pressure_level": "unknown", "recommendations": []}


class MemoryOptimizer:
    """Performs memory optimization operations"""
    
    def __init__(self, memory_manager: AdvancedMemoryManager, analyzer: MemoryAnalyzer):
        self.memory_manager = memory_manager
        self.analyzer = analyzer
        self.optimization_rules = self._initialize_default_rules()
        self.execution_history = []
    
    def _initialize_default_rules(self) -> List[OptimizationRule]:
        """Initialize default optimization rules"""
        
        return [
            OptimizationRule(
                rule_id="lru_cleanup",
                name="LRU Cleanup",
                description="Clean up least recently used blocks",
                strategy=OptimizationStrategy.LRU_CACHING,
                conditions={"max_age_days": 30, "min_access_count": 0},
                actions=[CleanupAction.ARCHIVE],
                priority=1,
                enabled=True,
                last_executed=None,
                execution_count=0
            ),
            OptimizationRule(
                rule_id="size_optimization",
                name="Size Optimization",
                description="Compress or archive large blocks",
                strategy=OptimizationStrategy.SIZE_BASED,
                conditions={"min_size_bytes": 10240},  # 10KB
                actions=[CleanupAction.COMPRESS],
                priority=2,
                enabled=True,
                last_executed=None,
                execution_count=0
            ),
            OptimizationRule(
                rule_id="frequency_cleanup",
                name="Frequency-based Cleanup",
                description="Clean up low-frequency blocks",
                strategy=OptimizationStrategy.FREQUENCY_BASED,
                conditions={"max_access_count": 2, "min_age_days": 7},
                actions=[CleanupAction.ARCHIVE],
                priority=3,
                enabled=True,
                last_executed=None,
                execution_count=0
            ),
            OptimizationRule(
                rule_id="type_consolidation",
                name="Type Consolidation",
                description="Merge similar block types",
                strategy=OptimizationStrategy.HYBRID,
                conditions={"similarity_threshold": 0.8},
                actions=[CleanupAction.MERGE_SIMILAR],
                priority=4,
                enabled=False,
                last_executed=None,
                execution_count=0
            )
        ]
    
    def execute_optimization(self, 
                           agent_id: str, 
                           strategy: OptimizationStrategy,
                           aggressive: bool = False) -> CleanupReport:
        """Execute memory optimization"""
        
        start_time = datetime.now()
        logger.info(f"Starting {strategy.value} optimization for agent {agent_id}")
        
        try:
            # Get memory blocks to optimize
            blocks = self._get_blocks_for_optimization(agent_id, strategy)
            
            actions_taken = {action: 0 for action in CleanupAction}
            space_freed = 0
            performance_improvement = 0
            errors = []
            
            # Execute based on strategy
            if strategy == OptimizationStrategy.LRU_CACHING:
                space_freed, actions_taken = self._execute_lru_optimization(blocks, aggressive, errors)
            elif strategy == OptimizationStrategy.LFU_CACHING:
                space_freed, actions_taken = self._execute_lfu_optimization(blocks, aggressive, errors)
            elif strategy == OptimizationStrategy.SIZE_BASED:
                space_freed, actions_taken = self._execute_size_optimization(blocks, aggressive, errors)
            elif strategy == OptimizationStrategy.FREQUENCY_BASED:
                space_freed, actions_taken = self._execute_frequency_optimization(blocks, aggressive, errors)
            elif strategy == OptimizationStrategy.TIME_BASED:
                space_freed, actions_taken = self._execute_time_optimization(blocks, aggressive, errors)
            elif strategy == OptimizationStrategy.PREDICTIVE:
                space_freed, actions_taken = self._execute_predictive_optimization(agent_id, blocks, aggressive, errors)
            elif strategy == OptimizationStrategy.HYBRID:
                space_freed, actions_taken = self._execute_hybrid_optimization(agent_id, blocks, aggressive, errors)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate performance improvement (simplified)
            metrics = self.analyzer.analyze_memory_usage(agent_id)
            performance_improvement = min(30.0, (space_freed / metrics.total_size_bytes) * 100)
            
            report = CleanupReport(
                timestamp=start_time,
                strategy=strategy,
                blocks_processed=len(blocks),
                actions_taken=actions_taken,
                space_freed_bytes=space_freed,
                performance_improvement=performance_improvement,
                errors=errors,
                execution_time_seconds=execution_time
            )
            
            self.execution_history.append(report)
            logger.info(f"Optimization completed: {report.blocks_processed} blocks processed, {space_freed} bytes freed")
            
            return report
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return CleanupReport(
                timestamp=start_time,
                strategy=strategy,
                blocks_processed=0,
                actions_taken={},
                space_freed_bytes=0,
                performance_improvement=0,
                errors=[str(e)],
                execution_time_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def _get_blocks_for_optimization(self, agent_id: str, strategy: OptimizationStrategy) -> List[MemoryBlock]:
        """Get blocks suitable for optimization based on strategy"""
        
        all_blocks = self.memory_manager.search_memory_blocks(agent_id, limit=10000)
        
        if strategy == OptimizationStrategy.LRU_CACHING:
            # Sort by last accessed time
            return sorted(all_blocks, key=lambda b: b.metadata.last_accessed)
        elif strategy == OptimizationStrategy.LFU_CACHING:
            # Sort by access count
            return sorted(all_blocks, key=lambda b: b.metadata.access_count)
        elif strategy == OptimizationStrategy.SIZE_BASED:
            # Sort by size (largest first)
            return sorted(all_blocks, key=lambda b: len(str(b.content)), reverse=True)
        elif strategy == OptimizationStrategy.FREQUENCY_BASED:
            # Sort by frequency and age
            return sorted(all_blocks, key=lambda b: (b.metadata.access_count, b.metadata.created_at))
        elif strategy == OptimizationStrategy.TIME_BASED:
            # Sort by creation time (oldest first)
            return sorted(all_blocks, key=lambda b: b.metadata.created_at)
        
        return all_blocks
    
    def _execute_lru_optimization(self, blocks: List[MemoryBlock], aggressive: bool, errors: List[str]) -> Tuple[int, Dict[CleanupAction, int]]:
        """Execute LRU-based optimization"""
        
        actions_taken = {action: 0 for action in CleanupAction}
        space_freed = 0
        
        # Define thresholds
        max_age_days = 30 if aggressive else 90
        archive_threshold = 7 if aggressive else 1
        
        for block in blocks:
            try:
                age_days = (datetime.now() - block.metadata.created_at).days
                days_since_access = (datetime.now() - block.metadata.last_accessed).days
                
                # Archive or delete based on access patterns
                if age_days > max_age_days or days_since_access > archive_threshold:
                    if block.metadata.priority in [MemoryPriority.LOW, MemoryPriority.MEDIUM]:
                        # Archive to Redis if available
                        if self.memory_manager.redis_client:
                            self.memory_manager._archive_to_redis(block)
                            actions_taken[CleanupAction.ARCHIVE] += 1
                            space_freed += len(str(block.content))
                        else:
                            # Delete if no Redis
                            self.memory_manager.delete_memory_block(
                                block.metadata.source_agent, 
                                block.block_id
                            )
                            actions_taken[CleanupAction.DELETE] += 1
                            space_freed += len(str(block.content))
                
            except Exception as e:
                errors.append(f"Error processing block {block.block_id}: {str(e)}")
        
        return space_freed, actions_taken
    
    def _execute_lfu_optimization(self, blocks: List[MemoryBlock], aggressive: bool, errors: List[str]) -> Tuple[int, Dict[CleanupAction, int]]:
        """Execute LFU-based optimization"""
        
        actions_taken = {action: 0 for action in CleanupAction}
        space_freed = 0
        
        # Process least frequently used blocks
        threshold = 3 if aggressive else 1
        
        for block in blocks:
            try:
                if block.metadata.access_count <= threshold:
                    # Compress or archive based on importance
                    if block.metadata.priority == MemoryPriority.LOW:
                        if self.memory_manager.redis_client:
                            self.memory_manager._archive_to_redis(block)
                            actions_taken[CleanupAction.ARCHIVE] += 1
                        else:
                            self.memory_manager.delete_memory_block(
                                block.metadata.source_agent, 
                                block.block_id
                            )
                            actions_taken[CleanupAction.DELETE] += 1
                        
                        space_freed += len(str(block.content))
                    else:
                        # Compress instead of delete
                        self.memory_manager._compress_block(block)
                        actions_taken[CleanupAction.COMPRESS] += 1
                        space_freed += len(str(block.content)) * 0.4  # Estimated compression savings
                
            except Exception as e:
                errors.append(f"Error processing block {block.block_id}: {str(e)}")
        
        return int(space_freed), actions_taken
    
    def _execute_size_optimization(self, blocks: List[MemoryBlock], aggressive: bool, errors: List[str]) -> Tuple[int, Dict[CleanupAction, int]]:
        """Execute size-based optimization"""
        
        actions_taken = {action: 0 for action in CleanupAction}
        space_freed = 0
        
        # Size thresholds
        compress_threshold = 10240 if aggressive else 20480  # 10KB or 20KB
        archive_threshold = 51200 if aggressive else 102400  # 50KB or 100KB
        
        for block in blocks:
            try:
                block_size = len(str(block.content))
                
                if block_size > archive_threshold:
                    # Archive large blocks
                    if self.memory_manager.redis_client:
                        self.memory_manager._archive_to_redis(block)
                        actions_taken[CleanupAction.ARCHIVE] += 1
                        space_freed += block_size
                    else:
                        # Compress if no archive available
                        self.memory_manager._compress_block(block)
                        actions_taken[CleanupAction.COMPRESS] += 1
                        space_freed += block_size * 0.5
                
                elif block_size > compress_threshold:
                    # Compress medium-sized blocks
                    if block.metadata.priority != MemoryPriority.CRITICAL:
                        self.memory_manager._compress_block(block)
                        actions_taken[CleanupAction.COMPRESS] += 1
                        space_freed += block_size * 0.3
                
            except Exception as e:
                errors.append(f"Error processing block {block.block_id}: {str(e)}")
        
        return int(space_freed), actions_taken
    
    def _execute_frequency_optimization(self, blocks: List[MemoryBlock], aggressive: bool, errors: List[str]) -> Tuple[int, Dict[CleanupAction, int]]:
        """Execute frequency-based optimization"""
        
        actions_taken = {action: 0 for action in CleanupAction}
        space_freed = 0
        
        # Frequency thresholds
        min_access_count = 5 if aggressive else 2
        max_age_days = 7 if aggressive else 14
        
        for block in blocks:
            try:
                age_days = (datetime.now() - block.metadata.created_at).days
                
                if (block.metadata.access_count <= min_access_count and 
                    age_days > max_age_days):
                    
                    if block.metadata.priority == MemoryPriority.LOW:
                        # Archive or delete low-priority blocks
                        if self.memory_manager.redis_client:
                            self.memory_manager._archive_to_redis(block)
                            actions_taken[CleanupAction.ARCHIVE] += 1
                        else:
                            self.memory_manager.delete_memory_block(
                                block.metadata.source_agent, 
                                block.block_id
                            )
                            actions_taken[CleanupAction.DELETE] += 1
                        
                        space_freed += len(str(block.content))
                
            except Exception as e:
                errors.append(f"Error processing block {block.block_id}: {str(e)}")
        
        return space_freed, actions_taken
    
    def _execute_time_optimization(self, blocks: List[MemoryBlock], aggressive: bool, errors: List[str]) -> Tuple[int, Dict[CleanupAction, int]]:
        """Execute time-based optimization"""
        
        actions_taken = {action: 0 for action in CleanupAction}
        space_freed = 0
        
        # Time thresholds
        archive_threshold = 30 if aggressive else 90  # days
        delete_threshold = 180 if aggressive else 365  # days
        
        for block in blocks:
            try:
                age_days = (datetime.now() - block.metadata.created_at).days
                
                if age_days > delete_threshold:
                    # Delete very old blocks
                    self.memory_manager.delete_memory_block(
                        block.metadata.source_agent, 
                        block.block_id
                    )
                    actions_taken[CleanupAction.DELETE] += 1
                    space_freed += len(str(block.content))
                
                elif age_days > archive_threshold:
                    # Archive old blocks
                    if self.memory_manager.redis_client:
                        self.memory_manager._archive_to_redis(block)
                        actions_taken[CleanupAction.ARCHIVE] += 1
                        space_freed += len(str(block.content))
                
            except Exception as e:
                errors.append(f"Error processing block {block.block_id}: {str(e)}")
        
        return space_freed, actions_taken
    
    def _execute_predictive_optimization(self, agent_id: str, blocks: List[MemoryBlock], aggressive: bool, errors: List[str]) -> Tuple[int, Dict[CleanupAction, int]]:
        """Execute predictive optimization based on usage patterns"""
        
        actions_taken = {action: 0 for action in CleanupAction}
        space_freed = 0
        
        # Get predictions
        predictions = self.analyzer.predict_memory_pressure(agent_id)
        
        # Adjust aggressiveness based on predicted pressure
        if predictions.get("pressure_level") == "critical":
            aggressive = True
        elif predictions.get("pressure_level") == "high":
            # Apply multiple strategies
            pass
        
        # Execute hybrid optimization for predictive mode
        space_freed, actions_taken = self._execute_hybrid_optimization(agent_id, blocks, aggressive, errors)
        
        return space_freed, actions_taken
    
    def _execute_hybrid_optimization(self, agent_id: str, blocks: List[MemoryBlock], aggressive: bool, errors: List[str]) -> Tuple[int, Dict[CleanupAction, int]]:
        """Execute hybrid optimization combining multiple strategies"""
        
        actions_taken = {action: 0 for action in CleanupAction}
        space_freed = 0
        
        # Get metrics for intelligent decisions
        metrics = self.analyzer.analyze_memory_usage(agent_id)
        
        # Strategy 1: LRU cleanup for old, unaccessed blocks
        lru_space, lru_actions = self._execute_lru_optimization(blocks[:len(blocks)//3], aggressive, errors)
        space_freed += lru_space
        for action, count in lru_actions.items():
            actions_taken[action] += count
        
        # Strategy 2: Size optimization for large blocks
        size_space, size_actions = self._execute_size_optimization(blocks[len(blocks)//3:2*len(blocks)//3], aggressive, errors)
        space_freed += size_space
        for action, count in size_actions.items():
            actions_taken[action] += count
        
        # Strategy 3: Frequency optimization for low-access blocks
        freq_space, freq_actions = self._execute_frequency_optimization(blocks[2*len(blocks)//3:], aggressive, errors)
        space_freed += freq_space
        for action, count in freq_actions.items():
            actions_taken[action] += count
        
        return space_freed, actions_taken
    
    def create_optimization_schedule(self, agent_id: str) -> Dict[str, Any]:
        """Create an optimization schedule based on current metrics"""
        
        metrics = self.analyzer.analyze_memory_usage(agent_id)
        opportunities = self.analyzer.identify_optimization_opportunities(agent_id)
        
        schedule = {
            "agent_id": agent_id,
            "current_metrics": asdict(metrics),
            "optimization_opportunities": opportunities,
            "recommended_strategies": [],
            "schedule_intervals": {},
            "priority_actions": []
        }
        
        # Recommend strategies based on metrics
        if metrics.cache_hit_rate < 0.7:
            schedule["recommended_strategies"].append({
                "strategy": OptimizationStrategy.LRU_CACHING.value,
                "reason": "Low cache hit rate",
                "frequency": "daily"
            })
        
        if metrics.memory_utilization > 0.8:
            schedule["recommended_strategies"].append({
                "strategy": OptimizationStrategy.HYBRID.value,
                "reason": "High memory utilization",
                "frequency": "immediate"
            })
        
        if metrics.average_block_size > 10000:
            schedule["recommended_strategies"].append({
                "strategy": OptimizationStrategy.SIZE_BASED.value,
                "reason": "Large average block size",
                "frequency": "weekly"
            })
        
        # Create schedule intervals
        schedule["schedule_intervals"] = {
            "lru_optimization": "6h" if metrics.cache_hit_rate < 0.7 else "24h",
            "size_optimization": "12h" if metrics.average_block_size > 10000 else "7d",
            "frequency_optimization": "1h" if metrics.memory_utilization > 0.8 else "24h",
            "full_optimization": "daily"
        }
        
        # Priority actions
        for opportunity in opportunities:
            if opportunity["priority"] == "high":
                schedule["priority_actions"].append({
                    "action": opportunity["type"],
                    "reason": opportunity["description"],
                    "urgency": "immediate"
                })
        
        return schedule
    
    def get_optimization_history(self, limit: int = 10) -> List[CleanupReport]:
        """Get optimization execution history"""
        return self.execution_history[-limit:] if limit > 0 else self.execution_history


class MemoryCleanupScheduler:
    """Schedules and manages automatic memory cleanup"""
    
    def __init__(self, optimizer: MemoryOptimizer):
        self.optimizer = optimizer
        self.scheduled_cleanups = {}
        self.running = False
        self.cleanup_thread = None
        self.executor = ThreadPoolExecutor(max_workers=2)
    
    def start(self):
        """Start the cleanup scheduler"""
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_scheduler_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info("Memory cleanup scheduler started")
    
    def stop(self):
        """Stop the cleanup scheduler"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("Memory cleanup scheduler stopped")
    
    def schedule_optimization(self, 
                            agent_id: str, 
                            strategy: OptimizationStrategy,
                            interval_hours: int = 24,
                            aggressive: bool = False) -> str:
        """Schedule periodic optimization"""
        
        schedule_id = f"{agent_id}_{strategy.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.scheduled_cleanups[schedule_id] = {
            "agent_id": agent_id,
            "strategy": strategy,
            "interval_hours": interval_hours,
            "aggressive": aggressive,
            "last_execution": None,
            "next_execution": datetime.now() + timedelta(hours=interval_hours),
            "execution_count": 0,
            "enabled": True
        }
        
        logger.info(f"Scheduled {strategy.value} optimization for agent {agent_id} every {interval_hours} hours")
        return schedule_id
    
    def cancel_scheduled_cleanup(self, schedule_id: str) -> bool:
        """Cancel a scheduled cleanup"""
        if schedule_id in self.scheduled_cleanups:
            del self.scheduled_cleanups[schedule_id]
            logger.info(f"Cancelled scheduled cleanup {schedule_id}")
            return True
        return False
    
    def get_scheduled_cleanups(self) -> Dict[str, Any]:
        """Get all scheduled cleanups"""
        return self.scheduled_cleanups
    
    def trigger_immediate_cleanup(self, agent_id: str, strategy: OptimizationStrategy) -> CleanupReport:
        """Trigger immediate cleanup"""
        
        return self.optimizer.execute_optimization(agent_id, strategy, aggressive=True)
    
    def _cleanup_scheduler_loop(self):
        """Main cleanup scheduler loop"""
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check for due cleanups
                for schedule_id, schedule_info in list(self.scheduled_cleanups.items()):
                    if (schedule_info["enabled"] and 
                        current_time >= schedule_info["next_execution"]):
                        
                        # Execute cleanup
                        future = self.executor.submit(
                            self.optimizer.execute_optimization,
                            schedule_info["agent_id"],
                            schedule_info["strategy"],
                            schedule_info["aggressive"]
                        )
                        
                        try:
                            report = future.result(timeout=300)  # 5 minute timeout
                            
                            # Update schedule info
                            schedule_info["last_execution"] = current_time
                            schedule_info["next_execution"] = current_time + timedelta(hours=schedule_info["interval_hours"])
                            schedule_info["execution_count"] += 1
                            
                            logger.info(f"Completed scheduled cleanup {schedule_id}: {report.blocks_processed} blocks processed")
                            
                        except Exception as e:
                            logger.error(f"Scheduled cleanup {schedule_id} failed: {e}")
                
                # Sleep for 1 minute before next check
                threading.Event().wait(60)
                
            except Exception as e:
                logger.error(f"Cleanup scheduler error: {e}")
                threading.Event().wait(300)  # Wait 5 minutes on error
    
    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get cleanup system status"""
        
        total_scheduled = len(self.scheduled_cleanups)
        enabled_scheduled = len([s for s in self.scheduled_cleanups.values() if s["enabled"]])
        
        upcoming_cleanups = []
        for schedule_id, schedule_info in self.scheduled_cleanups.items():
            if schedule_info["enabled"]:
                upcoming_cleanups.append({
                    "schedule_id": schedule_id,
                    "agent_id": schedule_info["agent_id"],
                    "strategy": schedule_info["strategy"].value,
                    "next_execution": schedule_info["next_execution"].isoformat(),
                    "hours_until_next": (schedule_info["next_execution"] - datetime.now()).total_seconds() / 3600
                })
        
        return {
            "scheduler_running": self.running,
            "total_scheduled": total_scheduled,
            "enabled_scheduled": enabled_scheduled,
            "upcoming_cleanups": upcoming_cleanups,
            "recent_reports": len(self.optimizer.get_optimization_history(5))
        }