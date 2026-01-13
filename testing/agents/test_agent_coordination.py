"""
Agent Coordination and Decision-Making Workflow Tests
Tests multi-agent coordination, decision-making processes, and communication patterns
"""
import pytest
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from unittest.mock import Mock, AsyncMock, patch
import uuid

from config import TestConfig
from utils.helpers import TestHelpers

class AgentCoordinationTests:
    """Tests for multi-agent coordination and workflow"""
    
    def __init__(self):
        self.config = TestConfig()
        self.helpers = TestHelpers()
        self.agent_types = [
            "data_collector", "feature_engineer", "prediction_agent",
            "risk_manager", "execution_agent", "monitoring_agent"
        ]
        
    @pytest.mark.agent
    @pytest.mark.e2e
    async def test_agent_coordination_workflow(self, mock_letta_client, redis_client):
        """Test complete agent coordination workflow"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting agent coordination workflow test")
        
        # Create agent instances
        agents = await self._create_agent_instances()
        
        # Define workflow stages
        workflow_stages = [
            "data_collection",
            "feature_engineering", 
            "prediction_generation",
            "risk_assessment",
            "execution_planning",
            "monitoring"
        ]
        
        workflow_start_time = time.time()
        
        # Execute workflow stages
        workflow_state = {}
        for stage in workflow_stages:
            stage_start = time.time()
            logger.info(f"Executing workflow stage: {stage}")
            
            # Execute stage with agent coordination
            stage_result = await self._execute_workflow_stage(
                agents, stage, workflow_state
            )
            
            # Validate stage completion
            assert stage_result is not None, f"Stage {stage} failed"
            workflow_state[stage] = stage_result
            
            # Store state in Redis for next stage
            await redis_client.set(
                f"workflow:stage:{stage}",
                json.dumps(stage_result),
                ex=300
            )
            
            stage_duration = time.time() - stage_start
            logger.info(f"Stage {stage} completed in {stage_duration:.2f}s")
        
        total_duration = time.time() - workflow_start_time
        
        # Validate overall workflow
        assert total_duration < 60, f"Workflow took too long: {total_duration}s"
        assert len(workflow_state) == len(workflow_stages), \
            f"Incomplete workflow: {len(workflow_state)}/{len(workflow_stages)} stages"
        
        # Validate data flow between stages
        await self._validate_workflow_data_flow(workflow_state)
        
        logger.info(f"Agent coordination workflow completed successfully in {total_duration:.2f}s")
        
    @pytest.mark.agent
    async def test_parallel_agent_execution(self, mock_letta_client, redis_client):
        """Test parallel execution of independent agent tasks"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting parallel agent execution test")
        
        # Create agent instances
        agents = await self._create_agent_instances()
        
        # Define parallel task groups
        parallel_tasks = {
            "data_parallel": ["collect_market_data", "fetch_news_sentiment", "get_economic_indicators"],
            "processing_parallel": ["compute_technical_features", "analyze_market_regime", "evaluate_risk_metrics"],
            "decision_parallel": ["generate_predictions", "assess_opportunities", "plan_execution"]
        }
        
        execution_start_time = time.time()
        
        # Execute task groups in parallel
        for group_name, tasks in parallel_tasks.items():
            logger.info(f"Executing parallel task group: {group_name}")
            
            # Run tasks in group in parallel
            group_tasks = []
            for task_name in tasks:
                task = self._execute_agent_task(agents, task_name)
                group_tasks.append(task)
            
            group_results = await asyncio.gather(*group_tasks, return_exceptions=True)
            
            # Validate group results
            successful_results = [r for r in group_results if not isinstance(r, Exception)]
            assert len(successful_results) >= len(tasks) * 0.9, \
                f"Too many task failures in {group_name}"
            
            # Store results
            await redis_client.set(
                f"agent_tasks:{group_name}",
                json.dumps({
                    "tasks": tasks,
                    "results": [str(r) for r in group_results],
                    "timestamp": datetime.utcnow().isoformat()
                }),
                ex=600
            )
        
        total_duration = time.time() - execution_start_time
        logger.info(f"Parallel agent execution completed in {total_duration:.2f}s")
        
    @pytest.mark.agent
    @pytest.mark.slow
    async def test_agent_consensus_decision_making(self, mock_letta_client, redis_client):
        """Test consensus-based decision making across agents"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting agent consensus decision-making test")
        
        # Create specialized agents for different aspects
        agents = await self._create_specialized_agents()
        
        # Define decision scenario
        decision_scenario = {
            "symbol": "AAPL",
            "investment_amount": 100000,
            "current_price": 150.25,
            "market_conditions": "volatile",
            "risk_tolerance": "medium"
        }
        
        # Collect decisions from each agent
        agent_decisions = {}
        decision_tasks = []
        
        for agent_name, agent in agents.items():
            task = self._collect_agent_decision(agent, agent_name, decision_scenario)
            decision_tasks.append((agent_name, task))
        
        # Execute decisions in parallel
        for agent_name, task in decision_tasks:
            try:
                decision = await task
                agent_decisions[agent_name] = decision
            except Exception as e:
                logger.error(f"Agent {agent_name} decision failed: {e}")
                agent_decisions[agent_name] = {"status": "failed", "error": str(e)}
        
        # Aggregate decisions using consensus algorithm
        consensus_result = await self._aggregate_agent_consensus(agent_decisions)
        
        # Validate consensus process
        assert consensus_result is not None, "Consensus aggregation failed"
        assert len(consensus_result.get("supporting_agents", [])) >= 2, \
            "Insufficient agent support for consensus"
        
        # Store consensus decision
        await redis_client.set(
            f"consensus_decision:{decision_scenario['symbol']}",
            json.dumps({
                "scenario": decision_scenario,
                "agent_decisions": agent_decisions,
                "consensus": consensus_result,
                "timestamp": datetime.utcnow().isoformat()
            }),
            ex=1800
        )
        
        logger.info(f"Agent consensus decision: {consensus_result.get('final_decision')}")
        
    @pytest.mark.agent
    async def test_agent_communication_patterns(self, mock_letta_client, redis_client):
        """Test various communication patterns between agents"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting agent communication patterns test")
        
        agents = await self._create_agent_instances()
        communication_scenarios = [
            "request_response",
            "broadcast",
            "pub_sub",
            "routing",
            "load_balancing"
        ]
        
        for scenario in communication_scenarios:
            logger.info(f"Testing communication pattern: {scenario}")
            
            scenario_result = await self._test_communication_pattern(
                agents, scenario
            )
            
            assert scenario_result is not None, \
                f"Communication pattern {scenario} failed"
            
            # Store communication test results
            await redis_client.set(
                f"communication_test:{scenario}",
                json.dumps(scenario_result),
                ex=600
            )
        
        logger.info("All communication patterns tested successfully")
        
    @pytest.mark.agent
    @pytest.mark.performance
    async def test_agent_load_balancing(self, mock_letta_client, redis_client):
        """Test agent load balancing under high load"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting agent load balancing test")
        
        # Create multiple instances of same agent type
        worker_agents = await self._create_worker_agents("execution_agent", 5)
        
        # Generate high load of tasks
        num_tasks = 100
        tasks = []
        for i in range(num_tasks):
            task = {
                "id": str(uuid.uuid4()),
                "symbol": f"SYM{i % 10}",
                "priority": i % 3,  # 0, 1, 2 priority levels
                "complexity": (i % 5) + 1  # 1-5 complexity levels
            }
            tasks.append(task)
        
        # Distribute tasks using load balancing
        distribution_start = time.time()
        load_balancer = await self._create_load_balancer(worker_agents)
        
        task_assignments = await load_balancer.distribute_tasks(tasks)
        
        distribution_duration = time.time() - distribution_start
        
        # Validate load balancing
        assert len(task_assignments) == num_tasks, "Not all tasks assigned"
        
        # Check load distribution
        load_per_agent = {}
        for task_id, agent_id in task_assignments.items():
            load_per_agent[agent_id] = load_per_agent.get(agent_id, 0) + 1
        
        # Ensure load is reasonably balanced (max 20% variance)
        load_values = list(load_per_agent.values())
        if load_values:
            avg_load = sum(load_values) / len(load_values)
            max_variance = max(load_values) - min(load_values)
            max_allowed_variance = avg_load * 0.2
            
            assert max_variance <= max_allowed_variance, \
                f"Load imbalance too high: {max_variance} vs {max_allowed_variance}"
        
        # Store load balancing results
        await redis_client.set(
            "load_balancing_test",
            json.dumps({
                "total_tasks": num_tasks,
                "task_assignments": task_assignments,
                "load_per_agent": load_per_agent,
                "distribution_duration": distribution_duration,
                "timestamp": datetime.utcnow().isoformat()
            }),
            ex=600
        )
        
        logger.info(f"Load balancing completed: {distribution_duration:.2f}s")
        
    @pytest.mark.agent
    async def test_agent_failure_recovery(self, mock_letta_client, redis_client):
        """Test agent failure detection and recovery"""
        logger = self.helpers.get_logger()
        
        logger.info("Starting agent failure recovery test")
        
        # Create agents with health monitoring
        agents = await self._create_agent_instances()
        agent_health_monitor = await self._create_health_monitor(agents)
        
        # Define failure scenarios
        failure_scenarios = [
            ("agent_timeout", self._simulate_agent_timeout),
            ("agent_crash", self._simulate_agent_crash),
            ("network_partition", self._simulate_network_partition),
            ("resource_exhaustion", self._simulate_resource_exhaustion)
        ]
        
        for scenario_name, simulate_failure in failure_scenarios:
            logger.info(f"Testing recovery from: {scenario_name}")
            
            # Start health monitoring
            health_monitor_task = asyncio.create_task(
                agent_health_monitor.monitor_agents()
            )
            
            # Simulate failure
            await simulate_failure(agents)
            
            # Allow time for failure detection
            await asyncio.sleep(2)
            
            # Check health status
            health_status = await agent_health_monitor.get_health_status()
            failed_agents = [aid for aid, status in health_status.items() 
                           if status["status"] != "healthy"]
            
            assert len(failed_agents) > 0, f"No agents failed in {scenario_name}"
            
            # Trigger recovery
            recovery_start = time.time()
            await agent_health_monitor.recover_failed_agents(failed_agents)
            
            # Verify recovery
            await asyncio.sleep(5)  # Wait for recovery
            
            recovery_status = await agent_health_monitor.get_health_status()
            recovered_agents = [aid for aid, status in recovery_status.items() 
                              if status["status"] == "healthy"]
            
            assert len(recovered_agents) >= len(failed_agents), \
                f"Insufficient recovery in {scenario_name}"
            
            recovery_duration = time.time() - recovery_start
            
            # Store recovery metrics
            await redis_client.set(
                f"recovery_test:{scenario_name}",
                json.dumps({
                    "failed_agents": failed_agents,
                    "recovered_agents": recovered_agents,
                    "recovery_duration": recovery_duration,
                    "timestamp": datetime.utcnow().isoformat()
                }),
                ex=600
            )
            
            # Cancel monitoring task
            health_monitor_task.cancel()
            try:
                await health_monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Agent failure recovery test completed")
        
    # Helper methods for agent coordination
    async def _create_agent_instances(self):
        """Create instances of all agent types"""
        agents = {}
        
        for agent_type in self.agent_types:
            agent = Mock()
            agent.type = agent_type
            agent.id = f"{agent_type}-{uuid.uuid4().hex[:8]}"
            agent.status = "active"
            agent.capabilities = await self._get_agent_capabilities(agent_type)
            agent.execute_task = AsyncMock(return_value={"status": "success"})
            agent.get_status = AsyncMock(return_value={"status": "active", "load": 0})
            
            agents[agent_type] = agent
        
        return agents
    
    async def _get_agent_capabilities(self, agent_type):
        """Get capabilities for specific agent type"""
        capabilities_map = {
            "data_collector": ["market_data", "news", "economic_data"],
            "feature_engineer": ["technical_indicators", "sentiment_analysis"],
            "prediction_agent": ["price_prediction", "pattern_recognition"],
            "risk_manager": ["risk_assessment", "position_sizing"],
            "execution_agent": ["order_routing", "execution_optimization"],
            "monitoring_agent": ["performance_tracking", "alerting"]
        }
        return capabilities_map.get(agent_type, [])
    
    async def _create_specialized_agents(self):
        """Create specialized agents for consensus decision making"""
        agents = {}
        
        # Create agents with different specializations
        specializations = [
            ("technical_analyst", "Technical Analysis Agent"),
            ("fundamental_analyst", "Fundamental Analysis Agent"),
            ("sentiment_analyst", "Sentiment Analysis Agent"),
            ("quantitative_analyst", "Quantitative Analysis Agent"),
            ("risk_analyst", "Risk Analysis Agent")
        ]
        
        for agent_id, agent_name in specializations:
            agent = Mock()
            agent.id = agent_id
            agent.name = agent_name
            agent.specialization = agent_id
            agent.make_decision = AsyncMock(return_value=self._generate_agent_decision(agent_id))
            
            agents[agent_id] = agent
        
        return agents
    
    def _generate_agent_decision(self, agent_type):
        """Generate decision based on agent type"""
        import random
        
        decisions = {
            "technical_analyst": {
                "action": random.choice(["BUY", "SELL", "HOLD"]),
                "confidence": random.uniform(0.6, 0.95),
                "reasoning": "Technical indicators suggest bullish momentum"
            },
            "fundamental_analyst": {
                "action": random.choice(["BUY", "SELL", "HOLD"]),
                "confidence": random.uniform(0.7, 0.90),
                "reasoning": "Strong fundamentals support price appreciation"
            },
            "sentiment_analyst": {
                "action": random.choice(["BUY", "SELL", "HOLD"]),
                "confidence": random.uniform(0.5, 0.85),
                "reasoning": "Positive sentiment trends in social media"
            },
            "quantitative_analyst": {
                "action": random.choice(["BUY", "SELL", "HOLD"]),
                "confidence": random.uniform(0.65, 0.92),
                "reasoning": "Statistical models show favorable probability"
            },
            "risk_analyst": {
                "action": random.choice(["BUY", "SELL", "HOLD"]),
                "confidence": random.uniform(0.6, 0.88),
                "reasoning": "Risk metrics within acceptable parameters"
            }
        }
        
        return decisions.get(agent_type, {"action": "HOLD", "confidence": 0.5})
    
    async def _execute_workflow_stage(self, agents, stage, workflow_state):
        """Execute a specific workflow stage"""
        stage_executor_map = {
            "data_collection": self._execute_data_collection_stage,
            "feature_engineering": self._execute_feature_engineering_stage,
            "prediction_generation": self._execute_prediction_stage,
            "risk_assessment": self._execute_risk_assessment_stage,
            "execution_planning": self._execute_execution_planning_stage,
            "monitoring": self._execute_monitoring_stage
        }
        
        executor = stage_executor_map.get(stage)
        if executor:
            return await executor(agents, workflow_state)
        return None
    
    async def _execute_data_collection_stage(self, agents, workflow_state):
        """Execute data collection stage"""
        data_collector = agents.get("data_collector")
        if not data_collector:
            return None
        
        # Collect market data
        market_data = await data_collector.execute_task({
            "task": "collect_market_data",
            "symbols": ["AAPL", "GOOGL", "MSFT"],
            "timeframe": "1d"
        })
        
        # Collect news data
        news_data = await data_collector.execute_task({
            "task": "collect_news_data",
            "symbols": ["AAPL", "GOOGL", "MSFT"]
        })
        
        return {
            "market_data": market_data,
            "news_data": news_data,
            "collection_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_feature_engineering_stage(self, agents, workflow_state):
        """Execute feature engineering stage"""
        feature_engineer = agents.get("feature_engineer")
        if not feature_engineer:
            return None
        
        market_data = workflow_state.get("data_collection", {}).get("market_data")
        if not market_data:
            return None
        
        features = await feature_engineer.execute_task({
            "task": "compute_features",
            "data": market_data,
            "indicators": ["sma", "rsi", "macd", "bollinger"]
        })
        
        return {
            "features": features,
            "feature_count": len(features) if features else 0
        }
    
    async def _execute_prediction_stage(self, agents, workflow_state):
        """Execute prediction generation stage"""
        prediction_agent = agents.get("prediction_agent")
        if not prediction_agent:
            return None
        
        features = workflow_state.get("feature_engineering", {}).get("features")
        if not features:
            return None
        
        predictions = await prediction_agent.execute_task({
            "task": "generate_predictions",
            "features": features,
            "model": "ensemble_v2"
        })
        
        return {
            "predictions": predictions,
            "prediction_confidence": predictions.get("confidence", 0) if predictions else 0
        }
    
    async def _execute_risk_assessment_stage(self, agents, workflow_state):
        """Execute risk assessment stage"""
        risk_manager = agents.get("risk_manager")
        if not risk_manager:
            return None
        
        predictions = workflow_state.get("prediction_generation", {}).get("predictions")
        if not predictions:
            return None
        
        risk_assessment = await risk_manager.execute_task({
            "task": "assess_risk",
            "predictions": predictions,
            "portfolio_value": 1000000,
            "max_drawdown": 0.15
        })
        
        return {
            "risk_assessment": risk_assessment,
            "risk_level": risk_assessment.get("risk_level", "medium") if risk_assessment else "unknown"
        }
    
    async def _execute_execution_planning_stage(self, agents, workflow_state):
        """Execute execution planning stage"""
        execution_agent = agents.get("execution_agent")
        if not execution_agent:
            return None
        
        risk_assessment = workflow_state.get("risk_assessment", {}).get("risk_assessment")
        if not risk_assessment:
            return None
        
        execution_plan = await execution_agent.execute_task({
            "task": "plan_execution",
            "risk_assessment": risk_assessment,
            "market_conditions": "normal"
        })
        
        return {
            "execution_plan": execution_plan,
            "planned_actions": execution_plan.get("actions", []) if execution_plan else []
        }
    
    async def _execute_monitoring_stage(self, agents, workflow_state):
        """Execute monitoring stage"""
        monitoring_agent = agents.get("monitoring_agent")
        if not monitoring_agent:
            return None
        
        # Monitor the entire workflow
        monitoring_result = await monitoring_agent.execute_task({
            "task": "monitor_workflow",
            "workflow_state": workflow_state,
            "metrics": ["throughput", "latency", "success_rate"]
        })
        
        return {
            "monitoring": monitoring_result,
            "workflow_health": monitoring_result.get("health_status", "unknown") if monitoring_result else "unknown"
        }
    
    async def _collect_agent_decision(self, agent, agent_name, decision_scenario):
        """Collect decision from specific agent"""
        decision = await agent.make_decision(decision_scenario)
        return {
            "agent_name": agent_name,
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _aggregate_agent_consensus(self, agent_decisions):
        """Aggregate decisions using consensus algorithm"""
        # Count decisions by action
        action_counts = {}
        total_confidence = 0
        decision_details = []
        
        for agent_name, decision_data in agent_decisions.items():
            if isinstance(decision_data, dict) and "decision" in decision_data:
                decision = decision_data["decision"]
                action = decision.get("action", "HOLD")
                confidence = decision.get("confidence", 0.5)
                
                action_counts[action] = action_counts.get(action, 0) + 1
                total_confidence += confidence
                decision_details.append({
                    "agent": agent_name,
                    "action": action,
                    "confidence": confidence,
                    "reasoning": decision.get("reasoning", "")
                })
        
        # Determine consensus action
        if action_counts:
            consensus_action = max(action_counts.items(), key=lambda x: x[1])[0]
            consensus_strength = max(action_counts.values()) / len(agent_decisions)
            avg_confidence = total_confidence / len(agent_decisions)
            
            # Identify supporting agents
            supporting_agents = [
                detail["agent"] for detail in decision_details 
                if detail["action"] == consensus_action
            ]
            
            return {
                "final_decision": consensus_action,
                "consensus_strength": consensus_strength,
                "average_confidence": avg_confidence,
                "supporting_agents": supporting_agents,
                "decision_details": decision_details,
                "aggregation_method": "majority_vote_with_confidence_weighting"
            }
        
        return None
    
    async def _test_communication_pattern(self, agents, pattern):
        """Test specific communication pattern"""
        pattern_handlers = {
            "request_response": self._test_request_response,
            "broadcast": self._test_broadcast,
            "pub_sub": self._test_pubsub,
            "routing": self._test_routing,
            "load_balancing": self._test_communication_load_balancing
        }
        
        handler = pattern_handlers.get(pattern)
        if handler:
            return await handler(agents)
        return None
    
    async def _test_request_response(self, agents):
        """Test request-response communication"""
        # Simulate request-response between data_collector and feature_engineer
        data_collector = agents.get("data_collector")
        feature_engineer = agents.get("feature_engineer")
        
        if not data_collector or not feature_engineer:
            return None
        
        # Send request
        request = {"task": "compute_features", "data": {"sample": "data"}}
        
        # Simulate response
        response = await feature_engineer.execute_task(request)
        
        return {
            "pattern": "request_response",
            "request": request,
            "response": response,
            "success": response is not None
        }
    
    async def _test_broadcast(self, agents):
        """Test broadcast communication"""
        # Simulate broadcast from monitoring agent to all other agents
        monitoring_agent = agents.get("monitoring_agent")
        
        if not monitoring_agent:
            return None
        
        broadcast_message = {
            "type": "market_alert",
            "message": "High volatility detected",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Simulate broadcast to all agents
        broadcast_results = []
        for agent_name, agent in agents.items():
            if agent_name != "monitoring_agent":
                # Simulate receiving broadcast
                result = {"agent": agent_name, "received": True, "message": broadcast_message}
                broadcast_results.append(result)
        
        return {
            "pattern": "broadcast",
            "message": broadcast_message,
            "recipients": len(broadcast_results),
            "results": broadcast_results
        }
    
    async def _test_pubsub(self, agents):
        """Test publish-subscribe communication"""
        # Simulate pub-sub for trade signals
        publisher = agents.get("prediction_agent")
        subscribers = [agents.get("execution_agent"), agents.get("risk_manager")]
        
        if not publisher or not subscribers:
            return None
        
        # Publish trade signal
        trade_signal = {
            "type": "trade_signal",
            "symbol": "AAPL",
            "action": "BUY",
            "confidence": 0.85
        }
        
        # Simulate subscription handling
        subscription_results = []
        for subscriber in subscribers:
            if subscriber:
                result = {
                    "subscriber": subscriber.type,
                    "received_signal": trade_signal,
                    "processed": True
                }
                subscription_results.append(result)
        
        return {
            "pattern": "pub_sub",
            "signal": trade_signal,
            "subscribers": len(subscription_results),
            "results": subscription_results
        }
    
    async def _test_routing(self, agents):
        """Test message routing through coordinator"""
        coordinator = agents.get("monitoring_agent")  # Use monitoring as coordinator
        
        if not coordinator:
            return None
        
        # Simulate routing request to appropriate agent
        routing_request = {
            "task": "execute_trade",
            "symbol": "AAPL",
            "amount": 1000
        }
        
        # Determine optimal route
        target_agent = agents.get("execution_agent")
        
        # Simulate routing
        routing_result = {
            "request": routing_request,
            "routed_to": target_agent.type if target_agent else None,
            "routing_success": target_agent is not None
        }
        
        return {
            "pattern": "routing",
            "routing": routing_result
        }
    
    async def _test_communication_load_balancing(self, agents):
        """Test load balancing in communication"""
        # Test distributing messages across multiple execution agents
        execution_agents = [agent for name, agent in agents.items() 
                          if name == "execution_agent"]
        
        if not execution_agents:
            return None
        
        # Create load balancing request
        load_balancing_request = {
            "task": "execute_multiple_trades",
            "trades": [
                {"symbol": "AAPL", "amount": 1000},
                {"symbol": "GOOGL", "amount": 2000},
                {"symbol": "MSFT", "amount": 1500}
            ]
        }
        
        # Distribute trades across agents
        trade_assignments = {}
        for i, trade in enumerate(load_balancing_request["trades"]):
            agent_index = i % len(execution_agents)
            assigned_agent = execution_agents[agent_index]
            trade_assignments[f"trade_{i}"] = assigned_agent.type
        
        return {
            "pattern": "load_balancing",
            "request": load_balancing_request,
            "agents": len(execution_agents),
            "assignments": trade_assignments,
            "balance_score": len(set(trade_assignments.values())) / len(execution_agents)
        }
    
    async def _create_load_balancer(self, worker_agents):
        """Create a load balancer for agent task distribution"""
        class LoadBalancer:
            def __init__(self, agents):
                self.agents = agents
                self.current_loads = {agent.id: 0 for agent in agents}
            
            async def distribute_tasks(self, tasks):
                """Distribute tasks across agents using round-robin with load consideration"""
                assignments = {}
                
                for task in tasks:
                    # Find agent with lowest load
                    min_load_agent = min(self.agents, key=lambda a: self.current_loads[a.id])
                    
                    # Assign task
                    assignments[task["id"]] = min_load_agent.id
                    self.current_loads[min_load_agent.id] += task.get("complexity", 1)
                
                return assignments
            
            async def get_load_status(self):
                """Get current load status of all agents"""
                return {
                    agent.id: {
                        "current_load": self.current_loads[agent.id],
                        "capacity": 10,  # Simplified capacity
                        "utilization": self.current_loads[agent.id] / 10
                    }
                    for agent in self.agents
                }
        
        return LoadBalancer(worker_agents)
    
    async def _create_worker_agents(self, agent_type, count):
        """Create multiple worker instances of same agent type"""
        workers = []
        for i in range(count):
            worker = Mock()
            worker.type = agent_type
            worker.id = f"{agent_type}-worker-{i}"
            worker.status = "active"
            worker.current_tasks = []
            worker.execute_task = AsyncMock(return_value={"status": "completed"})
            
            workers.append(worker)
        
        return workers
    
    async def _create_health_monitor(self, agents):
        """Create health monitoring system for agents"""
        class HealthMonitor:
            def __init__(self, agents):
                self.agents = agents
                self.health_status = {aid: {"status": "healthy"} for aid in agents.keys()}
                self.monitoring = False
            
            async def monitor_agents(self):
                """Monitor agent health continuously"""
                self.monitoring = True
                
                while self.monitoring:
                    for agent_id, agent in self.agents.items():
                        try:
                            status = await agent.get_status()
                            self.health_status[agent_id] = status
                        except Exception as e:
                            self.health_status[agent_id] = {
                                "status": "failed",
                                "error": str(e)
                            }
                    
                    await asyncio.sleep(1)  # Monitor every second
            
            async def get_health_status(self):
                """Get current health status of all agents"""
                return self.health_status
            
            async def recover_failed_agents(self, failed_agent_ids):
                """Attempt to recover failed agents"""
                for agent_id in failed_agent_ids:
                    if agent_id in self.agents:
                        agent = self.agents[agent_id]
                        try:
                            # Attempt recovery
                            agent.status = "recovering"
                            await asyncio.sleep(1)  # Simulate recovery time
                            agent.status = "active"
                            self.health_status[agent_id] = {"status": "healthy"}
                        except Exception:
                            self.health_status[agent_id] = {"status": "failed"}
            
            def stop_monitoring(self):
                """Stop health monitoring"""
                self.monitoring = False
        
        return HealthMonitor(agents)
    
    # Failure simulation methods
    async def _simulate_agent_timeout(self, agents):
        """Simulate agent timeout failure"""
        # Make one agent timeout
        timeout_agent = next(iter(agents.values()))
        timeout_agent.execute_task = AsyncMock(side_effect=asyncio.TimeoutError("Agent timeout"))
    
    async def _simulate_agent_crash(self, agents):
        """Simulate agent crash failure"""
        # Make one agent crash
        crash_agent = next(iter(agents.values()))
        crash_agent.execute_task = AsyncMock(side_effect=Exception("Agent crashed"))
    
    async def _simulate_network_partition(self, agents):
        """Simulate network partition"""
        # Disable network communication for all agents
        for agent in agents.values():
            original_method = agent.execute_task
            async def partition_wrapper(*args, **kwargs):
                raise Exception("Network partition - cannot communicate")
            agent.execute_task = partition_wrapper
    
    async def _simulate_resource_exhaustion(self, agents):
        """Simulate resource exhaustion"""
        # Make agents appear overloaded
        for agent in agents.values():
            agent.get_status = AsyncMock(return_value={
                "status": "overloaded",
                "current_load": 15,
                "capacity": 10,
                "memory_usage": 95
            })
    
    async def _validate_workflow_data_flow(self, workflow_state):
        """Validate data flows correctly between workflow stages"""
        # Check that each stage received data from previous stage
        stages = list(workflow_state.keys())
        
        for i in range(1, len(stages)):
            current_stage = stages[i]
            previous_stage = stages[i - 1]
            
            current_data = workflow_state[current_stage]
            previous_data = workflow_state[previous_stage]
            
            # Basic validation that data exists and is meaningful
            assert current_data is not None, f"No data in stage {current_stage}"
            assert previous_data is not None, f"No data in stage {previous_stage}"
            
            # Stage-specific validations
            if current_stage == "feature_engineering":
                assert "features" in current_data, "Features not computed"
                assert current_data.get("feature_count", 0) > 0, "No features generated"
            
            elif current_stage == "prediction_generation":
                assert "predictions" in current_data, "Predictions not generated"
                assert current_data.get("prediction_confidence", 0) > 0, "No prediction confidence"
            
            elif current_stage == "risk_assessment":
                assert "risk_assessment" in current_data, "Risk assessment missing"
            
            elif current_stage == "execution_planning":
                assert "execution_plan" in current_data, "Execution plan missing"
            
            elif current_stage == "monitoring":
                assert "monitoring" in current_data, "Monitoring data missing"
    
    async def _execute_agent_task(self, agents, task_name):
        """Execute specific agent task"""
        task_map = {
            "collect_market_data": self._execute_market_data_collection,
            "fetch_news_sentiment": self._execute_news_sentiment,
            "get_economic_indicators": self._execute_economic_indicators,
            "compute_technical_features": self._execute_technical_features,
            "analyze_market_regime": self._execute_market_regime,
            "evaluate_risk_metrics": self._execute_risk_metrics,
            "generate_predictions": self._execute_predictions,
            "assess_opportunities": self._execute_opportunities,
            "plan_execution": self._execute_execution_planning
        }
        
        executor = task_map.get(task_name)
        if executor:
            return await executor(agents)
        return {"task": task_name, "status": "not_implemented"}
    
    # Individual task executors
    async def _execute_market_data_collection(self, agents):
        """Execute market data collection task"""
        data_collector = agents.get("data_collector")
        if data_collector:
            return await data_collector.execute_task({"task": "collect_market_data"})
        return None
    
    async def _execute_news_sentiment(self, agents):
        """Execute news sentiment analysis task"""
        data_collector = agents.get("data_collector")
        if data_collector:
            return await data_collector.execute_task({"task": "analyze_news_sentiment"})
        return None
    
    async def _execute_economic_indicators(self, agents):
        """Execute economic indicators task"""
        data_collector = agents.get("data_collector")
        if data_collector:
            return await data_collector.execute_task({"task": "get_economic_indicators"})
        return None
    
    async def _execute_technical_features(self, agents):
        """Execute technical features task"""
        feature_engineer = agents.get("feature_engineer")
        if feature_engineer:
            return await feature_engineer.execute_task({"task": "compute_technical_features"})
        return None
    
    async def _execute_market_regime(self, agents):
        """Execute market regime analysis task"""
        feature_engineer = agents.get("feature_engineer")
        if feature_engineer:
            return await feature_engineer.execute_task({"task": "analyze_market_regime"})
        return None
    
    async def _execute_risk_metrics(self, agents):
        """Execute risk metrics evaluation task"""
        risk_manager = agents.get("risk_manager")
        if risk_manager:
            return await risk_manager.execute_task({"task": "evaluate_risk_metrics"})
        return None
    
    async def _execute_predictions(self, agents):
        """Execute prediction generation task"""
        prediction_agent = agents.get("prediction_agent")
        if prediction_agent:
            return await prediction_agent.execute_task({"task": "generate_predictions"})
        return None
    
    async def _execute_opportunities(self, agents):
        """Execute opportunity assessment task"""
        prediction_agent = agents.get("prediction_agent")
        if prediction_agent:
            return await prediction_agent.execute_task({"task": "assess_opportunities"})
        return None
    
    async def _execute_execution_planning(self, agents):
        """Execute execution planning task"""
        execution_agent = agents.get("execution_agent")
        if execution_agent:
            return await execution_agent.execute_task({"task": "plan_execution"})
        return None

# Pytest fixture for agent coordination tests
def pytest_agent_coordination():
    """Pytest fixture for agent coordination tests"""
    return AgentCoordinationTests()

if __name__ == "__main__":
    # Run tests directly
    pytest.main([
        __file__,
        "-v",
        "-m", "agent",
        "--tb=short"
    ])