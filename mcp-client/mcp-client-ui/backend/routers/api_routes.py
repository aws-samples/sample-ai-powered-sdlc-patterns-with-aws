"""API routes for project management."""

import json
import os
import re
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Request

from config.settings import settings
from models.api_models import ProjectRequest
from models.auth_models import UserClaims
from services.authenticated_project_service import AuthenticatedProjectService
from middleware.auth_middleware import get_current_user_dependency, AuthContext, get_auth_context


def create_api_router(auth_service=None) -> APIRouter:
    """Create and configure the API router."""
    router = APIRouter(prefix="/api", tags=["projects"])
    
    # Initialize authenticated S3 service and project service
    from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
    s3_service = AuthenticatedS3StorageService(auth_service=auth_service)
    project_service = AuthenticatedProjectService(s3_service=s3_service, auth_service=auth_service)
    
    # Authentication dependency
    get_current_user = get_current_user_dependency(auth_service) if auth_service else None
    
    @router.post("/projects")
    async def create_project(
        project: ProjectRequest,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None
    ):
        """Create a new project with S3 sync and user authentication."""
        try:
            # Convert project data to dictionary
            project_data = project.model_dump()
            
            # Create project using authenticated service
            if current_user:
                # Extract token from user claims (this would need to be passed differently in real implementation)
                user_token = f"user:{current_user.user_id}"  # Placeholder token format
                project_id = await project_service.create_project(project_data, user_token)
            else:
                # Fallback for non-authenticated requests (legacy support)
                from services.project_service import ProjectService
                legacy_service = ProjectService()
                project_id = await legacy_service.create_project(project_data)
            
            return {
                "message": "Project created successfully",
                "project_id": project_id,
                "status": "success"
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error creating project: {str(e)}"
            )
    
    @router.get("/projects")
    async def get_projects(
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None,
        auth_context: AuthContext = Depends(get_auth_context) if auth_service else None
    ):
        """Get projects accessible to the authenticated user."""
        try:
            if current_user and auth_context and auth_context.jwt_token:
                # Get user-specific projects using authenticated S3 service directly
                result = await s3_service.list_user_projects(auth_context.jwt_token)
                
                if result.success:
                    # Load full metadata for each project
                    projects_with_metadata = []
                    for project_info in result.data:
                        project_id = project_info["project_id"]
                        
                        # Load full project metadata
                        metadata_result = await s3_service.load_project_metadata(project_id, auth_context.jwt_token)
                        if metadata_result.success:
                            project_data = metadata_result.data
                            # Ensure consistent format for frontend
                            formatted_project = {
                                "project_id": project_data.get("project_id", project_id),
                                "name": project_data.get("name", project_id.replace("-", " ").title()),
                                "description": project_data.get("description", f"Project: {project_id}"),
                                "created_at": project_data.get("created_at", "Unknown"),
                                "project_type": project_data.get("project_type", "Unknown"),
                                "status": project_data.get("status", "active"),
                                "assigned_groups": project_data.get("assigned_groups", []),
                                "assigned_users": project_data.get("assigned_users", [])
                            }
                            projects_with_metadata.append(formatted_project)
                        else:
                            # Fallback if metadata can't be loaded
                            projects_with_metadata.append({
                                "project_id": project_id,
                                "name": project_id.replace("-", " ").title(),
                                "description": f"Project: {project_id}",
                                "created_at": "Unknown",
                                "project_type": "Unknown",
                                "status": "active",
                                "assigned_groups": [],
                                "assigned_users": []
                            })
                    
                    projects = projects_with_metadata
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to fetch projects: {result.error_message}"
                    )
                
                return {
                    "projects": projects,
                    "count": len(projects),
                    "user_id": current_user.user_id,
                    "groups": current_user.groups,
                    "status": "success"
                }
            else:
                # Fallback for non-authenticated requests (legacy support)
                from services.project_service import ProjectService
                legacy_service = ProjectService()
                project_lists = await legacy_service.list_projects()
                
                # Load project data for all projects
                projects = []
                for project_id in project_lists['all']:
                    project_data = await legacy_service.load_project(project_id)
                    if project_data:
                        projects.append(project_data)
                
                return {
                    "projects": projects,
                    "count": len(projects),
                    "local_count": len(project_lists['local']),
                    "s3_count": len(project_lists['s3']),
                    "status": "success"
                }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading projects: {str(e)}"
            )
    
    @router.get("/projects/{project_id}")
    async def get_project(
        project_id: str,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None
    ):
        """Get a specific project with authentication and authorization."""
        try:
            if current_user:
                # Load project using authenticated service
                user_token = f"user:{current_user.user_id}"  # Placeholder token format
                project_data = await project_service.load_project(project_id, user_token)
            else:
                # Fallback for non-authenticated requests (legacy support)
                from services.project_service import ProjectService
                legacy_service = ProjectService()
                project_data = await legacy_service.load_project(project_id)
            
            if not project_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project not found or access denied: {project_id}"
                )
            
            return {
                "project": project_data,
                "status": "success"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error loading project: {str(e)}"
            )
    
    @router.get("/projects/{project_id}/exists")
    async def check_project_exists(
        project_id: str,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None
    ):
        """Check project existence with user access validation."""
        try:
            if current_user:
                # Check existence with user access validation
                user_token = f"user:{current_user.user_id}"  # Placeholder token format
                try:
                    project_data = await project_service.load_project(project_id, user_token)
                    exists = project_data is not None
                except Exception:
                    exists = False  # Project doesn't exist or user doesn't have access
            else:
                # Fallback for non-authenticated requests (legacy support)
                from services.project_service import ProjectService
                legacy_service = ProjectService()
                exists = await legacy_service.project_exists(project_id)
            
            return {
                "project_id": project_id,
                "exists": exists,
                "status": "success"
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error checking project existence: {str(e)}"
            )
    
    @router.post("/projects/{project_id}/sync-to-s3")
    async def sync_project_to_s3(project_id: str):
        """Projects are now stored directly in S3 - no sync needed."""
        try:
            # Check if project exists in S3
            project_data = await project_service.load_project(project_id)
            
            if project_data:
                return {
                    "project_id": project_id,
                    "sync_status": "synced",
                    "message": "Projects are now stored directly in S3 - no sync needed",
                    "status": "success"
                }
            else:
                return {
                    "project_id": project_id,
                    "sync_status": "not_found",
                    "error": "Project not found in S3",
                    "status": "error"
                }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error syncing project to S3: {str(e)}"
            )
    
    @router.post("/projects/{project_id}/sync-from-s3")
    async def sync_project_from_s3(project_id: str):
        """Synchronize project from S3."""
        try:
            sync_result = await project_service.sync_project_from_s3(project_id)
            
            if sync_result.success:
                return {
                    "project_id": project_id,
                    "sync_status": sync_result.sync_status,
                    "files_synced": sync_result.files_synced,
                    "status": "success"
                }
            else:
                return {
                    "project_id": project_id,
                    "sync_status": sync_result.sync_status,
                    "error": sync_result.error_message,
                    "status": "error"
                }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error syncing project from S3: {str(e)}"
            )
    
    @router.post("/projects/{project_id}/save-context")
    async def save_project_context(project_id: str):
        """Save complete project context."""
        try:
            success = await project_service.save_project_context(project_id)
            
            if success:
                return {
                    "project_id": project_id,
                    "message": "Project context saved successfully",
                    "status": "success"
                }
            else:
                return {
                    "project_id": project_id,
                    "message": "Failed to save project context",
                    "status": "error"
                }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error saving project context: {str(e)}"
            )
    
    @router.post("/projects/{project_id}/restore-context")
    async def restore_project_context(project_id: str):
        """Restore complete project context."""
        try:
            success = await project_service.restore_project_context(project_id)
            
            if success:
                return {
                    "project_id": project_id,
                    "message": "Project context restored successfully",
                    "status": "success"
                }
            else:
                return {
                    "project_id": project_id,
                    "message": "Failed to restore project context",
                    "status": "error"
                }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error restoring project context: {str(e)}"
            )
    
    return router


def create_legacy_api_router() -> APIRouter:
    """Create router for legacy API endpoints that aren't prefixed with /api."""
    router = APIRouter(tags=["legacy"])
    
    @router.get("/my_projects")
    async def get_my_projects():
        """GET endpoint that returns all projects from the projects folder (legacy endpoint)."""
        try:
            projects = []
            
            # Check if projects directory exists
            if not os.path.exists(settings.PROJECTS_DIR):
                return {
                    "projects": [],
                    "count": 0,
                    "message": "No projects folder found",
                    "status": "success"
                }
            
            # Read all JSON files in the projects directory
            for filename in os.listdir(settings.PROJECTS_DIR):
                if filename.endswith('.json'):
                    file_path = os.path.join(settings.PROJECTS_DIR, filename)
                    try:
                        with open(file_path, 'r') as f:
                            project_data = json.load(f)
                        projects.append(project_data)
                    except Exception as e:
                        pass  # Skip files with errors
                        continue
            
            return {
                "projects": projects,
                "count": len(projects),
                "status": "success"
            }
            
        except Exception as e:
            return {
                "projects": [],
                "count": 0,
                "message": f"Error reading projects: {str(e)}",
                "status": "error"
            }
    
    return router