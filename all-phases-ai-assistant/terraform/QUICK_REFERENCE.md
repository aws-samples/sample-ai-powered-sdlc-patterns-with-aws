# Terraform Documentation Quick Reference

⚠️ **DOCUMENTATION ONLY - NEVER USE FOR DEPLOYMENT** ⚠️

## Essential Resource IDs (from outputs.tf)

```bash
# API Gateway
API_ID="jpt8wzkowd"
API_URL="https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev"

# Cognito
USER_POOL_ID="us-west-2_FLJTm8Xt8"
CLIENT_ID="3gr32ei5n768d88h02klhmpn8v"
COGNITO_DOMAIN="ai-assistant-auth-3gja49wa"

# S3 Buckets
DOCUMENTS_BUCKET="ai-assistant-dev-documents-993738bb"
FRONTEND_BUCKET="ai-assistant-dev-frontend-e5e9acfe"

# DynamoDB
DOCUMENTS_TABLE="ai-assistant-dev-documents"

# Bedrock Knowledge Base
KB_ID="PQB7MB5ORO"
DATA_SOURCE_ID="YUAUID9BJN"

# CloudFront
DISTRIBUTION_ID="EL8L41G6CQJCD"
CLOUDFRONT_DOMAIN="dq9tlzfsf1veq.cloudfront.net"
```

## Lambda Functions (from modules/lambda/)

```bash
# Function Names
ai-assistant-chat-endpoints          # nodejs20.x - Chat handler
ai-assistant-dev-document-management # nodejs20.x - Document CRUD
ai-assistant-dev-admin-management    # nodejs18.x - Admin operations
ai-assistant-dev-document-upload     # nodejs18.x - File uploads
ai-assistant-dev-kb-sync-monitor     # nodejs18.x - KB sync monitoring
ai-assistant-monitoring-metrics      # nodejs18.x - Metrics collection
```

## Quick Commands

### Verify Documentation Accuracy
```bash
cd all-phases-ai-assistant/terraform
./validate-terraform-docs.sh
```

### Find Resource Information
```bash
# Get all resource IDs
grep -A 2 "output.*id" outputs.tf

# Find Lambda configurations
cat modules/lambda/*/main.tf | grep -E "(function_name|runtime|role)"

# Check API Gateway endpoints
cat modules/api-gateway/main.tf | grep -E "(resource|method)"
```

### Cross-Reference with AWS
```bash
# Verify Lambda functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ai-assistant`)].FunctionName'

# Check API Gateway
aws apigateway get-rest-api --rest-api-id jpt8wzkowd

# Verify Cognito
aws cognito-idp describe-user-pool --user-pool-id us-west-2_FLJTm8Xt8
```

## Common Integration Patterns

### TypeScript/JavaScript
```typescript
// Use actual resource IDs from documentation
const config = {
  apiUrl: 'https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev',
  userPoolId: 'us-west-2_FLJTm8Xt8',
  clientId: '3gr32ei5n768d88h02klhmpn8v',
  region: 'us-west-2'
};
```

### AWS CLI Deployment
```bash
# Update Lambda function
aws lambda update-function-code \
  --function-name ai-assistant-chat-endpoints \
  --zip-file fileb://function.zip

# Upload to S3
aws s3 cp file.pdf s3://ai-assistant-dev-documents-993738bb/
```

## Documentation Structure

```
terraform/
├── README.md                 # Main documentation
├── DEVELOPER_GUIDE.md        # How to use docs for development  
├── DOCUMENTATION_MAINTENANCE.md # How to keep docs accurate
├── QUICK_REFERENCE.md        # This file
├── main.tf                   # Root module overview
├── outputs.tf                # ⭐ ACTUAL RESOURCE IDs
├── variables.tf              # Current deployment values
└── modules/
    ├── api-gateway/          # API Gateway jpt8wzkowd
    ├── bedrock/              # Knowledge Base PQB7MB5ORO
    ├── cloudfront/           # Distribution EL8L41G6CQJCD
    ├── cognito/              # User Pool us-west-2_FLJTm8Xt8
    ├── dynamodb/             # Table ai-assistant-dev-documents
    ├── iam/                  # All 9 IAM roles
    ├── lambda/               # All 6 Lambda functions
    ├── monitoring/           # CloudWatch, EventBridge, SNS
    └── s3/                   # Document and frontend buckets
```

## Remember

- ✅ **Use for reference**: Architecture understanding and resource IDs
- ✅ **Cross-check with AWS**: Always verify with AWS CLI/Console
- ✅ **Update after changes**: Keep documentation synchronized
- ❌ **Never deploy**: Use AWS CLI/Console for all infrastructure changes
- ❌ **Never run**: terraform init/plan/apply/destroy