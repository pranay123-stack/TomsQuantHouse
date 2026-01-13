# Disaster Recovery Procedures

## Overview

This document outlines comprehensive disaster recovery procedures for the entire system infrastructure. These procedures ensure rapid recovery and business continuity in the event of system failures, data center outages, or other disaster scenarios.

## Recovery Objectives

### Recovery Time Objectives (RTO)
- **Critical Systems**: 4 hours
- **Important Systems**: 24 hours
- **Standard Systems**: 72 hours

### Recovery Point Objectives (RPO)
- **Transactional Databases**: 15 minutes
- **Application Databases**: 1 hour
- **File Systems**: 24 hours
- **Archives**: 7 days

## Disaster Recovery Levels

### Level 1: Minor Failure
**Definition**: Component failure with minimal impact (single server, minor service interruption)

**Response Time**: 15 minutes
**Recovery Strategy**: Automated failover, service restart

### Level 2: Major Component Failure
**Definition**: Multi-component failure, data center subnet issues

**Response Time**: 1 hour
**Recovery Strategy**: Cross-region failover, load balancer redirection

### Level 3: Complete Data Center Outage
**Definition**: Entire data center unavailable, region-wide issues

**Response Time**: 4 hours
**Recovery Strategy**: Full disaster recovery to secondary region

### Level 4: Regional Disaster
**Definition**: Entire primary region unavailable (natural disaster, massive outage)

**Response Time**: 8 hours
**Recovery Strategy**: Complete DR activation, all services in secondary regions

## Automated Failover Procedures

### 1. Database Failover

#### Automated RDS Failover
```bash
#!/bin/bash
# Automated RDS Multi-AZ failover

# Parameters
DB_INSTANCE_ID=$1
TARGET_REGION=$2
SNAPSHOT_PREFIX="dr-failover"

# Create database snapshot
echo "Creating database snapshot..."
aws rds create-db-snapshot \
    --db-instance-identifier $DB_INSTANCE_ID \
    --db-snapshot-identifier "${SNAPSHOT_PREFIX}-$(date +%Y%m%d-%H%M%S)"

# Wait for snapshot completion (monitor via CloudWatch or polling)
# Then restore in target region

# Promote read replica if available
if [ -n "$READ_REPLICA_ID" ]; then
    echo "Promoting read replica to primary..."
    aws rds promote-read-replica \
        --db-instance-identifier $READ_REPLICA_ID
fi

# Update application configuration
# Switch DNS records
# Update connection strings
```

#### PostgreSQL Point-in-Time Recovery
```bash
#!/bin/bash
# PostgreSQL PITR DR procedure

TIMESTAMP=$1  # ISO 8601 format
TARGET_DATA_DIR=$2

# Stop PostgreSQL service
systemctl stop postgresql

# Restore base backup
echo "Restoring base backup..."
pg_restore -D $TARGET_DATA_DIR /path/to/base_backup.tar

# Create recovery configuration
cat > $TARGET_DATA_DIR/recovery.conf << EOF
restore_command = 'cp /archive/%f %p'
recovery_target_time = '$TIMESTAMP'
recovery_target_action = 'promote'
log_directory = '/var/log/postgresql'
EOF

# Start PostgreSQL in recovery mode
systemctl start postgresql

# Monitor recovery process
tail -f /var/log/postgresql/postgresql.log | grep "recovery complete"
```

#### MySQL Master-Slave Failover
```bash
#!/bin/bash
# MySQL master-slave promotion

# Stop writes to master
mysql -e "SET GLOBAL read_only = ON;"

# Get binary log position
BINLOG_FILE=$(mysql -e "SHOW MASTER STATUS\G" | grep File | awk '{print $2}')
BINLOG_POS=$(mysql -e "SHOW MASTER STATUS\G" | grep Position | awk '{print $2}')

# Promote slave to master
mysql -e "STOP SLAVE; RESET SLAVE ALL;"

# Enable writes
mysql -e "SET GLOBAL read_only = OFF;"

# Update application connection strings
# Update load balancer configuration
```

### 2. Application Failover

#### Kubernetes Multi-Region Deployment
```yaml
# kubernetes/dr-deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dr-config
data:
  DR_REGION: "us-west-2"
  FAILOVER_MODE: "automatic"
---
apiVersion: v1
kind: Service
metadata:
  name: app-service-dr
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  type: LoadBalancer
  selector:
    app: application
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-dr-deployment
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: application
      tier: dr
  template:
    metadata:
      labels:
        app: application
        tier: dr
    spec:
      containers:
      - name: application
        image: application:latest
        env:
        - name: DR_REGION
          valueFrom:
            configMapKeyRef:
              name: dr-config
              key: DR_REGION
```

#### Auto-Scaling Group DR
```bash
#!/bin/bash
# AWS Auto Scaling Group DR

ASG_NAME="app-asg-us-west-2"
LAUNCH_TEMPLATE="app-launch-template-v2"
MIN_SIZE=3
MAX_SIZE=10
DESIRED_CAPACITY=5

# Update launch template
aws autoscaling update-auto-scaling-group \
    --auto-scaling-group-name $ASG_NAME \
    --launch-template LaunchTemplateName=$LAUNCH_TEMPLATE,Version=Latest \
    --min-size $MIN_SIZE \
    --max-size $MAX_SIZE \
    --desired-capacity $DESIRED_CAPACITY

# Update target group attachments
aws elbv2 register-targets \
    --target-group-arn arn:aws:elasticloadbalancing:us-west-2:123456789012:targetgroup/app-tg/50dc6c495c0c9188 \
    --targets Id=i-0123456789abcdef0,Port=8080,AvailabilityZone=us-west-2a

# Scale to required capacity
aws autoscaling set-desired-capacity \
    --auto-scaling-group-name $ASG_NAME \
    --desired-capacity $DESIRED_CAPACITY
```

### 3. Storage Failover

#### S3 Cross-Region Replication
```bash
#!/bin/bash
# S3 bucket failover

SOURCE_BUCKET="production-data-us-east-1"
TARGET_BUCKET="production-data-us-west-2"
REPLICATION_CONFIG="replication-config.json"

# Apply replication configuration
aws s3api put-bucket-replication \
    --bucket $TARGET_BUCKET \
    --replication-configuration file://$REPLICATION_CONFIG

# Sync critical objects
aws s3 sync s3://$SOURCE_BUCKET s3://$TARGET_BUCKET \
    --storage-class STANDARD_IA \
    --exclude "*" \
    --include "critical/*"

# Update application configuration
# Point to secondary bucket
```

#### EBS Volume Failover
```bash
#!/bin/bash
# EBS volume snapshot and restore

VOLUME_ID=$1
TARGET_AZ=$2
SNAPSHOT_PREFIX="dr-snapshot"

# Create snapshot
echo "Creating snapshot..."
SNAPSHOT_ID=$(aws ec2 create-snapshot \
    --volume-id $VOLUME_ID \
    --description "DR snapshot $(date)" \
    --query 'SnapshotId' --output text)

# Wait for snapshot to complete
aws ec2 wait snapshot-completed --snapshot-ids $SNAPSHOT_ID

# Create volume in target AZ
NEW_VOLUME_ID=$(aws ec2 create-volume \
    --snapshot-id $SNAPSHOT_ID \
    --availability-zone $TARGET_AZ \
    --query 'VolumeId' --output text)

# Attach to instance
aws ec2 attach-volume \
    --volume-id $NEW_VOLUME_ID \
    --instance-id i-0123456789abcdef0 \
    --device /dev/sdf
```

### 4. Network Failover

#### Route 53 DNS Failover
```bash
#!/bin/bash
# DNS failover procedure

HOSTED_ZONE_ID="Z123456789"
RECORD_NAME="app.example.com"
PRIMARY_REGION="us-east-1"
SECONDARY_REGION="us-west-2"

# Update health check
aws route53 change-resource-record-sets \
    --hosted-zone-id $HOSTED_ZONE_ID \
    --change-batch file://route53-failover.json

# Monitor DNS propagation
sleep 30
dig $RECORD_NAME
```

#### CloudFront Distribution Failover
```bash
#!/bin/bash
# CloudFront distribution failover

DISTRIBUTION_ID="E123456789ABC"
SECONDARY_ORIGIN="secondary-origin.example.com"

# Update distribution configuration
aws cloudfront update-distribution \
    --id $DISTRIBUTION_ID \
    --distribution-config file://distribution-config.json \
    --if-match $ETAG

# Invalidate all cached content
aws cloudfront create-invalidation \
    --distribution-id $DISTRIBUTION_ID \
    --paths "/*"
```

## Manual Disaster Recovery Procedures

### Step 1: Disaster Assessment

1. **Initial Assessment**
   ```bash
   # Check system status
   ./scripts/dr/health_check.sh
   
   # Determine disaster level
   # Check service availability
   # Assess data loss
   ```

2. **Impact Analysis**
   - List affected services
   - Estimate downtime
   - Calculate data loss (RPO violation)
   - Document timeline

3. **Communication**
   - Notify stakeholders
   - Activate incident response team
   - Update status page
   - Send customer communications

### Step 2: Recovery Planning

1. **Select Recovery Strategy**
   - Determine if automated failover should be used
   - Choose target recovery region
   - Identify required resources

2. **Resource Preparation**
   ```bash
   # Provision infrastructure in target region
   ./scripts/dr/provision_resources.sh --target-region us-west-2
   
   # Validate resource availability
   ./scripts/dr/validate_resources.sh
   ```

3. **Backup Validation**
   ```bash
   # Verify backup integrity
   ./scripts/backup_encryption.py batch-check --directory /opt/backup
   
   # Test restore process
   ./scripts/dr/test_restore.sh --backup-type database
   ```

### Step 3: Execution

1. **Database Recovery**
   ```bash
   # PostgreSQL recovery
   ./scripts/pitr_system.py restore \
       --db-type postgresql \
       --target-time 2023-12-01T10:30:00 \
       --destination /var/lib/postgresql/data
   
   # MySQL recovery
   mysql < /opt/backup/mysql/full_backup.sql
   ```

2. **Application Deployment**
   ```bash
   # Deploy application in target region
   kubectl apply -f kubernetes/dr-deployment.yaml
   
   # Update configuration
   kubectl set env deployment/app-dr-deployment DR_REGION=us-west-2
   ```

3. **Data Synchronization**
   ```bash
   # Sync remaining data
   ./scripts/cross_region_replication.py replicate \
       --backup-type s3
   
   # Validate data consistency
   ./scripts/dr/validate_data_consistency.sh
   ```

### Step 4: Validation and Testing

1. **Service Health Check**
   ```bash
   # Run comprehensive health checks
   ./scripts/dr/comprehensive_health_check.sh
   
   # Test critical user paths
   ./tests/dr/user_path_tests.sh
   ```

2. **Performance Testing**
   ```bash
   # Load testing
   ./tests/dr/performance_test.sh
   
   # Verify SLA compliance
   ./tests/dr/sla_validation.sh
   ```

3. **Failback Planning**
   - Document lessons learned
   - Update procedures
   - Plan failback if needed

## Communication Templates

### Internal Communication
```
Subject: [DR ACTIVATED] Service Outage - Primary Region

Team,

A disaster recovery event has been activated at [TIMESTAMP].

DISASTER LEVEL: Level X
AFFECTED REGION: us-east-1
TARGET RECOVERY REGION: us-west-2
ESTIMATED RECOVERY TIME: [X hours]

CURRENT ACTIONS:
- [Action 1]
- [Action 2]
- [Action 3]

STATUS PAGE: https://status.example.com
INCIDENT: https://pagerduty.com/incidents/123456

Updates will follow.
DR Team
```

### Customer Communication
```
Subject: Service Status Update - Temporary Service Disruption

Hello,

We are currently experiencing a temporary service disruption affecting [SERVICES] 
in the [REGION] region. We have activated our disaster recovery procedures and 
are working to restore full service.

IMPACT: [IMPACT_DESCRIPTION]
STATUS: [STATUS]
ESTIMATED RECOVERY: [ESTIMATED_TIME]

We will continue to provide updates every [FREQUENCY] until full service is restored.

You can track our progress at: https://status.example.com

We apologize for any inconvenience.

[COMPANY_NAME] Support Team
```

## Post-Recovery Procedures

### 1. Failback Process
When primary region is restored, plan an organized failback:

1. **Data Synchronization**
   - Sync changes from DR region to primary
   - Verify data consistency

2. **Service Migration**
   - Gradually migrate traffic back
   - Monitor for issues

3. **Final Cutover**
   - Switch DNS records
   - Update load balancers
   - Decommission DR resources

### 2. Lessons Learned
- Conduct post-incident review
- Update documentation
- Test updated procedures
- Improve monitoring

### 3. Audit and Documentation
- Document all actions taken
- Update DR runbooks
- Revise procedures based on learnings
- Update recovery time estimates

## Testing Schedule

### Monthly Tests
- Automated failover validation
- Backup integrity verification
- Recovery procedure documentation review

### Quarterly Tests
- Full disaster recovery simulation
- Cross-region data consistency check
- Performance testing during recovery

### Annual Tests
- Complete DR environment testing
- Third-party validation
- Regulatory compliance check
- Business continuity assessment

## Monitoring and Alerting

### Key Metrics to Monitor
- Replication lag across regions
- Backup completion status
- Recovery time actuals vs targets
- Data consistency checks

### Alerting Thresholds
- Replication lag > 5 minutes: WARNING
- Backup failure: CRITICAL
- RTO exceeded: CRITICAL
- Data corruption detected: CRITICAL

## Contact Information

### Emergency Contacts
- DR Team Lead: +1-XXX-XXX-XXXX
- Infrastructure Team: +1-XXX-XXX-XXXX
- On-Call Engineer: +1-XXX-XXX-XXXX

### Escalation Matrix
- Level 1: On-call engineer
- Level 2: Team lead
- Level 3: VP Engineering
- Level 4: CTO

## References

- [Backup Configuration](../config/backup_config.yaml)
- [Automation Scripts](../automation/)
- [Testing Procedures](../tests/)
- [Monitoring Setup](../monitoring/)