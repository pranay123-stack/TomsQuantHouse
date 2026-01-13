#!/usr/bin/env python3
"""
API Security Audit Tool - Comprehensive API Security Assessment
"""

import os
import re
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import subprocess

@dataclass
class APIFinding:
    """API security finding"""
    type: str
    severity: str
    endpoint: str
    description: str
    evidence: str
    remediation: str
    cwe_id: Optional[str] = None

class APISecurityAuditor:
    """API Security Auditor"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.findings: List[APIFinding] = []
        self.endpoints: List[Dict[str, Any]] = []
        
    def audit_api_security(self) -> List[APIFinding]:
        """Perform comprehensive API security audit"""
        print("🌐 Auditing API security...")
        
        # 1. Extract API endpoints
        self._extract_api_endpoints()
        
        # 2. Audit input validation
        self._audit_input_validation()
        
        # 3. Audit authentication requirements
        self._audit_authentication_requirements()
        
        # 4. Audit rate limiting
        self._audit_rate_limiting()
        
        # 5. Audit error handling
        self._audit_error_handling()
        
        # 6. Audit CORS configuration
        self._audit_cors_configuration()
        
        # 7. Audit SQL injection vulnerabilities
        self._audit_sql_injection()
        
        # 8. Test live endpoints (if available)
        self._test_live_endpoints()
        
        return self.findings
    
    def _extract_api_endpoints(self):
        """Extract API endpoints from code"""
        api_files = list(self.workspace_path.rglob("*.py")) + list(self.workspace_path.rglob("*.js"))
        
        for api_file in api_files:
            if any(skip in str(api_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(api_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Extract FastAPI/Flask routes
                    routes = re.findall(r'@(app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']', content)
                    for method, http_method, path in routes:
                        self.endpoints.append({
                            'file': str(api_file),
                            'method': http_method.upper(),
                            'path': path,
                            'full_endpoint': f"{http_method.upper()} {path}"
                        })
                    
                    # Extract route handlers
                    handlers = re.findall(r'def\s+(\w+)\s*\([^)]*\):\s*.*?\n(?:async\s+)?def\s+\1', content, re.DOTALL)
                    for handler in handlers:
                        if any(keyword in handler.lower() for keyword in ['get', 'post', 'put', 'delete', 'login']):
                            self.findings.append(APIFinding(
                                type="API Handler Discovery",
                                severity="INFO",
                                endpoint=handler,
                                description=f"API endpoint handler found: {handler}",
                                evidence=f"Handler function: {handler}",
                                remediation="Review handler for security implications"
                            ))
                            
            except Exception:
                continue
    
    def _audit_input_validation(self):
        """Audit input validation in API endpoints"""
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if any(skip in str(py_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for missing input validation
                    validation_patterns = [
                        r'request\.json\s*\[',
                        r'request\.form\s*\[',
                        r'request\.args\s*\[',
                        r'\+\s*["\'].*\+',
                        r'\.\s*format\s*\('
                    ]
                    
                    for pattern in validation_patterns:
                        if re.search(pattern, content):
                            self.findings.append(APIFinding(
                                type="Missing Input Validation",
                                severity="HIGH",
                                endpoint=str(py_file),
                                description="API endpoint may lack proper input validation",
                                evidence=f"Pattern found: {pattern}",
                                remediation="Implement comprehensive input validation and sanitization",
                                cwe_id="CWE-20"
                            ))
                    
                    # Check for direct SQL parameter usage
                    if re.search(r'execute\s*\(\s*f["\'].*\{.*\}.*["\']', content):
                        self.findings.append(APIFinding(
                            type="SQL Injection Risk",
                            severity="CRITICAL",
                            endpoint=str(py_file),
                            description="Potential SQL injection vulnerability found",
                            evidence="F-string or string formatting in SQL query",
                            remediation="Use parameterized queries or ORM methods",
                            cwe_id="CWE-89"
                        ))
                    
                    # Check for command injection risks
                    if re.search(r'subprocess\.(call|run|Popen)\s*\([^)]*raw_input|input\(', content):
                        self.findings.append(APIFinding(
                            type="Command Injection Risk",
                            severity="HIGH",
                            endpoint=str(py_file),
                            description="Potential command injection vulnerability",
                            evidence="User input passed to subprocess functions",
                            remediation="Use subprocess with shell=False and validate input",
                            cwe_id="CWE-78"
                        ))
                        
            except Exception:
                continue
    
    def _audit_authentication_requirements(self):
        """Audit authentication requirements for API endpoints"""
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if any(skip in str(py_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for endpoints without authentication
                    protected_endpoints = []
                    public_endpoints = []
                    
                    # Look for auth decorators
                    auth_patterns = [
                        r'@auth\.requires_auth',
                        r'@login_required',
                        r'@require_login',
                        r'@jwt_required',
                        r'@authenticate'
                    ]
                    
                    has_auth = any(re.search(pattern, content) for pattern in auth_patterns)
                    
                    # Look for sensitive endpoints
                    sensitive_patterns = [
                        r'["\']/admin',
                        r'["\']/api/users',
                        r'["\']/api/data',
                        r'["\']/delete',
                        r'["\']/admin'
                    ]
                    
                    for pattern in sensitive_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            if has_auth:
                                protected_endpoints.append(pattern)
                            else:
                                public_endpoints.append(pattern)
                    
                    if public_endpoints:
                        self.findings.append(APIFinding(
                            type="Missing Authentication",
                            severity="HIGH",
                            endpoint=str(py_file),
                            description="Sensitive endpoints may not require authentication",
                            evidence=f"Unprotected endpoints: {', '.join(public_endpoints)}",
                            remediation="Implement authentication for all sensitive endpoints",
                            cwe_id="CWE-306"
                        ))
                        
            except Exception:
                continue
    
    def _audit_rate_limiting(self):
        """Audit rate limiting implementation"""
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if any(skip in str(py_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for login endpoints without rate limiting
                    if re.search(r'["\']/(login|auth|signin)', content, re.IGNORECASE):
                        if 'rate_limit' not in content.lower() and 'ratelimit' not in content.lower():
                            self.findings.append(APIFinding(
                                type="Missing Rate Limiting",
                                severity="MEDIUM",
                                endpoint=str(py_file),
                                description="Login endpoint may lack rate limiting",
                                evidence="No rate limiting found for authentication endpoint",
                                remediation="Implement rate limiting for authentication endpoints",
                                cwe_id="CWE-770"
                            ))
                    
                    # Check for weak rate limiting
                    if 'rate_limit' in content.lower() or 'ratelimit' in content.lower():
                        limit_match = re.search(r'limit\s*[=:]\s*(\d+)', content, re.IGNORECASE)
                        if limit_match and int(limit_match.group(1)) > 1000:
                            self.findings.append(APIFinding(
                                type="Weak Rate Limiting",
                                severity="MEDIUM",
                                endpoint=str(py_file),
                                description="Rate limit may be too permissive",
                                evidence=f"Rate limit: {limit_match.group(1)}",
                                remediation="Implement stricter rate limits (100-500 requests per minute)",
                                cwe_id="CWE-770"
                            ))
                            
            except Exception:
                continue
    
    def _audit_error_handling(self):
        """Audit error handling in API endpoints"""
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if any(skip in str(py_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for sensitive information in error messages
                    sensitive_patterns = [
                        r'traceback',
                        r'stack trace',
                        r'database.*error',
                        r'sql.*error',
                        r'connection.*error',
                        r'import.*error'
                    ]
                    
                    for pattern in sensitive_patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            self.findings.append(APIFinding(
                                type="Information Disclosure",
                                severity="MEDIUM",
                                endpoint=str(py_file),
                                description="Error messages may reveal sensitive information",
                                evidence=f"Pattern found: {pattern}",
                                remediation="Implement secure error handling that doesn't expose system details",
                                cwe_id="CWE-209"
                            ))
                    
                    # Check for generic exception handling
                    if re.search(r'except\s+Exception\s*:', content):
                        self.findings.append(APIFinding(
                            type="Generic Exception Handling",
                            severity="LOW",
                            endpoint=str(py_file),
                            description="Generic exception handling may hide security issues",
                            evidence="Generic Exception caught",
                            remediation="Use specific exception handling and implement proper logging",
                            cwe_id="CWE-396"
                        ))
                            
            except Exception:
                continue
    
    def _audit_cors_configuration(self):
        """Audit CORS configuration"""
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if any(skip in str(py_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for permissive CORS
                    if 'CORS' in content or 'cors' in content:
                        if re.search(r'allow_origins\s*=\s*\[?[\'"]\*[\'"\]]?', content):
                            self.findings.append(APIFinding(
                                type="Permissive CORS Policy",
                                severity="HIGH",
                                endpoint=str(py_file),
                                description="CORS policy allows all origins",
                                evidence="Wildcard (*) origin allowed",
                                remediation="Implement specific origin whitelist instead of wildcard",
                                cwe_id="CWE-942"
                            ))
                        
                        if 'allow_credentials=True' in content:
                            self.findings.append(APIFinding(
                                type="CORS with Credentials",
                                severity="MEDIUM",
                                endpoint=str(py_file),
                                description="CORS allows credentials with broad origins",
                                evidence="allow_credentials=True with potentially broad origins",
                                remediation="Ensure credentials are only allowed with specific trusted origins",
                                cwe_id="CWE-942"
                            ))
                            
            except Exception:
                continue
    
    def _audit_sql_injection(self):
        """Audit for SQL injection vulnerabilities"""
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if any(skip in str(py_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for SQL injection patterns
                    sql_patterns = [
                        (r'execute\s*\(\s*f["\'].*\%.*{.*}.*["\']', 'SQL injection via f-string'),
                        (r'execute\s*\(\s*["\'].*\+.*\+', 'SQL injection via string concatenation'),
                        (r'cursor\.execute\s*\(\s*f["\'].*{.*}.*["\']', 'SQL injection via cursor f-string'),
                        (r'cursor\.execute\s*\(\s*["\'].*\+.*\+', 'SQL injection via cursor concatenation'),
                    ]
                    
                    for pattern, description in sql_patterns:
                        if re.search(pattern, content):
                            self.findings.append(APIFinding(
                                type="SQL Injection Vulnerability",
                                severity="CRITICAL",
                                endpoint=str(py_file),
                                description=description,
                                evidence="Dynamic SQL construction found",
                                remediation="Use parameterized queries or prepared statements",
                                cwe_id="CWE-89"
                            ))
                            
            except Exception:
                continue
    
    def _test_live_endpoints(self):
        """Test live API endpoints (if available)"""
        endpoints_to_test = [
            "http://localhost:80",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://localhost:8002",
        ]
        
        for endpoint in endpoints_to_test:
            try:
                response = requests.get(endpoint, timeout=5, verify=False)
                
                # Check for missing security headers
                security_headers = [
                    'X-Content-Type-Options',
                    'X-Frame-Options',
                    'X-XSS-Protection',
                    'Strict-Transport-Security'
                ]
                
                missing_headers = []
                for header in security_headers:
                    if header not in response.headers:
                        missing_headers.append(header)
                
                if missing_headers:
                    self.findings.append(APIFinding(
                        type="Missing Security Headers",
                        severity="MEDIUM",
                        endpoint=endpoint,
                        description="Web server missing security headers",
                        evidence=f"Missing headers: {', '.join(missing_headers)}",
                        remediation="Add security headers to all HTTP responses",
                        cwe_id="CWE-116"
                    ))
                
                # Check for information disclosure
                if response.status_code == 500:
                    if any(sensitive in response.text.lower() for sensitive in ['error', 'traceback', 'exception', 'sql']):
                        self.findings.append(APIFinding(
                            type="Information Disclosure in Errors",
                            severity="MEDIUM",
                            endpoint=endpoint,
                            description="Error pages may reveal sensitive information",
                            evidence="Detailed error information in response",
                            remediation="Implement generic error pages",
                            cwe_id="CWE-209"
                        ))
                        
            except Exception:
                pass  # Service may not be running

def main():
    """Main function"""
    workspace = "/workspace"
    auditor = APISecurityAuditor(workspace)
    
    findings = auditor.audit_api_security()
    
    # Save findings
    output_file = "/workspace/security_audit/findings/api_security_report.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "scan_type": "API Security Audit",
            "total_findings": len(findings),
            "endpoints_discovered": auditor.endpoints,
            "findings": [finding.__dict__ for finding in findings]
        }, f, indent=2)
    
    print(f"✅ API security audit complete!")
    print(f"📊 Found {len(findings)} API security issues")
    print(f"📄 Report saved to {output_file}")
    print(f"🔍 Discovered {len(auditor.endpoints)} API endpoints")
    
    # Print summary
    if findings:
        print("\nKey Findings:")
        severity_counts = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        
        for severity, count in severity_counts.items():
            print(f"  {severity}: {count}")
    
    return findings

if __name__ == "__main__":
    main()
