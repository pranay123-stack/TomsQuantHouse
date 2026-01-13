#!/bin/bash

# Environment Management System - Main Management Script
# Provides unified interface to all environment management tools

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$(dirname "$SCRIPT_DIR")"
TOOLS_DIR="$SCRIPT_DIR/tools"

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to print usage
print_usage() {
    cat << EOF
Environment Management System

Usage: $0 <command> [options]

Commands:
    
    # Environment Configuration
    config validate <environment>         Validate environment configuration
    config generate <environment> <file>  Generate environment file
    config docs                          Generate documentation
    
    # Secrets Management
    secrets store <name> <value> [opts]   Store a secret
    secrets retrieve <name>               Retrieve a secret
    secrets list                          List all secrets
    secrets rotate [name]                 Rotate secrets
    
    # Secure Credentials
    creds create <name> <type> <value>    Create credential
    creds get <id>                        Get credential
    creds list                            List credentials
    creds delete <id>                     Delete credential
    
    # Backup and Migration
    backup create <name> <paths...>       Create backup
    backup list                           List backups
    backup restore <id> <target>          Restore backup
    
    migration create <source> <target>    Create migration plan
    migration execute <id>                Execute migration
    migration list                        List migrations
    
    # Testing and Validation
    test list                             List test suites
    test run <suite> <environment>        Run test suite
    test report <environment>             Generate test report
    
    # Change Tracking
    track monitor [interval]              Start file monitoring
    track change <file> <type> <user>     Record change
    track list                            List changes
    track approve <id> <user>             Approve change
    
    # Deployment Automation
    deploy plan create <name> <src> <dst> Create deployment plan
    deploy execute <plan_id>              Execute deployment
    deploy promote <src> <dst>            Promote environment
    deploy status <execution_id>          Check deployment status
    
    # System Management
    system init                           Initialize environment management
    system health                         Check system health
    system cleanup                        Clean old backups and logs
    system report                         Generate system report

Options:
    -h, --help                           Show this help message
    -v, --verbose                        Verbose output
    -q, --quiet                          Quiet output
    --dry-run                            Show what would be done without executing

Examples:
    $0 config validate production
    $0 secrets store db_password "secret123"
    $0 backup create pre_deployment config/
    $0 deploy plan create "Prod Update" dev prod
    $0 test run config_validation staging

EOF
}

# Function to check prerequisites
check_prerequisites() {
    local missing_deps=()
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check for required Python packages
    if ! python3 -c "import yaml, jsonschema, cryptography" &> /dev/null; then
        echo "Installing required Python packages..."
        pip3 install pyyaml jsonschema cryptography || {
            print_color $RED "Failed to install Python dependencies"
            exit 1
        }
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_color $RED "Missing dependencies: ${missing_deps[*]}"
        print_color $YELLOW "Please install missing dependencies and try again"
        exit 1
    fi
}

# Function to initialize system
init_system() {
    print_color $BLUE "Initializing Environment Management System..."
    
    # Create directory structure
    mkdir -p "$ENV_DIR"/{config,tools,docs,templates,validation,backup,migration,testing,audit,deployment}
    mkdir -p "$ENV_DIR/secure_credentials"/{config,storage}
    mkdir -p logs
    
    # Set permissions
    chmod 700 "$ENV_DIR/secure_credentials"
    chmod 700 "$ENV_DIR/secure_credentials/config"
    chmod 700 "$ENV_DIR/secure_credentials/storage"
    
    # Make scripts executable
    chmod +x "$TOOLS_DIR"/*.py
    
    # Create default configuration if it doesn't exist
    if [ ! -f "$ENV_DIR/config/environments.yaml" ]; then
        print_color $YELLOW "Creating default environment configuration..."
        # This would be populated from the environments.yaml we created earlier
    fi
    
    # Initialize databases
    python3 -c "
from tools.secrets_manager import SecretsManager
from tools.secure_credentials import CredentialManager
from tools.config_backup_migration import ConfigurationBackup
from tools.change_tracker import ConfigurationChangeTracker
import os
os.makedirs('environment/backup', exist_ok=True)
os.makedirs('environment/audit', exist_ok=True)
SecretsManager()
ConfigurationBackup()
ConfigurationChangeTracker()
CredentialManager(Path('environment/secure_credentials'))
print('Databases initialized')
"
    
    print_color $GREEN "Environment Management System initialized successfully!"
}

# Function to validate environment
validate_environment() {
    local environment=$1
    
    if [ -z "$environment" ]; then
        print_color $RED "Environment name is required"
        return 1
    fi
    
    print_color $BLUE "Validating environment: $environment"
    
    python3 "$TOOLS_DIR/env_validator.py" validate "$environment"
}

# Function to generate environment file
generate_env_file() {
    local environment=$1
    local output_file=$2
    
    if [ -z "$environment" ] || [ -z "$output_file" ]; then
        print_color $RED "Environment and output file are required"
        return 1
    fi
    
    print_color $BLUE "Generating environment file for: $environment"
    
    python3 "$TOOLS_DIR/env_validator.py" generate-env "$environment" "$output_file"
}

# Function to generate documentation
generate_docs() {
    print_color $BLUE "Generating documentation..."
    
    python3 "$TOOLS_DIR/env_validator.py" generate-docs "$ENV_DIR/docs"
    
    print_color $GREEN "Documentation generated in $ENV_DIR/docs/"
}

# Function to store secret
store_secret() {
    local name=$1
    local value=$2
    shift 2
    local type="password"
    local environment="global"
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                type="$2"
                shift 2
                ;;
            --env)
                environment="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    if [ -z "$name" ] || [ -z "$value" ]; then
        print_color $RED "Secret name and value are required"
        return 1
    fi
    
    print_color $BLUE "Storing secret: $name"
    
    python3 "$TOOLS_DIR/secrets_manager.py" store "$name" "$value" --type "$type" --env "$environment"
    
    print_color $GREEN "Secret stored successfully"
}

# Function to retrieve secret
retrieve_secret() {
    local name=$1
    local environment="global"
    
    # Parse options
    shift
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                environment="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    if [ -z "$name" ]; then
        print_color $RED "Secret name is required"
        return 1
    fi
    
    print_color $BLUE "Retrieving secret: $name"
    
    python3 "$TOOLS_DIR/secrets_manager.py" retrieve "$name" --env "$environment"
}

# Function to list secrets
list_secrets() {
    print_color $BLUE "Listing secrets..."
    
    python3 "$TOOLS_DIR/secrets_manager.py" list
}

# Function to rotate secrets
rotate_secret() {
    local name=$1
    local environment="global"
    
    # Parse options
    shift
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                environment="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    print_color $BLUE "Rotating secret: $name"
    
    python3 "$TOOLS_DIR/secrets_manager.py" rotate "$name" --env "$environment"
    
    print_color $GREEN "Secret rotated successfully"
}

# Function to create backup
create_backup() {
    local name=$1
    shift
    local paths=("$@")
    
    if [ -z "$name" ] || [ ${#paths[@]} -eq 0 ]; then
        print_color $RED "Backup name and paths are required"
        return 1
    fi
    
    print_color $BLUE "Creating backup: $name"
    
    python3 "$TOOLS_DIR/config_backup_migration.py" backup create "$name" "${paths[@]}"
}

# Function to list backups
list_backups() {
    print_color $BLUE "Listing backups..."
    
    python3 "$TOOLS_DIR/config_backup_migration.py" backup list
}

# Function to restore backup
restore_backup() {
    local backup_id=$1
    local target=$2
    
    if [ -z "$backup_id" ] || [ -z "$target" ]; then
        print_color $RED "Backup ID and target path are required"
        return 1
    fi
    
    print_color $BLUE "Restoring backup: $backup_id"
    
    python3 "$TOOLS_DIR/config_backup_migration.py" backup restore "$backup_id" "$target"
    
    print_color $GREEN "Backup restored successfully"
}

# Function to create migration
create_migration() {
    local source=$1
    local target=$2
    local name=${3:-"Migration $source to $target"}
    
    if [ -z "$source" ] || [ -z "$target" ]; then
        print_color $RED "Source and target environments are required"
        return 1
    fi
    
    print_color $BLUE "Creating migration: $source -> $target"
    
    python3 "$TOOLS_DIR/config_backup_migration.py" migration create "$source" "$target" "$name"
    
    print_color $GREEN "Migration created successfully"
}

# Function to execute migration
execute_migration() {
    local migration_id=$1
    
    if [ -z "$migration_id" ]; then
        print_color $RED "Migration ID is required"
        return 1
    fi
    
    print_color $BLUE "Executing migration: $migration_id"
    
    python3 "$TOOLS_DIR/config_backup_migration.py" migration execute "$migration_id"
}

# Function to list migrations
list_migrations() {
    print_color $BLUE "Listing migrations..."
    
    python3 "$TOOLS_DIR/config_backup_migration.py" migration list
}

# Function to list test suites
list_test_suites() {
    print_color $BLUE "Listing test suites..."
    
    python3 "$TOOLS_DIR/env_tester.py" list-suites
}

# Function to run test suite
run_test() {
    local suite=$1
    local environment=$2
    
    if [ -z "$suite" ] || [ -z "$environment" ]; then
        print_color $RED "Test suite and environment are required"
        return 1
    fi
    
    print_color $BLUE "Running test suite: $suite on $environment"
    
    python3 "$TOOLS_DIR/env_tester.py" run-suite "$suite" --env "$environment"
}

# Function to generate test report
generate_test_report() {
    local environment=$1
    local output_file=${2:-"test_report.json"}
    
    if [ -z "$environment" ]; then
        print_color $RED "Environment is required"
        return 1
    fi
    
    print_color $BLUE "Generating test report for: $environment"
    
    python3 "$TOOLS_DIR/env_tester.py" list-reports --env "$environment" --limit 1
}

# Function to start change tracking monitoring
start_monitoring() {
    local interval=${1:-5}
    
    print_color $BLUE "Starting file monitoring (interval: ${interval}s)"
    
    python3 "$TOOLS_DIR/change_tracker.py" monitor --interval "$interval"
}

# Function to record change
record_change() {
    local file_path=$1
    local change_type=$2
    local user_id=$3
    local user_name=${4:-"$user_id"}
    local environment=${5:-"unknown"}
    local description=${6:-"Manual change"}
    
    if [ -z "$file_path" ] || [ -z "$change_type" ] || [ -z "$user_id" ]; then
        print_color $RED "File path, change type, and user ID are required"
        return 1
    fi
    
    print_color $BLUE "Recording change: $file_path"
    
    python3 "$TOOLS_DIR/change_tracker.py" change record "$file_path" "$change_type" "$user_id" "$user_name" "$environment" "$description"
}

# Function to list changes
list_changes() {
    print_color $BLUE "Listing changes..."
    
    python3 "$TOOLS_DIR/change_tracker.py" list-changes
}

# Function to approve change
approve_change() {
    local change_id=$1
    local approver_id=$2
    local approver_name=${3:-"$approver_id"}
    
    if [ -z "$change_id" ] || [ -z "$approver_id" ]; then
        print_color $RED "Change ID and approver ID are required"
        return 1
    fi
    
    print_color $BLUE "Approving change: $change_id"
    
    python3 "$TOOLS_DIR/change_tracker.py" approve "$change_id" "$approver_id" "$approver_name"
}

# Function to create deployment plan
create_deployment_plan() {
    local name=$1
    local source_env=$2
    local target_env=$3
    
    if [ -z "$name" ] || [ -z "$source_env" ] || [ -z "$target_env" ]; then
        print_color $RED "Name, source environment, and target environment are required"
        return 1
    fi
    
    print_color $BLUE "Creating deployment plan: $name"
    
    python3 "$TOOLS_DIR/deploy_automation.py" plan create "$name" "$source_env" "$target_env"
    
    print_color $GREEN "Deployment plan created successfully"
}

# Function to execute deployment
execute_deployment() {
    local plan_id=$1
    
    if [ -z "$plan_id" ]; then
        print_color $RED "Plan ID is required"
        return 1
    fi
    
    print_color $BLUE "Executing deployment: $plan_id"
    
    python3 "$TOOLS_DIR/deploy_automation.py" execute "$plan_id"
    
    print_color $GREEN "Deployment executed successfully"
}

# Function to promote environment
promote_environment() {
    local source_env=$1
    local target_env=$2
    local description=${3:-"Promote $source_env to $target_env"}
    
    if [ -z "$source_env" ] || [ -z "$target_env" ]; then
        print_color $RED "Source and target environments are required"
        return 1
    fi
    
    print_color $BLUE "Promoting environment: $source_env -> $target_env"
    
    python3 "$TOOLS_DIR/deploy_automation.py" promote "$source_env" "$target_env" --description "$description"
    
    print_color $GREEN "Environment promotion initiated"
}

# Function to check deployment status
check_deployment_status() {
    local execution_id=$1
    
    if [ -z "$execution_id" ]; then
        print_color $RED "Execution ID is required"
        return 1
    fi
    
    print_color $BLUE "Checking deployment status: $execution_id"
    
    python3 "$TOOLS_DIR/deploy_automation.py" status "$execution_id"
}

# Function to check system health
check_system_health() {
    print_color $BLUE "Checking system health..."
    
    # Check directories
    local dirs=("$ENV_DIR/config" "$ENV_DIR/tools" "$ENV_DIR/backup" "$ENV_DIR/audit")
    for dir in "${dirs[@]}"; do
        if [ -d "$dir" ]; then
            print_color $GREEN "✓ Directory exists: $dir"
        else
            print_color $RED "✗ Directory missing: $dir"
        fi
    done
    
    # Check databases
    if [ -f "$ENV_DIR/backup/backup_metadata.db" ]; then
        print_color $GREEN "✓ Backup database exists"
    else
        print_color $YELLOW "! Backup database missing (will be created on first use)"
    fi
    
    if [ -f "$ENV_DIR/audit/audit_log.db" ]; then
        print_color $GREEN "✓ Audit database exists"
    else
        print_color $YELLOW "! Audit database missing (will be created on first use)"
    fi
    
    # Check scripts
    local scripts=("secrets_manager.py" "env_validator.py" "config_backup_migration.py")
    for script in "${scripts[@]}"; do
        if [ -x "$TOOLS_DIR/$script" ]; then
            print_color $GREEN "✓ Script executable: $script"
        else
            print_color $RED "✗ Script not executable: $script"
        fi
    done
    
    print_color $GREEN "System health check completed"
}

# Function to cleanup old files
cleanup_system() {
    print_color $BLUE "Cleaning up old files..."
    
    # Clean old backups (older than 90 days)
    find "$ENV_DIR/backup/backups" -type f -mtime +90 -delete 2>/dev/null || true
    
    # Clean old logs (older than 30 days)
    find logs -name "*.log" -type f -mtime +30 -delete 2>/dev/null || true
    
    # Clean temporary files
    find "$ENV_DIR" -name "*.tmp" -delete 2>/dev/null || true
    
    print_color $GREEN "Cleanup completed"
}

# Function to generate system report
generate_system_report() {
    print_color $BLUE "Generating system report..."
    
    local report_file="system_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "Environment Management System Report"
        echo "===================================="
        echo "Generated: $(date)"
        echo ""
        
        echo "Configuration Files:"
        find "$ENV_DIR/config" -type f 2>/dev/null | head -20
        echo ""
        
        echo "Backups:"
        python3 "$TOOLS_DIR/config_backup_migration.py" backup list 2>/dev/null || echo "No backups found"
        echo ""
        
        echo "Recent Changes:"
        python3 "$TOOLS_DIR/change_tracker.py" list-changes --limit 10 2>/dev/null || echo "No changes found"
        echo ""
        
        echo "Test Reports:"
        python3 "$TOOLS_DIR/env_tester.py" list-reports --limit 5 2>/dev/null || echo "No test reports found"
        echo ""
        
        echo "Deployment History:"
        python3 "$TOOLS_DIR/deploy_automation.py" list-executions --limit 5 2>/dev/null || echo "No deployments found"
        
    } > "$report_file"
    
    print_color $GREEN "System report generated: $report_file"
}

# Function to handle unknown commands
handle_unknown_command() {
    print_color $RED "Unknown command: $1"
    print_color $YELLOW "Use '$0 --help' for usage information"
    exit 1
}

# Main script logic
main() {
    # Parse global options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            -q|--quiet)
                # Redirect stderr to /dev/null for quiet mode
                exec 2>/dev/null
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Parse command
    if [ $# -eq 0 ]; then
        print_usage
        exit 0
    fi
    
    local command=$1
    shift
    
    case $command in
        config)
            local config_cmd=$1
            case $config_cmd in
                validate)
                    validate_environment "$@"
                    ;;
                generate)
                    generate_env_file "$@"
                    ;;
                docs)
                    generate_docs
                    ;;
                *)
                    handle_unknown_command "config $config_cmd"
                    ;;
            esac
            ;;
        secrets)
            local secrets_cmd=$1
            case $secrets_cmd in
                store)
                    store_secret "$@"
                    ;;
                retrieve)
                    retrieve_secret "$@"
                    ;;
                list)
                    list_secrets
                    ;;
                rotate)
                    rotate_secret "$@"
                    ;;
                *)
                    handle_unknown_command "secrets $secrets_cmd"
                    ;;
            esac
            ;;
        creds)
            local creds_cmd=$1
            case $creds_cmd in
                create)
                    # Call Python script directly for credential management
                    python3 "$TOOLS_DIR/secure_credentials.py" create "$@"
                    ;;
                get)
                    python3 "$TOOLS_DIR/secure_credentials.py" get "$@"
                    ;;
                list)
                    python3 "$TOOLS_DIR/secure_credentials.py" list "$@"
                    ;;
                delete)
                    python3 "$TOOLS_DIR/secure_credentials.py" delete "$@"
                    ;;
                *)
                    handle_unknown_command "creds $creds_cmd"
                    ;;
            esac
            ;;
        backup)
            local backup_cmd=$1
            case $backup_cmd in
                create)
                    create_backup "$@"
                    ;;
                list)
                    list_backups
                    ;;
                restore)
                    restore_backup "$@"
                    ;;
                *)
                    handle_unknown_command "backup $backup_cmd"
                    ;;
            esac
            ;;
        migration)
            local migration_cmd=$1
            case $migration_cmd in
                create)
                    create_migration "$@"
                    ;;
                execute)
                    execute_migration "$@"
                    ;;
                list)
                    list_migrations
                    ;;
                *)
                    handle_unknown_command "migration $migration_cmd"
                    ;;
            esac
            ;;
        test)
            local test_cmd=$1
            case $test_cmd in
                list)
                    list_test_suites
                    ;;
                run)
                    run_test "$@"
                    ;;
                report)
                    generate_test_report "$@"
                    ;;
                *)
                    handle_unknown_command "test $test_cmd"
                    ;;
            esac
            ;;
        track)
            local track_cmd=$1
            case $track_cmd in
                monitor)
                    start_monitoring "$@"
                    ;;
                change)
                    record_change "$@"
                    ;;
                list)
                    list_changes
                    ;;
                approve)
                    approve_change "$@"
                    ;;
                *)
                    handle_unknown_command "track $track_cmd"
                    ;;
            esac
            ;;
        deploy)
            local deploy_cmd=$1
            case $deploy_cmd in
                plan)
                    local plan_cmd=$2
                    case $plan_cmd in
                        create)
                            create_deployment_plan "$@"
                            ;;
                        *)
                            handle_unknown_command "deploy plan $plan_cmd"
                            ;;
                    esac
                    ;;
                execute)
                    execute_deployment "$@"
                    ;;
                promote)
                    promote_environment "$@"
                    ;;
                status)
                    check_deployment_status "$@"
                    ;;
                *)
                    handle_unknown_command "deploy $deploy_cmd"
                    ;;
            esac
            ;;
        system)
            local system_cmd=$1
            case $system_cmd in
                init)
                    init_system
                    ;;
                health)
                    check_system_health
                    ;;
                cleanup)
                    cleanup_system
                    ;;
                report)
                    generate_system_report
                    ;;
                *)
                    handle_unknown_command "system $system_cmd"
                    ;;
            esac
            ;;
        *)
            handle_unknown_command "$command"
            ;;
    esac
}

# Run main function
main "$@"