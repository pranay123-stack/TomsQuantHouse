#!/usr/bin/env python3
"""
Environment Configuration Manager

This module provides:
- Environment-specific configuration loading
- Variable substitution and validation
- Configuration change tracking
- Configuration promotion between environments
"""

import os
import yaml
import json
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import threading
import hashlib

logger = logging.getLogger(__name__)

class EnvironmentType(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class ValidationRule:
    """Configuration validation rule"""
    path: str
    required: bool = True
    type: str = "str"
    pattern: str = None
    min_length: int = None
    max_length: int = None
    min_value: int = None
    max_value: int = None
    choices: List[str] = None
    description: str = ""

@dataclass
class ChangeRecord:
    """Configuration change record"""
    timestamp: datetime
    path: str
    old_value: Any
    new_value: Any
    user: str
    reason: str = ""
    
@dataclass
class EnvironmentConfig:
    """Environment configuration container"""
    name: str
    type: EnvironmentType
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    version: int = 1
    checksum: str = ""
    
    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()
    
    def _calculate_checksum(self) -> str:
        """Calculate configuration checksum"""
        content = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def update_data(self, new_data: Dict[str, Any]):
        """Update configuration data"""
        self.data = new_data
        self.updated_at = datetime.now()
        self.version += 1
        self.checksum = self._calculate_checksum()
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by path (supports dot notation)"""
        keys = path.split('.')
        value = self.data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, path: str, value: Any):
        """Set configuration value by path"""
        keys = path.split('.')
        current = self.data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        self.update_data(self.data)

class ConfigValidator:
    """Configuration validation engine"""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default validation rules"""
        # Environment-specific rules
        self.add_rule(ValidationRule(
            path="environment.type",
            required=True,
            type="str",
            choices=["development", "staging", "production"],
            description="Environment type"
        ))
        
        # App configuration rules
        self.add_rule(ValidationRule(
            path="app.host",
            required=True,
            type="str",
            pattern=r"^[a-zA-Z0-9.-]+$",
            description="Application host"
        ))
        
        self.add_rule(ValidationRule(
            path="app.port",
            required=True,
            type="int",
            min_value=1,
            max_value=65535,
            description="Application port"
        ))
        
        # Security rules
        self.add_rule(ValidationRule(
            path="security.jwt.secret",
            required=True,
            type="str",
            min_length=32,
            description="JWT signing secret"
        ))
        
        self.add_rule(ValidationRule(
            path="security.cors.enabled",
            required=True,
            type="bool",
            description="CORS enabled"
        ))
        
        # Database rules
        self.add_rule(ValidationRule(
            path="app.database.host",
            required=True,
            type="str",
            description="Database host"
        ))
        
        self.add_rule(ValidationRule(
            path="app.database.port",
            required=True,
            type="int",
            min_value=1,
            max_value=65535,
            description="Database port"
        ))
    
    def add_rule(self, rule: ValidationRule):
        """Add validation rule"""
        self.rules.append(rule)
    
    def validate(self, config: EnvironmentConfig) -> List[str]:
        """Validate configuration against rules"""
        errors = []
        
        for rule in self.rules:
            try:
                value = config.get(rule.path)
                
                # Check required field
                if rule.required and value is None:
                    errors.append(f"Required field '{rule.path}' is missing")
                    continue
                
                if value is None:
                    continue  # Optional field, skip validation
                
                # Type validation
                if not self._validate_type(value, rule.type):
                    errors.append(f"Field '{rule.path}' must be of type {rule.type}")
                    continue
                
                # String-specific validations
                if isinstance(value, str):
                    if rule.min_length and len(value) < rule.min_length:
                        errors.append(f"Field '{path}' must be at least {rule.min_length} characters")
                    
                    if rule.max_length and len(value) > rule.max_length:
                        errors.append(f"Field '{rule.path}' must be at most {rule.max_length} characters")
                    
                    if rule.pattern and not re.match(rule.pattern, value):
                        errors.append(f"Field '{rule.path}' does not match required pattern")
                    
                    if rule.choices and value not in rule.choices:
                        errors.append(f"Field '{rule.path}' must be one of: {', '.join(rule.choices)}")
                
                # Integer-specific validations
                if isinstance(value, int):
                    if rule.min_value and value < rule.min_value:
                        errors.append(f"Field '{rule.path}' must be at least {rule.min_value}")
                    
                    if rule.max_value and value > rule.max_value:
                        errors.append(f"Field '{rule.path}' must be at most {rule.max_value}")
                
            except Exception as e:
                errors.append(f"Validation error for '{rule.path}': {e}")
        
        return errors
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type"""
        type_map = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict
        }
        
        return type(value) == type_map.get(expected_type)

class ConfigManager:
    """Environment configuration management system"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or Path(__file__).parent / "templates")
        self.validator = ConfigValidator()
        self.configs: Dict[str, EnvironmentConfig] = {}
        self.change_history: List[ChangeRecord] = []
        self._lock = threading.Lock()
        
        # Initialize change tracking
        self._init_change_tracking()
    
    def _init_change_tracking(self):
        """Initialize change tracking system"""
        history_dir = Path.home() / '.env_mgmt' / 'history'
        history_dir.mkdir(exist_ok=True, parents=True)
        
        self.history_file = history_dir / 'config_changes.json'
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    history_data = json.load(f)
                    for record_data in history_data:
                        record = ChangeRecord(
                            timestamp=datetime.fromisoformat(record_data['timestamp']),
                            path=record_data['path'],
                            old_value=record_data['old_value'],
                            new_value=record_data['new_value'],
                            user=record_data['user'],
                            reason=record_data['reason']
                        )
                        self.change_history.append(record)
            except Exception as e:
                logger.warning(f"Could not load change history: {e}")
    
    def load_config(self, environment: str) -> Optional[EnvironmentConfig]:
        """Load configuration for environment"""
        config_file = self.config_dir / f"{environment}.yaml"
        
        if not config_file.exists():
            logger.error(f"Configuration file not found: {config_file}")
            return None
        
        try:
            with open(config_file) as f:
                data = yaml.safe_load(f)
            
            # Process environment variables
            data = self._substitute_variables(data)
            
            # Create environment type
            env_type_str = data.get('environment', {}).get('type', 'development')
            env_type = EnvironmentType(env_type_str)
            
            config = EnvironmentConfig(
                name=environment,
                type=env_type,
                data=data,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Validate configuration
            validation_errors = self.validator.validate(config)
            if validation_errors:
                logger.warning(f"Configuration validation errors for {environment}:")
                for error in validation_errors:
                    logger.warning(f"  - {error}")
            
            self.configs[environment] = config
            logger.info(f"Configuration loaded for {environment}")
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration for {environment}: {e}")
            return None
    
    def _substitute_variables(self, data: Any) -> Any:
        """Recursively substitute environment variables and secrets"""
        if isinstance(data, dict):
            return {k: self._substitute_variables(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._substitute_variables(item) for item in data]
        elif isinstance(data, str):
            # Substitute ${VAR_NAME} format
            def replace_var(match):
                var_name = match.group(1)
                # Try environment variable first
                if var_name in os.environ:
                    return os.environ[var_name]
                # Try to get from secrets manager
                try:
                    from .secrets_mgmt.secrets_manager import SecretsManager
                    manager = SecretsManager()
                    secret_value = manager.get_secret(var_name)
                    if secret_value:
                        return secret_value
                except:
                    pass
                # Return placeholder if not found
                return f"${{{var_name}}}"
            
            return re.sub(r'\$\{([^}]+)\}', replace_var, data)
        else:
            return data
    
    def update_config(self, environment: str, path: str, new_value: Any, 
                     user: str = "system", reason: str = "") -> bool:
        """Update configuration value and track changes"""
        with self._lock:
            try:
                config = self.configs.get(environment)
                if not config:
                    logger.error(f"Configuration not loaded for {environment}")
                    return False
                
                # Get old value for change tracking
                old_value = config.get(path)
                
                # Update the value
                config.set(path, new_value)
                
                # Validate updated configuration
                validation_errors = self.validator.validate(config)
                if validation_errors:
                    logger.error(f"Validation failed after update: {validation_errors}")
                    return False
                
                # Record change
                change_record = ChangeRecord(
                    timestamp=datetime.now(),
                    path=path,
                    old_value=old_value,
                    new_value=new_value,
                    user=user,
                    reason=reason
                )
                self.change_history.append(change_record)
                
                # Save change history
                self._save_change_history()
                
                # Update configuration file
                self._save_config_file(environment)
                
                logger.info(f"Configuration updated: {environment}.{path} = {new_value}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to update configuration: {e}")
                return False
    
    def _save_config_file(self, environment: str):
        """Save configuration to file"""
        config = self.configs[environment]
        config_file = self.config_dir / f"{environment}.yaml"
        
        try:
            with open(config_file, 'w') as f:
                yaml.dump(config.data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            logger.error(f"Failed to save configuration file: {e}")
    
    def _save_change_history(self):
        """Save change history to file"""
        try:
            history_data = [
                {
                    'timestamp': record.timestamp.isoformat(),
                    'path': record.path,
                    'old_value': record.old_value,
                    'new_value': record.new_value,
                    'user': record.user,
                    'reason': record.reason
                }
                for record in self.change_history
            ]
            
            with open(self.history_file, 'w') as f:
                json.dump(history_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save change history: {e}")
    
    def get_config(self, environment: str, path: str = None) -> Any:
        """Get configuration value"""
        config = self.configs.get(environment)
        if not config:
            return None
        
        if path:
            return config.get(path)
        else:
            return config.data
    
    def list_configs(self) -> List[str]:
        """List loaded configurations"""
        return list(self.configs.keys())
    
    def promote_config(self, source_env: str, target_env: str, 
                      user: str = "system", reason: str = "") -> bool:
        """Promote configuration from one environment to another"""
        try:
            source_config = self.configs.get(source_env)
            target_config = self.configs.get(target_env)
            
            if not source_config:
                logger.error(f"Source configuration not found: {source_env}")
                return False
            
            if not target_config:
                logger.error(f"Target configuration not found: {target_env}")
                return False
            
            # Deep copy source data
            import copy
            promoted_data = copy.deepcopy(source_config.data)
            
            # Update environment-specific values
            promoted_data['environment']['name'] = target_env
            
            # Load promoted configuration
            temp_config = EnvironmentConfig(
                name=target_env,
                type=EnvironmentType(promoted_data['environment']['type']),
                data=promoted_data,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Validate promoted configuration
            validation_errors = self.validator.validate(temp_config)
            if validation_errors:
                logger.error(f"Promoted configuration validation failed: {validation_errors}")
                return False
            
            # Apply promotion
            self.configs[target_env].update_data(promoted_data)
            self._save_config_file(target_env)
            
            # Record promotion
            promotion_record = ChangeRecord(
                timestamp=datetime.now(),
                path=f"config_promotion",
                old_value=f"from_{source_env}",
                new_value=f"to_{target_env}",
                user=user,
                reason=reason or f"Promoted from {source_env} to {target_env}"
            )
            self.change_history.append(promotion_record)
            self._save_change_history()
            
            logger.info(f"Configuration promoted from {source_env} to {target_env}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote configuration: {e}")
            return False
    
    def get_change_history(self, environment: str = None, limit: int = 100) -> List[ChangeRecord]:
        """Get configuration change history"""
        filtered_history = self.change_history
        
        if environment:
            filtered_history = [
                record for record in self.change_history
                if record.path.startswith(environment)
            ]
        
        return sorted(filtered_history, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def generate_config_docs(self, output_dir: str = None):
        """Generate configuration documentation"""
        output_dir = Path(output_dir or "environment/docs")
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate configuration schema documentation
        schema_doc = []
        schema_doc.append("# Configuration Schema Documentation\n")
        
        for rule in self.validator.rules:
            schema_doc.append(f"## {rule.path}")
            schema_doc.append(f"**Type:** {rule.type}")
            if rule.required:
                schema_doc.append("**Required:** Yes")
            else:
                schema_doc.append("**Required:** No")
            
            if rule.description:
                schema_doc.append(f"**Description:** {rule.description}")
            
            if rule.choices:
                schema_doc.append(f"**Choices:** {', '.join(rule.choices)}")
            
            if rule.min_length:
                schema_doc.append(f"**Min Length:** {rule.min_length}")
            
            if rule.max_length:
                schema_doc.append(f"**Max Length:** {rule.max_length}")
            
            schema_doc.append("")
        
        with open(output_dir / "config_schema.md", 'w') as f:
            f.write('\n'.join(schema_doc))
        
        # Generate environment-specific documentation
        for env_name, config in self.configs.items():
            env_doc = []
            env_doc.append(f"# {env_name.title()} Environment Configuration\n")
            env_doc.append(f"**Version:** {config.version}")
            env_doc.append(f"**Checksum:** {config.checksum}")
            env_doc.append(f"**Last Updated:** {config.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            # Add configuration tree
            env_doc.append("## Configuration Structure\n")
            env_doc.append("```yaml")
            env_doc.append(yaml.dump(config.data, default_flow_style=False, sort_keys=False))
            env_doc.append("```")
            
            with open(output_dir / f"{env_name}_config.md", 'w') as f:
                f.write('\n'.join(env_doc))
        
        logger.info(f"Configuration documentation generated in {output_dir}")

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Environment Configuration Management')
    parser.add_argument('--config-dir', help='Configuration directory')
    parser.add_argument('--action', choices=['load', 'get', 'update', 'promote', 'docs'], 
                       required=True, help='Action to perform')
    parser.add_argument('--environment', help='Environment name')
    parser.add_argument('--path', help='Configuration path (dot notation)')
    parser.add_argument('--value', help='Configuration value')
    parser.add_argument('--source-env', help='Source environment for promotion')
    parser.add_argument('--target-env', help='Target environment for promotion')
    parser.add_argument('--user', default='system', help='User making the change')
    parser.add_argument('--reason', help='Reason for change')
    parser.add_argument('--output-dir', help='Output directory for documentation')
    
    args = parser.parse_args()
    
    manager = ConfigManager(args.config_dir)
    
    if args.action == 'load':
        if not args.environment:
            print("Error: environment is required for load action")
            return
        config = manager.load_config(args.environment)
        if config:
            print(f"Configuration loaded for {args.environment}")
        else:
            print(f"Failed to load configuration for {args.environment}")
    
    elif args.action == 'get':
        if not args.environment or not args.path:
            print("Error: environment and path are required for get action")
            return
        value = manager.get_config(args.environment, args.path)
        print(value)
    
    elif args.action == 'update':
        if not args.environment or not args.path or not args.value:
            print("Error: environment, path, and value are required for update action")
            return
        if manager.update_config(args.environment, args.path, args.value, args.user, args.reason):
            print(f"Configuration updated successfully")
        else:
            print(f"Failed to update configuration")
    
    elif args.action == 'promote':
        if not args.source_env or not args.target_env:
            print("Error: source-env and target-env are required for promote action")
            return
        if manager.promote_config(args.source_env, args.target_env, args.user, args.reason):
            print(f"Configuration promoted from {args.source_env} to {args.target_env}")
        else:
            print(f"Failed to promote configuration")
    
    elif args.action == 'docs':
        manager.generate_config_docs(args.output_dir)
        print(f"Documentation generated in {args.output_dir or 'environment/docs'}")

if __name__ == '__main__':
    main()