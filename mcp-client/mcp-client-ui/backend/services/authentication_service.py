"""
Authentication Service for JWT handling and user management.

This service handles JWT token validation, user claims extraction, token refresh,
user management operations, and secure session management using AWS Cognito.
"""

import jwt
import boto3
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from botocore.exceptions import ClientError, NoCredentialsError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import requests

from models.auth_models import UserClaims, UserCreateRequest, UserUpdateRequest, SessionInfo, UserInfo
from services.cognito_config_service import CognitoConfigService
from services.time_sync_service import time_sync_service


class AuthenticationService:
    """
    Service for handling JWT validation and user authentication with AWS Cognito.
    
    This service provides:
    - JWT token validation and parsing
    - User claims extraction from tokens
    - Token refresh functionality
    - User management operations (create, update, deactivate)
    - Secure session management
    """
    
    # AWS Cognito JWT token type identifiers (not secrets - these are standard JWT claim values)
    JWT_TOKEN_TYPE_ID = 'id'        # Standard AWS Cognito ID token type
    JWT_TOKEN_TYPE_ACCESS = 'access'  # Standard AWS Cognito access token type
    
    def __init__(self, cognito_config: CognitoConfigService):
        """
        Initialize the Authentication Service.
        
        Args:
            cognito_config: CognitoConfigService instance for Cognito operations
        """
        self.cognito_config = cognito_config
        self.user_pool_id = cognito_config.user_pool_id
        self.client_id = cognito_config.client_id
        self.region = cognito_config.region
        self.logger = logging.getLogger(__name__)
        
        try:
            self.cognito_client = boto3.client('cognito-idp', region_name=self.region)
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS Cognito client: {str(e)}")
            raise
        
        # Cache for JWT public keys
        self._jwks_cache = {}
        self._jwks_cache_expiry = None
        
        # In-memory session storage (in production, use Redis or DynamoDB)
        self._active_sessions: Dict[str, SessionInfo] = {}
        
        # Initialize time synchronization
        if time_sync_service.should_resync():
            time_sync_service.sync_with_ntp()
    
    def validate_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a JWT token and return its claims.
        
        Args:
            token: JWT token string to validate
            
        Returns:
            Dictionary containing token claims if valid, None otherwise
        """
        try:
            # Get JWT header to determine key ID
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get('kid')
            
            if not key_id:
                self.logger.error("JWT token missing key ID")
                return None
            
            # Get public key for verification
            public_key = self._get_public_key(key_id)
            if not public_key:
                self.logger.error(f"Could not retrieve public key for key ID: {key_id}")
                return None
            
            # First, decode without audience validation to check token type
            unverified_claims = jwt.decode(
                token,
                public_key,
                algorithms=['RS256'],
                options={"verify_aud": False},
                issuer=f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}',
                leeway=timedelta(seconds=30)  # Allow 30 seconds clock skew
            )
            
            # Determine expected audience based on token type
            token_use = unverified_claims.get('token_use')
            if token_use == self.JWT_TOKEN_TYPE_ID:
                # ID tokens have client_id as audience
                expected_audience = self.client_id
            elif token_use == self.JWT_TOKEN_TYPE_ACCESS:
                # Access tokens may not have audience or have different audience
                # For access tokens, we'll skip audience validation
                expected_audience = None
            else:
                self.logger.error(f"Invalid token use: {token_use}")
                return None
            
            # Now decode with proper audience validation and clock skew tolerance
            decode_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "require_exp": True,
                "require_iat": True,
                "require_nbf": False
            }
            
            if expected_audience:
                claims = jwt.decode(
                    token,
                    public_key,
                    algorithms=['RS256'],
                    audience=expected_audience,
                    issuer=f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}',
                    options=decode_options,
                    leeway=timedelta(seconds=30)  # Allow 30 seconds clock skew
                )
            else:
                # For access tokens, skip audience validation
                decode_options["verify_aud"] = False
                claims = jwt.decode(
                    token,
                    public_key,
                    algorithms=['RS256'],
                    options=decode_options,
                    issuer=f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}',
                    leeway=timedelta(seconds=30)  # Allow 30 seconds clock skew
                )
            
            # Validate token type and usage (accept both id and access tokens)
            token_use = claims.get('token_use')
            if token_use not in ['id', 'access']:
                self.logger.error(f"Invalid token use: {token_use}")
                return None
            
            # Additional validation for token timestamps using time sync service
            iat_timestamp = claims.get('iat', 0)
            exp_timestamp = claims.get('exp', 0)
            
            if not time_sync_service.validate_token_time(iat_timestamp, exp_timestamp):
                return None
            
            self.logger.debug(f"Successfully validated JWT token for user: {claims.get('username')}")
            return claims
            
        except jwt.ExpiredSignatureError:
            self.logger.error("JWT token has expired")
            return None
        except jwt.ImmatureSignatureError as e:
            self.logger.error(f"JWT token not yet valid (clock skew issue): {str(e)}")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.error(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error validating JWT token: {str(e)}")
            return None
    
    def extract_user_claims(self, token: str) -> Optional[UserClaims]:
        """
        Extract user claims from a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            UserClaims object if token is valid, None otherwise
        """
        claims = self.validate_jwt_token(token)
        if not claims:
            return None
        
        try:
            # Extract groups from token claims
            groups = claims.get('cognito:groups', [])
            if isinstance(groups, str):
                groups = [groups]
            
            user_claims = UserClaims(
                user_id=claims.get('sub', ''),
                username=claims.get('username', ''),
                email=claims.get('email', ''),
                groups=groups,
                token_expiry=datetime.fromtimestamp(claims.get('exp', 0), tz=timezone.utc),
                issued_at=datetime.fromtimestamp(claims.get('iat', 0), tz=timezone.utc),
                cognito_sub=claims.get('sub', '')
            )
            
            return user_claims
            
        except Exception as e:
            self.logger.error(f"Error extracting user claims: {str(e)}")
            return None
    
    def get_user_groups(self, token: str) -> List[str]:
        """
        Extract user groups from a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            List of group names the user belongs to
        """
        user_claims = self.extract_user_claims(token)
        return user_claims.groups if user_claims else []
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            Dictionary containing new tokens if successful, None otherwise
        """
        try:
            response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            auth_result = response.get('AuthenticationResult', {})
            
            if not auth_result:
                self.logger.error("No authentication result in refresh token response")
                return None
            
            token_data = {
                'access_token': auth_result.get('AccessToken'),
                'token_type': 'Bearer',
                'expires_in': auth_result.get('ExpiresIn', 3600)
            }
            
            # Include new refresh token if provided
            if 'RefreshToken' in auth_result:
                token_data['refresh_token'] = auth_result['RefreshToken']
            
            self.logger.info("Successfully refreshed access token")
            return token_data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                self.logger.error("Refresh token is invalid or expired")
            else:
                self.logger.error(f"Failed to refresh token: {e.response['Error']['Message']}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error refreshing token: {str(e)}")
            return None
    
    def create_user(self, user_request: UserCreateRequest) -> bool:
        """
        Create a new user in the Cognito User Pool.
        
        Args:
            user_request: UserCreateRequest containing user details
            
        Returns:
            True if user was created successfully, False otherwise
        """
        try:
            # Create user in Cognito
            create_params = {
                'UserPoolId': self.user_pool_id,
                'Username': user_request.username,
                'UserAttributes': [
                    {'Name': 'email', 'Value': user_request.email},
                    {'Name': 'email_verified', 'Value': 'true'}
                ],
                'MessageAction': 'SUPPRESS'  # Don't send welcome email
            }
            
            if user_request.temporary_password:
                create_params['TemporaryPassword'] = user_request.password
            else:
                create_params['Password'] = user_request.password
            
            self.cognito_client.admin_create_user(**create_params)
            
            # Add user to specified group
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=self.user_pool_id,
                Username=user_request.username,
                GroupName=user_request.group
            )
            
            # If not temporary password, set permanent password
            if not user_request.temporary_password:
                self.cognito_client.admin_set_user_password(
                    UserPoolId=self.user_pool_id,
                    Username=user_request.username,
                    Password=user_request.password,
                    Permanent=True
                )
            
            self.logger.info(f"Successfully created user: {user_request.username}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                self.logger.error(f"User {user_request.username} already exists")
            else:
                self.logger.error(f"Failed to create user: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error creating user: {str(e)}")
            return False
    
    def update_user_group(self, username: str, new_group: str) -> bool:
        """
        Update a user's group membership.
        
        Args:
            username: Username to update
            new_group: New group name to assign
            
        Returns:
            True if group was updated successfully, False otherwise
        """
        try:
            # Get current user groups
            current_groups = self._get_user_groups(username)
            
            # Remove user from all current groups
            for group in current_groups:
                self.cognito_client.admin_remove_user_from_group(
                    UserPoolId=self.user_pool_id,
                    Username=username,
                    GroupName=group
                )
            
            # Add user to new group
            self.cognito_client.admin_add_user_to_group(
                UserPoolId=self.user_pool_id,
                Username=username,
                GroupName=new_group
            )
            
            self.logger.info(f"Updated user {username} group to: {new_group}")
            return True
            
        except ClientError as e:
            self.logger.error(f"Failed to update user group: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error updating user group: {str(e)}")
            return False
    
    def deactivate_user(self, username: str) -> bool:
        """
        Deactivate a user account.
        
        Args:
            username: Username to deactivate
            
        Returns:
            True if user was deactivated successfully, False otherwise
        """
        try:
            # Disable the user account
            self.cognito_client.admin_disable_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            # Sign out user from all devices
            self.cognito_client.admin_user_global_sign_out(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            
            # Remove user from active sessions
            self._remove_user_sessions(username)
            
            self.logger.info(f"Successfully deactivated user: {username}")
            return True
            
        except ClientError as e:
            self.logger.error(f"Failed to deactivate user: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error deactivating user: {str(e)}")
            return False
    
    def list_users_in_group(self, group_name: str) -> List[UserInfo]:
        """
        List all users in a specific group.
        
        Args:
            group_name: Name of the group
            
        Returns:
            List of UserInfo objects for users in the group
        """
        try:
            response = self.cognito_client.list_users_in_group(
                UserPoolId=self.user_pool_id,
                GroupName=group_name
            )
            
            users = []
            for user_data in response.get('Users', []):
                user_info = self._parse_user_info(user_data, [group_name])
                if user_info:
                    users.append(user_info)
            
            return users
            
        except ClientError as e:
            self.logger.error(f"Failed to list users in group: {e.response['Error']['Message']}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error listing users in group: {str(e)}")
            return []
    
    def create_session(self, user_claims: UserClaims) -> str:
        """
        Create a new user session.
        
        Args:
            user_claims: UserClaims object containing user information
            
        Returns:
            Session ID string
        """
        session_id = secrets.token_urlsafe(32)
        
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user_claims.user_id,
            username=user_claims.username,
            groups=user_claims.groups,
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc),
            expires_at=user_claims.token_expiry
        )
        
        self._active_sessions[session_id] = session_info
        
        # Clean up expired sessions
        self._cleanup_expired_sessions()
        
        self.logger.debug(f"Created session {session_id} for user {user_claims.username}")
        return session_id
    
    def validate_session(self, session_id: str) -> bool:
        """
        Validate if a session is active and not expired.
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            True if session is valid, False otherwise
        """
        session = self._active_sessions.get(session_id)
        if not session:
            return False
        
        # Check if session has expired
        if datetime.now(timezone.utc) >= session.expires_at:
            self.invalidate_session(session_id)
            return False
        
        # Update last activity
        session.last_activity = datetime.now(timezone.utc)
        return True
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a user session.
        
        Args:
            session_id: Session ID to invalidate
            
        Returns:
            True if session was invalidated, False if session didn't exist
        """
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            self.logger.debug(f"Invalidated session: {session_id}")
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """
        Get session information.
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            SessionInfo object if session exists, None otherwise
        """
        return self._active_sessions.get(session_id)
    
    def _get_public_key(self, key_id: str) -> Optional[str]:
        """Get public key for JWT verification from Cognito JWKS endpoint."""
        try:
            # Check cache first
            if (self._jwks_cache_expiry and 
                datetime.now(timezone.utc) < self._jwks_cache_expiry and 
                key_id in self._jwks_cache):
                return self._jwks_cache[key_id]
            
            # Fetch JWKS from Cognito
            jwks_url = f'https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json'
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            
            jwks = response.json()
            
            # Find the key with matching key ID
            for key in jwks.get('keys', []):
                if key.get('kid') == key_id:
                    # Convert JWK to PEM format
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    pem_key = public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode('utf-8')
                    
                    # Cache the key for 1 hour
                    self._jwks_cache[key_id] = pem_key
                    self._jwks_cache_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
                    
                    return pem_key
            
            self.logger.error(f"Key ID {key_id} not found in JWKS")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching public key: {str(e)}")
            return None
    
    def _get_user_groups(self, username: str) -> List[str]:
        """Get list of groups for a user."""
        try:
            response = self.cognito_client.admin_list_groups_for_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            return [group['GroupName'] for group in response.get('Groups', [])]
        except ClientError:
            return []
    
    def _parse_user_info(self, user_data: Dict[str, Any], groups: List[str]) -> Optional[UserInfo]:
        """Parse Cognito user data into UserInfo object."""
        try:
            # Extract user attributes
            attributes = {attr['Name']: attr['Value'] for attr in user_data.get('Attributes', [])}
            
            return UserInfo(
                user_id=user_data.get('Username', ''),
                username=user_data.get('Username', ''),
                email=attributes.get('email', ''),
                groups=groups,
                enabled=user_data.get('Enabled', False),
                created_at=user_data.get('UserCreateDate', datetime.now(timezone.utc)),
                last_login=user_data.get('UserLastModifiedDate')
            )
        except Exception as e:
            self.logger.error(f"Error parsing user info: {str(e)}")
            return None
    
    def _remove_user_sessions(self, username: str) -> None:
        """Remove all sessions for a specific user."""
        sessions_to_remove = [
            session_id for session_id, session in self._active_sessions.items()
            if session.username == username
        ]
        
        for session_id in sessions_to_remove:
            del self._active_sessions[session_id]
    
    def _cleanup_expired_sessions(self) -> None:
        """Remove expired sessions from memory."""
        current_time = datetime.now(timezone.utc)
        expired_sessions = [
            session_id for session_id, session in self._active_sessions.items()
            if current_time >= session.expires_at
        ]
        
        for session_id in expired_sessions:
            del self._active_sessions[session_id]
        
        if expired_sessions:
            self.logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")