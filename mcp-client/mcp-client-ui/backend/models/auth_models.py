"""Authentication-related data models."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, validator
from dataclasses import dataclass


@dataclass
class UserClaims:
    """User claims extracted from JWT token."""
    user_id: str
    username: str
    email: str
    groups: List[str]
    token_expiry: datetime
    issued_at: datetime
    cognito_sub: str


class AuthenticationRequest(BaseModel):
    """Request model for user authentication."""
    username: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username is required')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_info: Dict[str, Any]


class UserCreateRequest(BaseModel):
    """Request model for creating a new user."""
    username: str
    email: str
    password: str
    group: str
    temporary_password: bool = True
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username is required')
        if len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v.strip()
    
    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Valid email is required')
        return v.strip().lower()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @validator('group')
    def validate_group(cls, v):
        if not v or not v.strip():
            raise ValueError('Group assignment is required')
        return v.strip()


class UserUpdateRequest(BaseModel):
    """Request model for updating user information."""
    email: Optional[str] = None
    group: Optional[str] = None
    enabled: Optional[bool] = None
    
    @validator('email')
    def validate_email(cls, v):
        if v is not None and ('@' not in v or not v.strip()):
            raise ValueError('Valid email is required')
        return v.strip().lower() if v else None
    
    @validator('group')
    def validate_group(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Group cannot be empty')
        return v.strip() if v else None


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    user_id: str
    username: str
    groups: List[str]
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UserInfo(BaseModel):
    """User information model."""
    user_id: str
    username: str
    email: str
    groups: List[str]
    enabled: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@dataclass
class GroupConfig:
    """Group configuration model."""
    group_name: str
    description: str
    iam_role_arn: str
    s3_path_prefix: str
    project_permissions: List[str]
    created_at: datetime
    member_count: int


@dataclass
class ProjectAccess:
    """Project access model."""
    project_id: str
    group_name: str
    access_level: str  # 'read', 'write', 'admin'
    granted_at: datetime
    granted_by: str


class GroupCreateRequest(BaseModel):
    """Request model for creating a new group."""
    group_name: str
    description: str
    iam_role_arn: Optional[str] = None
    project_permissions: List[str] = ['read', 'write']
    
    @validator('group_name')
    def validate_group_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Group name is required')
        if len(v.strip()) < 3:
            raise ValueError('Group name must be at least 3 characters long')
        # Check for valid characters (alphanumeric, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
            raise ValueError('Group name can only contain letters, numbers, hyphens, and underscores')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Group description is required')
        return v.strip()
    
    @validator('project_permissions')
    def validate_permissions(cls, v):
        valid_permissions = {'read', 'write', 'admin'}
        if not v:
            return ['read', 'write']
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(f'Invalid permission: {perm}. Valid permissions are: {valid_permissions}')
        return v


class GroupUpdateRequest(BaseModel):
    """Request model for updating group information."""
    description: Optional[str] = None
    iam_role_arn: Optional[str] = None
    project_permissions: Optional[List[str]] = None
    
    @validator('description')
    def validate_description(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip() if v else None
    
    @validator('project_permissions')
    def validate_permissions(cls, v):
        if v is not None:
            valid_permissions = {'read', 'write', 'admin'}
            for perm in v:
                if perm not in valid_permissions:
                    raise ValueError(f'Invalid permission: {perm}. Valid permissions are: {valid_permissions}')
        return v


class ProjectAssignmentRequest(BaseModel):
    """Request model for assigning projects to groups."""
    project_id: str
    group_name: str
    access_level: str = 'write'
    
    @validator('project_id')
    def validate_project_id(cls, v):
        if not v or not v.strip():
            raise ValueError('Project ID is required')
        return v.strip()
    
    @validator('group_name')
    def validate_group_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Group name is required')
        return v.strip()
    
    @validator('access_level')
    def validate_access_level(cls, v):
        valid_levels = {'read', 'write', 'admin'}
        if v not in valid_levels:
            raise ValueError(f'Invalid access level: {v}. Valid levels are: {valid_levels}')
        return v


# Additional models for authentication API endpoints

class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username is required')
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v:
            raise ValueError('Password is required')
        return v


class LoginResponse(BaseModel):
    """Response model for successful login."""
    access_token: str
    refresh_token: str
    id_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    user: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    amazonq_token: Optional[str] = None  # Token from Amazon Q API Gateway


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str
    
    @validator('refresh_token')
    def validate_refresh_token(cls, v):
        if not v or not v.strip():
            raise ValueError('Refresh token is required')
        return v.strip()


class TokenRefreshResponse(BaseModel):
    """Response model for token refresh."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response model for user profile information."""
    user_id: str
    username: str
    email: str
    groups: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class GroupInfo(BaseModel):
    """Group information model."""
    group_name: str
    description: str
    member_count: int
    created_at: datetime
    iam_role_arn: Optional[str] = None
    project_permissions: List[str] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Signup-related models

class SignUpRequest(BaseModel):
    """Request model for user signup."""
    username: str
    email: str
    password: str
    firstName: str
    lastName: str
    sdlcRole: str
    userGroup: str = 'admins'  # Default to admin as requested
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username is required')
        if len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v.strip()
    
    @validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Valid email is required')
        return v.strip().lower()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        # Check for uppercase, lowercase, and number
        import re
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @validator('firstName')
    def validate_first_name(cls, v):
        if not v or not v.strip():
            raise ValueError('First name is required')
        return v.strip()
    
    @validator('lastName')
    def validate_last_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Last name is required')
        return v.strip()
    
    @validator('sdlcRole')
    def validate_sdlc_role(cls, v):
        valid_roles = {
            'requirements-analyst',
            'system-architect', 
            'software-developer',
            'qa-engineer',
            'devops-engineer',
            'maintenance-specialist'
        }
        if not v or v not in valid_roles:
            raise ValueError(f'Invalid SDLC role. Valid roles are: {valid_roles}')
        return v
    

class SignUpResponse(BaseModel):
    """Response model for user signup."""
    message: str
    userSub: Optional[str] = None
    status: str = "success"


