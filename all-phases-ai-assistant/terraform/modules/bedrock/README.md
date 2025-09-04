# Bedrock Module - Documentation Only

> **⚠️ CRITICAL WARNING: DOCUMENTATION ONLY - DO NOT USE FOR DEPLOYMENT**
> 
> This Terraform module is for documentation purposes only. It reflects the current state of AWS Bedrock infrastructure deployed via AWS CLI. **DO NOT** run `terraform plan`, `terraform apply`, or `terraform destroy` on this module.

## Overview

This module documents the Amazon Bedrock Knowledge Base infrastructure that powers the AI Assistant's document retrieval and generation capabilities. The Knowledge Base uses vector search to find relevant documents and provides context for AI-powered responses.

## Current Deployed Resources

### Knowledge Base
- **ID**: `PQB7MB5ORO`
- **Name**: `ai-assistant-knowledge-base`
- **Status**: ACTIVE
- **Region**: us-west-2
- **Account**: 254539707041

### S3 Data Source
- **ID**: `YUAUID9BJN`
- **Name**: `ai-assistant-dev-s3-data-source`
- **Status**: AVAILABLE
- **S3 Bucket**: `ai-assistant-dev-documents-993738bb`
- **Inclusion Prefixes**: `documents/`

### IAM Service Role
- **Name**: `ai-assistant-dev-bedrock-kb-role`
- **ARN**: `arn:aws:iam::254539707041:role/ai-assistant-dev-bedrock-kb-role`
- **Purpose**: Allows Bedrock Knowledge Base to access S3 and OpenSearch

## Architecture Components

### Vector Store Configuration
- **Type**: OpenSearch Serverless
- **Collection**: `ai-assistant-knowledge-base-collection`
- **Index**: `bedrock-knowledge-base-default-index`
- **Embedding Model**: Amazon Titan Embed Text v1

### Document Processing
- **Chunking Strategy**: Fixed Size
- **Max Tokens per Chunk**: 300
- **Overlap Percentage**: 20%
- **Supported Formats**: PDF, TXT, MD, DOCX

### Security Configuration
- **Encryption**: AWS managed keys
- **Network Access**: Public (with IAM controls)
- **Data Access**: Restricted to Bedrock service role

## Usage in Application

The Knowledge Base is accessed through the AI Assistant chat interface using the Bedrock RetrieveAndGenerate API:

```typescript
// Example usage in Lambda function
const response = await bedrockAgentRuntime.retrieveAndGenerate({
  input: {
    text: userQuery
  },
  retrieveAndGenerateConfiguration: {
    type: 'KNOWLEDGE_BASE',
    knowledgeBaseConfiguration: {
      knowledgeBaseId: 'PQB7MB5ORO',
      modelArn: 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0'
    }
  }
});
```

## Data Flow

1. **Document Upload**: Users upload documents via the frontend
2. **S3 Storage**: Documents are stored in `ai-assistant-dev-documents-993738bb`
3. **Knowledge Base Sync**: Bedrock automatically processes and indexes documents
4. **Vector Generation**: Documents are chunked and converted to vectors using Titan Embed
5. **OpenSearch Storage**: Vectors are stored in OpenSearch Serverless collection
6. **Query Processing**: User queries are converted to vectors and matched against stored documents
7. **Response Generation**: Relevant documents provide context for Claude 3.5 Sonnet responses

## Monitoring and Maintenance

### CloudWatch Integration
- Knowledge Base operations are logged to CloudWatch
- Sync status is monitored via EventBridge rules
- Metrics are collected for query performance and accuracy

### Data Source Synchronization
- Automatic sync when new documents are added to S3
- Manual sync available through AWS Console
- Sync status monitored by `ai-assistant-dev-kb-sync-monitor` Lambda

## Deployment Commands (AWS CLI Only)

### Create Knowledge Base
```bash
aws bedrock-agent create-knowledge-base \
  --name "ai-assistant-knowledge-base" \
  --role-arn "arn:aws:iam::254539707041:role/ai-assistant-dev-bedrock-kb-role" \
  --knowledge-base-configuration '{
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:us-west-2::foundation-model/amazon.titan-embed-text-v1"
    }
  }' \
  --storage-configuration '{
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "arn:aws:aoss:us-west-2:254539707041:collection/ai-assistant-knowledge-base-collection",
      "vectorIndexName": "bedrock-knowledge-base-default-index",
      "fieldMapping": {
        "vectorField": "bedrock-knowledge-base-default-vector",
        "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
        "metadataField": "AMAZON_BEDROCK_METADATA"
      }
    }
  }'
```

### Create Data Source
```bash
aws bedrock-agent create-data-source \
  --knowledge-base-id "PQB7MB5ORO" \
  --name "ai-assistant-dev-s3-data-source" \
  --data-source-configuration '{
    "type": "S3",
    "s3Configuration": {
      "bucketArn": "arn:aws:s3:::ai-assistant-dev-documents-993738bb",
      "inclusionPrefixes": ["documents/"]
    }
  }' \
  --vector-ingestion-configuration '{
    "chunkingConfiguration": {
      "chunkingStrategy": "FIXED_SIZE",
      "fixedSizeChunkingConfiguration": {
        "maxTokens": 300,
        "overlapPercentage": 20
      }
    }
  }'
```

## Troubleshooting

### Common Issues
1. **Sync Failures**: Check IAM permissions for S3 access
2. **Query Errors**: Verify Knowledge Base is in ACTIVE state
3. **Empty Results**: Ensure documents are properly indexed
4. **Permission Errors**: Verify Bedrock service role has required permissions

### Useful Commands
```bash
# Check Knowledge Base status
aws bedrock-agent get-knowledge-base --knowledge-base-id PQB7MB5ORO

# Check data source status
aws bedrock-agent get-data-source --knowledge-base-id PQB7MB5ORO --data-source-id YUAUID9BJN

# Start ingestion job
aws bedrock-agent start-ingestion-job --knowledge-base-id PQB7MB5ORO --data-source-id YUAUID9BJN
```

## Security Considerations

- Knowledge Base uses IAM service roles for secure access
- Documents are encrypted at rest using AWS managed keys
- Vector embeddings do not contain sensitive data directly
- Access is controlled through API Gateway and Cognito authentication
- OpenSearch collection uses security policies for access control

## Related Resources

- **S3 Module**: Documents storage configuration
- **IAM Module**: Service roles and policies
- **Lambda Module**: Knowledge Base integration functions
- **Monitoring Module**: CloudWatch logs and metrics