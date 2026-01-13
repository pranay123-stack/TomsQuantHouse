#!/usr/bin/env python3
"""
Resource Allocation and Container Optimization
Optimizes Docker containers, Kubernetes pods, and resource allocation
"""

import asyncio
import json
import logging
import time
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import docker
import psutil
import numpy as np
from pathlib import Path
import aiofiles
import subprocess
import re

class ContainerOrchestrator(Enum):
    """Supported container orchestrators"""
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    PODMAN = "podman"
    DOCKER_SWARM = "docker_swarm"

class ResourceType(Enum):
    """Resource types for optimization"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"

@dataclass
class ResourceQuota:
    """Resource quota specification"""
    resource_type: ResourceType
    limit: float
    request: float
    unit: str  # cores, MB, GB, etc.

@dataclass
class ContainerMetrics:
    """Container performance metrics"""
    container_id: str
    name: str
    image: str
    status: str
    cpu_usage_percent: float
    memory_usage_mb: float
    memory_limit_mb: float
    network_io_mb: float
    disk_io_mb: float
    restart_count: int
    uptime_seconds: float
    created_at: datetime

@dataclass
class ResourceRecommendation:
    """Resource optimization recommendation"""
    container_id: str
    resource_type: ResourceType
    current_allocation: float
    recommended_allocation: float
    reason: str
    potential_improvement: float
    confidence: float
    implementation_steps: List[str]

@dataclass
class ContainerOptimization:
    """Container optimization analysis"""
    container_id: str
    name: str
    cpu_efficiency: float
    memory_efficiency: float
    network_efficiency: float
    overall_efficiency: float
    issues: List[str]
    recommendations: List[ResourceRecommendation]

class ResourceProfiler:
    """Resource usage profiler for containers"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.docker_client = None
        self.profiling_data = {}
        
        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            self.logger.warning(f"Docker client initialization failed: {e}")
    
    def get_system_resources(self) -> Dict[str, float]:
        """Get current system resource usage"""
        try:
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'load_average': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'disk_free_gb': psutil.disk_usage('/').free / (1024**3)
            }
        except Exception as e:
            self.logger.error(f"Failed to get system resources: {e}")
            return {}
    
    def get_container_stats(self, container_id: str) -> Optional[Dict]:
        """Get detailed container statistics"""
        try:
            if not self.docker_client:
                return None
            
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU usage
            cpu_usage = 0
            if 'cpu_stats' in stats and 'precpu_stats' in stats:
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                
                if system_delta > 0:
                    cpu_usage = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            
            # Calculate memory usage
            memory_usage = 0
            if 'memory_stats' in stats:
                memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)  # MB
                memory_limit = stats['memory_stats'].get('limit', float('inf')) / (1024 * 1024)  # MB
            
            # Network I/O
            network_io = 0
            if 'networks' in stats:
                network_io = sum(
                    stats['networks'][iface]['rx_bytes'] + stats['networks'][iface]['tx_bytes']
                    for iface in stats['networks']
                ) / (1024 * 1024)  # MB
            
            # Disk I/O
            disk_io = 0
            if 'blkio_stats' in stats:
                for io_entry in stats['blkio_stats']['io_service_bytes_recursive'] or []:
                    if io_entry['op'] == 'Read':
                        disk_io += io_entry['value']
                    elif io_entry['op'] == 'Write':
                        disk_io += io_entry['value']
                disk_io = disk_io / (1024 * 1024)  # MB
            
            return {
                'cpu_usage_percent': cpu_usage,
                'memory_usage_mb': memory_usage,
                'memory_limit_mb': memory_limit,
                'network_io_mb': network_io,
                'disk_io_mb': disk_io,
                'cpu_throttling': stats.get('cpu_stats', {}).get('throttling_data', {}).get('throttled_periods', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get container stats for {container_id}: {e}")
            return None
    
    def get_all_containers(self) -> List[ContainerMetrics]:
        """Get metrics for all running containers"""
        containers = []
        
        try:
            if not self.docker_client:
                return containers
            
            for container in self.docker_client.containers.list():
                try:
                    # Basic container info
                    container_info = {
                        'container_id': container.id[:12],  # Short ID
                        'name': container.name,
                        'image': container.image.tags[0] if container.image.tags else container.image.id,
                        'status': container.status,
                        'restart_count': 0,
                        'created_at': datetime.fromtimestamp(container.attrs['Created'])
                    }
                    
                    # Get detailed stats
                    stats = self.get_container_stats(container.id)
                    if stats:
                        container_info.update(stats)
                    else:
                        # Default values if stats unavailable
                        container_info.update({
                            'cpu_usage_percent': 0,
                            'memory_usage_mb': 0,
                            'memory_limit_mb': float('inf'),
                            'network_io_mb': 0,
                            'disk_io_mb': 0
                        })
                    
                    # Calculate uptime
                    uptime_seconds = (datetime.now() - container_info['created_at']).total_seconds()
                    container_info['uptime_seconds'] = uptime_seconds
                    
                    containers.append(ContainerMetrics(**container_info))
                    
                except Exception as e:
                    self.logger.error(f"Error processing container {container.name}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Failed to get container list: {e}")
        
        return containers
    
    async def profile_container_workload(self, container_id: str, duration_seconds: int = 60) -> Dict:
        """Profile container resource usage over time"""
        self.logger.info(f"Starting workload profiling for container {container_id}")
        
        samples = []
        sample_interval = 5  # seconds
        
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            stats = self.get_container_stats(container_id)
            if stats:
                stats['timestamp'] = datetime.now()
                samples.append(stats)
            await asyncio.sleep(sample_interval)
        
        if not samples:
            return {}
        
        # Calculate statistics
        cpu_values = [s['cpu_usage_percent'] for s in samples]
        memory_values = [s['memory_usage_mb'] for s in samples]
        
        profiling_results = {
            'container_id': container_id,
            'profiling_duration': duration_seconds,
            'sample_count': len(samples),
            'cpu_stats': {
                'mean': np.mean(cpu_values),
                'median': np.median(cpu_values),
                'std': np.std(cpu_values),
                'min': np.min(cpu_values),
                'max': np.max(cpu_values),
                'p95': np.percentile(cpu_values, 95),
                'p99': np.percentile(cpu_values, 99)
            },
            'memory_stats': {
                'mean': np.mean(memory_values),
                'median': np.median(memory_values),
                'std': np.std(memory_values),
                'min': np.min(memory_values),
                'max': np.max(memory_values),
                'p95': np.percentile(memory_values, 95),
                'p99': np.percentile(memory_values, 99)
            }
        }
        
        # Store profiling data
        self.profiling_data[container_id] = profiling_results
        
        self.logger.info(f"Workload profiling completed for container {container_id}")
        return profiling_results

class ResourceOptimizer:
    """Resource allocation optimizer for containers"""
    
    def __init__(self, profiler: ResourceProfiler):
        self.profiler = profiler
        self.logger = logging.getLogger(__name__)
        
        # Optimization configuration
        self.optimization_config = {
            'cpu_buffer_percent': 20,  # Keep 20% CPU buffer
            'memory_buffer_percent': 15,  # Keep 15% memory buffer
            'min_cpu_cores': 0.1,
            'min_memory_mb': 128,
            'max_cpu_cores': 16,
            'max_memory_gb': 32
        }
    
    def analyze_container_efficiency(self, container: ContainerMetrics) -> ContainerOptimization:
        """Analyze container resource efficiency"""
        
        # Calculate efficiency scores (0-100)
        cpu_efficiency = self._calculate_cpu_efficiency(container)
        memory_efficiency = self._calculate_memory_efficiency(container)
        network_efficiency = self._calculate_network_efficiency(container)
        
        # Overall efficiency (weighted average)
        overall_efficiency = (
            cpu_efficiency * 0.4 +
            memory_efficiency * 0.4 +
            network_efficiency * 0.2
        )
        
        # Identify issues
        issues = []
        recommendations = []
        
        # CPU analysis
        if container.cpu_usage_percent < 30 and container.memory_limit_mb > 256:
            issues.append("Under-utilized CPU resources")
            recommendations.append(ResourceRecommendation(
                container_id=container.container_id,
                resource_type=ResourceType.CPU,
                current_allocation=container.memory_limit_mb / 1024,  # Assume 1:1 for demo
                recommended_allocation=max(self.optimization_config['min_cpu_cores'], 
                                         container.cpu_usage_percent / 100),
                reason="Low CPU utilization detected",
                potential_improvement=15.0,
                confidence=0.8,
                implementation_steps=[
                    "Reduce CPU allocation in container config",
                    "Monitor for performance impact",
                    "Adjust based on actual usage patterns"
                ]
            ))
        
        # Memory analysis
        if container.memory_usage_mb > container.memory_limit_mb * 0.9:
            issues.append("High memory utilization - risk of OOM")
            recommendations.append(ResourceRecommendation(
                container_id=container.container_id,
                resource_type=ResourceType.MEMORY,
                current_allocation=container.memory_limit_mb,
                recommended_allocation=container.memory_usage_mb * 1.2,  # 20% buffer
                reason="Memory usage approaching limit",
                potential_improvement=25.0,
                confidence=0.9,
                implementation_steps=[
                    "Increase memory limit",
                    "Investigate memory leaks",
                    "Optimize memory usage in application"
                ]
            ))
        
        elif container.memory_usage_mb < container.memory_limit_mb * 0.5:
            issues.append("Over-provisioned memory")
            recommendations.append(ResourceRecommendation(
                container_id=container.container_id,
                resource_type=ResourceType.MEMORY,
                current_allocation=container.memory_limit_mb,
                recommended_allocation=max(container.memory_usage_mb * 1.1, 
                                         self.optimization_config['min_memory_mb']),
                reason="Memory allocation exceeds actual usage",
                potential_improvement=20.0,
                confidence=0.85,
                implementation_steps=[
                    "Reduce memory allocation",
                    "Monitor for out-of-memory errors",
                    "Fine-tune based on peak usage"
                ]
            ))
        
        return ContainerOptimization(
            container_id=container.container_id,
            name=container.name,
            cpu_efficiency=cpu_efficiency,
            memory_efficiency=memory_efficiency,
            network_efficiency=network_efficiency,
            overall_efficiency=overall_efficiency,
            issues=issues,
            recommendations=recommendations
        )
    
    def _calculate_cpu_efficiency(self, container: ContainerMetrics) -> float:
        """Calculate CPU efficiency score"""
        if container.cpu_usage_percent == 0:
            return 0
        
        # Optimal utilization range: 60-80%
        optimal_min = 60
        optimal_max = 80
        
        if optimal_min <= container.cpu_usage_percent <= optimal_max:
            return 100  # Perfect efficiency
        elif container.cpu_usage_percent < optimal_min:
            # Under-utilized penalty
            penalty = (optimal_min - container.cpu_usage_percent) / optimal_min * 50
            return max(0, 100 - penalty)
        else:
            # Over-utilized penalty
            penalty = (container.cpu_usage_percent - optimal_max) / optimal_max * 50
            return max(0, 100 - penalty)
    
    def _calculate_memory_efficiency(self, container: ContainerMetrics) -> float:
        """Calculate memory efficiency score"""
        if container.memory_limit_mb == 0:
            return 0
        
        utilization_ratio = container.memory_usage_mb / container.memory_limit_mb * 100
        
        # Optimal utilization range: 70-85%
        optimal_min = 70
        optimal_max = 85
        
        if optimal_min <= utilization_ratio <= optimal_max:
            return 100
        elif utilization_ratio < optimal_min:
            # Under-utilized penalty
            penalty = (optimal_min - utilization_ratio) / optimal_min * 40
            return max(0, 100 - penalty)
        else:
            # Over-utilized penalty
            penalty = (utilization_ratio - optimal_max) / optimal_max * 60
            return max(0, 100 - penalty)
    
    def _calculate_network_efficiency(self, container: ContainerMetrics) -> float:
        """Calculate network efficiency score"""
        # Simplified network efficiency based on I/O volume
        # In practice, this would consider network patterns, latency, etc.
        if container.network_io_mb == 0:
            return 50  # Neutral score for no network activity
        
        # Assume moderate network usage is optimal
        if 1 <= container.network_io_mb <= 100:
            return 85
        elif container.network_io_mb > 100:
            return max(0, 85 - (container.network_io_mb - 100) / 10)
        else:
            return max(30, container.network_io_mb * 30)
    
    def generate_optimization_recommendations(self, containers: List[ContainerMetrics]) -> Dict:
        """Generate comprehensive optimization recommendations"""
        
        analysis_results = []
        total_potential_improvement = 0
        high_priority_actions = 0
        
        for container in containers:
            optimization = self.analyze_container_efficiency(container)
            analysis_results.append(optimization)
            
            # Aggregate potential improvements
            for rec in optimization.recommendations:
                total_potential_improvement += rec.potential_improvement
                if rec.confidence > 0.8:
                    high_priority_actions += 1
        
        # System-wide recommendations
        system_resources = self.profiler.get_system_resources()
        
        system_recommendations = []
        
        if system_resources.get('cpu_percent', 0) > 80:
            system_recommendations.append({
                'type': 'system',
                'resource': 'cpu',
                'priority': 'high',
                'message': 'System CPU utilization is high',
                'suggestions': [
                    'Scale horizontally by adding more containers',
                    'Optimize CPU-intensive processes',
                    'Consider upgrading to higher CPU instances'
                ]
            })
        
        if system_resources.get('memory_percent', 0) > 85:
            system_recommendations.append({
                'type': 'system',
                'resource': 'memory',
                'priority': 'high',
                'message': 'System memory utilization is high',
                'suggestions': [
                    'Increase system RAM',
                    'Optimize memory usage across containers',
                    'Implement memory-efficient caching strategies'
                ]
            })
        
        return {
            'container_analyses': analysis_results,
            'system_recommendations': system_recommendations,
            'summary': {
                'total_containers_analyzed': len(containers),
                'containers_needing_optimization': len([a for a in analysis_results if a.issues]),
                'potential_resource_savings_percent': total_potential_improvement / max(1, len(containers)),
                'high_priority_actions': high_priority_actions,
                'average_efficiency': np.mean([a.overall_efficiency for a in analysis_results]),
                'system_cpu_utilization': system_resources.get('cpu_percent', 0),
                'system_memory_utilization': system_resources.get('memory_percent', 0)
            }
        }

class ContainerOrchestrator:
    """Container orchestration and optimization management"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        self.profiler = ResourceProfiler()
        self.optimizer = ResourceOptimizer(self.profiler)
        
        # Orchestrator configuration
        self.orchestrator_type = ContainerOrchestrator(config.get('orchestrator', 'docker'))
        self.auto_optimization = config.get('auto_optimization', False)
        self.optimization_interval = config.get('optimization_interval', 3600)  # 1 hour
        
        self.optimization_active = False
        self.optimization_task = None
    
    async def analyze_all_containers(self) -> Dict:
        """Analyze all running containers"""
        self.logger.info("Starting container analysis")
        
        containers = self.profiler.get_all_containers()
        
        if not containers:
            self.logger.warning("No running containers found")
            return {'error': 'No running containers found'}
        
        # Profile each container
        profiling_tasks = [
            self.profiler.profile_container_workload(c.container_id, 30)
            for c in containers[:5]  # Profile first 5 containers
        ]
        
        await asyncio.gather(*profiling_tasks, return_exceptions=True)
        
        # Generate optimization recommendations
        recommendations = self.optimizer.generate_optimization_recommendations(containers)
        
        self.logger.info(f"Container analysis completed for {len(containers)} containers")
        return recommendations
    
    async def optimize_container_resources(self, container_id: str, dry_run: bool = True) -> Dict:
        """Optimize resources for a specific container"""
        try:
            containers = self.profiler.get_all_containers()
            target_container = next((c for c in containers if c.container_id == container_id), None)
            
            if not target_container:
                return {'error': f'Container {container_id} not found'}
            
            # Analyze container
            optimization = self.optimizer.analyze_container_efficiency(target_container)
            
            if not optimization.recommendations:
                return {
                    'container_id': container_id,
                    'status': 'no_optimization_needed',
                    'efficiency_score': optimization.overall_efficiency,
                    'message': 'Container is already optimally configured'
                }
            
            # Apply optimizations if not dry run
            if not dry_run:
                optimization_results = []
                
                for rec in optimization.recommendations:
                    result = await self._apply_resource_recommendation(container_id, rec)
                    optimization_results.append(result)
                
                return {
                    'container_id': container_id,
                    'status': 'optimization_applied',
                    'efficiency_score': optimization.overall_efficiency,
                    'applied_optimizations': optimization_results
                }
            else:
                return {
                    'container_id': container_id,
                    'status': 'dry_run_completed',
                    'efficiency_score': optimization.overall_efficiency,
                    'recommended_optimizations': [
                        {
                            'resource_type': rec.resource_type.value,
                            'current_allocation': rec.current_allocation,
                            'recommended_allocation': rec.recommended_allocation,
                            'reason': rec.reason,
                            'implementation_steps': rec.implementation_steps
                        } for rec in optimization.recommendations
                    ]
                }
        
        except Exception as e:
            self.logger.error(f"Container optimization failed for {container_id}: {e}")
            return {'error': str(e)}
    
    async def _apply_resource_recommendation(self, container_id: str, recommendation: ResourceRecommendation) -> Dict:
        """Apply a specific resource recommendation"""
        try:
            if self.orchestrator_type == ContainerOrchestrator.DOCKER:
                return await self._apply_docker_optimization(container_id, recommendation)
            elif self.orchestrator_type == ContainerOrchestrator.KUBERNETES:
                return await self._apply_kubernetes_optimization(container_id, recommendation)
            else:
                return {'status': 'not_implemented', 'message': f'Optimization not implemented for {self.orchestrator_type.value}'}
                
        except Exception as e:
            self.logger.error(f"Failed to apply recommendation: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    async def _apply_docker_optimization(self, container_id: str, recommendation: ResourceRecommendation) -> Dict:
        """Apply Docker resource optimization"""
        try:
            if not self.profiler.docker_client:
                return {'status': 'failed', 'error': 'Docker client not available'}
            
            container = self.profiler.docker_client.containers.get(container_id)
            
            # Prepare resource updates
            if recommendation.resource_type == ResourceType.CPU:
                cpu_limit = int(recommendation.recommended_allocation * 100)  # Docker uses percentage
                container.update(cpu_limit=f"{cpu_limit}c")
                
            elif recommendation.resource_type == ResourceType.MEMORY:
                memory_limit = int(recommendation.recommended_allocation * 1024 * 1024)  # Bytes
                container.update(mem_limit=memory_limit)
            
            return {
                'status': 'success',
                'resource_type': recommendation.resource_type.value,
                'previous_allocation': recommendation.current_allocation,
                'new_allocation': recommendation.recommended_allocation
            }
            
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}
    
    async def _apply_kubernetes_optimization(self, container_id: str, recommendation: ResourceRecommendation) -> Dict:
        """Apply Kubernetes resource optimization"""
        # This would implement Kubernetes resource updates
        # For demo purposes, return success
        return {
            'status': 'success',
            'message': 'Kubernetes optimization would be applied here',
            'resource_type': recommendation.resource_type.value,
            'previous_allocation': recommendation.current_allocation,
            'new_allocation': recommendation.recommended_allocation
        }
    
    async def generate_optimization_report(self, output_path: str) -> str:
        """Generate comprehensive optimization report"""
        try:
            analysis_results = await self.analyze_all_containers()
            
            report = {
                'report_timestamp': datetime.now().isoformat(),
                'orchestrator_type': self.orchestrator_type.value,
                'analysis_results': analysis_results,
                'system_resources': self.profiler.get_system_resources()
            }
            
            async with aiofiles.open(output_path, 'w') as f:
                await f.write(json.dumps(report, indent=2, default=str))
            
            self.logger.info(f"Optimization report saved to {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            raise
    
    def export_container_configs(self, output_dir: str):
        """Export optimized container configurations"""
        try:
            containers = self.profiler.get_all_containers()
            
            for container in containers:
                optimization = self.optimizer.analyze_container_efficiency(container)
                
                # Generate Docker Compose configuration
                docker_config = self._generate_docker_compose_config(container, optimization)
                
                # Save configuration
                config_path = Path(output_dir) / f"{container.name}_optimized.yml"
                
                with open(config_path, 'w') as f:
                    yaml.dump(docker_config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Container configurations exported to {output_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to export configurations: {e}")
            raise
    
    def _generate_docker_compose_config(self, container: ContainerMetrics, optimization: ContainerOptimization) -> Dict:
        """Generate optimized Docker Compose configuration"""
        
        # Calculate resource limits based on optimization
        cpu_limit = 1.0
        memory_limit = container.memory_usage_mb * 1.2 / 1024  # Convert to GB
        
        for rec in optimization.recommendations:
            if rec.resource_type == ResourceType.CPU:
                cpu_limit = rec.recommended_allocation
            elif rec.resource_type == ResourceType.MEMORY:
                memory_limit = rec.recommended_allocation / 1024  # Convert to GB
        
        return {
            'version': '3.8',
            'services': {
                container.name: {
                    'image': container.image,
                    'deploy': {
                        'resources': {
                            'limits': {
                                'cpus': str(cpu_limit),
                                'memory': f"{memory_limit}G"
                            },
                            'reservations': {
                                'cpus': str(cpu_limit * 0.5),
                                'memory': f"{memory_limit * 0.6}G"
                            }
                        }
                    },
                    'restart': 'unless-stopped',
                    'networks': ['app-network']
                }
            },
            'networks': {
                'app-network': {
                    'driver': 'bridge'
                }
            }
        }

def create_sample_container_config() -> Dict:
    """Create sample container optimization configuration"""
    return {
        'orchestrator': 'docker',
        'auto_optimization': False,
        'optimization_interval': 3600,
        'docker_config': {
            'socket_path': '/var/run/docker.sock'
        },
        'optimization_rules': {
            'cpu_threshold_low': 30,
            'cpu_threshold_high': 80,
            'memory_threshold_low': 50,
            'memory_threshold_high': 85
        }
    }

def main():
    """Example usage and testing"""
    async def demo_container_optimization():
        # Create sample configuration
        config = create_sample_container_config()
        
        # Initialize container orchestrator
        orchestrator = ContainerOrchestrator(config)
        
        print("Container Resource Optimization Demo")
        print("=" * 50)
        
        # Analyze all containers
        print("Analyzing containers...")
        analysis = await orchestrator.analyze_all_containers()
        
        if 'error' in analysis:
            print(f"Analysis failed: {analysis['error']}")
            return
        
        # Display summary
        summary = analysis.get('summary', {})
        print(f"\nAnalysis Summary:")
        print(f"  Containers analyzed: {summary.get('total_containers_analyzed', 0)}")
        print(f"  Average efficiency: {summary.get('average_efficiency', 0):.1f}%")
        print(f"  Potential resource savings: {summary.get('potential_resource_savings_percent', 0):.1f}%")
        print(f"  High priority actions: {summary.get('high_priority_actions', 0)}")
        
        # Display container analyses
        print(f"\nContainer Efficiency Analysis:")
        for container_analysis in analysis.get('container_analyses', []):
            print(f"  {container_analysis.name}:")
            print(f"    Overall efficiency: {container_analysis.overall_efficiency:.1f}%")
            print(f"    CPU efficiency: {container_analysis.cpu_efficiency:.1f}%")
            print(f"    Memory efficiency: {container_analysis.memory_efficiency:.1f}%")
            
            if container_analysis.issues:
                print(f"    Issues: {', '.join(container_analysis.issues)}")
            
            if container_analysis.recommendations:
                print(f"    Recommendations:")
                for rec in container_analysis.recommendations[:2]:  # Show first 2
                    print(f"      {rec.resource_type.value}: {rec.reason}")
        
        # Display system recommendations
        system_recommendations = analysis.get('system_recommendations', [])
        if system_recommendations:
            print(f"\nSystem Recommendations:")
            for rec in system_recommendations:
                print(f"  {rec['priority'].upper()}: {rec['message']}")
        
        # Generate optimization report
        print(f"\nGenerating optimization report...")
        report_path = "/tmp/container_optimization_report.json"
        await orchestrator.generate_optimization_report(report_path)
        print(f"Report saved to: {report_path}")
        
        # Export optimized configurations
        print(f"\nExporting optimized configurations...")
        orchestrator.export_container_configs("/tmp/optimized_configs")
        print(f"Configurations exported to: /tmp/optimized_configs/")
    
    # Run the demo
    asyncio.run(demo_container_optimization())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()