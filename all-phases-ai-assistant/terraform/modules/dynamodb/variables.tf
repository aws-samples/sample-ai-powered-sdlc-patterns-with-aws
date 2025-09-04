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

variable "project_name" {
  description = "Name of the project (documentation only)"
  type        = string
  default     = "ai-assistant"
}

variable "environment" {
  description = "Environment name (documentation only)"
  type        = string
  default     = "dev"
}

variable "table_name" {
  description = "Actual DynamoDB table name in AWS"
  type        = string
  default     = "ai-assistant-dev-documents"
}

variable "tags" {
  description = "Common tags for DynamoDB resources (documentation only)"
  type        = map(string)
  default = {
    Project     = "ai-assistant"
    Environment = "dev"
    ManagedBy   = "aws-cli"
    Purpose     = "documentation-only"
  }
}