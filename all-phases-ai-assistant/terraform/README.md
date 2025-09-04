# AI Assistant Terraform Infrastructure Documentation

⚠️ **CRITICAL WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT** ⚠️

This Terraform configuration serves as **DOCUMENTATION ONLY** for the AI-powered software development assistant infrastructure. These files accurately reflect the current AWS deployment state but must **NEVER** be used for actual deployment.

**DEPLOYMENT POLICY**: All infrastructure is deployed and managed via AWS CLI and AWS Console only. Terraform is strictly prohibited for deployment purposes in this project.

## Architecture Overview

The infrastructure includes:

- **Amazon Bedrock Knowledge Base**: Central RAG component for document processing and AI responses
- **S3 Bucket**: Document storage that serves as the Knowledge Base data source
- **OpenSearch Serverless**: Vector database for semantic search (managed by Knowledge Base)
- **IAM Roles and Policies**: Secure access between services
- **Security Policies**: OpenSearch Serverless encryption, network, and data access policies

## Prerequisites

1. **AWS CLI**: Configured with `aidlc_main` profile
2. **Terraform**: Version >= 1.0
3. **AWS Permissions**: Required permissions for Bedrock, S3, OpenSearch Serverless, and IAM

## ⚠️ IMPORTANT: NO DEPLOYMENT COMMANDS

**DO NOT RUN THE FOLLOWING COMMANDS:**
- ❌ `terraform init`
- ❌ `terraform plan`
- ❌ `terraform apply`
- ❌ `terraform destroy`

These Terraform files are for **DOCUMENTATION AND REFERENCE ONLY**.

## Documentation Guides

This directory contains comprehensive documentation for developers and maintainers:

- **[README.md](./README.md)** - This file: Overview and deployment procedures
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** - ⭐ Essential resource IDs and quick commands
- **[DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)** - How to use Terraform docs for development
- **[DOCUMENTATION_MAINTENANCE.md](./DOCUMENTATION_MAINTENANCE.md)** - How to keep docs accurate

## How to Use This Documentation

### For Understanding Infrastructure
1. **Review module structure** to understand component relationships
2. **Check resource configurations** to see current AWS settings
3. **Reference outputs** to find actual resource IDs and ARNs
4. **Study variables** to understand configuration parameters

### For Development Integration
- **Read [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)** for integration patterns
- **Use outputs.tf** to find actual resource IDs for your code
- **Check module configurations** to understand service relationships
- **Verify with AWS CLI** before making assumptions

### For Documentation Maintenance
- **Follow [DOCUMENTATION_MAINTENANCE.md](./DOCUMENTATION_MAINTENANCE.md)** procedures
- **Run validation script** monthly and after AWS changes
- **Update immediately** when making infrastructure changes
- **Keep documentation synchronized** with actual AWS state

### For Deployment (AWS CLI Only)
All infrastructure changes must be made through:
- **AWS Console**: For interactive resource management
- **AWS CLI**: For scripted deployments and updates
- **AWS SDK**: For programmatic resource management

See the [Deployment Guide](#deployment-guide) section below for proper deployment procedures.

## Configuration

### Environment Variables

The configuration uses environment-specific variable files:

- `environments/dev/terraform.tfvars` - Development environment
- `environments/staging/terraform.tfvars` - Staging environment (to be created)
- `environments/prod/terraform.tfvars` - Production environment (to be created)

### Key Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `aws_region` | AWS region (must be us-west-2) | `us-west-2` |
| `environment` | Environment name | `dev` |
| `knowledge_base_name` | Name of the Bedrock Knowledge Base | `ai-assistant-knowledge-base` |
| `embedding_model_arn` | ARN of the embedding model | Titan Text Embeddings V2 |
| `chunk_max_tokens` | Maximum tokens per document chunk | `300` |
| `chunk_overlap_percentage` | Overlap between chunks | `20` |

## Outputs

After deployment, Terraform provides these outputs:

- `knowledge_base_id` - ID of the Bedrock Knowledge Base
- `knowledge_base_arn` - ARN of the Knowledge Base
- `data_source_id` - ID of the S3 data source
- `documents_bucket_name` - Name of the S3 documents bucket
- `opensearch_collection_endpoint` - OpenSearch collection endpoint

## Security Features

### S3 Security
- ✅ Server-side encryption (AES256)
- ✅ Public access blocked
- ✅ Versioning enabled
- ✅ Lifecycle policies for cost optimization
- ✅ Abort incomplete multipart uploads

### IAM Security
- ✅ Least privilege access policies
- ✅ Service-specific roles
- ✅ Account condition checks

### OpenSearch Security
- ✅ Encryption at rest (AWS owned keys)
- ✅ Network access policies
- ✅ Data access policies with principal restrictions

## Testing

The configuration includes validation tests that verify:

1. All required resources are defined
2. Knowledge Base uses correct embedding model
3. S3 bucket is in the correct region
4. OpenSearch collection is VECTORSEARCH type

Run tests with:
```bash
terraform plan
```

## Security Scanning

Run Checkov security scan:
```bash
checkov -f main.tf --framework terraform
```

## Troubleshooting

### Common Issues

1. **OpenSearch Policy Name Too Long**
   - Policy names are limited to 32 characters
   - Use shortened names like `ai-assistant-dev-encrypt`

2. **Bedrock Model Access**
   - Ensure Bedrock models are available in us-west-2
   - Check IAM permissions for bedrock:InvokeModel

3. **S3 Bucket Name Conflicts**
   - Bucket names include random suffix for uniqueness
   - Check for existing buckets with similar names

### Useful Commands

```bash
# Format Terraform files
terraform fmt

# Show current state
terraform show

# List resources
terraform state list

# Destroy infrastructure (use with caution)
terraform destroy -var-file="environments/dev/terraform.tfvars"
```

## Deployment Guide

### Actual Deployment Process (AWS CLI Only)

Since Terraform files are documentation-only, use these AWS CLI approaches for infrastructure management:

#### Lambda Function Deployment
```bash
# Update Lambda function code
aws lambda update-function-code \
  --function-name ai-assistant-chat-endpoints \
  --zip-file fileb://function.zip

# Update function configuration
aws lambda update-function-configuration \
  --function-name ai-assistant-chat-endpoints \
  --runtime nodejs20.x \
  --environment Variables='{KEY=value}'
```

#### API Gateway Management
```bash
# List API Gateway resources
aws apigateway get-resources --rest-api-id jpt8wzkowd

# Update API Gateway configuration via AWS Console
# Navigate to: API Gateway > ai-assistant-api > Resources
```

#### S3 and DynamoDB Management
```bash
# Upload documents to S3
aws s3 cp document.pdf s3://ai-assistant-dev-documents-993738bb/

# Query DynamoDB table
aws dynamodb scan --table-name ai-assistant-dev-documents
```

#### Bedrock Knowledge Base Management
```bash
# Start Knowledge Base sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id PQB7MB5ORO \
  --data-source-id YUAUID9BJN
```

## Maintaining Documentation Accuracy

### Regular Validation Process

This documentation must be kept in sync with actual AWS infrastructure. Follow this process:

#### 1. Monthly Validation (Required)
Run the validation script to check documentation accuracy:
```bash
cd all-phases-ai-assistant/terraform
./validate-terraform-docs.sh
```

#### 2. After Infrastructure Changes
Whenever AWS resources are modified via CLI/Console:

1. **Query current state** using AWS CLI
2. **Update Terraform files** to match current state
3. **Run validation** to ensure accuracy
4. **Commit changes** to version control

#### 3. Validation Commands
```bash
# Verify Lambda functions match documentation
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `ai-assistant`)].{Name:FunctionName,Runtime:Runtime,Role:Role}'

# Verify API Gateway matches documentation
aws apigateway get-rest-api --rest-api-id jpt8wzkowd

# Verify Cognito User Pool matches documentation
aws cognito-idp describe-user-pool --user-pool-id us-west-2_FLJTm8Xt8

# Verify S3 buckets match documentation
aws s3api list-buckets --query 'Buckets[?starts_with(Name, `ai-assistant`)].Name'

# Verify DynamoDB table matches documentation
aws dynamodb describe-table --table-name ai-assistant-dev-documents

# Verify Bedrock Knowledge Base matches documentation
aws bedrock-agent get-knowledge-base --knowledge-base-id PQB7MB5ORO
```

### Documentation Update Workflow

When AWS infrastructure changes are made:

1. **Make infrastructure changes** via AWS CLI/Console
2. **Document the changes** by updating corresponding Terraform files
3. **Update resource IDs/ARNs** in variables and outputs
4. **Add documentation warnings** to any new files
5. **Test validation script** to ensure accuracy
6. **Commit documentation updates** with descriptive commit message

### File-Specific Maintenance

#### Variables (variables.tf)
- Update default values to match current deployment
- Add new variables for any new resources
- Remove variables for decommissioned resources

#### Outputs (outputs.tf)
- Update resource IDs and ARNs from AWS CLI queries
- Add outputs for new resources
- Verify all outputs reflect actual AWS state

#### Module Configurations
- Update resource names to match AWS Console
- Sync configuration parameters with actual settings
- Add documentation warnings to new modules

## Developer Usage Guide

### Understanding the Infrastructure

#### 1. Architecture Overview
- **Start with**: `main.tf` to understand overall structure
- **Review modules**: Each module represents a major AWS service
- **Check relationships**: Follow resource references between modules

#### 2. Finding Resource Information
```bash
# Find actual resource IDs in outputs.tf
grep -r "output.*id" .

# Find resource configurations in modules
find modules/ -name "main.tf" -exec grep -l "resource" {} \;

# Check current variable values
cat variables.tf | grep -A 5 "default"
```

#### 3. Troubleshooting with Documentation
- **Lambda issues**: Check `modules/lambda/*/main.tf` for function configurations
- **API Gateway issues**: Review `modules/api-gateway/main.tf` for endpoint setup
- **Permission issues**: Check `modules/iam/main.tf` for role and policy definitions
- **Storage issues**: Review `modules/s3/main.tf` and `modules/dynamodb/main.tf`

#### 4. Cross-Referencing with AWS
```bash
# Compare documentation with actual AWS state
aws lambda get-function --function-name ai-assistant-chat-endpoints
# Then check modules/lambda/chat-handler/main.tf

aws apigateway get-rest-api --rest-api-id jpt8wzkowd
# Then check modules/api-gateway/main.tf
```

### Best Practices for Developers

1. **Always verify with AWS CLI** before making assumptions based on documentation
2. **Update documentation** when you make infrastructure changes
3. **Use validation script** to check accuracy before major deployments
4. **Reference actual resource IDs** from outputs.tf for integration code
5. **Check module README files** for service-specific guidance

## Support and Troubleshooting

### Documentation Issues
If Terraform documentation doesn't match AWS reality:

1. **Run validation script**: `./validate-terraform-docs.sh`
2. **Check recent AWS changes**: Review CloudTrail or AWS Config
3. **Update documentation**: Modify Terraform files to match current state
4. **Report discrepancies**: Create issue with validation script output

### Infrastructure Issues
For actual infrastructure problems:

1. **Use AWS Console**: Direct service management and troubleshooting
2. **Check CloudWatch logs**: Monitor application and service logs
3. **Review IAM permissions**: Verify roles and policies in AWS Console
4. **Consult AWS documentation**: Use official AWS service documentation

### Emergency Procedures
In case of production issues:

1. **Never use Terraform commands** for emergency fixes
2. **Use AWS Console** for immediate issue resolution
3. **Document emergency changes** in incident reports
4. **Update Terraform documentation** after incident resolution
5. **Run validation** to ensure documentation accuracy post-incident