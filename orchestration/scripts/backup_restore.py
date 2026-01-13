#!/usr/bin/env python3
"""
Backup and Restore System
Comprehensive backup and restore procedures for all data stores
"""

import os
import sys
import json
import yaml
import shutil
import tarfile
import gzip
import sqlite3
import subprocess
import logging
import hashlib
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import threading
import time

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class BackupTarget:
    name: str
    path: str
    type: str  # directory, database, redis, file
    compression: bool = True
    encrypted: bool = False
    retention_days: int = 30

class BackupRestoreSystem:
    def __init__(self, config_path: str = "/workspace/orchestration/config/services.yaml"):
        self.config_path = config_path
        self.backup_targets = []
        self.backup_dir = Path("/workspace/orchestration/backup")
        self.restore_dir = Path("/workspace/orchestration/restore")
        self.encryption_key = None
        
        # Setup logging
        self.setup_logging()
        
        # Create backup directories
        self.backup_dir.mkdir(exist_ok=True)
        self.restore_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.load_configuration()
        
        self.logger.info("Backup and Restore System initialized")

    def setup_logging(self):
        """Setup logging for backup system"""
        log_dir = Path("/workspace/orchestration/logs")
        log_dir.mkdir(exist_ok=True)
        
        self.logger = logging.getLogger('BackupRestoreSystem')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        handler = logging.FileHandler(log_dir / 'backup_restore.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def load_configuration(self):
        """Load backup configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            backup_config = config.get('backup', {})
            
            # Load backup targets
            targets = backup_config.get('targets', [])
            for target in targets:
                backup_target = BackupTarget(
                    name=target['name'],
                    path=target['path'],
                    type=target['type']
                )
                self.backup_targets.append(backup_target)
            
            # Load encryption key if configured
            encryption_key = os.environ.get('BACKUP_ENCRYPTION_KEY')
            if encryption_key:
                self.encryption_key = encryption_key.encode()
            
            self.logger.info(f"Loaded {len(self.backup_targets)} backup targets")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def create_backup_metadata(self, backup_path: Path, target: BackupTarget) -> Dict[str, Any]:
        """Create metadata for backup"""
        metadata = {
            'backup_name': target.name,
            'backup_type': target.type,
            'source_path': target.path,
            'backup_path': str(backup_path),
            'timestamp': datetime.datetime.now().isoformat(),
            'file_hash': None,
            'file_size': None,
            'compression': target.compression,
            'encrypted': target.encrypted,
            'files_included': []
        }
        
        if backup_path.exists():
            metadata['file_size'] = backup_path.stat().st_size
            metadata['file_hash'] = self.calculate_file_hash(backup_path)
            
            # List files if it's a directory
            if target.type == 'directory':
                metadata['files_included'] = self.list_directory_contents(Path(target.path))
        
        return metadata

    def list_directory_contents(self, directory: Path) -> List[str]:
        """List contents of directory recursively"""
        contents = []
        if directory.exists():
            for item in directory.rglob('*'):
                if item.is_file():
                    contents.append(str(item.relative_to(directory)))
        return contents

    def backup_directory(self, target: BackupTarget) -> Path:
        """Backup a directory"""
        source_path = Path(target.path)
        
        if not source_path.exists():
            self.logger.warning(f"Source directory does not exist: {source_path}")
            return None
        
        backup_name = f"{target.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        self.logger.info(f"Backing up directory: {source_path} -> {backup_path}")
        
        try:
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(source_path, arcname=os.path.basename(source_path))
            
            self.logger.info(f"Directory backup completed: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Directory backup failed: {e}")
            return None

    def backup_redis_data(self, target: BackupTarget) -> Path:
        """Backup Redis data"""
        redis_path = Path(target.path)
        backup_name = f"{target.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if redis_path.exists() and redis_path.is_dir():
            # Check for Redis RDB file
            rdb_files = list(redis_path.glob("*.rdb"))
            if rdb_files:
                backup_path = self.backup_dir / f"{backup_name}.rdb"
                shutil.copy2(rdb_files[0], backup_path)
                self.logger.info(f"Redis RDB backup completed: {backup_path}")
                return backup_path
        
        # Fallback: try to use Redis CLI if available
        try:
            backup_path = self.backup_dir / f"{backup_name}.rdb"
            result = subprocess.run(
                ["redis-cli", "BGSAVE"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Copy the dump file
                dump_path = Path("/var/lib/redis/dump.rdb")
                if dump_path.exists():
                    shutil.copy2(dump_path, backup_path)
                    self.logger.info(f"Redis backup completed via CLI: {backup_path}")
                    return backup_path
                    
        except Exception as e:
            self.logger.warning(f"Redis CLI backup failed: {e}")
        
        self.logger.warning(f"No Redis data found at: {target.path}")
        return None

    def backup_database(self, target: BackupTarget) -> Path:
        """Backup database files"""
        db_path = Path(target.path)
        backup_name = f"{target.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if not db_path.exists():
            self.logger.warning(f"Database file does not exist: {db_path}")
            return None
        
        backup_path = self.backup_dir / f"{backup_name}.db"
        
        try:
            if db_path.is_file():
                # SQLite database
                if db_path.suffix == '.db' or db_path.suffix == '.sqlite':
                    # Use SQLite backup API for consistency
                    conn = sqlite3.connect(str(db_path))
                    backup_conn = sqlite3.connect(str(backup_path))
                    conn.backup(backup_conn)
                    conn.close()
                    backup_conn.close()
                    self.logger.info(f"SQLite backup completed: {backup_path}")
                    return backup_path
                else:
                    # Regular file backup
                    shutil.copy2(db_path, backup_path)
                    self.logger.info(f"Database file backup completed: {backup_path}")
                    return backup_path
            elif db_path.is_dir():
                # Directory backup for databases
                return self.backup_directory(target)
                
        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return None

    def create_backup(self, target_name: str = None) -> List[Path]:
        """Create backup for specified target or all targets"""
        if target_name:
            targets = [t for t in self.backup_targets if t.name == target_name]
            if not targets:
                self.logger.error(f"Backup target not found: {target_name}")
                return []
        else:
            targets = self.backup_targets
        
        backup_files = []
        
        for target in targets:
            try:
                self.logger.info(f"Starting backup for: {target.name}")
                
                if target.type == 'directory':
                    backup_path = self.backup_directory(target)
                elif target.type == 'redis':
                    backup_path = self.backup_redis_data(target)
                elif target.type == 'database':
                    backup_path = self.backup_database(target)
                elif target.type == 'file':
                    file_path = Path(target.path)
                    if file_path.exists():
                        backup_name = f"{target.name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        backup_path = self.backup_dir / backup_name
                        shutil.copy2(file_path, backup_path)
                    else:
                        self.logger.warning(f"File does not exist: {file_path}")
                        backup_path = None
                else:
                    self.logger.warning(f"Unknown backup type: {target.type}")
                    backup_path = None
                
                if backup_path and backup_path.exists():
                    # Create metadata
                    metadata = self.create_backup_metadata(backup_path, target)
                    metadata_file = backup_path.with_suffix(backup_path.suffix + '.meta')
                    
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                    backup_files.append(backup_path)
                    self.logger.info(f"Backup completed for {target.name}")
                else:
                    self.logger.error(f"Backup failed for {target.name}")
                    
            except Exception as e:
                self.logger.error(f"Error backing up {target.name}: {e}")
        
        return backup_files

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        for target in self.backup_targets:
            pattern = f"{target.name}_*.tar.gz"
            backup_files = list(self.backup_dir.glob(pattern))
            backup_files.extend(list(self.backup_dir.glob(f"{target.name}_*.rdb")))
            backup_files.extend(list(self.backup_dir.glob(f"{target.name}_*.db")))
            backup_files.extend(list(self.backup_dir.glob(f"{target.name}_*")))
            
            for backup_file in backup_files:
                metadata_file = backup_file.with_suffix(backup_file.suffix + '.meta')
                
                backup_info = {
                    'name': target.name,
                    'file': str(backup_file),
                    'size': backup_file.stat().st_size,
                    'created': datetime.datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                    'type': target.type,
                    'metadata': None
                }
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            backup_info['metadata'] = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"Could not load metadata for {backup_file}: {e}")
                
                backups.append(backup_info)
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        return backups

    def cleanup_old_backups(self, retention_days: int = 30):
        """Clean up old backup files"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        
        for target in self.backup_targets:
            pattern = f"{target.name}_*"
            backup_files = list(self.backup_dir.glob(pattern))
            
            for backup_file in backup_files:
                file_time = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    try:
                        # Remove backup file and metadata
                        backup_file.unlink()
                        metadata_file = backup_file.with_suffix(backup_file.suffix + '.meta')
                        if metadata_file.exists():
                            metadata_file.unlink()
                        
                        self.logger.info(f"Cleaned up old backup: {backup_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to cleanup backup {backup_file}: {e}")

    def restore_from_backup(self, backup_file: Path, target_path: str, restore_mode: str = 'overwrite') -> bool:
        """Restore from backup file"""
        try:
            if not backup_file.exists():
                self.logger.error(f"Backup file does not exist: {backup_file}")
                return False
            
            restore_path = Path(target_path)
            
            # Create backup of current state if restore_mode is 'merge'
            if restore_mode == 'merge' and restore_path.exists():
                backup_current = restore_path.with_suffix(f".backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
                shutil.move(str(restore_path), str(backup_current))
                self.logger.info(f"Current state backed up to: {backup_current}")
            
            # Determine backup type and restore
            if backup_file.suffix == '.tar.gz':
                # Extract tar.gz archive
                self.logger.info(f"Extracting archive: {backup_file} -> {restore_path}")
                
                with tarfile.open(backup_file, 'r:gz') as tar:
                    tar.extractall(restore_path.parent)
                    
                # Move extracted content to target location
                extracted_name = os.path.basename(backup_file).replace('.tar.gz', '')
                extracted_path = restore_path.parent / extracted_name
                
                if extracted_path.exists():
                    if restore_path.exists():
                        shutil.rmtree(restore_path)
                    shutil.move(str(extracted_path), str(restore_path))
            
            elif backup_file.suffix == '.rdb':
                # Redis RDB file
                self.logger.info(f"Restoring Redis RDB: {backup_file} -> {restore_path}")
                shutil.copy2(backup_file, restore_path / "dump.rdb")
            
            elif backup_file.suffix == '.db':
                # Database file
                self.logger.info(f"Restoring database: {backup_file} -> {restore_path}")
                
                # Ensure parent directory exists
                restore_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, restore_path)
            
            else:
                # Regular file
                self.logger.info(f"Restoring file: {backup_file} -> {restore_path}")
                restore_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, restore_path)
            
            self.logger.info(f"Restore completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return False

    def verify_backup_integrity(self, backup_file: Path) -> bool:
        """Verify backup file integrity"""
        try:
            metadata_file = backup_file.with_suffix(backup_file.suffix + '.meta')
            
            if not metadata_file.exists():
                self.logger.warning(f"No metadata file for backup: {backup_file}")
                return False
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            stored_hash = metadata.get('file_hash')
            if not stored_hash:
                self.logger.warning(f"No file hash in metadata for: {backup_file}")
                return True  # Skip check if no hash stored
            
            current_hash = self.calculate_file_hash(backup_file)
            
            if current_hash == stored_hash:
                self.logger.info(f"Backup integrity verified: {backup_file}")
                return True
            else:
                self.logger.error(f"Backup integrity check failed: {backup_file}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying backup integrity: {e}")
            return False

    def schedule_automated_backups(self):
        """Schedule automated backups using threading"""
        def backup_worker():
            while True:
                try:
                    self.logger.info("Running scheduled backup...")
                    self.create_backup()
                    self.cleanup_old_backups()
                    time.sleep(24 * 3600)  # Run daily
                except Exception as e:
                    self.logger.error(f"Error in scheduled backup: {e}")
                    time.sleep(3600)  # Wait 1 hour before retry
        
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        self.logger.info("Automated backup scheduler started")

def main():
    """Main entry point for backup system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup and Restore System")
    parser.add_argument('--action', choices=['backup', 'restore', 'list', 'cleanup', 'verify'], 
                       required=True, help='Action to perform')
    parser.add_argument('--target', help='Target name for backup/restore')
    parser.add_argument('--backup-file', help='Backup file to restore from')
    parser.add_argument('--restore-path', help='Path to restore to')
    parser.add_argument('--retention-days', type=int, default=30, help='Retention period in days')
    
    args = parser.parse_args()
    
    backup_system = BackupRestoreSystem()
    
    if args.action == 'backup':
        backup_files = backup_system.create_backup(args.target)
        if backup_files:
            print(f"Backup completed successfully. Created {len(backup_files)} backup files.")
        else:
            print("Backup failed or no files created.")
    
    elif args.action == 'restore':
        if not args.backup_file or not args.restore_path:
            print("Error: --backup-file and --restore-path required for restore action")
            sys.exit(1)
        
        success = backup_system.restore_from_backup(
            Path(args.backup_file), 
            args.restore_path
        )
        if success:
            print("Restore completed successfully.")
        else:
            print("Restore failed.")
    
    elif args.action == 'list':
        backups = backup_system.list_backups()
        for backup in backups:
            print(f"{backup['name']} - {backup['created']} - {backup['size']} bytes")
    
    elif args.action == 'cleanup':
        backup_system.cleanup_old_backups(args.retention_days)
        print(f"Cleaned up backups older than {args.retention_days} days.")
    
    elif args.action == 'verify':
        if not args.backup_file:
            print("Error: --backup-file required for verify action")
            sys.exit(1)
        
        is_valid = backup_system.verify_backup_integrity(Path(args.backup_file))
        if is_valid:
            print("Backup integrity verified.")
        else:
            print("Backup integrity check failed.")
            sys.exit(1)

if __name__ == "__main__":
    main()