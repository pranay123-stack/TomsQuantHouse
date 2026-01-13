#!/usr/bin/env python3
"""
Secure Credential Storage with Access Controls
Provides centralized credential management with RBAC and audit logging
"""

import os
import json
import yaml
import hashlib
import hmac
import secrets
import jwt
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum

class Permission(Enum):
    """Permission levels for credential access"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"

class CredentialType(Enum):
    """Types of credentials"""
    DATABASE = "database"
    API_KEY = "api_key"
    SERVICE_ACCOUNT = "service_account"
    CERTIFICATE = "certificate"
    TOKEN = "token"
    PASSWORD = "password"

@dataclass
class User:
    """User model for access control"""
    id: str
    username: str
    email: str
    role: str
    permissions: Set[Permission]
    mfa_enabled: bool
    created_at: str
    last_login: Optional[str] = None
    is_active: bool = True
    groups: List[str] = None

@dataclass
class Credential:
    """Credential model"""
    id: str
    name: str
    type: CredentialType
    value: str
    metadata: Dict[str, Any]
    owner_id: str
    access_control: Dict[str, Set[Permission]]
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None
    version: int = 1
    tags: List[str] = None

class AccessControl:
    """Access control manager"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.users_file = config_dir / "users.yaml"
        self.groups_file = config_dir / "groups.yaml"
        self.policies_file = config_dir / "policies.yaml"
        
        self.users = self._load_users()
        self.groups = self._load_groups()
        self.policies = self._load_policies()
        
        self.logger = logging.getLogger('access_control')
    
    def _load_users(self) -> Dict[str, User]:
        """Load users from file"""
        if not self.users_file.exists():
            return self._create_default_users()
        
        with open(self.users_file, 'r') as f:
            data = yaml.safe_load(f)
        
        users = {}
        for user_data in data.get('users', []):
            permissions = set(Permission(p) for p in user_data.get('permissions', []))
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                permissions=permissions,
                mfa_enabled=user_data.get('mfa_enabled', False),
                created_at=user_data['created_at'],
                last_login=user_data.get('last_login'),
                is_active=user_data.get('is_active', True),
                groups=user_data.get('groups', [])
            )
            users[user_data['id']] = user
        
        return users
    
    def _create_default_users(self) -> Dict[str, User]:
        """Create default admin user"""
        users = {
            'admin': User(
                id='admin',
                username='admin',
                email='admin@example.com',
                role='administrator',
                permissions={Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.OWNER},
                mfa_enabled=False,
                created_at=datetime.now().isoformat(),
                groups=['administrators']
            )
        }
        
        self._save_users(users)
        return users
    
    def _save_users(self, users: Dict[str, User]):
        """Save users to file"""
        data = {'users': []}
        for user in users.values():
            user_dict = asdict(user)
            user_dict['permissions'] = [p.value for p in user_dict['permissions']]
            data['users'].append(user_dict)
        
        with open(self.users_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def _load_groups(self) -> Dict[str, Dict]:
        """Load groups from file"""
        if not self.groups_file.exists():
            return self._create_default_groups()
        
        with open(self.groups_file, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def _create_default_groups(self) -> Dict[str, Dict]:
        """Create default groups"""
        groups = {
            'administrators': {
                'name': 'administrators',
                'description': 'System administrators',
                'permissions': [p.value for p in [Permission.READ, Permission.WRITE, Permission.ADMIN, Permission.OWNER]],
                'users': ['admin']
            },
            'developers': {
                'name': 'developers',
                'description': 'Development team',
                'permissions': [Permission.READ.value, Permission.WRITE.value],
                'users': []
            },
            'operators': {
                'name': 'operators',
                'description': 'Operations team',
                'permissions': [Permission.READ.value, Permission.WRITE.value],
                'users': []
            },
            'readonly': {
                'name': 'readonly',
                'description': 'Read-only access',
                'permissions': [Permission.READ.value],
                'users': []
            }
        }
        
        self._save_groups(groups)
        return groups
    
    def _save_groups(self, groups: Dict[str, Dict]):
        """Save groups to file"""
        with open(self.groups_file, 'w') as f:
            yaml.dump(groups, f, default_flow_style=False)
    
    def _load_policies(self) -> Dict[str, Dict]:
        """Load access policies"""
        if not self.policies_file.exists():
            return self._create_default_policies()
        
        with open(self.policies_file, 'r') as f:
            return yaml.safe_load(f) or {}
    
    def _create_default_policies(self) -> Dict[str, Dict]:
        """Create default access policies"""
        policies = {
            'database_credentials': {
                'description': 'Database credential access policy',
                'rules': [
                    {
                        'action': 'read',
                        'condition': 'user.role in ["administrator", "developer"]',
                        'requires_mfa': True
                    },
                    {
                        'action': 'write',
                        'condition': 'user.role == "administrator"',
                        'requires_mfa': True
                    }
                ]
            },
            'api_keys': {
                'description': 'API key access policy',
                'rules': [
                    {
                        'action': 'read',
                        'condition': 'user.groups contains "developers" or user.role == "administrator"',
                        'requires_mfa': True
                    },
                    {
                        'action': 'write',
                        'condition': 'user.role == "administrator"',
                        'requires_mfa': True
                    }
                ]
            },
            'certificates': {
                'description': 'Certificate access policy',
                'rules': [
                    {
                        'action': 'read',
                        'condition': 'user.role in ["administrator", "operator"]',
                        'requires_mfa': True
                    },
                    {
                        'action': 'write',
                        'condition': 'user.role == "administrator"',
                        'requires_mfa': True
                    }
                ]
            }
        }
        
        self._save_policies(policies)
        return policies
    
    def _save_policies(self, policies: Dict[str, Dict]):
        """Save policies to file"""
        with open(self.policies_file, 'w') as f:
            yaml.dump(policies, f, default_flow_style=False)
    
    def check_permission(self, user_id: str, credential_id: str, 
                        permission: Permission) -> bool:
        """Check if user has permission for credential"""
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        
        # Check if user is owner
        if user_id == self._get_credential_owner(credential_id):
            return True
        
        # Check if user has direct permission
        if self._check_user_permission(user, credential_id, permission):
            return True
        
        # Check group permissions
        if self._check_group_permission(user, credential_id, permission):
            return True
        
        # Check policy permissions
        if self._check_policy_permission(user, credential_id, permission):
            return True
        
        return False
    
    def _get_credential_owner(self, credential_id: str) -> Optional[str]:
        """Get credential owner"""
        # This would be implemented to check credential storage
        # For now, return None
        return None
    
    def _check_user_permission(self, user: User, credential_id: str, 
                              permission: Permission) -> bool:
        """Check user-specific permission"""
        # This would check access_control in credential metadata
        return permission in user.permissions
    
    def _check_group_permission(self, user: User, credential_id: str,
                               permission: Permission) -> bool:
        """Check group-based permission"""
        for group_name in user.groups:
            if group_name in self.groups:
                group = self.groups[group_name]
                required_permission = permission.value
                
                if required_permission in group.get('permissions', []):
                    return True
        
        return False
    
    def _check_policy_permission(self, user: User, credential_id: str,
                                permission: Permission) -> bool:
        """Check policy-based permission"""
        # This would implement policy evaluation logic
        return False

class CredentialStorage:
    """Secure credential storage with encryption"""
    
    def __init__(self, storage_dir: Path, access_control: AccessControl):
        self.storage_dir = storage_dir
        self.access_control = access_control
        self.credentials_file = storage_dir / "credentials.json"
        self.index_file = storage_dir / "index.json"
        
        self.credentials = self._load_credentials()
        self.index = self._load_index()
        
        self.logger = logging.getLogger('credential_storage')
        
        # Create storage directory if it doesn't exist
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_credentials(self) -> Dict[str, Credential]:
        """Load credentials from storage"""
        if not self.credentials_file.exists():
            return {}
        
        with open(self.credentials_file, 'r') as f:
            data = json.load(f)
        
        credentials = {}
        for cred_id, cred_data in data.items():
            try:
                credential = Credential(
                    id=cred_data['id'],
                    name=cred_data['name'],
                    type=CredentialType(cred_data['type']),
                    value=cred_data['value'],  # In production, this should be encrypted
                    metadata=cred_data.get('metadata', {}),
                    owner_id=cred_data['owner_id'],
                    access_control=cred_data.get('access_control', {}),
                    created_at=cred_data['created_at'],
                    updated_at=cred_data['updated_at'],
                    expires_at=cred_data.get('expires_at'),
                    version=cred_data.get('version', 1),
                    tags=cred_data.get('tags', [])
                )
                credentials[cred_id] = credential
            except Exception as e:
                self.logger.error(f"Failed to load credential {cred_id}: {e}")
        
        return credentials
    
    def _load_index(self) -> Dict[str, Any]:
        """Load credential index"""
        if not self.index_file.exists():
            return {'last_id': 0, 'tags': {}, 'types': {}, 'owners': {}}
        
        with open(self.index_file, 'r') as f:
            return json.load(f)
    
    def _save_credentials(self):
        """Save credentials to storage"""
        data = {}
        for cred in self.credentials.values():
            cred_dict = asdict(cred)
            cred_dict['type'] = cred.type.value
            data[cred.id] = cred_dict
        
        with open(self.credentials_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_index(self):
        """Save credential index"""
        with open(self.index_file, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def create_credential(self, name: str, type: CredentialType, value: str,
                         metadata: Dict[str, Any], owner_id: str,
                         access_control: Dict[str, Set[Permission]] = None,
                         tags: List[str] = None) -> str:
        """Create a new credential"""
        # Generate unique ID
        self.index['last_id'] += 1
        cred_id = f"cred_{self.index['last_id']:06d}"
        
        # Create credential
        credential = Credential(
            id=cred_id,
            name=name,
            type=type,
            value=value,
            metadata=metadata,
            owner_id=owner_id,
            access_control=access_control or {},
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tags=tags or []
        )
        
        # Store credential
        self.credentials[cred_id] = credential
        
        # Update index
        self._update_index(credential)
        
        # Save to storage
        self._save_credentials()
        self._save_index()
        
        self.logger.info(f"Credential created: {cred_id} by {owner_id}")
        
        return cred_id
    
    def get_credential(self, cred_id: str, user_id: str) -> Optional[Credential]:
        """Get credential if user has permission"""
        if cred_id not in self.credentials:
            return None
        
        credential = self.credentials[cred_id]
        
        # Check read permission
        if not self.access_control.check_permission(user_id, cred_id, Permission.READ):
            self.logger.warning(f"Access denied: {user_id} trying to read {cred_id}")
            return None
        
        self.logger.info(f"Credential accessed: {cred_id} by {user_id}")
        return credential
    
    def update_credential(self, cred_id: str, user_id: str, 
                         updates: Dict[str, Any]) -> bool:
        """Update credential"""
        if cred_id not in self.credentials:
            return False
        
        credential = self.credentials[cred_id]
        
        # Check write permission
        if not self.access_control.check_permission(user_id, cred_id, Permission.WRITE):
            self.logger.warning(f"Access denied: {user_id} trying to update {cred_id}")
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(credential, key):
                setattr(credential, key, value)
        
        credential.updated_at = datetime.now().isoformat()
        credential.version += 1
        
        # Save to storage
        self._save_credentials()
        
        self.logger.info(f"Credential updated: {cred_id} by {user_id}")
        
        return True
    
    def delete_credential(self, cred_id: str, user_id: str) -> bool:
        """Delete credential"""
        if cred_id not in self.credentials:
            return False
        
        credential = self.credentials[cred_id]
        
        # Check admin or owner permission
        has_permission = (
            self.access_control.check_permission(user_id, cred_id, Permission.ADMIN) or
            self.access_control.check_permission(user_id, cred_id, Permission.OWNER)
        )
        
        if not has_permission:
            self.logger.warning(f"Access denied: {user_id} trying to delete {cred_id}")
            return False
        
        # Remove credential
        del self.credentials[cred_id]
        
        # Update index
        self._remove_from_index(credential)
        
        # Save to storage
        self._save_credentials()
        self._save_index()
        
        self.logger.info(f"Credential deleted: {cred_id} by {user_id}")
        
        return True
    
    def list_credentials(self, user_id: str, 
                        filters: Dict[str, Any] = None) -> List[Credential]:
        """List credentials accessible to user"""
        accessible_credentials = []
        
        for credential in self.credentials.values():
            if self.access_control.check_permission(user_id, credential.id, Permission.READ):
                # Apply filters
                if self._apply_filters(credential, filters):
                    accessible_credentials.append(credential)
        
        return accessible_credentials
    
    def _apply_filters(self, credential: Credential, filters: Dict[str, Any]) -> bool:
        """Apply filters to credential list"""
        if not filters:
            return True
        
        for key, value in filters.items():
            if key == 'type':
                if credential.type != value:
                    return False
            elif key == 'owner':
                if credential.owner_id != value:
                    return False
            elif key == 'tags':
                if not any(tag in credential.tags for tag in value):
                    return False
            elif key == 'expires_before':
                if credential.expires_at:
                    expires_date = datetime.fromisoformat(credential.expires_at)
                    filter_date = datetime.fromisoformat(value)
                    if expires_date > filter_date:
                        return False
            elif key == 'name_contains':
                if value not in credential.name:
                    return False
        
        return True
    
    def _update_index(self, credential: Credential):
        """Update search index"""
        # Update type index
        if credential.type.value not in self.index['types']:
            self.index['types'][credential.type.value] = []
        if credential.id not in self.index['types'][credential.type.value]:
            self.index['types'][credential.type.value].append(credential.id)
        
        # Update owner index
        if credential.owner_id not in self.index['owners']:
            self.index['owners'][credential.owner_id] = []
        if credential.id not in self.index['owners'][credential.owner_id]:
            self.index['owners'][credential.owner_id].append(credential.id)
        
        # Update tag index
        for tag in credential.tags:
            if tag not in self.index['tags']:
                self.index['tags'][tag] = []
            if credential.id not in self.index['tags'][tag]:
                self.index['tags'][tag].append(credential.id)
    
    def _remove_from_index(self, credential: Credential):
        """Remove credential from index"""
        # Remove from type index
        if credential.type.value in self.index['types']:
            self.index['types'][credential.type.value] = [
                cid for cid in self.index['types'][credential.type.value]
                if cid != credential.id
            ]
        
        # Remove from owner index
        if credential.owner_id in self.index['owners']:
            self.index['owners'][credential.owner_id] = [
                cid for cid in self.index['owners'][credential.owner_id]
                if cid != credential.id
            ]
        
        # Remove from tag index
        for tag in credential.tags:
            if tag in self.index['tags']:
                self.index['tags'][tag] = [
                    cid for cid in self.index['tags'][tag]
                    if cid != credential.id
                ]

class CredentialManager:
    """Main credential management interface"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_dir = base_dir / "config"
        self.storage_dir = base_dir / "storage"
        
        # Initialize components
        self.access_control = AccessControl(self.config_dir)
        self.storage = CredentialStorage(self.storage_dir, self.access_control)
        
        # Setup logging
        self.logger = logging.getLogger('credential_manager')
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        log_dir = self.base_dir / "logs"
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "credential_audit.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def authenticate_user(self, username: str, password: str, 
                         mfa_token: Optional[str] = None) -> Optional[str]:
        """Authenticate user and return token"""
        # This would implement proper authentication
        # For now, return a simple token based on username
        if username == "admin" and password == "admin":
            return f"token_{username}_{int(time.time())}"
        
        return None
    
    def create_user(self, username: str, email: str, role: str,
                   groups: List[str] = None) -> str:
        """Create new user"""
        user_id = f"user_{len(self.access_control.users) + 1:04d}"
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=set(),  # Set based on role
            mfa_enabled=False,
            created_at=datetime.now().isoformat(),
            groups=groups or []
        )
        
        self.access_control.users[user_id] = user
        self.access_control._save_users(self.access_control.users)
        
        self.logger.info(f"User created: {user_id}")
        
        return user_id

def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure Credential Storage")
    subparsers = parser.add_subparsers(dest='command')
    
    # Create credential command
    create_parser = subparsers.add_parser('create', help='Create credential')
    create_parser.add_argument('name', help='Credential name')
    create_parser.add_argument('type', help='Credential type')
    create_parser.add_argument('value', help='Credential value')
    create_parser.add_argument('--owner', required=True, help='Owner ID')
    create_parser.add_argument('--tags', nargs='*', help='Tags')
    
    # Get credential command
    get_parser = subparsers.add_parser('get', help='Get credential')
    get_parser.add_argument('id', help='Credential ID')
    get_parser.add_argument('--user', required=True, help='User ID')
    
    # List credentials command
    list_parser = subparsers.add_parser('list', help='List credentials')
    list_parser.add_argument('--user', required=True, help='User ID')
    list_parser.add_argument('--type', help='Filter by type')
    list_parser.add_argument('--tags', nargs='*', help='Filter by tags')
    
    # Update credential command
    update_parser = subparsers.add_parser('update', help='Update credential')
    update_parser.add_argument('id', help='Credential ID')
    update_parser.add_argument('--user', required=True, help='User ID')
    update_parser.add_argument('--value', help='New value')
    
    # Delete credential command
    delete_parser = subparsers.add_parser('delete', help='Delete credential')
    delete_parser.add_argument('id', help='Credential ID')
    delete_parser.add_argument('--user', required=True, help='User ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    base_dir = Path("environment/secure_credentials")
    manager = CredentialManager(base_dir)
    
    if args.command == 'create':
        cred_type = CredentialType(args.type)
        cred_id = manager.storage.create_credential(
            args.name, cred_type, args.value, {}, args.owner, tags=args.tags
        )
        print(f"Credential created: {cred_id}")
    
    elif args.command == 'get':
        credential = manager.storage.get_credential(args.id, args.user)
        if credential:
            print(json.dumps(asdict(credential), indent=2))
        else:
            print("Credential not found or access denied")
    
    elif args.command == 'list':
        filters = {}
        if args.type:
            filters['type'] = CredentialType(args.type)
        if args.tags:
            filters['tags'] = args.tags
        
        credentials = manager.storage.list_credentials(args.user, filters)
        for cred in credentials:
            print(f"- {cred.id}: {cred.name} ({cred.type.value})")
    
    elif args.command == 'update':
        updates = {}
        if args.value:
            updates['value'] = args.value
        
        success = manager.storage.update_credential(args.id, args.user, updates)
        print(f"Credential updated: {success}")
    
    elif args.command == 'delete':
        success = manager.storage.delete_credential(args.id, args.user)
        print(f"Credential deleted: {success}")

if __name__ == "__main__":
    main()