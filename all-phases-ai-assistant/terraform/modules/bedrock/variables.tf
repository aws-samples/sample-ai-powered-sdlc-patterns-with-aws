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

# Knowledge Base Configuration Variables
# Based on actual deployed Knowledge Base: PQB7MB5ORO

variable "knowledge_base_name" {
  description = "Name of the Bedrock Knowledge Base (actual: ai-assistant-knowledge-base)"
  type        = string
  default     = "ai-assistant-knowledge-base"
}

variable "knowledge_base_description" {
  description = "Description of the Bedrock Knowledge Base"
  type        = string
  default     = "AI Assistant Knowledge Base for document retrieval and generation"
}

variable "knowledge_base_role_arn" {
  description = "IAM role ARN for Bedrock Knowledge Base service (actual: ai-assistant-dev-bedrock-kb-role)"
  type        = string
  default     = "arn:aws:iam::254539707041:role/ai-assistant-dev-bedrock-kb-role"
}

# Embedding Model Configuration
variable "embedding_model_arn" {
  description = "ARN of the embedding model for vector generation"
  type        = string
  default     = "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v1"
}

# Data Source Configuration Variables
# Based on actual deployed data source: YUAUID9BJN

variable "data_source_name" {
  description = "Name of the S3 data source (actual: ai-assistant-dev-s3-data-source)"
  type        = string
  default     = "ai-assistant-dev-s3-data-source"
}

variable "data_source_description" {
  description = "Description of the S3 data source"
  type        = string
  default     = "S3 data source for AI Assistant documents"
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 bucket containing documents (actual: ai-assistant-dev-documents-993738bb)"
  type        = string
  default     = "arn:aws:s3:::ai-assistant-dev-documents-993738bb"
}

variable "s3_inclusion_prefixes" {
  description = "S3 prefixes to include in the knowledge base"
  type        = list(string)
  default     = ["documents/"]
}

variable "bucket_owner_account_id" {
  description = "AWS account ID that owns the S3 bucket"
  type        = string
  default     = "254539707041"
}

# Vector Ingestion Configuration
variable "chunking_strategy" {
  description = "Strategy for chunking documents"
  type        = string
  default     = "FIXED_SIZE"
}

variable "max_tokens_per_chunk" {
  description = "Maximum tokens per document chunk"
  type        = number
  default     = 300
}

variable "chunk_overlap_percentage" {
  description = "Percentage overlap between chunks"
  type        = number
  default     = 20
}

# OpenSearch Serverless Configuration
variable "opensearch_collection_name" {
  description = "Name of the OpenSearch Serverless collection"
  type        = string
  default     = "ai-assistant-knowledge-base-collection"
}

variable "opensearch_collection_description" {
  description = "Description of the OpenSearch Serverless collection"
  type        = string
  default     = "Vector store for AI Assistant Knowledge Base"
}

variable "opensearch_collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  type        = string
  default     = "arn:aws:aoss:us-west-2:254539707041:collection/ai-assistant-knowledge-base-collection"
}

variable "vector_index_name" {
  description = "Name of the vector index in OpenSearch"
  type        = string
  default     = "bedrock-knowledge-base-default-index"
}

variable "vector_field_name" {
  description = "Name of the vector field in OpenSearch"
  type        = string
  default     = "bedrock-knowledge-base-default-vector"
}

variable "text_field_name" {
  description = "Name of the text field in OpenSearch"
  type        = string
  default     = "AMAZON_BEDROCK_TEXT_CHUNK"
}

variable "metadata_field_name" {
  description = "Name of the metadata field in OpenSearch"
  type        = string
  default     = "AMAZON_BEDROCK_METADATA"
}

# Common Tags
variable "tags" {
  description = "Tags to apply to all Bedrock resources"
  type        = map(string)
  default = {
    Project     = "ai-assistant"
    Environment = "dev"
    Service     = "bedrock"
    ManagedBy   = "aws-cli"
    Purpose     = "documentation-only"
  }
}

# AWS Region and Account
variable "aws_region" {
  description = "AWS region for Bedrock resources"
  type        = string
  default     = "us-west-2"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
  default     = "254539707041"
}