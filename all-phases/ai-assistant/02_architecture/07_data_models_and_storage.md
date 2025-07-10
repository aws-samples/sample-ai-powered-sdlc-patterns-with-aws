# Data Models and Storage Design

## Overview
This document defines the data models, storage schemas, and data access patterns for the AI-powered software development assistant system.

## DynamoDB Table Designs

### 1. Users Table

#### Table Configuration
```json
{
  "TableName": "ai-assistant-users",
  "BillingMode": "PAY_PER_REQUEST",
  "AttributeDefinitions": [
    {"AttributeName": "userId", "AttributeType": "S"},
    {"AttributeName": "email", "AttributeType": "S"},
    {"AttributeName": "createdAt", "AttributeType": "S"},
    {"AttributeName": "lastLoginAt", "AttributeType": "S"}
  ],
  "KeySchema": [
    {"AttributeName": "userId", "KeyType": "HASH"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "EmailIndex",
      "KeySchema": [
        {"AttributeName": "email", "KeyType": "HASH"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    },
    {
      "IndexName": "LastLoginIndex",
      "KeySchema": [
        {"AttributeName": "lastLoginAt", "KeyType": "HASH"}
      ],
      "Projection": {"ProjectionType": "KEYS_ONLY"}
    }
  ],
  "StreamSpecification": {
    "StreamEnabled": true,
    "StreamViewType": "NEW_AND_OLD_IMAGES"
  },
  "PointInTimeRecoverySpecification": {
    "PointInTimeRecoveryEnabled": true
  },
  "SSESpecification": {
    "SSEEnabled": true
  }
}
```

#### Data Model
```typescript
interface User {
  userId: string;           // Primary key (Cognito sub)
  email: string;           // From Cognito
  firstName: string;       // From Cognito given_name
  lastName: string;        // From Cognito family_name
  role: 'user' | 'admin';  // Custom attribute in Cognito
  provider: 'COGNITO' | 'Google' | 'LoginWithAmazon'; // Identity provider
  isActive: boolean;       // Account status
  createdAt: string;       // ISO timestamp
  updatedAt: string;       // ISO timestamp
  lastLoginAt?: string;    // ISO timestamp
  loginCount: number;      // Total login count
  preferences: {
    theme: 'light' | 'dark';
    notifications: boolean;
    language: string;
  };
  metadata: {
    registrationSource: string; // cognito, google, amazon
    emailVerified: boolean;     // From Cognito
    termsAcceptedAt: string;
    cognitoUsername?: string;   // Cognito username if different from email
  };
}
```

#### Access Patterns
1. **Get user by Cognito sub**: `userId` (Primary Key)
2. **Get user by email**: `email` (EmailIndex GSI)
3. **List recent logins**: `lastLoginAt` (LastLoginIndex GSI)
4. **Cognito sync**: Upsert user data from Cognito claims

### 2. Documents Table

#### Table Configuration
```json
{
  "TableName": "ai-assistant-documents",
  "BillingMode": "PAY_PER_REQUEST",
  "AttributeDefinitions": [
    {"AttributeName": "userId", "AttributeType": "S"},
    {"AttributeName": "documentId", "AttributeType": "S"},
    {"AttributeName": "uploadDate", "AttributeType": "S"},
    {"AttributeName": "status", "AttributeType": "S"},
    {"AttributeName": "fileType", "AttributeType": "S"}
  ],
  "KeySchema": [
    {"AttributeName": "userId", "KeyType": "HASH"},
    {"AttributeName": "documentId", "KeyType": "RANGE"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "UserUploadDateIndex",
      "KeySchema": [
        {"AttributeName": "userId", "KeyType": "HASH"},
        {"AttributeName": "uploadDate", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    },
    {
      "IndexName": "StatusIndex",
      "KeySchema": [
        {"AttributeName": "status", "KeyType": "HASH"},
        {"AttributeName": "uploadDate", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"}
    },
    {
      "IndexName": "FileTypeIndex",
      "KeySchema": [
        {"AttributeName": "fileType", "KeyType": "HASH"},
        {"AttributeName": "uploadDate", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "KEYS_ONLY"}
    }
  ],
  "StreamSpecification": {
    "StreamEnabled": true,
    "StreamViewType": "NEW_AND_OLD_IMAGES"
  }
}
```

#### Data Model
```typescript
interface Document {
  userId: string;          // Partition key
  documentId: string;      // Sort key (UUID)
  fileName: string;        // Original filename
  fileType: string;        // MIME type
  fileSize: number;        // Size in bytes
  s3Key: string;          // S3 object key
  s3Bucket: string;       // S3 bucket name
  uploadDate: string;     // ISO timestamp
  updatedAt: string;      // ISO timestamp
  status: 'uploading' | 'processing' | 'ready' | 'error';
  processingStatus: {
    textExtracted: boolean;
    chunksCreated: boolean;
    vectorsGenerated: boolean;
    indexed: boolean;
    errorMessage?: string;
  };
  metadata: {
    title?: string;         // Extracted or provided title
    description?: string;   // User-provided description
    tags: string[];        // User-defined tags
    language?: string;     // Detected language
    pageCount?: number;    // For PDF files
    wordCount?: number;    // Extracted word count
  };
  searchableContent: {
    preview: string;       // First 500 characters
    keywords: string[];    // Extracted keywords
  };
  access: {
    isPublic: boolean;     // Future: shared documents
    sharedWith: string[];  // Future: user IDs with access
  };
}
```

#### Access Patterns
1. **Get document by ID**: `userId` + `documentId` (Primary Key)
2. **List user documents**: `userId` (Primary Key, scan)
3. **List by upload date**: `userId` + `uploadDate` (UserUploadDateIndex GSI)
4. **List by status**: `status` + `uploadDate` (StatusIndex GSI)
5. **List by file type**: `fileType` + `uploadDate` (FileTypeIndex GSI)

## S3 Storage Design

### Bucket Structure
```
ai-assistant-documents-{environment}/
├── documents/
│   └── {userId}/
│       └── {documentId}/
│           ├── original.{ext}           # Original uploaded file
│           ├── extracted-text.txt       # Extracted plain text
│           └── chunks/
│               ├── chunk-001.json       # Text chunk with metadata
│               ├── chunk-002.json
│               └── ...
├── temp-uploads/
│   └── {uploadId}/                      # Temporary multipart uploads
└── processed/
    └── {userId}/
        └── {documentId}/
            ├── metadata.json            # Processing metadata
            └── embeddings.json          # Vector embeddings backup
```

### S3 Configuration
```yaml
DocumentBucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketName: !Sub "ai-assistant-documents-${Environment}"
    VersioningConfiguration:
      Status: Enabled
    BucketEncryption:
      ServerSideEncryptionConfiguration:
        - ServerSideEncryptionByDefault:
            SSEAlgorithm: AES256
          BucketKeyEnabled: true
    LifecycleConfiguration:
      Rules:
        - Id: DeleteIncompleteMultipartUploads
          Status: Enabled
          AbortIncompleteMultipartUpload:
            DaysAfterInitiation: 7
        - Id: TransitionToIA
          Status: Enabled
          Transitions:
            - TransitionInDays: 30
              StorageClass: STANDARD_IA
        - Id: TransitionToGlacier
          Status: Enabled
          Transitions:
            - TransitionInDays: 90
              StorageClass: GLACIER
        - Id: DeleteTempUploads
          Status: Enabled
          Filter:
            Prefix: temp-uploads/
          ExpirationInDays: 1
    NotificationConfiguration:
      LambdaConfigurations:
        - Event: s3:ObjectCreated:*
          Function: !GetAtt ProcessingLambda.Arn
          Filter:
            S3Key:
              Rules:
                - Name: prefix
                  Value: documents/
                - Name: suffix
                  Value: original
    PublicAccessBlockConfiguration:
      BlockPublicAcls: true
      BlockPublicPolicy: true
      IgnorePublicAcls: true
      RestrictPublicBuckets: true
```

### File Storage Patterns

#### Document Upload Flow
```typescript
interface UploadMetadata {
  userId: string;
  documentId: string;
  fileName: string;
  fileType: string;
  fileSize: number;
  uploadTimestamp: string;
  checksumMD5: string;
}

// S3 Key Generation
const generateS3Key = (userId: string, documentId: string, type: 'original' | 'text' | 'chunk') => {
  const basePath = `documents/${userId}/${documentId}`;
  
  switch (type) {
    case 'original':
      return `${basePath}/original`;
    case 'text':
      return `${basePath}/extracted-text.txt`;
    case 'chunk':
      return `${basePath}/chunks/`;
    default:
      throw new Error('Invalid file type');
  }
};
```

#### Chunk Storage Format
```typescript
interface DocumentChunk {
  chunkId: string;         // UUID for the chunk
  documentId: string;      // Parent document ID
  userId: string;          // Document owner
  chunkIndex: number;      // Sequential chunk number
  content: string;         // Text content of the chunk
  startPosition: number;   // Character position in original
  endPosition: number;     // Character position in original
  metadata: {
    pageNumber?: number;   // For PDF files
    section?: string;      // Document section/heading
    wordCount: number;     // Words in this chunk
    charCount: number;     // Characters in this chunk
  };
  embedding?: number[];    // Vector embedding (optional)
  createdAt: string;      // ISO timestamp
}
```

## Amazon OpenSearch Serverless Design

### Collection Configuration
```yaml
VectorSearchCollection:
  Type: AWS::OpenSearchServerless::Collection
  Properties:
    Name: !Sub "ai-assistant-vectors-${Environment}"
    Type: VECTORSEARCH
    Description: "Vector storage for document embeddings and semantic search"

SecurityPolicy:
  Type: AWS::OpenSearchServerless::SecurityPolicy
  Properties:
    Name: !Sub "ai-assistant-security-policy-${Environment}"
    Type: encryption
    Policy: !Sub |
      {
        "Rules": [
          {
            "ResourceType": "collection",
            "Resource": ["collection/ai-assistant-vectors-${Environment}"]
          }
        ],
        "AWSOwnedKey": true
      }

NetworkPolicy:
  Type: AWS::OpenSearchServerless::SecurityPolicy
  Properties:
    Name: !Sub "ai-assistant-network-policy-${Environment}"
    Type: network
    Policy: !Sub |
      [
        {
          "Rules": [
            {
              "ResourceType": "collection",
              "Resource": ["collection/ai-assistant-vectors-${Environment}"]
            },
            {
              "ResourceType": "dashboard",
              "Resource": ["collection/ai-assistant-vectors-${Environment}"]
            }
          ],
          "AllowFromPublic": false
        }
      ]

AccessPolicy:
  Type: AWS::OpenSearchServerless::AccessPolicy
  Properties:
    Name: !Sub "ai-assistant-access-policy-${Environment}"
    Type: data
    Policy: !Sub |
      [
        {
          "Rules": [
            {
              "ResourceType": "collection",
              "Resource": ["collection/ai-assistant-vectors-${Environment}"],
              "Permission": ["aoss:*"]
            },
            {
              "ResourceType": "index",
              "Resource": ["index/ai-assistant-vectors-${Environment}/*"],
              "Permission": ["aoss:*"]
            }
          ],
          "Principal": [
            "${ProcessingLambdaRole.Arn}",
            "${QueryLambdaRole.Arn}"
          ]
        }
      ]
```

### Index Mapping
```json
{
  "mappings": {
    "properties": {
      "chunkId": {
        "type": "keyword"
      },
      "documentId": {
        "type": "keyword"
      },
      "userId": {
        "type": "keyword"
      },
      "content": {
        "type": "text",
        "analyzer": "standard"
      },
      "embedding": {
        "type": "knn_vector",
        "dimension": 1536,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimilarity",
          "engine": "nmslib",
          "parameters": {
            "ef_construction": 128,
            "m": 24
          }
        }
      },
      "metadata": {
        "properties": {
          "fileName": {"type": "keyword"},
          "fileType": {"type": "keyword"},
          "pageNumber": {"type": "integer"},
          "section": {"type": "text"},
          "wordCount": {"type": "integer"},
          "tags": {"type": "keyword"}
        }
      },
      "createdAt": {
        "type": "date",
        "format": "strict_date_optional_time"
      }
    }
  },
  "settings": {
    "index": {
      "knn": true,
      "knn.algo_param.ef_search": 100
    }
  }
}
```

### Vector Search Patterns
```typescript
interface VectorSearchQuery {
  query: {
    bool: {
      must: [
        {
          knn: {
            embedding: {
              vector: number[];      // Query embedding
              k: number;            // Number of results
            }
          }
        }
      ];
      filter: [
        {
          term: {
            userId: string;       // User-specific search
          }
        }
      ];
    }
  };
  size: number;                   // Result limit
  _source: string[];              // Fields to return
}

// Example search implementation
const searchSimilarChunks = async (queryEmbedding: number[], userId: string, limit: number = 10) => {
  const searchQuery: VectorSearchQuery = {
    query: {
      bool: {
        must: [
          {
            knn: {
              embedding: {
                vector: queryEmbedding,
                k: limit * 2  // Get more candidates for filtering
              }
            }
          }
        ],
        filter: [
          {
            term: {
              userId: userId
            }
          }
        ]
      }
    },
    size: limit,
    _source: ['chunkId', 'documentId', 'content', 'metadata', 'createdAt']
  };
  
  return await opensearchClient.search({
    index: 'document-chunks',
    body: searchQuery
  });
};
```

## Data Access Patterns

### 1. User Management Patterns

#### User Registration
```typescript
const createUser = async (userData: Partial<User>): Promise<User> => {
  const user: User = {
    userId: generateUUID(),
    email: userData.email!,
    passwordHash: await hashPassword(userData.password!),
    firstName: userData.firstName!,
    lastName: userData.lastName!,
    role: 'user',
    isActive: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    loginCount: 0,
    preferences: {
      theme: 'light',
      notifications: true,
      language: 'en'
    },
    metadata: {
      registrationSource: 'web',
      emailVerified: false,
      termsAcceptedAt: new Date().toISOString()
    }
  };
  
  await dynamoClient.putItem({
    TableName: 'ai-assistant-users',
    Item: user,
    ConditionExpression: 'attribute_not_exists(userId)'
  });
  
  return user;
};
```

#### User Authentication
```typescript
const authenticateUser = async (email: string, password: string): Promise<User | null> => {
  // Query by email using GSI
  const result = await dynamoClient.query({
    TableName: 'ai-assistant-users',
    IndexName: 'EmailIndex',
    KeyConditionExpression: 'email = :email',
    ExpressionAttributeValues: {
      ':email': email
    }
  });
  
  if (result.Items?.length !== 1) {
    return null;
  }
  
  const user = result.Items[0] as User;
  
  // Verify password
  const isValidPassword = await verifyPassword(password, user.passwordHash);
  if (!isValidPassword) {
    return null;
  }
  
  // Update last login
  await dynamoClient.updateItem({
    TableName: 'ai-assistant-users',
    Key: { userId: user.userId },
    UpdateExpression: 'SET lastLoginAt = :now, loginCount = loginCount + :inc',
    ExpressionAttributeValues: {
      ':now': new Date().toISOString(),
      ':inc': 1
    }
  });
  
  return user;
};
```

### 2. Document Management Patterns

#### Document Upload
```typescript
const createDocument = async (userId: string, fileData: any): Promise<Document> => {
  const documentId = generateUUID();
  const s3Key = generateS3Key(userId, documentId, 'original');
  
  // Upload to S3
  await s3Client.putObject({
    Bucket: DOCUMENT_BUCKET,
    Key: s3Key,
    Body: fileData.buffer,
    ContentType: fileData.mimetype,
    Metadata: {
      userId,
      documentId,
      originalName: fileData.originalname
    }
  });
  
  // Create document record
  const document: Document = {
    userId,
    documentId,
    fileName: fileData.originalname,
    fileType: fileData.mimetype,
    fileSize: fileData.size,
    s3Key,
    s3Bucket: DOCUMENT_BUCKET,
    uploadDate: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    status: 'processing',
    processingStatus: {
      textExtracted: false,
      chunksCreated: false,
      vectorsGenerated: false,
      indexed: false
    },
    metadata: {
      tags: [],
    },
    searchableContent: {
      preview: '',
      keywords: []
    },
    access: {
      isPublic: false,
      sharedWith: []
    }
  };
  
  await dynamoClient.putItem({
    TableName: 'ai-assistant-documents',
    Item: document
  });
  
  return document;
};
```

#### List User Documents
```typescript
const getUserDocuments = async (userId: string, limit: number = 20): Promise<Document[]> => {
  const result = await dynamoClient.query({
    TableName: 'ai-assistant-documents',
    KeyConditionExpression: 'userId = :userId',
    ExpressionAttributeValues: {
      ':userId': userId
    },
    ScanIndexForward: false, // Most recent first
    Limit: limit
  });
  
  return result.Items as Document[];
};
```

### 3. AI Query Patterns

#### Semantic Search and Response Generation
```typescript
const processQuery = async (userId: string, query: string): Promise<string> => {
  // Generate query embedding
  const queryEmbedding = await generateEmbedding(query);
  
  // Search for relevant chunks
  const searchResults = await searchSimilarChunks(queryEmbedding, userId, 5);
  
  // Prepare context from search results
  const context = searchResults.hits.hits
    .map(hit => hit._source.content)
    .join('\n\n');
  
  // Generate AI response using Bedrock
  const response = await invokeBedrockModel(query, context);
  
  return response;
};
```

## Caching Strategy

### Application-Level Caching
```typescript
// In-memory cache for frequently accessed data
const cache = new Map<string, { data: any; expiry: number }>();

const getCachedData = <T>(key: string): T | null => {
  const cached = cache.get(key);
  if (!cached || Date.now() > cached.expiry) {
    cache.delete(key);
    return null;
  }
  return cached.data as T;
};

const setCachedData = <T>(key: string, data: T, ttlSeconds: number = 300): void => {
  cache.set(key, {
    data,
    expiry: Date.now() + (ttlSeconds * 1000)
  });
};

// Cache user data for 5 minutes
const getCachedUser = async (userId: string): Promise<User | null> => {
  const cacheKey = `user:${userId}`;
  let user = getCachedData<User>(cacheKey);
  
  if (!user) {
    const result = await dynamoClient.getItem({
      TableName: 'ai-assistant-users',
      Key: { userId }
    });
    
    if (result.Item) {
      user = result.Item as User;
      setCachedData(cacheKey, user, 300); // 5 minutes
    }
  }
  
  return user;
};
```

### API Gateway Caching
```yaml
# API Gateway caching configuration
ApiGatewayRestApi:
  Type: AWS::ApiGateway::RestApi
  Properties:
    CacheClusterEnabled: true
    CacheClusterSize: "0.5"
    
# Cache configuration for specific methods
DocumentsMethod:
  Type: AWS::ApiGateway::Method
  Properties:
    CachingEnabled: true
    CacheTtlInSeconds: 300
    CacheKeyParameters:
      - method.request.header.Authorization
      - method.request.querystring.limit
```

## Data Backup and Recovery

### DynamoDB Backup Strategy
```yaml
# Point-in-time recovery
UsersTable:
  Type: AWS::DynamoDB::Table
  Properties:
    PointInTimeRecoverySpecification:
      PointInTimeRecoveryEnabled: true

# Automated backups
BackupPlan:
  Type: AWS::Backup::BackupPlan
  Properties:
    BackupPlan:
      BackupPlanName: AI-Assistant-Backup-Plan
      BackupPlanRule:
        - RuleName: DailyBackups
          TargetBackupVault: !Ref BackupVault
          ScheduleExpression: "cron(0 2 ? * * *)"
          Lifecycle:
            DeleteAfterDays: 30
```

### S3 Backup Strategy
```yaml
# Cross-region replication for disaster recovery
ReplicationConfiguration:
  Role: !GetAtt ReplicationRole.Arn
  Rules:
    - Id: ReplicateToSecondaryRegion
      Status: Enabled
      Prefix: documents/
      Destination:
        Bucket: !Sub "arn:aws:s3:::ai-assistant-documents-backup-${Environment}"
        StorageClass: STANDARD_IA
```

## Performance Optimization

### Database Performance
1. **Efficient Key Design**: Partition keys distribute load evenly
2. **GSI Usage**: Minimize GSI queries, use projection efficiently
3. **Batch Operations**: Use batch read/write for multiple items
4. **Connection Pooling**: Reuse DynamoDB connections in Lambda

### Storage Performance
1. **S3 Transfer Acceleration**: Enable for large file uploads
2. **Multipart Upload**: For files larger than 5MB
3. **Intelligent Tiering**: Automatic cost optimization
4. **CloudFront**: CDN for frequently accessed files (future)

### Search Performance
1. **Vector Indexing**: Optimized HNSW parameters for fast search
2. **Result Caching**: Cache frequent query results
3. **Batch Embedding**: Process multiple chunks together
4. **Index Optimization**: Regular index maintenance and optimization

## Data Governance

### Data Retention Policies
```typescript
// Automated data cleanup
const cleanupOldData = async () => {
  // Delete documents older than 2 years
  const cutoffDate = new Date();
  cutoffDate.setFullYear(cutoffDate.getFullYear() - 2);
  
  const oldDocuments = await dynamoClient.scan({
    TableName: 'ai-assistant-documents',
    FilterExpression: 'uploadDate < :cutoff',
    ExpressionAttributeValues: {
      ':cutoff': cutoffDate.toISOString()
    }
  });
  
  for (const doc of oldDocuments.Items || []) {
    await deleteDocument(doc.userId, doc.documentId);
  }
};
```

### Data Quality Monitoring
```typescript
// Monitor data quality metrics
const monitorDataQuality = async () => {
  const metrics = {
    totalUsers: await getUserCount(),
    totalDocuments: await getDocumentCount(),
    processingErrors: await getProcessingErrorCount(),
    averageProcessingTime: await getAverageProcessingTime()
  };
  
  // Send metrics to CloudWatch
  await cloudWatchClient.putMetricData({
    Namespace: 'AI-Assistant/DataQuality',
    MetricData: Object.entries(metrics).map(([name, value]) => ({
      MetricName: name,
      Value: value,
      Unit: 'Count',
      Timestamp: new Date()
    }))
  });
};
```
