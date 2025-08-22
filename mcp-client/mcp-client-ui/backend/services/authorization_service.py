"""
Authorization Service for group-based access control.
"""

import logging
from typing import Optional, Dict, List
from models.auth_models import UserClaims


class AuthorizationService:
    """Service for handling group-based authorization and access control."""
    
    def __init__(self):
        """Initialize the Authorization Service."""
        self.logger = logging.getLogger(__name__)
        
        # In-memory storage for project access mappings
        self._project_access: Dict[str, List] = {}
        
        # Group permission mappings
        self._group_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_groups'],
            'developer': ['read', 'write'],
            'viewer': ['read']
        }
    
    def check_permission(self, user_claims: UserClaims, resource: str, action: str) -> bool:
        """Check if a user has permission to perform an action on a resource."""
        # Admin users have all permissions
        if 'admin' in user_claims.groups:
            return True
        
        # Parse resource type and ID
        if ':' not in resource:
            return False
        
        resource_type, resource_id = resource.split(':', 1)
        
        # Check permissions based on resource type
        if resource_type == 'project':
            return self._check_project_permission(user_claims, resource_id, action)
        elif resource_type in ['user', 'group']:
            return 'admin' in user_claims.groups
        
        return False
    
    def _check_project_permission(self, user_claims: UserClaims, project_id: str, action: str) -> bool:
        """Check if user has permission to perform action on a project."""
        access_level = self.get_user_project_access(user_claims, project_id)
        
        if not access_level:
            return False
        
        # Define action requirements
        action_requirements = {
            'read': ['read', 'write', 'admin'],
            'write': ['write', 'admin'],
            'delete': ['admin'],
            'manage': ['admin']
        }
        
        required_levels = action_requirements.get(action, [])
        return access_level in required_levels
    
    def get_user_project_access(self, user_claims: UserClaims, project_id: str) -> Optional[str]:
        """Get the highest access level a user has to a specific project."""
        # Admin users have admin access to all projects
        if 'admin' in user_claims.groups:
            return 'admin'
        
        if project_id not in self._project_access:
            return None
        
        # Find highest access level from user's groups
        access_levels = []
        for access in self._project_access[project_id]:
            if access.get('group_name') in user_claims.groups:
                access_levels.append(access.get('access_level'))
        
        if not access_levels:
            return None
        
        # Return highest access level (admin > write > read)
        if 'admin' in access_levels:
            return 'admin'
        elif 'write' in access_levels:
            return 'write'
        elif 'read' in access_levels:
            return 'read'
        
        return None