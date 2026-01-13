#!/usr/bin/env python3
"""
Security System Test Suite
Comprehensive tests for all security components
"""

import sys
import os
import traceback
from datetime import datetime

# Add the parent directory to the path to import the security module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from security import (
    SecuritySystem, JWTManager, RBACManager, APIKeyManager,
    AuditLogger, KeyManager, SecurityMiddleware, SecurityScanner,
    Role, Permission, KeyType, AuditEventType, AuditSeverity
)


class SecuritySystemTest:
    """Test suite for security system"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.security_system = None
    
    def test(self, name, test_func):
        """Run a single test"""
        try:
            print(f"Testing {name}...", end=" ")
            test_func()
            print("✓ PASS")
            self.passed += 1
        except Exception as e:
            print(f"✗ FAIL: {e}")
            self.failed += 1
            self.errors.append((name, str(e), traceback.format_exc()))
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 60)
        print("SECURITY SYSTEM COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Initialize security system
        try:
            self.security_system = SecuritySystem()
            print("✓ Security system initialized")
        except Exception as e:
            print(f"✗ Failed to initialize security system: {e}")
            return False
        
        # Test JWT Authentication
        self.test("JWT Token Generation", self.test_jwt_generation)
        self.test("JWT Token Validation", self.test_jwt_validation)
        self.test("Token Refresh", self.test_token_refresh)
        
        # Test Password Management
        self.test("Password Hashing", self.test_password_hashing)
        self.test("Password Verification", self.test_password_verification)
        self.test("Password Strength Validation", self.test_password_strength)
        
        # Test RBAC
        self.test("Role Assignment", self.test_role_assignment)
        self.test("Permission Checking", self.test_permission_checking)
        self.test("Resource Access Control", self.test_resource_access)
        
        # Test API Key Management
        self.test("API Key Creation", self.test_api_key_creation)
        self.test("API Key Validation", self.test_api_key_validation)
        self.test("API Key Management", self.test_api_key_management)
        
        # Test Rate Limiting (if Redis is available)
        self.test("Rate Limiting", self.test_rate_limiting)
        
        # Test Audit Logging
        self.test("Audit Event Logging", self.test_audit_logging)
        self.test("Audit Event Query", self.test_audit_query)
        self.test("Audit Statistics", self.test_audit_statistics)
        
        # Test Encryption
        self.test("Data Encryption", self.test_data_encryption)
        self.test("Data Decryption", self.test_data_decryption)
        self.test("Key Derivation", self.test_key_derivation)
        
        # Test Security Middleware
        self.test("Input Validation", self.test_input_validation)
        self.test("Security Headers", self.test_security_headers)
        self.test("XSS Protection", self.test_xss_protection)
        
        # Test Integration
        self.test("User Authentication Flow", self.test_authentication_flow)
        self.test("Request Processing", self.test_request_processing)
        self.test("Security Analytics", self.test_security_analytics)
        
        # Print summary
        print()
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        if self.errors:
            print()
            print("FAILED TESTS:")
            for name, error, _ in self.errors:
                print(f"  - {name}: {error}")
        
        print()
        print("=" * 60)
        
        return self.failed == 0
    
    # Test Methods
    
    def test_jwt_generation(self):
        """Test JWT token generation"""
        jwt_manager = JWTManager()
        token = jwt_manager.generate_token(
            user_id="test_user",
            role="admin",
            token_type="access",
            permissions=["read", "write"]
        )
        assert token is not None
        assert len(token) > 50
    
    def test_jwt_validation(self):
        """Test JWT token validation"""
        jwt_manager = JWTManager()
        token = jwt_manager.generate_token("test_user", "admin", "access")
        payload = jwt_manager.validate_token(token)
        assert payload is not None
        assert payload['sub'] == "test_user"
    
    def test_token_refresh(self):
        """Test token refresh"""
        jwt_manager = JWTManager()
        refresh_token = jwt_manager.generate_token("test_user", "admin", "refresh")
        new_access = jwt_manager.refresh_token(refresh_token)
        assert new_access is not None
    
    def test_password_hashing(self):
        """Test password hashing"""
        password_manager = PasswordManager()
        hashed = password_manager.hash_password("test_password_123!")
        assert hashed is not None
        assert len(hashed) > 50
    
    def test_password_verification(self):
        """Test password verification"""
        password_manager = PasswordManager()
        password = "SecurePass123!"
        hashed = password_manager.hash_password(password)
        assert password_manager.verify_password(password, hashed)
        assert not password_manager.verify_password("wrong_password", hashed)
    
    def test_password_strength(self):
        """Test password strength validation"""
        password_manager = PasswordManager()
        
        # Weak password
        weak_result = password_manager.validate_password_strength("123")
        assert not weak_result['valid']
        
        # Strong password
        strong_result = password_manager.validate_password_strength("StrongPass123!")
        assert strong_result['valid']
    
    def test_role_assignment(self):
        """Test role assignment"""
        rbac = RBACManager()
        rbac.assign_role("test_user", Role.ADMIN)
        role = rbac.get_user_role("test_user")
        assert role == Role.ADMIN
    
    def test_permission_checking(self):
        """Test permission checking"""
        rbac = RBACManager()
        rbac.assign_role("test_user", Role.ADMIN)
        
        can_admin = rbac.check_permission("test_user", Permission.ADMIN_ACCESS)
        assert can_admin
        
        can_super = rbac.check_permission("test_user", Permission.USER_DELETE)
        assert can_super  # Admin has all permissions
    
    def test_resource_access(self):
        """Test resource access control"""
        rbac = RBACManager()
        rbac.assign_role("test_user", Role.ADMIN)
        
        can_access = rbac.check_resource_access("test_user", Resource.USERS, Permission.USER_CREATE)
        assert can_access
    
    def test_api_key_creation(self):
        """Test API key creation"""
        api_manager = APIKeyManager()
        key = api_manager.create_api_key(
            name="Test Key",
            key_type=KeyType.STANDARD,
            scopes=["read", "write"],
            created_by="admin"
        )
        assert key is not None
        assert len(key) > 50
    
    def test_api_key_validation(self):
        """Test API key validation"""
        api_manager = APIKeyManager()
        key = api_manager.create_api_key(
            name="Test Key",
            key_type=KeyType.STANDARD,
            scopes=["read"],
            created_by="admin"
        )
        
        validated = api_manager.validate_api_key(key)
        assert validated is not None
        assert validated.name == "Test Key"
    
    def test_api_key_management(self):
        """Test API key management operations"""
        api_manager = APIKeyManager()
        key = api_manager.create_api_key(
            name="Test Key",
            key_type=KeyType.STANDARD,
            scopes=["read"],
            created_by="admin"
        )
        
        key_id = list(api_manager.api_keys.keys())[0]
        
        # Update key
        success = api_manager.update_api_key(key_id, name="Updated Key")
        assert success
        
        # Get usage stats
        stats = api_manager.get_usage_statistics(key_id)
        assert stats is not None
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        if not self.security_system.rate_limiter:
            print("  (Skipping - Redis not available)")
            return
        
        rate_limiter = self.security_system.rate_limiter
        result = rate_limiter.check_rate_limit("test_client", limit_type="api_requests")
        
        assert result is not None
        assert 'allowed' in result
    
    def test_audit_logging(self):
        """Test audit logging"""
        audit_logger = AuditLogger()
        
        event = AuditEvent(AuditEventType.LOGIN_SUCCESS, "test_user")
        audit_logger.log_event(event)
        
        # Verify event was logged
        events = audit_logger.get_events(limit=1)
        assert len(events) > 0
    
    def test_audit_query(self):
        """Test audit event querying"""
        audit_logger = AuditLogger()
        
        # Log an event
        event = AuditEvent(AuditEventType.DATA_ACCESS, "test_user")
        audit_logger.log_event(event)
        
        # Query by event type
        events = audit_logger.get_events(
            event_type=AuditEventType.DATA_ACCESS,
            limit=10
        )
        assert len(events) > 0
    
    def test_audit_statistics(self):
        """Test audit statistics"""
        audit_logger = AuditLogger()
        
        # Log multiple events
        for i in range(5):
            event = AuditEvent(AuditEventType.DATA_ACCESS, f"user{i}")
            audit_logger.log_event(event)
        
        stats = audit_logger.get_statistics()
        assert stats is not None
        assert stats['total_events'] >= 5
    
    def test_data_encryption(self):
        """Test data encryption"""
        key_manager = KeyManager()
        data_protector = DataProtector(key_manager)
        
        data = "sensitive information"
        encrypted = data_protector.protect_data(data, "symmetric")
        
        assert encrypted is not None
        assert encrypted != data
    
    def test_data_decryption(self):
        """Test data decryption"""
        key_manager = KeyManager()
        data_protector = DataProtector(key_manager)
        
        data = "sensitive information"
        encrypted = data_protector.protect_data(data, "symmetric")
        decrypted = data_protector.unprotect_data(encrypted, "symmetric")
        
        assert decrypted.decode() == data
    
    def test_key_derivation(self):
        """Test key derivation"""
        from security.encryption.encryption_utils import KeyDerivation
        
        password = "test_password_123"
        key, salt = KeyDerivation.derive_key_from_password(password)
        
        assert key is not None
        assert salt is not None
        assert len(key) == 32  # 256 bits
        
        # Verify password
        assert KeyDerivation.verify_password(password, salt, key)
        assert not KeyDerivation.verify_password("wrong_password", salt, key)
    
    def test_input_validation(self):
        """Test input validation"""
        middleware = SecurityMiddleware()
        
        # Valid request
        valid_request = {
            'method': 'GET',
            'path': '/api/users',
            'ip_address': '192.168.1.1'
        }
        
        result = middleware.process_request(valid_request)
        assert result['allowed']
        
        # Invalid request (malicious)
        invalid_request = {
            'method': 'POST',
            'path': '/api/users?id=1 UNION SELECT password--',
            'ip_address': '192.168.1.1'
        }
        
        result = middleware.process_request(invalid_request)
        assert not result['allowed']
    
    def test_security_headers(self):
        """Test security headers generation"""
        headers_manager = SecurityHeaders()
        headers = headers_manager.get_security_headers()
        
        assert 'X-Content-Type-Options' in headers
        assert 'X-Frame-Options' in headers
        assert 'X-XSS-Protection' in headers
        assert headers['X-Content-Type-Options'] == 'nosniff'
    
    def test_xss_protection(self):
        """Test XSS protection"""
        validator = InputValidator()
        
        malicious_html = "<script>alert('XSS')</script>"
        sanitized = validator.sanitize_html(malicious_html)
        
        assert '<script>' not in sanitized
        assert 'alert' not in sanitized
    
    def test_authentication_flow(self):
        """Test complete authentication flow"""
        result = self.security_system.authenticate_user(
            username="test_user",
            password="password123",
            ip_address="192.168.1.1"
        )
        
        assert result['success']
        assert 'access_token' in result
        assert 'refresh_token' in result
    
    def test_request_processing(self):
        """Test request processing"""
        # First authenticate
        auth_result = self.security_system.authenticate_user(
            username="test_user",
            password="password123",
            ip_address="192.168.1.1"
        )
        
        if auth_result['success']:
            # Then process a request
            request_data = {
                'method': 'GET',
                'path': '/api/users',
                'headers': {
                    'authorization': f"Bearer {auth_result['access_token']}"
                },
                'ip_address': '192.168.1.1'
            }
            
            result = self.security_system.process_request(request_data)
            assert result['allowed']
    
    def test_security_analytics(self):
        """Test security analytics"""
        analytics = self.security_system.get_security_analytics()
        
        assert analytics is not None
        assert 'api_keys' in analytics
        assert 'active_sessions' in analytics


def main():
    """Main test runner"""
    test_suite = SecuritySystemTest()
    success = test_suite.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
