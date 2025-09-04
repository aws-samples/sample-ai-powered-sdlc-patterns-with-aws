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

# Variables for Knowledge Base Sync Monitor Lambda Function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-kb-sync-monitor

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
  description = "ARN of the IAM role for Lambda execution"
  type        = string
}

variable "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base"
  type        = string
}

variable "data_source_id" {
  description = "ID of the Bedrock Knowledge Base data source"
  type        = string
}

variable "documents_table_name" {
  description = "Name of the DynamoDB table storing document metadata"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of SNS topic for alarm notifications (optional)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}