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

# Variables for Chat Handler Lambda Function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-chat-endpoints

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"
}

variable "knowledge_base_id" {
  description = "ID of the Amazon Bedrock Knowledge Base"
  type        = string
}

variable "log_level" {
  description = "Log level for the Lambda function"
  type        = string
  default     = "INFO"
  
  validation {
    condition     = contains(["DEBUG", "INFO", "WARN", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARN, ERROR."
  }
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
  
  validation {
    condition     = var.aws_region == "us-west-2"
    error_message = "AWS region must be us-west-2 as per project requirements."
  }
}

variable "enable_advanced_rag" {
  description = "Enable advanced RAG configuration features"
  type        = string
  default     = "true"
  
  validation {
    condition     = contains(["true", "false"], var.enable_advanced_rag)
    error_message = "Enable advanced RAG must be either 'true' or 'false'."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "ai-assistant"
}

variable "api_gateway_id" {
  description = "ID of the API Gateway REST API"
  type        = string
}

variable "api_gateway_chat_resource_id" {
  description = "ID of the /chat resource in API Gateway"
  type        = string
}

variable "api_gateway_authorizer_id" {
  description = "ID of the Cognito authorizer in API Gateway"
  type        = string
}

variable "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  type        = string
}

variable "documents_table_name" {
  description = "Name of the DynamoDB table for documents and conversations"
  type        = string
}

variable "documents_table_arn" {
  description = "ARN of the DynamoDB table for documents and conversations"
  type        = string
}

variable "cloudfront_url" {
  description = "CloudFront distribution URL for CORS configuration"
  type        = string
}