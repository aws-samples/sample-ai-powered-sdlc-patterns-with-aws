#!/bin/bash

# iCode Full Stack Deployment Script
# This script handles the two-stage deployment process

set -e  # Exit on any error

echo "🚀 iCode Full Stack Deployment"
echo "================================"

# Check if .env file exists
if [ ! -f "cdk/.env" ]; then
    echo "❌ Error: .env file not found in cdk/"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

# Source environment variables and export them
set -a  # Automatically export all variables
source cdk/.env
set +a  # Stop automatically exporting

# Validate required environment variables
if [ -z "$CDK_DEFAULT_ACCOUNT" ] || [ -z "$CDK_DEFAULT_REGION" ] || [ -z "$ALLOWED_IP_ADDRESS" ]; then
    echo "❌ Error: Required environment variables not set"
    echo "Please ensure CDK_DEFAULT_ACCOUNT, CDK_DEFAULT_REGION, and ALLOWED_IP_ADDRESS are set in .env"
    exit 1
fi

echo "📋 Configuration:"
echo "  AWS Account: $CDK_DEFAULT_ACCOUNT"
echo "  AWS Region: $CDK_DEFAULT_REGION"
echo "  Allowed IP: $ALLOWED_IP_ADDRESS"
echo "  ECR Repository: ${ECR_REPOSITORY_NAME:-icode-fullstack}"
echo ""

# Stage 1: Create ECR Repository and Build/Push Container
echo "🏗️  Stage 1: Creating ECR Repository and Building Container"
echo "=========================================================="

# Create ECR repository
echo "Creating ECR repository..."
aws ecr create-repository \
    --repository-name "${ECR_REPOSITORY_NAME:-icode-fullstack}" \
    --region "$CDK_DEFAULT_REGION" \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    2>/dev/null || echo "ECR repository already exists (this is fine)"

# Get ECR login token
echo "Logging into ECR..."
aws ecr get-login-password --region "$CDK_DEFAULT_REGION" | \
    docker login --username AWS --password-stdin "$CDK_DEFAULT_ACCOUNT.dkr.ecr.$CDK_DEFAULT_REGION.amazonaws.com"

# Build Docker image for Linux AMD64 architecture
echo "Building Docker image for Linux AMD64..."
docker build --platform linux/amd64 -f Dockerfile.fullstack -t "${ECR_REPOSITORY_NAME:-icode-fullstack}:${IMAGE_TAG:-latest}" .

# Tag for ECR
docker tag "${ECR_REPOSITORY_NAME:-icode-fullstack}:${IMAGE_TAG:-latest}" \
    "$CDK_DEFAULT_ACCOUNT.dkr.ecr.$CDK_DEFAULT_REGION.amazonaws.com/${ECR_REPOSITORY_NAME:-icode-fullstack}:${IMAGE_TAG:-latest}"

# Push to ECR
echo "Pushing image to ECR..."
docker push "$CDK_DEFAULT_ACCOUNT.dkr.ecr.$CDK_DEFAULT_REGION.amazonaws.com/${ECR_REPOSITORY_NAME:-icode-fullstack}:${IMAGE_TAG:-latest}"

echo "✅ Stage 1 Complete: Container image is ready in ECR"
echo ""

# Stage 2: Deploy CDK Infrastructure
echo "🏗️  Stage 2: Deploying CDK Infrastructure"
echo "========================================"

cd cdk

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing CDK dependencies..."
    npm install
fi

# Build CDK
echo "Building CDK..."
npm run build

# Deploy CDK stack with environment variables
echo "Deploying CDK stack..."
export CDK_DEFAULT_ACCOUNT CDK_DEFAULT_REGION ALLOWED_IP_ADDRESS CLAUDE_MODEL_ID ECR_REPOSITORY_NAME IMAGE_TAG MCP_SERVER_URLS BEDROCK_KNOWLEDGE_BASE_ID
npx cdk deploy --require-approval never

cd ..

echo ""
echo "🎉 Deployment Complete!"
echo "======================"
echo ""
echo "📋 Next Steps:"
echo "1. Check the CDK outputs for your Load Balancer DNS name"
echo "2. Configure your frontend with the Cognito and API endpoints"
echo "3. Create users in Cognito User Pool through AWS Console"
echo "4. Test the application"
echo ""
echo "🔒 Security Note:"
echo "Your application is only accessible from IP: $ALLOWED_IP_ADDRESS"
echo "To change this, update ALLOWED_IP_ADDRESS in .env and redeploy"