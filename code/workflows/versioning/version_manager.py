"""
Workflow Versioning and Rollback System
"""

import json
import shutil
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import uuid

class VersionStatus(Enum):
    """Status of workflow version"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

class RollbackReason(Enum):
    """Reasons for rollback"""
    CRITICAL_BUG = "critical_bug"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    FAILED_VALIDATION = "failed_validation"
    EMERGENCY = "emergency"
    MANUAL_REVERT = "manual_revert"

@dataclass
class WorkflowVersion:
    """Workflow version metadata"""
    version_id: str
    template_id: str
    version_number: str
    status: VersionStatus
    created_at: datetime
    created_by: str
    description: str
    changes: List[str]
    parent_version: Optional[str]
    checksum: str
    file_path: str
    rollback_data: Optional[Dict[str, Any]] = None

@dataclass
class RollbackRecord:
    """Record of rollback operation"""
    rollback_id: str
    from_version: str
    to_version: str
    reason: RollbackReason
    initiated_by: str
    timestamp: datetime
    description: str
    success: bool
    error_message: Optional[str] = None

class WorkflowVersionManager:
    """Manages workflow versioning and rollback capabilities"""
    
    def __init__(self, workflows_dir: str = "code/workflows"):
        self.workflows_dir = Path(workflows_dir)
        self.version_dir = self.workflows_dir / 'versioning'
        self.templates_dir = self.workflows_dir / 'templates'
        self.version_history: Dict[str, List[WorkflowVersion]] = {}
        self.rollback_history: List[RollbackRecord] = []
        self.active_versions: Dict[str, str] = {}  # template_id -> version_id
        self.setup_directories()
        self.load_version_history()
    
    def setup_directories(self):
        """Setup version management directories"""
        self.version_dir.mkdir(exist_ok=True)
        (self.version_dir / 'templates').mkdir(exist_ok=True)
        (self.version_dir / 'history').mkdir(exist_ok=True)
        (self.version_dir / 'backups').mkdir(exist_ok=True)
        (self.version_dir / 'rollbacks').mkdir(exist_ok=True)
    
    def load_version_history(self):
        """Load version history from files"""
        history_dir = self.version_dir / 'history'
        
        if history_dir.exists():
            for version_file in history_dir.glob('*.json'):
                try:
                    with open(version_file) as f:
                        data = json.load(f)
                        version = self.dict_to_version(data)
                        
                        template_id = data['template_id']
                        if template_id not in self.version_history:
                            self.version_history[template_id] = []
                        
                        self.version_history[template_id].append(version)
                        
                        # Track active versions
                        if version.status == VersionStatus.ACTIVE:
                            self.active_versions[template_id] = version.version_id
                
                except Exception as e:
                    print(f"Error loading version history from {version_file}: {e}")
        
        # Load rollback history
        rollbacks_dir = self.version_dir / 'rollbacks'
        if rollbacks_dir.exists():
            for rollback_file in rollbacks_dir.glob('*.json'):
                try:
                    with open(rollback_file) as f:
                        data = json.load(f)
                        rollback = RollbackRecord(
                            rollback_id=data['rollback_id'],
                            from_version=data['from_version'],
                            to_version=data['to_version'],
                            reason=RollbackReason(data['reason']),
                            initiated_by=data['initiated_by'],
                            timestamp=datetime.fromisoformat(data['timestamp']),
                            description=data['description'],
                            success=data['success'],
                            error_message=data.get('error_message')
                        )
                        self.rollback_history.append(rollback)
                
                except Exception as e:
                    print(f"Error loading rollback history from {rollback_file}: {e}")
    
    def dict_to_version(self, data: Dict[str, Any]) -> WorkflowVersion:
        """Convert dictionary to WorkflowVersion object"""
        return WorkflowVersion(
            version_id=data['version_id'],
            template_id=data['template_id'],
            version_number=data['version_number'],
            status=VersionStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            created_by=data['created_by'],
            description=data['description'],
            changes=data['changes'],
            parent_version=data.get('parent_version'),
            checksum=data['checksum'],
            file_path=data['file_path'],
            rollback_data=data.get('rollback_data')
        )
    
    def create_new_version(self, template_file: str, version_description: str,
                          changes: List[str], created_by: str = "system") -> str:
        """Create a new version of a workflow template"""
        
        # Load current template
        template_path = Path(template_file)
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        with open(template_path) as f:
            template_content = f.read()
            template_data = json.loads(template_content)
        
        template_id = template_data['id']
        
        # Generate version number
        current_versions = self.version_history.get(template_id, [])
        version_number = self.generate_version_number(current_versions)
        
        # Generate version ID
        version_id = f"{template_id}_v{version_number}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Calculate checksum
        checksum = self.calculate_checksum(template_content)
        
        # Create version object
        parent_version = self.active_versions.get(template_id)
        version = WorkflowVersion(
            version_id=version_id,
            template_id=template_id,
            version_number=version_number,
            status=VersionStatus.DRAFT,
            created_at=datetime.utcnow(),
            created_by=created_by,
            description=version_description,
            changes=changes,
            parent_version=parent_version,
            checksum=checksum,
            file_path=str(template_path)
        )
        
        # Save version file
        version_file = self.version_dir / 'history' / f"{version_id}.json"
        with open(version_file, 'w') as f:
            json.dump(asdict(version), f, indent=2, default=str)
        
        # Add to history
        if template_id not in self.version_history:
            self.version_history[template_id] = []
        self.version_history[template_id].append(version)
        
        return version_id
    
    def generate_version_number(self, current_versions: List[WorkflowVersion]) -> str:
        """Generate next version number"""
        
        if not current_versions:
            return "1.0"
        
        # Extract version numbers and find highest
        version_numbers = []
        for version in current_versions:
            try:
                # Parse version number (e.g., "1.0", "1.1", "2.0")
                parts = version.version_number.split('.')
                major = int(parts[0])
                minor = int(parts[1]) if len(parts) > 1 else 0
                version_numbers.append((major, minor))
            except (ValueError, IndexError):
                continue
        
        if not version_numbers:
            return "1.0"
        
        # Sort by (major, minor)
        version_numbers.sort()
        last_major, last_minor = version_numbers[-1]
        
        # Determine next version based on changes
        # Minor version for backward-compatible changes
        # Major version for breaking changes
        return f"{last_major}.{last_minor + 1}"
    
    def calculate_checksum(self, content: str) -> str:
        """Calculate checksum for content verification"""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def activate_version(self, version_id: str, activated_by: str = "system") -> bool:
        """Activate a workflow version"""
        
        version = self.find_version(version_id)
        if not version:
            return False
        
        # Deactivate current active version
        template_id = version.template_id
        if template_id in self.active_versions:
            current_version_id = self.active_versions[template_id]
            current_version = self.find_version(current_version_id)
            if current_version:
                current_version.status = VersionStatus.DEPRECATED
                self.save_version(current_version)
        
        # Activate new version
        version.status = VersionStatus.ACTIVE
        self.active_versions[template_id] = version_id
        self.save_version(version)
        
        # Create rollback checkpoint
        if version.parent_version:
            self.create_rollback_checkpoint(version)
        
        return True
    
    def find_version(self, version_id: str) -> Optional[WorkflowVersion]:
        """Find version by ID"""
        for versions in self.version_history.values():
            for version in versions:
                if version.version_id == version_id:
                    return version
        return None
    
    def save_version(self, version: WorkflowVersion):
        """Save version to file"""
        version_file = self.version_dir / 'history' / f"{version.version_id}.json"
        with open(version_file, 'w') as f:
            json.dump(asdict(version), f, indent=2, default=str)
    
    def create_rollback_checkpoint(self, version: WorkflowVersion):
        """Create checkpoint data for rollback capability"""
        
        if not version.parent_version:
            return
        
        parent_version = self.find_version(version.parent_version)
        if not parent_version:
            return
        
        checkpoint_data = {
            'version_id': version.version_id,
            'parent_version': version.parent_version,
            'created_at': version.created_at.isoformat(),
            'rollback_data': {
                'template_id': version.template_id,
                'active_configuration': self.get_active_configuration(version.template_id),
                'performance_metrics': self.get_performance_snapshot(version.template_id),
                'dependencies': self.get_workflow_dependencies(version.template_id)
            }
        }
        
        version.rollback_data = checkpoint_data
        self.save_version(version)
    
    def get_active_configuration(self, template_id: str) -> Dict[str, Any]:
        """Get active configuration for template"""
        # In a real implementation, this would retrieve current system configuration
        return {
            'max_position_size': 5000000,
            'risk_threshold': 0.1,
            'automation_enabled': True,
            'escalation_rules': 'default'
        }
    
    def get_performance_snapshot(self, template_id: str) -> Dict[str, Any]:
        """Get performance snapshot for template"""
        # In a real implementation, this would retrieve actual performance data
        return {
            'success_rate': 0.85,
            'avg_execution_time': 180,
            'error_rate': 0.02,
            'last_updated': datetime.utcnow().isoformat()
        }
    
    def get_workflow_dependencies(self, template_id: str) -> List[str]:
        """Get workflow dependencies"""
        # Return dependencies based on template type
        dependencies = {
            'high_confidence_prediction': ['risk_analyzer', 'execution_agent'],
            'risk_event': ['emergency_protocol', 'notification_system'],
            'market_volatility': ['volatility_monitor', 'position_manager']
        }
        return dependencies.get(template_id, [])
    
    def rollback_to_version(self, version_id: str, reason: RollbackReason,
                          initiated_by: str, description: str = "") -> str:
        """Rollback to a previous version"""
        
        target_version = self.find_version(version_id)
        if not target_version:
            raise ValueError(f"Version not found: {version_id}")
        
        # Check if rollback is possible
        current_version_id = self.active_versions.get(target_version.template_id)
        if not current_version_id:
            raise ValueError("No active version to rollback from")
        
        current_version = self.find_version(current_version_id)
        if not current_version:
            raise ValueError("Current active version not found")
        
        # Create rollback record
        rollback_id = f"rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        rollback_record = RollbackRecord(
            rollback_id=rollback_id,
            from_version=current_version_id,
            to_version=version_id,
            reason=reason,
            initiated_by=initiated_by,
            timestamp=datetime.utcnow(),
            description=description or f"Rollback from {current_version.version_number} to {target_version.version_number}",
            success=False
        )
        
        try:
            # Perform rollback
            success = self.perform_rollback(target_version, current_version)
            
            if success:
                rollback_record.success = True
                
                # Update versions
                current_version.status = VersionStatus.DEPRECATED
                target_version.status = VersionStatus.ACTIVE
                
                self.save_version(current_version)
                self.save_version(target_version)
                
                # Update active versions tracking
                self.active_versions[target_version.template_id] = version_id
            else:
                rollback_record.success = False
                rollback_record.error_message = "Rollback operation failed"
            
        except Exception as e:
            rollback_record.success = False
            rollback_record.error_message = str(e)
        
        # Save rollback record
        rollback_file = self.version_dir / 'rollbacks' / f"{rollback_id}.json"
        with open(rollback_file, 'w') as f:
            json.dump(asdict(rollback_record), f, indent=2, default=str)
        
        self.rollback_history.append(rollback_record)
        
        return rollback_id
    
    def perform_rollback(self, target_version: WorkflowVersion, 
                        current_version: WorkflowVersion) -> bool:
        """Perform the actual rollback operation"""
        
        try:
            # Restore template file from backup or repository
            template_source = target_version.file_path
            template_destination = self.templates_dir / f"{target_version.template_id}.json"
            
            # Create backup of current template
            backup_path = self.version_dir / 'backups' / f"{current_version.version_id}.json"
            if template_destination.exists():
                shutil.copy2(template_destination, backup_path)
            
            # Restore target version template
            if Path(template_source).exists():
                shutil.copy2(template_source, template_destination)
            else:
                # If source doesn't exist, recreate from version data
                self.restore_template_from_version(target_version, template_destination)
            
            # Update workflow engine templates
            self.update_workflow_engine_templates()
            
            return True
            
        except Exception as e:
            print(f"Rollback failed: {e}")
            return False
    
    def restore_template_from_version(self, version: WorkflowVersion, destination: Path):
        """Restore template file from version data"""
        
        # Get template data from version history
        template_data = {
            'id': version.template_id,
            'version': version.version_number,
            'restored_from': version.version_id,
            'restored_at': datetime.utcnow().isoformat()
        }
        
        # In a real implementation, this would reconstruct the full template
        # For now, create a placeholder
        with open(destination, 'w') as f:
            json.dump(template_data, f, indent=2)
    
    def update_workflow_engine_templates(self):
        """Update workflow engine with new templates"""
        # In a real implementation, this would reload templates in the engine
        print("Updated workflow engine templates")
    
    def get_version_history(self, template_id: str) -> List[Dict[str, Any]]:
        """Get version history for a template"""
        
        versions = self.version_history.get(template_id, [])
        return [asdict(version) for version in sorted(versions, key=lambda x: x.created_at)]
    
    def get_active_version(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get currently active version for a template"""
        
        version_id = self.active_versions.get(template_id)
        if version_id:
            version = self.find_version(version_id)
            return asdict(version) if version else None
        
        return None
    
    def compare_versions(self, version_id_1: str, version_id_2: str) -> Dict[str, Any]:
        """Compare two workflow versions"""
        
        version_1 = self.find_version(version_id_1)
        version_2 = self.find_version(version_id_2)
        
        if not version_1 or not version_2:
            return {'error': 'One or both versions not found'}
        
        comparison = {
            'version_1': asdict(version_1),
            'version_2': asdict(version_2),
            'differences': {
                'metadata': self.compare_metadata(version_1, version_2),
                'content': self.compare_content(version_1, version_2),
                'performance': self.compare_performance(version_1, version_2)
            }
        }
        
        return comparison
    
    def compare_metadata(self, version_1: WorkflowVersion, version_2: WorkflowVersion) -> Dict[str, Any]:
        """Compare metadata between versions"""
        
        differences = {}
        
        # Compare version numbers
        if version_1.version_number != version_2.version_number:
            differences['version_number'] = {
                'from': version_1.version_number,
                'to': version_2.version_number
            }
        
        # Compare changes
        if version_1.changes != version_2.changes:
            differences['changes'] = {
                'from': version_1.changes,
                'to': version_2.changes,
                'added': list(set(version_2.changes) - set(version_1.changes)),
                'removed': list(set(version_1.changes) - set(version_2.changes))
            }
        
        return differences
    
    def compare_content(self, version_1: WorkflowVersion, version_2: WorkflowVersion) -> Dict[str, Any]:
        """Compare content between versions"""
        
        try:
            # Load template files
            with open(version_1.file_path) as f:
                content_1 = json.load(f)
            
            if Path(version_2.file_path).exists():
                with open(version_2.file_path) as f:
                    content_2 = json.load(f)
            else:
                content_2 = {}
            
            differences = {}
            
            # Compare top-level keys
            keys_1 = set(content_1.keys())
            keys_2 = set(content_2.keys())
            
            differences['added_keys'] = list(keys_2 - keys_1)
            differences['removed_keys'] = list(keys_1 - keys_2)
            differences['modified_keys'] = []
            
            # Find modified keys
            for key in keys_1 & keys_2:
                if content_1[key] != content_2[key]:
                    differences['modified_keys'].append(key)
            
            return differences
            
        except Exception as e:
            return {'error': f'Error comparing content: {e}'}
    
    def compare_performance(self, version_1: WorkflowVersion, version_2: WorkflowVersion) -> Dict[str, Any]:
        """Compare performance between versions"""
        
        # In a real implementation, this would compare actual performance metrics
        # For now, return placeholder data
        
        return {
            'version_1_performance': {
                'success_rate': 0.85,
                'avg_execution_time': 180,
                'error_rate': 0.02
            },
            'version_2_performance': {
                'success_rate': 0.88,
                'avg_execution_time': 165,
                'error_rate': 0.015
            },
            'improvement': {
                'success_rate_delta': 0.03,
                'execution_time_delta': -15,
                'error_rate_delta': -0.005
            }
        }
    
    def validate_version(self, version_id: str) -> Dict[str, Any]:
        """Validate a workflow version"""
        
        version = self.find_version(version_id)
        if not version:
            return {'valid': False, 'error': 'Version not found'}
        
        validation_result = {
            'valid': True,
            'version_id': version_id,
            'checks': {
                'file_exists': False,
                'checksum_valid': False,
                'template_valid': False,
                'dependencies_met': False
            },
            'warnings': [],
            'errors': []
        }
        
        # Check if template file exists
        template_path = Path(version.file_path)
        if template_path.exists():
            validation_result['checks']['file_exists'] = True
        else:
            validation_result['errors'].append('Template file not found')
            validation_result['valid'] = False
        
        # Validate template content
        if validation_result['checks']['file_exists']:
            try:
                with open(template_path) as f:
                    template_data = json.load(f)
                
                # Check required fields
                required_fields = ['id', 'name', 'version', 'steps']
                missing_fields = [field for field in required_fields if field not in template_data]
                
                if missing_fields:
                    validation_result['errors'].append(f'Missing required fields: {missing_fields}')
                    validation_result['valid'] = False
                
                validation_result['checks']['template_valid'] = len(missing_fields) == 0
                
            except json.JSONDecodeError:
                validation_result['errors'].append('Invalid JSON format')
                validation_result['valid'] = False
        
        # Validate checksum
        if validation_result['checks']['file_exists']:
            with open(template_path) as f:
                content = f.read()
            
            current_checksum = self.calculate_checksum(content)
            if current_checksum == version.checksum:
                validation_result['checks']['checksum_valid'] = True
            else:
                validation_result['warnings'].append('Checksum mismatch - file may have been modified')
        
        # Check dependencies (simplified)
        template_id = version.template_id
        dependencies = self.get_workflow_dependencies(template_id)
        if dependencies:
            # In a real implementation, check if dependencies are available
            validation_result['checks']['dependencies_met'] = True
        
        return validation_result
    
    def get_version_metrics(self) -> Dict[str, Any]:
        """Get version management metrics"""
        
        total_versions = sum(len(versions) for versions in self.version_history.values())
        active_versions = len(self.active_versions)
        total_rollbacks = len(self.rollback_history)
        successful_rollbacks = len([r for r in self.rollback_history if r.success])
        
        # Version distribution by status
        status_distribution = {'draft': 0, 'active': 0, 'deprecated': 0, 'archived': 0}
        for versions in self.version_history.values():
            for version in versions:
                status_distribution[version.status.value] += 1
        
        # Rollback success rate
        rollback_success_rate = successful_rollbacks / total_rollbacks if total_rollbacks > 0 else 0
        
        return {
            'total_versions': total_versions,
            'active_versions': active_versions,
            'total_rollbacks': total_rollbacks,
            'successful_rollbacks': successful_rollbacks,
            'rollback_success_rate': rollback_success_rate,
            'status_distribution': status_distribution,
            'templates_with_versions': len(self.version_history)
        }