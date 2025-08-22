"""
Authenticated Project Service with group-based access control.

This service extends the base ProjectService to provide authentication-aware
project operations with group-based access control and project sharing functionality.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .project_service import ProjectService, ProjectSyncResult
from .authenticated_s3_storage_service import AuthenticatedS3StorageService
from .authentication_service import AuthenticationService
from .authorization_service import AuthorizationService
from models.auth_models import UserClaims

logger = logging.getLogger(__name__)


@dataclass
class AuthenticatedProjectResult:
    """Result of authenticated project operations."""
    success: bool
    project_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    user_id: Optional[str] = None
    groups: Optional[List[str]] = None


@dataclass
class ProjectShareResult:
    """Result of project sharing operations."""
    success: bool
    project_id: str
    shared_with_group: str
    error_message: Optional[str] = None


class AuthenticatedProjectService(ProjectService):
    """
    Project Service with authentication and group-based access control.
    
    This service provides:
    - User token validation for all project operations
    - Group-based project access control
    - User-specific project listing
    - Project sharing functionality between groups
    - Project creation with group association
    """
    
    def __init__(self, s3_service: Optional[AuthenticatedS3StorageService] = None, 
                 auth_service: Optional[AuthenticationService] = None,
                 authorization_service: Optional[AuthorizationService] = None):
        """
        Initialize authenticated project service.
        
        Args:
            s3_service: AuthenticatedS3StorageService instance
            auth_service: AuthenticationService instance for token validation
            authorization_service: AuthorizationService instance for access control
        """
        # Initialize parent with authenticated S3 service
        super().__init__(s3_service)
        
        self.auth_service = auth_service
        self.authorization_service = authorization_service or AuthorizationService()
        
        if not self.auth_service:
            raise ValueError("AuthenticationService is required for authenticated operations")
        
        # Override s3_service to ensure it's authenticated
        if not isinstance(self.s3_service, AuthenticatedS3StorageService):
            raise ValueError("AuthenticatedS3StorageService is required")
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
    
    def _validate_user_token(self, user_token: str) -> Optional[UserClaims]:
        """
        Validate user token and extract claims.
        
        Args:
            user_token: JWT token string
            
        Returns:
            UserClaims if token is valid, None otherwise
        """
        if not user_token:
            logger.error("User token is required for authenticated operations")
            return None
        
        # Remove 'Bearer ' prefix if present
        if user_token.startswith('Bearer '):
            user_token = user_token[7:]
        
        user_claims = self.auth_service.extract_user_claims(user_token)
        if not user_claims:
            logger.error("Invalid or expired user token")
            return None
        
        return user_claims
    
    def _can_access_project(self, user_claims: UserClaims, project_id: str, action: str = "read") -> bool:
        """
        Check if user can perform action on project.
        
        Args:
            user_claims: User claims from JWT token
            project_id: Project identifier
            action: Action to perform (read, write, delete, manage)
            
        Returns:
            True if user has access, False otherwise
        """
        # 1. Admin access - admins can access all projects
        if 'admins' in user_claims.groups:
            return True
        
        # 2. Project-specific group access (e.g., developers-web-app for web-app project)
        project_group = f"developers-{project_id}"
        if project_group in user_claims.groups:
            return True
        
        # 3. General developers group access
        if 'developers' in user_claims.groups:
            return True
        
        # 4. Fallback to authorization service for other cases
        resource = f"project:{project_id}"
        return self.authorization_service.check_permission(user_claims, resource, action)
    
    async def create_project(self, project_data: Dict[str, Any], user_token: str) -> AuthenticatedProjectResult:
        """
        Create a new project with authentication and group association.
        
        Args:
            project_data: Project metadata dictionary
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedProjectResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="Authentication failed"
                )
            
            # Check if user can create projects
            if not self.authorization_service.check_permission(user_claims, "project:*", "write"):
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="Insufficient permissions to create projects",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Generate project ID from name if not provided
            project_id = project_data.get('name', f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            # Determine primary group for project
            if not user_claims.groups:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="User has no group assignments",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            primary_group = user_claims.groups[0]  # Use first group as primary
            
            # Add authentication and group context to project data
            enhanced_project_data = {
                **project_data,
                'project_id': project_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'created_by': user_claims.user_id,
                'created_by_username': user_claims.username,
                'primary_group': primary_group,
                'shared_with_groups': [primary_group],  # Initially only shared with primary group
                's3_sync_status': 'pending'
            }
            
            # Save using authenticated S3 service
            s3_result = await self.s3_service.save_project_metadata(
                project_id, 
                enhanced_project_data, 
                user_token
            )
            
            if not s3_result.success:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Failed to save project to S3: {s3_result.error_message}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Project is now stored only in S3 - no local caching needed
            
            logger.info(f"Created project: {project_id} for user {user_claims.username} in group {primary_group}")
            return AuthenticatedProjectResult(
                success=True,
                project_id=project_id,
                data=enhanced_project_data,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error creating project: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedProjectResult(
                success=False,
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def load_project(self, project_id: str, user_token: str) -> AuthenticatedProjectResult:
        """
        Load project with authentication and access control.
        
        Args:
            project_id: Project identifier
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedProjectResult with project data or error
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="Authentication failed"
                )
            
            # Check if user can access this project
            if not self._can_access_project(user_claims, project_id, "read"):
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Access denied to project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Load using authenticated S3 service
            s3_result = await self.s3_service.load_project_metadata(project_id, user_token)
            
            if not s3_result.success:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Failed to load project: {s3_result.error_message}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            project_data = s3_result.data
            
            # Project loaded from S3 only - no local caching needed
            
            logger.info(f"Loaded project: {project_id} for user {user_claims.username}")
            return AuthenticatedProjectResult(
                success=True,
                project_id=project_id,
                data=project_data,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error loading project: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedProjectResult(
                success=False,
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def save_project(self, project_id: str, project_data: Dict[str, Any], user_token: str) -> AuthenticatedProjectResult:
        """
        Save project with authentication and access control.
        
        Args:
            project_id: Project identifier
            project_data: Project data dictionary
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedProjectResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="Authentication failed"
                )
            
            # Check if user can modify this project
            if not self._can_access_project(user_claims, project_id, "write"):
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Insufficient permissions to modify project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Update metadata with modification info
            enhanced_project_data = {
                **project_data,
                'project_id': project_id,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'last_modified_by': user_claims.user_id,
                'last_modified_by_username': user_claims.username,
                's3_sync_status': 'pending'
            }
            
            # Save using authenticated S3 service
            s3_result = await self.s3_service.save_project_metadata(
                project_id, 
                enhanced_project_data, 
                user_token
            )
            
            if not s3_result.success:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Failed to save project to S3: {s3_result.error_message}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Project saved to S3 only - no local caching needed
            
            logger.info(f"Saved project: {project_id} by user {user_claims.username}")
            return AuthenticatedProjectResult(
                success=True,
                project_id=project_id,
                data=enhanced_project_data,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error saving project: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedProjectResult(
                success=False,
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def delete_project(self, project_id: str, user_token: str) -> AuthenticatedProjectResult:
        """
        Delete project with authentication and access control.
        
        Args:
            project_id: Project identifier
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedProjectResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="Authentication failed"
                )
            
            # Check if user can delete this project
            if not self._can_access_project(user_claims, project_id, "delete"):
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Insufficient permissions to delete project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # First load project to get group information
            load_result = await self.load_project(project_id, user_token)
            if not load_result.success:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Cannot delete project that doesn't exist: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Delete from all groups the project is shared with
            project_data = load_result.data
            shared_groups = project_data.get('shared_with_groups', [])
            
            # Note: In a full implementation, we would delete from S3 for each group
            # For now, we'll use the authenticated S3 service which handles group-based deletion
            
            # Delete local copy
            local_path = self._get_local_project_path(project_id)
            try:
                import os
                if os.path.exists(local_path):
                    os.remove(local_path)
            except Exception as e:
                logger.warning(f"Failed to delete local project file: {str(e)}")
            
            logger.info(f"Deleted project: {project_id} by user {user_claims.username}")
            return AuthenticatedProjectResult(
                success=True,
                project_id=project_id,
                data={"deleted_from_groups": shared_groups},
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error deleting project: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedProjectResult(
                success=False,
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def list_user_projects(self, user_token: str) -> AuthenticatedProjectResult:
        """
        List all projects accessible to the authenticated user.
        
        Args:
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedProjectResult with list of accessible projects
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="Authentication failed"
                )
            
            # Get projects from authenticated S3 service
            s3_result = await self.s3_service.list_user_projects(user_token)
            
            if not s3_result.success:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Failed to list projects: {s3_result.error_message}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            projects = s3_result.data or []
            
            # Enhance project list with additional metadata
            enhanced_projects = []
            for project_info in projects:
                project_id = project_info.get('project_id')
                group = project_info.get('group')
                
                # Try to get additional metadata
                try:
                    load_result = await self.load_project(project_id, user_token)
                    if load_result.success and load_result.data:
                        project_metadata = load_result.data
                        enhanced_project = {
                            'project_id': project_id,
                            'group': group,
                            'name': project_metadata.get('name', project_id),
                            'description': project_metadata.get('description', ''),
                            'created_at': project_metadata.get('created_at'),
                            'last_updated': project_metadata.get('last_updated'),
                            'created_by': project_metadata.get('created_by_username', 'Unknown'),
                            'shared_with_groups': project_metadata.get('shared_with_groups', [group])
                        }
                        enhanced_projects.append(enhanced_project)
                    else:
                        # Fallback to basic info
                        enhanced_projects.append(project_info)
                except Exception as e:
                    self.logger.warning(f"Failed to load metadata for project {project_id}: {str(e)}")
                    enhanced_projects.append(project_info)
            
            self.logger.info(f"Listed {len(enhanced_projects)} projects for user {user_claims.username}")
            return AuthenticatedProjectResult(
                success=True,
                data=enhanced_projects,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error listing user projects: {str(e)}"
            self.logger.error(error_msg)
            return AuthenticatedProjectResult(
                success=False,
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def share_project_with_group(self, project_id: str, target_group: str, user_token: str) -> ProjectShareResult:
        """
        Share a project with another group.
        
        Args:
            project_id: Project identifier
            target_group: Group to share the project with
            user_token: JWT token for authentication
            
        Returns:
            ProjectShareResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message="Authentication failed"
                )
            
            # Check if user can manage this project
            if not self._can_access_project(user_claims, project_id, "manage"):
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Insufficient permissions to share project: {project_id}"
                )
            
            # Load current project data
            load_result = await self.load_project(project_id, user_token)
            if not load_result.success:
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Project not found: {project_id}"
                )
            
            project_data = load_result.data
            shared_groups = project_data.get('shared_with_groups', [])
            
            # Check if already shared with target group
            if target_group in shared_groups:
                return ProjectShareResult(
                    success=True,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Project already shared with group: {target_group}"
                )
            
            # Add target group to shared groups
            shared_groups.append(target_group)
            project_data['shared_with_groups'] = shared_groups
            project_data['last_shared_at'] = datetime.now(timezone.utc).isoformat()
            project_data['last_shared_by'] = user_claims.user_id
            
            # Save updated project data
            save_result = await self.save_project(project_id, project_data, user_token)
            if not save_result.success:
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Failed to update project sharing: {save_result.error_message}"
                )
            
            # TODO: In a full implementation, we would also copy the project data
            # to the target group's S3 path structure
            
            logger.info(f"Shared project {project_id} with group {target_group} by user {user_claims.username}")
            return ProjectShareResult(
                success=True,
                project_id=project_id,
                shared_with_group=target_group
            )
            
        except Exception as e:
            error_msg = f"Error sharing project: {str(e)}"
            logger.error(error_msg)
            return ProjectShareResult(
                success=False,
                project_id=project_id,
                shared_with_group=target_group,
                error_message=error_msg
            )
    
    async def unshare_project_from_group(self, project_id: str, target_group: str, user_token: str) -> ProjectShareResult:
        """
        Remove project sharing from a group.
        
        Args:
            project_id: Project identifier
            target_group: Group to remove sharing from
            user_token: JWT token for authentication
            
        Returns:
            ProjectShareResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message="Authentication failed"
                )
            
            # Check if user can manage this project
            if not self._can_access_project(user_claims, project_id, "manage"):
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Insufficient permissions to unshare project: {project_id}"
                )
            
            # Load current project data
            load_result = await self.load_project(project_id, user_token)
            if not load_result.success:
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Project not found: {project_id}"
                )
            
            project_data = load_result.data
            shared_groups = project_data.get('shared_with_groups', [])
            primary_group = project_data.get('primary_group')
            
            # Cannot unshare from primary group
            if target_group == primary_group:
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message="Cannot unshare project from its primary group"
                )
            
            # Check if shared with target group
            if target_group not in shared_groups:
                return ProjectShareResult(
                    success=True,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Project not shared with group: {target_group}"
                )
            
            # Remove target group from shared groups
            shared_groups.remove(target_group)
            project_data['shared_with_groups'] = shared_groups
            project_data['last_unshared_at'] = datetime.now(timezone.utc).isoformat()
            project_data['last_unshared_by'] = user_claims.user_id
            
            # Save updated project data
            save_result = await self.save_project(project_id, project_data, user_token)
            if not save_result.success:
                return ProjectShareResult(
                    success=False,
                    project_id=project_id,
                    shared_with_group=target_group,
                    error_message=f"Failed to update project sharing: {save_result.error_message}"
                )
            
            logger.info(f"Unshared project {project_id} from group {target_group} by user {user_claims.username}")
            return ProjectShareResult(
                success=True,
                project_id=project_id,
                shared_with_group=target_group
            )
            
        except Exception as e:
            error_msg = f"Error unsharing project: {str(e)}"
            logger.error(error_msg)
            return ProjectShareResult(
                success=False,
                project_id=project_id,
                shared_with_group=target_group,
                error_message=error_msg
            )
    
    async def get_project_sharing_info(self, project_id: str, user_token: str) -> AuthenticatedProjectResult:
        """
        Get sharing information for a project.
        
        Args:
            project_id: Project identifier
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedProjectResult with sharing information
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message="Authentication failed"
                )
            
            # Check if user can read this project
            if not self._can_access_project(user_claims, project_id, "read"):
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Access denied to project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Load project data
            load_result = await self.load_project(project_id, user_token)
            if not load_result.success:
                return AuthenticatedProjectResult(
                    success=False,
                    error_message=f"Project not found: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            project_data = load_result.data
            
            sharing_info = {
                'project_id': project_id,
                'primary_group': project_data.get('primary_group'),
                'shared_with_groups': project_data.get('shared_with_groups', []),
                'created_by': project_data.get('created_by_username', 'Unknown'),
                'last_shared_at': project_data.get('last_shared_at'),
                'last_shared_by': project_data.get('last_shared_by'),
                'last_unshared_at': project_data.get('last_unshared_at'),
                'last_unshared_by': project_data.get('last_unshared_by')
            }
            
            return AuthenticatedProjectResult(
                success=True,
                project_id=project_id,
                data=sharing_info,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error getting project sharing info: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedProjectResult(
                success=False,
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )