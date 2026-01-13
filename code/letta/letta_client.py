#!/usr/bin/env python3
"""
Letta REST API Client
Provides functionality to interact with Letta agents and their memory
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LettaClient:
    def __init__(self, base_url: str = "http://localhost:8283", api_key: str = "your-secret-api-key-here"):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to Letta API"""
        url = f"{self.base_url}/api/{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {"error": str(e)}
    
    def get_agents(self) -> List[Dict[str, Any]]:
        """Get all agents"""
        return self._make_request("GET", "agents")
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get specific agent by ID"""
        return self._make_request("GET", f"agents/{agent_id}")
    
    def get_agent_by_name(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent by name"""
        agents = self.get_agents()
        for agent in agents:
            if agent.get("name") == agent_name:
                return agent
        return None
    
    def send_message(self, agent_id: str, message: str, role: str = "user") -> Dict[str, Any]:
        """Send message to agent and get response"""
        data = {
            "agent_id": agent_id,
            "message": message,
            "role": role,
            "stream": False
        }
        return self._make_request("POST", "agents/message", data)
    
    def get_agent_memory(self, agent_id: str) -> Dict[str, Any]:
        """Get agent's memory blocks"""
        return self._make_request("GET", f"agents/{agent_id}/memory")
    
    def add_memory_block(self, agent_id: str, memory_config: Dict[str, Any]) -> Dict[str, Any]:
        """Add memory block to agent"""
        return self._make_request("POST", f"agents/{agent_id}/memory", memory_config)
    
    def update_memory_block(self, agent_id: str, block_id: str, content: str, metadata: Dict = None) -> Dict[str, Any]:
        """Update existing memory block"""
        data = {
            "content": content,
            "metadata": metadata or {}
        }
        return self._make_request("PUT", f"agents/{agent_id}/memory/{block_id}", data)
    
    def delete_memory_block(self, agent_id: str, block_id: str) -> Dict[str, Any]:
        """Delete memory block"""
        return self._make_request("DELETE", f"agents/{agent_id}/memory/{block_id}")
    
    def search_memory(self, agent_id: str, query: str) -> List[Dict[str, Any]]:
        """Search agent memory blocks"""
        data = {
            "query": query,
            "agent_id": agent_id
        }
        return self._make_request("POST", "memory/search", data)

class TradingAgentQuery:
    """Specialized queries for trading agents"""
    
    def __init__(self, letta_client: LettaClient):
        self.client = letta_client
    
    def get_trading_strategies(self, agent_name: str = "trading_strategist") -> List[Dict[str, Any]]:
        """Get trading strategy memory blocks"""
        agent = self.client.get_agent_by_name(agent_name)
        if not agent:
            return []
        
        memory = self.client.get_agent_memory(agent["id"])
        return [
            block for block in memory.get("blocks", [])
            if block.get("block_type") == "trading_strategy"
        ]
    
    def get_market_conditions(self, agent_name: str = "market_analyst") -> List[Dict[str, Any]]:
        """Get market condition memory blocks"""
        agent = self.client.get_agent_by_name(agent_name)
        if not agent:
            return []
        
        memory = self.client.get_agent_memory(agent["id"])
        return [
            block for block in memory.get("blocks", [])
            if block.get("block_type") == "market_conditions"
        ]
    
    def get_risk_parameters(self, agent_name: str = "risk_manager") -> List[Dict[str, Any]]:
        """Get risk parameter memory blocks"""
        agent = self.client.get_agent_by_name(agent_name)
        if not agent:
            return []
        
        memory = self.client.get_agent_memory(agent["id"])
        return [
            block for block in memory.get("blocks", [])
            if block.get("block_type") == "risk_parameters"
        ]
    
    def get_learned_patterns(self, agent_name: str = "trading_strategist") -> List[Dict[str, Any]]:
        """Get learned patterns memory blocks"""
        agent = self.client.get_agent_by_name(agent_name)
        if not agent:
            return []
        
        memory = self.client.get_agent_memory(agent["id"])
        return [
            block for block in memory.get("blocks", [])
            if block.get("block_type") == "learned_patterns"
        ]
    
    def get_market_analysis(self, agent_name: str = "market_analyst") -> Dict[str, Any]:
        """Get complete market analysis"""
        agent = self.client.get_agent_by_name(agent_name)
        if not agent:
            return {}
        
        memory = self.client.get_agent_memory(agent["id"])
        
        return {
            "agent_info": agent,
            "market_conditions": [
                block for block in memory.get("blocks", [])
                if block.get("block_type") == "market_conditions"
            ],
            "system_context": [
                block for block in memory.get("blocks", [])
                if block.get("block_type") == "system_context"
            ],
            "recent_activity": [
                block for block in memory.get("blocks", [])
                if block.get("block_type") == "recent"
            ]
        }
    
    def query_trading_advice(self, agent_name: str, query: str) -> Dict[str, Any]:
        """Query trading agent for advice based on stored knowledge"""
        agent = self.client.get_agent_by_name(agent_name)
        if not agent:
            return {"error": f"Agent {agent_name} not found"}
        
        # First try to get relevant memory
        memory = self.client.get_agent_memory(agent["id"])
        
        # Send message to agent with context
        context = f"Based on the trading knowledge stored in my memory blocks, please provide advice on: {query}"
        response = self.client.send_message(agent["id"], context)
        
        return {
            "query": query,
            "response": response,
            "available_memory": {
                block["block_type"]: block["title"]
                for block in memory.get("blocks", [])
            }
        }
    
    def update_trading_performance(self, agent_name: str, trade_result: Dict[str, Any]) -> bool:
        """Update agent memory with new trading performance data"""
        agent = self.client.get_agent_by_name(agent_name)
        if not agent:
            return False
        
        # Create new memory block for the trade result
        memory_block = {
            "block_type": "learned_patterns",
            "title": f"Trade Result - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": json.dumps(trade_result, indent=2),
            "value_type": "json",
            "metadata": {
                "trade_date": datetime.now().isoformat(),
                "performance_type": "trade_result",
                "processed_by": "TradingAgentQuery"
            }
        }
        
        result = self.client.add_memory_block(agent["id"], memory_block)
        return "error" not in result

def main():
    """Example usage of LettaClient"""
    client = LettaClient()
    trading_queries = TradingAgentQuery(client)
    
    # Load agent IDs
    try:
        with open("/workspace/code/letta/agent_ids.json", "r") as f:
            agent_ids = json.load(f)
    except FileNotFoundError:
        print("Agent IDs file not found. Please run create_agents.py first.")
        return
    
    print("Letta Trading Agent Client - Query Examples")
    print("=" * 50)
    
    # Example 1: Get all agents
    print("\n1. Listing all agents:")
    agents = client.get_agents()
    for agent in agents:
        print(f"  - {agent.get('name', 'Unknown')}: {agent.get('id', 'No ID')}")
    
    # Example 2: Get trading strategies
    print("\n2. Trading Strategies:")
    strategies = trading_queries.get_trading_strategies()
    for strategy in strategies:
        print(f"  - {strategy.get('title', 'No title')}")
        print(f"    {strategy.get('content', 'No content')[:100]}...")
    
    # Example 3: Get market conditions
    print("\n3. Market Conditions:")
    conditions = trading_queries.get_market_conditions()
    for condition in conditions:
        print(f"  - {condition.get('title', 'No title')}")
        print(f"    {condition.get('content', 'No content')[:100]}...")
    
    # Example 4: Get risk parameters
    print("\n4. Risk Parameters:")
    risks = trading_queries.get_risk_parameters()
    for risk in risks:
        print(f"  - {risk.get('title', 'No title')}")
        print(f"    {risk.get('content', 'No content')[:100]}...")
    
    # Example 5: Query for trading advice
    print("\n5. Query Trading Advice:")
    query = "What are the current market conditions and should I be cautious about?"
    response = trading_queries.query_trading_advice("market_analyst", query)
    print(f"Query: {query}")
    print(f"Response: {response.get('response', {}).get('messages', [{}])[-1].get('content', 'No response')}")
    
    # Example 6: Update trading performance
    print("\n6. Update Trading Performance:")
    trade_result = {
        "symbol": "AAPL",
        "entry_price": 150.00,
        "exit_price": 155.50,
        "profit_loss": 5.50,
        "percentage_return": 3.67,
        "trade_duration": "2 days",
        "setup_type": "pullback_to_ma",
        "success": True
    }
    
    success = trading_queries.update_trading_performance("trading_strategist", trade_result)
    print(f"Performance update: {'Success' if success else 'Failed'}")

if __name__ == "__main__":
    main()