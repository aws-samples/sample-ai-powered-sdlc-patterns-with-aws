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

# Outputs for IAM module - DOCUMENTATION ONLY

# ============================================================================
# LAMBDA EXECUTION ROLE OUTPUTS
# ============================================================================

output "lambda_chat_execution_role_arn" {
  description = "ARN of the Lambda chat execution role (actual: arn:aws:iam::254539707041:role/ai-assistant-lambda-chat-execution-role)"
  value       = aws_iam_role.lambda_chat_execution.arn
}

output "lambda_chat_execution_role_name" {
  description = "Name of the Lambda chat execution role"
  value       = aws_iam_role.lambda_chat_execution.name
}

output "lambda_document_execution_role_arn" {
  description = "ARN of the Lambda document execution role"
  value       = aws_iam_role.lambda_document_execution.arn
}

output "lambda_document_execution_role_name" {
  description = "Name of the Lambda document execution role"
  value       = aws_iam_role.lambda_document_execution.name
}

output "lambda_admin_execution_role_arn" {
  description = "ARN of the Lambda admin execution role"
  value       = aws_iam_role.lambda_admin_execution.arn
}

output "lambda_admin_execution_role_name" {
  description = "Name of the Lambda admin execution role"
  value       = aws_iam_role.lambda_admin_execution.name
}

output "lambda_kb_monitor_execution_role_arn" {
  description = "ARN of the Lambda Knowledge Base monitor execution role"
  value       = aws_iam_role.lambda_kb_monitor_execution.arn
}

output "lambda_kb_monitor_execution_role_name" {
  description = "Name of the Lambda Knowledge Base monitor execution role"
  value       = aws_iam_role.lambda_kb_monitor_execution.name
}

# Chat handler role outputs
output "chat_handler_role_arn" {
  description = "ARN of the chat handler role (actual: arn:aws:iam::254539707041:role/ai-assistant-chat-handler-role)"
  value       = aws_iam_role.chat_handler_role.arn
}

output "chat_handler_role_name" {
  description = "Name of the chat handler role"
  value       = aws_iam_role.chat_handler_role.name
}

# ============================================================================
# SERVICE ROLE OUTPUTS
# ============================================================================

# API Gateway CloudWatch role outputs
output "api_gateway_cloudwatch_role_arn" {
  description = "ARN of the API Gateway CloudWatch role (actual: arn:aws:iam::254539707041:role/ai-assistant-api-gateway-cloudwatch-role)"
  value       = aws_iam_role.api_gateway_cloudwatch.arn
}

output "api_gateway_cloudwatch_role_name" {
  description = "Name of the API Gateway CloudWatch role"
  value       = aws_iam_role.api_gateway_cloudwatch.name
}

# Bedrock Knowledge Base service role outputs
output "bedrock_kb_service_role_arn" {
  description = "ARN of the Bedrock Knowledge Base service role (actual: arn:aws:iam::254539707041:role/ai-assistant-dev-bedrock-kb-role)"
  value       = aws_iam_role.bedrock_kb_service.arn
}

output "bedrock_kb_service_role_name" {
  description = "Name of the Bedrock Knowledge Base service role"
  value       = aws_iam_role.bedrock_kb_service.name
}

# ============================================================================
# MONITORING ROLE OUTPUTS
# ============================================================================

# Monitoring metrics role outputs
output "monitoring_metrics_role_arn" {
  description = "ARN of the monitoring metrics role (actual: arn:aws:iam::254539707041:role/ai-assistant-monitoring-metrics-role)"
  value       = aws_iam_role.monitoring_metrics.arn
}

output "monitoring_metrics_role_name" {
  description = "Name of the monitoring metrics role"
  value       = aws_iam_role.monitoring_metrics.name
}

# CloudWatch SNS role outputs
output "cloudwatch_sns_role_arn" {
  description = "ARN of the CloudWatch SNS role (actual: arn:aws:iam::254539707041:role/ai-assistant-cloudwatch-sns-role)"
  value       = aws_iam_role.cloudwatch_sns.arn
}

output "cloudwatch_sns_role_name" {
  description = "Name of the CloudWatch SNS role"
  value       = aws_iam_role.cloudwatch_sns.name
}