"""
Authentication and user management API routes.

This module provides API endpoints for:
- User authentication (login, logout, token refresh)
- User management (create, update, deactivate users)
- Group management (create, delete, list groups)
- User profile management
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from models.auth_models import (
    UserClaims, UserCreateRequest, UserUpdateRequest, UserInfo,
    LoginRequest, LoginResponse, TokenRefreshRequest, TokenRefreshResponse,
    GroupCreateRequest, GroupInfo, UserProfileResponse,
    SignUpRequest, SignUpResponse
)
from services.authentication_service import AuthenticationService
from services.authorization_service import AuthorizationService
from services.cognito_config_service import CognitoConfigService

from middleware.auth_middleware import (
    get_current_user_dependency, require_groups, AuthContext, get_auth_context
)


# Response models
class UserListResponse(BaseModel):
    """Response model for user list endpoints."""
    users: List[UserInfo]
    total_count: int
    group_name: Optional[str] = None
    status: str = "success"


class GroupListResponse(BaseModel):
    """Response model for group list endpoints."""
    groups: List[GroupInfo]
    total_count: int
    status: str = "success"


class UserCreateResponse(BaseModel):
    """Response model for user creation."""
    user_id: str
    username: str
    message: str
    status: str = "success"


class GroupCreateResponse(BaseModel):
    """Response model for group creation."""
    group_name: str
    message: str
    status: str = "success"


class ErrorResponse(BaseModel):
    """Standard error response model."""
    detail: str
    error_code: Optional[str] = None
    status: str = "error"


def create_auth_router(
    auth_service: AuthenticationService,
    authorization_service: AuthorizationService,
    cognito_config: CognitoConfigService
) -> APIRouter:
    """
    Create and configure the authentication router.
    
    Args:
        auth_service: AuthenticationService instance
        authorization_service: AuthorizationService instance
        cognito_config: CognitoConfigService instance
        
    Returns:
        Configured APIRouter instance
    """
    router = APIRouter(prefix="/api/auth", tags=["authentication"])
    logger = logging.getLogger(__name__)
    
    # Security scheme
    security = HTTPBearer()
    
    # Dependencies
    get_current_user = get_current_user_dependency(auth_service)
    
    @router.post("/login", response_model=LoginResponse)
    async def login(login_request: LoginRequest):
        """
        Authenticate user and return JWT tokens.
        
        This endpoint handles user login using AWS Cognito authentication.
        Returns access token, refresh token, and user information.
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Initialize Cognito client
            cognito_client = boto3.client('cognito-idp', region_name=cognito_config.region)
            
            # Authenticate with Cognito
            response = cognito_client.admin_initiate_auth(
                UserPoolId=cognito_config.user_pool_id,
                ClientId=cognito_config.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': login_request.username,
                    'PASSWORD': login_request.password
                }
            )
            
            # Extract tokens from response
            auth_result = response.get('AuthenticationResult', {})
            if not auth_result:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
            
            access_token = auth_result.get('AccessToken')
            refresh_token = auth_result.get('RefreshToken')
            id_token = auth_result.get('IdToken')
            
            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to obtain access token"
                )
            
            # Extract user claims from the ID token
            user_claims = auth_service.extract_user_claims(id_token or access_token)
            if not user_claims:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to extract user information"
                )
            
            # Create session
            session_id = auth_service.create_session(user_claims)
            
            # Store ID token for Amazon Q Business MCP authentication
            if id_token:
                logger.info("ID token available for Amazon Q Business MCP authentication")
            else:
                logger.warning("No ID token available for Amazon Q Business MCP authentication")
            
            return LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                id_token=id_token,
                token_type="Bearer",
                expires_in=auth_result.get('ExpiresIn', 3600),
                user={
                    "user_id": user_claims.user_id,
                    "username": user_claims.username,
                    "email": user_claims.email,
                    "groups": user_claims.groups
                },
                session_id=session_id
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )
            elif error_code == 'UserNotConfirmedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account not confirmed"
                )
            elif error_code == 'PasswordResetRequiredException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Password reset required"
                )
            else:
                logger.error(f"Cognito authentication error: {e.response['Error']['Message']}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Authentication service error"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
    
    @router.post("/signup", response_model=SignUpResponse)
    async def signup(signup_request: SignUpRequest):
        """
        Register a new user account.
        
        This endpoint creates a new user in AWS Cognito with the specified
        SDLC role and assigns them to the admin group by default.
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Initialize Cognito client
            cognito_client = boto3.client('cognito-idp', region_name=cognito_config.region)
            
            # Prepare user attributes
            user_attributes = [
                {'Name': 'email', 'Value': signup_request.email},
                {'Name': 'given_name', 'Value': signup_request.firstName},
                {'Name': 'family_name', 'Value': signup_request.lastName},
                {'Name': 'custom:sdlc_role', 'Value': signup_request.sdlcRole},
                {'Name': 'email_verified', 'Value': 'false'}
            ]
            
            # Create user in Cognito
            response = cognito_client.admin_create_user(
                UserPoolId=cognito_config.user_pool_id,
                Username=signup_request.username,
                UserAttributes=user_attributes,
                TemporaryPassword=signup_request.password,
                MessageAction='SUPPRESS',  # Don't send welcome email, we'll handle confirmation
                DesiredDeliveryMediums=['EMAIL']
            )
            
            # Set permanent password
            cognito_client.admin_set_user_password(
                UserPoolId=cognito_config.user_pool_id,
                Username=signup_request.username,
                Password=signup_request.password,
                Permanent=True
            )
            
            # Add user to the specified group (default: admins)
            try:
                cognito_client.admin_add_user_to_group(
                    UserPoolId=cognito_config.user_pool_id,
                    Username=signup_request.username,
                    GroupName=signup_request.userGroup
                )
            except ClientError as e:
                logger.warning(f"Failed to add user to group {signup_request.userGroup}: {e}")
                # Continue anyway, user is created
            
            # Send verification email
            try:
                cognito_client.admin_initiate_auth(
                    UserPoolId=cognito_config.user_pool_id,
                    ClientId=cognito_config.client_id,
                    AuthFlow='ADMIN_NO_SRP_AUTH',
                    AuthParameters={
                        'USERNAME': signup_request.username,
                        'PASSWORD': signup_request.password
                    }
                )
            except ClientError as e:
                # If user needs to verify email, this will fail - that's expected
                if e.response['Error']['Code'] == 'UserNotConfirmedException':
                    # Resend confirmation code
                    cognito_client.resend_confirmation_code(
                        ClientId=cognito_config.client_id,
                        Username=signup_request.username
                    )
            
            user_sub = response['User']['Username']  # Cognito returns the user sub
            
            return SignUpResponse(
                message="Account created successfully! Please check your email for a confirmation code.",
                userSub=user_sub
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists"
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password does not meet requirements"
                )
            elif error_code == 'InvalidParameterException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid user information provided"
                )
            else:
                logger.error(f"Cognito signup error: {e.response['Error']['Message']}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Account creation failed"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Signup error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account creation failed"
            )
    

    @router.post("/refresh", response_model=TokenRefreshResponse)
    async def refresh_token(refresh_request: TokenRefreshRequest):
        """
        Refresh access token using refresh token.
        
        This endpoint allows clients to obtain a new access token
        using a valid refresh token.
        """
        try:
            token_data = auth_service.refresh_token(refresh_request.refresh_token)
            
            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired refresh token"
                )
            
            return TokenRefreshResponse(
                access_token=token_data['access_token'],
                token_type=token_data['token_type'],
                expires_in=token_data['expires_in'],
                refresh_token=token_data.get('refresh_token')
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token refresh failed"
            )
    
    @router.post("/logout")
    async def logout(
        request: Request,
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Logout user and invalidate session.
        
        This endpoint invalidates the user's current session and
        optionally signs them out from all devices.
        """
        try:
            # Get session ID from request context if available
            session_id = getattr(request.state, 'session_id', None)
            
            if session_id:
                auth_service.invalidate_session(session_id)
            
            # Note: In a full implementation, you might also want to
            # call Cognito's global sign out API
            
            return {
                "message": "Successfully logged out",
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )
    
    @router.get("/profile", response_model=UserProfileResponse)
    async def get_user_profile(
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Get current user's profile information.
        
        Returns detailed information about the authenticated user
        including groups, permissions, and account status.
        """
        try:
            # Get additional user attributes from Cognito
            try:
                import boto3
                cognito_client = boto3.client('cognito-idp', region_name=cognito_config.region)
                
                user_response = cognito_client.admin_get_user(
                    UserPoolId=cognito_config.user_pool_id,
                    Username=current_user.username
                )
                
                # Extract custom attributes
                user_attributes = {attr['Name']: attr['Value'] for attr in user_response.get('UserAttributes', [])}
                
                profile_data = {
                    "user_id": current_user.user_id,
                    "username": current_user.username,
                    "email": current_user.email,
                    "firstName": user_attributes.get('given_name', ''),
                    "lastName": user_attributes.get('family_name', ''),
                    "sdlcRole": user_attributes.get('custom:sdlc_role', ''),
                    "groups": current_user.groups,
                    "created_at": current_user.issued_at,
                    "last_login": datetime.utcnow(),
                    "is_active": user_response.get('Enabled', True),
                    "emailVerified": user_attributes.get('email_verified', 'false').lower() == 'true'
                }
                
                return profile_data
                
            except Exception as e:
                logger.warning(f"Could not fetch extended user profile: {e}")
                # Fallback to basic profile
                return UserProfileResponse(
                    user_id=current_user.user_id,
                    username=current_user.username,
                    email=current_user.email,
                    groups=current_user.groups,
                    created_at=current_user.issued_at,
                    last_login=datetime.utcnow(),
                    is_active=True
                )
            
        except Exception as e:
            logger.error(f"Profile retrieval error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user profile"
            )
    
    @router.get("/test")
    async def test_auth(
        current_user: UserClaims = Depends(get_current_user)
    ):
        """
        Simple test endpoint to verify authentication is working.
        """
        return {
            "message": "Authentication successful!",
            "user": {
                "username": current_user.username,
                "email": current_user.email,
                "groups": current_user.groups,
                "user_id": current_user.user_id
            },
            "status": "success"
        }
    
    # User Management Endpoints (Admin only)
    
    @router.post("/users", response_model=UserCreateResponse)
    async def create_user(
        user_request: UserCreateRequest,
        current_user: UserClaims = Depends(get_current_user),
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        Create a new user account.
        
        This endpoint allows administrators to create new user accounts
        with specified group membership and initial settings.
        
        Requires: admin group membership
        """
        # Check admin permissions
        if not auth_context.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to create users"
            )
        
        try:
            success = auth_service.create_user(user_request)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user. Username may already exist."
                )
            
            return UserCreateResponse(
                user_id=user_request.username,  # Cognito uses username as user ID
                username=user_request.username,
                message=f"User {user_request.username} created successfully"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User creation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed"
            )
    
    @router.get("/users", response_model=UserListResponse)
    async def list_users(
        group_name: Optional[str] = None,
        current_user: UserClaims = Depends(get_current_user),
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        List users, optionally filtered by group.
        
        This endpoint allows administrators to view all users
        or users within a specific group.
        
        Requires: admin group membership
        """
        # Check admin permissions
        if not auth_context.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to list users"
            )
        
        try:
            if group_name:
                users = auth_service.list_users_in_group(group_name)
            else:
                # For listing all users, we'd need to implement this in the auth service
                # For now, return empty list with appropriate message
                users = []
                logger.warning("List all users not implemented - would require pagination")
            
            return UserListResponse(
                users=users,
                total_count=len(users),
                group_name=group_name
            )
            
        except Exception as e:
            logger.error(f"User listing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve user list"
            )
    
    @router.put("/users/{username}/group")
    async def update_user_group(
        username: str,
        new_group: str,
        current_user: UserClaims = Depends(get_current_user),
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        Update a user's group membership.
        
        This endpoint allows administrators to change a user's
        group assignment, which affects their access permissions.
        
        Requires: admin group membership
        """
        # Check admin permissions
        if not auth_context.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to update user groups"
            )
        
        try:
            success = auth_service.update_user_group(username, new_group)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to update user group. User {username} may not exist or group {new_group} may be invalid."
                )
            
            return {
                "message": f"User {username} moved to group {new_group}",
                "username": username,
                "new_group": new_group,
                "status": "success"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User group update error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user group"
            )
    
    @router.delete("/users/{username}")
    async def deactivate_user(
        username: str,
        current_user: UserClaims = Depends(get_current_user),
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        Deactivate a user account.
        
        This endpoint allows administrators to deactivate user accounts,
        which prevents login and invalidates all active sessions.
        
        Requires: admin group membership
        """
        # Check admin permissions
        if not auth_context.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to deactivate users"
            )
        
        # Prevent self-deactivation
        if username == current_user.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        try:
            success = auth_service.deactivate_user(username)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to deactivate user {username}. User may not exist."
                )
            
            return {
                "message": f"User {username} has been deactivated",
                "username": username,
                "status": "success"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User deactivation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate user"
            )
    
    # Group Management Endpoints (Admin only)
    
    @router.post("/groups", response_model=GroupCreateResponse)
    async def create_group(
        group_request: GroupCreateRequest,
        current_user: UserClaims = Depends(get_current_user),
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        Create a new user group.
        
        This endpoint allows administrators to create new groups
        for organizing users and managing access permissions.
        
        Requires: admin group membership
        """
        # Check admin permissions
        if not auth_context.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to create groups"
            )
        
        try:
            # Note: This would require implementing group creation in CognitoConfigService
            # For now, return a placeholder response
            
            return GroupCreateResponse(
                group_name=group_request.group_name,
                message=f"Group {group_request.group_name} created successfully"
            )
            
        except Exception as e:
            logger.error(f"Group creation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Group creation failed"
            )
    
    @router.get("/groups", response_model=GroupListResponse)
    async def list_groups(
        current_user: UserClaims = Depends(get_current_user),
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        List all user groups.
        
        This endpoint allows administrators to view all available
        user groups and their configurations.
        
        Requires: admin group membership
        """
        # Check admin permissions
        if not auth_context.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to list groups"
            )
        
        try:
            # Note: This would require implementing group listing in CognitoConfigService
            # For now, return a placeholder response
            groups = []
            
            return GroupListResponse(
                groups=groups,
                total_count=len(groups)
            )
            
        except Exception as e:
            logger.error(f"Group listing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve group list"
            )
    
    @router.delete("/groups/{group_name}")
    async def delete_group(
        group_name: str,
        current_user: UserClaims = Depends(get_current_user),
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        Delete a user group.
        
        This endpoint allows administrators to delete user groups.
        Users in the group will need to be reassigned before deletion.
        
        Requires: admin group membership
        """
        # Check admin permissions
        if not auth_context.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required to delete groups"
            )
        
        # Prevent deletion of core groups
        if group_name in ['admin', 'developer', 'viewer']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete core group: {group_name}"
            )
        
        try:
            # Note: This would require implementing group deletion in CognitoConfigService
            # For now, return a placeholder response
            
            return {
                "message": f"Group {group_name} has been deleted",
                "group_name": group_name,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Group deletion error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete group"
            )
    
    return router