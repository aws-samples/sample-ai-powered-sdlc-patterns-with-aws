"""Utility script for testing S3 connection validation."""

import sys
import os
import logging

# Add the parent directory to the path so we can import from services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.s3_config import s3_config_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_s3_connection():
    """Test S3 connection and configuration."""
    print("Testing S3 Configuration and Connection...")
    print("=" * 50)
    
    # Display current configuration
    print("Current S3 Configuration:")
    bucket_config = s3_config_service.get_bucket_configuration()
    for key, value in bucket_config.items():
        if key == "endpoint_url" and not value:
            continue
        print(f"  {key}: {value}")
    
    print("\nAWS Credentials Configuration:")
    creds = s3_config_service.get_aws_credentials()
    print(f"  Region: {creds['region_name']}")
    print(f"  Access Key ID: {'***' if creds['aws_access_key_id'] else 'Not set'}")
    print(f"  Secret Access Key: {'***' if creds['aws_secret_access_key'] else 'Not set'}")
    
    print("\nValidating S3 Connection...")
    is_valid, error_message = s3_config_service.validate_s3_connection()
    
    if is_valid:
        print("✅ S3 connection validation successful!")
        print("✅ Bucket access confirmed")
        print("✅ Ready for project context storage!")
    else:
        print("❌ S3 connection validation failed!")
        print(f"Error: {error_message}")
        
        # Provide troubleshooting suggestions
        print("\nTroubleshooting suggestions:")
        print("1. Check AWS credentials are properly configured")
        print("2. Verify the S3 bucket exists and is accessible")
        print("3. Check AWS region configuration")
        print("4. Ensure proper IAM permissions for S3 access")
        print("5. Make sure you have permissions to create S3 buckets")
    
    return is_valid


if __name__ == "__main__":
    test_s3_connection()