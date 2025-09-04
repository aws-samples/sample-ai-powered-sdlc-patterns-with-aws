# Development environment configuration

aws_region  = "us-west-2"
environment = "dev"

# Project Configuration
project_name = "ai-assistant"

# Knowledge Base Configuration
knowledge_base_name        = "ai-assistant-dev-knowledge-base"
knowledge_base_description = "AI Assistant Knowledge Base for development environment"
embedding_model_arn        = "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v2:0"
embedding_dimensions       = 1024

# S3 Configuration
documents_bucket_name = "documents"
documents_prefix      = "documents/"

# OpenSearch Configuration
opensearch_collection_name = "ai-assistant-dev-kb-collection"
vector_index_name          = "ai-assistant-dev-index"

# Chunking Configuration
chunk_max_tokens         = 300
chunk_overlap_percentage = 20

# Additional Tags
additional_tags = {
  Owner       = "Development Team"
  CostCenter  = "Engineering"
  Environment = "dev"
}