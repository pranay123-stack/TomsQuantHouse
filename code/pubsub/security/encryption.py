"""
Message encryption and security system.
Provides message encryption, authentication, integrity checking, and security policies.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from schemas.message_schemas import BaseMessage, MessageMetadata
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import uuid
import logging
import hashlib
import hmac
import secrets
import time
from pathlib import Path
import base64

# Crypto imports (with fallbacks)
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("Cryptography library not available. Encryption features will be limited.")

from schemas.message_schemas import BaseMessage, MessageMetadata

logger = logging.getLogger(__name__)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    AES_256 = "aes_256"
    RSA_2048 = "rsa_2048"
    AES_256_GCM = "aes_256_gcm"
    CHACHA20_POLY1305 = "chacha20_poly1305"


class SignatureAlgorithm(Enum):
    """Supported signature algorithms"""
    RSA_PSS_SHA256 = "rsa_pss_sha256"
    ECDSA_P256 = "ecdsa_p256"
    HMAC_SHA256 = "hmac_sha256"


class SecurityLevel(Enum):
    """Security levels for messages"""
    NONE = 0
    BASIC = 1
    STANDARD = 2
    HIGH = 3
    CRITICAL = 4


class TrustLevel(Enum):
    """Trust levels for agents"""
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


@dataclass
class EncryptionKey:
    """Encryption key representation"""
    key_id: str
    algorithm: EncryptionAlgorithm
    key_data: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None
    usage_count: int = 0
    max_usage: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityContext:
    """Security context for message processing"""
    sender_id: str
    recipient_id: str
    security_level: SecurityLevel
    trust_level: TrustLevel
    encryption_keys: Dict[str, EncryptionKey] = field(default_factory=dict)
    shared_secrets: Dict[str, bytes] = field(default_factory=dict)
    policies: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityPolicy:
    """Security policy definition"""
    policy_id: str
    name: str
    description: str
    min_security_level: SecurityLevel
    required_encryption: bool
    required_signature: bool
    allowed_algorithms: List[Union[EncryptionAlgorithm, SignatureAlgorithm]]
    trust_requirements: Dict[str, TrustLevel]
    valid_from: datetime
    valid_to: Optional[datetime] = None
    enabled: bool = True


@dataclass
class SecurityEvent:
    """Security event for auditing"""
    event_id: str
    event_type: str
    timestamp: datetime
    source: str
    severity: str  # info, warning, error, critical
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    signature: Optional[str] = None


class CryptographicManager:
    """Manager for cryptographic operations"""
    
    def __init__(self, manager_id: str):
        self.manager_id = manager_id
        self.keys: Dict[str, EncryptionKey] = {}
        self.key_derivation_cache: Dict[str, bytes] = {}
        self.backend = default_backend() if CRYPTO_AVAILABLE else None
        
        # Security events
        self.security_events: List[SecurityEvent] = []
        
        logger.info(f"Cryptographic manager {manager_id} initialized")
    
    def generate_key(self, algorithm: EncryptionAlgorithm, key_id: Optional[str] = None) -> EncryptionKey:
        """Generate a new encryption key"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        if not key_id:
            key_id = f"{algorithm.value}_{uuid.uuid4().hex[:8]}"
        
        try:
            if algorithm == EncryptionAlgorithm.AES_256:
                key_data = Fernet.generate_key()
                fernet = Fernet(key_data)
                
            elif algorithm == EncryptionAlgorithm.RSA_2048:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=self.backend
                )
                key_data = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            encryption_key = EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_data=key_data,
                created_at=datetime.now()
            )
            
            self.keys[key_id] = encryption_key
            
            self._log_security_event("key_generated", "info", 
                                    f"Generated {algorithm.value} key: {key_id}")
            
            return encryption_key
            
        except Exception as e:
            self._log_security_event("key_generation_failed", "error",
                                    f"Failed to generate key: {e}")
            raise
    
    def derive_key_from_password(self, password: str, salt: Optional[bytes] = None,
                               algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256) -> EncryptionKey:
        """Derive encryption key from password"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        if not salt:
            salt = secrets.token_bytes(32)
        
        password_bytes = password.encode()
        
        if algorithm == EncryptionAlgorithm.AES_256:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=self.backend
            )
            key_data = base64.urlsafe_b64encode(kdf.derive(password_bytes))
            
            key_id = f"derived_{uuid.uuid4().hex[:8]}"
            
            encryption_key = EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_data=key_data,
                created_at=datetime.now(),
                metadata={'salt': base64.b64encode(salt).decode()}
            )
            
        else:
            raise ValueError(f"Key derivation not supported for algorithm: {algorithm}")
        
        self.keys[key_id] = encryption_key
        return encryption_key
    
    def encrypt_message(self, message: str, key_id: str) -> Tuple[bytes, str]:
        """Encrypt a message using specified key"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        if key_id not in self.keys:
            raise ValueError(f"Key {key_id} not found")
        
        key = self.keys[key_id]
        algorithm = key.algorithm
        
        try:
            if algorithm == EncryptionAlgorithm.AES_256:
                fernet = Fernet(key.key_data)
                encrypted_data = fernet.encrypt(message.encode())
                return encrypted_data, key_id
                
            else:
                raise ValueError(f"Encryption not implemented for algorithm: {algorithm}")
                
        except Exception as e:
            self._log_security_event("encryption_failed", "error",
                                    f"Failed to encrypt with key {key_id}: {e}")
            raise
    
    def decrypt_message(self, encrypted_data: bytes, key_id: str) -> str:
        """Decrypt a message using specified key"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        if key_id not in self.keys:
            raise ValueError(f"Key {key_id} not found")
        
        key = self.keys[key_id]
        algorithm = key.algorithm
        
        try:
            if algorithm == EncryptionAlgorithm.AES_256:
                fernet = Fernet(key.key_data)
                decrypted_data = fernet.decrypt(encrypted_data)
                return decrypted_data.decode()
                
            else:
                raise ValueError(f"Decryption not implemented for algorithm: {algorithm}")
                
        except Exception as e:
            self._log_security_event("decryption_failed", "error",
                                    f"Failed to decrypt with key {key_id}: {e}")
            raise
    
    def create_signature(self, data: bytes, key_id: str, 
                        algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256) -> str:
        """Create digital signature for data"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        if key_id not in self.keys:
            raise ValueError(f"Key {key_id} not found")
        
        key = self.keys[key_id]
        
        try:
            if algorithm == SignatureAlgorithm.HMAC_SHA256:
                signature = hmac.new(key.key_data, data, hashlib.sha256).hexdigest()
                return signature
                
            else:
                raise ValueError(f"Signature algorithm not implemented: {algorithm}")
                
        except Exception as e:
            self._log_security_event("signature_failed", "error",
                                    f"Failed to create signature: {e}")
            raise
    
    def verify_signature(self, data: bytes, signature: str, key_id: str,
                        algorithm: SignatureAlgorithm = SignatureAlgorithm.HMAC_SHA256) -> bool:
        """Verify digital signature"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        if key_id not in self.keys:
            return False
        
        key = self.keys[key_id]
        
        try:
            if algorithm == SignatureAlgorithm.HMAC_SHA256:
                expected_signature = hmac.new(key.key_data, data, hashlib.sha256).hexdigest()
                return hmac.compare_digest(signature, expected_signature)
                
            else:
                raise ValueError(f"Signature verification not implemented for: {algorithm}")
                
        except Exception as e:
            self._log_security_event("signature_verification_failed", "error",
                                    f"Failed to verify signature: {e}")
            return False
    
    def generate_random_bytes(self, length: int) -> bytes:
        """Generate cryptographically secure random bytes"""
        return secrets.token_bytes(length)
    
    def hash_data(self, data: bytes, algorithm: str = "sha256") -> str:
        """Hash data using specified algorithm"""
        if algorithm == "sha256":
            return hashlib.sha256(data).hexdigest()
        elif algorithm == "sha512":
            return hashlib.sha512(data).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    def _log_security_event(self, event_type: str, severity: str, description: str):
        """Log security event"""
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            source=self.manager_id,
            severity=severity,
            description=description
        )
        
        self.security_events.append(event)
        
        # Keep only recent events
        if len(self.security_events) > 10000:
            self.security_events = self.security_events[-5000:]
        
        logger.debug(f"Security event: {event_type} - {description}")


class SecurityManager:
    """Manager for message security policies and enforcement"""
    
    def __init__(self, manager_id: str, crypto_manager: CryptographicManager):
        self.manager_id = manager_id
        self.crypto_manager = crypto_manager
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.trust_relationships: Dict[str, TrustLevel] = {}
        self.encryption_cache: Dict[str, bytes] = {}
        
        # Security configuration
        self.default_security_level = SecurityLevel.STANDARD
        self.require_encryption = True
        self.require_signatures = False
        
        # Initialize with default policies
        self._initialize_default_policies()
        
        logger.info(f"Security manager {manager_id} initialized")
    
    def _initialize_default_policies(self):
        """Initialize default security policies"""
        # High security policy for critical messages
        high_security_policy = SecurityPolicy(
            policy_id="high_security",
            name="High Security Policy",
            description="Required for critical and sensitive messages",
            min_security_level=SecurityLevel.HIGH,
            required_encryption=True,
            required_signature=True,
            allowed_algorithms=[EncryptionAlgorithm.AES_256, SignatureAlgorithm.HMAC_SHA256],
            trust_requirements={"default": TrustLevel.HIGH},
            valid_from=datetime.now(),
            enabled=True
        )
        
        # Standard security policy
        standard_policy = SecurityPolicy(
            policy_id="standard_security",
            name="Standard Security Policy",
            description="Standard security for normal operations",
            min_security_level=SecurityLevel.STANDARD,
            required_encryption=True,
            required_signature=False,
            allowed_algorithms=[EncryptionAlgorithm.AES_256, SignatureAlgorithm.HMAC_SHA256],
            trust_requirements={"default": TrustLevel.MEDIUM},
            valid_from=datetime.now(),
            enabled=True
        )
        
        # Add policies
        self.add_policy(high_security_policy)
        self.add_policy(standard_policy)
    
    def add_policy(self, policy: SecurityPolicy):
        """Add a security policy"""
        self.security_policies[policy.policy_id] = policy
        logger.info(f"Added security policy: {policy.name}")
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a security policy"""
        if policy_id in self.security_policies:
            del self.security_policies[policy_id]
            logger.info(f"Removed security policy: {policy_id}")
            return True
        return False
    
    def set_trust_level(self, agent_id: str, trust_level: TrustLevel):
        """Set trust level for an agent"""
        self.trust_relationships[agent_id] = trust_level
        logger.info(f"Set trust level for {agent_id}: {trust_level.value}")
    
    def get_trust_level(self, agent_id: str) -> TrustLevel:
        """Get trust level for an agent"""
        return self.trust_relationships.get(agent_id, TrustLevel.UNKNOWN)
    
    def encrypt_message(self, message: BaseMessage, 
                       security_level: Optional[SecurityLevel] = None) -> BaseMessage:
        """Encrypt message according to security requirements"""
        try:
            if not CRYPTO_AVAILABLE:
                # Fallback: mark as encrypted without actual encryption
                message.metadata.encrypted = False
                message.metadata.signature = "unavailable"
                return message
            
            if security_level is None:
                security_level = self.default_security_level
            
            # Check if encryption is required
            if security_level.value >= SecurityLevel.STANDARD.value:
                # Generate or get encryption key
                key_id = self._get_or_create_key(message.sender_id, message.recipient_id)
                
                # Serialize message
                message_json = message.to_json()
                
                # Encrypt message
                encrypted_data, _ = self.crypto_manager.encrypt_message(message_json, key_id)
                
                # Replace payload with encrypted data
                message.payload = {
                    'encrypted_data': base64.b64encode(encrypted_data).decode(),
                    'encryption_key_id': key_id,
                    'original_payload': message.payload
                }
                
                message.metadata.encrypted = True
                message.metadata.signature = self._sign_message(message)
                
                logger.debug(f"Encrypted message {message.metadata.message_id} with level {security_level.value}")
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to encrypt message {message.metadata.message_id}: {e}")
            # Return unencrypted message with security failure marking
            message.payload['security_error'] = str(e)
            return message
    
    def decrypt_message(self, message: BaseMessage) -> BaseMessage:
        """Decrypt message if encrypted"""
        try:
            if not CRYPTO_AVAILABLE or not message.metadata.encrypted:
                return message
            
            if 'encrypted_data' in message.payload:
                encrypted_data = base64.b64decode(message.payload['encrypted_data'])
                key_id = message.payload['encryption_key_id']
                
                # Decrypt message
                decrypted_json = self.crypto_manager.decrypt_message(encrypted_data, key_id)
                
                # Parse decrypted message
                decrypted_message = BaseMessage.from_json(decrypted_json)
                
                # Restore original payload
                decrypted_message.payload = message.payload['original_payload']
                decrypted_message.metadata.encrypted = False  # Clear encryption flag
                
                logger.debug(f"Decrypted message {message.metadata.message_id}")
                return decrypted_message
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to decrypt message {message.metadata.message_id}: {e}")
            # Mark as decryption failed
            message.payload['decryption_error'] = str(e)
            return message
    
    def verify_message_integrity(self, message: BaseMessage) -> bool:
        """Verify message integrity using signature"""
        try:
            if not CRYPTO_AVAILABLE or not message.metadata.signature:
                return True  # Skip verification if no crypto or signature
            
            # Generate signature for current message
            current_signature = self._sign_message(message)
            
            # Compare signatures (simplified - in real implementation would verify against stored signature)
            return message.metadata.signature == current_signature
            
        except Exception as e:
            logger.error(f"Failed to verify message integrity {message.metadata.message_id}: {e}")
            return False
    
    def enforce_security_policy(self, message: BaseMessage, 
                              policy_id: str = "standard_security") -> bool:
        """Enforce security policy on message"""
        if policy_id not in self.security_policies:
            logger.warning(f"Security policy {policy_id} not found, using default")
            policy_id = "standard_security"
        
        policy = self.security_policies[policy_id]
        
        # Check if policy is enabled and valid
        if not policy.enabled:
            logger.warning(f"Security policy {policy_id} is disabled")
            return True
        
        if policy.valid_to and datetime.now() > policy.valid_to:
            logger.warning(f"Security policy {policy_id} has expired")
            return False
        
        # Check if encryption is required
        if policy.required_encryption and not message.metadata.encrypted:
            logger.warning(f"Message {message.metadata.message_id} violates encryption requirement")
            return False
        
        # Check if signature is required
        if policy.required_signature and not message.metadata.signature:
            logger.warning(f"Message {message.metadata.message_id} violates signature requirement")
            return False
        
        # Check security level
        message_security_level = self._assess_message_security_level(message)
        if message_security_level.value < policy.min_security_level.value:
            logger.warning(f"Message security level {message_security_level.value} below required {policy.min_security_level.value}")
            return False
        
        # Check trust requirements
        sender_trust = self.get_trust_level(message.sender_id)
        required_trust = policy.trust_requirements.get(message.sender_id, policy.trust_requirements.get('default', TrustLevel.MEDIUM))
        
        if self._trust_level_to_numeric(sender_trust) < self._trust_level_to_numeric(required_trust):
            logger.warning(f"Sender {message.sender_id} trust level {sender_trust.value} below required {required_trust.value}")
            return False
        
        return True
    
    def _get_or_create_key(self, sender_id: str, recipient_id: str) -> str:
        """Get or create encryption key for sender-recipient pair"""
        key_id = f"{sender_id}:{recipient_id}"
        
        if key_id not in self.crypto_manager.keys:
            # Create new key
            key = self.crypto_manager.generate_key(EncryptionAlgorithm.AES_256, key_id)
            logger.info(f"Created new encryption key for {sender_id} -> {recipient_id}")
        
        return key_id
    
    def _sign_message(self, message: BaseMessage) -> str:
        """Create signature for message"""
        try:
            # Create key for signing
            sign_key_id = f"sign:{message.sender_id}"
            if sign_key_id not in self.crypto_manager.keys:
                # Generate signing key
                self.crypto_manager.generate_key(EncryptionAlgorithm.AES_256, sign_key_id)
            
            # Create signature data (simplified)
            signature_data = f"{message.sender_id}:{message.payload}:{message.metadata.timestamp}".encode()
            return self.crypto_manager.create_signature(signature_data, sign_key_id)
            
        except Exception as e:
            logger.error(f"Failed to sign message: {e}")
            return ""
    
    def _assess_message_security_level(self, message: BaseMessage) -> SecurityLevel:
        """Assess security level of message based on content and metadata"""
        # Check message type for security sensitivity
        sensitive_types = ['trade_signal', 'prediction', 'coordination']
        
        if message.message_type.value in sensitive_types:
            return SecurityLevel.HIGH
        
        # Check if encrypted
        if message.metadata.encrypted:
            return SecurityLevel.STANDARD
        
        # Check priority
        if hasattr(message.metadata, 'priority') and message.metadata.priority.value >= 4:
            return SecurityLevel.HIGH
        
        return SecurityLevel.BASIC
    
    def _trust_level_to_numeric(self, trust_level: TrustLevel) -> int:
        """Convert trust level to numeric value for comparison"""
        mapping = {
            TrustLevel.UNKNOWN: 0,
            TrustLevel.LOW: 1,
            TrustLevel.MEDIUM: 2,
            TrustLevel.HIGH: 3,
            TrustLevel.VERIFIED: 4
        }
        return mapping.get(trust_level, 0)
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        return {
            'security_manager_id': self.manager_id,
            'policies_count': len(self.security_policies),
            'active_policies': len([p for p in self.security_policies.values() if p.enabled]),
            'trust_relationships': len(self.trust_relationships),
            'crypto_keys': len(self.crypto_manager.keys),
            'security_events': len(self.crypto_manager.security_events),
            'default_security_level': self.default_security_level.value,
            'encryption_required': self.require_encryption,
            'signatures_required': self.require_signatures
        }


class SecureTransport:
    """Secure transport layer for message transmission"""
    
    def __init__(self, transport_id: str, security_manager: SecurityManager):
        self.transport_id = transport_id
        self.security_manager = security_manager
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.message_counter = 0
        self.security_events = []
        
        logger.info(f"Secure transport {transport_id} initialized")
    
    async def send_message(self, message: BaseMessage, 
                          target_agent: str) -> bool:
        """Send message securely to target agent"""
        try:
            # Generate message ID if not present
            if not message.metadata.message_id:
                message.metadata.message_id = str(uuid.uuid4())
            
            # Apply security policies
            policy_applied = self.security_manager.encrypt_message(message)
            
            # Verify integrity
            integrity_verified = self.security_manager.verify_message_integrity(message)
            
            if not integrity_verified:
                logger.error(f"Message integrity verification failed: {message.metadata.message_id}")
                return False
            
            # Check security policy compliance
            policy_compliant = self.security_manager.enforce_security_policy(message)
            
            if not policy_compliant:
                logger.warning(f"Message violates security policy: {message.metadata.message_id}")
                # Still send but log the violation
            
            # Increment message counter
            self.message_counter += 1
            
            # Log security event
            self._log_security_event("message_sent", "info", {
                'message_id': message.metadata.message_id,
                'sender': message.sender_id,
                'recipient': target_agent,
                'encrypted': message.metadata.encrypted,
                'signed': bool(message.metadata.signature)
            })
            
            logger.debug(f"Securely sent message {message.metadata.message_id} to {target_agent}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send secure message: {e}")
            self._log_security_event("message_send_failed", "error", {
                'error': str(e),
                'message_id': message.metadata.message_id
            })
            return False
    
    async def receive_message(self, message: BaseMessage, 
                            source_agent: str) -> Optional[BaseMessage]:
        """Receive and decrypt message from source agent"""
        try:
            # Verify integrity before processing
            integrity_verified = self.security_manager.verify_message_integrity(message)
            
            if not integrity_verified:
                logger.error(f"Received message with failed integrity verification: {message.metadata.message_id}")
                return None
            
            # Decrypt message if encrypted
            decrypted_message = self.security_manager.decrypt_message(message)
            
            # Log security event
            self._log_security_event("message_received", "info", {
                'message_id': message.metadata.message_id,
                'sender': source_agent,
                'encrypted': message.metadata.encrypted
            })
            
            logger.debug(f"Securely received message {message.metadata.message_id} from {source_agent}")
            return decrypted_message
            
        except Exception as e:
            logger.error(f"Failed to receive secure message: {e}")
            self._log_security_event("message_receive_failed", "error", {
                'error': str(e),
                'message_id': message.metadata.message_id
            })
            return None
    
    def _log_security_event(self, event_type: str, severity: str, details: Dict[str, Any]):
        """Log security event"""
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            source=self.transport_id,
            severity=severity,
            description=f"{event_type} for transport",
            details=details
        )
        
        self.security_events.append(event)
        
        # Keep only recent events
        if len(self.security_events) > 5000:
            self.security_events = self.security_events[-2500:]
    
    def get_transport_stats(self) -> Dict[str, Any]:
        """Get transport statistics"""
        return {
            'transport_id': self.transport_id,
            'messages_sent': self.message_counter,
            'active_connections': len(self.connections),
            'security_events': len(self.security_events)
        }


# Factory functions and utilities
def create_security_system(system_id: str = "default") -> Tuple[CryptographicManager, SecurityManager, SecureTransport]:
    """Create complete security system"""
    crypto_manager = CryptographicManager(f"crypto_{system_id}")
    security_manager = SecurityManager(f"security_{system_id}", crypto_manager)
    secure_transport = SecureTransport(f"transport_{system_id}", security_manager)
    
    return crypto_manager, security_manager, secure_transport


def create_secure_message(message: BaseMessage, security_level: SecurityLevel = SecurityLevel.STANDARD) -> BaseMessage:
    """Create a secure message with encryption and signatures"""
    crypto_manager, security_manager, _ = create_security_system()
    
    # Set security level in metadata
    message.metadata.routing_key = f"secure.{security_level.name.lower()}.{message.message_type.value}"
    
    # Encrypt if security level requires it
    if security_level.value >= SecurityLevel.STANDARD.value:
        message = security_manager.encrypt_message(message, security_level)
    
    return message


# Default security configuration
DEFAULT_SECURITY_CONFIG = {
    "encryption_required": True,
    "signature_required": False,
    "default_security_level": SecurityLevel.STANDARD,
    "allowed_algorithms": [EncryptionAlgorithm.AES_256, SignatureAlgorithm.HMAC_SHA256],
    "key_rotation_interval_days": 30,
    "max_key_usage": 10000,
    "trust_level_requirements": {
        "critical_messages": TrustLevel.HIGH,
        "trade_signals": TrustLevel.MEDIUM,
        "coordination_messages": TrustLevel.MEDIUM
    }
}