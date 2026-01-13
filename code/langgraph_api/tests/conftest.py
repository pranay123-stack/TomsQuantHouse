"""
Pytest configuration and shared fixtures
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import os

# FastAPI and testing imports
from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest_asyncio

# Application imports
from app.main import app
from app.core.database import Base, engine, get_db
from app.core.config import settings
from app.models.database_models import User, Workflow, State, WorkflowExecution
from app.auth.auth_handler import create_access_token

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db():
    """Create test database and tables."""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def test_user(test_db):
    """Create a test user."""
    from app.models.user import User as UserModel
    
    # Create test user in database
    user = UserModel(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed_password",
        role="standard",
        is_active=True
    )
    
    # Note: In a real test, we'd need to add this to the database
    # For now, we'll use this as a mock
    return user


@pytest.fixture
def test_user_data():
    """Test user data for creating users."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
        "role": "standard"
    }


@pytest.fixture
def auth_headers():
    """Create authentication headers for test requests."""
    access_token = create_access_token({"sub": "test@example.com"})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client():
    """Create an async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch('app.core.database.redis_client') as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager."""
    with patch('app.api.websocket.manager.WebSocketManager') as mock:
        manager = AsyncMock()
        manager.connect = AsyncMock()
        manager.disconnect = AsyncMock()
        manager.broadcast_to_user = AsyncMock()
        manager.broadcast_workflow_update = AsyncMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow for unit testing",
        "workflow_type": "sequential",
        "config": {
            "nodes": [
                {"name": "start", "type": "entry"},
                {"name": "process", "type": "task"},
                {"name": "end", "type": "exit"}
            ],
            "edges": [
                {"from": "start", "to": "process"},
                {"from": "process", "to": "end"}
            ]
        },
        "timeout_minutes": 30,
        "priority": 1
    }


@pytest.fixture
def sample_state_data():
    """Sample state data for testing."""
    return {
        "workflow_id": "test-workflow-id",
        "node_name": "test_node",
        "state_data": {"key": "value", "count": 0},
        "metadata": {"step": 1, "retry_count": 0},
        "status": "pending"
    }


@pytest.fixture
def mock_workflow_service():
    """Mock workflow service."""
    with patch('app.api.v1.workflows.WorkflowService') as mock:
        service = AsyncMock()
        service.create_workflow = AsyncMock()
        service.get_workflow_by_id = AsyncMock()
        service.list_workflows = AsyncMock()
        service.update_workflow = AsyncMock()
        service.delete_workflow = AsyncMock()
        service.execute_workflow = AsyncMock()
        service.batch_execute = AsyncMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_state_service():
    """Mock state service."""
    with patch('app.api.v1.states.StateService') as mock:
        service = AsyncMock()
        service.create_state = AsyncMock()
        service.get_state_by_id = AsyncMock()
        service.list_states = AsyncMock()
        service.update_state = AsyncMock()
        service.delete_state = AsyncMock()
        service.get_workflow_states = AsyncMock()
        mock.return_value = service
        yield service


@pytest.fixture
def mock_auth_handler():
    """Mock auth handler."""
    with patch('app.auth.auth_handler.auth_handler') as mock:
        mock.create_access_token = Mock(return_value="test-jwt-token")
        mock.verify_token = Mock(return_value={"sub": "test@example.com"})
        mock.authenticate_user = AsyncMock()
        mock.get_current_user = AsyncMock()
        yield mock


# Test data generators
class TestDataGenerator:
    """Generate test data for various models."""
    
    @staticmethod
    def workflow(user_id="test-user-id", **overrides):
        """Generate a workflow with default values."""
        defaults = {
            "name": "Test Workflow",
            "description": "Test description",
            "workflow_type": "sequential",
            "config": {"nodes": [], "edges": []},
            "user_id": user_id,
            "status": "pending"
        }
        defaults.update(overrides)
        return defaults
    
    @staticmethod
    def state(workflow_id="test-workflow-id", **overrides):
        """Generate a state with default values."""
        defaults = {
            "workflow_id": workflow_id,
            "node_name": "test_node",
            "state_data": {},
            "status": "pending"
        }
        defaults.update(overrides)
        return defaults
    
    @staticmethod
    def user(**overrides):
        """Generate a user with default values."""
        defaults = {
            "email": "test@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "role": "standard",
            "is_active": True
        }
        defaults.update(overrides)
        return defaults


@pytest.fixture
def test_data():
    """Test data generator."""
    return TestDataGenerator