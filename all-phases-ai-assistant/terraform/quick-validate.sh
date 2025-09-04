#!/bin/bash

# ============================================================================
# Quick Terraform Documentation Validation
# ============================================================================
# 
# This script performs a quick validation of the most critical resources
# to verify that the main validation script logic works correctly.
# ============================================================================

set -euo pipefail

AWS_PROFILE="aidlc_main"
AWS_REGION="us-west-2"
ACCOUNT_ID="254539707041"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_CHECKS++))
}

increment_check() {
    ((TOTAL_CHECKS++))
}

echo "============================================================================"
echo "                    Quick Terraform Documentation Validation"
echo "============================================================================"
echo ""

# Check AWS CLI authentication
log_info "Checking AWS CLI authentication..."
increment_check
if aws --profile "$AWS_PROFILE" sts get-caller-identity --query 'Account' --output text | grep -q "$ACCOUNT_ID"; then
    log_success "AWS CLI authentication verified"
else
    log_error "AWS CLI authentication failed"
fi

# Check critical Lambda function
log_info "Checking critical Lambda function..."
increment_check
if aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-chat-endpoints" &> /dev/null; then
    runtime=$(aws --profile "$AWS_PROFILE" lambda get-function --function-name "ai-assistant-chat-endpoints" --query 'Configuration.Runtime' --output text)
    log_success "Lambda ai-assistant-chat-endpoints exists (runtime: $runtime)"
else
    log_error "Lambda ai-assistant-chat-endpoints not found"
fi

# Check API Gateway
log_info "Checking API Gateway..."
increment_check
if aws --profile "$AWS_PROFILE" apigateway get-rest-api --rest-api-id "jpt8wzkowd" &> /dev/null; then
    api_name=$(aws --profile "$AWS_PROFILE" apigateway get-rest-api --rest-api-id "jpt8wzkowd" --query 'name' --output text)
    log_success "API Gateway jpt8wzkowd exists (name: $api_name)"
else
    log_error "API Gateway jpt8wzkowd not found"
fi

# Check Cognito User Pool
log_info "Checking Cognito User Pool..."
increment_check
if aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool --user-pool-id "us-west-2_FLJTm8Xt8" &> /dev/null; then
    pool_name=$(aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool --user-pool-id "us-west-2_FLJTm8Xt8" --query 'UserPool.Name' --output text)
    log_success "Cognito User Pool us-west-2_FLJTm8Xt8 exists (name: $pool_name)"
else
    log_error "Cognito User Pool us-west-2_FLJTm8Xt8 not found"
fi

# Check S3 documents bucket
log_info "Checking S3 documents bucket..."
increment_check
if aws --profile "$AWS_PROFILE" s3api head-bucket --bucket "ai-assistant-dev-documents-993738bb" &> /dev/null; then
    log_success "S3 bucket ai-assistant-dev-documents-993738bb exists"
else
    log_error "S3 bucket ai-assistant-dev-documents-993738bb not found"
fi

# Check DynamoDB table
log_info "Checking DynamoDB table..."
increment_check
if aws --profile "$AWS_PROFILE" dynamodb describe-table --table-name "ai-assistant-dev-documents" &> /dev/null; then
    table_status=$(aws --profile "$AWS_PROFILE" dynamodb describe-table --table-name "ai-assistant-dev-documents" --query 'Table.TableStatus' --output text)
    log_success "DynamoDB table ai-assistant-dev-documents exists (status: $table_status)"
else
    log_error "DynamoDB table ai-assistant-dev-documents not found"
fi

# Check CloudFront distribution
log_info "Checking CloudFront distribution..."
increment_check
if aws --profile "$AWS_PROFILE" cloudfront get-distribution --id "EL8L41G6CQJCD" &> /dev/null; then
    domain=$(aws --profile "$AWS_PROFILE" cloudfront get-distribution --id "EL8L41G6CQJCD" --query 'Distribution.DomainName' --output text)
    log_success "CloudFront distribution EL8L41G6CQJCD exists (domain: $domain)"
else
    log_error "CloudFront distribution EL8L41G6CQJCD not found"
fi

# Check Bedrock Knowledge Base
log_info "Checking Bedrock Knowledge Base..."
increment_check
if aws --profile "$AWS_PROFILE" bedrock-agent get-knowledge-base --knowledge-base-id "PQB7MB5ORO" &> /dev/null; then
    kb_name=$(aws --profile "$AWS_PROFILE" bedrock-agent get-knowledge-base --knowledge-base-id "PQB7MB5ORO" --query 'knowledgeBase.name' --output text)
    log_success "Bedrock Knowledge Base PQB7MB5ORO exists (name: $kb_name)"
else
    log_error "Bedrock Knowledge Base PQB7MB5ORO not found"
fi

echo ""
echo "============================================================================"
echo "                            QUICK VALIDATION SUMMARY"
echo "============================================================================"
echo ""
echo "Total Checks: $TOTAL_CHECKS"
echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
echo ""

if [[ $FAILED_CHECKS -eq 0 ]]; then
    echo -e "${GREEN}✓ Quick validation passed! Core infrastructure matches Terraform documentation.${NC}"
    echo ""
    echo "You can now run the full validation script:"
    echo "  ./validate-terraform-docs.sh"
    exit 0
else
    echo -e "${RED}✗ Quick validation found $FAILED_CHECKS issues.${NC}"
    echo ""
    echo "Please check the AWS resources and update Terraform documentation as needed."
    exit 1
fi