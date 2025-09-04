#!/bin/bash

# ============================================================================
# Terraform vs AWS State Comparison Script
# ============================================================================
# 
# This script compares specific values documented in Terraform files
# with actual AWS resource configurations to identify discrepancies.
# ============================================================================

set -euo pipefail

AWS_PROFILE="aidlc_main"
AWS_REGION="us-west-2"
ACCOUNT_ID="254539707041"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TOTAL_COMPARISONS=0
MATCHES=0
MISMATCHES=0

declare -a COMPARISON_RESULTS=()

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_match() {
    echo -e "${GREEN}[MATCH]${NC} $1"
    ((MATCHES++))
    COMPARISON_RESULTS+=("✓ $1")
}

log_mismatch() {
    echo -e "${RED}[MISMATCH]${NC} $1"
    ((MISMATCHES++))
    COMPARISON_RESULTS+=("✗ $1")
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

increment_comparison() {
    ((TOTAL_COMPARISONS++))
}

# Function to compare values
compare_values() {
    local description="$1"
    local terraform_value="$2"
    local aws_value="$3"
    
    increment_comparison
    
    if [[ "$terraform_value" == "$aws_value" ]]; then
        log_match "$description: $terraform_value"
    else
        log_mismatch "$description: Terraform='$terraform_value' AWS='$aws_value'"
    fi
}

echo "============================================================================"
echo "                 Terraform vs AWS State Comparison"
echo "============================================================================"
echo ""

log_info "Starting detailed comparison of Terraform documentation vs AWS state..."
echo ""

# Lambda Functions Comparison
log_info "Comparing Lambda functions..."

# Chat endpoints function
if aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-chat-endpoints" &> /dev/null; then
    aws_runtime=$(aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-chat-endpoints" --query 'Configuration.Runtime' --output text)
    compare_values "Lambda ai-assistant-chat-endpoints runtime" "nodejs20.x" "$aws_runtime"
else
    log_mismatch "Lambda ai-assistant-chat-endpoints: Documented but not found in AWS"
    increment_comparison
fi

# Document management function
if aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-dev-document-management" &> /dev/null; then
    aws_runtime=$(aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-dev-document-management" --query 'Configuration.Runtime' --output text)
    compare_values "Lambda ai-assistant-dev-document-management runtime" "nodejs20.x" "$aws_runtime"
else
    log_mismatch "Lambda ai-assistant-dev-document-management: Documented but not found in AWS"
    increment_comparison
fi

echo ""

# API Gateway Comparison
log_info "Comparing API Gateway..."

if aws --profile "$AWS_PROFILE" apigateway get-rest-api --rest-api-id "jpt8wzkowd" &> /dev/null; then
    aws_api_name=$(aws --profile "$AWS_PROFILE" apigateway get-rest-api --rest-api-id "jpt8wzkowd" --query 'name' --output text)
    compare_values "API Gateway jpt8wzkowd name" "ai-assistant-api" "$aws_api_name"
    
    # Construct expected URL
    terraform_url="https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev"
    aws_url="https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev"
    compare_values "API Gateway URL" "$terraform_url" "$aws_url"
else
    log_mismatch "API Gateway jpt8wzkowd: Documented but not found in AWS"
    increment_comparison
fi

echo ""

# Cognito Comparison
log_info "Comparing Cognito User Pool..."

if aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool --user-pool-id "us-west-2_FLJTm8Xt8" &> /dev/null; then
    aws_pool_name=$(aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool --user-pool-id "us-west-2_FLJTm8Xt8" --query 'UserPool.Name' --output text)
    compare_values "Cognito User Pool us-west-2_FLJTm8Xt8 name" "ai-assistant-user-pool" "$aws_pool_name"
else
    log_mismatch "Cognito User Pool us-west-2_FLJTm8Xt8: Documented but not found in AWS"
    increment_comparison
fi

echo ""

# S3 Buckets Comparison
log_info "Comparing S3 buckets..."

# Documents bucket
if aws --profile "$AWS_PROFILE" s3api head-bucket --bucket "ai-assistant-dev-documents-993738bb" &> /dev/null; then
    aws_bucket_region=$(aws --profile "$AWS_PROFILE" s3api get-bucket-location --bucket "ai-assistant-dev-documents-993738bb" --query 'LocationConstraint' --output text)
    if [[ "$aws_bucket_region" == "null" ]]; then
        aws_bucket_region="us-east-1"
    fi
    compare_values "S3 documents bucket region" "us-west-2" "$aws_bucket_region"
else
    log_mismatch "S3 bucket ai-assistant-dev-documents-993738bb: Documented but not found in AWS"
    increment_comparison
fi

# Frontend bucket
if aws --profile "$AWS_PROFILE" s3api head-bucket --bucket "ai-assistant-dev-frontend-e5e9acfe" &> /dev/null; then
    aws_bucket_region=$(aws --profile "$AWS_PROFILE" s3api get-bucket-location --bucket "ai-assistant-dev-frontend-e5e9acfe" --query 'LocationConstraint' --output text)
    if [[ "$aws_bucket_region" == "null" ]]; then
        aws_bucket_region="us-east-1"
    fi
    compare_values "S3 frontend bucket region" "us-west-2" "$aws_bucket_region"
else
    log_mismatch "S3 bucket ai-assistant-dev-frontend-e5e9acfe: Documented but not found in AWS"
    increment_comparison
fi

echo ""

# DynamoDB Comparison
log_info "Comparing DynamoDB table..."

if aws --profile "$AWS_PROFILE" dynamodb describe-table --table-name "ai-assistant-dev-documents" &> /dev/null; then
    aws_table_status=$(aws --profile "$AWS_PROFILE" dynamodb describe-table --table-name "ai-assistant-dev-documents" --query 'Table.TableStatus' --output text)
    compare_values "DynamoDB table ai-assistant-dev-documents status" "ACTIVE" "$aws_table_status"
else
    log_mismatch "DynamoDB table ai-assistant-dev-documents: Documented but not found in AWS"
    increment_comparison
fi

echo ""

# CloudFront Comparison
log_info "Comparing CloudFront distribution..."

if aws --profile "$AWS_PROFILE" cloudfront get-distribution --id "EL8L41G6CQJCD" &> /dev/null; then
    aws_cf_domain=$(aws --profile "$AWS_PROFILE" cloudfront get-distribution --id "EL8L41G6CQJCD" --query 'Distribution.DomainName' --output text)
    compare_values "CloudFront distribution EL8L41G6CQJCD domain" "dq9tlzfsf1veq.cloudfront.net" "$aws_cf_domain"
else
    log_mismatch "CloudFront distribution EL8L41G6CQJCD: Documented but not found in AWS"
    increment_comparison
fi

echo ""

# Bedrock Knowledge Base Comparison
log_info "Comparing Bedrock Knowledge Base..."

if aws --profile "$AWS_PROFILE" bedrock-agent get-knowledge-base --knowledge-base-id "PQB7MB5ORO" &> /dev/null; then
    aws_kb_name=$(aws --profile "$AWS_PROFILE" bedrock-agent get-knowledge-base --knowledge-base-id "PQB7MB5ORO" --query 'knowledgeBase.name' --output text)
    compare_values "Bedrock Knowledge Base PQB7MB5ORO name" "ai-assistant-knowledge-base" "$aws_kb_name"
else
    log_mismatch "Bedrock Knowledge Base PQB7MB5ORO: Documented but not found in AWS"
    increment_comparison
fi

# Data Source Comparison
if aws --profile "$AWS_PROFILE" bedrock-agent get-data-source --knowledge-base-id "PQB7MB5ORO" --data-source-id "YUAUID9BJN" &> /dev/null; then
    aws_ds_name=$(aws --profile "$AWS_PROFILE" bedrock-agent get-data-source --knowledge-base-id "PQB7MB5ORO" --data-source-id "YUAUID9BJN" --query 'dataSource.name' --output text)
    compare_values "Bedrock Data Source YUAUID9BJN name" "ai-assistant-dev-s3-data-source" "$aws_ds_name"
else
    log_mismatch "Bedrock Data Source YUAUID9BJN: Documented but not found in AWS"
    increment_comparison
fi

echo ""
echo "============================================================================"
echo "                           COMPARISON SUMMARY"
echo "============================================================================"
echo ""
echo "Total Comparisons: $TOTAL_COMPARISONS"
echo -e "Matches: ${GREEN}$MATCHES${NC}"
echo -e "Mismatches: ${RED}$MISMATCHES${NC}"
echo ""

if [[ $MISMATCHES -eq 0 ]]; then
    echo -e "${GREEN}✓ All Terraform documentation matches AWS state!${NC}"
    echo "The Terraform files accurately reflect the current infrastructure."
else
    echo -e "${RED}✗ Found $MISMATCHES discrepancies between Terraform documentation and AWS state${NC}"
    echo ""
    echo "Detailed Results:"
    for result in "${COMPARISON_RESULTS[@]}"; do
        echo "  $result"
    done
fi

echo ""
echo "Comparison completed at $(date)"
echo "============================================================================"

# Exit with appropriate code
if [[ $MISMATCHES -eq 0 ]]; then
    exit 0
else
    exit 1
fi