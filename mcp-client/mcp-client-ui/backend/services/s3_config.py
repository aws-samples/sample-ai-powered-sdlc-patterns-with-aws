"""S3 configuration and connection validation service."""

import boto3
import logging
from typing import Dict, Optional, Tuple
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from config.settings import settings

logger = logging.getLogger(__name__)


class S3ConfigurationService:
    """Service for managing S3 configuration and connection validation."""
    
    def __init__(self):
        """Initialize S3 configuration service."""
        self._s3_client = None
        self._connection_validated = False
    
    def get_aws_credentials(self) -> Dict[str, Optional[str]]:
        """
        Get AWS credentials configuration.
        
        Returns:
            Dict containing AWS credential configuration
        """
        return {
            "aws_access_key_id": settings.S3_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
            "region_name": settings.S3_REGION
        }
    
    def get_bucket_configuration(self) -> Dict[str, str]:
        """
        Get S3 bucket configuration.
        
        Returns:
            Dict containing S3 bucket configuration
            
        Raises:
            ValueError: If required S3 configuration is missing
        """
        if not settings.S3_BUCKET_NAME:
            raise ValueError("S3_BUCKET_NAME environment variable is required but not set")
            
        return {
            "bucket_name": settings.S3_BUCKET_NAME,
            "region": settings.S3_REGION,
            "endpoint_url": settings.S3_ENDPOINT_URL,
            "use_ssl": settings.S3_USE_SSL,
            "verify_ssl": settings.S3_VERIFY_SSL
        }
    
    def create_s3_client(self) -> boto3.client:
        """
        Create and configure S3 client.
        
        Returns:
            Configured boto3 S3 client
            
        Raises:
            NoCredentialsError: If AWS credentials are not properly configured
            ClientError: If there's an error creating the client
        """
        try:
            # Get credentials
            credentials = self.get_aws_credentials()
            
            # Create client configuration
            client_config = {
                "service_name": "s3",
                "region_name": credentials["region_name"]
            }
            
            # Add credentials if provided
            if credentials["aws_access_key_id"] and credentials["aws_secret_access_key"]:
                client_config.update({
                    "aws_access_key_id": credentials["aws_access_key_id"],
                    "aws_secret_access_key": credentials["aws_secret_access_key"]
                })
            
            # Add endpoint URL if specified (for LocalStack or custom endpoints)
            if settings.S3_ENDPOINT_URL:
                client_config["endpoint_url"] = settings.S3_ENDPOINT_URL
            
            # Add SSL configuration
            client_config["use_ssl"] = settings.S3_USE_SSL
            client_config["verify"] = settings.S3_VERIFY_SSL
            
            self._s3_client = boto3.client(**client_config)
            logger.info("S3 client created successfully")
            return self._s3_client
            
        except NoCredentialsError as e:
            logger.error("AWS credentials not found or invalid")
            raise
        except Exception as e:
            logger.error(f"Error creating S3 client: {str(e)}")
            raise ClientError(
                error_response={"Error": {"Code": "ClientCreationError", "Message": str(e)}},
                operation_name="CreateClient"
            )
    
    def create_bucket_if_not_exists(self) -> Tuple[bool, Optional[str]]:
        """
        Create S3 bucket if it doesn't exist.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not self._s3_client:
                self._s3_client = self.create_s3_client()
            
            bucket_name = settings.S3_BUCKET_NAME
            region = settings.S3_REGION
            
            # Check if bucket already exists
            try:
                self._s3_client.head_bucket(Bucket=bucket_name)
                logger.info(f"Bucket '{bucket_name}' already exists")
                return True, None
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code != "404":
                    return False, f"Error checking bucket existence: {error_code}"
            
            # Create the bucket
            try:
                if region == "us-east-1":
                    # us-east-1 doesn't need LocationConstraint
                    self._s3_client.create_bucket(Bucket=bucket_name)
                else:
                    self._s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                
                logger.info(f"Successfully created bucket '{bucket_name}' in region '{region}'")
                return True, None
                
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "BucketAlreadyExists":
                    logger.info(f"Bucket '{bucket_name}' already exists")
                    return True, None
                elif error_code == "BucketAlreadyOwnedByYou":
                    logger.info(f"Bucket '{bucket_name}' already owned by you")
                    return True, None
                else:
                    return False, f"Error creating bucket: {error_code}"
                    
        except Exception as e:
            error_msg = f"Unexpected error creating bucket: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def validate_s3_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Validate S3 connection and bucket access.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Create S3 client if not exists
            if not self._s3_client:
                self._s3_client = self.create_s3_client()
            
            # Test connection by listing buckets
            response = self._s3_client.list_buckets()
            logger.info("Successfully connected to S3")
            
            # Check if our specific bucket exists
            bucket_name = settings.S3_BUCKET_NAME
            bucket_exists = any(bucket["Name"] == bucket_name for bucket in response.get("Buckets", []))
            
            if not bucket_exists:
                logger.warning(f"Bucket '{bucket_name}' does not exist, attempting to create it...")
                # Try to create the bucket
                created, create_error = self.create_bucket_if_not_exists()
                if not created:
                    return False, f"Bucket '{bucket_name}' does not exist and could not be created: {create_error}"
                logger.info(f"Successfully created bucket '{bucket_name}'")
            
            # Test bucket access by attempting to list objects
            try:
                self._s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                logger.info(f"Successfully validated access to bucket '{bucket_name}'")
                self._connection_validated = True
                return True, None
                
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "NoSuchBucket":
                    return False, f"Bucket '{bucket_name}' does not exist"
                elif error_code == "AccessDenied":
                    return False, f"Access denied to bucket '{bucket_name}'"
                else:
                    return False, f"Error accessing bucket '{bucket_name}': {error_code}"
            
        except NoCredentialsError:
            error_msg = "AWS credentials not configured"
            logger.error(error_msg)
            return False, error_msg
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = f"AWS client error: {error_code}"
            logger.error(error_msg)
            return False, error_msg
            
        except BotoCoreError as e:
            error_msg = f"AWS connection error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error validating S3 connection: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_s3_client(self) -> Optional[boto3.client]:
        """
        Get the configured S3 client.
        
        Returns:
            boto3 S3 client if connection is validated, None otherwise
        """
        if not self._connection_validated:
            is_valid, error = self.validate_s3_connection()
            if not is_valid:
                logger.error(f"S3 connection validation failed: {error}")
                return None
        
        return self._s3_client
    
    def is_connection_valid(self) -> bool:
        """
        Check if S3 connection has been validated.
        
        Returns:
            True if connection is validated, False otherwise
        """
        return self._connection_validated
    
    def reset_connection(self) -> None:
        """Reset S3 connection state to force re-validation."""
        self._s3_client = None
        self._connection_validated = False
        logger.info("S3 connection state reset")


# Global instance
s3_config_service = S3ConfigurationService()