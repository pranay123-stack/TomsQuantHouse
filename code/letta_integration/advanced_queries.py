#!/usr/bin/env python3
"""
Advanced Agent Memory Querying System for Strategic Decision Making
Provides sophisticated querying capabilities for agent memory retrieval and analysis
"""

import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from abc import ABC, abstractmethod
import re
from collections import defaultdict, Counter

from advanced_memory_manager import (
    AdvancedMemoryManager,
    MemoryBlockType,
    MemoryPriority,
    TradingPattern,
    MarketLearning,
    PerformanceInsight
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of memory queries"""
    TEXT_SEARCH = "text_search"
    PATTERN_MATCH = "pattern_match"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    TEMPORAL_FILTER = "temporal_filter"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    CORRELATION_SEARCH = "correlation_search"
    STRATEGY_COMPARISON = "strategy_comparison"
    RISK_ASSESSMENT = "risk_assessment"
    MARKET_REGIME = "market_regime"
    COMPOSITE = "composite"


class QueryOperator(Enum):
    """Query operators for complex filtering"""
    AND = "and"
    OR = "or"
    NOT = "not"
    IN = "in"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"


@dataclass
class QueryFilter:
    """Filter for memory queries"""
    field: str
    operator: QueryOperator
    value: Any
    weight: float = 1.0


@dataclass
class QueryResult:
    """Result of memory query"""
    query_id: str
    query_type: QueryType
    execution_time: float
    total_results: int
    results: List[Dict[str, Any]]
    relevance_scores: List[float]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class StrategyInsight:
    """Strategic insight from memory analysis"""
    insight_id: str
    category: str
    title: str
    description: str
    confidence: float
    impact_score: float
    time_sensitivity: str
    actionable_recommendations: List[str]
    related_patterns: List[str]
    risk_level: str


@dataclass
class MarketMemoryContext:
    """Market context from agent memory"""
    current_regime: str
    recent_volatility: float
    dominant_trends: List[str]
    risk_events: List[Dict[str, Any]]
    successful_patterns: List[TradingPattern]
    failed_patterns: List[TradingPattern]
    performance_metrics: Dict[str, float]
    correlations: Dict[str, float]


class QueryEngine:
    """Advanced query engine for agent memory"""
    
    def __init__(self, memory_manager: AdvancedMemoryManager):
        self.memory_manager = memory_manager
        self.query_cache = {}
        self.pattern_matcher = PatternMatcher()
        self.performance_analyzer = PerformanceAnalyzer()
        self.correlation_calculator = CorrelationCalculator()
        
        # Query statistics
        self.query_stats = defaultdict(int)
        self.popular_queries = []
    
    def execute_query(self, 
                     query_type: QueryType,
                     agent_id: str,
                     filters: List[QueryFilter] = None,
                     search_text: str = None,
                     limit: int = 50,
                     sort_by: str = "relevance") -> QueryResult:
        """Execute comprehensive memory query"""
        
        query_id = f"{query_type.value}_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        start_time = datetime.now()
        
        try:
            logger.info(f"Executing query {query_id} of type {query_type.value}")
            
            # Initialize result
            results = []
            relevance_scores = []
            
            # Execute based on query type
            if query_type == QueryType.TEXT_SEARCH:
                results, relevance_scores = self._execute_text_search(
                    agent_id, search_text, filters, limit
                )
            elif query_type == QueryType.PATTERN_MATCH:
                results, relevance_scores = self._execute_pattern_match(
                    agent_id, filters, limit
                )
            elif query_type == QueryType.PERFORMANCE_ANALYSIS:
                results, relevance_scores = self._execute_performance_analysis(
                    agent_id, filters, limit
                )
            elif query_type == QueryType.TEMPORAL_FILTER:
                results, relevance_scores = self._execute_temporal_filter(
                    agent_id, filters, limit
                )
            elif query_type == QueryType.SEMANTIC_SIMILARITY:
                results, relevance_scores = self._execute_semantic_similarity(
                    agent_id, search_text, limit
                )
            elif query_type == QueryType.CORRELATION_SEARCH:
                results, relevance_scores = self._execute_correlation_search(
                    agent_id, filters, limit
                )
            elif query_type == QueryType.STRATEGY_COMPARISON:
                results, relevance_scores = self._execute_strategy_comparison(
                    agent_id, filters, limit
                )
            elif query_type == QueryType.RISK_ASSESSMENT:
                results, relevance_scores = self._execute_risk_assessment(
                    agent_id, filters, limit
                )
            elif query_type == QueryType.MARKET_REGIME:
                results, relevance_scores = self._execute_market_regime_query(
                    agent_id, filters, limit
                )
            elif query_type == QueryType.COMPOSITE:
                results, relevance_scores = self._execute_composite_query(
                    agent_id, search_text, filters, limit
                )
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Sort results if needed
            if sort_by == "relevance" and relevance_scores:
                sorted_pairs = sorted(
                    zip(results, relevance_scores),
                    key=lambda x: x[1],
                    reverse=True
                )
                results, relevance_scores = zip(*sorted_pairs) if sorted_pairs else ([], [])
            
            # Create summary
            summary = self._create_query_summary(results, query_type)
            
            # Update query statistics
            self.query_stats[query_type.value] += 1
            
            query_result = QueryResult(
                query_id=query_id,
                query_type=query_type,
                execution_time=execution_time,
                total_results=len(results),
                results=list(results),
                relevance_scores=list(relevance_scores),
                summary=summary,
                metadata={
                    "agent_id": agent_id,
                    "filters_applied": len(filters) if filters else 0,
                    "cache_hit": False
                }
            )
            
            logger.info(f"Query {query_id} completed: {len(results)} results in {execution_time:.2f}s")
            return query_result
            
        except Exception as e:
            logger.error(f"Query {query_id} failed: {e}")
            return QueryResult(
                query_id=query_id,
                query_type=query_type,
                execution_time=(datetime.now() - start_time).total_seconds(),
                total_results=0,
                results=[],
                relevance_scores=[],
                summary={"error": str(e)},
                metadata={"agent_id": agent_id}
            )
    
    def _execute_text_search(self, 
                           agent_id: str, 
                           search_text: str, 
                           filters: List[QueryFilter],
                           limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute text-based search"""
        # Use Letta's built-in search first
        letta_results = self.memory_manager.base_client.search_memory(agent_id, search_text)
        
        results = []
        relevance_scores = []
        
        for result in letta_results:
            # Calculate relevance score
            score = self._calculate_text_relevance(search_text, result)
            
            # Apply additional filters
            if self._passes_filters(result, filters):
                results.append(result)
                relevance_scores.append(score)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_pattern_match(self, 
                             agent_id: str, 
                             filters: List[QueryFilter],
                             limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute pattern-based search"""
        
        # Search for pattern-type memory blocks
        pattern_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.LEARNED_PATTERNS,
            limit=limit * 2  # Get more to filter
        )
        
        results = []
        relevance_scores = []
        
        for block in pattern_blocks:
            pattern_match_score = self.pattern_matcher.match_pattern(
                block, filters
            )
            
            if pattern_match_score > 0:
                results.append(block.to_dict())
                relevance_scores.append(pattern_match_score)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_performance_analysis(self, 
                                    agent_id: str, 
                                    filters: List[QueryFilter],
                                    limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute performance-based search"""
        
        # Get performance-related blocks
        performance_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.PERFORMANCE_METRICS,
            limit=limit
        )
        
        trade_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.TRADE_OUTCOMES,
            limit=limit
        )
        
        results = []
        relevance_scores = []
        
        # Analyze performance data
        for block in performance_blocks + trade_blocks:
            performance_score = self.performance_analyzer.analyze_block_relevance(
                block, filters
            )
            
            if performance_score > 0:
                results.append(block.to_dict())
                relevance_scores.append(performance_score)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_temporal_filter(self, 
                               agent_id: str, 
                               filters: List[QueryFilter],
                               limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute temporal-based search"""
        
        # Extract time range from filters
        time_range = None
        for filter_obj in filters or []:
            if filter_obj.field == "created_at" and filter_obj.operator == QueryOperator.IN:
                time_range = filter_obj.value
        
        # Get blocks with temporal filtering
        all_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            limit=limit * 3
        )
        
        results = []
        relevance_scores = []
        
        for block in all_blocks:
            temporal_score = self._calculate_temporal_relevance(
                block, time_range, filters
            )
            
            if temporal_score > 0:
                results.append(block.to_dict())
                relevance_scores.append(temporal_score)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_semantic_similarity(self, 
                                   agent_id: str, 
                                   search_text: str,
                                   limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute semantic similarity search"""
        
        # Use basic text similarity for now
        all_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            limit=limit * 2
        )
        
        results = []
        relevance_scores = []
        
        for block in all_blocks:
            similarity = self._calculate_semantic_similarity(
                search_text, block
            )
            
            if similarity > 0.1:  # Minimum similarity threshold
                results.append(block.to_dict())
                relevance_scores.append(similarity)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_correlation_search(self, 
                                  agent_id: str, 
                                  filters: List[QueryFilter],
                                  limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute correlation-based search"""
        
        # Find correlation-related memory blocks
        correlation_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.CORRELATION_MATRICES,
            limit=limit
        )
        
        results = []
        relevance_scores = []
        
        for block in correlation_blocks:
            correlation_data = block.trading_data
            correlation_relevance = self.correlation_calculator.calculate_relevance(
                correlation_data, filters
            )
            
            if correlation_relevance > 0:
                results.append(block.to_dict())
                relevance_scores.append(correlation_relevance)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_strategy_comparison(self, 
                                   agent_id: str, 
                                   filters: List[QueryFilter],
                                   limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute strategy comparison search"""
        
        # Get strategy-related blocks
        strategy_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.TRADING_STRATEGY,
            limit=limit
        )
        
        evolution_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.STRATEGY_EVOLUTION,
            limit=limit
        )
        
        results = []
        relevance_scores = []
        
        all_strategy_blocks = strategy_blocks + evolution_blocks
        
        for block in all_strategy_blocks:
            comparison_score = self._calculate_strategy_relevance(block, filters)
            
            if comparison_score > 0:
                results.append(block.to_dict())
                relevance_scores.append(comparison_score)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_risk_assessment(self, 
                               agent_id: str, 
                               filters: List[QueryFilter],
                               limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute risk assessment search"""
        
        # Get risk-related blocks
        risk_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.RISK_PARAMETERS,
            limit=limit
        )
        
        risk_events = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.RISK_EVENTS,
            limit=limit
        )
        
        results = []
        relevance_scores = []
        
        all_risk_blocks = risk_blocks + risk_events
        
        for block in all_risk_blocks:
            risk_score = self._calculate_risk_relevance(block, filters)
            
            if risk_score > 0:
                results.append(block.to_dict())
                relevance_scores.append(risk_score)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_market_regime_query(self, 
                                   agent_id: str, 
                                   filters: List[QueryFilter],
                                   limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute market regime query"""
        
        # Get market regime blocks
        regime_blocks = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.MARKET_REGIME,
            limit=limit
        )
        
        market_conditions = self.memory_manager.search_memory_blocks(
            agent_id=agent_id,
            block_type=MemoryBlockType.MARKET_CONDITIONS,
            limit=limit
        )
        
        results = []
        relevance_scores = []
        
        all_market_blocks = regime_blocks + market_conditions
        
        for block in all_market_blocks:
            regime_score = self._calculate_regime_relevance(block, filters)
            
            if regime_score > 0:
                results.append(block.to_dict())
                relevance_scores.append(regime_score)
        
        return results[:limit], relevance_scores[:limit]
    
    def _execute_composite_query(self, 
                               agent_id: str, 
                               search_text: str,
                               filters: List[QueryFilter],
                               limit: int) -> Tuple[List[Dict], List[float]]:
        """Execute composite query combining multiple types"""
        
        # Execute multiple query types and combine results
        partial_results = []
        
        # Text search
        text_results, text_scores = self._execute_text_search(agent_id, search_text, filters, limit)
        for result, score in zip(text_results, text_scores):
            partial_results.append((result, score * 0.4))  # Weight for text search
        
        # Pattern match
        pattern_results, pattern_scores = self._execute_pattern_match(agent_id, filters, limit)
        for result, score in zip(pattern_results, pattern_scores):
            partial_results.append((result, score * 0.3))  # Weight for pattern match
        
        # Performance analysis
        perf_results, perf_scores = self._execute_performance_analysis(agent_id, filters, limit)
        for result, score in zip(perf_results, perf_scores):
            partial_results.append((result, score * 0.3))  # Weight for performance
        
        # Combine and deduplicate results
        result_dict = {}
        for result, score in partial_results:
            result_id = result.get("id", hash(str(result)))
            if result_id not in result_dict or score > result_dict[result_id]:
                result_dict[result_id] = score
        
        results = []
        relevance_scores = []
        
        # Sort by combined score
        sorted_results = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)
        
        for result_id, score in sorted_results[:limit]:
            # Find the original result
            for result, _ in partial_results:
                if result.get("id", hash(str(result))) == result_id:
                    results.append(result)
                    relevance_scores.append(score)
                    break
        
        return results, relevance_scores
    
    def _calculate_text_relevance(self, search_text: str, result: Dict) -> float:
        """Calculate text-based relevance score"""
        score = 0.0
        
        # Simple keyword matching
        search_words = search_text.lower().split()
        result_text = f"{result.get('title', '')} {result.get('content', '')}".lower()
        
        for word in search_words:
            if word in result_text:
                score += 1.0 / len(search_words)
        
        # Boost for title matches
        if any(word in result.get('title', '').lower() for word in search_words):
            score *= 1.5
        
        return min(score, 1.0)
    
    def _calculate_temporal_relevance(self, block, time_range: Tuple[datetime, datetime], filters: List[QueryFilter]) -> float:
        """Calculate temporal relevance score"""
        score = 0.0
        
        # Check if block falls within time range
        if time_range:
            created_at = block.metadata.created_at
            if time_range[0] <= created_at <= time_range[1]:
                score += 0.5
        
        # Recent blocks get higher scores
        days_old = (datetime.now() - block.metadata.created_at).days
        if days_old < 7:
            score += 0.5
        elif days_old < 30:
            score += 0.3
        elif days_old < 90:
            score += 0.1
        
        # Boost for frequently accessed blocks
        if block.metadata.access_count > 10:
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_semantic_similarity(self, search_text: str, block) -> float:
        """Calculate semantic similarity score"""
        # Simple character-based similarity for now
        search_lower = search_text.lower()
        block_text = f"{block.title} {str(block.content)}".lower()
        
        # Jaccard similarity on words
        search_words = set(search_lower.split())
        block_words = set(block_text.split())
        
        if not search_words:
            return 0.0
        
        intersection = len(search_words.intersection(block_words))
        union = len(search_words.union(block_words))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_strategy_relevance(self, block, filters: List[QueryFilter]) -> float:
        """Calculate strategy-related relevance score"""
        score = 0.0
        
        # Boost for strategy-related blocks
        if block.block_type == MemoryBlockType.TRADING_STRATEGY:
            score += 0.6
        
        if block.block_type == MemoryBlockType.STRATEGY_EVOLUTION:
            score += 0.8
        
        # Check metadata for strategy tags
        strategy_tags = ["strategy", "trading", "evolution"]
        if any(tag in block.metadata.tags for tag in strategy_tags):
            score += 0.4
        
        # Recent evolution gets higher score
        if block.block_type == MemoryBlockType.STRATEGY_EVOLUTION:
            days_old = (datetime.now() - block.metadata.created_at).days
            if days_old < 30:
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_risk_relevance(self, block, filters: List[QueryFilter]) -> float:
        """Calculate risk-related relevance score"""
        score = 0.0
        
        # Boost for high priority risk blocks
        if block.metadata.priority in [MemoryPriority.CRITICAL, MemoryPriority.HIGH]:
            score += 0.6
        
        # Check for risk-related content
        risk_keywords = ["risk", "loss", "drawdown", "volatility", "correlation"]
        content_text = f"{block.title} {str(block.content)}".lower()
        
        for keyword in risk_keywords:
            if keyword in content_text:
                score += 0.2
        
        # Recent risk events get higher score
        days_old = (datetime.now() - block.metadata.created_at).days
        if days_old < 30:
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_regime_relevance(self, block, filters: List[QueryFilter]) -> float:
        """Calculate market regime relevance score"""
        score = 0.0
        
        # Market regime blocks get high base score
        if block.block_type == MemoryBlockType.MARKET_REGIME:
            score += 0.8
        
        # Recent regime changes get higher score
        days_old = (datetime.now() - block.metadata.created_at).days
        if days_old < 7:
            score += 0.4
        elif days_old < 30:
            score += 0.2
        
        # Boost for blocks with market data
        if "regime" in block.title.lower() or "market" in block.title.lower():
            score += 0.3
        
        return min(score, 1.0)
    
    def _passes_filters(self, result: Dict, filters: List[QueryFilter]) -> bool:
        """Check if result passes all filters"""
        if not filters:
            return True
        
        for filter_obj in filters:
            field_value = self._get_field_value(result, filter_obj.field)
            
            if not self._apply_operator(field_value, filter_obj.operator, filter_obj.value):
                return False
        
        return True
    
    def _get_field_value(self, obj: Dict, field: str) -> Any:
        """Get field value from object"""
        # Handle nested fields
        parts = field.split('.')
        current = obj
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current
    
    def _apply_operator(self, field_value: Any, operator: QueryOperator, filter_value: Any) -> bool:
        """Apply operator to field value"""
        if operator == QueryOperator.EQUALS:
            return field_value == filter_value
        elif operator == QueryOperator.NOT_EQUALS:
            return field_value != filter_value
        elif operator == QueryOperator.GREATER_THAN:
            return field_value > filter_value
        elif operator == QueryOperator.LESS_THAN:
            return field_value < filter_value
        elif operator == QueryOperator.CONTAINS:
            return filter_value in str(field_value)
        elif operator == QueryOperator.STARTS_WITH:
            return str(field_value).startswith(filter_value)
        elif operator == QueryOperator.ENDS_WITH:
            return str(field_value).endswith(filter_value)
        elif operator == QueryOperator.IN:
            return field_value in filter_value
        elif operator == QueryOperator.REGEX:
            return bool(re.search(filter_value, str(field_value)))
        
        return True
    
    def _create_query_summary(self, results: List[Dict], query_type: QueryType) -> Dict[str, Any]:
        """Create summary of query results"""
        
        if not results:
            return {"message": "No results found"}
        
        summary = {
            "total_blocks": len(results),
            "block_types": {},
            "time_range": {"earliest": None, "latest": None},
            "top_keywords": [],
            "insights": []
        }
        
        # Analyze result types
        for result in results:
            block_type = result.get("block_type", "unknown")
            summary["block_types"][block_type] = summary["block_types"].get(block_type, 0) + 1
        
        # Find time range
        timestamps = []
        for result in results:
            if "metadata" in result and "created_at" in result["metadata"]:
                try:
                    timestamp = datetime.fromisoformat(result["metadata"]["created_at"])
                    timestamps.append(timestamp)
                except:
                    pass
        
        if timestamps:
            summary["time_range"]["earliest"] = min(timestamps).isoformat()
            summary["time_range"]["latest"] = max(timestamps).isoformat()
        
        # Extract top keywords
        all_text = " ".join([
            f"{result.get('title', '')} {result.get('content', '')}"
            for result in results
        ]).lower()
        
        words = re.findall(r'\b\w+\b', all_text)
        word_freq = Counter(words)
        summary["top_keywords"] = [word for word, count in word_freq.most_common(10)]
        
        # Generate insights based on query type
        if query_type == QueryType.PERFORMANCE_ANALYSIS:
            summary["insights"].append("Performance data available for analysis")
        elif query_type == QueryType.RISK_ASSESSMENT:
            summary["insights"].append("Risk-related memory blocks identified")
        elif query_type == QueryType.MARKET_REGIME:
            summary["insights"].append("Market regime information found")
        
        return summary


class PatternMatcher:
    """Matches patterns in memory blocks"""
    
    def match_pattern(self, block, filters: List[QueryFilter]) -> float:
        """Match pattern against filters"""
        score = 0.0
        
        # Pattern-specific scoring
        if hasattr(block, 'trading_data') and block.trading_data:
            # Check success rate
            success_rate = block.trading_data.get('success_rate', 0)
            if success_rate > 0.7:
                score += 0.6
            elif success_rate > 0.5:
                score += 0.4
            
            # Check confidence
            confidence = block.metadata.confidence_score
            score += confidence * 0.4
        
        return min(score, 1.0)


class PerformanceAnalyzer:
    """Analyzes performance relevance"""
    
    def analyze_block_relevance(self, block, filters: List[QueryFilter]) -> float:
        """Analyze performance block relevance"""
        score = 0.0
        
        # Recent performance gets higher score
        days_old = (datetime.now() - block.metadata.created_at).days
        if days_old < 7:
            score += 0.7
        elif days_old < 30:
            score += 0.5
        elif days_old < 90:
            score += 0.3
        
        # High access frequency indicates importance
        if block.metadata.access_count > 5:
            score += 0.3
        
        # Check for performance-related content
        perf_keywords = ["return", "profit", "win_rate", "drawdown", "sharpe"]
        content_text = f"{block.title} {str(block.content)}".lower()
        
        for keyword in perf_keywords:
            if keyword in content_text:
                score += 0.1
        
        return min(score, 1.0)


class CorrelationCalculator:
    """Calculates correlation relevance"""
    
    def calculate_relevance(self, correlation_data: Dict, filters: List[QueryFilter]) -> float:
        """Calculate correlation relevance score"""
        score = 0.0
        
        # Check for high correlations
        if isinstance(correlation_data, dict):
            correlations = correlation_data.get('correlations', {})
            high_correlations = [abs(v) for v in correlations.values() if abs(v) > 0.7]
            
            if high_correlations:
                score += len(high_correlations) * 0.2
        
        return min(score, 1.0)


class StrategicQueryInterface:
    """High-level interface for strategic memory queries"""
    
    def __init__(self, query_engine: QueryEngine):
        self.query_engine = query_engine
    
    def get_trading_opportunities(self, agent_id: str, symbol: str = None) -> List[StrategyInsight]:
        """Get trading opportunities from memory"""
        
        filters = []
        if symbol:
            filters.append(QueryFilter("symbol", QueryOperator.EQUALS, symbol))
        
        query_result = self.query_engine.execute_query(
            QueryType.PATTERN_MATCH,
            agent_id,
            filters,
            limit=20
        )
        
        insights = []
        for result in query_result.results:
            if isinstance(result, dict) and result.get("trading_data"):
                trading_data = result["trading_data"]
                if trading_data.get("success_rate", 0) > 0.6:
                    insight = StrategyInsight(
                        insight_id=f"opp_{result.get('id', 'unknown')}",
                        category="trading_opportunity",
                        title=result.get("title", "Trading Pattern"),
                        description="High success rate pattern identified",
                        confidence=result["metadata"].get("confidence_score", 0.7),
                        impact_score=trading_data.get("success_rate", 0),
                        time_sensitivity="high",
                        actionable_recommendations=[
                            f"Consider using {result.get('title', 'this pattern')} for {symbol or 'current market'}",
                            "Monitor pattern performance and adjust parameters"
                        ],
                        related_patterns=[result.get("title", "")],
                        risk_level="medium"
                    )
                    insights.append(insight)
        
        return insights
    
    def get_risk_assessment(self, agent_id: str, current_positions: List[str] = None) -> List[StrategyInsight]:
        """Get risk assessment from memory"""
        
        query_result = self.query_engine.execute_query(
            QueryType.RISK_ASSESSMENT,
            agent_id,
            limit=15
        )
        
        insights = []
        for result in query_result.results:
            insight = StrategyInsight(
                insight_id=f"risk_{result.get('id', 'unknown')}",
                category="risk_assessment",
                title=result.get("title", "Risk Factor"),
                description=result.get("content", "")[:200],
                confidence=result["metadata"].get("confidence_score", 0.6),
                impact_score=0.8,
                time_sensitivity="urgent",
                actionable_recommendations=[
                    "Review risk management parameters",
                    "Consider position size adjustments"
                ],
                related_patterns=[],
                risk_level="high"
            )
            insights.append(insight)
        
        return insights
    
    def get_market_context(self, agent_id: str) -> MarketMemoryContext:
        """Get current market context from memory"""
        
        # Get recent market conditions
        market_query = self.query_engine.execute_query(
            QueryType.MARKET_REGIME,
            agent_id,
            limit=10
        )
        
        # Get recent patterns
        pattern_query = self.query_engine.execute_query(
            QueryType.PATTERN_MATCH,
            agent_id,
            limit=20
        )
        
        # Get performance metrics
        performance_query = self.query_engine.execute_query(
            QueryType.PERFORMANCE_ANALYSIS,
            agent_id,
            limit=10
        )
        
        # Build market context
        current_regime = "unknown"
        successful_patterns = []
        failed_patterns = []
        performance_metrics = {}
        
        for result in market_query.results:
            if isinstance(result, dict) and "current_regime" in result.get("content", ""):
                current_regime = result["content"]["current_regime"] if isinstance(result["content"], dict) else "trending"
        
        for result in pattern_query.results:
            if isinstance(result, dict) and result.get("trading_data"):
                success_rate = result["trading_data"].get("success_rate", 0)
                if success_rate > 0.6:
                    successful_patterns.append(result)
                else:
                    failed_patterns.append(result)
        
        for result in performance_query.results:
            if isinstance(result, dict) and "content" in result:
                if isinstance(result["content"], dict):
                    performance_metrics.update(result["content"])
        
        return MarketMemoryContext(
            current_regime=current_regime,
            recent_volatility=0.15,  # Default value
            dominant_trends=["bullish"],
            risk_events=[],
            successful_patterns=[],
            failed_patterns=[],
            performance_metrics=performance_metrics,
            correlations={}
        )
    
    def compare_strategies(self, agent_id: str, strategy_names: List[str]) -> Dict[str, Any]:
        """Compare multiple strategies from memory"""
        
        results = {}
        
        for strategy_name in strategy_names:
            filters = [QueryFilter("content", QueryOperator.CONTAINS, strategy_name)]
            
            query_result = self.query_engine.execute_query(
                QueryType.STRATEGY_COMPARISON,
                agent_id,
                filters,
                limit=10
            )
            
            strategy_data = []
            for result in query_result.results:
                if strategy_name.lower() in result.get("content", "").lower():
                    strategy_data.append(result)
            
            results[strategy_name] = {
                "data_points": len(strategy_data),
                "performance_indicators": self._extract_performance_indicators(strategy_data),
                "recent_activity": len([r for r in strategy_data if self._is_recent(r)]),
                "success_rate": self._calculate_strategy_success_rate(strategy_data)
            }
        
        return results
    
    def get_adaptive_recommendations(self, agent_id: str) -> List[StrategyInsight]:
        """Get adaptive recommendations based on recent learning"""
        
        # Get recent strategy evolution
        evolution_query = self.query_engine.execute_query(
            QueryType.STRATEGY_COMPARISON,
            agent_id,
            limit=15
        )
        
        insights = []
        for result in evolution_query.results:
            if result.get("metadata", {}).get("source_agent") == agent_id:
                insight = StrategyInsight(
                    insight_id=f"adaptive_{result.get('id', 'unknown')}",
                    category="adaptive_recommendation",
                    title=f"Adaptive Learning: {result.get('title', 'Strategy Change')}",
                    description=result.get("content", "")[:300],
                    confidence=result["metadata"].get("confidence_score", 0.7),
                    impact_score=0.6,
                    time_sensitivity="medium",
                    actionable_recommendations=[
                        "Consider implementing learned adaptations",
                        "Monitor performance of new parameters"
                    ],
                    related_patterns=[],
                    risk_level="low"
                )
                insights.append(insight)
        
        return insights
    
    def _extract_performance_indicators(self, strategy_data: List[Dict]) -> Dict[str, float]:
        """Extract performance indicators from strategy data"""
        indicators = {}
        
        if strategy_data:
            # Simple aggregation of metrics
            metrics = []
            for data in strategy_data:
                if isinstance(data.get("content"), dict):
                    metrics.append(data["content"])
            
            if metrics:
                # Calculate averages
                numeric_fields = ["success_rate", "confidence", "impact"]
                for field in numeric_fields:
                    values = [m.get(field, 0) for m in metrics if field in m]
                    if values:
                        indicators[f"avg_{field}"] = sum(values) / len(values)
        
        return indicators
    
    def _is_recent(self, data: Dict) -> bool:
        """Check if data is recent (within last 30 days)"""
        if "metadata" not in data or "created_at" not in data["metadata"]:
            return False
        
        try:
            created_at = datetime.fromisoformat(data["metadata"]["created_at"])
            return (datetime.now() - created_at).days <= 30
        except:
            return False
    
    def _calculate_strategy_success_rate(self, strategy_data: List[Dict]) -> float:
        """Calculate success rate for strategy"""
        if not strategy_data:
            return 0.0
        
        success_indicators = ["win", "profitable", "successful"]
        total_count = len(strategy_data)
        success_count = 0
        
        for data in strategy_data:
            content = str(data.get("content", "")).lower()
            if any(indicator in content for indicator in success_indicators):
                success_count += 1
        
        return success_count / total_count if total_count > 0 else 0.0