"""
Comprehensive tests for the Agent Communication System.
Tests all major components and integration scenarios.
"""

import asyncio
import pytest
import logging
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta

# Import system components
from ..communication_system import (
    AgentCommunicationSystem, AgentConfig, create_communication_system
)
from schemas.message_schemas import (
    MessageFactory, MessageType, Priority, DeliveryGuarantee
)
from message_router import MessageRouter, Route, RoutingStrategy
from agents.agent_discovery import AgentRegistry, AgentDiscoveryService
from message_persistence import MessagePersistor, StorageType
from event_architecture import EventBus, Event, EventType
from monitoring.analytics import create_monitoring_system
from security.encryption import create_security_system, SecurityLevel, TrustLevel

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAgentCommunicationSystem:
    """Test suite for the agent communication system"""
    
    @pytest.fixture
    async def system(self):
        """Create test system"""
        system = await create_communication_system("test_system")
        yield system
        await system.stop()
    
    @pytest.fixture
    def sample_agents(self) -> List[AgentConfig]:
        """Create sample agent configurations"""
        return [
            AgentConfig(
                agent_id="trading_agent_1",
                agent_type="trading",
                capabilities=["signal_generation", "risk_management"],
                endpoint="tcp://localhost:8001",
                region="us-east-1",
                tags=["crypto", "high_frequency"]
            ),
            AgentConfig(
                agent_id="analysis_agent_1",
                agent_type="analysis", 
                capabilities=["pattern_recognition", "prediction"],
                endpoint="tcp://localhost:8002",
                region="us-east-1",
                tags=["ml", "technical_analysis"]
            ),
            AgentConfig(
                agent_id="risk_agent_1",
                agent_type="risk",
                capabilities=["portfolio_analysis", "stress_testing"],
                endpoint="tcp://localhost:8003",
                region="us-east-1",
                tags=["risk", "compliance"]
            )
        ]
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, system):
        """Test system initialization"""
        assert system.state.value in ["running", "initializing"]
        assert system.message_router is not None
        assert system.agent_registry is not None
        assert system.event_bus is not None
        assert system.metric_collector is not None
        assert system.security_manager is not None
    
    @pytest.mark.asyncio
    async def test_agent_registration(self, system, sample_agents):
        """Test agent registration"""
        # Register agents
        for agent_config in sample_agents:
            success = await system.register_agent(agent_config)
            assert success, f"Failed to register agent {agent_config.agent_id}"
        
        # Verify agents are registered
        assert len(system.registered_agents) == len(sample_agents)
        
        # Test unregistration
        success = await system.unregister_agent("trading_agent_1")
        assert success
        assert "trading_agent_1" not in system.registered_agents
        assert len(system.registered_agents) == len(sample_agents) - 1
    
    @pytest.mark.asyncio
    async def test_message_sending(self, system, sample_agents):
        """Test message sending"""
        # Register agents
        for agent_config in sample_agents:
            await system.register_agent(agent_config)
        
        # Create test messages
        messages = [
            MessageFactory.create_trade_signal(
                sender_id="trading_agent_1",
                symbol="BTCUSDT",
                signal="BUY",
                price=45000.0,
                confidence=0.85
            ),
            MessageFactory.create_prediction(
                sender_id="analysis_agent_1",
                model="LSTM_v2",
                prediction="price_up",
                confidence=0.78
            ),
            MessageFactory.create_alert(
                sender_id="risk_agent_1",
                alert_type="WARNING",
                message="High volatility detected"
            )
        ]
        
        # Send messages
        for message in messages:
            success = await system.send_message(message)
            assert success, f"Failed to send message {message.metadata.message_id}"
    
    @pytest.mark.asyncio
    async def test_agent_discovery(self, system, sample_agents):
        """Test agent discovery functionality"""
        # Register agents
        for agent_config in sample_agents:
            await system.register_agent(agent_config)
        
        # Test discovery by agent type
        trading_agents = await system.discover_agents({
            'agent_type': 'trading'
        })
        assert len(trading_agents) == 1
        assert trading_agents[0].agent_id == "trading_agent_1"
        
        # Test discovery by capabilities
        ml_agents = await system.discover_agents({
            'capabilities': ['pattern_recognition']
        })
        assert len(ml_agents) == 1
        assert ml_agents[0].agent_id == "analysis_agent_1"
        
        # Test discovery by region
        region_agents = await system.discover_agents({
            'region': 'us-east-1'
        })
        assert len(region_agents) == 3
    
    @pytest.mark.asyncio
    async def test_coordination(self, system, sample_agents):
        """Test agent coordination"""
        # Register agents
        for agent_config in sample_agents:
            await system.register_agent(agent_config)
        
        # Start coordination
        task_id = await system.start_coordination(
            coordinator_id="trading_agent_1",
            task_type="portfolio_optimization",
            participants=["analysis_agent_1", "risk_agent_1"],
            parameters={
                "portfolio_value": 100000,
                "risk_tolerance": "medium",
                "symbols": ["BTCUSDT", "ETHUSDT"]
            }
        )
        
        assert task_id is not None
        assert len(task_id) > 0
        
        # Check coordination status
        coordination_stats = system.coordination_engine.get_coordination_stats()
        assert coordination_stats['tasks_started'] > 0
    
    @pytest.mark.asyncio
    async def test_message_routing(self, system, sample_agents):
        """Test message routing functionality"""
        # Register agents
        for agent_config in sample_agents:
            await system.register_agent(agent_config)
        
        # Create route for testing
        route = Route(
            route_id="test_route",
            source="trading_agent_1",
            destination="analysis_agent_1",
            priority=Priority.HIGH,
            delivery_guarantee=DeliveryGuarantee.AT_LEAST_ONCE
        )
        system.message_router.add_route(route)
        
        # Send message through specific route
        message = MessageFactory.create_trade_signal(
            sender_id="trading_agent_1",
            symbol="ETHUSDT",
            signal="SELL",
            price=3200.0
        )
        
        success = await system.send_message(message)
        assert success
        
        # Verify routing statistics
        router_stats = system.message_router.get_router_stats()
        assert router_stats['messages_routed'] > 0
    
    @pytest.mark.asyncio
    async def test_message_persistence(self, system):
        """Test message persistence"""
        # Create messages with different storage types
        messages = []
        for i in range(5):
            message = MessageFactory.create_prediction(
                sender_id="test_agent",
                model="test_model",
                prediction=f"prediction_{i}",
                confidence=0.7
            )
            messages.append(message)
        
        # Store messages
        for message in messages:
            record_id = system.message_persistor.store_message(
                message,
                storage_type=StorageType.PERSISTENT,
                ttl_seconds=300
            )
            assert record_id is not None
        
        # Retrieve messages
        retrieved_messages = system.message_persistor.retrieve_messages_by_criteria({
            'sender_id': 'test_agent'
        })
        
        assert len(retrieved_messages) == 5
        
        # Test message replay
        replay_session_id = system.message_persistor.start_replay_session(
            query={'sender_id': 'test_agent'},
            replay_mode="time_ordered"
        )
        
        assert replay_session_id is not None
    
    @pytest.mark.asyncio
    async def test_event_system(self, system, sample_agents):
        """Test event system functionality"""
        # Register agents to trigger events
        for agent_config in sample_agents:
            await system.register_agent(agent_config)
        
        # Wait for events to be processed
        await asyncio.sleep(0.1)
        
        # Get event history
        events = system.event_bus.get_event_history(limit=100)
        
        # Verify events were generated
        agent_events = [e for e in events if e.event_type in [EventType.AGENT_REGISTERED, EventType.AGENT_UNREGISTERED]]
        assert len(agent_events) >= 3  # At least one event per agent
        
        # Test manual event publishing
        test_event = Event(
            event_id="test_event",
            event_type=EventType.PERFORMANCE_METRIC,
            source="test_source",
            timestamp=datetime.now(),
            data={'metric': 'test_metric', 'value': 42}
        )
        
        await system.event_bus.publish_event(test_event)
    
    @pytest.mark.asyncio
    async def test_monitoring_system(self, system):
        """Test monitoring and analytics"""
        # Generate some test metrics
        system.metric_collector.increment_counter('test_counter', 5.0)
        system.metric_collector.set_gauge('test_gauge', 100.0)
        
        # Track some messages
        for i in range(10):
            message = MessageFactory.create_prediction(
                sender_id="test_agent",
                model="test_model",
                prediction=f"prediction_{i}",
                confidence=0.7
            )
            system.flow_analyzer.track_message(message, processing_time=0.1)
        
        # Analyze flow patterns
        flow_stats = system.flow_analyzer.analyze_flow_patterns(60)
        assert flow_stats['messages_total'] == 10
        
        # Detect anomalies
        anomalies = system.flow_analyzer.detect_anomalies()
        # Should not detect anomalies in normal test data
        
        # Test alert system
        active_alerts = system.alert_manager.get_active_alerts()
        assert isinstance(active_alerts, list)
        
        # Generate report
        report = system.monitoring_dashboard.generate_report(1)
        assert 'report_id' in report
        assert 'summary' in report
    
    @pytest.mark.asyncio
    async def test_security_system(self, system, sample_agents):
        """Test security and encryption"""
        # Register agents with different trust levels
        sample_agents[0].trust_level = TrustLevel.HIGH
        sample_agents[1].trust_level = TrustLevel.MEDIUM
        sample_agents[2].trust_level = TrustLevel.LOW
        
        for agent_config in sample_agents:
            await system.register_agent(agent_config)
        
        # Create sensitive message
        sensitive_message = MessageFactory.create_trade_signal(
            sender_id="trading_agent_1",
            symbol="BTCUSDT",
            signal="BUY",
            price=45000.0,
            confidence=0.95
        )
        
        # Send with high security
        success = await system.send_message(sensitive_message, secure=True)
        assert success
        
        # Test security policy enforcement
        policy_stats = system.security_manager.get_security_stats()
        assert policy_stats['policies_count'] > 0
        
        # Test trust level management
        trust_level = system.security_manager.get_trust_level("trading_agent_1")
        assert trust_level == TrustLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_system_status(self, system, sample_agents):
        """Test system status reporting"""
        # Register some agents
        for agent_config in sample_agents[:2]:
            await system.register_agent(agent_config)
        
        # Get system status
        status = await system.get_system_status()
        
        # Verify status structure
        assert status['system_id'] == 'test_system'
        assert status['state'] in ['running', 'initializing']
        assert 'statistics' in status
        assert 'components' in status
        assert 'registered_agents' in status
        assert status['registered_agents'] == 2
        
        # Check component statuses
        components = status['components']
        assert 'message_router' in components
        assert 'agent_registry' in components
        assert 'event_bus' in components
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, system):
        """Test system performance under load"""
        # Create multiple agents
        agents = []
        for i in range(10):
            agent_config = AgentConfig(
                agent_id=f"agent_{i}",
                agent_type="test",
                capabilities=["test_capability"],
                endpoint=f"tcp://localhost:80{i}",
                region="us-east-1"
            )
            agents.append(agent_config)
            await system.register_agent(agent_config)
        
        # Send multiple messages
        start_time = time.time()
        messages_sent = 0
        successes = 0
        
        for i in range(50):
            message = MessageFactory.create_prediction(
                sender_id=f"agent_{i % 10}",
                model="test_model",
                prediction=f"prediction_{i}",
                confidence=0.7
            )
            
            success = await system.send_message(message)
            messages_sent += 1
            if success:
                successes += 1
        
        end_time = time.time()
        
        # Verify performance
        assert messages_sent == 50
        assert successes >= 45  # Allow for some failures under load
        assert (end_time - start_time) < 10  # Should complete within 10 seconds
        
        # Check system statistics
        stats = await system.get_system_status()
        assert stats['statistics']['messages_processed'] >= 45


class TestMessageSchemas:
    """Test message schema functionality"""
    
    def test_message_factory(self):
        """Test message factory functions"""
        # Test trade signal creation
        trade_signal = MessageFactory.create_trade_signal(
            sender_id="test_agent",
            symbol="BTCUSDT",
            signal="BUY",
            price=45000.0
        )
        
        assert trade_signal.sender_id == "test_agent"
        assert trade_signal.payload['symbol'] == "BTCUSDT"
        assert trade_signal.payload['signal'] == "BUY"
        assert trade_signal.payload['price'] == 45000.0
        
        # Test prediction creation
        prediction = MessageFactory.create_prediction(
            sender_id="test_agent",
            model="LSTM_v2",
            prediction="price_up",
            confidence=0.85
        )
        
        assert prediction.sender_id == "test_agent"
        assert prediction.payload['model'] == "LSTM_v2"
        assert prediction.payload['confidence'] == 0.85
        
        # Test alert creation
        alert = MessageFactory.create_alert(
            sender_id="test_agent",
            alert_type="WARNING",
            message="High volatility detected"
        )
        
        assert alert.sender_id == "test_agent"
        assert alert.payload['alert_type'] == "WARNING"
        assert "volatility" in alert.payload['message']
    
    def test_message_serialization(self):
        """Test message serialization and deserialization"""
        original_message = MessageFactory.create_trade_signal(
            sender_id="test_agent",
            symbol="ETHUSDT",
            signal="SELL",
            price=3200.0,
            confidence=0.9
        )
        
        # Serialize to JSON
        json_str = original_message.to_json()
        assert len(json_str) > 0
        
        # Deserialize from JSON
        restored_message = BaseMessage.from_json(json_str)
        
        # Verify properties
        assert restored_message.sender_id == original_message.sender_id
        assert restored_message.payload['symbol'] == original_message.payload['symbol']
        assert restored_message.payload['signal'] == original_message.payload['signal']
        assert restored_message.payload['price'] == original_message.payload['price']


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_trading_workflow(self):
        """Test complete trading workflow scenario"""
        system = await create_communication_system("trading_workflow_test")
        
        try:
            # Register trading agents
            agents = [
                AgentConfig("signal_agent", "trading", ["signal_generation"], "tcp://localhost:8001"),
                AgentConfig("risk_agent", "risk", ["risk_management"], "tcp://localhost:8002"),
                AgentConfig("execution_agent", "execution", ["order_execution"], "tcp://localhost:8003")
            ]
            
            for agent in agents:
                await system.register_agent(agent)
            
            # Step 1: Signal generation
            signal_message = MessageFactory.create_trade_signal(
                sender_id="signal_agent",
                symbol="BTCUSDT",
                signal="BUY",
                price=45000.0,
                confidence=0.85
            )
            await system.send_message(signal_message)
            
            # Step 2: Risk assessment coordination
            risk_task_id = await system.start_coordination(
                coordinator_id="signal_agent",
                task_type="risk_assessment",
                participants=["risk_agent"],
                parameters={
                    "signal": signal_message.payload,
                    "portfolio_context": {"value": 100000, "positions": {}}
                }
            )
            
            # Step 3: Execution if approved
            await asyncio.sleep(1)  # Wait for coordination
            
            execution_message = MessageFactory.create_trade_signal(
                sender_id="risk_agent",
                symbol="BTCUSDT",
                signal="EXECUTE_BUY",
                price=45000.0,
                confidence=1.0,
                metadata={"risk_approved": True, "task_id": risk_task_id}
            )
            await system.send_message(execution_message)
            
            # Verify workflow completion
            status = await system.get_system_status()
            assert status['statistics']['coordination_tasks'] >= 1
            assert status['statistics']['messages_processed'] >= 3
            
        finally:
            await system.stop()
    
    @pytest.mark.asyncio
    async def test_multi_agent_coordination(self):
        """Test complex multi-agent coordination scenario"""
        system = await create_communication_system("coordination_test")
        
        try:
            # Register diverse agents
            agents = [
                AgentConfig("coordinator", "coordinator", ["coordination"], "tcp://localhost:8001"),
                AgentConfig("data_collector", "data", ["data_collection"], "tcp://localhost:8002"),
                AgentConfig("analyzer", "analysis", ["pattern_analysis"], "tcp://localhost:8003"),
                AgentConfig("validator", "validation", ["data_validation"], "tcp://localhost:8004"),
                AgentConfig("reporter", "reporting", ["report_generation"], "tcp://localhost:8005")
            ]
            
            for agent in agents:
                await system.register_agent(agent)
            
            # Start complex coordination workflow
            workflow_task_id = await system.start_coordination(
                coordinator_id="coordinator",
                task_type="market_analysis_workflow",
                participants=["data_collector", "analyzer", "validator", "reporter"],
                parameters={
                    "analysis_type": "comprehensive",
                    "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
                    "timeframe": "1h",
                    "depth": "deep"
                }
            )
            
            # Verify coordination started
            assert workflow_task_id is not None
            
            # Wait for coordination to complete
            await asyncio.sleep(2)
            
            # Check coordination statistics
            coordination_stats = system.coordination_engine.get_coordination_stats()
            assert coordination_stats['tasks_started'] >= 1
            
        finally:
            await system.stop()


if __name__ == "__main__":
    # Run specific test
    async def run_basic_test():
        """Run a basic integration test"""
        print("Starting Agent Communication System Test...")
        
        # Create system
        system = await create_communication_system("demo_system")
        
        try:
            # Register test agents
            agents = [
                AgentConfig(
                    agent_id="demo_trading_agent",
                    agent_type="trading",
                    capabilities=["signal_generation", "risk_management"],
                    endpoint="tcp://localhost:8001"
                ),
                AgentConfig(
                    agent_id="demo_analysis_agent",
                    agent_type="analysis",
                    capabilities=["pattern_recognition"],
                    endpoint="tcp://localhost:8002"
                )
            ]
            
            for agent in agents:
                success = await system.register_agent(agent)
                print(f"Registered {agent.agent_id}: {success}")
            
            # Send test messages
            messages = [
                MessageFactory.create_trade_signal(
                    sender_id="demo_trading_agent",
                    symbol="BTCUSDT",
                    signal="BUY",
                    price=45000.0
                ),
                MessageFactory.create_prediction(
                    sender_id="demo_analysis_agent",
                    model="DemoModel",
                    prediction="bullish",
                    confidence=0.8
                )
            ]
            
            for message in messages:
                success = await system.send_message(message)
                print(f"Sent message {message.metadata.message_id}: {success}")
            
            # Test discovery
            discovered_agents = await system.discover_agents({'agent_type': 'trading'})
            print(f"Discovered {len(discovered_agents)} trading agents")
            
            # Get system status
            status = await system.get_system_status()
            print(f"System status: {status['state']}")
            print(f"Messages processed: {status['statistics']['messages_processed']}")
            print(f"Agents registered: {status['registered_agents']}")
            
            # Keep running for a bit
            print("System running... (waiting 5 seconds)")
            await asyncio.sleep(5)
            
        finally:
            await system.stop()
            print("System stopped")
    
    # Run the test
    asyncio.run(run_basic_test())