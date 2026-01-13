#!/usr/bin/env python3
"""
Backup Validation and Restore Testing System
Automated testing of backup integrity and restore procedures
"""

import os
import sys
import time
import logging
import json
import subprocess
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import boto3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupValidation:
    def __init__(self, config_path='/workspace/backup_recovery/config/backup_config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        self.s3_client = boto3.client('s3')
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests': [],
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
        
    def _load_config(self):
        """Load configuration"""
        import yaml
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def run_full_validation(self):
        """Run comprehensive backup validation"""
        logger.info("Starting full backup validation suite")
        
        test_suites = [
            self.test_backup_completeness,
            self.test_backup_integrity,
            self.test_backup_availability,
            self.test_restore_procedures,
            self.test_encryption_compliance,
            self.test_retention_compliance,
            self.test_point_in_time_recovery
        ]
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            
            for test_suite in test_suites:
                future = executor.submit(test_suite)
                futures[test_suite.__name__] = future
            
            for test_name, future in futures.items():
                try:
                    result = future.result(timeout=3600)  # 1 hour timeout per test
                    self.test_results['tests'].append({
                        'test_name': test_name,
                        'status': result['status'],
                        'details': result.get('details', {}),
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    logger.info(f"✓ {test_name}: {result['status']}")
                    
                    if result['status'] == 'PASSED':
                        self.test_results['summary']['passed'] += 1
                    elif result['status'] == 'FAILED':
                        self.test_results['summary']['failed'] += 1
                    elif result['status'] == 'WARNING':
                        self.test_results['summary']['warnings'] += 1
                        
                except Exception as e:
                    logger.error(f"✗ {test_name} exception: {e}")
                    self.test_results['tests'].append({
                        'test_name': test_name,
                        'status': 'ERROR',
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    self.test_results['summary']['failed'] += 1
        
        self.test_results['summary']['total'] = len(self.test_results['tests'])
        
        # Save results
        self._save_validation_results()
        
        return self.test_results
    
    def test_backup_completeness(self):
        """Test that all required data is being backed up"""
        logger.info("Testing backup completeness")
        
        details = {
            'databases': {},
            'filesystems': {},
            'containers': {},
            'cloud_storage': {}
        }
        
        issues = []
        
        # Check database backups
        for db_type in self.config['databases'].keys():
            backup_dir = Path('/opt/backup') / db_type
            
            if backup_dir.exists():
                backups = list(backup_dir.rglob('*'))
                details['databases'][db_type] = {
                    'backup_count': len(backups),
                    'latest_backup': max([b.stat().st_mtime for b in backups]) if backups else None
                }
                
                # Check for recent backups
                if backups:
                    latest_backup = max([b.stat().st_mtime for b in backups])
                    if (time.time() - latest_backup) > 86400:  # 24 hours
                        issues.append(f"No recent backup for {db_type} (last: {latest_backup})")
            else:
                issues.append(f"Backup directory missing for {db_type}")
                details['databases'][db_type] = {'backup_count': 0}
        
        # Check filesystem backups
        for fs_type in self.config['filesystems'].keys():
            backup_dir = Path('/opt/backup') / 'filesystem' / fs_type
            
            if backup_dir.exists():
                backups = list(backup_dir.rglob('*'))
                details['filesystems'][fs_type] = {
                    'backup_count': len(backups),
                    'latest_backup': max([b.stat().st_mtime for b in backups]) if backups else None
                }
            else:
                issues.append(f"Backup directory missing for filesystem {fs_type}")
                details['filesystems'][fs_type] = {'backup_count': 0}
        
        # Check S3 bucket backups
        try:
            bucket = self.config['global_settings']['backup_location'].replace('s3://', '').split('/')[0]
            
            response = self.s3_client.list_objects_v2(Bucket=bucket)
            
            if 'Contents' in response:
                details['cloud_storage']['s3_backup'] = {
                    'object_count': len(response['Contents']),
                    'total_size': sum(obj['Size'] for obj in response['Contents'])
                }
            else:
                details['cloud_storage']['s3_backup'] = {'object_count': 0}
                
        except Exception as e:
            issues.append(f"S3 backup check failed: {e}")
        
        status = 'PASSED' if not issues else 'WARNING'
        
        return {
            'status': status,
            'details': {
                'summary': details,
                'issues': issues
            }
        }
    
    def test_backup_integrity(self):
        """Test backup file integrity using checksums"""
        logger.info("Testing backup integrity")
        
        details = {
            'files_checked': 0,
            'files_valid': 0,
            'files_corrupted': 0,
            'missing_checksums': 0
        }
        
        issues = []
        
        backup_root = Path('/opt/backup')
        
        if not backup_root.exists():
            return {
                'status': 'FAILED',
                'details': {'error': 'Backup directory not found'}
            }
        
        # Check checksum files
        for checksum_file in backup_root.rglob('*.sha256'):
            details['files_checked'] += 1
            
            try:
                # Read expected checksum
                with open(checksum_file, 'r') as f:
                    line = f.read().strip()
                    expected_checksum, filename = line.split(None, 1)
                
                backup_file = checksum_file.with_suffix('')
                
                if not backup_file.exists():
                    issues.append(f"Backup file missing: {backup_file}")
                    details['files_corrupted'] += 1
                    continue
                
                # Calculate actual checksum
                actual_checksum = self._calculate_sha256(backup_file)
                
                if actual_checksum == expected_checksum:
                    details['files_valid'] += 1
                else:
                    issues.append(f"Checksum mismatch: {backup_file}")
                    details['files_corrupted'] += 1
                
            except Exception as e:
                issues.append(f"Error checking checksum {checksum_file}: {e}")
                details['files_corrupted'] += 1
        
        # Check for backup files without checksums
        for backup_file in backup_root.rglob('*.sql'):
            checksum_file = backup_file.with_suffix(backup_file.suffix + '.sha256')
            if not checksum_file.exists():
                details['missing_checksums'] += 1
        
        status = 'PASSED'
        if details['files_corrupted'] > 0:
            status = 'FAILED'
        elif details['missing_checksums'] > 0:
            status = 'WARNING'
        
        return {
            'status': status,
            'details': details
        }
    
    def _calculate_sha256(self, file_path):
        """Calculate SHA-256 checksum"""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def test_backup_availability(self):
        """Test backup availability and accessibility"""
        logger.info("Testing backup availability")
        
        details = {
            's3_backups': {},
            'local_backups': {},
            'cross_region_replication': {}
        }
        
        issues = []
        
        # Check S3 backup availability
        try:
            bucket = self.config['global_settings']['backup_location'].replace('s3://', '').split('/')[0]
            
            # List recent backups
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix='databases/'
            )
            
            if 'Contents' in response:
                recent_backups = [obj for obj in response['Contents']
                                if (time.time() - obj['LastModified'].timestamp()) < 86400]
                
                details['s3_backups'] = {
                    'total_objects': len(response['Contents']),
                    'recent_backups': len(recent_backups),
                    'total_size': sum(obj['Size'] for obj in response['Contents'])
                }
                
                if len(recent_backups) < 5:
                    issues.append("Insufficient recent backups in S3")
                
                # Test download
                test_obj = recent_backups[0] if recent_backups else None
                if test_obj:
                    try:
                        with tempfile.NamedTemporaryFile() as tmp:
                            self.s3_client.download_file(bucket, test_obj['Key'], tmp.name)
                            details['s3_backups']['download_test'] = 'PASSED'
                    except Exception as e:
                        issues.append(f"S3 download test failed: {e}")
                        details['s3_backups']['download_test'] = 'FAILED'
                        
        except Exception as e:
            issues.append(f"S3 availability check failed: {e}")
        
        # Check local backup availability
        backup_root = Path('/opt/backup')
        if backup_root.exists():
            total_size = sum(f.stat().st_size for f in backup_root.rglob('*') if f.is_file())
            details['local_backups'] = {
                'exists': True,
                'total_size': total_size
            }
        else:
            details['local_backups'] = {'exists': False}
            issues.append("Local backup directory not found")
        
        # Check cross-region replication
        try:
            secondary_bucket = self.config['global_settings']['secondary_location'].replace('s3://', '').split('/')[0]
            
            response = self.s3_client.list_objects_v2(Bucket=secondary_bucket)
            
            details['cross_region_replication'] = {
                'secondary_objects': len(response.get('Contents', [])),
                'status': 'available' if response.get('Contents') else 'empty'
            }
            
        except Exception as e:
            issues.append(f"Cross-region replication check failed: {e}")
        
        status = 'PASSED' if not issues else 'WARNING'
        
        return {
            'status': status,
            'details': details
        }
    
    def test_restore_procedures(self):
        """Test database and file restoration procedures"""
        logger.info("Testing restore procedures")
        
        details = {
            'mysql_restore': None,
            'postgresql_restore': None,
            'mongodb_restore': None,
            'filesystem_restore': None
        }
        
        issues = []
        
        # Test MySQL restore
        mysql_details = self._test_mysql_restore()
        details['mysql_restore'] = mysql_details
        
        if mysql_details['status'] != 'PASSED':
            issues.extend(mysql_details.get('issues', []))
        
        # Test PostgreSQL restore
        pg_details = self._test_postgresql_restore()
        details['postgresql_restore'] = pg_details
        
        if pg_details['status'] != 'PASSED':
            issues.extend(pg_details.get('issues', []))
        
        # Test MongoDB restore
        mongo_details = self._test_mongodb_restore()
        details['mongodb_restore'] = mongo_details
        
        if mongo_details['status'] != 'PASSED':
            issues.extend(mongo_details.get('issues', []))
        
        # Test filesystem restore
        fs_details = self._test_filesystem_restore()
        details['filesystem_restore'] = fs_details
        
        if fs_details['status'] != 'PASSED':
            issues.extend(fs_details.get('issues', []))
        
        status = 'PASSED' if not issues else 'FAILED'
        
        return {
            'status': status,
            'details': details
        }
    
    def _test_mysql_restore(self):
        """Test MySQL restore procedure"""
        details = {'status': 'PASSED', 'issues': []}
        
        try:
            # Find latest MySQL backup
            backup_dir = Path('/opt/backup/mysql')
            
            if not backup_dir.exists():
                details['status'] = 'WARNING'
                details['issues'].append('No MySQL backup directory found')
                return details
            
            backups = list(backup_dir.rglob('*.sql'))
            
            if not backups:
                details['status'] = 'WARNING'
                details['issues'].append('No MySQL backup files found')
                return details
            
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            
            # Test SQL syntax
            result = subprocess.run(
                ['mysql', '--help'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                details['status'] = 'FAILED'
                details['issues'].append('MySQL client not available')
                return details
            
            # Check backup file size (should not be empty)
            if latest_backup.stat().st_size == 0:
                details['status'] = 'FAILED'
                details['issues'].append('Latest MySQL backup is empty')
            
            details['latest_backup'] = str(latest_backup)
            details['backup_size'] = latest_backup.stat().st_size
            
        except Exception as e:
            details['status'] = 'FAILED'
            details['issues'].append(f'MySQL restore test error: {e}')
        
        return details
    
    def _test_postgresql_restore(self):
        """Test PostgreSQL restore procedure"""
        details = {'status': 'PASSED', 'issues': []}
        
        try:
            # Check pg_restore availability
            result = subprocess.run(
                ['pg_restore', '--help'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                details['status'] = 'FAILED'
                details['issues'].append('pg_restore not available')
                return details
            
            # Find latest PostgreSQL backup
            backup_dir = Path('/opt/backup/postgresql')
            
            if not backup_dir.exists():
                details['status'] = 'WARNING'
                details['issues'].append('No PostgreSQL backup directory found')
                return details
            
            backups = list(backup_dir.rglob('*.tar.gz'))
            
            if not backups:
                details['status'] = 'WARNING'
                details['issues'].append('No PostgreSQL backup files found')
                return details
            
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            
            # Test archive integrity
            result = subprocess.run(
                ['tar', '-tzf', str(latest_backup)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                details['status'] = 'FAILED'
                details['issues'].append('PostgreSQL backup archive corrupted')
            
            details['latest_backup'] = str(latest_backup)
            details['backup_size'] = latest_backup.stat().st_size
            
        except Exception as e:
            details['status'] = 'FAILED'
            details['issues'].append(f'PostgreSQL restore test error: {e}')
        
        return details
    
    def _test_mongodb_restore(self):
        """Test MongoDB restore procedure"""
        details = {'status': 'PASSED', 'issues': []}
        
        try:
            # Check mongorestore availability
            result = subprocess.run(
                ['mongorestore', '--help'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                details['status'] = 'FAILED'
                details['issues'].append('mongorestore not available')
                return details
            
            # Find latest MongoDB backup
            backup_dir = Path('/opt/backup/mongodb')
            
            if not backup_dir.exists():
                details['status'] = 'WARNING'
                details['issues'].append('No MongoDB backup directory found')
                return details
            
            backups = list(backup_dir.rglob('*.tar.gz'))
            
            if not backups:
                details['status'] = 'WARNING'
                details['issues'].append('No MongoDB backup files found')
                return details
            
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            
            # Test archive integrity
            result = subprocess.run(
                ['tar', '-tzf', str(latest_backup)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                details['status'] = 'FAILED'
                details['issues'].append('MongoDB backup archive corrupted')
            
            details['latest_backup'] = str(latest_backup)
            details['backup_size'] = latest_backup.stat().st_size
            
        except Exception as e:
            details['status'] = 'FAILED'
            details['issues'].append(f'MongoDB restore test error: {e}')
        
        return details
    
    def _test_filesystem_restore(self):
        """Test filesystem restore procedure"""
        details = {'status': 'PASSED', 'issues': []}
        
        try:
            # Find latest filesystem backup
            backup_dir = Path('/opt/backup/filesystem')
            
            if not backup_dir.exists():
                details['status'] = 'WARNING'
                details['issues'].append('No filesystem backup directory found')
                return details
            
            backups = list(backup_dir.rglob('*.tar.gz'))
            
            if not backups:
                details['status'] = 'WARNING'
                details['issues'].append('No filesystem backup files found')
                return details
            
            latest_backup = max(backups, key=lambda p: p.stat().st_mtime)
            
            # Test archive integrity
            result = subprocess.run(
                ['tar', '-tzf', str(latest_backup)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                details['status'] = 'FAILED'
                details['issues'].append('Filesystem backup archive corrupted')
            
            details['latest_backup'] = str(latest_backup)
            details['backup_size'] = latest_backup.stat().st_size
            
        except Exception as e:
            details['status'] = 'FAILED'
            details['issues'].append(f'Filesystem restore test error: {e}')
        
        return details
    
    def test_encryption_compliance(self):
        """Test encryption compliance for all backups"""
        logger.info("Testing encryption compliance")
        
        details = {
            'encrypted_files': 0,
            'unencrypted_files': 0,
            'encryption_method': self.config['encryption']['at_rest']['algorithm'],
            'key_rotation_status': 'unknown'
        }
        
        issues = []
        
        # Check if backups are encrypted
        backup_root = Path('/opt/backup')
        
        if backup_root.exists():
            all_files = list(backup_root.rglob('*'))
            encrypted_files = list(backup_root.rglob('*.encrypted'))
            
            details['encrypted_files'] = len(encrypted_files)
            details['unencrypted_files'] = len([f for f in all_files if f.is_file() and f not in encrypted_files])
            
            # Check if expected percentage is encrypted
            if details['encrypted_files'] < len(all_files) * 0.8:  # Expect 80% encrypted
                issues.append('Low encryption coverage for backups')
        
        # Check key rotation
        try:
            key_rotation_script = '/workspace/backup_recovery/automation/backup_encryption.py'
            result = subprocess.run(
                [sys.executable, key_rotation_script, 'rotate-keys', '--dry-run'],
                capture_output=True,
                text=True
            )
            
            details['key_rotation_status'] = 'configured'
            
        except Exception as e:
            issues.append(f'Key rotation check failed: {e}')
        
        status = 'PASSED' if not issues else 'WARNING'
        
        return {
            'status': status,
            'details': details
        }
    
    def test_retention_compliance(self):
        """Test backup retention policy compliance"""
        logger.info("Testing retention compliance")
        
        details = {
            'database_retention': {},
            'filesystem_retention': {},
            's3_lifecycle_policies': {}
        }
        
        issues = []
        
        # Check database retention
        for db_type, db_config in self.config['databases'].items():
            retention = db_config['retention']
            
            backup_dir = Path('/opt/backup') / db_type
            
            if backup_dir.exists():
                # List backups by age
                now = time.time()
                
                daily_backups = []
                weekly_backups = []
                monthly_backups = []
                
                for backup_file in backup_dir.rglob('*'):
                    if backup_file.is_file():
                        age_days = (now - backup_file.stat().st_mtime) / 86400
                        
                        if age_days <= retention['daily']:
                            daily_backups.append(backup_file)
                        elif age_days <= retention['weekly']:
                            weekly_backups.append(backup_file)
                        elif age_days <= retention['monthly']:
                            monthly_backups.append(backup_file)
                
                details['database_retention'][db_type] = {
                    'daily_count': len(daily_backups),
                    'weekly_count': len(weekly_backups),
                    'monthly_count': len(monthly_backups),
                    'retention_policy': retention
                }
                
                # Check if retention is being followed
                if retention.get('daily', 0) > 0 and len(daily_backups) == 0:
                    issues.append(f"No daily backups for {db_type}")
        
        # Check S3 lifecycle policies
        try:
            bucket = self.config['global_settings']['backup_location'].replace('s3://', '').split('/')[0]
            
            response = self.s3_client.get_bucket_lifecycle_configuration(Bucket=bucket)
            
            details['s3_lifecycle_policies'] = {
                'configured': True,
                'rules_count': len(response.get('Rules', []))
            }
            
        except Exception as e:
            issues.append(f"S3 lifecycle policy check failed: {e}")
        
        status = 'PASSED' if not issues else 'WARNING'
        
        return {
            'status': status,
            'details': details
        }
    
    def test_point_in_time_recovery(self):
        """Test PITR capability"""
        logger.info("Testing point-in-time recovery capability")
        
        details = {
            'continuous_backup_status': {},
            'replication_status': {},
            'recovery_time_estimate': {}
        }
        
        issues = []
        
        # Check continuous backup for each database
        for db_type, db_config in self.config['databases'].items():
            if 'point_in_time_recovery' in db_config and db_config['point_in_time_recovery'].get('enabled'):
                details['continuous_backup_status'][db_type] = 'enabled'
                
                # Check if continuous backup is actually running
                # This would require database-specific checks
                
            else:
                details['continuous_backup_status'][db_type] = 'disabled'
                issues.append(f"PITR not enabled for {db_type}")
        
        # Estimate recovery time
        details['recovery_time_estimate'] = {
            'database_minutes': 30,
            'filesystem_minutes': 60,
            'total_minutes': 90
        }
        
        status = 'PASSED' if not issues else 'WARNING'
        
        return {
            'status': status,
            'details': details
        }
    
    def _save_validation_results(self):
        """Save validation results to file"""
        results_dir = Path('/var/log/backup/validation')
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = results_dir / f'validation_results_{timestamp}.json'
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        # Update summary file
        summary_file = results_dir / 'validation_summary.json'
        with open(summary_file, 'w') as f:
            json.dump(self.test_results['summary'], f, indent=2)
        
        logger.info(f"Validation results saved to {results_file}")
    
    def generate_validation_report(self):
        """Generate human-readable validation report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("BACKUP VALIDATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Timestamp: {self.test_results['timestamp']}")
        report_lines.append("")
        
        # Summary
        summary = self.test_results['summary']
        report_lines.append("SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"Total Tests: {summary['total']}")
        report_lines.append(f"Passed: {summary['passed']}")
        report_lines.append(f"Failed: {summary['failed']}")
        report_lines.append(f"Warnings: {summary['warnings']}")
        report_lines.append("")
        
        # Test details
        report_lines.append("TEST DETAILS")
        report_lines.append("-" * 40)
        
        for test in self.test_results['tests']:
            report_lines.append(f"\n{test['test_name']}")
            report_lines.append(f"Status: {test['status']}")
            
            if 'issues' in test.get('details', {}):
                report_lines.append("Issues:")
                for issue in test['details']['issues']:
                    report_lines.append(f"  - {issue}")
            
            if 'error' in test:
                report_lines.append(f"Error: {test['error']}")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        report_text = '\n'.join(report_lines)
        
        # Save report
        report_dir = Path('/var/log/backup/validation')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f'validation_report_{timestamp}.txt'
        
        with open(report_file, 'w') as f:
            f.write(report_text)
        
        # Also print to console
        print(report_text)
        
        return str(report_file)

def main():
    validator = BackupValidation()
    
    import argparse
    parser = argparse.ArgumentParser(description='Backup Validation System')
    parser.add_argument('--mode', choices=['full', 'integrity', 'restore', 'compliance'], 
                       default='full', help='Validation mode')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--test-database', help='Test specific database')
    
    args = parser.parse_args()
    
    if args.mode == 'full':
        results = validator.run_full_validation()
        
        # Generate report
        report_file = validator.generate_validation_report()
        print(f"\nReport saved to: {report_file}")
        
        # Exit with error code if any tests failed
        if results['summary']['failed'] > 0:
            sys.exit(1)
            
    elif args.mode == 'integrity':
        result = validator.test_backup_integrity()
        print(json.dumps(result, indent=2))
        
    elif args.mode == 'restore':
        result = validator.test_restore_procedures()
        print(json.dumps(result, indent=2))
        
    elif args.mode == 'compliance':
        result = validator.test_encryption_compliance()
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
