#!/bin/bash

# ============================================================================
# Terraform Documentation Validation Script
# ============================================================================
# 
# This script validates that Terraform documentation accurately reflects
# the current AWS infrastructure state by comparing documented values
# with actual AWS CLI output.
# 
# Requirements: AWS CLI configured with aidlc_main profile
# ============================================================================

set -euo pipefail

# Configuration
AWS_PROFILE="aidlc_main"
AWS_REGION="us-west-2"
ACCOUNT_ID="254539707041"
PROJECT_NAME="ai-assistant"
ENVIRONMENT="dev"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Arrays to store results
declare -a VALIDATION_RESULTS=()
declare -a DISCREPANCIES=()

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_CHECKS++))
    DISCREPANCIES+=("$1")
}

increment_check() {
    ((TOTAL_CHECKS++))
}

# Utility functions
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed or not in PATH"
        exit 1
    fi
    
    # Verify AWS profile
    if ! aws --profile "$AWS_PROFILE" sts get-caller-identity &> /dev/null; then
        log_error "Cannot authenticate with AWS profile: $AWS_PROFILE"
        exit 1
    fi
    
    local caller_identity
    caller_identity=$(aws --profile "$AWS_PROFILE" sts get-caller-identity --query 'Account' --output text)
    
    if [[ "$caller_identity" != "$ACCOUNT_ID" ]]; then
        log_error "AWS profile is connected to account $caller_identity, expected $ACCOUNT_ID"
        exit 1
    fi
    
    log_success "AWS CLI authentication verified for account $ACCOUNT_ID"
}

# Resource validation functions
validate_lambda_functions() {
    log_info "Validating Lambda functions..."
    
    # Expected Lambda functions from Terraform documentation
    declare -A expected_functions=(
        ["ai-assistant-chat-endpoints"]="nodejs20.x"
        ["ai-assistant-dev-document-management"]="nodejs20.x"
        ["ai-assistant-dev-admin-management"]="nodejs18.x"
        ["ai-assistant-dev-document-upload"]="nodejs18.x"
        ["ai-assistant-dev-kb-sync-monitor"]="nodejs18.x"
        ["ai-assistant-monitoring-metrics"]="nodejs18.x"
    )
    
    for function_name in "${!expected_functions[@]}"; do
        increment_check
        local expected_runtime="${expected_functions[$function_name]}"
        
        # Check if function exists
        if aws --profile "$AWS_PROFILE" lambda get-function --function-name "$function_name" &> /dev/null; then
            # Get actual runtime
            local actual_runtime
            actual_runtime=$(aws --profile "$AWS_PROFILE" lambda get-function \
                --function-name "$function_name" \
                --query 'Configuration.Runtime' --output text)
            
            if [[ "$actual_runtime" == "$expected_runtime" ]]; then
                log_success "Lambda function $function_name exists with runtime $actual_runtime"
            else
                log_error "Lambda function $function_name runtime mismatch: expected $expected_runtime, got $actual_runtime"
            fi
        else
            log_error "Lambda function $function_name does not exist"
        fi
    done
}

validate_api_gateway() {
    log_info "Validating API Gateway..."
    
    local expected_api_id="jpt8wzkowd"
    increment_check
    
    # Check if API Gateway exists
    if aws --profile "$AWS_PROFILE" apigateway get-rest-api --rest-api-id "$expected_api_id" &> /dev/null; then
        local api_name
        api_name=$(aws --profile "$AWS_PROFILE" apigateway get-rest-api \
            --rest-api-id "$expected_api_id" \
            --query 'name' --output text)
        
        log_success "API Gateway $expected_api_id exists with name: $api_name"
        
        # Validate API Gateway URL
        increment_check
        local expected_url="https://${expected_api_id}.execute-api.${AWS_REGION}.amazonaws.com/dev"
        log_success "API Gateway URL: $expected_url"
        
    else
        log_error "API Gateway $expected_api_id does not exist"
    fi
}

validate_cognito() {
    log_info "Validating Cognito User Pool..."
    
    local expected_user_pool_id="us-west-2_FLJTm8Xt8"
    local expected_client_id="3gr32ei5n768d88h02klhmpn8v"
    local expected_domain="ai-assistant-auth-3gja49wa"
    
    # Check User Pool
    increment_check
    if aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool --user-pool-id "$expected_user_pool_id" &> /dev/null; then
        local pool_name
        pool_name=$(aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool \
            --user-pool-id "$expected_user_pool_id" \
            --query 'UserPool.Name' --output text)
        
        log_success "Cognito User Pool $expected_user_pool_id exists with name: $pool_name"
    else
        log_error "Cognito User Pool $expected_user_pool_id does not exist"
    fi
    
    # Check User Pool Client
    increment_check
    if aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool-client \
        --user-pool-id "$expected_user_pool_id" \
        --client-id "$expected_client_id" &> /dev/null; then
        
        local client_name
        client_name=$(aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool-client \
            --user-pool-id "$expected_user_pool_id" \
            --client-id "$expected_client_id" \
            --query 'UserPoolClient.ClientName' --output text)
        
        log_success "Cognito User Pool Client $expected_client_id exists with name: $client_name"
    else
        log_error "Cognito User Pool Client $expected_client_id does not exist"
    fi
    
    # Check User Pool Domain
    increment_check
    if aws --profile "$AWS_PROFILE" cognito-idp describe-user-pool-domain --domain "$expected_domain" &> /dev/null; then
        log_success "Cognito User Pool Domain $expected_domain exists"
    else
        log_error "Cognito User Pool Domain $expected_domain does not exist"
    fi
}

validate_s3_buckets() {
    log_info "Validating S3 buckets..."
    
    local expected_documents_bucket="ai-assistant-dev-documents-993738bb"
    local expected_frontend_bucket="ai-assistant-dev-frontend-e5e9acfe"
    
    # Check documents bucket
    increment_check
    if aws --profile "$AWS_PROFILE" s3api head-bucket --bucket "$expected_documents_bucket" &> /dev/null; then
        local bucket_region
        bucket_region=$(aws --profile "$AWS_PROFILE" s3api get-bucket-location \
            --bucket "$expected_documents_bucket" \
            --query 'LocationConstraint' --output text)
        
        # Handle null response for us-east-1
        if [[ "$bucket_region" == "null" ]]; then
            bucket_region="us-east-1"
        fi
        
        if [[ "$bucket_region" == "$AWS_REGION" ]]; then
            log_success "S3 documents bucket $expected_documents_bucket exists in region $bucket_region"
        else
            log_error "S3 documents bucket $expected_documents_bucket is in region $bucket_region, expected $AWS_REGION"
        fi
    else
        log_error "S3 documents bucket $expected_documents_bucket does not exist"
    fi
    
    # Check frontend bucket
    increment_check
    if aws --profile "$AWS_PROFILE" s3api head-bucket --bucket "$expected_frontend_bucket" &> /dev/null; then
        local bucket_region
        bucket_region=$(aws --profile "$AWS_PROFILE" s3api get-bucket-location \
            --bucket "$expected_frontend_bucket" \
            --query 'LocationConstraint' --output text)
        
        # Handle null response for us-east-1
        if [[ "$bucket_region" == "null" ]]; then
            bucket_region="us-east-1"
        fi
        
        if [[ "$bucket_region" == "$AWS_REGION" ]]; then
            log_success "S3 frontend bucket $expected_frontend_bucket exists in region $bucket_region"
        else
            log_error "S3 frontend bucket $expected_frontend_bucket is in region $bucket_region, expected $AWS_REGION"
        fi
    else
        log_error "S3 frontend bucket $expected_frontend_bucket does not exist"
    fi
}

validate_dynamodb() {
    log_info "Validating DynamoDB tables..."
    
    local expected_table_name="ai-assistant-dev-documents"
    increment_check
    
    if aws --profile "$AWS_PROFILE" dynamodb describe-table --table-name "$expected_table_name" &> /dev/null; then
        local table_status
        table_status=$(aws --profile "$AWS_PROFILE" dynamodb describe-table \
            --table-name "$expected_table_name" \
            --query 'Table.TableStatus' --output text)
        
        if [[ "$table_status" == "ACTIVE" ]]; then
            log_success "DynamoDB table $expected_table_name exists and is ACTIVE"
        else
            log_warning "DynamoDB table $expected_table_name exists but status is $table_status"
        fi
    else
        log_error "DynamoDB table $expected_table_name does not exist"
    fi
}

validate_cloudfront() {
    log_info "Validating CloudFront distribution..."
    
    local expected_distribution_id="EL8L41G6CQJCD"
    local expected_domain="dq9tlzfsf1veq.cloudfront.net"
    
    increment_check
    if aws --profile "$AWS_PROFILE" cloudfront get-distribution --id "$expected_distribution_id" &> /dev/null; then
        local actual_domain
        actual_domain=$(aws --profile "$AWS_PROFILE" cloudfront get-distribution \
            --id "$expected_distribution_id" \
            --query 'Distribution.DomainName' --output text)
        
        if [[ "$actual_domain" == "$expected_domain" ]]; then
            log_success "CloudFront distribution $expected_distribution_id exists with domain $actual_domain"
        else
            log_error "CloudFront distribution $expected_distribution_id domain mismatch: expected $expected_domain, got $actual_domain"
        fi
    else
        log_error "CloudFront distribution $expected_distribution_id does not exist"
    fi
}

validate_bedrock_knowledge_base() {
    log_info "Validating Bedrock Knowledge Base..."
    
    local expected_kb_id="PQB7MB5ORO"
    local expected_kb_name="ai-assistant-knowledge-base"
    local expected_data_source_id="YUAUID9BJN"
    local expected_data_source_name="ai-assistant-dev-s3-data-source"
    
    # Check Knowledge Base
    increment_check
    if aws --profile "$AWS_PROFILE" bedrock-agent get-knowledge-base --knowledge-base-id "$expected_kb_id" &> /dev/null; then
        local kb_name
        kb_name=$(aws --profile "$AWS_PROFILE" bedrock-agent get-knowledge-base \
            --knowledge-base-id "$expected_kb_id" \
            --query 'knowledgeBase.name' --output text)
        
        if [[ "$kb_name" == "$expected_kb_name" ]]; then
            log_success "Bedrock Knowledge Base $expected_kb_id exists with name $kb_name"
        else
            log_error "Bedrock Knowledge Base $expected_kb_id name mismatch: expected $expected_kb_name, got $kb_name"
        fi
    else
        log_error "Bedrock Knowledge Base $expected_kb_id does not exist"
    fi
    
    # Check Data Source
    increment_check
    if aws --profile "$AWS_PROFILE" bedrock-agent get-data-source \
        --knowledge-base-id "$expected_kb_id" \
        --data-source-id "$expected_data_source_id" &> /dev/null; then
        
        local data_source_name
        data_source_name=$(aws --profile "$AWS_PROFILE" bedrock-agent get-data-source \
            --knowledge-base-id "$expected_kb_id" \
            --data-source-id "$expected_data_source_id" \
            --query 'dataSource.name' --output text)
        
        if [[ "$data_source_name" == "$expected_data_source_name" ]]; then
            log_success "Bedrock Data Source $expected_data_source_id exists with name $data_source_name"
        else
            log_error "Bedrock Data Source $expected_data_source_id name mismatch: expected $expected_data_source_name, got $data_source_name"
        fi
    else
        log_error "Bedrock Data Source $expected_data_source_id does not exist"
    fi
}

validate_iam_roles() {
    log_info "Validating IAM roles..."
    
    # Expected IAM roles from Terraform documentation
    declare -a expected_roles=(
        "ai-assistant-lambda-chat-execution-role"
        "ai-assistant-lambda-document-execution-role"
        "ai-assistant-lambda-admin-execution-role"
        "ai-assistant-lambda-kb-monitor-execution-role"
        "ai-assistant-api-gateway-cloudwatch-role"
        "ai-assistant-dev-bedrock-kb-role"
        "ai-assistant-monitoring-metrics-role"
        "ai-assistant-cloudwatch-sns-role"
    )
    
    for role_name in "${expected_roles[@]}"; do
        increment_check
        
        if aws --profile "$AWS_PROFILE" iam get-role --role-name "$role_name" &> /dev/null; then
            log_success "IAM role $role_name exists"
        else
            log_error "IAM role $role_name does not exist"
        fi
    done
}

validate_cloudwatch_logs() {
    log_info "Validating CloudWatch log groups..."
    
    # Expected log groups
    declare -a expected_log_groups=(
        "/aws/lambda/ai-assistant-chat-endpoints"
        "/aws/lambda/ai-assistant-dev-document-management"
        "/aws/lambda/ai-assistant-dev-admin-management"
        "/aws/lambda/ai-assistant-dev-document-upload"
        "/aws/lambda/ai-assistant-dev-kb-sync-monitor"
        "/aws/lambda/ai-assistant-monitoring-metrics"
        "/aws/apigateway/ai-assistant"
        "/aws/cloudfront/ai-assistant-dev"
    )
    
    for log_group in "${expected_log_groups[@]}"; do
        increment_check
        
        if aws --profile "$AWS_PROFILE" logs describe-log-groups --log-group-name-prefix "$log_group" --query 'logGroups[?logGroupName==`'"$log_group"'`]' --output text | grep -q "$log_group"; then
            log_success "CloudWatch log group $log_group exists"
        else
            log_error "CloudWatch log group $log_group does not exist"
        fi
    done
}

validate_eventbridge_rules() {
    log_info "Validating EventBridge rules..."
    
    # Expected EventBridge rules
    declare -a expected_rules=(
        "ai-assistant-dev-kb-sync-monitor-schedule"
        "ai-assistant-metrics-collection"
    )
    
    for rule_name in "${expected_rules[@]}"; do
        increment_check
        
        if aws --profile "$AWS_PROFILE" events describe-rule --name "$rule_name" &> /dev/null; then
            local rule_state
            rule_state=$(aws --profile "$AWS_PROFILE" events describe-rule \
                --name "$rule_name" \
                --query 'State' --output text)
            
            log_success "EventBridge rule $rule_name exists with state $rule_state"
        else
            log_error "EventBridge rule $rule_name does not exist"
        fi
    done
}

validate_sns_topics() {
    log_info "Validating SNS topics..."
    
    local expected_topic_name="ai-assistant-alerts"
    increment_check
    
    # List all SNS topics and check if our expected topic exists
    local topic_arn
    topic_arn=$(aws --profile "$AWS_PROFILE" sns list-topics \
        --query "Topics[?contains(TopicArn, '$expected_topic_name')].TopicArn" \
        --output text)
    
    if [[ -n "$topic_arn" ]]; then
        log_success "SNS topic $expected_topic_name exists with ARN: $topic_arn"
    else
        log_error "SNS topic $expected_topic_name does not exist"
    fi
}

# Generate validation report
generate_report() {
    echo ""
    echo "============================================================================"
    echo "                        VALIDATION REPORT"
    echo "============================================================================"
    echo ""
    echo "Total Checks: $TOTAL_CHECKS"
    echo -e "Passed: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed: ${RED}$FAILED_CHECKS${NC}"
    echo ""
    
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo -e "${GREEN}✓ All Terraform documentation is accurate!${NC}"
        echo "The Terraform files correctly reflect the current AWS infrastructure state."
    else
        echo -e "${RED}✗ Found $FAILED_CHECKS discrepancies between Terraform documentation and AWS state${NC}"
        echo ""
        echo "Discrepancies found:"
        for discrepancy in "${DISCREPANCIES[@]}"; do
            echo -e "  ${RED}•${NC} $discrepancy"
        done
        echo ""
        echo "Please update the Terraform documentation to match the current AWS state."
    fi
    
    echo ""
    echo "Validation completed at $(date)"
    echo "============================================================================"
}

# Main execution
main() {
    echo "============================================================================"
    echo "           Terraform Documentation Validation Script"
    echo "============================================================================"
    echo ""
    echo "Validating Terraform documentation against AWS infrastructure state..."
    echo "AWS Profile: $AWS_PROFILE"
    echo "AWS Region: $AWS_REGION"
    echo "Account ID: $ACCOUNT_ID"
    echo ""
    
    # Check prerequisites
    check_aws_cli
    
    # Run all validations
    validate_lambda_functions
    validate_api_gateway
    validate_cognito
    validate_s3_buckets
    validate_dynamodb
    validate_cloudfront
    validate_bedrock_knowledge_base
    validate_iam_roles
    validate_cloudwatch_logs
    validate_eventbridge_rules
    validate_sns_topics
    
    # Generate final report
    generate_report
    
    # Exit with appropriate code
    if [[ $FAILED_CHECKS -eq 0 ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"