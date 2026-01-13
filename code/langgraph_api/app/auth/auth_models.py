"""
Authentication models and data structures
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
import uuid

class UserRole(str, Enum):
    """User roles for authorization"""
    ADMIN = "admin"
    PREMIUM = "premium"
    STANDARD = "standard"
    BASIC = "basic"

class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class NodeStatus(str, Enum):
    """Workflow node execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

# User Models
class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.BASIC
    is_active: bool = True
    is_verified: bool = False

class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(min_length=8, description="Password (minimum 8 characters)")

class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class User(UserBase):
    """Complete user model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    login_attempts: int = 0
    locked_until: Optional[datetime] = None

    class Config:
        from_attributes = True

# Authentication Models
class Token(BaseModel):
    """JWT token model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    username: str
    role: UserRole
    permissions: list[str] = []

class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str
    remember_me: bool = False

class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str

# Workflow Models
class WorkflowCreate(BaseModel):
    """Workflow creation model"""
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = None
    workflow_type: str = Field(..., description="Workflow type")
    config: dict = Field(default_factory=dict, description="Workflow configuration")
    timeout_minutes: int = Field(default=60, description="Workflow timeout in minutes")
    priority: int = Field(default=0, description="Workflow priority")

class WorkflowUpdate(BaseModel):
    """Workflow update model"""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    timeout_minutes: Optional[int] = None
    priority: Optional[int] = None

class Workflow(WorkflowCreate):
    """Complete workflow model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[dict] = None
    execution_count: int = 0

    class Config:
        from_attributes = True

# Workflow Execution Models
class WorkflowExecutionRequest(BaseModel):
    """Workflow execution request model"""
    workflow_id: str
    input_data: dict = Field(default_factory=dict, description="Input data for workflow")
    context: dict = Field(default_factory=dict, description="Execution context")
    callback_url: Optional[str] = None
    synchronous: bool = Field(default=True, description="Execute synchronously")

class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response model"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime = Field(default_factory=datetime.now)
    estimated_completion: Optional[datetime] = None
    message: Optional[str] = None

class BatchWorkflowExecutionRequest(BaseModel):
    """Batch workflow execution request model"""
    executions: list[WorkflowExecutionRequest]
    max_concurrent: int = Field(default=5, description="Maximum concurrent executions")
    fail_fast: bool = Field(default=True, description="Stop on first failure")

# State Management Models
class StateCreate(BaseModel):
    """Workflow state creation model"""
    workflow_id: str
    node_name: str
    state_data: dict = Field(..., description="Node state data")
    metadata: dict = Field(default_factory=dict, description="State metadata")

class StateUpdate(BaseModel):
    """Workflow state update model"""
    state_data: Optional[dict] = None
    metadata: Optional[dict] = None
    status: Optional[NodeStatus] = None

class State(StateCreate):
    """Complete workflow state model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: NodeStatus = NodeStatus.PENDING
    execution_time_ms: Optional[int] = None

    class Config:
        from_attributes = True

# Monitoring Models
class HealthStatus(BaseModel):
    """Health status model"""
    status: str  # healthy, degraded, unhealthy
    timestamp: datetime = Field(default_factory=datetime.now)
    components: dict[str, str]
    metrics: dict[str, float] = Field(default_factory=dict)
    alerts: list[dict] = Field(default_factory=list)

class MetricsData(BaseModel):
    """Metrics data model"""
    timestamp: datetime = Field(default_factory=datetime.now)
    workflow_count: int
    active_workflows: int
    completed_workflows: int
    failed_workflows: int
    avg_execution_time: float
    system_load: float
    memory_usage: float
    cpu_usage: float

# API Response Models
class APIResponse(BaseModel):
    """Base API response model"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: dict
    timestamp: datetime = Field(default_factory=datetime.now)

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: list
    total: int
    page: int
    per_page: int
    pages: int

# WebSocket Models
class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: str  # workflow_update, alert, metrics, heartbeat
    data: dict
    timestamp: datetime = Field(default_factory=datetime.now)

class WorkflowUpdateMessage(BaseModel):
    """Workflow update WebSocket message"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    progress: float = 0.0
    current_node: Optional[str] = None
    message: Optional[str] = None

class AlertMessage(BaseModel):
    """Alert WebSocket message"""
    level: str  # info, warning, error, critical
    title: str
    message: str
    workflow_id: Optional[str] = None
    details: Optional[dict] = None