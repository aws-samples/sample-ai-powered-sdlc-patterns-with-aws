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

# Outputs for Chat Handler Lambda Function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-chat-endpoints

output "chat_handler_function_name" {
  description = "Name of the chat handler Lambda function"
  value       = aws_lambda_function.chat_handler.function_name
}

output "chat_handler_function_arn" {
  description = "ARN of the chat handler Lambda function"
  value       = aws_lambda_function.chat_handler.arn
}

output "chat_handler_invoke_arn" {
  description = "Invoke ARN of the chat handler Lambda function"
  value       = aws_lambda_function.chat_handler.invoke_arn
}

output "chat_handler_qualified_arn" {
  description = "Qualified ARN of the chat handler Lambda function"
  value       = aws_lambda_function.chat_handler.qualified_arn
}

output "chat_handler_role_arn" {
  description = "ARN of the chat handler IAM role"
  value       = aws_iam_role.chat_handler_role.arn
}

output "chat_handler_log_group_name" {
  description = "Name of the chat handler CloudWatch log group"
  value       = aws_cloudwatch_log_group.chat_handler.name
}