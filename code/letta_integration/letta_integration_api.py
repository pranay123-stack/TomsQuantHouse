#!/usr/bin/env python3
"""
Complete Letta Integration API Client
Unified interface for all Letta integration components
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
import os
import redis

from letta_client import LettaClient, TradingAgentQuery
from advanced_memory_manager import (
    AdvancedMemoryManager,
    MemoryBlockType,
    MemoryPriority,
    MemoryRetentionPolicy,
    TradingPattern,
    MarketLearning,
    PerformanceInsight,
    MemoryBlock
)
from memory_workflows import (
    WorkflowExecutor,
    WorkflowScheduler,
    WorkflowType,
    TradeEvent,
    prepare_trade_analysis_workflow,
    prepare_performance_review_workflow
)
from advanced_queries import (
    QueryEngine,
    StrategicQueryInterface,
    QueryType,
    QueryFilter,
    QueryOperator
)
from redis_archival import RedisArchivalManager, ArchivalTier, ArchivalQuery
from multi_agent_communication import (
    MultiAgentCommunication,
    AgentRole,
    CommunicationPriority,
    MessageType
)
from memory_optimization import (
    MemoryOptimizer,
    MemoryCleanupScheduler,
    OptimizationStrategy,
    CleanupAction
)
from backup_restore import (
    BackupManager,
    BackupType,
    RestoreMode,
    BackupFormat
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LettaIntegrationAPI:
    """Complete Letta Integration API Client
    
    This is the main interface for all Letta integration functionality, combining:
    - Advanced memory management
    - Workflow automation
    - Query capabilities
    - Redis archival storage
    - Multi-agent communication
    - Memory optimization
    - Backup and restore
    """
    
    def __init__(self, 
                 letta_config: Dict[str, Any],
                 redis_config: Dict[str, Any] = None):
        """
        Initialize the complete Letta integration API
        
        Args:
            letta_config: Letta client configuration
            redis_config: Redis configuration for archival storage
        """
        
        self.letta_config = letta_config
        self.redis_config = redis_config or {}
        
        # Initialize base Letta client
        self.letta_client = LettaClient(
            base_url=letta_config.get("base_url", "http://localhost:8283"),
            api_key=letta_config.get("api_key", "your-secret-api-key-here")
        )
        
        # Initialize Redis client for archival
        self.redis_client = None
        self.redis_archival = None
        if redis_config:
            try:
                self.redis_client = redis.Redis(
                    host=redis_config.get("host", "localhost"),
                    port=redis_config.get("port", 6379),
                    db=redis_config.get("db", 1),
                    password=redis_config.get("password"),
                    decode_responses=False
                )
                self.redis_client.ping()
                logger.info("Redis connection established for archival storage")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
        
        # Initialize core components
        self.memory_manager = AdvancedMemoryManager(
            self.letta_client,
            self.redis_client
        )
        
        # Initialize advanced features
        if self.redis_client:
            self.redis_archival = RedisArchivalManager(redis_config)
            self.redis_archival.start_background_processes()
        
        self.query_engine = QueryEngine(self.memory_manager)
        self.strategic_interface = StrategicQueryInterface(self.query_engine)
        
        # Initialize workflow system
        self.workflow_executor = WorkflowExecutor(self.memory_manager)
        self.workflow_scheduler = WorkflowScheduler(self.workflow_executor)
        self.workflow_scheduler.start()
        
        # Initialize multi-agent communication
        self.communication = MultiAgentCommunication(
            self.letta_client,
            self.memory_manager,
            self.redis_archival
        )
        
        # Initialize optimization system
        self.memory_optimizer = MemoryOptimizer(self.memory_manager, self.memory_manager.analyzer)
        self.cleanup_scheduler = MemoryCleanupScheduler(self.memory_optimizer)
        self.cleanup_scheduler.start()
        
        # Initialize backup system
        self.backup_manager = BackupManager(self.memory_manager, self.redis_archival)
        self.backup_manager.start()
        
        # Start multi-agent communication
        self.communication.start()
        
        # Configuration
        self.auto_optimization = True
        self.auto_backup = True
        self.backup_interval_hours = 24
        
        # Background tasks
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.running = False
        self.background_threads = []
        
        logger.info("Letta Integration API initialized successfully")
    
    def start(self):
        """Start all background processes"""
        if not self.running:
            self.running = True
            
            # Start background optimization task
            if self.auto_optimization:
                optimization_thread = threading.Thread(target=self._optimization_worker, daemon=True)
                optimization_thread.start()
                self.background_threads.append(optimization_thread)
            
            # Start background backup task
            if self.auto_backup:
                backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
                backup_thread.start()
                self.background_threads.append(backup_thread)
            
            # Start health monitoring
            health_thread = threading.Thread(target=self._health_monitor_worker, daemon=True)
            health_thread.start()
            self.background_threads.append(health_thread)
            
            logger.info("All Letta integration services started")
    
    def stop(self):
        """Stop all background processes"""
        self.running = False
        
        # Stop all components
        if hasattr(self, 'workflow_scheduler'):
            self.workflow_scheduler.stop()
        
        if hasattr(self, 'cleanup_scheduler'):
            self.cleanup_scheduler.stop()
        
        if hasattr(self, 'backup_manager'):
            self.backup_manager.stop()
        
        if hasattr(self, 'communication'):
            self.communication.stop()
        
        if hasattr(self, 'redis_archival'):
            self.redis_archival.stop_background_processes()
        
        # Wait for threads
        for thread in self.background_threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        self.executor.shutdown(wait=True)
        logger.info("All Letta integration services stopped")
    
    # ============================================================================
    # Memory Management API
    # ============================================================================
    
    def create_memory_block(self,
                          agent_id: str,
                          block_type: Union[str, MemoryBlockType],
                          title: str,
                          content: Any,
                          priority: Union[str, MemoryPriority] = MemoryPriority.MEDIUM,
                          retention_policy: Union[str, MemoryRetentionPolicy] = MemoryRetentionPolicy.MEDIUM_TERM,
                          tags: List[str] = None) -> str:
        """Create a new memory block"""
        
        if isinstance(block_type, str):
            block_type = MemoryBlockType(block_type)
        if isinstance(priority, str):
            priority = MemoryPriority(priority)
        if isinstance(retention_policy, str):
            retention_policy = MemoryRetentionPolicy(retention_policy)
        
        return self.memory_manager.create_memory_block(
            agent_id=agent_id,
            block_type=block_type,
            title=title,
            content=content,
            priority=priority,
            retention_policy=retention_policy,
            tags=tags
        )
    
    def search_memory(self,
                     agent_id: str,
                     query: str = None,
                     block_type: Union[str, MemoryBlockType] = None,
                     priority: Union[str, MemoryPriority] = None,
                     tags: List[str] = None,
                     limit: int = 50) -> List[Dict[str, Any]]:
        """Search agent memory"""
        
        filters = []
        
        if block_type:
            if isinstance(block_type, str):
                block_type = MemoryBlockType(block_type)
            filters.append(QueryFilter("block_type", QueryOperator.EQUALS, block_type.value))
        
        if priority:
            if isinstance(priority, str):
                priority = MemoryPriority(priority)
            filters.append(QueryFilter("metadata.priority", QueryOperator.EQUALS, priority.value))
        
        if tags:
            filters.append(QueryFilter("metadata.tags", QueryOperator.CONTAINS, tags))
        
        query_result = self.query_engine.execute_query(
            query_type=QueryType.TEXT_SEARCH if query else QueryType.COMPOSITE,
            agent_id=agent_id,
            filters=filters,
            search_text=query,
            limit=limit
        )
        
        return query_result.results
    
    def get_performance_insights(self, agent_id: str) -> List[PerformanceInsight]:
        """Get performance insights from agent memory"""
        return self.memory_manager.get_performance_insights(agent_id)
    
    # ============================================================================
    # Trading Pattern Management
    # ============================================================================
    
    def create_trading_pattern(self,
                             agent_id: str,
                             symbol: str,
                             pattern_type: str,
                             success_rate: float,
                             confidence: float,
                             conditions: Dict[str, Any],
                             entry_signals: List[str],
                             exit_signals: List[str],
                             risk_metrics: Dict[str, float] = None) -> str:
        """Create a trading pattern memory block"""
        
        pattern = TradingPattern(
            pattern_id=f"pattern_{symbol}_{pattern_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            symbol=symbol,
            timeframe="daily",  # Default, could be parameter
            pattern_type=pattern_type,
            success_rate=success_rate,
            confidence=confidence,
            conditions=conditions,
            entry_signals=entry_signals,
            exit_signals=exit_signals,
            risk_metrics=risk_metrics or {},
            performance_history=[],
            last_validated=datetime.now()
        )
        
        return self.memory_manager.create_trading_pattern(agent_id, pattern)
    
    def get_trading_opportunities(self, agent_id: str, symbol: str = None) -> List[Dict[str, Any]]:
        """Get trading opportunities from memory"""
        insights = self.strategic_interface.get_trading_opportunities(agent_id, symbol)
        return [asdict(insight) for insight in insights]
    
    # ============================================================================
    # Workflow API
    # ============================================================================
    
    def execute_trade_analysis_workflow(self, 
                                      agent_id: str,
                                      trade_event: Dict[str, Any]) -> str:
        """Execute trade analysis workflow"""
        
        workflow_data = prepare_trade_analysis_workflow(agent_id, trade_event)
        
        return self.workflow_executor.execute_workflow(
            WorkflowType.TRADE_ANALYSIS,
            agent_id,
            workflow_data
        )
    
    def execute_performance_review_workflow(self, agent_id: str) -> str:
        """Execute performance review workflow"""
        
        workflow_data = prepare_performance_review_workflow(agent_id)
        
        return self.workflow_executor.execute_workflow(
            WorkflowType.PERFORMANCE_REVIEW,
            agent_id,
            workflow_data
        )
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow execution status"""
        result = self.workflow_executor.get_workflow_status(workflow_id)
        return asdict(result) if result else None
    
    def schedule_workflow(self,
                         workflow_type: Union[str, WorkflowType],
                         agent_id: str,
                         schedule_time: datetime,
                         recurring: bool = False,
                         interval_hours: int = 24) -> str:
        """Schedule a workflow for future execution"""
        
        if isinstance(workflow_type, str):
            workflow_type = WorkflowType(workflow_type)
        
        return self.workflow_scheduler.schedule_workflow(
            workflow_type, agent_id, {}, schedule_time, recurring, interval_hours
        )
    
    # ============================================================================
    # Multi-Agent Communication API
    # ============================================================================
    
    def register_agent(self, 
                      agent_id: str,
                      role: Union[str, AgentRole],
                      capabilities: List[str] = None):
        """Register an agent for communication"""
        
        if isinstance(role, str):
            role = AgentRole(role)
        
        self.communication.register_agent(agent_id, role, capabilities)
    
    def send_message(self,
                    sender_agent_id: str,
                    receiver_agent_id: str,
                    subject: str,
                    content: str,
                    priority: Union[str, CommunicationPriority] = CommunicationPriority.NORMAL) -> str:
        """Send direct message to another agent"""
        
        if isinstance(priority, str):
            priority = CommunicationPriority(priority)
        
        return self.communication.send_direct_message(
            sender_agent_id, receiver_agent_id, subject, content, priority
        )
    
    def broadcast_message(self,
                         sender_agent_id: str,
                         subject: str,
                         content: str,
                         target_roles: List[Union[str, AgentRole]] = None) -> List[str]:
        """Broadcast message to multiple agents"""
        
        if target_roles:
            role_objects = []
            for role in target_roles:
                if isinstance(role, str):
                    role_objects.append(AgentRole(role))
                else:
                    role_objects.append(role)
            target_roles = role_objects
        
        return self.communication.broadcast_message(
            sender_agent_id, subject, content, target_roles=target_roles
        )
    
    def share_memory(self,
                    sharing_agent_id: str,
                    recipient_agent_id: str,
                    memory_block_ids: List[str],
                    access_level: str = "read",
                    duration_hours: int = 24) -> str:
        """Share memory blocks between agents"""
        
        duration = timedelta(hours=duration_hours)
        
        return self.communication.share_memory(
            sharing_agent_id, recipient_agent_id, memory_block_ids, access_level, duration
        )
    
    def send_risk_alert(self,
                       agent_id: str,
                       risk_level: str,
                       description: str,
                       risk_data: Dict[str, Any]) -> str:
        """Send risk alert to appropriate agents"""
        
        return self.communication.send_risk_alert(
            agent_id, risk_level, description, risk_data
        )
    
    # ============================================================================
    # Archival Storage API
    # ============================================================================
    
    def archive_memory_blocks(self,
                            agent_id: str,
                            block_ids: List[str],
                            tier: Union[str, ArchivalTier] = ArchivalTier.WARM) -> Dict[str, bool]:
        """Archive memory blocks to Redis"""
        
        if not self.redis_archival:
            raise ValueError("Redis archival not configured")
        
        if isinstance(tier, str):
            tier = ArchivalTier(tier)
        
        results = {}
        
        for block_id in block_ids:
            try:
                # Get memory block data
                memory_block = self.memory_manager.get_memory_block(agent_id, block_id)
                if memory_block:
                    block_data = memory_block.to_dict()
                    success = self.redis_archival.archive_memory_block(
                        agent_id, block_id, block_data, tier
                    )
                    results[block_id] = success
                else:
                    results[block_id] = False
            except Exception as e:
                logger.error(f"Error archiving block {block_id}: {e}")
                results[block_id] = False
        
        return results
    
    def restore_archived_memory(self,
                              agent_id: str,
                              block_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Restore archived memory blocks"""
        
        if not self.redis_archival:
            raise ValueError("Redis archival not configured")
        
        results = {}
        
        for block_id in block_ids:
            try:
                restored_data = self.redis_archival.restore_memory_block(agent_id, block_id)
                results[block_id] = restored_data
            except Exception as e:
                logger.error(f"Error restoring block {block_id}: {e}")
                results[block_id] = None
        
        return results
    
    def search_archived_content(self,
                              agent_id: str,
                              search_text: str,
                              limit: int = 50) -> List[Dict[str, Any]]:
        """Search through archived memory content"""
        
        if not self.redis_archival:
            raise ValueError("Redis archival not configured")
        
        results = self.redis_archival.search_archived_content(
            agent_id, search_text, limit=limit
        )
        
        return results
    
    # ============================================================================
    # Memory Optimization API
    # ============================================================================
    
    def optimize_memory(self,
                       agent_id: str,
                       strategy: Union[str, OptimizationStrategy] = OptimizationStrategy.HYBRID,
                       aggressive: bool = False) -> Dict[str, Any]:
        """Optimize agent memory usage"""
        
        if isinstance(strategy, str):
            strategy = OptimizationStrategy(strategy)
        
        report = self.memory_optimizer.execute_optimization(agent_id, strategy, aggressive)
        return asdict(report)
    
    def schedule_optimization(self,
                            agent_id: str,
                            strategy: Union[str, OptimizationStrategy],
                            interval_hours: int = 24,
                            aggressive: bool = False) -> str:
        """Schedule periodic memory optimization"""
        
        if isinstance(strategy, str):
            strategy = OptimizationStrategy(strategy)
        
        return self.cleanup_scheduler.schedule_optimization(
            agent_id, strategy, interval_hours, aggressive
        )
    
    def get_optimization_recommendations(self, agent_id: str) -> Dict[str, Any]:
        """Get memory optimization recommendations"""
        schedule = self.memory_optimizer.create_optimization_schedule(agent_id)
        return schedule
    
    # ============================================================================
    # Backup and Restore API
    # ============================================================================
    
    def create_backup(self,
                     agent_id: str = None,
                     backup_type: Union[str, BackupType] = BackupType.FULL,
                     block_types: List[Union[str, MemoryBlockType]] = None) -> str:
        """Create a backup of agent memory"""
        
        if isinstance(backup_type, str):
            backup_type = BackupType(backup_type)
        
        if block_types:
            type_objects = []
            for bt in block_types:
                if isinstance(bt, str):
                    type_objects.append(MemoryBlockType(bt))
                else:
                    type_objects.append(bt)
            block_types = type_objects
        
        return self.backup_manager.create_backup(
            agent_id=agent_id or "all",  # Handle multi-agent backups
            backup_type=backup_type,
            block_types=block_types
        )
    
    def restore_backup(self,
                      backup_id: str,
                      agent_id: str = None,
                      restore_mode: Union[str, RestoreMode] = RestoreMode.MERGE) -> Dict[str, Any]:
        """Restore from backup"""
        
        if isinstance(restore_mode, str):
            restore_mode = RestoreMode(restore_mode)
        
        report = self.backup_manager.restore_backup(
            backup_id, agent_id, restore_mode
        )
        return asdict(report)
    
    def list_backups(self, agent_id: str = None) -> List[Dict[str, Any]]:
        """List available backups"""
        backups = self.backup_manager.list_backups(agent_id)
        return [asdict(backup) for backup in backups]
    
    def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """Validate backup integrity"""
        return self.backup_manager.validate_backup(backup_id)
    
    # ============================================================================
    # Strategic Decision Making API
    # ============================================================================
    
    def get_trading_advice(self, agent_id: str, query: str) -> Dict[str, Any]:
        """Get strategic trading advice from agent memory"""
        return self.strategic_interface.query_engine.execute_query(
            QueryType.TEXT_SEARCH, agent_id, search_text=query
        ).to_dict() if hasattr(QueryResult, 'to_dict') else {
            "query": query,
            "results": []
        }
    
    def get_market_context(self, agent_id: str) -> Dict[str, Any]:
        """Get current market context from agent memory"""
        context = self.strategic_interface.get_market_context(agent_id)
        return asdict(context)
    
    def get_risk_assessment(self, agent_id: str, current_positions: List[str] = None) -> List[Dict[str, Any]]:
        """Get risk assessment from agent memory"""
        insights = self.strategic_interface.get_risk_assessment(agent_id, current_positions)
        return [asdict(insight) for insight in insights]
    
    def compare_strategies(self, agent_id: str, strategy_names: List[str]) -> Dict[str, Any]:
        """Compare multiple strategies from memory"""
        return self.strategic_interface.compare_strategies(agent_id, strategy_names)
    
    def get_adaptive_recommendations(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get adaptive recommendations based on recent learning"""
        insights = self.strategic_interface.get_adaptive_recommendations(agent_id)
        return [asdict(insight) for insight in insights]
    
    # ============================================================================
    # System Information and Monitoring
    # ============================================================================
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        return {
            "memory_manager": {
                "cache_size": len(self.memory_manager.memory_cache),
                "blocks_cached": len(self.memory_manager.memory_cache),
                "cache_hit_rate": getattr(self.memory_manager, 'cache_hit_rate', 0.0)
            },
            "workflow_scheduler": self.workflow_scheduler.get_scheduled_workflows(),
            "cleanup_scheduler": self.cleanup_scheduler.get_cleanup_status(),
            "communication": {
                "active_agents": len(self.communication.agent_registry.get_active_agents()),
                "messages_sent": self.communication.stats.total_messages_sent,
                "messages_received": self.communication.stats.total_messages_received
            },
            "backup_manager": {
                "backups_created": len(self.backup_manager.backup_history),
                "total_backup_size": sum(b.total_size_bytes for b in self.backup_manager.backup_history)
            },
            "redis_archival": {
                "enabled": self.redis_archival is not None,
                "stats": self.redis_archival.get_archival_stats().to_dict() if self.redis_archival else {}
            }
        }
    
    def get_memory_usage(self, agent_id: str) -> Dict[str, Any]:
        """Get memory usage statistics for an agent"""
        metrics = self.memory_manager.analyzer.analyze_memory_usage(agent_id)
        opportunities = self.memory_manager.analyzer.identify_optimization_opportunities(agent_id)
        predictions = self.memory_manager.analyzer.predict_memory_pressure(agent_id)
        
        return {
            "metrics": asdict(metrics),
            "optimization_opportunities": opportunities,
            "pressure_predictions": predictions
        }
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        stats = self.communication.get_communication_stats()
        return asdict(stats)
    
    def get_recent_messages(self, 
                          agent_id: str = None,
                          time_range_hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent communication messages"""
        time_range = timedelta(hours=time_range_hours)
        messages = self.communication.get_message_history(
            agent_id=agent_id,
            time_range=time_range
        )
        return messages
    
    # ============================================================================
    # Configuration and Settings
    # ============================================================================
    
    def configure_auto_optimization(self, enabled: bool, interval_hours: int = 24):
        """Configure automatic memory optimization"""
        self.auto_optimization = enabled
        if enabled:
            # Schedule optimization for all agents
            agents = self.letta_client.get_agents()
            for agent in agents:
                self.schedule_optimization(
                    agent["id"], 
                    OptimizationStrategy.HYBRID, 
                    interval_hours
                )
    
    def configure_auto_backup(self, enabled: bool, interval_hours: int = 24):
        """Configure automatic backups"""
        self.auto_backup = enabled
        self.backup_interval_hours = interval_hours
    
    # ============================================================================
    # Internal Background Workers
    # ============================================================================
    
    def _optimization_worker(self):
        """Background worker for automatic optimization"""
        while self.running:
            try:
                # Get all agents
                agents = self.letta_client.get_agents()
                
                for agent in agents:
                    agent_id = agent["id"]
                    
                    # Check if optimization is needed
                    metrics = self.memory_manager.analyzer.analyze_memory_usage(agent_id)
                    
                    # Trigger optimization if memory utilization is high
                    if metrics.memory_utilization > 0.8:
                        logger.info(f"Auto-optimizing agent {agent_id} due to high memory utilization")
                        self.optimize_memory(agent_id, OptimizationStrategy.HYBRID, aggressive=True)
                
                # Wait before next optimization cycle
                threading.Event().wait(1800)  # 30 minutes
                
            except Exception as e:
                logger.error(f"Optimization worker error: {e}")
                threading.Event().wait(3600)  # Wait 1 hour on error
    
    def _backup_worker(self):
        """Background worker for automatic backups"""
        while self.running:
            try:
                if self.auto_backup:
                    # Create backups for all agents
                    agents = self.letta_client.get_agents()
                    
                    for agent in agents:
                        agent_id = agent["id"]
                        
                        # Create incremental backup
                        self.create_backup(
                            agent_id=agent_id,
                            backup_type=BackupType.INCREMENTAL
                        )
                
                # Wait for next backup cycle
                threading.Event().wait(self.backup_interval_hours * 3600)
                
            except Exception as e:
                logger.error(f"Backup worker error: {e}")
                threading.Event().wait(3600)  # Wait 1 hour on error
    
    def _health_monitor_worker(self):
        """Background worker for system health monitoring"""
        while self.running:
            try:
                # Monitor system health
                system_status = self.get_system_status()
                
                # Log critical issues
                if system_status["memory_manager"]["cache_hit_rate"] < 0.5:
                    logger.warning("Low cache hit rate detected")
                
                if system_status["cleanup_scheduler"]["scheduler_running"] != True:
                    logger.warning("Cleanup scheduler not running")
                
                if system_status["redis_archival"]["enabled"]:
                    archival_stats = system_status["redis_archival"]["stats"]
                    if archival_stats.get("compression_ratio", 1.0) < 2.0:
                        logger.warning("Low compression ratio in archival storage")
                
                # Wait before next health check
                threading.Event().wait(600)  # 10 minutes
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                threading.Event().wait(1200)  # Wait 20 minutes on error


# Convenience functions for common operations

def create_trading_integration(letta_config: Dict[str, Any], 
                              redis_config: Dict[str, Any] = None) -> LettaIntegrationAPI:
    """Create a trading-focused Letta integration"""
    
    api = LettaIntegrationAPI(letta_config, redis_config)
    
    # Register default trading agents
    api.register_agent("trading_strategist", AgentRole.STRATEGIST, ["strategy", "pattern_analysis"])
    api.register_agent("market_analyst", AgentRole.ANALYST, ["market_analysis", "data_processing"])
    api.register_agent("risk_manager", AgentRole.RISK_MANAGER, ["risk_assessment", "risk_management"])
    api.register_agent("coordinator", AgentRole.COORDINATOR, ["coordination", "orchestration"])
    
    return api


def create_research_integration(letta_config: Dict[str, Any], 
                               redis_config: Dict[str, Any] = None) -> LettaIntegrationAPI:
    """Create a research-focused Letta integration"""
    
    api = LettaIntegrationAPI(letta_config, redis_config)
    
    # Register research agents
    api.register_agent("researcher", AgentRole.SPECIALIST, ["research", "analysis", "documentation"])
    api.register_agent("data_analyst", AgentRole.ANALYST, ["data_processing", "statistical_analysis"])
    api.register_agent("coordinator", AgentRole.COORDINATOR, ["coordination", "project_management"])
    
    return api


# Example usage and testing
if __name__ == "__main__":
    # Example configuration
    letta_config = {
        "base_url": "http://localhost:8283",
        "api_key": "your-api-key-here"
    }
    
    redis_config = {
        "host": "localhost",
        "port": 6379,
        "db": 1,
        "password": None
    }
    
    # Create integration
    api = create_trading_integration(letta_config, redis_config)
    
    try:
        # Start the system
        api.start()
        
        # Example operations
        print("Letta Integration System Started")
        print("=" * 50)
        
        # Create memory blocks
        block_id = api.create_memory_block(
            agent_id="trading_strategist",
            block_type=MemoryBlockType.TRADING_STRATEGY,
            title="Moving Average Crossover Strategy",
            content="Strategy based on MA crossovers with volume confirmation",
            priority=MemoryPriority.HIGH,
            tags=["strategy", "moving_average", "trending"]
        )
        
        print(f"Created memory block: {block_id}")
        
        # Create trading pattern
        pattern_id = api.create_trading_pattern(
            agent_id="trading_strategist",
            symbol="AAPL",
            pattern_type="bullish_breakout",
            success_rate=0.75,
            confidence=0.8,
            conditions={"volume_spike": True, "rsi_oversold": False},
            entry_signals=["price_breaks_resistance", "volume_confirmation"],
            exit_signals=["stop_loss", "profit_target"],
            risk_metrics={"max_risk": 0.02, "position_size": 0.1}
        )
        
        print(f"Created trading pattern: {pattern_id}")
        
        # Execute workflow
        trade_event = {
            "trade_id": "trade_001",
            "symbol": "AAPL",
            "action": "buy",
            "quantity": 100,
            "entry_price": 150.00,
            "exit_price": 155.50,
            "entry_time": datetime.now().isoformat(),
            "pnl": 5.50,
            "strategy": "moving_average_crossover",
            "confidence": 0.8,
            "outcome": "win"
        }
        
        workflow_id = api.execute_trade_analysis_workflow("trading_strategist", trade_event)
        print(f"Started workflow: {workflow_id}")
        
        # Send communication
        message_id = api.send_message(
            sender_agent_id="trading_strategist",
            receiver_agent_id="risk_manager",
            subject="Strategy Update",
            content="New high-confidence pattern identified for AAPL",
            priority=CommunicationPriority.HIGH
        )
        
        print(f"Sent message: {message_id}")
        
        # Get trading opportunities
        opportunities = api.get_trading_opportunities("trading_strategist")
        print(f"Found {len(opportunities)} trading opportunities")
        
        # Search memory
        results = api.search_memory("trading_strategist", "strategy")
        print(f"Found {len(results)} memory blocks matching 'strategy'")
        
        # Get system status
        status = api.get_system_status()
        print("System Status:")
        print(f"  Active Agents: {status['communication']['active_agents']}")
        print(f"  Messages Sent: {status['communication']['messages_sent']}")
        print(f"  Memory Cache Size: {status['memory_manager']['cache_size']}")
        
        print("\nLetta Integration System is running successfully!")
        
        # Keep running
        try:
            while True:
                threading.Event().wait(10)
        except KeyboardInterrupt:
            print("\nShutting down...")
    
    finally:
        # Clean shutdown
        api.stop()
        print("Letta Integration System stopped")