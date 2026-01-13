#!/usr/bin/env python3
"""
Automated Scaling System
Scales services based on load metrics and performance indicators
"""

import os
import sys
import json
import yaml
import time
import psutil
import logging
import threading
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class ScalingAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"

class ScalingTrigger(Enum):
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    RESPONSE_TIME = "response_time"
    QUEUE_LENGTH = "queue_length"
    ERROR_RATE = "error_rate"

@dataclass
class ScalingPolicy:
    service_name: str
    min_instances: int
    max_instances: int
    cpu_threshold: float
    memory_threshold: float
    response_time_threshold: float
    cooldown_period: int  # seconds
    scale_up_factor: float
    scale_down_factor: float

@dataclass
class ScalingMetric:
    service_name: str
    current_instances: int
    cpu_usage: float
    memory_usage: float
    response_time: Optional[float]
    queue_length: Optional[int]
    error_rate: float
    timestamp: datetime

class AutomatedScalingSystem:
    def __init__(self, config_path: str = "/workspace/orchestration/config/services.yaml"):
        self.config_path = config_path
        self.services = {}
        self.scaling_policies = {}
        self.scaling_history = []
        self.running = False
        
        # Setup logging
        self.setup_logging()
        
        # Load configuration
        self.load_configuration()
        
        # Initialize scaling state
        self.service_instances = {}
        self.last_scaling_action = {}
        self.cooldown_timers = {}
        
        self.logger.info("Automated Scaling System initialized")

    def setup_logging(self):
        """Setup logging for scaling system"""
        log_dir = Path("/workspace/orchestration/logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger('AutomatedScalingSystem')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler(log_dir / 'scaling.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def load_configuration(self):
        """Load scaling configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            scaling_config = config.get('scaling', {})
            
            # Load service configurations
            self.services = config.get('services', {})
            
            # Load scaling policies
            policies = scaling_config.get('policies', [])
            for policy in policies:
                scaling_policy = ScalingPolicy(
                    service_name=policy['service'],
                    min_instances=policy.get('min_instances', 1),
                    max_instances=policy.get('max_instances', 5),
                    cpu_threshold=policy.get('cpu_threshold', 70),
                    memory_threshold=policy.get('memory_threshold', 80),
                    response_time_threshold=policy.get('response_time_threshold', 2000),
                    cooldown_period=policy.get('cooldown_period', 300),
                    scale_up_factor=policy.get('scale_up_factor', 1.5),
                    scale_down_factor=policy.get('scale_down_factor', 0.7)
                )
                self.scaling_policies[policy['service']] = scaling_policy
            
            self.logger.info(f"Loaded {len(self.scaling_policies)} scaling policies")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def get_service_instances(self, service_name: str) -> int:
        """Get current number of service instances"""
        try:
            # Find processes for this service
            instances = 0
            service_config = self.services.get(service_name, {})
            service_command = service_config.get('command', '')
            
            if not service_command:
                return 1  # Default to 1 instance
            
            # Count processes running this service
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    # Simple pattern matching for service processes
                    if (service_name in cmdline.lower() or 
                        any(service_name in arg for arg in pinfo['cmdline'])):
                        instances += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # If no processes found, return 0 (service not running)
            return max(instances, 0)
            
        except Exception as e:
            self.logger.error(f"Error getting service instances for {service_name}: {e}")
            return 0

    def get_service_metrics(self, service_name: str) -> ScalingMetric:
        """Get scaling metrics for a service"""
        try:
            service_config = self.services.get(service_name, {})
            
            # Get aggregate metrics for all instances
            total_cpu = 0.0
            total_memory = 0.0
            instance_count = 0
            total_response_time = 0.0
            response_time_count = 0
            health_errors = 0
            
            # Find all processes for this service
            for proc in psutil.process_iter(['pid', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    cmdline = ' '.join(pinfo['cmdline']) if pinfo['cmdline'] else ''
                    
                    # Match service processes
                    if (service_name in cmdline.lower() or 
                        any(service_name in arg for arg in pinfo['cmdline'])):
                        
                        total_cpu += pinfo['cpu_percent']
                        total_memory += pinfo['memory_percent']
                        instance_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Get response time from health endpoint
            health_endpoint = service_config.get('health_endpoint')
            if health_endpoint and instance_count > 0:
                try:
                    import requests
                    start_time = time.time()
                    response = requests.get(health_endpoint, timeout=5)
                    response_time = (time.time() - start_time) * 1000  # milliseconds
                    total_response_time = response_time
                    response_time_count = 1
                    
                    if response.status_code >= 400:
                        health_errors += 1
                        
                except Exception:
                    # If health check fails, count as error
                    health_errors += 1
                    total_response_time = 5000  # Assume high response time
                    response_time_count = 1
            
            # Calculate averages
            avg_cpu = total_cpu / max(instance_count, 1)
            avg_memory = total_memory / max(instance_count, 1)
            avg_response_time = total_response_time / max(response_time_count, 1) if response_time_count > 0 else None
            
            # Calculate error rate
            error_rate = (health_errors / max(instance_count, 1)) * 100
            
            return ScalingMetric(
                service_name=service_name,
                current_instances=instance_count,
                cpu_usage=avg_cpu,
                memory_usage=avg_memory,
                response_time=avg_response_time,
                queue_length=None,  # Would need service-specific implementation
                error_rate=error_rate,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting service metrics for {service_name}: {e}")
            return ScalingMetric(
                service_name=service_name,
                current_instances=0,
                cpu_usage=0.0,
                memory_usage=0.0,
                response_time=None,
                queue_length=None,
                error_rate=0.0,
                timestamp=datetime.now()
            )

    def evaluate_scaling_decision(self, policy: ScalingPolicy, metrics: ScalingMetric) -> Tuple[ScalingAction, int]:
        """Evaluate whether to scale up, down, or take no action"""
        current_instances = metrics.current_instances
        
        # Check if service is not running
        if current_instances == 0:
            return ScalingAction.SCALE_UP, 1
        
        # Check cooldown period
        last_action_time = self.last_scaling_action.get(petrics.service_name)
        if last_action_time:
            time_since_last_action = (datetime.now() - last_action_time).total_seconds()
            if time_since_last_action < policy.cooldown_period:
                return ScalingAction.NO_ACTION, 0
        
        # Evaluate scaling up conditions
        scale_up_conditions = []
        if metrics.cpu_usage > policy.cpu_threshold:
            scale_up_conditions.append("CPU")
        if metrics.memory_usage > policy.memory_threshold:
            scale_up_conditions.append("Memory")
        if metrics.response_time and metrics.response_time > policy.response_time_threshold:
            scale_up_conditions.append("ResponseTime")
        if metrics.error_rate > 10:  # 10% error rate threshold
            scale_up_conditions.append("ErrorRate")
        
        # Evaluate scaling down conditions
        scale_down_conditions = []
        if metrics.cpu_usage < policy.cpu_threshold * policy.scale_down_factor:
            scale_down_conditions.append("CPU")
        if metrics.memory_usage < policy.memory_threshold * policy.scale_down_factor:
            scale_down_conditions.append("Memory")
        if metrics.response_time and metrics.response_time < policy.response_time_threshold * 0.5:
            scale_down_conditions.append("ResponseTime")
        if metrics.error_rate < 1:  # Less than 1% error rate
            scale_down_conditions.append("ErrorRate")
        
        # Make scaling decision
        if scale_up_conditions and current_instances < policy.max_instances:
            # Scale up required
            scale_instances = max(1, int(current_instances * (policy.scale_up_factor - 1)))
            new_instances = min(current_instances + scale_instances, policy.max_instances)
            self.logger.info(
                f"Scaling up {metrics.service_name}: {scale_up_conditions} trigger, "
                f"{current_instances} -> {new_instances} instances"
            )
            return ScalingAction.SCALE_UP, new_instances - current_instances
        
        elif scale_down_conditions and current_instances > policy.min_instances:
            # Scale down possible
            scale_instances = max(1, int(current_instances * (1 - policy.scale_down_factor)))
            new_instances = max(current_instances - scale_instances, policy.min_instances)
            self.logger.info(
                f"Scaling down {metrics.service_name}: {scale_down_conditions} trigger, "
                f"{current_instances} -> {new_instances} instances"
            )
            return ScalingAction.SCALE_DOWN, current_instances - new_instances
        
        else:
            return ScalingAction.NO_ACTION, 0

    def execute_scaling_action(self, service_name: str, action: ScalingAction, instance_change: int) -> bool:
        """Execute scaling action"""
        try:
            if action == ScalingAction.NO_ACTION:
                return True
            
            current_instances = self.get_service_instances(service_name)
            
            if action == ScalingAction.SCALE_UP:
                new_instances = current_instances + instance_change
                success = self.scale_service_up(service_name, instance_change)
                if success:
                    self.logger.info(f"Successfully scaled up {service_name} by {instance_change} instances")
                    self.record_scaling_action(service_name, action, current_instances, new_instances)
                    return True
            
            elif action == ScalingAction.SCALE_DOWN:
                new_instances = current_instances - instance_change
                success = self.scale_service_down(service_name, instance_change)
                if success:
                    self.logger.info(f"Successfully scaled down {service_name} by {instance_change} instances")
                    self.record_scaling_action(service_name, action, current_instances, new_instances)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error executing scaling action for {service_name}: {e}")
            return False

    def scale_service_up(self, service_name: str, instances: int) -> bool:
        """Scale service up by creating new instances"""
        try:
            # In a real implementation, this would:
            # 1. Start new container/process instances
            # 2. Add them to load balancer
            # 3. Update service discovery
            
            self.logger.info(f"Scaling up {service_name} by {instances} instances")
            
            # For now, simulate the scaling action
            # In practice, this would integrate with Docker, Kubernetes, or process manager
            
            # Check if we can connect to the orchestrator
            try:
                # Try to interact with the main orchestrator
                from orchestration.orchestrator import ServiceOrchestrator
                
                # This would be more complex in a real implementation
                # For demonstration, we'll just log the action
                self.logger.info(f"Would start {instances} new instances of {service_name}")
                
            except ImportError:
                # Orchestrator not available, just simulate
                self.logger.warning("Orchestrator not available, simulating scaling up")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scaling up {service_name}: {e}")
            return False

    def scale_service_down(self, service_name: str, instances: int) -> bool:
        """Scale service down by stopping instances"""
        try:
            self.logger.info(f"Scaling down {service_name} by {instances} instances")
            
            # In a real implementation, this would:
            # 1. Remove instances from load balancer
            # 2. Stop container/process instances
            # 3. Clean up resources
            
            # For now, simulate the scaling action
            # Check if we can connect to the orchestrator
            try:
                from orchestration.orchestrator import ServiceOrchestrator
                
                # This would be more complex in a real implementation
                # For demonstration, we'll just log the action
                self.logger.info(f"Would stop {instances} instances of {service_name}")
                
            except ImportError:
                # Orchestrator not available, just simulate
                self.logger.warning("Orchestrator not available, simulating scaling down")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scaling down {service_name}: {e}")
            return False

    def record_scaling_action(self, service_name: str, action: ScalingAction, 
                            from_instances: int, to_instances: int):
        """Record scaling action for history"""
        scaling_record = {
            'service_name': service_name,
            'action': action.value,
            'from_instances': from_instances,
            'to_instances': to_instances,
            'timestamp': datetime.now().isoformat()
        }
        
        self.scaling_history.append(scaling_record)
        
        # Update last action time
        self.last_scaling_action[service_name] = datetime.now()
        
        # Save scaling history
        try:
            scaling_file = Path("/workspace/orchestration/logs/scaling_history.json")
            with open(scaling_file, 'w') as f:
                json.dump(self.scaling_history, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save scaling history: {e}")

    def analyze_scaling_trends(self) -> Dict[str, Any]:
        """Analyze scaling trends and patterns"""
        try:
            # Get recent scaling history (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_history = [
                record for record in self.scaling_history
                if datetime.fromisoformat(record['timestamp']) > cutoff_time
            ]
            
            # Analyze scaling frequency per service
            scaling_frequency = {}
            for record in recent_history:
                service = record['service_name']
                if service not in scaling_frequency:
                    scaling_frequency[service] = {'up': 0, 'down': 0}
                
                if record['action'] == 'scale_up':
                    scaling_frequency[service]['up'] += 1
                elif record['action'] == 'scale_down':
                    scaling_frequency[service]['down'] += 1
            
            # Calculate scaling stability score
            stability_scores = {}
            for service, counts in scaling_frequency.items():
                total_scaling = counts['up'] + counts['down']
                if total_scaling > 0:
                    # Lower frequency = higher stability
                    stability_score = max(0, 100 - (total_scaling * 10))
                else:
                    stability_score = 100
                stability_scores[service] = stability_score
            
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'scaling_frequency': scaling_frequency,
                'stability_scores': stability_scores,
                'total_scaling_events_24h': len(recent_history),
                'most_active_service': max(scaling_frequency.items(), 
                                          key=lambda x: x[1]['up'] + x[1]['down'])[0] if scaling_frequency else None
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing scaling trends: {e}")
            return {}

    def run_scaling_cycle(self):
        """Run a single scaling evaluation cycle"""
        try:
            scaling_decisions = []
            
            # Evaluate each service with scaling policy
            for service_name, policy in self.scaling_policies.items():
                try:
                    # Get current metrics
                    metrics = self.get_service_metrics(service_name)
                    
                    # Evaluate scaling decision
                    action, instance_change = self.evaluate_scaling_decision(policy, metrics)
                    
                    decision = {
                        'service_name': service_name,
                        'action': action.value,
                        'instance_change': instance_change,
                        'current_instances': metrics.current_instances,
                        'metrics': {
                            'cpu_usage': metrics.cpu_usage,
                            'memory_usage': metrics.memory_usage,
                            'response_time': metrics.response_time,
                            'error_rate': metrics.error_rate
                        }
                    }
                    
                    scaling_decisions.append(decision)
                    
                    # Execute scaling action if needed
                    if action != ScalingAction.NO_ACTION:
                        success = self.execute_scaling_action(service_name, action, instance_change)
                        if not success:
                            self.logger.error(f"Scaling action failed for {service_name}")
                    
                except Exception as e:
                    self.logger.error(f"Error evaluating scaling for {service_name}: {e}")
            
            # Log summary
            successful_actions = len([d for d in scaling_decisions if d['action'] != 'no_action'])
            self.logger.info(f"Scaling cycle completed: {successful_actions} actions taken")
            
        except Exception as e:
            self.logger.error(f"Error in scaling cycle: {e}")

    def generate_scaling_report(self) -> Dict[str, Any]:
        """Generate comprehensive scaling report"""
        try:
            # Get current service metrics
            service_metrics = {}
            for service_name in self.scaling_policies.keys():
                service_metrics[service_name] = self.get_service_metrics(service_name)
            
            # Analyze trends
            trend_analysis = self.analyze_scaling_trends()
            
            # Get scaling policies status
            policy_status = {}
            for service_name, policy in self.scaling_policies.items():
                current_instances = service_metrics[service_name].current_instances
                policy_status[service_name] = {
                    'current_instances': current_instances,
                    'min_instances': policy.min_instances,
                    'max_instances': policy.max_instances,
                    'within_limits': policy.min_instances <= current_instances <= policy.max_instances
                }
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'service_metrics': {
                    name: {
                        'current_instances': metrics.current_instances,
                        'cpu_usage': metrics.cpu_usage,
                        'memory_usage': metrics.memory_usage,
                        'response_time': metrics.response_time,
                        'error_rate': metrics.error_rate
                    }
                    for name, metrics in service_metrics.items()
                },
                'policy_status': policy_status,
                'trend_analysis': trend_analysis,
                'recent_scaling_actions': len(self.scaling_history[-10:])  # Last 10 actions
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate scaling report: {e}")
            return {}

    def start_scaling(self):
        """Start automated scaling system"""
        self.running = True
        self.logger.info("Starting automated scaling system")
        
        # Schedule scaling evaluation
        schedule.every(60).seconds.do(self.run_scaling_cycle)  # Check every minute
        schedule.every(30).minutes.do(self.generate_trend_analysis)
        
        # Main scaling loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(10)
            except Exception as e:
                self.logger.error(f"Error in scaling loop: {e}")
                time.sleep(30)

    def generate_trend_analysis(self):
        """Generate periodic trend analysis"""
        try:
            analysis = self.analyze_scaling_trends()
            
            # Save analysis
            analysis_file = Path("/workspace/orchestration/logs/scaling_trends.json")
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            self.logger.info("Scaling trend analysis generated")
            
        except Exception as e:
            self.logger.error(f"Failed to generate trend analysis: {e}")

    def stop_scaling(self):
        """Stop automated scaling system"""
        self.running = False
        self.logger.info("Stopping automated scaling system")

def main():
    """Main entry point for scaling system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated Scaling System")
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--evaluate', action='store_true', help='Run single evaluation')
    parser.add_argument('--report', action='store_true', help='Generate scaling report')
    
    args = parser.parse_args()
    
    scaling_system = AutomatedScalingSystem()
    
    if args.report:
        report = scaling_system.generate_scaling_report()
        print(json.dumps(report, indent=2))
        return
    
    if args.evaluate:
        scaling_system.run_scaling_cycle()
        return
    
    if args.daemon:
        scaling_system.start_scaling()
    else:
        # Run for a limited time
        scaling_system.start_scaling()
        try:
            time.sleep(300)  # Run for 5 minutes
        except KeyboardInterrupt:
            pass
        finally:
            scaling_system.stop_scaling()

if __name__ == "__main__":
    main()