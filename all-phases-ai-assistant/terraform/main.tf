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

# Main Terraform configuration for AI Assistant infrastructure
# DOCUMENTATION ONLY - Reflects actual deployed AWS resources

# Local values reflecting actual deployed resource identifiers
locals {
  project_name = "ai-assistant"
  environment  = "dev"
  region      = "us-west-2"
  account_id  = "254539707041"
  
  # Actual deployed resource IDs (DOCUMENTATION ONLY)
  api_gateway_id           = "jpt8wzkowd"
  user_pool_id            = "us-west-2_FLJTm8Xt8"
  user_pool_client_id     = "3gr32ei5n768d88h02klhmpn8v"
  cloudfront_distribution_id = "EL8L41G6CQJCD"
  cloudfront_domain       = "dq9tlzfsf1veq.cloudfront.net"
  knowledge_base_id       = "PQB7MB5ORO"
  data_source_id          = "YUAUID9BJN"
  
  # Actual S3 bucket names
  documents_bucket_name   = "ai-assistant-dev-documents-993738bb"
  frontend_bucket_name    = "ai-assistant-dev-frontend-e5e9acfe"
  
  # Actual DynamoDB table name
  documents_table_name    = "ai-assistant-dev-documents"
  
  # Actual Lambda function names
  lambda_functions = {
    chat_endpoints      = "ai-assistant-chat-endpoints"
    document_management = "ai-assistant-dev-document-management"
    admin_management    = "ai-assistant-dev-admin-management"
    document_upload     = "ai-assistant-dev-document-upload"
    kb_sync_monitor     = "ai-assistant-dev-kb-sync-monitor"
    monitoring_metrics  = "ai-assistant-monitoring-metrics"
  }
}

# S3 Storage Module
# DOCUMENTATION ONLY - Reflects actual deployed S3 buckets
module "s3" {
  source = "./modules/s3"
  
  project_name                 = local.project_name
  environment                  = local.environment
  documents_bucket_name        = local.documents_bucket_name
  frontend_bucket_name         = local.frontend_bucket_name
  cloudfront_distribution_arn  = "arn:aws:cloudfront::${local.account_id}:distribution/${local.cloudfront_distribution_id}"
  cloudfront_domain           = local.cloudfront_domain
  api_gateway_domain          = "${local.api_gateway_id}.execute-api.${local.region}.amazonaws.com"
  
  tags = var.additional_tags
}

# IAM role for Bedrock Knowledge Base
# DOCUMENTATION ONLY - Reflects actual deployed role: ai-assistant-dev-bedrock-kb-role
resource "aws_iam_role" "bedrock_kb_role" {
  name = "ai-assistant-dev-bedrock-kb-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
  
  tags = merge(var.additional_tags, {
    Name = "${var.project_name}-${var.environment}-bedrock-kb-role"
  })
}

# Encryption security policy for OpenSearch Serverless collection
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.project_name}-${var.environment}-encrypt"
  type = "encryption"
  
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${var.opensearch_collection_name}"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# Network security policy for OpenSearch Serverless collection
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.project_name}-${var.environment}-network"
  type = "network"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.opensearch_collection_name}"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "collection/${var.opensearch_collection_name}"
          ]
          ResourceType = "dashboard"
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# Data access policy for OpenSearch Serverless collection
resource "aws_opensearchserverless_access_policy" "data_access" {
  name = "${var.project_name}-${var.environment}-data"
  type = "data"
  
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.opensearch_collection_name}"
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
        aws_iam_role.bedrock_kb_role.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}

# OpenSearch Serverless collection for vector storage
resource "aws_opensearchserverless_collection" "kb_collection" {
  name = var.opensearch_collection_name
  type = "VECTORSEARCH"
  
  description = "Vector search collection for ${var.project_name} ${var.environment} Knowledge Base"
  
  tags = merge(var.additional_tags, {
    Name        = var.opensearch_collection_name
    Purpose     = "Knowledge Base Vector Storage"
    Environment = var.environment
  })
  
  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data_access
  ]
}

# IAM policies for Bedrock Knowledge Base
resource "aws_iam_role_policy" "bedrock_kb_s3_policy" {
  name = "${var.project_name}-${var.environment}-bedrock-kb-s3-policy"
  role = aws_iam_role.bedrock_kb_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.s3.documents_bucket_arn,
          "${module.s3.documents_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "bedrock_kb_opensearch_policy" {
  name = "${var.project_name}-${var.environment}-bedrock-kb-opensearch-policy"
  role = aws_iam_role.bedrock_kb_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = aws_opensearchserverless_collection.kb_collection.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "bedrock_kb_bedrock_policy" {
  name = "${var.project_name}-${var.environment}-bedrock-kb-bedrock-policy"
  role = aws_iam_role.bedrock_kb_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = var.embedding_model_arn
      }
    ]
  })
}

# Wait for OpenSearch collection to be fully ready
resource "time_sleep" "wait_for_opensearch" {
  depends_on = [aws_opensearchserverless_collection.kb_collection]
  create_duration = "60s"
}

# Create the vector index using AWS CLI (required for Bedrock Knowledge Base)
resource "null_resource" "create_opensearch_index" {
  depends_on = [
    time_sleep.wait_for_opensearch,
    aws_opensearchserverless_access_policy.data_access
  ]

  provisioner "local-exec" {
    command = <<-EOT
      python3 -c "
import boto3
import json
import requests
from requests_aws4auth import AWS4Auth
import sys

def manage_index():
    try:
        session = boto3.Session(profile_name='aidlc_main')
        credentials = session.get_credentials()
        
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            '${var.aws_region}',
            'aoss',
            session_token=credentials.token
        )
        
        base_url = '${aws_opensearchserverless_collection.kb_collection.collection_endpoint}'
        index_url = f'{base_url}/${var.vector_index_name}'
        
        # First, try to delete existing index
        print('Attempting to delete existing index...')
        delete_response = requests.delete(index_url, auth=awsauth, timeout=30)
        if delete_response.status_code in [200, 404]:
            print('Index deleted or did not exist')
        else:
            print(f'Delete response: {delete_response.status_code} - {delete_response.text}')
        
        # Wait a moment for deletion to propagate
        import time
        time.sleep(5)
        
        # Create new index with correct configuration
        index_mapping = {
            'settings': {
                'index': {
                    'knn': True,
                    'knn.algo_param.ef_search': 512
                }
            },
            'mappings': {
                'properties': {
                    'bedrock-knowledge-base-default-vector': {
                        'type': 'knn_vector',
                        'dimension': ${var.embedding_dimensions},
                        'method': {
                            'name': 'hnsw',
                            'space_type': 'l2',
                            'engine': 'faiss',
                            'parameters': {
                                'm': 16
                            }
                        }
                    },
                    'AMAZON_BEDROCK_TEXT_CHUNK': {'type': 'text'},
                    'AMAZON_BEDROCK_METADATA': {'type': 'text'}
                }
            }
        }
        
        print('Creating new index with FAISS engine...')
        response = requests.put(index_url, auth=awsauth, headers={'Content-Type': 'application/json'}, data=json.dumps(index_mapping), timeout=30)
        
        if response.status_code in [200, 201]:
            print('Index created successfully with FAISS engine')
            sys.exit(0)
        else:
            print(f'Failed to create index: {response.status_code} - {response.text}')
            sys.exit(1)
            
    except Exception as e:
        print(f'Error: {str(e)}')
        sys.exit(1)

manage_index()
"
    EOT
  }

  triggers = {
    collection_endpoint = aws_opensearchserverless_collection.kb_collection.collection_endpoint
    index_name         = var.vector_index_name
  }
}

# Bedrock Knowledge Base
# DOCUMENTATION ONLY - Reflects actual deployed Knowledge Base: PQB7MB5ORO
resource "aws_bedrockagent_knowledge_base" "main" {
  name        = "ai-assistant-knowledge-base"
  description = "AI Assistant Knowledge Base for development team"
  role_arn    = "arn:aws:iam::${local.account_id}:role/ai-assistant-dev-bedrock-kb-role"
  
  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = var.embedding_model_arn
      
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = var.embedding_dimensions
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }
  
  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.kb_collection.arn
      vector_index_name = var.vector_index_name
      
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }
  
  tags = merge(var.additional_tags, {
    Name        = var.knowledge_base_name
    Purpose     = "AI Assistant Knowledge Base"
    Environment = var.environment
  })
  
  depends_on = [
    aws_iam_role_policy.bedrock_kb_s3_policy,
    aws_iam_role_policy.bedrock_kb_opensearch_policy,
    aws_iam_role_policy.bedrock_kb_bedrock_policy,
    null_resource.create_opensearch_index
  ]
}

# Bedrock Data Source (S3)
# DOCUMENTATION ONLY - Reflects actual deployed data source: YUAUID9BJN
resource "aws_bedrockagent_data_source" "s3_source" {
  knowledge_base_id = local.knowledge_base_id
  name              = "ai-assistant-dev-s3-data-source"
  description       = "S3 data source for ai-assistant documents"
  
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = module.s3.documents_bucket_arn
      inclusion_prefixes = [var.documents_prefix]
    }
  }
  
  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = var.chunk_max_tokens
        overlap_percentage = var.chunk_overlap_percentage
      }
    }
  }
  
  data_deletion_policy = "RETAIN"
}

# Data source for current AWS account
data "aws_caller_identity" "current" {}

# Cognito module for authentication
# DOCUMENTATION ONLY - Reflects actual deployed Cognito User Pool: us-west-2_FLJTm8Xt8
module "cognito" {
  source = "./modules/cognito"
  
  project_name = local.project_name
  aws_region   = local.region
  
  # Actual deployed callback URLs
  callback_urls = [
    "https://${local.cloudfront_domain}/callback",
    "http://localhost:3000/callback"
  ]
  logout_urls = [
    "https://${local.cloudfront_domain}/logout",
    "http://localhost:3000/logout"
  ]
  
  tags = var.additional_tags
}

# API Gateway module
# DOCUMENTATION ONLY - Reflects actual deployed API Gateway: jpt8wzkowd
module "api_gateway" {
  source = "./modules/api-gateway"
  
  project_name          = local.project_name
  aws_region           = local.region
  cognito_user_pool_arn = "arn:aws:cognito-idp:${local.region}:${local.account_id}:userpool/${local.user_pool_id}"
  stage_name           = local.environment
  allowed_origins      = "https://${local.cloudfront_domain}"
  rate_limit          = var.api_rate_limit
  burst_limit         = var.api_burst_limit
  
  tags = var.additional_tags
}

# DynamoDB module for document metadata
# DOCUMENTATION ONLY - Reflects actual deployed table: ai-assistant-dev-documents
module "dynamodb" {
  source = "./modules/dynamodb"
  
  project_name = local.project_name
  environment  = local.environment
  table_name   = local.documents_table_name
  tags         = var.additional_tags
}

# IAM module for Lambda execution roles
module "iam" {
  source = "./modules/iam"
  
  project_name         = var.project_name
  aws_region          = var.aws_region
  documents_bucket_arn = module.s3.documents_bucket_arn
  documents_table_arn  = module.dynamodb.table_arn
  
  tags = var.additional_tags
}

# Document Upload Lambda Function
module "document_upload_lambda" {
  source = "./modules/lambda/document-upload/terraform"
  
  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  
  lambda_execution_role_arn = module.iam.lambda_document_execution_role_arn
  documents_bucket_name     = module.s3.documents_bucket_id
  documents_table_name      = module.dynamodb.table_name
  knowledge_base_id         = aws_bedrockagent_knowledge_base.main.id
  data_source_id           = aws_bedrockagent_data_source.s3_source.data_source_id
  
  api_gateway_id                     = module.api_gateway.api_gateway_id
  api_gateway_documents_resource_id  = module.api_gateway.documents_resource_id
  api_gateway_authorizer_id          = module.api_gateway.authorizer_id
  api_gateway_execution_arn          = module.api_gateway.api_gateway_execution_arn
  
  tags = var.additional_tags
}

# Knowledge Base Sync Monitor Lambda Function
module "kb_sync_monitor_lambda" {
  source = "./modules/lambda/kb-sync-monitor/terraform"
  
  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  
  lambda_execution_role_arn = module.iam.lambda_kb_monitor_execution_role_arn
  knowledge_base_id         = aws_bedrockagent_knowledge_base.main.id
  data_source_id           = aws_bedrockagent_data_source.s3_source.data_source_id
  documents_table_name      = module.dynamodb.table_name
  
  tags = var.additional_tags
}

# Document Management Lambda Function
module "document_management_lambda" {
  source = "./modules/lambda/document-management/terraform"
  
  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  
  lambda_execution_role_arn = module.iam.lambda_document_execution_role_arn
  documents_bucket_name     = module.s3.documents_bucket_id
  documents_table_name      = module.dynamodb.table_name
  knowledge_base_id         = aws_bedrockagent_knowledge_base.main.id
  data_source_id           = aws_bedrockagent_data_source.s3_source.data_source_id
  
  api_gateway_id                     = module.api_gateway.api_gateway_id
  api_gateway_documents_resource_id  = module.api_gateway.documents_resource_id
  api_gateway_authorizer_id          = module.api_gateway.authorizer_id
  api_gateway_execution_arn          = module.api_gateway.api_gateway_execution_arn
  
  tags = var.additional_tags
}

# Chat Handler Lambda Function
module "chat_handler_lambda" {
  source = "./modules/lambda/chat-handler/terraform"
  
  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  
  knowledge_base_id         = aws_bedrockagent_knowledge_base.main.id
  documents_table_name      = module.dynamodb.table_name
  documents_table_arn       = module.dynamodb.table_arn
  
  api_gateway_id                = module.api_gateway.api_gateway_id
  api_gateway_chat_resource_id  = module.api_gateway.chat_resource_id
  api_gateway_authorizer_id     = module.api_gateway.authorizer_id
  api_gateway_execution_arn     = module.api_gateway.api_gateway_execution_arn
  
  cloudfront_url      = module.cloudfront.cloudfront_url
  log_level           = "INFO"
  enable_advanced_rag = "false"
}

# Admin Management Lambda Function
module "admin_management_lambda" {
  source = "./modules/lambda/admin-management/terraform"
  
  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  
  lambda_execution_role_arn = module.iam.lambda_admin_execution_role_arn
  knowledge_base_id         = aws_bedrockagent_knowledge_base.main.id
  data_source_id           = aws_bedrockagent_data_source.s3_source.data_source_id
  documents_table_name      = module.dynamodb.table_name
  
  api_gateway_id                = module.api_gateway.api_gateway_id
  api_gateway_root_resource_id  = module.api_gateway.root_resource_id
  api_gateway_authorizer_id     = module.api_gateway.authorizer_id
  api_gateway_execution_arn     = module.api_gateway.api_gateway_execution_arn
  
  log_level               = "INFO"
  audit_log_group_name    = module.monitoring.admin_audit_log_group
  metrics_log_group_name  = module.monitoring.knowledge_base_metrics_log_group
  
  tags = var.additional_tags
}

# CloudFront distribution for React frontend
# DOCUMENTATION ONLY - Reflects actual deployed distribution: EL8L41G6CQJCD
module "cloudfront" {
  source = "./modules/cloudfront"
  
  project_name         = local.project_name
  environment          = local.environment
  aws_region          = local.region
  frontend_bucket_name = local.frontend_bucket_name
  
  # Actual deployed API Gateway domain
  api_gateway_domain = "${local.api_gateway_id}.execute-api.${local.region}.amazonaws.com"
  cognito_domain     = "ai-assistant-auth-3gja49wa"
  
  price_class    = "PriceClass_100"
  enable_ipv6    = true
  
  tags = var.additional_tags
}

# Monitoring Metrics Lambda Function
module "monitoring_metrics_lambda" {
  source = "./modules/lambda/monitoring-metrics"
  
  project_name    = var.project_name
  environment     = var.environment
  aws_region      = var.aws_region
  
  knowledge_base_id       = aws_bedrockagent_knowledge_base.main.id
  metrics_log_group_name  = module.monitoring.knowledge_base_metrics_log_group
  audit_log_group_name    = module.monitoring.admin_audit_log_group
  log_retention_days      = 30
}

# Bedrock Knowledge Base Module
# DOCUMENTATION ONLY - Reflects actual deployed Bedrock resources
module "bedrock" {
  source = "./modules/bedrock"
  
  # Actual deployed Knowledge Base configuration
  knowledge_base_name        = "ai-assistant-knowledge-base"
  knowledge_base_description = "AI Assistant Knowledge Base for document retrieval and generation"
  knowledge_base_role_arn    = "arn:aws:iam::${local.account_id}:role/ai-assistant-dev-bedrock-kb-role"
  
  # Actual deployed data source configuration
  data_source_name        = "ai-assistant-dev-s3-data-source"
  data_source_description = "S3 data source for AI Assistant documents"
  s3_bucket_arn          = module.s3.documents_bucket_arn
  s3_inclusion_prefixes  = ["documents/"]
  bucket_owner_account_id = local.account_id
  
  # Vector configuration
  embedding_model_arn = "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v1"
  chunking_strategy   = "FIXED_SIZE"
  max_tokens_per_chunk = 300
  chunk_overlap_percentage = 20
  
  # OpenSearch configuration
  opensearch_collection_name = "ai-assistant-knowledge-base-collection"
  opensearch_collection_arn  = "arn:aws:aoss:us-west-2:${local.account_id}:collection/ai-assistant-knowledge-base-collection"
  vector_index_name         = "bedrock-knowledge-base-default-index"
  vector_field_name         = "bedrock-knowledge-base-default-vector"
  text_field_name           = "AMAZON_BEDROCK_TEXT_CHUNK"
  metadata_field_name       = "AMAZON_BEDROCK_METADATA"
  
  # AWS configuration
  aws_region     = local.region
  aws_account_id = local.account_id
  
  tags = var.additional_tags
}

# CloudWatch Monitoring and Alerting
module "monitoring" {
  source = "./modules/monitoring"
  
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  
  # Alert configuration
  alert_email_addresses = var.alert_email_addresses
  log_retention_days    = 30
  
  # Resource references for monitoring
  bedrock_model_id                = "anthropic.claude-opus-4-1-20250805-v1:0"
  chat_lambda_function_name       = module.chat_handler_lambda.chat_handler_function_name
  document_lambda_function_name   = module.document_management_lambda.lambda_function_name
  admin_lambda_function_name      = module.admin_management_lambda.lambda_function_name
  documents_table_name            = module.dynamodb.table_name
  knowledge_base_id               = local.knowledge_base_id
  s3_bucket_name                  = module.s3.documents_bucket_id
}