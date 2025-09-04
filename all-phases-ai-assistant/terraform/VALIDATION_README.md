# Terraform Documentation Validation

This directory contains scripts to validate that the Terraform documentation accurately reflects the current AWS infrastructure state.

## Overview

The Terraform files in this project are **DOCUMENTATION ONLY** and should never be used for deployment. These validation scripts ensure that the documented infrastructure matches the actual deployed AWS resources.

## Scripts

### `validate-terraform-docs.sh`

The main validation script that performs comprehensive checks against all documented AWS resources.

**Usage:**
```bash
./validate-terraform-docs.sh
```

**What it validates:**
- Lambda functions (6 functions with correct runtimes)
- API Gateway (ID: jpt8wzkowd)
- Cognito User Pool (ID: us-west-2_FLJTm8Xt8)
- S3 buckets (documents and frontend)
- DynamoDB table (ai-assistant-dev-documents)
- CloudFront distribution (ID: EL8L41G6CQJCD)
- Bedrock Knowledge Base (ID: PQB7MB5ORO)
- IAM roles (9 roles)
- CloudWatch log groups
- EventBridge rules
- SNS topics

**Exit codes:**
- `0`: All validations passed
- `1`: One or more validations failed

### `test-validation.sh`

A quick test script to verify basic AWS connectivity and key resources.

**Usage:**
```bash
./test-validation.sh
```

### `generate-validation-report.sh`

Generates a detailed validation report with timestamps and saves it to a file.

**Usage:**
```bash
./generate-validation-report.sh
```

## Prerequisites

1. **AWS CLI**: Must be installed and configured
2. **AWS Profile**: Must use `aidlc_main` profile
3. **Permissions**: Must have read access to all AWS services
4. **Region**: Must be configured for `us-west-2`

## Validation Process

The validation script performs the following steps:

1. **Authentication Check**: Verifies AWS CLI access and correct account
2. **Resource Existence**: Checks if all documented resources exist
3. **Configuration Validation**: Compares resource configurations with documented values
4. **Discrepancy Reporting**: Reports any mismatches found

## Expected Resources

### Lambda Functions
- `ai-assistant-chat-endpoints` (nodejs20.x)
- `ai-assistant-dev-document-management` (nodejs20.x)
- `ai-assistant-dev-admin-management` (nodejs18.x)
- `ai-assistant-dev-document-upload` (nodejs18.x)
- `ai-assistant-dev-kb-sync-monitor` (nodejs18.x)
- `ai-assistant-monitoring-metrics` (nodejs18.x)

### API Gateway
- ID: `jpt8wzkowd`
- URL: `https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev`

### Cognito
- User Pool ID: `us-west-2_FLJTm8Xt8`
- Client ID: `3gr32ei5n768d88h02klhmpn8v`
- Domain: `ai-assistant-auth-3gja49wa`

### S3 Buckets
- Documents: `ai-assistant-dev-documents-993738bb`
- Frontend: `ai-assistant-dev-frontend-e5e9acfe`

### DynamoDB
- Table: `ai-assistant-dev-documents`

### CloudFront
- Distribution ID: `EL8L41G6CQJCD`
- Domain: `dq9tlzfsf1veq.cloudfront.net`

### Bedrock
- Knowledge Base ID: `PQB7MB5ORO`
- Data Source ID: `YUAUID9BJN`

### IAM Roles
- `ai-assistant-lambda-chat-execution-role`
- `ai-assistant-lambda-document-execution-role`
- `ai-assistant-lambda-admin-execution-role`
- `ai-assistant-lambda-kb-monitor-execution-role`
- `ai-assistant-api-gateway-cloudwatch-role`
- `ai-assistant-dev-bedrock-kb-role`
- `ai-assistant-monitoring-metrics-role`
- `ai-assistant-cloudwatch-sns-role`

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   # Verify AWS profile
   aws --profile aidlc_main sts get-caller-identity
   ```

2. **Permission Errors**
   - Ensure the AWS profile has read access to all services
   - Check IAM permissions for the user/role

3. **Resource Not Found**
   - Verify the resource exists in the AWS Console
   - Check if the resource is in the correct region (us-west-2)
   - Update Terraform documentation if resource has changed

### Manual Verification

You can manually verify specific resources:

```bash
# Check Lambda function
aws --profile aidlc_main lambda get-function --function-name ai-assistant-chat-endpoints

# Check API Gateway
aws --profile aidlc_main apigateway get-rest-api --rest-api-id jpt8wzkowd

# Check S3 bucket
aws --profile aidlc_main s3api head-bucket --bucket ai-assistant-dev-documents-993738bb

# Check Cognito User Pool
aws --profile aidlc_main cognito-idp describe-user-pool --user-pool-id us-west-2_FLJTm8Xt8
```

## Maintenance

### Regular Validation

Run the validation script regularly to ensure documentation stays accurate:

```bash
# Weekly validation (recommended)
./validate-terraform-docs.sh

# Generate report for review
./generate-validation-report.sh
```

### Updating Documentation

When AWS resources change:

1. Run validation to identify discrepancies
2. Update Terraform files to match current AWS state
3. Re-run validation to confirm accuracy
4. Commit updated documentation

### Automation

Consider setting up automated validation:

```bash
# Add to cron for weekly validation
0 9 * * 1 /path/to/validate-terraform-docs.sh > /path/to/validation.log 2>&1
```

## Security Considerations

- Scripts only perform read operations on AWS resources
- No sensitive data is exposed in validation output
- AWS credentials are handled through standard AWS CLI configuration
- Validation logs should be reviewed for any sensitive information before sharing

## Support

For issues with validation scripts:

1. Check AWS CLI configuration and permissions
2. Verify all prerequisites are met
3. Review the validation output for specific error messages
4. Manually verify problematic resources using AWS CLI or Console