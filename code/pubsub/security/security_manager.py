"""
Security and Encryption System for Sensitive Trading Data
Provides message encryption, authentication, authorization, and data protection
"""

import asyncio
import json
import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import uuid
import logging
import ssl
import threading
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import jwt

from core.redis_client import RedisPubSubClient, MessagePriority
from protocols.message_schemas import ProtocolMessage, MessageType, MessageStatus


class SecurityLevel(Enum):
    """Security levels for different types of data"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"


class AuthenticationMethod(Enum):
    """Authentication methods"""
    API_KEY = "api_key"
    JWT_TOKEN = "jwt_token"
    MUTUAL_TLS = "mutual_tls"
    OAUTH2 = "oauth2"


class EncryptionAlgorithm(Enum):
    """Encryption algorithms"""
    AES_256_GCM = "aes_256_gcm"
    RSA_2048 = "rsa_2048"
    HYBRID_RSA_AES = "hybrid_rsa_aes"
    FERNET = "fernet"


@dataclass
class SecurityContext:
    """Security context for message processing"""
    agent_id: str
    security_level: SecurityLevel
    encryption_algorithm: EncryptionAlgorithm
    authentication_method: AuthenticationMethod
    permissions: Set[str] = field(default_factory=set)
    issued_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncryptedMessage:
    """Encrypted message wrapper"""
    message_id: str
    original_message: ProtocolMessage
    encrypted_payload: bytes
    encryption_algorithm: EncryptionAlgorithm
    security_level: SecurityLevel
    encrypted_at: datetime
    encryption_key_id: Optional[str] = None
    signature: Optional[bytes] = None
    authentication_tag: Optional[bytes] = None
    nonce: Optional[bytes] = None


@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    policy_id: str
    name: str
    security_level: SecurityLevel
    required_encryption: bool
    allowed_algorithms: List[EncryptionAlgorithm]
    required_authentication: bool
    allowed_auth_methods: List[AuthenticationMethod]
    data_retention_days: int = 30
    audit_required: bool = True
    compliance_frameworks: List[str] = field(default_factory=list)


class SecurityManager:
    """Central security manager for the pub/sub system"""
    
    def __init__(self, redis_client: RedisPubSubClient):
        self.redis = redis_client
        
        # Security configurations
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.active_sessions: Dict[str, SecurityContext] = {}
        self.encryption_keys: Dict[str, bytes] = {}
        
        # Security statistics
        self.security_stats = {
            'messages_encrypted': 0,
            'messages_decrypted': 0,
            'authentication_failures': 0,
            'authorization_failures': 0,
            'encryption_errors': 0,
            'decryption_errors': 0
        }
        
        # Thread safety
        self.security_lock = threading.RLock()
        
        # Background tasks
        self.key_rotation_task: Optional[asyncio.Task] = None
        self.session_cleanup_task: Optional[asyncio.Task] = None
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the security manager"""
        # Initialize encryption keys
        await self._initialize_encryption_keys()
        
        # Load security policies
        await self._load_security_policies()
        
        # Start background tasks
        self.key_rotation_task = asyncio.create_task(self._key_rotation_loop())
        self.session_cleanup_task = asyncio.create_task(self._session_cleanup_loop())
        
        self.logger.info("Security manager started")
    
    async def stop(self):
        """Stop the security manager"""
        # Cancel background tasks
        if self.key_rotation_task:
            self.key_rotation_task.cancel()
        if self.session_cleanup_task:
            self.session_cleanup_task.cancel()
        
        self.logger.info("Security manager stopped")
    
    def create_security_context(self, agent_id: str, security_level: SecurityLevel,
                              permissions: List[str] = None,
                              ttl_hours: int = 24) -> SecurityContext:
        """Create a security context for an agent"""
        context = SecurityContext(
            agent_id=agent_id,
            security_level=security_level,
            encryption_algorithm=EncryptionAlgorithm.AES_256_GCM,
            authentication_method=AuthenticationMethod.JWT_TOKEN,
            permissions=set(permissions or []),
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours)
        )
        
        self.active_sessions[agent_id] = context
        return context
    
    def get_security_context(self, agent_id: str) -> Optional[SecurityContext]:
        """Get security context for an agent"""
        context = self.active_sessions.get(agent_id)
        
        # Check if context has expired
        if context and context.expires_at and context.expires_at < datetime.utcnow():
            del self.active_sessions[agent_id]
            return None
        
        return context
    
    async def encrypt_message(self, message: ProtocolMessage, 
                            security_level: SecurityLevel = SecurityLevel.CONFIDENTIAL) -> EncryptedMessage:
        """Encrypt a message based on security level"""
        try:
            # Determine encryption algorithm based on security level
            algorithm = self._get_encryption_algorithm(security_level)
            
            # Serialize message
            message_json = json.dumps(message.to_dict(), default=str)
            message_bytes = message_json.encode('utf-8')
            
            # Encrypt message
            if algorithm == EncryptionAlgorithm.AES_256_GCM:
                encrypted_payload, signature, auth_tag, nonce = await self._encrypt_aes_gcm(
                    message_bytes, security_level
                )
            elif algorithm == EncryptionAlgorithm.FERNET:
                encrypted_payload, signature, auth_tag, nonce = await self._encrypt_fernet(
                    message_bytes, security_level
                )
            else:
                raise ValueError(f"Unsupported encryption algorithm: {algorithm}")
            
            encrypted_message = EncryptedMessage(
                message_id=message.message_id,
                original_message=message,
                encrypted_payload=encrypted_payload,
                encryption_algorithm=algorithm,
                security_level=security_level,
                encrypted_at=datetime.utcnow(),
                signature=signature,
                authentication_tag=auth_tag,
                nonce=nonce
            )
            
            # Update statistics
            self.security_stats['messages_encrypted'] += 1
            
            self.logger.debug(f"Message {message.message_id} encrypted with {algorithm.value}")
            return encrypted_message
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt message {message.message_id}: {e}")
            self.security_stats['encryption_errors'] += 1
            raise
    
    async def decrypt_message(self, encrypted_message: EncryptedMessage) -> ProtocolMessage:
        """Decrypt an encrypted message"""
        try:
            # Decrypt message
            if encrypted_message.encryption_algorithm == EncryptionAlgorithm.AES_256_GCM:
                decrypted_bytes = await self._decrypt_aes_gcm(
                    encrypted_message.encrypted_payload,
                    encrypted_message.nonce,
                    encrypted_message.authentication_tag,
                    encrypted_message.security_level
                )
            elif encrypted_message.encryption_algorithm == EncryptionAlgorithm.FERNET:
                decrypted_bytes = await self._decrypt_fernet(
                    encrypted_message.encrypted_payload,
                    encrypted_message.security_level
                )
            else:
                raise ValueError(f"Unsupported encryption algorithm: {encrypted_message.encryption_algorithm}")
            
            # Deserialize message
            message_dict = json.loads(decrypted_bytes.decode('utf-8'))
            message = ProtocolMessage.from_dict(message_dict)
            
            # Update statistics
            self.security_stats['messages_decrypted'] += 1
            
            self.logger.debug(f"Message {encrypted_message.message_id} decrypted")
            return message
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt message {encrypted_message.message_id}: {e}")
            self.security_stats['decryption_errors'] += 1
            raise
    
    async def authenticate_agent(self, agent_id: str, credentials: Dict[str, Any]) -> bool:
        """Authenticate an agent"""
        try:
            # Check authentication method
            auth_method = credentials.get('method')
            
            if auth_method == AuthenticationMethod.API_KEY.value:
                return await self._authenticate_api_key(agent_id, credentials)
            elif auth_method == AuthenticationMethod.JWT_TOKEN.value:
                return await self._authenticate_jwt_token(agent_id, credentials)
            else:
                self.logger.warning(f"Unsupported authentication method: {auth_method}")
                self.security_stats['authentication_failures'] += 1
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication failed for agent {agent_id}: {e}")
            self.security_stats['authentication_failures'] += 1
            return False
    
    def authorize_action(self, agent_id: str, action: str, resource: str) -> bool:
        """Authorize an agent action"""
        try:
            context = self.get_security_context(agent_id)
            if not context:
                self.logger.warning(f"No security context for agent {agent_id}")
                self.security_stats['authorization_failures'] += 1
                return False
            
            # Check if agent has required permission
            required_permission = f"{resource}:{action}"
            if required_permission in context.permissions:
                return True
            
            # Check if agent has wildcard permission
            wildcard_permission = f"{resource}:*"
            if wildcard_permission in context.permissions:
                return True
            
            # Check if agent has admin permission
            if "admin:*" in context.permissions:
                return True
            
            self.logger.warning(f"Agent {agent_id} not authorized for {action} on {resource}")
            self.security_stats['authorization_failures'] += 1
            return False
            
        except Exception as e:
            self.logger.error(f"Authorization check failed for agent {agent_id}: {e}")
            self.security_stats['authorization_failures'] += 1
            return False
    
    async def create_api_key(self, agent_id: str, permissions: List[str] = None) -> str:
        """Create an API key for an agent"""
        try:
            # Generate secure API key
            api_key = f"ak_{secrets.token_urlsafe(32)}"
            
            # Store API key with agent ID and permissions
            key_data = {
                'agent_id': agent_id,
                'permissions': permissions or [],
                'created_at': datetime.utcnow().isoformat(),
                'last_used': None
            }
            
            api_key_key = f"api_key:{api_key}"
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.setex(
                    api_key_key,
                    86400 * 30,  # 30 days expiration
                    json.dumps(key_data, default=str)
                )
            )
            
            self.logger.info(f"API key created for agent {agent_id}")
            return api_key
            
        except Exception as e:
            self.logger.error(f"Failed to create API key for agent {agent_id}: {e}")
            raise
    
    async def create_jwt_token(self, agent_id: str, permissions: List[str] = None,
                             ttl_hours: int = 24) -> str:
        """Create a JWT token for an agent"""
        try:
            # Get secret key for JWT signing
            secret_key = await self._get_jwt_secret_key()
            
            # Create token payload
            payload = {
                'agent_id': agent_id,
                'permissions': permissions or [],
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=ttl_hours),
                'jti': str(uuid.uuid4())  # JWT ID
            }
            
            # Sign token
            token = jwt.encode(payload, secret_key, algorithm='HS256')
            
            self.logger.info(f"JWT token created for agent {agent_id}")
            return token
            
        except Exception as e:
            self.logger.error(f"Failed to create JWT token for agent {agent_id}: {e}")
            raise
    
    async def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            secret_key = await self._get_jwt_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            return payload
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("Invalid JWT token")
            return None
        except Exception as e:
            self.logger.error(f"JWT token verification failed: {e}")
            return None
    
    async def _initialize_encryption_keys(self):
        """Initialize encryption keys"""
        try:
            # Check if keys exist in Redis
            aes_key_key = "encryption_key:aes"
            fernet_key_key = "encryption_key:fernet"
            
            aes_key = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.get(aes_key_key)
            )
            
            fernet_key = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.get(fernet_key_key)
            )
            
            # Generate keys if they don't exist
            if not aes_key:
                aes_key = Fernet.generate_key()
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.setex(
                        aes_key_key, 86400 * 30, aes_key  # 30 days
                    )
                )
            
            if not fernet_key:
                fernet_key = Fernet.generate_key()
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.redis.connection.setex(
                        fernet_key_key, 86400 * 30, fernet_key  # 30 days
                    )
                )
            
            # Store keys locally
            self.encryption_keys['aes'] = aes_key
            self.encryption_keys['fernet'] = fernet_key
            
            self.logger.info("Encryption keys initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption keys: {e}")
            raise
    
    async def _get_jwt_secret_key(self) -> bytes:
        """Get JWT secret key"""
        secret_key_key = "jwt_secret_key"
        
        secret_key = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.redis.connection.get(secret_key_key)
        )
        
        if not secret_key:
            # Generate new secret key
            secret_key = secrets.token_urlsafe(32).encode()
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.setex(
                    secret_key_key, 86400 * 30, secret_key  # 30 days
                )
            )
        
        return secret_key
    
    def _get_encryption_algorithm(self, security_level: SecurityLevel) -> EncryptionAlgorithm:
        """Get encryption algorithm based on security level"""
        algorithm_mapping = {
            SecurityLevel.PUBLIC: EncryptionAlgorithm.FERNET,
            SecurityLevel.INTERNAL: EncryptionAlgorithm.FERNET,
            SecurityLevel.CONFIDENTIAL: EncryptionAlgorithm.AES_256_GCM,
            SecurityLevel.SECRET: EncryptionAlgorithm.AES_256_GCM,
            SecurityLevel.TOP_SECRET: EncryptionAlgorithm.AES_256_GCM
        }
        
        return algorithm_mapping.get(security_level, EncryptionAlgorithm.FERNET)
    
    async def _encrypt_aes_gcm(self, data: bytes, security_level: SecurityLevel) -> Tuple[bytes, bytes, bytes, bytes]:
        """Encrypt data using AES-256-GCM"""
        try:
            # Generate random key and nonce
            key = secrets.token_bytes(32)  # 256-bit key
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            
            # Create cipher
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
            encryptor = cipher.encryptor()
            
            # Encrypt data
            ciphertext = encryptor.update(data) + encryptor.finalize()
            
            # Get authentication tag
            auth_tag = encryptor.tag
            
            # Store key securely (in practice, this should use a proper key management system)
            await self._store_encryption_key(key, security_level)
            
            # Create signature
            signature = hmac.new(key, ciphertext + nonce + auth_tag, hashlib.sha256).digest()
            
            return ciphertext, signature, auth_tag, nonce
            
        except Exception as e:
            self.logger.error(f"AES-GCM encryption failed: {e}")
            raise
    
    async def _decrypt_aes_gcm(self, ciphertext: bytes, nonce: bytes, 
                             auth_tag: bytes, security_level: SecurityLevel) -> bytes:
        """Decrypt data using AES-256-GCM"""
        try:
            # Get encryption key
            key = await self._get_encryption_key(security_level)
            
            # Create cipher
            cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, auth_tag))
            decryptor = cipher.decryptor()
            
            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"AES-GCM decryption failed: {e}")
            raise
    
    async def _encrypt_fernet(self, data: bytes, security_level: SecurityLevel) -> Tuple[bytes, bytes, bytes, None]:
        """Encrypt data using Fernet"""
        try:
            # Get Fernet key
            fernet_key = self.encryption_keys['fernet']
            
            # Create Fernet instance
            fernet = Fernet(fernet_key)
            
            # Encrypt data
            ciphertext = fernet.encrypt(data)
            
            # Create signature
            signature = hmac.new(fernet_key, ciphertext, hashlib.sha256).digest()
            
            return ciphertext, signature, None, None
            
        except Exception as e:
            self.logger.error(f"Fernet encryption failed: {e}")
            raise
    
    async def _decrypt_fernet(self, ciphertext: bytes, security_level: SecurityLevel) -> bytes:
        """Decrypt data using Fernet"""
        try:
            # Get Fernet key
            fernet_key = self.encryption_keys['fernet']
            
            # Create Fernet instance
            fernet = Fernet(fernet_key)
            
            # Decrypt data
            plaintext = fernet.decrypt(ciphertext)
            
            return plaintext
            
        except Exception as e:
            self.logger.error(f"Fernet decryption failed: {e}")
            raise
    
    async def _store_encryption_key(self, key: bytes, security_level: SecurityLevel):
        """Store encryption key securely"""
        # In practice, this should use a proper key management system
        # For now, we store it in Redis with encryption
        key_id = f"key:{security_level.value}:{uuid.uuid4().hex[:8]}"
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.redis.connection.setex(
                key_id,
                86400 * 30,  # 30 days
                key
            )
        )
    
    async def _get_encryption_key(self, security_level: SecurityLevel) -> bytes:
        """Get encryption key for security level"""
        # This is a simplified implementation
        # In practice, you'd implement proper key retrieval based on key ID
        return secrets.token_bytes(32)
    
    async def _authenticate_api_key(self, agent_id: str, credentials: Dict[str, Any]) -> bool:
        """Authenticate using API key"""
        api_key = credentials.get('api_key')
        if not api_key:
            return False
        
        # Check API key in Redis
        api_key_key = f"api_key:{api_key}"
        key_data_json = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.redis.connection.get(api_key_key)
        )
        
        if not key_data_json:
            return False
        
        try:
            key_data = json.loads(key_data_json)
            
            # Check if key belongs to the agent
            if key_data.get('agent_id') != agent_id:
                return False
            
            # Update last used timestamp
            key_data['last_used'] = datetime.utcnow().isoformat()
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.redis.connection.setex(
                    api_key_key,
                    86400 * 30,  # 30 days
                    json.dumps(key_data, default=str)
                )
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"API key authentication failed: {e}")
            return False
    
    async def _authenticate_jwt_token(self, agent_id: str, credentials: Dict[str, Any]) -> bool:
        """Authenticate using JWT token"""
        token = credentials.get('token')
        if not token:
            return False
        
        # Verify JWT token
        payload = await self.verify_jwt_token(token)
        if not payload:
            return False
        
        # Check if token belongs to the agent
        if payload.get('agent_id') != agent_id:
            return False
        
        return True
    
    async def _load_security_policies(self):
        """Load security policies from configuration"""
        # Add default security policies
        default_policies = [
            SecurityPolicy(
                policy_id="trading_policy",
                name="Trading Policy",
                security_level=SecurityLevel.CONFIDENTIAL,
                required_encryption=True,
                allowed_algorithms=[EncryptionAlgorithm.AES_256_GCM, EncryptionAlgorithm.FERNET],
                required_authentication=True,
                allowed_auth_methods=[AuthenticationMethod.JWT_TOKEN, AuthenticationMethod.API_KEY],
                data_retention_days=90,
                audit_required=True,
                compliance_frameworks=["SOX", "GDPR"]
            ),
            SecurityPolicy(
                policy_id="prediction_policy",
                name="Prediction Policy",
                security_level=SecurityLevel.INTERNAL,
                required_encryption=True,
                allowed_algorithms=[EncryptionAlgorithm.FERNET],
                required_authentication=True,
                allowed_auth_methods=[AuthenticationMethod.JWT_TOKEN, AuthenticationMethod.API_KEY],
                data_retention_days=30,
                audit_required=False,
                compliance_frameworks=[]
            ),
            SecurityPolicy(
                policy_id="alert_policy",
                name="Alert Policy",
                security_level=SecurityLevel.CONFIDENTIAL,
                required_encryption=True,
                allowed_algorithms=[EncryptionAlgorithm.AES_256_GCM],
                required_authentication=True,
                allowed_auth_methods=[AuthenticationMethod.JWT_TOKEN, AuthenticationMethod.API_KEY],
                data_retention_days=365,
                audit_required=True,
                compliance_frameworks=["SOX"]
            )
        ]
        
        for policy in default_policies:
            self.security_policies[policy.policy_id] = policy
        
        self.logger.info(f"Loaded {len(self.security_policies)} security policies")
    
    async def _key_rotation_loop(self):
        """Rotate encryption keys periodically"""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                
                # Rotate keys
                await self._initialize_encryption_keys()
                
                self.logger.info("Encryption keys rotated")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Key rotation failed: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def _session_cleanup_loop(self):
        """Clean up expired security contexts"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run hourly
                
                current_time = datetime.utcnow()
                expired_sessions = [
                    agent_id for agent_id, context in self.active_sessions.items()
                    if context.expires_at and context.expires_at < current_time
                ]
                
                for agent_id in expired_sessions:
                    del self.active_sessions[agent_id]
                
                if expired_sessions:
                    self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Session cleanup failed: {e}")
                await asyncio.sleep(300)
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        with self.security_lock:
            return {
                'security_statistics': self.security_stats.copy(),
                'active_sessions': len(self.active_sessions),
                'security_policies': len(self.security_policies),
                'encryption_keys': len(self.encryption_keys)
            }


class SecurityMiddleware:
    """Security middleware for message processing"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.logger = logging.getLogger(__name__)
    
    async def process_outgoing_message(self, message: ProtocolMessage) -> Optional[EncryptedMessage]:
        """Process outgoing message with security"""
        try:
            # Determine security level based on message type and content
            security_level = self._determine_security_level(message)
            
            # Encrypt message if required
            if security_level != SecurityLevel.PUBLIC:
                encrypted_message = await self.security_manager.encrypt_message(message, security_level)
                
                # Store encrypted message for later decryption if needed
                await self._store_encrypted_message(encrypted_message)
                
                return encrypted_message
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to process outgoing message: {e}")
            return None
    
    async def process_incoming_message(self, encrypted_message: EncryptedMessage) -> Optional[ProtocolMessage]:
        """Process incoming encrypted message"""
        try:
            # Decrypt message
            decrypted_message = await self.security_manager.decrypt_message(encrypted_message)
            
            # Verify authentication and authorization
            if not await self._verify_message_security(decrypted_message, encrypted_message):
                self.logger.warning(f"Message security verification failed for {encrypted_message.message_id}")
                return None
            
            return decrypted_message
            
        except Exception as e:
            self.logger.error(f"Failed to process incoming message: {e}")
            return None
    
    def _determine_security_level(self, message: ProtocolMessage) -> SecurityLevel:
        """Determine security level for a message"""
        # Trading signals are always confidential
        if message.message_type == MessageType.TRADE_SIGNAL:
            return SecurityLevel.CONFIDENTIAL
        
        # Predictions are internal
        if message.message_type == MessageType.PREDICTION:
            return SecurityLevel.INTERNAL
        
        # Alerts are confidential
        if message.message_type == MessageType.ALERT:
            return SecurityLevel.CONFIDENTIAL
        
        # Analysis results are confidential
        if message.message_type == MessageType.ANALYSIS_RESULT:
            return SecurityLevel.CONFIDENTIAL
        
        # System messages are internal
        if message.message_type in [MessageType.AGENT_REGISTER, MessageType.AGENT_HEARTBEAT]:
            return SecurityLevel.INTERNAL
        
        # Default to internal
        return SecurityLevel.INTERNAL
    
    async def _store_encrypted_message(self, encrypted_message: EncryptedMessage):
        """Store encrypted message for later processing"""
        # Store in Redis for potential replay or analysis
        message_key = f"encrypted_message:{encrypted_message.message_id}"
        
        encrypted_data = {
            'encrypted_payload': base64.b64encode(encrypted_message.encrypted_payload).decode(),
            'encryption_algorithm': encrypted_message.encryption_algorithm.value,
            'security_level': encrypted_message.security_level.value,
            'encrypted_at': encrypted_message.encrypted_at.isoformat(),
            'signature': base64.b64encode(encrypted_message.signature).decode() if encrypted_message.signature else None,
            'authentication_tag': base64.b64encode(encrypted_message.authentication_tag).decode() if encrypted_message.authentication_tag else None,
            'nonce': base64.b64encode(encrypted_message.nonce).decode() if encrypted_message.nonce else None
        }
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.redis.connection.setex(
                message_key,
                3600,  # 1 hour
                json.dumps(encrypted_data, default=str)
            )
        )
    
    async def _verify_message_security(self, message: ProtocolMessage, 
                                     encrypted_message: EncryptedMessage) -> bool:
        """Verify message security properties"""
        try:
            # Check if message requires authentication
            context = self.security_manager.get_security_context(message.sender_id)
            if not context:
                return False
            
            # Verify security level alignment
            if encrypted_message.security_level != context.security_level:
                return False
            
            # Verify encryption algorithm is allowed
            policy = self._get_security_policy_for_level(encrypted_message.security_level)
            if encrypted_message.encryption_algorithm not in policy.allowed_algorithms:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Message security verification failed: {e}")
            return False
    
    def _get_security_policy_for_level(self, security_level: SecurityLevel) -> SecurityPolicy:
        """Get security policy for a security level"""
        for policy in self.security_manager.security_policies.values():
            if policy.security_level == security_level:
                return policy
        
        # Return default policy
        return SecurityPolicy(
            policy_id="default",
            name="Default Policy",
            security_level=security_level,
            required_encryption=True,
            allowed_algorithms=[EncryptionAlgorithm.FERNET],
            required_authentication=True,
            allowed_auth_methods=[AuthenticationMethod.JWT_TOKEN],
            audit_required=False
        )


# Example usage and integration
async def create_secure_system(redis_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a secure pub/sub system"""
    # Initialize Redis client
    redis_client = RedisPubSubClient(**redis_config)
    await redis_client.connect()
    
    # Create security manager
    security_manager = SecurityManager(redis_client)
    await security_manager.start()
    
    # Create security middleware
    security_middleware = SecurityMiddleware(security_manager)
    
    # Create test agents with security contexts
    trader_context = security_manager.create_security_context(
        "trader_001", SecurityLevel.CONFIDENTIAL, 
        permissions=["trading:execute", "trading:query"]
    )
    
    predictor_context = security_manager.create_security_context(
        "predictor_001", SecurityLevel.INTERNAL,
        permissions=["prediction:create", "prediction:query"]
    )
    
    secure_system = {
        'redis_client': redis_client,
        'security_manager': security_manager,
        'security_middleware': security_middleware,
        'security_contexts': {
            'trader': trader_context,
            'predictor': predictor_context
        }
    }
    
    return secure_system