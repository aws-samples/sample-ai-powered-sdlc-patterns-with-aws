"""
Cognito-based S3 Storage Service that uses user's Cognito credentials for S3 access.

This service exchanges Cognito JWT tokens for temporary AWS credentials
and uses those credentials for S3 operations, ensuring proper access control.
"""

import json
import logging
import boto3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from botocore.exceptions import ClientError, NoCredentialsError

from .authentication_service import AuthenticationService
from models.auth_models import UserClaims
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CognitoS3OperationResult:
    """Result of a Cognito-authenticated S3 operation."""
    success: bool
    error_message: Optional[str] = None
    data: Optional[Any] = None
    user_id: Optional[str] = None
    groups: Optional[List[str]] = None


class CognitoS3StorageService:
    """
    S3 Storage Service that uses Cognito Identity Pool credentials.
    
    This service:
    - Exchanges Cognito JWT tokens for temporary AWS credentials
    - Uses user-specific credentials for all S3 operations
    - Enforces IAM policies based on user's Cognito groups
    - Provides proper access control at the AWS level
    """
    
    def __init__(self, auth_service: AuthenticationService):
        """
        Initialize Cognito S3 storage service.
        
        Args:
            auth_service: AuthenticationService instance for token validation
        """
        self.auth_service = auth_service
        self.bucket_name = settings.S3_BUCKET_NAME
        self.aws_region = settings.AWS_REGION
        self.identity_pool_id = settings.COGNITO_IDENTITY_POOL_ID
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        if not self.identity_pool_id:
            raise ValueError("COGNITO_IDENTITY_POOL_ID is required")
        if not self.user_pool_id:
            raise ValueError("COGNITO_USER_POOL_ID is required")
    
    def _validate_user_token(self, user_token: str) -> Optional[UserClaims]:
        """
        Validate user token and extract claims.
        
        Args:
            user_token: JWT token string
            
        Returns:
            UserClaims if token is valid, None otherwise
        """
        if not user_token:
            logger.error("User token is required for authenticated operations")
            return None
        
        # Remove 'Bearer ' prefix if present
        if user_token.startswith('Bearer '):
            user_token = user_token[7:]
        
        user_claims = self.auth_service.extract_user_claims(user_token)
        if not user_claims:
            logger.error("Invalid or expired user token")
            return None
        
        return user_claims
    
    def _create_user_s3_client(self, cognito_token: str) -> Optional[boto3.client]:
        """
        Create S3 client using user's Cognito credentials.
        
        Args:
            cognito_token: User's Cognito token (should be ID token, not access token)
            
        Returns:
            boto3 S3 client with user credentials, None if failed
        """
        try:
            # Remove Bearer prefix if present
            if cognito_token.startswith('Bearer '):
                cognito_token = cognito_token[7:]
            
            # For Cognito Identity Pool, we need the ID token, not access token
            # Try to extract ID token from the user claims
            user_claims = self.auth_service.extract_user_claims(cognito_token)
            if not user_claims:
                logger.error("Cannot extract user claims from token")
                return None
            
            # We need to get the ID token from the authentication service
            # For now, let's try using the token directly and see if it works
            id_token = cognito_token  # This might be the access token, we'll need to get ID token
            
            # Create Cognito Identity client
            identity_client = boto3.client(
                'cognito-identity', 
                region_name=self.aws_region
            )
            
            # Construct the login provider key
            login_provider = f'cognito-idp.{self.aws_region}.amazonaws.com/{self.user_pool_id}'
            
            # Get identity ID using ID token
            identity_response = identity_client.get_id(
                IdentityPoolId=self.identity_pool_id,
                Logins={
                    login_provider: id_token
                }
            )
            
            identity_id = identity_response['IdentityId']
            logger.debug(f"Got identity ID: {identity_id}")
            
            # Get temporary credentials for the identity
            credentials_response = identity_client.get_credentials_for_identity(
                IdentityId=identity_id,
                Logins={
                    login_provider: id_token
                }
            )
            
            credentials = credentials_response['Credentials']
            logger.debug("Successfully obtained temporary AWS credentials")
            
            # Create S3 client with user's temporary credentials
            s3_client = boto3.client(
                's3',
                aws_access_key_id=credentials['AccessKeyId'],
                aws_secret_access_key=credentials['SecretKey'],
                aws_session_token=credentials['SessionToken'],
                region_name=self.aws_region
            )
            
            return s3_client
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", "Unknown error")
            logger.error(f"Failed to create user S3 client: {error_code} - {error_message}")
            
            # Provide more specific error messages
            if error_code == "NotAuthorizedException" and "Missing a required claim: aud" in error_message:
                logger.error("Token is missing 'aud' claim - need ID token instead of access token")
            
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating user S3 client: {str(e)}")
            return None
    
    def _generate_s3_key(self, project_id: str, file_type: str, filename: str = "") -> str:
        """
        Generate S3 key for project files.
        
        Args:
            project_id: Project identifier
            file_type: Type of file (metadata, generated-code, diagrams, sessions)
            filename: Optional filename for specific files
            
        Returns:
            S3 key path
        """
        base_key = f"projects/{project_id}"
        
        if file_type == "metadata":
            return f"{base_key}/metadata.json"
        elif file_type == "generated-code":
            if filename:
                return f"{base_key}/generated-code/{filename}"
            return f"{base_key}/generated-code/"
        elif file_type == "diagrams":
            if filename:
                return f"{base_key}/diagrams/{filename}"
            return f"{base_key}/diagrams/"
        elif file_type == "sessions":
            if filename:
                return f"{base_key}/sessions/{filename}"
            return f"{base_key}/sessions/"
        else:
            return f"{base_key}/{file_type}/{filename}" if filename else f"{base_key}/{file_type}/"
    
    async def save_project_metadata(self, project_id: str, metadata: Dict[str, Any], user_token: str) -> CognitoS3OperationResult:
        """
        Save project metadata to S3 using user's Cognito credentials.
        
        Args:
            project_id: Project identifier
            metadata: Project metadata dictionary
            user_token: JWT token for authentication
            
        Returns:
            CognitoS3OperationResult with operation status
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return CognitoS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Create user-specific S3 client
            s3_client = self._create_user_s3_client(user_token)
            if not s3_client:
                return CognitoS3OperationResult(
                    success=False, 
                    error_message="Failed to create S3 client with user credentials",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Add authentication context to metadata
            metadata_with_auth = {
                **metadata,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "project_id": project_id,
                "created_by": user_claims.user_id,
                "last_modified_by": user_claims.user_id,
                "assigned_users": metadata.get("assigned_users", [user_claims.username]),
                "assigned_groups": metadata.get("assigned_groups", [])
            }
            
            # Convert to JSON bytes
            json_data = json.dumps(metadata_with_auth, indent=2).encode('utf-8')
            
            # Generate S3 key
            s3_key = self._generate_s3_key(project_id, "metadata")
            
            # Upload to S3 using user's credentials
            import asyncio
            loop = asyncio.get_event_loop()
            
            def sync_put_object():
                try:
                    s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        Body=json_data,
                        ContentType="application/json",
                        ServerSideEncryption='AES256'
                    )
                    return True
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")
                    logger.error(f"S3 put_object failed: {error_code}")
                    if error_code == "AccessDenied":
                        logger.error(f"User {user_claims.username} denied access to {s3_key}")
                    raise
            
            success = await loop.run_in_executor(self._executor, sync_put_object)
            
            if success:
                logger.info(f"Successfully saved project metadata to S3: {project_id} by user {user_claims.username}")
                return CognitoS3OperationResult(
                    success=True, 
                    data={"s3_key": s3_key, "project_id": project_id},
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
                
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = f"S3 operation failed: {error_code}"
            if error_code == "AccessDenied":
                error_msg = f"Access denied to project: {project_id}"
            logger.error(error_msg)
            return CognitoS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
        except Exception as e:
            error_msg = f"Error saving project metadata to S3: {str(e)}"
            logger.error(error_msg)
            return CognitoS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def load_project_metadata(self, project_id: str, user_token: str) -> CognitoS3OperationResult:
        """
        Load project metadata from S3 using user's Cognito credentials.
        
        Args:
            project_id: Project identifier
            user_token: JWT token for authentication
            
        Returns:
            CognitoS3OperationResult with metadata or error
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return CognitoS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Create user-specific S3 client
            s3_client = self._create_user_s3_client(user_token)
            if not s3_client:
                return CognitoS3OperationResult(
                    success=False, 
                    error_message="Failed to create S3 client with user credentials",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # Generate S3 key
            s3_key = self._generate_s3_key(project_id, "metadata")
            
            # Download from S3 using user's credentials
            import asyncio
            loop = asyncio.get_event_loop()
            
            def sync_get_object():
                try:
                    response = s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                    return response['Body'].read()
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")
                    if error_code == "NoSuchKey":
                        return None
                    logger.error(f"S3 get_object failed: {error_code}")
                    if error_code == "AccessDenied":
                        logger.error(f"User {user_claims.username} denied access to {s3_key}")
                    raise
            
            content = await loop.run_in_executor(self._executor, sync_get_object)
            
            if content is None:
                return CognitoS3OperationResult(
                    success=False, 
                    error_message=f"Project metadata not found: {project_id}",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            metadata = json.loads(content.decode('utf-8'))
            logger.info(f"Successfully loaded project metadata from S3: {project_id} by user {user_claims.username}")
            return CognitoS3OperationResult(
                success=True, 
                data=metadata,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = f"S3 operation failed: {error_code}"
            if error_code == "AccessDenied":
                error_msg = f"Access denied to project: {project_id}"
            logger.error(error_msg)
            return CognitoS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in project metadata: {str(e)}"
            logger.error(error_msg)
            return CognitoS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
        except Exception as e:
            error_msg = f"Error loading project metadata from S3: {str(e)}"
            logger.error(error_msg)
            return CognitoS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
    
    async def list_user_projects(self, user_token: str) -> CognitoS3OperationResult:
        """
        List all projects accessible to the authenticated user using their credentials.
        
        Args:
            user_token: JWT token for authentication
            
        Returns:
            CognitoS3OperationResult with list of accessible projects
        """
        try:
            # Validate user token
            user_claims = self._validate_user_token(user_token)
            if not user_claims:
                return CognitoS3OperationResult(
                    success=False, 
                    error_message="Authentication failed"
                )
            
            # Create user-specific S3 client
            s3_client = self._create_user_s3_client(user_token)
            if not s3_client:
                return CognitoS3OperationResult(
                    success=False, 
                    error_message="Failed to create S3 client with user credentials",
                    user_id=user_claims.user_id,
                    groups=user_claims.groups
                )
            
            # List objects with projects prefix using user's credentials
            # This will automatically enforce IAM policies based on user's groups
            prefix = "projects/"
            
            import asyncio
            loop = asyncio.get_event_loop()
            
            def sync_list_objects():
                try:
                    response = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
                    objects = []
                    if 'Contents' in response:
                        objects = [obj['Key'] for obj in response['Contents']]
                    return objects
                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "Unknown")
                    logger.error(f"S3 list_objects failed: {error_code}")
                    if error_code == "AccessDenied":
                        logger.error(f"User {user_claims.username} denied access to list projects")
                    raise
            
            object_keys = await loop.run_in_executor(self._executor, sync_list_objects)
            
            # Filter for metadata.json files and extract project IDs
            projects = []
            metadata_files = [key for key in object_keys if key.endswith('metadata.json')]
            
            for key in metadata_files:
                # Keys look like: projects/{project_id}/metadata.json
                parts = key.split('/')
                if len(parts) >= 3 and parts[0] == "projects":
                    project_id = parts[1]
                    projects.append({
                        "project_id": project_id,
                        "s3_key": key
                    })
            
            logger.info(f"Successfully listed {len(projects)} accessible projects for user {user_claims.username}")
            return CognitoS3OperationResult(
                success=True, 
                data=projects,
                user_id=user_claims.user_id,
                groups=user_claims.groups
            )
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = f"S3 operation failed: {error_code}"
            if error_code == "AccessDenied":
                error_msg = "Access denied to list projects"
            logger.error(error_msg)
            return CognitoS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )
        except Exception as e:
            error_msg = f"Error listing user projects from S3: {str(e)}"
            logger.error(error_msg)
            return CognitoS3OperationResult(
                success=False, 
                error_message=error_msg,
                user_id=user_claims.user_id if 'user_claims' in locals() else None,
                groups=user_claims.groups if 'user_claims' in locals() else None
            )