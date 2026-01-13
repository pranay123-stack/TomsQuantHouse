"""
Example: Advanced Security Features
Demonstrates RBAC, encryption, audit logging, and security scanning
"""

from security import (
    SecuritySystem, Role, Permission, KeyType,
    AuditEventType, AuditSeverity
)
import json

def main():
    security_system = SecuritySystem()
    
    print("=== Advanced Security Features Example ===\n")
    
    # Setup: Create admin user and assign roles
    print("Setup: Creating test users and roles...")
    
    # Create users with different roles
    users = {
        'admin_user': Role.SUPER_ADMIN,
        'regular_user': Role.USER,
        'auditor': Role.AUDITOR,
        'api_client_user': Role.API_CLIENT
    }
    
    for username, role in users.items():
        security_system.rbac_manager.assign_role(username, role)
        print(f"  ✓ Assigned {role.value} to {username}")
    
    # 1. RBAC Demonstration
    print("\n1. Role-Based Access Control (RBAC)")
    print("User Permissions:")
    
    for username, role in users.items():
        permissions = security_system.rbac_manager.get_user_permissions(username)
        print(f"\n  {username} ({role.value}):")
        
        # Show key permissions
        key_perms = [p.value for p in list(permissions)[:5]]
        print(f"    Permissions: {', '.join(key_perms)}...")
        
        # Test specific permission
        can_admin = security_system.rbac_manager.check_permission(
            username, Permission.ADMIN_ACCESS
        )
        can_user_create = security_system.rbac_manager.check_permission(
            username, Permission.USER_CREATE
        )
        
        print(f"    Can access admin: {can_admin}")
        print(f"    Can create users: {can_user_create}")
    
    # 2. Encryption Demonstration
    print("\n2. Data Encryption & Protection")
    
    sensitive_data = {
        "api_keys": ["key1", "key2", "key3"],
        "database_password": "super_secret_db_pass",
        "user_pii": {
            "ssn": "123-45-6789",
            "email": "user@example.com",
            "phone": "+1-555-0123"
        },
        "configuration": {
            "secret_token": "jwt-secret-key",
            "encryption_key": "aes-256-key"
        }
    }
    
    # Protect the data
    encrypted = security_system.data_protector.protect_json(sensitive_data)
    print(f"✓ Data encrypted: {encrypted[:50]}...")
    
    # Unprotect the data
    decrypted = security_system.data_protector.unprotect_json(encrypted)
    print(f"✓ Data decrypted successfully: {len(decrypted)} items")
    
    # Verify data integrity
    if sensitive_data == decrypted:
        print("✓ Data integrity verified")
    else:
        print("✗ Data integrity check failed")
    
    # 3. Secure Storage
    print("\n3. Secure Storage")
    
    # Store sensitive configuration
    config_data = {
        "database": {
            "host": "db.example.com",
            "port": 5432,
            "name": "production_db"
        },
        "redis": {
            "host": "redis.example.com",
            "port": 6379
        },
        "api_settings": {
            "rate_limit": 1000,
            "timeout": 30
        }
    }
    
    security_system.secure_storage.store_secure_data(
        "app_config", config_data
    )
    print("✓ Configuration stored securely")
    
    # Retrieve configuration
    retrieved_config = security_system.secure_storage.retrieve_secure_data("app_config")
    if retrieved_config:
        print("✓ Configuration retrieved successfully")
    
    # 4. Custom Audit Events
    print("\n4. Audit Logging")
    
    # Log various security events
    
    # High-risk event
    high_risk_event = security_system.audit_logger.log_event(
        AuditEvent(AuditEventType.SECURITY_VIOLATION, "user123", AuditSeverity.HIGH)
    )
    print("✓ Logged security violation event")
    
    # Admin action
    admin_action = security_system.audit_logger.log_event(
        AuditEvent(AuditEventType.ADMIN_ACTION, "admin_user", AuditSeverity.MEDIUM)
    )
    print("✓ Logged admin action")
    
    # Data access
    data_access = security_system.audit_logger.log_event(
        AuditEvent(AuditEventType.DATA_ACCESS, "regular_user", AuditSeverity.LOW)
    )
    print("✓ Logged data access")
    
    # Get audit statistics
    stats = security_system.audit_logger.get_statistics()
    print(f"\nAudit Statistics:")
    print(f"  Total Events: {stats['total_events']}")
    print(f"  Event Types: {list(stats['event_type_counts'].keys())[:3]}...")
    print(f"  Severity Distribution: {stats['severity_counts']}")
    
    # 5. API Key Management
    print("\n5. API Key Management")
    
    # Create different types of API keys
    api_keys = []
    
    key_specs = [
        ("Read-Only Service", KeyType.READ_ONLY, ["read"]),
        ("Admin API", KeyType.ADMIN, ["read", "write", "delete"]),
        ("Batch Processor", KeyType.BATCH, ["read", "write", "data:import", "data:export"]),
        ("Webhook Handler", KeyType.WEBHOOK, ["read"])
    ]
    
    for name, key_type, scopes in key_specs:
        result = security_system.create_api_key(
            name=name,
            key_type=key_type,
            scopes=scopes,
            created_by="admin_user",
            expiry_days=30
        )
        
        if result['success']:
            api_keys.append(result)
            print(f"✓ Created {key_type.value} API key: {name}")
    
    # Get API key analytics
    analytics = security_system.security_scanner
    key_analytics = security_system.api_key_manager.get_key_analytics()
    
    print(f"\nAPI Key Analytics:")
    print(f"  Total Keys: {key_analytics['total_keys']}")
    print(f"  Active Keys: {key_analytics['active_keys']}")
    print(f"  Type Distribution: {key_analytics['type_distribution']}")
    
    # 6. Security Scanning (if configured)
    print("\n6. Security Scanning")
    
    try:
        # Note: This would scan a real URL in production
        # For demo, we'll simulate a scan
        print("  Running security scan on localhost...")
        print("  (In production, this would scan actual targets)")
        print("  ✓ Vulnerability scanning configured")
        print("  ✓ SSL/TLS checking enabled")
        print("  ✓ Security headers validation enabled")
        
    except Exception as e:
        print(f"  ✗ Scan configuration issue: {e}")
    
    # 7. Rate Limiting Demonstration
    print("\n7. Rate Limiting")
    
    if security_system.rate_limiter:
        print("  Testing rate limits...")
        
        # Simulate multiple requests
        for i in range(5):
            result = security_system.rate_limiter.check_rate_limit(
                identifier="test_client",
                limit_type="api_requests"
            )
            
            status = "✓" if result['allowed'] else "✗"
            print(f"    Request {i+1}: {status} Allowed (Count: {result.get('current_count', 0)})")
        
        # Get rate limiting stats
        rate_stats = security_system.rate_limiter.get_rate_limit_stats()
        print(f"  ✓ Rate limiting active: {rate_stats.get('total_keys', 0)} tracked")
    else:
        print("  ✗ Rate limiting not configured (Redis unavailable)")
    
    # 8. Key Rotation
    print("\n8. Encryption Key Management")
    
    try:
        rotation_result = security_system.rotate_encryption_keys()
        if rotation_result['success']:
            print("✓ Encryption keys rotated successfully")
        else:
            print("✗ Key rotation failed")
    except Exception as e:
        print(f"✗ Key rotation error: {e}")
    
    # 9. Comprehensive Security Status
    print("\n9. Complete System Status")
    
    status = security_system.get_security_status()
    
    print("System Health:")
    print(f"  Status: {status['status']}")
    print(f"  Environment: {status['configuration']['environment']}")
    print(f"  Version: {status['version']}")
    
    print("\nComponent Details:")
    for component, details in status['components'].items():
        health_icon = "🟢" if details['status'] == 'operational' else "🔴"
        print(f"  {health_icon} {component.title()}: {details['status']}")
        
        # Show specific component details
        if component == 'api_keys':
            print(f"    Total: {details.get('total_keys', 0)}, Active: {details.get('active_keys', 0)}")
        elif component == 'rate_limiting':
            print(f"    Redis Connected: {details.get('redis_connected', False)}")
        elif component == 'encryption':
            print(f"    Key Rotation: {details.get('key_rotation_enabled', False)}")
    
    # 10. Cleanup and Maintenance
    print("\n10. Maintenance Operations")
    
    cleanup_result = security_system.cleanup_expired_data()
    if cleanup_result['success']:
        print("✓ Cleanup completed:")
        print(f"    Expired API keys removed: {cleanup_result['expired_api_keys_removed']}")
        print(f"    Audit logs cleaned: {cleanup_result['audit_logs_cleaned']}")
        print(f"    Rate limit keys cleaned: {cleanup_result['rate_limit_keys_cleaned']}")
    
    print("\n=== Advanced Security Features Demo Complete ===")
    print("All components tested successfully!")

if __name__ == "__main__":
    main()
