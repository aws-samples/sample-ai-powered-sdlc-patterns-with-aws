# Infrastructure

This directory contains the AWS CDK infrastructure code for the AI-Powered Software Development Assistant.

## Structure

```
infrastructure/
├── lib/                    # CDK stack definitions
│   ├── cognito-stack.ts   # Authentication infrastructure
│   ├── api-stack.ts       # API Gateway and Lambda functions
│   ├── storage-stack.ts   # DynamoDB and S3 resources
│   ├── ai-stack.ts        # Bedrock and OpenSearch resources
│   └── monitoring-stack.ts # CloudWatch and logging
├── bin/                   # CDK app entry point
├── test/                  # Infrastructure tests
├── cdk.json              # CDK configuration
├── package.json          # Dependencies
└── README.md             # This file
```

## Prerequisites

- AWS CDK v2 installed
- Node.js 18+
- AWS CLI configured
- Appropriate AWS permissions

## Deployment

```bash
# Install dependencies
npm install

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy all stacks
cdk deploy --all

# Deploy specific stack
cdk deploy AiAssistantCognitoStack
```

## Configuration

Environment variables required:
- `AWS_REGION`: Target AWS region
- `GOOGLE_CLIENT_ID`: Google OAuth client ID
- `AMAZON_CLIENT_ID`: Amazon LWA client ID
- `DOMAIN_NAME`: Custom domain (optional)

## Stacks

### CognitoStack
- User Pool with federated identity providers
- User Pool Client configuration
- Identity providers (Google, Amazon)

### ApiStack
- API Gateway REST API
- Lambda functions for backend services
- Cognito authorizer configuration

### StorageStack
- DynamoDB tables for users and documents
- S3 bucket for document storage
- Bucket policies and CORS configuration

### AiStack
- OpenSearch Serverless collection
- Bedrock model access configuration
- Vector search index setup

### MonitoringStack
- CloudWatch log groups
- Custom metrics and alarms
- Dashboard configuration

## Security

All resources are configured with:
- Encryption at rest and in transit
- Least privilege IAM policies
- VPC endpoints where applicable
- Security group restrictions

## Cost Optimization

- Serverless architecture for cost efficiency
- On-demand billing for DynamoDB
- S3 lifecycle policies for storage optimization
- Lambda provisioned concurrency only when needed
