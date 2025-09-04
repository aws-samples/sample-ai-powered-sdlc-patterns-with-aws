# Terraform Documentation Maintenance Guide

⚠️ **CRITICAL**: This guide is for maintaining Terraform files as documentation only. Never use Terraform for actual deployment.

## Overview

The Terraform files in this project serve as Infrastructure as Code documentation that accurately reflects the current AWS deployment state. This guide provides procedures for keeping this documentation synchronized with the actual AWS infrastructure.

## Maintenance Schedule

### Monthly Validation (Required)
- **Frequency**: First Monday of each month
- **Duration**: 30-45 minutes
- **Responsibility**: DevOps team lead
- **Process**: Run full validation script and update any discrepancies

### Post-Change Updates (Immediate)
- **Trigger**: Any AWS infrastructure change via CLI/Console
- **Duration**: 5-15 minutes per change
- **Responsibility**: Developer making the change
- **Process**: Update corresponding Terraform files immediately

### Quarterly Review (Recommended)
- **Frequency**: End of each quarter
- **Duration**: 2-3 hours
- **Responsibility**: Full development team
- **Process**: Comprehensive review of all modules and documentation

## Validation Procedures

### 1. Automated Validation Script

Run the validation script to check all resources:

```bash
cd all-phases-ai-assistant/terraform
./validate-terraform-docs.sh
```

The script checks:
- ✅ Lambda function configurations
- ✅ API Gateway settings
- ✅ Cognito User Pool configuration
- ✅ S3 bucket policies and settings
- ✅ DynamoDB table structure
- ✅ IAM roles and policies
- ✅ Bedrock Knowledge Base configuration
- ✅ CloudWatch log groups
- ✅ EventBridge rules
- ✅ CloudFront distribution

### 2. Manual Verification Commands

#### Lambda Functions
```bash
# List all AI Assistant Lambda functions
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `ai-assistant`)].{Name:FunctionName,Runtime:Runtime,Handler:Handler,Role:Role}' \
  --output table

# Get specific function details
aws lambda get-function --function-name ai-assistant-chat-endpoints
```

#### API Gateway
```bash
# Get API Gateway details
aws apigateway get-rest-api --rest-api-id jpt8wzkowd

# List resources and methods
aws apigateway get-resources --rest-api-id jpt8wzkowd
```

#### Cognito
```bash
# Get User Pool details
aws cognito-idp describe-user-pool --user-pool-id us-west-2_FLJTm8Xt8

# Get User Pool Client details
aws cognito-idp describe-user-pool-client \
  --user-pool-id us-west-2_FLJTm8Xt8 \
  --client-id 3gr32ei5n768d88h02klhmpn8v
```

#### Storage Resources
```bash
# List S3 buckets
aws s3api list-buckets --query 'Buckets[?starts_with(Name, `ai-assistant`)].{Name:Name,CreationDate:CreationDate}'

# Get DynamoDB table details
aws dynamodb describe-table --table-name ai-assistant-dev-documents
```

#### Bedrock Knowledge Base
```bash
# Get Knowledge Base details
aws bedrock-agent get-knowledge-base --knowledge-base-id PQB7MB5ORO

# Get data source details
aws bedrock-agent get-data-source \
  --knowledge-base-id PQB7MB5ORO \
  --data-source-id YUAUID9BJN
```

#### IAM Roles
```bash
# List AI Assistant IAM roles
aws iam list-roles --query 'Roles[?starts_with(RoleName, `ai-assistant`)].{RoleName:RoleName,Arn:Arn}'
```

#### Monitoring Resources
```bash
# List CloudWatch log groups
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/ai-assistant"

# List EventBridge rules
aws events list-rules --name-prefix "ai-assistant"

# List SNS topics
aws sns list-topics --query 'Topics[?contains(TopicArn, `ai-assistant`)]'
```

## Update Procedures

### When AWS Resources Change

#### 1. Immediate Documentation Update
After making any AWS infrastructure change:

```bash
# 1. Query the changed resource
aws <service> <describe-command> --<resource-id> <actual-id>

# 2. Update corresponding Terraform file
vim modules/<service>/main.tf

# 3. Update variables if needed
vim variables.tf

# 4. Update outputs if needed
vim outputs.tf

# 5. Validate the change
./validate-terraform-docs.sh

# 6. Commit the documentation update
git add .
git commit -m "docs: update <service> configuration to match AWS state"
```

#### 2. Resource Addition Process
When new AWS resources are created:

1. **Create new module** (if needed):
   ```bash
   mkdir -p modules/<new-service>
   touch modules/<new-service>/main.tf
   touch modules/<new-service>/variables.tf
   touch modules/<new-service>/outputs.tf
   ```

2. **Add documentation warning** to all new files:
   ```hcl
   /*
    * ============================================================================
    * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
    * ============================================================================
    * 
    * This Terraform configuration is for documentation purposes only.
    * It reflects the current state of AWS infrastructure deployed via AWS CLI.
    * 
    * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
    * 
    * For deployments, use AWS CLI commands as specified in README.md
    * ============================================================================
    */
   ```

3. **Document the resource** with actual AWS values
4. **Add module call** to main.tf
5. **Add variables** with current values as defaults
6. **Add outputs** with actual resource IDs/ARNs
7. **Update validation script** to include new resource checks

#### 3. Resource Removal Process
When AWS resources are decommissioned:

1. **Remove module call** from main.tf
2. **Remove or comment out** module directory
3. **Remove related variables** and outputs
4. **Update validation script** to remove checks
5. **Document removal** in commit message

### Common Update Scenarios

#### Lambda Function Updates
```bash
# After updating Lambda function via AWS CLI
aws lambda get-function --function-name <function-name>

# Update corresponding module file
vim modules/lambda/<function-name>/main.tf

# Update runtime, environment variables, role, etc.
```

#### API Gateway Changes
```bash
# After modifying API Gateway via Console
aws apigateway get-rest-api --rest-api-id jpt8wzkowd

# Update API Gateway module
vim modules/api-gateway/main.tf

# Update resources, methods, integrations, etc.
```

#### IAM Role/Policy Changes
```bash
# After modifying IAM via Console
aws iam get-role --role-name <role-name>
aws iam list-attached-role-policies --role-name <role-name>

# Update IAM module
vim modules/iam/main.tf

# Update role definitions and policy attachments
```

## Quality Assurance

### Pre-Commit Checklist
Before committing documentation updates:

- [ ] Ran validation script successfully
- [ ] All resource IDs/ARNs match AWS CLI output
- [ ] Documentation warnings present in all files
- [ ] Variable defaults reflect current deployment
- [ ] Outputs reference actual resource values
- [ ] Module relationships are accurate
- [ ] No sensitive data exposed in configurations

### Validation Script Maintenance
The validation script itself needs maintenance:

#### Monthly Script Review
- Check for new AWS CLI commands or output formats
- Add validation for any new resource types
- Update expected values for changed resources
- Test script execution and error handling

#### Script Enhancement
```bash
# Add new resource validation
echo "Validating new resource type..."
aws <service> <command> --query '<query>' --output text

# Add comparison logic
if [ "$actual_value" != "$expected_value" ]; then
    echo "❌ Mismatch found in <resource>"
    echo "Expected: $expected_value"
    echo "Actual: $actual_value"
fi
```

## Troubleshooting

### Common Issues

#### 1. Validation Script Failures
**Symptom**: Script reports mismatches
**Solution**:
1. Verify AWS CLI profile is correct (`aidlc_main`)
2. Check AWS permissions for describe/list operations
3. Update Terraform files to match current AWS state
4. Re-run validation script

#### 2. Missing Resources
**Symptom**: AWS CLI returns empty results
**Solution**:
1. Verify resource still exists in AWS Console
2. Check resource naming and IDs
3. Confirm correct AWS region (us-west-2)
4. Update documentation if resource was removed

#### 3. Permission Errors
**Symptom**: AWS CLI commands fail with access denied
**Solution**:
1. Verify AWS profile configuration
2. Check IAM permissions for CLI operations
3. Ensure using correct account (254539707041)
4. Contact AWS administrator if needed

#### 4. Outdated Documentation
**Symptom**: Large number of validation failures
**Solution**:
1. Run comprehensive AWS CLI queries
2. Systematically update each module
3. Focus on one service at a time
4. Validate incrementally

### Emergency Procedures

#### Critical Infrastructure Changes
If emergency AWS changes are made without documentation updates:

1. **Document immediately** after emergency resolution
2. **Run full validation** to identify all changes
3. **Update all affected modules** systematically
4. **Create incident report** documenting changes made
5. **Schedule review** to prevent future occurrences

#### Documentation Corruption
If Terraform files become severely out of sync:

1. **Backup current files**: `cp -r . ../terraform-backup-$(date +%Y%m%d)`
2. **Query all AWS resources** systematically
3. **Rebuild documentation** module by module
4. **Validate each module** before proceeding to next
5. **Test validation script** thoroughly

## Best Practices

### Documentation Standards
- **Always include warnings** about documentation-only purpose
- **Use actual resource IDs** from AWS, never placeholders
- **Keep comments current** and relevant
- **Follow consistent naming** patterns
- **Document all relationships** between resources

### Maintenance Habits
- **Update immediately** after AWS changes
- **Run validation regularly** (at least monthly)
- **Review quarterly** for completeness
- **Keep validation script current** with new resources
- **Document maintenance activities** in commit messages

### Team Coordination
- **Assign ownership** for each module
- **Share validation results** with team
- **Coordinate major updates** during team meetings
- **Train new team members** on maintenance procedures
- **Maintain this guide** as processes evolve

## Resources

### AWS CLI References
- [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/reference/)
- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [AWS CLI Output Formats](https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-output-format.html)

### Terraform Documentation
- [Terraform Configuration Language](https://www.terraform.io/docs/language/index.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

### Project-Specific Resources
- [Main Project README](../README.md)
- [Deployment Workflow](../deployment-workflow.md)
- [No Terraform Policy](../.kiro/steering/no-terraform.md)
- [AWS Profile Configuration](../.kiro/steering/aws-profile.md)