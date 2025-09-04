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

# Outputs for CloudWatch Monitoring Module - ACTUAL DEPLOYED VALUES

# Actual deployed SNS topic ARN
output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts (actual deployed ARN)"
  value       = "arn:aws:sns:us-west-2:254539707041:ai-assistant-alerts"
}

# Actual CloudWatch dashboard URL
output "dashboard_url" {
  description = "URL of the CloudWatch dashboard (actual deployed dashboard)"
  value       = "https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#dashboards:name=ai-assistant-knowledge-base-dashboard"
}

# Actual deployed log group names
output "knowledge_base_metrics_log_group" {
  description = "Name of the Knowledge Base metrics log group (actual deployed)"
  value       = "/aws/ai-assistant/knowledge-base-metrics"
}

output "admin_audit_log_group" {
  description = "Name of the admin audit log group (actual deployed)"
  value       = "/aws/ai-assistant/admin-audit"
}

output "api_gateway_log_group" {
  description = "Name of the API Gateway log group (actual deployed)"
  value       = "/aws/apigateway/ai-assistant"
}

output "cloudfront_log_group" {
  description = "Name of the CloudFront log group (actual deployed)"
  value       = "/aws/cloudfront/ai-assistant-dev"
}

# Lambda function log groups
output "lambda_log_groups" {
  description = "Names of all Lambda function log groups (actual deployed)"
  value = {
    chat_endpoints        = "/aws/lambda/ai-assistant-chat-endpoints"
    admin_management      = "/aws/lambda/ai-assistant-dev-admin-management"
    document_management   = "/aws/lambda/ai-assistant-dev-document-management"
    document_upload       = "/aws/lambda/ai-assistant-dev-document-upload"
    kb_sync_monitor      = "/aws/lambda/ai-assistant-dev-kb-sync-monitor"
    monitoring_metrics   = "/aws/lambda/ai-assistant-monitoring-metrics"
  }
}

# Actual deployed IAM role ARN
output "cloudwatch_sns_role_arn" {
  description = "ARN of the CloudWatch SNS role (actual deployed ARN)"
  value       = "arn:aws:iam::254539707041:role/ai-assistant-cloudwatch-sns-role"
}

# EventBridge rules
output "eventbridge_rules" {
  description = "Names of EventBridge rules (actual deployed)"
  value = {
    kb_sync_monitor_schedule = "ai-assistant-dev-kb-sync-monitor-schedule"
    metrics_collection      = "ai-assistant-metrics-collection"
  }
}

# Actual deployed alarm names (documentation reference)
output "alarm_names" {
  description = "Names of all CloudWatch alarms (actual deployed)"
  value = {
    bedrock_high_latency           = "ai-assistant-bedrock-high-latency"
    bedrock_errors                 = "ai-assistant-bedrock-errors"
    chat_lambda_errors             = "ai-assistant-chat-lambda-errors"
    document_lambda_errors         = "ai-assistant-document-lambda-errors"
    dynamodb_throttles             = "ai-assistant-dynamodb-throttles"
    kb_query_success_rate          = "ai-assistant-kb-query-success-rate"
    kb_response_time               = "ai-assistant-kb-response-time"
    kb_ingestion_failures          = "ai-assistant-kb-ingestion-failures"
    kb_query_latency               = "ai-assistant-kb-query-latency"
    kb_monitor_function_errors     = "ai-assistant-dev-kb-monitor-function-errors"
    kb_ingestion_failure_rate      = "ai-assistant-dev-kb-ingestion-failure-rate"
  }
}

# Log retention policies (actual deployed values)
output "log_retention_policies" {
  description = "Log retention policies for different log groups (actual deployed)"
  value = {
    lambda_functions     = "14 days"
    custom_metrics      = "30 days"
    api_gateway         = "14 days"
    cloudfront          = "30 days"
    admin_audit         = "30 days"
    kb_metrics          = "30 days"
  }
}