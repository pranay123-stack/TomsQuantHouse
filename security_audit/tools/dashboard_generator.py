#!/usr/bin/env python3
"""
Security Metrics Dashboard Generator
Generates visual dashboards for ongoing security monitoring
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

def generate_metrics_dashboard():
    """Generate security metrics dashboard configuration"""
    
    dashboard_config = {
        "dashboard": {
            "title": "Security Metrics Dashboard",
            "refresh_interval": "30s",
            "time_range": "24h",
            "panels": [
                {
                    "title": "Vulnerability Summary",
                    "type": "stat",
                    "targets": [
                        {"query": "vulnerabilities_total", "legend": "Total Vulnerabilities"},
                        {"query": "vulnerabilities_critical", "legend": "Critical"},
                        {"query": "vulnerabilities_high", "legend": "High"},
                        {"query": "vulnerabilities_medium", "legend": "Medium"},
                        {"query": "vulnerabilities_low", "legend": "Low"}
                    ]
                },
                {
                    "title": "Security Incidents (Last 30 Days)",
                    "type": "graph",
                    "targets": [
                        {"query": "security_incidents_total", "legend": "Total Incidents"},
                        {"query": "security_incidents_critical", "legend": "Critical"},
                        {"query": "security_incidents_high", "legend": "High"},
                        {"query": "security_incidents_medium", "legend": "Medium"}
                    ]
                },
                {
                    "title": "Authentication Failures",
                    "type": "graph",
                    "targets": [
                        {"query": "auth_failures_total", "legend": "Total Failures"},
                        {"query": "auth_failures_brute_force", "legend": "Brute Force"},
                        {"query": "auth_failures_invalid_credentials", "legend": "Invalid Credentials"}
                    ]
                },
                {
                    "title": "API Security Metrics",
                    "type": "stat",
                    "targets": [
                        {"query": "api_requests_total", "legend": "Total Requests"},
                        {"query": "api_requests_blocked", "legend": "Blocked Requests"},
                        {"query": "api_rate_limit_violations", "legend": "Rate Limit Violations"}
                    ]
                },
                {
                    "title": "Network Security",
                    "type": "graph",
                    "targets": [
                        {"query": "network_traffic_total", "legend": "Total Traffic (GB)"},
                        {"query": "network_traffic_blocked", "legend": "Blocked Traffic"},
                        {"query": "network_intrusion_attempts", "legend": "Intrusion Attempts"}
                    ]
                },
                {
                    "title": "Compliance Status",
                    "type": "table",
                    "targets": [
                        {"query": "compliance_owasp_score", "legend": "OWASP Score"},
                        {"query": "compliance_nist_score", "legend": "NIST Score"},
                        {"query": "compliance_pci_score", "legend": "PCI DSS Score"},
                        {"query": "compliance_iso_score", "legend": "ISO 27001 Score"}
                    ]
                },
                {
                    "title": "System Health",
                    "type": "stat",
                    "targets": [
                        {"query": "security_controls_active", "legend": "Active Controls"},
                        {"query": "security_controls_failed", "legend": "Failed Controls"},
                        {"query": "monitoring_systems_up", "legend": "Monitoring Systems Up"}
                    ]
                },
                {
                    "title": "Response Time Metrics",
                    "type": "graph",
                    "targets": [
                        {"query": "incident_response_time_avg", "legend": "Avg Response Time (min)"},
                        {"query": "vulnerability_remediation_time_avg", "legend": "Avg Remediation Time (hrs)"},
                        {"query": "patch_deployment_time_avg", "legend": "Avg Patch Time (hrs)"}
                    ]
                }
            ]
        },
        "alerts": [
            {
                "name": "Critical Vulnerability Detected",
                "condition": "vulnerabilities_critical > 0",
                "severity": "critical",
                "message": "Critical vulnerability detected requiring immediate attention"
            },
            {
                "name": "High Number of Failed Logins",
                "condition": "auth_failures_brute_force > 10",
                "severity": "warning",
                "message": "Possible brute force attack detected"
            },
            {
                "name": "Security Incident",
                "condition": "security_incidents_critical > 0",
                "severity": "critical",
                "message": "Critical security incident detected"
            },
            {
                "name": "API Abuse Detected",
                "condition": "api_rate_limit_violations > 100",
                "severity": "warning",
                "message": "API rate limit violations exceeding threshold"
            },
            {
                "name": "Network Intrusion Attempt",
                "condition": "network_intrusion_attempts > 5",
                "severity": "warning",
                "message": "Multiple network intrusion attempts detected"
            }
        ],
        "kpis": [
            {
                "name": "Mean Time to Detection (MTTD)",
                "target": "< 1 hour",
                "current": "TBD",
                "unit": "hours"
            },
            {
                "name": "Mean Time to Response (MTTR)",
                "target": "< 2 hours",
                "current": "TBD",
                "unit": "hours"
            },
            {
                "name": "Mean Time to Remediation (MTTR)",
                "target": "< 24 hours",
                "current": "TBD",
                "unit": "hours"
            },
            {
                "name": "Patch Compliance Rate",
                "target": "> 95%",
                "current": "TBD",
                "unit": "percentage"
            },
            {
                "name": "Security Training Completion",
                "target": "100%",
                "current": "TBD",
                "unit": "percentage"
            },
            {
                "name": "Vulnerability Remediation Rate",
                "target": "> 90%",
                "current": "TBD",
                "unit": "percentage"
            }
        ]
    }
    
    # Save dashboard configuration
    output_file = "/workspace/security_audit/compliance/security_dashboard.json"
    with open(output_file, 'w') as f:
        json.dump(dashboard_config, f, indent=2)
    
    print(f"📊 Security metrics dashboard saved to {output_file}")
    return dashboard_config

def generate_monitoring_config():
    """Generate security monitoring configuration"""
    
    monitoring_config = {
        "monitoring": {
            "siem": {
                "tool": "ELK Stack",
                "version": "8.x",
                "retention": "90 days",
                "index_pattern": "security-*",
                "alerts": {
                    "failed_logins": {
                        "threshold": 5,
                        "window": "5m",
                        "severity": "warning"
                    },
                    "privilege_escalation": {
                        "threshold": 1,
                        "window": "1m",
                        "severity": "critical"
                    },
                    "data_exfiltration": {
                        "threshold": "100MB",
                        "window": "1m",
                        "severity": "critical"
                    },
                    "malware_detection": {
                        "threshold": 1,
                        "window": "1m",
                        "severity": "critical"
                    }
                }
            },
            "log_aggregation": {
                "tool": "Fluentd",
                "sources": [
                    "application_logs",
                    "security_logs",
                    "audit_logs",
                    "network_logs",
                    "system_logs"
                ],
                "destinations": [
                    "elasticsearch",
                    "s3_archive"
                ]
            },
            "metrics_collection": {
                "tool": "Prometheus",
                "targets": [
                    "security_controls",
                    "vulnerability_scanners",
                    "authentication_servers",
                    "api_gateways",
                    "network_devices"
                ],
                "retention": "30 days"
            },
            "alerting": {
                "tool": "AlertManager",
                "channels": [
                    {
                        "type": "email",
                        "address": "security-team@company.com",
                        "severities": ["critical", "warning"]
                    },
                    {
                        "type": "slack",
                        "webhook": "${SLACK_WEBHOOK}",
                        "severities": ["critical"]
                    },
                    {
                        "type": "pagerduty",
                        "service_key": "${PAGERDUTY_KEY}",
                        "severities": ["critical"]
                    }
                ]
            },
            "visualization": {
                "tool": "Grafana",
                "dashboards": [
                    "security-overview",
                    "vulnerability-status",
                    "incident-timeline",
                    "compliance-metrics",
                    "threat-intelligence"
                ]
            }
        }
    }
    
    # Save monitoring configuration
    output_file = "/workspace/security_audit/compliance/monitoring_config.json"
    with open(output_file, 'w') as f:
        json.dump(monitoring_config, f, indent=2)
    
    print(f"📡 Monitoring configuration saved to {output_file}")
    return monitoring_config

def generate_security_metrics_script():
    """Generate script for collecting security metrics"""
    
    script_content = '''#!/usr/bin/env python3
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
        print("\\n" + "="*80)
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
        print("\\n🚨 ALERTS:")
        for alert in alerts:
            print(f"  {alert}")
    
    return metrics

if __name__ == "__main__":
    main()
'''
    
    # Save metrics collection script
    output_file = "/workspace/security_audit/compliance/metrics_collector.py"
    with open(output_file, 'w') as f:
        f.write(script_content)
    
    print(f"📊 Metrics collection script saved to {output_file}")
    return output_file

def main():
    """Generate all security dashboard components"""
    print("🔧 Generating security metrics dashboard components...")
    
    # Generate dashboard configuration
    dashboard_config = generate_metrics_dashboard()
    
    # Generate monitoring configuration
    monitoring_config = generate_monitoring_config()
    
    # Generate metrics collection script
    script_file = generate_security_metrics_script()
    
    # Make script executable
    os.chmod(script_file, 0o755)
    
    print("\n✅ Security dashboard components generated successfully!")
    print("\n📋 Generated Files:")
    print("  - Dashboard Config: /workspace/security_audit/compliance/security_dashboard.json")
    print("  - Monitoring Config: /workspace/security_audit/compliance/monitoring_config.json")
    print("  - Metrics Script: /workspace/security_audit/compliance/metrics_collector.py")
    
    print("\n🚀 To use:")
    print("  1. Deploy dashboard to Grafana")
    print("  2. Configure monitoring stack (Prometheus + AlertManager)")
    print("  3. Run metrics collection: python /workspace/security_audit/compliance/metrics_collector.py")

if __name__ == "__main__":
    main()
