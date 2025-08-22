#!/bin/bash

# iCode Full Stack Cleanup Script
# This script removes all deployed resources

set -e

echo "🧹 iCode Full Stack Cleanup"
echo "==========================="

# Check if .env file exists
if [ ! -f "cdk/.env" ]; then
    echo "❌ Error: .env file not found in cdk/"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

# Source environment variables
source cdk/.env

echo "📋 Configuration:"
echo "  AWS Account: $CDK_DEFAULT_ACCOUNT"
echo "  AWS Region: $CDK_DEFAULT_REGION"
echo "  ECR Repository: ${ECR_REPOSITORY_NAME:-icode-fullstack}"
echo ""

read -p "⚠️  This will DELETE all iCode resources. Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleanup cancelled."
    exit 1
fi

# Scale down ECS service first (if it exists)
echo "🗑️  Scaling down ECS service..."
aws ecs update-service \
    --cluster icode-cluster \
    --service icode-fullstack-service \
    --desired-count 0 \
    --region "$CDK_DEFAULT_REGION" \
    2>/dev/null || echo "ECS service not found or already scaled down"

# Wait a moment for tasks to stop
echo "⏳ Waiting for ECS tasks to stop..."
sleep 10

# Destroy CDK stack
echo "🗑️  Destroying CDK stack..."
cd cdk
npx cdk destroy --force || echo "CDK stack destruction completed (or was already destroyed)"
cd ..

# Clean up persistent log groups that CDK might not remove
echo "🗑️  Cleaning up CloudWatch log groups..."
LOG_GROUPS=(
    "/aws/cloudtrail/icode-audit"
    "/aws/vpc/flowlogs"
    "/ecs/icode-fullstack"
    "/ecs/backend"
    "/aws/ecs/containerinsights/icode-cluster/performance"
    "/aws/lambda/conversation-summarizer"
)

for log_group in "${LOG_GROUPS[@]}"; do
    aws logs delete-log-group \
        --log-group-name "$log_group" \
        --region "$CDK_DEFAULT_REGION" \
        2>/dev/null || echo "Log group $log_group already deleted or doesn't exist"
done

# Clean up any remaining icode-related log groups
echo "🗑️  Cleaning up any remaining iCode log groups..."
REMAINING_LOGS=$(aws logs describe-log-groups \
    --query 'logGroups[?contains(logGroupName, `icode`)].logGroupName' \
    --output text \
    --region "$CDK_DEFAULT_REGION" 2>/dev/null || echo "")

if [ ! -z "$REMAINING_LOGS" ]; then
    for log_group in $REMAINING_LOGS; do
        echo "Deleting remaining log group: $log_group"
        aws logs delete-log-group \
            --log-group-name "$log_group" \
            --region "$CDK_DEFAULT_REGION" \
            2>/dev/null || echo "Failed to delete $log_group"
    done
fi

# Delete ECR repository (this will also delete all images)
echo "🗑️  Deleting ECR repository..."
aws ecr delete-repository \
    --repository-name "${ECR_REPOSITORY_NAME:-icode-fullstack}" \
    --region "$CDK_DEFAULT_REGION" \
    --force \
    2>/dev/null || echo "ECR repository already deleted (this is fine)"

# Clean up any remaining CloudFormation stacks
echo "🗑️  Checking for remaining CloudFormation stacks..."
REMAINING_STACKS=$(aws cloudformation list-stacks \
    --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE ROLLBACK_COMPLETE CREATE_FAILED ROLLBACK_FAILED \
    --query 'StackSummaries[?contains(StackName, `icode`) || contains(StackName, `ICode`)].StackName' \
    --output text \
    --region "$CDK_DEFAULT_REGION" 2>/dev/null || echo "")

if [ ! -z "$REMAINING_STACKS" ]; then
    for stack in $REMAINING_STACKS; do
        echo "Deleting remaining stack: $stack"
        aws cloudformation delete-stack \
            --stack-name "$stack" \
            --region "$CDK_DEFAULT_REGION" \
            2>/dev/null || echo "Failed to delete stack $stack"
    done
fi

echo ""
echo "✅ Cleanup Complete!"
echo "All iCode resources have been removed."
echo ""
echo "Note: If you had a Knowledge Base, you may need to delete it manually from the Bedrock console."