#!/usr/bin/env python3
"""
Environment Management System Demo Script

This script demonstrates the key features of the environment management system.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from environment_manager import EnvironmentManagementSystem

def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)

def print_step(step_num: int, description: str):
    """Print a formatted step"""
    print(f"\n📋 Step {step_num}: {description}")
    print("-" * 40)

def main():
    """Run the demonstration"""
    print("🌟 Environment Management System Demo")
    print("This demo will showcase the key features of the system.")
    
    try:
        # Initialize the system
        print_header("INITIALIZING SYSTEM")
        env_mgmt = EnvironmentManagementSystem()
        
        print_step(1, "Initializing Environment Management System")
        success = env_mgmt.initialize_system(["development", "staging"])
        if success:
            print("✅ System initialized successfully")
        else:
            print("❌ System initialization failed")
            return
        
        # Show system status
        print_step(2, "Displaying System Status")
        status = env_mgmt.show_status()
        print("System Status:")
        print(f"  • Status: {status['system']['status']}")
        print(f"  • Secrets: {status['system']['secrets_count']}")
        print(f"  • Configs: {status['system']['configs_count']}")
        print(f"  • Active Deployments: {status['system']['active_deployments']}")
        
        # Manage secrets
        print_header("SECRETS MANAGEMENT")
        print_step(3, "Storing a Secret")
        
        # Store a test secret
        success = env_mgmt.secrets_manager.store_secret(
            "demo_secret", "demo_password_123", "development"
        )
        if success:
            print("✅ Secret stored successfully")
        else:
            print("❌ Failed to store secret")
        
        print_step(4, "Retrieving the Secret")
        retrieved = env_mgmt.secrets_manager.get_secret("demo_secret")
        if retrieved:
            print(f"✅ Secret retrieved: {retrieved}")
        else:
            print("❌ Failed to retrieve secret")
        
        print_step(5, "Generating a New Secret")
        generated = env_mgmt.secrets_manager.generate_secret("demo_generated_secret")
        print(f"✅ Generated secret: {generated[:20]}...")
        
        # Configuration management
        print_header("CONFIGURATION MANAGEMENT")
        print_step(6, "Loading Configuration")
        
        config = env_mgmt.config_manager.load_config("development")
        if config:
            print(f"✅ Configuration loaded for {config.name}")
            print(f"  • Type: {config.type.value}")
            print(f"  • Version: {config.version}")
            print(f"  • Host: {config.get('app.host', 'N/A')}")
            print(f"  • Port: {config.get('app.port', 'N/A')}")
        else:
            print("❌ Failed to load configuration")
        
        print_step(7, "Updating Configuration")
        success = env_mgmt.config_manager.update_config(
            "development", 
            "app.demo_field", 
            "demo_value", 
            "demo_user", 
            "Demo configuration update"
        )
        if success:
            print("✅ Configuration updated successfully")
            
            # Verify the update
            updated_value = env_mgmt.config_manager.get_config("development", "app.demo_field")
            print(f"  • Updated value: {updated_value}")
        else:
            print("❌ Failed to update configuration")
        
        # Backup management
        print_header("BACKUP MANAGEMENT")
        print_step(8, "Creating a Backup")
        
        backup_id = env_mgmt.create_backup(
            "development", 
            "full", 
            "Demo backup", 
            encrypt=False
        )
        if backup_id:
            print(f"✅ Backup created: {backup_id}")
            
            print_step(9, "Verifying Backup")
            if env_mgmt.backup_manager.verify_backup(backup_id):
                print("✅ Backup verified successfully")
            else:
                print("❌ Backup verification failed")
        else:
            print("❌ Failed to create backup")
        
        # Testing and validation
        print_header("TESTING & VALIDATION")
        print_step(10, "Running Environment Validation")
        
        validation_result = env_mgmt.validate_environment("development")
        if validation_result:
            summary = validation_result.get("summary", {})
            print(f"✅ Validation completed:")
            print(f"  • Total tests: {summary.get('total_tests', 0)}")
            print(f"  • Passed: {summary.get('passed', 0)}")
            print(f"  • Failed: {summary.get('failed', 0)}")
            print(f"  • Success rate: {summary.get('success_rate', 0):.1f}%")
            
            if validation_result.get("valid"):
                print("✅ Environment is valid")
            else:
                print("⚠️  Environment has validation issues")
        
        # Deployment automation
        print_header("DEPLOYMENT AUTOMATION")
        print_step(11, "Creating a Deployment")
        
        try:
            deployment_id = env_mgmt.deploy_environment(
                "development", 
                "v1.0.0-demo", 
                "standard"
            )
            if deployment_id:
                print(f"✅ Deployment created: {deployment_id}")
                
                # Get deployment status
                status = env_mgmt.deployment_manager.get_deployment_status(deployment_id)
                if status:
                    print(f"  • Status: {status['status']}")
                    print(f"  • Environment: {status['environment']}")
                    print(f"  • Version: {status['version']}")
            else:
                print("❌ Failed to create deployment")
        except Exception as e:
            print(f"⚠️  Deployment creation skipped: {e}")
        
        # Health monitoring
        print_header("HEALTH MONITORING")
        print_step(12, "Running Health Check")
        
        health = env_mgmt.run_health_check()
        if health:
            print(f"✅ Health check completed:")
            print(f"  • Overall status: {health.get('overall_status', 'unknown')}")
            
            components = health.get("components", {})
            for component, status in components.items():
                status_text = "✅" if status.get("healthy", False) else "❌"
                print(f"  {status_text} {component}: {status.get('details', 'N/A')}")
        
        # Final status
        print_header("FINAL SYSTEM STATUS")
        final_status = env_mgmt.show_status()
        print("Final System Status:")
        print(f"  • Status: {final_status['system']['status']}")
        print(f"  • Total Secrets: {final_status['system']['secrets_count']}")
        print(f"  • Total Configs: {final_status['system']['configs_count']}")
        print(f"  • Recent Backups: {final_status['system']['recent_backups']}")
        
        # Demo complete
        print_header("DEMO COMPLETED SUCCESSFULLY")
        print("🎉 The Environment Management System demo has completed!")
        print("\nKey features demonstrated:")
        print("  ✅ System initialization and health monitoring")
        print("  ✅ Secure secrets management with encryption")
        print("  ✅ Configuration management and validation")
        print("  ✅ Backup creation and verification")
        print("  ✅ Environment testing and validation")
        print("  ✅ Deployment automation")
        print("\nNext steps:")
        print("  • Review the documentation: environment/docs/README.md")
        print("  • Run the test suite: python environment/tests/test_environment_management.py")
        print("  • Set up daily maintenance: python environment/scripts/daily_maintenance.py")
        print("  • Customize configurations for your needs")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()