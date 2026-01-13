#!/bin/bash

################################################################################
# Backup and Recovery Orchestration Script
# Main entry point for all backup and recovery operations
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/../config"
LOG_DIR="/var/log/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/backup_orchestration_${TIMESTAMP}.log"

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Error handler
error_exit() {
    log "ERROR: $*"
    exit 1
}

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND

Commands:
    backup-full              Run full backup of all systems
    backup-incremental       Run incremental backup
    backup-cleanup           Clean up old backups
    validate-backups         Validate backup integrity
    dr-test                  Run disaster recovery tests
    rto-test                 Test recovery time objectives
    rpo-test                 Test recovery point objectives
    rotate-keys              Rotate encryption keys
    replicate-cross-region   Trigger cross-region replication
    failover-test            Test failover procedures
    status                   Show backup status
    help                     Show this help message

Options:
    -h, --help               Show this help
    -v, --verbose            Verbose output
    -d, --debug              Debug mode
    --dry-run                Show what would be done without executing
    --config PATH            Path to configuration file (default: ${CONFIG_DIR}/backup_config.yaml)
    --parallel-workers N     Number of parallel workers (default: 5)

Examples:
    $0 backup-full
    $0 backup-incremental
    $0 dr-test --verbose
    $0 rto-test --dry-run
    $0 status

EOF
}

# Parse command line arguments
VERBOSE=false
DEBUG=false
DRY_RUN=false
CONFIG_FILE="${CONFIG_DIR}/backup_config.yaml"
PARALLEL_WORKERS=5

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --parallel-workers)
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        backup-full|backup-incremental|backup-cleanup|validate-backups|dr-test|rto-test|rpo-test|rotate-keys|replicate-cross-region|failover-test|status)
            COMMAND="$1"
            shift
            ;;
        *)
            error_exit "Unknown option: $1"
            ;;
    esac
done

# Check if command was provided
if [[ -z "${COMMAND:-}" ]]; then
    usage
    exit 1
fi

# Validate configuration file
if [[ ! -f "${CONFIG_FILE}" ]]; then
    error_exit "Configuration file not found: ${CONFIG_FILE}"
fi

# Set up environment
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"
export PATH="${SCRIPT_DIR}:${PATH}"

# Logging configuration
if [[ "${VERBOSE}" == "true" ]]; then
    set -x
fi

################################################################################
# Command Functions
################################################################################

# Full backup command
cmd_backup_full() {
    log "Starting full backup operation..."
    
    local start_time=$(date +%s)
    
    # Run the backup scheduler
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would run: python3 ${SCRIPT_DIR}/backup_scheduler.py --mode full"
    else
        python3 "${SCRIPT_DIR}/backup_scheduler.py" \
            --mode full \
            --config "${CONFIG_FILE}" \
            || error_exit "Backup scheduler failed"
    fi
    
    # Run point-in-time recovery system
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would run: python3 ${SCRIPT_DIR}/pitr_system.py --mode validate"
    else
        python3 "${SCRIPT_DIR}/pitr_system.py" \
            --mode validate \
            || log "WARNING: PITR validation had issues"
    fi
    
    # Encrypt any new backups
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would encrypt backups"
    else
        find /opt/backup -type f -name "*.sql" -o -name "*.tar.gz" | while read -r file; do
            [[ ! -f "${file}.encrypted" ]] || continue
            python3 "${SCRIPT_DIR}/backup_encryption.py" \
                --mode encrypt \
                --file "${file}" \
                || log "WARNING: Failed to encrypt ${file}"
        done
    fi
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "Full backup completed in ${duration} seconds"
}

# Incremental backup command
cmd_backup_incremental() {
    log "Starting incremental backup operation..."
    
    # Run incremental backup
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would run: python3 ${SCRIPT_DIR}/backup_scheduler.py --mode incremental"
    else
        python3 "${SCRIPT_DIR}/backup_scheduler.py" \
            --mode incremental \
            --config "${CONFIG_FILE}" \
            || error_exit "Incremental backup failed"
    fi
    
    log "Incremental backup completed"
}

# Backup cleanup command
cmd_backup_cleanup() {
    log "Starting backup cleanup operation..."
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would run: python3 ${SCRIPT_DIR}/backup_scheduler.py --mode cleanup"
    else
        python3 "${SCRIPT_DIR}/backup_scheduler.py" \
            --mode cleanup \
            --config "${CONFIG_FILE}" \
            || log "WARNING: Backup cleanup had issues"
    fi
    
    log "Backup cleanup completed"
}

# Validate backups command
cmd_validate_backups() {
    log "Starting backup validation..."
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would run: python3 ${SCRIPT_DIR}/backup_validation.py --mode full"
    else
        python3 "${SCRIPT_DIR}/backup_validation.py" \
            --mode full \
            --config "${CONFIG_FILE}" \
            || error_exit "Backup validation failed"
    fi
    
    log "Backup validation completed"
}

# Disaster recovery test command
cmd_dr_test() {
    log "Starting disaster recovery test..."
    
    local test_start=$(date +%s)
    
    # Test backup completeness
    log "Testing backup completeness..."
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would test backup completeness"
    else
        python3 "${SCRIPT_DIR}/backup_validation.py" \
            --mode backup_completeness \
            || log "WARNING: Backup completeness test failed"
    fi
    
    # Test restore procedures
    log "Testing restore procedures..."
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would test restore procedures"
    else
        python3 "${SCRIPT_DIR}/backup_validation.py" \
            --mode restore \
            || log "WARNING: Restore test failed"
    fi
    
    # Test cross-region replication
    log "Testing cross-region replication..."
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would test cross-region replication"
    else
        python3 "${SCRIPT_DIR}/cross_region_replication.py" \
            --mode monitor-lag \
            || log "WARNING: Replication lag test had issues"
    fi
    
    # Test failover procedures
    log "Testing failover procedures..."
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would test failover procedures"
    else
        bash "${SCRIPT_DIR}/../procedures/disaster_recovery_procedures.sh" \
            --mode test \
            --dry-run \
            || log "WARNING: Failover test had issues"
    fi
    
    local test_end=$(date +%s)
    local test_duration=$((test_end - test_start))
    
    log "Disaster recovery test completed in ${test_duration} seconds"
}

# RTO test command
cmd_rto_test() {
    log "Starting RTO (Recovery Time Objective) test..."
    
    # Get test parameters
    local test_system="${1:-production_database}"
    local test_start=$(date +%s)
    
    log "Testing RTO for system: ${test_system}"
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would run RTO test for ${test_system}"
        log "[DRY RUN] Target RTO: 2 hours"
        log "[DRY RUN] Test duration would be simulated"
    else
        # Run RTO test script
        bash "${SCRIPT_DIR}/../tests/rto_test.sh" \
            --system "${test_system}" \
            --verbose \
            || error_exit "RTO test failed"
    fi
    
    local test_end=$(date +%s)
    local test_duration=$((test_end - test_start))
    
    log "RTO test completed in ${test_duration} seconds"
    
    # Record results
    if [[ "${DRY_RUN}" != "true" ]]; then
        echo "${test_duration}" > "/tmp/rto_test_${test_system}_${TIMESTAMP}.result"
    fi
}

# RPO test command
cmd_rpo_test() {
    log "Starting RPO (Recovery Point Objective) test..."
    
    # Get test parameters
    local test_database="${1:-postgresql}"
    local test_start=$(date +%s)
    
    log "Testing RPO for database: ${test_database}"
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would run RPO test for ${test_database}"
        log "[DRY RUN] Target RPO: 15 minutes"
        log "[DRY RUN] Data loss simulation would run"
    else
        # Run RPO test script
        bash "${SCRIPT_DIR}/../tests/rpo_test.sh" \
            --database "${test_database}" \
            --verbose \
            || error_exit "RPO test failed"
    fi
    
    local test_end=$(date +%s)
    local test_duration=$((test_end - test_start))
    
    log "RPO test completed in ${test_duration} seconds"
}

# Rotate keys command
cmd_rotate_keys() {
    log "Starting encryption key rotation..."
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would rotate encryption keys"
        log "[DRY RUN] Would re-encrypt all backups"
    else
        python3 "${SCRIPT_DIR}/backup_encryption.py" \
            --mode rotate-keys \
            || error_exit "Key rotation failed"
    fi
    
    log "Key rotation completed"
}

# Replicate cross-region command
cmd_replicate_cross_region() {
    log "Starting cross-region replication..."
    
    # Get replication configuration
    local backup_type="${1:-s3}"
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would replicate ${backup_type} to all secondary regions"
    else
        # Sample backup data
        local backup_data='{"type":"'"${backup_type}"'","name":"example-bucket"}'
        
        python3 "${SCRIPT_DIR}/cross_region_replication.py" \
            --mode replicate \
            --backup-type "${backup_type}" \
            --backup-data "${backup_data}" \
            || log "WARNING: Cross-region replication had issues"
    fi
    
    log "Cross-region replication completed"
}

# Failover test command
cmd_failover_test() {
    log "Starting failover test..."
    
    # Get test parameters
    local service_type="${1:-database}"
    local target_region="${2:-us-west-2}"
    
    log "Testing failover for ${service_type} to ${target_region}"
    
    if [[ "${DRY_RUN}" == "true" ]]; then
        log "[DRY RUN] Would trigger failover for ${service_type} to ${target_region}"
        log "[DRY RUN] Would update endpoints"
        log "[DRY RUN] Would verify service health"
    else
        python3 "${SCRIPT_DIR}/cross_region_replication.py" \
            --mode failover \
            --service-type "${service_type}" \
            --target-region "${target_region}" \
            || log "WARNING: Failover test had issues"
    fi
    
    log "Failover test completed"
}

# Status command
cmd_status() {
    log "Showing backup system status..."
    
    # Check backup directory
    log "Backup directory: /opt/backup"
    if [[ -d "/opt/backup" ]]; then
        local backup_size=$(du -sh /opt/backup 2>/dev/null | cut -f1)
        log "Backup size: ${backup_size}"
        
        # Count backup files
        local backup_count=$(find /opt/backup -type f 2>/dev/null | wc -l)
        log "Backup files: ${backup_count}"
    else
        log "WARNING: Backup directory not found"
    fi
    
    # Check S3 buckets
    log ""
    log "S3 Backup Status:"
    if command -v aws &> /dev/null; then
        local backup_bucket=$(grep "backup_location:" "${CONFIG_FILE}" | cut -d'"' -f2 | sed 's|s3://||' | cut -d'/' -f1)
        local object_count=$(aws s3api list-objects-v2 --bucket "${backup_bucket}" --query 'length(Contents)' --output text 2>/dev/null || echo "N/A")
        log "  Primary bucket (${backup_bucket}): ${object_count} objects"
        
        local secondary_bucket=$(grep "secondary_location:" "${CONFIG_FILE}" | cut -d'"' -f2 | sed 's|s3://||' | cut -d'/' -f1)
        local secondary_count=$(aws s3api list-objects-v2 --bucket "${secondary_bucket}" --query 'length(Contents)' --output text 2>/dev/null || echo "N/A")
        log "  Secondary bucket (${secondary_bucket}): ${secondary_count} objects"
    else
        log "  AWS CLI not available"
    fi
    
    # Check validation logs
    log ""
    log "Recent Validations:"
    local validation_log="/var/log/backup/validation"
    if [[ -d "${validation_log}" ]]; then
        local last_validation=$(ls -t "${validation_log}"/*.json 2>/dev/null | head -n1)
        if [[ -n "${last_validation}" ]]; then
            log "  Last validation: ${last_validation}"
            if [[ -f "${last_validation}" ]]; then
                python3 -c "
import json
try:
    with open('${last_validation}') as f:
        data = json.load(f)
    summary = data.get('summary', {})
    print('  Results: {}/{} passed, {} failed, {} warnings'.format(
        summary.get('passed', 0),
        summary.get('total', 0),
        summary.get('failed', 0),
        summary.get('warnings', 0)
    ))
except:
    pass
" 2>/dev/null || true
        fi
    else
        log "  No validation logs found"
    fi
    
    # Check running processes
    log ""
    log "Running Processes:"
    local processes=(
        "backup_scheduler"
        "pitr_system"
        "cross_region_replication"
        "backup_encryption"
        "backup_validation"
    )
    
    for process in "${processes[@]}"; do
        if pgrep -f "${process}" > /dev/null; then
            log "  ${process}: RUNNING"
        else
            log "  ${process}: NOT RUNNING"
        fi
    done
    
    # Show disk usage
    log ""
    log "Disk Usage:"
    df -h /opt/backup 2>/dev/null | tail -n1 || log "  Backup partition info not available"
    df -h /var/log/backup 2>/dev/null | tail -n1 || log "  Log partition info not available"
}

################################################################################
# Main Script
################################################################################

log "Starting backup orchestration: ${COMMAND}"
log "Configuration: ${CONFIG_FILE}"
log "Log file: ${LOG_FILE}"

# Execute command
case "${COMMAND}" in
    backup-full)
        cmd_backup_full
        ;;
    backup-incremental)
        cmd_backup_incremental
        ;;
    backup-cleanup)
        cmd_backup_cleanup
        ;;
    validate-backups)
        cmd_validate_backups
        ;;
    dr-test)
        cmd_dr_test
        ;;
    rto-test)
        shift # Remove command from args
        cmd_rto_test "$@"
        ;;
    rpo-test)
        shift # Remove command from args
        cmd_rpo_test "$@"
        ;;
    rotate-keys)
        cmd_rotate_keys
        ;;
    replicate-cross-region)
        shift # Remove command from args
        cmd_replicate_cross_region "$@"
        ;;
    failover-test)
        shift # Remove command from args
        cmd_failover_test "$@"
        ;;
    status)
        cmd_status
        ;;
    *)
        error_exit "Unknown command: ${COMMAND}"
        ;;
esac

log "Backup orchestration completed: ${COMMAND}"
exit 0
