#!/usr/bin/env python3
"""
Daily Maintenance Script for Environment Management System

This script performs routine maintenance tasks including:
- Backup rotation and cleanup
- Secret rotation checks
- Health monitoring
- Log rotation
- System validation
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from environment_manager import EnvironmentManagementSystem

def setup_logging(log_file: str = None):
    """Setup logging for the maintenance script"""
    log_dir = Path.home() / '.env_mgmt' / 'logs'
    log_dir.mkdir(exist_ok=True, parents=True)
    
    log_file = log_file or str(log_dir / 'maintenance.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def rotate_backups(env_mgmt: EnvironmentManagementSystem, max_age_days: int = 30):
    """Rotate and cleanup old backups"""
    logger = logging.getLogger(__name__)
    logger.info("Starting backup rotation...")
    
    try:
        from tools.backup_migration import BackupManager
        backup_manager = BackupManager()
        
        # Get all backups
        all_backups = backup_manager.list_backups(limit=1000)
        
        # Filter old backups
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        old_backups = [
            backup for backup in all_backups
            if backup.timestamp < cutoff_date
        ]
        
        # Remove old backups
        for backup in old_backups:
            try:
                archive_path = Path(backup_manager.backup_dir) / f"{backup.backup_id}.tar.gz"
                if archive_path.exists():
                    archive_path.unlink()
                
                # Remove from database
                with backup_manager._get_backup_metadata(backup.backup_id):
                    pass  # Already handled in backup_manager
                
                logger.info(f"Removed old backup: {backup.backup_id}")
                
            except Exception as e:
                logger.error(f"Failed to remove backup {backup.backup_id}: {e}")
        
        logger.info(f"Backup rotation completed. Removed {len(old_backups)} old backups")
        
    except Exception as e:
        logger.error(f"Backup rotation failed: {e}")

def check_secret_rotation(env_mgmt: EnvironmentManagementSystem):
    """Check for secrets that need rotation"""
    logger = logging.getLogger(__name__)
    logger.info("Checking secret rotation requirements...")
    
    try:
        all_secrets = env_mgmt.secrets_manager.db.list_secrets()
        now = datetime.now()
        secrets_to_rotate = []
        
        for secret in all_secrets:
            # Check if secret is due for rotation
            next_rotation = secret.last_rotated + timedelta(days=secret.rotation_days)
            
            if now >= next_rotation:
                secrets_to_rotate.append({
                    'name': secret.name,
                    'environment': secret.environment,
                    'last_rotated': secret.last_rotated,
                    'rotation_days': secret.rotation_days
                })
        
        if secrets_to_rotate:
            logger.warning(f"Found {len(secrets_to_rotate)} secrets requiring rotation:")
            for secret_info in secrets_to_rotate:
                logger.warning(f"  - {secret_info['name']} ({secret_info['environment']}) - "
                              f"Last rotated: {secret_info['last_rotated'].strftime('%Y-%m-%d')}")
            
            # Optionally auto-rotate (uncomment to enable)
            # for secret_info in secrets_to_rotate:
            #     try:
            #         success = env_mgmt.secrets_manager.rotate_secret(secret_info['name'])
            #         if success:
            #             logger.info(f"Auto-rotated secret: {secret_info['name']}")
            #         else:
            #             logger.error(f"Failed to auto-rotate secret: {secret_info['name']}")
            #     except Exception as e:
            #         logger.error(f"Auto-rotation error for {secret_info['name']}: {e}")
        else:
            logger.info("No secrets require rotation")
            
    except Exception as e:
        logger.error(f"Secret rotation check failed: {e}")

def validate_all_environments(env_mgmt: EnvironmentManagementSystem):
    """Validate all configured environments"""
    logger = logging.getLogger(__name__)
    logger.info("Validating all environments...")
    
    try:
        environments = ["development", "staging", "production"]
        validation_results = {}
        
        for env in environments:
            try:
                result = env_mgmt.validate_environment(env)
                validation_results[env] = result
                
                if result.get("valid", False):
                    logger.info(f"✅ Environment '{env}' validation passed")
                else:
                    logger.warning(f"⚠️  Environment '{env}' validation failed")
                    
            except Exception as e:
                logger.error(f"Environment '{env}' validation error: {e}")
                validation_results[env] = {"valid": False, "error": str(e)}
        
        # Save validation results
        results_file = Path.home() / '.env_mgmt' / 'validation_results.json'
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        logger.info(f"Validation results saved to {results_file}")
        
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")

def cleanup_logs(max_age_days: int = 30):
    """Clean up old log files"""
    logger = logging.getLogger(__name__)
    logger.info("Cleaning up old log files...")
    
    try:
        log_dir = Path.home() / '.env_mgmt' / 'logs'
        if not log_dir.exists():
            return
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        cleaned_files = 0
        
        for log_file in log_dir.glob("*.log"):
            try:
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    cleaned_files += 1
                    logger.info(f"Removed old log file: {log_file.name}")
            except Exception as e:
                logger.error(f"Failed to remove log file {log_file.name}: {e}")
        
        logger.info(f"Log cleanup completed. Removed {cleaned_files} old log files")
        
    except Exception as e:
        logger.error(f"Log cleanup failed: {e}")

def run_health_monitoring(env_mgmt: EnvironmentManagementSystem):
    """Run health monitoring and alert on issues"""
    logger = logging.getLogger(__name__)
    logger.info("Running health monitoring...")
    
    try:
        health = env_mgmt.run_health_check()
        
        if health.get("overall_status") == "healthy":
            logger.info("✅ System health is good")
        elif health.get("overall_status") == "degraded":
            logger.warning("⚠️  System health is degraded")
            if "failed_components" in health:
                logger.warning(f"Failed components: {', '.join(health['failed_components'])}")
        else:
            logger.error("❌ System health check failed")
            
            # Save health report for later analysis
            health_file = Path.home() / '.env_mgmt' / 'health_report.json'
            with open(health_file, 'w') as f:
                json.dump(health, f, indent=2, default=str)
            
            logger.error(f"Health report saved to {health_file}")
        
        # Check disk usage
        import shutil
        usage = shutil.disk_usage(Path.home())
        usage_percent = (usage.used / usage.total) * 100
        
        if usage_percent > 90:
            logger.error(f"⚠️  Disk usage is critically high: {usage_percent:.1f}%")
        elif usage_percent > 80:
            logger.warning(f"⚠️  Disk usage is elevated: {usage_percent:.1f}%")
        else:
            logger.info(f"✅ Disk usage is normal: {usage_percent:.1f}%")
        
        return health
        
    except Exception as e:
        logger.error(f"Health monitoring failed: {e}")
        return {"status": "error", "error": str(e)}

def generate_daily_report(env_mgmt: EnvironmentManagementSystem, health_status: dict):
    """Generate daily maintenance report"""
    logger = logging.getLogger(__name__)
    logger.info("Generating daily maintenance report...")
    
    try:
        # Get system status
        status = env_mgmt.show_status()
        
        # Create report
        report = {
            "timestamp": datetime.now().isoformat(),
            "report_type": "daily_maintenance",
            "health_status": health_status,
            "system_status": status,
            "maintenance_performed": [
                "Backup rotation",
                "Secret rotation check",
                "Environment validation",
                "Log cleanup",
                "Health monitoring"
            ]
        }
        
        # Save report
        report_file = Path.home() / '.env_mgmt' / f"maintenance_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Daily maintenance report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("DAILY MAINTENANCE REPORT")
        print("="*60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"System Status: {status['system']['status']}")
        print(f"Health Status: {health_status.get('overall_status', 'unknown')}")
        print(f"Active Deployments: {status['system']['active_deployments']}")
        print(f"Recent Backups: {status['system']['recent_backups']}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")

def main():
    """Main maintenance function"""
    parser = argparse.ArgumentParser(description="Daily Maintenance for Environment Management System")
    parser.add_argument("--config-dir", help="Configuration directory")
    parser.add_argument("--backup-dir", help="Backup directory")
    parser.add_argument("--backup-rotation-days", type=int, default=30, 
                       help="Days to keep backups (default: 30)")
    parser.add_argument("--log-cleanup-days", type=int, default=30,
                       help="Days to keep logs (default: 30)")
    parser.add_argument("--health-only", action="store_true", 
                       help="Run only health monitoring")
    parser.add_argument("--validate-only", action="store_true",
                       help="Run only environment validation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting daily maintenance routine")
    
    # Initialize system
    env_mgmt = EnvironmentManagementSystem(args.config_dir, args.backup_dir)
    
    try:
        if args.health_only:
            # Run only health monitoring
            health_status = run_health_monitoring(env_mgmt)
            generate_daily_report(env_mgmt, health_status)
            
        elif args.validate_only:
            # Run only environment validation
            validate_all_environments(env_mgmt)
            
        else:
            # Run full maintenance routine
            logger.info("Running full maintenance routine")
            
            # 1. Rotate backups
            rotate_backups(env_mgmt, args.backup_rotation_days)
            
            # 2. Check secret rotation
            check_secret_rotation(env_mgmt)
            
            # 3. Validate environments
            validate_all_environments(env_mgmt)
            
            # 4. Cleanup logs
            cleanup_logs(args.log_cleanup_days)
            
            # 5. Run health monitoring
            health_status = run_health_monitoring(env_mgmt)
            
            # 6. Generate report
            generate_daily_report(env_mgmt, health_status)
        
        logger.info("Daily maintenance routine completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Maintenance routine interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Maintenance routine failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()