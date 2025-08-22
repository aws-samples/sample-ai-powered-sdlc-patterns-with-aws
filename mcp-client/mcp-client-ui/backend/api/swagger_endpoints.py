"""
Swagger API Endpoints

Simple endpoints to serve OpenAPI specifications for Swagger UI display.
"""

import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import boto3
from botocore.exceptions import ClientError

from models.auth_models import UserClaims
from services.authenticated_s3_storage_service import AuthenticatedS3StorageService
from middleware.auth_middleware import get_current_user_dependency, AuthContext, get_auth_context

logger = logging.getLogger(__name__)

def create_swagger_router(auth_service=None) -> APIRouter:
    """Create and configure the swagger router."""
    router = APIRouter(prefix="/swagger", tags=["swagger"])  # Remove /api prefix to avoid auth middleware
    
    @router.get("/spec/{project_id}/{filename}")
    async def get_swagger_spec(project_id: str, filename: str):
        """
        Get OpenAPI specification from S3 for Swagger UI display.
        
        Args:
            project_id: Project identifier
            filename: Name of the JSON file containing the OpenAPI spec
            
        Returns:
            JSON response with the OpenAPI specification
        """
        try:
            logger.info(f"Fetching Swagger spec: {filename} for project: {project_id}")
            
            # Construct S3 key - try both timestamped and latest folders
            possible_keys = [
                f"projects/{project_id}/generated-code/latest/{filename}",
                f"projects/{project_id}/generated-code/{filename}",
            ]
            
            # Also try to find in timestamped folders by listing
            try:
                # Use direct S3 client
                import boto3
                import os
                s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                list_response = s3_client.list_objects_v2(
                    Bucket=os.getenv('S3_BUCKET_NAME'),
                    Prefix=f"projects/{project_id}/generated-code/",
                    MaxKeys=100
                )
                for obj in list_response.get('Contents', []):
                    if obj['Key'].endswith(filename):
                        possible_keys.insert(0, obj['Key'])  # Add to front of list
                        
            except Exception as list_error:
                logger.warning(f"Could not list S3 objects: {list_error}")
            
            # Try each possible key
            content = None
            used_key = None
            
            for s3_key in possible_keys:
                try:
                    logger.info(f"Trying S3 key: {s3_key}")
                    
                    # Use direct S3 client for simplicity
                    import boto3
                    import os
                    s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
                    response = s3_client.get_object(Bucket=os.getenv('S3_BUCKET_NAME'), Key=s3_key)
                    content = response['Body'].read().decode('utf-8')
                    
                    used_key = s3_key
                    logger.info(f"Successfully fetched from S3 key: {s3_key}")
                    break
                    
                except Exception as e:
                    logger.debug(f"Could not fetch from key {s3_key}: {e}")
                    continue
            
            if not content:
                logger.error(f"Could not find file {filename} in any location for project {project_id}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"OpenAPI specification file '{filename}' not found for project '{project_id}'"
                )
            
            # Parse and validate JSON
            try:
                spec_data = json.loads(content)
                logger.info(f"Successfully parsed JSON from {used_key}")
                
                # Basic validation - check if it looks like an OpenAPI spec
                if not isinstance(spec_data, dict):
                    raise HTTPException(
                        status_code=400,
                        detail="File content is not a valid JSON object"
                    )
                
                # Check for OpenAPI indicators (optional validation)
                has_openapi_structure = (
                    spec_data.get('openapi') or 
                    spec_data.get('swagger') or 
                    (spec_data.get('info') and spec_data.get('paths'))
                )
                
                if not has_openapi_structure:
                    logger.warning(f"File {filename} doesn't appear to be an OpenAPI spec, but serving anyway")
                
                return JSONResponse(content=spec_data)
                
            except json.JSONDecodeError as json_error:
                logger.error(f"Invalid JSON in file {filename}: {json_error}")
                raise HTTPException(
                    status_code=400,
                    detail=f"File '{filename}' contains invalid JSON: {str(json_error)}"
                )
                
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error fetching Swagger spec {filename}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error while fetching specification: {str(e)}"
            )

    @router.get("/health")
    async def swagger_health_check():
        """Health check for Swagger endpoints."""
        try:
            return {
                "status": "healthy",
                "service": "swagger-api",
                "timestamp": "2025-07-31T14:00:00Z"
            }
            
        except Exception as e:
            logger.error(f"Swagger health check failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Service unhealthy: {str(e)}"
            )
    
    @router.get("/test")
    async def test_endpoint():
        """Simple test endpoint to verify routing works."""
        return {"message": "Swagger router is working!", "timestamp": "2025-07-31T14:00:00Z"}
    
    return router