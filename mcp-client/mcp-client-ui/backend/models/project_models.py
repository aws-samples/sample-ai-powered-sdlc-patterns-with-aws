"""Project-specific models for project creation and management."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, validator


class CreateProjectRequest(BaseModel):
    """Request model for creating a new project."""
    name: str
    description: str
    project_type: str = "web"
    assigned_groups: List[str] = ["Developers"]
    assigned_users: List[str] = []
    status: str = "active"
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Project name is required')
        if len(v.strip()) > 100:
            raise ValueError('Project name too long (maximum 100 characters)')
        # Convert to project_id format (lowercase, replace spaces with hyphens)
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Project description is required')
        if len(v.strip()) > 500:
            raise ValueError('Project description too long (maximum 500 characters)')
        return v.strip()
    
    @validator('project_type')
    def validate_project_type(cls, v):
        allowed_types = ['web', 'mobile', 'api', 'desktop', 'data', 'ml', 'other']
        if v not in allowed_types:
            raise ValueError(f'Project type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('assigned_groups')
    def validate_assigned_groups(cls, v):
        if not v:
            return ["Developers"]  # Default group
        for group in v:
            if not isinstance(group, str) or not group.strip():
                raise ValueError('Each assigned group must be a non-empty string')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'archived']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v


class ProjectMetadata(BaseModel):
    """Project metadata model matching S3 structure."""
    project_id: str
    name: str
    description: str
    created_at: str
    assigned_groups: List[str]
    assigned_users: List[str]
    project_type: str
    status: str
    last_updated: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CreateProjectResponse(BaseModel):
    """Response model for project creation."""
    success: bool
    project_id: str
    message: str
    metadata: ProjectMetadata