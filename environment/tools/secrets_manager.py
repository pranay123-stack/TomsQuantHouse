#!/usr/bin/env python3
"""
Secrets Management System with Encryption and Rotation
Provides secure storage, encryption, and rotation of secrets
"""

import os
import json
import base64
import hashlib
import hmac
import secrets
import string
import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import getpass

class SecretsManager:
    """Secure secrets management with encryption and rotation"""
    
    def __init__(self, config_path: str = "config/secrets.yaml", 
                 master_key: Optional[str] = None):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.logger = self._setup_logging()
        
        # Initialize encryption
        self.master_key = master_key or os.getenv('MASTER_KEY')
        if not self.master_key:
            self.master_key = self._generate_master_key()
        
        self.cipher = self._create_cipher(self.master_key)
        self.rotation_schedule = {}
        
    def _load_config(self) -> Dict:
        """Load secrets configuration"""
        if not self.config_path.exists():
            return self._create_default_config()
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_default_config(self) -> Dict:
        """Create default secrets configuration"""
        config = {
            'secrets': {},
            'rotation': {
                'enabled': True,
                'schedule': {
                    'database_passwords': 90,  # days
                    'api_keys': 365,  # days
                    'jwt_secrets': 30,  # days
                    'encryption_keys': 180  # days
                },
                'notify_before_days': 7,
                'auto_rotate': False
            },
            'access_control': {
                'allowed_users': [],
                'admin_users': [],
                'require_mfa': True,
                'session_timeout': 3600
            },
            'audit': {
                'enabled': True,
                'log_file': 'logs/secrets_audit.log',
                'retention_days': 365
            }
        }
        
        # Create config directory if it doesn't exist
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save default config
        with open(self.config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        return config
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for secrets operations"""
        logger = logging.getLogger('secrets_manager')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_dir / 'secrets_audit.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _create_cipher(self, key: str) -> Fernet:
        """Create Fernet cipher from master key"""
        # Derive key from master key
        salt = b'secrets_manager_salt'  # In production, use proper salt storage
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(key)
    
    def _generate_master_key(self) -> str:
        """Generate a new master key"""
        key = secrets.token_urlsafe(32)
        print(f"Generated new master key. Please store it securely!")
        print(f"Key: {key}")
        
        # In production, this should be stored in a secure vault
        env_path = Path('.env.master_key')
        if not env_path.exists():
            with open(env_path, 'w') as f:
                f.write(f"MASTER_KEY={key}\n")
            os.chmod(env_path, 0o600)
        
        return key
    
    def store_secret(self, name: str, value: str, 
                    secret_type: str = "password",
                    description: str = "",
                    expires_at: Optional[datetime] = None,
                    environment: str = "global") -> bool:
        """Store a secret with encryption"""
        try:
            # Encrypt the secret value
            encrypted_value = self.cipher.encrypt(value.encode()).decode()
            
            # Generate secret metadata
            secret_id = hashlib.sha256(f"{name}_{environment}_{datetime.now()}".encode()).hexdigest()[:16]
            
            secret_data = {
                'id': secret_id,
                'name': name,
                'type': secret_type,
                'description': description,
                'encrypted_value': encrypted_value,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat() if expires_at else None,
                'environment': environment,
                'version': 1,
                'rotated_at': None
            }
            
            # Store in config
            key = f"{environment}.{name}"
            self.config['secrets'][key] = secret_data
            
            # Save config
            self._save_config()
            
            # Log operation
            self.logger.info(f"Secret stored: {name} in {environment}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store secret {name}: {e}")
            return False
    
    def retrieve_secret(self, name: str, environment: str = "global") -> Optional[str]:
        """Retrieve and decrypt a secret"""
        try:
            key = f"{environment}.{name}"
            
            if key not in self.config['secrets']:
                self.logger.warning(f"Secret not found: {name} in {environment}")
                return None
            
            secret_data = self.config['secrets'][key]
            
            # Check if expired
            if secret_data.get('expires_at'):
                expires_at = datetime.fromisoformat(secret_data['expires_at'])
                if datetime.now() > expires_at:
                    self.logger.warning(f"Secret {name} has expired")
                    return None
            
            # Decrypt the value
            encrypted_value = secret_data['encrypted_value']
            decrypted_value = self.cipher.decrypt(encrypted_value.encode()).decode()
            
            # Log access
            self.logger.info(f"Secret retrieved: {name} in {environment}")
            
            return decrypted_value
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve secret {name}: {e}")
            return None
    
    def list_secrets(self, environment: Optional[str] = None) -> List[Dict]:
        """List all secrets (without values)"""
        secrets_list = []
        
        for key, secret_data in self.config['secrets'].items():
            if environment and not key.startswith(f"{environment}."):
                continue
            
            # Remove sensitive data
            safe_data = secret_data.copy()
            safe_data.pop('encrypted_value', None)
            secrets_list.append(safe_data)
        
        return secrets_list
    
    def delete_secret(self, name: str, environment: str = "global") -> bool:
        """Delete a secret"""
        try:
            key = f"{environment}.{name}"
            
            if key not in self.config['secrets']:
                self.logger.warning(f"Secret not found for deletion: {name}")
                return False
            
            # Remove from config
            del self.config['secrets'][key]
            
            # Save config
            self._save_config()
            
            # Log operation
            self.logger.info(f"Secret deleted: {name} from {environment}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete secret {name}: {e}")
            return False
    
    def rotate_secret(self, name: str, environment: str = "global") -> bool:
        """Rotate a secret"""
        try:
            key = f"{environment}.{name}"
            
            if key not in self.config['secrets']:
                self.logger.warning(f"Secret not found for rotation: {name}")
                return False
            
            secret_data = self.config['secrets'][key]
            secret_type = secret_data['type']
            
            # Generate new value based on type
            new_value = self._generate_secret_value(secret_type)
            
            # Update the secret
            secret_data['encrypted_value'] = self.cipher.encrypt(new_value.encode()).decode()
            secret_data['version'] += 1
            secret_data['rotated_at'] = datetime.now().isoformat()
            secret_data['updated_at'] = datetime.now().isoformat()
            
            # Save config
            self._save_config()
            
            # Log operation
            self.logger.info(f"Secret rotated: {name} in {environment} (v{secret_data['version']})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate secret {name}: {e}")
            return False
    
    def _generate_secret_value(self, secret_type: str) -> str:
        """Generate a new secret value based on type"""
        if secret_type == "password":
            # Generate strong password
            length = 20
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(chars) for _ in range(length))
        
        elif secret_type == "api_key":
            # Generate API key
            return secrets.token_urlsafe(32)
        
        elif secret_type == "jwt_secret":
            # Generate JWT secret
            return secrets.token_urlsafe(64)
        
        elif secret_type == "encryption_key":
            # Generate encryption key
            return secrets.token_urlsafe(32)
        
        else:
            # Generate generic secret
            return secrets.token_urlsafe(32)
    
    def check_rotation_schedule(self) -> List[Dict]:
        """Check which secrets need rotation based on schedule"""
        secrets_to_rotate = []
        rotation_config = self.config['rotation']
        
        if not rotation_config.get('enabled'):
            return secrets_to_rotate
        
        schedule = rotation_config.get('schedule', {})
        
        for key, secret_data in self.config['secrets'].items():
            secret_type = secret_data['type']
            last_rotated = secret_data.get('rotated_at')
            
            if secret_type not in schedule:
                continue
            
            rotation_days = schedule[secret_type]
            
            if not last_rotated:
                # Never rotated, calculate from creation
                last_rotated = secret_data['created_at']
            
            last_rotated_date = datetime.fromisoformat(last_rotated)
            days_since_rotation = (datetime.now() - last_rotated_date).days
            
            if days_since_rotation >= rotation_days:
                secrets_to_rotate.append({
                    'name': secret_data['name'],
                    'environment': secret_data['environment'],
                    'type': secret_type,
                    'days_since_rotation': days_since_rotation,
                    'rotation_days': rotation_days,
                    'priority': 'high' if days_since_rotation > rotation_days * 1.5 else 'medium'
                })
        
        return secrets_to_rotate
    
    def _save_config(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
    
    def create_backup(self, backup_path: str) -> bool:
        """Create encrypted backup of all secrets"""
        try:
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'config': self.config,
                'master_key_hash': hashlib.sha256(self.master_key.encode()).hexdigest()
            }
            
            # Encrypt backup data
            backup_json = json.dumps(backup_data, indent=2)
            encrypted_backup = self.cipher.encrypt(backup_json.encode()).decode()
            
            # Write backup file
            with open(backup_path, 'w') as f:
                f.write(encrypted_backup)
            
            self.logger.info(f"Backup created: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore secrets from encrypted backup"""
        try:
            # Read encrypted backup
            with open(backup_path, 'r') as f:
                encrypted_backup = f.read()
            
            # Decrypt backup data
            backup_json = self.cipher.decrypt(encrypted_backup.encode()).decode()
            backup_data = json.loads(backup_json)
            
            # Verify master key hash
            key_hash = hashlib.sha256(self.master_key.encode()).hexdigest()
            if key_hash != backup_data['master_key_hash']:
                raise ValueError("Master key mismatch - cannot restore backup")
            
            # Restore config
            self.config = backup_data['config']
            self._save_config()
            
            self.logger.info(f"Backup restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            return False

def main():
    """Main CLI interface for secrets management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secrets Management System")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Store command
    store_parser = subparsers.add_parser('store', help='Store a secret')
    store_parser.add_argument('name', help='Secret name')
    store_parser.add_argument('value', help='Secret value')
    store_parser.add_argument('--type', default='password', help='Secret type')
    store_parser.add_argument('--env', default='global', help='Environment')
    
    # Retrieve command
    retrieve_parser = subparsers.add_parser('retrieve', help='Retrieve a secret')
    retrieve_parser.add_argument('name', help='Secret name')
    retrieve_parser.add_argument('--env', default='global', help='Environment')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List secrets')
    list_parser.add_argument('--env', help='Filter by environment')
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Rotate a secret')
    rotate_parser.add_argument('name', help='Secret name')
    rotate_parser.add_argument('--env', default='global', help='Environment')
    
    # Check rotation command
    check_parser = subparsers.add_parser('check-rotation', help='Check rotation schedule')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    backup_parser.add_argument('path', help='Backup file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = SecretsManager()
    
    if args.command == 'store':
        success = manager.store_secret(args.name, args.value, args.type, environment=args.env)
        print(f"Secret stored: {success}")
    
    elif args.command == 'retrieve':
        value = manager.retrieve_secret(args.name, args.env)
        if value:
            print(value)
        else:
            print("Secret not found or expired")
    
    elif args.command == 'list':
        secrets_list = manager.list_secrets(args.env)
        print(json.dumps(secrets_list, indent=2))
    
    elif args.command == 'rotate':
        success = manager.rotate_secret(args.name, args.env)
        print(f"Secret rotated: {success}")
    
    elif args.command == 'check-rotation':
        secrets_to_rotate = manager.check_rotation_schedule()
        print(json.dumps(secrets_to_rotate, indent=2))
    
    elif args.command == 'backup':
        success = manager.create_backup(args.path)
        print(f"Backup created: {success}")

if __name__ == "__main__":
    main()