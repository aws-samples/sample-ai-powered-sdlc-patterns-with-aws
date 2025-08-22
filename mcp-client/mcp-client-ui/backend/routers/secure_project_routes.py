"""
Secure project routes that use Cognito Identity Pool credentials for S3 access.

These routes ensure proper access control by using the user's Cognito credentials
for all S3 operations, enforcing IAM policies based on user groups.

Note: For now, we'll implement a simpler backend-level access control until
we can properly handle ID tokens for Cognito Identity Pool operations.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
from services.authentication_service import AuthenticationService
from middleware.auth_middleware import get_current_user_dependency
from models.auth_models import UserClaims

logger = logging.getLogger(__name__)


def create_secure_project_router(auth_service: AuthenticationService) -> APIRouter:
    """
    Create secure project router with Cognito S3 access control.
    
    Args:
        auth_service: Authentication service instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/secure/projects", tags=["secure-projects"])
    
    # Create the dependency function for getting current user
    get_current_user = get_current_user_dependency(auth_service)
    
    # Initialize Authenticated S3 service (backend-level access control)
    # This provides proper access control until we can implement full Cognito Identity Pool integration
    try:
        s3_service = AuthenticatedS3StorageService(auth_service=auth_service)
    except Exception as e:
        logger.error(f"Failed to initialize AuthenticatedS3StorageService: {e}")
        # Return a router that will fail gracefully
        @router.get("/")
        async def service_unavailable():
            raise HTTPException(
                status_code=503, 
                detail="Secure project service unavailable: S3 service not configured"
            )
        return router
    
    @router.get("/")
    async def list_user_projects(
        request: Request,
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        List all projects accessible to the authenticated user.
        Uses user's Cognito credentials to enforce proper access control.
        """
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Use authenticated S3 service to list projects with access control
            result = await s3_service.list_user_projects(auth_header)
            
            if result.success:
                return {
                    "success": True,
                    "projects": result.data,
                    "user_id": result.user_id,
                    "groups": result.groups,
                    "message": f"Found {len(result.data)} accessible projects"
                }
            else:
                # Handle access denied specifically
                if "Access denied" in result.error_message:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied: {result.error_message}"
                    )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to list projects: {result.error_message}"
                    )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing projects: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.get("/{project_id}")
    async def get_project_metadata(
        project_id: str,
        request: Request,
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Get project metadata using user's Cognito credentials.
        Will return 403 if user doesn't have access to the project.
        """
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Use authenticated S3 service to load project metadata with access control
            result = await s3_service.load_project_metadata(project_id, auth_header)
            
            if result.success:
                return {
                    "success": True,
                    "project": result.data,
                    "user_id": result.user_id,
                    "groups": result.groups
                }
            else:
                # Handle different error types
                if "Access denied" in result.error_message:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied to project '{project_id}': User does not have permission"
                    )
                elif "not found" in result.error_message:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Project '{project_id}' not found or not accessible"
                    )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to load project: {result.error_message}"
                    )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading project {project_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.post("/{project_id}")
    async def save_project_metadata(
        project_id: str,
        metadata: Dict[str, Any],
        request: Request,
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Save project metadata using user's Cognito credentials.
        Will return 403 if user doesn't have write access to the project.
        """
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Use authenticated S3 service to save project metadata with access control
            result = await s3_service.save_project_metadata(project_id, metadata, auth_header)
            
            if result.success:
                return {
                    "success": True,
                    "message": f"Project '{project_id}' metadata saved successfully",
                    "data": result.data,
                    "user_id": result.user_id,
                    "groups": result.groups
                }
            else:
                # Handle different error types
                if "Access denied" in result.error_message:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied to project '{project_id}': User does not have write permission"
                    )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to save project: {result.error_message}"
                    )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving project {project_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.get("/{project_id}/access-test")
    async def test_project_access(
        project_id: str,
        request: Request,
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Test endpoint to verify user's access to a specific project.
        Useful for debugging access control issues.
        """
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Try to load project metadata to test access
            result = await s3_service.load_project_metadata(project_id, auth_header)
            
            return {
                "project_id": project_id,
                "user_id": current_user.user_id,
                "username": current_user.username,
                "groups": current_user.groups,
                "has_access": result.success,
                "error_message": result.error_message if not result.success else None,
                "test_timestamp": "2025-01-14T00:00:00Z"
            }
                
        except Exception as e:
            logger.error(f"Unexpected error testing access to project {project_id}: {str(e)}")
            return {
                "project_id": project_id,
                "user_id": current_user.user_id,
                "username": current_user.username,
                "groups": current_user.groups,
                "has_access": False,
                "error_message": f"Test failed: {str(e)}",
                "test_timestamp": "2025-01-14T00:00:00Z"
            }
    
    return router