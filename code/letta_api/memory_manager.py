#!/usr/bin/env python3
"""
Advanced Memory Management Wrapper for Letta API

Provides high-level memory management operations, advanced querying,
memory optimization, and intelligent memory organization for agent memory.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import defaultdict, Counter
import re
import hashlib

from letta_client import (
    LettaAPIClient, MemoryBlockType, QueryType, Priority, 
    SearchResult, TradingPattern, TradeEvent
)

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Memory optimization strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    SIZE_BASED = "size_based"
    FREQUENCY_BASED = "frequency_based"
    TIME_BASED = "time_based"
    HYBRID = "hybrid"
    AI_DRIVEN = "ai_driven"


class MemoryTier(Enum):
    """Memory storage tiers"""
    HOT = "hot"  # Frequently accessed
    WARM = "warm"  # Occasionally accessed
    COLD = "cold"  # Rarely accessed
    ARCHIVE = "archive"  # Historical data


@dataclass
class MemoryAnalytics:
    """Memory analytics and insights"""
    total_blocks: int
    total_size_bytes: int
    utilization_percentage: float
    fragmentation_index: float
    access_patterns: Dict[str, int]
    most_accessed_blocks: List[str]
    least_accessed_blocks: List[str]
    priority_distribution: Dict[str, int]
    age_distribution: Dict[str, int]
    compression_ratio: float
    cache_hit_rate: float


@dataclass
class OptimizationReport:
    """Memory optimization report"""
    strategy_used: str
    blocks_processed: int
    blocks_optimized: int
    space_freed_bytes: int
    performance_improvement: float
    optimization_time_seconds: float
    recommendations: List[str]


@dataclass
class MemoryInsight:
    """Memory insight and recommendation"""
    title: str
    description: str
    insight_type: str
    priority: str
    actionable_recommendations: List[str]
    estimated_impact: str
    confidence_score: float


class AdvancedMemoryManager:
    """
    Advanced Memory Manager for Letta API
    
    Provides high-level memory management operations including:
    - Intelligent memory organization
    - Advanced query capabilities
    - Memory optimization
    - Performance analytics
    - Insight generation
    - Memory tier management
    """
    
    def __init__(self, client: LettaAPIClient):
        self.client = client
        self._analytics_cache = {}
        self._optimization_history = []
        
    # === QUERY ENGINE ===
    
    def intelligent_search(
        self,
        agent_id: str,
        query: str,
        context: Dict[str, Any] = None,
        search_options: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """
        Intelligent search that combines multiple search strategies
        based on query type and context
        """
        
        search_options = search_options or {}
        context = context or {}
        
        # Determine search strategy based on query characteristics
        query_lower = query.lower()
        
        # Pattern detection
        if any(pattern in query_lower for pattern in ['pattern', 'signal', 'setup']):
            return self.pattern_intelligent_search(agent_id, query, search_options)
        
        # Temporal queries
        elif any(pattern in query_lower for pattern in ['recent', 'latest', 'today', 'yesterday', 'week', 'month']):
            return self.temporal_intelligent_search(agent_id, query, search_options)
        
        # Performance queries
        elif any(pattern in query_lower for pattern in ['performance', 'success', 'return', 'pnl', 'win', 'loss']):
            return self.performance_intelligent_search(agent_id, query, search_options)
        
        # Risk queries
        elif any(pattern in query_lower for pattern in ['risk', 'volatility', 'drawdown', 'stop loss']):
            return self.risk_intelligent_search(agent_id, query, search_options)
        
        # Default to semantic search with text fallback
        else:
            return self.semantic_search_with_fallback(agent_id, query, search_options)
    
    def pattern_intelligent_search(
        self,
        agent_id: str,
        query: str,
        search_options: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Search specifically for trading patterns and signals"""
        
        # Get patterns directly
        patterns = self.client.get_trading_patterns(agent_id)
        
        # Filter patterns based on query
        query_lower = query.lower()
        relevant_patterns = []
        
        for pattern in patterns:
            # Check if pattern matches query
            pattern_text = f"{pattern.pattern_type} {pattern.symbol}".lower()
            if any(term in pattern_text for term in query_lower.split()):
                result = SearchResult(
                    block_id=pattern.id,
                    agent_id=agent_id,
                    title=f"Pattern: {pattern.pattern_type} for {pattern.symbol}",
                    content=json.dumps(asdict(pattern), indent=2),
                    block_type=MemoryBlockType.LEARNED_PATTERNS,
                    relevance_score=pattern.confidence,
                    metadata={
                        "pattern_type": pattern.pattern_type,
                        "symbol": pattern.symbol,
                        "success_rate": pattern.success_rate,
                        "confidence": pattern.confidence
                    },
                    tags=["pattern", pattern.symbol.lower(), pattern.pattern_type.lower()],
                    created_at=pattern.created_at
                )
                relevant_patterns.append(result)
        
        # Also search memory blocks for pattern-related content
        memory_results = self.client.search_memory(
            agent_id=agent_id,
            query=query,
            query_type=QueryType.PATTERN_MATCHING,
            filters={"block_type": "learned_patterns"},
            limit=10
        )
        
        # Combine and deduplicate results
        all_results = relevant_patterns + memory_results
        return self._deduplicate_results(all_results)
    
    def temporal_intelligent_search(
        self,
        agent_id: str,
        query: str,
        search_options: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Intelligent temporal search based on query context"""
        
        search_options = search_options or {}
        now = datetime.now()
        
        # Determine time range from query
        query_lower = query.lower()
        
        if 'today' in query_lower:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif 'yesterday' in query_lower:
            start_time = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(days=1)
        elif 'week' in query_lower:
            start_time = now - timedelta(days=7)
        elif 'month' in query_lower:
            start_time = now - timedelta(days=30)
        else:
            # Default to recent 24 hours
            start_time = now - timedelta(days=1)
        
        end_time = search_options.get('end_time') or now
        
        # Perform temporal search
        temporal_results = self.client.temporal_search_memory(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            limit=20
        )
        
        # Also search for recent activity
        recent_results = self.client.search_memory(
            agent_id=agent_id,
            query="recent activity",
            query_type=QueryType.TEXT_SEARCH,
            filters={"block_type": "recent"},
            limit=10
        )
        
        # Combine results
        all_results = temporal_results + recent_results
        return self._deduplicate_results(all_results)
    
    def performance_intelligent_search(
        self,
        agent_id: str,
        query: str,
        search_options: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Search for performance-related content"""
        
        # Search trade outcomes
        outcomes_results = self.client.search_memory(
            agent_id=agent_id,
            query=query,
            query_type=QueryType.TEXT_SEARCH,
            filters={"block_type": "trade_outcomes"},
            limit=15
        )
        
        # Search performance metrics
        metrics_results = self.client.search_memory(
            agent_id=agent_id,
            query=query,
            query_type=QueryType.TEXT_SEARCH,
            filters={"block_type": "performance_metrics"},
            limit=10
        )
        
        # Search learned patterns (for performance data)
        patterns_results = self.client.search_memory(
            agent_id=agent_id,
            query=query,
            query_type=QueryType.TEXT_SEARCH,
            filters={"block_type": "learned_patterns"},
            limit=5
        )
        
        all_results = outcomes_results + metrics_results + patterns_results
        
        # Sort by relevance and recent activity
        return sorted(all_results, key=lambda x: x.relevance_score, reverse=True)
    
    def risk_intelligent_search(
        self,
        agent_id: str,
        query: str,
        search_options: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Search for risk-related content"""
        
        # Search risk parameters
        risk_params_results = self.client.search_memory(
            agent_id=agent_id,
            query=query,
            query_type=QueryType.TEXT_SEARCH,
            filters={"block_type": "risk_parameters"},
            limit=10
        )
        
        # Search for risk-related patterns in learned patterns
        pattern_risk_results = self.client.search_memory(
            agent_id=agent_id,
            query=query,
            query_type=QueryType.PATTERN_MATCHING,
            filters={
                "block_type": "learned_patterns",
                "tags_contains": ["risk"]
            },
            limit=10
        )
        
        # Search system context for risk alerts
        context_results = self.client.search_memory(
            agent_id=agent_id,
            query="risk alert volatility",
            query_type=QueryType.SEMANTIC_SIMILARITY,
            filters={"block_type": "system_context"},
            limit=5
        )
        
        all_results = risk_params_results + pattern_risk_results + context_results
        return self._deduplicate_results(all_results)
    
    def semantic_search_with_fallback(
        self,
        agent_id: str,
        query: str,
        search_options: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Semantic search with fallback to text search"""
        
        search_options = search_options or {}
        
        # Try semantic search first
        semantic_results = self.client.semantic_search_memory(
            query=query,
            agent_id=agent_id,
            similarity_threshold=0.6,
            limit=15
        )
        
        # If semantic search returns few results, add text search
        if len(semantic_results) < 5:
            text_results = self.client.search_memory(
                agent_id=agent_id,
                query=query,
                query_type=QueryType.TEXT_SEARCH,
                limit=15
            )
            
            # Combine and deduplicate
            all_results = semantic_results + text_results
            return self._deduplicate_results(all_results)
        
        return semantic_results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on block_id"""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.block_id not in seen_ids:
                seen_ids.add(result.block_id)
                unique_results.append(result)
        
        return unique_results
    
    # === MEMORY ANALYTICS ===
    
    def get_comprehensive_analytics(self, agent_id: str) -> MemoryAnalytics:
        """Get comprehensive memory analytics"""
        
        # Get all memory blocks
        memory_blocks = self.client.get_agent_memory(agent_id)
        
        if not memory_blocks:
            return MemoryAnalytics(
                total_blocks=0,
                total_size_bytes=0,
                utilization_percentage=0.0,
                fragmentation_index=0.0,
                access_patterns={},
                most_accessed_blocks=[],
                least_accessed_blocks=[],
                priority_distribution={},
                age_distribution={},
                compression_ratio=1.0,
                cache_hit_rate=0.0
            )
        
        # Calculate basic metrics
        total_blocks = len(memory_blocks)
        total_size_bytes = sum(len(block.content) for block in memory_blocks)
        
        # Access patterns
        access_patterns = Counter()
        for block in memory_blocks:
            access_patterns[block.block_type.value] += block.access_count
        
        # Most/least accessed blocks
        sorted_by_access = sorted(memory_blocks, key=lambda x: x.access_count, reverse=True)
        most_accessed = [block.id for block in sorted_by_access[:5]]
        least_accessed = [block.id for block in sorted_by_access[-5:]]
        
        # Priority distribution
        priority_distribution = Counter()
        for block in memory_blocks:
            priority_distribution[block.priority.value] += 1
        
        # Age distribution
        now = datetime.now()
        age_distribution = {
            "recent": 0,      # < 1 day
            "short": 0,       # 1-7 days
            "medium": 0,      # 1-4 weeks
            "long": 0,        # 1-6 months
            "old": 0          # > 6 months
        }
        
        for block in memory_blocks:
            age_days = (now - block.created_at).days
            if age_days < 1:
                age_distribution["recent"] += 1
            elif age_days <= 7:
                age_distribution["short"] += 1
            elif age_days <= 28:
                age_distribution["medium"] += 1
            elif age_days <= 180:
                age_distribution["long"] += 1
            else:
                age_distribution["old"] += 1
        
        # Calculate utilization (estimated)
        # This would ideally come from server-side metrics
        utilization_percentage = min(100.0, (total_size_bytes / (1024 * 1024)) * 0.1)  # Rough estimate
        
        # Fragmentation index (simplified calculation)
        block_sizes = [len(block.content) for block in memory_blocks]
        if len(block_sizes) > 1:
            size_variance = statistics.variance(block_sizes)
            size_mean = statistics.mean(block_sizes)
            fragmentation_index = min(1.0, size_variance / (size_mean * size_mean) if size_mean > 0 else 0)
        else:
            fragmentation_index = 0.0
        
        # Cache hit rate (from client monitoring)
        cache_stats = self.client.get_cache_stats()
        cache_hit_rate = cache_stats.get("hit_rate", 0.0)
        
        # Compression ratio (estimated)
        compression_ratio = 0.75 if total_size_bytes > 0 else 1.0  # Rough estimate
        
        return MemoryAnalytics(
            total_blocks=total_blocks,
            total_size_bytes=total_size_bytes,
            utilization_percentage=utilization_percentage,
            fragmentation_index=fragmentation_index,
            access_patterns=dict(access_patterns),
            most_accessed_blocks=most_accessed,
            least_accessed_blocks=least_accessed,
            priority_distribution=dict(priority_distribution),
            age_distribution=age_distribution,
            compression_ratio=compression_ratio,
            cache_hit_rate=cache_hit_rate
        )
    
    def get_access_pattern_analysis(self, agent_id: str) -> Dict[str, Any]:
        """Analyze access patterns to identify trends and anomalies"""
        
        memory_blocks = self.client.get_agent_memory(agent_id)
        now = datetime.now()
        
        # Analyze access patterns by time
        access_by_hour = defaultdict(int)
        access_by_day = defaultdict(int)
        access_by_block_type = defaultdict(int)
        
        for block in memory_blocks:
            if block.last_accessed:
                hour = block.last_accessed.hour
                day = block.last_accessed.strftime("%Y-%m-%d")
                access_by_hour[hour] += block.access_count
                access_by_day[day] += block.access_count
            
            access_by_block_type[block.block_type.value] += block.access_count
        
        # Identify peak access times
        peak_hour = max(access_by_hour, key=access_by_hour.get) if access_by_hour else 0
        peak_day = max(access_by_day, key=access_by_day.get) if access_by_day else ""
        
        # Identify cold blocks (high priority but low access)
        cold_blocks = []
        for block in memory_blocks:
            if block.priority in [Priority.CRITICAL, Priority.HIGH] and block.access_count < 2:
                cold_blocks.append({
                    "id": block.id,
                    "title": block.title,
                    "priority": block.priority.value,
                    "access_count": block.access_count,
                    "days_old": (now - block.created_at).days
                })
        
        return {
            "peak_access_hour": peak_hour,
            "peak_access_day": peak_day,
            "access_by_hour": dict(access_by_hour),
            "access_by_day": dict(access_by_day),
            "access_by_block_type": dict(access_by_block_type),
            "cold_blocks": cold_blocks,
            "total_accesses": sum(block.access_count for block in memory_blocks)
        }
    
    # === INTELLIGENT INSIGHTS ===
    
    def generate_memory_insights(self, agent_id: str) -> List[MemoryInsight]:
        """Generate intelligent insights from memory data"""
        
        insights = []
        analytics = self.get_comprehensive_analytics(agent_id)
        access_patterns = self.get_access_pattern_analysis(agent_id)
        
        # Memory utilization insights
        if analytics.utilization_percentage > 90:
            insights.append(MemoryInsight(
                title="High Memory Utilization",
                description=f"Memory utilization is at {analytics.utilization_percentage:.1f}%, which may impact performance.",
                insight_type="performance",
                priority="high",
                actionable_recommendations=[
                    "Run memory optimization",
                    "Archive old, infrequently accessed blocks",
                    "Consider increasing memory limits"
                ],
                estimated_impact="medium",
                confidence_score=0.9
            ))
        elif analytics.utilization_percentage < 30:
            insights.append(MemoryInsight(
                title="Low Memory Utilization",
                description=f"Memory utilization is only {analytics.utilization_percentage:.1f}%, indicating underutilized resources.",
                insight_type="efficiency",
                priority="low",
                actionable_recommendations=[
                    "Consider consolidating memory blocks",
                    "Review and remove duplicate content",
                    "Optimize block structure for better organization"
                ],
                estimated_impact="low",
                confidence_score=0.8
            ))
        
        # Fragmentation insights
        if analytics.fragmentation_index > 0.7:
            insights.append(MemoryInsight(
                title="High Memory Fragmentation",
                description=f"Memory fragmentation index is {analytics.fragmentation_index:.2f}, indicating poor organization.",
                insight_type="organization",
                priority="medium",
                actionable_recommendations=[
                    "Run memory organization",
                    "Consolidate similar blocks",
                    "Implement memory defragmentation"
                ],
                estimated_impact="medium",
                confidence_score=0.85
            ))
        
        # Access pattern insights
        if access_patterns["cold_blocks"]:
            insights.append(MemoryInsight(
                title="Cold High-Priority Blocks",
                description=f"Found {len(access_patterns['cold_blocks'])} high-priority blocks with low access rates.",
                insight_type="optimization",
                priority="medium",
                actionable_recommendations=[
                    "Review priority assignments for cold blocks",
                    "Consider promoting frequently accessed medium-priority blocks",
                    "Archive or remove obsolete high-priority blocks"
                ],
                estimated_impact="low",
                confidence_score=0.75
            ))
        
        # Cache performance insights
        if analytics.cache_hit_rate < 0.5:
            insights.append(MemoryInsight(
                title="Low Cache Hit Rate",
                description=f"Cache hit rate is {analytics.cache_hit_rate:.1%}, indicating poor caching efficiency.",
                insight_type="performance",
                priority="medium",
                actionable_recommendations=[
                    "Increase cache TTL",
                    "Review access patterns",
                    "Optimize query strategies"
                ],
                estimated_impact="medium",
                confidence_score=0.8
            ))
        
        # Block type distribution insights
        total_blocks = analytics.total_blocks
        if total_blocks > 0:
            largest_type = max(analytics.priority_distribution, key=analytics.priority_distribution.get)
            if analytics.priority_distribution[largest_type] / total_blocks > 0.6:
                insights.append(MemoryInsight(
                    title="Imbalanced Block Distribution",
                    description=f"{largest_type} blocks constitute {analytics.priority_distribution[largest_type]/total_blocks:.1%} of all blocks.",
                    insight_type="organization",
                    priority="low",
                    actionable_recommendations=[
                        "Review block categorization",
                        "Consider splitting large categories",
                        "Balance memory usage across types"
                    ],
                    estimated_impact="low",
                    confidence_score=0.7
                ))
        
        # Recent activity insights
        recent_blocks = sum(1 for block in self.client.get_agent_memory(agent_id) 
                          if (datetime.now() - block.created_at).days <= 7)
        if recent_blocks > total_blocks * 0.3:
            insights.append(MemoryInsight(
                title="High Recent Activity",
                description=f"{recent_blocks} blocks created in the last 7 days, indicating active learning.",
                insight_type="learning",
                priority="low",
                actionable_recommendations=[
                    "Review recent learning outcomes",
                    "Consolidate redundant recent additions",
                    "Consider scheduling periodic optimization"
                ],
                estimated_impact="medium",
                confidence_score=0.9
            ))
        
        return insights
    
    # === MEMORY OPTIMIZATION ===
    
    def optimize_memory_intelligent(
        self,
        agent_id: str,
        strategy: OptimizationStrategy = OptimizationStrategy.HYBRID,
        aggressive: bool = False,
        target_utilization: float = 70.0
    ) -> OptimizationReport:
        """Intelligent memory optimization based on analytics and access patterns"""
        
        start_time = datetime.now()
        
        # Get current analytics
        analytics = self.get_comprehensive_analytics(agent_id)
        
        # Determine optimization approach based on current state
        if analytics.utilization_percentage > 90:
            # High utilization - need aggressive cleanup
            optimization_strategy = "size_based" if aggressive else "frequency_based"
        elif analytics.fragmentation_index > 0.5:
            # High fragmentation - reorganize
            optimization_strategy = "organization"
        else:
            # Normal optimization
            optimization_strategy = strategy.value
        
        # Get optimization recommendations
        optimization_data = self.client.optimize_memory(
            agent_id=agent_id,
            optimization_strategy=optimization_strategy,
            aggressive=aggressive,
            target_size=int((target_utilization / 100.0) * analytics.total_size_bytes)
        )
        
        optimization_time = (datetime.now() - start_time).total_seconds()
        
        # Generate optimization report
        recommendations = []
        
        if optimization_data.get("blocks_removed", 0) > 0:
            recommendations.append(f"Removed {optimization_data['blocks_removed']} low-priority blocks")
        
        if optimization_data.get("blocks_consolidated", 0) > 0:
            recommendations.append(f"Consolidated {optimization_data['blocks_consolidated']} duplicate blocks")
        
        if optimization_data.get("space_freed_bytes", 0) > 0:
            space_mb = optimization_data["space_freed_bytes"] / (1024 * 1024)
            recommendations.append(f"Freed {space_mb:.1f} MB of memory")
        
        # Add strategic recommendations
        if analytics.fragmentation_index > 0.6:
            recommendations.append("Consider running memory organization")
        
        if analytics.cache_hit_rate < 0.6:
            recommendations.append("Review caching configuration")
        
        report = OptimizationReport(
            strategy_used=optimization_strategy,
            blocks_processed=optimization_data.get("blocks_processed", 0),
            blocks_optimized=optimization_data.get("blocks_optimized", 0),
            space_freed_bytes=optimization_data.get("space_freed_bytes", 0),
            performance_improvement=optimization_data.get("performance_improvement", 0.0),
            optimization_time_seconds=optimization_time,
            recommendations=recommendations
        )
        
        # Store in history
        self._optimization_history.append(report)
        
        return report
    
    def get_optimization_recommendations(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get specific optimization recommendations"""
        
        recommendations = []
        analytics = self.get_comprehensive_analytics(agent_id)
        access_patterns = self.get_access_pattern_analysis(agent_id)
        
        # Utilization recommendations
        if analytics.utilization_percentage > 85:
            recommendations.append({
                "type": "cleanup",
                "description": "High memory utilization detected",
                "recommendation": "Run memory optimization with size-based strategy",
                "priority": "high",
                "estimated_impact": "high"
            })
        
        # Fragmentation recommendations
        if analytics.fragmentation_index > 0.6:
            recommendations.append({
                "type": "organization",
                "description": "Memory fragmentation is high",
                "recommendation": "Run memory organization to consolidate blocks",
                "priority": "medium",
                "estimated_impact": "medium"
            })
        
        # Cache recommendations
        if analytics.cache_hit_rate < 0.6:
            recommendations.append({
                "type": "caching",
                "description": "Cache hit rate is low",
                "recommendation": "Increase cache TTL and review query patterns",
                "priority": "medium",
                "estimated_impact": "medium"
            })
        
        # Cold block recommendations
        if access_patterns["cold_blocks"]:
            recommendations.append({
                "type": "priority",
                "description": f"{len(access_patterns['cold_blocks'])} high-priority blocks are rarely accessed",
                "recommendation": "Review priority assignments and consider downgrading cold blocks",
                "priority": "low",
                "estimated_impact": "low"
            })
        
        # Age-based recommendations
        old_blocks = analytics.age_distribution.get("old", 0)
        if old_blocks > analytics.total_blocks * 0.2:
            recommendations.append({
                "type": "archival",
                "description": f"{old_blocks} blocks are older than 6 months",
                "recommendation": "Archive old blocks to cold storage",
                "priority": "low",
                "estimated_impact": "low"
            })
        
        return recommendations
    
    # === MEMORY ORGANIZATION ===
    
    def organize_memory_by_category(self, agent_id: str) -> Dict[str, Any]:
        """Organize memory blocks by category and type"""
        
        memory_blocks = self.client.get_agent_memory(agent_id)
        
        # Group blocks by type
        blocks_by_type = defaultdict(list)
        for block in memory_blocks:
            blocks_by_type[block.block_type.value].append(block)
        
        # Generate organization plan
        organization_plan = {
            "total_blocks": len(memory_blocks),
            "categories": {},
            "consolidation_opportunities": [],
            "recommendations": []
        }
        
        # Analyze each category
        for block_type, blocks in blocks_by_type.items():
            category_info = {
                "count": len(blocks),
                "total_size": sum(len(block.content) for block in blocks),
                "avg_size": sum(len(block.content) for block in blocks) / len(blocks) if blocks else 0,
                "priority_distribution": Counter(block.priority.value for block in blocks),
                "age_distribution": self._calculate_age_distribution(blocks)
            }
            organization_plan["categories"][block_type] = category_info
            
            # Identify consolidation opportunities
            if len(blocks) > 10:
                organization_plan["consolidation_opportunities"].append({
                    "category": block_type,
                    "opportunity": f"Large number of {block_type} blocks ({len(blocks)}) could benefit from consolidation",
                    "estimated_space_saving": len(blocks) * 100  # Rough estimate
                })
        
        # Generate recommendations
        largest_category = max(blocks_by_type, key=lambda x: len(blocks_by_type[x]))
        if len(blocks_by_type[largest_category]) > len(memory_blocks) * 0.4:
            organization_plan["recommendations"].append(
                f"Consider breaking down {largest_category} category into subcategories"
            )
        
        # Execute organization
        organization_result = self.client.organize_memory_blocks(
            agent_id=agent_id,
            organization_type="category",
            auto_cleanup=True
        )
        
        organization_plan["execution_result"] = organization_result
        
        return organization_plan
    
    def _calculate_age_distribution(self, blocks: List) -> Dict[str, int]:
        """Calculate age distribution for a list of blocks"""
        now = datetime.now()
        distribution = {
            "recent": 0,    # < 1 day
            "short": 0,     # 1-7 days
            "medium": 0,    # 1-4 weeks
            "long": 0       # > 1 month
        }
        
        for block in blocks:
            age_days = (now - block.created_at).days
            if age_days < 1:
                distribution["recent"] += 1
            elif age_days <= 7:
                distribution["short"] += 1
            elif age_days <= 28:
                distribution["medium"] += 1
            else:
                distribution["long"] += 1
        
        return distribution
    
    # === UTILITY METHODS ===
    
    def get_memory_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get a comprehensive summary of agent memory"""
        
        analytics = self.get_comprehensive_analytics(agent_id)
        insights = self.generate_memory_insights(agent_id)
        recommendations = self.get_optimization_recommendations(agent_id)
        
        return {
            "agent_id": agent_id,
            "analytics": asdict(analytics),
            "insights": [asdict(insight) for insight in insights],
            "optimization_opportunities": recommendations,
            "last_updated": datetime.now().isoformat()
        }
    
    def compare_agents_memory(self, agent_ids: List[str]) -> Dict[str, Any]:
        """Compare memory usage and patterns across agents"""
        
        comparisons = {}
        
        for agent_id in agent_ids:
            analytics = self.get_comprehensive_analytics(agent_id)
            comparisons[agent_id] = {
                "total_blocks": analytics.total_blocks,
                "total_size_mb": analytics.total_size_bytes / (1024 * 1024),
                "utilization": analytics.utilization_percentage,
                "fragmentation": analytics.fragmentation_index,
                "cache_hit_rate": analytics.cache_hit_rate,
                "main_block_types": list(analytics.priority_distribution.keys())[:3]
            }
        
        # Generate comparative insights
        avg_utilization = statistics.mean(comp["utilization"] for comp in comparisons.values())
        max_size_agent = max(comparisons, key=lambda x: comparisons[x]["total_size_mb"])
        
        comparative_insights = {
            "average_utilization": avg_utilization,
            "largest_agent": max_size_agent,
            "size_range": {
                "min": min(comp["total_size_mb"] for comp in comparisons.values()),
                "max": max(comp["total_size_mb"] for comp in comparisons.values())
            },
            "utilization_range": {
                "min": min(comp["utilization"] for comp in comparisons.values()),
                "max": max(comp["utilization"] for comp in comparisons.values())
            }
        }
        
        return {
            "agent_comparisons": comparisons,
            "comparative_insights": comparative_insights
        }


# === CONVENIENT FUNCTIONS ===

def create_memory_manager(client: LettaAPIClient) -> AdvancedMemoryManager:
    """Create an advanced memory manager instance"""
    return AdvancedMemoryManager(client)


def quick_memory_insights(agent_id: str, client: LettaAPIClient) -> Dict[str, Any]:
    """Get quick memory insights without detailed analytics"""
    
    manager = AdvancedMemoryManager(client)
    
    # Get basic analytics
    memory_blocks = client.get_agent_memory(agent_id)
    
    if not memory_blocks:
        return {
            "status": "no_memory",
            "message": "No memory blocks found for agent"
        }
    
    # Quick stats
    total_blocks = len(memory_blocks)
    total_size = sum(len(block.content) for block in memory_blocks)
    recent_blocks = sum(1 for block in memory_blocks 
                       if (datetime.now() - block.created_at).days <= 7)
    
    # Quick insights
    insights = []
    
    if total_blocks > 100:
        insights.append("High number of memory blocks - consider organization")
    
    if recent_blocks > total_blocks * 0.3:
        insights.append("High recent activity - active learning detected")
    
    if total_size > 1024 * 1024:  # > 1MB
        insights.append("Large memory footprint - optimization recommended")
    
    return {
        "total_blocks": total_blocks,
        "total_size_kb": total_size / 1024,
        "recent_blocks": recent_blocks,
        "quick_insights": insights,
        "recommendations": manager.get_optimization_recommendations(agent_id)[:3]
    }


if __name__ == "__main__":
    # Example usage
    import sys
    sys.path.append('/workspace/code/letta_api')
    
    from letta_client import LettaAPIClient
    
    # Configuration
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8283"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "your-secret-api-key"
    agent_id = sys.argv[3] if len(sys.argv) > 3 else "test_agent"
    
    print("Advanced Memory Manager Demo")
    print("=" * 50)
    
    client = LettaAPIClient(base_url, api_key)
    manager = AdvancedMemoryManager(client)
    
    try:
        # Quick insights
        print(f"\n1. Quick Memory Insights for {agent_id}:")
        quick_insights = quick_memory_insights(agent_id, client)
        for key, value in quick_insights.items():
            if key != "recommendations":
                print(f"   {key}: {value}")
        
        # Comprehensive analytics
        print(f"\n2. Comprehensive Analytics:")
        analytics = manager.get_comprehensive_analytics(agent_id)
        print(f"   Total Blocks: {analytics.total_blocks}")
        print(f"   Total Size: {analytics.total_size_bytes / 1024:.1f} KB")
        print(f"   Utilization: {analytics.utilization_percentage:.1f}%")
        print(f"   Fragmentation: {analytics.fragmentation_index:.2f}")
        
        # Memory insights
        print(f"\n3. Generated Insights:")
        insights = manager.generate_memory_insights(agent_id)
        for insight in insights[:3]:  # Show first 3 insights
            print(f"   - {insight.title}: {insight.description}")
        
        # Optimization recommendations
        print(f"\n4. Optimization Opportunities:")
        recommendations = manager.get_optimization_recommendations(agent_id)
        for rec in recommendations[:3]:  # Show first 3 recommendations
            print(f"   - {rec['description']}: {rec['recommendation']}")
        
        print("\nDemo completed successfully!")
        
    except Exception as e:
        print(f"Error during demo: {e}")
    finally:
        client.close()