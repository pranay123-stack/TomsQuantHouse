# Data Retention and Archival Policies

## Overview

This document defines comprehensive data retention and archival policies for all systems and data stores. These policies ensure compliance with legal requirements, optimize storage costs, and maintain historical data accessibility.

## Policy Framework

### Retention Tiers

| Tier | Duration | Storage Class | Access Level | Cost |
|------|----------|---------------|--------------|------|
| Hot | 0-30 days | Standard | Immediate | $0.023/GB |
| Warm | 30-90 days | Standard-IA | 1-3 hours | $0.0125/GB |
| Cold | 90 days - 7 years | Glacier | 3-12 hours | $0.004/GB |
| Archive | 7+ years | Deep Archive | 12-48 hours | $0.00099/GB |

## Database Retention Policies

### MySQL/PostgreSQL Database Retention

```yaml
production_databases:
  hot_tier:
    duration: "30 days"
    backup_frequency: "Daily at 2 AM"
    storage_location: "S3 Standard"
    access_time: "Immediate"
    
    retention_schedule:
      - daily_backups: 30
      - weekly_backups: 12
      - monthly_backups: 12
      - yearly_backups: 7
    
    archival_criteria:
      - size_threshold: "100GB"
      - access_frequency: "<5% per month"
      - compliance_requirement: "False"
  
  warm_tier:
    duration: "30-365 days"
    storage_location: "S3 Standard-IA"
    access_time: "1-3 hours"
    compression: "Gzip (ratio: 3:1)"
    
    archive_method:
      type: "Automated via lifecycle policy"
      transition_time: "30 days after creation"
    
  cold_tier:
    duration: "1-7 years"
    storage_location: "S3 Glacier"
    access_time: "3-12 hours"
    encryption: "AES-256"
    
    archival_requirements:
      - compliance_review: "Required"
      - business_justification: "Documented"
      - legal_hold: "If applicable"
    
  archive_tier:
    duration: "7+ years (or regulatory minimum)"
    storage_location: "S3 Deep Archive"
    access_time: "12-48 hours"
    
    compliance_requirements:
      - retention_policy: "GDPR/CCPA compliant"
      - audit_trail: "Required"
      - immutable_storage: "Yes"
```

### MongoDB Retention

```yaml
mongodb_databases:
  oplog_retention:
    primary: "24 hours in hot tier"
    secondary: "7 days in warm tier"
    archival: "30 days in cold tier"
    
  data_retention:
    hot_data: "7 days"
    warm_data: "30 days"
    cold_data: "90 days - 2 years"
    archive: "2+ years (case-by-case)"
  
  backup_strategy:
    continuous_backup: "Enabled"
    point_in_time_recovery: "24 hour window"
    snapshot_frequency: "Every 6 hours"
    
  archival_criteria:
    - collection_type: "historical_logs"
      retention: "2 years"
    - collection_type: "user_data"
      retention: "7 years"
    - collection_type: "analytics"
      retention: "5 years"
```

### Redis Cache Retention

```yaml
redis_backups:
  rdb_snapshots:
    frequency: "Daily at 4 AM"
    retention:
      daily: "7 backups"
      weekly: "4 backups"
    
  aof_logs:
    retention: "24 hours"
    rotation: "Every hour"
    
  persistence:
    aof_enabled: true
    rdb_enabled: true
    save_schedule:
      - "900 1"   # 15 minutes if 1+ keys changed
      - "300 10"  # 5 minutes if 10+ keys changed
      - "60 10000" # 1 minute if 10000+ keys changed
```

## Filesystem Retention Policies

### Application Files

```yaml
application_files:
  /var/www/html:
    hot_tier: "30 days"
    warm_tier: "90 days"
    cold_tier: "1 year"
    
    retention_rules:
      - pattern: "*.log"
        retention: "90 days"
        compression: "Gzip after 7 days"
      - pattern: "*.tmp"
        retention: "7 days"
        auto_delete: true
      - pattern: "cache/*"
        retention: "24 hours"
        auto_delete: true
    
  /var/lib/application:
    hot_tier: "30 days"
    warm_tier: "90 days"
    cold_tier: "7 years"
    
    critical_data:
      retention: "7+ years"
      compliance: "Industry-specific"
      encryption: "Required"
```

### User Generated Content

```yaml
user_uploads:
  /var/uploads:
    active_files: "Unlimited"
    deleted_files: "30 days (grace period)"
    compression: "Gzip after 90 days"
    
    storage_tiers:
      0-90 days:
        location: "S3 Standard"
        cost: "$0.023/GB"
        access: "Immediate"
      
      90-365 days:
        location: "S3 Standard-IA"
        cost: "$0.0125/GB"
        access: "1-3 hours"
      
      1-7 years:
        location: "S3 Glacier"
        cost: "$0.004/GB"
        access: "3-12 hours"
      
      7+ years:
        location: "S3 Deep Archive"
        cost: "$0.00099/GB"
        access: "12-48 hours"
    
  metadata_retention:
    user_activity_logs: "2 years"
    access_logs: "1 year"
    deletion_logs: "7 years (compliance)"
```

### System Logs

```yaml
system_logs:
  application_logs:
    hot_tier: "30 days"
    warm_tier: "90 days"
    cold_tier: "1 year"
    
  access_logs:
    hot_tier: "90 days"
    warm_tier: "1 year"
    cold_tier: "7 years"
    
  security_logs:
    hot_tier: "90 days"
    warm_tier: "1 year"
    cold_tier: "7 years"
    
  database_logs:
    hot_tier: "30 days"
    warm_tier: "90 days"
    cold_tier: "1 year"
```

## Container and Image Retention

### Docker Images

```yaml
docker_images:
  production_images:
    retention:
      - "Latest 10 tagged versions"
      - "All images from last 90 days"
      - "Critical images (1+ years)"
    
    registry_policy:
      automatic_cleanup: "Enabled"
      tag_patterns_to_keep:
        - "latest"
        - "release-*"
        - "hotfix-*"
      
      deletion_criteria:
        - "Untagged images after 30 days"
        - "Tagged images older than 90 days (non-critical)"
        - "Failed builds after 7 days"
  
  staging_images:
    retention:
      - "Latest 5 versions"
      - "Images older than 30 days (deleted)"
    
  development_images:
    retention: "7 days"
    auto_cleanup: true
```

## Cloud Storage Retention

### S3 Bucket Lifecycle Policies

```yaml
s3_lifecycle_policies:
  primary_backup_bucket:
    id: "BackupRetentionPolicy"
    filter:
      prefix: "backups/"
    
    transitions:
      - days: 30
        storage_class: "STANDARD_IA"
      - days: 90
        storage_class: "GLACIER"
      - days: 365
        storage_class: "DEEP_ARCHIVE"
    
    expiration:
      - days: 2555  # 7 years
        expired_object_delete_marker: true
    
    abort_incomplete_multipart_uploads:
      - days_after_initiation: 7
  
  user_uploads_bucket:
    id: "UserUploadsRetentionPolicy"
    filter:
      prefix: "user-content/"
    
    transitions:
      - days: 30
        storage_class: "STANDARD_IA"
      - days: 90
        storage_class: "GLACIER"
      - days: 365
        storage_class: "DEEP_ARCHIVE"
    
    expiration:
      - days: 2555  # 7 years
        expired_object_delete_marker: true
  
  logs_bucket:
    id: "LogsRetentionPolicy"
    filter:
      prefix: "application-logs/"
    
    transitions:
      - days: 30
        storage_class: "STANDARD_IA"
      - days: 90
        storage_class: "GLACIER"
    
    expiration:
      - days: 365  # 1 year
```

## Compliance and Legal Retention

### GDPR Compliance

```yaml
gdpr_compliance:
  personal_data:
    retention: "Only as long as necessary for purpose"
    right_to_erasure: "Supported"
    data_portability: "Export available"
    consent_tracking: "7 years"
    
  data_subjects:
    customer_data: "Account closure + 7 years"
    support_tickets: "3 years"
    communications: "2 years"
    analytics: "Anonymized after 90 days"
  
  deletion_procedures:
    automated: "User-initiated deletion triggers"
    manual: "Admin-initiated deletion (audit logged)"
    bulk_deletion: "Scheduled (monthly)"
    
    deletion_confirmation:
      method: "Email notification"
      retention: "30 days (recovery window)"
```

### Financial Records

```yaml
financial_records:
  retention_periods:
    transaction_logs: "7 years"
    invoices: "7 years"
    tax_documents: "7 years"
    audit_logs: "7 years"
    
  archival_method:
    storage: "Encrypted Glacier"
    compression: "High ratio"
    access_controls: "Restricted (CFO approval)"
  
  compliance_requirements:
    - "SOC 2 Type II"
    - "PCI DSS (if applicable)"
    - "SOX compliance"
    - "Regional tax laws"
```

### Healthcare (HIPAA)

```yaml
hipaa_compliance:
  phi_data:
    retention: "6 years minimum"
    encryption: "AES-256 (at rest and in transit)"
    access_logging: "Required"
    minimum_necessary: "Enforced"
    
  medical_records:
    retention: "7 years (adults)"
    retention: "Until age of majority + 7 years (minors)
    
  audit_trails:
    retention: "6 years"
    immutable: "Yes"
    encryption: "Required"
```

## Automated Retention Management

### Lifecycle Policy Automation

```bash
#!/bin/bash
# Automated retention policy management

# S3 Lifecycle Policies
aws s3api put-bucket-lifecycle-configuration \
    --bucket backup-bucket \
    --lifecycle-configuration file://s3-lifecycle-policy.json

# Clean up old local backups
find /opt/backup -type f -mtime +30 -delete

# Archive completed backups
./scripts/archive_backups.sh \
    --source /opt/backup \
    --destination s3://archive-bucket/ \
    --retention-policy daily

# Compliance check
./scripts/compliance_check.py \
    --check-retention \
    --report-format json
```

### Database-Specific Retention

```sql
-- PostgreSQL: Auto-cleanup old WAL files
-- This runs daily via cron
SELECT pg_archivecleanup('/var/lib/pg_wal/', 
  (SELECT MAX(name) FROM pg_ls_waldir()));

-- MySQL: Purge old binary logs
-- Retain only last 7 days
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 7 DAY);

-- MongoDB: TTL index for automatic document expiration
db.logs.createIndex(
    { "createdAt": 1 },
    { expireAfterSeconds: 2592000 }  // 30 days
)
```

## Backup Retention Matrix

| Data Type | Hot (0-30d) | Warm (30-365d) | Cold (1-7y) | Archive (7+y) | Legal Min | Storage Cost/Year |
|-----------|-------------|----------------|-------------|---------------|-----------|-------------------|
| Database (Prod) | Daily | Weekly | Monthly | Yearly | 7y | $1.20/GB |
| Database (Dev) | Daily | Weekly | - | - | - | $0.84/GB |
| User Uploads | All | All | All | All | - | $0.96/GB |
| Application Files | Daily | Weekly | Monthly | Yearly | 7y | $1.08/GB |
| Logs (App) | Daily | Weekly | - | - | - | $0.60/GB |
| Logs (Access) | Daily | Weekly | Monthly | - | 1y | $0.72/GB |
| Logs (Security) | Daily | Weekly | Monthly | Yearly | 7y | $1.20/GB |
| Container Images | Weekly | Monthly | - | - | - | $0.48/GB |
| Analytics Data | Daily | Weekly | Monthly | Yearly | 5y | $0.96/GB |
| Backups | Daily | Weekly | Monthly | Yearly | 7y | $1.20/GB |

## Cost Optimization Strategies

### Storage Tiering

1. **Automatic Transitions**
   - 0-30 days: Standard storage (frequent access)
   - 30-90 days: Standard-IA (occasional access)
   - 90-365 days: Glacier (rare access)
   - 1+ years: Deep Archive (compliance/archival)

2. **Manual Review**
   - Quarterly review of retention policies
   - Annual cost optimization analysis
   - Compliance requirement updates

### Compression and Deduplication

```yaml
compression_strategies:
  database_backups:
    method: "Gzip"
    ratio: "3:1"
    cpu_cost: "Low"
    
  log_files:
    method: "Gzip (after 7 days)"
    ratio: "10:1"
    retention_before_compression: "7 days"
    
  file_uploads:
    method: "Automatic (based on type)"
    images: "WebP (if compatible)"
    documents: "PDF (if applicable)"
  
  deduplication:
    enabled: true
    method: "Block-level"
    savings: "20-40% for similar files"
```

## Archival Procedures

### Monthly Archival Process

```bash
#!/bin/bash
# Monthly archival process

# 1. Identify data for archival
./scripts/identify_archival_candidates.sh \
    --criteria "last_access > 90 days" \
    --output archival_candidates.json

# 2. Create archival package
./scripts/create_archival_package.sh \
    --source archival_candidates.json \
    --destination /tmp/monthly_archive \
    --encrypt true

# 3. Upload to archival storage
aws s3 cp /tmp/monthly_archive \
    s3://archive-bucket/$(date +%Y)/$(date +%m)/ \
    --storage-class DEEP_ARCHIVE

# 4. Update retention database
./scripts/update_retention_db.sh \
    --archive-path s3://archive-bucket/$(date +%Y)/$(date +%m)/ \
    --retention-date "$(date -d '+7 years' +%Y-%m-%d)"

# 5. Send confirmation
./scripts/notify_archival_complete.sh \
    --archive-path s3://archive-bucket/$(date +%Y)/$(date +%m)/ \
    --data-size $(du -sh /tmp/monthly_archive | cut -f1)
```

### Quarterly Review Process

1. **Compliance Audit**
   - Review all retention policies
   - Verify legal requirement compliance
   - Update policies as needed

2. **Cost Analysis**
   - Calculate storage costs
   - Identify optimization opportunities
   - Plan for growth

3. **Data Classification Review**
   - Reclassify data based on access patterns
   - Adjust retention policies
   - Update automation rules

## Emergency Data Recovery

### Urgent Restore Procedures

```yaml
urgent_restore:
  tier_1_emergency:  # Critical system failure
    response_time: "15 minutes"
    data_age: "<24 hours"
    restoration_location: "Primary DR site"
    
  tier_2_urgent:    # Important system failure
    response_time: "4 hours"
    data_age: "<7 days"
    restoration_location: "Secondary region"
    
  tier_3_scheduled: # Routine restoration
    response_time: "24 hours"
    data_age: "<30 days"
    restoration_location: "As requested"
```

### Data Recovery SLA

| Priority | Response Time | Data Age | Cost |
|----------|---------------|----------|------|
| P0 (Critical) | 15 min | <24h | Included |
| P1 (High) | 4 hours | <7d | $100/hour |
| P2 (Medium) | 24 hours | <30d | $200/hour |
| P3 (Low) | 72 hours | <90d | $500/hour |

## Monitoring and Alerts

### Retention Compliance Monitoring

```bash
#!/bin/bash
# Daily retention compliance check

# Check for data exceeding retention period
./scripts/check_retention_violations.sh \
    --output violations.json \
    --send-alerts true

# Verify archival completeness
./scripts/verify_archival.sh \
    --period last_month \
    --report-missing true

# Generate retention report
./scripts/generate_retention_report.sh \
    --period monthly \
    --format json \
    --output /var/log/backup/retention_report.json
```

### Key Metrics to Monitor

1. **Storage Utilization**
   - Current usage vs capacity
   - Growth rate
   - Tier distribution

2. **Retention Compliance**
   - Data exceeding retention periods
   - Legal hold violations
   - Deletion failures

3. **Cost Metrics**
   - Cost per GB by tier
   - Monthly storage costs
   - Archival savings

4. **Operational Metrics**
   - Backup completion rates
   - Restoration success rates
   - Archive retrieval times

## Policy Enforcement

### Automated Enforcement

```python
# retention_enforcer.py
import boto3
import json
from datetime import datetime, timedelta

class RetentionEnforcer:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.dynamodb = boto3.resource('dynamodb')
        
    def enforce_retention_policies(self):
        """Enforce all retention policies"""
        
        # Enforce S3 lifecycle policies
        self.enforce_s3_lifecycle()
        
        # Clean up expired backups
        self.cleanup_expired_backups()
        
        # Archive old data
        self.archive_old_data()
        
        # Update retention tracking
        self.update_retention_tracking()
    
    def enforce_s3_lifecycle(self):
        """Apply S3 lifecycle policies"""
        buckets = ['backup-bucket', 'user-uploads', 'logs-bucket']
        
        for bucket in buckets:
            try:
                self.s3.put_bucket_lifecycle_configuration(
                    Bucket=bucket,
                    LifecycleConfiguration=self.get_lifecycle_config(bucket)
                )
            except Exception as e:
                logger.error(f"Failed to update lifecycle for {bucket}: {e}")
```

### Manual Review Process

```yaml
manual_review_schedule:
  weekly:
    - "Review high-priority violations"
    - "Check critical system backups"
    
  monthly:
    - "Full retention compliance review"
    - "Cost analysis and optimization"
    - "Update lifecycle policies"
    
  quarterly:
    - "Compliance audit"
    - "Legal requirement review"
    - "Policy updates"
    
  annually:
    - "Comprehensive policy review"
    - "Multi-year cost projection"
    - "Technology assessment"
```

## Contact and Escalation

### Retention Policy Questions
- **Data Governance Team**: data-governance@company.com
- **Legal Compliance**: compliance@company.com
- **Technical Issues**: backup-team@company.com

### Emergency Retention Issues
- **On-call Engineer**: +1-XXX-XXX-XXXX
- **Data Protection Officer**: dpo@company.com
- **Incident Response**: incident@company.com