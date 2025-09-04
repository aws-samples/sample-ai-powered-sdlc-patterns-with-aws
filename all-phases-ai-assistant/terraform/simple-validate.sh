#!/bin/bash

# Simple validation test
set -e

AWS_PROFILE="aidlc_main"

echo "Testing AWS CLI with profile: $AWS_PROFILE"

# Test basic AWS CLI functionality
echo "1. Testing AWS authentication..."
aws --profile "$AWS_PROFILE" sts get-caller-identity --output table

echo ""
echo "2. Testing Lambda function..."
aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-chat-endpoints" --query 'Configuration.{Name:FunctionName,Runtime:Runtime}' --output table

echo ""
echo "3. Testing API Gateway..."
aws --profile "$AWS_PROFILE" apigateway get-rest-api --rest-api-id "jpt8wzkowd" --query '{Name:name,Id:id}' --output table

echo ""
echo "4. Testing S3 bucket..."
aws --profile "$AWS_PROFILE" s3api head-bucket --bucket "ai-assistant-dev-documents-993738bb" && echo "✓ S3 bucket exists"

echo ""
echo "Simple validation completed successfully!"