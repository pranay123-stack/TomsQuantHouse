# Environment Management System Documentation

## Overview

The Environment Management System provides comprehensive tools and workflows for managing application configurations across different environments (development, staging, production). It includes secrets management, configuration validation, backup/migration, testing, change tracking, and automated deployment capabilities.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Configuration Management](#configuration-management)
3. [Secrets Management](#secrets-management)
4. [Secure Credentials](#secure-credentials)
5. [Environment Validation](#environment-validation)
6. [Backup and Migration](#backup-and-migration)
7. [Testing and Validation](#testing-and-validation)
8. [Change Tracking](#change-tracking)
9. [Deployment Automation](#deployment-automation)
10. [Management Tools](#management-tools)

## Getting Started

### System Requirements

- Python 3.7 or higher
- Required Python packages: `pyyaml`, `jsonschema`, `cryptography`

### Installation

1. Make the management script executable:
   ```bash
   chmod +x environment/manage.sh
   ```

2. Initialize the system:
   ```bash
   ./environment/manage.sh system init
   ```

### Quick Start

1. **Validate an environment:**
   ```bash
   ./environment/manage.sh config validate production
   ```

2. **Store a secret:**
   ```bash
   ./environment/manage.sh secrets store db_password "your_secret_here"
   ```

3. **Create a backup:**
   ```bash
   ./environment/manage.sh backup create pre_deployment config/
   ```

4. **Run tests:**
   ```bash
   ./environment/manage.sh test run config_validation staging
   ```

5. **Promote environment:**
   ```bash
   ./environment/manage.sh deploy promote staging production
   ```

## Configuration Management

### Environment Configuration Files

The system uses `config/environments.yaml` to define all environment-specific settings. This includes:

- **API Configuration**: Base URLs, timeouts, retry settings
- **Database Configuration**: Connection parameters, pool sizes
- **Security Settings**: JWT secrets, session timeouts
- **Feature Flags**: Debug mode, caching, rate limiting
- **Resource Limits**: CPU, memory, storage limits

### Environment Types

1. **Development**: Local development and testing
2. **Staging**: Pre-production testing environment
3. **Production**: Live production environment

### Example Configuration

```yaml
environments:
  production:
    api:
      base_url: "https://api.example.com"
      timeout: 30000
      retry_attempts: 5
    database:
      host: "${DB_HOST_PROD}"
      port: 5432
      name: "app_prod"
      username: "${DB_USER_PROD}"
      password: "${DB_PASSWORD_PROD}"
      ssl_mode: "require"
```

## Secrets Management

### Features

- **Encryption**: All secrets are encrypted at rest
- **Rotation**: Automated secret rotation based on schedules
- **Access Control**: Role-based access to secrets
- **Audit Logging**: All secret operations are logged
- **Environment Isolation**: Secrets are isolated by environment

### Usage

1. **Store a secret:**
   ```bash
   ./environment/manage.sh secrets store api_key "your_api_key"
   ```

2. **Retrieve a secret:**
   ```bash
   ./environment/manage.sh secrets retrieve api_key
   ```

3. **List all secrets:**
   ```bash
   ./environment/manage.sh secrets list
   ```

4. **Rotate secrets:**
   ```bash
   ./environment/manage.sh secrets rotate api_key
   ```

### Secret Types

- **Passwords**: General passwords and credentials
- **API Keys**: API keys and tokens
- **JWT Secrets**: JWT signing secrets
- **Encryption Keys**: Encryption/decryption keys

### Rotation Schedule

- **Database passwords**: Every 90 days
- **API keys**: Every 365 days
- **JWT secrets**: Every 30 days
- **Encryption keys**: Every 180 days

## Secure Credentials

### Features

- **Centralized Storage**: All credentials in one secure location
- **Access Control**: Role-based permissions
- **Encryption**: Credentials encrypted at rest
- **Versioning**: Track credential changes
- **Search**: Index by tags, types, owners

### Credential Types

- **Database**: Database connection credentials
- **API Key**: API authentication keys
- **Service Account**: Service account credentials
- **Certificate**: SSL/TLS certificates
- **Token**: Access tokens
- **Password**: General passwords

### Usage

1. **Create a credential:**
   ```bash
   ./environment/manage.sh creds create db_creds database "username:password"
   ```

2. **Get a credential:**
   ```bash
   ./environment/manage.sh creds get cred_000001
   ```

3. **List credentials:**
   ```bash
   ./environment/manage.sh creds list --type database
   ```

## Environment Validation

### Features

- **Variable Validation**: Check environment variables
- **Type Checking**: Validate variable types and formats
- **Required Variables**: Ensure all required variables are set
- **Documentation**: Generate comprehensive documentation
- **Templates**: Generate environment-specific templates

### Validation Rules

- **Required**: Variables must be set
- **Type Validation**: Check data types (string, integer, boolean, etc.)
- **Format Validation**: Validate URLs, emails, IP addresses
- **Range Validation**: Check minimum/maximum values
- **Pattern Validation**: Validate against regex patterns

### Usage

1. **Validate environment:**
   ```bash
   ./environment/manage.sh config validate production
   ```

2. **Generate environment file:**
   ```bash
   ./environment/manage.sh config generate production .env.production
   ```

3. **Generate documentation:**
   ```bash
   ./environment/manage.sh config docs
   ```

### Variable Types

- **STRING**: General string values
- **INTEGER**: Integer numbers
- **FLOAT**: Decimal numbers
- **BOOLEAN**: true/false values
- **URL**: HTTP/HTTPS URLs
- **EMAIL**: Email addresses
- **IP_ADDRESS**: IPv4 addresses
- **PORT**: Port numbers (1-65535)
- **PATH**: File/directory paths
- **SECRET**: Sensitive data
- **TIME_DURATION**: Time durations (30s, 5m, 2h)
- **SIZE_BYTES**: Size values (100, 1.5KB, 500MB)

## Backup and Migration

### Features

- **Automated Backups**: Create encrypted backups
- **Configuration Migration**: Migrate between environments
- **Version Control**: Track configuration changes
- **Rollback**: Restore previous configurations
- **Integrity Checking**: Verify backup integrity

### Backup Features

- **Compression**: Compress backups to save space
- **Encryption**: Encrypt sensitive data
- **Checksums**: Verify backup integrity
- **Retention**: Automatic cleanup of old backups
- **Metadata**: Store backup information

### Migration Features

- **Environment Migration**: Migrate configurations
- **Validation**: Verify migration success
- **Rollback Plans**: Automatic rollback on failure
- **Step-by-Step**: Track migration progress

### Usage

1. **Create backup:**
   ```bash
   ./environment/manage.sh backup create pre_deployment config/
   ```

2. **List backups:**
   ```bash
   ./environment/manage.sh backup list
   ```

3. **Restore backup:**
   ```bash
   ./environment/manage.sh backup restore backup_20241102_143000 restored_config/
   ```

4. **Create migration:**
   ```bash
   ./environment/manage.sh migration create staging production
   ```

5. **Execute migration:**
   ```bash
   ./environment/manage.sh migration execute migration_20241102_143000
   ```

## Testing and Validation

### Features

- **Comprehensive Testing**: Multiple test suites
- **Environment-Specific**: Tests tailored to each environment
- **Automated Execution**: Run tests automatically
- **Reporting**: Detailed test reports
- **Continuous Integration**: Integrate with CI/CD pipelines

### Test Suites

1. **Configuration Validation**
   - Required environment variables
   - Configuration file validity
   - Environment variable formats

2. **Security Validation**
   - Secrets encryption
   - Access controls
   - SSL certificates
   - Firewall rules

3. **Connectivity Validation**
   - Database connectivity
   - Redis connectivity
   - API endpoints
   - External services

4. **Resource Validation**
   - CPU limits
   - Memory limits
   - Storage limits
   - Network limits

### Usage

1. **List test suites:**
   ```bash
   ./environment/manage.sh test list
   ```

2. **Run test suite:**
   ```bash
   ./environment/manage.sh test run config_validation production
   ```

3. **Generate test report:**
   ```bash
   ./environment/manage.sh test report production
   ```

### Test Results

Each test generates:
- **Status**: Passed, failed, skipped, error
- **Duration**: Test execution time
- **Details**: Test-specific information
- **Recommendations**: Improvement suggestions

## Change Tracking

### Features

- **File Monitoring**: Watch configuration files for changes
- **Change Recording**: Log all configuration changes
- **Approval Workflow**: Require approval for critical changes
- **Audit Trail**: Complete audit log
- **Compliance**: Check compliance with rules

### Change Types

- **CREATE**: New files created
- **UPDATE**: Files modified
- **DELETE**: Files deleted
- **MOVE**: Files moved
- **RENAME**: Files renamed

### Severity Levels

- **CRITICAL**: Production changes, security updates
- **HIGH**: Important configuration changes
- **MEDIUM**: Standard configuration updates
- **LOW**: Documentation changes
- **INFO**: Informational changes

### Usage

1. **Start monitoring:**
   ```bash
   ./environment/manage.sh track monitor 5
   ```

2. **Record manual change:**
   ```bash
   ./environment/manage.sh track change config/production.yaml update user123 "Updated database settings"
   ```

3. **List changes:**
   ```bash
   ./environment/manage.sh track list
   ```

4. **Approve change:**
   ```bash
   ./environment/manage.sh track approve change_20241102_143000 admin_user "Looks good"
   ```

### Compliance Rules

The system includes built-in compliance rules:

1. **Critical files require approval**
2. **Production changes require description**
3. **Secret file changes must be logged**

## Deployment Automation

### Features

- **Deployment Planning**: Create structured deployment plans
- **Automated Execution**: Execute deployments automatically
- **Environment Promotion**: Promote configurations between environments
- **Rollback**: Automatic rollback on failures
- **Approval Workflow**: Require approval for production deployments

### Deployment Types

1. **INITIAL**: Initial deployment to environment
2. **UPDATE**: Update existing deployment
3. **ROLLBACK**: Rollback to previous version
4. **CANARY**: Gradual rollout deployment
5. **BLUE_GREEN**: Zero-downtime deployment

### Deployment Phases

1. **Planning**: Validate deployment plan
2. **Validation**: Validate source and target environments
3. **Backup**: Create pre-deployment backup
4. **Migration**: Migrate configuration
5. **Testing**: Run validation tests
6. **Deployment**: Apply changes
7. **Verification**: Verify deployment success

### Usage

1. **Create deployment plan:**
   ```bash
   ./environment/manage.sh deploy plan create "Production Update" staging production
   ```

2. **Execute deployment:**
   ```bash
   ./environment/manage.sh deploy execute plan_20241102_143000
   ```

3. **Promote environment:**
   ```bash
   ./environment/manage.sh deploy promote staging production
   ```

4. **Check deployment status:**
   ```bash
   ./environment/manage.sh deploy status exec_20241102_143000
   ```

### Approval Workflow

Production deployments and critical changes require approval:

1. **Submit for approval**: Change marked as pending
2. **Review**: Administrator reviews the change
3. **Approve/Reject**: Approve or reject with comments
4. **Execute**: Approved changes can be executed

## Management Tools

### System Management

1. **Initialize system:**
   ```bash
   ./environment/manage.sh system init
   ```

2. **Check system health:**
   ```bash
   ./environment/manage.sh system health
   ```

3. **Cleanup old files:**
   ```bash
   ./environment/manage.sh system cleanup
   ```

4. **Generate system report:**
   ```bash
   ./environment/manage.sh system report
   ```

### Command Line Options

- **-h, --help**: Show help message
- **-v, --verbose**: Verbose output
- **-q, --quiet**: Quiet output
- **--dry-run**: Show what would be done without executing

### Directory Structure

```
environment/
├── config/
│   ├── environments.yaml          # Environment definitions
│   └── *.yaml                     # Additional config files
├── tools/
│   ├── secrets_manager.py         # Secrets management
│   ├── secure_credentials.py      # Credential storage
│   ├── env_validator.py           # Environment validation
│   ├── config_backup_migration.py # Backup and migration
│   ├── env_tester.py              # Testing framework
│   ├── change_tracker.py          # Change tracking
│   └── deploy_automation.py       # Deployment automation
├── backup/
│   ├── backups/                   # Backup files
│   └── backup_metadata.db         # Backup metadata
├── audit/
│   ├── changes/                   # Change records
│   └── audit_log.db               # Audit database
├── testing/
│   ├── suites/                    # Test suites
│   ├── reports/                   # Test reports
│   └── test_results.db            # Test results
├── secure_credentials/
│   ├── config/                    # Credential config
│   └── storage/                   # Credential storage
├── migrations/                    # Migration plans
├── docs/                          # Generated documentation
├── deployments/
│   ├── plans/                     # Deployment plans
│   └── executions/                # Execution records
└── logs/                          # System logs
```

## Best Practices

### Security

1. **Never commit secrets** to version control
2. **Use strong passwords** for all credentials
3. **Enable MFA** for all user accounts
4. **Regularly rotate** secrets and passwords
5. **Audit access** to sensitive resources

### Configuration Management

1. **Use environment-specific** configurations
2. **Validate configurations** before deployment
3. **Keep configurations** under version control
4. **Document all** configuration changes
5. **Test configurations** in non-production first

### Backup Strategy

1. **Create backups** before any deployment
2. **Verify backup** integrity regularly
3. **Store backups** in secure locations
4. **Test restore** procedures periodically
5. **Cleanup old** backups automatically

### Deployment

1. **Plan deployments** carefully
2. **Use approval** workflows for production
3. **Test thoroughly** before production
4. **Have rollback** plans ready
5. **Monitor deployments** closely

## Troubleshooting

### Common Issues

1. **Missing environment variables**
   - Check variable names and spelling
   - Verify variables are set in correct files
   - Run validation to identify issues

2. **Secret access errors**
   - Verify master key is set correctly
   - Check user permissions
   - Review audit logs

3. **Test failures**
   - Check environment configuration
   - Verify connectivity to services
   - Review test output for details

4. **Deployment failures**
   - Check backup availability
   - Verify target environment state
   - Review deployment logs

### Getting Help

1. **Check logs** in `logs/` directory
2. **Run health checks** to identify issues
3. **Review system report** for overview
4. **Check documentation** for examples

## API Reference

### Python Classes

#### SecretsManager

```python
from tools.secrets_manager import SecretsManager

# Initialize
manager = SecretsManager()

# Store secret
manager.store_secret("name", "value", "password")

# Retrieve secret
value = manager.retrieve_secret("name")

# Rotate secret
manager.rotate_secret("name")
```

#### EnvironmentValidator

```python
from tools.env_validator import EnvironmentValidator

# Initialize
validator = EnvironmentValidator()

# Validate environment
report = validator.validate_environment("production")

# Generate environment file
validator.generate_env_file("production", ".env.production")
```

#### ConfigurationBackup

```python
from tools.config_backup_migration import ConfigurationBackup

# Initialize
backup = ConfigurationBackup()

# Create backup
backup_id = backup.create_backup(
    ["config/"], "backup_name", "production"
)

# Restore backup
backup.restore_backup(backup_id, "target_path")
```

#### EnvironmentTester

```python
from tools.env_tester import EnvironmentTester

# Initialize
tester = EnvironmentTester()

# Run test suite
report = tester.run_test_suite("config_validation", "production")

# List test suites
suites = tester.list_test_suites()
```

### Database Schema

#### Backup Metadata

```sql
CREATE TABLE backups (
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
);
```

#### Change Records

```sql
CREATE TABLE change_records (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    change_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    user_id TEXT NOT NULL,
    user_name TEXT NOT NULL,
    environment TEXT NOT NULL,
    description TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL
);
```

## Contributing

### Development Setup

1. **Clone repository**
2. **Install dependencies**
3. **Run tests**
4. **Follow coding standards**

### Adding New Features

1. **Create feature branch**
2. **Implement functionality**
3. **Add tests**
4. **Update documentation**
5. **Submit pull request**

### Code Standards

- **Python**: Follow PEP 8
- **Documentation**: Use docstrings
- **Testing**: Include unit tests
- **Logging**: Use appropriate log levels
- **Error Handling**: Handle exceptions properly

## License

This Environment Management System is provided as-is for internal use. Please ensure compliance with your organization's security policies and procedures.