"""
Example: Basic Authentication Flow
Demonstrates complete authentication workflow
"""

from security import SecuritySystem, Role, KeyType

def main():
    # Initialize security system
    security_system = SecuritySystem()
    
    print("=== Security System Example ===\n")
    
    # 1. User Authentication
    print("1. User Authentication")
    auth_result = security_system.authenticate_user(
        username="john_doe",
        password="password123",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    )
    
    if auth_result['success']:
        print(f"✓ Authentication successful!")
        print(f"  User ID: {auth_result['user_id']}")
        print(f"  Role: {auth_result['role']}")
        print(f"  Permissions: {auth_result['permissions']}")
        print(f"  Access Token: {auth_result['access_token'][:50]}...")
        
        access_token = auth_result['access_token']
        
        # 2. Token Validation
        print("\n2. Token Validation")
        validation = security_system.validate_token(access_token)
        print(f"✓ Token valid: {validation['valid']}")
        print(f"  User: {validation.get('user_id')}")
        print(f"  Role: {validation.get('role')}")
        
        # 3. Request Processing
        print("\n3. Request Processing")
        request_data = {
            'method': 'GET',
            'path': '/api/users',
            'headers': {
                'authorization': f"Bearer {access_token}",
                'content-type': 'application/json',
                'user-agent': 'ExampleApp/1.0'
            },
            'ip_address': '192.168.1.100'
        }
        
        result = security_system.process_request(request_data)
        
        if result['allowed']:
            print("✓ Request authorized successfully")
            print(f"  User ID: {result['user_id']}")
            print(f"  Risk Score: {result.get('risk_score', 0)}")
        else:
            print(f"✗ Request denied: {result.get('error')}")
        
        # 4. API Key Creation
        print("\n4. API Key Creation")
        api_key_result = security_system.create_api_key(
            name="Mobile App API",
            key_type=KeyType.STANDARD,
            scopes=["read", "write"],
            created_by=auth_result['user_id'],
            expiry_days=90
        )
        
        if api_key_result['success']:
            print("✓ API key created successfully!")
            print(f"  API Key: {api_key_result['api_key'][:50]}...")
            print(f"  Key ID: {api_key_result['key_id']}")
            
            # 5. API Key Usage
            print("\n5. API Key Usage")
            api_request = {
                'method': 'POST',
                'path': '/api/data',
                'api_key': api_key_result['api_key'],
                'headers': {
                    'content-type': 'application/json'
                },
                'body': '{"action": "create", "data": "test"}',
                'ip_address': '192.168.1.100'
            }
            
            api_result = security_system.process_request(api_request)
            
            if api_result['allowed']:
                print("✓ API request authorized")
                print(f"  Key Type: {api_result['auth_info']['key_type']}")
                print(f"  Scopes: {api_result['auth_info']['scopes']}")
            else:
                print(f"✗ API request denied: {api_result.get('error')}")
        
        # 6. Security Analytics
        print("\n6. Security Analytics")
        analytics = security_system.get_security_analytics()
        
        print("System Statistics:")
        print(f"  Total API Keys: {analytics['api_keys']['total_keys']}")
        print(f"  Active Sessions: {analytics['active_sessions']}")
        print(f"  Audit Events: {analytics['audit_logs']['total_events']}")
        
        # 7. Security Status
        print("\n7. System Health Check")
        status = security_system.get_security_status()
        
        print("Component Status:")
        for component, info in status['components'].items():
            status_icon = "✓" if info['status'] == 'operational' else "✗"
            print(f"  {status_icon} {component.title()}: {info['status']}")
    
    else:
        print(f"✗ Authentication failed: {auth_result['error']}")

if __name__ == "__main__":
    main()
