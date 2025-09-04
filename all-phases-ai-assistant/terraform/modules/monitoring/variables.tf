/*
 * ============================================================================
 * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
 * ============================================================================
 * 
 * This Terraform configuration is for documentation purposes only.
 * It reflects the current state of AWS monitoring infrastructure deployed via AWS CLI.
 * 
 * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
 * 
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

# Variables for CloudWatch Monitoring Module - ACTUAL DEPLOYED VALUES

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

variable "aws_region" {
  description = "AWS region (documentation only)"
  type        = string
  default     = "us-west-2"
}

variable "alert_email_addresses" {
  description = "List of email addresses to receive alerts (documentation only)"
  type        = list(string)
  default     = []
}

# Actual deployed log retention values
variable "lambda_log_retention_days" {
  description = "Number of days to retain Lambda CloudWatch logs (actual: 14 days)"
  type        = number
  default     = 14
}

variable "custom_log_retention_days" {
  description = "Number of days to retain custom CloudWatch logs (actual: 30 days)"
  type        = number
  default     = 30
}

variable "api_gateway_log_retention_days" {
  description = "Number of days to retain API Gateway logs (actual: 14 days)"
  type        = number
  default     = 14
}

# Actual deployed Bedrock model
variable "bedrock_model_id" {
  description = "Bedrock model ID for monitoring (actual deployed model)"
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20241022-v2:0"
}

# Actual deployed Lambda function names
variable "chat_lambda_function_name" {
  description = "Name of the chat Lambda function (actual deployed name)"
  type        = string
  default     = "ai-assistant-chat-endpoints"
}

variable "document_lambda_function_name" {
  description = "Name of the document management Lambda function (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-document-management"
}

variable "admin_lambda_function_name" {
  description = "Name of the admin Lambda function (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-admin-management"
}

variable "document_upload_lambda_function_name" {
  description = "Name of the document upload Lambda function (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-document-upload"
}

variable "kb_sync_monitor_lambda_function_name" {
  description = "Name of the KB sync monitor Lambda function (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-kb-sync-monitor"
}

variable "monitoring_metrics_lambda_function_name" {
  description = "Name of the monitoring metrics Lambda function (actual deployed name)"
  type        = string
  default     = "ai-assistant-monitoring-metrics"
}

# Actual deployed DynamoDB table
variable "documents_table_name" {
  description = "Name of the DynamoDB documents table (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-documents"
}

# Actual deployed Bedrock Knowledge Base
variable "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base (actual deployed ID)"
  type        = string
  default     = "PQB7MB5ORO"
}

variable "knowledge_base_name" {
  description = "Name of the Bedrock Knowledge Base (actual deployed name)"
  type        = string
  default     = "ai-assistant-knowledge-base"
}

# Actual deployed S3 buckets
variable "documents_s3_bucket_name" {
  description = "Name of the S3 bucket for documents (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-documents-993738bb"
}

variable "frontend_s3_bucket_name" {
  description = "Name of the S3 bucket for frontend (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-frontend-e5e9acfe"
}

# Actual deployed SNS topic
variable "sns_topic_name" {
  description = "Name of the SNS topic for alerts (actual deployed name)"
  type        = string
  default     = "ai-assistant-alerts"
}

# Actual deployed EventBridge rules
variable "kb_sync_monitor_rule_name" {
  description = "Name of the KB sync monitor EventBridge rule (actual deployed name)"
  type        = string
  default     = "ai-assistant-dev-kb-sync-monitor-schedule"
}

variable "metrics_collection_rule_name" {
  description = "Name of the metrics collection EventBridge rule (actual deployed name)"
  type        = string
  default     = "ai-assistant-metrics-collection"
}

# Actual deployed CloudWatch dashboards
variable "dashboard_name" {
  description = "Name of the CloudWatch dashboard (actual deployed name)"
  type        = string
  default     = "ai-assistant-knowledge-base-dashboard"
}