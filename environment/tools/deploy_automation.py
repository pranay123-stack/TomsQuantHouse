#!/usr/bin/env python3
"""
Environment Management System - Main Deployment Automation
Orchestrates all environment management components for automated deployments
"""

import os
import sys
import json
import yaml
import logging
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Import all our environment management tools
sys.path.append(str(Path(__file__).parent / "tools"))

from secrets_manager import SecretsManager
from secure_credentials import CredentialManager
from env_validator import EnvironmentValidator
from config_backup_migration import ConfigurationBackup, ConfigurationMigrator
from env_tester import EnvironmentTester
from change_tracker import ConfigurationChangeTracker

class DeploymentStatus(Enum):
    """Deployment status tracking"""
    PLANNING = "planning"
    VALIDATING = "validating"
    BACKING_UP = "backing_up"
    MIGRATING = "migrating"
    TESTING = "testing"
    DEPLOYING = "deploying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class DeploymentType(Enum):
    """Types of deployments"""
    INITIAL = "initial"
    UPDATE = "update"
    ROLLBACK = "rollback"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"

@dataclass
class DeploymentPlan:
    """Deployment plan definition"""
    id: str
    name: str
    source_environment: str
    target_environment: str
    deployment_type: DeploymentType
    description: str
    configuration_changes: List[Dict[str, Any]]
    secrets_updates: List[Dict[str, Any]]
    validation_requirements: List[str]
    testing_suites: List[str]
    rollback_procedures: List[Dict[str, Any]]
    approval_required: bool
    created_at: str
    created_by: str
    scheduled_at: Optional[str] = None

@dataclass
class DeploymentExecution:
    """Deployment execution tracking"""
    plan_id: str
    execution_id: str
    status: DeploymentStatus
    started_at: str
    completed_at: Optional[str] = None
    current_step: Optional[str] = None
    total_steps: int = 0
    completed_steps: int = 0
    steps: List[Dict[str, Any]] = None
    results: Dict[str, Any] = None
    errors: List[str] = None
    warnings: List[str] = None
    logs: List[str] = None

@dataclass
class EnvironmentState:
    """Current state of an environment"""
    name: str
    configuration_version: str
    secrets_version: str
    test_results: Dict[str, Any]
    last_updated: str
    health_status: str
    deployment_history: List[str]

class DeploymentOrchestrator:
    """Main deployment orchestration system"""
    
    def __init__(self, base_dir: str = "environment"):
        self.base_dir = Path(base_dir)
        self.config_dir = self.base_dir / "config"
        self.deployments_dir = self.base_dir / "deployments"
        self.plans_dir = self.deployments_dir / "plans"
        self.executions_dir = self.deployments_dir / "executions"
        
        # Create directories
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        self.executions_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize all management components
        self.secrets_manager = SecretsManager()
        self.credential_manager = CredentialManager(self.base_dir / "secure_credentials")
        self.validator = EnvironmentValidator(str(self.config_dir / "environments.yaml"))
        self.backup_system = ConfigurationBackup(str(self.base_dir / "backup"))
        self.migrator = ConfigurationMigrator(self.backup_system)
        self.tester = EnvironmentTester(str(self.base_dir / "testing"))
        self.change_tracker = ConfigurationChangeTracker(str(self.base_dir / "audit"))
        
        # Setup logging
        self.logger = logging.getLogger('deployment_orchestrator')
        self._setup_logging()
        
        # Load deployment plans
        self.deployment_plans = self._load_deployment_plans()
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Main deployment log
        main_handler = logging.FileHandler(log_dir / 'deployment_main.log')
        main_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        
        # Detailed deployment log
        detail_handler = logging.FileHandler(log_dir / 'deployment_detail.log')
        detail_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        detail_handler.setFormatter(detail_formatter)
        
        self.logger.addHandler(main_handler)
        self.logger.addHandler(detail_handler)
        self.logger.setLevel(logging.INFO)
    
    def _load_deployment_plans(self) -> Dict[str, DeploymentPlan]:
        """Load all deployment plans"""
        plans = {}
        
        # Load from files
        for plan_file in self.plans_dir.glob("*.yaml"):
            try:
                with open(plan_file, 'r') as f:
                    data = yaml.safe_load(f)
                
                # Convert enums
                data['deployment_type'] = DeploymentType(data['deployment_type'])
                
                plan = DeploymentPlan(**data)
                plans[plan.id] = plan
                
            except Exception as e:
                self.logger.error(f"Failed to load deployment plan {plan_file}: {e}")
        
        return plans
    
    def create_deployment_plan(self, name: str, source_env: str, target_env: str,
                             deployment_type: DeploymentType = DeploymentType.UPDATE,
                             description: str = "", created_by: str = "system",
                             config_changes: List[Dict[str, Any]] = None,
                             secrets_updates: List[Dict[str, Any]] = None,
                             testing_suites: List[str] = None) -> str:
        """Create a new deployment plan"""
        
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Default configuration changes
        default_config_changes = [
            {
                "type": "environment_validation",
                "description": "Validate target environment configuration",
                "required": True
            },
            {
                "type": "secrets_verification",
                "description": "Verify all required secrets are available",
                "required": True
            },
            {
                "type": "backup_creation",
                "description": "Create backup of current configuration",
                "required": True
            }
        ]
        
        # Default secrets updates
        default_secrets_updates = [
            {
                "action": "validate",
                "description": "Validate secret accessibility",
                "required": True
            }
        ]
        
        # Default validation requirements
        validation_requirements = [
            "required_env_vars",
            "config_file_valid",
            "secrets_accessible",
            "connectivity_test"
        ]
        
        # Default testing suites
        default_testing_suites = [
            "config_validation",
            "security_validation",
            "connectivity_validation"
        ]
        
        # Default rollback procedures
        rollback_procedures = [
            {
                "step": 1,
                "action": "restore_backup",
                "description": "Restore from pre-deployment backup",
                "required": True
            },
            {
                "step": 2,
                "action": "validate_restore",
                "description": "Validate restoration",
                "required": True
            }
        ]
        
        plan = DeploymentPlan(
            id=plan_id,
            name=name,
            source_environment=source_env,
            target_environment=target_env,
            deployment_type=deployment_type,
            description=description,
            configuration_changes=config_changes or default_config_changes,
            secrets_updates=secrets_updates or default_secrets_updates,
            validation_requirements=validation_requirements,
            testing_suites=testing_suites or default_testing_suites,
            rollback_procedures=rollback_procedures,
            approval_required=deployment_type in [DeploymentType.PRODUCTION, DeploymentType.CANARY],
            created_at=datetime.now().isoformat(),
            created_by=created_by
        )
        
        # Save plan
        self._save_deployment_plan(plan)
        self.deployment_plans[plan_id] = plan
        
        self.logger.info(f"Deployment plan created: {plan_id}")
        return plan_id
    
    def execute_deployment(self, plan_id: str, 
                          auto_approve: bool = False) -> DeploymentExecution:
        """Execute a deployment plan"""
        
        if plan_id not in self.deployment_plans:
            raise ValueError(f"Deployment plan not found: {plan_id}")
        
        plan = self.deployment_plans[plan_id]
        
        # Create execution record
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        execution = DeploymentExecution(
            plan_id=plan_id,
            execution_id=execution_id,
            status=DeploymentStatus.PLANNING,
            started_at=datetime.now().isoformat(),
            total_steps=len(self._get_deployment_steps(plan)),
            completed_steps=0,
            steps=[],
            results={},
            errors=[],
            warnings=[],
            logs=[]
        )
        
        try:
            # Start change tracking
            self.change_tracker.record_audit_event(
                event_type="deployment_start",
                user_id="system",
                user_name="Deployment System",
                action="execute_deployment",
                resource=plan_id,
                details={"execution_id": execution_id, "plan_name": plan.name},
                result="started"
            )
            
            # Execute deployment steps
            self._execute_deployment_steps(plan, execution)
            
            # Mark as completed
            execution.status = DeploymentStatus.COMPLETED
            execution.completed_at = datetime.now().isoformat()
            
            self.logger.info(f"Deployment completed: {execution_id}")
            
        except Exception as e:
            execution.status = DeploymentStatus.FAILED
            execution.errors.append(str(e))
            execution.completed_at = datetime.now().isoformat()
            
            self.logger.error(f"Deployment failed: {execution_id} - {e}")
            
            # Attempt rollback
            try:
                self._execute_rollback(plan, execution)
            except Exception as rollback_error:
                self.logger.error(f"Rollback failed: {rollback_error}")
        
        # Save execution record
        self._save_deployment_execution(execution)
        
        return execution
    
    def _get_deployment_steps(self, plan: DeploymentPlan) -> List[Dict[str, Any]]:
        """Get ordered list of deployment steps"""
        steps = []
        
        # Planning phase
        steps.append({
            "phase": "planning",
            "step": 1,
            "action": "validate_plan",
            "description": "Validate deployment plan",
            "required": True
        })
        
        # Validation phase
        steps.append({
            "phase": "validating",
            "step": 2,
            "action": "validate_source_environment",
            "description": "Validate source environment",
            "required": True
        })
        
        steps.append({
            "phase": "validating",
            "step": 3,
            "action": "validate_target_environment",
            "description": "Validate target environment",
            "required": True
        })
        
        # Backup phase
        steps.append({
            "phase": "backing_up",
            "step": 4,
            "action": "create_backup",
            "description": "Create configuration backup",
            "required": True
        })
        
        # Migration phase
        steps.append({
            "phase": "migrating",
            "step": 5,
            "action": "migrate_configuration",
            "description": "Migrate configuration",
            "required": True
        })
        
        steps.append({
            "phase": "migrating",
            "step": 6,
            "action": "update_secrets",
            "description": "Update secrets if needed",
            "required": False
        })
        
        # Testing phase
        steps.append({
            "phase": "testing",
            "step": 7,
            "action": "run_test_suites",
            "description": "Run validation tests",
            "required": True
        })
        
        # Deployment phase
        steps.append({
            "phase": "deploying",
            "step": 8,
            "action": "apply_changes",
            "description": "Apply configuration changes",
            "required": True
        })
        
        # Verification phase
        steps.append({
            "phase": "verifying",
            "step": 9,
            "action": "verify_deployment",
            "description": "Verify deployment success",
            "required": True
        })
        
        return steps
    
    def _execute_deployment_steps(self, plan: DeploymentPlan, execution: DeploymentExecution):
        """Execute deployment steps"""
        
        steps = self._get_deployment_steps(plan)
        
        for step in steps:
            try:
                execution.current_step = step["action"]
                execution.status = DeploymentStatus(step["phase"].upper())
                
                self.logger.info(f"Executing step: {step['action']}")
                
                # Execute step
                step_result = self._execute_step(step, plan, execution)
                
                # Update execution
                execution.steps.append({
                    "step": step["step"],
                    "action": step["action"],
                    "description": step["description"],
                    "status": "completed",
                    "result": step_result,
                    "timestamp": datetime.now().isoformat()
                })
                
                execution.completed_steps += 1
                
                # Record in change tracker
                self.change_tracker.record_audit_event(
                    event_type="deployment_step",
                    user_id="system",
                    user_name="Deployment System",
                    action=step["action"],
                    resource=execution.execution_id,
                    details={"step": step["step"], "result": step_result},
                    result="completed"
                )
                
            except Exception as e:
                error_msg = f"Step {step['action']} failed: {str(e)}"
                execution.errors.append(error_msg)
                
                execution.steps.append({
                    "step": step["step"],
                    "action": step["action"],
                    "description": step["description"],
                    "status": "failed",
                    "error": error_msg,
                    "timestamp": datetime.now().isoformat()
                })
                
                self.logger.error(error_msg)
                
                if step["required"]:
                    raise
                
                execution.warnings.append(error_msg)
    
    def _execute_step(self, step: Dict[str, Any], plan: DeploymentPlan,
                     execution: DeploymentExecution) -> Dict[str, Any]:
        """Execute a single deployment step"""
        
        action = step["action"]
        
        if action == "validate_plan":
            return self._validate_deployment_plan(plan)
        
        elif action == "validate_source_environment":
            return self._validate_environment(plan.source_environment)
        
        elif action == "validate_target_environment":
            return self._validate_environment(plan.target_environment)
        
        elif action == "create_backup":
            return self._create_deployment_backup(plan, execution)
        
        elif action == "migrate_configuration":
            return self._migrate_configuration(plan, execution)
        
        elif action == "update_secrets":
            return self._update_secrets(plan, execution)
        
        elif action == "run_test_suites":
            return self._run_deployment_tests(plan, execution)
        
        elif action == "apply_changes":
            return self._apply_configuration_changes(plan, execution)
        
        elif action == "verify_deployment":
            return self._verify_deployment(plan, execution)
        
        else:
            raise ValueError(f"Unknown deployment action: {action}")
    
    def _validate_deployment_plan(self, plan: DeploymentPlan) -> Dict[str, Any]:
        """Validate deployment plan"""
        validation_results = {
            "plan_valid": True,
            "issues": [],
            "warnings": []
        }
        
        # Check environment existence
        if not self._environment_exists(plan.source_environment):
            validation_results["issues"].append(f"Source environment {plan.source_environment} not found")
            validation_results["plan_valid"] = False
        
        if not self._environment_exists(plan.target_environment):
            validation_results["issues"].append(f"Target environment {plan.target_environment} not found")
            validation_results["plan_valid"] = False
        
        # Check for dangerous operations
        if plan.deployment_type == DeploymentType.INITIAL and plan.target_environment == "production":
            validation_results["warnings"].append("Initial deployment to production - ensure all testing is complete")
        
        # Check approval requirements
        if plan.approval_required:
            validation_results["warnings"].append("Deployment requires manual approval")
        
        return validation_results
    
    def _validate_environment(self, environment: str) -> Dict[str, Any]:
        """Validate an environment"""
        
        try:
            # Run environment validation
            report = self.validator.validate_environment(environment)
            
            validation_result = {
                "environment": environment,
                "validation_passed": report.invalid_variables == 0,
                "total_variables": report.total_variables,
                "invalid_variables": report.invalid_variables,
                "warnings": report.warnings,
                "summary": report.summary
            }
            
            # Run basic tests
            for suite_name in ["config_validation", "security_validation"]:
                if suite_name in self.tester.test_suites:
                    try:
                        test_report = self.tester.run_test_suite(suite_name, environment)
                        validation_result[f"{suite_name}_passed"] = test_report.failed_tests == 0
                    except Exception as e:
                        validation_result[f"{suite_name}_error"] = str(e)
            
            return validation_result
            
        except Exception as e:
            return {
                "environment": environment,
                "validation_passed": False,
                "error": str(e)
            }
    
    def _create_deployment_backup(self, plan: DeploymentPlan,
                                execution: DeploymentExecution) -> Dict[str, Any]:
        """Create backup before deployment"""
        
        try:
            backup_id = self.backup_system.create_backup(
                config_paths=["config/environments.yaml", "config/*.yaml"],
                backup_name=f"pre_deployment_{plan.target_environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                environment=plan.target_environment,
                description=f"Pre-deployment backup for {plan.name}",
                tags=["deployment", plan.target_environment, "pre_deployment"]
            )
            
            return {
                "backup_id": backup_id,
                "backup_created": True,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "backup_created": False,
                "error": str(e)
            }
    
    def _migrate_configuration(self, plan: DeploymentPlan,
                             execution: DeploymentExecution) -> Dict[str, Any]:
        """Migrate configuration between environments"""
        
        try:
            # Create migration plan
            migration_id = self.migrator.create_migration_plan(
                source_env=plan.source_environment,
                target_env=plan.target_environment,
                name=f"deployment_{plan.name}",
                description=f"Migration for deployment: {plan.description}"
            )
            
            # Execute migration
            migration_result = self.migrator.execute_migration(migration_id)
            
            return {
                "migration_id": migration_id,
                "migration_status": migration_result["status"],
                "migration_completed": migration_result["status"] == "completed"
            }
            
        except Exception as e:
            return {
                "migration_completed": False,
                "error": str(e)
            }
    
    def _update_secrets(self, plan: DeploymentPlan,
                       execution: DeploymentExecution) -> Dict[str, Any]:
        """Update secrets if needed"""
        
        try:
            updates_completed = 0
            
            for secret_update in plan.secrets_updates:
                if secret_update["action"] == "validate":
                    # Just validate secrets are accessible
                    secrets_to_check = self.secrets_manager.list_secrets(plan.target_environment)
                    validation_results = []
                    
                    for secret in secrets_to_check:
                        try:
                            value = self.secrets_manager.retrieve_secret(secret["name"], plan.target_environment)
                            validation_results.append({
                                "name": secret["name"],
                                "accessible": value is not None
                            })
                            if value is not None:
                                updates_completed += 1
                        except Exception as e:
                            validation_results.append({
                                "name": secret["name"],
                                "accessible": False,
                                "error": str(e)
                            })
                    
                    return {
                        "secrets_validated": len([r for r in validation_results if r.get("accessible")]),
                        "validation_results": validation_results
                    }
            
            return {
                "updates_completed": updates_completed
            }
            
        except Exception as e:
            return {
                "updates_completed": False,
                "error": str(e)
            }
    
    def _run_deployment_tests(self, plan: DeploymentPlan,
                            execution: DeploymentExecution) -> Dict[str, Any]:
        """Run deployment validation tests"""
        
        try:
            test_results = {}
            
            for suite_name in plan.testing_suites:
                if suite_name in self.tester.test_suites:
                    try:
                        test_report = self.tester.run_test_suite(
                            suite_name, 
                            plan.target_environment
                        )
                        
                        test_results[suite_name] = {
                            "total_tests": test_report.total_tests,
                            "passed_tests": test_report.passed_tests,
                            "failed_tests": test_report.failed_tests,
                            "success_rate": test_report.summary["success_rate"],
                            "all_passed": test_report.failed_tests == 0
                        }
                        
                    except Exception as e:
                        test_results[suite_name] = {
                            "error": str(e),
                            "all_passed": False
                        }
            
            all_tests_passed = all(
                result.get("all_passed", False) for result in test_results.values()
            )
            
            return {
                "test_results": test_results,
                "all_tests_passed": all_tests_passed,
                "summary": {
                    "suites_run": len(test_results),
                    "suites_passed": len([r for r in test_results.values() if r.get("all_passed", False)])
                }
            }
            
        except Exception as e:
            return {
                "testing_completed": False,
                "error": str(e)
            }
    
    def _apply_configuration_changes(self, plan: DeploymentPlan,
                                   execution: DeploymentExecution) -> Dict[str, Any]:
        """Apply configuration changes"""
        
        try:
            changes_applied = 0
            
            for config_change in plan.configuration_changes:
                change_type = config_change.get("type")
                
                if change_type == "environment_validation":
                    # Already done in validation phase
                    changes_applied += 1
                    
                elif change_type == "secrets_verification":
                    # Already done in secrets phase
                    changes_applied += 1
                    
                elif change_type == "backup_creation":
                    # Already done in backup phase
                    changes_applied += 1
                    
                else:
                    # Apply other configuration changes
                    change_id = self.change_tracker.record_manual_change(
                        file_path=f"deployment/{plan.id}",
                        change_type="update",
                        user_id="deployment_system",
                        user_name="Deployment System",
                        environment=plan.target_environment,
                        description=f"Deployment: {config_change.get('description', change_type)}",
                        severity="medium"
                    )
                    changes_applied += 1
            
            return {
                "changes_applied": changes_applied,
                "configuration_updated": True
            }
            
        except Exception as e:
            return {
                "configuration_updated": False,
                "error": str(e)
            }
    
    def _verify_deployment(self, plan: DeploymentPlan,
                         execution: DeploymentExecution) -> Dict[str, Any]:
        """Verify deployment success"""
        
        try:
            # Run final validation
            final_validation = self._validate_environment(plan.target_environment)
            
            # Record deployment completion
            self.change_tracker.record_audit_event(
                event_type="deployment_completion",
                user_id="system",
                user_name="Deployment System",
                action="deployment_completed",
                resource=plan.id,
                details={"execution_id": execution.execution_id},
                result="success"
            )
            
            return {
                "deployment_verified": final_validation.get("validation_passed", False),
                "final_validation": final_validation,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "deployment_verified": False,
                "error": str(e)
            }
    
    def _execute_rollback(self, plan: DeploymentPlan,
                        execution: DeploymentExecution):
        """Execute rollback procedures"""
        
        try:
            execution.status = DeploymentStatus.ROLLED_BACK
            
            # Find latest backup for this environment
            backups = self.backup_system.list_backups(plan.target_environment)
            if backups:
                latest_backup = backups[0]  # Most recent
                
                # Restore from backup
                restore_success = self.backup_system.restore_backup(
                    latest_backup.id,
                    f"deployment_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                if restore_success:
                    execution.results["rollback_success"] = True
                    execution.results["backup_restored"] = latest_backup.id
                else:
                    execution.results["rollback_success"] = False
                    execution.results["rollback_error"] = "Failed to restore backup"
            
            # Record rollback
            self.change_tracker.record_audit_event(
                event_type="deployment_rollback",
                user_id="system",
                user_name="Deployment System",
                action="rollback_deployment",
                resource=plan.id,
                details={"execution_id": execution.execution_id},
                result="completed"
            )
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            execution.results["rollback_error"] = str(e)
    
    def _environment_exists(self, environment: str) -> bool:
        """Check if environment exists"""
        try:
            # This would check against actual environment configuration
            env_config = self.validator.environments_config.get('environments', {})
            return environment in env_config
        except Exception:
            return False
    
    def _save_deployment_plan(self, plan: DeploymentPlan):
        """Save deployment plan to file"""
        
        # Convert enums for serialization
        plan_dict = asdict(plan)
        plan_dict['deployment_type'] = plan.deployment_type.value
        
        plan_file = self.plans_dir / f"{plan.id}.yaml"
        with open(plan_file, 'w') as f:
            yaml.dump(plan_dict, f, default_flow_style=False)
    
    def _save_deployment_execution(self, execution: DeploymentExecution):
        """Save deployment execution to file"""
        
        # Convert enums for serialization
        execution_dict = asdict(execution)
        execution_dict['status'] = execution.status.value
        
        execution_file = self.executions_dir / f"{execution.execution_id}.json"
        with open(execution_file, 'w') as f:
            json.dump(execution_dict, f, indent=2, default=str)
    
    def list_deployment_plans(self) -> List[DeploymentPlan]:
        """List all deployment plans"""
        return list(self.deployment_plans.values())
    
    def get_deployment_plan(self, plan_id: str) -> Optional[DeploymentPlan]:
        """Get specific deployment plan"""
        return self.deployment_plans.get(plan_id)
    
    def list_deployment_executions(self, plan_id: Optional[str] = None) -> List[DeploymentExecution]:
        """List deployment executions"""
        executions = []
        
        for exec_file in self.executions_dir.glob("*.json"):
            try:
                with open(exec_file, 'r') as f:
                    data = json.load(f)
                
                # Convert enums
                data['status'] = DeploymentStatus(data['status'])
                
                execution = DeploymentExecution(**data)
                executions.append(execution)
                
            except Exception as e:
                self.logger.error(f"Failed to load execution {exec_file}: {e}")
        
        # Filter by plan if specified
        if plan_id:
            executions = [e for e in executions if e.plan_id == plan_id]
        
        # Sort by start time (most recent first)
        executions.sort(key=lambda x: x.started_at, reverse=True)
        
        return executions
    
    def promote_environment(self, source_env: str, target_env: str,
                          description: str = "") -> str:
        """Promote environment (shortcut for common deployment pattern)"""
        
        return self.create_deployment_plan(
            name=f"Promote {source_env} to {target_env}",
            source_env=source_env,
            target_env=target_env,
            deployment_type=DeploymentType.UPDATE,
            description=description or f"Promote configuration from {source_env} to {target_env}"
        )

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Environment Deployment Automation")
    subparsers = parser.add_subparsers(dest='command')
    
    # Plan commands
    plan_parser = subparsers.add_parser('plan', help='Deployment plan commands')
    plan_subparsers = plan_parser.add_subparsers(dest='plan_command')
    
    create_plan = plan_subparsers.add_parser('create', help='Create deployment plan')
    create_plan.add_argument('name', help='Plan name')
    create_plan.add_argument('source_env', help='Source environment')
    create_plan.add_argument('target_env', help='Target environment')
    create_plan.add_argument('--type', choices=[t.value for t in DeploymentType],
                           default=DeploymentType.UPDATE.value, help='Deployment type')
    create_plan.add_argument('--description', default='', help='Plan description')
    create_plan.add_argument('--auto-approve', action='store_true', help='Skip approval requirement')
    
    list_plans = plan_subparsers.add_parser('list', help='List deployment plans')
    
    get_plan = plan_subparsers.add_parser('get', help='Get deployment plan')
    get_plan.add_argument('plan_id', help='Plan ID')
    
    # Execute commands
    execute_parser = subparsers.add_parser('execute', help='Execute deployment')
    execute_parser.add_argument('plan_id', help='Plan ID to execute')
    execute_parser.add_argument('--auto-approve', action='store_true', help='Auto-approve if required')
    
    # Promote command (shortcut)
    promote_parser = subparsers.add_parser('promote', help='Promote environment')
    promote_parser.add_argument('source_env', help='Source environment')
    promote_parser.add_argument('target_env', help='Target environment')
    promote_parser.add_argument('--description', default='', help='Description')
    
    # List executions
    list_exec = subparsers.add_parser('list-executions', help='List executions')
    list_exec.add_argument('--plan', help='Filter by plan ID')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check deployment status')
    status_parser.add_argument('execution_id', help='Execution ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    orchestrator = DeploymentOrchestrator()
    
    if args.command == 'plan':
        if args.plan_command == 'create':
            deployment_type = DeploymentType(args.type)
            
            plan_id = orchestrator.create_deployment_plan(
                name=args.name,
                source_env=args.source_env,
                target_env=args.target_env,
                deployment_type=deployment_type,
                description=args.description
            )
            
            if args.auto_approve and plan_id in orchestrator.deployment_plans:
                plan = orchestrator.deployment_plans[plan_id]
                plan.approval_required = False
            
            print(f"Deployment plan created: {plan_id}")
        
        elif args.plan_command == 'list':
            plans = orchestrator.list_deployment_plans()
            for plan in plans:
                print(f"{plan.id}: {plan.name} ({plan.source_environment} -> {plan.target_env})")
        
        elif args.plan_command == 'get':
            plan = orchestrator.get_deployment_plan(args.plan_id)
            if plan:
                print(f"Plan: {plan.name}")
                print(f"Type: {plan.deployment_type.value}")
                print(f"From: {plan.source_environment}")
                print(f"To: {plan.target_environment}")
                print(f"Description: {plan.description}")
                print(f"Approval Required: {plan.approval_required}")
            else:
                print(f"Plan not found: {args.plan_id}")
    
    elif args.command == 'execute':
        execution = orchestrator.execute_deployment(args.plan_id, args.auto_approve)
        print(f"Execution started: {execution.execution_id}")
        print(f"Status: {execution.status.value}")
        print(f"Steps: {execution.completed_steps}/{execution.total_steps}")
    
    elif args.command == 'promote':
        plan_id = orchestrator.promote_environment(
            args.source_env, args.target_env, args.description
        )
        print(f"Promotion plan created: {plan_id}")
    
    elif args.command == 'list-executions':
        executions = orchestrator.list_deployment_executions(args.plan)
        for execution in executions:
            print(f"{execution.execution_id}: {execution.status.value} - {execution.started_at}")
    
    elif args.command == 'status':
        executions = orchestrator.list_deployment_executions()
        execution = next((e for e in executions if e.execution_id == args.execution_id), None)
        
        if execution:
            print(f"Execution: {execution.execution_id}")
            print(f"Status: {execution.status.value}")
            print(f"Started: {execution.started_at}")
            print(f"Current Step: {execution.current_step}")
            print(f"Progress: {execution.completed_steps}/{execution.total_steps}")
            
            if execution.completed_at:
                print(f"Completed: {execution.completed_at}")
            
            if execution.errors:
                print(f"Errors: {len(execution.errors)}")
                for error in execution.errors:
                    print(f"  - {error}")
            
            if execution.warnings:
                print(f"Warnings: {len(execution.warnings)}")
                for warning in execution.warnings:
                    print(f"  - {warning}")
        else:
            print(f"Execution not found: {args.execution_id}")

if __name__ == "__main__":
    main()