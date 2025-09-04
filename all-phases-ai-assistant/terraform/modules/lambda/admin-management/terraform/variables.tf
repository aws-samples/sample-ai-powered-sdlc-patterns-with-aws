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

# Variables for Admin Management Lambda Function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-admin-management

variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  type        = string
}

variable "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  type        = string
}

variable "data_source_id" {
  description = "ID of the Knowledge Base data source"
  type        = string
}

variable "documents_table_name" {
  description = "Name of the DynamoDB documents table"
  type        = string
}

variable "api_gateway_id" {
  description = "ID of the API Gateway"
  type        = string
}

variable "api_gateway_root_resource_id" {
  description = "Root resource ID of the API Gateway"
  type        = string
}

variable "api_gateway_authorizer_id" {
  description = "ID of the API Gateway Cognito authorizer"
  type        = string
}

variable "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  type        = string
}

variable "log_level" {
  description = "Log level for the Lambda function"
  type        = string
  default     = "INFO"
}

variable "audit_log_group_name" {
  description = "Name of the CloudWatch log group for audit logging"
  type        = string
}

variable "metrics_log_group_name" {
  description = "Name of the CloudWatch log group for metrics logging"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}