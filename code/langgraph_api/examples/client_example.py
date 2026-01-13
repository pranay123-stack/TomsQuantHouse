"""
Example client for LangGraph API
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

class LangGraphAPIClient:
    """Async client for LangGraph API"""
    
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def _request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        async with self.session.request(method, url, json=data, headers=headers) as response:
            response_data = await response.json()
            
            if response.status >= 400:
                raise Exception(f"API error: {response.status} - {response_data}")
            
            return response_data
    
    # Authentication endpoints
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login to get access token"""
        return await self._request("POST", "/api/v1/auth/login", {
            "username": username,
            "password": password
        })
    
    async def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register new user"""
        return await self._request("POST", "/api/v1/auth/register", {
            "username": username,
            "email": email,
            "password": password
        })
    
    # Workflow endpoints
    async def create_workflow(self, name: str, workflow_type: str, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create new workflow"""
        workflow_data = {
            "name": name,
            "workflow_type": workflow_type,
            "config": config or {}
        }
        return await self._request("POST", "/api/v1/workflows/", workflow_data)
    
    async def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow by ID"""
        return await self._request("GET", f"/api/v1/workflows/{workflow_id}")
    
    async def list_workflows(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """List workflows"""
        return await self._request("GET", f"/api/v1/workflows/?page={page}&per_page={per_page}")
    
    async def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update workflow"""
        return await self._request("PUT", f"/api/v1/workflows/{workflow_id}", updates)
    
    async def delete_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Delete workflow"""
        return await self._request("DELETE", f"/api/v1/workflows/{workflow_id}")
    
    async def execute_workflow(
        self, 
        workflow_id: str, 
        input_data: Dict[str, Any] = None,
        synchronous: bool = True
    ) -> Dict[str, Any]:
        """Execute workflow"""
        execution_data = {
            "workflow_id": workflow_id,
            "input_data": input_data or {},
            "synchronous": synchronous
        }
        return await self._request("POST", f"/api/v1/workflows/{workflow_id}/execute", execution_data)
    
    async def execute_batch_workflows(self, executions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple workflows"""
        batch_data = {
            "executions": executions,
            "max_concurrent": 5
        }
        return await self._request("POST", "/api/v1/workflows/execute/batch", batch_data)
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status"""
        return await self._request("GET", f"/api/v1/workflows/{workflow_id}/status")
    
    async def get_workflow_history(self, workflow_id: str, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get workflow execution history"""
        return await self._request("GET", f"/api/v1/workflows/{workflow_id}/history?page={page}&per_page={per_page}")
    
    # State endpoints
    async def create_state(
        self, 
        workflow_id: str, 
        node_name: str, 
        state_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create workflow state"""
        state_create_data = {
            "workflow_id": workflow_id,
            "node_name": node_name,
            "state_data": state_data
        }
        return await self._request("POST", "/api/v1/states/", state_create_data)
    
    async def get_state(self, state_id: str) -> Dict[str, Any]:
        """Get state by ID"""
        return await self._request("GET", f"/api/v1/states/{state_id}")
    
    async def list_states(self, workflow_id: str = None, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """List states"""
        params = f"?page={page}&per_page={per_page}"
        if workflow_id:
            params += f"&workflow_id={workflow_id}"
        return await self._request("GET", f"/api/v1/states/{params}")
    
    async def get_workflow_states(self, workflow_id: str, latest_only: bool = False) -> List[Dict[str, Any]]:
        """Get all states for a workflow"""
        params = f"?latest_only={latest_only}"
        return await self._request("GET", f"/api/v1/states/workflow/{workflow_id}{params}")
    
    async def update_state(self, state_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update state"""
        return await self._request("PUT", f"/api/v1/states/{state_id}", updates)
    
    async def delete_state(self, state_id: str) -> Dict[str, Any]:
        """Delete state"""
        return await self._request("DELETE", f"/api/v1/states/{state_id}")
    
    # Monitoring endpoints
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        return await self._request("GET", "/api/v1/monitoring/health")
    
    async def get_workflow_health(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow health"""
        return await self._request("GET", f"/api/v1/monitoring/health/{workflow_id}")
    
    async def get_system_metrics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get system metrics"""
        return await self._request("GET", f"/api/v1/monitoring/metrics?time_range_hours={time_range_hours}")
    
    async def get_workflow_metrics(self, workflow_id: str, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get workflow metrics"""
        return await self._request("GET", f"/api/v1/monitoring/metrics/workflow/{workflow_id}?time_range_hours={time_range_hours}")
    
    async def get_alerts(self, severity: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get system alerts"""
        params = f"?limit={limit}"
        if severity:
            params += f"&severity={severity}"
        return await self._request("GET", f"/api/v1/monitoring/alerts{params}")
    
    async def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get dashboard summary"""
        return await self._request("GET", "/api/v1/monitoring/dashboards/summary")
    
    # Visualization endpoints
    async def get_workflow_graph(self, workflow_id: str, format: str = "mermaid") -> Dict[str, Any]:
        """Get workflow graph visualization"""
        return await self._request("GET", f"/api/v1/visualization/graph/{workflow_id}?format={format}")
    
    async def get_workflow_timeline(self, workflow_id: str, format: str = "mermaid") -> Dict[str, Any]:
        """Get workflow timeline"""
        return await self._request("GET", f"/api/v1/visualization/timeline/{workflow_id}?format={format}")
    
    async def get_state_flow_diagram(self, workflow_id: str, format: str = "mermaid") -> Dict[str, Any]:
        """Get state flow diagram"""
        return await self._request("GET", f"/api/v1/visualization/state-flow/{workflow_id}?format={format}")
    
    async def get_execution_path(self, workflow_id: str, format: str = "json") -> Dict[str, Any]:
        """Get execution path"""
        return await self._request("GET", f"/api/v1/visualization/execution-path/{workflow_id}?format={format}")
    
    async def get_metrics_charts(self, workflow_id: str = None, chart_type: str = "overview") -> Dict[str, Any]:
        """Get metrics charts"""
        params = f"?chart_type={chart_type}"
        if workflow_id:
            params += f"&workflow_id={workflow_id}"
        return await self._request("GET", f"/api/v1/visualization/metrics/charts{params}")
    
    async def get_execution_heatmap(self, workflow_id: str = None, time_range_hours: int = 168) -> Dict[str, Any]:
        """Get execution heatmap"""
        params = f"?time_range_hours={time_range_hours}"
        if workflow_id:
            params += f"&workflow_id={workflow_id}"
        return await self._request("GET", f"/api/v1/visualization/heatmap{params}")
    
    # User endpoints
    async def get_current_user(self) -> Dict[str, Any]:
        """Get current user info"""
        return await self._request("GET", "/api/v1/auth/me")
    
    async def update_current_user(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update current user"""
        return await self._request("PUT", "/api/v1/auth/me", updates)
    
    async def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """Change password"""
        return await self._request("POST", "/api/v1/auth/change-password", {
            "current_password": current_password,
            "new_password": new_password
        })
    
    # WebSocket connection for real-time updates
    async def connect_websocket(self, user_id: str):
        """Connect to WebSocket for real-time updates"""
        url = f"{self.base_url.replace('http', 'ws')}/ws/{user_id}"
        headers = self._get_headers()
        
        return await self.session.ws_connect(url, headers=headers)

# Example usage
async def example_usage():
    """Example of using the LangGraph API client"""
    
    # Initialize client
    async with LangGraphAPIClient("http://localhost:8000", "your-api-key") as client:
        
        # 1. Login
        login_result = await client.login("username", "password")
        print(f"Logged in: {login_result}")
        
        # 2. Create workflow
        workflow = await client.create_workflow(
            name="Data Processing Workflow",
            workflow_type="data_pipeline",
            config={
                "nodes": [
                    {"id": "start", "type": "start"},
                    {"id": "process", "type": "process"},
                    {"id": "end", "type": "end"}
                ],
                "edges": [
                    {"from": "start", "to": "process"},
                    {"from": "process", "to": "end"}
                ]
            }
        )
        print(f"Created workflow: {workflow}")
        
        # 3. Execute workflow
        execution = await client.execute_workflow(
            workflow_id=workflow["id"],
            input_data={"input": "test data"},
            synchronous=True
        )
        print(f"Execution result: {execution}")
        
        # 4. Create state
        state = await client.create_state(
            workflow_id=workflow["id"],
            node_name="process",
            state_data={"status": "running", "progress": 0.5}
        )
        print(f"Created state: {state}")
        
        # 5. Get workflow visualization
        graph = await client.get_workflow_graph(workflow["id"], "mermaid")
        print(f"Workflow graph: {graph}")
        
        # 6. Get system health
        health = await client.get_system_health()
        print(f"System health: {health}")
        
        # 7. Get dashboard summary
        dashboard = await client.get_dashboard_summary()
        print(f"Dashboard: {dashboard}")

if __name__ == "__main__":
    asyncio.run(example_usage())