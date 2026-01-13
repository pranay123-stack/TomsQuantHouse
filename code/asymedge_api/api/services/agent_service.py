"""
ASYMEdge Dashboard API - Letta Agent Integration

Comprehensive service for interacting with Letta stateful agents including:
- Agent lifecycle management
- Query processing and response handling
- Memory state management
- Performance monitoring
- Error handling and retry logic
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import json
import uuid
from dataclasses import dataclass

from api.config import settings
from api.database.models import AgentInstance, AgentQuery
from api.schemas import AgentQueryCreate, AgentQueryResponse, QueryStatus

logger = logging.getLogger(__name__)

@dataclass
class LettaAgentConfig:
    """Letta agent configuration"""
    agent_type: str
    model: str = "gpt-4"
    tools: List[str] = None
    memory_type: str = "conversation"
    system_prompt: str = ""
    temperature: float = 0.7
    max_tokens: int = 2048

class LettaClient:
    """Async client for Letta API integration"""
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or settings.LETTA_API_BASE_URL
        self.api_key = api_key or settings.LETTA_API_KEY
        self.timeout = aiohttp.ClientTimeout(total=settings.LETTA_TIMEOUT)
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._close_session()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is available"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}" if self.api_key else None
                }
            )
    
    async def _close_session(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def create_agent(self, config: LettaAgentConfig, name: str = None) -> Dict[str, Any]:
        """Create a new Letta agent"""
        try:
            await self._ensure_session()
            
            # Build agent creation payload
            payload = {
                "name": name or f"agent_{uuid.uuid4().hex[:8]}",
                "agent_type": config.agent_type,
                "model": config.model,
                "system_prompt": config.system_prompt,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "memory": {
                    "type": config.memory_type
                },
                "tools": config.tools or []
            }
            
            async with self._session.post(f"{self.base_url}/api/v1/agents", json=payload) as response:
                response.raise_for_status()
                result = await response.json()
                
                logger.info(f"Letta agent created: {result.get('id', 'unknown')}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to create Letta agent: {e}")
            raise
    
    async def delete_agent(self, agent_id: str) -> bool:
        """Delete a Letta agent"""
        try:
            await self._ensure_session()
            
            async with self._session.delete(f"{self.base_url}/api/v1/agents/{agent_id}") as response:
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete Letta agent {agent_id}: {e}")
            return False
    
    async def send_message(self, agent_id: str, message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a message to a Letta agent and get response"""
        try:
            await self._ensure_session()
            
            payload = {
                "message": message,
                "context": context or {}
            }
            
            async with self._session.post(
                f"{self.base_url}/api/v1/agents/{agent_id}/messages", 
                json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                return {
                    "response": result.get("response", ""),
                    "tokens_used": result.get("tokens_used", 0),
                    "execution_time": result.get("execution_time", 0.0),
                    "memory_update": result.get("memory_update", {}),
                    "tools_called": result.get("tools_called", [])
                }
                
        except Exception as e:
            logger.error(f"Failed to send message to agent {agent_id}: {e}")
            raise
    
    async def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get agent status and memory state"""
        try:
            await self._ensure_session()
            
            async with self._session.get(f"{self.base_url}/api/v1/agents/{agent_id}") as response:
                response.raise_for_status()
                result = await response.json()
                
                return {
                    "status": result.get("status", "unknown"),
                    "memory": result.get("memory", {}),
                    "tools": result.get("tools", []),
                    "created_at": result.get("created_at"),
                    "last_activity": result.get("last_activity"),
                    "resource_usage": result.get("resource_usage", {})
                }
                
        except Exception as e:
            logger.error(f"Failed to get status for agent {agent_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def update_agent_memory(self, agent_id: str, memory_update: Dict[str, Any]) -> bool:
        """Update agent memory state"""
        try:
            await self._ensure_session()
            
            payload = {
                "memory": memory_update
            }
            
            async with self._session.patch(
                f"{self.base_url}/api/v1/agents/{agent_id}/memory", 
                json=payload
            ) as response:
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update memory for agent {agent_id}: {e}")
            return False

class AgentManager:
    """Manager for agent lifecycle and operations"""
    
    def __init__(self):
        self.letta_client = LettaClient()
        self._agent_configs: Dict[str, LettaAgentConfig] = {}
        
    async def start_agent_instance(self, agent_definition_id: int, name: str, 
                                 configuration: Dict[str, Any], owner_id: int) -> str:
        """Start a new agent instance"""
        try:
            # Get agent definition configuration
            agent_config = await self._get_agent_config(agent_definition_id)
            
            # Merge with instance configuration
            final_config = {**agent_config.__dict__, **configuration}
            
            # Create Letta agent
            letta_config = LettaAgentConfig(
                agent_type=final_config["letta_agent_type"],
                model=final_config.get("model", "gpt-4"),
                tools=final_config.get("tools", []),
                memory_type=final_config.get("memory_type", "conversation"),
                system_prompt=final_config.get("system_prompt", ""),
                temperature=final_config.get("temperature", 0.7),
                max_tokens=final_config.get("max_tokens", 2048)
            )
            
            async with LettaClient() as client:
                letta_agent = await client.create_agent(letta_config, name)
                letta_agent_id = letta_agent["id"]
                
                # Update database record with Letta agent ID
                # This would typically be done through a database service
                
                logger.info(f"Agent instance started: {letta_agent_id}")
                return letta_agent_id
                
        except Exception as e:
            logger.error(f"Failed to start agent instance: {e}")
            raise
    
    async def stop_agent_instance(self, letta_agent_id: str) -> bool:
        """Stop an agent instance"""
        try:
            async with LettaClient() as client:
                success = await client.delete_agent(letta_agent_id)
                
                if success:
                    logger.info(f"Agent instance stopped: {letta_agent_id}")
                else:
                    logger.warning(f"Failed to stop agent instance: {letta_agent_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to stop agent instance {letta_agent_id}: {e}")
            return False
    
    async def process_query(self, letta_agent_id: str, query_text: str, 
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a query through a Letta agent"""
        try:
            start_time = datetime.now()
            
            async with LettaClient() as client:
                # Send message to Letta agent
                response = await client.send_message(
                    letta_agent_id, 
                    query_text, 
                    metadata
                )
                
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds() * 1000
                
                result = {
                    "response_text": response["response"],
                    "token_count": response["tokens_used"],
                    "execution_time_ms": execution_time,
                    "memory_update": response["memory_update"],
                    "tools_called": response["tools_called"],
                    "status": "completed"
                }
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to process query for agent {letta_agent_id}: {e}")
            return {
                "response_text": None,
                "token_count": 0,
                "execution_time_ms": 0,
                "memory_update": {},
                "tools_called": [],
                "status": "error",
                "error_message": str(e)
            }
    
    async def get_agent_status(self, letta_agent_id: str) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        try:
            async with LettaClient() as client:
                status = await client.get_agent_status(letta_agent_id)
                
                # Add derived metrics
                if status.get("status") == "running":
                    status["activity_status"] = "active"
                    status["last_activity_ago"] = self._calculate_time_ago(status.get("last_activity"))
                else:
                    status["activity_status"] = "inactive"
                
                return status
                
        except Exception as e:
            logger.error(f"Failed to get agent status for {letta_agent_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def update_agent_memory(self, letta_agent_id: str, 
                                memory_update: Dict[str, Any]) -> bool:
        """Update agent memory state"""
        try:
            async with LettaClient() as client:
                success = await client.update_agent_memory(letta_agent_id, memory_update)
                return success
                
        except Exception as e:
            logger.error(f"Failed to update agent memory for {letta_agent_id}: {e}")
            return False
    
    async def batch_process_queries(self, queries: List[Dict[str, Any]], 
                                  max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """Process multiple queries concurrently"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_query(query_data):
            async with semaphore:
                return await self.process_query(
                    query_data["agent_id"],
                    query_data["query_text"],
                    query_data.get("metadata")
                )
        
        tasks = [process_single_query(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [result if not isinstance(result, Exception) else {"status": "error", "error": str(result)} 
                for result in results]
    
    def _calculate_time_ago(self, timestamp: Optional[datetime]) -> Optional[str]:
        """Calculate human-readable time ago string"""
        if not timestamp:
            return None
            
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    async def _get_agent_config(self, agent_definition_id: int) -> LettaAgentConfig:
        """Get agent configuration from database"""
        # This would fetch from database in a real implementation
        # For now, return a default configuration
        return LettaAgentConfig(
            agent_type="general_assistant",
            model="gpt-4",
            tools=["web_search", "calculator"],
            memory_type="conversation",
            system_prompt="You are a helpful assistant for trading and analysis."
        )

class AgentQueryService:
    """Service for handling agent query operations"""
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        
    async def execute_query(self, agent_instance_id: int, query_data: AgentQueryCreate) -> AgentQueryResponse:
        """Execute an agent query and track results"""
        try:
            # Get agent instance details
            agent_instance = await self._get_agent_instance(agent_instance_id)
            if not agent_instance:
                raise ValueError(f"Agent instance {agent_instance_id} not found")
            
            # Create database record for query
            query_record = await self._create_query_record(
                agent_instance_id, query_data.query_text, query_data.metadata
            )
            
            try:
                # Process query through Letta agent
                result = await self.agent_manager.process_query(
                    agent_instance.letta_agent_id,
                    query_data.query_text,
                    query_data.metadata
                )
                
                # Update query record with results
                await self._update_query_record(
                    query_record.id,
                    result
                )
                
                # Update agent memory if needed
                if result.get("memory_update"):
                    await self.agent_manager.update_agent_memory(
                        agent_instance.letta_agent_id,
                        result["memory_update"]
                    )
                
                # Return response schema
                return AgentQueryResponse(
                    id=query_record.id,
                    agent_instance_id=agent_instance_id,
                    query_text=query_data.query_text,
                    response_text=result.get("response_text"),
                    status=QueryStatus.COMPLETED if result.get("status") == "completed" else QueryStatus.ERROR,
                    execution_time_ms=result.get("execution_time_ms"),
                    token_count=result.get("token_count"),
                    error_message=result.get("error_message"),
                    created_at=query_record.created_at,
                    completed_at=datetime.now()
                )
                
            except Exception as e:
                # Update query record with error
                await self._update_query_record(
                    query_record.id,
                    {"status": "error", "error_message": str(e)}
                )
                raise
                
        except Exception as e:
            logger.error(f"Failed to execute query for agent {agent_instance_id}: {e}")
            raise
    
    async def get_query_history(self, agent_instance_id: int, limit: int = 50) -> List[AgentQueryResponse]:
        """Get query history for an agent instance"""
        # This would fetch from database in real implementation
        return []
    
    async def get_agent_performance_metrics(self, agent_instance_id: int) -> Dict[str, Any]:
        """Get performance metrics for an agent instance"""
        # This would calculate metrics from query history
        return {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_execution_time": 0.0,
            "average_tokens_per_query": 0.0,
            "success_rate": 0.0
        }
    
    async def _get_agent_instance(self, agent_instance_id: int) -> Optional[AgentInstance]:
        """Get agent instance from database"""
        # This would fetch from database in real implementation
        return None
    
    async def _create_query_record(self, agent_instance_id: int, query_text: str, 
                                 metadata: Optional[Dict[str, Any]]) -> AgentQuery:
        """Create query record in database"""
        # This would create record in database
        return AgentQuery(
            id=1,  # Placeholder
            agent_instance_id=agent_instance_id,
            query_text=query_text,
            status=QueryStatus.PROCESSING,
            metadata=metadata or {},
            created_at=datetime.now()
        )
    
    async def _update_query_record(self, query_id: int, update_data: Dict[str, Any]):
        """Update query record in database"""
        # This would update record in database
        pass

# Global agent manager instance
agent_manager = AgentManager()
agent_query_service = AgentQueryService(agent_manager)