# Document Management Lambda Function

This module implements the document management API endpoints for the AI Assistant system, following Test-Driven Development (TDD) principles and integrating with Amazon Bedrock Knowledge Bases.

## Overview

The Document Management Lambda provides three main API endpoints:
- `GET /documents` - List user documents with Knowledge Base sync status
- `DELETE /documents/{id}` - Delete document with Knowledge Base cleanup
- `GET /documents/status` - Document processing status with ingestion job tracking

## Architecture

### TDD Implementation
This module follows the Red-Green-Refactor TDD cycle:

1. **RED Phase**: Tests written first (see `__tests__/index.test.ts`)
2. **GREEN Phase**: Minimal implementation to pass tests
3. **REFACTOR Phase**: Optimized production-ready code

### AWS Services Integration
- **Amazon Bedrock Knowledge Base**: Document ingestion and sync status tracking
- **Amazon S3**: Document storage (Knowledge Base data source)
- **Amazon DynamoDB**: Document metadata storage
- **AWS Lambda**: Serverless compute for API endpoints
- **Amazon API Gateway**: RESTful API with Cognito authentication

## API Endpoints

### GET /documents
Lists documents based on user role:
- **Regular users**: Only their own documents
- **Admin users**: All documents in the system

**Response includes:**
- Document metadata (name, size, upload date, etc.)
- Knowledge Base sync status (pending, ingesting, synced, failed)
- Current ingestion job information
- Processing statistics

### DELETE /documents/{id}
Deletes a document with proper authorization:
- **Permission check**: Users can only delete their own documents, admins can delete any
- **S3 cleanup**: Removes document from storage bucket
- **Metadata cleanup**: Removes document record from DynamoDB
- **Knowledge Base cleanup**: Document removed during next sync

### GET /documents/status
Provides comprehensive processing status:
- **Status summary**: Counts by processing state
- **Active ingestion jobs**: Current Knowledge Base processing
- **Processing documents**: Documents currently being ingested
- **Job statistics**: Processing metrics and performance data

## Authentication & Authorization

### Cognito Integration
- JWT token validation via API Gateway Cognito authorizer
- User ID extracted from token claims
- Role-based access control (admin vs user)

### Permission Model
- **Users**: Can view/delete only their own documents
- **Admins**: Can view/delete all documents and access system-wide status

## Error Handling

### Comprehensive Error Responses
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Document or endpoint not found
- **500 Internal Server Error**: AWS service failures

### Graceful Degradation
- Knowledge Base API failures don't break core functionality
- Partial data returned when some services are unavailable
- Detailed error logging for debugging

## Knowledge Base Integration

### Sync Status Tracking
- **pending**: Document uploaded, waiting for ingestion
- **ingesting**: Currently being processed by Knowledge Base
- **synced**: Successfully indexed and searchable
- **failed**: Processing failed, retry logic applies

### Ingestion Job Monitoring
- Real-time job status from Bedrock APIs
- Processing statistics and performance metrics
- Failure reason tracking and retry management

## Testing

### Unit Tests
```bash
npm test
```

### Integration Tests
```bash
./integration-test.sh
```

### Test Coverage
- Authentication and authorization flows
- All API endpoints with various scenarios
- Error handling and edge cases
- Knowledge Base integration
- CORS configuration

## Deployment

### Prerequisites
- Node.js 20.x
- AWS CLI configured with `aidlc_main` profile
- Terraform for infrastructure deployment

### Build and Deploy
```bash
./deploy.sh
```

### Infrastructure Deployment
```bash
# From terraform root directory
terraform plan
terraform apply
```

## Configuration

### Environment Variables
- `AWS_REGION`: AWS region (us-west-2)
- `DOCUMENTS_BUCKET`: S3 bucket for document storage
- `DOCUMENTS_TABLE`: DynamoDB table for metadata
- `KNOWLEDGE_BASE_ID`: Bedrock Knowledge Base ID
- `DATA_SOURCE_ID`: Knowledge Base data source ID

### Lambda Configuration
- **Runtime**: Node.js 20.x
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Tracing**: X-Ray enabled
- **Logging**: CloudWatch with 14-day retention

## Monitoring

### CloudWatch Metrics
- Function invocation count and duration
- Error rates and types
- Knowledge Base API call success/failure

### CloudWatch Logs
- Structured logging with request IDs
- Error details and stack traces
- Performance timing information

### X-Ray Tracing
- End-to-end request tracing
- AWS service call performance
- Error root cause analysis

## Security

### IAM Permissions
- Least privilege access to AWS services
- Separate roles for different function types
- Resource-level permissions where possible

### Data Protection
- S3 server-side encryption
- DynamoDB encryption at rest
- Secure API Gateway integration

### Input Validation
- Request parameter validation
- File type and size restrictions
- SQL injection prevention

## Performance

### Optimization Features
- Connection pooling for AWS clients
- Efficient DynamoDB queries with indexes
- Minimal data transfer and processing
- Caching strategies for frequent operations

### Scalability
- Serverless auto-scaling
- API Gateway throttling protection
- DynamoDB on-demand billing
- S3 unlimited storage capacity

## Troubleshooting

### Common Issues
1. **401 Errors**: Check Cognito token validity and API Gateway authorizer
2. **403 Errors**: Verify user roles and permissions
3. **Knowledge Base Sync**: Check ingestion job status and S3 permissions
4. **Performance**: Monitor Lambda memory usage and timeout settings

### Debug Steps
1. Check CloudWatch logs for detailed error messages
2. Verify environment variables are set correctly
3. Test AWS service permissions with AWS CLI
4. Use X-Ray traces to identify bottlenecks

## Requirements Satisfied

This implementation satisfies the following requirements:
- **US-005 (Document Management)**: Complete document CRUD operations
- **US-005a (Document Viewing)**: Document listing with metadata
- **Authentication**: Cognito integration with role-based access
- **Knowledge Base Integration**: Real-time sync status tracking
- **Error Handling**: Comprehensive error responses
- **Performance**: Sub-30 second response times
- **Security**: Proper authorization and data protection