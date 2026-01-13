#!/usr/bin/env python3
"""
Configuration Change Tracking and Audit Logging
Provides comprehensive change tracking, audit logging, and compliance monitoring
"""

import os
import json
import yaml
import sqlite3
import hashlib
import logging
import difflib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import subprocess
import threading
import time
from contextlib import contextmanager

class ChangeType(Enum):
    """Types of configuration changes"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MOVE = "move"
    RENAME = "rename"
    RESTORE = "restore"
    BACKUP = "backup"

class ChangeSeverity(Enum):
    """Change severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ChangeStatus(Enum):
    """Change tracking status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"

@dataclass
class ChangeRecord:
    """Record of a configuration change"""
    id: str
    timestamp: str
    change_type: ChangeType
    file_path: str
    old_value: Optional[str]
    new_value: Optional[str]
    user_id: str
    user_name: str
    environment: str
    description: str
    severity: ChangeSeverity
    status: ChangeStatus = ChangeStatus.PENDING
    approval_required: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    rollback_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    diff: Optional[str] = None
    checksum_before: Optional[str] = None
    checksum_after: Optional[str] = None

@dataclass
class AuditEvent:
    """Audit event record"""
    id: str
    timestamp: str
    event_type: str
    user_id: str
    user_name: str
    action: str
    resource: str
    details: Dict[str, Any]
    result: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    id: str
    name: str
    description: str
    rule_type: str
    severity: ChangeSeverity
    condition: str
    action: str
    enabled: bool = True
    last_checked: Optional[str] = None

class ConfigurationChangeTracker:
    """Configuration change tracking system"""
    
    def __init__(self, base_dir: str = "environment/audit",
                 audit_db: str = "audit_log.db"):
        self.base_dir = Path(base_dir)
        self.audit_db = Path(audit_db)
        self.changes_dir = self.base_dir / "changes"
        self.reports_dir = self.base_dir / "reports"
        
        # Create directories
        self.changes_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_audit_db()
        
        # Load configuration watch list
        self.watched_files = self._load_watched_files()
        
        # Initialize file watchers
        self.file_monitors = {}
        self.monitoring_active = False
        
        self.logger = logging.getLogger('change_tracker')
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_dir / 'change_audit.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_audit_db(self):
        """Initialize audit database"""
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS change_records (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                change_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                environment TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                approval_required BOOLEAN NOT NULL,
                approved_by TEXT,
                approved_at TEXT,
                rollback_data TEXT,
                metadata TEXT,
                diff TEXT,
                checksum_before TEXT,
                checksum_after TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                details TEXT NOT NULL,
                result TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_rules (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                condition TEXT NOT NULL,
                action TEXT NOT NULL,
                enabled BOOLEAN NOT NULL,
                last_checked TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compliance_violations (
                id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                change_id TEXT,
                violation_description TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                resolved_by TEXT,
                resolved_at TEXT,
                FOREIGN KEY (rule_id) REFERENCES compliance_rules (id),
                FOREIGN KEY (change_id) REFERENCES change_records (id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON change_records (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_user ON change_records (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_changes_environment ON change_records (environment)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events (timestamp)')
        
        conn.commit()
        conn.close()
    
    def _load_watched_files(self) -> List[str]:
        """Load list of files to watch for changes"""
        watched_patterns = [
            "config/*.yaml",
            "config/*.json",
            "config/*.yml",
            ".env.*",
            "environment/config/*.yaml",
            "environment/config/*.json",
            "secrets/*",
            "*.conf",
            "*.cfg",
            "*.ini"
        ]
        
        watched_files = []
        for pattern in watched_patterns:
            if '*' in pattern:
                # Handle glob patterns
                import glob
                matching_files = glob.glob(pattern, recursive=True)
                watched_files.extend(matching_files)
            else:
                # Handle exact file paths
                if os.path.exists(pattern):
                    watched_files.append(pattern)
        
        return list(set(watched_files))  # Remove duplicates
    
    def start_monitoring(self, interval: float = 5.0):
        """Start file monitoring for changes"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.logger.info("Starting file monitoring")
        
        # Store initial file checksums
        file_checksums = {}
        for file_path in self.watched_files:
            if os.path.exists(file_path):
                file_checksums[file_path] = self._calculate_file_checksum(file_path)
        
        def monitor_files():
            while self.monitoring_active:
                try:
                    current_checksums = {}
                    for file_path in self.watched_files:
                        if os.path.exists(file_path):
                            current_checksums[file_path] = self._calculate_file_checksum(file_path)
                    
                    # Compare checksums and detect changes
                    for file_path, current_checksum in current_checksums.items():
                        old_checksum = file_checksums.get(file_path)
                        
                        if old_checksum is None:
                            # New file created
                            self._record_change(
                                change_type=ChangeType.CREATE,
                                file_path=file_path,
                                user_id="system",
                                user_name="System Monitor",
                                environment="unknown",
                                description=f"New file created: {file_path}",
                                severity=ChangeSeverity.LOW
                            )
                        
                        elif old_checksum != current_checksum:
                            # File modified
                            old_content = self._read_file_safely(file_path, old_checksum)
                            new_content = self._read_file_safely(file_path, current_checksum)
                            
                            self._record_change(
                                change_type=ChangeType.UPDATE,
                                file_path=file_path,
                                old_value=old_content,
                                new_value=new_content,
                                user_id="system",
                                user_name="System Monitor",
                                environment="unknown",
                                description=f"File modified: {file_path}",
                                severity=ChangeSeverity.MEDIUM
                            )
                    
                    # Check for deleted files
                    for file_path in list(file_checksums.keys()):
                        if file_path not in current_checksums:
                            self._record_change(
                                change_type=ChangeType.DELETE,
                                file_path=file_path,
                                user_id="system",
                                user_name="System Monitor",
                                environment="unknown",
                                description=f"File deleted: {file_path}",
                                severity=ChangeSeverity.HIGH
                            )
                    
                    # Update checksums
                    file_checksums.update(current_checksums)
                    
                    # Remove deleted files from checksums
                    file_checksums = {k: v for k, v in file_checksums.items() if k in current_checksums}
                    
                    # Sleep before next check
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in file monitoring: {e}")
                    time.sleep(interval)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_files, daemon=True)
        monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop file monitoring"""
        self.monitoring_active = False
        self.logger.info("Stopped file monitoring")
    
    def record_manual_change(self, file_path: str, change_type: ChangeType,
                           user_id: str, user_name: str, environment: str,
                           description: str, severity: ChangeSeverity = ChangeSeverity.MEDIUM,
                           old_value: Optional[str] = None, new_value: Optional[str] = None) -> str:
        """Record a manual configuration change"""
        
        change_id = self._record_change(
            change_type=change_type,
            file_path=file_path,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            user_name=user_name,
            environment=environment,
            description=description,
            severity=severity
        )
        
        return change_id
    
    def _record_change(self, change_type: ChangeType, file_path: str,
                      user_id: str, user_name: str, environment: str,
                      description: str, severity: ChangeSeverity,
                      old_value: Optional[str] = None,
                      new_value: Optional[str] = None) -> str:
        """Record a change to the database"""
        
        change_id = f"change_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Calculate checksums
        checksum_before = None
        checksum_after = None
        
        if old_value:
            checksum_before = hashlib.sha256(old_value.encode()).hexdigest()
        if new_value:
            checksum_after = hashlib.sha256(new_value.encode()).hexdigest()
        
        # Generate diff
        diff = None
        if old_value and new_value:
            diff = self._generate_diff(old_value, new_value)
        
        # Determine if approval is required
        approval_required = severity in [ChangeSeverity.CRITICAL, ChangeSeverity.HIGH]
        
        change_record = ChangeRecord(
            id=change_id,
            timestamp=datetime.now().isoformat(),
            change_type=change_type,
            file_path=file_path,
            old_value=old_value,
            new_value=new_value,
            user_id=user_id,
            user_name=user_name,
            environment=environment,
            description=description,
            severity=severity,
            status=ChangeStatus.PENDING if approval_required else ChangeStatus.APPLIED,
            approval_required=approval_required,
            diff=diff,
            checksum_before=checksum_before,
            checksum_after=checksum_after
        )
        
        # Save to database
        self._save_change_record(change_record)
        
        # Log the change
        self.logger.info(f"Change recorded: {change_id} - {description}")
        
        # Check compliance rules
        self._check_compliance_rules(change_record)
        
        return change_id
    
    def _save_change_record(self, record: ChangeRecord):
        """Save change record to database"""
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO change_records (
                id, timestamp, change_type, file_path, old_value, new_value,
                user_id, user_name, environment, description, severity, status,
                approval_required, approved_by, approved_at, rollback_data,
                metadata, diff, checksum_before, checksum_after
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.id, record.timestamp, record.change_type.value, record.file_path,
            record.old_value, record.new_value, record.user_id, record.user_name,
            record.environment, record.description, record.severity.value, record.status.value,
            record.approval_required, record.approved_by, record.approved_at,
            json.dumps(record.rollback_data) if record.rollback_data else None,
            json.dumps(record.metadata), record.diff, record.checksum_before, record.checksum_after
        ))
        
        conn.commit()
        conn.close()
    
    def approve_change(self, change_id: str, approver_id: str,
                      approver_name: str, comment: str = "") -> bool:
        """Approve a pending change"""
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE change_records SET status = ?, approved_by = ?, approved_at = ? WHERE id = ?",
            (ChangeStatus.APPROVED.value, approver_id, datetime.now().isoformat(), change_id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return False
        
        conn.commit()
        conn.close()
        
        # Record audit event
        self.record_audit_event(
            event_type="change_approval",
            user_id=approver_id,
            user_name=approver_name,
            action="approve_change",
            resource=change_id,
            details={"comment": comment},
            result="success"
        )
        
        self.logger.info(f"Change approved: {change_id} by {approver_name}")
        return True
    
    def reject_change(self, change_id: str, approver_id: str,
                     approver_name: str, reason: str) -> bool:
        """Reject a pending change"""
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE change_records SET status = ? WHERE id = ?",
            (ChangeStatus.REJECTED.value, change_id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return False
        
        conn.commit()
        conn.close()
        
        # Record audit event
        self.record_audit_event(
            event_type="change_rejection",
            user_id=approver_id,
            user_name=approver_name,
            action="reject_change",
            resource=change_id,
            details={"reason": reason},
            result="success"
        )
        
        self.logger.info(f"Change rejected: {change_id} by {approver_name}")
        return True
    
    def rollback_change(self, change_id: str, user_id: str,
                       user_name: str) -> bool:
        """Rollback a change"""
        
        # Get change record
        change_record = self.get_change_record(change_id)
        if not change_record:
            return False
        
        if change_record.change_type not in [ChangeType.UPDATE, ChangeType.DELETE]:
            return False
        
        # For now, just mark as rolled back (actual rollback would require more logic)
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE change_records SET status = ? WHERE id = ?",
            (ChangeStatus.ROLLED_BACK.value, change_id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            return False
        
        conn.commit()
        conn.close()
        
        # Record audit event
        self.record_audit_event(
            event_type="change_rollback",
            user_id=user_id,
            user_name=user_name,
            action="rollback_change",
            resource=change_id,
            details={},
            result="success"
        )
        
        self.logger.info(f"Change rolled back: {change_id} by {user_name}")
        return True
    
    def get_change_record(self, change_id: str) -> Optional[ChangeRecord]:
        """Get a specific change record"""
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM change_records WHERE id = ?", (change_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return ChangeRecord(
            id=row[0],
            timestamp=row[1],
            change_type=ChangeType(row[2]),
            file_path=row[3],
            old_value=row[4],
            new_value=row[5],
            user_id=row[6],
            user_name=row[7],
            environment=row[8],
            description=row[9],
            severity=ChangeSeverity(row[10]),
            status=ChangeStatus(row[11]),
            approval_required=bool(row[12]),
            approved_by=row[13],
            approved_at=row[14],
            rollback_data=json.loads(row[15]) if row[15] else None,
            metadata=json.loads(row[16]) if row[16] else {},
            diff=row[17],
            checksum_before=row[18],
            checksum_after=row[19]
        )
    
    def list_changes(self, environment: Optional[str] = None,
                    user_id: Optional[str] = None,
                    limit: int = 100) -> List[ChangeRecord]:
        """List change records with optional filtering"""
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        query = "SELECT * FROM change_records"
        params = []
        
        if environment or user_id:
            query += " WHERE"
            conditions = []
            
            if environment:
                conditions.append("environment = ?")
                params.append(environment)
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            query += " " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        changes = []
        for row in rows:
            change = ChangeRecord(
                id=row[0],
                timestamp=row[1],
                change_type=ChangeType(row[2]),
                file_path=row[3],
                old_value=row[4],
                new_value=row[5],
                user_id=row[6],
                user_name=row[7],
                environment=row[8],
                description=row[9],
                severity=ChangeSeverity(row[10]),
                status=ChangeStatus(row[11]),
                approval_required=bool(row[12]),
                approved_by=row[13],
                approved_at=row[14],
                rollback_data=json.loads(row[15]) if row[15] else None,
                metadata=json.loads(row[16]) if row[16] else {},
                diff=row[17],
                checksum_before=row[18],
                checksum_after=row[19]
            )
            changes.append(change)
        
        return changes
    
    def record_audit_event(self, event_type: str, user_id: str, user_name: str,
                          action: str, resource: str, details: Dict[str, Any],
                          result: str, ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None,
                          session_id: Optional[str] = None):
        """Record an audit event"""
        
        event_id = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        audit_event = AuditEvent(
            id=event_id,
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            user_id=user_id,
            user_name=user_name,
            action=action,
            resource=resource,
            details=details,
            result=result,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        
        # Save to database
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO audit_events (
                id, timestamp, event_type, user_id, user_name, action, resource,
                details, result, ip_address, user_agent, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            audit_event.id, audit_event.timestamp, audit_event.event_type,
            audit_event.user_id, audit_event.user_name, audit_event.action,
            audit_event.resource, json.dumps(audit_event.details),
            audit_event.result, audit_event.ip_address, audit_event.user_agent,
            audit_event.session_id
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Audit event recorded: {event_id} - {action}")
    
    def list_audit_events(self, user_id: Optional[str] = None,
                         event_type: Optional[str] = None,
                         limit: int = 100) -> List[AuditEvent]:
        """List audit events with optional filtering"""
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        query = "SELECT * FROM audit_events"
        params = []
        
        if user_id or event_type:
            query += " WHERE"
            conditions = []
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            if event_type:
                conditions.append("event_type = ?")
                params.append(event_type)
            
            query += " " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        events = []
        for row in rows:
            event = AuditEvent(
                id=row[0],
                timestamp=row[1],
                event_type=row[2],
                user_id=row[3],
                user_name=row[4],
                action=row[5],
                resource=row[6],
                details=json.loads(row[7]),
                result=row[8],
                ip_address=row[9],
                user_agent=row[10],
                session_id=row[11]
            )
            events.append(event)
        
        return events
    
    def _check_compliance_rules(self, change_record: ChangeRecord):
        """Check change against compliance rules"""
        
        # This would implement actual compliance rule checking
        # For now, we'll create some example rules
        
        example_rules = [
            {
                "id": "rule_001",
                "name": "Critical files require approval",
                "condition": f"change_record.severity == 'critical' and change_record.approval_required == False",
                "action": "reject_change"
            },
            {
                "id": "rule_002",
                "name": "Production changes require description",
                "condition": f"change_record.environment == 'production' and len(change_record.description) < 10",
                "action": "require_approval"
            },
            {
                "id": "rule_003",
                "name": "Secret files changes must be logged",
                "condition": "'secret' in change_record.file_path.lower()",
                "action": "log_security_event"
            }
        ]
        
        for rule in example_rules:
            try:
                # Simple rule evaluation (in production, use proper expression evaluator)
                if "critical" in rule["condition"] and change_record.severity == ChangeSeverity.CRITICAL:
                    self._record_compliance_violation(rule["id"], change_record, 
                                                    f"Rule violation: {rule['name']}")
                
                elif "production" in rule["condition"] and change_record.environment == "production":
                    if len(change_record.description) < 10:
                        self._record_compliance_violation(rule["id"], change_record,
                                                        f"Rule violation: {rule['name']}")
                
                elif "secret" in rule["condition"] and "secret" in change_record.file_path.lower():
                    # Log security event
                    self.record_audit_event(
                        event_type="security_event",
                        user_id=change_record.user_id,
                        user_name=change_record.user_name,
                        action="secret_file_changed",
                        resource=change_record.file_path,
                        details={"change_id": change_record.id, "rule": rule["name"]},
                        result="logged"
                    )
            except Exception as e:
                self.logger.error(f"Error checking compliance rule {rule['id']}: {e}")
    
    def _record_compliance_violation(self, rule_id: str, change_record: ChangeRecord,
                                   description: str):
        """Record a compliance rule violation"""
        
        violation_id = f"violation_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO compliance_violations (
                id, rule_id, timestamp, change_id, violation_description,
                severity, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            violation_id, rule_id, datetime.now().isoformat(), change_record.id,
            description, change_record.severity.value, "open"
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.warning(f"Compliance violation recorded: {violation_id}")
    
    def generate_change_report(self, start_date: str, end_date: str,
                             environment: Optional[str] = None) -> Dict[str, Any]:
        """Generate change tracking report"""
        
        conn = sqlite3.connect(self.audit_db)
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT change_type, severity, status, COUNT(*) as count
            FROM change_records
            WHERE timestamp BETWEEN ? AND ?
        """
        params = [start_date, end_date]
        
        if environment:
            query += " AND environment = ?"
            params.append(environment)
        
        query += " GROUP BY change_type, severity, status"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get audit events summary
        audit_query = """
            SELECT event_type, COUNT(*) as count
            FROM audit_events
            WHERE timestamp BETWEEN ? AND ?
        """
        audit_params = [start_date, end_date]
        
        if environment:
            audit_query += " AND user_id IN (SELECT user_id FROM change_records WHERE environment = ?)"
            audit_params.append(environment)
        
        cursor.execute(audit_query, audit_params)
        audit_rows = cursor.fetchall()
        
        conn.close()
        
        # Process results
        change_stats = {}
        for row in rows:
            change_type, severity, status, count = row
            key = f"{change_type}_{severity}_{status}"
            change_stats[key] = count
        
        audit_stats = {row[0]: row[1] for row in audit_rows}
        
        return {
            "report_period": {"start": start_date, "end": end_date},
            "environment": environment or "all",
            "change_statistics": change_stats,
            "audit_statistics": audit_stats,
            "generated_at": datetime.now().isoformat()
        }
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def _read_file_safely(self, file_path: str, checksum: str) -> Optional[str]:
        """Read file content safely"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            # Verify checksum
            current_checksum = hashlib.sha256(content.encode()).hexdigest()
            if current_checksum == checksum:
                return content
            else:
                return None
        except Exception:
            return None
    
    def _generate_diff(self, old_content: str, new_content: str) -> str:
        """Generate unified diff between two contents"""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile="old_content", tofile="new_content",
            lineterm=""
        )
        
        return '\n'.join(diff)

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuration Change Tracking")
    subparsers = parser.add_subparsers(dest='command')
    
    # Start monitoring command
    monitor_parser = subparsers.add_parser('monitor', help='Start file monitoring')
    monitor_parser.add_argument('--interval', type=float, default=5.0, help='Monitoring interval in seconds')
    
    # Record change command
    change_parser = subparsers.add_parser('change', help='Record configuration change')
    change_subparsers = change_parser.add_subparsers(dest='change_command')
    
    record_change = change_subparsers.add_parser('record', help='Record a change')
    record_change.add_argument('file_path', help='File path that changed')
    record_change.add_argument('change_type', choices=[t.value for t in ChangeType], help='Type of change')
    record_change.add_argument('user_id', help='User ID making the change')
    record_change.add_argument('user_name', help='User name')
    record_change.add_argument('environment', help='Environment')
    record_change.add_argument('description', help='Change description')
    record_change.add_argument('--severity', choices=[s.value for s in ChangeSeverity], 
                              default=ChangeSeverity.MEDIUM.value, help='Change severity')
    record_change.add_argument('--old-value', help='Old value (for updates)')
    record_change.add_argument('--new-value', help='New value (for updates)')
    
    # List changes command
    list_changes = subparsers.add_parser('list-changes', help='List changes')
    list_changes.add_argument('--env', help='Filter by environment')
    list_changes.add_argument('--user', help='Filter by user')
    list_changes.add_argument('--limit', type=int, default=100, help='Limit number of results')
    
    # Approve/reject commands
    approve_parser = subparsers.add_parser('approve', help='Approve change')
    approve_parser.add_argument('change_id', help='Change ID to approve')
    approve_parser.add_argument('approver_id', help='Approver user ID')
    approve_parser.add_argument('approver_name', help='Approver user name')
    approve_parser.add_argument('--comment', default='', help='Approval comment')
    
    reject_parser = subparsers.add_parser('reject', help='Reject change')
    reject_parser.add_argument('change_id', help='Change ID to reject')
    reject_parser.add_argument('approver_id', help='Approver user ID')
    reject_parser.add_argument('approver_name', help='Approver user name')
    reject_parser.add_argument('reason', help='Rejection reason')
    
    # Audit commands
    audit_parser = subparsers.add_parser('audit', help='Audit events')
    audit_subparsers = audit_parser.add_subparsers(dest='audit_command')
    
    list_audit = audit_subparsers.add_parser('list', help='List audit events')
    list_audit.add_argument('--user', help='Filter by user')
    list_audit.add_argument('--type', help='Filter by event type')
    list_audit.add_argument('--limit', type=int, default=100, help='Limit number of results')
    
    record_audit = audit_subparsers.add_parser('record', help='Record audit event')
    record_audit.add_argument('event_type', help='Event type')
    record_audit.add_argument('user_id', help='User ID')
    record_audit.add_argument('user_name', help='User name')
    record_audit.add_argument('action', help='Action performed')
    record_audit.add_argument('resource', help='Resource affected')
    record_audit.add_argument('details', help='Event details (JSON)')
    record_audit.add_argument('result', help='Result of action')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    report_parser.add_argument('end_date', help='End date (YYYY-MM-DD)')
    report_parser.add_argument('--env', help='Filter by environment')
    report_parser.add_argument('--output', help='Output file for report')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tracker = ConfigurationChangeTracker()
    
    if args.command == 'monitor':
        print(f"Starting file monitoring (interval: {args.interval}s)")
        tracker.start_monitoring(args.interval)
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitoring...")
            tracker.stop_monitoring()
    
    elif args.command == 'change':
        if args.change_command == 'record':
            change_type = ChangeType(args.change_type)
            severity = ChangeSeverity(args.severity)
            
            change_id = tracker.record_manual_change(
                file_path=args.file_path,
                change_type=change_type,
                user_id=args.user_id,
                user_name=args.user_name,
                environment=args.environment,
                description=args.description,
                severity=severity,
                old_value=args.old_value,
                new_value=args.new_value
            )
            
            print(f"Change recorded: {change_id}")
    
    elif args.command == 'list-changes':
        changes = tracker.list_changes(
            environment=args.env,
            user_id=args.user,
            limit=args.limit
        )
        
        print(f"Found {len(changes)} changes:")
        for change in changes:
            print(f"{change.timestamp} - {change.change_type.value} - {change.file_path} - "
                  f"{change.user_name} - {change.status.value}")
    
    elif args.command == 'approve':
        success = tracker.approve_change(
            change_id=args.change_id,
            approver_id=args.approver_id,
            approver_name=args.approver_name,
            comment=args.comment
        )
        print(f"Change approved: {success}")
    
    elif args.command == 'reject':
        success = tracker.reject_change(
            change_id=args.change_id,
            approver_id=args.approver_id,
            approver_name=args.approver_name,
            reason=args.reason
        )
        print(f"Change rejected: {success}")
    
    elif args.command == 'audit':
        if args.audit_command == 'list':
            events = tracker.list_audit_events(
                user_id=args.user,
                event_type=args.type,
                limit=args.limit
            )
            
            print(f"Found {len(events)} audit events:")
            for event in events:
                print(f"{event.timestamp} - {event.event_type} - {event.action} - "
                      f"{event.user_name} - {event.result}")
        
        elif args.audit_command == 'record':
            details = json.loads(args.details)
            
            tracker.record_audit_event(
                event_type=args.event_type,
                user_id=args.user_id,
                user_name=args.user_name,
                action=args.action,
                resource=args.resource,
                details=details,
                result=args.result
            )
            
            print("Audit event recorded")
    
    elif args.command == 'report':
        start_datetime = f"{args.start_date} 00:00:00"
        end_datetime = f"{args.end_date} 23:59:59"
        
        report = tracker.generate_change_report(start_datetime, end_datetime, args.env)
        
        print("Change Tracking Report")
        print("=" * 50)
        print(f"Period: {args.start_date} to {args.end_date}")
        print(f"Environment: {args.env or 'all'}")
        print()
        
        print("Change Statistics:")
        for key, count in report['change_statistics'].items():
            print(f"  {key}: {count}")
        
        print("\nAudit Statistics:")
        for key, count in report['audit_statistics'].items():
            print(f"  {key}: {count}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {args.output}")

if __name__ == "__main__":
    main()