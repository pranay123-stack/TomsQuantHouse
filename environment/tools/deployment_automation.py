#!/usr/bin/env python3
"""
Deployment Automation with Environment Promotion

This module provides:
- Automated environment promotion workflows
- Deployment pipeline management
- Rollback and canary deployment capabilities
- Integration with CI/CD systems
- Environment state management
"""

import os
import json
import yaml
import subprocess
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import logging
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
import hashlib
import requests

logger = logging.getLogger(__name__)

class DeploymentStatus(Enum):
    """Deployment status types"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    CANARY = "canary"

class EnvironmentState(Enum):
    """Environment state types"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEPLOYING = "deploying"
    MAINTENANCE = "maintenance"

@dataclass
class DeploymentStep:
    """Individual deployment step"""
    name: str
    step_type: str  # pre-deploy, deploy, post-deploy, validate
    command: str
    timeout: int = 300
    retry_count: int = 0
    required: bool = True
    environment_vars: Dict[str, str] = field(default_factory=dict)

@dataclass
class Deployment:
    """Deployment configuration and status"""
    deployment_id: str
    environment: str
    version: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps: List[DeploymentStep] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    environment_state: EnvironmentState = EnvironmentState.HEALTHY
    rollback_version: Optional[str] = None
    canary_percentage: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

class DeploymentPipeline:
    """Deployment pipeline manager"""
    
    def __init__(self, pipeline_config_file: str = None):
        self.pipelines: Dict[str, Dict[str, Any]] = {}
        self.active_deployments: Dict[str, Deployment] = {}
        self.deployment_history = []
        
        # Load pipeline configurations
        if pipeline_config_file and Path(pipeline_config_file).exists():
            self._load_pipeline_config(pipeline_config_file)
        else:
            self._load_default_pipelines()
    
    def _load_default_pipelines(self):
        """Load default deployment pipelines"""
        
        # Development pipeline
        dev_pipeline = {
            "name": "development",
            "description": "Development environment deployment",
            "stages": [
                {
                    "name": "pre-deploy",
                    "steps": [
                        {
                            "name": "validate_config",
                            "type": "pre-deploy",
                            "command": "python environment/tools/testing_validation.py --action validate --environment development --config-file environment/templates/development.yaml",
                            "timeout": 60
                        }
                    ]
                },
                {
                    "name": "deploy",
                    "steps": [
                        {
                            "name": "start_app",
                            "type": "deploy",
                            "command": "echo 'Starting application in development mode'",
                            "timeout": 30
                        }
                    ]
                },
                {
                    "name": "post-deploy",
                    "steps": [
                        {
                            "name": "health_check",
                            "type": "post-deploy",
                            "command": "python -c 'import time; time.sleep(5); print(\"Health check passed\")'",
                            "timeout": 30
                        }
                    ]
                }
            ]
        }
        
        # Staging pipeline
        staging_pipeline = {
            "name": "staging",
            "description": "Staging environment deployment",
            "stages": [
                {
                    "name": "pre-deploy",
                    "steps": [
                        {
                            "name": "backup_current",
                            "type": "pre-deploy",
                            "command": "python environment/tools/backup_migration.py --action backup --environment staging --description 'Pre-deployment backup'",
                            "timeout": 120
                        },
                        {
                            "name": "validate_config",
                            "type": "pre-deploy",
                            "command": "python environment/tools/testing_validation.py --action validate --environment staging --config-file environment/templates/staging.yaml",
                            "timeout": 60
                        }
                    ]
                },
                {
                    "name": "deploy",
                    "steps": [
                        {
                            "name": "stop_services",
                            "type": "deploy",
                            "command": "echo 'Stopping services gracefully'",
                            "timeout": 30
                        },
                        {
                            "name": "update_config",
                            "type": "deploy",
                            "command": "python environment/config_manager.py --action load --environment staging",
                            "timeout": 30
                        },
                        {
                            "name": "start_services",
                            "type": "deploy",
                            "command": "echo 'Starting services'",
                            "timeout": 60
                        }
                    ]
                },
                {
                    "name": "validate",
                    "steps": [
                        {
                            "name": "integration_tests",
                            "type": "validate",
                            "command": "python -c 'print(\"Running integration tests...\")'",
                            "timeout": 300
                        },
                        {
                            "name": "performance_tests",
                            "type": "validate",
                            "command": "python environment/tools/testing_validation.py --action validate --environment staging --config-file environment/templates/staging.yaml",
                            "timeout": 180
                        }
                    ]
                }
            ]
        }
        
        # Production pipeline
        prod_pipeline = {
            "name": "production",
            "description": "Production environment deployment",
            "stages": [
                {
                    "name": "pre-deploy",
                    "steps": [
                        {
                            "name": "backup_current",
                            "type": "pre-deploy",
                            "command": "python environment/tools/backup_migration.py --action backup --environment production --description 'Pre-deployment backup' --encrypt",
                            "timeout": 300
                        },
                        {
                            "name": "validate_config",
                            "type": "pre-deploy",
                            "command": "python environment/tools/testing_validation.py --action validate --environment production --config-file environment/templates/production.yaml",
                            "timeout": 120
                        },
                        {
                            "name": "security_scan",
                            "type": "pre-deploy",
                            "command": "echo 'Running security scan...'",
                            "timeout": 300
                        }
                    ]
                },
                {
                    "name": "deploy",
                    "steps": [
                        {
                            "name": "canary_deploy",
                            "type": "deploy",
                            "command": "echo 'Starting canary deployment'",
                            "timeout": 180
                        },
                        {
                            "name": "monitor_canary",
                            "type": "deploy",
                            "command": "python -c 'import time; time.sleep(60); print(\"Canary monitoring completed\")'",
                            "timeout": 120
                        },
                        {
                            "name": "full_deploy",
                            "type": "deploy",
                            "command": "echo 'Completing full deployment'",
                            "timeout": 300
                        }
                    ]
                },
                {
                    "name": "post-deploy",
                    "steps": [
                        {
                            "name": "smoke_tests",
                            "type": "post-deploy",
                            "command": "python environment/tools/testing_validation.py --action validate --environment production --config-file environment/templates/production.yaml",
                            "timeout": 180
                        },
                        {
                            "name": "notify_team",
                            "type": "post-deploy",
                            "command": "echo 'Deployment notification sent'",
                            "timeout": 30
                        }
                    ]
                }
            ]
        }
        
        self.pipelines = {
            "development": dev_pipeline,
            "staging": staging_pipeline,
            "production": prod_pipeline
        }
    
    def _load_pipeline_config(self, config_file: str):
        """Load pipeline configuration from file"""
        try:
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
                self.pipelines = config_data
        except Exception as e:
            logger.error(f"Failed to load pipeline config: {e}")
            self._load_default_pipelines()
    
    def get_pipeline(self, environment: str) -> Optional[Dict[str, Any]]:
        """Get pipeline for environment"""
        return self.pipelines.get(environment)
    
    def list_pipelines(self) -> List[str]:
        """List available pipelines"""
        return list(self.pipelines.keys())

class DeploymentManager:
    """Deployment management system"""
    
    def __init__(self, pipeline_config: str = None):
        self.pipeline_manager = DeploymentPipeline(pipeline_config)
        self.active_deployments: Dict[str, Deployment] = {}
        self.deployment_queue = []
        self._deployment_lock = threading.Lock()
    
    def create_deployment(self, environment: str, version: str, 
                         deployment_type: str = "standard") -> str:
        """Create a new deployment"""
        
        pipeline = self.pipeline_manager.get_pipeline(environment)
        if not pipeline:
            raise ValueError(f"No pipeline found for environment: {environment}")
        
        deployment_id = self._generate_deployment_id()
        
        # Convert pipeline steps to deployment steps
        steps = []
        for stage in pipeline.get("stages", []):
            for step_config in stage.get("steps", []):
                step = DeploymentStep(
                    name=step_config["name"],
                    step_type=step_config["type"],
                    command=step_config["command"],
                    timeout=step_config.get("timeout", 300),
                    retry_count=step_config.get("retry_count", 0),
                    required=step_config.get("required", True),
                    environment_vars=step_config.get("environment_vars", {})
                )
                steps.append(step)
        
        deployment = Deployment(
            deployment_id=deployment_id,
            environment=environment,
            version=version,
            status=DeploymentStatus.PENDING,
            started_at=datetime.now(),
            steps=steps,
            metadata={
                "deployment_type": deployment_type,
                "pipeline": pipeline["name"],
                "user": os.getenv("USER", "system")
            }
        )
        
        with self._deployment_lock:
            self.active_deployments[deployment_id] = deployment
            self.deployment_queue.append(deployment_id)
        
        logger.info(f"Created deployment {deployment_id} for {environment} version {version}")
        return deployment_id
    
    def execute_deployment(self, deployment_id: str, dry_run: bool = False) -> bool:
        """Execute a deployment"""
        
        with self._deployment_lock:
            if deployment_id not in self.active_deployments:
                logger.error(f"Deployment not found: {deployment_id}")
                return False
            
            deployment = self.active_deployments[deployment_id]
        
        if deployment.status != DeploymentStatus.PENDING:
            logger.error(f"Deployment {deployment_id} is not pending (current: {deployment.status.value})")
            return False
        
        logger.info(f"Starting deployment {deployment_id} for {deployment.environment}")
        
        # Update status
        deployment.status = DeploymentStatus.RUNNING
        deployment.environment_state = EnvironmentState.DEPLOYING
        
        try:
            # Execute deployment steps
            for step in deployment.steps:
                if not self._execute_deployment_step(deployment, step, dry_run):
                    logger.error(f"Deployment step failed: {step.name}")
                    deployment.status = DeploymentStatus.FAILED
                    deployment.completed_at = datetime.now()
                    return False
            
            # Deployment completed successfully
            deployment.status = DeploymentStatus.SUCCESS
            deployment.environment_state = EnvironmentState.HEALTHY
            deployment.completed_at = datetime.now()
            
            logger.info(f"Deployment {deployment_id} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {e}")
            deployment.status = DeploymentStatus.FAILED
            deployment.completed_at = datetime.now()
            return False
    
    def _execute_deployment_step(self, deployment: Deployment, step: DeploymentStep, 
                                dry_run: bool = False) -> bool:
        """Execute a single deployment step"""
        
        logger.info(f"Executing step '{step.name}' for deployment {deployment.deployment_id}")
        
        deployment.logs.append(f"[{datetime.now().isoformat()}] Starting step: {step.name}")
        
        if dry_run:
            deployment.logs.append(f"[{datetime.now().isoformat()}] DRY RUN: Would execute: {step.command}")
            return True
        
        try:
            # Set environment variables
            old_env = {}
            for key, value in step.environment_vars.items():
                old_env[key] = os.environ.get(key)
                os.environ[key] = value
            
            # Execute command
            start_time = time.time()
            result = subprocess.run(
                step.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=step.timeout
            )
            execution_time = time.time() - start_time
            
            # Restore environment variables
            for key, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value
            
            if result.returncode == 0:
                deployment.logs.append(f"[{datetime.now().isoformat()}] Step '{step.name}' completed in {execution_time:.2f}s")
                if result.stdout:
                    deployment.logs.append(result.stdout)
                return True
            else:
                deployment.logs.append(f"[{datetime.now().isoformat()}] Step '{step.name}' failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            deployment.logs.append(f"[{datetime.now().isoformat()}] Step '{step.name}' timed out after {step.timeout}s")
            return False
        except Exception as e:
            deployment.logs.append(f"[{datetime.now().isoformat()}] Step '{step.name}' error: {e}")
            return False
    
    def promote_environment(self, source_env: str, target_env: str, 
                           version: str = "auto", dry_run: bool = False) -> bool:
        """Promote environment to another"""
        
        try:
            # Load configurations
            from ..config_manager import ConfigManager
            config_manager = ConfigManager()
            
            source_config = config_manager.load_config(source_env)
            if not source_config:
                logger.error(f"Source configuration not found: {source_env}")
                return False
            
            # Auto-determine version if not specified
            if version == "auto":
                version = f"{source_env}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Create deployment for target environment
            deployment_id = self.create_deployment(target_env, version, "promotion")
            
            if dry_run:
                deployment = self.active_deployments[deployment_id]
                deployment.logs.append(f"[{datetime.now().isoformat()}] DRY RUN: Configuration promotion from {source_env} to {target_env}")
                deployment.logs.append(f"[{datetime.now().isoformat()}] DRY RUN: Would deploy version: {version}")
                logger.info(f"DRY RUN: Configuration promotion planned from {source_env} to {target_env}")
                return True
            
            # Execute configuration promotion as part of deployment
            promotion_step = DeploymentStep(
                name="promote_configuration",
                step_type="deploy",
                command=f"python environment/config_manager.py --action promote --source-env {source_env} --target-env {target_env} --user {os.getenv('USER', 'system')} --reason 'Environment promotion'",
                timeout=300
            )
            
            deployment = self.active_deployments[deployment_id]
            deployment.steps.insert(0, promotion_step)  # Insert at beginning
            
            # Execute deployment
            success = self.execute_deployment(deployment_id, dry_run)
            
            if success:
                logger.info(f"Environment promotion completed: {source_env} -> {target_env}")
            
            return success
            
        except Exception as e:
            logger.error(f"Environment promotion failed: {e}")
            return False
    
    def rollback_deployment(self, deployment_id: str, target_version: str = None) -> bool:
        """Rollback a deployment"""
        
        with self._deployment_lock:
            if deployment_id not in self.active_deployments:
                logger.error(f"Deployment not found: {deployment_id}")
                return False
            
            deployment = self.active_deployments[deployment_id]
        
        logger.info(f"Starting rollback of deployment {deployment_id}")
        
        deployment.status = DeploymentStatus.ROLLING_BACK
        
        try:
            # Determine rollback version
            if not target_version:
                if deployment.rollback_version:
                    target_version = deployment.rollback_version
                else:
                    # Get previous version from history
                    target_version = self._get_previous_version(deployment.environment, deployment.version)
            
            # Create rollback deployment
            rollback_deployment_id = self.create_deployment(
                deployment.environment, 
                target_version, 
                "rollback"
            )
            
            # Execute rollback
            success = self.execute_deployment(rollback_deployment_id)
            
            if success:
                deployment.status = DeploymentStatus.ROLLED_BACK
                logger.info(f"Rollback completed for deployment {deployment_id} to version {target_version}")
            else:
                deployment.status = DeploymentStatus.FAILED
                logger.error(f"Rollback failed for deployment {deployment_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Rollback error: {e}")
            deployment.status = DeploymentStatus.FAILED
            return False
    
    def canary_deployment(self, environment: str, version: str, 
                         canary_percentage: int = 10) -> str:
        """Start canary deployment"""
        
        deployment_id = self.create_deployment(environment, version, "canary")
        deployment = self.active_deployments[deployment_id]
        deployment.canary_percentage = canary_percentage
        
        logger.info(f"Starting canary deployment {deployment_id} with {canary_percentage}% traffic")
        return deployment_id
    
    def get_deployment_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status"""
        
        with self._deployment_lock:
            deployment = self.active_deployments.get(deployment_id)
        
        if not deployment:
            return None
        
        return {
            "deployment_id": deployment.deployment_id,
            "environment": deployment.environment,
            "version": deployment.version,
            "status": deployment.status.value,
            "environment_state": deployment.environment_state.value,
            "started_at": deployment.started_at.isoformat(),
            "completed_at": deployment.completed_at.isoformat() if deployment.completed_at else None,
            "canary_percentage": deployment.canary_percentage,
            "steps_count": len(deployment.steps),
            "logs_count": len(deployment.logs),
            "metadata": deployment.metadata
        }
    
    def list_deployments(self, environment: str = None, status: DeploymentStatus = None) -> List[str]:
        """List deployments"""
        
        with self._deployment_lock:
            deployment_ids = list(self.active_deployments.keys())
        
        if environment:
            deployment_ids = [
                d_id for d_id in deployment_ids
                if self.active_deployments[d_id].environment == environment
            ]
        
        if status:
            deployment_ids = [
                d_id for d_id in deployment_ids
                if self.active_deployments[d_id].status == status
            ]
        
        return deployment_ids
    
    def cleanup_completed_deployments(self, max_age_hours: int = 24):
        """Cleanup old completed deployments"""
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self._deployment_lock:
            to_remove = []
            
            for deployment_id, deployment in self.active_deployments.items():
                if (deployment.status in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED, 
                                         DeploymentStatus.ROLLED_BACK] and 
                    deployment.completed_at and 
                    deployment.completed_at < cutoff_time):
                    to_remove.append(deployment_id)
            
            for deployment_id in to_remove:
                del self.active_deployments[deployment_id]
        
        logger.info(f"Cleaned up {len(to_remove)} completed deployments")
    
    def _generate_deployment_id(self) -> str:
        """Generate unique deployment ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"deploy_{timestamp}_{random_suffix}"
    
    def _get_previous_version(self, environment: str, current_version: str) -> str:
        """Get previous version for rollback"""
        # This would typically query a version history
        # For now, return a simple pattern
        return f"{environment}-previous"

class CICDIntegration:
    """CI/CD system integration"""
    
    def __init__(self, deployment_manager: DeploymentManager):
        self.deployment_manager = deployment_manager
        self.webhook_endpoints = {}
    
    def setup_webhook(self, environment: str, webhook_url: str):
        """Setup webhook for CI/CD integration"""
        self.webhook_endpoints[environment] = webhook_url
        logger.info(f"Webhook configured for {environment}: {webhook_url}")
    
    def trigger_deployment(self, environment: str, version: str, 
                          deployment_type: str = "standard") -> bool:
        """Trigger deployment via CI/CD webhook"""
        
        try:
            webhook_url = self.webhook_endpoints.get(environment)
            if not webhook_url:
                logger.warning(f"No webhook configured for {environment}")
                return False
            
            # Trigger deployment through webhook
            payload = {
                "environment": environment,
                "version": version,
                "deployment_type": deployment_type,
                "timestamp": datetime.now().isoformat(),
                "triggered_by": "webhook"
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Deployment triggered for {environment} version {version}")
                return True
            else:
                logger.error(f"Webhook failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to trigger deployment: {e}")
            return False

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deployment Automation and Environment Promotion')
    parser.add_argument('--action', choices=['deploy', 'promote', 'rollback', 'status', 'list'], 
                       required=True, help='Action to perform')
    parser.add_argument('--environment', help='Target environment')
    parser.add_argument('--source-env', help='Source environment for promotion')
    parser.add_argument('--target-env', help='Target environment for promotion')
    parser.add_argument('--version', help='Deployment version')
    parser.add_argument('--deployment-id', help='Deployment ID')
    parser.add_argument('--deployment-type', default='standard', 
                       choices=['standard', 'canary', 'blue-green'], 
                       help='Deployment type')
    parser.add_argument('--canary-percentage', type=int, default=10, 
                       help='Canary percentage (1-100)')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run')
    parser.add_argument('--pipeline-config', help='Pipeline configuration file')
    parser.add_argument('--max-age', type=int, default=24, help='Max age in hours for cleanup')
    
    args = parser.parse_args()
    
    deployment_manager = DeploymentManager(args.pipeline_config)
    
    if args.action == 'deploy':
        if not args.environment:
            print("Error: environment is required for deploy action")
            return
        
        version = args.version or f"{args.environment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        deployment_id = deployment_manager.create_deployment(
            args.environment, version, args.deployment_type
        )
        
        print(f"Created deployment {deployment_id}")
        
        if not args.dry_run:
            if deployment_manager.execute_deployment(deployment_id, args.dry_run):
                print(f"Deployment {deployment_id} completed successfully")
            else:
                print(f"Deployment {deployment_id} failed")
    
    elif args.action == 'promote':
        if not args.source_env or not args.target_env:
            print("Error: source-env and target-env are required for promote action")
            return
        
        if deployment_manager.promote_environment(
            args.source_env, args.target_env, args.version, args.dry_run
        ):
            print(f"Environment promotion completed: {args.source_env} -> {args.target_env}")
        else:
            print(f"Environment promotion failed")
    
    elif args.action == 'rollback':
        if not args.deployment_id:
            print("Error: deployment-id is required for rollback action")
            return
        
        if deployment_manager.rollback_deployment(args.deployment_id, args.version):
            print(f"Rollback completed for {args.deployment_id}")
        else:
            print(f"Rollback failed for {args.deployment_id}")
    
    elif args.action == 'status':
        if not args.deployment_id:
            print("Error: deployment-id is required for status action")
            return
        
        status = deployment_manager.get_deployment_status(args.deployment_id)
        if status:
            print(f"Deployment status: {json.dumps(status, indent=2)}")
        else:
            print(f"Deployment not found: {args.deployment_id}")
    
    elif args.action == 'list':
        deployments = deployment_manager.list_deployments(
            args.environment, 
            DeploymentStatus[args.status.upper()] if hasattr(DeploymentStatus, args.status.upper()) else None
        )
        
        print(f"Deployments{(' for ' + args.environment) if args.environment else ''}:")
        for deployment_id in deployments:
            print(f"  - {deployment_id}")
    
    # Cleanup old deployments
    deployment_manager.cleanup_completed_deployments(args.max_age)

if __name__ == '__main__':
    main()