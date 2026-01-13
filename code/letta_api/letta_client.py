#!/usr/bin/env python3
"""
Comprehensive Letta REST API Client for Dashboard Integration

Provides advanced functionality for memory queries, agent management,
trading insights, and dashboard integration with comprehensive error handling,
caching, and performance monitoring.
"""

import asyncio
import json
import logging
import time
import hashlib
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import requests
import aiohttp
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Agent roles for classification and routing"""
    STRATEGIST = "strategist"
    ANALYST = "analyst"
    RISK_MANAGER = "risk_manager"
    COORDINATOR = "coordinator"
    SPECIALIST = "specialist"
    OBSERVER = "observer"


class MemoryBlockType(Enum):
    """Memory block types for different kinds of agent knowledge"""
    TRADING_STRATEGY = "trading_strategy"
    MARKET_CONDITIONS = "market_conditions"
    RISK_PARAMETERS = "risk_parameters"
    LEARNED_PATTERNS = "learned_patterns"
    PERFORMANCE_METRICS = "performance_metrics"
    TRADE_OUTCOMES = "trade_outcomes"
    MARKET_REGIME = "market_regime"
    CORRELATION_MATRICES = "correlation_matrices"
    SYSTEM_CONTEXT = "system_context"
    USER_CONTEXT = "user_context"
    LONG_TERM = "long_term"
    RECENT = "recent"
    SCRATCH = "scratch"


class Priority(Enum):
    """Memory block priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVE = "archive"


class QueryType(Enum):
    """Types of memory queries"""
    TEXT_SEARCH = "text_search"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    PATTERN_MATCHING = "pattern_matching"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    TEMPORAL_FILTER = "temporal_filter"
    TAG_BASED = "tag_based"
    METADATA_FILTER = "metadata_filter"
    COMPOSITE = "composite"


@dataclass
class AgentInfo:
    """Agent information structure"""
    id: str
    name: str
    role: str
    description: str
    capabilities: List[str]
    status: str
    created_at: datetime
    last_active: Optional[datetime] = None
    memory_blocks_count: int = 0
    performance_score: float = 0.0


@dataclass
class MemoryBlock:
    """Memory block structure"""
    id: str
    agent_id: str
    block_type: MemoryBlockType
    title: str
    content: str
    metadata: Dict[str, Any]
    tags: List[str]
    priority: Priority
    created_at: datetime
    updated_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    checksum: Optional[str] = None


@dataclass
class SearchResult:
    """Search result structure"""
    block_id: str
    agent_id: str
    title: str
    content: str
    block_type: MemoryBlockType
    relevance_score: float
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: datetime


@dataclass
class TradingPattern:
    """Trading pattern structure"""
    id: str
    symbol: str
    pattern_type: str
    success_rate: float
    confidence: float
    conditions: Dict[str, Any]
    entry_signals: List[str]
    exit_signals: List[str]
    risk_metrics: Dict[str, Any]
    performance_history: List[Dict[str, Any]]
    created_at: datetime
    last_validated: Optional[datetime] = None


@dataclass
class TradeEvent:
    """Trade event structure"""
    trade_id: str
    symbol: str
    action: str
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    pnl: float
    strategy: str
    confidence: float
    outcome: str
    timestamp: datetime
    metadata: Dict[str, Any]


class LettaAPIClient:
    """
    Comprehensive Letta REST API Client with advanced features for dashboard integration
    
    Features:
    - Advanced memory query capabilities
    - Agent management and coordination
    - Trading pattern learning and analysis
    - Memory optimization and cleanup
    - Backup and restore functionality
    - Performance monitoring and analytics
    - Caching and rate limiting
    - Error handling and retry logic
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8283",
        api_key: str = "your-secret-api-key",
        session_timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 0.3,
        cache_ttl: int = 300,
        rate_limit: float = 10.0,
        enable_caching: bool = True,
        enable_monitoring: bool = True
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session_timeout = session_timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.cache_ttl = cache_ttl
        self.rate_limit = rate_limit
        self.enable_caching = enable_caching
        self.enable_monitoring = enable_monitoring
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_backoff,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LettaAPI-Client/2.0"
        }
        
        # Internal state
        self._cache = {} if enable_caching else None
        self._rate_limiter = None
        self._monitoring_data = {
            "requests_count": 0,
            "errors_count": 0,
            "avg_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        logger.info(f"Letta API Client initialized - URL: {base_url}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None,
        params: Dict = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Make HTTP request with caching, retry logic, and monitoring"""
        
        # Check cache for GET requests
        if method.upper() == "GET" and use_cache and self._cache:
            cache_key = self._generate_cache_key(method, endpoint, params)
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                    self._monitoring_data["cache_hits"] += 1
                    logger.debug(f"Cache hit for {endpoint}")
                    return cache_entry["data"]
                else:
                    # Expired cache
                    del self._cache[cache_key]
        
        # Rate limiting (simple implementation)
        if hasattr(self, '_last_request_time'):
            time_since_last = time.time() - self._last_request_time
            if time_since_last < (1.0 / self.rate_limit):
                time.sleep((1.0 / self.rate_limit) - time_since_last)
        
        # Prepare request
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        start_time = time.time()
        
        try:
            # Make request
            if method.upper() == "GET":
                response = self.session.get(url, headers=self.headers, params=params, timeout=self.session_timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=self.headers, json=data, params=params, timeout=self.session_timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=self.headers, json=data, params=params, timeout=self.session_timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=self.headers, params=params, timeout=self.session_timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Update monitoring
            response_time = time.time() - start_time
            self._update_monitoring_stats(response_time, True)
            self._last_request_time = time.time()
            
            # Parse response
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"text": response.text, "status_code": response.status_code}
            
            response.raise_for_status()
            
            # Cache successful GET responses
            if method.upper() == "GET" and use_cache and self._cache:
                cache_key = self._generate_cache_key(method, endpoint, params)
                self._cache[cache_key] = {
                    "data": response_data,
                    "timestamp": time.time()
                }
                self._monitoring_data["cache_misses"] += 1
            
            return response_data
        
        except requests.exceptions.RequestException as e:
            self._monitoring_data["errors_count"] += 1
            error_msg = f"API request failed: {method} {endpoint} - {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}

    def _generate_cache_key(self, method: str, endpoint: str, params: Dict = None) -> str:
        """Generate cache key for request"""
        key_data = f"{method}:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _update_monitoring_stats(self, response_time: float, success: bool):
        """Update monitoring statistics"""
        if not self.enable_monitoring:
            return
        
        self._monitoring_data["requests_count"] += 1
        
        # Update average response time
        current_avg = self._monitoring_data["avg_response_time"]
        count = self._monitoring_data["requests_count"]
        self._monitoring_data["avg_response_time"] = (current_avg * (count - 1) + response_time) / count

    def _clear_cache(self):
        """Clear the request cache"""
        if self._cache:
            self._cache.clear()
            logger.info("Cache cleared")

    # === AGENT MANAGEMENT ===
    
    def get_agents(self, include_inactive: bool = False) -> List[AgentInfo]:
        """Get all agents with detailed information"""
        response = self._make_request("GET", "agents")
        
        if "error" in response:
            return []
        
        agents = []
        for agent_data in response.get("agents", []):
            try:
                agent = AgentInfo(
                    id=agent_data["id"],
                    name=agent_data["name"],
                    role=agent_data.get("role", "unknown"),
                    description=agent_data.get("description", ""),
                    capabilities=agent_data.get("capabilities", []),
                    status=agent_data.get("status", "unknown"),
                    created_at=datetime.fromisoformat(agent_data["created_at"]),
                    last_active=datetime.fromisoformat(agent_data["last_active"]) if agent_data.get("last_active") else None,
                    memory_blocks_count=agent_data.get("memory_blocks_count", 0),
                    performance_score=agent_data.get("performance_score", 0.0)
                )
                agents.append(agent)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse agent data: {e}")
                continue
        
        # Filter inactive agents if requested
        if not include_inactive:
            agents = [a for a in agents if a.status == "active"]
        
        return agents

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get specific agent by ID"""
        response = self._make_request("GET", f"agents/{agent_id}")
        
        if "error" in response:
            return None
        
        agent_data = response.get("agent", {})
        try:
            return AgentInfo(
                id=agent_data["id"],
                name=agent_data["name"],
                role=agent_data.get("role", "unknown"),
                description=agent_data.get("description", ""),
                capabilities=agent_data.get("capabilities", []),
                status=agent_data.get("status", "unknown"),
                created_at=datetime.fromisoformat(agent_data["created_at"]),
                last_active=datetime.fromisoformat(agent_data["last_active"]) if agent_data.get("last_active") else None,
                memory_blocks_count=agent_data.get("memory_blocks_count", 0),
                performance_score=agent_data.get("performance_score", 0.0)
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse agent data: {e}")
            return None

    def get_agent_by_name(self, agent_name: str) -> Optional[AgentInfo]:
        """Get agent by name"""
        agents = self.get_agents()
        for agent in agents:
            if agent.name == agent_name:
                return agent
        return None

    def create_agent(
        self,
        name: str,
        role: AgentRole,
        description: str = "",
        capabilities: List[str] = None,
        system_prompt: str = "",
        memory_blocks_config: List[Dict] = None
    ) -> Optional[str]:
        """Create a new agent with configuration"""
        
        agent_config = {
            "name": name,
            "role": role.value,
            "description": description,
            "capabilities": capabilities or [],
            "system_prompt": system_prompt,
            "memory_blocks_config": memory_blocks_config or []
        }
        
        response = self._make_request("POST", "agents", data=agent_config)
        
        if "error" in response:
            logger.error(f"Failed to create agent: {response['error']}")
            return None
        
        self._clear_cache()  # Clear cache to reflect new agent
        return response.get("agent_id")

    def update_agent(self, agent_id: str, **kwargs) -> bool:
        """Update agent configuration"""
        response = self._make_request("PUT", f"agents/{agent_id}", data=kwargs)
        
        if "error" in response:
            logger.error(f"Failed to update agent: {response['error']}")
            return False
        
        self._clear_cache()  # Clear cache to reflect changes
        return True

    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent"""
        response = self._make_request("DELETE", f"agents/{agent_id}")
        
        if "error" in response:
            logger.error(f"Failed to delete agent: {response['error']}")
            return False
        
        self._clear_cache()  # Clear cache to reflect changes
        return True

    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return self._make_request("GET", f"agents/{agent_id}/performance")

    # === MEMORY MANAGEMENT ===
    
    def get_agent_memory(self, agent_id: str, include_metadata: bool = True) -> List[MemoryBlock]:
        """Get all memory blocks for an agent"""
        params = {"include_metadata": include_metadata}
        response = self._make_request("GET", f"agents/{agent_id}/memory", params=params)
        
        if "error" in response:
            return []
        
        memory_blocks = []
        for block_data in response.get("blocks", []):
            try:
                block = MemoryBlock(
                    id=block_data["id"],
                    agent_id=agent_id,
                    block_type=MemoryBlockType(block_data["block_type"]),
                    title=block_data["title"],
                    content=block_data["content"],
                    metadata=block_data.get("metadata", {}),
                    tags=block_data.get("tags", []),
                    priority=Priority(block_data.get("priority", "medium")),
                    created_at=datetime.fromisoformat(block_data["created_at"]),
                    updated_at=datetime.fromisoformat(block_data["updated_at"]) if block_data.get("updated_at") else None,
                    access_count=block_data.get("access_count", 0),
                    last_accessed=datetime.fromisoformat(block_data["last_accessed"]) if block_data.get("last_accessed") else None,
                    checksum=block_data.get("checksum")
                )
                memory_blocks.append(block)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse memory block: {e}")
                continue
        
        return memory_blocks

    def add_memory_block(
        self,
        agent_id: str,
        block_type: MemoryBlockType,
        title: str,
        content: str,
        metadata: Dict = None,
        tags: List[str] = None,
        priority: Priority = Priority.MEDIUM
    ) -> Optional[str]:
        """Add a new memory block to an agent"""
        
        memory_config = {
            "block_type": block_type.value,
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "tags": tags or [],
            "priority": priority.value
        }
        
        response = self._make_request("POST", f"agents/{agent_id}/memory", data=memory_config)
        
        if "error" in response:
            logger.error(f"Failed to add memory block: {response['error']}")
            return None
        
        self._clear_cache()  # Clear cache to reflect new memory
        return response.get("block_id")

    def update_memory_block(
        self,
        agent_id: str,
        block_id: str,
        content: str = None,
        title: str = None,
        metadata: Dict = None,
        tags: List[str] = None,
        priority: Priority = None
    ) -> bool:
        """Update an existing memory block"""
        
        update_data = {}
        if content is not None:
            update_data["content"] = content
        if title is not None:
            update_data["title"] = title
        if metadata is not None:
            update_data["metadata"] = metadata
        if tags is not None:
            update_data["tags"] = tags
        if priority is not None:
            update_data["priority"] = priority.value
        
        response = self._make_request("PUT", f"agents/{agent_id}/memory/{block_id}", data=update_data)
        
        if "error" in response:
            logger.error(f"Failed to update memory block: {response['error']}")
            return False
        
        self._clear_cache()  # Clear cache to reflect changes
        return True

    def delete_memory_block(self, agent_id: str, block_id: str) -> bool:
        """Delete a memory block"""
        response = self._make_request("DELETE", f"agents/{agent_id}/memory/{block_id}")
        
        if "error" in response:
            logger.error(f"Failed to delete memory block: {response['error']}")
            return False
        
        self._clear_cache()  # Clear cache to reflect changes
        return True

    def get_memory_block(self, agent_id: str, block_id: str) -> Optional[MemoryBlock]:
        """Get a specific memory block"""
        response = self._make_request("GET", f"agents/{agent_id}/memory/{block_id}")
        
        if "error" in response:
            return None
        
        block_data = response.get("block", {})
        try:
            return MemoryBlock(
                id=block_data["id"],
                agent_id=agent_id,
                block_type=MemoryBlockType(block_data["block_type"]),
                title=block_data["title"],
                content=block_data["content"],
                metadata=block_data.get("metadata", {}),
                tags=block_data.get("tags", []),
                priority=Priority(block_data.get("priority", "medium")),
                created_at=datetime.fromisoformat(block_data["created_at"]),
                updated_at=datetime.fromisoformat(block_data["updated_at"]) if block_data.get("updated_at") else None,
                access_count=block_data.get("access_count", 0),
                last_accessed=datetime.fromisoformat(block_data["last_accessed"]) if block_data.get("last_accessed") else None,
                checksum=block_data.get("checksum")
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse memory block: {e}")
            return None

    # === ADVANCED MEMORY QUERIES ===
    
    def search_memory(
        self,
        agent_id: Optional[str] = None,
        query: str = "",
        query_type: QueryType = QueryType.TEXT_SEARCH,
        filters: Dict = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "desc"
    ) -> List[SearchResult]:
        """Advanced memory search with multiple query types and filters"""
        
        search_data = {
            "query": query,
            "query_type": query_type.value,
            "filters": filters or {},
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        if agent_id:
            search_data["agent_id"] = agent_id
        
        response = self._make_request("POST", "memory/search", data=search_data)
        
        if "error" in response:
            return []
        
        results = []
        for result_data in response.get("results", []):
            try:
                result = SearchResult(
                    block_id=result_data["block_id"],
                    agent_id=result_data["agent_id"],
                    title=result_data["title"],
                    content=result_data["content"],
                    block_type=MemoryBlockType(result_data["block_type"]),
                    relevance_score=result_data.get("relevance_score", 0.0),
                    metadata=result_data.get("metadata", {}),
                    tags=result_data.get("tags", []),
                    created_at=datetime.fromisoformat(result_data["created_at"])
                )
                results.append(result)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse search result: {e}")
                continue
        
        return results

    def semantic_search_memory(
        self,
        query: str,
        agent_id: Optional[str] = None,
        similarity_threshold: float = 0.7,
        limit: int = 20
    ) -> List[SearchResult]:
        """Semantic similarity search across agent memory"""
        
        search_data = {
            "query": query,
            "query_type": QueryType.SEMANTIC_SIMILARITY.value,
            "similarity_threshold": similarity_threshold,
            "limit": limit
        }
        
        if agent_id:
            search_data["agent_id"] = agent_id
        
        response = self._make_request("POST", "memory/semantic-search", data=search_data)
        
        if "error" in response:
            return []
        
        results = []
        for result_data in response.get("results", []):
            try:
                result = SearchResult(
                    block_id=result_data["block_id"],
                    agent_id=result_data["agent_id"],
                    title=result_data["title"],
                    content=result_data["content"],
                    block_type=MemoryBlockType(result_data["block_type"]),
                    relevance_score=result_data.get("relevance_score", 0.0),
                    metadata=result_data.get("metadata", {}),
                    tags=result_data.get("tags", []),
                    created_at=datetime.fromisoformat(result_data["created_at"])
                )
                results.append(result)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse semantic search result: {e}")
                continue
        
        return results

    def pattern_search_memory(
        self,
        pattern: str,
        agent_id: Optional[str] = None,
        pattern_type: str = "regex",
        case_sensitive: bool = False,
        limit: int = 20
    ) -> List[SearchResult]:
        """Pattern-based memory search (regex, wildcards, etc.)"""
        
        search_data = {
            "pattern": pattern,
            "query_type": QueryType.PATTERN_MATCHING.value,
            "pattern_type": pattern_type,
            "case_sensitive": case_sensitive,
            "limit": limit
        }
        
        if agent_id:
            search_data["agent_id"] = agent_id
        
        response = self._make_request("POST", "memory/pattern-search", data=search_data)
        
        if "error" in response:
            return []
        
        results = []
        for result_data in response.get("results", []):
            try:
                result = SearchResult(
                    block_id=result_data["block_id"],
                    agent_id=result_data["agent_id"],
                    title=result_data["title"],
                    content=result_data["content"],
                    block_type=MemoryBlockType(result_data["block_type"]),
                    relevance_score=result_data.get("relevance_score", 0.0),
                    metadata=result_data.get("metadata", {}),
                    tags=result_data.get("tags", []),
                    created_at=datetime.fromisoformat(result_data["created_at"])
                )
                results.append(result)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse pattern search result: {e}")
                continue
        
        return results

    def temporal_search_memory(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        agent_id: Optional[str] = None,
        time_field: str = "created_at",
        limit: int = 50
    ) -> List[SearchResult]:
        """Temporal-based memory search"""
        
        search_data = {
            "query_type": QueryType.TEMPORAL_FILTER.value,
            "start_time": start_time.isoformat(),
            "time_field": time_field,
            "limit": limit
        }
        
        if end_time:
            search_data["end_time"] = end_time.isoformat()
        
        if agent_id:
            search_data["agent_id"] = agent_id
        
        response = self._make_request("POST", "memory/temporal-search", data=search_data)
        
        if "error" in response:
            return []
        
        results = []
        for result_data in response.get("results", []):
            try:
                result = SearchResult(
                    block_id=result_data["block_id"],
                    agent_id=result_data["agent_id"],
                    title=result_data["title"],
                    content=result_data["content"],
                    block_type=MemoryBlockType(result_data["block_type"]),
                    relevance_score=result_data.get("relevance_score", 0.0),
                    metadata=result_data.get("metadata", {}),
                    tags=result_data.get("tags", []),
                    created_at=datetime.fromisoformat(result_data["created_at"])
                )
                results.append(result)
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse temporal search result: {e}")
                continue
        
        return results

    # === AGENT COMMUNICATION ===
    
    def send_message(
        self,
        sender_agent_id: str,
        receiver_agent_id: str,
        subject: str,
        content: str,
        priority: str = "normal",
        message_type: str = "direct"
    ) -> Optional[str]:
        """Send message between agents"""
        
        message_data = {
            "sender_agent_id": sender_agent_id,
            "receiver_agent_id": receiver_agent_id,
            "subject": subject,
            "content": content,
            "priority": priority,
            "message_type": message_type
        }
        
        response = self._make_request("POST", "agents/message", data=message_data)
        
        if "error" in response:
            logger.error(f"Failed to send message: {response['error']}")
            return None
        
        return response.get("message_id")

    def broadcast_message(
        self,
        sender_agent_id: str,
        subject: str,
        content: str,
        target_roles: List[str] = None,
        target_agents: List[str] = None,
        priority: str = "normal"
    ) -> List[str]:
        """Broadcast message to multiple agents"""
        
        message_data = {
            "sender_agent_id": sender_agent_id,
            "subject": subject,
            "content": content,
            "priority": priority,
            "broadcast": True
        }
        
        if target_roles:
            message_data["target_roles"] = target_roles
        
        if target_agents:
            message_data["target_agents"] = target_agents
        
        response = self._make_request("POST", "agents/broadcast", data=message_data)
        
        if "error" in response:
            logger.error(f"Failed to broadcast message: {response['error']}")
            return []
        
        return response.get("message_ids", [])

    def get_agent_messages(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get messages for an agent"""
        
        params = {"limit": limit}
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()
        
        response = self._make_request("GET", f"agents/{agent_id}/messages", params=params)
        
        if "error" in response:
            return []
        
        return response.get("messages", [])

    # === MEMORY ORGANIZATION ===
    
    def organize_memory_blocks(
        self,
        agent_id: str,
        organization_type: str = "category",
        auto_cleanup: bool = True
    ) -> Dict[str, Any]:
        """Organize memory blocks by category, priority, or other criteria"""
        
        data = {
            "organization_type": organization_type,
            "auto_cleanup": auto_cleanup
        }
        
        response = self._make_request("POST", f"agents/{agent_id}/memory/organize", data=data)
        
        if "error" in response:
            logger.error(f"Failed to organize memory: {response['error']}")
            return {}
        
        return response

    def optimize_memory(
        self,
        agent_id: str,
        optimization_strategy: str = "hybrid",
        aggressive: bool = False,
        target_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """Optimize agent memory using various strategies"""
        
        data = {
            "optimization_strategy": optimization_strategy,
            "aggressive": aggressive
        }
        
        if target_size:
            data["target_size"] = target_size
        
        response = self._make_request("POST", f"agents/{agent_id}/memory/optimize", data=data)
        
        if "error" in response:
            logger.error(f"Failed to optimize memory: {response['error']}")
            return {}
        
        return response

    # === TRADING-SPECIFIC FUNCTIONS ===
    
    def create_trading_pattern(
        self,
        agent_id: str,
        symbol: str,
        pattern_type: str,
        success_rate: float,
        confidence: float,
        conditions: Dict[str, Any],
        entry_signals: List[str],
        exit_signals: List[str],
        risk_metrics: Dict[str, Any]
    ) -> Optional[str]:
        """Create a new trading pattern"""
        
        pattern_data = {
            "symbol": symbol,
            "pattern_type": pattern_type,
            "success_rate": success_rate,
            "confidence": confidence,
            "conditions": conditions,
            "entry_signals": entry_signals,
            "exit_signals": exit_signals,
            "risk_metrics": risk_metrics
        }
        
        # Create memory block for the trading pattern
        block_id = self.add_memory_block(
            agent_id=agent_id,
            block_type=MemoryBlockType.LEARNED_PATTERNS,
            title=f"Trading Pattern: {pattern_type} for {symbol}",
            content=json.dumps(pattern_data, indent=2),
            metadata={
                "pattern_type": "trading_pattern",
                "symbol": symbol,
                "success_rate": success_rate,
                "confidence": confidence,
                "created_by": "letta_client"
            },
            tags=["pattern", symbol.lower(), pattern_type.lower()],
            priority=Priority.HIGH
        )
        
        return block_id

    def get_trading_patterns(
        self,
        agent_id: str,
        symbol: Optional[str] = None,
        pattern_type: Optional[str] = None,
        min_success_rate: float = 0.0
    ) -> List[TradingPattern]:
        """Get trading patterns for an agent"""
        
        filters = {"min_success_rate": min_success_rate}
        if symbol:
            filters["symbol"] = symbol
        if pattern_type:
            filters["pattern_type"] = pattern_type
        
        results = self.search_memory(
            agent_id=agent_id,
            query="trading pattern",
            query_type=QueryType.TEXT_SEARCH,
            filters=filters,
            limit=100
        )
        
        patterns = []
        for result in results:
            if "trading_pattern" in result.metadata:
                try:
                    pattern_data = json.loads(result.content)
                    pattern = TradingPattern(
                        id=result.block_id,
                        symbol=pattern_data["symbol"],
                        pattern_type=pattern_data["pattern_type"],
                        success_rate=pattern_data["success_rate"],
                        confidence=pattern_data["confidence"],
                        conditions=pattern_data["conditions"],
                        entry_signals=pattern_data["entry_signals"],
                        exit_signals=pattern_data["exit_signals"],
                        risk_metrics=pattern_data["risk_metrics"],
                        performance_history=pattern_data.get("performance_history", []),
                        created_at=result.created_at
                    )
                    patterns.append(pattern)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to parse trading pattern: {e}")
                    continue
        
        return patterns

    def record_trade_outcome(
        self,
        agent_id: str,
        trade_event: TradeEvent
    ) -> bool:
        """Record a trade outcome for learning"""
        
        trade_data = asdict(trade_event)
        
        # Create memory block for the trade outcome
        block_id = self.add_memory_block(
            agent_id=agent_id,
            block_type=MemoryBlockType.TRADE_OUTCOMES,
            title=f"Trade Outcome: {trade_event.symbol} - {trade_event.trade_id}",
            content=json.dumps(trade_data, indent=2),
            metadata={
                "trade_type": "outcome",
                "symbol": trade_event.symbol,
                "outcome": trade_event.outcome,
                "pnl": trade_event.pnl,
                "strategy": trade_event.strategy,
                "recorded_by": "letta_client"
            },
            tags=["trade", trade_event.symbol.lower(), trade_event.strategy.lower(), trade_event.outcome.lower()],
            priority=Priority.MEDIUM if trade_event.outcome == "win" else Priority.HIGH
        )
        
        return block_id is not None

    def get_trading_opportunities(
        self,
        agent_id: str,
        symbol: Optional[str] = None,
        confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Get current trading opportunities based on learned patterns"""
        
        filters = {"min_confidence": confidence_threshold}
        if symbol:
            filters["symbol"] = symbol
        
        # Get high-confidence patterns
        patterns = self.get_trading_patterns(
            agent_id=agent_id,
            symbol=symbol,
            min_success_rate=0.6
        )
        
        opportunities = []
        for pattern in patterns:
            if pattern.confidence >= confidence_threshold:
                opportunity = {
                    "pattern_id": pattern.id,
                    "symbol": pattern.symbol,
                    "pattern_type": pattern.pattern_type,
                    "confidence": pattern.confidence,
                    "success_rate": pattern.success_rate,
                    "conditions": pattern.conditions,
                    "entry_signals": pattern.entry_signals,
                    "exit_signals": pattern.exit_signals,
                    "risk_metrics": pattern.risk_metrics
                }
                opportunities.append(opportunity)
        
        return opportunities

    # === BACKUP AND RESTORE ===
    
    def create_backup(
        self,
        agent_id: str,
        backup_type: str = "full",
        block_types: List[str] = None,
        compress: bool = True
    ) -> Optional[str]:
        """Create backup of agent memory"""
        
        backup_data = {
            "backup_type": backup_type,
            "compress": compress
        }
        
        if block_types:
            backup_data["block_types"] = block_types
        
        response = self._make_request("POST", f"agents/{agent_id}/backup", data=backup_data)
        
        if "error" in response:
            logger.error(f"Failed to create backup: {response['error']}")
            return None
        
        return response.get("backup_id")

    def list_backups(self, agent_id: str) -> List[Dict[str, Any]]:
        """List available backups for an agent"""
        response = self._make_request("GET", f"agents/{agent_id}/backups")
        
        if "error" in response:
            return []
        
        return response.get("backups", [])

    def restore_backup(
        self,
        backup_id: str,
        agent_id: str,
        restore_mode: str = "merge",
        validate: bool = True
    ) -> Dict[str, Any]:
        """Restore backup to agent memory"""
        
        restore_data = {
            "restore_mode": restore_mode,
            "validate": validate
        }
        
        response = self._make_request("POST", f"agents/{agent_id}/restore/{backup_id}", data=restore_data)
        
        if "error" in response:
            logger.error(f"Failed to restore backup: {response['error']}")
            return {}
        
        return response

    def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """Validate backup integrity"""
        response = self._make_request("GET", f"backups/{backup_id}/validate")
        
        if "error" in response:
            logger.error(f"Failed to validate backup: {response['error']}")
            return {}
        
        return response

    # === MONITORING AND ANALYTICS ===
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        response = self._make_request("GET", "system/status", use_cache=False)
        
        if "error" in response:
            return {}
        
        # Add client-side monitoring data
        response["client_monitoring"] = self._monitoring_data.copy()
        
        return response

    def get_memory_analytics(self, agent_id: str) -> Dict[str, Any]:
        """Get detailed memory analytics for an agent"""
        response = self._make_request("GET", f"agents/{agent_id}/memory/analytics")
        
        if "error" in response:
            return {}
        
        return response

    def get_performance_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get performance metrics for an agent"""
        response = self._make_request("GET", f"agents/{agent_id}/performance/metrics")
        
        if "error" in response:
            return {}
        
        return response

    def get_usage_statistics(self, time_range_days: int = 7) -> Dict[str, Any]:
        """Get usage statistics for the system"""
        params = {"time_range_days": time_range_days}
        response = self._make_request("GET", "system/usage", params=params)
        
        if "error" in response:
            return {}
        
        return response

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "client_status": "healthy",
            "checks": {}
        }
        
        # Check server connectivity
        try:
            server_response = self._make_request("GET", "health", use_cache=False)
            health_data["checks"]["server_connectivity"] = "healthy" if "error" not in server_response else "unhealthy"
        except Exception as e:
            health_data["checks"]["server_connectivity"] = f"error: {str(e)}"
        
        # Check API authentication
        try:
            auth_response = self._make_request("GET", "agents", use_cache=False)
            health_data["checks"]["api_authentication"] = "healthy" if "error" not in auth_response else "unhealthy"
        except Exception as e:
            health_data["checks"]["api_authentication"] = f"error: {str(e)}"
        
        # Overall status
        healthy_checks = sum(1 for check in health_data["checks"].values() if check == "healthy")
        total_checks = len(health_data["checks"])
        health_data["overall_status"] = "healthy" if healthy_checks == total_checks else "degraded"
        health_data["health_percentage"] = (healthy_checks / total_checks) * 100 if total_checks > 0 else 0
        
        return health_data

    # === UTILITY METHODS ===
    
    def clear_cache(self):
        """Clear internal cache"""
        self._clear_cache()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self._cache:
            return {"cache_enabled": False}
        
        return {
            "cache_enabled": True,
            "cache_size": len(self._cache),
            "cache_hits": self._monitoring_data["cache_hits"],
            "cache_misses": self._monitoring_data["cache_misses"],
            "hit_rate": self._monitoring_data["cache_hits"] / max(1, self._monitoring_data["cache_hits"] + self._monitoring_data["cache_misses"])
        }

    def close(self):
        """Close the client session"""
        if self.session:
            self.session.close()
        logger.info("Letta API Client session closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# === CONVENIENT FACTORY FUNCTIONS ===

def create_trading_client(
    base_url: str = "http://localhost:8283",
    api_key: str = "your-secret-api-key"
) -> LettaAPIClient:
    """Create a client optimized for trading operations"""
    return LettaAPIClient(
        base_url=base_url,
        api_key=api_key,
        cache_ttl=600,  # 10 minutes for trading data
        rate_limit=5.0,  # Conservative rate limiting for trading
        enable_monitoring=True
    )

def create_monitoring_client(
    base_url: str = "http://localhost:8283",
    api_key: str = "your-secret-api-key"
) -> LettaAPIClient:
    """Create a client optimized for monitoring and analytics"""
    return LettaAPIClient(
        base_url=base_url,
        api_key=api_key,
        cache_ttl=60,  # Short cache for real-time monitoring
        rate_limit=20.0,  # Higher rate for monitoring
        enable_monitoring=True,
        enable_caching=True
    )

def create_development_client(
    base_url: str = "http://localhost:8283",
    api_key: str = "your-secret-api-key"
) -> LettaAPIClient:
    """Create a client for development and testing"""
    return LettaAPIClient(
        base_url=base_url,
        api_key=api_key,
        cache_ttl=30,  # Short cache for development
        rate_limit=1.0,  # Conservative for testing
        enable_monitoring=True,
        enable_caching=False  # Disable caching for development
    )


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Get configuration from environment or command line
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8283"
    api_key = sys.argv[2] if len(sys.argv) > 2 else "your-secret-api-key"
    
    print(f"Letta API Client Demo")
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:20]}...")
    print("=" * 50)
    
    with LettaAPIClient(base_url, api_key) as client:
        # Health check
        print("1. Health Check:")
        health = client.health_check()
        print(f"   Status: {health.get('overall_status', 'unknown')}")
        print(f"   Health: {health.get('health_percentage', 0):.1f}%")
        
        # Get agents
        print("\n2. Agents:")
        agents = client.get_agents()
        for agent in agents[:5]:  # Show first 5 agents
            print(f"   - {agent.name} ({agent.role}) - {agent.status}")
        
        # System status
        print("\n3. System Status:")
        status = client.get_system_status()
        print(f"   Agents: {status.get('agents', {}).get('total_agents', 'unknown')}")
        print(f"   Memory Blocks: {status.get('memory', {}).get('total_blocks', 'unknown')}")
        
        print("\n4. Cache Stats:")
        cache_stats = client.get_cache_stats()
        print(f"   Cache Enabled: {cache_stats.get('cache_enabled', False)}")
        if cache_stats.get('cache_enabled'):
            print(f"   Cache Size: {cache_stats.get('cache_size', 0)}")
            print(f"   Hit Rate: {cache_stats.get('hit_rate', 0):.1%}")
        
        print("\nDemo completed successfully!")