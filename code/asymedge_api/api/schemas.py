"""
ASYMEdge Dashboard API - Pydantic Schemas

Pydantic models for API request/response validation including:
- User management schemas
- Agent query and management schemas
- Trading metrics schemas
- Workflow monitoring schemas
- Dashboard configuration schemas
- Authentication schemas
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums for type safety
class UserTier(str, Enum):
    DEFAULT = "default"
    PREMIUM = "premium" 
    ENTERPRISE = "enterprise"

class AgentStatus(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"
    PAUSED = "paused"

class QueryStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SubscriptionType(str, Enum):
    AGENTS = "agents"
    TRADING = "trading"
    WORKFLOWS = "workflows"
    SYSTEM = "system"

# User Management Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    tier: UserTier = UserTier.DEFAULT

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    tier: Optional[UserTier] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    is_superuser: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

class TokenRefresh(BaseModel):
    refresh_token: str

# Authentication Schemas
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

# Agent Management Schemas
class AgentDefinitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    letta_agent_type: str = Field(..., min_length=1, max_length=100)
    configuration: Dict[str, Any]
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    version: str = Field(default="1.0.0", max_length=20)

class AgentDefinitionCreate(AgentDefinitionBase):
    pass

class AgentDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    version: Optional[str] = Field(None, max_length=20)

class AgentDefinitionResponse(AgentDefinitionBase):
    id: int
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AgentInstanceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    agent_definition_id: int
    configuration: Dict[str, Any]

class AgentInstanceCreate(AgentInstanceBase):
    pass

class AgentInstanceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    configuration: Optional[Dict[str, Any]] = None
    status: Optional[AgentStatus] = None

class AgentInstanceResponse(AgentInstanceBase):
    id: int
    letta_agent_id: str
    status: AgentStatus
    memory_state: Optional[Dict[str, Any]] = None
    last_activity: Optional[datetime] = None
    resource_usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    definition: AgentDefinitionResponse
    
    class Config:
        from_attributes = True

# Agent Query Schemas
class AgentQueryBase(BaseModel):
    query_text: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None

class AgentQueryCreate(AgentQueryBase):
    agent_instance_id: int

class AgentQueryResponse(AgentQueryBase):
    id: int
    agent_instance_id: int
    response_text: Optional[str] = None
    status: QueryStatus
    execution_time_ms: Optional[float] = None
    token_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Trading Metrics Schemas
class TradingMetricBase(BaseModel):
    metric_type: str = Field(..., min_length=1, max_length=50)
    symbol: Optional[str] = Field(None, max_length=20)
    value: float
    currency: str = Field(default="USD", max_length=3)
    metadata: Optional[Dict[str, Any]] = None

class TradingMetricCreate(TradingMetricBase):
    timestamp: Optional[datetime] = None

class TradingMetricResponse(TradingMetricBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

class MarketDataBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    price: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    source: str = Field(default="internal", max_length=50)

class MarketDataResponse(MarketDataBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

class TradingAnalyticsResponse(BaseModel):
    portfolio_value: float
    total_pnl: float
    daily_pnl: float
    total_return: float
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    timestamp: datetime

# Workflow Management Schemas
class WorkflowDefinitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    workflow_type: str = Field(..., min_length=1, max_length=50)
    configuration: Dict[str, Any]
    version: str = Field(default="1.0.0", max_length=20)

class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    pass

class WorkflowDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    version: Optional[str] = Field(None, max_length=20)

class WorkflowDefinitionResponse(WorkflowDefinitionBase):
    id: int
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class WorkflowInstanceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    workflow_definition_id: int
    configuration: Dict[str, Any]
    input_data: Optional[Dict[str, Any]] = None

class WorkflowInstanceCreate(WorkflowInstanceBase):
    pass

class WorkflowInstanceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    configuration: Optional[Dict[str, Any]] = None
    status: Optional[WorkflowStatus] = None
    current_step: Optional[str] = None
    progress: Optional[float] = Field(None, ge=0.0, le=1.0)

class WorkflowInstanceResponse(WorkflowInstanceBase):
    id: int
    status: WorkflowStatus
    current_step: Optional[str] = None
    progress: float
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_log: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    definition: WorkflowDefinitionResponse
    
    class Config:
        from_attributes = True

# Dashboard Configuration Schemas
class DashboardConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    layout_config: Dict[str, Any]
    widget_configs: Dict[str, Any]
    theme_config: Optional[Dict[str, Any]] = None
    filters_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class DashboardConfigCreate(DashboardConfigBase):
    is_default: bool = False
    is_public: bool = False

class DashboardConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    layout_config: Optional[Dict[str, Any]] = None
    widget_configs: Optional[Dict[str, Any]] = None
    theme_config: Optional[Dict[str, Any]] = None
    filters_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None
    is_public: Optional[bool] = None

class DashboardConfigResponse(DashboardConfigBase):
    id: int
    owner_id: int
    is_default: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# System and Monitoring Schemas
class SystemLogBase(BaseModel):
    level: LogLevel
    message: str = Field(..., min_length=1)
    module: Optional[str] = Field(None, max_length=50)
    function: Optional[str] = Field(None, max_length=100)
    line_number: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class SystemLogResponse(SystemLogBase):
    id: int
    user_id: Optional[int] = None
    request_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class StreamingSubscriptionBase(BaseModel):
    subscription_type: SubscriptionType
    filter_config: Optional[Dict[str, Any]] = None

class StreamingSubscriptionResponse(StreamingSubscriptionBase):
    id: int
    user_id: int
    subscription_id: str
    is_active: bool
    last_activity: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Health and Status Schemas
class HealthStatus(BaseModel):
    status: str
    timestamp: datetime
    version: str
    uptime: Optional[float] = None
    services: Dict[str, str]

class DatabaseHealth(BaseModel):
    status: str
    connectivity: bool
    database: Dict[str, Any]
    tables: Dict[str, int]
    timestamp: Any

# WebSocket Message Schemas
class WebSocketMessage(BaseModel):
    type: str  # agent_update, metric_update, workflow_update, system_alert
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    subscription_id: Optional[str] = None

class AgentUpdateMessage(BaseModel):
    agent_id: int
    status: AgentStatus
    activity: Optional[str] = None
    memory_update: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, float]] = None

class MetricUpdateMessage(BaseModel):
    metric_type: str
    symbol: Optional[str]
    value: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class WorkflowUpdateMessage(BaseModel):
    workflow_id: int
    status: WorkflowStatus
    current_step: Optional[str]
    progress: float
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# API Response Wrappers
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

class PaginationResponse(BaseModel):
    success: bool
    data: List[Any]
    pagination: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)

# Query Parameter Schemas
class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", regex="^(asc|desc)$")

class DateRangeParams(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if v and 'start_date' in values and values['start_date']:
            if v < values['start_date']:
                raise ValueError('end_date must be after start_date')
        return v

# Export all schemas
__all__ = [
    # User schemas
    "UserBase", "UserCreate", "UserUpdate", "UserResponse", 
    "UserLogin", "TokenResponse", "TokenRefresh",
    "PasswordChange", "PasswordReset", "PasswordResetConfirm",
    
    # Agent schemas
    "AgentDefinitionBase", "AgentDefinitionCreate", "AgentDefinitionUpdate", "AgentDefinitionResponse",
    "AgentInstanceBase", "AgentInstanceCreate", "AgentInstanceUpdate", "AgentInstanceResponse",
    "AgentQueryBase", "AgentQueryCreate", "AgentQueryResponse",
    
    # Trading schemas
    "TradingMetricBase", "TradingMetricCreate", "TradingMetricResponse",
    "MarketDataBase", "MarketDataResponse", "TradingAnalyticsResponse",
    
    # Workflow schemas
    "WorkflowDefinitionBase", "WorkflowDefinitionCreate", "WorkflowDefinitionUpdate", "WorkflowDefinitionResponse",
    "WorkflowInstanceBase", "WorkflowInstanceCreate", "WorkflowInstanceUpdate", "WorkflowInstanceResponse",
    
    # Dashboard schemas
    "DashboardConfigBase", "DashboardConfigCreate", "DashboardConfigUpdate", "DashboardConfigResponse",
    
    # System schemas
    "SystemLogBase", "SystemLogResponse", "StreamingSubscriptionBase", "StreamingSubscriptionResponse",
    "HealthStatus", "DatabaseHealth",
    
    # WebSocket schemas
    "WebSocketMessage", "AgentUpdateMessage", "MetricUpdateMessage", "WorkflowUpdateMessage",
    
    # Response wrappers
    "APIResponse", "ErrorResponse", "PaginationResponse",
    
    # Query parameters
    "PaginationParams", "DateRangeParams"
]