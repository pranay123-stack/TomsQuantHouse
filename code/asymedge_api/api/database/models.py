"""
ASYMEdge Dashboard API - Database Models

SQLAlchemy models for all database entities including:
- User management and authentication
- Agent instances and configurations
- Trading metrics and performance data
- Workflow monitoring and status tracking
- Dashboard configurations and customizations
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    tier = Column(String(20), default="default")  # default, premium, enterprise
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    agent_instances = relationship("AgentInstance", back_populates="owner", cascade="all, delete-orphan")
    workflows = relationship("WorkflowInstance", back_populates="owner", cascade="all, delete-orphan")
    dashboard_configs = relationship("DashboardConfig", back_populates="owner", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tier='{self.tier}')>"

class UserSession(Base):
    """User session model for authentication tracking"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

class AgentDefinition(Base):
    """Agent definition model for reusable agent templates"""
    __tablename__ = "agent_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    letta_agent_type = Column(String(100), nullable=False)
    configuration = Column(JSON, nullable=False)  # Agent-specific configuration
    input_schema = Column(JSON, nullable=True)  # Expected input format
    output_schema = Column(JSON, nullable=True)  # Expected output format
    version = Column(String(20), default="1.0.0")
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    instances = relationship("AgentInstance", back_populates="definition", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentDefinition(id={self.id}, name='{self.name}', type='{self.letta_agent_type}')>"

class AgentInstance(Base):
    """Agent instance model for running agents"""
    __tablename__ = "agent_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    agent_definition_id = Column(Integer, ForeignKey("agent_definitions.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    letta_agent_id = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(20), default="stopped")  # stopped, running, error, paused
    configuration = Column(JSON, nullable=False)  # Instance-specific configuration
    memory_state = Column(JSON, nullable=True)  # Current memory state
    last_activity = Column(DateTime, nullable=True)
    resource_usage = Column(JSON, nullable=True)  # CPU, memory, etc.
    metadata = Column(JSON, nullable=True)  # Additional metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    definition = relationship("AgentDefinition", back_populates="instances")
    owner = relationship("User", back_populates="agent_instances")
    queries = relationship("AgentQuery", back_populates="agent_instance", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AgentInstance(id={self.id}, name='{self.name}', status='{self.status}')>"

class AgentQuery(Base):
    """Agent query model for tracking agent interactions"""
    __tablename__ = "agent_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_instance_id = Column(Integer, ForeignKey("agent_instances.id"), nullable=False)
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending, processing, completed, error
    execution_time_ms = Column(Float, nullable=True)
    token_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata = Column(JSON, nullable=True)  # Additional query metadata
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    agent_instance = relationship("AgentInstance", back_populates="queries")
    
    def __repr__(self):
        return f"<AgentQuery(id={self.id}, agent_id={self.agent_instance_id}, status='{self.status}')>"

class TradingMetric(Base):
    """Trading metrics model for performance tracking"""
    __tablename__ = "trading_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_type = Column(String(50), nullable=False)  # portfolio_value, pnl, sharpe_ratio, etc.
    symbol = Column(String(20), nullable=True)  # For symbol-specific metrics
    value = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    timestamp = Column(DateTime, default=func.now(), index=True)
    metadata = Column(JSON, nullable=True)  # Additional metric data
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_trading_metrics_type_timestamp', 'metric_type', 'timestamp'),
        Index('idx_trading_metrics_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_trading_metrics_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<TradingMetric(id={self.id}, type='{self.metric_type}', value={self.value}, symbol='{self.symbol}')>"

class MarketData(Base):
    """Market data model for real-time and historical data"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)
    bid = Column(Float, nullable=True)
    ask = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=func.now(), index=True)
    source = Column(String(50), default="internal")  # data provider source
    
    # Indexes
    __table_args__ = (
        Index('idx_market_data_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_market_data_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<MarketData(id={self.id}, symbol='{self.symbol}', price={self.price})>"

class WorkflowDefinition(Base):
    """Workflow definition model for reusable workflow templates"""
    __tablename__ = "workflow_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    workflow_type = Column(String(50), nullable=False)  # trading, analysis, monitoring, etc.
    configuration = Column(JSON, nullable=False)  # Workflow configuration
    version = Column(String(20), default="1.0.0")
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    creator = relationship("User")
    instances = relationship("WorkflowInstance", back_populates="definition", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<WorkflowDefinition(id={self.id}, name='{self.name}', type='{self.workflow_type}')>"

class WorkflowInstance(Base):
    """Workflow instance model for running workflows"""
    __tablename__ = "workflow_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    workflow_definition_id = Column(Integer, ForeignKey("workflow_definitions.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed, cancelled
    current_step = Column(String(50), nullable=True)
    progress = Column(Float, default=0.0)  # 0.0 to 1.0
    configuration = Column(JSON, nullable=False)  # Instance-specific configuration
    input_data = Column(JSON, nullable=True)  # Workflow input
    output_data = Column(JSON, nullable=True)  # Workflow output
    error_message = Column(Text, nullable=True)
    execution_log = Column(JSON, nullable=True)  # Step-by-step execution log
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    definition = relationship("WorkflowDefinition", back_populates="instances")
    owner = relationship("User", back_populates="workflows")
    
    def __repr__(self):
        return f"<WorkflowInstance(id={self.id}, name='{self.name}', status='{self.status}')>"

class DashboardConfig(Base):
    """Dashboard configuration model for user customizations"""
    __tablename__ = "dashboard_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_default = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    layout_config = Column(JSON, nullable=False)  # Widget positions and sizes
    widget_configs = Column(JSON, nullable=False)  # Individual widget configurations
    theme_config = Column(JSON, nullable=True)  # Theme and appearance settings
    filters_config = Column(JSON, nullable=True)  # Data filters and preferences
    metadata = Column(JSON, nullable=True)  # Additional configuration data
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="dashboard_configs")
    
    def __repr__(self):
        return f"<DashboardConfig(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"

class SystemLog(Base):
    """System log model for monitoring and debugging"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    module = Column(String(50), nullable=True)  # Source module/component
    function = Column(String(100), nullable=True)  # Source function
    line_number = Column(Integer, nullable=True)  # Source line number
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Associated user
    request_id = Column(String(100), nullable=True)  # Request tracking ID
    metadata = Column(JSON, nullable=True)  # Additional log data
    created_at = Column(DateTime, default=func.now(), index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_system_logs_level_timestamp', 'level', 'created_at'),
        Index('idx_system_logs_user_timestamp', 'user_id', 'created_at'),
        Index('idx_system_logs_module_timestamp', 'module', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', message='{self.message[:50]}...')>"

class StreamingSubscription(Base):
    """Streaming subscription model for real-time data management"""
    __tablename__ = "streaming_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_type = Column(String(50), nullable=False)  # agents, trading, workflows, system
    subscription_id = Column(String(255), unique=True, index=True, nullable=False)
    filter_config = Column(JSON, nullable=True)  # Data filtering configuration
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<StreamingSubscription(id={self.id}, type='{self.subscription_type}', user_id={self.user_id})>"

# Create all database indexes for performance optimization
Index('idx_users_email_active', User.email, User.is_active)
Index('idx_users_tier_active', User.tier, User.is_active)
Index('idx_agent_instances_status', AgentInstance.status)
Index('idx_agent_instances_owner', AgentInstance.owner_id)
Index('idx_agent_queries_timestamp', AgentQuery.created_at)
Index('idx_workflow_instances_status', WorkflowInstance.status)
Index('idx_workflow_instances_owner', WorkflowInstance.owner_id)
Index('idx_dashboard_configs_owner', DashboardConfig.owner_id)
Index('idx_dashboard_configs_default', DashboardConfig.is_default, DashboardConfig.owner_id)