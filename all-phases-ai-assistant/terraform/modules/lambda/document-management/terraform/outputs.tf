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

# Outputs for Document Management Lambda Function Terraform Module (DOCUMENTATION ONLY)
# ACTUAL DEPLOYED FUNCTION: ai-assistant-dev-document-management

output "lambda_function_arn" {
  description = "ARN of the document management Lambda function"
  value       = aws_lambda_function.document_management.arn
}

output "lambda_function_name" {
  description = "Name of the document management Lambda function"
  value       = aws_lambda_function.document_management.function_name
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the document management Lambda function"
  value       = aws_lambda_function.document_management.invoke_arn
}

output "documents_id_resource_id" {
  description = "ID of the /documents/{id} API Gateway resource"
  value       = aws_api_gateway_resource.documents_id.id
}

output "documents_status_resource_id" {
  description = "ID of the /documents/status API Gateway resource"
  value       = aws_api_gateway_resource.documents_status.id
}