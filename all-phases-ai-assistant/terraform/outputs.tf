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

# Outputs for AI Assistant infrastructure
# DOCUMENTATION ONLY - Values reflect actual deployed resources

# Bedrock Module Outputs (Actual deployed values)
output "bedrock_knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base from module (actual: PQB7MB5ORO)"
  value       = module.bedrock.knowledge_base_id
}

output "bedrock_knowledge_base_arn" {
  description = "ARN of the Bedrock Knowledge Base from module"
  value       = module.bedrock.knowledge_base_arn
}

output "bedrock_knowledge_base_name" {
  description = "Name of the Bedrock Knowledge Base from module"
  value       = module.bedrock.knowledge_base_name
}

output "bedrock_data_source_id" {
  description = "ID of the Bedrock data source from module (actual: YUAUID9BJN)"
  value       = module.bedrock.data_source_id
}

output "bedrock_data_source_name" {
  description = "Name of the Bedrock data source from module"
  value       = module.bedrock.data_source_name
}

output "bedrock_opensearch_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection from module"
  value       = module.bedrock.opensearch_collection_arn
}

output "bedrock_opensearch_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection from module"
  value       = module.bedrock.opensearch_collection_endpoint
}

output "bedrock_embedding_model_arn" {
  description = "ARN of the embedding model used by Bedrock from module"
  value       = module.bedrock.embedding_model_arn
}

output "bedrock_chunking_configuration" {
  description = "Document chunking configuration from module"
  value       = module.bedrock.chunking_configuration
}

output "bedrock_deployment_info" {
  description = "Bedrock deployment information from module"
  value       = module.bedrock.deployment_info
}

# Legacy Knowledge Base Outputs (Actual deployed values - for backward compatibility)
output "knowledge_base_id" {
  description = "ID of the Bedrock Knowledge Base (actual: PQB7MB5ORO)"
  value       = "PQB7MB5ORO"
}

output "knowledge_base_arn" {
  description = "ARN of the Bedrock Knowledge Base"
  value       = "arn:aws:bedrock:us-west-2:254539707041:knowledge-base/PQB7MB5ORO"
}

output "knowledge_base_name" {
  description = "Name of the Bedrock Knowledge Base"
  value       = "ai-assistant-knowledge-base"
}

# Data Source Outputs (Actual deployed values)
output "data_source_id" {
  description = "ID of the Bedrock data source (actual: YUAUID9BJN)"
  value       = "YUAUID9BJN"
}

output "data_source_name" {
  description = "Name of the Bedrock data source"
  value       = "ai-assistant-dev-s3-data-source"
}

# S3 Outputs (Actual deployed values)
output "documents_bucket_name" {
  description = "Name of the S3 bucket for documents (actual: ai-assistant-dev-documents-993738bb)"
  value       = "ai-assistant-dev-documents-993738bb"
}

output "documents_bucket_arn" {
  description = "ARN of the S3 bucket for documents"
  value       = "arn:aws:s3:::ai-assistant-dev-documents-993738bb"
}

output "documents_bucket_region" {
  description = "Region of the S3 bucket"
  value       = "us-west-2"
}

# OpenSearch Outputs
output "opensearch_collection_id" {
  description = "ID of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb_collection.id
}

output "opensearch_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb_collection.arn
}

output "opensearch_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb_collection.collection_endpoint
}

output "opensearch_dashboard_endpoint" {
  description = "Dashboard endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.kb_collection.dashboard_endpoint
}

# IAM Outputs
output "bedrock_kb_role_arn" {
  description = "ARN of the IAM role for Bedrock Knowledge Base"
  value       = aws_iam_role.bedrock_kb_role.arn
}

output "bedrock_kb_role_name" {
  description = "Name of the IAM role for Bedrock Knowledge Base"
  value       = aws_iam_role.bedrock_kb_role.name
}

# Configuration Outputs for Lambda Functions
output "knowledge_base_config" {
  description = "Configuration object for Knowledge Base integration"
  value = {
    knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
    data_source_id    = aws_bedrockagent_data_source.s3_source.data_source_id
    embedding_model   = var.embedding_model_arn
    s3_bucket        = aws_s3_bucket.documents.id
    s3_prefix        = var.documents_prefix
  }
  sensitive = false
}

# Environment Information
output "environment_info" {
  description = "Environment configuration information"
  value = {
    environment = var.environment
    region      = var.aws_region
    project     = var.project_name
  }
}

# Cognito outputs (Actual deployed values)
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool (actual: us-west-2_FLJTm8Xt8)"
  value       = "us-west-2_FLJTm8Xt8"
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito User Pool Client (actual: 3gr32ei5n768d88h02klhmpn8v)"
  value       = "3gr32ei5n768d88h02klhmpn8v"
}

output "cognito_user_pool_domain" {
  description = "Domain of the Cognito User Pool (actual: ai-assistant-auth-3gja49wa)"
  value       = "ai-assistant-auth-3gja49wa"
}

# API Gateway outputs (Actual deployed values)
output "api_gateway_id" {
  description = "ID of the API Gateway (actual: jpt8wzkowd)"
  value       = "jpt8wzkowd"
}

output "api_gateway_invoke_url" {
  description = "Invoke URL of the API Gateway"
  value       = "https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev"
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the API Gateway"
  value       = module.api_gateway.api_gateway_execution_arn
}

output "api_gateway_authorizer_id" {
  description = "ID of the API Gateway Cognito authorizer"
  value       = module.api_gateway.authorizer_id
}

output "api_gateway_chat_resource_id" {
  description = "ID of the API Gateway chat resource"
  value       = module.api_gateway.chat_resource_id
}

# IAM outputs
output "lambda_chat_execution_role_arn" {
  description = "ARN of the Lambda chat execution role"
  value       = module.iam.lambda_chat_execution_role_arn
}

output "lambda_document_execution_role_arn" {
  description = "ARN of the Lambda document execution role"
  value       = module.iam.lambda_document_execution_role_arn
}

output "lambda_admin_execution_role_arn" {
  description = "ARN of the Lambda admin execution role"
  value       = module.iam.lambda_admin_execution_role_arn
}

# CloudFront outputs (Actual deployed values)
output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (actual: EL8L41G6CQJCD)"
  value       = "EL8L41G6CQJCD"
}

output "cloudfront_distribution_arn" {
  description = "CloudFront distribution ARN"
  value       = "arn:aws:cloudfront::254539707041:distribution/EL8L41G6CQJCD"
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (actual: dq9tlzfsf1veq.cloudfront.net)"
  value       = "dq9tlzfsf1veq.cloudfront.net"
}

output "cloudfront_url" {
  description = "Full CloudFront URL for the frontend"
  value       = "https://dq9tlzfsf1veq.cloudfront.net"
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend assets (actual: ai-assistant-dev-frontend-e5e9acfe)"
  value       = "ai-assistant-dev-frontend-e5e9acfe"
}

output "frontend_bucket_arn" {
  description = "S3 bucket ARN for frontend assets"
  value       = "arn:aws:s3:::ai-assistant-dev-frontend-e5e9acfe"
}

# Monitoring outputs
output "monitoring_dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = module.monitoring.dashboard_url
}

output "monitoring_sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = module.monitoring.sns_topic_arn
}

output "monitoring_alarm_arns" {
  description = "ARNs of all CloudWatch alarms"
  value       = module.monitoring.alarm_arns
}

output "monitoring_log_groups" {
  description = "CloudWatch log groups for monitoring"
  value = {
    knowledge_base_metrics = module.monitoring.knowledge_base_metrics_log_group
    admin_audit           = module.monitoring.admin_audit_log_group
    monitoring_lambda     = module.monitoring_metrics_lambda.log_group_name
  }
}

# DynamoDB outputs (Actual deployed values)
output "documents_table_name" {
  description = "Name of the DynamoDB documents table (actual: ai-assistant-dev-documents)"
  value       = "ai-assistant-dev-documents"
}

output "documents_table_arn" {
  description = "ARN of the DynamoDB documents table"
  value       = "arn:aws:dynamodb:us-west-2:254539707041:table/ai-assistant-dev-documents"
}

# Complete application configuration for frontend (Actual deployed values)
output "frontend_config" {
  description = "Complete configuration for React frontend"
  value = {
    # AWS Configuration
    aws_region = "us-west-2"
    
    # Cognito Configuration (Actual deployed values)
    cognito_user_pool_id     = "us-west-2_FLJTm8Xt8"
    cognito_user_pool_client_id = "3gr32ei5n768d88h02klhmpn8v"
    cognito_user_pool_domain = "ai-assistant-auth-3gja49wa"
    
    # API Configuration (Actual deployed values)
    api_gateway_url = "https://jpt8wzkowd.execute-api.us-west-2.amazonaws.com/dev"
    
    # CloudFront Configuration (Actual deployed values)
    cloudfront_url = "https://dq9tlzfsf1veq.cloudfront.net"
    
    # Environment
    environment = "dev"
    project_name = "ai-assistant"
  }
  sensitive = false
}