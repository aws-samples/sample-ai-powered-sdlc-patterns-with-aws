#!/bin/bash

# Configure Knowledge Base for iCode Application
# This script updates the ECS service with Knowledge Base configuration
# without requiring a full CDK redeployment

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 iCode Knowledge Base Configuration${NC}"
echo "========================================"

# Check if required parameters are provided
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Error: Missing required parameters${NC}"
    echo ""
    echo "Usage: $0 <KNOWLEDGE_BASE_ID> <DATA_SOURCE_ID>"
    echo ""
    echo "Example:"
    echo "  $0 ABCD1234EF WXYZ5678GH"
    echo ""
    echo "To get these IDs:"
    echo "  1. Go to AWS Bedrock console → Knowledge bases"
    echo "  2. Find your Knowledge Base ID"
    echo "  3. Click on the KB → Data sources → Find your Data Source ID"
    exit 1
fi

KB_ID="$1"
DATA_SOURCE_ID="$2"

# Load environment variables from CDK deployment
if [ ! -f "cdk/.env" ]; then
    echo -e "${RED}❌ Error: .env file not found in cdk/${NC}"
    echo "Please ensure you've deployed the CDK stack first"
    exit 1
fi

source cdk/.env

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  AWS Account: $CDK_DEFAULT_ACCOUNT"
echo "  AWS Region: $CDK_DEFAULT_REGION"
echo "  Knowledge Base ID: $KB_ID"
echo "  Data Source ID: $DATA_SOURCE_ID"
echo ""

# Verify AWS CLI is configured
if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: AWS CLI not configured or no valid credentials${NC}"
    exit 1
fi

# Get current ECS task definition
echo -e "${GREEN}🔍 Getting current ECS task definition...${NC}"
TASK_DEF_ARN=$(aws ecs describe-services \
    --cluster icode-cluster \
    --services icode-fullstack-service \
    --query 'services[0].taskDefinition' \
    --output text)

if [ "$TASK_DEF_ARN" == "None" ] || [ -z "$TASK_DEF_ARN" ]; then
    echo -e "${RED}❌ Error: Could not find ECS service or task definition${NC}"
    echo "Please ensure the CDK stack is deployed and ECS service is running"
    exit 1
fi

echo "  Current task definition: $TASK_DEF_ARN"

# Get the current task definition JSON
TASK_DEF_JSON=$(aws ecs describe-task-definition --task-definition "$TASK_DEF_ARN")

# Extract the task definition without revision-specific fields and save to temp file for debugging
TEMP_FILE=$(mktemp)
echo "$TASK_DEF_JSON" | jq '.taskDefinition | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' > "$TEMP_FILE"
NEW_TASK_DEF=$(cat "$TEMP_FILE")

# Update environment variables
echo -e "${GREEN}🔧 Updating environment variables...${NC}"

# First, let's check if environment array exists and handle it properly
UPDATED_TASK_DEF=$(echo "$NEW_TASK_DEF" | jq --arg kb_id "$KB_ID" --arg ds_id "$DATA_SOURCE_ID" '
  # Ensure environment array exists
  if .containerDefinitions[0].environment == null then
    .containerDefinitions[0].environment = []
  else . end |
  
  # Update existing KB ID or add it
  if (.containerDefinitions[0].environment | map(.name) | index("BEDROCK_KNOWLEDGE_BASE_ID")) then
    .containerDefinitions[0].environment |= map(if .name == "BEDROCK_KNOWLEDGE_BASE_ID" then .value = $kb_id else . end)
  else
    .containerDefinitions[0].environment += [{"name": "BEDROCK_KNOWLEDGE_BASE_ID", "value": $kb_id}]
  end |
  
  # Update existing Data Source ID or add it
  if (.containerDefinitions[0].environment | map(.name) | index("BEDROCK_DATA_SOURCE_ID")) then
    .containerDefinitions[0].environment |= map(if .name == "BEDROCK_DATA_SOURCE_ID" then .value = $ds_id else . end)
  else
    .containerDefinitions[0].environment += [{"name": "BEDROCK_DATA_SOURCE_ID", "value": $ds_id}]
  end
')

# Verify the updates
KB_FOUND=$(echo "$UPDATED_TASK_DEF" | jq -r '.containerDefinitions[0].environment[]? | select(.name == "BEDROCK_KNOWLEDGE_BASE_ID") | .value // empty')
DS_FOUND=$(echo "$UPDATED_TASK_DEF" | jq -r '.containerDefinitions[0].environment[]? | select(.name == "BEDROCK_DATA_SOURCE_ID") | .value // empty')

echo "  ✅ BEDROCK_KNOWLEDGE_BASE_ID: $KB_FOUND"
echo "  ✅ BEDROCK_DATA_SOURCE_ID: $DS_FOUND"

# Register new task definition
echo -e "${GREEN}📝 Registering new task definition...${NC}"

# Save updated task definition to temp file
UPDATED_TEMP_FILE=$(mktemp)
echo "$UPDATED_TASK_DEF" > "$UPDATED_TEMP_FILE"

# Validate JSON before sending
if ! jq empty "$UPDATED_TEMP_FILE" 2>/dev/null; then
    echo -e "${RED}❌ Error: Generated task definition is not valid JSON${NC}"
    echo "Task definition saved to: $UPDATED_TEMP_FILE"
    exit 1
fi

NEW_TASK_DEF_ARN=$(aws ecs register-task-definition --cli-input-json file://"$UPDATED_TEMP_FILE" --query 'taskDefinition.taskDefinitionArn' --output text)

# Clean up temp files
rm -f "$TEMP_FILE" "$UPDATED_TEMP_FILE"

echo "  New task definition: $NEW_TASK_DEF_ARN"

# Update ECS service to use new task definition
echo -e "${GREEN}🚀 Updating ECS service...${NC}"
aws ecs update-service \
    --cluster icode-cluster \
    --service icode-fullstack-service \
    --task-definition "$NEW_TASK_DEF_ARN" \
    --force-new-deployment >/dev/null

echo -e "${GREEN}✅ Knowledge Base configuration completed successfully!${NC}"
echo ""
echo -e "${YELLOW}📊 Next steps:${NC}"
echo "  1. Wait for ECS service to deploy new tasks (2-3 minutes)"
echo "  2. Check service status: aws ecs describe-services --cluster icode-cluster --services icode-fullstack-service"
echo "  3. Monitor logs: aws logs tail /ecs/icode-fullstack --follow"
echo "  4. Test Knowledge Base integration in your application"
echo ""
echo -e "${GREEN}🎉 Your iCode application now has Knowledge Base integration enabled!${NC}"