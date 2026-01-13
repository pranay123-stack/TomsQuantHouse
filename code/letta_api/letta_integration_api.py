#!/usr/bin/env python3
"""
Letta Integration API - Main Entry Point

Comprehensive integration API that combines all Letta API functionality:
- Advanced memory management and queries
- Trading workflows and insights
- Agent communication and coordination
- Backup and restore capabilities
- Performance monitoring and analytics
- Dashboard integration helpers

This is the main API interface for external applications.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from pathlib import Path
import json

# Import all modules
from letta_client import (
    LettaAPIClient, AgentRole, MemoryBlockType, Priority, 
    QueryType, AgentInfo, MemoryBlock, SearchResult,
    TradingPattern, TradeEvent, create_trading_client
)
from memory_manager import AdvancedMemoryManager, create_memory_manager
from trading_workflows import TradingWorkflows, create_trading_workflows
from agent_communication import (
    AgentCommunicationHub, create_communication_hub,
    MessageType, MessagePriority, CoordinationType,
    AgentCapability, AgentRegistration
)
from backup_restore import BackupManager, create_backup_manager
from performance_monitor import PerformanceMonitor, create_performance_monitor

logger = logging.getLogger(__name__)


class LettaIntegrationAPI:
    """
    Comprehensive Letta Integration API
    
    This is the main entry point that provides unified access to all Letta API functionality.
    It combines memory management, trading workflows, agent communication, 
    backup/restore, and performance monitoring into a single, easy-to-use interface.
    """
    
    def __init__(
        self,
        letta_config: Dict[str, Any],
        redis_config: Optional[Dict[str, Any]] = None,
        backup_directory: str = "./backups",
        enable_monitoring: bool = True,
        enable_communication: bool = True,
        enable_workflows: bool = True,
        auto_optimization: bool = True,
        auto_backup: bool = False,
        optimization_interval_hours: int = 6,
        backup_interval_hours: int = 24
    ):
        """
        Initialize the Letta Integration API
        
        Args:
            letta_config: Configuration for Letta API client
            redis_config: Optional Redis configuration for caching
            backup_directory: Directory for backup storage
            enable_monitoring: Enable performance monitoring
            enable_communication: Enable agent communication hub
            enable_workflows: Enable trading workflows
            auto_optimization: Enable automatic memory optimization
            auto_backup: Enable automatic backups
            optimization_interval_hours: Hours between optimization runs
            backup_interval_hours: Hours between backup runs
        """
        
        # Store configuration
        self.config = {
            "letta": letta_config,
            "redis": redis_config or {},
            "backup_directory": backup_directory,
            "auto_optimization": auto_optimization,
            "auto_backup": auto_backup,
            "optimization_interval_hours": optimization_interval_hours,
            "backup_interval_hours": backup_interval_hours
        }
        
        # Initialize core components
        self.client = LettaAPIClient(**letta_config)
        self.memory_manager = create_memory_manager(self.client)
        self.workflows = create_trading_workflows(self.client)
        
        # Initialize optional components
        self.communication_hub = None
        self.backup_manager = None
        self.performance_monitor = None
        
        if enable_communication:
            self.communication_hub = create_communication_hub(self.client)
        
        if enable_monitoring:
            self.performance_monitor = create_performance_monitor(self.client)
        
        if enable_workflows:
            self.backup_manager = create_backup_manager(self.client, backup_directory)
        
        # Internal state
        self.is_running = False
        self._auto_tasks = {}
        self._setup_logging()
        
        logger.info("Letta Integration API initialized")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # === SYSTEM LIFECYCLE ===
    
    def start(self):
        """Start the integration system"""
        
        if self.is_running:
            logger.warning("System is already running")
            return
        
        logger.info("Starting Letta Integration System...")
        
        # Test connectivity
        health = self.client.health_check()
        if health["overall_status"] not in ["healthy", "degraded"]:
            raise ConnectionError(f"Letta server health check failed: {health}")
        
        # Start performance monitoring
        if self.performance_monitor:
            self.performance_monitor.start_monitoring()
        
        # Setup default agents for communication
        if self.communication_hub:
            from agent_communication import setup_default_agents
            setup_default_agents(self.communication_hub, self.client)
        
        # Start automatic optimization
        if self.config["auto_optimization"]:
            self._start_auto_optimization()
        
        # Start automatic backups
        if self.config["auto_backup"]:
            self._start_auto_backup()
        
        self.is_running = True
        logger.info("Letta Integration System started successfully")
    
    def stop(self):
        """Stop the integration system"""
        
        if not self.is_running:
            logger.warning("System is not running")
            return
        
        logger.info("Stopping Letta Integration System...")
        
        # Stop auto tasks
        for task_name, task in self._auto_tasks.items():
            try:
                task.cancel()
                logger.info(f"Stopped auto task: {task_name}")
            except Exception as e:
                logger.error(f"Error stopping auto task {task_name}: {e}")
        
        self._auto_tasks.clear()
        
        # Stop performance monitoring
        if self.performance_monitor:
            self.performance_monitor.stop_monitoring()
        
        self.is_running = False
        logger.info("Letta Integration System stopped")
    
    def _start_auto_optimization(self):
        """Start automatic memory optimization"""
        
        async def optimization_task():
            while self.is_running:
                try:
                    logger.info("Running automatic memory optimization...")
                    
                    # Get all agents
                    agents = self.client.get_agents()
                    
                    for agent in agents:
                        try:
                            # Run optimization
                            report = self.memory_manager.optimize_memory_intelligent(
                                agent_id=agent.id,
                                strategy="hybrid"
                            )
                            
                            logger.info(f"Optimized agent {agent.id}: {report.blocks_processed} blocks processed")
                            
                        except Exception as e:
                            logger.warning(f"Optimization failed for agent {agent.id}: {e}")
                    
                    # Wait for next interval
                    await asyncio.sleep(self.config["optimization_interval_hours"] * 3600)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in optimization task: {e}")
                    await asyncio.sleep(300)  # 5 minute retry
        
        task = asyncio.create_task(optimization_task())
        self._auto_tasks["optimization"] = task
        logger.info("Automatic optimization started")
    
    def _start_auto_backup(self):
        """Start automatic backup task"""
        
        async def backup_task():
            while self.is_running:
                try:
                    logger.info("Running automatic backup...")
                    
                    # Get all agents
                    agents = self.client.get_agents()
                    
                    for agent in agents:
                        try:
                            # Create incremental backup
                            backup_id = self.backup_manager.create_backup(
                                agent_id=agent.id,
                                backup_type="incremental",
                                description=f"Auto backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                                tags=["automatic", "scheduled"]
                            )
                            
                            if backup_id:
                                logger.info(f"Created backup for agent {agent.id}: {backup_id}")
                            
                        except Exception as e:
                            logger.warning(f"Backup failed for agent {agent.id}: {e}")
                    
                    # Wait for next interval
                    await asyncio.sleep(self.config["backup_interval_hours"] * 3600)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in backup task: {e}")
                    await asyncio.sleep(300)  # 5 minute retry
        
        task = asyncio.create_task(backup_task())
        self._auto_tasks["backup"] = task
        logger.info("Automatic backup started")
    
    # === COMPREHENSIVE MEMORY MANAGEMENT ===
    
    def create_memory_block(
        self,
        agent_id: str,
        block_type: str,
        title: str,
        content: str,
        priority: str = "medium",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Create a new memory block"""
        
        try:
            # Convert string to enum
            memory_block_type = MemoryBlockType(block_type)
            priority_enum = Priority(priority)
            
            return self.client.add_memory_block(
                agent_id=agent_id,
                block_type=memory_block_type,
                title=title,
                content=content,
                priority=priority_enum,
                tags=tags or [],
                metadata=metadata or {}
            )
            
        except ValueError as e:
            logger.error(f"Invalid parameters for memory block creation: {e}")
            return None
    
    def search_memory_intelligent(
        self,
        agent_id: Optional[str] = None,
        query: str = "",
        context: Dict[str, Any] = None,
        search_options: Dict[str, Any] = None
    ) -> List[SearchResult]:
        """Intelligent memory search with multiple strategies"""
        
        return self.memory_manager.intelligent_search(
            agent_id=agent_id or "",
            query=query,
            context=context,
            search_options=search_options
        )
    
    def get_memory_analytics(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive memory analytics for an agent"""
        
        return self.memory_manager.get_memory_summary(agent_id)
    
    def optimize_memory(self, agent_id: str, strategy: str = "hybrid") -> Dict[str, Any]:
        """Optimize agent memory"""
        
        from memory_manager import OptimizationStrategy
        
        try:
            strategy_enum = OptimizationStrategy(strategy)
            report = self.memory_manager.optimize_memory_intelligent(
                agent_id=agent_id,
                strategy=strategy_enum
            )
            
            return {
                "success": True,
                "strategy_used": report.strategy_used,
                "blocks_processed": report.blocks_processed,
                "blocks_optimized": report.blocks_optimized,
                "space_freed_bytes": report.space_freed_bytes,
                "performance_improvement": report.performance_improvement,
                "optimization_time_seconds": report.optimization_time_seconds,
                "recommendations": report.recommendations
            }
            
        except ValueError as e:
            return {"success": False, "error": str(e)}
    
    # === TRADING WORKFLOWS ===
    
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
        
        return self.client.create_trading_pattern(
            agent_id=agent_id,
            symbol=symbol,
            pattern_type=pattern_type,
            success_rate=success_rate,
            confidence=confidence,
            conditions=conditions,
            entry_signals=entry_signals,
            exit_signals=exit_signals,
            risk_metrics=risk_metrics
        )
    
    def record_trade_outcome(
        self,
        agent_id: str,
        trade_data: Dict[str, Any]
    ) -> bool:
        """Record a trade outcome for analysis"""
        
        try:
            # Validate and convert trade data
            trade_event = TradeEvent(**trade_data)
            return self.client.record_trade_outcome(agent_id, trade_event)
            
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid trade data: {e}")
            return False
    
    def execute_trade_analysis_workflow(
        self,
        agent_id: str,
        trade_data: Dict[str, Any]
    ) -> Optional[str]:
        """Execute automated trade analysis workflow"""
        
        try:
            trade_event = TradeEvent(**trade_data)
            return self.workflows.execute_trade_analysis_workflow(agent_id, trade_event)
            
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid trade data for workflow: {e}")
            return None
    
    def get_trading_opportunities(
        self,
        agent_id: str,
        symbol: Optional[str] = None,
        confidence_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Get current trading opportunities based on learned patterns"""
        
        return self.client.get_trading_opportunities(
            agent_id=agent_id,
            symbol=symbol,
            confidence_threshold=confidence_threshold
        )
    
    def get_market_context(self, agent_id: str) -> Dict[str, Any]:
        """Get current market context and analysis"""
        
        return self.workflows.get_market_context_analysis(agent_id)
    
    def get_performance_analysis(
        self,
        agent_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive performance analysis"""
        
        return self.workflows.get_comprehensive_performance_analysis(agent_id, period_days)
    
    # === AGENT COMMUNICATION ===
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        role: str,
        capabilities: List[Dict[str, Any]],
        contact_info: Dict[str, Any] = None
    ) -> bool:
        """Register an agent in the communication hub"""
        
        if not self.communication_hub:
            logger.error("Communication hub is not enabled")
            return False
        
        try:
            # Convert capabilities
            agent_capabilities = []
            for cap_data in capabilities:
                capability = AgentCapability(
                    name=cap_data["name"],
                    description=cap_data["description"],
                    level=cap_data.get("level", 3),
                    tags=cap_data.get("tags", [])
                )
                agent_capabilities.append(capability)
            
            # Convert role
            role_enum = AgentRole(role)
            
            return self.communication_hub.register_agent(
                agent_id=agent_id,
                name=name,
                role=role_enum,
                capabilities=agent_capabilities,
                contact_info=contact_info or {}
            )
            
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid agent registration data: {e}")
            return False
    
    def send_message(
        self,
        sender_agent_id: str,
        receiver_agent_id: str,
        subject: str,
        content: str,
        priority: str = "normal"
    ) -> Optional[str]:
        """Send message between agents"""
        
        if not self.communication_hub:
            logger.error("Communication hub is not enabled")
            return None
        
        try:
            priority_enum = MessagePriority(priority)
            
            return self.communication_hub.send_direct_message(
                sender_agent_id=sender_agent_id,
                receiver_agent_id=receiver_agent_id,
                subject=subject,
                content=content,
                priority=priority_enum
            )
            
        except ValueError as e:
            logger.error(f"Invalid message parameters: {e}")
            return None
    
    def broadcast_message(
        self,
        sender_agent_id: str,
        subject: str,
        content: str,
        target_roles: List[str] = None,
        target_agents: List[str] = None
    ) -> List[str]:
        """Broadcast message to multiple agents"""
        
        if not self.communication_hub:
            logger.error("Communication hub is not enabled")
            return []
        
        try:
            # Convert roles
            role_enums = None
            if target_roles:
                role_enums = [AgentRole(role) for role in target_roles]
            
            return self.communication_hub.broadcast_message(
                sender_agent_id=sender_agent_id,
                subject=subject,
                content=content,
                target_roles=role_enums,
                target_agents=target_agents
            )
            
        except ValueError as e:
            logger.error(f"Invalid broadcast parameters: {e}")
            return []
    
    def share_memory(
        self,
        sharing_agent_id: str,
        recipient_agent_id: str,
        memory_block_ids: List[str],
        access_level: str = "read_only",
        duration_hours: int = 24
    ) -> Optional[str]:
        """Share memory blocks between agents"""
        
        if not self.communication_hub:
            logger.error("Communication hub is not enabled")
            return None
        
        try:
            from agent_communication import AccessLevel
            
            access_level_enum = AccessLevel(access_level)
            
            return self.communication_hub.share_memory_blocks(
                sharing_agent_id=sharing_agent_id,
                recipient_agent_id=recipient_agent_id,
                memory_block_ids=memory_block_ids,
                access_level=access_level_enum,
                duration_hours=duration_hours
            )
            
        except ValueError as e:
            logger.error(f"Invalid memory share parameters: {e}")
            return None
    
    # === BACKUP AND RESTORE ===
    
    def create_backup(
        self,
        agent_id: str,
        backup_type: str = "full",
        description: str = "",
        tags: List[str] = None,
        retention_days: int = None
    ) -> Optional[str]:
        """Create backup of agent memory"""
        
        if not self.backup_manager:
            logger.error("Backup manager is not enabled")
            return None
        
        try:
            from backup_restore import BackupType
            
            backup_type_enum = BackupType(backup_type)
            
            return self.backup_manager.create_backup(
                agent_id=agent_id,
                backup_type=backup_type_enum,
                description=description,
                tags=tags or [],
                retention_days=retention_days
            )
            
        except ValueError as e:
            logger.error(f"Invalid backup parameters: {e}")
            return None
    
    def restore_backup(
        self,
        backup_id: str,
        agent_id: str,
        restore_mode: str = "merge"
    ) -> Optional[str]:
        """Restore backup to agent memory"""
        
        if not self.backup_manager:
            logger.error("Backup manager is not enabled")
            return None
        
        try:
            from backup_restore import RestoreMode
            
            restore_mode_enum = RestoreMode(restore_mode)
            
            return self.backup_manager.restore_backup(
                backup_id=backup_id,
                agent_id=agent_id,
                restore_mode=restore_mode_enum
            )
            
        except ValueError as e:
            logger.error(f"Invalid restore parameters: {e}")
            return None
    
    def list_backups(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups"""
        
        if not self.backup_manager:
            logger.error("Backup manager is not enabled")
            return []
        
        try:
            backups = self.backup_manager.list_backups(agent_id=agent_id)
            return [asdict(backup) for backup in backups]
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    # === MONITORING AND ANALYTICS ===
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        status = {
            "integration_system": {
                "status": "running" if self.is_running else "stopped",
                "components": {}
            },
            "letta_api": {},
            "memory_management": {},
            "communication": {},
            "performance": {}
        }
        
        # Letta API status
        try:
            health = self.client.health_check()
            status["letta_api"] = health
        except Exception as e:
            status["letta_api"] = {"error": str(e)}
        
        # Memory management status
        try:
            agents = self.client.get_agents()
            status["memory_management"] = {
                "total_agents": len(agents),
                "active_agents": len([a for a in agents if a.status == "active"])
            }
        except Exception as e:
            status["memory_management"] = {"error": str(e)}
        
        # Communication status
        if self.communication_hub:
            try:
                registered_agents = self.communication_hub.get_registered_agents()
                status["communication"] = {
                    "registered_agents": len(registered_agents),
                    "message_history_size": len(self.communication_hub.message_history)
                }
            except Exception as e:
                status["communication"] = {"error": str(e)}
        else:
            status["communication"] = {"enabled": False}
        
        # Performance monitoring status
        if self.performance_monitor:
            try:
                dashboard_data = self.performance_monitor.get_dashboard_data()
                status["performance"] = dashboard_data["monitoring_status"]
            except Exception as e:
                status["performance"] = {"error": str(e)}
        else:
            status["performance"] = {"enabled": False}
        
        return status
    
    def get_memory_usage(self, agent_id: str) -> Dict[str, Any]:
        """Get memory usage statistics for an agent"""
        
        return self.memory_manager.get_comprehensive_analytics(agent_id)
    
    def get_performance_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get performance metrics for an agent"""
        
        if self.performance_monitor:
            return self.performance_monitor.get_agent_metrics(agent_id)
        else:
            return {"error": "Performance monitoring is not enabled"}
    
    def get_recent_messages(self, agent_id: str, time_range_hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent messages for an agent"""
        
        if not self.communication_hub:
            logger.error("Communication hub is not enabled")
            return []
        
        try:
            messages = self.communication_hub.get_agent_messages(
                agent_id=agent_id,
                limit=50
            )
            
            return [
                {
                    "message_id": msg.message_id,
                    "subject": msg.subject,
                    "sender_agent_id": msg.sender_agent_id,
                    "timestamp": msg.timestamp.isoformat(),
                    "message_type": msg.message_type.value,
                    "priority": msg.priority.value
                }
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []
    
    def get_optimization_recommendations(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get memory optimization recommendations"""
        
        return self.memory_manager.get_optimization_recommendations(agent_id)
    
    def get_trading_advice(self, agent_id: str, query: str) -> Dict[str, Any]:
        """Get trading advice based on agent knowledge"""
        
        try:
            # Search for relevant memory
            search_results = self.search_memory_intelligent(
                agent_id=agent_id,
                query=query,
                search_options={"limit": 5}
            )
            
            # Get market context
            market_context = self.get_market_context(agent_id)
            
            # Generate advice based on findings
            advice = {
                "query": query,
                "relevant_memory_blocks": len(search_results),
                "market_regime": market_context.get("current_regime", {}).get("regime", "unknown"),
                "confidence_score": min(0.9, len(search_results) * 0.2),
                "recommendations": [
                    "Consider current market conditions",
                    "Review recent performance patterns",
                    "Monitor risk levels carefully"
                ],
                "supporting_evidence": [
                    {
                        "block_title": result.title,
                        "relevance_score": result.relevance_score,
                        "block_type": result.block_type.value
                    }
                    for result in search_results[:3]
                ]
            }
            
            return advice
            
        except Exception as e:
            logger.error(f"Error generating trading advice: {e}")
            return {"error": str(e)}
    
    def compare_strategies(self, agent_id: str, strategy_names: List[str]) -> Dict[str, Any]:
        """Compare trading strategies performance"""
        
        comparison = {}
        
        for strategy_name in strategy_names:
            try:
                # Get performance for this strategy
                patterns = self.client.get_trading_patterns(
                    agent_id=agent_id,
                    min_success_rate=0.0
                )
                
                strategy_patterns = [
                    p for p in patterns
                    if strategy_name.lower() in p.pattern_type.lower()
                ]
                
                if strategy_patterns:
                    success_rates = [p.success_rate for p in strategy_patterns]
                    comparison[strategy_name] = {
                        "pattern_count": len(strategy_patterns),
                        "average_success_rate": sum(success_rates) / len(success_rates),
                        "max_success_rate": max(success_rates),
                        "min_success_rate": min(success_rates),
                        "average_confidence": sum(p.confidence for p in strategy_patterns) / len(strategy_patterns)
                    }
                else:
                    comparison[strategy_name] = {
                        "pattern_count": 0,
                        "status": "no_patterns_found"
                    }
                    
            except Exception as e:
                comparison[strategy_name] = {
                    "error": str(e)
                }
        
        return comparison
    
    # === UTILITY METHODS ===
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an agent"""
        
        agent = self.client.get_agent(agent_id)
        if agent:
            return asdict(agent)
        return None
    
    def list_agents(self, role_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all agents, optionally filtered by role"""
        
        try:
            if role_filter:
                role_enum = AgentRole(role_filter)
                agents = self.client.get_agents()
                filtered_agents = [agent for agent in agents if agent.role == role_enum.value]
            else:
                filtered_agents = self.client.get_agents()
            
            return [asdict(agent) for agent in filtered_agents]
            
        except ValueError as e:
            logger.error(f"Invalid role filter: {e}")
            return []
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all components"""
        
        health = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {}
        }
        
        # Check Letta API
        try:
            letta_health = self.client.health_check()
            health["components"]["letta_api"] = letta_health
        except Exception as e:
            health["components"]["letta_api"] = {"error": str(e)}
            health["overall_status"] = "degraded"
        
        # Check memory management
        try:
            agents = self.client.get_agents()
            health["components"]["memory_management"] = {
                "status": "healthy",
                "agent_count": len(agents)
            }
        except Exception as e:
            health["components"]["memory_management"] = {"error": str(e)}
            health["overall_status"] = "degraded"
        
        # Check optional components
        if self.communication_hub:
            try:
                registered_agents = self.communication_hub.get_registered_agents()
                health["components"]["communication"] = {
                    "status": "healthy",
                    "registered_agents": len(registered_agents)
                }
            except Exception as e:
                health["components"]["communication"] = {"error": str(e)}
                health["overall_status"] = "degraded"
        
        if self.performance_monitor:
            try:
                dashboard_data = self.performance_monitor.get_dashboard_data()
                health["components"]["performance_monitoring"] = {
                    "status": "healthy",
                    "monitoring_active": dashboard_data["monitoring_status"]["is_active"]
                }
            except Exception as e:
                health["components"]["performance_monitoring"] = {"error": str(e)}
                health["overall_status"] = "degraded"
        
        return health
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired data from all components"""
        
        cleanup_results = {
            "expired_backups": 0,
            "expired_memory_shares": 0,
            "expired_alerts": 0,
            "space_freed_bytes": 0
        }
        
        # Cleanup backups
        if self.backup_manager:
            backup_cleanup = self.backup_manager.cleanup_expired_backups()
            cleanup_results["expired_backups"] = backup_cleanup["files_deleted"]
            cleanup_results["space_freed_bytes"] = backup_cleanup["space_freed_bytes"]
        
        # Cleanup communication hub
        if self.communication_hub:
            comm_cleanup = self.communication_hub.cleanup_expired_entries()
            cleanup_results["expired_memory_shares"] = comm_cleanup["expired_shares_cleaned"]
        
        # Cleanup performance monitor
        if self.performance_monitor:
            # Performance monitor handles its own cleanup
            pass
        
        return cleanup_results


# === CONVENIENT FACTORY FUNCTIONS ===

def create_trading_integration(
    letta_config: Dict[str, Any],
    redis_config: Optional[Dict[str, Any]] = None,
    backup_directory: str = "./backups"
) -> LettaIntegrationAPI:
    """Create a trading-focused integration API"""
    
    return LettaIntegrationAPI(
        letta_config=letta_config,
        redis_config=redis_config,
        backup_directory=backup_directory,
        enable_monitoring=True,
        enable_communication=True,
        enable_workflows=True,
        auto_optimization=True,
        auto_backup=False,  # Manual backups for trading
        optimization_interval_hours=6,
        backup_interval_hours=24
    )


def create_monitoring_integration(
    letta_config: Dict[str, Any],
    redis_config: Optional[Dict[str, Any]] = None,
    backup_directory: str = "./backups"
) -> LettaIntegrationAPI:
    """Create a monitoring-focused integration API"""
    
    return LettaIntegrationAPI(
        letta_config=letta_config,
        redis_config=redis_config,
        backup_directory=backup_directory,
        enable_monitoring=True,
        enable_communication=True,
        enable_workflows=False,
        auto_optimization=False,
        auto_backup=False,
        optimization_interval_hours=24,
        backup_interval_hours=168  # Weekly backups
    )


def create_development_integration(
    letta_config: Dict[str, Any],
    redis_config: Optional[Dict[str, Any]] = None,
    backup_directory: str = "./backups"
) -> LettaIntegrationAPI:
    """Create a development-focused integration API"""
    
    return LettaIntegrationAPI(
        letta_config=letta_config,
        redis_config=redis_config,
        backup_directory=backup_directory,
        enable_monitoring=True,
        enable_communication=True,
        enable_workflows=True,
        auto_optimization=False,
        auto_backup=False,
        optimization_interval_hours=1,  # Frequent for development
        backup_interval_hours=24
    )


# === EXAMPLE USAGE ===

async def example_usage():
    """Example of using the Letta Integration API"""
    
    # Configuration
    letta_config = {
        "base_url": "http://localhost:8283",
        "api_key": "your-secret-api-key",
        "enable_caching": True,
        "enable_monitoring": True
    }
    
    redis_config = {
        "host": "localhost",
        "port": 6379,
        "db": 1
    }
    
    # Create integration API
    api = create_trading_integration(letta_config, redis_config, "./demo_backups")
    
    try:
        # Start the system
        api.start()
        print("Letta Integration System Started")
        print("=" * 50)
        
        # Example 1: Create a memory block
        print("\n1. Creating Memory Block:")
        block_id = api.create_memory_block(
            agent_id="trading_strategist",
            block_type="trading_strategy",
            title="Moving Average Crossover Strategy",
            content="Strategy details for MA crossover trading...",
            priority="high",
            tags=["strategy", "moving_average"],
            metadata={"confidence": 0.8, "tested_period": "1y"}
        )
        print(f"   Created block: {block_id}")
        
        # Example 2: Create a trading pattern
        print("\n2. Creating Trading Pattern:")
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
        print(f"   Created pattern: {pattern_id}")
        
        # Example 3: Record trade outcome
        print("\n3. Recording Trade Outcome:")
        trade_data = {
            "trade_id": "demo_trade_001",
            "symbol": "AAPL",
            "action": "buy",
            "quantity": 100,
            "entry_price": 150.00,
            "exit_price": 155.50,
            "pnl": 5.50,
            "strategy": "bullish_breakout",
            "confidence": 0.8,
            "outcome": "win",
            "timestamp": datetime.now(),
            "metadata": {}
        }
        
        success = api.record_trade_outcome("trading_strategist", trade_data)
        print(f"   Trade recorded: {success}")
        
        # Example 4: Execute trade analysis workflow
        print("\n4. Executing Trade Analysis Workflow:")
        workflow_id = api.execute_trade_analysis_workflow("trading_strategist", trade_data)
        print(f"   Workflow ID: {workflow_id}")
        
        # Example 5: Search memory intelligently
        print("\n5. Intelligent Memory Search:")
        search_results = api.search_memory_intelligent(
            agent_id="trading_strategist",
            query="moving average strategy performance",
            search_options={"limit": 5}
        )
        print(f"   Found {len(search_results)} relevant results")
        
        # Example 6: Get trading opportunities
        print("\n6. Trading Opportunities:")
        opportunities = api.get_trading_opportunities("trading_strategist", confidence_threshold=0.7)
        print(f"   Found {len(opportunities)} opportunities")
        
        # Example 7: Get market context
        print("\n7. Market Context:")
        context = api.get_market_context("trading_strategist")
        print(f"   Current regime: {context.get('current_regime', {}).get('regime', 'unknown')}")
        
        # Example 8: Get system status
        print("\n8. System Status:")
        status = api.get_system_status()
        print(f"   Integration status: {status['integration_system']['status']}")
        print(f"   Active agents: {status['memory_management']['active_agents']}")
        
        # Example 9: Get memory analytics
        print("\n9. Memory Analytics:")
        analytics = api.get_memory_usage("trading_strategist")
        print(f"   Total blocks: {analytics.total_blocks}")
        print(f"   Memory utilization: {analytics.utilization_percentage:.1f}%")
        
        # Example 10: Get performance analysis
        print("\n10. Performance Analysis:")
        performance = api.get_performance_analysis("trading_strategist", period_days=30)
        if "error" not in performance:
            basic = performance["basic_metrics"]
            print(f"   Total trades: {basic['total_trades']}")
            print(f"   Win rate: {basic['win_rate']:.1%}")
            print(f"   Profit factor: {basic['profit_factor']:.2f}")
        
        # Keep running for demo
        print("\nSystem is running. Press Ctrl+C to stop...")
        try:
            while True:
                await asyncio.sleep(10)
                
                # Show periodic updates
                recent_messages = api.get_recent_messages("trading_strategist", time_range_hours=1)
                print(f"Recent messages: {len(recent_messages)}")
                
        except KeyboardInterrupt:
            print("\nShutting down...")
            
    finally:
        # Clean shutdown
        api.stop()
        print("Letta Integration System stopped")


if __name__ == "__main__":
    # Run example
    print("Letta Integration API Demo")
    print("=" * 50)
    
    # You can run the async example:
    # asyncio.run(example_usage())
    
    # Or create a simple integration for testing:
    letta_config = {
        "base_url": "http://localhost:8283",
        "api_key": "your-secret-api-key"
    }
    
    api = create_trading_integration(letta_config, backup_directory="./demo_backups")
    
    try:
        api.start()
        print("Integration API started successfully!")
        
        # Test basic functionality
        health = api.health_check()
        print(f"System health: {health['overall_status']}")
        
        agents = api.list_agents()
        print(f"Found {len(agents)} agents")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        api.stop()