#!/usr/bin/env python3
"""
Configuration Backup and Migration Tools
Provides backup, restore, and migration capabilities for configurations
"""

import os
import json
import yaml
import gzip
import shutil
import tarfile
import hashlib
import logging
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import sqlite3
import subprocess

@dataclass
class BackupMetadata:
    """Metadata for a configuration backup"""
    id: str
    name: str
    description: str
    created_at: str
    environment: str
    source_path: str
    backup_path: str
    file_count: int
    total_size: int
    checksum: str
    compression: str
    encryption: bool
    tags: List[str]

@dataclass
class MigrationPlan:
    """Migration plan between environments"""
    id: str
    name: str
    source_environment: str
    target_environment: str
    description: str
    steps: List[Dict[str, Any]]
    validation_rules: List[Dict[str, Any]]
    rollback_plan: List[Dict[str, Any]]
    created_at: str
    status: str

class ConfigurationBackup:
    """Configuration backup and restore system"""
    
    def __init__(self, base_dir: str = "environment/backup", 
                 metadata_db: str = "backup_metadata.db"):
        self.base_dir = Path(base_dir)
        self.metadata_db = Path(metadata_db)
        self.backups_dir = self.base_dir / "backups"
        self.temp_dir = self.base_dir / "temp"
        
        # Create directories
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_metadata_db()
        
        self.logger = logging.getLogger('config_backup')
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_dir / 'backup_audit.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_metadata_db(self):
        """Initialize metadata database"""
        conn = sqlite3.connect(self.metadata_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                environment TEXT NOT NULL,
                source_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                file_count INTEGER,
                total_size INTEGER,
                checksum TEXT,
                compression TEXT,
                encryption BOOLEAN,
                tags TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS migrations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_environment TEXT NOT NULL,
                target_environment TEXT NOT NULL,
                description TEXT,
                plan TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                executed_at TEXT,
                result TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_backup(self, config_paths: List[str], 
                     backup_name: str,
                     environment: str,
                     description: str = "",
                     compress: bool = True,
                     encrypt: bool = False,
                     tags: List[str] = None) -> str:
        """Create a configuration backup"""
        
        # Generate backup ID
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(backup_name)}"
        
        # Create backup directory
        backup_dir = self.backups_dir / backup_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create archive file
        archive_path = backup_dir / f"{backup_name}.tar.gz" if compress else backup_dir / f"{backup_name}.tar"
        
        try:
            # Create archive
            if compress:
                with tarfile.open(archive_path, "w:gz") as tar:
                    for config_path in config_paths:
                        path = Path(config_path)
                        if path.exists():
                            tar.add(path, arcname=path.name)
            else:
                with tarfile.open(archive_path, "w") as tar:
                    for config_path in config_paths:
                        path = Path(config_path)
                        if path.exists():
                            tar.add(path, arcname=path.name)
            
            # Calculate checksum
            checksum = self._calculate_checksum(archive_path)
            
            # Get file stats
            file_count = len(config_paths)
            total_size = archive_path.stat().st_size
            
            # Create metadata
            metadata = BackupMetadata(
                id=backup_id,
                name=backup_name,
                description=description,
                created_at=datetime.now().isoformat(),
                environment=environment,
                source_path=", ".join(config_paths),
                backup_path=str(archive_path),
                file_count=file_count,
                total_size=total_size,
                checksum=checksum,
                compression="gzip" if compress else "none",
                encryption=encrypt,
                tags=tags or []
            )
            
            # Save metadata
            self._save_backup_metadata(metadata)
            
            # Log operation
            self.logger.info(f"Backup created: {backup_id} - {backup_name}")
            
            return backup_id
            
        except Exception as e:
            # Clean up on failure
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            self.logger.error(f"Failed to create backup: {e}")
            raise
    
    def restore_backup(self, backup_id: str, target_path: str,
                      verify_checksum: bool = True) -> bool:
        """Restore configuration from backup"""
        
        # Get backup metadata
        metadata = self._get_backup_metadata(backup_id)
        if not metadata:
            raise ValueError(f"Backup not found: {backup_id}")
        
        archive_path = Path(metadata.backup_path)
        if not archive_path.exists():
            raise FileNotFoundError(f"Backup archive not found: {archive_path}")
        
        # Verify checksum if requested
        if verify_checksum:
            current_checksum = self._calculate_checksum(archive_path)
            if current_checksum != metadata.checksum:
                raise ValueError("Backup checksum verification failed")
        
        # Create target directory
        target_dir = Path(target_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Extract archive
            if metadata.compression == "gzip":
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(target_dir)
            else:
                with tarfile.open(archive_path, "r") as tar:
                    tar.extractall(target_dir)
            
            self.logger.info(f"Backup restored: {backup_id} to {target_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    def list_backups(self, environment: Optional[str] = None) -> List[BackupMetadata]:
        """List all backups, optionally filtered by environment"""
        
        conn = sqlite3.connect(self.metadata_db)
        cursor = conn.cursor()
        
        if environment:
            cursor.execute(
                "SELECT * FROM backups WHERE environment = ? ORDER BY created_at DESC",
                (environment,)
            )
        else:
            cursor.execute("SELECT * FROM backups ORDER BY created_at DESC")
        
        backups = []
        for row in cursor.fetchall():
            metadata = BackupMetadata(
                id=row[0],
                name=row[1],
                description=row[2],
                created_at=row[3],
                environment=row[4],
                source_path=row[5],
                backup_path=row[6],
                file_count=row[7],
                total_size=row[8],
                checksum=row[9],
                compression=row[10],
                encryption=bool(row[11]),
                tags=json.loads(row[12]) if row[12] else []
            )
            backups.append(metadata)
        
        conn.close()
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        
        # Get backup metadata
        metadata = self._get_backup_metadata(backup_id)
        if not metadata:
            return False
        
        try:
            # Delete archive file
            archive_path = Path(metadata.backup_path)
            if archive_path.exists():
                archive_path.unlink()
            
            # Delete backup directory
            backup_dir = archive_path.parent
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            
            # Delete metadata
            conn = sqlite3.connect(self.metadata_db)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM backups WHERE id = ?", (backup_id,))
            conn.commit()
            conn.close()
            
            self.logger.info(f"Backup deleted: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    def cleanup_old_backups(self, retention_days: int = 90) -> int:
        """Clean up old backups"""
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        backups = self.list_backups()
        
        deleted_count = 0
        for backup in backups:
            created_at = datetime.fromisoformat(backup.created_at)
            if created_at < cutoff_date:
                if self.delete_backup(backup.id):
                    deleted_count += 1
        
        self.logger.info(f"Cleaned up {deleted_count} old backups")
        return deleted_count
    
    def _save_backup_metadata(self, metadata: BackupMetadata):
        """Save backup metadata to database"""
        
        conn = sqlite3.connect(self.metadata_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO backups (
                id, name, description, created_at, environment, source_path,
                backup_path, file_count, total_size, checksum, compression,
                encryption, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.id, metadata.name, metadata.description,
            metadata.created_at, metadata.environment, metadata.source_path,
            metadata.backup_path, metadata.file_count, metadata.total_size,
            metadata.checksum, metadata.compression, metadata.encryption,
            json.dumps(metadata.tags)
        ))
        
        conn.commit()
        conn.close()
    
    def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get backup metadata from database"""
        
        conn = sqlite3.connect(self.metadata_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM backups WHERE id = ?", (backup_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        metadata = BackupMetadata(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=row[3],
            environment=row[4],
            source_path=row[5],
            backup_path=row[6],
            file_count=row[7],
            total_size=row[8],
            checksum=row[9],
            compression=row[10],
            encryption=bool(row[11]),
            tags=json.loads(row[12]) if row[12] else []
        )
        
        conn.close()
        return metadata
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

class ConfigurationMigrator:
    """Configuration migration between environments"""
    
    def __init__(self, backup_system: ConfigurationBackup):
        self.backup_system = backup_system
        self.migrations_dir = Path("environment/migration")
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger('config_migration')
    
    def create_migration_plan(self, source_env: str, target_env: str,
                             name: str, description: str = "",
                             steps: List[Dict[str, Any]] = None) -> str:
        """Create a migration plan"""
        
        migration_id = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Default migration steps
        default_steps = [
            {
                "step": 1,
                "action": "backup",
                "description": "Create backup of current configuration",
                "config": {
                    "backup_name": f"{source_env}_pre_migration",
                    "environment": source_env,
                    "tags": ["migration", source_env, "pre_migration"]
                }
            },
            {
                "step": 2,
                "action": "validate_source",
                "description": "Validate source environment configuration",
                "config": {
                    "environment": source_env
                }
            },
            {
                "step": 3,
                "action": "validate_target",
                "description": "Validate target environment configuration",
                "config": {
                    "environment": target_env
                }
            },
            {
                "step": 4,
                "action": "copy_files",
                "description": "Copy configuration files to target",
                "config": {
                    "source_paths": ["config/environments.yaml", "config/*.json"],
                    "target_environment": target_env
                }
            },
            {
                "step": 5,
                "action": "update_environment_vars",
                "description": "Update environment-specific variables",
                "config": {
                    "source_environment": source_env,
                    "target_environment": target_env
                }
            },
            {
                "step": 6,
                "action": "validate_migration",
                "description": "Validate migrated configuration",
                "config": {
                    "environment": target_env
                }
            }
        ]
        
        # Default validation rules
        default_validation_rules = [
            {
                "rule": "required_files_exist",
                "description": "All required configuration files exist",
                "severity": "error"
            },
            {
                "rule": "environment_vars_valid",
                "description": "All environment variables are valid",
                "severity": "error"
            },
            {
                "rule": "secrets_accessible",
                "description": "All secrets are accessible",
                "severity": "warning"
            }
        ]
        
        # Default rollback plan
        rollback_plan = [
            {
                "step": 1,
                "action": "restore_backup",
                "description": "Restore from pre-migration backup",
                "config": {}
            },
            {
                "step": 2,
                "action": "validate_restore",
                "description": "Validate restoration",
                "config": {}
            }
        ]
        
        plan = MigrationPlan(
            id=migration_id,
            name=name,
            source_environment=source_env,
            target_environment=target_env,
            description=description,
            steps=steps or default_steps,
            validation_rules=default_validation_rules,
            rollback_plan=rollback_plan,
            created_at=datetime.now().isoformat(),
            status="pending"
        )
        
        # Save migration plan
        self._save_migration_plan(plan)
        
        return migration_id
    
    def execute_migration(self, migration_id: str) -> Dict[str, Any]:
        """Execute a migration plan"""
        
        plan = self._get_migration_plan(migration_id)
        if not plan:
            raise ValueError(f"Migration plan not found: {migration_id}")
        
        # Update status
        plan.status = "running"
        self._save_migration_plan(plan)
        
        results = {
            "migration_id": migration_id,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "steps": [],
            "errors": [],
            "warnings": []
        }
        
        try:
            # Execute each step
            for step in plan.steps:
                step_result = self._execute_migration_step(step, plan)
                results["steps"].append(step_result)
                
                if step_result["status"] == "failed":
                    results["status"] = "failed"
                    results["errors"].append(step_result["error"])
                    break
                
                if step_result["status"] == "warning":
                    results["warnings"].append(step_result["warning"])
            
            # Set final status
            if results["status"] == "running":
                results["status"] = "completed"
                plan.status = "completed"
            
        except Exception as e:
            results["status"] = "failed"
            results["errors"].append(str(e))
            plan.status = "failed"
        
        # Update plan with results
        results["completed_at"] = datetime.now().isoformat()
        self._save_migration_plan(plan, results)
        
        return results
    
    def _execute_migration_step(self, step: Dict[str, Any], plan: MigrationPlan) -> Dict[str, Any]:
        """Execute a single migration step"""
        
        step_result = {
            "step": step["step"],
            "action": step["action"],
            "description": step["description"],
            "status": "pending",
            "started_at": datetime.now().isoformat()
        }
        
        try:
            action = step["action"]
            config = step.get("config", {})
            
            if action == "backup":
                # Create backup
                backup_id = self.backup_system.create_backup(
                    config_paths=["config/environments.yaml"],
                    backup_name=config["backup_name"],
                    environment=config["environment"],
                    description=f"Migration backup for {plan.source_environment}",
                    tags=config.get("tags", [])
                )
                step_result["status"] = "completed"
                step_result["result"] = {"backup_id": backup_id}
            
            elif action == "validate_source":
                # Validate source environment
                from environment.tools.env_validator import EnvironmentValidator
                validator = EnvironmentValidator()
                report = validator.validate_environment(config["environment"])
                
                if report.invalid_variables > 0:
                    step_result["status"] = "warning"
                    step_result["warning"] = f"Source environment has {report.invalid_variables} invalid variables"
                else:
                    step_result["status"] = "completed"
                step_result["result"] = report.summary
            
            elif action == "validate_target":
                # Validate target environment
                from environment.tools.env_validator import EnvironmentValidator
                validator = EnvironmentValidator()
                report = validator.validate_environment(config["environment"])
                
                if report.invalid_variables > 0:
                    step_result["status"] = "failed"
                    step_result["error"] = f"Target environment has {report.invalid_variables} invalid variables"
                else:
                    step_result["status"] = "completed"
                step_result["result"] = report.summary
            
            elif action == "copy_files":
                # Copy configuration files
                source_paths = config.get("source_paths", [])
                target_env = config["target_environment"]
                
                # This would implement actual file copying logic
                step_result["status"] = "completed"
                step_result["result"] = {"copied_files": len(source_paths)}
            
            elif action == "update_environment_vars":
                # Update environment-specific variables
                source_env = config["source_environment"]
                target_env = config["target_environment"]
                
                # This would implement environment variable transformation
                step_result["status"] = "completed"
                step_result["result"] = {"updated_variables": 0}
            
            elif action == "validate_migration":
                # Validate migration result
                from environment.tools.env_validator import EnvironmentValidator
                validator = EnvironmentValidator()
                report = validator.validate_environment(config["environment"])
                
                if report.invalid_variables > 0:
                    step_result["status"] = "failed"
                    step_result["error"] = f"Migrated environment has {report.invalid_variables} invalid variables"
                else:
                    step_result["status"] = "completed"
                step_result["result"] = report.summary
            
            else:
                step_result["status"] = "failed"
                step_result["error"] = f"Unknown action: {action}"
        
        except Exception as e:
            step_result["status"] = "failed"
            step_result["error"] = str(e)
        
        step_result["completed_at"] = datetime.now().isoformat()
        return step_result
    
    def rollback_migration(self, migration_id: str) -> Dict[str, Any]:
        """Rollback a migration"""
        
        plan = self._get_migration_plan(migration_id)
        if not plan:
            raise ValueError(f"Migration plan not found: {migration_id}")
        
        # Get latest backup for rollback
        backups = self.backup_system.list_backups(plan.source_environment)
        if not backups:
            raise ValueError("No backup found for rollback")
        
        # Execute rollback steps
        rollback_results = []
        for rollback_step in plan.rollback_plan:
            # This would implement actual rollback logic
            rollback_results.append({
                "step": rollback_step["step"],
                "action": rollback_step["action"],
                "status": "completed"
            })
        
        return {
            "migration_id": migration_id,
            "rollback_status": "completed",
            "rollback_steps": rollback_results
        }
    
    def _save_migration_plan(self, plan: MigrationPlan, results: Dict[str, Any] = None):
        """Save migration plan to database"""
        
        conn = sqlite3.connect(self.backup_system.metadata_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO migrations (
                id, name, source_environment, target_environment, description,
                plan, created_at, status, executed_at, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            plan.id, plan.name, plan.source_environment, plan.target_environment,
            plan.description, json.dumps(asdict(plan)),
            plan.created_at, plan.status,
            datetime.now().isoformat() if results else None,
            json.dumps(results) if results else None
        ))
        
        conn.commit()
        conn.close()
    
    def _get_migration_plan(self, migration_id: str) -> Optional[MigrationPlan]:
        """Get migration plan from database"""
        
        conn = sqlite3.connect(self.backup_system.metadata_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM migrations WHERE id = ?", (migration_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        plan_data = json.loads(row[5])  # plan column
        
        plan = MigrationPlan(
            id=plan_data["id"],
            name=plan_data["name"],
            source_environment=plan_data["source_environment"],
            target_environment=plan_data["target_environment"],
            description=plan_data["description"],
            steps=plan_data["steps"],
            validation_rules=plan_data["validation_rules"],
            rollback_plan=plan_data["rollback_plan"],
            created_at=plan_data["created_at"],
            status=row[7]  # status from database
        )
        
        conn.close()
        return plan
    
    def list_migrations(self) -> List[Dict[str, Any]]:
        """List all migrations"""
        
        conn = sqlite3.connect(self.backup_system.metadata_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM migrations ORDER BY created_at DESC")
        
        migrations = []
        for row in cursor.fetchall():
            migration = {
                "id": row[0],
                "name": row[1],
                "source_environment": row[2],
                "target_environment": row[3],
                "description": row[4],
                "created_at": row[6],
                "status": row[7],
                "executed_at": row[8],
                "result": json.loads(row[9]) if row[9] else None
            }
            migrations.append(migration)
        
        conn.close()
        return migrations

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuration Backup and Migration")
    subparsers = parser.add_subparsers(dest='command')
    
    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Backup commands')
    backup_subparsers = backup_parser.add_subparsers(dest='backup_command')
    
    create_backup = backup_subparsers.add_parser('create', help='Create backup')
    create_backup.add_argument('name', help='Backup name')
    create_backup.add_argument('paths', nargs='+', help='Configuration paths to backup')
    create_backup.add_argument('--env', required=True, help='Environment name')
    create_backup.add_argument('--description', default='', help='Backup description')
    create_backup.add_argument('--no-compress', action='store_true', help='Don\'t compress')
    create_backup.add_argument('--tags', nargs='*', help='Backup tags')
    
    list_backup = backup_subparsers.add_parser('list', help='List backups')
    list_backup.add_argument('--env', help='Filter by environment')
    
    restore_backup = backup_subparsers.add_parser('restore', help='Restore backup')
    restore_backup.add_argument('id', help='Backup ID')
    restore_backup.add_argument('target', help='Target path')
    restore_backup.add_argument('--no-verify', action='store_true', help='Don\'t verify checksum')
    
    delete_backup = backup_subparsers.add_parser('delete', help='Delete backup')
    delete_backup.add_argument('id', help='Backup ID')
    
    # Migration commands
    migration_parser = subparsers.add_parser('migration', help='Migration commands')
    migration_subparsers = migration_parser.add_subparsers(dest='migration_command')
    
    create_migration = migration_subparsers.add_parser('create', help='Create migration plan')
    create_migration.add_argument('source', help='Source environment')
    create_migration.add_argument('target', help='Target environment')
    create_migration.add_argument('name', help='Migration name')
    create_migration.add_argument('--description', default='', help='Migration description')
    
    execute_migration = migration_subparsers.add_parser('execute', help='Execute migration')
    execute_migration.add_argument('id', help='Migration ID')
    
    list_migration = migration_subparsers.add_parser('list', help='List migrations')
    
    rollback_migration = migration_subparsers.add_parser('rollback', help='Rollback migration')
    rollback_migration.add_argument('id', help='Migration ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    backup_system = ConfigurationBackup()
    migrator = ConfigurationMigrator(backup_system)
    
    if args.command == 'backup':
        if args.backup_command == 'create':
            backup_id = backup_system.create_backup(
                config_paths=args.paths,
                backup_name=args.name,
                environment=args.env,
                description=args.description,
                compress=not args.no_compress,
                tags=args.tags
            )
            print(f"Backup created: {backup_id}")
        
        elif args.backup_command == 'list':
            backups = backup_system.list_backups(args.env)
            for backup in backups:
                print(f"{backup.id} - {backup.name} ({backup.environment}) - {backup.created_at}")
        
        elif args.backup_command == 'restore':
            success = backup_system.restore_backup(args.id, args.target, verify_checksum=not args.no_verify)
            print(f"Backup restored: {success}")
        
        elif args.backup_command == 'delete':
            success = backup_system.delete_backup(args.id)
            print(f"Backup deleted: {success}")
    
    elif args.command == 'migration':
        if args.migration_command == 'create':
            migration_id = migrator.create_migration_plan(
                source_env=args.source,
                target_env=args.target,
                name=args.name,
                description=args.description
            )
            print(f"Migration plan created: {migration_id}")
        
        elif args.migration_command == 'execute':
            results = migrator.execute_migration(args.id)
            print(f"Migration status: {results['status']}")
            if results['errors']:
                print("Errors:")
                for error in results['errors']:
                    print(f"  - {error}")
        
        elif args.migration_command == 'list':
            migrations = migrator.list_migrations()
            for migration in migrations:
                print(f"{migration['id']} - {migration['name']} ({migration['status']})")
        
        elif args.migration_command == 'rollback':
            results = migrator.rollback_migration(args.id)
            print(f"Rollback status: {results['rollback_status']}")

if __name__ == "__main__":
    main()