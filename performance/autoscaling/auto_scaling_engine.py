#!/usr/bin/env python3
"""
Auto-Scaling Policies
Implements intelligent auto-scaling based on metrics and policies
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import yaml

class ScalingTrigger(Enum):
    """Auto-scaling trigger types"""
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    REQUEST_RATE = "request_rate"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    QUEUE_DEPTH = "queue_depth"
    CUSTOM_METRIC = "custom_metric"

class ScalingAction(Enum):
    """Auto-scaling actions"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    SCALE_OUT = "scale_out"  # Horizontal
    SCALE_IN = "scale_in"    # Horizontal
    SCALE_UP_RESOURCE = "scale_up_resource"  # Vertical
    SCALE_DOWN_RESOURCE = "scale_down_resource"  # Vertical

class PolicyStatus(Enum):
    """Auto-scaling policy status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class ScalingCondition:
    """Condition for auto-scaling trigger"""
    trigger: ScalingTrigger
    operator: str  # ">", "<", ">=", "<=", "==", "!="
    threshold: float
    duration_seconds: int = 60  # How long condition must persist
    evaluation_window: int = 300  # Time window for metric calculation

@dataclass
class ScalingActionConfig:
    """Configuration for scaling action"""
    action: ScalingAction
    target_value: float  # Scale to this value
    increment: Optional[float] = None  # Or increment by this amount
    max_value: Optional[float] = None
    min_value: Optional[float] = None

@dataclass
class MetricValue:
    """Single metric value with timestamp"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = None

@dataclass
class ScalingDecision:
    """Auto-scaling decision result"""
    policy_id: str
    decision_time: datetime
    condition_met: bool
    triggered_actions: List[ScalingActionConfig]
    current_metrics: Dict[str, float]
    previous_metrics: Dict[str, float]
    confidence: float
    reasoning: str

@dataclass
class AutoScalingPolicy:
    """Complete auto-scaling policy definition"""
    policy_id: str
    name: str
    description: str
    enabled: bool
    priority: int
    cooldown_period: int  # seconds
    conditions: List[ScalingCondition]
    actions: List[ScalingActionConfig]
    execution_count: int = 0
    success_count: int = 0
    last_execution: Optional[datetime] = None
    status: PolicyStatus = PolicyStatus.ACTIVE

class MetricsCollector:
    """Collect and aggregate metrics for auto-scaling"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Metric storage
        self.metrics_storage = defaultdict(lambda: deque(maxlen=1000))
        self.custom_metrics_collectors = {}
        
        # Collection intervals
        self.collection_interval = config.get('collection_interval', 30)  # seconds
        self.is_collecting = False
        
        # Initialize custom collectors if provided
        self._initialize_custom_collectors(config.get('custom_collectors', {}))
    
    def _initialize_custom_collectors(self, collectors_config: Dict):
        """Initialize custom metrics collectors"""
        for metric_name, collector_config in collectors_config.items():
            try:
                # This would initialize actual collectors
                # For demo, we'll simulate
                self.custom_metrics_collectors[metric_name] = {
                    'config': collector_config,
                    'last_collection': None,
                    'collection_function': lambda: self._simulate_metric_collection(metric_name)
                }
            except Exception as e:
                self.logger.error(f"Failed to initialize collector for {metric_name}: {e}")
    
    def _simulate_metric_collection(self, metric_name: str) -> float:
        """Simulate metric collection (in real implementation, this would be actual collection)"""
        import random
        
        # Simulate realistic metric values
        if 'cpu' in metric_name.lower():
            return random.uniform(20, 90)
        elif 'memory' in metric_name.lower():
            return random.uniform(30, 85)
        elif 'request' in metric_name.lower():
            return random.uniform(50, 500)
        elif 'response' in metric_name.lower():
            return random.uniform(100, 2000)
        elif 'error' in metric_name.lower():
            return random.uniform(0, 10)
        else:
            return random.uniform(0, 100)
    
    async def start_collection(self):
        """Start metrics collection"""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        
        async def collection_loop():
            while self.is_collecting:
                try:
                    await self._collect_all_metrics()
                    await asyncio.sleep(self.collection_interval)
                except Exception as e:
                    self.logger.error(f"Metrics collection error: {e}")
                    await asyncio.sleep(self.collection_interval)
        
        asyncio.create_task(collection_loop())
        self.logger.info("Metrics collection started")
    
    async def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        self.logger.info("Metrics collection stopped")
    
    async def _collect_all_metrics(self):
        """Collect all metrics from various sources"""
        current_time = datetime.now()
        
        # Collect system metrics
        system_metrics = await self._collect_system_metrics()
        for metric_name, value in system_metrics.items():
            self._store_metric(metric_name, current_time, value)
        
        # Collect custom metrics
        for metric_name, collector in self.custom_metrics_collectors.items():
            try:
                value = collector['collection_function']()
                self._store_metric(metric_name, current_time, value)
                collector['last_collection'] = current_time
            except Exception as e:
                self.logger.error(f"Custom metric collection failed for {metric_name}: {e}")
        
        # Collect application metrics (simulated)
        app_metrics = await self._collect_application_metrics()
        for metric_name, value in app_metrics.items():
            self._store_metric(metric_name, current_time, value)
    
    async def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system-level metrics"""
        try:
            import psutil
            
            return {
                'cpu_utilization': psutil.cpu_percent(interval=1),
                'memory_utilization': psutil.virtual_memory().percent,
                'disk_utilization': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                'network_connections': len(psutil.net_connections())
            }
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
            return {}
    
    async def _collect_application_metrics(self) -> Dict[str, float]:
        """Collect application-specific metrics"""
        # This would integrate with your application monitoring
        # For demo, return simulated values
        import random
        
        return {
            'request_rate': random.uniform(50, 300),
            'average_response_time': random.uniform(100, 800),
            'error_rate': random.uniform(0, 5),
            'active_connections': random.randint(10, 100),
            'queue_depth': random.randint(0, 50)
        }
    
    def _store_metric(self, metric_name: str, timestamp: datetime, value: float, tags: Dict[str, str] = None):
        """Store metric value"""
        metric = MetricValue(timestamp=timestamp, value=value, tags=tags or {})
        self.metrics_storage[metric_name].append(metric)
    
    def get_metric_values(self, metric_name: str, duration_seconds: int = 300) -> List[MetricValue]:
        """Get metric values for specified duration"""
        cutoff_time = datetime.now() - timedelta(seconds=duration_seconds)
        
        return [
            metric for metric in self.metrics_storage[metric_name]
            if metric.timestamp > cutoff_time
        ]
    
    def get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get most recent value for a metric"""
        if self.metrics_storage[metric_name]:
            return self.metrics_storage[metric_name][-1].value
        return None
    
    def calculate_metric_average(self, metric_name: str, duration_seconds: int = 300) -> Optional[float]:
        """Calculate average value of metric over duration"""
        values = self.get_metric_values(metric_name, duration_seconds)
        if not values:
            return None
        
        return sum(m.value for m in values) / len(values)
    
    def calculate_metric_percentile(self, metric_name: str, percentile: float, duration_seconds: int = 300) -> Optional[float]:
        """Calculate percentile value of metric over duration"""
        values = [m.value for m in self.get_metric_values(metric_name, duration_seconds)]
        if not values:
            return None
        
        values.sort()
        index = int((percentile / 100.0) * len(values))
        return values[min(index, len(values) - 1)]

class ScalingEngine:
    """Core auto-scaling engine"""
    
    def __init__(self, config: Dict, metrics_collector: MetricsCollector):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.metrics_collector = metrics_collector
        
        # Policy management
        self.policies = {}
        self.policy_history = defaultdict(list)
        
        # Scaling execution
        self.execution_handlers = {
            ScalingAction.SCALE_UP: self._handle_scale_up,
            ScalingAction.SCALE_DOWN: self._handle_scale_down,
            ScalingAction.SCALE_OUT: self._handle_scale_out,
            ScalingAction.SCALE_IN: self._handle_scale_in,
            ScalingAction.SCALE_UP_RESOURCE: self._handle_scale_up_resource,
            ScalingAction.SCALE_DOWN_RESOURCE: self._handle_scale_down_resource
        }
        
        # State tracking
        self.current_replicas = 1
        self.current_cpu_limit = 1000  # millicores
        self.current_memory_limit = 1024  # MB
        self.last_scale_time = datetime.now()
        
        # Load policies from configuration
        self._load_policies(config.get('scaling_policies', {}))
    
    def _load_policies(self, policies_config: Dict):
        """Load scaling policies from configuration"""
        for policy_id, policy_data in policies_config.items():
            try:
                # Parse conditions
                conditions = []
                for condition_data in policy_data.get('conditions', []):
                    condition = ScalingCondition(
                        trigger=ScalingTrigger(condition_data['trigger']),
                        operator=condition_data['operator'],
                        threshold=condition_data['threshold'],
                        duration_seconds=condition_data.get('duration_seconds', 60),
                        evaluation_window=condition_data.get('evaluation_window', 300)
                    )
                    conditions.append(condition)
                
                # Parse actions
                actions = []
                for action_data in policy_data.get('actions', []):
                    action = ScalingActionConfig(
                        action=ScalingAction(action_data['action']),
                        target_value=action_data['target_value'],
                        increment=action_data.get('increment'),
                        max_value=action_data.get('max_value'),
                        min_value=action_data.get('min_value')
                    )
                    actions.append(action)
                
                # Create policy
                policy = AutoScalingPolicy(
                    policy_id=policy_id,
                    name=policy_data['name'],
                    description=policy_data.get('description', ''),
                    enabled=policy_data.get('enabled', True),
                    priority=policy_data.get('priority', 0),
                    cooldown_period=policy_data.get('cooldown_period', 300),
                    conditions=conditions,
                    actions=actions
                )
                
                self.policies[policy_id] = policy
                
            except Exception as e:
                self.logger.error(f"Failed to load policy {policy_id}: {e}")
        
        self.logger.info(f"Loaded {len(self.policies)} scaling policies")
    
    async def evaluate_policies(self) -> List[ScalingDecision]:
        """Evaluate all active scaling policies"""
        decisions = []
        
        # Sort policies by priority
        sorted_policies = sorted(
            [p for p in self.policies.values() if p.enabled and p.status == PolicyStatus.ACTIVE],
            key=lambda p: p.priority,
            reverse=True
        )
        
        for policy in sorted_policies:
            try:
                decision = await self._evaluate_policy(policy)
                decisions.append(decision)
                
                # Execute decision if conditions are met
                if decision.condition_met:
                    await self._execute_scaling_decision(decision)
                    
            except Exception as e:
                self.logger.error(f"Policy evaluation failed for {policy.policy_id}: {e}")
                policy.status = PolicyStatus.ERROR
        
        return decisions
    
    async def _evaluate_policy(self, policy: AutoScalingPolicy) -> ScalingDecision:
        """Evaluate a single scaling policy"""
        
        # Check cooldown period
        if policy.last_execution:
            time_since_execution = (datetime.now() - policy.last_execution).total_seconds()
            if time_since_execution < policy.cooldown_period:
                return ScalingDecision(
                    policy_id=policy.policy_id,
                    decision_time=datetime.now(),
                    condition_met=False,
                    triggered_actions=[],
                    current_metrics={},
                    previous_metrics={},
                    confidence=0.0,
                    reasoning=f"Cooldown period active ({time_since_execution:.0f}s remaining)"
                )
        
        # Collect current and previous metrics
        current_metrics = {}
        previous_metrics = {}
        
        for condition in policy.conditions:
            metric_name = condition.trigger.value
            current_metrics[metric_name] = self.metrics_collector.get_current_metric_value(metric_name) or 0
            
            # Get metric value from previous evaluation window
            previous_values = self.metrics_collector.get_metric_values(
                metric_name, 
                condition.evaluation_window + condition.duration_seconds
            )
            if len(previous_values) > condition.duration_seconds:
                previous_metrics[metric_name] = sum(
                    m.value for m in previous_values[:condition.duration_seconds]
                ) / condition.duration_seconds
        
        # Check if all conditions are met
        conditions_met = []
        for condition in policy.conditions:
            metric_name = condition.trigger.value
            current_value = current_metrics.get(metric_name, 0)
            
            condition_met = self._evaluate_condition(condition, current_value, previous_metrics.get(metric_name, 0))
            conditions_met.append(condition_met)
        
        all_conditions_met = all(conditions_met)
        
        # Determine triggered actions
        triggered_actions = []
        if all_conditions_met:
            triggered_actions = policy.actions.copy()
        
        # Calculate confidence based on how long conditions have been met
        confidence = self._calculate_confidence(policy, all_conditions_met)
        
        reasoning = self._generate_reasoning(policy, conditions_met, confidence)
        
        return ScalingDecision(
            policy_id=policy.policy_id,
            decision_time=datetime.now(),
            condition_met=all_conditions_met,
            triggered_actions=triggered_actions,
            current_metrics=current_metrics,
            previous_metrics=previous_metrics,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _evaluate_condition(self, condition: ScalingCondition, current_value: float, 
                          previous_value: float) -> bool:
        """Evaluate if a scaling condition is met"""
        operator = condition.operator
        
        if operator == '>':
            return current_value > condition.threshold
        elif operator == '<':
            return current_value < condition.threshold
        elif operator == '>=':
            return current_value >= condition.threshold
        elif operator == '<=':
            return current_value <= condition.threshold
        elif operator == '==':
            return abs(current_value - condition.threshold) < 0.001
        elif operator == '!=':
            return abs(current_value - condition.threshold) >= 0.001
        else:
            self.logger.warning(f"Unknown operator: {operator}")
            return False
    
    def _calculate_confidence(self, policy: AutoScalingPolicy, conditions_met: bool) -> float:
        """Calculate confidence in scaling decision"""
        if not conditions_met:
            return 0.0
        
        # Simple confidence calculation based on how extreme the metric values are
        confidence_score = 0.0
        
        for condition in policy.conditions:
            metric_name = condition.trigger.value
            current_value = self.metrics_collector.get_current_metric_value(metric_name) or 0
            
            # Calculate how far from threshold
            distance = abs(current_value - condition.threshold)
            relative_distance = distance / max(condition.threshold, 1)
            
            confidence_score += min(relative_distance, 1.0)
        
        return min(confidence_score / len(policy.conditions), 1.0)
    
    def _generate_reasoning(self, policy: AutoScalingPolicy, conditions_met: List[bool], 
                          confidence: float) -> str:
        """Generate human-readable reasoning for scaling decision"""
        if not any(conditions_met):
            return "Scaling conditions not met"
        
        met_conditions = [
            f"{condition.trigger.value} {condition.operator} {condition.threshold}"
            for condition, met in zip(policy.conditions, conditions_met) if met
        ]
        
        return f"Conditions met: {', '.join(met_conditions)} (confidence: {confidence:.2%})"
    
    async def _execute_scaling_decision(self, decision: ScalingDecision):
        """Execute scaling actions based on decision"""
        if not decision.triggered_actions:
            return
        
        policy = self.policies[decision.policy_id]
        
        try:
            # Execute each action
            for action_config in decision.triggered_actions:
                handler = self.execution_handlers.get(action_config.action)
                if handler:
                    await handler(action_config)
                else:
                    self.logger.warning(f"No handler found for action: {action_config.action}")
            
            # Update policy statistics
            policy.execution_count += 1
            policy.success_count += 1
            policy.last_execution = datetime.now()
            self.last_scale_time = datetime.now()
            
            # Store decision in history
            self.policy_history[decision.policy_id].append(decision)
            
            self.logger.info(f"Scaling decision executed for policy {decision.policy_id}")
            
        except Exception as e:
            self.logger.error(f"Scaling execution failed for policy {decision.policy_id}: {e}")
            policy.success_count = max(0, policy.success_count - 1)
    
    async def _handle_scale_out(self, action: ScalingActionConfig):
        """Handle horizontal scale out (increase replicas)"""
        target_replicas = int(action.target_value)
        
        # Validate limits
        if action.max_value:
            target_replicas = min(target_replicas, int(action.max_value))
        
        self.logger.info(f"Scaling out from {self.current_replicas} to {target_replicas} replicas")
        self.current_replicas = target_replicas
        
        # In production, this would execute actual scaling action
        # (e.g., kubectl scale deployment, Docker Compose up, etc.)
    
    async def _handle_scale_in(self, action: ScalingActionConfig):
        """Handle horizontal scale in (decrease replicas)"""
        target_replicas = int(action.target_value)
        
        # Validate limits
        if action.min_value:
            target_replicas = max(target_replicas, int(action.min_value))
        
        self.logger.info(f"Scaling in from {self.current_replicas} to {target_replicas} replicas")
        self.current_replicas = target_replicas
    
    async def _handle_scale_up_resource(self, action: ScalingActionConfig):
        """Handle vertical scale up (increase resources)"""
        if 'cpu' in action.action.value:
            target_cpu = int(action.target_value)
            if action.max_value:
                target_cpu = min(target_cpu, int(action.max_value))
            
            self.logger.info(f"Scaling CPU from {self.current_cpu_limit} to {target_cpu} millicores")
            self.current_cpu_limit = target_cpu
            
        elif 'memory' in action.action.value:
            target_memory = int(action.target_value)
            if action.max_value:
                target_memory = min(target_memory, int(action.max_value))
            
            self.logger.info(f"Scaling memory from {self.current_memory_limit} to {target_memory} MB")
            self.current_memory_limit = target_memory
    
    async def _handle_scale_down_resource(self, action: ScalingActionConfig):
        """Handle vertical scale down (decrease resources)"""
        if 'cpu' in action.action.value:
            target_cpu = int(action.target_value)
            if action.min_value:
                target_cpu = max(target_cpu, int(action.min_value))
            
            self.logger.info(f"Scaling CPU from {self.current_cpu_limit} to {target_cpu} millicores")
            self.current_cpu_limit = target_cpu
            
        elif 'memory' in action.action.value:
            target_memory = int(action.target_value)
            if action.min_value:
                target_memory = max(target_memory, int(action.min_value))
            
            self.logger.info(f"Scaling memory from {self.current_memory_limit} to {target_memory} MB")
            self.current_memory_limit = target_memory
    
    async def _handle_scale_up(self, action: ScalingActionConfig):
        """Handle generic scale up"""
        # Could be used for container orchestration level scaling
        self.logger.info(f"Scale up action: {action.target_value}")
    
    async def _handle_scale_down(self, action: ScalingActionConfig):
        """Handle generic scale down"""
        # Could be used for container orchestration level scaling
        self.logger.info(f"Scale down action: {action.target_value}")
    
    def get_policy_status(self) -> Dict[str, Any]:
        """Get status of all policies"""
        status = {
            'total_policies': len(self.policies),
            'active_policies': len([p for p in self.policies.values() if p.status == PolicyStatus.ACTIVE]),
            'current_replicas': self.current_replicas,
            'current_cpu_limit': self.current_cpu_limit,
            'current_memory_limit': self.current_memory_limit,
            'policies': {}
        }
        
        for policy_id, policy in self.policies.items():
            status['policies'][policy_id] = {
                'name': policy.name,
                'enabled': policy.enabled,
                'status': policy.status.value,
                'execution_count': policy.execution_count,
                'success_rate': policy.success_count / max(policy.execution_count, 1),
                'last_execution': policy.last_execution.isoformat() if policy.last_execution else None,
                'conditions_met_recently': self._check_recent_conditions(policy)
            }
        
        return status
    
    def _check_recent_conditions(self, policy: AutoScalingPolicy) -> bool:
        """Check if policy conditions have been met recently"""
        for condition in policy.conditions:
            metric_name = condition.trigger.value
            current_value = self.metrics_collector.get_current_metric_value(metric_name) or 0
            
            if not self._evaluate_condition(condition, current_value, 0):
                return False
        return True
    
    def export_policy_history(self, filepath: str):
        """Export scaling policy execution history"""
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'current_state': {
                'replicas': self.current_replicas,
                'cpu_limit': self.current_cpu_limit,
                'memory_limit': self.current_memory_limit,
                'last_scale_time': self.last_scale_time.isoformat()
            },
            'policy_history': {
                policy_id: [asdict(decision) for decision in decisions[-100:]]  # Last 100 decisions
                for policy_id, decisions in self.policy_history.items()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        self.logger.info(f"Policy history exported to {filepath}")

class AutoScalingOrchestrator:
    """Main auto-scaling orchestrator"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.metrics_collector = MetricsCollector(config.get('metrics', {}))
        self.scaling_engine = ScalingEngine(config.get('scaling', {}), self.metrics_collector)
        
        # Orchestration settings
        self.evaluation_interval = config.get('evaluation_interval', 60)  # seconds
        self.is_running = False
        self.orchestrator_task = None
    
    async def start(self):
        """Start auto-scaling orchestrator"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start metrics collection
        await self.metrics_collector.start_collection()
        
        # Start policy evaluation loop
        async def evaluation_loop():
            while self.is_running:
                try:
                    decisions = await self.scaling_engine.evaluate_policies()
                    
                    # Log any triggered actions
                    for decision in decisions:
                        if decision.condition_met:
                            self.logger.info(f"Policy {decision.policy_id}: {decision.reasoning}")
                    
                    await asyncio.sleep(self.evaluation_interval)
                    
                except Exception as e:
                    self.logger.error(f"Auto-scaling evaluation error: {e}")
                    await asyncio.sleep(self.evaluation_interval)
        
        self.orchestrator_task = asyncio.create_task(evaluation_loop())
        self.logger.info("Auto-scaling orchestrator started")
    
    async def stop(self):
        """Stop auto-scaling orchestrator"""
        self.is_running = False
        
        if self.orchestrator_task:
            self.orchestrator_task.cancel()
            try:
                await self.orchestrator_task
            except asyncio.CancelledError:
                pass
        
        await self.metrics_collector.stop_collection()
        self.logger.info("Auto-scaling orchestrator stopped")
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get comprehensive orchestrator status"""
        return {
            'is_running': self.is_running,
            'metrics_collection_active': self.metrics_collector.is_collecting,
            'scaling_engine_status': self.scaling_engine.get_policy_status(),
            'configuration': {
                'evaluation_interval': self.evaluation_interval,
                'collection_interval': self.metrics_collector.collection_interval
            }
        }

def create_sample_autoscaling_config() -> Dict:
    """Create sample auto-scaling configuration"""
    return {
        'metrics': {
            'collection_interval': 30,
            'custom_collectors': {
                'cpu_utilization': {
                    'type': 'system',
                    'source': 'psutil'
                },
                'memory_utilization': {
                    'type': 'system', 
                    'source': 'psutil'
                },
                'request_rate': {
                    'type': 'application',
                    'endpoint': '/metrics'
                },
                'response_time': {
                    'type': 'application',
                    'endpoint': '/metrics'
                }
            }
        },
        'scaling': {
            'evaluation_interval': 60,
            'scaling_policies': {
                'high_cpu_scale_out': {
                    'name': 'Scale Out on High CPU',
                    'description': 'Scale out when CPU usage is high for sustained period',
                    'enabled': True,
                    'priority': 10,
                    'cooldown_period': 300,
                    'conditions': [
                        {
                            'trigger': 'cpu_utilization',
                            'operator': '>',
                            'threshold': 80,
                            'duration_seconds': 120,
                            'evaluation_window': 300
                        }
                    ],
                    'actions': [
                        {
                            'action': 'scale_out',
                            'target_value': 5,
                            'increment': 2,
                            'max_value': 10
                        }
                    ]
                },
                'low_cpu_scale_in': {
                    'name': 'Scale In on Low CPU',
                    'description': 'Scale in when CPU usage is low for sustained period',
                    'enabled': True,
                    'priority': 5,
                    'cooldown_period': 600,
                    'conditions': [
                        {
                            'trigger': 'cpu_utilization',
                            'operator': '<',
                            'threshold': 30,
                            'duration_seconds': 300,
                            'evaluation_window': 600
                        }
                    ],
                    'actions': [
                        {
                            'action': 'scale_in',
                            'target_value': 2,
                            'increment': 1,
                            'min_value': 1
                        }
                    ]
                },
                'memory_pressure': {
                    'name': 'Scale Resources on Memory Pressure',
                    'description': 'Scale up resources when memory usage is high',
                    'enabled': True,
                    'priority': 8,
                    'cooldown_period': 900,
                    'conditions': [
                        {
                            'trigger': 'memory_utilization',
                            'operator': '>',
                            'threshold': 85,
                            'duration_seconds': 180,
                            'evaluation_window': 360
                        }
                    ],
                    'actions': [
                        {
                            'action': 'scale_up_resource',
                            'target_value': 2048,
                            'max_value': 8192
                        }
                    ]
                }
            }
        }
    }

def main():
    """Example usage and testing"""
    async def demo_autoscaling():
        # Create sample configuration
        config = create_sample_autoscaling_config()
        
        # Initialize auto-scaling orchestrator
        orchestrator = AutoScalingOrchestrator(config)
        
        print("Auto-Scaling Orchestrator Demo")
        print("=" * 50)
        
        try:
            # Start orchestrator
            await orchestrator.start()
            
            print("Auto-scaling orchestrator started")
            print("Monitoring metrics and evaluating policies...")
            
            # Monitor for a short period
            for i in range(10):
                await asyncio.sleep(10)
                
                status = orchestrator.get_orchestrator_status()
                scaling_status = status['scaling_engine_status']
                
                print(f"\n--- Status Update {i+1} ---")
                print(f"Current replicas: {scaling_status['current_replicas']}")
                print(f"CPU limit: {scaling_status['current_cpu_limit']} millicores")
                print(f"Memory limit: {scaling_status['current_memory_limit']} MB")
                print(f"Active policies: {scaling_status['active_policies']}")
                
                # Show policy details
                for policy_id, policy_status in scaling_status['policies'].items():
                    if policy_status['execution_count'] > 0:
                        print(f"  {policy_status['name']}: "
                              f"{policy_status['execution_count']} executions, "
                              f"{policy_status['success_rate']:.1%} success rate")
            
            # Export policy history
            orchestrator.scaling_engine.export_policy_history('/tmp/autoscaling_history.json')
            print(f"\nPolicy history exported")
            
        except Exception as e:
            print(f"Auto-scaling demo failed: {e}")
        
        finally:
            # Stop orchestrator
            await orchestrator.stop()
            print("Auto-scaling orchestrator stopped")
    
    # Run the demo
    asyncio.run(demo_autoscaling())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()