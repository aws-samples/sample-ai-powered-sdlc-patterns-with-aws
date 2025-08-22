"""Code generation and download routes."""

import os
import tempfile
import zipfile
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import FileResponse

from config.settings import settings
from models.api_models import CodeGenerationRequest
from models.auth_models import UserClaims
from services.architecture_code_generator import ArchitectureCodeGenerator
from middleware.auth_middleware import get_current_user_dependency, AuthContext, get_auth_context


def extract_project_name_from_conversation_id(conversation_id: str) -> str:
    """
    Extract the original project name from a conversation ID.
    
    Conversation IDs are formatted as: {phase}_{project_name}_{YYYYMMDD_HHMMSS}
    This function extracts the project_name part.
    """
    try:
        # The timestamp format is YYYYMMDD_HHMMSS (e.g., 20250711_092729)
        # So we need to remove the phase (first part) and the timestamp (last 2 parts)
        parts = conversation_id.split('_')
        if len(parts) >= 4:
            # Remove phase (first part) and timestamp (last 2 parts: YYYYMMDD and HHMMSS)
            # Join the middle parts in case project name had underscores
            project_name_parts = parts[1:-2]
            return '_'.join(project_name_parts)
        elif len(parts) == 3:
            # Fallback: if only 3 parts, assume middle part is project name
            return parts[1]
        else:
            # If format doesn't match expected pattern, return as-is
            return conversation_id
    except Exception:
        # If any error occurs, return the original ID
        return conversation_id


def create_code_router(auth_service=None) -> APIRouter:
    """Create and configure the code generation router."""
    router = APIRouter(prefix="/api", tags=["code"])
    
    # Initialize architecture code generator with S3 support
    code_generator = ArchitectureCodeGenerator()
    
    # Authentication dependency
    get_current_user = get_current_user_dependency(auth_service) if auth_service else None
    
    @router.post("/code-generation/generate")
    async def generate_architecture_code(
        request: CodeGenerationRequest,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None
    ):
        """Generate architecture code from diagram and context with user authentication."""
        try:
            # Process code generation request
            
            # Import required modules
            from services.architecture_code_models import CodeType, TargetPlatform
            
            # Map string values to enums
            code_type_map = {
                'cloudformation': CodeType.CLOUDFORMATION,
                'terraform': CodeType.TERRAFORM,
                'kubernetes': CodeType.KUBERNETES
            }
            platform_map = {
                'aws': TargetPlatform.AWS
            }
            
            # Create a mock diagram response for code generation
            diagram_response = {
                'success': True,
                'diagram_url': request.diagram_url,
                'metadata': {
                    'project_id': request.project_id,
                    'description': request.architecture_description or 'Architecture design'
                }
            }
            
            # Create context from request
            context = {
                'project_id': request.project_id,
                'conversation_summary': request.architecture_description or 'Architecture design for code generation'
            }
            
            # Generate code
            response = await code_generator.generate_code_from_diagram(
                diagram_response=diagram_response,
                context=context,
                code_type=code_type_map.get(request.code_type, CodeType.CLOUDFORMATION),
                target_platform=platform_map.get(request.target_platform, TargetPlatform.AWS),
                project_name=request.project_name or request.project_id
            )
            
            if response.success:
                return {
                    "success": True,
                    "project_id": response.project_id,
                    "project_name": response.project_name,
                    "files_generated": len(response.generated_files),
                    "files": [
                        {
                            "filename": file.filename,
                            "file_type": file.file_type.value if hasattr(file.file_type, 'value') else str(file.file_type),
                            "language": file.language,
                            "description": file.description,
                            "size": len(file.content) if file.content else 0
                        }
                        for file in response.generated_files
                    ],
                    "message": "Code generation completed successfully"
                }
            else:
                return {
                    "success": False,
                    "error": response.error_message,
                    "message": "Code generation failed"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Code generation failed due to internal error"
            }
    
    @router.get("/code-download/{project_id}/files")
    async def get_available_code_files(
        project_id: str, 
        version: str = "latest",
        request: Request = None,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None,
        auth_context: AuthContext = Depends(get_auth_context) if auth_service else None
    ):
        """Get list of available code files for a project from S3 or local storage with access control."""
        try:
            # Check authentication and access control
            if not current_user or not auth_context or not auth_context.jwt_token:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            # Check if user has access to this project using authenticated S3 service
            from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
            s3_service = AuthenticatedS3StorageService(auth_service=auth_service)
            
            # Test access by trying to load project metadata
            access_result = await s3_service.load_project_metadata(actual_project_name, auth_context.jwt_token)
            if not access_result.success:
                if "Access denied" in access_result.error_message:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied to project: {actual_project_name}"
                    )
                elif "not found" in access_result.error_message:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Project not found: {actual_project_name}"
                    )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail="Failed to verify project access"
                    )
            
            # First try to get metadata from S3 via code generator with extracted name
            metadata = await code_generator.get_code_files_metadata(actual_project_name, version)            
            # If not found with extracted name, try with original project_id
            if not metadata or metadata.get('total_files', 0) == 0:
                metadata = await code_generator.get_code_files_metadata(project_id, version)
                if metadata and metadata.get('total_files', 0) > 0:
                    actual_project_name = project_id  # Use original if found
            
            if metadata:
                files = []
                for file_info in metadata['files']:
                    file_ext = os.path.splitext(file_info['filename'])[1].lower()
                    file_type, language = _get_file_type_and_language(file_ext)
                    
                    files.append({
                        "id": file_info.get('relative_path', file_info['filename']),
                        "filename": file_info['filename'],
                        "relativePath": file_info.get('relative_path', file_info['filename']),
                        "fileType": file_type,
                        "language": language,
                        "fileSize": file_info['size'],
                        "description": f"{file_type.title()} file: {file_info['filename']}",
                        "content": None
                    })
                
                return {
                    "success": True,
                    "files": files,
                    "projectName": actual_project_name,
                    "totalFiles": metadata['total_files'],
                    "totalSize": metadata['total_size'],
                    "source": metadata['source'],
                    "version": metadata['version'],
                    "generatedAt": datetime.utcnow().isoformat()
                }
            
            # No local fallback - S3 is required
            return {
                "success": False,
                "files": [],
                "projectName": actual_project_name,
                "message": "No generated code files found in S3 for this project"
            }
            
        except Exception as e:
            return {
                "success": False,
                "files": [],
                "error": str(e),
                "message": "Failed to retrieve code files"
            }
    
    @router.get("/code-download/{project_id}/file/{file_id:path}")
    async def download_individual_file(
        project_id: str, 
        file_id: str, 
        version: str = "latest",
        request: Request = None,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None,
        auth_context: AuthContext = Depends(get_auth_context) if auth_service else None
    ):
        """Download an individual code file from S3 or local storage with access control."""
        try:
            # Check authentication and access control
            if not current_user or not auth_context or not auth_context.jwt_token:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            # Check if user has access to this project using authenticated S3 service
            from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
            s3_service = AuthenticatedS3StorageService(auth_service=auth_service)
            
            # Test access by trying to load project metadata
            access_result = await s3_service.load_project_metadata(actual_project_name, auth_context.jwt_token)
            if not access_result.success:
                if "Access denied" in access_result.error_message:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied to project: {actual_project_name}"
                    )
                elif "not found" in access_result.error_message:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Project not found: {actual_project_name}"
                    )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail="Failed to verify project access"
                    )
            # First try to get file from S3 with extracted project name
            s3_files = await code_generator.load_generated_code_from_s3(actual_project_name, version)
            
            # If not found with extracted name, try with original project_id
            if not s3_files:
                s3_files = await code_generator.load_generated_code_from_s3(project_id, version)
            
            if s3_files and file_id in s3_files:
                # Create temporary file for S3 content
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_id)[1])
                
                try:
                    content = s3_files[file_id]
                    if isinstance(content, str):
                        temp_file.write(content.encode('utf-8'))
                    else:
                        temp_file.write(content)
                    temp_file.close()
                    
                    filename = os.path.basename(file_id)
                    return FileResponse(
                        path=temp_file.name,
                        filename=filename,
                        media_type='application/octet-stream'
                    )
                    
                except Exception as e:
                    # Clean up temp file on error
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                    raise e
            
            # No local fallback - S3 is required
            raise HTTPException(status_code=404, detail="File not found in S3")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")
    
    @router.get("/code-download/{project_id}/zip")
    async def download_project_zip(
        project_id: str, 
        version: str = "latest",
        request: Request = None,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None,
        auth_context: AuthContext = Depends(get_auth_context) if auth_service else None
    ):
        """Download all project files as a ZIP archive from S3 or local storage with access control."""
        try:
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            # Create temporary ZIP file
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_zip.close()
            
            try:
                # First try to get files from S3 with extracted project name
                s3_files = await code_generator.load_generated_code_from_s3(actual_project_name, version)
                
                # If not found with extracted name, try with original project_id
                if not s3_files:
                    s3_files = await code_generator.load_generated_code_from_s3(project_id, version)
                
                if s3_files:
                    # Create ZIP from S3 files
                    with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for filename, content in s3_files.items():
                            if isinstance(content, str):
                                zipf.writestr(filename, content.encode('utf-8'))
                            else:
                                zipf.writestr(filename, content)
                    
                    return FileResponse(
                        path=temp_zip.name,
                        filename=f"{project_id}-{version}.zip",
                        media_type='application/zip'
                    )
                
                # No local fallback - S3 is required
                raise HTTPException(status_code=404, detail="Project files not found in S3")
                
                # Return ZIP file as download
                return FileResponse(
                    path=temp_zip.name,
                    filename=f"{project_id}.zip",
                    media_type='application/zip'
                )
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_zip.name):
                    os.unlink(temp_zip.name)
                raise e
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create ZIP archive: {str(e)}")
    
    @router.post("/code-download/{project_id}/zip-selected")
    async def download_selected_files_zip(project_id: str, request: Request):
        """Download selected files as a ZIP archive from S3 or local storage."""
        try:
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            # Parse request body
            body = await request.json()
            file_ids = body.get('fileIds', [])
            version = body.get('version', 'latest')
            
            if not file_ids:
                raise HTTPException(status_code=400, detail="No files selected")
            
            # Create temporary ZIP file
            temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            temp_zip.close()
            
            try:
                # First try to get files from S3
                s3_files = await code_generator.load_generated_code_from_s3(project_id, version)
                
                if s3_files:
                    # Create ZIP from selected S3 files
                    with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for file_id in file_ids:
                            if file_id in s3_files:
                                content = s3_files[file_id]
                                if isinstance(content, str):
                                    zipf.writestr(file_id, content.encode('utf-8'))
                                else:
                                    zipf.writestr(file_id, content)
                    
                    return FileResponse(
                        path=temp_zip.name,
                        filename=f"{project_id}-selected-{version}.zip",
                        media_type='application/zip'
                    )
                
                # No local fallback - S3 is required
                raise HTTPException(status_code=404, detail="Selected files not found in S3")
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_zip.name):
                    os.unlink(temp_zip.name)
                raise e
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create selected files ZIP: {str(e)}")
    
    @router.get("/code-download/{project_id}/metadata")
    async def get_download_metadata(project_id: str, version: str = "latest"):
        """Get download metadata for a project from S3 or local storage."""
        try:
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            # First try to get metadata from S3 via code generator with extracted project name
            metadata = await code_generator.get_code_files_metadata(actual_project_name, version)
            
            # If not found with extracted name, try with original project_id
            if not metadata or metadata.get('total_files', 0) == 0:
                metadata = await code_generator.get_code_files_metadata(project_id, version)
            
            if metadata:
                return {
                    "projectId": actual_project_name,
                    "projectName": actual_project_name,
                    "totalFiles": metadata['total_files'],
                    "totalSize": metadata['total_size'],
                    "source": metadata['source'],
                    "version": metadata['version'],
                    "generatedAt": datetime.utcnow().isoformat(),
                    "lastModified": datetime.utcnow().isoformat(),
                    "availableFormats": ["individual", "zip"]
                }
            
            # No local fallback - S3 is required
            raise HTTPException(status_code=404, detail="Project metadata not found in S3")
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get metadata: {str(e)}")
    
    @router.get("/code-download/{project_id}/versions")
    async def get_code_versions(project_id: str):
        """Get available code versions for a project."""
        try:
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            # Try to get versions from S3 with extracted project name first
            versions = await code_generator.list_code_versions_from_s3(actual_project_name)
            
            # If no versions found with extracted name, try with original project_id
            if not versions:
                versions = await code_generator.list_code_versions_from_s3(project_id)
            
            # No local version check - S3 only
            return {
                "projectId": actual_project_name,
                "versions": versions,
                "totalVersions": len(versions),
                "hasS3Versions": len(versions) > 0,
                "hasLocalVersion": False
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get versions: {str(e)}")
    
    # Sync endpoint removed - all code is now stored directly in S3
    @router.get("/s3/status")
    async def get_s3_status():
        """Get S3 configuration and availability status."""
        try:
            s3_status = await code_generator.check_s3_availability()
            
            return {
                "s3_available": s3_status['available'],
                "s3_configured": s3_status['configured'],
                "bucket_name": s3_status['bucket_name'],
                "region": s3_status.get('region', 'unknown'),
                "error": s3_status.get('error'),
                "message": "S3 is working correctly" if s3_status['available'] else "S3 is not available - files will be stored locally only"
            }
            
        except Exception as e:
            return {
                "s3_available": False,
                "s3_configured": False,
                "bucket_name": "unknown",
                "region": "unknown",
                "error": str(e),
                "message": "Failed to check S3 status"
            }
    
    # Diagram S3 endpoints
    @router.get("/diagrams/{project_id}/list")
    async def list_project_diagrams(project_id: str):
        """List all diagrams for a project from S3."""
        try:
            from services.diagram_service import DiagramService
            diagram_service = DiagramService()
            
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            diagrams = await diagram_service.list_project_diagrams(actual_project_name)
            
            return {
                "success": True,
                "project_id": actual_project_name,
                "diagrams": diagrams,
                "total_diagrams": len(diagrams),
                "message": f"Found {len(diagrams)} diagrams for project {actual_project_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "diagrams": [],
                "total_diagrams": 0,
                "error": str(e),
                "message": "Failed to list project diagrams"
            }
    
    @router.get("/diagrams/{project_id}/specification")
    async def get_project_diagrams_for_specification(
        project_id: str,
        request: Request,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None,
        auth_context: AuthContext = Depends(get_auth_context) if auth_service else None
    ):
        """Get diagrams formatted for specification display (S3-only, project-specific) with access control."""
        try:
            # Check authentication and access control
            if not current_user or not auth_context or not auth_context.jwt_token:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            # Check if user has access to this project using authenticated S3 service
            from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
            s3_service = AuthenticatedS3StorageService(auth_service=auth_service)
            
            # Test access by trying to load project metadata
            access_result = await s3_service.load_project_metadata(actual_project_name, auth_context.jwt_token)
            if not access_result.success:
                if "Access denied" in access_result.error_message:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied to project: {actual_project_name}"
                    )
                elif "not found" in access_result.error_message:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Project not found: {actual_project_name}"
                    )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail="Failed to verify project access"
                    )
            
            # User has access, proceed with diagram loading
            from services.diagram_service import DiagramService
            diagram_service = DiagramService()
            
            # Get diagrams from S3 only (project-specific)
            diagrams = await diagram_service.list_project_diagrams(actual_project_name)
            
            # Format diagrams for specification display
            formatted_diagrams = []
            for diagram in diagrams:
                # Use the S3 serving endpoint instead of local static files
                # This ensures we serve the correct diagram for the correct project
                s3_serve_url = f"/api/diagrams/{actual_project_name}/serve/{diagram['filename']}"
                
                # Generate S3 serve URL
                
                # Determine description based on source
                description = "Architecture diagram (stored in S3)"
                if diagram.get("s3_key"):
                    description = f"Architecture diagram from S3: {diagram['s3_key']}"
                
                formatted_diagram = {
                    "diagram_type": "architecture",  # Default type
                    "diagram_url": s3_serve_url,  # Use S3 serving endpoint
                    "diagram_data": None,
                    "diagram_metadata": {
                        "format": diagram.get("format", "png"),
                        "description": description,
                        "title": diagram.get("name", "Architecture Diagram"),
                        "filename": diagram["filename"],
                        "s3_key": diagram.get("s3_key", ""),
                        "source": "s3",  # Always S3 now
                        "project_specific": True  # Flag to indicate this is project-specific
                    }
                }
                formatted_diagrams.append(formatted_diagram)
                # Diagram formatted and added
            
            return {
                "success": True,
                "project_id": actual_project_name,
                "diagrams": formatted_diagrams,
                "total_diagrams": len(formatted_diagrams),
                "message": f"Found {len(formatted_diagrams)} S3 diagrams for project {actual_project_name}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "diagrams": [],
                "total_diagrams": 0,
                "error": str(e),
                "message": "Failed to get diagrams for specification"
            }
    
    @router.get("/diagrams/{project_id}/download/{diagram_name}")
    async def download_diagram(
        project_id: str, 
        diagram_name: str, 
        format: str = "png", 
        inline: bool = False,
        request: Request = None,
        current_user: UserClaims = Depends(get_current_user) if get_current_user else None,
        auth_context: AuthContext = Depends(get_auth_context) if auth_service else None
    ):
        """Download or serve a specific diagram from S3 with access control."""
        try:
            # Check authentication and access control
            if not current_user or not auth_context or not auth_context.jwt_token:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            # Check if user has access to this project using authenticated S3 service
            from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
            s3_service = AuthenticatedS3StorageService(auth_service=auth_service)
            
            # Test access by trying to load project metadata
            access_result = await s3_service.load_project_metadata(actual_project_name, auth_context.jwt_token)
            if not access_result.success:
                if "Access denied" in access_result.error_message:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Access denied to project: {actual_project_name}"
                    )
                elif "not found" in access_result.error_message:
                    raise HTTPException(
                        status_code=404, 
                        detail=f"Project not found: {actual_project_name}"
                    )
                else:
                    raise HTTPException(
                        status_code=500, 
                        detail="Failed to verify project access"
                    )
            
            # User has access, proceed with diagram download
            from services.diagram_service import DiagramService
            diagram_service = DiagramService()
            
            # Handle filename with extension
            if '.' in diagram_name:
                diagram_name_only, format_ext = diagram_name.rsplit('.', 1)
                format = format_ext.lower()
            else:
                diagram_name_only = diagram_name
            
            diagram_data = await diagram_service.load_diagram_from_s3(actual_project_name, diagram_name_only, format)
            
            if not diagram_data:
                raise HTTPException(status_code=404, detail="Diagram not found")
            
            # Create temporary file for diagram content
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format}')
            
            try:
                temp_file.write(diagram_data['content'])
                temp_file.close()
                
                # Determine media type based on format
                media_type_map = {
                    'png': 'image/png',
                    'svg': 'image/svg+xml',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'gif': 'image/gif'
                }
                media_type = media_type_map.get(format.lower(), 'image/png')
                
                return FileResponse(
                    path=temp_file.name,
                    filename=diagram_data['diagram_name'],
                    media_type=media_type
                )
                
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
                raise e
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to download diagram: {str(e)}")
    
    @router.get("/diagrams/{project_id}/serve/{diagram_filename}")
    async def serve_diagram_from_s3(project_id: str, diagram_filename: str):
        """Serve a diagram directly from S3 (similar to code file serving)."""
        try:
            from services.diagram_service import DiagramService
            diagram_service = DiagramService()
            
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            # Extract diagram name and format from filename
            if '.' in diagram_filename:
                diagram_name, format_ext = diagram_filename.rsplit('.', 1)
                format = format_ext.lower()
            else:
                diagram_name = diagram_filename
                format = 'png'
            
            # Try to load from S3
            diagram_data = await diagram_service.load_diagram_from_s3(actual_project_name, diagram_name, format)
            
            if diagram_data:
                # Create temporary file for S3 content
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format}')
                
                try:
                    temp_file.write(diagram_data['content'])
                    temp_file.close()
                    
                    # Determine media type based on format
                    media_type_map = {
                        'png': 'image/png',
                        'svg': 'image/svg+xml',
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'gif': 'image/gif'
                    }
                    media_type = media_type_map.get(format, 'image/png')
                    
                    return FileResponse(
                        path=temp_file.name,
                        filename=diagram_filename,
                        media_type=media_type
                    )
                    
                except Exception as e:
                    # Clean up temp file on error
                    if os.path.exists(temp_file.name):
                        os.unlink(temp_file.name)
                    raise e
            
            # Fallback to local file system (but only for the specific project)
            # This should be rare since we're focusing on S3
            raise HTTPException(status_code=404, detail="Diagram not found")
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to serve diagram: {str(e)}")
    
    @router.delete("/diagrams/{project_id}/delete/{diagram_name}")
    async def delete_diagram(project_id: str, diagram_name: str, format: str = "png"):
        """Delete a diagram from S3."""
        try:
            from services.diagram_service import DiagramService
            diagram_service = DiagramService()
            
            # Extract actual project name if this is a conversation ID
            actual_project_name = extract_project_name_from_conversation_id(project_id)
            
            success = await diagram_service.delete_diagram_from_s3(actual_project_name, diagram_name, format)
            
            if success:
                return {
                    "success": True,
                    "project_id": actual_project_name,
                    "diagram_name": diagram_name,
                    "message": f"Successfully deleted diagram {diagram_name}.{format}"
                }
            else:
                return {
                    "success": False,
                    "project_id": actual_project_name,
                    "diagram_name": diagram_name,
                    "error": "Failed to delete diagram",
                    "message": f"Could not delete diagram {diagram_name}.{format}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "project_id": project_id,
                "diagram_name": diagram_name,
                "error": str(e),
                "message": "Failed to delete diagram"
            }
    
    return router


def _get_file_type_and_language(file_ext: str) -> tuple[str, str]:
    """Determine file type and language from extension."""
    ext_map = {
        '.yaml': ('infrastructure', 'yaml'),
        '.yml': ('infrastructure', 'yaml'),
        '.json': ('config', 'json'),
        '.tf': ('infrastructure', 'terraform'),
        '.py': ('application', 'python'),
        '.js': ('application', 'javascript'),
        '.jsx': ('application', 'javascript'),
        '.md': ('documentation', 'markdown'),
        '.sh': ('config', 'bash')
    }
    
    return ext_map.get(file_ext, ('application', 'text'))