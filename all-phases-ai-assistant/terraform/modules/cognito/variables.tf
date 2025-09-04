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

# Variables for Cognito module - ACTUAL DEPLOYED VALUES

variable "project_name" {
  description = "Name of the project (actual deployed value)"
  type        = string
  default     = "ai-assistant"  # Matches actual deployed resources
}

# Note: OAuth callback/logout URLs not configured in deployed client
variable "callback_urls" {
  description = "List of callback URLs for the Cognito client (not used in deployed config)"
  type        = list(string)
  default     = []  # OAuth not enabled in deployed client
}

variable "logout_urls" {
  description = "List of logout URLs for the Cognito client (not used in deployed config)"
  type        = list(string)
  default     = []  # OAuth not enabled in deployed client
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {
    Environment = "dev"
    Project     = "AI-Assistant"
    ManagedBy   = "AWS-CLI"  # Reflects actual deployment method
  }
}

variable "aws_region" {
  description = "AWS region (actual deployed region)"
  type        = string
  default     = "us-west-2"  # Actual deployed region
}

# Note: IAM roles not configured for user groups in deployed infrastructure
variable "admin_role_arn" {
  description = "ARN of the IAM role for admin users (not configured in deployed groups)"
  type        = string
  default     = ""  # Not used in deployed configuration
}

variable "user_role_arn" {
  description = "ARN of the IAM role for standard users (not configured in deployed groups)"
  type        = string
  default     = ""  # Not used in deployed configuration
}

# Additional variables reflecting actual deployed configuration
variable "user_pool_id" {
  description = "Actual deployed User Pool ID"
  type        = string
  default     = "us-west-2_FLJTm8Xt8"
}

variable "client_id" {
  description = "Actual deployed User Pool Client ID"
  type        = string
  default     = "3gr32ei5n768d88h02klhmpn8v"
}

variable "domain_name" {
  description = "Actual deployed Cognito domain name"
  type        = string
  default     = "ai-assistant-auth-3gja49wa"
}