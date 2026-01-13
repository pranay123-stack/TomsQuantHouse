"""
ASYMEdge Dashboard API - Streaming Routes

Real-time streaming endpoints providing:
- WebSocket connections for live data
- Subscription management for different data types
- Real-time agent activity updates
- Live trading metrics streaming
- System alerts and notifications
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.responses import HTMLResponse
from typing import List, Optional, Dict, Any, Set
import json
import logging

from api.services.streaming_service import streaming_service, SubscriptionType
from api.middleware.auth import get_current_user
from api.database.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

# WebSocket connection manager
class WebSocketManager:
    """Manage WebSocket connections per user"""
    
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove WebSocket connection"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], user_id: int):
        """Send message to all connections for a user"""
        if user_id not in self.active_connections:
            return
        
        message_str = json.dumps(message)
        
        # Send to all connections for this user
        disconnected_connections = set()
        
        for connection in self.active_connections[user_id].copy():
            try:
                await connection.send_text(message_str)
            except WebSocketDisconnect:
                disconnected_connections.add(connection)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message to user {user_id}: {e}")
                disconnected_connections.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected_connections:
            self.active_connections[user_id].discard(connection)
        
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected users"""
        message_str = json.dumps(message)
        
        for user_id, connections in self.active_connections.items():
            for connection in connections.copy():
                try:
                    await connection.send_text(message_str)
                except WebSocketDisconnect:
                    connections.discard(connection)
                except Exception as e:
                    logger.error(f"Failed to broadcast message to user {user_id}: {e}")
                    connections.discard(connection)
            
            if not connections:
                del self.active_connections[user_id]

# Global WebSocket manager
ws_manager = WebSocketManager()

@router.get("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user: User = Depends(get_current_user),
    subscriptions: Optional[str] = Query(None, description="JSON array of subscription configs")
):
    """Main WebSocket endpoint for real-time streaming"""
    try:
        # Parse subscription configurations
        subscription_configs = []
        if subscriptions:
            try:
                subscription_configs = json.loads(subscriptions)
            except json.JSONDecodeError:
                await websocket.close(code=1008, reason="Invalid subscription format")
                return
        
        # Connect to streaming service
        await streaming_service.handle_websocket_connection(
            websocket, user.id, subscription_configs
        )
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        await websocket.close(code=1011, reason="Internal server error")

@router.websocket("/live")
async def live_data_websocket(websocket: WebSocket):
    """Simplified WebSocket for live data streaming"""
    await websocket.accept()
    
    user_id = None
    try:
        # Wait for authentication message
        auth_message = await websocket.receive_text()
        auth_data = json.loads(auth_message)
        
        if auth_message.get("type") != "auth":
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        # Extract user ID (in production, validate token)
        user_id = auth_data.get("user_id", 1)  # Default demo user
        
        # Connect to manager
        await ws_manager.connect(websocket, user_id)
        
        # Send welcome message
        welcome_message = {
            "type": "connected",
            "message": "Connected to ASYMEdge live data stream",
            "timestamp": "2025-11-02T09:09:04.123Z"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Handle messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                data = json.loads(message)
                
                message_type = data.get("type")
                
                if message_type == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": "2025-11-02T09:09:04.123Z"
                    }))
                
                elif message_type == "subscribe":
                    # Handle subscription changes
                    subscription_type = data.get("subscription_type")
                    filters = data.get("filters", {})
                    
                    # In production, would update subscriptions in streaming service
                    await websocket.send_text(json.dumps({
                        "type": "subscription_confirmed",
                        "subscription_type": subscription_type,
                        "filters": filters
                    }))
                
                elif message_type == "get_status":
                    # Send current status
                    status_message = {
                        "type": "status",
                        "subscriptions": ["agent_activity", "trading_metrics"],
                        "connected_since": "2025-11-02T09:09:04.123Z",
                        "message_count": 0
                    }
                    await websocket.send_text(json.dumps(status_message))
                
                else:
                    # Unknown message type
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    }))
            
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
            except Exception as e:
                logger.error(f"WebSocket message handling error: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Internal server error"
                }))
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        if user_id:
            ws_manager.disconnect(websocket, user_id)

@router.get("/subscriptions", response_model=Dict[str, Any])
async def get_streaming_subscriptions(
    user: User = Depends(get_current_user)
):
    """Get available streaming subscription types and configurations"""
    try:
        # Get active subscriptions for user (from streaming service)
        active_subscriptions = await streaming_service.connection_manager.get_active_subscriptions(user.id)
        
        subscription_info = {
            "available_types": [
                {
                    "type": "agent_activity",
                    "description": "Real-time agent activity updates",
                    "filters": ["agent_id", "status", "activity_type"],
                    "update_frequency": "real-time"
                },
                {
                    "type": "trading_metrics",
                    "description": "Live trading metrics and portfolio updates",
                    "filters": ["metric_type", "symbol", "portfolio_id"],
                    "update_frequency": "real-time"
                },
                {
                    "type": "workflow_status",
                    "description": "Workflow execution status updates",
                    "filters": ["workflow_id", "status", "workflow_type"],
                    "update_frequency": "real-time"
                },
                {
                    "type": "market_data",
                    "description": "Real-time market data and price updates",
                    "filters": ["symbol", "exchange", "data_type"],
                    "update_frequency": "real-time"
                },
                {
                    "type": "system_alerts",
                    "description": "System alerts and notifications",
                    "filters": ["severity", "alert_type", "component"],
                    "update_frequency": "as-needed"
                },
                {
                    "type": "portfolio_updates",
                    "description": "Portfolio value and allocation updates",
                    "filters": ["portfolio_id", "user_id"],
                    "update_frequency": "real-time"
                }
            ],
            "active_subscriptions": [
                {
                    "id": sub.subscription_id,
                    "type": sub.subscription_type.value,
                    "filters": sub.filters,
                    "created_at": sub.created_at.isoformat(),
                    "message_count": sub.message_count
                }
                for sub in active_subscriptions
            ],
            "connection_info": {
                "max_connections_per_user": settings.WEBSOCKET_MAX_CONNECTIONS,
                "heartbeat_interval": settings.WEBSOCKET_HEARTBEAT_INTERVAL,
                "supported_protocols": ["websocket", "wss"]
            }
        }
        
        return subscription_info
        
    except Exception as e:
        logger.error(f"Failed to get streaming subscriptions: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/publish/agent-update", response_model=Dict[str, Any])
async def publish_agent_update(
    agent_id: int,
    status: str,
    activity: Optional[str] = None,
    performance: Optional[Dict[str, float]] = None,
    user: User = Depends(get_current_user)
):
    """Publish agent activity update (admin/simulated)"""
    try:
        await streaming_service.publish_agent_update(agent_id, status, activity, performance)
        
        return {
            "success": True,
            "message": "Agent update published",
            "agent_id": agent_id,
            "status": status,
            "timestamp": "2025-11-02T09:09:04.123Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to publish agent update: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/publish/metric-update", response_model=Dict[str, Any])
async def publish_metric_update(
    metric_type: str,
    value: float,
    symbol: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user)
):
    """Publish trading metric update (admin/simulated)"""
    try:
        await streaming_service.publish_metric_update(metric_type, value, symbol, metadata)
        
        return {
            "success": True,
            "message": "Metric update published",
            "metric_type": metric_type,
            "value": value,
            "symbol": symbol,
            "timestamp": "2025-11-02T09:09:04.123Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to publish metric update: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/publish/workflow-update", response_model=Dict[str, Any])
async def publish_workflow_update(
    workflow_id: int,
    status: str,
    current_step: Optional[str] = None,
    progress: Optional[float] = None,
    output: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """Publish workflow status update (admin/simulated)"""
    try:
        await streaming_service.publish_workflow_update(
            workflow_id, status, current_step, progress, output, error
        )
        
        return {
            "success": True,
            "message": "Workflow update published",
            "workflow_id": workflow_id,
            "status": status,
            "timestamp": "2025-11-02T09:09:04.123Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to publish workflow update: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/publish/system-alert", response_model=Dict[str, Any])
async def publish_system_alert(
    alert_type: str,
    message: str,
    severity: str = "normal",
    metadata: Optional[Dict[str, Any]] = None,
    user: User = Depends(get_current_user)
):
    """Publish system alert (admin/simulated)"""
    try:
        await streaming_service.publish_system_alert(alert_type, message, severity, metadata)
        
        return {
            "success": True,
            "message": "System alert published",
            "alert_type": alert_type,
            "severity": severity,
            "timestamp": "2025-11-02T09:09:04.123Z"
        }
        
    except Exception as e:
        logger.error(f"Failed to publish system alert: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/stats", response_model=Dict[str, Any])
async def get_streaming_statistics(user: User = Depends(get_current_user)):
    """Get streaming service statistics"""
    try:
        # Get connection statistics from WebSocket manager
        connection_stats = {
            "total_active_connections": sum(len(connections) for connections in ws_manager.active_connections.values()),
            "user_connection_counts": {
                str(user_id): len(connections) 
                for user_id, connections in ws_manager.active_connections.items()
            }
        }
        
        # Get rate limit statistics from streaming service
        rate_limit_stats = {
            "total_subscriptions": len(streaming_service.connection_manager.subscriptions),
            "active_subscriptions": len([
                sub for sub in streaming_service.connection_manager.subscriptions.values()
                if sub.is_active
            ]),
            "subscription_types": {
                "agent_activity": len([
                    sub for sub in streaming_service.connection_manager.subscriptions.values()
                    if sub.subscription_type == SubscriptionType.AGENT_ACTIVITY and sub.is_active
                ]),
                "trading_metrics": len([
                    sub for sub in streaming_service.connection_manager.subscriptions.values()
                    if sub.subscription_type == SubscriptionType.TRADING_METRICS and sub.is_active
                ]),
                "workflow_status": len([
                    sub for sub in streaming_service.connection_manager.subscriptions.values()
                    if sub.subscription_type == SubscriptionType.WORKFLOW_STATUS and sub.is_active
                ]),
                "market_data": len([
                    sub for sub in streaming_service.connection_manager.subscriptions.values()
                    if sub.subscription_type == SubscriptionType.MARKET_DATA and sub.is_active
                ]),
                "system_alerts": len([
                    sub for sub in streaming_service.connection_manager.subscriptions.values()
                    if sub.subscription_type == SubscriptionType.SYSTEM_ALERTS and sub.is_active
                ])
            }
        }
        
        return {
            "timestamp": "2025-11-02T09:09:04.123Z",
            "connections": connection_stats,
            "subscriptions": rate_limit_stats,
            "service_status": "healthy",
            "uptime": "running"
        }
        
    except Exception as e:
        logger.error(f"Failed to get streaming statistics: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/health", response_model=Dict[str, Any])
async def get_streaming_health(user: User = Depends(get_current_user)):
    """Get streaming service health status"""
    try:
        return {
            "status": "healthy",
            "timestamp": "2025-11-02T09:09:04.123Z",
            "components": {
                "websocket_manager": "healthy",
                "streaming_service": "healthy",
                "connection_manager": "healthy",
                "data_generation": "healthy"
            },
            "metrics": {
                "active_connections": len(ws_manager.active_connections),
                "total_subscriptions": len(streaming_service.connection_manager.subscriptions),
                "message_queue_size": "N/A",  # Would get from actual queue
                "memory_usage": "N/A"  # Would get actual memory stats
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get streaming health: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.get("/test-stream", response_class=HTMLResponse)
async def test_stream_page(user: User = Depends(get_current_user)):
    """Simple HTML page for testing WebSocket streaming"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ASYMEdge Streaming Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .log { background: #f5f5f5; border: 1px solid #ddd; padding: 10px; height: 300px; overflow-y: scroll; }
            button { margin: 5px; padding: 10px; }
            .status { padding: 5px; margin: 5px; border-radius: 3px; }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <h1>ASYMEdge Real-time Streaming Test</h1>
        
        <div>
            <span id="connectionStatus" class="status disconnected">Disconnected</span>
            <button onclick="connectWebSocket()">Connect</button>
            <button onclick="disconnectWebSocket()">Disconnect</button>
            <button onclick="clearLog()">Clear Log</button>
        </div>
        
        <div>
            <h3>Test Controls</h3>
            <button onclick="subscribeToAgentUpdates()">Subscribe to Agent Updates</button>
            <button onclick="subscribeToTradingMetrics()">Subscribe to Trading Metrics</button>
            <button onclick="subscribeToWorkflowStatus()">Subscribe to Workflow Status</button>
            <button onclick="pingServer()">Send Ping</button>
        </div>
        
        <h3>Stream Log</h3>
        <div id="log" class="log"></div>
        
        <script>
            let ws = null;
            let reconnectInterval = null;
            
            function log(message) {
                const logDiv = document.getElementById('log');
                const timestamp = new Date().toISOString();
                logDiv.innerHTML += `[${timestamp}] ${message}<br>`;
                logDiv.scrollTop = logDiv.scrollHeight;
            }
            
            function updateConnectionStatus(connected) {
                const statusSpan = document.getElementById('connectionStatus');
                statusSpan.textContent = connected ? 'Connected' : 'Disconnected';
                statusSpan.className = `status ${connected ? 'connected' : 'disconnected'}`;
            }
            
            function connectWebSocket() {
                const wsUrl = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host + '/api/v1/streaming/live';
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = function(event) {
                    log('WebSocket connected');
                    updateConnectionStatus(true);
                    
                    // Send authentication
                    ws.send(JSON.stringify({
                        type: 'auth',
                        user_id: 1,
                        token: 'demo_token'
                    }));
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    log(`Received: ${JSON.stringify(data, null, 2)}`);
                };
                
                ws.onclose = function(event) {
                    log('WebSocket disconnected');
                    updateConnectionStatus(false);
                    
                    // Auto-reconnect
                    if (!reconnectInterval) {
                        reconnectInterval = setTimeout(() => {
                            connectWebSocket();
                            reconnectInterval = null;
                        }, 3000);
                    }
                };
                
                ws.onerror = function(error) {
                    log('WebSocket error: ' + error);
                };
            }
            
            function disconnectWebSocket() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
                if (reconnectInterval) {
                    clearTimeout(reconnectInterval);
                    reconnectInterval = null;
                }
            }
            
            function subscribeToAgentUpdates() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'subscribe',
                        subscription_type: 'agent_activity',
                        filters: { agent_id: 1 }
                    }));
                }
            }
            
            function subscribeToTradingMetrics() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'subscribe',
                        subscription_type: 'trading_metrics',
                        filters: { metric_type: 'portfolio_value' }
                    }));
                }
            }
            
            function subscribeToWorkflowStatus() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'subscribe',
                        subscription_type: 'workflow_status',
                        filters: { workflow_id: 1 }
                    }));
                }
            }
            
            function pingServer() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'ping' }));
                }
            }
            
            function clearLog() {
                document.getElementById('log').innerHTML = '';
            }
            
            // Auto-connect on page load
            window.onload = function() {
                setTimeout(connectWebSocket, 1000);
            };
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)