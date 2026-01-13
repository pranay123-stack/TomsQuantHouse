"""
API Key Management System
Handles creation, validation, and rotation of API keys for external integrations
"""

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import json
import hmac
import time


class KeyStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"


class KeyType(Enum):
    STANDARD = "standard"
    READ_ONLY = "read_only"
    ADMIN = "admin"
    BATCH = "batch"
    WEBHOOK = "webhook"


class APIKeyScope:
    """API Key scope/permissions definition"""
    
    def __init__(self, scopes: List[str]):
        self.scopes = set(scopes)
        self.allowed_operations = {
            'read': 'GET',
            'write': ['POST', 'PUT', 'PATCH'],
            'delete': 'DELETE',
            'admin': 'ALL'
        }
    
    def has_scope(self, scope: str) -> bool:
        """Check if scope is granted"""
        return scope in self.scopes
    
    def can_perform_operation(self, operation: str, endpoint: str) -> bool:
        """Check if operation is allowed"""
        if 'admin' in self.scopes:
            return True
        
        if operation.upper() == 'GET':
            return 'read' in self.scopes
        elif operation.upper() in ['POST', 'PUT', 'PATCH']:
            return 'write' in self.scopes
        elif operation.upper() == 'DELETE':
            return 'delete' in self.scopes
        
        return False


class APIKey:
    """API Key data model"""
    
    def __init__(self, key_id: str, name: str, key_type: KeyType, 
                 scopes: APIKeyScope, created_by: str):
        self.key_id = key_id
        self.name = name
        self.key_type = key_type
        self.scopes = scopes
        self.created_by = created_by
        self.created_at = datetime.utcnow()
        self.expires_at = None
        self.last_used = None
        self.usage_count = 0
        self.status = KeyStatus.ACTIVE
        self.metadata = {}
        self.rate_limits = {}
        
        # Generate the actual API key
        self.api_key = self._generate_api_key()
        
        # Store hash for validation
        self.key_hash = self._hash_api_key(self.api_key)
        
        # Rate limiting
        self.rate_limit_counters = {}
        self.rate_limit_window_start = time.time()
    
    def _generate_api_key(self) -> str:
        """Generate cryptographically secure API key"""
        # Format: prefix_keyid_payload_checksum
        prefix = "ak"  # API Key prefix
        payload = secrets.token_urlsafe(32)
        checksum = hashlib.sha256(f"{self.key_id}:{payload}".encode()).hexdigest()[:8]
        return f"{prefix}_{self.key_id}_{payload}_{checksum}"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def is_valid(self) -> bool:
        """Check if key is currently valid"""
        if self.status != KeyStatus.ACTIVE:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            self.status = KeyStatus.EXPIRED
            return False
        
        return True
    
    def update_usage(self, endpoint: str = None, method: str = None):
        """Update usage statistics"""
        self.last_used = datetime.utcnow()
        self.usage_count += 1
        
        # Update endpoint-specific usage
        if endpoint:
            if endpoint not in self.metadata:
                self.metadata[endpoint] = 0
            self.metadata[endpoint] += 1
    
    def revoke(self):
        """Revoke the API key"""
        self.status = KeyStatus.REVOKED
    
    def rotate(self) -> str:
        """Rotate API key and return new key"""
        old_key = self.api_key
        self.api_key = self._generate_api_key()
        self.key_hash = self._hash_api_key(self.api_key)
        return self.api_key
    
    def set_expiry(self, days: int = None):
        """Set expiry date"""
        if days:
            self.expires_at = datetime.utcnow() + timedelta(days=days)
        else:
            self.expires_at = None
    
    def check_rate_limit(self, limit: int, window_seconds: int) -> bool:
        """Check if request is within rate limits"""
        current_time = time.time()
        
        # Reset window if needed
        if current_time - self.rate_limit_window_start >= window_seconds:
            self.rate_limit_counters = {}
            self.rate_limit_window_start = current_time
        
        # Get or create counter for this window
        counter_key = f"{limit}_{window_seconds}"
        current_count = self.rate_limit_counters.get(counter_key, 0)
        
        if current_count >= limit:
            return False
        
        self.rate_limit_counters[counter_key] = current_count + 1
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)"""
        return {
            'key_id': self.key_id,
            'name': self.name,
            'key_type': self.key_type.value,
            'scopes': list(self.scopes.scopes),
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count,
            'status': self.status.value,
            'metadata': self.metadata,
            'rate_limits': self.rate_limits
        }


class APIKeyManager:
    """API Key Management System"""
    
    def __init__(self):
        self.api_keys: Dict[str, APIKey] = {}
        self.key_hash_index: Dict[str, str] = {}  # hash -> key_id
        self.key_prefixes = {
            KeyType.STANDARD: "ak_",
            KeyType.READ_ONLY: "ak_ro_",
            KeyType.ADMIN: "ak_admin_",
            KeyType.BATCH: "ak_batch_",
            KeyType.WEBHOOK: "ak_webhook_"
        }
    
    def create_api_key(self, name: str, key_type: KeyType, 
                      scopes: List[str], created_by: str,
                      expiry_days: int = None) -> str:
        """Create new API key"""
        # Generate unique key ID
        key_id = f"key_{secrets.token_hex(8)}"
        
        # Create scope object
        api_key_scope = APIKeyScope(scopes)
        
        # Create API key
        api_key = APIKey(key_id, name, key_type, api_key_scope, created_by)
        
        # Set expiry if specified
        if expiry_days:
            api_key.set_expiry(expiry_days)
        
        # Store key
        self.api_keys[key_id] = api_key
        self.key_hash_index[api_key.key_hash] = key_id
        
        return api_key.api_key
    
    def validate_api_key(self, api_key: str) -> Optional[APIKey]:
        """Validate API key and return key object"""
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Look up in index
        key_id = self.key_hash_index.get(key_hash)
        if not key_id:
            return None
        
        # Get and validate key
        api_key_obj = self.api_keys.get(key_id)
        if not api_key_obj or not api_key_obj.is_valid():
            return None
        
        return api_key_obj
    
    def get_api_key(self, key_id: str) -> Optional[APIKey]:
        """Get API key by ID"""
        return self.api_keys.get(key_id)
    
    def list_api_keys(self, created_by: str = None, 
                     key_type: KeyType = None,
                     status: KeyStatus = None) -> List[APIKey]:
        """List API keys with optional filters"""
        keys = list(self.api_keys.values())
        
        if created_by:
            keys = [k for k in keys if k.created_by == created_by]
        
        if key_type:
            keys = [k for k in keys if k.key_type == key_type]
        
        if status:
            keys = [k for k in keys if k.status == status]
        
        return keys
    
    def update_api_key(self, key_id: str, 
                      name: str = None,
                      scopes: List[str] = None,
                      status: KeyStatus = None) -> bool:
        """Update API key properties"""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False
        
        if name:
            api_key.name = name
        
        if scopes:
            api_key.scopes = APIKeyScope(scopes)
        
        if status:
            api_key.status = status
        
        return True
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key"""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False
        
        api_key.revoke()
        
        # Remove from index
        del self.key_hash_index[api_key.key_hash]
        
        return True
    
    def rotate_api_key(self, key_id: str) -> Optional[str]:
        """Rotate API key and return new key"""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return None
        
        # Remove old hash from index
        del self.key_hash_index[api_key.key_hash]
        
        # Rotate key
        new_key = api_key.rotate()
        
        # Add new hash to index
        self.key_hash_index[api_key.key_hash] = key_id
        
        return new_key
    
    def get_usage_statistics(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for API key"""
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return None
        
        return {
            'key_id': key_id,
            'usage_count': api_key.usage_count,
            'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
            'endpoint_usage': api_key.metadata,
            'current_status': api_key.status.value
        }
    
    def cleanup_expired_keys(self) -> int:
        """Clean up expired keys"""
        expired_count = 0
        
        for key_id, api_key in list(self.api_keys.items()):
            if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
                api_key.status = KeyStatus.EXPIRED
                expired_count += 1
        
        return expired_count
    
    def bulk_revoke(self, key_ids: List[str]) -> Dict[str, bool]:
        """Revoke multiple keys"""
        results = {}
        for key_id in key_ids:
            results[key_id] = self.revoke_api_key(key_id)
        return results
    
    def get_key_analytics(self) -> Dict[str, Any]:
        """Get analytics for all keys"""
        total_keys = len(self.api_keys)
        active_keys = len([k for k in self.api_keys.values() if k.status == KeyStatus.ACTIVE])
        expired_keys = len([k for k in self.api_keys.values() if k.status == KeyStatus.EXPIRED])
        revoked_keys = len([k for k in self.api_keys.values() if k.status == KeyStatus.REVOKED])
        
        type_distribution = {}
        for key_type in KeyType:
            type_distribution[key_type.value] = len([
                k for k in self.api_keys.values() if k.key_type == key_type
            ])
        
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'expired_keys': expired_keys,
            'revoked_keys': revoked_keys,
            'type_distribution': type_distribution,
            'total_usage': sum(k.usage_count for k in self.api_keys.values())
        }


class APIKeyMiddleware:
    """Middleware for API key validation"""
    
    def __init__(self, key_manager: APIKeyManager):
        self.key_manager = key_manager
    
    def validate_request(self, api_key: str, method: str, endpoint: str) -> Dict[str, Any]:
        """Validate API key request"""
        # Validate key
        key_obj = self.key_manager.validate_api_key(api_key)
        if not key_obj:
            return {
                'valid': False,
                'error': 'Invalid API key',
                'status': 401
            }
        
        # Check if key can perform operation
        if not key_obj.scopes.can_perform_operation(method, endpoint):
            return {
                'valid': False,
                'error': 'Insufficient permissions',
                'status': 403
            }
        
        # Update usage
        key_obj.update_usage(endpoint, method)
        
        return {
            'valid': True,
            'key_id': key_obj.key_id,
            'key_type': key_obj.key_type.value,
            'scopes': list(key_obj.scopes.scopes)
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize API key manager
    key_manager = APIKeyManager()
    
    # Create API keys
    key1 = key_manager.create_api_key(
        name="Production API",
        key_type=KeyType.STANDARD,
        scopes=["read", "write"],
        created_by="user123",
        expiry_days=30
    )
    
    key2 = key_manager.create_api_key(
        name="Read-Only Service",
        key_type=KeyType.READ_ONLY,
        scopes=["read"],
        created_by="service456",
        expiry_days=90
    )
    
    print(f"Generated API Key 1: {key1[:50]}...")
    print(f"Generated API Key 2: {key2[:50]}...")
    
    # Validate keys
    validated = key_manager.validate_api_key(key1)
    print(f"Key validation: {validated is not None}")
    
    # Get key details
    key_id = list(key_manager.api_keys.keys())[0]
    key_details = key_manager.api_keys[key_id]
    print(f"Key details: {key_details.to_dict()['name']} ({key_details.key_type.value})")
    
    # Get analytics
    analytics = key_manager.get_key_analytics()
    print(f"Analytics: {analytics}")
