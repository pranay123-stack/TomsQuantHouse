"""
Database models for LangGraph API
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base
import uuid
import enum

class WorkflowStatus(enum.Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class NodeStatus(enum.Enum):
    """Workflow node execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class Workflow(Base):
    """Workflow database model"""
    __tablename__ = "workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    workflow_type = Column(String(100), nullable=False)
    config = Column(JSON, default={})
    timeout_minutes = Column(Integer, default=60)
    priority = Column(Integer, default=0)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default=WorkflowStatus.PENDING.value, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    result = Column(JSON)
    execution_count = Column(Integer, default=0)

class WorkflowExecution(Base):
    """Workflow execution database model"""
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    status = Column(String(20), default=WorkflowStatus.PENDING.value, nullable=False)
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime)
    result = Column(JSON)
    error_message = Column(Text)

class State(Base):
    """Workflow state database model"""
    __tablename__ = "states"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False)
    node_name = Column(String(100), nullable=False)
    state_data = Column(JSON, default={})
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    status = Column(String(20), default=NodeStatus.PENDING.value, nullable=False)
    execution_time_ms = Column(Integer)

class MonitoringMetrics(Base):
    """System monitoring metrics database model"""
    __tablename__ = "monitoring_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_labels = Column(JSON, default={})
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)

class SystemAlert(Base):
    """System alerts database model"""
    __tablename__ = "system_alerts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)  # info, warning, error, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, default={})
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)

class AuditLog(Base):
    """Audit log database model"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, default={})
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)