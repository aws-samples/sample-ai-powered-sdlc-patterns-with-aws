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

# Outputs for Document Upload Lambda Function (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-document-upload

output "lambda_function_arn" {
  description = "ARN of the document upload Lambda function"
  value       = aws_lambda_function.document_upload.arn
}

output "lambda_function_name" {
  description = "Name of the document upload Lambda function"
  value       = aws_lambda_function.document_upload.function_name
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the document upload Lambda function"
  value       = aws_lambda_function.document_upload.invoke_arn
}