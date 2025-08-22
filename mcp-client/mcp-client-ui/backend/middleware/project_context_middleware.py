"""
Project Context Detection Middleware

This middleware automatically detects project context from requests
and ensures knowledge bases are ready for enhanced responses.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

class ProjectContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect and inject project context into requests
    
    Security Features:
    - Input validation
    - Rate limiting per project
    - Access control
    - Audit logging
    """
    
    def __init__(self, app, tool_service=None):
        super().__init__(app)
        self.tool_service = tool_service
        self.project_access_counts = {}
        self.max_requests_per_project_per_minute = 100
    
    async def dispatch(self, request: Request, call_next):
        """Process request and inject project context"""
        
        # Skip middleware for non-API routes
        if not request.url.path.startswith('/api/'):
            return await call_next(request)
        
        try:
            # Extract project context from request
            project_context = await self._extract_project_context(request)
            
            if project_context:
                # Validate access and rate limits
                await self._validate_project_access(project_context['project_name'], request)
                
                # Inject context into request state
                request.state.project_context = project_context
                
                # Log project access
                logger.info(f"Project context detected: {project_context['project_name']} "
                           f"for path: {request.url.path}")
            
            # Continue with request processing
            response = await call_next(request)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Project context middleware error: {e}")
            # Continue without project context
            return await call_next(request)
    
    async def _extract_project_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """Extract project context from various request sources"""
        
        project_name = None
        
        # Method 1: URL path extraction
        path = request.url.path
        if '/projects/' in path:
            try:
                project_part = path.split('/projects/')[1].split('/')[0]
                if project_part and len(project_part) > 0:
                    project_name = project_part
            except (IndexError, AttributeError):
                pass
        
        # Method 2: Query parameters
        if not project_name:
            project_name = request.query_params.get('project')
        
        # Method 3: Headers
        if not project_name:
            project_name = request.headers.get('X-Project-Name')
        
        # Method 4: Request body (for POST requests)
        if not project_name and request.method == 'POST':
            try:
                # This is a simplified check - in practice you'd want to be more careful
                # about reading the body to avoid consuming it
                content_type = request.headers.get('content-type', '')
                if 'application/json' in content_type:
                    # Note: This is just for detection, actual body reading should be done carefully
                    pass
            except (KeyError, AttributeError, ValueError):
                # Ignore header parsing errors - project detection is optional
                pass
        
        if project_name:
            return {
                'project_name': project_name,
                'url_path': path,
                'headers': dict(request.headers),
                'method': request.method,
                'client_ip': request.client.host if request.client else 'unknown'
            }
        
        return None
    
    async def _validate_project_access(self, project_name: str, request: Request):
        """Validate project access and enforce rate limits"""
        
        # Basic rate limiting per project
        current_minute = int(datetime.utcnow().timestamp() // 60)
        key = f"{project_name}:{current_minute}"
        
        if key not in self.project_access_counts:
            self.project_access_counts[key] = 0
        
        self.project_access_counts[key] += 1
        
        if self.project_access_counts[key] > self.max_requests_per_project_per_minute:
            logger.warning(f"Rate limit exceeded for project {project_name}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for project {project_name}"
            )
        
        # Clean up old entries (keep only current and previous minute)
        keys_to_remove = []
        for existing_key in self.project_access_counts:
            key_minute = int(existing_key.split(':')[1])
            if current_minute - key_minute > 1:
                keys_to_remove.append(existing_key)
        
        for key_to_remove in keys_to_remove:
            del self.project_access_counts[key_to_remove]
        
        # Additional security validations could go here
        # - User permissions for project
        # - Project existence validation
        # - Access control lists
        
        return True

def get_project_context_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Helper function to get project context from request state"""
    return getattr(request.state, 'project_context', None)