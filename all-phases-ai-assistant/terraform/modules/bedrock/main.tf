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

# Bedrock Knowledge Base
# Actual deployed resource: PQB7MB5ORO (ai-assistant-knowledge-base)
resource "aws_bedrock_knowledge_base" "ai_assistant_kb" {
  name        = var.knowledge_base_name
  description = var.knowledge_base_description
  role_arn    = var.knowledge_base_role_arn

  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = var.embedding_model_arn
    }
    type = "VECTOR"
  }

  storage_configuration {
    opensearch_serverless_configuration {
      collection_arn    = var.opensearch_collection_arn
      vector_index_name = var.vector_index_name
      field_mapping {
        vector_field   = var.vector_field_name
        text_field     = var.text_field_name
        metadata_field = var.metadata_field_name
      }
    }
    type = "OPENSEARCH_SERVERLESS"
  }

  tags = var.tags
}

# Bedrock Knowledge Base Data Source
# Actual deployed resource: YUAUID9BJN (ai-assistant-dev-s3-data-source)
resource "aws_bedrock_knowledge_base_data_source" "s3_data_source" {
  knowledge_base_id = aws_bedrock_knowledge_base.ai_assistant_kb.id
  name              = var.data_source_name
  description       = var.data_source_description

  data_source_configuration {
    s3_configuration {
      bucket_arn              = var.s3_bucket_arn
      inclusion_prefixes      = var.s3_inclusion_prefixes
      bucket_owner_account_id = var.bucket_owner_account_id
    }
    type = "S3"
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = var.chunking_strategy
      fixed_size_chunking_configuration {
        max_tokens         = var.max_tokens_per_chunk
        overlap_percentage = var.chunk_overlap_percentage
      }
    }
  }

  tags = var.tags
}

# OpenSearch Serverless Collection for Vector Store
# Note: This is managed by Bedrock Knowledge Base service
resource "aws_opensearchserverless_collection" "knowledge_base_collection" {
  name        = var.opensearch_collection_name
  type        = "VECTORSEARCH"
  description = var.opensearch_collection_description

  tags = var.tags
}

# OpenSearch Serverless Security Policy
resource "aws_opensearchserverless_security_policy" "knowledge_base_encryption" {
  name        = "${var.opensearch_collection_name}-encryption"
  type        = "encryption"
  description = "Encryption policy for Knowledge Base collection"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.opensearch_collection_name}"
          ]
          ResourceType = "collection"
        }
      ]
      AWSOwnedKey = true
    }
  ])
}

resource "aws_opensearchserverless_security_policy" "knowledge_base_network" {
  name        = "${var.opensearch_collection_name}-network"
  type        = "network"
  description = "Network policy for Knowledge Base collection"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.opensearch_collection_name}"
          ]
          ResourceType = "collection"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Data Access Policy for Bedrock Service
resource "aws_opensearchserverless_access_policy" "knowledge_base_data_access" {
  name        = "${var.opensearch_collection_name}-data-access"
  type        = "data"
  description = "Data access policy for Bedrock Knowledge Base"

  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.opensearch_collection_name}",
            "index/${var.opensearch_collection_name}/*"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/${var.opensearch_collection_name}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        var.knowledge_base_role_arn
      ]
    }
  ])
}