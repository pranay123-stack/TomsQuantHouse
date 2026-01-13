"""
Security Middleware
Request validation, sanitization, and security headers
"""

import re
import html
import json
import ipaddress
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import base64


class SecurityRules:
    """Security validation rules configuration"""
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        'image': {'.jpg', '.jpeg', '.png', '.gif', '.webp'},
        'document': {'.pdf', '.doc', '.docx', '.txt'},
        'data': {'.json', '.csv', '.xml', '.yaml', '.yml'}
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        'image': 10 * 1024 * 1024,  # 10MB
        'document': 50 * 1024 * 1024,  # 50MB
        'data': 100 * 1024 * 1024,  # 100MB
    }
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'(\bunion\b\s+\bselect\b)',
        r'(\bor\b\s+\d+\s*=\s*\d+)',
        r'(\band\b\s+\d+\s*=\s*\d+)',
        r"('|(\-\-)|(;)|(\|)|(\*)|(%))"
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>'
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$(){}\[\]<>]',
        r'\brm\b|\bcp\b|\bmv\b|\bcat\b|\bls\b',
        r'&&\s*\w+',
        r'\|\|\s*\w+',
        r'>\s*\w+',
        r'<\s*\w+'
    ]
    
    # SSRF patterns
    SSRF_PATTERNS = [
        r'localhost',
        r'127\.0\.0\.1',
        r'0\.0\.0\.0',
        r'::1',
        r'169\.254\.169\.254',
        r'10\.\d+\.\d+\.\d+',
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+',
        r'192\.168\.\d+\.\d+',
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',
        r'\.\.\\',
        r'%2e%2e%2f',
        r'%2e%2e%5c'
    ]


class InputValidator:
    """Input validation and sanitization"""
    
    def __init__(self):
        self.security_rules = SecurityRules()
    
    def validate_email(self, email: str) -> Dict[str, Any]:
        """Validate email address"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return {'valid': False, 'error': 'Invalid email format'}
        
        # Additional checks
        if len(email) > 254:
            return {'valid': False, 'error': 'Email too long'}
        
        if email.count('@') != 1:
            return {'valid': False, 'error': 'Invalid email format'}
        
        local, domain = email.split('@', 1)
        
        if len(local) > 64:
            return {'valid': False, 'error': 'Local part too long'}
        
        return {'valid': True, 'clean': email.lower()}
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL"""
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return {'valid': False, 'error': 'Only HTTP/HTTPS allowed'}
            
            # Check for localhost/private IPs
            if self._is_private_ip(parsed.hostname):
                return {'valid': False, 'error': 'Private IP addresses not allowed'}
            
            # Check for dangerous patterns
            if self._contains_malicious_patterns(url):
                return {'valid': False, 'error': 'Malicious patterns detected'}
            
            return {
                'valid': True,
                'clean': url,
                'parsed': {
                    'scheme': parsed.scheme,
                    'hostname': parsed.hostname,
                    'port': parsed.port,
                    'path': parsed.path,
                    'query': parsed.query
                }
            }
        except Exception:
            return {'valid': False, 'error': 'Invalid URL format'}
    
    def validate_file_upload(self, filename: str, content_type: str, 
                           file_size: int) -> Dict[str, Any]:
        """Validate file upload"""
        errors = []
        
        # Check file extension
        _, ext = os.path.splitext(filename.lower())
        if ext not in sum(SecurityRules.ALLOWED_EXTENSIONS.values(), set()):
            errors.append(f'File extension {ext} not allowed')
        
        # Check file size
        file_category = None
        for category, extensions in SecurityRules.ALLOWED_EXTENSIONS.items():
            if ext in extensions:
                file_category = category
                break
        
        if file_category and file_size > SecurityRules.MAX_FILE_SIZES[file_category]:
            errors.append(f'File too large. Maximum size: {SecurityRules.MAX_FILE_SIZES[file_category]} bytes')
        
        # Check content type
        allowed_types = {
            'image': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
            'document': ['application/pdf', 'application/msword', 'text/plain'],
            'data': ['application/json', 'text/csv', 'application/xml']
        }
        
        if file_category and content_type not in allowed_types.get(file_category, []):
            errors.append(f'Content type {content_type} not allowed for this file type')
        
        # Check for malicious content
        if self._contains_malicious_patterns(filename):
            errors.append('Malicious patterns detected in filename')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'file_category': file_category,
            'safe_filename': self._sanitize_filename(filename)
        }
    
    def validate_json(self, json_data: str) -> Dict[str, Any]:
        """Validate JSON data"""
        try:
            parsed = json.loads(json_data)
            
            # Check for dangerous keys
            dangerous_keys = ['__proto__', 'constructor', 'prototype']
            if self._contains_dangerous_keys(parsed, dangerous_keys):
                return {'valid': False, 'error': 'Dangerous keys detected'}
            
            # Check depth
            if self._get_json_depth(parsed) > 10:
                return {'valid': False, 'error': 'JSON too deeply nested'}
            
            return {'valid': True, 'data': parsed}
        except json.JSONDecodeError:
            return {'valid': False, 'error': 'Invalid JSON format'}
    
    def sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML content"""
        # Remove dangerous tags
        dangerous_tags = [
            'script', 'object', 'embed', 'link', 'style',
            'iframe', 'frame', 'frameset', 'meta', 'base'
        ]
        
        for tag in dangerous_tags:
            html_content = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
            html_content = re.sub(f'<{tag}[^>]*/?>', '', html_content, flags=re.IGNORECASE)
        
        # Escape HTML entities
        html_content = html.escape(html_content)
        
        # Remove dangerous attributes
        html_content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'javascript:\s*', '', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'data:\s*', 'data:', html_content, flags=re.IGNORECASE)
        
        return html_content
    
    def sanitize_sql(self, sql_input: str) -> str:
        """Sanitize SQL input"""
        # Remove SQL injection patterns
        for pattern in SecurityRules.SQL_INJECTION_PATTERNS:
            sql_input = re.sub(pattern, '', sql_input, flags=re.IGNORECASE)
        
        # Remove quotes and semicolons
        sql_input = sql_input.replace("'", "").replace('"', '').replace(';', '')
        
        return sql_input.strip()
    
    def _is_private_ip(self, hostname: str) -> bool:
        """Check if hostname resolves to private IP"""
        if not hostname:
            return False
        
        try:
            # Try to resolve hostname
            import socket
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if private
            return ip_obj.is_private or ip_obj.is_loopback
        except Exception:
            # If resolution fails, check if hostname itself is suspicious
            return any(pattern in hostname.lower() for pattern in [
                'localhost', '127.0.0.1', '0.0.0.0'
            ])
    
    def _contains_malicious_patterns(self, content: str) -> bool:
        """Check for malicious patterns"""
        all_patterns = (
            SecurityRules.SQL_INJECTION_PATTERNS +
            SecurityRules.XSS_PATTERNS +
            SecurityRules.COMMAND_INJECTION_PATTERNS +
            SecurityRules.SSRF_PATTERNS +
            SecurityRules.PATH_TRAVERSAL_PATTERNS
        )
        
        for pattern in all_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False
    
    def _contains_dangerous_keys(self, obj: Any, dangerous_keys: List[str]) -> bool:
        """Check if object contains dangerous keys"""
        if isinstance(obj, dict):
            for key in obj.keys():
                if key in dangerous_keys:
                    return True
                if self._contains_dangerous_keys(obj[key], dangerous_keys):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self._contains_dangerous_keys(item, dangerous_keys):
                    return True
        return False
    
    def _get_json_depth(self, obj: Any) -> int:
        """Get JSON object depth"""
        if isinstance(obj, dict):
            if not obj:
                return 1
            return 1 + max(self._get_json_depth(v) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return 1
            return 1 + max(self._get_json_depth(item) for item in obj)
        else:
            return 1
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename"""
        # Remove path traversal attempts
        filename = re.sub(r'\.\./', '', filename)
        filename = re.sub(r'\.\.\\', '', filename)
        
        # Keep only safe characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250-len(ext)] + ext
        
        return filename


class SecurityHeaders:
    """Security HTTP headers management"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get standard security headers"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            ),
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': (
                'geolocation=(), '
                'microphone=(), '
                'camera=(), '
                'payment=()'
            ),
            'Cache-Control': 'no-store, no-cache, must-revalidate, private',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    
    @staticmethod
    def get_cors_headers(origin: str = None, methods: List[str] = None,
                       headers: List[str] = None) -> Dict[str, str]:
        """Get CORS headers"""
        cors_headers = {
            'Access-Control-Allow-Origin': origin or '*',
            'Access-Control-Allow-Methods': ', '.join(methods or ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']),
            'Access-Control-Allow-Headers': ', '.join(headers or ['Content-Type', 'Authorization', 'X-Requested-With']),
            'Access-Control-Allow-Credentials': 'true',
            'Access-Control-Max-Age': '86400'
        }
        
        return cors_headers


class RateLimitProtection:
    """Additional rate limit protection"""
    
    def __init__(self):
        self.request_counts = {}
        self.last_reset = datetime.now()
    
    def check_rate_limit(self, identifier: str, limit: int = 100, 
                        window_minutes: int = 1) -> Dict[str, Any]:
        """Check request rate limit"""
        current_time = datetime.now()
        
        # Reset window if needed
        if (current_time - self.last_reset).total_seconds() >= window_minutes * 60:
            self.request_counts = {}
            self.last_reset = current_time
        
        # Get current count
        current_count = self.request_counts.get(identifier, 0)
        
        if current_count >= limit:
            return {
                'allowed': False,
                'current_count': current_count,
                'limit': limit,
                'retry_after': window_minutes * 60
            }
        
        # Increment count
        self.request_counts[identifier] = current_count + 1
        
        return {
            'allowed': True,
            'current_count': current_count + 1,
            'limit': limit,
            'remaining': limit - current_count - 1
        }


class SecurityMiddleware:
    """Main security middleware"""
    
    def __init__(self):
        self.validator = InputValidator()
        self.headers_manager = SecurityHeaders()
        self.rate_limit_protection = RateLimitProtection()
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming request for security"""
        response = {
            'allowed': True,
            'errors': [],
            'warnings': [],
            'sanitized_data': {},
            'security_headers': {},
            'risk_score': 0
        }
        
        # Extract request components
        method = request_data.get('method', 'GET')
        path = request_data.get('path', '')
        headers = request_data.get('headers', {})
        body = request_data.get('body', '')
        query_params = request_data.get('query_params', {})
        ip_address = request_data.get('ip_address')
        
        # Check rate limiting
        rate_limit_result = self.rate_limit_protection.check_rate_limit(ip_address or 'unknown')
        if not rate_limit_result['allowed']:
            response['allowed'] = False
            response['errors'].append('Rate limit exceeded')
            response['risk_score'] += 50
            return response
        
        # Validate headers
        headers_validation = self._validate_headers(headers)
        if not headers_validation['valid']:
            response['errors'].extend(headers_validation['errors'])
            response['risk_score'] += 20
        
        # Validate path
        path_validation = self._validate_path(path)
        if not path_validation['valid']:
            response['errors'].extend(path_validation['errors'])
            response['risk_score'] += 30
        
        # Validate query parameters
        query_validation = self._validate_query_params(query_params)
        if not query_validation['valid']:
            response['errors'].extend(query_validation['errors'])
            response['risk_score'] += 20
        
        # Validate body
        body_validation = self._validate_body(body, headers.get('content-type', ''))
        if not body_validation['valid']:
            response['errors'].extend(body_validation['errors'])
            response['risk_score'] += 25
        
        # Check for suspicious patterns
        suspicious_check = self._check_suspicious_patterns(
            method, path, body, headers, query_params
        )
        if suspicious_check['suspicious']:
            response['warnings'].extend(suspicious_check['warnings'])
            response['risk_score'] += suspicious_check['risk_increase']
        
        # Sanitize data
        if body_validation['valid']:
            response['sanitized_data'] = body_validation['sanitized_data']
        
        # Set security headers
        response['security_headers'] = self.headers_manager.get_security_headers()
        
        # Determine final decision
        if response['errors'] or response['risk_score'] >= 70:
            response['allowed'] = False
        
        return response
    
    def _validate_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Validate request headers"""
        errors = []
        
        # Check for dangerous headers
        dangerous_headers = ['host', 'x-forwarded-host', 'x-original-url']
        for header in dangerous_headers:
            if header in headers and headers[header].count('.') > 3:
                errors.append(f'Suspicious {header} header')
        
        # Validate content type
        content_type = headers.get('content-type', '')
        if content_type:
            if 'text/html' in content_type and 'application/json' in body:
                errors.append('Mismatched content type')
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _validate_path(self, path: str) -> Dict[str, Any]:
        """Validate request path"""
        errors = []
        
        # Check for path traversal
        for pattern in SecurityRules.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                errors.append('Path traversal attempt detected')
        
        # Check for malicious patterns
        for pattern in SecurityRules.SQL_INJECTION_PATTERNS + SecurityRules.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                errors.append('Malicious patterns in path')
        
        # Normalize path
        normalized_path = re.sub(r'/{2,}', '/', path)
        if normalized_path != path:
            errors.append('Suspicious path normalization')
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _validate_query_params(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate query parameters"""
        errors = []
        
        for key, value in query_params.items():
            # Check for SQL injection patterns
            for pattern in SecurityRules.SQL_INJECTION_PATTERNS:
                if re.search(pattern, str(value), re.IGNORECASE):
                    errors.append(f'SQL injection pattern in parameter {key}')
            
            # Check for XSS patterns
            for pattern in SecurityRules.XSS_PATTERNS:
                if re.search(pattern, str(value), re.IGNORECASE):
                    errors.append(f'XSS pattern in parameter {key}')
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _validate_body(self, body: str, content_type: str) -> Dict[str, Any]:
        """Validate request body"""
        errors = []
        sanitized_data = {}
        
        if not body:
            return {'valid': True, 'sanitized_data': {}}
        
        if 'application/json' in content_type:
            validation = self.validator.validate_json(body)
            if not validation['valid']:
                errors.append(validation['error'])
            else:
                sanitized_data = validation['data']
        
        elif 'application/x-www-form-urlencoded' in content_type:
            # Parse and validate form data
            from urllib.parse import parse_qs
            try:
                form_data = parse_qs(body)
                for key, values in form_data.items():
                    # Basic sanitization
                    sanitized_data[key] = [self.validator.sanitize_sql(v) for v in values]
            except Exception:
                errors.append('Invalid form data')
        
        return {'valid': len(errors) == 0, 'errors': errors, 'sanitized_data': sanitized_data}
    
    def _check_suspicious_patterns(self, method: str, path: str, body: str,
                                 headers: Dict[str, str], query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Check for suspicious patterns"""
        warnings = []
        risk_increase = 0
        
        # Check user agent
        user_agent = headers.get('user-agent', '')
        if not user_agent or len(user_agent) < 10:
            warnings.append('Suspicious user agent')
            risk_increase += 10
        
        # Check for automation indicators
        automation_patterns = ['bot', 'crawler', 'spider', 'curl', 'wget']
        if any(pattern in user_agent.lower() for pattern in automation_patterns):
            warnings.append('Possible automation detected')
            risk_increase += 15
        
        # Check request frequency (would need proper implementation)
        # This is a simplified check
        
        # Check for encoding attacks
        if '%' in path or '%' in body:
            warnings.append('URL encoding detected')
            risk_increase += 5
        
        return {
            'suspicious': len(warnings) > 0,
            'warnings': warnings,
            'risk_increase': risk_increase
        }
    
    def process_response(self, response_data: Dict[str, Any], 
                        request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process response for security"""
        # Add security headers to response
        security_headers = self.headers_manager.get_security_headers()
        
        # Add CORS headers if needed
        origin = request_data.get('headers', {}).get('origin')
        if origin:
            cors_headers = self.headers_manager.get_cors_headers(origin=origin)
            security_headers.update(cors_headers)
        
        response_data['headers'] = security_headers
        return response_data


# Example usage and testing
if __name__ == "__main__":
    # Initialize security middleware
    security_middleware = SecurityMiddleware()
    
    # Test malicious request
    malicious_request = {
        'method': 'POST',
        'path': '/api/users?id=1 UNION SELECT password FROM users--',
        'headers': {
            'content-type': 'application/json',
            'user-agent': 'curl/7.68.0'
        },
        'body': '{"name": "<script>alert(1)</script>", "__proto__": {"admin": true}}',
        'query_params': {'id': '1 UNION SELECT password FROM users--'},
        'ip_address': '192.168.1.1'
    }
    
    # Process request
    result = security_middleware.process_request(malicious_request)
    print(f"Malicious request processed:")
    print(f"  Allowed: {result['allowed']}")
    print(f"  Errors: {result['errors']}")
    print(f"  Warnings: {result['warnings']}")
    print(f"  Risk Score: {result['risk_score']}")
    print(f"  Security Headers: {len(result['security_headers'])} headers added")
    
    # Test valid request
    valid_request = {
        'method': 'GET',
        'path': '/api/users/123',
        'headers': {
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        'ip_address': '192.168.1.1'
    }
    
    result = security_middleware.process_request(valid_request)
    print(f"\nValid request processed:")
    print(f"  Allowed: {result['allowed']}")
    print(f"  Risk Score: {result['risk_score']}")
