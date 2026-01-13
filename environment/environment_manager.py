#!/usr/bin/env python3
"""
Environment Management System - Main Interface

This is the main entry point for the comprehensive environment and secrets management system.
It provides a unified interface for all environment management operations.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import logging

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Import all management modules
from secrets_mgmt.secrets_manager import SecretsManager
from config_manager import ConfigManager
from tools.backup_migration import BackupManager, MigrationManager
from tools.testing_validation import EnvironmentTester
from tools.deployment_automation import DeploymentManager, DeploymentStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnvironmentManagementSystem:
    """Main environment management system interface"""
    
    def __init__(self, config_dir: str = None, backup_dir: str = None):
        self.config_dir = config_dir or "environment/templates"
        self.backup_dir = backup_dir or str(Path.home() / '.env_mgmt' / 'backups')
        
        # Initialize all subsystems
        self.secrets_manager = SecretsManager()
        self.config_manager = ConfigManager(self.config_dir)
        self.backup_manager = BackupManager(self.backup_dir)
        self.migration_manager = MigrationManager(self.backup_manager)
        self.tester = EnvironmentTester()
        self.deployment_manager = DeploymentManager()
        
        logger.info("Environment Management System initialized")
    
    def initialize_system(self, environments: list = None) -> bool:
        """Initialize the environment management system"""
        try:
            environments = environments or ["development", "staging", "production"]
            
            logger.info("Initializing environment management system...")
            
            # Create configuration directories
            Path(self.config_dir).mkdir(exist_ok=True, parents=True)
            
            # Load and validate configurations for all environments
            for env in environments:
                logger.info(f"Loading configuration for {env}...")
                config = self.config_manager.load_config(env)
                if config:
                    logger.info(f"✓ Configuration loaded for {env}")
                else:
                    logger.warning(f"⚠ Configuration not found for {env}")
            
            # Initialize secrets management
            logger.info("Initializing secrets management...")
            # Create some example secrets for testing
            self.secrets_manager.store_secret("db_password", "dev_password", "development")
            self.secrets_manager.store_secret("jwt_secret", "dev_jwt_secret_key", "development")
            
            # Test the system components
            logger.info("Running system tests...")
            test_results = self._run_system_tests()
            
            if test_results["success"]:
                logger.info("✓ System initialization completed successfully")
                return True
            else:
                logger.error("✗ System initialization failed")
                return False
                
        except Exception as e:
            logger.error(f"System initialization error: {e}")
            return False
    
    def _run_system_tests(self) -> dict:
        """Run basic system tests"""
        try:
            results = {
                "secrets_management": True,
                "config_validation": True,
                "backup_system": True,
                "testing_system": True,
                "deployment_system": True
            }
            
            # Test secrets management
            try:
                test_secret = self.secrets_manager.get_secret("db_password")
                if test_secret is None:
                    results["secrets_management"] = False
            except:
                results["secrets_management"] = False
            
            # Test config validation
            try:
                if self.config_manager.list_configs():
                    pass  # Configs loaded successfully
                else:
                    results["config_validation"] = False
            except:
                results["config_validation"] = False
            
            # Test backup system
            try:
                # Try to create a test backup
                test_backup_id = self.backup_manager.create_backup(
                    "test", backup_type="full", description="System test backup"
                )
                if not test_backup_id:
                    results["backup_system"] = False
            except:
                results["backup_system"] = False
            
            success = all(results.values())
            return {
                "success": success,
                "tests": results
            }
            
        except Exception as e:
            logger.error(f"System tests failed: {e}")
            return {"success": False, "tests": {}}
    
    def show_status(self) -> dict:
        """Show system status"""
        try:
            # Get secrets count
            try:
                secrets_list = self.secrets_manager.db.list_secrets()
                secrets_count = len(secrets_list)
            except:
                secrets_count = 0
            
            # Get configs count
            try:
                configs_list = self.config_manager.list_configs()
                configs_count = len(configs_list)
            except:
                configs_count = 0
            
            # Get recent backups
            try:
                recent_backups = self.backup_manager.list_backups(limit=5)
            except:
                recent_backups = []
            
            # Get recent deployments
            try:
                recent_deployments = self.deployment_manager.list_deployments(
                    status=DeploymentStatus.RUNNING
                )
            except:
                recent_deployments = []
            
            status = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "status": "operational",
                    "secrets_count": secrets_count,
                    "configs_count": configs_count,
                    "recent_backups": len(recent_backups),
                    "active_deployments": len(recent_deployments)
                },
                "environments": {},
                "recent_backups": [
                    {
                        "backup_id": backup.backup_id,
                        "environment": backup.environment,
                        "timestamp": backup.timestamp.isoformat(),
                        "type": backup.backup_type.value
                    }
                    for backup in recent_backups
                ],
                "active_deployments": recent_deployments
            }
            
            # Get environment-specific status
            for env in ["development", "staging", "production"]:
                try:
                    config = self.config_manager.configs.get(env)
                    if config:
                        status["environments"][env] = {
                            "loaded": True,
                            "version": config.version,
                            "type": config.type.value,
                            "last_updated": config.updated_at.isoformat()
                        }
                    else:
                        status["environments"][env] = {
                            "loaded": False
                        }
                except:
                    status["environments"][env] = {
                        "loaded": False,
                        "error": "Failed to load"
                    }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "system": {"status": "error", "error": str(e)},
                "environments": {},
                "recent_backups": [],
                "active_deployments": []
            }
    
    def validate_environment(self, environment: str) -> dict:
        """Validate an environment"""
        try:
            # Load configuration
            config = self.config_manager.load_config(environment)
            if not config:
                return {
                    "environment": environment,
                    "valid": False,
                    "error": "Configuration not found",
                    "results": []
                }
            
            # Run validation tests
            test_results = self.tester.run_full_validation(environment, config.data)
            
            # Determine overall validity
            summary = test_results["summary"]
            valid = summary["failed"] == 0
            
            return {
                "environment": environment,
                "valid": valid,
                "timestamp": test_results["timestamp"],
                "summary": summary,
                "results": test_results["results"]
            }
            
        except Exception as e:
            logger.error(f"Environment validation failed for {environment}: {e}")
            return {
                "environment": environment,
                "valid": False,
                "error": str(e),
                "results": []
            }
    
    def promote_configuration(self, source_env: str, target_env: str, 
                             user: str = "system", reason: str = "") -> bool:
        """Promote configuration from one environment to another"""
        try:
            return self.config_manager.promote_config(
                source_env, target_env, user, reason
            )
        except Exception as e:
            logger.error(f"Configuration promotion failed: {e}")
            return False
    
    def create_backup(self, environment: str, backup_type: str = "full", 
                     description: str = "", encrypt: bool = False) -> str:
        """Create a backup"""
        try:
            from tools.backup_migration import BackupType
            
            backup_type_enum = BackupType(backup_type)
            backup_id = self.backup_manager.create_backup(
                environment, backup_type_enum, description, encrypt
            )
            return backup_id
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return None
    
    def deploy_environment(self, environment: str, version: str = None, 
                          deployment_type: str = "standard") -> str:
        """Deploy to an environment"""
        try:
            if not version:
                version = f"{environment}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            deployment_id = self.deployment_manager.create_deployment(
                environment, version, deployment_type
            )
            
            # Execute deployment
            success = self.deployment_manager.execute_deployment(deployment_id)
            
            if success:
                logger.info(f"Deployment {deployment_id} completed successfully")
            else:
                logger.error(f"Deployment {deployment_id} failed")
            
            return deployment_id
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return None
    
    def run_health_check(self) -> dict:
        """Run comprehensive health check"""
        try:
            logger.info("Running comprehensive health check...")
            
            health_report = {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "healthy",
                "components": {}
            }
            
            # Check each component
            components = {
                "secrets_management": self._check_secrets_management(),
                "config_management": self._check_config_management(),
                "backup_system": self._check_backup_system(),
                "testing_system": self._check_testing_system(),
                "deployment_system": self._check_deployment_system()
            }
            
            health_report["components"] = components
            
            # Determine overall status
            failed_components = [name for name, status in components.items() 
                               if not status.get("healthy", False)]
            
            if failed_components:
                health_report["overall_status"] = "degraded"
                health_report["failed_components"] = failed_components
            
            return health_report
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "error": str(e),
                "components": {}
            }
    
    def _check_secrets_management(self) -> dict:
        """Check secrets management health"""
        try:
            # Test basic operations
            test_secret = "test_health_check"
            test_value = "test_value_" + str(datetime.now().timestamp())
            
            # Store test secret
            self.secrets_manager.store_secret(test_secret, test_value, "health_check")
            
            # Retrieve test secret
            retrieved_value = self.secrets_manager.get_secret(test_secret)
            
            # Clean up
            self.secrets_manager.db.delete_secret(test_secret)
            
            success = retrieved_value == test_value
            
            return {
                "healthy": success,
                "details": "Secrets management operational" if success else "Secrets management failed"
            }
        except Exception as e:
            return {
                "healthy": False,
                "details": f"Secrets management error: {e}"
            }
    
    def _check_config_management(self) -> dict:
        """Check configuration management health"""
        try:
            configs = self.config_manager.list_configs()
            return {
                "healthy": len(configs) > 0,
                "details": f"Found {len(configs)} configurations" if configs else "No configurations loaded",
                "configs": configs
            }
        except Exception as e:
            return {
                "healthy": False,
                "details": f"Config management error: {e}"
            }
    
    def _check_backup_system(self) -> dict:
        """Check backup system health"""
        try:
            test_backup = self.backup_manager.create_backup(
                "health_check", description="Health check backup"
            )
            if test_backup:
                self.backup_manager.verify_backup(test_backup)
                return {
                    "healthy": True,
                    "details": "Backup system operational",
                    "test_backup_id": test_backup
                }
            else:
                return {
                    "healthy": False,
                    "details": "Failed to create test backup"
                }
        except Exception as e:
            return {
                "healthy": False,
                "details": f"Backup system error: {e}"
            }
    
    def _check_testing_system(self) -> dict:
        """Check testing system health"""
        try:
            # Test with development environment if available
            dev_config = self.config_manager.load_config("development")
            if dev_config:
                test_results = self.tester.run_full_validation("development", dev_config.data)
                return {
                    "healthy": test_results["summary"]["failed"] == 0,
                    "details": f"Testing system operational - {test_results['summary']['passed']}/{test_results['summary']['total_tests']} tests passed"
                }
            else:
                return {
                    "healthy": True,
                    "details": "Testing system ready (no development config to test)"
                }
        except Exception as e:
            return {
                "healthy": False,
                "details": f"Testing system error: {e}"
            }
    
    def _check_deployment_system(self) -> dict:
        """Check deployment system health"""
        try:
            pipelines = self.deployment_manager.pipeline_manager.list_pipelines()
            return {
                "healthy": len(pipelines) > 0,
                "details": f"Deployment system operational - {len(pipelines)} pipelines available",
                "pipelines": pipelines
            }
        except Exception as e:
            return {
                "healthy": False,
                "details": f"Deployment system error: {e}"
            }

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="Environment Management System - Unified Management Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initialize the system
  python environment_manager.py init --environments development staging production

  # Show system status
  python environment_manager.py status

  # Validate an environment
  python environment_manager.py validate --environment staging

  # Promote configuration
  python environment_manager.py promote --source staging --target production --reason "Ready for production"

  # Create backup
  python environment_manager.py backup --environment staging --type full

  # Deploy to environment
  python environment_manager.py deploy --environment production --version v1.2.3

  # Run health check
  python environment_manager.py health-check
        """
    )
    
    parser.add_argument('--config-dir', help='Configuration directory')
    parser.add_argument('--backup-dir', help='Backup directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize the environment management system')
    init_parser.add_argument('--environments', nargs='+', 
                           default=['development', 'staging', 'production'],
                           help='Environments to initialize')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate an environment')
    validate_parser.add_argument('--environment', required=True, help='Environment to validate')
    
    # Promote command
    promote_parser = subparsers.add_parser('promote', help='Promote configuration between environments')
    promote_parser.add_argument('--source', required=True, help='Source environment')
    promote_parser.add_argument('--target', required=True, help='Target environment')
    promote_parser.add_argument('--user', default='system', help='User performing promotion')
    promote_parser.add_argument('--reason', default='', help='Reason for promotion')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create a backup')
    backup_parser.add_argument('--environment', required=True, help='Environment to backup')
    backup_parser.add_argument('--type', default='full', 
                              choices=['full', 'config_only', 'secrets_only', 'incremental'],
                              help='Backup type')
    backup_parser.add_argument('--description', default='', help='Backup description')
    backup_parser.add_argument('--encrypt', action='store_true', help='Encrypt backup')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy to an environment')
    deploy_parser.add_argument('--environment', required=True, help='Target environment')
    deploy_parser.add_argument('--version', help='Deployment version')
    deploy_parser.add_argument('--type', default='standard',
                              choices=['standard', 'canary', 'blue-green'],
                              help='Deployment type')
    
    # Health check command
    health_parser = subparsers.add_parser('health-check', help='Run comprehensive health check')
    
    # Secrets command (subcommands)
    secrets_parser = subparsers.add_parser('secrets', help='Secrets management')
    secrets_subparsers = secrets_parser.add_subparsers(dest='secrets_action')
    
    secrets_store = secrets_subparsers.add_parser('store', help='Store a secret')
    secrets_store.add_argument('--name', required=True, help='Secret name')
    secrets_store.add_argument('--value', required=True, help='Secret value')
    secrets_store.add_argument('--environment', required=True, help='Environment')
    
    secrets_get = secrets_subparsers.add_parser('get', help='Get a secret')
    secrets_get.add_argument('--name', required=True, help='Secret name')
    
    secrets_list = secrets_subparsers.add_parser('list', help='List secrets')
    secrets_list.add_argument('--environment', help='Filter by environment')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize the system
    env_mgmt = EnvironmentManagementSystem(args.config_dir, args.backup_dir)
    
    try:
        if args.command == 'init':
            print("Initializing Environment Management System...")
            if env_mgmt.initialize_system(args.environments):
                print("✓ System initialized successfully")
            else:
                print("✗ System initialization failed")
                sys.exit(1)
        
        elif args.command == 'status':
            status = env_mgmt.show_status()
            print(json.dumps(status, indent=2))
        
        elif args.command == 'validate':
            print(f"Validating environment: {args.environment}")
            result = env_mgmt.validate_environment(args.environment)
            print(json.dumps(result, indent=2))
        
        elif args.command == 'promote':
            print(f"Promoting configuration: {args.source} -> {args.target}")
            if env_mgmt.promote_configuration(args.source, args.target, args.user, args.reason):
                print("✓ Promotion completed successfully")
            else:
                print("✗ Promotion failed")
                sys.exit(1)
        
        elif args.command == 'backup':
            print(f"Creating backup for environment: {args.environment}")
            backup_id = env_mgmt.create_backup(args.environment, args.type, args.description, args.encrypt)
            if backup_id:
                print(f"✓ Backup created: {backup_id}")
            else:
                print("✗ Backup creation failed")
                sys.exit(1)
        
        elif args.command == 'deploy':
            print(f"Deploying to environment: {args.environment}")
            deployment_id = env_mgmt.deploy_environment(args.environment, args.version, args.type)
            if deployment_id:
                print(f"✓ Deployment created: {deployment_id}")
            else:
                print("✗ Deployment failed")
                sys.exit(1)
        
        elif args.command == 'health-check':
            print("Running comprehensive health check...")
            health = env_mgmt.run_health_check()
            print(json.dumps(health, indent=2))
            
            if health["overall_status"] == "healthy":
                print("✓ System is healthy")
            elif health["overall_status"] == "degraded":
                print("⚠ System is degraded")
                sys.exit(1)
            else:
                print("✗ System has errors")
                sys.exit(1)
        
        elif args.command == 'secrets':
            if args.secrets_action == 'store':
                if env_mgmt.secrets_manager.store_secret(args.name, args.value, args.environment):
                    print(f"✓ Secret '{args.name}' stored successfully")
                else:
                    print("✗ Failed to store secret")
                    sys.exit(1)
            
            elif args.secrets_action == 'get':
                value = env_mgmt.secrets_manager.get_secret(args.name)
                if value:
                    print(value)
                else:
                    print(f"Secret '{args.name}' not found")
                    sys.exit(1)
            
            elif args.secrets_action == 'list':
                secrets_list = env_mgmt.secrets_manager.db.list_secrets(args.environment)
                print(f"Secrets in {args.environment or 'all'} environments:")
                for secret in secrets_list:
                    print(f"  - {secret.name} ({secret.environment})")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Unhandled error")
        sys.exit(1)

if __name__ == '__main__':
    main()