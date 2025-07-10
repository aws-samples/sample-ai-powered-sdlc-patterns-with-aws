# System Architecture Overview

## Architecture Diagram
![System Architecture](../generated-diagrams/system_architecture_diagram.png)

## Architecture Principles

### 1. Serverless-First Approach
- **Rationale**: Minimize operational overhead, automatic scaling, pay-per-use pricing
- **Implementation**: AWS Lambda for all backend services, managed databases
- **Benefits**: Reduced infrastructure management, cost optimization, automatic scaling

### 2. Microservices Architecture
- **Rationale**: Separation of concerns, independent deployment, scalability
- **Services**: Authentication, Document Management, Document Processing, AI Query
- **Benefits**: Independent scaling, fault isolation, technology flexibility

### 3. Event-Driven Processing
- **Rationale**: Asynchronous processing, better user experience, system resilience
- **Implementation**: S3 events trigger document processing, queue-based processing
- **Benefits**: Non-blocking operations, better resource utilization

### 4. Security by Design
- **Rationale**: Protect sensitive team knowledge and documents
- **Implementation**: IAM roles, encryption at rest/transit, API authentication
- **Benefits**: Comprehensive security, compliance readiness, access control

## System Components

### Frontend Layer

#### React Web Application
- **Purpose**: User interface for document upload and AI chat
- **Technology**: React.js with modern hooks and state management
- **Features**:
  - Responsive chat interface
  - Drag-and-drop file upload
  - Real-time conversation display
  - User authentication UI
  - Document management interface

**Key Characteristics**:
- Single Page Application (SPA)
- Mobile-responsive design
- Progressive Web App capabilities
- Client-side routing
- State management with React Context/Redux

### API Layer

#### Amazon API Gateway
- **Purpose**: Centralized API management and routing
- **Features**:
  - Request/response transformation
  - Rate limiting and throttling
  - CORS handling
  - API versioning
  - Request validation

**Security Features**:
- JWT token validation
- API key management
- Request/response logging
- DDoS protection

### Backend Services

#### 1. Authentication Service
**Components**:
- **AWS Cognito User Pool**: User registration, authentication, and management
- **Identity Providers**: Google OAuth 2.0, Amazon Login with Amazon (LWA)
- **DynamoDB Table**: Extended user profiles and application-specific data

**Responsibilities**:
- User registration with email verification
- Multi-provider authentication (Cognito, Google, Amazon)
- JWT token generation and validation
- Session management and logout
- Password reset and account recovery
- User profile synchronization

**Authentication Flow**:
- Native: Email/password through Cognito
- Federated: OAuth 2.0 with Google or Amazon
- Token: JWT tokens issued by Cognito
- Authorization: API Gateway Cognito authorizer

**API Integration**:
- Cognito handles all authentication flows
- API Gateway validates JWT tokens automatically
- Lambda functions receive user context from Cognito claims
- No custom authentication logic required

#### 2. Document Management Service
**Components**:
- **Lambda Function**: Document upload, metadata management
- **S3 Bucket**: Document storage with versioning
- **DynamoDB Table**: Document metadata and search index

**Responsibilities**:
- Secure file upload with validation
- Document metadata extraction and storage
- File organization and access control
- Document listing and search
- File deletion and cleanup

**API Endpoints**:
- `POST /documents/upload` - File upload
- `GET /documents` - List user documents
- `GET /documents/{id}` - Get document details
- `DELETE /documents/{id}` - Delete document

#### 3. Document Processing Service
**Components**:
- **Lambda Function**: Text extraction and processing
- **Amazon OpenSearch**: Vector storage and semantic search
- **S3 Integration**: Source document access

**Responsibilities**:
- Text extraction from various file formats
- Document chunking for optimal AI processing
- Vector embedding generation using Bedrock
- Semantic indexing for fast retrieval
- Processing status tracking

**Processing Pipeline**:
1. S3 event triggers processing Lambda
2. Text extraction based on file type
3. Document chunking (1000-2000 characters)
4. Vector embedding generation
5. Storage in OpenSearch with metadata
6. Processing status update

#### 4. AI Query Service
**Components**:
- **Lambda Function**: Query processing and response generation
- **Amazon Bedrock**: AI model integration (Claude 3 Haiku)
- **OpenSearch Integration**: Semantic document search

**Responsibilities**:
- Natural language query processing
- Semantic search across document corpus
- Context preparation for AI model
- Response generation and formatting
- Conversation history management

**Query Processing Flow**:
1. Receive user query
2. Generate query embedding
3. Semantic search in OpenSearch
4. Retrieve relevant document chunks
5. Prepare context for Bedrock
6. Generate AI response
7. Format and return response

### Data Storage Layer

#### 1. Amazon S3 (Document Storage)
**Structure**:
```
ai-assistant-documents/
├── users/
│   └── {user-id}/
│       ├── documents/
│       │   └── {document-id}.{extension}
│       └── processed/
│           └── {document-id}/
│               ├── text.txt
│               └── chunks/
│                   ├── chunk-001.txt
│                   └── chunk-002.txt
```

**Features**:
- Server-side encryption (SSE-S3)
- Versioning enabled
- Lifecycle policies for cost optimization
- Cross-region replication for disaster recovery

#### 2. Amazon DynamoDB Tables

##### Users Table
```json
{
  "TableName": "ai-assistant-users",
  "KeySchema": [
    {"AttributeName": "userId", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "userId", "AttributeType": "S"},
    {"AttributeName": "email", "AttributeType": "S"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "email-index",
      "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}]
    }
  ]
}
```

##### Documents Table
```json
{
  "TableName": "ai-assistant-documents",
  "KeySchema": [
    {"AttributeName": "userId", "KeyType": "HASH"},
    {"AttributeName": "documentId", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "userId", "AttributeType": "S"},
    {"AttributeName": "documentId", "AttributeType": "S"},
    {"AttributeName": "uploadDate", "AttributeType": "S"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "upload-date-index",
      "KeySchema": [
        {"AttributeName": "userId", "KeyType": "HASH"},
        {"AttributeName": "uploadDate", "KeyType": "RANGE"}
      ]
    }
  ]
}
```

#### 3. Amazon OpenSearch Serverless
**Purpose**: Vector storage and semantic search
**Configuration**:
- Collection type: Vector search
- Index mapping for document embeddings
- Metadata fields for filtering
- Security policies for access control

### Infrastructure Layer

#### Security Components
- **AWS IAM**: Role-based access control for all services
- **AWS KMS**: Encryption key management
- **VPC**: Network isolation (if required)
- **Security Groups**: Network access control

#### Monitoring and Logging
- **Amazon CloudWatch**: Metrics, logs, and alarms
- **AWS X-Ray**: Distributed tracing (optional)
- **CloudTrail**: API call auditing

## Data Flow Architecture

### 1. User Authentication Flow
```
User → Frontend → API Gateway → Auth Lambda → DynamoDB
                                      ↓
                              JWT Token ← Frontend ← API Gateway
```

### 2. Document Upload Flow
```
User → Frontend → API Gateway → Document Lambda → S3
                                      ↓
                              S3 Event → Processing Lambda → OpenSearch
                                      ↓
                              Status Update → DynamoDB
```

### 3. AI Query Flow
```
User Query → Frontend → API Gateway → Query Lambda → OpenSearch (search)
                                           ↓
                              Bedrock (AI) ← Context Preparation
                                           ↓
                              Response → Frontend ← API Gateway
```

## Scalability Design

### Horizontal Scaling
- **Lambda Functions**: Automatic scaling based on request volume
- **API Gateway**: Built-in scaling and throttling
- **DynamoDB**: On-demand scaling or provisioned capacity
- **OpenSearch**: Cluster scaling based on data volume

### Performance Optimization
- **Caching**: API Gateway caching for static responses
- **Connection Pooling**: Database connection optimization
- **Async Processing**: Non-blocking document processing
- **CDN**: CloudFront for static asset delivery

### Cost Optimization
- **Serverless Architecture**: Pay-per-use pricing model
- **S3 Lifecycle Policies**: Automatic data archiving
- **DynamoDB On-Demand**: Pay for actual usage
- **Lambda Provisioned Concurrency**: Only when needed

## Security Architecture

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- API key management
- Session timeout and refresh

### Data Protection
- Encryption at rest (S3, DynamoDB, OpenSearch)
- Encryption in transit (HTTPS/TLS)
- Secure key management (AWS KMS)
- Data isolation per user

### Network Security
- API Gateway with throttling
- CORS configuration
- Input validation and sanitization
- SQL injection prevention

### Compliance & Auditing
- CloudTrail for API auditing
- CloudWatch for security monitoring
- Access logging and analysis
- Data retention policies

## Disaster Recovery

### Backup Strategy
- **S3**: Cross-region replication
- **DynamoDB**: Point-in-time recovery and backups
- **OpenSearch**: Automated snapshots
- **Code**: Version control and CI/CD

### Recovery Procedures
- **RTO (Recovery Time Objective)**: 4 hours
- **RPO (Recovery Point Objective)**: 1 hour
- **Multi-AZ deployment**: Automatic failover
- **Infrastructure as Code**: Quick environment recreation

## Performance Specifications

### Response Time Targets
- **Authentication**: < 1 second
- **Document Upload**: < 30 seconds (10MB file)
- **Document Processing**: < 2 minutes (average document)
- **AI Query Response**: < 5 seconds
- **Document Listing**: < 2 seconds

### Throughput Targets
- **Concurrent Users**: 30+ simultaneous users
- **API Requests**: 1000+ requests per minute
- **Document Processing**: 10+ documents per minute
- **Query Processing**: 100+ queries per minute

### Availability Targets
- **System Availability**: 99.5% uptime
- **Planned Maintenance**: < 4 hours per month
- **Unplanned Downtime**: < 2 hours per month
- **Data Durability**: 99.999999999% (11 9's)
