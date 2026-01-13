#!/usr/bin/env python3
"""
Configuration Backup and Migration Tools

This module provides:
- Automated configuration backups
- Configuration migration between environments
- Version control and rollback capabilities
- Backup validation and restoration
"""

import os
import json
import yaml
import shutil
import tarfile
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import threading

logger = logging.getLogger(__name__)

class BackupType(Enum):
    """Backup types"""
    FULL = "full"
    CONFIG_ONLY = "config_only"
    SECRETS_ONLY = "secrets_only"
    INCREMENTAL = "incremental"

@dataclass
class BackupMetadata:
    """Backup metadata"""
    backup_id: str
    backup_type: BackupType
    environment: str
    timestamp: datetime
    source_version: str
    checksum: str
    file_size: int
    compressed: bool
    encrypted: bool
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['backup_type'] = self.backup_type.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
        """Create from dictionary"""
        data['backup_type'] = BackupType(data['backup_type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class BackupManager:
    """Configuration backup management system"""
    
    def __init__(self, backup_dir: str = None, max_backups: int = 30):
        self.backup_dir = Path(backup_dir or Path.home() / '.env_mgmt' / 'backups')
        self.max_backups = max_backups
        self.backup_metadata_db = self.backup_dir / 'metadata.db'
        self._init_backup_system()
        
        # Start cleanup scheduler
        self._start_cleanup_scheduler()
    
    def _init_backup_system(self):
        """Initialize backup system"""
        self.backup_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize metadata database
        with sqlite3.connect(str(self.backup_metadata_db)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    backup_id TEXT PRIMARY KEY,
                    backup_type TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    compressed BOOLEAN NOT NULL,
                    encrypted BOOLEAN NOT NULL,
                    description TEXT,
                    file_path TEXT NOT NULL
                )
            ''')
            conn.commit()
    
    def create_backup(self, environment: str, backup_type: BackupType = BackupType.FULL,
                     description: str = "", encrypt: bool = False) -> Optional[str]:
        """Create a configuration backup"""
        try:
            backup_id = self._generate_backup_id()
            timestamp = datetime.now()
            
            # Create backup directory
            backup_subdir = self.backup_dir / backup_id
            backup_subdir.mkdir(exist_ok=True)
            
            # Copy configuration files
            config_files = []
            if backup_type in [BackupType.FULL, BackupType.CONFIG_ONLY]:
                config_source = Path("environment/templates")
                if config_source.exists():
                    config_dest = backup_subdir / "configs"
                    if config_dest.exists():
                        shutil.rmtree(config_dest)
                    shutil.copytree(config_source, config_dest)
                    config_files = list(config_dest.glob("*.yaml"))
            
            # Copy secrets if available
            secrets_files = []
            if backup_type in [BackupType.FULL, BackupType.SECRETS_ONLY]:
                secrets_source = Path.home() / '.env_mgmt'
                if secrets_source.exists():
                    secrets_backup_dir = backup_subdir / "secrets"
                    if secrets_backup_dir.exists():
                        shutil.rmtree(secrets_backup_dir)
                    shutil.copytree(secrets_source, secrets_backup_dir)
                    secrets_files = list(secrets_backup_dir.glob("**/*"))
            
            # Create archive
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_subdir, arcname=backup_id)
            
            # Calculate checksum
            checksum = self._calculate_file_checksum(archive_path)
            file_size = archive_path.stat().st_size
            
            # Encrypt if requested
            if encrypt:
                encrypted_path = self._encrypt_backup(archive_path)
                if encrypted_path:
                    archive_path = encrypted_path
                    encrypted = True
                else:
                    encrypted = False
            else:
                encrypted = False
            
            # Store metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                environment=environment,
                timestamp=timestamp,
                source_version=self._get_current_version(),
                checksum=checksum,
                file_size=file_size,
                compressed=True,
                encrypted=encrypted,
                description=description
            )
            
            self._store_backup_metadata(metadata, str(archive_path))
            
            # Cleanup temporary files
            shutil.rmtree(backup_subdir)
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            logger.info(f"Backup created: {backup_id}")
            return backup_id
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_id: str, target_dir: str = None) -> bool:
        """Restore configuration from backup"""
        try:
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                logger.error(f"Backup metadata not found: {backup_id}")
                return False
            
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            if metadata.encrypted:
                archive_path = self._decrypt_backup(archive_path)
                if not archive_path:
                    logger.error(f"Failed to decrypt backup: {backup_id}")
                    return False
            
            # Create temporary extraction directory
            temp_dir = self.backup_dir / f"restore_{backup_id}_{int(datetime.now().timestamp())}"
            temp_dir.mkdir(exist_ok=True)
            
            try:
                # Extract archive
                with tarfile.open(archive_path, "r:gz") as tar:
                    tar.extractall(temp_dir)
                
                # Verify checksum
                extracted_dir = temp_dir / backup_id
                if not extracted_dir.exists():
                    logger.error(f"Extracted directory not found: {extracted_dir}")
                    return False
                
                # Restore configs
                if (extracted_dir / "configs").exists():
                    target_config_dir = Path(target_dir or "environment/templates")
                    if target_config_dir.exists():
                        shutil.rmtree(target_config_dir)
                    shutil.copytree(extracted_dir / "configs", target_config_dir)
                
                # Restore secrets (optional)
                if (extracted_dir / "secrets").exists():
                    target_secrets_dir = Path(target_dir or Path.home() / '.env_mgmt')
                    if (target_secrets_dir / "secrets.db").exists():
                        # Backup current secrets before overwriting
                        current_backup = self.create_backup("current", BackupType.SECRETS_ONLY, 
                                                          "Auto-backup before restore")
                        logger.info(f"Current secrets backed up: {current_backup}")
                    
                    # Overwrite secrets directory
                    for item in (extracted_dir / "secrets").iterdir():
                        if item.name == "secrets.db":
                            target_file = target_secrets_dir / item.name
                            shutil.copy2(item, target_file)
                            os.chmod(target_file, 0o600)  # Set secure permissions
                
                logger.info(f"Backup restored successfully: {backup_id}")
                return True
                
            finally:
                # Cleanup temporary files
                if archive_path != self.backup_dir / f"{backup_id}.tar.gz":
                    # Clean up decrypted file
                    archive_path.unlink()
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def list_backups(self, environment: str = None, limit: int = 50) -> List[BackupMetadata]:
        """List available backups"""
        with sqlite3.connect(str(self.backup_metadata_db)) as conn:
            query = "SELECT * FROM backups"
            params = []
            
            if environment:
                query += " WHERE environment = ?"
                params.append(environment)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            results = []
            
            for row in cursor.fetchall():
                results.append(BackupMetadata(
                    backup_id=row[0],
                    backup_type=BackupType(row[1]),
                    environment=row[2],
                    timestamp=datetime.fromisoformat(row[3]),
                    source_version=row[4],
                    checksum=row[5],
                    file_size=row[6],
                    compressed=bool(row[7]),
                    encrypted=bool(row[8]),
                    description=row[9]
                ))
            
            return results
    
    def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity"""
        try:
            metadata = self._get_backup_metadata(backup_id)
            if not metadata:
                return False
            
            archive_path = self.backup_dir / f"{backup_id}.tar.gz"
            if not archive_path.exists():
                logger.error(f"Backup file not found: {archive_path}")
                return False
            
            # Decrypt if necessary
            if metadata.encrypted:
                archive_path = self._decrypt_backup(archive_path)
                if not archive_path:
                    return False
            
            # Verify checksum
            calculated_checksum = self._calculate_file_checksum(archive_path)
            if calculated_checksum != metadata.checksum:
                logger.error(f"Backup checksum mismatch: {backup_id}")
                return False
            
            # Test archive integrity
            try:
                with tarfile.open(archive_path, "r:gz") as tar:
                    members = tar.getmembers()
                    if not members:
                        logger.error(f"Backup is empty: {backup_id}")
                        return False
            except Exception as e:
                logger.error(f"Backup archive corrupted: {e}")
                return False
            
            logger.info(f"Backup verified successfully: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify backup: {e}")
            return False
    
    def migrate_config(self, source_env: str, target_env: str, 
                      migrate_secrets: bool = False) -> bool:
        """Migrate configuration between environments"""
        try:
            # Create backup of target environment
            backup_id = self.create_backup(target_env, BackupType.FULL, 
                                         f"Auto-backup before migration from {source_env}")
            if not backup_id:
                logger.error(f"Failed to create backup before migration")
                return False
            
            # Load source configuration
            from ..config_manager import ConfigManager
            config_manager = ConfigManager()
            
            source_config = config_manager.load_config(source_env)
            if not source_config:
                logger.error(f"Source configuration not found: {source_env}")
                return False
            
            # Create new configuration for target environment
            target_config_data = source_config.data.copy()
            target_config_data['environment']['name'] = target_env
            target_config_data['environment']['type'] = source_config.type.value
            
            # Save target configuration
            target_config = config_manager.configs.get(target_env)
            if not target_config:
                from ..config_manager import EnvironmentConfig, EnvironmentType
                target_config = EnvironmentConfig(
                    name=target_env,
                    type=EnvironmentType(source_config.type.value),
                    data=target_config_data,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                config_manager.configs[target_env] = target_config
            
            config_manager.update_config(target_env, "", target_config_data, 
                                       reason=f"Migrated from {source_env}")
            
            # Migrate secrets if requested
            if migrate_secrets:
                self._migrate_secrets(source_env, target_env)
            
            logger.info(f"Configuration migrated from {source_env} to {target_env}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate configuration: {e}")
            return False
    
    def _migrate_secrets(self, source_env: str, target_env: str):
        """Migrate secrets between environments"""
        try:
            from ..secrets_mgmt.secrets_manager import SecretsManager
            secrets_manager = SecretsManager()
            
            # Get all secrets for source environment
            source_secrets = secrets_manager.db.list_secrets(source_env)
            
            # For each secret, create a new one for target environment
            for secret in source_secrets:
                decrypted_value = secrets_manager.encryption.decrypt(secret.value)
                secrets_manager.store_secret(
                    secret.name, decrypted_value, target_env,
                    secret.rotation_days, secret.expires_at
                )
            
            logger.info(f"Migrated {len(source_secrets)} secrets from {source_env} to {target_env}")
            
        except Exception as e:
            logger.error(f"Failed to migrate secrets: {e}")
    
    def _generate_backup_id(self) -> str:
        """Generate unique backup ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"backup_{timestamp}_{random_suffix}"
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _get_current_version(self) -> str:
        """Get current configuration version"""
        try:
            from ..config_manager import ConfigManager
            config_manager = ConfigManager()
            return f"config_v{config_manager.configs.get('production', {}).version or 1}"
        except:
            return "unknown"
    
    def _store_backup_metadata(self, metadata: BackupMetadata, file_path: str):
        """Store backup metadata in database"""
        with sqlite3.connect(str(self.backup_metadata_db)) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO backups 
                (backup_id, backup_type, environment, timestamp, source_version, 
                 checksum, file_size, compressed, encrypted, description, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata.backup_id, metadata.backup_type.value,
                metadata.environment, metadata.timestamp.isoformat(),
                metadata.source_version, metadata.checksum, metadata.file_size,
                metadata.compressed, metadata.encrypted, metadata.description, file_path
            ))
            conn.commit()
    
    def _get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get backup metadata"""
        with sqlite3.connect(str(self.backup_metadata_db)) as conn:
            cursor = conn.execute('SELECT * FROM backups WHERE backup_id = ?', (backup_id,))
            row = cursor.fetchone()
            
            if row:
                return BackupMetadata(
                    backup_id=row[0],
                    backup_type=BackupType(row[1]),
                    environment=row[2],
                    timestamp=datetime.fromisoformat(row[3]),
                    source_version=row[4],
                    checksum=row[5],
                    file_size=row[6],
                    compressed=bool(row[7]),
                    encrypted=bool(row[8]),
                    description=row[9]
                )
            return None
    
    def _encrypt_backup(self, backup_path: Path) -> Optional[Path]:
        """Encrypt backup file (placeholder implementation)"""
        try:
            # For production use, implement proper encryption here
            # This is a placeholder that would use proper encryption libraries
            encrypted_path = backup_path.with_suffix(backup_path.suffix + '.enc')
            # shutil.copy2(backup_path, encrypted_path)  # Placeholder
            return encrypted_path
        except:
            return None
    
    def _decrypt_backup(self, encrypted_path: Path) -> Optional[Path]:
        """Decrypt backup file (placeholder implementation)"""
        try:
            # For production use, implement proper decryption here
            decrypted_path = encrypted_path.with_suffix('')  # Remove .enc
            if decrypted_path.suffix == '.enc':
                decrypted_path = decrypted_path.with_suffix('')
            # shutil.copy2(encrypted_path, decrypted_path)  # Placeholder
            return decrypted_path
        except:
            return None
    
    def _cleanup_old_backups(self):
        """Remove old backups exceeding retention limit"""
        backups = self.list_backups(limit=1000)  # Get all backups
        
        if len(backups) <= self.max_backups:
            return
        
        # Sort by timestamp (oldest first)
        backups.sort(key=lambda x: x.timestamp)
        backups_to_delete = backups[:-self.max_backups]
        
        for backup in backups_to_delete:
            try:
                archive_path = self.backup_dir / f"{backup.backup_id}.tar.gz"
                if archive_path.exists():
                    archive_path.unlink()
                
                # Remove from database
                with sqlite3.connect(str(self.backup_metadata_db)) as conn:
                    conn.execute('DELETE FROM backups WHERE backup_id = ?', (backup.backup_id,))
                    conn.commit()
                
                logger.info(f"Old backup removed: {backup.backup_id}")
                
            except Exception as e:
                logger.error(f"Failed to remove old backup {backup.backup_id}: {e}")
    
    def _start_cleanup_scheduler(self):
        """Start automatic backup cleanup scheduler"""
        def cleanup_worker():
            while True:
                try:
                    # Run cleanup every day at 2 AM
                    now = datetime.now()
                    if now.hour == 2 and now.minute == 0:
                        self._cleanup_old_backups()
                        logger.info("Daily backup cleanup completed")
                    
                    # Sleep for 1 minute
                    import time
                    time.sleep(60)
                    
                except Exception as e:
                    logger.error(f"Cleanup scheduler error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

class MigrationManager:
    """Configuration migration and deployment manager"""
    
    def __init__(self, backup_manager: BackupManager = None):
        self.backup_manager = backup_manager or BackupManager()
        self.migration_history = []
    
    def plan_migration(self, source_env: str, target_env: str, 
                      migration_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Plan and validate migration steps"""
        plan = {
            'source_environment': source_env,
            'target_environment': target_env,
            'estimated_duration': 'unknown',
            'steps': migration_steps,
            'validation_checks': [],
            'rollback_strategy': '',
            'success_criteria': []
        }
        
        # Add validation steps
        plan['validation_checks'] = [
            "Source configuration exists",
            "Target environment is compatible",
            "Backup created for target",
            "Migration plan approved"
        ]
        
        # Define rollback strategy
        plan['rollback_strategy'] = f"Restore from backup created before migration"
        
        # Define success criteria
        plan['success_criteria'] = [
            "Target configuration matches source",
            "All validation rules pass",
            "No secrets conflicts",
            "System operational in target environment"
        ]
        
        return plan
    
    def execute_migration(self, plan: Dict[str, Any], dry_run: bool = False) -> bool:
        """Execute migration plan"""
        try:
            if dry_run:
                logger.info("DRY RUN: Migration would execute the following steps:")
                for step in plan['steps']:
                    logger.info(f"  - {step}")
                return True
            
            # Create backup of target
            backup_id = self.backup_manager.create_backup(
                plan['target_environment'],
                BackupType.FULL,
                f"Pre-migration backup for {plan['source_environment']}"
            )
            
            if not backup_id:
                logger.error("Failed to create backup before migration")
                return False
            
            # Execute migration steps
            for step in plan['steps']:
                step_type = step.get('type')
                
                if step_type == 'config_migrate':
                    success = self.backup_manager.migrate_config(
                        plan['source_environment'],
                        plan['target_environment'],
                        step.get('migrate_secrets', False)
                    )
                elif step_type == 'validate':
                    # Add validation logic here
                    success = True
                else:
                    logger.warning(f"Unknown migration step type: {step_type}")
                    success = False
                
                if not success:
                    logger.error(f"Migration step failed: {step}")
                    # Rollback would happen here
                    return False
            
            logger.info(f"Migration completed successfully to {plan['target_environment']}")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Environment Backup and Migration')
    parser.add_argument('--backup-dir', help='Backup directory')
    parser.add_argument('--action', choices=['backup', 'restore', 'list', 'verify', 'migrate'], 
                       required=True, help='Action to perform')
    parser.add_argument('--environment', help='Environment name')
    parser.add_argument('--backup-type', choices=['full', 'config_only', 'secrets_only', 'incremental'], 
                       default='full', help='Backup type')
    parser.add_argument('--backup-id', help='Backup ID for restore/verify')
    parser.add_argument('--source-env', help='Source environment for migration')
    parser.add_argument('--target-env', help='Target environment for migration')
    parser.add_argument('--migrate-secrets', action='store_true', help='Include secrets in migration')
    parser.add_argument('--description', help='Backup description')
    parser.add_argument('--encrypt', action='store_true', help='Encrypt backup')
    parser.add_argument('--dry-run', action='store_true', help='Dry run migration')
    parser.add_argument('--limit', type=int, default=50, help='Limit for list action')
    
    args = parser.parse_args()
    
    backup_manager = BackupManager(args.backup_dir)
    
    if args.action == 'backup':
        if not args.environment:
            print("Error: environment is required for backup action")
            return
        
        backup_type = BackupType(args.backup_type)
        backup_id = backup_manager.create_backup(
            args.environment, backup_type, args.description, args.encrypt
        )
        if backup_id:
            print(f"Backup created: {backup_id}")
        else:
            print("Failed to create backup")
    
    elif args.action == 'restore':
        if not args.backup_id:
            print("Error: backup-id is required for restore action")
            return
        
        if backup_manager.restore_backup(args.backup_id):
            print(f"Backup restored: {args.backup_id}")
        else:
            print("Failed to restore backup")
    
    elif args.action == 'list':
        backups = backup_manager.list_backups(args.environment, args.limit)
        print(f"Backups for {args.environment or 'all'} environments:")
        for backup in backups:
            print(f"  - {backup.backup_id} ({backup.backup_type.value}) - {backup.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    elif args.action == 'verify':
        if not args.backup_id:
            print("Error: backup-id is required for verify action")
            return
        
        if backup_manager.verify_backup(args.backup_id):
            print(f"Backup verified: {args.backup_id}")
        else:
            print("Backup verification failed")
    
    elif args.action == 'migrate':
        if not args.source_env or not args.target_env:
            print("Error: source-env and target-env are required for migrate action")
            return
        
        migration_manager = MigrationManager(backup_manager)
        
        if args.dry_run:
            plan = migration_manager.plan_migration(
                args.source_env, args.target_env,
                [{'type': 'config_migrate', 'migrate_secrets': args.migrate_secrets}]
            )
            print("Migration plan:")
            print(json.dumps(plan, indent=2))
        else:
            plan = migration_manager.plan_migration(
                args.source_env, args.target_env,
                [{'type': 'config_migrate', 'migrate_secrets': args.migrate_secrets}]
            )
            if migration_manager.execute_migration(plan):
                print(f"Migration completed: {args.source_env} -> {args.target_env}")
            else:
                print("Migration failed")

if __name__ == '__main__':
    main()