#!/bin/bash

# Quick test of validation script functionality
set -euo pipefail

AWS_PROFILE="aidlc_main"
AWS_REGION="us-west-2"

echo "Testing AWS CLI connectivity..."

# Test AWS CLI authentication
if aws --profile "$AWS_PROFILE" sts get-caller-identity &> /dev/null; then
    echo "✓ AWS CLI authentication successful"
    
    # Test a few key resources
    echo "Testing key resources..."
    
    # Test Lambda function
    if aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-chat-endpoints" &> /dev/null; then
        echo "✓ Lambda function ai-assistant-chat-endpoints exists"
    else
        echo "✗ Lambda function ai-assistant-chat-endpoints not found"
    fi
    
    # Test API Gateway
    if aws --profile "$AWS_PROFILE" apigateway get-rest-api --rest-api-id "jpt8wzkowd" &> /dev/null; then
        echo "✓ API Gateway jpt8wzkowd exists"
    else
        echo "✗ API Gateway jpt8wzkowd not found"
    fi
    
    # Test S3 bucket
    if aws --profile "$AWS_PROFILE" s3api head-bucket --bucket "ai-assistant-dev-documents-993738bb" &> /dev/null; then
        echo "✓ S3 bucket ai-assistant-dev-documents-993738bb exists"
    else
        echo "✗ S3 bucket ai-assistant-dev-documents-993738bb not found"
    fi
    
    echo "Basic validation test completed successfully"
else
    echo "✗ AWS CLI authentication failed"
    exit 1
fi