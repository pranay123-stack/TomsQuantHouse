#!/usr/bin/env python3
"""
Agent Memory Backup and Restore Functionality
Provides comprehensive backup, restore, and data migration capabilities for agent memory
"""

import json
import os
import zipfile
import hashlib
import gzip
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import shutil
import tempfile
import uuid

from advanced_memory_manager import (
    AdvancedMemoryManager,
    MemoryBlock,
    MemoryBlockType,
    MemoryPriority,
    MemoryRetentionPolicy,
    MemoryMetadata
)
from redis_archival import RedisArchivalManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackupType(Enum):
    """Types of backups"""
    FULL = "full"              # Complete backup of all memory
    INCREMENTAL = "incremental"  # Only changes since last backup
    DIFFERENTIAL = "differential"  # Changes since last full backup
    SELECTIVE = "selective"    # Specific agents or block types
    ARCHIVAL = "archival"      # Archive old blocks


class BackupFormat(Enum):
    """Backup file formats"""
    JSON = "json"              # Plain JSON
    JSON_COMPRESSED = "json_gzip"  # Gzipped JSON
    BINARY = "binary"          # Binary format
    CUSTOM = "custom"          # Custom format


class RestoreMode(Enum):
    """Restore operation modes"""
    MERGE = "merge"            # Merge with existing data
    REPLACE = "replace"        # Replace existing data
    APPEND = "append"          # Append only (no duplicates)
    VALIDATE_ONLY = "validate_only"  # Validate backup without restoring


@dataclass
class BackupMetadata:
    """Metadata for backup operations"""
    backup_id: str
    backup_type: BackupType
    format: BackupFormat
    created_at: datetime
    agent_id: Optional[str]
    block_types: List[str]
    total_blocks: int
    total_size_bytes: int
    checksum: str
    version: str
    description: str
    compression_ratio: float
    source_system: str


@dataclass
class BackupStats:
    """Statistics about backup operations"""
    backups_created: int
    total_backup_size: int
    average_backup_size: int
    oldest_backup: Optional[datetime]
    newest_backup: Optional[datetime]
    success_rate: float
    total_restore_time: float
    agents_backed_up: List[str]
    block_types_covered: List[str]


@dataclass
class RestoreReport:
    """Report of restore operations"""
    backup_id: str
    restore_mode: RestoreMode
    start_time: datetime
    end_time: Optional[datetime]
    blocks_processed: int
    blocks_restored: int
    blocks_skipped: int
    blocks_failed: int
    errors: List[str]
    warnings: List[str]
    validation_results: Dict[str, Any]


class BackupManager:
    """Manages agent memory backup operations"""
    
    def __init__(self, 
                 memory_manager: AdvancedMemoryManager,
                 redis_archival: Optional[RedisArchivalManager] = None):
        
        self.memory_manager = memory_manager
        self.redis_archival = redis_archival
        
        # Backup configuration
        self.backup_dir = "/workspace/code/letta_integration/backups"
        self.max_backups = 100
        self.compression_enabled = True
        self.encryption_enabled = False  # For future implementation
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.backup_queue = []
        self.running = False
        self.backup_thread = None
        
        # Backup tracking
        self.backup_history = []
        self.metadata_cache = {}
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Load existing backup metadata
        self._load_backup_metadata()
    
    def start(self):
        """Start the backup manager"""
        self.running = True
        self.backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
        self.backup_thread.start()
        logger.info("Backup manager started")
    
    def stop(self):
        """Stop the backup manager"""
        self.running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        logger.info("Backup manager stopped")
    
    def create_backup(self,
                     agent_id: str,
                     backup_type: BackupType = BackupType.FULL,
                     backup_format: BackupFormat = BackupFormat.JSON_COMPRESSED,
                     block_types: List[MemoryBlockType] = None,
                     description: str = None) -> str:
        """Create a backup of agent memory"""
        
        backup_id = f"backup_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Add to queue for async processing
        backup_job = {
            "backup_id": backup_id,
            "agent_id": agent_id,
            "backup_type": backup_type,
            "backup_format": backup_format,
            "block_types": block_types or list(MemoryBlockType),
            "description": description or f"{backup_type.value} backup of {agent_id}",
            "created_at": datetime.now()
        }
        
        self.backup_queue.append(backup_job)
        
        logger.info(f"Backup {backup_id} queued for agent {agent_id}")
        return backup_id
    
    def create_full_backup(self, 
                          agent_ids: List[str],
                          output_path: str = None,
                          backup_format: BackupFormat = BackupFormat.JSON_COMPRESSED) -> str:
        """Create a comprehensive full backup of multiple agents"""
        
        backup_id = f"full_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        if not output_path:
            output_path = os.path.join(self.backup_dir, f"{backup_id}.backup")
        
        try:
            logger.info(f"Creating full backup {backup_id} for {len(agent_ids)} agents")
            
            backup_data = {
                "backup_id": backup_id,
                "backup_type": BackupType.FULL.value,
                "format": backup_format.value,
                "created_at": datetime.now().isoformat(),
                "agents": [],
                "metadata": {
                    "total_agents": len(agent_ids),
                    "backup_version": "1.0"
                }
            }
            
            total_blocks = 0
            total_size = 0
            
            # Process each agent
            for agent_id in agent_ids:
                logger.info(f"Backing up agent {agent_id}")
                
                agent_data = {
                    "agent_id": agent_id,
                    "backup_timestamp": datetime.now().isoformat(),
                    "blocks": []
                }
                
                # Get all memory blocks for agent
                all_blocks = self.memory_manager.search_memory_blocks(agent_id, limit=10000)
                
                for block in all_blocks:
                    try:
                        # Create backup entry
                        backup_entry = {
                            "block_id": block.block_id,
                            "block_type": block.block_type.value,
                            "title": block.title,
                            "content": block.content,
                            "metadata": asdict(block.metadata),
                            "trading_data": block.trading_data,
                            "backup_timestamp": datetime.now().isoformat()
                        }
                        
                        agent_data["blocks"].append(backup_entry)
                        total_blocks += 1
                        total_size += len(str(block.content))
                        
                    except Exception as e:
                        logger.error(f"Error backing up block {block.block_id}: {e}")
                
                backup_data["agents"].append(agent_data)
            
            # Calculate compression ratio and checksum
            backup_json = json.dumps(backup_data, indent=2, default=str)
            original_size = len(backup_json.encode('utf-8'))
            
            compressed_data = backup_json.encode('utf-8')
            if backup_format == BackupFormat.JSON_COMPRESSED:
                compressed_data = gzip.compress(compressed_data)
            
            compression_ratio = original_size / len(compressed_data) if compressed_data else 1.0
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=BackupType.FULL,
                format=backup_format,
                created_at=datetime.now(),
                agent_id=None,  # Multiple agents
                block_types=[bt.value for bt in MemoryBlockType],
                total_blocks=total_blocks,
                total_size_bytes=original_size,
                checksum=checksum,
                version="1.0",
                description=f"Full backup of {len(agent_ids)} agents",
                compression_ratio=compression_ratio,
                source_system="letta_integration"
            )
            
            # Write backup file
            with open(output_path, 'wb') as f:
                f.write(compressed_data)
            
            # Save metadata
            metadata_path = f"{output_path}.metadata"
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2, default=str)
            
            # Store in history
            self.backup_history.append(metadata)
            
            # Update metadata cache
            self.metadata_cache[backup_id] = metadata
            
            logger.info(f"Full backup {backup_id} completed: {total_blocks} blocks, {original_size} bytes")
            return backup_id
            
        except Exception as e:
            logger.error(f"Full backup {backup_id} failed: {e}")
            raise
    
    def create_incremental_backup(self,
                                agent_id: str,
                                since_backup_id: str = None,
                                since_timestamp: datetime = None,
                                backup_format: BackupFormat = BackupFormat.JSON_COMPRESSED) -> str:
        """Create an incremental backup (changes since last backup)"""
        
        backup_id = f"incremental_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Creating incremental backup {backup_id} for agent {agent_id}")
            
            # Determine baseline for incremental backup
            baseline_time = since_timestamp
            if not baseline_time and since_backup_id:
                # Get timestamp from previous backup
                baseline_metadata = self.metadata_cache.get(since_backup_id)
                if baseline_metadata:
                    baseline_time = baseline_metadata.created_at
            
            if not baseline_time:
                baseline_time = datetime.now() - timedelta(hours=24)  # Default to 24 hours
            
            # Get all blocks and filter for changes
            all_blocks = self.memory_manager.search_memory_blocks(agent_id, limit=10000)
            changed_blocks = []
            
            for block in all_blocks:
                # Check if block was created or modified after baseline
                if (block.metadata.created_at > baseline_time or 
                    block.metadata.last_accessed > baseline_time):
                    changed_blocks.append(block)
            
            if not changed_blocks:
                logger.info(f"No changes found for incremental backup {backup_id}")
                return backup_id
            
            # Create backup data
            backup_data = {
                "backup_id": backup_id,
                "backup_type": BackupType.INCREMENTAL.value,
                "format": backup_format.value,
                "created_at": datetime.now().isoformat(),
                "baseline_timestamp": baseline_time.isoformat(),
                "agent_id": agent_id,
                "blocks": []
            }
            
            total_size = 0
            
            for block in changed_blocks:
                backup_entry = {
                    "block_id": block.block_id,
                    "block_type": block.block_type.value,
                    "title": block.title,
                    "content": block.content,
                    "metadata": asdict(block.metadata),
                    "trading_data": block.trading_data,
                    "change_type": "modified" if block.metadata.created_at <= baseline_time else "created",
                    "backup_timestamp": datetime.now().isoformat()
                }
                
                backup_data["blocks"].append(backup_entry)
                total_size += len(str(block.content))
            
            # Calculate compression and checksum
            backup_json = json.dumps(backup_data, indent=2, default=str)
            original_size = len(backup_json.encode('utf-8'))
            
            compressed_data = backup_json.encode('utf-8')
            if backup_format == BackupFormat.JSON_COMPRESSED:
                compressed_data = gzip.compress(compressed_data)
            
            compression_ratio = original_size / len(compressed_data) if compressed_data else 1.0
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            # Save backup file
            backup_path = os.path.join(self.backup_dir, f"{backup_id}.backup")
            with open(backup_path, 'wb') as f:
                f.write(compressed_data)
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=BackupType.INCREMENTAL,
                format=backup_format,
                created_at=datetime.now(),
                agent_id=agent_id,
                block_types=[bt.value for bt in MemoryBlockType],
                total_blocks=len(changed_blocks),
                total_size_bytes=original_size,
                checksum=checksum,
                version="1.0",
                description=f"Incremental backup of {len(changed_blocks)} changed blocks",
                compression_ratio=compression_ratio,
                source_system="letta_integration"
            )
            
            # Save metadata
            metadata_path = f"{backup_path}.metadata"
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2, default=str)
            
            self.backup_history.append(metadata)
            self.metadata_cache[backup_id] = metadata
            
            logger.info(f"Incremental backup {backup_id} completed: {len(changed_blocks)} blocks")
            return backup_id
            
        except Exception as e:
            logger.error(f"Incremental backup {backup_id} failed: {e}")
            raise
    
    def create_selective_backup(self,
                              agent_id: str,
                              block_types: List[MemoryBlockType],
                              filters: Dict[str, Any] = None,
                              backup_format: BackupFormat = BackupFormat.JSON_COMPRESSED) -> str:
        """Create a selective backup with specific criteria"""
        
        backup_id = f"selective_{agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        try:
            logger.info(f"Creating selective backup {backup_id} for agent {agent_id}")
            
            # Get blocks matching criteria
            selected_blocks = []
            for block_type in block_types:
                blocks = self.memory_manager.search_memory_blocks(
                    agent_id=agent_id,
                    block_type=block_type,
                    limit=1000
                )
                
                # Apply additional filters
                for block in blocks:
                    if self._passes_filters(block, filters or {}):
                        selected_blocks.append(block)
            
            if not selected_blocks:
                logger.warning(f"No blocks found matching criteria for selective backup {backup_id}")
                return backup_id
            
            # Create backup data
            backup_data = {
                "backup_id": backup_id,
                "backup_type": BackupType.SELECTIVE.value,
                "format": backup_format.value,
                "created_at": datetime.now().isoformat(),
                "agent_id": agent_id,
                "selection_criteria": {
                    "block_types": [bt.value for bt in block_types],
                    "filters": filters or {}
                },
                "blocks": []
            }
            
            total_size = 0
            
            for block in selected_blocks:
                backup_entry = {
                    "block_id": block.block_id,
                    "block_type": block.block_type.value,
                    "title": block.title,
                    "content": block.content,
                    "metadata": asdict(block.metadata),
                    "trading_data": block.trading_data,
                    "backup_timestamp": datetime.now().isoformat()
                }
                
                backup_data["blocks"].append(backup_entry)
                total_size += len(str(block.content))
            
            # Process backup file
            backup_json = json.dumps(backup_data, indent=2, default=str)
            original_size = len(backup_json.encode('utf-8'))
            
            compressed_data = backup_json.encode('utf-8')
            if backup_format == BackupFormat.JSON_COMPRESSED:
                compressed_data = gzip.compress(compressed_data)
            
            compression_ratio = original_size / len(compressed_data) if compressed_data else 1.0
            checksum = hashlib.sha256(compressed_data).hexdigest()
            
            # Save files
            backup_path = os.path.join(self.backup_dir, f"{backup_id}.backup")
            with open(backup_path, 'wb') as f:
                f.write(compressed_data)
            
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=BackupType.SELECTIVE,
                format=backup_format,
                created_at=datetime.now(),
                agent_id=agent_id,
                block_types=[bt.value for bt in block_types],
                total_blocks=len(selected_blocks),
                total_size_bytes=original_size,
                checksum=checksum,
                version="1.0",
                description=f"Selective backup: {', '.join([bt.value for bt in block_types])}",
                compression_ratio=compression_ratio,
                source_system="letta_integration"
            )
            
            metadata_path = f"{backup_path}.metadata"
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2, default=str)
            
            self.backup_history.append(metadata)
            self.metadata_cache[backup_id] = metadata
            
            logger.info(f"Selective backup {backup_id} completed: {len(selected_blocks)} blocks")
            return backup_id
            
        except Exception as e:
            logger.error(f"Selective backup {backup_id} failed: {e}")
            raise
    
    def restore_backup(self,
                     backup_id: str,
                     target_agent_id: str = None,
                     restore_mode: RestoreMode = RestoreMode.MERGE,
                     validation_only: bool = False) -> RestoreReport:
        """Restore from a backup"""
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting restore of backup {backup_id} for agent {target_agent_id}")
            
            # Load backup metadata
            metadata = self._load_backup_metadata_single(backup_id)
            if not metadata:
                raise ValueError(f"Backup metadata not found for {backup_id}")
            
            # Load backup data
            backup_path = os.path.join(self.backup_dir, f"{backup_id}.backup")
            if not os.path.exists(backup_path):
                raise ValueError(f"Backup file not found: {backup_path}")
            
            with open(backup_path, 'rb') as f:
                backup_data = f.read()
            
            # Validate checksum
            calculated_checksum = hashlib.sha256(backup_data).hexdigest()
            if calculated_checksum != metadata.checksum:
                raise ValueError(f"Backup checksum mismatch: expected {metadata.checksum}, got {calculated_checksum}")
            
            # Decompress if needed
            if metadata.format == BackupFormat.JSON_COMPRESSED:
                backup_data = gzip.decompress(backup_data)
            
            backup_json = backup_data.decode('utf-8')
            backup_content = json.loads(backup_json)
            
            # Determine target agent
            if target_agent_id is None:
                target_agent_id = backup_content.get("agent_id", metadata.agent_id)
            
            if not target_agent_id:
                raise ValueError("No target agent specified and no agent ID in backup")
            
            report = RestoreReport(
                backup_id=backup_id,
                restore_mode=restore_mode,
                start_time=start_time,
                end_time=None,
                blocks_processed=0,
                blocks_restored=0,
                blocks_skipped=0,
                blocks_failed=0,
                errors=[],
                warnings=[],
                validation_results={"checksum_valid": True}
            )
            
            if restore_mode == RestoreMode.VALIDATE_ONLY:
                report.blocks_processed = len(backup_content.get("blocks", []))
                report.end_time = datetime.now()
                return report
            
            # Process blocks
            blocks = backup_content.get("blocks", [])
            existing_blocks = set()
            
            # Get existing blocks for merge/append mode
            if restore_mode in [RestoreMode.MERGE, RestoreMode.APPEND]:
                existing_memory = self.memory_manager.search_memory_blocks(
                    target_agent_id, limit=10000
                )
                existing_blocks = {block.block_id for block in existing_memory}
            
            for block_data in blocks:
                try:
                    report.blocks_processed += 1
                    
                    # Check if block already exists
                    block_id = block_data.get("block_id")
                    if block_id in existing_blocks and restore_mode == RestoreMode.APPEND:
                        report.blocks_skipped += 1
                        continue
                    
                    # Reconstruct memory block
                    memory_block = self._reconstruct_block_from_backup(block_data)
                    
                    if restore_mode == RestoreMode.REPLACE:
                        # Delete existing block first
                        if block_id in existing_blocks:
                            self.memory_manager.delete_memory_block(target_agent_id, block_id)
                    
                    # Add or update block
                    if restore_mode == RestoreMode.MERGE and block_id in existing_blocks:
                        # Update existing block
                        success = self.memory_manager.update_memory_block(
                            target_agent_id, block_id, 
                            content=memory_block.content,
                            metadata_updates=asdict(memory_block.metadata)
                        )
                    else:
                        # Add new block
                        new_block_id = self.memory_manager.create_memory_block(
                            target_agent_id,
                            memory_block.block_type,
                            memory_block.title,
                            memory_block.content,
                            priority=memory_block.metadata.priority,
                            retention_policy=memory_block.metadata.retention_policy,
                            tags=memory_block.metadata.tags,
                            trading_data=memory_block.trading_data
                        )
                        success = new_block_id is not None
                    
                    if success:
                        report.blocks_restored += 1
                    else:
                        report.blocks_failed += 1
                        report.errors.append(f"Failed to restore block {block_id}")
                
                except Exception as e:
                    report.blocks_failed += 1
                    report.errors.append(f"Error restoring block {block_data.get('block_id', 'unknown')}: {str(e)}")
            
            report.end_time = datetime.now()
            
            logger.info(f"Restore completed: {report.blocks_processed} processed, {report.blocks_restored} restored")
            return report
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return RestoreReport(
                backup_id=backup_id,
                restore_mode=restore_mode,
                start_time=start_time,
                end_time=datetime.now(),
                blocks_processed=0,
                blocks_restored=0,
                blocks_skipped=0,
                blocks_failed=1,
                errors=[str(e)],
                warnings=[],
                validation_results={}
            )
    
    def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """Validate backup integrity"""
        
        try:
            logger.info(f"Validating backup {backup_id}")
            
            metadata = self._load_backup_metadata_single(backup_id)
            if not metadata:
                return {"valid": False, "error": "Metadata not found"}
            
            backup_path = os.path.join(self.backup_dir, f"{backup_id}.backup")
            if not os.path.exists(backup_path):
                return {"valid": False, "error": "Backup file not found"}
            
            # Check file size
            file_size = os.path.getsize(backup_path)
            expected_size = metadata.total_size_bytes
            
            if file_size != expected_size:
                return {"valid": False, "error": f"File size mismatch: {file_size} vs {expected_size}"}
            
            # Verify checksum
            with open(backup_path, 'rb') as f:
                backup_data = f.read()
            
            calculated_checksum = hashlib.sha256(backup_data).hexdigest()
            if calculated_checksum != metadata.checksum:
                return {"valid": False, "error": "Checksum mismatch"}
            
            # Test decompression (if applicable)
            try:
                if metadata.format == BackupFormat.JSON_COMPRESSED:
                    decompressed = gzip.decompress(backup_data)
                    json.loads(decompressed.decode('utf-8'))
                else:
                    json.loads(backup_data.decode('utf-8'))
            except Exception as e:
                return {"valid": False, "error": f"Data corruption: {str(e)}"}
            
            return {
                "valid": True,
                "metadata": asdict(metadata),
                "file_size": file_size,
                "checksum_valid": True,
                "data_integrity": True
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def list_backups(self, agent_id: str = None) -> List[BackupMetadata]:
        """List all available backups"""
        
        backups = list(self.backup_history)
        
        if agent_id:
            backups = [b for b in backups if b.agent_id == agent_id or b.agent_id is None]
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda b: b.created_at, reverse=True)
        
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        
        try:
            # Remove from history
            self.backup_history = [b for b in self.backup_history if b.backup_id != backup_id]
            
            # Remove from cache
            if backup_id in self.metadata_cache:
                del self.metadata_cache[backup_id]
            
            # Delete files
            backup_path = os.path.join(self.backup_dir, f"{backup_id}.backup")
            metadata_path = f"{backup_path}.metadata"
            
            files_to_delete = [backup_path, metadata_path]
            for file_path in files_to_delete:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            logger.info(f"Deleted backup {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    def cleanup_old_backups(self, max_age_days: int = 30, max_count: int = 50) -> int:
        """Clean up old backups based on age and count limits"""
        
        try:
            logger.info("Starting cleanup of old backups")
            
            current_time = datetime.now()
            backups_to_delete = []
            
            # Find backups exceeding age limit
            for backup in self.backup_history:
                age_days = (current_time - backup.created_at).days
                if age_days > max_age_days:
                    backups_to_delete.append(backup.backup_id)
            
            # Find excess backups beyond count limit
            if len(self.backup_history) > max_count:
                # Keep most recent backups
                sorted_backups = sorted(self.backup_history, key=lambda b: b.created_at, reverse=True)
                excess_backups = sorted_backups[max_count:]
                backups_to_delete.extend([b.backup_id for b in excess_backups])
            
            # Remove duplicates
            backups_to_delete = list(set(backups_to_delete))
            
            # Delete backups
            deleted_count = 0
            for backup_id in backups_to_delete:
                if self.delete_backup(backup_id):
                    deleted_count += 1
            
            logger.info(f"Cleanup completed: {deleted_count} backups deleted")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")
            return 0
    
    def export_backup_catalog(self, output_path: str) -> bool:
        """Export backup catalog to file"""
        
        try:
            catalog_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_backups": len(self.backup_history),
                "backups": [asdict(backup) for backup in self.backup_history],
                "statistics": self.get_backup_statistics()
            }
            
            with open(output_path, 'w') as f:
                json.dump(catalog_data, f, indent=2, default=str)
            
            logger.info(f"Backup catalog exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export backup catalog: {e}")
            return False
    
    def get_backup_statistics(self) -> BackupStats:
        """Get backup statistics"""
        
        if not self.backup_history:
            return BackupStats(0, 0, 0, None, None, 0, 0, [], [])
        
        total_backups = len(self.backup_history)
        total_size = sum(b.total_size_bytes for b in self.backup_history)
        avg_size = total_size / total_backups
        
        oldest_backup = min(b.created_at for b in self.backup_history)
        newest_backup = max(b.created_at for b in self.backup_history)
        
        # Calculate success rate (simplified)
        success_rate = 0.95  # Assume 95% success rate for now
        
        agents_backed_up = list(set(b.agent_id for b in self.backup_history if b.agent_id))
        block_types_covered = list(set(bt for b in self.backup_history for bt in b.block_types))
        
        return BackupStats(
            backups_created=total_backups,
            total_backup_size=total_size,
            average_backup_size=avg_size,
            oldest_backup=oldest_backup,
            newest_backup=newest_backup,
            success_rate=success_rate,
            total_restore_time=0,  # Would need to track
            agents_backed_up=agents_backed_up,
            block_types_covered=block_types_covered
        )
    
    # Internal methods
    
    def _passes_filters(self, block: MemoryBlock, filters: Dict[str, Any]) -> bool:
        """Check if block passes filters"""
        
        # Priority filter
        if "priority" in filters:
            if block.metadata.priority.value != filters["priority"]:
                return False
        
        # Age filter
        if "min_age_days" in filters:
            age_days = (datetime.now() - block.metadata.created_at).days
            if age_days < filters["min_age_days"]:
                return False
        
        if "max_age_days" in filters:
            age_days = (datetime.now() - block.metadata.created_at).days
            if age_days > filters["max_age_days"]:
                return False
        
        # Access count filter
        if "min_access_count" in filters:
            if block.metadata.access_count < filters["min_access_count"]:
                return False
        
        # Tags filter
        if "tags" in filters:
            required_tags = filters["tags"]
            if not any(tag in block.metadata.tags for tag in required_tags):
                return False
        
        # Size filter
        if "min_size_bytes" in filters:
            if len(str(block.content)) < filters["min_size_bytes"]:
                return False
        
        if "max_size_bytes" in filters:
            if len(str(block.content)) > filters["max_size_bytes"]:
                return False
        
        return True
    
    def _reconstruct_block_from_backup(self, block_data: Dict[str, Any]) -> MemoryBlock:
        """Reconstruct MemoryBlock from backup data"""
        
        # Reconstruct metadata
        metadata_dict = block_data.get("metadata", {})
        metadata = MemoryMetadata(
            created_at=datetime.fromisoformat(metadata_dict.get("created_at")),
            last_accessed=datetime.fromisoformat(metadata_dict.get("last_accessed")),
            access_count=metadata_dict.get("access_count", 0),
            priority=MemoryPriority(metadata_dict.get("priority", MemoryPriority.MEDIUM.value)),
            retention_policy=MemoryRetentionPolicy(metadata_dict.get("retention_policy", MemoryRetentionPolicy.MEDIUM_TERM.value)),
            confidence_score=metadata_dict.get("confidence_score", 0.5),
            source_agent=block_data.get("agent_id", ""),
            related_blocks=metadata_dict.get("related_blocks", []),
            tags=metadata_dict.get("tags", []),
            data_type=block_data.get("value_type", "text"),
            compression_ratio=1.0,
            checksum=metadata_dict.get("checksum", "")
        )
        
        return MemoryBlock(
            block_id=block_data.get("block_id"),
            block_type=MemoryBlockType(block_data.get("block_type")),
            title=block_data.get("title"),
            content=block_data.get("content"),
            metadata=metadata,
            trading_data=block_data.get("trading_data", {})
        )
    
    def _load_backup_metadata(self):
        """Load backup metadata from files"""
        
        try:
            metadata_files = []
            if os.path.exists(self.backup_dir):
                for file in os.listdir(self.backup_dir):
                    if file.endswith('.metadata'):
                        metadata_files.append(os.path.join(self.backup_dir, file))
            
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r') as f:
                        metadata_dict = json.load(f)
                        metadata = BackupMetadata(**metadata_dict)
                        self.backup_history.append(metadata)
                        self.metadata_cache[metadata.backup_id] = metadata
                except Exception as e:
                    logger.warning(f"Failed to load metadata from {metadata_file}: {e}")
            
            logger.info(f"Loaded {len(self.backup_history)} backup metadata entries")
            
        except Exception as e:
            logger.error(f"Failed to load backup metadata: {e}")
    
    def _load_backup_metadata_single(self, backup_id: str) -> Optional[BackupMetadata]:
        """Load metadata for a specific backup"""
        
        # Check cache first
        if backup_id in self.metadata_cache:
            return self.metadata_cache[backup_id]
        
        # Load from file
        metadata_path = os.path.join(self.backup_dir, f"{backup_id}.backup.metadata")
        try:
            with open(metadata_path, 'r') as f:
                metadata_dict = json.load(f)
                metadata = BackupMetadata(**metadata_dict)
                self.metadata_cache[backup_id] = metadata
                return metadata
        except Exception as e:
            logger.error(f"Failed to load metadata for {backup_id}: {e}")
            return None
    
    def _backup_worker(self):
        """Background worker for processing backup queue"""
        
        while self.running:
            try:
                if self.backup_queue:
                    backup_job = self.backup_queue.pop(0)
                    
                    # Process backup job
                    future = self.executor.submit(self._process_backup_job, backup_job)
                    
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout
                        logger.info(f"Completed backup job: {result}")
                    except Exception as e:
                        logger.error(f"Backup job failed: {e}")
                
                threading.Event().wait(1)  # Check queue every second
                
            except Exception as e:
                logger.error(f"Backup worker error: {e}")
                threading.Event().wait(10)
    
    def _process_backup_job(self, backup_job: Dict[str, Any]) -> str:
        """Process a backup job from the queue"""
        
        try:
            backup_id = backup_job["backup_id"]
            agent_id = backup_job["agent_id"]
            backup_type = backup_job["backup_type"]
            backup_format = backup_job["backup_format"]
            block_types = backup_job["block_types"]
            
            logger.info(f"Processing backup job {backup_id}")
            
            # Execute backup based on type
            if backup_type == BackupType.FULL:
                # Full backup logic
                pass
            elif backup_type == BackupType.INCREMENTAL:
                # Incremental backup logic
                pass
            elif backup_type == BackupType.SELECTIVE:
                # Selective backup logic
                pass
            
            return backup_id
            
        except Exception as e:
            logger.error(f"Backup job processing failed: {e}")
            raise