"""
Authenticated S3 Storage Service with group-based access control.

This service extends the base S3StorageService to provide authentication-aware
storage operations with group-based project access and user-specific session storage.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from .s3_storage_service import S3StorageService, S3OperationResult
from .authentication_service import AuthenticationService
from models.auth_models import UserClaims

logger = logging.getLogger(__name__)


@dataclass
class AuthenticatedS3OperationResult(S3OperationResult):
    """Extended result class with authentication context."""
    user_id: Optional[str] = None
    groups: Optional[List[str]] = None


class AuthenticatedS3StorageService(S3StorageService):
    """
    S3 Storage Service with authentication and group-based access control.
    
    This service provides:
    - Group-based S3 path structure (groups/{group-name}/projects/)
    - User token validation for all operations
    - User-specific session storage
    - Group storage management
    - Project access control based on user groups
    """
    
    def __init__(self, bucket_name: Optional[str] = None, aws_region: Optional[str] = None, 
                 auth_service: Optional[AuthenticationService] = None):
        """
        Initialize authenticated S3 storage service.
        
        Args:
            bucket_name: S3 bucket name (uses config default if None)
            aws_region: AWS region (uses config default if None)
            auth_service: AuthenticationService instance for token validation
        """
        # Initialize with default AWS credentials (from CLI/IAM role)
        super().__init__(bucket_name, aws_region)
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        self.auth_service = auth_service
        if not self.auth_service:
            raise ValueError("AuthenticationService is required for authenticated operations")
    
    def _validate_user_token(self, user_token: str) -> Optional[UserClaims]:
        """
        Validate user token and extract claims.
        
        Args:
            user_token: JWT token string
            
        Returns:
            UserClaims if token is valid, None otherwise
        """
        if not user_token:
            self.logger.error("User token is required for authenticated operations")
            return None
        
        # Remove 'Bearer ' prefix if present
        if user_token.startswith('Bearer '):
            user_token = user_token[7:]
        
        user_claims = self.auth_service.extract_user_claims(user_token)
        if not user_claims:
            self.logger.error("Invalid or expired user token")
            return None
        
        return user_claims
    
    def _generate_project_s3_key(self, project_id: str, file_type: str, filename: str = "") -> str:
        """
        Generate S3 key for project files using simple project-based structure.
        
        Args:
            project_id: Project identifier
            file_type: Type of file (metadata, generated-code, diagrams, sessions)
            filename: Optional filename for specific files
            
        Returns:
            S3 key path with project-based structure
        """
        base_key = f"projects/{project_id}"
        
        if file_type == "metadata":
            return f"{base_key}/metadata.json"
        elif file_type == "generated-code":
            if filename:
                return f"{base_key}/generated-code/{filename}"
            return f"{base_key}/generated-code/"
        elif file_type == "diagrams":
            if filename:
                return f"{base_key}/diagrams/{filename}"
            return f"{base_key}/diagrams/"
        elif file_type == "sessions":
            if filename:
                return f"{base_key}/sessions/{filename}"
            return f"{base_key}/sessions/"
        else:
            return f"{base_key}/{file_type}/{filename}" if filename else f"{base_key}/{file_type}/"
    
    def _generate_user_session_key(self, project_id: str, user_id: str) -> str:
        """
        Generate S3 key for user-specific session storage.
        
        Args:
            project_id: Project identifier
            user_id: User identifier
            
        Returns:
            S3 key path for user session data
        """
        return f"projects/{project_id}/sessions/{user_id}/conversations.json"
    
    async def _can_access_project(self, user_claims: UserClaims, project_id: str) -> bool:
        """
        Check if user can access a specific project.
        
        Args:
            user_claims: User claims from JWT token
            project_id: Project identifier
            
        Returns:
            True if user has access, False otherwise
        """
        # 1. Admin access - admins can access all projects
        if 'admins' in user_claims.groups:
            self.logger.debug(f"User {user_claims.username} has admin access to {project_id}")
            return True
        
        # 2. Project-specific group access with mapping
        # Map project IDs to their corresponding groups (only main projects)
        project_group_mapping = {
            "mobile-application-project": "developers-mobile-app",
            "web-application-project": "developers-web-app"
        }
        
        # Check if user's group matches the project
        required_group = project_group_mapping.get(project_id)
        if required_group and required_group in user_claims.groups:
            self.logger.debug(f"User {user_claims.username} has group access to {project_id} via group {required_group}")
            return True
        
        # 3. Fallback: Check project metadata for individual user assignment
        try:
            metadata_key = self._generate_project_s3_key(project_id, "metadata")
            import asyncio
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor, 
                self._sync_get_object, 
                metadata_key
            )
            
            if content:
                metadata = json.loads(content.decode('utf-8'))
                assigned_users = metadata.get('assigned_users', [])
                assigned_groups = metadata.get('assigned_groups', [])
                
                # Check if user is individually assigned
                if user_claims.username in assigned_users:
                    self.logger.debug(f"User {user_claims.username} individually assigned to project {project_id}")
                    return True
                
                # Check if any of user's groups are assigned to project
                for group in user_claims.groups:
                    if group in assigned_groups:
                        self.logger.debug(f"User {user_claims.username} has group access to project {project_id} via group {group}")
                        return True
        
        except Exception as e:
            self.logger.warning(f"Error checking project metadata for access control: {e}")
        
        self.logger.warning(f"User {user_claims.username} denied access to project {project_id}. User groups: {user_claims.groups}")
        return False
    
    async def save_project_metadata(self, project_id: str, metadata: Dict[str, Any], user_token: str) -> AuthenticatedS3OperationResult:
        """
        Save project metadata to S3 with authentication.
        
        Args:
            project_id: Project identifier
            metadata: Project metadata dictionary
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedS3OperationResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Check if user can access this project
            can_access = await self._can_access_project(user_claims, project_id)
            if not can_access:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Access denied to project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Add authentication context to metadata
            metadata_with_auth = {
                **metadata,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
                "created_by": user_claims.user_id,
                "last_modified_by": user_claims.user_id,
                "assigned_users": metadata.get("assigned_users", [user_claims.username]),
                "assigned_groups": metadata.get("assigned_groups", [])
            }
            
            # Convert to JSON bytes
            json_data = json.dumps(metadata_with_auth, indent=2).encode('utf-8')
            
            # Generate project-based S3 key
            s3_key = self._generate_project_s3_key(project_id, "metadata")
            
            # Upload to S3 asynchronously
            import asyncio
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self._executor, 
                self._sync_put_object, 
                s3_key, 
                json_data, 
                "application/json"
            )
            
            if success:
                logger.info(f"Successfully saved project metadata to S3: {project_id}")
                return AuthenticatedS3OperationResult(
                    success=True, 
                    data={"s3_key": s3_key, "project_id": project_id},
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            else:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Failed to upload metadata",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
                
        except Exception as e:
            error_msg = f"Error saving project metadata to S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def load_project_metadata(self, project_id: str, user_token: str) -> AuthenticatedS3OperationResult:
        """
        Load project metadata from S3 with authentication.
        
        Args:
            project_id: Project identifier
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedS3OperationResult with metadata or error
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Check if user can access this project
            can_access = await self._can_access_project(user_claims, project_id)
            if not can_access:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Access denied to project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Generate project-based S3 key
            s3_key = self._generate_project_s3_key(project_id, "metadata")
            
            # Download from S3 asynchronously
            import asyncio
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor, 
                self._sync_get_object, 
                s3_key
            )
            
            if content is None:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Project metadata not found: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            metadata = json.loads(content.decode('utf-8'))
            logger.info(f"Successfully loaded project metadata from S3: {project_id}")
            return AuthenticatedS3OperationResult(
                success=True, 
                data=metadata,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in project metadata: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
        except Exception as e:
            error_msg = f"Error loading project metadata from S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def list_user_projects(self, user_token: str) -> AuthenticatedS3OperationResult:
        """
        List all projects accessible to the authenticated user.
        
        Args:
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedS3OperationResult with list of project IDs
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            all_projects = []
            
            # For now, let's list all projects and filter based on access control
            # This is simpler and more reliable than trying to guess prefixes
            prefix = "projects/"
                
            self.logger.info(f"Searching for all projects with prefix: {prefix}")
            
            import asyncio
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            self.logger.info(f"Found {len(object_keys)} objects with prefix {prefix}")
            
            # Filter for project metadata.json files (not diagram metadata files)
            metadata_files = [key for key in object_keys if key.endswith('/metadata.json') and '/diagrams/' not in key]
            self.logger.info(f"Found {len(metadata_files)} metadata files: {metadata_files}")
            
            # Extract project IDs and check access for each
            seen_projects = set()  # Avoid duplicates
            
            for key in metadata_files:
                # Keys look like: projects/{project_id}/metadata.json
                parts = key.split('/')
                if parts[0] == "projects" and len(parts) >= 3:
                    project_id = parts[1]  # Get project_id from path
                    
                    # Skip if we've already processed this project
                    if project_id in seen_projects:
                        continue
                    
                    seen_projects.add(project_id)
                    self.logger.info(f"Checking access to project: {project_id}")
                    
                    # Check if user has access to this project
                    if await self._can_access_project(user_claims, project_id):
                        all_projects.append({
                            "project_id": project_id,
                            "s3_key": key
                        })
                        self.logger.info(f"User {user_claims.username} has access to project: {project_id}")
                    else:
                        self.logger.info(f"User {user_claims.username} denied access to project: {project_id}")
            
            logger.info(f"Successfully listed {len(all_projects)} projects for user {user_claims.username}")
            return AuthenticatedS3OperationResult(
                success=True, 
                data=all_projects,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error listing user projects from S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def save_user_session(self, project_id: str, user_id: str, session_data: Dict[str, Any], user_token: str) -> AuthenticatedS3OperationResult:
        """
        Save user-specific session data to S3.
        
        Args:
            project_id: Project identifier
            user_id: User identifier
            session_data: Session data dictionary
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedS3OperationResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Verify user can only save their own session data
            if user_claims.user_id != user_id:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Cannot save session data for another user",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Find which group contains this project
            project_group = None
            for group_name in user_claims.groups:
                # Check if project exists in this group
                metadata_key = self._generate_group_s3_key(group_name, project_id, "metadata")
                import asyncio
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(
                    self._executor, 
                    self._sync_get_object, 
                    metadata_key
                )
                if content is not None:
                    project_group = group_name
                    break
            
            if not project_group:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Project not found or access denied: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Add timestamp to session data
            session_with_timestamp = {
                **session_data,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "user_id": user_id,
                "project_id": project_id
            }
            
            # Convert to JSON bytes
            json_data = json.dumps(session_with_timestamp, indent=2).encode('utf-8')
            
            # Generate user session S3 key
            s3_key = self._generate_user_session_key(project_group, project_id, user_id)
            
            # Upload to S3 asynchronously
            success = await loop.run_in_executor(
                self._executor, 
                self._sync_put_object, 
                s3_key, 
                json_data, 
                "application/json"
            )
            
            if success:
                logger.info(f"Successfully saved user session to S3: {project_id}/{user_id}")
                return AuthenticatedS3OperationResult(
                    success=True, 
                    data={"s3_key": s3_key, "group": project_group},
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            else:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Failed to upload session data",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
                
        except Exception as e:
            error_msg = f"Error saving user session to S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def load_user_session(self, project_id: str, user_id: str, user_token: str) -> AuthenticatedS3OperationResult:
        """
        Load user-specific session data from S3.
        
        Args:
            project_id: Project identifier
            user_id: User identifier
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedS3OperationResult with session data or error
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Verify user can only load their own session data
            if user_claims.user_id != user_id:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Cannot load session data for another user",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Find which group contains this project
            session_data = None
            found_group = None
            
            for group_name in user_claims.groups:
                # Generate user session S3 key
                s3_key = self._generate_user_session_key(group_name, project_id, user_id)
                
                # Download from S3 asynchronously
                import asyncio
                loop = asyncio.get_event_loop()
                content = await loop.run_in_executor(
                    self._executor, 
                    self._sync_get_object, 
                    s3_key
                )
                
                if content is not None:
                    session_data = json.loads(content.decode('utf-8'))
                    found_group = group_name
                    break
            
            if session_data is None:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Session data not found: {project_id}/{user_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            logger.info(f"Successfully loaded user session from S3: {project_id}/{user_id}")
            return AuthenticatedS3OperationResult(
                success=True, 
                data=session_data,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in session data: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
        except Exception as e:
            error_msg = f"Error loading user session from S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def create_group_storage(self, group_name: str, admin_token: str) -> AuthenticatedS3OperationResult:
        """
        Create storage structure for a new group.
        
        Args:
            group_name: Name of the group
            admin_token: JWT token for admin authentication
            
        Returns:
            AuthenticatedS3OperationResult with operation status
        """
        try:
            # Validate admin token
            user_claims = self._validate_user_token(admin_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Check if user has admin privileges (admin group or specific permission)
            if 'admins' not in user_claims.groups:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Admin privileges required",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Create group configuration metadata
            group_config = {
                "group_name": group_name,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": user_claims.user_id,
                "description": f"Storage for group {group_name}",
                "project_count": 0
            }
            
            # Convert to JSON bytes
            json_data = json.dumps(group_config, indent=2).encode('utf-8')
            
            # Create group configuration file
            config_key = f"groups/{group_name}/group_config.json"
            
            import asyncio
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self._executor, 
                self._sync_put_object, 
                config_key, 
                json_data, 
                "application/json"
            )
            
            if success:
                # Create shared directory structure
                shared_config = {
                    "templates": {},
                    "configurations": {},
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                shared_json = json.dumps(shared_config, indent=2).encode('utf-8')
                shared_key = f"groups/{group_name}/shared/config.json"
                
                await loop.run_in_executor(
                    self._executor, 
                    self._sync_put_object, 
                    shared_key, 
                    shared_json, 
                    "application/json"
                )
                
                logger.info(f"Successfully created group storage: {group_name}")
                return AuthenticatedS3OperationResult(
                    success=True, 
                    data={"group_name": group_name, "config_key": config_key},
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            else:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Failed to create group storage",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
                
        except Exception as e:
            error_msg = f"Error creating group storage: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def delete_group_storage(self, group_name: str, admin_token: str) -> AuthenticatedS3OperationResult:
        """
        Delete all storage for a group.
        
        Args:
            group_name: Name of the group
            admin_token: JWT token for admin authentication
            
        Returns:
            AuthenticatedS3OperationResult with operation status
        """
        try:
            # Validate admin token
            user_claims = self._validate_user_token(admin_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Check if user has admin privileges
            if 'admins' not in user_claims.groups:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Admin privileges required",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # List all objects for this group
            prefix = f"groups/{group_name}/"
            
            import asyncio
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            if not object_keys:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Group storage not found: {group_name}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Delete all objects for this group
            deleted_count = 0
            for key in object_keys:
                try:
                    await loop.run_in_executor(
                        self._executor, 
                        self._sync_delete_object, 
                        key
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete object {key}: {str(e)}")
            
            logger.info(f"Successfully deleted {deleted_count} objects for group: {group_name}")
            return AuthenticatedS3OperationResult(
                success=True, 
                data={"deleted_objects": deleted_count, "group_name": group_name},
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error deleting group storage: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def list_group_projects(self, group_name: str, user_token: str) -> AuthenticatedS3OperationResult:
        """
        List all projects in a specific group.
        
        Args:
            group_name: Name of the group
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedS3OperationResult with list of project IDs
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Check if user belongs to the group or is admin
            if group_name not in user_claims.groups and 'admins' not in user_claims.groups:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Access denied to group: {group_name}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # List objects with group projects prefix
            prefix = f"groups/{group_name}/projects/"
            
            import asyncio
            loop = asyncio.get_event_loop()
            object_keys = await loop.run_in_executor(
                self._executor, 
                self._sync_list_objects, 
                prefix
            )
            
            # Extract project IDs from keys
            project_ids = set()
            for key in object_keys:
                # Keys look like: groups/{group}/projects/{project_id}/metadata.json
                parts = key.split('/')
                if len(parts) >= 4 and parts[0] == "groups" and parts[2] == "projects":
                    project_ids.add(parts[3])
            
            project_list = sorted(list(project_ids))
            
            logger.info(f"Successfully listed {len(project_list)} projects for group: {group_name}")
            return AuthenticatedS3OperationResult(
                success=True, 
                data=project_list,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except Exception as e:
            error_msg = f"Error listing group projects from S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def save_file(self, file_key: str, file_data: bytes, user_token: str, content_type: str = "application/json") -> AuthenticatedS3OperationResult:
        """
        Save a file to S3 with authentication.
        
        Args:
            file_key: S3 key for the file
            file_data: File content as bytes
            user_token: JWT token for authentication
            content_type: MIME type of the file
            
        Returns:
            AuthenticatedS3OperationResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Extract project ID from file key to check access
            # Expected format: projects/{project_id}/... or groups/{group}/projects/{project_id}/...
            project_id = self._extract_project_id_from_key(file_key)
            if project_id and not self._user_has_project_access(user_claims, project_id):
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Access denied to project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Save file to S3
            import asyncio
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(
                self._executor, 
                self._sync_put_object, 
                file_key, 
                file_data, 
                content_type
            )
            
            if success:
                logger.info(f"Successfully saved file to S3: {file_key}")
                return AuthenticatedS3OperationResult(
                    success=True, 
                    data={"file_key": file_key},
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            else:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Failed to save file to S3",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
                
        except Exception as e:
            error_msg = f"Error saving file to S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def load_file(self, file_key: str, user_token: str) -> AuthenticatedS3OperationResult:
        """
        Load a file from S3 with authentication.
        
        Args:
            file_key: S3 key for the file
            user_token: JWT token for authentication
            
        Returns:
            AuthenticatedS3OperationResult with file content
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Extract project ID from file key to check access
            project_id = self._extract_project_id_from_key(file_key)
            if project_id and not self._user_has_project_access(user_claims, project_id):
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message=f"Access denied to project: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Load file from S3
            import asyncio
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                self._executor, 
                self._sync_get_object, 
                file_key
            )
            
            if content is not None:
                logger.info(f"Successfully loaded file from S3: {file_key}")
                return AuthenticatedS3OperationResult(
                    success=True, 
                    data=content,
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            else:
                return AuthenticatedS3OperationResult(
                    success=False, 
                    error_message="File not found",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
                
        except Exception as e:
            error_msg = f"Error loading file from S3: {str(e)}"
            logger.error(error_msg)
            return AuthenticatedS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    def _extract_project_id_from_key(self, file_key: str) -> Optional[str]:
        """Extract project ID from S3 file key."""
        parts = file_key.split('/')
        if len(parts) >= 2 and parts[0] == "projects":
            return parts[1]
        elif len(parts) >= 4 and parts[0] == "groups" and parts[2] == "projects":
            return parts[3]
        return None