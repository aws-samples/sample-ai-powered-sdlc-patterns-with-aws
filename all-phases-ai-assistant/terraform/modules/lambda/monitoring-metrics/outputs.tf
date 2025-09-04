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

# Outputs for Monitoring Metrics Lambda Module (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-monitoring-metrics

output "function_name" {
  description = "Name of the monitoring metrics Lambda function"
  value       = aws_lambda_function.monitoring_metrics.function_name
}

output "function_arn" {
  description = "ARN of the monitoring metrics Lambda function"
  value       = aws_lambda_function.monitoring_metrics.arn
}

output "role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.monitoring_metrics_role.arn
}

output "log_group_name" {
  description = "Name of the Lambda log group"
  value       = aws_cloudwatch_log_group.monitoring_metrics_logs.name
}