#!/usr/bin/env python3
"""
Log Analyzer
Advanced log file analysis and pattern detection tool
"""

import os
import sys
import json
import re
import logging
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class LogAnalyzer:
    def __init__(self, log_directory: str = "/workspace/orchestration/logs"):
        self.log_directory = Path(log_directory)
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for log analyzer"""
        self.logger = logging.getLogger('LogAnalyzer')
        self.logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler(self.log_directory / 'log_analyzer.log')
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def find_log_files(self, pattern: str = "*.log") -> List[Path]:
        """Find all log files matching the pattern"""
        try:
            log_files = list(self.log_directory.rglob(pattern))
            return sorted(log_files)
        except Exception as e:
            self.logger.error(f"Error finding log files: {e}")
            return []
    
    def search_pattern(self, pattern: str, case_sensitive: bool = False) -> Dict[str, Any]:
        """Search for a specific pattern in all log files"""
        try:
            matches = []
            total_matches = 0
            file_matches = defaultdict(int)
            
            log_files = self.find_log_files()
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if case_sensitive:
                                if pattern in line:
                                    matches.append({
                                        'file': str(log_file),
                                        'line_number': line_num,
                                        'content': line.strip()
                                    })
                                    file_matches[str(log_file)] += 1
                                    total_matches += 1
                            else:
                                if pattern.lower() in line.lower():
                                    matches.append({
                                        'file': str(log_file),
                                        'line_number': line_num,
                                        'content': line.strip()
                                    })
                                    file_matches[str(log_file)] += 1
                                    total_matches += 1
                                    
                except Exception as e:
                    self.logger.warning(f"Error reading {log_file}: {e}")
            
            return {
                'pattern': pattern,
                'total_matches': total_matches,
                'files_with_matches': len(file_matches),
                'file_match_counts': dict(file_matches),
                'matches': matches[-100:]  # Last 100 matches
            }
            
        except Exception as e:
            self.logger.error(f"Error searching for pattern: {e}")
            return {'error': str(e)}
    
    def analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns across all log files"""
        try:
            error_patterns = [
                r'ERROR',
                r'Exception',
                r'Traceback',
                r'Failed',
                r'CRITICAL',
                r'FATAL'
            ]
            
            results = {}
            
            for pattern in error_patterns:
                search_result = self.search_pattern(pattern, case_sensitive=False)
                results[pattern] = {
                    'count': search_result.get('total_matches', 0),
                    'files': search_result.get('files_with_matches', 0),
                    'pattern': pattern
                }
            
            return {
                'error_analysis': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing error patterns: {e}")
            return {'error': str(e)}
    
    def analyze_performance_metrics(self) -> Dict[str, Any]:
        """Extract and analyze performance metrics from logs"""
        try:
            # Common performance metric patterns
            metric_patterns = {
                'response_time': [
                    r'response[_\s]?time[:\s]+(\d+(?:\.\d+)?)\s*ms',
                    r'rt[:\s]+(\d+(?:\.\d+)?)\s*ms',
                    r'([\d.]+)\s*ms.*response'
                ],
                'cpu_usage': [
                    r'cpu[_\s]?usage[:\s]+(\d+(?:\.\d+)?)\s*%',
                    r'cpu[:\s]+(\d+(?:\.\d+)?)\s*%'
                ],
                'memory_usage': [
                    r'memory[_\s]?usage[:\s]+(\d+(?:\.\d+)?)\s*%',
                    r'mem[:\s]+(\d+(?:\.\d+)?)\s*%'
                ],
                'disk_usage': [
                    r'disk[_\s]?usage[:\s]+(\d+(?:\.\d+)?)\s*%',
                    r'([\d.]+)%\s*disk'
                ],
                'response_code': [
                    r'HTTP[_\s]?(\d{3})',
                    r'status[_\s]?code[:\s]+(\d{3})'
                ]
            }
            
            metrics_data = defaultdict(list)
            
            log_files = self.find_log_files()
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            for metric_name, patterns in metric_patterns.items():
                                for pattern in patterns:
                                    matches = re.finditer(pattern, line, re.IGNORECASE)
                                    for match in matches:
                                        value = match.group(1)
                                        try:
                                            numeric_value = float(value)
                                            metrics_data[metric_name].append({
                                                'value': numeric_value,
                                                'source': str(log_file),
                                                'context': line.strip()[:200]  # First 200 chars
                                            })
                                        except ValueError:
                                            pass  # Skip non-numeric values
                                            
                except Exception as e:
                    self.logger.warning(f"Error processing {log_file}: {e}")
            
            # Calculate statistics for each metric
            stats = {}
            for metric_name, values in metrics_data.items():
                if values:
                    numeric_values = [v['value'] for v in values]
                    stats[metric_name] = {
                        'count': len(numeric_values),
                        'min': min(numeric_values),
                        'max': max(numeric_values),
                        'avg': sum(numeric_values) / len(numeric_values),
                        'recent_samples': values[-10:],  # Last 10 samples
                        'sources': len(set(v['source'] for v in values))
                    }
                else:
                    stats[metric_name] = {'count': 0}
            
            return {
                'performance_metrics': stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing performance metrics: {e}")
            return {'error': str(e)}
    
    def analyze_log_frequency(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Analyze log frequency over time"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            
            # Pattern for extracting timestamp from log lines
            timestamp_patterns = [
                r'(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})',  # ISO format
                r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',     # Standard format
                r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})'     # US format
            ]
            
            hourly_counts = defaultdict(int)
            daily_counts = defaultdict(int)
            total_lines = 0
            
            log_files = self.find_log_files()
            
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            total_lines += 1
                            
                            # Try to extract timestamp
                            for pattern in timestamp_patterns:
                                match = re.search(pattern, line)
                                if match:
                                    try:
                                        timestamp_str = match.group(1)
                                        
                                        # Try different timestamp parsing methods
                                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %H:%M:%S']:
                                            try:
                                                timestamp = datetime.strptime(timestamp_str, fmt)
                                                if timestamp >= cutoff_time:
                                                    hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                                                    daily_key = timestamp.strftime('%Y-%m-%d')
                                                    hourly_counts[hour_key] += 1
                                                    daily_counts[daily_key] += 1
                                                break
                                            except ValueError:
                                                continue
                                    except Exception:
                                        pass
                                    break
                                    
                except Exception as e:
                    self.logger.warning(f"Error processing {log_file}: {e}")
            
            return {
                'time_window_hours': time_window_hours,
                'total_log_lines': total_lines,
                'hourly_distribution': dict(hourly_counts),
                'daily_distribution': dict(daily_counts),
                'total_hours_with_activity': len(hourly_counts),
                'avg_lines_per_hour': sum(hourly_counts.values()) / max(len(hourly_counts), 1),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing log frequency: {e}")
            return {'error': str(e)}
    
    def detect_anomalies(self) -> Dict[str, Any]:
        """Detect anomalies in log patterns"""
        try:
            anomalies = []
            
            # Check for sudden spikes in error rates
            error_analysis = self.analyze_error_patterns()
            error_data = error_analysis.get('error_analysis', {})
            
            total_errors = sum(data.get('count', 0) for data in error_data.values())
            
            if total_errors > 100:  # Threshold for anomaly
                anomalies.append({
                    'type': 'high_error_rate',
                    'severity': 'high',
                    'description': f'High error count detected: {total_errors} errors',
                    'count': total_errors
                })
            
            # Check for large log files
            log_files = self.find_log_files()
            for log_file in log_files:
                file_size_mb = log_file.stat().st_size / (1024 * 1024)
                if file_size_mb > 100:  # Files larger than 100MB
                    anomalies.append({
                        'type': 'large_log_file',
                        'severity': 'medium',
                        'description': f'Large log file detected: {log_file.name} ({file_size_mb:.1f}MB)',
                        'file': str(log_file),
                        'size_mb': file_size_mb
                    })
            
            # Check for recent errors
            recent_errors = self.search_pattern('ERROR', case_sensitive=False)
            if recent_errors.get('total_matches', 0) > 10:
                anomalies.append({
                    'type': 'recent_error_spike',
                    'severity': 'high',
                    'description': f'Recent error spike: {recent_errors["total_matches"]} errors',
                    'count': recent_errors['total_matches']
                })
            
            return {
                'anomalies': anomalies,
                'total_anomalies': len(anomalies),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {e}")
            return {'error': str(e)}
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive log analysis summary"""
        try:
            log_files = self.find_log_files()
            total_size = sum(f.stat().st_size for f in log_files if f.is_file())
            
            # Run all analyses
            error_analysis = self.analyze_error_patterns()
            performance_analysis = self.analyze_performance_metrics()
            frequency_analysis = self.analyze_log_frequency()
            anomaly_analysis = self.detect_anomalies()
            
            # Calculate overall health score
            total_errors = sum(data.get('count', 0) for data in error_analysis.get('error_analysis', {}).values())
            total_anomalies = anomaly_analysis.get('total_anomalies', 0)
            
            # Simple health scoring
            if total_errors == 0 and total_anomalies == 0:
                health_score = 100
                health_status = 'excellent'
            elif total_errors < 10 and total_anomalies < 3:
                health_score = 85
                health_status = 'good'
            elif total_errors < 50 and total_anomalies < 5:
                health_score = 70
                health_status = 'fair'
            else:
                health_score = 50
                health_status = 'poor'
            
            return {
                'summary': {
                    'total_log_files': len(log_files),
                    'total_size_mb': total_size / (1024 * 1024),
                    'health_score': health_score,
                    'health_status': health_status,
                    'total_errors': total_errors,
                    'total_anomalies': total_anomalies
                },
                'error_analysis': error_analysis,
                'performance_analysis': performance_analysis,
                'frequency_analysis': frequency_analysis,
                'anomaly_analysis': anomaly_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            return {'error': str(e)}
    
    def export_analysis(self, output_file: str = None) -> str:
        """Export analysis results to file"""
        try:
            report = self.generate_summary_report()
            
            if not output_file:
                output_file = self.log_directory / f"log_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                output_file = Path(output_file)
            
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Analysis exported to {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Error exporting analysis: {e}")
            return ""

def main():
    """Main entry point for log analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Log Analysis Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for pattern in logs')
    search_parser.add_argument('pattern', help='Pattern to search for')
    search_parser.add_argument('--case-sensitive', action='store_true', help='Case sensitive search')
    
    # Error analysis command
    error_parser = subparsers.add_parser('errors', help='Analyze error patterns')
    
    # Performance analysis command
    perf_parser = subparsers.add_parser('performance', help='Analyze performance metrics')
    
    # Frequency analysis command
    freq_parser = subparsers.add_parser('frequency', help='Analyze log frequency')
    freq_parser.add_argument('--hours', type=int, default=24, help='Time window in hours')
    
    # Anomaly detection command
    anomaly_parser = subparsers.add_parser('anomalies', help='Detect anomalies')
    
    # Summary report command
    summary_parser = subparsers.add_parser('summary', help='Generate summary report')
    summary_parser.add_argument('--export', help='Export to file')
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer()
    
    if args.command == 'search':
        result = analyzer.search_pattern(args.pattern, args.case_sensitive)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'errors':
        result = analyzer.analyze_error_patterns()
        print(json.dumps(result, indent=2))
    
    elif args.command == 'performance':
        result = analyzer.analyze_performance_metrics()
        print(json.dumps(result, indent=2))
    
    elif args.command == 'frequency':
        result = analyzer.analyze_log_frequency(args.hours)
        print(json.dumps(result, indent=2))
    
    elif args.command == 'anomalies':
        result = analyzer.detect_anomalies()
        print(json.dumps(result, indent=2))
    
    elif args.command == 'summary':
        if args.export:
            output_file = analyzer.export_analysis(args.export)
            print(f"Analysis exported to: {output_file}")
        else:
            result = analyzer.generate_summary_report()
            print(json.dumps(result, indent=2))
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()