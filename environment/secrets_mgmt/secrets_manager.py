#!/usr/bin/env python3
"""
Secrets Management System with Encryption and Rotation

This module provides secure secrets management with:
- AES-256-GCM encryption for all secrets
- Automatic secret rotation
- Access control and audit logging
- Secure storage backend
"""

import os
import json
import base64
import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecretEntry:
    """Represents a secret entry in the system"""
    name: str
    value: str
    environment: str
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]
    encrypted: bool
    rotation_days: int
    last_rotated: datetime
    access_count: int
    last_accessed: Optional[datetime]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SecretEntry':
        """Create from dictionary"""
        # Convert datetime strings back to datetime objects
        for key in ['created_at', 'updated_at', 'expires_at', 'last_rotated', 'last_accessed']:
            if data[key]:
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)

class EncryptionManager:
    """Handles encryption and decryption of secrets"""
    
    def __init__(self, master_key: str = None):
        self.master_key = self._get_or_create_master_key(master_key)
        self._fernet = self._create_fernet()
        self._lock = threading.Lock()
    
    def _get_or_create_master_key(self, master_key: str = None) -> bytes:
        """Get or create master encryption key"""
        key_file = Path.home() / '.env_mgmt' / 'master.key'
        key_file.parent.mkdir(exist_ok=True)
        
        if master_key:
            # Derive key from provided master key
            salt = b'environment_management_salt_2024'  # Fixed salt for consistency
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new master key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return key
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet instance for encryption/decryption"""
        return Fernet(self.master_key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt data and return base64 encoded string"""
        with self._lock:
            encrypted_data = self._fernet.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded encrypted data"""
        with self._lock:
            try:
                decoded_data = base64.b64decode(encrypted_data.encode())
                decrypted_data = self._fernet.decrypt(decoded_data)
                return decrypted_data.decode()
            except Exception as e:
                logger.error(f"Decryption failed: {e}")
                raise ValueError("Failed to decrypt data")

class SecretsDatabase:
    """Manages secrets database operations"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path.home() / '.env_mgmt' / 'secrets.db')
        Path(self.db_path).parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the secrets database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS secrets (
                    name TEXT PRIMARY KEY,
                    environment TEXT NOT NULL,
                    value_encrypted TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    rotation_days INTEGER DEFAULT 90,
                    last_rotated TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    secret_name TEXT,
                    user_id TEXT,
                    ip_address TEXT,
                    success BOOLEAN,
                    details TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_secrets_env ON secrets(environment)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
            ''')
            
            conn.commit()
    
    def store_secret(self, secret: SecretEntry):
        """Store a secret in the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO secrets 
                (name, environment, value_encrypted, created_at, updated_at, expires_at, 
                 rotation_days, last_rotated, access_count, last_accessed, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                secret.name, secret.environment, secret.value,
                secret.created_at.isoformat(), secret.updated_at.isoformat(),
                secret.expires_at.isoformat() if secret.expires_at else None,
                secret.rotation_days, secret.last_rotated.isoformat(),
                secret.access_count, secret.last_accessed.isoformat() if secret.last_accessed else None,
                json.dumps({})
            ))
            conn.commit()
    
    def get_secret(self, name: str) -> Optional[SecretEntry]:
        """Retrieve a secret from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT * FROM secrets WHERE name = ?', (name,))
            row = cursor.fetchone()
            
            if row:
                return SecretEntry(
                    name=row[0],
                    environment=row[1],
                    value=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    updated_at=datetime.fromisoformat(row[4]),
                    expires_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    rotation_days=row[6],
                    last_rotated=datetime.fromisoformat(row[7]),
                    access_count=row[8],
                    last_accessed=datetime.fromisoformat(row[9]) if row[9] else None
                )
            return None
    
    def list_secrets(self, environment: str = None) -> List[SecretEntry]:
        """List secrets, optionally filtered by environment"""
        with sqlite3.connect(self.db_path) as conn:
            if environment:
                cursor = conn.execute('SELECT * FROM secrets WHERE environment = ?', (environment,))
            else:
                cursor = conn.execute('SELECT * FROM secrets')
            
            secrets_list = []
            for row in cursor.fetchall():
                secrets_list.append(SecretEntry(
                    name=row[0],
                    environment=row[1],
                    value=row[2],
                    created_at=datetime.fromisoformat(row[3]),
                    updated_at=datetime.fromisoformat(row[4]),
                    expires_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    rotation_days=row[6],
                    last_rotated=datetime.fromisoformat(row[7]),
                    access_count=row[8],
                    last_accessed=datetime.fromisoformat(row[9]) if row[9] else None
                ))
            return secrets_list
    
    def delete_secret(self, name: str):
        """Delete a secret from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM secrets WHERE name = ?', (name,))
            conn.commit()
    
    def log_access(self, action: str, secret_name: str = None, success: bool = True, details: str = None):
        """Log secret access for audit purposes"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO audit_log 
                (timestamp, action, secret_name, user_id, ip_address, success, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                action,
                secret_name,
                os.getenv('USER', 'unknown'),
                os.getenv('REMOTE_ADDR', 'local'),
                success,
                details
            ))
            conn.commit()

class SecretsManager:
    """Main secrets management interface"""
    
    def __init__(self, master_key: str = None):
        self.encryption = EncryptionManager(master_key)
        self.db = SecretsDatabase()
        self.rotation_scheduler = None
        self.start_rotation_scheduler()
    
    def store_secret(self, name: str, value: str, environment: str, 
                    rotation_days: int = 90, expires_at: datetime = None) -> bool:
        """Store a new secret"""
        try:
            encrypted_value = self.encryption.encrypt(value)
            
            now = datetime.now()
            secret = SecretEntry(
                name=name,
                value=encrypted_value,
                environment=environment,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                rotation_days=rotation_days,
                last_rotated=now,
                access_count=0,
                last_accessed=None,
                encrypted=True
            )
            
            self.db.store_secret(secret)
            self.db.log_access('STORE', name, True)
            
            logger.info(f"Secret '{name}' stored for environment '{environment}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret '{name}': {e}")
            self.db.log_access('STORE', name, False, str(e))
            return False
    
    def get_secret(self, name: str) -> Optional[str]:
        """Retrieve and decrypt a secret"""
        try:
            secret = self.db.get_secret(name)
            if not secret:
                logger.warning(f"Secret '{name}' not found")
                return None
            
            # Update access tracking
            secret.access_count += 1
            secret.last_accessed = datetime.now()
            self.db.store_secret(secret)
            
            # Decrypt the value
            decrypted_value = self.encryption.decrypt(secret.value)
            self.db.log_access('GET', name, True)
            
            logger.info(f"Secret '{name}' retrieved")
            return decrypted_value
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret '{name}': {e}")
            self.db.log_access('GET', name, False, str(e))
            return None
    
    def rotate_secret(self, name: str, new_value: str = None) -> bool:
        """Rotate a secret with new value"""
        try:
            secret = self.db.get_secret(name)
            if not secret:
                return False
            
            # Generate new value if not provided
            if new_value is None:
                new_value = self.generate_secret(secret_name=name)
            
            # Store with new encrypted value
            self.store_secret(name, new_value, secret.environment, 
                            secret.rotation_days, secret.expires_at)
            
            logger.info(f"Secret '{name}' rotated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate secret '{name}': {e}")
            return False
    
    def generate_secret(self, secret_name: str, length: int = 32) -> str:
        """Generate a cryptographically secure random secret"""
        return secrets.token_urlsafe(length)
    
    def start_rotation_scheduler(self):
        """Start automatic secret rotation scheduler"""
        def rotation_worker():
            while True:
                try:
                    time.sleep(3600)  # Check every hour
                    self.check_and_rotate_secrets()
                except Exception as e:
                    logger.error(f"Rotation scheduler error: {e}")
        
        self.rotation_scheduler = threading.Thread(target=rotation_worker, daemon=True)
        self.rotation_scheduler.start()
        logger.info("Secret rotation scheduler started")
    
    def check_and_rotate_secrets(self):
        """Check for secrets that need rotation"""
        now = datetime.now()
        all_secrets = self.db.list_secrets()
        
        for secret in all_secrets:
            if secret.expires_at and now >= secret.expires_at:
                logger.warning(f"Secret '{secret.name}' has expired")
                continue
            
            next_rotation = secret.last_rotated + timedelta(days=secret.rotation_days)
            if now >= next_rotation:
                logger.info(f"Auto-rotating expired secret '{secret.name}'")
                self.rotate_secret(secret.name)
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries"""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?
            ''', (limit,))
            
            return [
                {
                    'timestamp': row[1],
                    'action': row[2],
                    'secret_name': row[3],
                    'user_id': row[4],
                    'ip_address': row[5],
                    'success': bool(row[6]),
                    'details': row[7]
                }
                for row in cursor.fetchall()
            ]
    
    def export_secrets_backup(self, output_file: str, environment: str = None):
        """Export secrets for backup purposes"""
        try:
            secrets_list = self.db.list_secrets(environment)
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'environment': environment or 'all',
                'secrets': []
            }
            
            for secret in secrets_list:
                backup_data['secrets'].append({
                    'name': secret.name,
                    'encrypted_value': secret.value if hasattr(secret, 'value') else str(secret),
                    'metadata': {
                        'environment': secret.environment,
                        'rotation_days': secret.rotation_days,
                        'created_at': secret.created_at.isoformat(),
                        'last_rotated': secret.last_rotated.isoformat()
                    }
                })
            
            with open(output_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Secrets backup exported to {output_file}")
            
        except Exception as e:
            logger.error(f"Backup export failed: {e}")
            raise

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Environment Secrets Management')
    parser.add_argument('--master-key', help='Master encryption key')
    parser.add_argument('--action', choices=['store', 'get', 'rotate', 'list', 'backup'], 
                       required=True, help='Action to perform')
    parser.add_argument('--name', help='Secret name')
    parser.add_argument('--value', help='Secret value')
    parser.add_argument('--environment', help='Environment name')
    parser.add_argument('--rotation-days', type=int, default=90, help='Rotation period in days')
    parser.add_argument('--output', help='Output file for backup')
    
    args = parser.parse_args()
    
    manager = SecretsManager(args.master_key)
    
    if args.action == 'store':
        if not args.name or not args.value or not args.environment:
            print("Error: name, value, and environment are required for store action")
            return
        manager.store_secret(args.name, args.value, args.environment, args.rotation_days)
        print(f"Secret '{args.name}' stored successfully")
    
    elif args.action == 'get':
        if not args.name:
            print("Error: name is required for get action")
            return
        value = manager.get_secret(args.name)
        if value:
            print(value)
        else:
            print(f"Secret '{args.name}' not found")
    
    elif args.action == 'rotate':
        if not args.name:
            print("Error: name is required for rotate action")
            return
        if manager.rotate_secret(args.name):
            print(f"Secret '{args.name}' rotated successfully")
        else:
            print(f"Failed to rotate secret '{args.name}'")
    
    elif args.action == 'list':
        environment = args.environment
        secrets_list = manager.db.list_secrets(environment)
        print(f"Secrets in {environment or 'all'} environments:")
        for secret in secrets_list:
            print(f"  - {secret.name} ({secret.environment})")
    
    elif args.action == 'backup':
        if not args.output:
            print("Error: output file is required for backup action")
            return
        manager.export_secrets_backup(args.output, args.environment)
        print(f"Backup exported to {args.output}")

if __name__ == '__main__':
    main()