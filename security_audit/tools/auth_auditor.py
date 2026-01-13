#!/usr/bin/env python3
"""
Security Audit Tool - Authentication and Authorization Assessment
"""

import os
import re
import json
import bcrypt
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class AuthFinding:
    """Authentication and authorization finding"""
    type: str
    severity: str
    description: str
    component: str
    evidence: str
    recommendation: str
    cwe_id: Optional[str] = None

class AuthSecurityAuditor:
    """Authentication and Authorization Security Auditor"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.findings: List[AuthFinding] = []
        
    def audit_authentication(self) -> List[AuthFinding]:
        """Audit authentication mechanisms"""
        print("🔐 Auditing authentication mechanisms...")
        
        # JWT Security Audit
        self._audit_jwt_implementation()
        
        # Password Security Audit
        self._audit_password_security()
        
        # Session Management Audit
        self._audit_session_management()
        
        # API Key Security Audit
        self._audit_api_key_security()
        
        return self.findings
    
    def _audit_jwt_implementation(self):
        """Audit JWT token implementation"""
        jwt_files = list(self.workspace_path.rglob("*jwt*")) + list(self.workspace_path.rglob("*security*"))
        
        for jwt_file in jwt_files:
            try:
                with open(jwt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for weak JWT algorithms
                    if '"alg": "none"' in content or "'alg': 'none'" in content:
                        self.findings.append(AuthFinding(
                            type="JWT Algorithm Vulnerability",
                            severity="CRITICAL",
                            description="JWT allows 'none' algorithm which is insecure",
                            component=str(jwt_file),
                            evidence="Found 'none' algorithm configuration",
                            recommendation="Remove 'none' algorithm and use only HS256 or RS256",
                            cwe_id="CWE-347"
                        ))
                    
                    # Check for weak secret key
                    if re.search(r'(secret|key)["\']?\s*[:=]\s*["\']?["\']?\s*(?!.*(?:random|token|hash))', content, re.IGNORECASE):
                        if any(weak in content.lower() for weak in ['secret', 'password', 'key', '123', 'abc']):
                            self.findings.append(AuthFinding(
                                type="Weak JWT Secret",
                                severity="HIGH",
                                description="JWT secret key appears to be weak or hardcoded",
                                component=str(jwt_file),
                                evidence="Weak or hardcoded secret found",
                                recommendation="Use strong, randomly generated secret keys",
                                cwe_id="CWE-521"
                            ))
                    
                    # Check for missing expiration
                    if 'exp' not in content and 'expiry' not in content and 'expire' not in content:
                        self.findings.append(AuthFinding(
                            type="Missing Token Expiration",
                            severity="MEDIUM",
                            description="JWT tokens may not have expiration time",
                            component=str(jwt_file),
                            evidence="No expiration logic found",
                            recommendation="Implement token expiration for all JWT tokens",
                            cwe_id="CWE-613"
                        ))
                        
            except Exception:
                continue
    
    def _audit_password_security(self):
        """Audit password handling and storage"""
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if "test" in str(py_file).lower() or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for plaintext password storage
                    if re.search(r'(password|passwd)\s*[=:]\s*["\'][^"\']+["\']', content, re.IGNORECASE):
                        self.findings.append(AuthFinding(
                            type="Plaintext Password",
                            severity="CRITICAL",
                            description="Password stored in plaintext",
                            component=str(py_file),
                            evidence="Plaintext password found in code",
                            recommendation="Never store passwords in plaintext; use secure hashing",
                            cwe_id="CWE-256"
                        ))
                    
                    # Check for weak password hashing
                    if 'md5' in content.lower():
                        self.findings.append(AuthFinding(
                            type="Weak Password Hash",
                            severity="HIGH",
                            description="MD5 is being used for password hashing",
                            component=str(py_file),
                            evidence="MD5 hash function found",
                            recommendation="Use bcrypt, scrypt, or Argon2 for password hashing",
                            cwe_id="CWE-327"
                        ))
                    
                    # Check for missing salt
                    if 'salt' not in content.lower() and ('hash' in content.lower() or 'bcrypt' in content.lower()):
                        self.findings.append(AuthFinding(
                            type="Missing Password Salt",
                            severity="MEDIUM",
                            description="Password hashing without salt",
                            component=str(py_file),
                            evidence="No salt usage detected",
                            recommendation="Always use unique salts for password hashing",
                            cwe_id="CWE-759"
                        ))
                        
            except Exception:
                continue
    
    def _audit_session_management(self):
        """Audit session management security"""
        # Check for session security issues
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if "test" in str(py_file).lower() or "__pycache__" in str(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for insecure session configuration
                    if 'session' in content.lower():
                        if 'secure' not in content.lower() and 'httponly' not in content.lower():
                            self.findings.append(AuthFinding(
                                type="Insecure Session Configuration",
                                severity="MEDIUM",
                                description="Session cookies may not have secure flags",
                                component=str(py_file),
                                evidence="Session usage without secure flag configuration",
                                recommendation="Set Secure, HttpOnly, and SameSite flags on session cookies",
                                cwe_id="CWE-614"
                            ))
                        
                        # Check for long session timeouts
                        if re.search(r'timeout.*[>](24\s*hours|7\s*days|30\s*days)', content, re.IGNORECASE):
                            self.findings.append(AuthFinding(
                                type="Excessive Session Timeout",
                                severity="LOW",
                                description="Session timeout may be too long",
                                component=str(py_file),
                                evidence=f"Long session timeout found: {re.search(r'timeout.*(\d+\s*(?:hours|days))', content, re.IGNORECASE).group() if re.search(r'timeout.*\d+\s*(?:hours|days)', content, re.IGNORECASE) else 'long timeout'}",
                                recommendation="Implement reasonable session timeouts (30 minutes for sensitive applications)",
                                cwe_id="CWE-613"
                            ))
                            
            except Exception:
                continue
    
    def _audit_api_key_security(self):
        """Audit API key management"""
        # Check for API key security issues
        all_files = list(self.workspace_path.rglob("*"))
        
        for file_path in all_files:
            if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.env', '.yaml', '.yml', '.json']:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # Check for exposed API keys
                        api_key_patterns = [
                            r'(?i)(api[_-]?key|apikey|api-key)\s*[:=]\s*["\']?([a-zA-Z0-9]{20,})',
                            r'(?i)(secret[_-]?key|secret)\s*[:=]\s*["\']?([a-zA-Z0-9]{20,})',
                            r'(?i)(access[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9]{20,})',
                        ]
                        
                        for pattern in api_key_patterns:
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                # Skip obvious placeholders
                                if not any(placeholder in match.group(2).lower() for placeholder in ['your', 'change', 'placeholder', 'example']):
                                    self.findings.append(AuthFinding(
                                        type="Exposed API Key",
                                        severity="HIGH",
                                        description="API key or secret token may be exposed",
                                        component=str(file_path),
                                        evidence=f"Found potential key: {match.group(0)[:50]}...",
                                        recommendation="Move API keys to secure configuration management and rotate exposed keys",
                                        cwe_id="CWE-798"
                                    ))
                                    
                except Exception:
                    continue

def main():
    """Main function"""
    workspace = "/workspace"
    auditor = AuthSecurityAuditor(workspace)
    
    findings = auditor.audit_authentication()
    
    # Save findings
    output_file = "/workspace/security_audit/findings/auth_security_report.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "scan_type": "Authentication & Authorization Security",
            "total_findings": len(findings),
            "findings": [finding.__dict__ for finding in findings]
        }, f, indent=2)
    
    print(f"✅ Authentication security audit complete!")
    print(f"📊 Found {len(findings)} authentication/security issues")
    print(f"📄 Report saved to {output_file}")
    
    # Print summary
    if findings:
        print("\nKey Findings:")
        for finding in findings[:5]:  # Show top 5
            print(f"  ⚠️  {finding.severity}: {finding.type}")
            print(f"      {finding.description}")
            print()
    
    return findings

if __name__ == "__main__":
    main()
