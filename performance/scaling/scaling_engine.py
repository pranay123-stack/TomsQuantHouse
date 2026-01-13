#!/usr/bin/env python3
"""
Scaling Strategies Implementation
Implements horizontal and vertical scaling strategies for system optimization
"""

import asyncio
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import docker
import yaml
import aiohttp
import kubernetes
from pathlib import Path

class ScalingStrategy(Enum):
    """Types of scaling strategies"""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOTH = "both"

class ScaleDirection(Enum):
    """Direction of scaling operation"""
    UP = "up"
    DOWN = "down"

@dataclass
class ScalingAction:
    """Represents a scaling action"""
    action_id: str
    strategy: ScalingStrategy
    direction: ScaleDirection
    resource_type: str  # cpu, memory, instances, etc.
    target_value: float
    current_value: float
    timestamp: datetime
    success: bool
    message: str
    execution_time: float

@dataclass
class ScalingPolicy:
    """Defines scaling policy rules"""
    policy_id: str
    name: str
    resource_type: str
    scaling_strategy: ScalingStrategy
    min_threshold: float
    max_threshold: float
    scale_up_trigger: float
    scale_down_trigger: float
    cooldown_period: int  # seconds
    max_instances: int
    min_instances: int
    step_size: float
    enabled: bool = True

@dataclass
class ScalingMetrics:
    """Current scaling-related metrics"""
    timestamp: datetime
    current_instances: int
    target_instances: int
    cpu_utilization: float
    memory_utilization: float
    request_rate: float
    queue_depth: int
    response_time_p95: float
    error_rate: float

class ContainerOrchestrator:
    """Container orchestration interface for scaling operations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.docker_client = None
        self.k8s_client = None
        self.initialize_clients()
    
    def initialize_clients(self):
        """Initialize container orchestration clients"""
        try:
            if self.config.get('use_docker', True):
                self.docker_client = docker.from_env()
                self.logger.info("Docker client initialized")
        except Exception as e:
            self.logger.warning(f"Docker client initialization failed: {e}")
        
        try:
            if self.config.get('use_kubernetes', False):
                kubernetes.config.load_incluster_config() or kubernetes.config.load_config()
                self.k8s_client = kubernetes.client.ApiClient()
                self.logger.info("Kubernetes client initialized")
        except Exception as e:
            self.logger.warning(f"Kubernetes client initialization failed: {e}")
    
    async def scale_horizontal(self, service_name: str, target_instances: int, 
                              namespace: str = "default") -> Dict:
        """Scale service horizontally (change instance count)"""
        try:
            if self.k8s_client:
                return await self._scale_k8s_horizontal(service_name, target_instances, namespace)
            elif self.docker_client:
                return await self._scale_docker_horizontal(service_name, target_instances)
            else:
                raise Exception("No orchestration platform available")
        except Exception as e:
            self.logger.error(f"Horizontal scaling failed: {e}")
            raise
    
    async def _scale_k8s_horizontal(self, service_name: str, target_instances: int, 
                                   namespace: str) -> Dict:
        """Scale Kubernetes deployment horizontally"""
        try:
            apps_v1 = kubernetes.client.AppsV1Api(self.k8s_client)
            
            # Get current deployment
            deployment = apps_v1.read_namespaced_deployment(
                name=service_name,
                namespace=namespace
            )
            
            # Update replica count
            deployment.spec.replicas = target_instances
            
            # Apply changes
            updated_deployment = apps_v1.patch_namespaced_deployment(
                name=service_name,
                namespace=namespace,
                body=deployment
            )
            
            return {
                "success": True,
                "action": "scale_horizontal",
                "service": service_name,
                "target_instances": target_instances,
                "previous_replicas": updated_deployment.spec.replicas,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Kubernetes horizontal scaling failed: {e}")
            raise
    
    async def _scale_docker_horizontal(self, service_name: str, target_instances: int) -> Dict:
        """Scale Docker Compose service horizontally"""
        try:
            # This is a simplified implementation
            # In production, you'd use Docker Swarm or Compose API
            containers = self.docker_client.containers.list(
                filters={"name": service_name}
            )
            
            current_instances = len(containers)
            
            if target_instances > current_instances:
                # Scale up
                for i in range(target_instances - current_instances):
                    # Launch new container instance
                    # This would include proper configuration, networks, etc.
                    pass
            elif target_instances < current_instances:
                # Scale down
                for container in containers[target_instances:]:
                    container.stop()
            
            return {
                "success": True,
                "action": "scale_horizontal",
                "service": service_name,
                "target_instances": target_instances,
                "previous_instances": current_instances,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Docker horizontal scaling failed: {e}")
            raise
    
    async def scale_vertical(self, service_name: str, target_cpu: str, target_memory: str,
                           namespace: str = "default") -> Dict:
        """Scale service vertically (change resource allocation)"""
        try:
            if self.k8s_client:
                return await self._scale_k8s_vertical(service_name, target_cpu, target_memory, namespace)
            else:
                raise Exception("Vertical scaling requires Kubernetes")
        except Exception as e:
            self.logger.error(f"Vertical scaling failed: {e}")
            raise
    
    async def _scale_k8s_vertical(self, service_name: str, target_cpu: str, target_memory: str,
                                 namespace: str) -> Dict:
        """Scale Kubernetes resource allocation vertically"""
        try:
            apps_v1 = kubernetes.client.AppsV1Api(self.k8s_client)
            
            # Get current deployment
            deployment = apps_v1.read_namespaced_deployment(
                name=service_name,
                namespace=namespace
            )
            
            # Update resource limits and requests
            container = deployment.spec.template.spec.containers[0]
            container.resources.limits = {
                'cpu': target_cpu,
                'memory': target_memory
            }
            container.resources.requests = {
                'cpu': target_cpu,
                'memory': target_memory
            }
            
            # Apply changes
            updated_deployment = apps_v1.patch_namespaced_deployment(
                name=service_name,
                namespace=namespace,
                body=deployment
            )
            
            return {
                "success": True,
                "action": "scale_vertical",
                "service": service_name,
                "target_cpu": target_cpu,
                "target_memory": target_memory,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Kubernetes vertical scaling failed: {e}")
            raise

class ScalingEngine:
    """Core scaling engine with policy-based automation"""
    
    def __init__(self, config: Dict, orchestrator: ContainerOrchestrator):
        self.config = config
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(__name__)
        self.scaling_policies = {}
        self.scaling_history = []
        self.active_scaling_actions = {}
        self.last_scaled = {}
        
        # Load scaling policies
        self.load_scaling_policies()
    
    def load_scaling_policies(self):
        """Load scaling policies from configuration"""
        policies_config = self.config.get('scaling_policies', {})
        
        for policy_id, policy_data in policies_config.items():
            try:
                policy = ScalingPolicy(
                    policy_id=policy_id,
                    name=policy_data.get('name', policy_id),
                    resource_type=policy_data.get('resource_type', 'cpu'),
                    scaling_strategy=ScalingStrategy(policy_data.get('strategy', 'horizontal')),
                    min_threshold=policy_data.get('min_threshold', 30),
                    max_threshold=policy_data.get('max_threshold', 80),
                    scale_up_trigger=policy_data.get('scale_up_trigger', 70),
                    scale_down_trigger=policy_data.get('scale_down_trigger', 30),
                    cooldown_period=policy_data.get('cooldown_period', 300),
                    max_instances=policy_data.get('max_instances', 10),
                    min_instances=policy_data.get('min_instances', 1),
                    step_size=policy_data.get('step_size', 1),
                    enabled=policy_data.get('enabled', True)
                )
                self.scaling_policies[policy_id] = policy
            except Exception as e:
                self.logger.error(f"Failed to load scaling policy {policy_id}: {e}")
        
        self.logger.info(f"Loaded {len(self.scaling_policies)} scaling policies")
    
    async def evaluate_scaling_conditions(self, metrics: ScalingMetrics) -> List[str]:
        """Evaluate which scaling policies should trigger"""
        triggered_policies = []
        
        for policy in self.scaling_policies.values():
            if not policy.enabled:
                continue
            
            # Check cooldown period
            last_scale_time = self.last_scaled.get(policy.policy_id, datetime.min)
            if (datetime.now() - last_scale_time).total_seconds() < policy.cooldown_period:
                continue
            
            # Evaluate condition based on resource type
            current_value = self._get_current_metric_value(metrics, policy.resource_type)
            
            if current_value >= policy.scale_up_trigger:
                # Check if we can scale up
                if metrics.current_instances < policy.max_instances:
                    triggered_policies.append(policy.policy_id)
            elif current_value <= policy.scale_down_trigger:
                # Check if we can scale down
                if metrics.current_instances > policy.min_instances:
                    triggered_policies.append(policy.policy_id)
        
        return triggered_policies
    
    def _get_current_metric_value(self, metrics: ScalingMetrics, resource_type: str) -> float:
        """Get the current value for a specific resource type"""
        if resource_type == 'cpu':
            return metrics.cpu_utilization
        elif resource_type == 'memory':
            return metrics.memory_utilization
        elif resource_type == 'requests':
            return metrics.request_rate
        elif resource_type == 'queue':
            return metrics.queue_depth
        elif resource_type == 'response_time':
            return metrics.response_time_p95
        elif resource_type == 'error_rate':
            return metrics.error_rate
        else:
            return 0.0
    
    async def execute_scaling_action(self, policy_id: str, metrics: ScalingMetrics) -> ScalingAction:
        """Execute a scaling action based on policy and current metrics"""
        policy = self.scaling_policies[policy_id]
        action_id = f"{policy_id}_{int(time.time())}"
        
        start_time = time.time()
        
        try:
            # Calculate target scale values
            current_value = self._get_current_metric_value(metrics, policy.resource_type)
            
            if current_value >= policy.scale_up_trigger:
                direction = ScaleDirection.UP
                if policy.scaling_strategy in [ScalingStrategy.HORIZONTAL, ScalingStrategy.BOTH]:
                    # Calculate target instances for horizontal scaling
                    target_instances = min(
                        metrics.current_instances + policy.step_size,
                        policy.max_instances
                    )
                    
                    # Execute horizontal scaling
                    if target_instances != metrics.current_instances:
                        scaling_result = await self.orchestrator.scale_horizontal(
                            service_name=policy.resource_type,
                            target_instances=int(target_instances)
                        )
                    
            elif current_value <= policy.scale_down_trigger:
                direction = ScaleDirection.DOWN
                if policy.scaling_strategy in [ScalingStrategy.HORIZONTAL, ScalingStrategy.BOTH]:
                    target_instances = max(
                        metrics.current_instances - policy.step_size,
                        policy.min_instances
                    )
                    
                    if target_instances != metrics.current_instances:
                        scaling_result = await self.orchestrator.scale_horizontal(
                            service_name=policy.resource_type,
                            target_instances=int(target_instances)
                        )
            
            # Record successful scaling action
            action = ScalingAction(
                action_id=action_id,
                strategy=policy.scaling_strategy,
                direction=direction,
                resource_type=policy.resource_type,
                target_value=target_instances if 'target_instances' in locals() else current_value,
                current_value=current_value,
                timestamp=datetime.now(),
                success=True,
                message=f"Scaling {direction.value} successful",
                execution_time=time.time() - start_time
            )
            
            self.last_scaled[policy_id] = datetime.now()
            self.scaling_history.append(action)
            
        except Exception as e:
            # Record failed scaling action
            action = ScalingAction(
                action_id=action_id,
                strategy=policy.scaling_strategy,
                direction=direction if 'direction' in locals() else ScaleDirection.UP,
                resource_type=policy.resource_type,
                target_value=current_value,
                current_value=current_value,
                timestamp=datetime.now(),
                success=False,
                message=f"Scaling failed: {str(e)}",
                execution_time=time.time() - start_time
            )
            
            self.logger.error(f"Scaling action failed: {e}")
        
        self.active_scaling_actions[action_id] = action
        return action
    
    async def auto_scale(self, metrics: ScalingMetrics):
        """Run automatic scaling evaluation and execution"""
        try:
            # Evaluate which policies should trigger
            triggered_policies = await self.evaluate_scaling_conditions(metrics)
            
            if triggered_policies:
                self.logger.info(f"Triggered scaling policies: {triggered_policies}")
                
                # Execute scaling actions
                for policy_id in triggered_policies:
                    action = await self.execute_scaling_action(policy_id, metrics)
                    self.logger.info(f"Scaling action: {action.action_id} - {action.message}")
            else:
                self.logger.debug("No scaling policies triggered")
                
        except Exception as e:
            self.logger.error(f"Auto-scaling failed: {e}")
    
    def get_scaling_recommendations(self, metrics: ScalingMetrics) -> List[Dict]:
        """Get scaling recommendations without executing"""
        recommendations = []
        
        for policy in self.scaling_policies.values():
            if not policy.enabled:
                continue
            
            current_value = self._get_current_metric_value(metrics, policy.resource_type)
            
            recommendation = {
                'policy_id': policy.policy_id,
                'policy_name': policy.name,
                'resource_type': policy.resource_type,
                'current_value': current_value,
                'status': 'stable',
                'recommendation': None
            }
            
            if current_value >= policy.scale_up_trigger:
                recommendation['status'] = 'scale_up_needed'
                recommendation['recommendation'] = {
                    'action': 'scale_up',
                    'strategy': policy.scaling_strategy.value,
                    'reason': f"{policy.resource_type} utilization ({current_value:.1f}%) exceeds threshold ({policy.scale_up_trigger}%)"
                }
            elif current_value <= policy.scale_down_trigger:
                recommendation['status'] = 'scale_down_possible'
                recommendation['recommendation'] = {
                    'action': 'scale_down',
                    'strategy': policy.scaling_strategy.value,
                    'reason': f"{policy.resource_type} utilization ({current_value:.1f}%) below threshold ({policy.scale_down_trigger}%)"
                }
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def export_scaling_history(self, filepath: str):
        """Export scaling history to file"""
        data = {
            'scaling_history': [asdict(action) for action in self.scaling_history],
            'scaling_policies': {pid: asdict(policy) for pid, policy in self.scaling_policies.items()},
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Scaling history exported to {filepath}")

class CloudScaler:
    """Cloud-specific scaling implementations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    async def scale_aws_autoscaling_group(self, asg_name: str, desired_capacity: int) -> Dict:
        """Scale AWS Auto Scaling Group"""
        try:
            # This would use boto3 for actual AWS operations
            return {
                "success": True,
                "platform": "aws",
                "resource_type": "autoscaling_group",
                "resource_name": asg_name,
                "desired_capacity": desired_capacity,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"AWS scaling failed: {e}")
            raise
    
    async def scale_azure_vm_scale_set(self, vmss_name: str, instance_count: int) -> Dict:
        """Scale Azure VM Scale Set"""
        try:
            # This would use Azure SDK for actual Azure operations
            return {
                "success": True,
                "platform": "azure",
                "resource_type": "vm_scale_set",
                "resource_name": vmss_name,
                "instance_count": instance_count,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Azure scaling failed: {e}")
            raise
    
    async def scale_gcp_managed_instance_group(self, mig_name: str, target_size: int) -> Dict:
        """Scale Google Cloud Managed Instance Group"""
        try:
            # This would use Google Cloud SDK for actual GCP operations
            return {
                "success": True,
                "platform": "gcp",
                "resource_type": "managed_instance_group",
                "resource_name": mig_name,
                "target_size": target_size,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"GCP scaling failed: {e}")
            raise

def create_sample_scaling_config() -> Dict:
    """Create sample scaling configuration"""
    return {
        'orchestrator': {
            'use_docker': True,
            'use_kubernetes': False,
            'namespace': 'default'
        },
        'scaling_policies': {
            'cpu_scaling_policy': {
                'name': 'CPU-based Scaling',
                'resource_type': 'cpu',
                'strategy': 'horizontal',
                'min_threshold': 20,
                'max_threshold': 90,
                'scale_up_trigger': 70,
                'scale_down_trigger': 30,
                'cooldown_period': 300,
                'max_instances': 20,
                'min_instances': 2,
                'step_size': 1,
                'enabled': True
            },
            'memory_scaling_policy': {
                'name': 'Memory-based Scaling',
                'resource_type': 'memory',
                'strategy': 'horizontal',
                'min_threshold': 30,
                'max_threshold': 85,
                'scale_up_trigger': 75,
                'scale_down_trigger': 40,
                'cooldown_period': 600,
                'max_instances': 15,
                'min_instances': 1,
                'step_size': 1,
                'enabled': True
            },
            'request_rate_scaling': {
                'name': 'Request Rate Scaling',
                'resource_type': 'requests',
                'strategy': 'horizontal',
                'min_threshold': 100,
                'max_threshold': 2000,
                'scale_up_trigger': 1500,
                'scale_down_trigger': 200,
                'cooldown_period': 180,
                'max_instances': 25,
                'min_instances': 1,
                'step_size': 2,
                'enabled': True
            }
        },
        'cloud_providers': {
            'aws': {
                'region': 'us-west-2',
                'enabled': False
            },
            'azure': {
                'region': 'eastus',
                'enabled': False
            },
            'gcp': {
                'region': 'us-central1',
                'enabled': False
            }
        }
    }

def main():
    """Example usage and testing"""
    import asyncio
    
    async def demo_scaling():
        # Create sample configuration
        config = create_sample_scaling_config()
        
        # Initialize orchestrator and scaling engine
        orchestrator = ContainerOrchestrator(config['orchestrator'])
        scaling_engine = ScalingEngine(config, orchestrator)
        
        # Create sample metrics
        metrics = ScalingMetrics(
            timestamp=datetime.now(),
            current_instances=3,
            target_instances=3,
            cpu_utilization=75.5,
            memory_utilization=60.0,
            request_rate=1200.0,
            queue_depth=50,
            response_time_p95=250.0,
            error_rate=0.01
        )
        
        print("Scaling Strategies Demo")
        print("=" * 50)
        
        # Get recommendations
        recommendations = scaling_engine.get_scaling_recommendations(metrics)
        print("\nScaling Recommendations:")
        for rec in recommendations:
            print(f"  {rec['policy_name']}: {rec['status']}")
            if rec['recommendation']:
                print(f"    Action: {rec['recommendation']['action']}")
                print(f"    Reason: {rec['recommendation']['reason']}")
        
        # Execute auto-scaling
        print("\nExecuting auto-scaling...")
        await scaling_engine.auto_scale(metrics)
        
        # Export scaling history
        scaling_engine.export_scaling_history('/tmp/scaling_history.json')
        print("\nScaling history exported")
    
    # Run the demo
    asyncio.run(demo_scaling())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()