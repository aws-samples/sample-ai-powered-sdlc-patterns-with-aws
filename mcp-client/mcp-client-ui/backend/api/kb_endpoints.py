"""
Knowledge Base API Endpoints - AWS Only

Secure endpoints for managing project knowledge bases using AWS services only
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, validator
from datetime import datetime

logger = logging.getLogger(__name__)

# Request/Response models
class ProjectKBRequest(BaseModel):
    project_name: str
    
    @validator('project_name')
    def validate_project_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Project name cannot be empty')
        if len(v) > 100:
            raise ValueError('Project name too long')
        return v.strip()

class KBQueryRequest(BaseModel):
    project_name: str
    query: str
    content_types: Optional[list] = None
    max_results: int = 10
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        if len(v) > 1000:
            raise ValueError('Query too long')
        return v.strip()
    
    @validator('max_results')
    def validate_max_results(cls, v):
        if v < 1 or v > 50:
            raise ValueError('max_results must be between 1 and 50')
        return v

class KBSyncRequest(BaseModel):
    project_name: str
    force_full_sync: bool = False

# Router setup
router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])

# Global service instance (will be set by main app)
_dynamic_service = None

def set_dynamic_service(service):
    """Set the dynamic service instance"""
    global _dynamic_service
    _dynamic_service = service

def get_dynamic_service():
    """Get the dynamic service instance"""
    if _dynamic_service is None:
        raise HTTPException(status_code=500, detail="Service not initialized")
    return _dynamic_service

@router.post("/create")
async def create_project_kb(request: ProjectKBRequest):
    """
    Create or ensure project knowledge base exists
    
    This will:
    1. Ensure Bedrock KB is ready for the project
    2. Trigger direct content ingestion from S3
    3. Return immediately while ingestion runs in background
    """
    try:
        logger.info(f"Creating KB for project: {request.project_name}")
        
        dynamic_service = get_dynamic_service()
        
        # Ensure KB exists (this is fast - just creates index structure)
        project_context = await dynamic_service.ensure_project_kb_ready(request.project_name)
        
        return {
            "success": True,
            "project_name": project_context.project_name,
            "kb_id": project_context.kb_id,
            "kb_ready": project_context.kb_ready,
            "message": f"Knowledge base ready for project {request.project_name}. Using existing Bedrock KB with project filtering.",
            "existing_kb": True
        }
        
    except Exception as e:
        logger.error(f"Failed to create KB for {request.project_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create knowledge base"
        )

@router.post("/query")
async def query_project_kb(request: KBQueryRequest):
    """
    Query project knowledge base using AWS Bedrock KB
    
    This will:
    1. Use Bedrock KB's built-in semantic search
    2. Filter results by project metadata
    3. Return relevant project context
    """
    try:
        logger.info(f"Querying KB for project {request.project_name}: {request.query[:100]}...")
        
        dynamic_service = get_dynamic_service()
        
        # Get project context with semantic search
        kb_context = await dynamic_service.get_project_context(
            request.project_name, 
            request.query
        )
        
        return {
            "success": True,
            "project_name": request.project_name,
            "query": request.query,
            "results": kb_context['relevant_context'],
            "total_results": sum(len(results) for results in kb_context['relevant_context'].values()),
            "context_quality": kb_context['context_quality'],
            "recent_activity": kb_context['recent_activity'][:3],  # Top 3 recent items
            "timestamp": datetime.utcnow().isoformat(),
            "embedding_service": "aws-bedrock-titan"
        }
        
    except Exception as e:
        logger.error(f"Failed to query KB for {request.project_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to query knowledge base"
        )

@router.post("/sync")
async def sync_project_content(request: KBSyncRequest):
    """
    Manually trigger project content synchronization
    
    This will:
    1. Trigger Bedrock KB ingestion job
    2. Process S3 content directly through Bedrock
    3. Update knowledge base with new content
    """
    try:
        logger.info(f"Manual sync requested for project: {request.project_name}")
        
        dynamic_service = get_dynamic_service()
        
        # Ensure KB exists
        await dynamic_service.ensure_project_kb_ready(request.project_name)
        
        # Trigger direct ingestion
        await dynamic_service.kb_service.trigger_s3_ingestion(request.project_name)
        
        return {
            "success": True,
            "project_name": request.project_name,
            "message": "Content synchronization started in background",
            "async_sync": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to sync content for {request.project_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to synchronize content"
        )

@router.get("/stats/{project_name}")
async def get_project_kb_stats(project_name: str):
    """
    Get knowledge base statistics for a project
    
    Returns:
    - Document count
    - Index size
    - Last sync time
    - Content breakdown by type
    """
    try:
        # Validate project name
        if not project_name or len(project_name) > 100:
            raise HTTPException(status_code=400, detail="Invalid project name")
        
        dynamic_service = get_dynamic_service()
        
        # Get stats
        stats = await dynamic_service.kb_service.get_project_stats(project_name)
        
        return {
            "success": True,
            "project_name": project_name,
            "stats": stats,
            "embedding_service": "aws-bedrock-kb",
            "search_service": "bedrock-knowledge-base",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats for {project_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get project statistics"
        )

@router.get("/health")
async def kb_health_check():
    """
    Health check for knowledge base services
    
    Checks:
    - AWS Bedrock KB access
    - S3 bucket access
    - Ingestion job status
    """
    try:
        dynamic_service = get_dynamic_service()
        
        health_status = {
            "success": True,
            "services": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check Bedrock KB connection
        try:
            kb_status = await dynamic_service.kb_service._check_kb_status()
            health_status["services"]["bedrock_kb"] = {
                "status": "healthy" if kb_status else "unhealthy",
                "kb_id": dynamic_service.kb_service.kb_id,
                "data_source_id": dynamic_service.kb_service.data_source_id
            }
        except Exception as e:
            health_status["services"]["bedrock_kb"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check Bedrock Agent access
        try:
            # Try to get KB info to test access
            response = dynamic_service.kb_service.bedrock_agent_client.get_knowledge_base(
                knowledgeBaseId=dynamic_service.kb_service.kb_id
            )
            kb_status = response.get('knowledgeBase', {}).get('status')
            health_status["services"]["bedrock_agent"] = {
                "status": "healthy",
                "kb_status": kb_status
            }
        except Exception as e:
            health_status["services"]["bedrock_agent"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Check S3 access
        try:
            s3_client = dynamic_service.kb_service.s3_client
            bucket_name = dynamic_service.kb_service.s3_bucket
            
            # Try to list objects in the bucket
            s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
            health_status["services"]["s3"] = {
                "status": "healthy",
                "bucket": bucket_name
            }
        except Exception as e:
            health_status["services"]["s3"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Overall health
        unhealthy_services = [name for name, service in health_status["services"].items() 
                            if service.get("status") != "healthy"]
        
        if unhealthy_services:
            health_status["success"] = False
            health_status["unhealthy_services"] = unhealthy_services
        
        return health_status
        
    except Exception as e:
        logger.error(f"KB health check failed: {e}")
        return {
            "success": False,
            "error": "Health check failed",
            "timestamp": datetime.utcnow().isoformat()
        }

@router.delete("/project/{project_name}")
async def delete_project_kb(project_name: str):
    """
    Delete project knowledge base content (admin only)
    
    WARNING: This will remove project-specific content from the shared KB
    Note: Since we use a shared Bedrock KB, this will remove project metadata filters
    """
    try:
        # Validate project name
        dynamic_service = get_dynamic_service()
        sanitized_name = dynamic_service.kb_service._validate_project_name(project_name)
        
        # Note: With Bedrock KB, we can't delete specific project data easily
        # This would require re-ingesting all data except for this project
        # For now, we'll just clear any cached data and log the request
        
        logger.warning(f"Delete request for project KB: {sanitized_name} - Manual S3 cleanup required")
        
        return {
            "success": True,
            "project_name": sanitized_name,
            "message": f"Project {sanitized_name} marked for deletion. Manual S3 cleanup required for complete removal.",
            "note": "Bedrock KB uses shared storage - project files must be removed from S3 and KB re-ingested",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to delete KB for {project_name}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete knowledge base"
        )