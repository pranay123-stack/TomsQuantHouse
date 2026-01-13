#!/usr/bin/env python3
"""
Network Security Audit Tool
"""

import os
import socket
import ssl
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class NetworkFinding:
    """Network security finding"""
    severity: str
    component: str
    issue: str
    evidence: str
    recommendation: str

class NetworkSecurityAuditor:
    """Network Security Auditor"""
    
    def __init__(self):
        self.findings: List[NetworkFinding] = []
        self.open_ports: List[int] = []
        
    def audit_network_security(self) -> List[NetworkFinding]:
        """Perform network security audit"""
        print("🌐 Auditing network security...")
        
        # Port scanning
        self._scan_ports()
        
        # SSL/TLS configuration
        self._audit_ssl_config()
        
        # Docker network security
        self._audit_docker_security()
        
        # Nginx security configuration
        self._audit_nginx_security()
        
        # Firewall rules audit
        self._audit_firewall_rules()
        
        return self.findings
    
    def _scan_ports(self):
        """Scan for open ports"""
        common_ports = [22, 80, 443, 8000, 8001, 8002, 8003, 8004, 8005, 3000, 5432, 6379]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    self.open_ports.append(port)
                    service_name = self._get_service_name(port)
                    
                    # Check for insecure services
                    if port in [22, 23, 21, 25]:
                        self.findings.append(NetworkFinding(
                            severity="HIGH",
                            component=f"Port {port}",
                            issue="Potentially insecure service exposed",
                            evidence=f"Port {port} ({service_name}) is open",
                            recommendation="Ensure proper authentication and encryption for this service"
                        ))
                sock.close()
            except Exception:
                pass
    
    def _get_service_name(self, port: int) -> str:
        """Get service name for port"""
        services = {
            22: "SSH",
            80: "HTTP",
            443: "HTTPS",
            8000: "Python HTTP",
            8001: "Abacus AI",
            8002: "ASYM Edge",
            8003: "PubSub",
            8004: "Workflows",
            8005: "Security",
            3000: "Composio",
            5432: "PostgreSQL",
            6379: "Redis"
        }
        return services.get(port, "Unknown")
    
    def _audit_ssl_config(self):
        """Audit SSL/TLS configuration"""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Test SSL configuration
            with socket.create_connection(('localhost', 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname='localhost') as ssock:
                    cert = ssock.getpeercert()
                    protocol = ssock.version()
                    
                    if protocol in ['TLSv1', 'TLSv1.1']:
                        self.findings.append(NetworkFinding(
                            severity="HIGH",
                            component="SSL/TLS Configuration",
                            issue="Deprecated TLS version in use",
                            evidence=f"Using {protocol}",
                            recommendation="Upgrade to TLSv1.2 or higher"
                        ))
                    
                    # Check cipher strength
                    cipher = ssock.cipher()
                    if cipher and 'RC4' in cipher[0] or 'DES' in cipher[0]:
                        self.findings.append(NetworkFinding(
                            severity="MEDIUM",
                            component="SSL/TLS Configuration",
                            issue="Weak cipher suite in use",
                            evidence=f"Cipher: {cipher[0]}",
                            recommendation="Use strong cipher suites only"
                        ))
        except Exception:
            # HTTPS service may not be available
            pass
    
    def _audit_docker_security(self):
        """Audit Docker security configuration"""
        docker_files = list(Path("/workspace").rglob("docker-compose*.yml"))
        
        for docker_file in docker_files:
            try:
                with open(docker_file, 'r') as f:
                    content = f.read()
                    
                    # Check for privileged containers
                    if 'privileged: true' in content:
                        self.findings.append(NetworkFinding(
                            severity="HIGH",
                            component=f"Docker ({docker_file.name})",
                            issue="Privileged container configuration",
                            evidence="privileged: true found in container configuration",
                            recommendation="Avoid using privileged containers when not absolutely necessary"
                        ))
                    
                    # Check for missing user specification
                    if 'user: ' not in content and 'root' not in content:
                        self.findings.append(NetworkFinding(
                            severity="MEDIUM",
                            component=f"Docker ({docker_file.name})",
                            issue="Container running as root user",
                            evidence="No user specification found",
                            recommendation="Specify non-root user for containers"
                        ))
                    
                    # Check for network mode
                    if 'network_mode: host' in content:
                        self.findings.append(NetworkFinding(
                            severity="MEDIUM",
                            component=f"Docker ({docker_file.name})",
                            issue="Container using host network mode",
                            evidence="network_mode: host configuration found",
                            recommendation="Use bridge network mode for better isolation"
                        ))
            except Exception:
                continue
    
    def _audit_nginx_security(self):
        """Audit Nginx security configuration"""
        nginx_conf = Path("/workspace/docker/nginx/nginx.conf")
        
        if nginx_conf.exists():
            try:
                with open(nginx_conf, 'r') as f:
                    content = f.read()
                    
                    # Check security headers
                    required_headers = [
                        'X-Frame-Options',
                        'X-Content-Type-Options',
                        'X-XSS-Protection',
                        'Strict-Transport-Security'
                    ]
                    
                    for header in required_headers:
                        if header not in content:
                            self.findings.append(NetworkFinding(
                                severity="MEDIUM",
                                component="Nginx Configuration",
                                issue=f"Missing security header: {header}",
                                evidence=f"{header} not found in configuration",
                                recommendation=f"Add {header} header to Nginx configuration"
                            ))
                    
                    # Check TLS configuration
                    if 'TLSv1' in content or 'SSLv3' in content:
                        self.findings.append(NetworkFinding(
                            severity="HIGH",
                            component="Nginx Configuration",
                            issue="Deprecated SSL/TLS protocols enabled",
                            evidence="Found deprecated protocol versions",
                            recommendation="Use only TLSv1.2 and TLSv1.3"
                        ))
                    
                    # Check client body size limit
                    if 'client_max_body_size' not in content:
                        self.findings.append(NetworkFinding(
                            severity="LOW",
                            component="Nginx Configuration",
                            issue="No client body size limit configured",
                            evidence="No client_max_body_size directive found",
                            recommendation="Set reasonable client body size limits"
                        ))
            except Exception:
                pass
    
    def _audit_firewall_rules(self):
        """Audit firewall configuration"""
        try:
            # Check if iptables is available
            result = subprocess.run(['iptables', '-L'], capture_output=True, text=True)
            if result.returncode == 0:
                output = result.stdout
                
                # Check for basic protection
                if 'DROP' not in output and 'REJECT' not in output:
                    self.findings.append(NetworkFinding(
                        severity="MEDIUM",
                        component="Firewall Configuration",
                        issue="No DROP/REJECT rules found in iptables",
                        evidence="Firewall appears to have permissive rules",
                        recommendation="Implement restrictive firewall rules"
                    ))
        except Exception:
            # iptables may not be available or accessible
            pass

def main():
    """Main function"""
    auditor = NetworkSecurityAuditor()
    findings = auditor.audit_network_security()
    
    # Save findings
    output_file = "/workspace/security_audit/findings/network_security_report.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "scan_type": "Network Security Audit",
            "open_ports": auditor.open_ports,
            "total_findings": len(findings),
            "findings": [finding.__dict__ for finding in findings]
        }, f, indent=2)
    
    print(f"✅ Network security audit complete!")
    print(f"📊 Found {len(findings)} network security issues")
    print(f"🔍 Found {len(auditor.open_ports)} open ports: {auditor.open_ports}")
    print(f"📄 Report saved to {output_file}")
    
    if findings:
        print("\nKey Findings:")
        for finding in findings[:5]:
            print(f"  ⚠️  {finding.severity}: {finding.issue}")
    
    return findings

if __name__ == "__main__":
    main()
