/*
 * ============================================================================
 * WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT
 * ============================================================================
 * 
 * This Terraform configuration is for documentation purposes only.
 * It reflects the current state of AWS Bedrock infrastructure deployed via AWS CLI.
 * 
 * DO NOT RUN: terraform plan, terraform apply, or terraform destroy
 * 
 * For deployments, use AWS CLI commands as specified in deployment-workflow.md
 * ============================================================================
 */

# Knowledge Base Outputs
# Based on actual deployed Knowledge Base: PQB7MB5ORO

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
  value       = var.knowledge_base_name
}

output "knowledge_base_status" {
  description = "Status of the Knowledge Base (documentation only)"
  value       = "ACTIVE"
}

# Data Source Outputs
# Based on actual deployed data source: YUAUID9BJN

output "data_source_id" {
  description = "ID of the S3 data source (actual: YUAUID9BJN)"
  value       = "YUAUID9BJN"
}

output "data_source_arn" {
  description = "ARN of the S3 data source"
  value       = "arn:aws:bedrock:us-west-2:254539707041:knowledge-base/PQB7MB5ORO/data-source/YUAUID9BJN"
}

output "data_source_name" {
  description = "Name of the S3 data source"
  value       = var.data_source_name
}

output "data_source_status" {
  description = "Status of the data source (documentation only)"
  value       = "AVAILABLE"
}

# OpenSearch Serverless Outputs
output "opensearch_collection_id" {
  description = "ID of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.knowledge_base_collection.id
}

output "opensearch_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.knowledge_base_collection.arn
}

output "opensearch_collection_endpoint" {
  description = "Endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.knowledge_base_collection.collection_endpoint
}

output "opensearch_dashboard_endpoint" {
  description = "Dashboard endpoint of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.knowledge_base_collection.dashboard_endpoint
}

# IAM Role Outputs
output "knowledge_base_role_arn" {
  description = "ARN of the Knowledge Base service role (actual: ai-assistant-dev-bedrock-kb-role)"
  value       = var.knowledge_base_role_arn
}

output "knowledge_base_role_name" {
  description = "Name of the Knowledge Base service role"
  value       = "ai-assistant-dev-bedrock-kb-role"
}

# Vector Configuration Outputs
output "embedding_model_arn" {
  description = "ARN of the embedding model used for vector generation"
  value       = var.embedding_model_arn
}

output "vector_index_name" {
  description = "Name of the vector index in OpenSearch"
  value       = var.vector_index_name
}

output "chunking_configuration" {
  description = "Document chunking configuration"
  value = {
    strategy           = var.chunking_strategy
    max_tokens         = var.max_tokens_per_chunk
    overlap_percentage = var.chunk_overlap_percentage
  }
}

# S3 Configuration Outputs
output "s3_bucket_arn" {
  description = "ARN of the S3 bucket used as data source"
  value       = var.s3_bucket_arn
}

output "s3_inclusion_prefixes" {
  description = "S3 prefixes included in the knowledge base"
  value       = var.s3_inclusion_prefixes
}

# Deployment Information
output "deployment_info" {
  description = "Information about the deployment method and status"
  value = {
    deployment_method = "aws-cli"
    terraform_purpose = "documentation-only"
    last_updated      = "2025-01-09"
    region            = var.aws_region
    account_id        = var.aws_account_id
  }
}