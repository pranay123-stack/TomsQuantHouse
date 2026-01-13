# Comprehensive Security Authentication System

A robust, enterprise-grade security framework providing JWT authentication, RBAC authorization, API key management, rate limiting, audit logging, encryption, and security testing capabilities.

## Features

### 🛡️ Authentication & Authorization
- **JWT-based Authentication**: Secure token-based authentication with refresh token support
- **Role-Based Access Control (RBAC)**: Granular permission system with role hierarchy
- **Password Security**: Bcrypt hashing with strength validation
- **Session Management**: User session tracking with timeout and cleanup

### 🔑 API Key Management
- **API Key Generation**: Cryptographically secure API key creation
- **Key Types**: Standard, Read-Only, Admin, Batch, Webhook keys
- **Scope Management**: Granular permissions for API keys
- **Key Rotation**: Automatic and manual key rotation capabilities

### 🚦 Rate Limiting
- **Multiple Algorithms**: Sliding Window, Fixed Window, Token Bucket, Leaky Bucket
- **Redis Storage**: Distributed rate limiting across multiple instances
- **Flexible Configuration**: Custom rate limits per endpoint and user type
- **Real-time Monitoring**: Rate limit statistics and alerts

### 📝 Audit Logging
- **Comprehensive Logging**: All security events and API operations
- **Risk Scoring**: Automated risk assessment for security events
- **SQLite Storage**: Efficient storage with indexing and querying
- **Alert System**: Automatic alerting for high-risk events

### 🔒 Encryption
- **Data at Rest**: AES-256-GCM encryption for sensitive data
- **Data in Transit**: RSA encryption for secure communication
- **Key Management**: Secure key generation, rotation, and storage
- **Cryptographic Hashing**: SHA-256 and HMAC for data integrity

### 🛠️ Security Middleware
- **Input Validation**: Comprehensive request validation and sanitization
- **Security Headers**: Automatic security header injection
- **Threat Detection**: SQL injection, XSS, and other attack detection
- **CORS Management**: Configurable CORS policies

### 🔍 Security Testing
- **Vulnerability Scanning**: Automated security assessment
- **Penetration Testing**: Manual security testing tools
- **SSL/TLS Analysis**: Certificate and protocol validation
- **Information Disclosure**: Detection of sensitive information leaks

## Quick Start

### Installation

```bash
# Clone or copy the security package
cp -r security/ /your-project/
```

### Basic Usage

```python
from security import SecuritySystem, SecurityConfig

# Initialize security system
security_system = SecuritySystem()

# Authenticate user
auth_result = security_system.authenticate_user(
    username="admin",
    password="password123",
    ip_address="192.168.1.1"
)

if auth_result['success']:
    access_token = auth_result['access_token']
    print(f"Authentication successful! Token: {access_token[:50]}...")
```

### Processing Requests

```python
# Process incoming request
request_data = {
    'method': 'POST',
    'path': '/api/users',
    'headers': {
        'authorization': f"Bearer {access_token}",
        'content-type': 'application/json'
    },
    'body': '{"name": "John Doe"}',
    'ip_address': '192.168.1.1'
}

result = security_system.process_request(request_data)

if result['allowed']:
    print("Request authorized successfully")
    print(f"User ID: {result['user_id']}")
else:
    print(f"Request denied: {result['error']}")
```

## Detailed Component Guide

### 1. JWT Authentication

```python
from security import JWTManager, TokenType

jwt_manager = JWTManager()

# Generate access token
access_token = jwt_manager.generate_token(
    user_id="user123",
    role="admin",
    token_type=TokenType.ACCESS,
    permissions=["read", "write", "delete"]
)

# Validate token
payload = jwt_manager.validate_token(access_token)
if payload:
    print(f"Token valid for user: {payload['sub']}")
```

### 2. RBAC Authorization

```python
from security import RBACManager, Role, Permission

rbac = RBACManager()

# Assign role to user
rbac.assign_role("user123", Role.ADMIN)

# Check permissions
if rbac.check_permission("user123", Permission.USER_CREATE):
    print("User can create users")
```

### 3. API Key Management

```python
from security import APIKeyManager, KeyType

api_manager = APIKeyManager()

# Create API key
api_key = api_manager.create_api_key(
    name="Production API",
    key_type=KeyType.STANDARD,
    scopes=["read", "write"],
    created_by="admin",
    expiry_days=30
)

# Validate API key
key_obj = api_manager.validate_api_key(api_key)
if key_obj and key_obj.is_valid():
    print("API key is valid")
```

### 4. Rate Limiting

```python
from security import RateLimitManager

# Initialize with Redis
rate_limiter = RateLimitManager(
    redis_host="localhost",
    redis_port=6379
)

# Check rate limit
result = rate_limiter.check_rate_limit(
    identifier="user123",
    limit_type="api_requests"
)

if result['allowed']:
    print("Request allowed")
else:
    print(f"Rate limit exceeded. Retry after {result['retry_after']} seconds")
```

### 5. Audit Logging

```python
from security import AuditLogger, AuditEvent, AuditEventType

audit_logger = AuditLogger()

# Log security event
event = AuditEvent(AuditEventType.LOGIN_SUCCESS, "user123")
event.add_context(ip_address="192.168.1.1")
event.add_details(endpoint="/api/login")
audit_logger.log_event(event)

# Query events
events = audit_logger.get_events(
    event_type=AuditEventType.LOGIN_SUCCESS,
    limit=10
)
```

### 6. Encryption

```python
from security import KeyManager, DataProtector

key_manager = KeyManager()
data_protector = DataProtector(key_manager)

# Protect sensitive data
encrypted = data_protector.protect_data("sensitive information")
print(f"Encrypted: {encrypted[:50]}...")

# Unprotect data
decrypted = data_protector.unprotect_data(encrypted)
print(f"Decrypted: {decrypted}")
```

### 7. Security Middleware

```python
from security import SecurityMiddleware

security_middleware = SecurityMiddleware()

# Validate request
request_data = {
    'method': 'POST',
    'path': '/api/data',
    'body': '{"malicious": "<script>alert(1)</script>"}',
    'ip_address': '192.168.1.1'
}

result = security_middleware.process_request(request_data)

if not result['allowed']:
    print(f"Request blocked: {result['errors']}")
```

### 8. Security Testing

```python
from security import SecurityScanner

scanner = SecurityScanner()

# Run security scan
scan_results = scanner.scan_target("https://example.com")

print(f"Found {scan_results['scan_summary']['total']} vulnerabilities")

for vuln in scan_results['vulnerabilities']:
    print(f"- {vuln['title']} ({vuln['severity'].upper()})")
```

## Configuration

### Environment Variables

```bash
# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key
JWT_ACCESS_TOKEN_EXPIRY=900
JWT_REFRESH_TOKEN_EXPIRY=604800

# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Security
SECURITY_DEBUG=false
ENVIRONMENT=production
SESSION_TIMEOUT=30
```

### Configuration File

```python
from security.config import SecurityConfig

# Customize configuration
config = SecurityConfig()
config.JWT_ACCESS_TOKEN_EXPIRY = 1800  # 30 minutes
config.RATE_LIMITS['api_requests']['limit'] = 200

# Validate configuration
issues = config.validate_config()
if issues:
    print("Configuration issues:", issues)
```

## Advanced Usage

### Custom Security Middleware

```python
from security.middleware.security_middleware import SecurityMiddleware

class CustomSecurityMiddleware(SecurityMiddleware):
    def process_request(self, request_data):
        # Add custom validation logic
        result = super().process_request(request_data)
        
        # Add custom business logic
        if request_data.get('custom_header') != 'required_value':
            result['allowed'] = False
            result['errors'].append('Custom validation failed')
        
        return result
```

### Custom Audit Events

```python
from security.audit.audit_logger import AuditEvent, AuditEventType, AuditSeverity

# Log custom security event
custom_event = AuditEvent(
    AuditEventType.SECURITY_VIOLATION,
    user_id="user123",
    severity=AuditSeverity.HIGH
)

custom_event.add_details(
    violation_type="excessive_failed_logins",
    attempts=10,
    time_window="5_minutes"
)

audit_logger.log_event(custom_event)
```

### API Key with Custom Scopes

```python
# Create API key with custom scopes
api_key = api_manager.create_api_key(
    name="Data Export API",
    key_type=KeyType.BATCH,
    scopes=[
        "data:export",
        "data:read",
        "report:generate"
    ],
    created_by="admin"
)

# Check specific scope
if api_key.scopes.has_scope("data:export"):
    print("API key can export data")
```

## Security Best Practices

### 1. Environment Configuration
- Use strong, unique secrets in production
- Enable key rotation in production
- Configure proper CORS origins
- Set appropriate session timeouts

### 2. Monitoring and Alerting
- Monitor failed login attempts
- Set up alerts for suspicious activity
- Regular security scans
- Monitor rate limit violations

### 3. Data Protection
- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Implement proper key management
- Regular security updates

### 4. Access Control
- Principle of least privilege
- Regular permission audits
- Role-based access control
- API key scope limitations

## API Reference

### SecuritySystem

Main integration class that brings together all security components.

**Methods:**
- `authenticate_user(username, password, ip_address, user_agent)` - Authenticate user
- `process_request(request_data)` - Process incoming request
- `create_api_key(name, key_type, scopes, created_by, expiry_days)` - Create API key
- `get_security_analytics()` - Get security system analytics
- `run_security_scan(target_url, scan_types)` - Run security vulnerability scan

### JWTManager

Handles JWT token generation, validation, and refresh.

**Methods:**
- `generate_token(user_id, role, token_type, permissions, additional_claims)` - Generate JWT
- `validate_token(token)` - Validate JWT token
- `refresh_token(refresh_token)` - Refresh access token

### RBACManager

Manages role-based access control and permissions.

**Methods:**
- `assign_role(user_id, role)` - Assign role to user
- `check_permission(user_id, permission)` - Check user permission
- `check_resource_access(user_id, resource, action)` - Check resource access

## Testing

### Unit Tests

```bash
# Test individual components
python -m pytest security/auth/test_jwt_auth.py
python -m pytest security/rbac/test_rbac_manager.py
```

### Integration Tests

```bash
# Test full security system
python security/security_system.py
```

### Security Scanning

```python
# Test the security system itself
scanner = SecurityScanner()
results = scanner.scan_target("http://localhost:8000")
print("Security scan results:", results)
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   - Ensure Redis server is running
   - Check Redis credentials and network connectivity
   - Rate limiting will be disabled if Redis is unavailable

2. **JWT Token Validation Failed**
   - Check JWT_SECRET_KEY configuration
   - Verify token hasn't expired
   - Ensure clock synchronization across servers

3. **Permission Denied Errors**
   - Verify user roles are properly assigned
   - Check permission mappings
   - Ensure RBAC manager is initialized

4. **API Key Validation Failed**
   - Check API key format and validity
   - Verify API key scopes
   - Ensure key hasn't been revoked

### Performance Optimization

1. **Database Indexing**
   - Add indexes for frequently queried fields
   - Partition audit logs by date
   - Use connection pooling

2. **Redis Optimization**
   - Use Redis cluster for high availability
   - Configure appropriate memory limits
   - Monitor memory usage and keys

3. **Caching**
   - Cache permission checks
   - Cache user roles
   - Use distributed caching

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Security Considerations

- Never log sensitive data (passwords, tokens, keys)
- Use HTTPS in all environments
- Regularly rotate encryption keys
- Monitor for suspicious patterns
- Keep dependencies updated
- Perform regular security audits

## License

This security system is provided as-is for educational and development purposes. Review and test thoroughly before production use.

## Support

For issues and questions:
- Check the documentation
- Review the examples
- Test with the provided test cases
- Examine the code comments for implementation details

---

**Important**: This security system requires proper configuration and testing before production deployment. Always follow security best practices and keep dependencies updated.
