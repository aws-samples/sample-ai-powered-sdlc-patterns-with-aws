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

# Outputs for Admin Management Lambda Function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-admin-management

output "lambda_function_arn" {
  description = "ARN of the admin management Lambda function"
  value       = aws_lambda_function.admin_management.arn
}

output "lambda_function_name" {
  description = "Name of the admin management Lambda function"
  value       = aws_lambda_function.admin_management.function_name
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the admin management Lambda function"
  value       = aws_lambda_function.admin_management.invoke_arn
}

output "admin_api_resource_id" {
  description = "ID of the admin API Gateway resource"
  value       = aws_api_gateway_resource.admin.id
}

output "admin_proxy_resource_id" {
  description = "ID of the admin proxy API Gateway resource"
  value       = aws_api_gateway_resource.admin_proxy.id
}