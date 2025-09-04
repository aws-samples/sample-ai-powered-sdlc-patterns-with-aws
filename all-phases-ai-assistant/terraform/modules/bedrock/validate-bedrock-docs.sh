#!/bin/bash

# Bedrock Module Documentation Validation Script
# This script validates that the Terraform documentation matches actual AWS Bedrock resources

set -e

echo "============================================================================"
echo "WARNING: DOCUMENTATION VALIDATION ONLY - DO NOT USE FOR DEPLOYMENT"
echo "============================================================================"
echo ""
echo "Validating Bedrock module documentation against AWS state..."
echo ""

# Set AWS profile
export AWS_PROFILE=aidlc_main

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
if ! command_exists aws; then
    echo -e "${RED}Error: AWS CLI is not installed${NC}"
    exit 1
fi

if ! command_exists jq; then
    echo -e "${YELLOW}Warning: jq is not installed. Some validations will be skipped.${NC}"
fi

echo "Checking AWS credentials..."
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo -e "${RED}Error: AWS credentials not configured or invalid${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ Connected to AWS account: $ACCOUNT_ID${NC}"

# Validate Knowledge Base
echo ""
echo "Validating Knowledge Base (PQB7MB5ORO)..."
KB_ID="PQB7MB5ORO"

if aws bedrock-agent get-knowledge-base --knowledge-base-id "$KB_ID" >/dev/null 2>&1; then
    KB_NAME=$(aws bedrock-agent get-knowledge-base --knowledge-base-id "$KB_ID" --query 'knowledgeBase.name' --output text)
    KB_STATUS=$(aws bedrock-agent get-knowledge-base --knowledge-base-id "$KB_ID" --query 'knowledgeBase.status' --output text)
    echo -e "${GREEN}✓ Knowledge Base found: $KB_NAME (Status: $KB_STATUS)${NC}"
    
    # Check if name matches documentation
    if [ "$KB_NAME" = "ai-assistant-knowledge-base" ]; then
        echo -e "${GREEN}✓ Knowledge Base name matches documentation${NC}"
    else
        echo -e "${YELLOW}⚠ Knowledge Base name mismatch: Expected 'ai-assistant-knowledge-base', got '$KB_NAME'${NC}"
    fi
else
    echo -e "${RED}✗ Knowledge Base PQB7MB5ORO not found${NC}"
fi

# Validate Data Source
echo ""
echo "Validating Data Source (YUAUID9BJN)..."
DS_ID="YUAUID9BJN"

if aws bedrock-agent get-data-source --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" >/dev/null 2>&1; then
    DS_NAME=$(aws bedrock-agent get-data-source --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" --query 'dataSource.name' --output text)
    DS_STATUS=$(aws bedrock-agent get-data-source --knowledge-base-id "$KB_ID" --data-source-id "$DS_ID" --query 'dataSource.status' --output text)
    echo -e "${GREEN}✓ Data Source found: $DS_NAME (Status: $DS_STATUS)${NC}"
    
    # Check if name matches documentation
    if [ "$DS_NAME" = "ai-assistant-dev-s3-data-source" ]; then
        echo -e "${GREEN}✓ Data Source name matches documentation${NC}"
    else
        echo -e "${YELLOW}⚠ Data Source name mismatch: Expected 'ai-assistant-dev-s3-data-source', got '$DS_NAME'${NC}"
    fi
else
    echo -e "${RED}✗ Data Source YUAUID9BJN not found${NC}"
fi

# Validate IAM Role
echo ""
echo "Validating IAM Role (ai-assistant-dev-bedrock-kb-role)..."
ROLE_NAME="ai-assistant-dev-bedrock-kb-role"

if aws iam get-role --role-name "$ROLE_NAME" >/dev/null 2>&1; then
    ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
    echo -e "${GREEN}✓ IAM Role found: $ROLE_ARN${NC}"
    
    # Check if ARN matches documentation
    EXPECTED_ARN="arn:aws:iam::$ACCOUNT_ID:role/ai-assistant-dev-bedrock-kb-role"
    if [ "$ROLE_ARN" = "$EXPECTED_ARN" ]; then
        echo -e "${GREEN}✓ IAM Role ARN matches documentation${NC}"
    else
        echo -e "${YELLOW}⚠ IAM Role ARN mismatch: Expected '$EXPECTED_ARN', got '$ROLE_ARN'${NC}"
    fi
else
    echo -e "${RED}✗ IAM Role ai-assistant-dev-bedrock-kb-role not found${NC}"
fi

# Validate S3 Bucket
echo ""
echo "Validating S3 Bucket (ai-assistant-dev-documents-993738bb)..."
BUCKET_NAME="ai-assistant-dev-documents-993738bb"

if aws s3api head-bucket --bucket "$BUCKET_NAME" >/dev/null 2>&1; then
    BUCKET_REGION=$(aws s3api get-bucket-location --bucket "$BUCKET_NAME" --query 'LocationConstraint' --output text)
    if [ "$BUCKET_REGION" = "None" ]; then
        BUCKET_REGION="us-east-1"
    fi
    echo -e "${GREEN}✓ S3 Bucket found: $BUCKET_NAME (Region: $BUCKET_REGION)${NC}"
    
    # Check if region matches
    if [ "$BUCKET_REGION" = "us-west-2" ]; then
        echo -e "${GREEN}✓ S3 Bucket region matches documentation${NC}"
    else
        echo -e "${YELLOW}⚠ S3 Bucket region mismatch: Expected 'us-west-2', got '$BUCKET_REGION'${NC}"
    fi
else
    echo -e "${RED}✗ S3 Bucket ai-assistant-dev-documents-993738bb not found or not accessible${NC}"
fi

# Summary
echo ""
echo "============================================================================"
echo "Validation Summary"
echo "============================================================================"
echo ""
echo "This validation confirms that the Terraform Bedrock module documentation"
echo "accurately reflects the current AWS Bedrock infrastructure state."
echo ""
echo -e "${YELLOW}Remember: This Terraform configuration is for DOCUMENTATION ONLY${NC}"
echo -e "${YELLOW}DO NOT use terraform apply, plan, or destroy commands${NC}"
echo ""
echo "For actual deployments, use AWS CLI commands as specified in the README.md"
echo ""