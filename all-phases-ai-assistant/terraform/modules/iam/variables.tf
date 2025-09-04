/*
 * ============================================================================
 * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
 * ============================================================================
 * 
 * This Terraform configuration is for documentation purposes only.
 * It reflects the current state of AWS IAM roles deployed via AWS CLI.
 * 
 * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
 * 
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

# Variables for IAM module - DOCUMENTATION ONLY

variable "project_name" {
  description = "Name of the project (actual value: ai-assistant)"
  type        = string
  default     = "ai-assistant"
}

variable "documents_bucket_arn" {
  description = "ARN of the S3 bucket for documents (actual: ai-assistant-dev-documents-993738bb)"
  type        = string
  default     = "arn:aws:s3:::ai-assistant-dev-documents-993738bb"
}

variable "documents_table_arn" {
  description = "ARN of the DynamoDB table for document metadata (actual: ai-assistant-dev-documents)"
  type        = string
  default     = "arn:aws:dynamodb:us-west-2:254539707041:table/ai-assistant-dev-documents"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}