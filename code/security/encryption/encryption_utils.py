"""
Encryption System
Handles encryption for data in transit and at rest
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import secrets
import json
from typing import Union, Tuple, Optional, Dict, Any


class EncryptionConfig:
    """Encryption configuration"""
    
    # Symmetric encryption
    SYMMETRIC_ALGORITHM = "AES-256-GCM"
    SYMMETRIC_KEY_LENGTH = 32  # 256 bits
    
    # Asymmetric encryption
    ASYMMETRIC_ALGORITHM = "RSA-2048"
    PUBLIC_EXPONENT = 65537
    KEY_SIZE = 2048
    
    # Key derivation
    PBKDF2_ITERATIONS = 100000
    PBKDF2_KEY_LENGTH = 32
    SALT_LENGTH = 32
    
    # Hashing
    HASH_ALGORITHM = "SHA-256"
    
    # Random generation
    NONCE_LENGTH = 12  # GCM nonce length


class KeyManager:
    """Cryptographic key management"""
    
    def __init__(self, key_storage_path: str = ".crypto_keys"):
        self.key_storage_path = key_storage_path
        self.master_key = self._load_or_create_master_key()
        
        # Create storage directory
        os.makedirs(key_storage_path, exist_ok=True)
        
        # Load or generate encryption keys
        self.symmetric_key = self._load_or_create_symmetric_key()
        self.key_pair = self._load_or_create_key_pair()
    
    def _load_or_create_master_key(self) -> bytes:
        """Load or create master key for key derivation"""
        master_key_path = os.path.join(self.key_storage_path, "master.key")
        
        if os.path.exists(master_key_path):
            with open(master_key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new master key
            master_key = os.urandom(32)  # 256 bits
            with open(master_key_path, 'wb') as f:
                f.write(master_key)
            os.chmod(master_key_path, 0o600)  # Read/write for owner only
            return master_key
    
    def _load_or_create_symmetric_key(self) -> bytes:
        """Load or create symmetric encryption key"""
        symmetric_key_path = os.path.join(self.key_storage_path, "symmetric.key")
        
        if os.path.exists(symmetric_key_path):
            with open(symmetric_key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new symmetric key
            symmetric_key = os.urandom(EncryptionConfig.SYMMETRIC_KEY_LENGTH)
            with open(symmetric_key_path, 'wb') as f:
                f.write(symmetric_key)
            os.chmod(symmetric_key_path, 0o600)
            return symmetric_key
    
    def _load_or_create_key_pair(self) -> Tuple[bytes, bytes]:
        """Load or create RSA key pair"""
        private_key_path = os.path.join(self.key_storage_path, "private.key")
        public_key_path = os.path.join(self.key_storage_path, "public.key")
        
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            # Load existing keys
            with open(private_key_path, 'rb') as f:
                private_key = f.read()
            with open(public_key_path, 'rb') as f:
                public_key = f.read()
            
            return private_key, public_key
        else:
            # Generate new key pair
            private_key = rsa.generate_private_key(
                public_exponent=EncryptionConfig.PUBLIC_EXPONENT,
                key_size=EncryptionConfig.KEY_SIZE
            )
            
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Store keys
            with open(private_key_path, 'wb') as f:
                f.write(private_pem)
            os.chmod(private_key_path, 0o600)
            
            with open(public_key_path, 'wb') as f:
                f.write(public_pem)
            os.chmod(public_key_path, 0o644)
            
            return private_pem, public_pem
    
    def rotate_keys(self) -> Dict[str, str]:
        """Rotate all keys"""
        # Backup old keys
        self._backup_keys()
        
        # Generate new keys
        self.symmetric_key = os.urandom(EncryptionConfig.SYMMETRIC_KEY_LENGTH)
        self.key_pair = self._load_or_create_key_pair()
        
        # Store new keys
        symmetric_key_path = os.path.join(self.key_storage_path, "symmetric.key")
        with open(symmetric_key_path, 'wb') as f:
            f.write(self.symmetric_key)
        os.chmod(symmetric_key_path, 0o600)
        
        return {
            'status': 'rotated',
            'timestamp': secrets.token_hex(8)
        }
    
    def _backup_keys(self):
        """Backup current keys"""
        backup_dir = os.path.join(self.key_storage_path, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        import time
        backup_timestamp = int(time.time())
        
        # Backup symmetric key
        symmetric_key_path = os.path.join(self.key_storage_path, "symmetric.key")
        backup_symmetric = os.path.join(backup_dir, f"symmetric_{backup_timestamp}.key")
        
        if os.path.exists(symmetric_key_path):
            with open(symmetric_key_path, 'rb') as src, open(backup_symmetric, 'wb') as dst:
                dst.write(src.read())
        
        # Backup key pair
        private_key_path = os.path.join(self.key_storage_path, "private.key")
        public_key_path = os.path.join(self.key_storage_path, "public.key")
        backup_private = os.path.join(backup_dir, f"private_{backup_timestamp}.key")
        backup_public = os.path.join(backup_dir, f"public_{backup_timestamp}.key")
        
        if os.path.exists(private_key_path):
            with open(private_key_path, 'rb') as src, open(backup_private, 'wb') as dst:
                dst.write(src.read())
        
        if os.path.exists(public_key_path):
            with open(public_key_path, 'rb') as src, open(backup_public, 'wb') as dst:
                dst.write(src.read())


class SymmetricEncryption:
    """Symmetric encryption using AES-256-GCM"""
    
    def __init__(self, key: bytes):
        if len(key) != EncryptionConfig.SYMMETRIC_KEY_LENGTH:
            raise ValueError(f"Key must be {EncryptionConfig.SYMMETRIC_KEY_LENGTH} bytes")
        self.key = key
    
    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """Encrypt data and return base64 encoded result"""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Generate random nonce
        nonce = os.urandom(EncryptionConfig.NONCE_LENGTH)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce))
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        
        # Combine nonce + tag + ciphertext
        result = nonce + encryptor.tag + ciphertext
        
        return base64.b64encode(result).decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> bytes:
        """Decrypt base64 encoded data"""
        try:
            data = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract components
            nonce = data[:EncryptionConfig.NONCE_LENGTH]
            tag = data[EncryptionConfig.NONCE_LENGTH:EncryptionConfig.NONCE_LENGTH+16]
            ciphertext = data[EncryptionConfig.NONCE_LENGTH+16:]
            
            # Create cipher
            cipher = Cipher(algorithms.AES(self.key), modes.GCM(nonce, tag))
            decryptor = cipher.decryptor()
            
            # Decrypt data
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


class AsymmetricEncryption:
    """Asymmetric encryption using RSA"""
    
    def __init__(self, private_key_pem: bytes = None, public_key_pem: bytes = None):
        if private_key_pem:
            self.private_key = serialization.load_pem_private_key(
                private_key_pem, password=None
            )
        
        if public_key_pem:
            self.public_key = serialization.load_pem_public_key(public_key_pem)
    
    def encrypt(self, plaintext: Union[str, bytes], public_key_pem: bytes = None) -> str:
        """Encrypt data using public key"""
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Use provided public key or instance public key
        if public_key_pem:
            public_key = serialization.load_pem_public_key(public_key_pem)
        else:
            public_key = self.public_key
        
        # Encrypt (RSA can only encrypt small amounts of data)
        max_size = EncryptionConfig.KEY_SIZE // 8 - 42  # PKCS#1 v1.5 padding overhead
        if len(plaintext) > max_size:
            raise ValueError(f"Data too large for RSA encryption (max {max_size} bytes)")
        
        ciphertext = public_key.encrypt(
            plaintext,
            padding.PKCS1v15()
        )
        
        return base64.b64encode(ciphertext).decode('utf-8')
    
    def decrypt(self, encrypted_data: str, private_key_pem: bytes = None) -> bytes:
        """Encrypt data using private key"""
        try:
            ciphertext = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Use provided private key or instance private key
            if private_key_pem:
                private_key = serialization.load_pem_private_key(
                    private_key_pem, password=None
                )
            else:
                private_key = self.private_key
            
            # Decrypt
            plaintext = private_key.decrypt(
                ciphertext,
                padding.PKCS1v15()
            )
            
            return plaintext
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


class KeyDerivation:
    """Key derivation functions"""
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Derive key from password using PBKDF2"""
        if salt is None:
            salt = os.urandom(EncryptionConfig.SALT_LENGTH)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=EncryptionConfig.PBKDF2_KEY_LENGTH,
            salt=salt,
            iterations=EncryptionConfig.PBKDF2_ITERATIONS
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    @staticmethod
    def verify_password(password: str, salt: bytes, key: bytes) -> bool:
        """Verify password against derived key"""
        try:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=EncryptionConfig.PBKDF2_KEY_LENGTH,
                salt=salt,
                iterations=EncryptionConfig.PBKDF2_ITERATIONS
            )
            kdf.verify(password.encode('utf-8'), key)
            return True
        except Exception:
            return False


class Hashing:
    """Cryptographic hashing functions"""
    
    @staticmethod
    def sha256(data: Union[str, bytes]) -> str:
        """Generate SHA-256 hash"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def sha256_b64(data: Union[str, bytes]) -> str:
        """Generate SHA-256 hash and return base64 encoded"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return base64.b64encode(hashlib.sha256(data).digest()).decode('utf-8')
    
    @staticmethod
    def hmac_sha256(key: bytes, data: Union[str, bytes]) -> str:
        """Generate HMAC-SHA256"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        import hmac
        return hmac.new(key, data, hashlib.sha256).hexdigest()


class DataProtector:
    """High-level data protection interface"""
    
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.symmetric_encryptor = SymmetricEncryption(key_manager.symmetric_key)
        self.asymmetric_encryptor = AsymmetricEncryption(
            key_manager.key_pair[0], key_manager.key_pair[1]
        )
    
    def protect_data(self, data: Union[str, bytes], method: str = "symmetric") -> str:
        """Protect data using specified method"""
        if method == "symmetric":
            return self.symmetric_encryptor.encrypt(data)
        elif method == "asymmetric":
            return self.asymmetric_encryptor.encrypt(data)
        elif method == "hash":
            return Hashing.sha256_b64(data)
        else:
            raise ValueError(f"Unknown protection method: {method}")
    
    def unprotect_data(self, protected_data: str, method: str = "symmetric") -> bytes:
        """Unprotect data using specified method"""
        if method == "symmetric":
            return self.symmetric_encryptor.decrypt(protected_data)
        elif method == "asymmetric":
            return self.asymmetric_encryptor.decrypt(protected_data)
        else:
            raise ValueError(f"Unknown protection method: {method}")
    
    def protect_json(self, data: Dict[str, Any], method: str = "symmetric") -> str:
        """Protect JSON data"""
        json_data = json.dumps(data)
        return self.protect_data(json_data, method)
    
    def unprotect_json(self, protected_data: str, method: str = "symmetric") -> Dict[str, Any]:
        """Unprotect JSON data"""
        json_bytes = self.unprotect_data(protected_data, method)
        json_str = json_bytes.decode('utf-8')
        return json.loads(json_str)


class SecureStorage:
    """Secure storage for sensitive data"""
    
    def __init__(self, storage_path: str = ".secure_storage", 
                 data_protector: DataProtector = None):
        self.storage_path = storage_path
        self.data_protector = data_protector or DataProtector(KeyManager())
        
        os.makedirs(storage_path, exist_ok=True)
    
    def store_secure_data(self, key: str, data: Dict[str, Any], 
                         protect_method: str = "symmetric"):
        """Store data securely"""
        # Protect data
        protected_data = self.data_protector.protect_json(data, protect_method)
        
        # Store in file
        file_path = os.path.join(self.storage_path, f"{key}.enc")
        with open(file_path, 'w') as f:
            f.write(protected_data)
        
        os.chmod(file_path, 0o600)
    
    def retrieve_secure_data(self, key: str, protect_method: str = "symmetric") -> Optional[Dict[str, Any]]:
        """Retrieve stored data"""
        file_path = os.path.join(self.storage_path, f"{key}.enc")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r') as f:
                protected_data = f.read()
            
            return self.data_protector.unprotect_json(protected_data, protect_method)
        except Exception as e:
            print(f"Failed to retrieve data for key {key}: {e}")
            return None
    
    def delete_secure_data(self, key: str):
        """Delete stored data"""
        file_path = os.path.join(self.storage_path, f"{key}.enc")
        if os.path.exists(file_path):
            os.remove(file_path)
    
    def list_stored_keys(self) -> List[str]:
        """List all stored keys"""
        if not os.path.exists(self.storage_path):
            return []
        
        keys = []
        for file in os.listdir(self.storage_path):
            if file.endswith('.enc'):
                keys.append(file[:-4])  # Remove .enc extension
        return keys


# Example usage and testing
if __name__ == "__main__":
    # Initialize encryption system
    key_manager = KeyManager()
    data_protector = DataProtector(key_manager)
    secure_storage = SecureStorage()
    
    # Test symmetric encryption
    print("=== Symmetric Encryption Test ===")
    original_data = "This is sensitive data"
    encrypted = data_protector.protect_data(original_data, "symmetric")
    decrypted = data_protector.unprotect_data(encrypted, "symmetric")
    print(f"Original: {original_data}")
    print(f"Encrypted: {encrypted[:50]}...")
    print(f"Decrypted: {decrypted.decode()}")
    print(f"Match: {original_data == decrypted.decode()}")
    
    # Test hashing
    print("\n=== Hashing Test ===")
    password = "MySecretPassword123!"
    hashed = data_protector.protect_data(password, "hash")
    print(f"Password: {password}")
    print(f"Hash: {hashed}")
    
    # Test JSON protection
    print("\n=== JSON Protection Test ===")
    sensitive_config = {
        "api_key": "sk-1234567890abcdef",
        "database_url": "postgresql://user:pass@localhost/db",
        "private_key": "-----BEGIN PRIVATE KEY-----"
    }
    protected_json = data_protector.protect_json(sensitive_config, "symmetric")
    recovered_json = data_protector.unprotect_json(protected_json, "symmetric")
    print(f"Original: {sensitive_config}")
    print(f"Protected: {protected_json[:50]}...")
    print(f"Recovered: {recovered_json}")
    print(f"Match: {sensitive_config == recovered_json}")
    
    # Test secure storage
    print("\n=== Secure Storage Test ===")
    secure_storage.store_secure_data("user_config", sensitive_config)
    stored_keys = secure_storage.list_stored_keys()
    print(f"Stored keys: {stored_keys}")
    
    retrieved = secure_storage.retrieve_secure_data("user_config")
    print(f"Retrieved: {retrieved}")
    
    # Test key rotation
    print("\n=== Key Rotation Test ===")
    rotation_result = key_manager.rotate_keys()
    print(f"Rotation result: {rotation_result}")
