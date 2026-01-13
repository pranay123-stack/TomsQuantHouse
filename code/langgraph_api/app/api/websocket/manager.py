"""
WebSocket manager for real-time updates
"""

import json
import logging
from typing import Dict, Set, Any, Optional
from datetime import datetime
import asyncio
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from ..auth.auth_models import User

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    """WebSocket message types"""
    WORKFLOW_UPDATE = "workflow_update"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    ALERT = "alert"
    METRICS_UPDATE = "metrics_update"
    HEARTBEAT = "heartbeat"
    USER_NOTIFICATION = "user_notification"
    SYSTEM_STATUS = "system_status"
    ERROR = "error"

class WebSocketManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        # Active connections: user_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # Connection metadata: websocket -> metadata
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[str, datetime] = {}
        
        # Message queues for offline users
        self.message_queues: Dict[str, list] = {}
        
        # Subscriptions: user_id -> set of subscription types
        self.subscriptions: Dict[str, Set[str]] = {}
        
        logger.info("WebSocket manager initialized")
    
    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: str,
        user: Optional[User] = None,
        subscription_types: Optional[Set[str]] = None
    ) -> None:
        """Accept WebSocket connection"""
        await websocket.accept()
        
        # Add to active connections
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.now(),
            "user": user,
            "subscription_types": subscription_types or {"workflow_updates"}
        }
        
        # Track subscriptions
        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = set()
        
        self.subscriptions[user_id].update(subscription_types or {"workflow_updates"})
        
        # Send welcome message
        await self.send_message(websocket, {
            "type": MessageType.HEARTBEAT,
            "message": "Connected to LangGraph API WebSocket",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id
        })
        
        logger.info(f"WebSocket connected: user {user_id}")
        
        # Send any queued messages
        if user_id in self.message_queues:
            for message in self.message_queues[user_id]:
                await self.send_message(websocket, message)
            self.message_queues[user_id].clear()
    
    def disconnect(self, user_id: str, websocket: WebSocket = None) -> None:
        """Disconnect WebSocket"""
        if websocket:
            # Disconnect specific websocket
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Clean up metadata
                if websocket in self.connection_metadata:
                    del self.connection_metadata[websocket]
                
                # If no more connections for this user, clean up user data
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    if user_id in self.subscriptions:
                        del self.subscriptions[user_id]
                    if user_id in self.last_heartbeat:
                        del self.last_heartbeat[user_id]
        else:
            # Disconnect all connections for user
            if user_id in self.active_connections:
                for ws in list(self.active_connections[user_id]):
                    if ws in self.connection_metadata:
                        del self.connection_metadata[ws]
                del self.active_connections[user_id]
                
                if user_id in self.subscriptions:
                    del self.subscriptions[user_id]
                if user_id in self.last_heartbeat:
                    del self.last_heartbeat[user_id]
        
        logger.info(f"WebSocket disconnected: user {user_id}")
    
    async def send_message(
        self, 
        websocket: WebSocket, 
        message: Dict[str, Any]
    ) -> None:
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            # Connection likely closed, clean it up
            user_id = self.connection_metadata.get(websocket, {}).get("user_id")
            if user_id:
                self.disconnect(user_id, websocket)
    
    async def send_to_user(
        self, 
        user_id: str, 
        message: Dict[str, Any],
        message_type: str = "notification"
    ) -> None:
        """Send message to all connections for a specific user"""
        if user_id in self.active_connections:
            message["message_type"] = message_type
            message["timestamp"] = datetime.now().isoformat()
            
            # Send to all active connections
            disconnected_users = []
            for websocket in list(self.active_connections[user_id]):
                try:
                    await self.send_message(websocket, message)
                except Exception as e:
                    logger.warning(f"Failed to send message to user {user_id}: {e}")
                    disconnected_users.append(websocket)
            
            # Clean up disconnected websockets
            for ws in disconnected_users:
                self.active_connections[user_id].discard(ws)
                if ws in self.connection_metadata:
                    del self.connection_metadata[ws]
        else:
            # User not connected, queue message
            if user_id not in self.message_queues:
                self.message_queues[user_id] = []
            
            message["message_type"] = message_type
            message["timestamp"] = datetime.now().isoformat()
            message["queued"] = True
            self.message_queues[user_id].append(message)
    
    async def broadcast_to_subscribers(
        self, 
        subscription_type: str, 
        message: Dict[str, Any]
    ) -> None:
        """Broadcast message to all users subscribed to a specific type"""
        message["subscription_type"] = subscription_type
        message["timestamp"] = datetime.now().isoformat()
        
        disconnected_users = []
        
        for user_id, connections in self.active_connections.items():
            if user_id in self.subscriptions and subscription_type in self.subscriptions[user_id]:
                for websocket in list(connections):
                    try:
                        await self.send_message(websocket, message)
                    except Exception as e:
                        logger.warning(f"Failed to broadcast to user {user_id}: {e}")
                        disconnected_users.append((user_id, websocket))
        
        # Clean up disconnected websockets
        for user_id, ws in disconnected_users:
            self.disconnect(user_id, ws)
    
    async def send_workflow_update(
        self, 
        user_id: str, 
        workflow_id: str,
        status: str,
        progress: float = 0.0,
        current_node: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """Send workflow execution update"""
        update_message = {
            "type": MessageType.WORKFLOW_UPDATE,
            "workflow_id": workflow_id,
            "status": status,
            "progress": progress,
            "current_node": current_node,
            "message": message
        }
        
        await self.send_to_user(user_id, update_message, "workflow_update")
    
    async def send_workflow_completion(
        self, 
        user_id: str, 
        workflow_id: str,
        execution_id: str,
        result: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None
    ) -> None:
        """Send workflow completion notification"""
        completion_message = {
            "type": MessageType.WORKFLOW_COMPLETED,
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "result": result,
            "execution_time": execution_time
        }
        
        await self.send_to_user(user_id, completion_message, "workflow_completed")
    
    async def send_workflow_failure(
        self, 
        user_id: str, 
        workflow_id: str,
        execution_id: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send workflow failure notification"""
        failure_message = {
            "type": MessageType.WORKFLOW_FAILED,
            "workflow_id": workflow_id,
            "execution_id": execution_id,
            "error_message": error_message,
            "error_details": error_details
        }
        
        await self.send_to_user(user_id, failure_message, "workflow_failed")
    
    async def send_alert(
        self, 
        user_id: str, 
        alert_level: str,
        title: str,
        message: str,
        workflow_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send alert notification"""
        alert_message = {
            "type": MessageType.ALERT,
            "alert_level": alert_level,
            "title": title,
            "message": message,
            "workflow_id": workflow_id,
            "details": details
        }
        
        await self.send_to_user(user_id, alert_message, "alert")
    
    async def send_metrics_update(
        self, 
        user_id: str, 
        metrics: Dict[str, Any]
    ) -> None:
        """Send metrics update"""
        metrics_message = {
            "type": MessageType.METRICS_UPDATE,
            "metrics": metrics
        }
        
        await self.send_to_user(user_id, metrics_message, "metrics_update")
    
    async def send_heartbeat(self, user_id: str) -> None:
        """Send heartbeat to user"""
        self.last_heartbeat[user_id] = datetime.now()
        
        heartbeat_message = {
            "type": MessageType.HEARTBEAT,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_to_user(user_id, heartbeat_message, "heartbeat")
    
    async def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    async def get_connected_users(self) -> Set[str]:
        """Get set of connected user IDs"""
        return set(self.active_connections.keys())
    
    async def cleanup_stale_connections(self, timeout_minutes: int = 30) -> None:
        """Clean up stale WebSocket connections"""
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        stale_users = []
        
        for user_id, last_heartbeat_time in self.last_heartbeat.items():
            if last_heartbeat_time < cutoff_time:
                stale_users.append(user_id)
        
        for user_id in stale_users:
            self.disconnect(user_id)
            logger.info(f"Cleaned up stale WebSocket connection for user {user_id}")
    
    async def handle_websocket_communication(self, websocket: WebSocket):
        """Handle WebSocket communication"""
        user_id = self.connection_metadata.get(websocket, {}).get("user_id")
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    message_type = message.get("type")
                    
                    if message_type == "ping":
                        # Respond to ping
                        await self.send_message(websocket, {
                            "type": "pong",
                            "timestamp": datetime.now().isoformat()
                        })
                    elif message_type == "subscribe":
                        # Handle subscription changes
                        subscription_types = message.get("subscription_types", [])
                        if user_id and user_id in self.subscriptions:
                            self.subscriptions[user_id].update(subscription_types)
                            
                    elif message_type == "unsubscribe":
                        # Handle unsubscription
                        subscription_types = message.get("subscription_types", [])
                        if user_id and user_id in self.subscriptions:
                            self.subscriptions[user_id].discard(subscription_types)
                            
                    elif message_type == "get_status":
                        # Send current status
                        await self.send_message(websocket, {
                            "type": "status",
                            "connected_users": len(await self.get_connected_users()),
                            "total_connections": await self.get_connection_count(),
                            "timestamp": datetime.now().isoformat()
                        })
                    
                except json.JSONDecodeError:
                    await self.send_message(websocket, {
                        "type": MessageType.ERROR,
                        "message": "Invalid JSON message"
                    })
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {user_id}")
        except Exception as e:
            logger.error(f"WebSocket communication error: {e}")
            if user_id:
                self.disconnect(user_id, websocket)

# Global WebSocket manager instance
ws_manager = WebSocketManager()