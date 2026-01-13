"""
Vulnerability Scanning and Security Testing Tools
Comprehensive security assessment tools
"""

import requests
import re
import ssl
import socket
import subprocess
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import concurrent.futures
import threading
from urllib.parse import urljoin, urlparse
import base64


class VulnerabilitySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VulnerabilityCategory(Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INPUT_VALIDATION = "input_validation"
    SESSION_MANAGEMENT = "session_management"
    CRYPTOGRAPHY = "cryptography"
    ERROR_HANDLING = "error_handling"
    SECURITY_HEADERS = "security_headers"
    INFORMATION_DISCLOSURE = "information_disclosure"
    BUSINESS_LOGIC = "business_logic"
    INJECTION = "injection"


class Vulnerability:
    """Vulnerability data model"""
    
    def __init__(self, category: VulnerabilityCategory, severity: VulnerabilitySeverity,
                 title: str, description: str, solution: str, references: List[str] = None):
        self.id = self._generate_vuln_id()
        self.category = category
        self.severity = severity
        self.title = title
        self.description = description
        self.solution = solution
        self.references = references or []
        self.discovered_at = datetime.utcnow()
        self.status = "open"
    
    def _generate_vuln_id(self) -> str:
        """Generate unique vulnerability ID"""
        return f"VULN-{datetime.utcnow().strftime('%Y%m%d')}-{hashlib.md5(str(datetime.utcnow().timestamp()).encode()).hexdigest()[:8].upper()}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'solution': self.solution,
            'references': self.references,
            'discovered_at': self.discovered_at.isoformat(),
            'status': self.status
        }


class SecurityScanner:
    """Main security scanner"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SecurityScanner/1.0 (+https://security-scanner.example.com)'
        })
        self.vulnerabilities = []
        self.scan_results = {}
    
    def scan_target(self, target_url: str, scan_types: List[str] = None) -> Dict[str, Any]:
        """Scan target for vulnerabilities"""
        if scan_types is None:
            scan_types = [
                'security_headers',
                'ssl_configuration',
                'information_disclosure',
                'injection_vulnerabilities',
                'authentication_bypass'
            ]
        
        results = {
            'target': target_url,
            'scan_started': datetime.utcnow().isoformat(),
            'scan_completed': None,
            'vulnerabilities': [],
            'scan_summary': {},
            'scan_type': scan_types
        }
        
        print(f"Starting security scan for: {target_url}")
        
        # Parse target URL
        parsed_url = urlparse(target_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Run scans concurrently where possible
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            
            if 'security_headers' in scan_types:
                futures['headers'] = executor.submit(self._scan_security_headers, target_url)
            
            if 'ssl_configuration' in scan_types:
                futures['ssl'] = executor.submit(self._scan_ssl_configuration, parsed_url.hostname, parsed_url.port or 443)
            
            if 'information_disclosure' in scan_types:
                futures['info_disclosure'] = executor.submit(self._scan_information_disclosure, base_url)
            
            if 'injection_vulnerabilities' in scan_types:
                futures['injection'] = executor.submit(self._scan_injection_vulnerabilities, target_url)
            
            if 'authentication_bypass' in scan_types:
                futures['auth'] = executor.submit(self._scan_authentication_bypass, target_url)
            
            # Collect results
            for scan_type, future in futures.items():
                try:
                    scan_result = future.result(timeout=60)
                    results[scan_type] = scan_result
                    results['vulnerabilities'].extend(scan_result.get('vulnerabilities', []))
                    print(f"Completed {scan_type} scan")
                except Exception as e:
                    print(f"Error in {scan_type} scan: {e}")
                    results[scan_type] = {'error': str(e)}
        
        # Generate summary
        results['scan_completed'] = datetime.utcnow().isoformat()
        results['scan_summary'] = self._generate_scan_summary(results['vulnerabilities'])
        
        return results
    
    def _scan_security_headers(self, url: str) -> Dict[str, Any]:
        """Scan for security headers"""
        vulnerabilities = []
        
        try:
            response = self.session.get(url, timeout=10)
            headers = response.headers
            
            # Required security headers
            required_headers = {
                'X-Content-Type-Options': {
                    'expected': 'nosniff',
                    'severity': VulnerabilitySeverity.MEDIUM,
                    'title': 'Missing X-Content-Type-Options Header',
                    'description': 'Missing X-Content-Type-Options header allows MIME type sniffing',
                    'solution': 'Add X-Content-Type-Options: nosniff to all responses'
                },
                'X-Frame-Options': {
                    'expected': ['DENY', 'SAMEORIGIN'],
                    'severity': VulnerabilitySeverity.HIGH,
                    'title': 'Missing X-Frame-Options Header',
                    'description': 'Missing X-Frame-Options header allows clickjacking attacks',
                    'solution': 'Add X-Frame-Options: DENY or SAMEORIGIN to prevent framing'
                },
                'Strict-Transport-Security': {
                    'expected': None,
                    'severity': VulnerabilitySeverity.HIGH,
                    'title': 'Missing HSTS Header',
                    'description': 'Missing Strict-Transport-Security header allows man-in-the-middle attacks',
                    'solution': 'Add Strict-Transport-Security header with appropriate max-age'
                },
                'Content-Security-Policy': {
                    'expected': None,
                    'severity': VulnerabilitySeverity.HIGH,
                    'title': 'Missing Content Security Policy',
                    'description': 'Missing CSP header increases risk of XSS attacks',
                    'solution': 'Implement a strict Content Security Policy'
                }
            }
            
            for header, config in required_headers.items():
                if header not in headers:
                    vuln = Vulnerability(
                        category=VulnerabilityCategory.SECURITY_HEADERS,
                        severity=config['severity'],
                        title=config['title'],
                        description=config['description'],
                        solution=config['solution'],
                        references=['https://owasp.org/www-project-secure-headers/']
                    )
                    vulnerabilities.append(vuln.to_dict())
                
                elif config['expected'] and isinstance(config['expected'], list):
                    if headers[header] not in config['expected']:
                        vuln = Vulnerability(
                            category=VulnerabilityCategory.SECURITY_HEADERS,
                            severity=config['severity'],
                            title=f'{header} Header Misconfiguration',
                            description=f'{header} header has unexpected value: {headers[header]}',
                            solution=f'Set {header} to one of: {", ".join(config["expected"])}',
                            references=['https://owasp.org/www-project-secure-headers/']
                        )
                        vulnerabilities.append(vuln.to_dict())
            
            # Check for information disclosure headers
            info_disclosure_headers = ['Server', 'X-Powered-By', 'X-AspNet-Version']
            for header in info_disclosure_headers:
                if header in headers:
                    vuln = Vulnerability(
                        category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
                        severity=VulnerabilitySeverity.LOW,
                        title=f'Information Disclosure in {header}',
                        description=f'{header} header reveals version information: {headers[header]}',
                        solution=f'Remove or obscure the {header} header to prevent version disclosure',
                        references=['https://owasp.org/www-community/attacks/Information_exposure_through_server_version_information']
                    )
                    vulnerabilities.append(vuln.to_dict())
        
        except Exception as e:
            return {'error': str(e), 'vulnerabilities': []}
        
        return {'vulnerabilities': vulnerabilities}
    
    def _scan_ssl_configuration(self, hostname: str, port: int) -> Dict[str, Any]:
        """Scan SSL/TLS configuration"""
        vulnerabilities = []
        
        try:
            # Check SSL certificate
            context = ssl.create_default_context()
            
            # Test different SSL versions
            ssl_issues = []
            
            # Check certificate validity
            try:
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        
                        # Check certificate expiration
                        not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                        days_until_expiry = (not_after - datetime.utcnow()).days
                        
                        if days_until_expiry < 30:
                            vuln = Vulnerability(
                                category=VulnerabilityCategory.CRYPTOGRAPHY,
                                severity=VulnerabilitySeverity.MEDIUM if days_until_expiry > 7 else VulnerabilitySeverity.HIGH,
                                title='SSL Certificate Expiring Soon',
                                description=f'SSL certificate expires in {days_until_expiry} days',
                                solution='Renew SSL certificate before expiration',
                                references=['https://www.ssllabs.com/downloads/']
                            )
                            vulnerabilities.append(vuln.to_dict())
                        
                        # Check certificate chain
                        if 'subjectAltName' not in cert:
                            vuln = Vulnerability(
                                category=VulnerabilityCategory.CRYPTOGRAPHY,
                                severity=VulnerabilitySeverity.MEDIUM,
                                title='Missing Subject Alternative Name',
                                description='Certificate missing Subject Alternative Name extension',
                                solution='Add Subject Alternative Name extension to certificate',
                                references=['https://tools.ietf.org/html/rfc6125']
                            )
                            vulnerabilities.append(vuln.to_dict())
                        
            except ssl.SSLError as e:
                vuln = Vulnerability(
                    category=VulnerabilityCategory.CRYPTOGRAPHY,
                    severity=VulnerabilitySeverity.CRITICAL,
                    title='SSL/TLS Configuration Error',
                    description=f'SSL/TLS error: {str(e)}',
                    solution='Fix SSL/TLS configuration and certificate issues',
                    references=['https://owasp.org/www-project-test-guides/']
                )
                vulnerabilities.append(vuln.to_dict())
            
            # Check for weak SSL protocols
            try:
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    # Try SSLv2 and SSLv3 (should be disabled)
                    for protocol in [ssl.PROTOCOL_SSLv23, ssl.PROTOCOL_SSLv3, ssl.PROTOCOL_TLSv1]:
                        try:
                            context = ssl.SSLContext(protocol)
                            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                                if protocol in [ssl.PROTOCOL_SSLv3, ssl.PROTOCOL_TLSv1]:
                                    vuln = Vulnerability(
                                        category=VulnerabilityCategory.CRYPTOGRAPHY,
                                        severity=VulnerabilitySeverity.HIGH,
                                        title='Weak SSL/TLS Protocol Enabled',
                                        description=f'Weak protocol {protocol} is enabled',
                                        solution='Disable weak SSL/TLS protocols (SSLv2, SSLv3, TLSv1.0)',
                                        references=['https://owasp.org/www-project-top-ten/']
                                    )
                                    vulnerabilities.append(vuln.to_dict())
                        except Exception:
                            continue  # Good, protocol is disabled
            except Exception:
                pass  # Connection failed, which is expected for some tests
        
        except Exception as e:
            return {'error': str(e), 'vulnerabilities': []}
        
        return {'vulnerabilities': vulnerabilities}
    
    def _scan_information_disclosure(self, base_url: str) -> Dict[str, Any]:
        """Scan for information disclosure vulnerabilities"""
        vulnerabilities = []
        
        # Common information disclosure paths
        info_paths = [
            '/robots.txt',
            '/.well-known/security.txt',
            '/sitemap.xml',
            '/crossdomain.xml',
            '/clientaccesspolicy.xml',
            '/.env',
            '/config.json',
            '/package.json',
            '/composer.json',
            '/wp-config.php',
            '/admin/',
            '/backup/',
            '/test/',
            '/debug/',
            '/.git/',
            '/.svn/',
            '/error',
            '/404',
            '/server-status',
            '/server-info'
        ]
        
        for path in info_paths:
            try:
                url = urljoin(base_url, path)
                response = self.session.get(url, timeout=5)
                
                if response.status_code == 200:
                    content = response.text.lower()
                    
                    # Check for sensitive information
                    sensitive_patterns = {
                        'password': r'password\s*[=:]\s*[\'"]?[\w\W]+[\'"]?',
                        'api_key': r'(api[_-]?key|apikey)\s*[=:]\s*[\'"]?[\w\W]+[\'"]?',
                        'secret': r'secret\s*[=:]\s*[\'"]?[\w\W]+[\'"]?',
                        'database': r'(database|db[_-]?connection)\s*[=:]\s*[\'"]?[\w\W]+[\'"]?',
                        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    }
                    
                    for info_type, pattern in sensitive_patterns.items():
                        if re.search(pattern, content, re.IGNORECASE):
                            vuln = Vulnerability(
                                category=VulnerabilityCategory.INFORMATION_DISCLOSURE,
                                severity=VulnerabilitySeverity.HIGH,
                                title=f'Sensitive Information Disclosure in {path}',
                                description=f'Found potential {info_type} information in {url}',
                                solution=f'Secure or remove {path} and ensure no sensitive data is exposed',
                                references=['https://owasp.org/www-community/attacks/Information_exposure']
                            )
                            vulnerabilities.append(vuln.to_dict())
                            break
                    
                    # Check for debug/error pages
                    if 'error' in path or 'debug' in path:
                        if any(word in content for word in ['stack trace', 'debug', 'error:', 'exception']):
                            vuln = Vulnerability(
                                category=VulnerabilityCategory.ERROR_HANDLING,
                                severity=VulnerabilitySeverity.MEDIUM,
                                title='Debug/Error Information Disclosure',
                                description=f'Error or debug information exposed at {url}',
                                solution='Disable debug mode and ensure proper error handling',
                                references=['https://owasp.org/www-community/attacks/Information_exposure_through_error_messages']
                            )
                            vulnerabilities.append(vuln.to_dict())
            
            except requests.RequestException:
                continue  # Path not found, which is good
        
        return {'vulnerabilities': vulnerabilities}
    
    def _scan_injection_vulnerabilities(self, url: str) -> Dict[str, Any]:
        """Scan for injection vulnerabilities"""
        vulnerabilities = []
        
        # SQL injection payloads
        sql_payloads = [
            "' OR '1'='1",
            "' UNION SELECT NULL--",
            "' OR 1=1--",
            "'; DROP TABLE users--",
            "' AND (SELECT COUNT(*) FROM users)>0--"
        ]
        
        # XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>"
        ]
        
        # Test SQL injection on common parameters
        test_params = ['id', 'user_id', 'search', 'q', 'query']
        
        try:
            # Test GET parameters
            for param in test_params:
                for payload in sql_payloads:
                    test_url = f"{url}?{param}={payload}"
                    response = self.session.get(test_url, timeout=10)
                    
                    # Check for SQL errors
                    sql_error_patterns = [
                        r'sql syntax.*mysql',
                        r'ora-\d{5}',
                        r'microsoft ole db.*odbc.*driver',
                        r'postgresql.*error',
                        r'warning.*\Wmysql_.*\W'
                    ]
                    
                    for pattern in sql_error_patterns:
                        if re.search(pattern, response.text, re.IGNORECASE):
                            vuln = Vulnerability(
                                category=VulnerabilityCategory.INJECTION,
                                severity=VulnerabilitySeverity.HIGH,
                                title='SQL Injection Vulnerability',
                                description=f'Potential SQL injection found in parameter {param} at {test_url}',
                                solution='Use parameterized queries or prepared statements',
                                references=['https://owasp.org/www-community/attacks/SQL_Injection']
                            )
                            vulnerabilities.append(vuln.to_dict())
                            break
            
            # Test POST parameters for XSS
            for payload in xss_payloads:
                data = {'input': payload, 'search': payload}
                response = self.session.post(url, data=data, timeout=10)
                
                if payload in response.text:
                    vuln = Vulnerability(
                        category=VulnerabilityCategory.INJECTION,
                        severity=VulnerabilitySeverity.HIGH,
                        title='Cross-Site Scripting (XSS) Vulnerability',
                        description=f'Potential XSS vulnerability found in POST data at {url}',
                        solution='Implement proper input validation and output encoding',
                        references=['https://owasp.org/www-community/attacks/xss/']
                    )
                    vulnerabilities.append(vuln.to_dict())
                    break
        
        except requests.RequestException:
            pass
        
        return {'vulnerabilities': vulnerabilities}
    
    def _scan_authentication_bypass(self, url: str) -> Dict[str, Any]:
        """Scan for authentication bypass vulnerabilities"""
        vulnerabilities = []
        
        # Test common admin endpoints
        admin_endpoints = [
            '/admin',
            '/admin/',
            '/administrator',
            '/wp-admin',
            '/phpmyadmin',
            '/cpanel',
            '/manager/html'
        ]
        
        # Bypass techniques to test
        bypass_techniques = [
            {'param': 'admin', 'value': 'true'},
            {'param': 'user', 'value': 'admin'},
            {'param': 'role', 'value': 'administrator'},
            {'param': 'debug', 'value': 'true'},
            {'param': 'bypass', 'value': '1'}
        ]
        
        for endpoint in admin_endpoints:
            test_url = urljoin(url, endpoint)
            
            # Test direct access
            try:
                response = self.session.get(test_url, timeout=10)
                
                if response.status_code == 200:
                    # Check if it's a login page or if authentication is bypassed
                    content = response.text.lower()
                    login_indicators = ['login', 'sign in', 'username', 'password', 'authentication']
                    access_indicators = ['dashboard', 'admin panel', 'welcome', 'logout']
                    
                    if any(indicator in content for indicator in login_indicators):
                        # Likely a proper login page
                        pass
                    elif any(indicator in content for indicator in access_indicators):
                        vuln = Vulnerability(
                            category=VulnerabilityCategory.AUTHORIZATION,
                            severity=VulnerabilitySeverity.HIGH,
                            title='Authentication Bypass',
                            description=f'Administrative endpoint {test_url} may be accessible without authentication',
                            solution='Implement proper authentication and authorization controls',
                            references=['https://owasp.org/www-community/controls/Authorization']
                        )
                        vulnerabilities.append(vuln.to_dict())
                
                # Test bypass parameters
                for technique in bypass_techniques:
                    bypass_url = f"{test_url}?{technique['param']}={technique['value']}"
                    bypass_response = self.session.get(bypass_url, timeout=10)
                    
                    if bypass_response.status_code == 200 and bypass_response.text != response.text:
                        vuln = Vulnerability(
                            category=VulnerabilityCategory.AUTHORIZATION,
                            severity=VulnerabilitySeverity.HIGH,
                            title='Authentication Bypass via Parameter',
                            description=f'Authentication may be bypassed using parameter {technique["param"]}={technique["value"]}',
                            solution='Remove or properly validate authentication bypass parameters',
                            references=['https://owasp.org/www-community/controls/Authorization']
                        )
                        vulnerabilities.append(vuln.to_dict())
            
            except requests.RequestException:
                continue
        
        return {'vulnerabilities': vulnerabilities}
    
    def _generate_scan_summary(self, vulnerabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate scan summary"""
        if not vulnerabilities:
            return {'total': 0, 'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        summary = {'total': len(vulnerabilities), 'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for vuln in vulnerabilities:
            severity = vuln.get('severity', 'low')
            if severity in summary:
                summary[severity] += 1
        
        return summary


class PenetrationTest:
    """Penetration testing tools"""
    
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PenTest/1.0'
        })
    
    def test_brute_force_protection(self, login_url: str, username: str, 
                                  password_list: List[str]) -> Dict[str, Any]:
        """Test brute force protection mechanisms"""
        results = {
            'brute_force_protected': False,
            'attempts_made': 0,
            'successful_attempts': [],
            'rate_limits_detected': False,
            'lockout_detected': False
        }
        
        for password in password_list:
            results['attempts_made'] += 1
            
            try:
                response = self.session.post(login_url, data={
                    'username': username,
                    'password': password
                }, timeout=10)
                
                # Check for successful login indicators
                if any(indicator in response.text.lower() for indicator in 
                      ['dashboard', 'welcome', 'logout', 'profile']):
                    results['successful_attempts'].append(password)
                
                # Check for rate limiting
                if response.status_code == 429 or 'rate limit' in response.text.lower():
                    results['rate_limits_detected'] = True
                    break
                
                # Check for account lockout
                if 'locked' in response.text.lower() or 'disabled' in response.text.lower():
                    results['lockout_detected'] = True
                    break
                
                # Wait between attempts
                time.sleep(1)
            
            except requests.RequestException:
                continue
        
        results['brute_force_protected'] = results['rate_limits_detected'] or results['lockout_detected']
        
        return results
    
    def test_session_security(self, authenticated_url: str) -> Dict[str, Any]:
        """Test session security"""
        results = {
            'cookies_secure': False,
            'httponly_cookies': False,
            'session_fixation_vulnerable': False,
            'secure_attributes_checked': []
        }
        
        try:
            # First, get initial cookies
            login_response = self.session.get(authenticated_url)
            initial_cookies = dict(self.session.cookies)
            
            # Check cookie attributes
            for cookie in self.session.cookies:
                results['secure_attributes_checked'].append({
                    'name': cookie.name,
                    'secure': cookie.secure,
                    'httponly': hasattr(cookie, 'has_nonstandard_attr') and cookie.has_nonstandard_attr('HttpOnly'),
                    'samesite': getattr(cookie, 'samesite', None)
                })
            
            # Check if cookies are marked as secure
            results['cookies_secure'] = all(cookie.secure for cookie in self.session.cookies)
            
            # Test session fixation (in a real test, this would require more sophisticated testing)
            # This is a simplified check
            
            return results
        
        except Exception as e:
            return {'error': str(e)}
    
    def test_file_upload_security(self, upload_url: str, test_files: List[Tuple[str, str, bytes]]) -> Dict[str, Any]:
        """Test file upload security"""
        results = {
            'unsafe_files_detected': [],
            'security_controls': [],
            'mimic_attempts': []
        }
        
        for filename, content_type, file_content in test_files:
            try:
                files = {'file': (filename, file_content, content_type)}
                response = self.session.post(upload_url, files=files, timeout=10)
                
                # Check if dangerous file types are accepted
                dangerous_extensions = ['.php', '.jsp', '.asp', '.aspx', '.exe', '.sh']
                if any(filename.lower().endswith(ext) for ext in dangerous_extensions):
                    if response.status_code == 200:
                        results['unsafe_files_detected'].append(filename)
                
                # Test for file type validation
                if response.status_code == 400:
                    results['security_controls'].append('file_type_validation')
            
            except requests.RequestException:
                continue
        
        return results


# Example usage and testing
if __name__ == "__main__":
    # Initialize security scanner
    scanner = SecurityScanner()
    
    # Example scan (replace with actual target URL)
    target_url = "https://httpbin.org"
    
    print("=== Security Scan Example ===")
    scan_results = scanner.scan_target(target_url)
    
    print(f"\nScan completed for: {scan_results['target']}")
    print(f"Total vulnerabilities found: {scan_results['scan_summary'].get('total', 0)}")
    
    if scan_results['scan_summary'].get('total', 0) > 0:
        print("\nVulnerabilities by severity:")
        for severity, count in scan_results['scan_summary'].items():
            if severity != 'total':
                print(f"  {severity.upper()}: {count}")
    
    # Example penetration test
    print("\n=== Penetration Test Example ===")
    pentest = PenetrationTest(target_url)
    
    # Test session security
    session_results = pentest.test_session_security(f"{target_url}/cookies")
    print(f"Session security test: {session_results}")
    
    print("\nScan results saved to scan_results.json")
    with open('scan_results.json', 'w') as f:
        json.dump(scan_results, f, indent=2)
