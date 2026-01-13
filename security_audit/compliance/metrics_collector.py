#!/usr/bin/env python3
"""
Security Metrics Collection Script
Collects and reports security metrics
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path

class SecurityMetricsCollector:
    """Collects security metrics from various sources"""
    
    def __init__(self):
        self.metrics = {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def collect_vulnerability_metrics(self):
        """Collect vulnerability metrics"""
        try:
            # Read vulnerability scan results
            vuln_file = "/workspace/security_audit/findings/vulnerability_report.json"
            if Path(vuln_file).exists():
                with open(vuln_file, 'r') as f:
                    vuln_data = json.load(f)
                
                self.metrics.update({
                    "vulnerabilities_total": len(vuln_data.get("findings", [])),
                    "vulnerabilities_critical": sum(
                        1 for f in vuln_data.get("findings", []) 
                        if f.get("severity") == "CRITICAL"
                    ),
                    "vulnerabilities_high": sum(
                        1 for f in vuln_data.get("findings", []) 
                        if f.get("severity") == "HIGH"
                    ),
                    "vulnerabilities_medium": sum(
                        1 for f in vuln_data.get("findings", []) 
                        if f.get("severity") == "MEDIUM"
                    ),
                    "vulnerabilities_low": sum(
                        1 for f in vuln_data.get("findings", []) 
                        if f.get("severity") == "LOW"
                    )
                })
            else:
                # Default values if file doesn't exist
                self.metrics.update({
                    "vulnerabilities_total": 0,
                    "vulnerabilities_critical": 0,
                    "vulnerabilities_high": 0,
                    "vulnerabilities_medium": 0,
                    "vulnerabilities_low": 0
                })
        except Exception as e:
            print(f"Error collecting vulnerability metrics: {e}")
            self.metrics.update({
                "vulnerabilities_total": 0,
                "vulnerabilities_critical": 0,
                "vulnerabilities_high": 0,
                "vulnerabilities_medium": 0,
                "vulnerabilities_low": 0
            })
    
    def collect_compliance_metrics(self):
        """Collect compliance metrics"""
        try:
            # Read compliance report
            compliance_file = "/workspace/security_audit/compliance/compliance_report.json"
            if Path(compliance_file).exists():
                with open(compliance_file, 'r') as f:
                    compliance_data = json.load(f)
                
                framework_scores = compliance_data.get("framework_scores", {})
                
                self.metrics.update({
                    "compliance_owasp_score": framework_scores.get("OWASP Top 10 2021", {}).get("percentage", 0),
                    "compliance_nist_score": framework_scores.get("NIST Cybersecurity Framework", {}).get("percentage", 0),
                    "compliance_pci_score": framework_scores.get("PCI DSS", {}).get("percentage", 0),
                    "compliance_iso_score": framework_scores.get("ISO 27001", {}).get("percentage", 0),
                    "compliance_cis_score": framework_scores.get("CIS Controls", {}).get("percentage", 0)
                })
            else:
                # Default values
                self.metrics.update({
                    "compliance_owasp_score": 0,
                    "compliance_nist_score": 0,
                    "compliance_pci_score": 0,
                    "compliance_iso_score": 0,
                    "compliance_cis_score": 0
                })
        except Exception as e:
            print(f"Error collecting compliance metrics: {e}")
    
    def collect_auth_metrics(self):
        """Collect authentication metrics"""
        # Placeholder - would integrate with actual auth system
        self.metrics.update({
            "auth_failures_total": 0,
            "auth_failures_brute_force": 0,
            "auth_failures_invalid_credentials": 0,
            "active_sessions": 0,
            "mfa_adoption_rate": 0
        })
    
    def collect_api_metrics(self):
        """Collect API security metrics"""
        # Placeholder - would integrate with API gateway
        self.metrics.update({
            "api_requests_total": 0,
            "api_requests_blocked": 0,
            "api_rate_limit_violations": 0,
            "api_authorization_failures": 0
        })
    
    def collect_network_metrics(self):
        """Collect network security metrics"""
        # Placeholder - would integrate with network monitoring
        self.metrics.update({
            "network_traffic_total": 0,
            "network_traffic_blocked": 0,
            "network_intrusion_attempts": 0,
            "ddos_attempts": 0
        })
    
    def collect_incident_metrics(self):
        """Collect incident metrics"""
        # Placeholder - would integrate with incident management
        self.metrics.update({
            "security_incidents_total": 0,
            "security_incidents_critical": 0,
            "security_incidents_high": 0,
            "security_incidents_medium": 0,
            "incident_response_time_avg": 0
        })
    
    def collect_system_metrics(self):
        """Collect system health metrics"""
        # Placeholder - would integrate with system monitoring
        self.metrics.update({
            "security_controls_active": 10,
            "security_controls_failed": 0,
            "monitoring_systems_up": 5,
            "patch_compliance_rate": 85,
            "vulnerability_remediation_rate": 70
        })
    
    def collect_all_metrics(self):
        """Collect all security metrics"""
        print("Collecting security metrics...")
        
        self.collect_vulnerability_metrics()
        self.collect_compliance_metrics()
        self.collect_auth_metrics()
        self.collect_api_metrics()
        self.collect_network_metrics()
        self.collect_incident_metrics()
        self.collect_system_metrics()
        
        self.metrics["timestamp"] = self.timestamp
        
        return self.metrics
    
    def export_metrics(self, output_file=None):
        """Export metrics to JSON file"""
        if output_file is None:
            output_file = "/workspace/security_audit/compliance/security_metrics.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        print(f"Metrics exported to {output_file}")
        return self.metrics
    
    def print_dashboard(self):
        """Print metrics in dashboard format"""
        print("\n" + "="*80)
        print("SECURITY METRICS DASHBOARD")
        print("="*80)
        print(f"Timestamp: {self.timestamp}")
        print()
        
        # Vulnerability Summary
        print("VULNERABILITIES:")
        print(f"  Total: {self.metrics.get('vulnerabilities_total', 0)}")
        print(f"  Critical: {self.metrics.get('vulnerabilities_critical', 0)}")
        print(f"  High: {self.metrics.get('vulnerabilities_high', 0)}")
        print(f"  Medium: {self.metrics.get('vulnerabilities_medium', 0)}")
        print(f"  Low: {self.metrics.get('vulnerabilities_low', 0)}")
        print()
        
        # Compliance Scores
        print("COMPLIANCE SCORES:")
        print(f"  OWASP Top 10: {self.metrics.get('compliance_owasp_score', 0):.1f}%")
        print(f"  NIST Framework: {self.metrics.get('compliance_nist_score', 0):.1f}%")
        print(f"  PCI DSS: {self.metrics.get('compliance_pci_score', 0):.1f}%")
        print(f"  ISO 27001: {self.metrics.get('compliance_iso_score', 0):.1f}%")
        print()
        
        # System Health
        print("SYSTEM HEALTH:")
        print(f"  Security Controls Active: {self.metrics.get('security_controls_active', 0)}")
        print(f"  Security Controls Failed: {self.metrics.get('security_controls_failed', 0)}")
        print(f"  Monitoring Systems Up: {self.metrics.get('monitoring_systems_up', 0)}")
        print(f"  Patch Compliance: {self.metrics.get('patch_compliance_rate', 0)}%")
        print()
        
        # API Metrics
        print("API SECURITY:")
        print(f"  Total Requests: {self.metrics.get('api_requests_total', 0)}")
        print(f"  Blocked Requests: {self.metrics.get('api_requests_blocked', 0)}")
        print(f"  Rate Limit Violations: {self.metrics.get('api_rate_limit_violations', 0)}")
        print()
        
        print("="*80)

def main():
    """Main function"""
    collector = SecurityMetricsCollector()
    
    # Collect metrics
    metrics = collector.collect_all_metrics()
    
    # Export to file
    collector.export_metrics()
    
    # Print dashboard
    collector.print_dashboard()
    
    # Check for alerts
    alerts = []
    if metrics.get('vulnerabilities_critical', 0) > 0:
        alerts.append(f"CRITICAL: {metrics['vulnerabilities_critical']} critical vulnerabilities found")
    
    if metrics.get('security_incidents_critical', 0) > 0:
        alerts.append(f"CRITICAL: {metrics['security_incidents_critical']} critical incidents")
    
    if alerts:
        print("\n🚨 ALERTS:")
        for alert in alerts:
            print(f"  {alert}")
    
    return metrics

if __name__ == "__main__":
    main()
