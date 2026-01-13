#!/usr/bin/env python3
"""
Environment Variable Validation and Documentation System
Validates environment variables, provides documentation, and generates templates
"""

import os
import re
import json
import yaml
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import jsonschema
from jsonschema import validate, ValidationError as JsonSchemaValidationError

class ValidationSeverity(Enum):
    """Validation error severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class EnvVarType(Enum):
    """Environment variable types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    URL = "url"
    EMAIL = "email"
    IP_ADDRESS = "ip_address"
    PORT = "port"
    PATH = "path"
    FILE_PATH = "file_path"
    DIRECTORY_PATH = "directory_path"
    SECRET = "secret"
    JSON = "json"
    YAML = "yaml"
    TIME_DURATION = "time_duration"
    SIZE_BYTES = "size_bytes"

@dataclass
class ValidationRule:
    """Validation rule for environment variables"""
    name: str
    type: EnvVarType
    required: bool = False
    default_value: Optional[str] = None
    description: str = ""
    validation_regex: Optional[str] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_values: List[str] = None
    depends_on: List[str] = None
    conditional_required: Optional[Dict[str, Any]] = None
    sensitive: bool = False
    examples: List[str] = field(default_factory=list)
    documentation: str = ""
    environment_specific: Dict[str, Dict] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Validation result for a single variable"""
    variable: str
    is_valid: bool
    value: Optional[str]
    severity: ValidationSeverity
    message: str
    suggestion: Optional[str] = None
    resolved_value: Optional[str] = None

@dataclass
class EnvironmentValidationReport:
    """Complete validation report"""
    environment: str
    timestamp: str
    total_variables: int
    valid_variables: int
    invalid_variables: int
    warnings: int
    results: List[ValidationResult]
    summary: Dict[str, Any]

class EnvironmentValidator:
    """Main environment variable validator"""
    
    def __init__(self, config_path: str = "config/environments.yaml"):
        self.config_path = Path(config_path)
        self.environments_config = self._load_environments_config()
        self.validation_rules = self._load_validation_rules()
        self.logger = logging.getLogger('env_validator')
        
    def _load_environments_config(self) -> Dict:
        """Load environments configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Environments config not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_validation_rules(self) -> Dict[str, ValidationRule]:
        """Load validation rules from configuration"""
        rules = {}
        
        # Get environment variable templates
        env_templates = self.environments_config.get('global', {}).get('env_templates', {})
        
        for env_name, template in env_templates.items():
            variables = template.get('variables', [])
            
            for var_def in variables:
                var_name = var_def['name']
                
                # Create validation rule
                rule = ValidationRule(
                    name=var_name,
                    type=EnvVarType.STRING,  # Default type
                    required=var_def.get('required', False),
                    default_value=var_def.get('default'),
                    description=var_def.get('description', ''),
                    sensitive=var_def.get('sensitive', False),
                    examples=var_def.get('examples', []),
                    documentation=var_def.get('documentation', ''),
                    environment_specific={
                        env_name: {
                            'default_value': var_def.get('default'),
                            'required': var_def.get('required', False)
                        }
                    }
                )
                
                # Determine type based on name patterns
                if var_name.lower().endswith('_password') or var_name.lower().endswith('_secret'):
                    rule.type = EnvVarType.SECRET
                elif 'port' in var_name.lower():
                    rule.type = EnvVarType.PORT
                elif 'url' in var_name.lower() or 'uri' in var_name.lower():
                    rule.type = EnvVarType.URL
                elif var_name.lower().startswith('enable_') or var_name.lower().startswith('disable_'):
                    rule.type = EnvVarType.BOOLEAN
                elif var_name.lower().endswith('_timeout') or var_name.lower().endswith('_duration'):
                    rule.type = EnvVarType.TIME_DURATION
                elif var_name.lower().endswith('_size') or var_name.lower().endswith('_limit'):
                    rule.type = EnvVarType.SIZE_BYTES
                
                rules[var_name] = rule
        
        return rules
    
    def validate_environment(self, environment: str, 
                           custom_vars: Dict[str, str] = None) -> EnvironmentValidationReport:
        """Validate environment variables for a specific environment"""
        custom_vars = custom_vars or {}
        
        # Get environment configuration
        env_config = self.environments_config.get('environments', {}).get(environment, {})
        
        results = []
        
        # Validate each rule
        for var_name, rule in self.validation_rules.items():
            result = self._validate_variable(var_name, rule, environment, custom_vars)
            results.append(result)
        
        # Count results
        valid_count = sum(1 for r in results if r.is_valid)
        warning_count = sum(1 for r in results if r.severity == ValidationSeverity.WARNING)
        
        # Create summary
        summary = {
            'total_variables': len(results),
            'required_variables': sum(1 for r in results if self.validation_rules[r.variable].required),
            'valid_required': sum(1 for r in results if r.is_valid and self.validation_rules[r.variable].required),
            'missing_required': sum(1 for r in results if not r.is_valid and self.validation_rules[r.variable].required),
            'validation_rate': valid_count / len(results) * 100 if results else 0
        }
        
        return EnvironmentValidationReport(
            environment=environment,
            timestamp=datetime.now().isoformat(),
            total_variables=len(results),
            valid_variables=valid_count,
            invalid_variables=len(results) - valid_count,
            warnings=warning_count,
            results=results,
            summary=summary
        )
    
    def _validate_variable(self, var_name: str, rule: ValidationRule,
                          environment: str, custom_vars: Dict[str, str]) -> ValidationResult:
        """Validate a single environment variable"""
        
        # Get value from custom vars or environment
        value = custom_vars.get(var_name) or os.getenv(var_name)
        
        # Check if required
        is_env_specific = rule.environment_specific.get(environment, {})
        is_required = is_env_specific.get('required', rule.required)
        
        if not value and is_required:
            return ValidationResult(
                variable=var_name,
                is_valid=False,
                value=None,
                severity=ValidationSeverity.ERROR,
                message="Required environment variable is missing",
                suggestion=f"Set {var_name} environment variable"
            )
        
        if not value:
            # Use default value if available
            default_value = is_env_specific.get('default_value', rule.default_value)
            if default_value:
                return ValidationResult(
                    variable=var_name,
                    is_valid=True,
                    value=default_value,
                    severity=ValidationSeverity.INFO,
                    message="Using default value",
                    resolved_value=default_value
                )
            else:
                return ValidationResult(
                    variable=var_name,
                    is_valid=True,
                    value=None,
                    severity=ValidationSeverity.INFO,
                    message="Optional variable not set"
                )
        
        # Validate value based on type
        validation_result = self._validate_value(value, rule)
        
        return ValidationResult(
            variable=var_name,
            is_valid=validation_result['valid'],
            value=value,
            severity=validation_result['severity'],
            message=validation_result['message'],
            suggestion=validation_result.get('suggestion'),
            resolved_value=value if validation_result['valid'] else None
        )
    
    def _validate_value(self, value: str, rule: ValidationRule) -> Dict[str, Any]:
        """Validate a single value based on its type and rules"""
        
        try:
            # Type-specific validation
            if rule.type == EnvVarType.BOOLEAN:
                if value.lower() not in ['true', 'false', '1', '0', 'yes', 'no']:
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid boolean value: {value}",
                        'suggestion': "Use true/false, 1/0, yes/no"
                    }
            
            elif rule.type == EnvVarType.INTEGER:
                try:
                    int_value = int(value)
                    if rule.min_value and int_value < rule.min_value:
                        return {
                            'valid': False,
                            'severity': ValidationSeverity.ERROR,
                            'message': f"Value {int_value} is less than minimum {rule.min_value}",
                            'suggestion': f"Use a value >= {rule.min_value}"
                        }
                    if rule.max_value and int_value > rule.max_value:
                        return {
                            'valid': False,
                            'severity': ValidationSeverity.ERROR,
                            'message': f"Value {int_value} is greater than maximum {rule.max_value}",
                            'suggestion': f"Use a value <= {rule.max_value}"
                        }
                except ValueError:
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid integer value: {value}",
                        'suggestion': "Use a valid integer"
                    }
            
            elif rule.type == EnvVarType.FLOAT:
                try:
                    float_value = float(value)
                    if rule.min_value and float_value < rule.min_value:
                        return {
                            'valid': False,
                            'severity': ValidationSeverity.ERROR,
                            'message': f"Value {float_value} is less than minimum {rule.min_value}",
                            'suggestion': f"Use a value >= {rule.min_value}"
                        }
                    if rule.max_value and float_value > rule.max_value:
                        return {
                            'valid': False,
                            'severity': ValidationSeverity.ERROR,
                            'message': f"Value {float_value} is greater than maximum {rule.max_value}",
                            'suggestion': f"Use a value <= {rule.max_value}"
                        }
                except ValueError:
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid float value: {value}",
                        'suggestion': "Use a valid number"
                    }
            
            elif rule.type == EnvVarType.PORT:
                try:
                    port = int(value)
                    if port < 1 or port > 65535:
                        return {
                            'valid': False,
                            'severity': ValidationSeverity.ERROR,
                            'message': f"Invalid port number: {port}",
                            'suggestion': "Use a port between 1 and 65535"
                        }
                except ValueError:
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid port value: {value}",
                        'suggestion': "Use a valid port number"
                    }
            
            elif rule.type == EnvVarType.URL:
                url_pattern = re.compile(
                    r'^https?://'  # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                    r'localhost|'  # localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                    r'(?::\d+)?'  # optional port
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)
                
                if not url_pattern.match(value):
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid URL format: {value}",
                        'suggestion': "Use a valid URL (http:// or https://)"
                    }
            
            elif rule.type == EnvVarType.EMAIL:
                email_pattern = re.compile(
                    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
                
                if not email_pattern.match(value):
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid email format: {value}",
                        'suggestion': "Use a valid email address"
                    }
            
            elif rule.type == EnvVarType.IP_ADDRESS:
                ip_pattern = re.compile(
                    r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}'
                    r'([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$')
                
                if not ip_pattern.match(value):
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid IP address: {value}",
                        'suggestion': "Use a valid IPv4 address"
                    }
            
            elif rule.type == EnvVarType.PATH:
                if not value.startswith('/') and not value.startswith('./'):
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.WARNING,
                        'message': f"Path should be absolute or relative: {value}",
                        'suggestion': "Use absolute paths (starting with /) or relative paths (starting with ./)"
                    }
            
            elif rule.type == EnvVarType.FILE_PATH:
                if not os.path.exists(value):
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.WARNING,
                        'message': f"File does not exist: {value}",
                        'suggestion': "Ensure the file exists or use the correct path"
                    }
            
            elif rule.type == EnvVarType.DIRECTORY_PATH:
                if not os.path.isdir(value):
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.WARNING,
                        'message': f"Directory does not exist: {value}",
                        'suggestion': "Ensure the directory exists or create it"
                    }
            
            elif rule.type == EnvVarType.SIZE_BYTES:
                size_pattern = re.compile(r'^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$', re.IGNORECASE)
                match = size_pattern.match(value)
                if not match:
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid size format: {value}",
                        'suggestion': "Use formats like 100, 1.5KB, 500MB, 2GB"
                    }
            
            elif rule.type == EnvVarType.TIME_DURATION:
                duration_pattern = re.compile(r'^(\d+)\s*([smhd])$', re.IGNORECASE)
                match = duration_pattern.match(value)
                if not match:
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Invalid duration format: {value}",
                        'suggestion': "Use formats like 30s, 5m, 2h, 1d"
                    }
            
            # Generic validations
            if rule.validation_regex:
                if not re.match(rule.validation_regex, value):
                    return {
                        'valid': False,
                        'severity': ValidationSeverity.ERROR,
                        'message': f"Value does not match required pattern: {value}",
                        'suggestion': f"Must match pattern: {rule.validation_regex}"
                    }
            
            if rule.allowed_values and value not in rule.allowed_values:
                return {
                    'valid': False,
                    'severity': ValidationSeverity.ERROR,
                    'message': f"Value '{value}' is not in allowed values",
                    'suggestion': f"Allowed values: {', '.join(rule.allowed_values)}"
                }
            
            if rule.min_length and len(value) < rule.min_length:
                return {
                    'valid': False,
                    'severity': ValidationSeverity.ERROR,
                    'message': f"Value is too short (minimum {rule.min_length} characters)",
                    'suggestion': f"Use at least {rule.min_length} characters"
                }
            
            if rule.max_length and len(value) > rule.max_length:
                return {
                    'valid': False,
                    'severity': ValidationSeverity.ERROR,
                    'message': f"Value is too long (maximum {rule.max_length} characters)",
                    'suggestion': f"Use at most {rule.max_length} characters"
                }
            
            # All validations passed
            return {
                'valid': True,
                'severity': ValidationSeverity.INFO,
                'message': "Value is valid"
            }
            
        except Exception as e:
            return {
                'valid': False,
                'severity': ValidationSeverity.ERROR,
                'message': f"Validation error: {str(e)}",
                'suggestion': "Check the value format"
            }
    
    def generate_env_file(self, environment: str, output_path: str,
                         include_defaults: bool = True,
                         include_comments: bool = True) -> bool:
        """Generate environment file with documentation"""
        try:
            env_config = self.environments_config.get('environments', {}).get(environment, {})
            env_vars = self.environments_config.get('global', {}).get('env_templates', {}).get(environment, {}).get('variables', [])
            
            content = []
            
            if include_comments:
                content.append(f"# Environment: {environment}")
                content.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                content.append("")
            
            for var_def in env_vars:
                var_name = var_def['name']
                rule = self.validation_rules.get(var_name)
                
                if include_comments:
                    content.append(f"# {var_name}")
                    if var_def.get('description'):
                        content.append(f"# Description: {var_def['description']}")
                    
                    if rule and rule.sensitive:
                        content.append("# WARNING: This variable contains sensitive data")
                    
                    if var_def.get('required'):
                        content.append("# Required: Yes")
                    else:
                        content.append("# Required: No")
                    
                    if rule and rule.examples:
                        content.append(f"# Examples: {', '.join(rule.examples)}")
                    
                    content.append("")
                
                # Add the variable
                if include_defaults and var_def.get('default'):
                    content.append(f"{var_name}={var_def['default']}")
                else:
                    content.append(f"{var_name}=")
                
                content.append("")
            
            # Write to file
            with open(output_path, 'w') as f:
                f.write('\n'.join(content))
            
            self.logger.info(f"Environment file generated: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate environment file: {e}")
            return False
    
    def generate_documentation(self, output_dir: str) -> bool:
        """Generate comprehensive documentation"""
        try:
            docs_dir = Path(output_dir)
            docs_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate overview documentation
            self._generate_overview_doc(docs_dir)
            
            # Generate environment-specific documentation
            environments = self.environments_config.get('environments', {})
            for env_name in environments.keys():
                self._generate_env_doc(env_name, docs_dir)
            
            # Generate variable reference
            self._generate_variable_reference(docs_dir)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate documentation: {e}")
            return False
    
    def _generate_overview_doc(self, docs_dir: Path):
        """Generate overview documentation"""
        content = """# Environment Configuration Overview

This document provides an overview of the environment configuration system.

## Environments

The system supports multiple environments:

"""
        
        environments = self.environments_config.get('environments', {})
        for env_name, env_config in environments.items():
            content += f"### {env_name.title()}\n"
            content += f"Description: {env_config.get('description', 'N/A')}\n\n"
        
        content += """
## Variable Types

- `STRING`: General string values
- `INTEGER`: Integer numbers
- `FLOAT`: Decimal numbers
- `BOOLEAN`: true/false values
- `URL`: HTTP/HTTPS URLs
- `EMAIL`: Email addresses
- `IP_ADDRESS`: IPv4 addresses
- `PORT`: Port numbers (1-65535)
- `PATH`: File/directory paths
- `SECRET`: Sensitive data (passwords, keys)
- `TIME_DURATION`: Time durations (30s, 5m, 2h, 1d)
- `SIZE_BYTES`: Size values (100, 1.5KB, 500MB, 2GB)

## Validation Rules

All environment variables are validated according to their defined rules:

- Required variables must be set
- Type validation ensures correct formats
- Range validation checks minimum/maximum values
- Pattern validation enforces specific formats
- Sensitive variables are handled with extra care

## Getting Started

1. Choose your environment (development, staging, production)
2. Copy the environment template file
3. Fill in the required variables
4. Validate your configuration
5. Deploy to your environment

"""
        
        with open(docs_dir / "README.md", 'w') as f:
            f.write(content)
    
    def _generate_env_doc(self, environment: str, docs_dir: Path):
        """Generate environment-specific documentation"""
        env_config = self.environments_config.get('environments', {}).get(environment, {})
        env_vars = self.environments_config.get('global', {}).get('env_templates', {}).get(environment, {}).get('variables', [])
        
        content = f"# {environment.title()} Environment\n\n"
        content += f"Description: {env_config.get('description', 'N/A')}\n\n"
        
        content += "## Configuration Variables\n\n"
        content += "| Variable | Required | Type | Description | Default |\n"
        content += "|----------|----------|------|-------------|----------|\n"
        
        for var_def in env_vars:
            var_name = var_def['name']
            rule = self.validation_rules.get(var_name)
            
            required = "Yes" if var_def.get('required') else "No"
            var_type = rule.type.value if rule else "string"
            description = var_def.get('description', 'N/A')
            default = var_def.get('default', 'N/A')
            
            content += f"| {var_name} | {required} | {var_type} | {description} | {default} |\n"
        
        content += "\n## Environment-Specific Settings\n\n"
        
        api_config = env_config.get('api', {})
        content += f"- API Base URL: {api_config.get('base_url', 'N/A')}\n"
        content += f"- Timeout: {api_config.get('timeout', 'N/A')}ms\n"
        content += f"- Retry Attempts: {api_config.get('retry_attempts', 'N/A')}\n\n"
        
        db_config = env_config.get('database', {})
        content += f"- Database Host: {db_config.get('host', 'N/A')}\n"
        content += f"- Database Port: {db_config.get('port', 'N/A')}\n"
        content += f"- Database Name: {db_config.get('name', 'N/A')}\n\n"
        
        # Save documentation
        with open(docs_dir / f"{environment}.md", 'w') as f:
            f.write(content)
    
    def _generate_variable_reference(self, docs_dir: Path):
        """Generate variable reference documentation"""
        content = "# Environment Variable Reference\n\n"
        content += "This document provides a complete reference of all environment variables.\n\n"
        
        # Group variables by type
        variables_by_type = {}
        for var_name, rule in self.validation_rules.items():
            var_type = rule.type.value
            if var_type not in variables_by_type:
                variables_by_type[var_type] = []
            variables_by_type[var_type].append((var_name, rule))
        
        for var_type, variables in variables_by_type.items():
            content += f"## {var_type.title()} Variables\n\n"
            
            for var_name, rule in variables:
                content += f"### {var_name}\n"
                content += f"**Type:** {rule.type.value}\n"
                content += f"**Required:** {'Yes' if rule.required else 'No'}\n"
                content += f"**Description:** {rule.description or 'N/A'}\n"
                
                if rule.default_value:
                    content += f"**Default:** {rule.default_value}\n"
                
                if rule.allowed_values:
                    content += f"**Allowed Values:** {', '.join(rule.allowed_values)}\n"
                
                if rule.examples:
                    content += f"**Examples:** {', '.join(rule.examples)}\n"
                
                content += "\n"
        
        with open(docs_dir / "variables.md", 'w') as f:
            f.write(content)

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Environment Variable Validator")
    subparsers = parser.add_subparsers(dest='command')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate environment')
    validate_parser.add_argument('environment', help='Environment to validate')
    validate_parser.add_argument('--output', help='Output report file (JSON)')
    
    # Generate env file command
    gen_env_parser = subparsers.add_parser('generate-env', help='Generate environment file')
    gen_env_parser.add_argument('environment', help='Environment to generate for')
    gen_env_parser.add_argument('output', help='Output file path')
    gen_env_parser.add_argument('--no-defaults', action='store_true', help='Don\'t include defaults')
    gen_env_parser.add_argument('--no-comments', action='store_true', help='Don\'t include comments')
    
    # Generate docs command
    docs_parser = subparsers.add_parser('generate-docs', help='Generate documentation')
    docs_parser.add_argument('output', help='Output directory for documentation')
    
    # Check command
    check_parser = subparsers.add_parser('check', help='Check specific variable')
    check_parser.add_argument('variable', help='Variable name')
    check_parser.add_argument('value', help='Variable value')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    validator = EnvironmentValidator()
    
    if args.command == 'validate':
        report = validator.validate_environment(args.environment)
        
        print(f"Environment: {report.environment}")
        print(f"Total Variables: {report.total_variables}")
        print(f"Valid: {report.valid_variables}")
        print(f"Invalid: {report.invalid_variables}")
        print(f"Warnings: {report.warnings}")
        print(f"Validation Rate: {report.summary['validation_rate']:.1f}%")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report.__dict__, f, indent=2, default=str)
            print(f"Report saved to: {args.output}")
    
    elif args.command == 'generate-env':
        success = validator.generate_env_file(
            args.environment,
            args.output,
            include_defaults=not args.no_defaults,
            include_comments=not args.no_comments
        )
        print(f"Environment file generated: {success}")
    
    elif args.command == 'generate-docs':
        success = validator.generate_documentation(args.output)
        print(f"Documentation generated: {success}")
    
    elif args.command == 'check':
        rule = validator.validation_rules.get(args.variable)
        if rule:
            result = validator._validate_value(args.value, rule)
            print(f"Valid: {result['valid']}")
            print(f"Message: {result['message']}")
            if result.get('suggestion'):
                print(f"Suggestion: {result['suggestion']}")
        else:
            print("Variable not found in validation rules")

if __name__ == "__main__":
    main()