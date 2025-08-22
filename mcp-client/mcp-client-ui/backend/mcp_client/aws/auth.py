"""
AWS IAM authentication for the MCP Client.
"""

import logging
from typing import Dict, Optional

import boto3
from botocore.credentials import Credentials
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from botocore.session import Session

from mcp_client.core.models import ErrorCode, MCPError

logger = logging.getLogger(__name__)


class AWSCredentialProvider:
    """Provides AWS credentials using various authentication methods."""

    def __init__(
        self,
        region: str,
        profile: Optional[str] = None,
        role_arn: Optional[str] = None,
        session_name: Optional[str] = None,
        external_id: Optional[str] = None,
    ):
        """
        Initialize the AWS credential provider.

        Args:
            region: AWS region to use
            profile: AWS profile to use (optional)
            role_arn: IAM role ARN to assume (optional)
            session_name: Session name for role assumption (optional)
            external_id: External ID for role assumption (optional)
        """
        self.region = region
        self.profile = profile
        self.role_arn = role_arn
        self.session_name = session_name or "mcp-client-session"
        self.external_id = external_id
        self._session: Optional[Session] = None
        self._credentials: Optional[Credentials] = None

    def get_session(self) -> Session:
        """
        Get a boto3 session with appropriate credentials.

        Returns:
            Session: Configured boto3 session

        Raises:
            MCPError: If authentication fails
        """
        if self._session is None:
            try:
                if self.profile:
                    # Use specific profile
                    self._session = boto3.Session(
                        profile_name=self.profile, region_name=self.region
                    )
                    logger.info(f"Using AWS profile: {self.profile}")
                else:
                    # Use default credentials
                    self._session = boto3.Session(region_name=self.region)
                    logger.info("Using default AWS credentials")

                # Test credentials by making a simple call
                sts_client = self._session.client("sts")
                identity = sts_client.get_caller_identity()
                logger.info(f"Authenticated as: {identity.get('Arn', 'Unknown')}")
                logger.debug(f"AWS session initialized with region: {self.region}, profile: {self.profile}")

            except NoCredentialsError as e:
                raise MCPError(
                    error_code=ErrorCode.AUTHENTICATION_ERROR,
                    message="No AWS credentials found",
                    details={
                        "error": str(e),
                        "profile": self.profile,
                        "region": self.region,
                    },
                ) from e
            except (ClientError, BotoCoreError) as e:
                raise MCPError(
                    error_code=ErrorCode.AUTHENTICATION_ERROR,
                    message=f"AWS authentication failed: {str(e)}",
                    details={
                        "error": str(e),
                        "profile": self.profile,
                        "region": self.region,
                    },
                ) from e

        return self._session

    def assume_role(self) -> Session:
        """
        Assume an IAM role and return a session with temporary credentials.

        Returns:
            Session: Session with assumed role credentials

        Raises:
            MCPError: If role assumption fails
        """
        if not self.role_arn:
            raise MCPError(
                error_code=ErrorCode.AUTHENTICATION_ERROR,
                message="Role ARN is required for role assumption",
                details={"role_arn": self.role_arn},
            )

        try:
            # Get base session
            base_session = self.get_session()
            sts_client = base_session.client("sts")

            # Prepare assume role parameters
            assume_role_params = {
                "RoleArn": self.role_arn,
                "RoleSessionName": self.session_name,
            }

            if self.external_id:
                assume_role_params["ExternalId"] = self.external_id
                logger.info(f"Using external ID for role assumption: {self.external_id}")

            # Assume the role
            response = sts_client.assume_role(**assume_role_params)
            credentials = response["Credentials"]

            # Create new session with temporary credentials
            assumed_session = boto3.Session(
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
                region_name=self.region,
            )

            logger.info(f"Successfully assumed role: {self.role_arn}")
            return assumed_session

        except (ClientError, BotoCoreError) as e:
            raise MCPError(
                error_code=ErrorCode.AUTHENTICATION_ERROR,
                message=f"Failed to assume role {self.role_arn}: {str(e)}",
                details={
                    "error": str(e),
                    "role_arn": self.role_arn,
                    "session_name": self.session_name,
                    "external_id": self.external_id,
                },
            ) from e

    def get_credentials(self) -> Dict[str, str]:
        """
        Get AWS credentials as a dictionary.

        Returns:
            Dict[str, str]: Dictionary containing AWS credentials

        Raises:
            MCPError: If credentials cannot be obtained
        """
        try:
            session = self.assume_role() if self.role_arn else self.get_session()
            credentials = session.get_credentials()

            if not credentials:
                raise MCPError(
                    error_code=ErrorCode.AUTHENTICATION_ERROR,
                    message="Unable to obtain AWS credentials",
                    details={"profile": self.profile, "region": self.region},
                )

            return {
                "aws_access_key_id": credentials.access_key,
                "aws_secret_access_key": credentials.secret_key,
                "aws_session_token": credentials.token,
                "region": self.region,
            }

        except MCPError:
            raise
        except Exception as e:
            raise MCPError(
                error_code=ErrorCode.AUTHENTICATION_ERROR,
                message=f"Failed to get AWS credentials: {str(e)}",
                details={"error": str(e)},
            ) from e

    def refresh_credentials(self) -> None:
        """
        Refresh the cached credentials.
        """
        self._session = None
        self._credentials = None
        logger.info("AWS credentials cache cleared")


class AWSAuthenticator:
    """Handles AWS authentication for MCP client requests."""

    def __init__(self, credential_provider: AWSCredentialProvider):
        """
        Initialize the AWS authenticator.

        Args:
            credential_provider: Provider for AWS credentials
        """
        self.credential_provider = credential_provider
        self._jwt_token = None  # Store JWT token directly

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for HTTP requests.

        Returns:
            Dict[str, str]: Authentication headers

        Raises:
            MCPError: If authentication fails
        """
        try:
            credentials = self.credential_provider.get_credentials()

            # For now, we'll include basic AWS credential information in headers
            # In a real implementation, you might want to use AWS Signature Version 4
            headers = {
                "X-AWS-Region": credentials["region"],
                "X-AWS-Access-Key-Id": credentials["aws_access_key_id"][:8] + "...",  # Truncated for security
            }

            if credentials.get("aws_session_token"):
                # Use actual session token for authentication
                headers["X-AWS-Session-Token"] = credentials["aws_session_token"]

            return headers

        except Exception as e:
            raise MCPError(
                error_code=ErrorCode.AUTHENTICATION_ERROR,
                message=f"Failed to generate auth headers: {str(e)}",
                details={"error": str(e)},
            ) from e

    def sign_request(self, method: str, url: str, headers: Dict[str, str], body: str = "", service: str = "execute-api", server_id: str = None) -> Dict[str, str]:
        """
        Sign an HTTP request using AWS Signature Version 4 with Cognito JWT.
        
        Simplified approach: Use client's AWS credentials + include JWT token
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            body: Request body
            service: AWS service name (default: execute-api)
            server_id: Server identifier for JWT detection

        Returns:
            Dict[str, str]: Updated headers with signature

        Raises:
            MCPError: If signing fails
        """
        logger.info(f"Starting simplified SigV4 signing for {method} request to {url}")
        try:
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            import os
            
            # Get credentials using the credential provider
            session = self.credential_provider.get_session()
            credentials = session.get_credentials()

            if not credentials:
                raise MCPError(
                    error_code=ErrorCode.AUTHENTICATION_ERROR,
                    message="No credentials available for request signing",
                    details={
                        "credential_provider_region": self.credential_provider.region,
                        "credential_provider_profile": self.credential_provider.profile
                    }
                )

            # Ensure headers is a mutable dict
            headers = dict(headers) if headers else {}
            
            # Get JWT token for Amazon Q Business
            jwt_token = self._jwt_token or os.environ.get('COGNITO_JWT_TOKEN')
            is_amazon_q = server_id and 'amazon-q-business' in server_id
            
            logger.info(f"Amazon Q Business detected: {is_amazon_q}")
            logger.info(f"JWT token available: {bool(jwt_token)}")
            
            # Add Cognito JWT token for Amazon Q Business
            if is_amazon_q and jwt_token:
                headers['X-Cognito-JWT'] = jwt_token
                logger.info(f"Added Cognito JWT token to X-Cognito-JWT header")
            elif is_amazon_q:
                logger.info("No JWT token provided for Amazon Q Business request (this is expected if not using Q Business features)")
            
            # Create AWS request with headers (including JWT if applicable)
            request = AWSRequest(
                method=method, 
                url=url, 
                data=body, 
                headers=headers
            )
            
            # Sign with SigV4 using client's AWS credentials
            signer = SigV4Auth(credentials, service, self.credential_provider.region)
            signer.add_auth(request)
            
            # Ensure JWT token is preserved after signing (if it was added)
            if is_amazon_q and jwt_token:
                request.headers['X-Cognito-JWT'] = jwt_token
                logger.info("JWT token preserved after SigV4 signing")
            
            logger.info(f"Successfully signed request with {len(request.headers)} headers")
            logger.info(f"Final headers: {list(request.headers.keys())}")
            
            # Return the signed headers
            return dict(request.headers)

        except MCPError:
            raise
        except Exception as e:
            logger.error(f"Request signing failed: {e}")
            raise MCPError(
                error_code=ErrorCode.AUTHENTICATION_ERROR,
                message=f"Failed to sign request: {str(e)}",
                details={
                    "method": method,
                    "url": url,
                    "service": service,
                    "region": self.credential_provider.region,
                    "error": str(e)
                },
            ) from e

    def validate_permissions(self, required_actions: Optional[list] = None) -> bool:
        """
        Validate that the current credentials have the required permissions.

        Args:
            required_actions: List of required IAM actions (optional)

        Returns:
            bool: True if permissions are valid

        Raises:
            MCPError: If validation fails
        """
        try:
            session = self.credential_provider.get_session()
            sts_client = session.client("sts")

            # Test basic permissions by calling get_caller_identity
            identity = sts_client.get_caller_identity()
            logger.info(f"Validated permissions for: {identity.get('Arn', 'Unknown')}")

            # If specific actions are required, we could use IAM policy simulation here
            # For now, we'll just validate that we can make basic AWS calls
            if required_actions:
                logger.info(f"Required actions: {required_actions}")
                # In a full implementation, you would use sts.simulate_principal_policy
                # to check specific permissions

            return True

        except (ClientError, BotoCoreError) as e:
            raise MCPError(
                error_code=ErrorCode.AUTHORIZATION_ERROR,
                message=f"Permission validation failed: {str(e)}",
                details={
                    "error": str(e),
                    "required_actions": required_actions,
                },
            ) from e