"""Project creation routes for creating new projects with S3 folder structure."""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse

from models.project_models import CreateProjectRequest, CreateProjectResponse, ProjectMetadata
from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
from services.authentication_service import AuthenticationService
from middleware.auth_middleware import get_current_user_dependency
from models.auth_models import UserClaims

logger = logging.getLogger(__name__)


def create_project_creation_router(auth_service: AuthenticationService) -> APIRouter:
    """
    Create project creation router with authentication.
    
    Args:
        auth_service: Authentication service instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/projects", tags=["project-creation"])
    
    # Create the dependency function for getting current user
    get_current_user = get_current_user_dependency(auth_service)
    
    # Initialize Authenticated S3 service
    try:
        s3_service = AuthenticatedS3StorageService(auth_service=auth_service)
    except Exception as e:
        logger.error(f"Failed to initialize AuthenticatedS3StorageService: {e}")
        
        @router.post("/create")
        async def service_unavailable():
            raise HTTPException(
                status_code=503, 
                detail="Project creation service unavailable: S3 service not configured"
            )
        return router
    
    def _generate_project_id(name: str) -> str:
        """Generate project ID from name."""
        # Convert name to lowercase, replace spaces and special chars with hyphens
        import re
        project_id = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
        project_id = re.sub(r'\s+', '-', project_id.strip())
        project_id = re.sub(r'-+', '-', project_id)
        return project_id.strip('-')
    
    @router.post("/create", response_model=CreateProjectResponse)
    async def create_new_project(
        request_data: CreateProjectRequest,
        request: Request,
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Create a new project with S3 folder structure and metadata.json file.
        
        Creates:
        - S3 folder: projects/{project_id}/
        - S3 file: projects/{project_id}/metadata.json
        """
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Generate project ID from name
            project_id = _generate_project_id(request_data.name)
            
            # Check if project already exists
            existing_result = await s3_service.load_project_metadata(project_id, auth_header)
            if existing_result.success:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Project with ID '{project_id}' already exists"
                )
            
            # Create project metadata
            current_time = datetime.now(timezone.utc).isoformat()
            metadata = ProjectMetadata(
                project_id=project_id,
                name=request_data.name,
                description=request_data.description,
                created_at=current_time,
                assigned_groups=request_data.assigned_groups,
                assigned_users=request_data.assigned_users,
                project_type=request_data.project_type,
                status=request_data.status,
                last_updated=current_time
            )
            
            # Save project metadata to S3
            save_result = await s3_service.save_project_metadata(
                project_id, 
                metadata.dict(), 
                auth_header
            )
            
            if not save_result.success:
                logger.error(f"Failed to create project {project_id}: {save_result.error_message}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to create project: {save_result.error_message}"
                )
            
            logger.info(f"Successfully created project: {project_id} by user: {current_user.username}")
            
            # Ensure knowledge base is ready for the new project (async)
            try:
                from services.simple_tool_service import SimpleToolService
                import asyncio
                
                tool_service = SimpleToolService()
                # Trigger KB readiness check in background - doesn't block response
                asyncio.create_task(tool_service.ensure_project_kb_ready(project_id))
                logger.info(f"KB readiness check initiated for project: {project_id}")
                
            except Exception as e:
                # Don't fail project creation if KB fails
                logger.warning(f"KB creation failed for project {project_id}: {e}")
            
            return CreateProjectResponse(
                success=True,
                project_id=project_id,
                message=f"Project '{request_data.name}' created successfully",
                metadata=metadata
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating project: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @router.get("/validate-name/{project_name}")
    async def validate_project_name(
        project_name: str,
        request: Request,
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Validate if a project name is available (check if project ID already exists).
        """
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header required")
            
            # Generate project ID from name
            project_id = _generate_project_id(project_name)
            
            # Check if project exists
            existing_result = await s3_service.load_project_metadata(project_id, auth_header)
            
            return {
                "project_name": project_name,
                "project_id": project_id,
                "available": not existing_result.success,
                "message": "Project name is available" if not existing_result.success else "Project name already exists"
            }
            
        except Exception as e:
            logger.error(f"Error validating project name: {str(e)}")
            return {
                "project_name": project_name,
                "project_id": _generate_project_id(project_name),
                "available": False,
                "message": f"Error validating name: {str(e)}"
            }
    
    @router.get("/types")
    async def get_project_types():
        """Get available project types."""
        return {
            "project_types": [
                {"value": "web", "label": "Web Application"},
                {"value": "mobile", "label": "Mobile Application"},
                {"value": "api", "label": "API/Backend Service"},
                {"value": "desktop", "label": "Desktop Application"},
                {"value": "data", "label": "Data Processing"},
                {"value": "ml", "label": "Machine Learning"},
                {"value": "other", "label": "Other"}
            ]
        }
    
    return router