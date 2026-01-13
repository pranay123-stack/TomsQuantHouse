"""
Audit Logging System
Comprehensive logging for all security events and API operations
"""

import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import sqlite3
import threading
from pathlib import Path
import gzip
import os


class AuditEventType(Enum):
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    
    # Authorization events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    
    # API key events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_KEY_ROTATED = "api_key_rotated"
    API_KEY_USED = "api_key_used"
    
    # Data access events
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    DATA_DELETE = "data_delete"
    
    # Security events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"
    
    # Admin events
    ADMIN_ACTION = "admin_action"
    CONFIG_CHANGE = "config_change"
    
    # System events
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_THRESHOLD = "performance_threshold"


class AuditSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditContext:
    """Context information for audit events"""
    
    def __init__(self):
        self.timestamp = datetime.now(timezone.utc)
        self.ip_address = None
        self.user_agent = None
        self.session_id = None
        self.request_id = None
        self.api_key = None
        self.rate_limit_info = {}
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'request_id': self.request_id,
            'api_key': self.api_key,
            'rate_limit_info': self.rate_limit_info
        }


class AuditEvent:
    """Audit event data model"""
    
    def __init__(self, event_type: AuditEventType, user_id: str = None,
                 severity: AuditSeverity = AuditSeverity.MEDIUM):
        self.event_id = self._generate_event_id()
        self.event_type = event_type
        self.user_id = user_id
        self.severity = severity
        self.timestamp = datetime.now(timezone.utc)
        self.context = AuditContext()
        self.details = {}
        self.result = "success"
        self.error_message = None
        self.risk_score = 0
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.now(timezone.utc).timestamp()
        random_data = os.urandom(16)
        return hashlib.sha256(f"{timestamp}{random_data.hex()}".encode()).hexdigest()[:16]
    
    def add_context(self, **kwargs):
        """Add context information"""
        for key, value in kwargs.items():
            setattr(self.context, key, value)
    
    def add_details(self, **kwargs):
        """Add event details"""
        self.details.update(kwargs)
    
    def set_result(self, success: bool, error: str = None):
        """Set event result"""
        self.result = "success" if success else "failure"
        if not success and error:
            self.error_message = error
    
    def calculate_risk_score(self):
        """Calculate risk score based on event characteristics"""
        score = 0
        
        # Base score from severity
        severity_scores = {
            AuditSeverity.LOW: 10,
            AuditSeverity.MEDIUM: 25,
            AuditSeverity.HIGH: 50,
            AuditSeverity.CRITICAL: 100
        }
        score += severity_scores[self.severity]
        
        # Add points for failure events
        if self.result == "failure":
            score += 25
        
        # Add points for specific event types
        high_risk_events = [
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.PERMISSION_DENIED,
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.RATE_LIMIT_EXCEEDED
        ]
        
        if self.event_type in high_risk_events:
            score += 30
        
        self.risk_score = min(score, 100)  # Cap at 100
        return self.risk_score
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'user_id': self.user_id,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context.to_dict(),
            'details': self.details,
            'result': self.result,
            'error_message': self.error_message,
            'risk_score': self.risk_score
        }


class AuditLogger:
    """Main audit logging system"""
    
    def __init__(self, db_path: str = "audit_logs.db", 
                 retention_days: int = 90,
                 enable_compression: bool = True):
        self.db_path = db_path
        self.retention_days = retention_days
        self.enable_compression = enable_compression
        
        # Threading lock for database writes
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Configure file logging
        self._setup_file_logging()
        
        # Start background cleanup
        self._start_cleanup_job()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    session_id TEXT,
                    request_id TEXT,
                    api_key_hash TEXT,
                    details TEXT,
                    result TEXT NOT NULL,
                    error_message TEXT,
                    risk_score INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for performance
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON audit_events(timestamp)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_id 
                ON audit_events(user_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_event_type 
                ON audit_events(event_type)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_risk_score 
                ON audit_events(risk_score)
            ''')
    
    def _setup_file_logging(self):
        """Setup file logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure audit logger
        audit_logger = logging.getLogger('audit')
        audit_logger.setLevel(logging.INFO)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_dir / "audit.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        
        # JSON formatter
        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        audit_logger.addHandler(file_handler)
        
        # Console handler for critical events
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        audit_logger.addHandler(console_handler)
        
        self.audit_logger = audit_logger
    
    def log_event(self, event: AuditEvent):
        """Log audit event"""
        # Calculate risk score
        event.calculate_risk_score()
        
        # Store in database
        self._store_in_database(event)
        
        # Log to file
        self._log_to_file(event)
        
        # Check for alerts
        self._check_alerts(event)
    
    def _store_in_database(self, event: AuditEvent):
        """Store event in database"""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_events (
                        event_id, event_type, user_id, severity, timestamp,
                        ip_address, user_agent, session_id, request_id,
                        api_key_hash, details, result, error_message, risk_score
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_id,
                    event.event_type.value,
                    event.user_id,
                    event.severity.value,
                    event.timestamp.isoformat(),
                    event.context.ip_address,
                    event.context.user_agent,
                    event.context.session_id,
                    event.context.request_id,
                    hashlib.sha256(event.context.api_key.encode()).hexdigest() 
                        if event.context.api_key else None,
                    json.dumps(event.details),
                    event.result,
                    event.error_message,
                    event.risk_score
                ))
    
    def _log_to_file(self, event: AuditEvent):
        """Log event to file"""
        # Log to audit logger
        self.audit_logger.info(json.dumps(event.to_dict()))
        
        # For critical events, also log to separate file
        if event.severity == AuditSeverity.CRITICAL:
            critical_logger = logging.getLogger('audit.critical')
            critical_logger.error(json.dumps(event.to_dict()))
    
    def _check_alerts(self, event: AuditEvent):
        """Check if event should trigger alerts"""
        alert_conditions = []
        
        # High risk score
        if event.risk_score >= 75:
            alert_conditions.append("high_risk_score")
        
        # Multiple failures
        if event.event_type == AuditEventType.LOGIN_FAILURE:
            # Check for brute force attempt
            recent_failures = self.get_events(
                event_type=AuditEventType.LOGIN_FAILURE,
                user_id=event.user_id,
                minutes_back=5
            )
            if len(recent_failures) >= 3:
                alert_conditions.append("brute_force_attempt")
        
        # Security violations
        if event.event_type in [
            AuditEventType.SECURITY_VIOLATION,
            AuditEventType.SUSPICIOUS_ACTIVITY
        ]:
            alert_conditions.append("security_violation")
        
        # Write alert to separate file
        if alert_conditions:
            self._write_alert(event, alert_conditions)
    
    def _write_alert(self, event: AuditEvent, conditions: List[str]):
        """Write security alert"""
        alert_dir = Path("alerts")
        alert_dir.mkdir(exist_ok=True)
        
        alert_file = alert_dir / f"alert_{event.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        
        alert_data = {
            'alert_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type.value,
            'user_id': event.user_id,
            'severity': event.severity.value,
            'conditions': conditions,
            'risk_score': event.risk_score,
            'event_data': event.to_dict()
        }
        
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
    
    def get_events(self, user_id: str = None, event_type: AuditEventType = None,
                   start_date: datetime = None, end_date: datetime = None,
                   severity: AuditSeverity = None, risk_score_min: int = None,
                   limit: int = 100, offset: int = 0, minutes_back: int = None) -> List[Dict[str, Any]]:
        """Query audit events"""
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity.value)
        
        if risk_score_min:
            query += " AND risk_score >= ?"
            params.append(risk_score_min)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        if minutes_back:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes_back)
            query += " AND timestamp >= ?"
            params.append(cutoff.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            events = []
            for row in cursor:
                event_dict = dict(row)
                event_dict['details'] = json.loads(event_dict['details']) if event_dict['details'] else {}
                events.append(event_dict)
            
            return events
    
    def get_statistics(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get audit statistics"""
        where_clause = ""
        params = []
        
        if start_date and end_date:
            where_clause = "WHERE timestamp BETWEEN ? AND ?"
            params = [start_date.isoformat(), end_date.isoformat()]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Event type counts
            cursor = conn.execute(f'''
                SELECT event_type, COUNT(*) as count
                FROM audit_events {where_clause}
                GROUP BY event_type
            ''', params)
            event_counts = dict(cursor.fetchall())
            
            # Severity counts
            cursor = conn.execute(f'''
                SELECT severity, COUNT(*) as count
                FROM audit_events {where_clause}
                GROUP BY severity
            ''', params)
            severity_counts = dict(cursor.fetchall())
            
            # Top users by event count
            cursor = conn.execute(f'''
                SELECT user_id, COUNT(*) as count
                FROM audit_events {where_clause}
                WHERE user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY count DESC
                LIMIT 10
            ''', params)
            top_users = dict(cursor.fetchall())
            
            # High risk events
            cursor = conn.execute(f'''
                SELECT COUNT(*) as count
                FROM audit_events {where_clause}
                WHERE risk_score >= 75
            ''', params)
            high_risk_count = cursor.fetchone()['count']
            
            return {
                'event_type_counts': event_counts,
                'severity_counts': severity_counts,
                'top_users': top_users,
                'high_risk_events': high_risk_count,
                'total_events': sum(event_counts.values()) if event_counts else 0
            }
    
    def cleanup_old_logs(self) -> int:
        """Clean up old audit logs"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM audit_events 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            
            # Vacuum database
            conn.execute('VACUUM')
            
            return deleted_count
    
    def export_events(self, format: str = "json", output_file: str = None) -> str:
        """Export audit events"""
        events = self.get_events(limit=10000)  # Limit export size
        
        if format.lower() == "json":
            output = json.dumps(events, indent=2)
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(output)
                return output_file
            return output
        
        elif format.lower() == "csv":
            import csv
            
            if not output_file:
                output_file = f"audit_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(output_file, 'w', newline='') as f:
                if events:
                    writer = csv.DictWriter(f, fieldnames=events[0].keys())
                    writer.writeheader()
                    writer.writerows(events)
            
            return output_file
        
        raise ValueError(f"Unsupported export format: {format}")
    
    def _start_cleanup_job(self):
        """Start background cleanup job"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(86400)  # Run daily
                    self.cleanup_old_logs()
                except Exception as e:
                    logging.error(f"Audit cleanup job error: {e}")
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()


# Convenience functions for logging
def log_login_success(user_id: str, ip_address: str = None, user_agent: str = None):
    """Log successful login"""
    event = AuditEvent(AuditEventType.LOGIN_SUCCESS, user_id, AuditSeverity.LOW)
    event.add_context(ip_address=ip_address, user_agent=user_agent)
    audit_logger = get_audit_logger()
    audit_logger.log_event(event)


def log_login_failure(user_id: str, ip_address: str = None, error: str = None):
    """Log failed login"""
    event = AuditEvent(AuditEventType.LOGIN_FAILURE, user_id, AuditSeverity.MEDIUM)
    event.add_context(ip_address=ip_address)
    event.set_result(False, error)
    audit_logger = get_audit_logger()
    audit_logger.log_event(event)


def log_api_key_usage(api_key_hash: str, endpoint: str, method: str, 
                     success: bool, user_id: str = None):
    """Log API key usage"""
    event = AuditEvent(AuditEventType.API_KEY_USED, user_id, AuditSeverity.LOW)
    event.add_context(api_key=api_key_hash)
    event.add_details(endpoint=endpoint, method=method)
    event.set_result(success)
    audit_logger = get_audit_logger()
    audit_logger.log_event(event)


def log_permission_denied(user_id: str, permission: str, resource: str):
    """Log permission denial"""
    event = AuditEvent(AuditEventType.PERMISSION_DENIED, user_id, AuditSeverity.HIGH)
    event.add_details(permission=permission, resource=resource)
    audit_logger = get_audit_logger()
    audit_logger.log_event(event)


# Global audit logger instance
_audit_logger_instance = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = AuditLogger()
    return _audit_logger_instance


# Example usage
if __name__ == "__main__":
    # Initialize audit logger
    audit_logger = AuditLogger()
    
    # Log various events
    log_login_success("user123", "192.168.1.1", "Mozilla/5.0...")
    log_login_failure("user456", "10.0.0.1", "Invalid credentials")
    log_permission_denied("user789", "user:delete", "users")
    
    # Get statistics
    stats = audit_logger.get_statistics()
    print(f"Audit Statistics: {stats}")
    
    # Query events
    events = audit_logger.get_events(
        event_type=AuditEventType.LOGIN_SUCCESS,
        limit=10
    )
    print(f"Login success events: {len(events)}")
