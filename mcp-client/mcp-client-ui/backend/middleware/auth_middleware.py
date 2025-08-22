"""
Authentication middleware for FastAPI.

This module provides JWT validation middleware, authentication decorators,
and group-based authorization decorators for protecting API endpoints.
"""

import logging
from typing import Optional, List, Callable, Any
from functools import wraps

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from models.auth_models import UserClaims
from services.authentication_service import AuthenticationService
from services.authorization_service import AuthorizationService


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for JWT token validation and user context injection.
    
    This middleware:
    - Validates JWT tokens on protected routes
    - Extracts user claims and adds them to request state
    - Handles authentication errors gracefully
    - Provides request context for user information
    """
    
    def __init__(self, app, auth_service: AuthenticationService, 
                 excluded_paths: Optional[List[str]] = None):
        """
        Initialize the authentication middleware.
        
        Args:
            app: FastAPI application instance
            auth_service: AuthenticationService instance
            excluded_paths: List of paths to exclude from authentication
        """
        super().__init__(app)
        self.auth_service = auth_service
        self.logger = logging.getLogger(__name__)
        
        # Default excluded paths (public endpoints)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/refresh"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process incoming requests and validate authentication.
        
        Args:
            request: FastAPI Request object
            call_next: Next middleware/handler in the chain
            
        Returns:
            Response object
        """
        # Skip authentication for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            self.logger.debug(f"Skipping auth for OPTIONS request to {request.url.path}")
            return await call_next(request)
        
        # Extract and validate JWT token
        try:
            token = self._extract_token(request)
            self.logger.debug(f"Extracted token for {request.method} {request.url.path}: {'Present' if token else 'Missing'}")
            if not token:
                return self._create_auth_error_response("Missing authentication token")
            
            # Validate token and extract user claims
            user_claims = self.auth_service.extract_user_claims(token)
            if not user_claims:
                return self._create_auth_error_response("Invalid or expired token")
            
            # Initialize request state if it doesn't exist
            if not hasattr(request, 'state'):
                from starlette.datastructures import State
                request.state = State()
            
            # Extract ID token for Amazon Q Business
            id_token = self._extract_id_token(request)
            
            # Add user context to request state
            request.state.user = user_claims
            request.state.authenticated = True
            request.state.jwt_token = token  # Access token for general auth
            request.state.id_token = id_token  # ID token for Amazon Q Business
            
            self.logger.debug(f"Authenticated user: {user_claims.username}")
            
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return self._create_auth_error_response("Authentication failed")
        
        # Continue to next middleware/handler
        response = await call_next(request)
        return response
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if a path should be excluded from authentication."""
        # First check explicit excluded paths
        for excluded_path in self.excluded_paths:
            # Exact match for root path
            if excluded_path == "/" and path == "/":
                return True
            # For other paths, check if it starts with the excluded path
            elif excluded_path != "/" and path.startswith(excluded_path):
                return True
        
        # For SPA routing: exclude all non-API routes (let React handle them)
        # Only require authentication for API routes
        if not path.startswith('/api/'):
            return True
            
        return False
    
    def _extract_token(self, request: Request) -> Optional[str]:
        """Extract JWT token from request headers."""
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        
        # Try cookie as fallback
        token_cookie = request.cookies.get("access_token")
        if token_cookie:
            return token_cookie
        
        return None
    
    def _extract_id_token(self, request: Request) -> Optional[str]:
        """Extract ID token from request headers for Amazon Q Business."""
        # Try X-ID-Token header first
        id_token_header = request.headers.get("X-ID-Token")
        if id_token_header:
            return id_token_header
        
        # Try cookie as fallback
        id_token_cookie = request.cookies.get("id_token")
        if id_token_cookie:
            return id_token_cookie
        
        return None
    
    def _create_auth_error_response(self, message: str) -> Response:
        """Create a standardized authentication error response."""
        from fastapi.responses import JSONResponse
        
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": message,
                "error": "authentication_required",
                "status_code": 401
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthDependency:
    """
    Dependency class for extracting authenticated user information.
    
    This class provides FastAPI dependencies for:
    - Getting current authenticated user
    - Validating user authentication
    - Extracting user claims from request context
    """
    
    def __init__(self, auth_service: AuthenticationService):
        """Initialize the auth dependency."""
        self.auth_service = auth_service
        self.security = HTTPBearer(auto_error=False)
        self.logger = logging.getLogger(__name__)
    
    async def get_current_user(self, request: Request) -> UserClaims:
        """
        Get the current authenticated user from request context.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            UserClaims object for the authenticated user
            
        Raises:
            HTTPException: If user is not authenticated
        """
        # Check if user is already authenticated by middleware
        if hasattr(request, 'state') and hasattr(request.state, 'user') and request.state.user:
            return request.state.user
        
        # Fallback: try to authenticate directly
        credentials = await self.security(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user_claims = self.auth_service.extract_user_claims(credentials.credentials)
        if not user_claims:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user_claims
    
    async def get_optional_user(self, request: Request) -> Optional[UserClaims]:
        """
        Get the current user if authenticated, None otherwise.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            UserClaims object if authenticated, None otherwise
        """
        try:
            return await self.get_current_user(request)
        except HTTPException:
            return None


def require_auth(auth_service: AuthenticationService):
    """
    Decorator factory for requiring authentication on route handlers.
    
    Args:
        auth_service: AuthenticationService instance
        
    Returns:
        Decorator function that validates authentication
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # Look in kwargs
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Check authentication
            if not hasattr(request.state, 'authenticated') or not request.state.authenticated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_groups(required_groups: List[str], auth_service: AuthenticationService):
    """
    Decorator factory for requiring specific group membership.
    
    Args:
        required_groups: List of group names that are allowed access
        auth_service: AuthenticationService instance
        
    Returns:
        Decorator function that validates group membership
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Check authentication first
            if not hasattr(request.state, 'user') or not request.state.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            user_claims: UserClaims = request.state.user
            
            # Check group membership
            user_groups = set(user_claims.groups)
            required_groups_set = set(required_groups)
            
            if not user_groups.intersection(required_groups_set):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required groups: {required_groups}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permission(resource: str, action: str, 
                      auth_service: AuthenticationService,
                      authorization_service: AuthorizationService):
    """
    Decorator factory for requiring specific permissions.
    
    Args:
        resource: Resource identifier (e.g., "project:123")
        action: Action to perform (e.g., "read", "write", "delete")
        auth_service: AuthenticationService instance
        authorization_service: AuthorizationService instance
        
    Returns:
        Decorator function that validates permissions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            # Check authentication first
            if not hasattr(request.state, 'user') or not request.state.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            user_claims: UserClaims = request.state.user
            
            # Check permission
            if not authorization_service.check_permission(user_claims, resource, action):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required permission: {action} on {resource}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class AuthContext:
    """
    Context manager for accessing authentication information in route handlers.
    
    This class provides convenient access to:
    - Current user information
    - User groups and permissions
    - Authentication status
    """
    
    def __init__(self, request: Request):
        """Initialize auth context from request."""
        self.request = request
        if hasattr(request, 'state'):
            self._user: Optional[UserClaims] = getattr(request.state, 'user', None)
            self._authenticated: bool = getattr(request.state, 'authenticated', False)
            self._jwt_token: Optional[str] = getattr(request.state, 'jwt_token', None)
            self._id_token: Optional[str] = getattr(request.state, 'id_token', None)
        else:
            self._user = None
            self._authenticated = False
            self._jwt_token = None
            self._id_token = None
    
    @property
    def is_authenticated(self) -> bool:
        """Check if the current request is authenticated."""
        return self._authenticated
    
    @property
    def user(self) -> Optional[UserClaims]:
        """Get the current authenticated user."""
        return self._user
    
    @property
    def user_id(self) -> Optional[str]:
        """Get the current user's ID."""
        return self._user.user_id if self._user else None
    
    @property
    def username(self) -> Optional[str]:
        """Get the current user's username."""
        return self._user.username if self._user else None
    
    @property
    def user_groups(self) -> List[str]:
        """Get the current user's groups."""
        return self._user.groups if self._user else []
    
    @property
    def user_email(self) -> Optional[str]:
        """Get the current user's email."""
        return self._user.email if self._user else None
    
    @property
    def jwt_token(self) -> Optional[str]:
        """Get the current JWT token (access token)."""
        return self._jwt_token
    
    @property
    def id_token(self) -> Optional[str]:
        """Get the current ID token for Amazon Q Business."""
        return getattr(self.request.state, 'id_token', None) if hasattr(self.request, 'state') else None
    
    def has_group(self, group_name: str) -> bool:
        """Check if the current user belongs to a specific group."""
        return group_name in self.user_groups
    
    def has_any_group(self, group_names: List[str]) -> bool:
        """Check if the current user belongs to any of the specified groups."""
        return bool(set(self.user_groups).intersection(set(group_names)))
    
    def is_admin(self) -> bool:
        """Check if the current user is an admin."""
        return self.has_group('admin')


def get_auth_context(request: Request) -> AuthContext:
    """
    Dependency function to get authentication context.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        AuthContext instance
    """
    return AuthContext(request)


# FastAPI Dependencies
def get_current_user_dependency(auth_service: AuthenticationService):
    """Create a FastAPI dependency for getting the current user."""
    auth_dep = AuthDependency(auth_service)
    return auth_dep.get_current_user


def get_optional_user_dependency(auth_service: AuthenticationService):
    """Create a FastAPI dependency for getting the current user (optional)."""
    auth_dep = AuthDependency(auth_service)
    return auth_dep.get_optional_user