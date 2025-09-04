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

# Outputs for API Gateway module - DEPLOYED VALUES

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = "jpt8wzkowd"  # Actual deployed API Gateway ID
}

output "api_gateway_arn" {
  description = "ARN of the API Gateway"
  value       = "arn:aws:apigateway:us-west-2::/restapis/jpt8wzkowd"  # Actual deployed API Gateway ARN
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = "arn:aws:execute-api:us-west-2:254539707041:jpt8wzkowd"  # Actual execution ARN
}

output "api_gateway_invoke_url" {
  description = "Invoke URL of the API Gateway"
  value       = "https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev"  # Actual deployed invoke URL
}

output "authorizer_id" {
  description = "ID of the Cognito authorizer"
  value       = "z8gap2"  # Actual deployed authorizer ID
}

output "chat_resource_id" {
  description = "ID of the chat resource"
  value       = "4ymylk"  # Actual deployed chat resource ID
}

output "chat_ask_resource_id" {
  description = "ID of the chat/ask resource"
  value       = "drpsmy"  # Actual deployed chat/ask resource ID
}

output "chat_stream_resource_id" {
  description = "ID of the chat/stream resource"
  value       = "mummfa"  # Actual deployed chat/stream resource ID
}

output "chat_history_resource_id" {
  description = "ID of the chat/history resource"
  value       = "4r974g"  # Actual deployed chat/history resource ID
}

output "documents_resource_id" {
  description = "ID of the documents resource"
  value       = "w4weo7"  # Actual deployed documents resource ID
}

output "documents_status_resource_id" {
  description = "ID of the documents/status resource"
  value       = "1zvznt"  # Actual deployed documents/status resource ID
}

output "documents_id_resource_id" {
  description = "ID of the documents/{id} resource"
  value       = "5ixqhj"  # Actual deployed documents/{id} resource ID
}

output "upload_resource_id" {
  description = "ID of the upload resource"
  value       = "6ixqhj"  # Actual deployed upload resource ID
}

output "admin_resource_id" {
  description = "ID of the admin resource"
  value       = "kkolty"  # Actual deployed admin resource ID
}

output "admin_proxy_resource_id" {
  description = "ID of the admin/{proxy+} resource"
  value       = "ng6vfm"  # Actual deployed admin/{proxy+} resource ID
}

output "root_resource_id" {
  description = "ID of the API Gateway root resource"
  value       = "44jglfjt1l"  # Actual deployed root resource ID
}