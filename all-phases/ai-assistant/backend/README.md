# Backend Services

This directory contains the AWS Lambda functions and backend services for the AI-Powered Software Development Assistant.

## Structure

```
backend/
├── src/
│   ├── auth/              # Authentication service
│   │   ├── handler.ts     # Lambda handler
│   │   ├── service.ts     # Business logic
│   │   └── types.ts       # Type definitions
│   ├── documents/         # Document management service
│   │   ├── handler.ts     # Lambda handler
│   │   ├── service.ts     # Business logic
│   │   └── processor.ts   # Document processing
│   ├── query/             # AI query service
│   │   ├── handler.ts     # Lambda handler
│   │   ├── service.ts     # Business logic
│   │   └── ai-client.ts   # Bedrock integration
│   ├── shared/            # Shared utilities
│   │   ├── database.ts    # DynamoDB client
│   │   ├── storage.ts     # S3 client
│   │   ├── logger.ts      # Logging utility
│   │   └── types.ts       # Common types
│   └── layers/            # Lambda layers
├── tests/                 # Unit and integration tests
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript configuration
└── README.md             # This file
```

## Services

### Authentication Service
- User profile management
- Cognito user synchronization
- JWT token validation
- Role-based authorization

### Document Service
- File upload handling
- Document metadata management
- S3 integration
- Document processing triggers

### Query Service
- Natural language query processing
- Vector search integration
- Bedrock AI integration
- Response generation

### Processing Service
- Text extraction from documents
- Document chunking
- Vector embedding generation
- OpenSearch indexing

## Development

```bash
# Install dependencies
npm install

# Run tests
npm test

# Build for deployment
npm run build

# Local development
npm run dev
```

## Environment Variables

Required environment variables:
- `USER_TABLE`: DynamoDB users table name
- `DOCUMENT_TABLE`: DynamoDB documents table name
- `DOCUMENT_BUCKET`: S3 bucket for documents
- `OPENSEARCH_ENDPOINT`: OpenSearch endpoint
- `BEDROCK_REGION`: Bedrock service region

## API Endpoints

### Authentication
- `POST /auth/profile` - Get user profile
- `PUT /auth/profile` - Update user profile
- `POST /auth/sync` - Sync user from Cognito

### Documents
- `GET /documents` - List user documents
- `POST /documents/upload` - Upload document
- `GET /documents/{id}` - Get document details
- `DELETE /documents/{id}` - Delete document

### Query
- `POST /query/ask` - Process AI query
- `GET /query/history` - Get conversation history

## Testing

```bash
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# Coverage report
npm run test:coverage
```

## Deployment

Lambda functions are deployed via AWS CDK from the infrastructure directory. Each service is packaged as a separate Lambda function with appropriate IAM permissions and environment variables.
