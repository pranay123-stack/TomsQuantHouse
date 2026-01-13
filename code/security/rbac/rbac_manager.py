"""
Role-Based Access Control (RBAC) System
Implements permissions, roles, and access control logic
"""

from enum import Enum
from typing import List, Dict, Set, Optional, Any
import json
import copy


class Permission(Enum):
    """System permissions"""
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_LIST = "user:list"
    
    # Authentication
    AUTH_LOGIN = "auth:login"
    AUTH_REFRESH = "auth:refresh"
    AUTH_LOGOUT = "auth:logout"
    
    # Admin operations
    ADMIN_ACCESS = "admin:access"
    ADMIN_LOGS = "admin:logs"
    ADMIN_CONFIG = "admin:config"
    
    # API management
    API_CREATE = "api:create"
    API_READ = "api:read"
    API_UPDATE = "api:update"
    API_DELETE = "api:delete"
    
    # Data operations
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"
    DATA_BACKUP = "data:backup"
    
    # System operations
    SYSTEM_STATUS = "system:status"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_MAINTENANCE = "system:maintenance"


class Role(Enum):
    """System roles"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    API_CLIENT = "api_client"
    AUDITOR = "auditor"


class Resource(Enum):
    """System resources"""
    USERS = "users"
    AUTH = "auth"
    ADMIN = "admin"
    API = "api"
    DATA = "data"
    SYSTEM = "system"
    AUDIT = "audit"


class RBACConfig:
    """RBAC Configuration"""
    
    # Role hierarchy (higher roles inherit lower role permissions)
    ROLE_HIERARCHY = {
        Role.SUPER_ADMIN: [Role.ADMIN, Role.USER, Role.AUDITOR],
        Role.ADMIN: [Role.USER],
        Role.USER: [Role.GUEST],
        Role.GUEST: [],
        Role.API_CLIENT: [],
        Role.AUDITOR: []
    }
    
    # Default role permissions
    ROLE_PERMISSIONS = {
        Role.SUPER_ADMIN: set(Permission),
        Role.ADMIN: {
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.USER_LIST,
            Permission.ADMIN_ACCESS,
            Permission.API_CREATE,
            Permission.API_READ,
            Permission.API_UPDATE,
            Permission.API_DELETE,
            Permission.DATA_EXPORT,
            Permission.DATA_IMPORT,
            Permission.DATA_BACKUP,
            Permission.SYSTEM_STATUS,
            Permission.SYSTEM_METRICS
        },
        Role.USER: {
            Permission.USER_READ,
            Permission.AUTH_LOGIN,
            Permission.AUTH_REFRESH,
            Permission.AUTH_LOGOUT,
            Permission.API_READ
        },
        Role.GUEST: {
            Permission.AUTH_LOGIN
        },
        Role.API_CLIENT: {
            Permission.API_READ
        },
        Role.AUDITOR: {
            Permission.ADMIN_LOGS,
            Permission.ADMIN_ACCESS,
            Permission.SYSTEM_STATUS
        }
    }


class PermissionChecker:
    """Permission checking utility"""
    
    def __init__(self):
        self.role_permissions = copy.deepcopy(RBACConfig.ROLE_PERMISSIONS)
        self._build_inherited_permissions()
    
    def _build_inherited_permissions(self):
        """Build permission inheritance from role hierarchy"""
        for role, inherited_roles in RBACConfig.ROLE_HIERARCHY.items():
            for inherited_role in inherited_roles:
                self.role_permissions[role].update(
                    self.role_permissions[inherited_role]
                )
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """Get all permissions for a role (including inherited)"""
        return self.role_permissions.get(role, set())
    
    def check_permission(self, user_permissions: Set[Permission], 
                        required_permission: Permission) -> bool:
        """Check if user has required permission"""
        return required_permission in user_permissions
    
    def check_permissions(self, user_permissions: Set[Permission],
                         required_permissions: List[Permission]) -> bool:
        """Check if user has all required permissions"""
        return all(perm in user_permissions for perm in required_permissions)


class ResourceAccess:
    """Resource-based access control"""
    
    RESOURCE_PERMISSIONS = {
        Resource.USERS: {
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.USER_LIST
        },
        Resource.AUTH: {
            Permission.AUTH_LOGIN,
            Permission.AUTH_REFRESH,
            Permission.AUTH_LOGOUT
        },
        Resource.ADMIN: {
            Permission.ADMIN_ACCESS,
            Permission.ADMIN_LOGS,
            Permission.ADMIN_CONFIG
        },
        Resource.API: {
            Permission.API_CREATE,
            Permission.API_READ,
            Permission.API_UPDATE,
            Permission.API_DELETE
        },
        Resource.DATA: {
            Permission.DATA_EXPORT,
            Permission.DATA_IMPORT,
            Permission.DATA_BACKUP
        },
        Resource.SYSTEM: {
            Permission.SYSTEM_STATUS,
            Permission.SYSTEM_METRICS,
            Permission.SYSTEM_MAINTENANCE
        },
        Resource.AUDIT: {
            Permission.ADMIN_LOGS
        }
    }
    
    @classmethod
    def get_resource_permissions(cls, resource: Resource) -> Set[Permission]:
        """Get permissions associated with a resource"""
        return cls.RESOURCE_PERMISSIONS.get(resource, set())
    
    @classmethod
    def check_resource_access(cls, user_permissions: Set[Permission],
                            resource: Resource,
                            action: Permission) -> bool:
        """Check access to a resource action"""
        resource_perms = cls.get_resource_permissions(resource)
        return action in user_permissions and action in resource_perms


class RBACManager:
    """Main RBAC Manager"""
    
    def __init__(self):
        self.permission_checker = PermissionChecker()
        self.user_roles = {}  # In production, store in database
        self.user_permissions = {}  # Cache for performance
    
    def assign_role(self, user_id: str, role: Role) -> bool:
        """Assign role to user"""
        self.user_roles[user_id] = role
        # Clear permission cache
        self.user_permissions.pop(user_id, None)
        return True
    
    def revoke_role(self, user_id: str, role: Role) -> bool:
        """Revoke role from user"""
        if user_id in self.user_roles and self.user_roles[user_id] == role:
            del self.user_roles[user_id]
            # Clear permission cache
            self.user_permissions.pop(user_id, None)
            return True
        return False
    
    def get_user_role(self, user_id: str) -> Optional[Role]:
        """Get user's role"""
        return self.user_roles.get(user_id)
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for user"""
        if user_id in self.user_permissions:
            return self.user_permissions[user_id]
        
        role = self.get_user_role(user_id)
        if role:
            permissions = self.permission_checker.get_role_permissions(role)
            self.user_permissions[user_id] = permissions
            return permissions
        
        return set()
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission"""
        user_permissions = self.get_user_permissions(user_id)
        return self.permission_checker.check_permission(user_permissions, permission)
    
    def check_permissions(self, user_id: str, 
                         permissions: List[Permission]) -> bool:
        """Check if user has all required permissions"""
        user_permissions = self.get_user_permissions(user_id)
        return self.permission_checker.check_permissions(user_permissions, permissions)
    
    def check_resource_access(self, user_id: str, resource: Resource, 
                             action: Permission) -> bool:
        """Check resource-based access"""
        user_permissions = self.get_user_permissions(user_id)
        return ResourceAccess.check_resource_access(
            user_permissions, resource, action
        )
    
    def get_authorized_resources(self, user_id: str) -> Dict[Resource, Set[Permission]]:
        """Get all resources and actions user can access"""
        user_permissions = self.get_user_permissions(user_id)
        authorized = {}
        
        for resource in Resource:
            resource_perms = ResourceAccess.get_resource_permissions(resource)
            authorized_perms = user_permissions.intersection(resource_perms)
            if authorized_perms:
                authorized[resource] = authorized_perms
        
        return authorized
    
    def create_role_permissions_matrix(self) -> Dict[str, Dict[str, bool]]:
        """Create role-permissions matrix for admin interface"""
        matrix = {}
        
        for role in Role:
            role_perms = self.permission_checker.get_role_permissions(role)
            matrix[role.value] = {}
            
            for permission in Permission:
                matrix[role.value][permission.value] = permission in role_perms
        
        return matrix
    
    def validate_role_assignment(self, user_id: str, role: Role) -> Dict[str, Any]:
        """Validate if role can be assigned to user"""
        validation = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check for conflicting roles
        current_role = self.get_user_role(user_id)
        if current_role and current_role != role:
            # Check role hierarchy
            if role in RBACConfig.ROLE_HIERARCHY.get(current_role, []):
                validation['warnings'].append(
                    f"Assigning {role.value} is a downgrade from {current_role.value}"
                )
            elif current_role in RBACConfig.ROLE_HIERARCHY.get(role, []):
                validation['warnings'].append(
                    f"Assigning {role.value} will elevate privileges"
                )
        
        # Check minimum requirements for sensitive roles
        if role == Role.SUPER_ADMIN:
            # In production, check audit logs, recent activity, etc.
            pass
        
        return validation


class DecoratorHelpers:
    """Helper decorators for RBAC"""
    
    @staticmethod
    def require_permission(permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func):
            def wrapper(self, user_id: str, *args, **kwargs):
                rbac_manager = RBACManager()
                if not rbac_manager.check_permission(user_id, permission):
                    raise PermissionError(f"Permission denied: {permission.value}")
                return func(self, user_id, *args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def require_role(role: Role):
        """Decorator to require specific role"""
        def decorator(func):
            def wrapper(self, user_id: str, *args, **kwargs):
                rbac_manager = RBACManager()
                user_role = rbac_manager.get_user_role(user_id)
                if user_role != role:
                    raise PermissionError(f"Role required: {role.value}")
                return func(self, user_id, *args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def require_any_permission(permissions: List[Permission]):
        """Decorator to require any of the specified permissions"""
        def decorator(func):
            def wrapper(self, user_id: str, *args, **kwargs):
                rbac_manager = RBACManager()
                if not any(rbac_manager.check_permission(user_id, perm) 
                          for perm in permissions):
                    raise PermissionError(f"Any of these permissions required: {[p.value for p in permissions]}")
                return func(self, user_id, *args, **kwargs)
            return wrapper
        return decorator


# Example usage and testing
if __name__ == "__main__":
    # Initialize RBAC manager
    rbac = RBACManager()
    
    # Assign roles
    rbac.assign_role("user123", Role.ADMIN)
    rbac.assign_role("user456", Role.USER)
    
    # Check permissions
    print(f"User123 permissions: {[p.value for p in rbac.get_user_permissions('user123')]}")
    print(f"User456 permissions: {[p.value for p in rbac.get_user_permissions('user456')]}")
    
    # Test permission checking
    print(f"User123 can create users: {rbac.check_permission('user123', Permission.USER_CREATE)}")
    print(f"User456 can create users: {rbac.check_permission('user456', Permission.USER_CREATE)}")
    
    # Test resource access
    print(f"User123 can access users resource: {rbac.check_resource_access('user123', Resource.USERS, Permission.USER_CREATE)}")
    
    # Generate permissions matrix
    matrix = rbac.create_role_permissions_matrix()
    print("\nRole Permissions Matrix (first 3 roles):")
    for role, perms in list(matrix.items())[:3]:
        print(f"{role}: {sum(perms.values())} permissions")
