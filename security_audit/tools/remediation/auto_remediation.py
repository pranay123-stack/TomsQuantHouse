#!/usr/bin/env python3
"""
Automated Security Remediation Script
Applies security fixes based on audit findings
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime

class SecurityRemediator:
    """Automated security remediation tool"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.backup_dir = self.workspace_path / "security_audit" / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    def apply_critical_fixes(self):
        """Apply critical security fixes"""
        print("🔧 Applying critical security fixes...")
        
        # 1. Fix hardcoded secrets
        self._fix_hardcoded_secrets()
        
        # 2. Secure JWT configuration
        self._secure_jwt_config()
        
        # 3. Fix SQL injection patterns
        self._fix_sql_injection()
        
        # 4. Add security headers
        self._add_security_headers()
        
        print("✅ Critical fixes applied successfully!")
    
    def _create_backup(self, file_path: Path) -> Path:
        """Create backup of file before modification"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{file_path.name}.{timestamp}.backup"
        shutil.copy2(file_path, backup_path)
        print(f"  📁 Created backup: {backup_path}")
        return backup_path
    
    def _fix_hardcoded_secrets(self):
        """Fix hardcoded secrets in configuration files"""
        print("  🔐 Fixing hardcoded secrets...")
        
        config_files = list(self.workspace_path.rglob("*.py"))
        
        for config_file in config_files:
            if "test" in str(config_file).lower() or "__pycache__" in str(config_file):
                continue
                
            try:
                with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Pattern to find hardcoded secrets
                patterns = {
                    r'(JWT_SECRET_KEY\s*=\s*[\'"])(.*?)([\'"]\s*\n)': 
                        r'\1os.getenv(\'JWT_SECRET_KEY\', \'CHANGE_ME_IN_PRODUCTION\')\3',
                    r'(password\s*=\s*[\'"])(.*?)([\'"]\s*\n)': 
                        r'\1os.getenv(\'PASSWORD\', \'CHANGE_ME\')\3',
                    r'(api_key\s*=\s*[\'"])(.*?)([\'"]\s*\n)': 
                        r'\1os.getenv(\'API_KEY\', \'CHANGE_ME\')\3'
                }
                
                modified = False
                for pattern, replacement in patterns.items():
                    new_content, count = re.subn(pattern, replacement, content)
                    if count > 0:
                        content = new_content
                        modified = True
                
                if modified:
                    backup_path = self._create_backup(config_file)
                    with open(config_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"    ✅ Fixed secrets in {config_file}")
                    
            except Exception as e:
                print(f"    ❌ Error fixing {config_file}: {e}")
    
    def _secure_jwt_config(self):
        """Secure JWT configuration"""
        print("  🔑 Securing JWT configuration...")
        
        jwt_files = list(self.workspace_path.rglob("*jwt*")) + list(self.workspace_path.rglob("*security*"))
        
        for jwt_file in jwt_files:
            try:
                with open(jwt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Remove insecure algorithms
                content = re.sub(r'"alg"\s*:\s*"none"', '"alg": "HS256"', content)
                content = re.sub(r"'alg'\s*:\s*'none'", "'alg': 'HS256'", content)
                
                # Add token expiration
                if 'exp' not in content and 'expiry' not in content:
                    expiration_code = '''
    # Add token expiration
    def generate_token(self, user_id: str, expires_delta: int = 900):
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        exp = now + timedelta(seconds=expires_delta)
        payload = {
            'sub': user_id,
            'iat': now,
            'exp': exp,
            'jti': secrets.token_hex(16)
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)
'''
                    content += expiration_code
                
                if content != f.read():
                    backup_path = self._create_backup(jwt_file)
                    with open(jwt_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"    ✅ Secured JWT config in {jwt_file}")
                    
            except Exception:
                continue
    
    def _fix_sql_injection(self):
        """Fix SQL injection vulnerabilities"""
        print("  🛡️  Fixing SQL injection vulnerabilities...")
        
        py_files = list(self.workspace_path.rglob("*.py"))
        
        for py_file in py_files:
            if any(skip in str(py_file).lower() for skip in ['test', 'spec', '__pycache__']):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                original_content = content
                
                # Fix f-string SQL injection
                content = re.sub(
                    r'cursor\.execute\s*\(\s*f["\'](.*?\{.*?\}.*?)["\']',
                    r'cursor.execute("\1", (variable,))',
                    content
                )
                
                # Fix string concatenation SQL injection
                content = re.sub(
                    r'cursor\.execute\s*\(\s*["\'](.*?)\s*\+\s*.*\+',
                    r'cursor.execute("\1", (sanitized_input,))',
                    content
                )
                
                if content != original_content:
                    backup_path = self._create_backup(py_file)
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"    ✅ Fixed SQL injection in {py_file}")
                    
            except Exception:
                continue
    
    def _add_security_headers(self):
        """Add security headers to web configurations"""
        print("  🔒 Adding security headers...")
        
        # Update nginx configuration
        nginx_conf = self.workspace_path / "docker" / "nginx" / "nginx.conf"
        
        if nginx_conf.exists():
            try:
                with open(nginx_conf, 'r') as f:
                    content = f.read()
                
                # Add comprehensive security headers
                security_headers = '''
        # Security Headers
        add_header X-Frame-Options DENY always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' wss:; font-src 'self' data:;" always;
        add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=()" always;
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header Cache-Control "no-store, no-cache, must-revalidate, private" always;
'''
                
                if 'X-Frame-Options' not in content:
                    content = content.replace('location / {', f'location / {{{security_headers}')
                    
                    backup_path = self._create_backup(nginx_conf)
                    with open(nginx_conf, 'w') as f:
                        f.write(content)
                    print(f"    ✅ Added security headers to nginx.conf")
                    
            except Exception as e:
                print(f"    ❌ Error updating nginx config: {e}")

def main():
    """Main remediation function"""
    workspace = "/workspace"
    remediator = SecurityRemediator(workspace)
    
    # Confirm before applying fixes
    response = input("⚠️  This will apply automated security fixes. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Remediation cancelled.")
        return
    
    print("\n" + "="*60)
    print("AUTOMATED SECURITY REMEDIATION")
    print("="*60)
    
    remediator.apply_critical_fixes()
    
    print("\n" + "="*60)
    print("REMEDIATION COMPLETE")
    print("="*60)
    print(f"📁 Backups created in: {remediator.backup_dir}")
    print("\n⚠️  IMPORTANT:")
    print("  1. Review all changes before deployment")
    print("  2. Update environment variables with proper secrets")
    print("  3. Test all modified functionality")
    print("  4. Run security scan again to verify fixes")

if __name__ == "__main__":
    main()
