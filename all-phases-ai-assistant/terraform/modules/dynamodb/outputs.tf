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
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

output "table_name" {
  description = "Actual DynamoDB table name"
  value       = "ai-assistant-dev-documents"
}

output "table_arn" {
  description = "Actual DynamoDB table ARN"
  value       = "arn:aws:dynamodb:us-west-2:254539707041:table/ai-assistant-dev-documents"
}

output "table_id" {
  description = "Actual DynamoDB table ID"
  value       = "ai-assistant-dev-documents"
}

output "gsi_name" {
  description = "Global Secondary Index name"
  value       = "GSI1"
}

output "gsi_arn" {
  description = "Global Secondary Index ARN"
  value       = "arn:aws:dynamodb:us-west-2:254539707041:table/ai-assistant-dev-documents/index/GSI1"
}

output "table_configuration" {
  description = "Table configuration details"
  value = {
    billing_mode = "PAY_PER_REQUEST"
    hash_key     = "PK"
    range_key    = "SK"
    status       = "ACTIVE"
    region       = "us-west-2"
  }
}