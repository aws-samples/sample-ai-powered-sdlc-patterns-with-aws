# Developer Guide: Using Terraform Documentation

⚠️ **CRITICAL**: These Terraform files are for documentation and reference only. Never use them for deployment.

## Quick Start for Developers

### Understanding the Documentation Structure

```
terraform/
├── main.tf                    # Root module - start here for overview
├── variables.tf               # Current deployment values
├── outputs.tf                 # Actual AWS resource IDs and ARNs
├── README.md                  # Main documentation and deployment guide
├── DOCUMENTATION_MAINTENANCE.md # How to keep docs accurate
├── DEVELOPER_GUIDE.md         # This file - how to use the docs
└── modules/                   # Service-specific documentation
    ├── api-gateway/           # API Gateway configuration
    ├── bedrock/               # Bedrock Knowledge Base setup
    ├── cloudfront/            # CloudFront distribution
    ├── cognito/               # Authentication configuration
    ├── dynamodb/              # Database table structure
    ├── iam/                   # All IAM roles and policies
    ├── lambda/                # All Lambda functions
    ├── monitoring/            # CloudWatch, EventBridge, SNS
    └── s3/                    # S3 bucket configurations
```

## Common Developer Tasks

### 1. Finding Resource Information

#### Get Actual Resource IDs
```bash
# Check outputs.tf for current resource identifiers
grep -A 2 "output.*id" outputs.tf
grep -A 2 "output.*arn" outputs.tf

# Example outputs you'll find:
# - API Gateway ID: jpt8wzkowd
# - User Pool ID: us-west-2_FLJTm8Xt8
# - Knowledge Base ID: PQB7MB5ORO
```

#### Understand Service Configuration
```bash
# Lambda function details
cat modules/lambda/chat-handler/main.tf

# API Gateway endpoint structure
cat modules/api-gateway/main.tf

# Database schema
cat modules/dynamodb/main.tf
```

### 2. Integration Development

#### Lambda Function Integration
```typescript
// Use actual function names from documentation
const functionName = 'ai-assistant-chat-endpoints'; // From modules/lambda/chat-handler/main.tf

// Use actual IAM role ARNs from documentation
const executionRole = 'arn:aws:iam::254539707041:role/ai-assistant-lambda-chat-execution-role';
```

#### API Gateway Integration
```typescript
// Use actual API Gateway ID from outputs.tf
const apiGatewayId = 'jpt8wzkowd';
const baseUrl = 'https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev';

// Check modules/api-gateway/main.tf for endpoint structure
const endpoints = {
  chat: '/chat/ask',
  documents: '/documents',
  admin: '/admin'
};
```

#### Database Integration
```typescript
// Use actual table name from modules/dynamodb/main.tf
const tableName = 'ai-assistant-dev-documents';

// Check table structure in documentation
const documentSchema = {
  id: 'string',        // Partition key
  userId: 'string',    // GSI partition key
  title: 'string',
  content: 'string',
  createdAt: 'string'
};
```

### 3. Authentication Integration

#### Cognito Configuration
```typescript
// Use actual values from modules/cognito/main.tf and outputs.tf
const cognitoConfig = {
  userPoolId: 'us-west-2_FLJTm8Xt8',
  clientId: '3gr32ei5n768d88h02klhmpn8v',
  domain: 'ai-assistant-auth-3gja49wa',
  region: 'us-west-2'
};
```

### 4. Storage Integration

#### S3 Bucket Access
```typescript
// Use actual bucket names from modules/s3/main.tf
const buckets = {
  documents: 'ai-assistant-dev-documents-993738bb',
  frontend: 'ai-assistant-dev-frontend-e5e9acfe'
};

// Check bucket policies in documentation for access patterns
```

#### Bedrock Knowledge Base Integration
```typescript
// Use actual Knowledge Base ID from modules/bedrock/main.tf
const knowledgeBaseConfig = {
  knowledgeBaseId: 'PQB7MB5ORO',
  dataSourceId: 'YUAUID9BJN',
  modelArn: 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0'
};
```

## Troubleshooting with Documentation

### 1. Permission Issues

#### Check IAM Roles
```bash
# Find relevant IAM role in modules/iam/main.tf
grep -A 10 "resource.*aws_iam_role.*lambda" modules/iam/main.tf

# Check attached policies
grep -A 5 "aws_iam_role_policy_attachment" modules/iam/main.tf
```

#### Verify Resource Access
```bash
# Cross-reference with actual AWS state
aws iam get-role --role-name ai-assistant-lambda-chat-execution-role
aws iam list-attached-role-policies --role-name ai-assistant-lambda-chat-execution-role
```

### 2. Configuration Issues

#### Lambda Environment Variables
```bash
# Check documented environment variables
grep -A 10 "environment" modules/lambda/*/main.tf

# Compare with actual Lambda configuration
aws lambda get-function-configuration --function-name ai-assistant-chat-endpoints
```

#### API Gateway CORS Issues
```bash
# Check CORS configuration in documentation
grep -A 5 "cors" modules/api-gateway/main.tf

# Verify actual CORS settings
aws apigateway get-method --rest-api-id jpt8wzkowd --resource-id <resource-id> --http-method OPTIONS
```

### 3. Connectivity Issues

#### VPC and Security Groups
```bash
# Check network configuration (if applicable)
grep -A 10 "vpc\|security_group" modules/*/main.tf

# Verify actual network settings
aws ec2 describe-security-groups --group-names ai-assistant-*
```

## Best Practices for Developers

### 1. Always Verify with AWS CLI

Before making assumptions based on documentation:

```bash
# Verify resource exists and matches documentation
aws lambda get-function --function-name ai-assistant-chat-endpoints
aws apigateway get-rest-api --rest-api-id jpt8wzkowd
aws cognito-idp describe-user-pool --user-pool-id us-west-2_FLJTm8Xt8
```

### 2. Use Documentation for Architecture Understanding

```bash
# Understand service relationships
grep -r "module\." main.tf

# See data flow between services
grep -r "aws_.*\." modules/*/main.tf | grep -E "(bucket|table|function|api)"
```

### 3. Keep Documentation Updated

When you make AWS infrastructure changes:

```bash
# 1. Make the change via AWS CLI/Console
aws lambda update-function-configuration --function-name my-function --timeout 30

# 2. Update the corresponding documentation
vim modules/lambda/my-function/main.tf

# 3. Validate the change
./validate-terraform-docs.sh

# 4. Commit the documentation update
git add modules/lambda/my-function/main.tf
git commit -m "docs: update my-function timeout to 30 seconds"
```

## Common Integration Patterns

### 1. Lambda Function Development

```typescript
// File: src/lambda-function.ts
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';

export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
  // Use actual resource names from Terraform documentation
  const tableName = process.env.DYNAMODB_TABLE || 'ai-assistant-dev-documents';
  const bucketName = process.env.S3_BUCKET || 'ai-assistant-dev-documents-993738bb';
  
  // Implementation here
  return {
    statusCode: 200,
    headers: {
      'Access-Control-Allow-Origin': '*', // Check modules/api-gateway/main.tf for CORS config
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message: 'Success' })
  };
};
```

### 2. Frontend Integration

```typescript
// File: src/config/aws-config.ts
// Use values from Terraform outputs.tf and modules/cognito/main.tf

export const awsConfig = {
  region: 'us-west-2',
  cognito: {
    userPoolId: 'us-west-2_FLJTm8Xt8',
    clientId: '3gr32ei5n768d88h02klhmpn8v',
    domain: 'ai-assistant-auth-3gja49wa'
  },
  api: {
    baseUrl: 'https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev'
  },
  cloudfront: {
    domain: 'dq9tlzfsf1veq.cloudfront.net'
  }
};
```

### 3. Infrastructure Queries

```bash
#!/bin/bash
# File: scripts/get-infrastructure-info.sh
# Use this script to query actual AWS state and compare with documentation

echo "=== Lambda Functions ==="
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ai-assistant`)].FunctionName'

echo "=== API Gateway ==="
aws apigateway get-rest-api --rest-api-id jpt8wzkowd --query '{Name:name,Id:id,CreatedDate:createdDate}'

echo "=== Cognito User Pool ==="
aws cognito-idp describe-user-pool --user-pool-id us-west-2_FLJTm8Xt8 --query 'UserPool.{Name:Name,Id:Id,Status:Status}'

echo "=== S3 Buckets ==="
aws s3api list-buckets --query 'Buckets[?starts_with(Name, `ai-assistant`)].Name'

echo "=== DynamoDB Tables ==="
aws dynamodb list-tables --query 'TableNames[?starts_with(@, `ai-assistant`)]'
```

## Documentation Navigation Tips

### 1. Quick Reference Commands

```bash
# Find all resource types
grep -r "resource \"" modules/ | cut -d'"' -f2 | sort | uniq

# Find all data sources
grep -r "data \"" modules/ | cut -d'"' -f2 | sort | uniq

# Find all outputs
grep -r "output \"" . | cut -d'"' -f2 | sort

# Find specific resource by name
grep -r "ai-assistant-chat-endpoints" modules/
```

### 2. Understanding Dependencies

```bash
# Find what depends on a resource
grep -r "module\.lambda" .
grep -r "aws_lambda_function\." modules/

# Find resource references
grep -r "var\." modules/
grep -r "local\." modules/
```

### 3. Configuration Validation

```bash
# Check Terraform syntax (documentation only)
terraform validate

# Format files (if needed)
terraform fmt

# Show what would be planned (DO NOT APPLY)
terraform plan -out=/dev/null
```

## Getting Help

### 1. Documentation Issues
- Check [DOCUMENTATION_MAINTENANCE.md](./DOCUMENTATION_MAINTENANCE.md) for maintenance procedures
- Run validation script: `./validate-terraform-docs.sh`
- Compare with actual AWS state using AWS CLI

### 2. Integration Issues
- Verify resource IDs in `outputs.tf`
- Check service configuration in relevant module
- Cross-reference with AWS Console/CLI

### 3. Architecture Questions
- Start with `main.tf` for overall structure
- Review module README files for service-specific details
- Check variable defaults for current configuration values

### 4. Emergency Procedures
- **Never use Terraform commands** for fixes
- Use AWS Console for immediate issue resolution
- Update documentation after emergency changes
- Run validation script to ensure accuracy

## Remember

1. **Documentation Only**: Never run Terraform deployment commands
2. **Always Verify**: Cross-check documentation with actual AWS state
3. **Keep Updated**: Update documentation when making AWS changes
4. **Use AWS CLI**: For all actual infrastructure operations
5. **Validate Regularly**: Run validation script to ensure accuracy