"""API request and response models."""

import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, validator


class ProjectRequest(BaseModel):
    """Request model for project creation."""
    name: str
    type: str
    description: str
    userRole: str
    createdAt: str
    status: str


class ChatboxRequest(BaseModel):
    """Request model for chatbox conversations."""
    message: str
    conversation_id: Optional[str] = None
    project_name: Optional[str] = None
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v.strip()) > 10000:
            raise ValueError('Message too long (maximum 10000 characters)')
        return v.strip()
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        if v is not None:
            if not isinstance(v, str) or not v.strip():
                raise ValueError('Conversation ID must be a non-empty string')
            if len(v.strip()) > 100:
                raise ValueError('Conversation ID too long (maximum 100 characters)')
            if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
                raise ValueError('Conversation ID can only contain letters, numbers, hyphens, and underscores')
            return v.strip()
        return v


class ChatboxResponse(BaseModel):
    """Response model for chatbox conversations."""
    response: str
    conversation_id: str
    status: str
    timestamp: str
    tools_used: List[str] = []
    jira_data_updated: Optional[bool] = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator('response')
    def validate_response(cls, v):
        if not isinstance(v, str):
            raise ValueError('Response must be a string')
        return v
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        if not isinstance(v, str) or not v.strip():
            raise ValueError('Conversation ID must be a non-empty string')
        return v.strip()
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['success', 'error', 'partial']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        if not isinstance(v, str):
            raise ValueError('Timestamp must be a string')
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Timestamp must be in ISO format')
        return v
    
    @validator('tools_used')
    def validate_tools_used(cls, v):
        if v is not None:
            if not isinstance(v, list):
                raise ValueError('Tools used must be a list')
            for tool in v:
                if not isinstance(tool, str):
                    raise ValueError('Each tool name must be a string')
        return v


class CodeGenerationRequest(BaseModel):
    """Request model for code generation from diagrams."""
    project_id: str
    diagram_url: Optional[str] = None
    architecture_description: Optional[str] = None
    code_type: str = "cloudformation"
    target_platform: str = "aws"
    project_name: Optional[str] = None
    
    @validator('project_id')
    def validate_project_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Project ID is required')
        return v.strip()
    
    @validator('code_type')
    def validate_code_type(cls, v):
        allowed_types = ['cloudformation', 'terraform', 'kubernetes']
        if v not in allowed_types:
            raise ValueError(f'Code type must be one of: {", ".join(allowed_types)}')
        return v
    
    @validator('target_platform')
    def validate_target_platform(cls, v):
        allowed_platforms = ['aws']
        if v not in allowed_platforms:
            raise ValueError(f'Target platform must be one of: {", ".join(allowed_platforms)}')
        return v