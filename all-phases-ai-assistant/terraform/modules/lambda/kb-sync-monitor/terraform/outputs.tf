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

# Outputs for Knowledge Base Sync Monitor Lambda Function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-kb-sync-monitor

output "lambda_function_arn" {
  description = "ARN of the Knowledge Base sync monitor Lambda function"
  value       = aws_lambda_function.kb_sync_monitor.arn
}

output "lambda_function_name" {
  description = "Name of the Knowledge Base sync monitor Lambda function"
  value       = aws_lambda_function.kb_sync_monitor.function_name
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for the Lambda function"
  value       = aws_cloudwatch_log_group.kb_sync_monitor_logs.name
}

output "dashboard_url" {
  description = "URL of the CloudWatch dashboard for Knowledge Base monitoring"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.kb_monitoring.dashboard_name}"
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule that triggers the monitoring function"
  value       = aws_cloudwatch_event_rule.kb_sync_monitor_schedule.arn
}