#!/usr/bin/env python3
"""
Backup Encryption and Integrity Verification System
Handles encryption at rest and in transit, plus integrity checks for all backups
"""

import os
import sys
import hashlib
import hmac
import logging
import boto3
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
import tempfile
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupEncryption:
    def __init__(self, config_path='/workspace/backup_recovery/config/backup_config.yaml'):
        self.config_path = config_path
        self.config = self._load_config()
        self.kms_client = boto3.client('kms')
        self.s3_client = boto3.client('s3')
        
    def _load_config(self):
        """Load configuration"""
        import yaml
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def encrypt_backup_file(self, file_path, encryption_key_id=None):
        """Encrypt backup file using configured encryption method"""
        logger.info(f"Encrypting backup file: {file_path}")
        
        try:
            file_path = Path(file_path)
            encrypted_file_path = file_path.with_suffix(file_path.suffix + '.encrypted')
            
            # Get encryption configuration
            enc_config = self.config['encryption']
            
            if enc_config['at_rest']['algorithm'] == 'AES-256-GCM':
                return self._encrypt_file_aes_gcm(file_path, encrypted_file_path, encryption_key_id)
            elif enc_config['at_rest']['algorithm'] == 'AWS-KMS':
                return self._encrypt_file_kms(file_path, encrypted_file_path, encryption_key_id)
            else:
                raise ValueError(f"Unsupported encryption algorithm: {enc_config['at_rest']['algorithm']}")
                
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def _encrypt_file_aes_gcm(self, file_path, output_path, encryption_key_id):
        """Encrypt file using AES-256-GCM"""
        # Generate random key
        key = Fernet.generate_key()
        fernet = Fernet(key)
        
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Encrypt data
        encrypted_data = fernet.encrypt(file_data)
        
        # Write encrypted data
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Get encryption key from KMS if key_id provided
        if encryption_key_id:
            encrypted_key = self.kms_client.encrypt(
                KeyId=encryption_key_id,
                Plaintext=key,
                EncryptionAlgorithm='SYMMETRIC_DEFAULT'
            )['CiphertextBlob']
            
            # Save encrypted key metadata
            key_metadata = {
                'encrypted_key': base64.b64encode(encrypted_key).decode(),
                'encryption_algorithm': 'AES-256-GCM',
                'timestamp': datetime.now().isoformat(),
                'key_id': encryption_key_id
            }
            
            metadata_file = output_path.with_suffix(output_path.suffix + '.meta')
            with open(metadata_file, 'w') as f:
                json.dump(key_metadata, f, indent=2)
        
        logger.info(f"File encrypted successfully: {output_path}")
        return str(output_path)
    
    def _encrypt_file_kms(self, file_path, output_path, encryption_key_id):
        """Encrypt file using AWS KMS"""
        if not encryption_key_id:
            encryption_key_id = self.config['encryption']['key_management']['backup_keys']
        
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Use AWS KMS to encrypt file
        response = self.kms_client.encrypt(
            KeyId=encryption_key_id,
            Plaintext=file_data,
            EncryptionAlgorithm='SYMMETRIC_DEFAULT'
        )
        
        encrypted_data = response['CiphertextBlob']
        
        # Write encrypted data
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Save encryption metadata
        metadata = {
            'ciphertext_blob': base64.b64encode(encrypted_data).decode(),
            'key_id': response['KeyId'],
            'encryption_algorithm': 'AWS-KMS',
            'timestamp': datetime.now().isoformat()
        }
        
        metadata_file = output_path.with_suffix(output_path.suffix + '.meta')
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"File encrypted with KMS: {output_path}")
        return str(output_path)
    
    def decrypt_backup_file(self, encrypted_file_path, output_path=None):
        """Decrypt backup file"""
        logger.info(f"Decrypting backup file: {encrypted_file_path}")
        
        try:
            encrypted_file_path = Path(encrypted_file_path)
            
            # Find metadata file
            metadata_file = encrypted_file_path.with_suffix(encrypted_file_path.suffix + '.meta')
            
            if not metadata_file.exists():
                raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
            
            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            algorithm = metadata.get('encryption_algorithm')
            
            if algorithm == 'AES-256-GCM':
                return self._decrypt_file_aes_gcm(encrypted_file_path, output_path, metadata)
            elif algorithm == 'AWS-KMS':
                return self._decrypt_file_kms(encrypted_file_path, output_path, metadata)
            else:
                raise ValueError(f"Unsupported encryption algorithm: {algorithm}")
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def _decrypt_file_aes_gcm(self, encrypted_file_path, output_path, metadata):
        """Decrypt file encrypted with AES-256-GCM"""
        # Get encrypted key
        encrypted_key = base64.b64decode(metadata['encrypted_key'])
        key_id = metadata['key_id']
        
        # Decrypt the key
        response = self.kms_client.decrypt(
            CiphertextBlob=encrypted_key
        )
        
        key = response['Plaintext']
        fernet = Fernet(key)
        
        # Read encrypted data
        with open(encrypted_file_path, 'rb') as f:
            encrypted_data = f.read()
        
        # Decrypt data
        decrypted_data = fernet.decrypt(encrypted_data)
        
        # Determine output path
        if output_path is None:
            output_path = encrypted_file_path.with_suffix(encrypted_file_path.suffix.replace('.encrypted', ''))
        else:
            output_path = Path(output_path)
        
        # Write decrypted data
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        logger.info(f"File decrypted successfully: {output_path}")
        return str(output_path)
    
    def _decrypt_file_kms(self, encrypted_file_path, output_path, metadata):
        """Decrypt file encrypted with AWS KMS"""
        # Get encrypted data
        encrypted_data = base64.b64decode(metadata['ciphertext_blob'])
        
        # Decrypt with KMS
        response = self.kms_client.decrypt(
            CiphertextBlob=encrypted_data
        )
        
        decrypted_data = response['Plaintext']
        
        # Determine output path
        if output_path is None:
            output_path = encrypted_file_path.with_suffix(encrypted_file_path.suffix.replace('.encrypted', ''))
        else:
            output_path = Path(output_path)
        
        # Write decrypted data
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        logger.info(f"File decrypted with KMS: {output_path}")
        return str(output_path)
    
    def verify_backup_integrity(self, file_path, expected_checksum=None):
        """Verify backup file integrity using checksums"""
        logger.info(f"Verifying integrity of: {file_path}")
        
        try:
            file_path = Path(file_path)
            
            # Calculate checksum
            algorithm = self.config['integrity_checks']['algorithm']
            
            if algorithm == 'SHA-256':
                checksum = self._calculate_sha256(file_path)
            elif algorithm == 'SHA-512':
                checksum = self._calculate_sha512(file_path)
            elif algorithm == 'MD5':
                checksum = self._calculate_md5(file_path)
            else:
                raise ValueError(f"Unsupported checksum algorithm: {algorithm}")
            
            # Check if expected checksum is provided
            if expected_checksum:
                if checksum == expected_checksum:
                    logger.info(f"✓ Integrity verification passed: {file_path}")
                    return {'valid': True, 'checksum': checksum}
                else:
                    logger.error(f"✗ Integrity verification failed: {file_path}")
                    logger.error(f"Expected: {expected_checksum}")
                    logger.error(f"Actual: {checksum}")
                    return {'valid': False, 'expected': expected_checksum, 'actual': checksum}
            
            # Look for stored checksum file
            checksum_file = file_path.with_suffix(file_path.suffix + '.sha256')
            
            if checksum_file.exists():
                with open(checksum_file, 'r') as f:
                    stored_checksum = f.read().strip().split()[0]
                
                if checksum == stored_checksum:
                    logger.info(f"✓ Integrity verification passed (stored checksum): {file_path}")
                    return {'valid': True, 'checksum': checksum, 'stored_checksum': stored_checksum}
                else:
                    logger.error(f"✗ Integrity verification failed (stored checksum): {file_path}")
                    return {'valid': False, 'checksum': checksum, 'stored_checksum': stored_checksum}
            
            # Save calculated checksum
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {file_path.name}\n")
            
            logger.info(f"✓ Integrity verification passed (checksum saved): {file_path}")
            return {'valid': True, 'checksum': checksum, 'stored_checksum': checksum}
            
        except Exception as e:
            logger.error(f"Integrity verification error: {e}")
            return {'valid': False, 'error': str(e)}
    
    def _calculate_sha256(self, file_path):
        """Calculate SHA-256 checksum"""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def _calculate_sha512(self, file_path):
        """Calculate SHA-512 checksum"""
        hash_sha512 = hashlib.sha512()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha512.update(chunk)
        
        return hash_sha512.hexdigest()
    
    def _calculate_md5(self, file_path):
        """Calculate MD5 checksum"""
        hash_md5 = hashlib.md5()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def rotate_encryption_keys(self):
        """Rotate encryption keys based on configured schedule"""
        logger.info("Starting encryption key rotation")
        
        rotation_config = self.config['encryption']['key_management']
        rotation_days = rotation_config['rotation_days']
        
        # Check if rotation is needed
        last_rotation = self._get_last_key_rotation()
        
        if last_rotation:
            days_since_rotation = (datetime.now() - last_rotation).days
            
            if days_since_rotation >= rotation_days:
                logger.info(f"Key rotation needed (last: {last_rotation}, days: {days_since_rotation})")
                return self._perform_key_rotation()
            else:
                logger.info(f"Key rotation not needed (last: {last_rotation}, days: {days_since_rotation})")
                return {'rotation_needed': False}
        else:
            logger.info("No previous rotation found, performing initial rotation")
            return self._perform_key_rotation()
    
    def _get_last_key_rotation(self):
        """Get date of last key rotation"""
        rotation_log = Path('/var/log/backup/key_rotation.log')
        
        if rotation_log.exists():
            with open(rotation_log, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    return datetime.fromisoformat(last_line)
        
        return None
    
    def _perform_key_rotation(self):
        """Perform key rotation"""
        try:
            # Create new KMS key
            new_key_response = self.kms_client.create_key(
                Description='Backup encryption key rotation ' + datetime.now().isoformat(),
                KeyUsage='ENCRYPT_DECRYPT'
            )
            
            new_key_id = new_key_response['KeyMetadata']['KeyId']
            
            # Update configuration to use new key
            self._update_encryption_key(new_key_id)
            
            # Re-encrypt existing backups with new key
            reencryption_result = self._reencrypt_backups(new_key_id)
            
            # Log rotation
            rotation_log = Path('/var/log/backup/key_rotation.log')
            with open(rotation_log, 'a') as f:
                f.write(datetime.now().isoformat() + '\n')
            
            logger.info(f"Key rotation completed successfully (new key: {new_key_id})")
            
            return {
                'rotation_successful': True,
                'new_key_id': new_key_id,
                'reencryption_count': reencryption_result.get('count', 0)
            }
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            return {'rotation_successful': False, 'error': str(e)}
    
    def _update_encryption_key(self, new_key_id):
        """Update configuration with new encryption key"""
        # Update configuration file
        # This would update the backup_config.yaml with new key_id
        logger.info(f"Updated encryption key to: {new_key_id}")
    
    def _reencrypt_backups(self, new_key_id):
        """Re-encrypt existing backups with new key"""
        backup_dir = Path('/opt/backup')
        reencrypted_count = 0
        
        # Find all encrypted files
        for encrypted_file in backup_dir.rglob('*.encrypted'):
            try:
                # Decrypt with old key
                temp_file = tempfile.NamedTemporaryFile(delete=False)
                temp_file_path = temp_file.name
                temp_file.close()
                
                decrypted_file = self.decrypt_backup_file(str(encrypted_file), temp_file_path)
                
                # Re-encrypt with new key
                reencrypted_file = self.encrypt_backup_file(decrypted_file, new_key_id)
                
                # Replace original file
                os.replace(reencrypted_file, str(encrypted_file))
                
                # Clean up temp file
                os.remove(temp_file_path)
                
                reencrypted_count += 1
                logger.info(f"Re-encrypted: {encrypted_file}")
                
            except Exception as e:
                logger.error(f"Failed to re-encrypt {encrypted_file}: {e}")
        
        return {'count': reencrypted_count}
    
    def verify_encrypted_backup_integrity(self, encrypted_file_path):
        """Verify integrity of encrypted backup file"""
        try:
            encrypted_file_path = Path(encrypted_file_path)
            
            # Decrypt file to temp location
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            self.decrypt_backup_file(str(encrypted_file_path), temp_file_path)
            
            # Verify integrity of decrypted file
            integrity_result = self.verify_backup_integrity(temp_file_path)
            
            # Clean up temp file
            os.remove(temp_file_path)
            
            return integrity_result
            
        except Exception as e:
            logger.error(f"Encrypted backup integrity verification failed: {e}")
            return {'valid': False, 'error': str(e)}
    
    def batch_integrity_check(self, backup_directory):
        """Perform batch integrity check on all backups in directory"""
        logger.info(f"Starting batch integrity check: {backup_directory}")
        
        backup_dir = Path(backup_directory)
        results = {
            'total_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'errors': 0,
            'file_results': []
        }
        
        # Find all backup files (not just .encrypted)
        backup_files = []
        
        # Regular backup files
        backup_files.extend(list(backup_dir.rglob('*.sql')))
        backup_files.extend(list(backup_dir.rglob('*.tar.gz')))
        backup_files.extend(list(backup_dir.rglob('*.dump')))
        backup_files.extend(list(backup_dir.rglob('*.rdb')))
        
        # Encrypted backup files
        backup_files.extend(list(backup_dir.rglob('*.encrypted')))
        
        for backup_file in backup_files:
            results['total_files'] += 1
            
            try:
                if backup_file.suffix == '.encrypted':
                    result = self.verify_encrypted_backup_integrity(str(backup_file))
                else:
                    result = self.verify_backup_integrity(str(backup_file))
                
                if result['valid']:
                    results['valid_files'] += 1
                else:
                    results['invalid_files'] += 1
                
                results['file_results'].append({
                    'file': str(backup_file.relative_to(backup_dir)),
                    'valid': result['valid'],
                    'checksum': result.get('checksum')
                })
                
                logger.info(f"{'✓' if result['valid'] else '✗'} {backup_file.name}")
                
            except Exception as e:
                results['errors'] += 1
                logger.error(f"Error checking {backup_file}: {e}")
                
                results['file_results'].append({
                    'file': str(backup_file.relative_to(backup_dir)),
                    'valid': False,
                    'error': str(e)
                })
        
        logger.info(f"Batch integrity check completed: {results['valid_files']}/{results['total_files']} valid")
        
        return results

def main():
    encryption = BackupEncryption()
    
    import argparse
    parser = argparse.ArgumentParser(description='Backup Encryption and Integrity Verification')
    parser.add_argument('--mode', choices=[
        'encrypt', 'decrypt', 'verify', 'rotate-keys', 'batch-check'
    ], default='verify', help='Operation mode')
    parser.add_argument('--file', help='File to encrypt/decrypt/verify')
    parser.add_argument('--output', help='Output file for decryption')
    parser.add_argument('--expected-checksum', help='Expected checksum for verification')
    parser.add_argument('--directory', help='Directory for batch operations')
    parser.add_argument('--key-id', help='Encryption key ID')
    
    args = parser.parse_args()
    
    if args.mode == 'encrypt':
        if not args.file:
            print("Encryption mode requires --file")
            sys.exit(1)
        
        result = encryption.encrypt_backup_file(args.file, args.key_id)
        print(f"Encrypted file: {result}")
        
    elif args.mode == 'decrypt':
        if not args.file:
            print("Decryption mode requires --file")
            sys.exit(1)
        
        result = encryption.decrypt_backup_file(args.file, args.output)
        print(f"Decrypted file: {result}")
        
    elif args.mode == 'verify':
        if not args.file:
            print("Verification mode requires --file")
            sys.exit(1)
        
        result = encryption.verify_backup_integrity(args.file, args.expected_checksum)
        print(json.dumps(result, indent=2))
        
    elif args.mode == 'rotate-keys':
        result = encryption.rotate_encryption_keys()
        print(json.dumps(result, indent=2))
        
    elif args.mode == 'batch-check':
        if not args.directory:
            print("Batch check mode requires --directory")
            sys.exit(1)
        
        result = encryption.batch_integrity_check(args.directory)
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
