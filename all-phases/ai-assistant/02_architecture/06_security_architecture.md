# Security Architecture

## Security Principles

### 1. Defense in Depth
Multiple layers of security controls to protect against various attack vectors:
- **Perimeter Security**: API Gateway with rate limiting and DDoS protection
- **Application Security**: Input validation, authentication, and authorization
- **Data Security**: Encryption at rest and in transit
- **Infrastructure Security**: IAM roles and network isolation

### 2. Principle of Least Privilege
Each component has only the minimum permissions required:
- **IAM Roles**: Specific permissions for each Lambda function
- **API Access**: User-based access control for documents
- **Database Access**: Row-level security where applicable
- **Service Integration**: Minimal cross-service permissions

### 3. Zero Trust Architecture
No implicit trust between system components:
- **Authentication Required**: All API calls require valid tokens
- **Authorization Checks**: Every resource access is validated
- **Encryption Everywhere**: All data encrypted in transit and at rest
- **Audit Logging**: All access attempts are logged

## Authentication Architecture

### AWS Cognito Integration
**Implementation**: AWS Cognito User Pool with federated identity providers
**Supported Providers**: 
- Email/Password (native Cognito)
- Google OAuth 2.0
- Amazon Login with Amazon (LWA)

**Cognito User Pool Configuration**:
```yaml
UserPool:
  Type: AWS::Cognito::UserPool
  Properties:
    UserPoolName: !Sub "ai-assistant-users-${Environment}"
    AutoVerifiedAttributes:
      - email
    UsernameAttributes:
      - email
    Policies:
      PasswordPolicy:
        MinimumLength: 8
        RequireUppercase: true
        RequireLowercase: true
        RequireNumbers: true
        RequireSymbols: false
    Schema:
      - Name: email
        AttributeDataType: String
        Required: true
        Mutable: true
      - Name: given_name
        AttributeDataType: String
        Required: true
        Mutable: true
      - Name: family_name
        AttributeDataType: String
        Required: true
        Mutable: true
      - Name: custom:role
        AttributeDataType: String
        Required: false
        Mutable: true
    UserPoolTags:
      Environment: !Ref Environment
      Application: AI-Assistant

UserPoolClient:
  Type: AWS::Cognito::UserPoolClient
  Properties:
    UserPoolId: !Ref UserPool
    ClientName: !Sub "ai-assistant-client-${Environment}"
    GenerateSecret: false
    SupportedIdentityProviders:
      - COGNITO
      - Google
      - LoginWithAmazon
    CallbackURLs:
      - !Sub "https://${DomainName}/auth/callback"
      - "http://localhost:3000/auth/callback"  # Development
    LogoutURLs:
      - !Sub "https://${DomainName}/auth/logout"
      - "http://localhost:3000/auth/logout"   # Development
    AllowedOAuthFlows:
      - code
      - implicit
    AllowedOAuthScopes:
      - email
      - openid
      - profile
    AllowedOAuthFlowsUserPoolClient: true
    ExplicitAuthFlows:
      - ALLOW_USER_SRP_AUTH
      - ALLOW_REFRESH_TOKEN_AUTH
      - ALLOW_USER_PASSWORD_AUTH

# Google Identity Provider
GoogleIdentityProvider:
  Type: AWS::Cognito::UserPoolIdentityProvider
  Properties:
    UserPoolId: !Ref UserPool
    ProviderName: Google
    ProviderType: Google
    ProviderDetails:
      client_id: !Ref GoogleClientId
      client_secret: !Ref GoogleClientSecret
      authorize_scopes: "email openid profile"
    AttributeMapping:
      email: email
      given_name: given_name
      family_name: family_name
      username: sub

# Amazon Identity Provider
AmazonIdentityProvider:
  Type: AWS::Cognito::UserPoolIdentityProvider
  Properties:
    UserPoolId: !Ref UserPool
    ProviderName: LoginWithAmazon
    ProviderType: LoginWithAmazon
    ProviderDetails:
      client_id: !Ref AmazonClientId
      client_secret: !Ref AmazonClientSecret
      authorize_scopes: "profile"
    AttributeMapping:
      email: email
      given_name: name
      username: user_id

# Cognito Domain for Hosted UI
UserPoolDomain:
  Type: AWS::Cognito::UserPoolDomain
  Properties:
    Domain: !Sub "ai-assistant-auth-${Environment}"
    UserPoolId: !Ref UserPool
```

### Identity Pool for AWS Resource Access
```yaml
IdentityPool:
  Type: AWS::Cognito::IdentityPool
  Properties:
    IdentityPoolName: !Sub "ai-assistant-identity-${Environment}"
    AllowUnauthenticatedIdentities: false
    CognitoIdentityProviders:
      - ClientId: !Ref UserPoolClient
        ProviderName: !GetAtt UserPool.ProviderName

# IAM Roles for authenticated users
AuthenticatedRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Federated: cognito-identity.amazonaws.com
          Action: sts:AssumeRoleWithWebIdentity
          Condition:
            StringEquals:
              'cognito-identity.amazonaws.com:aud': !Ref IdentityPool
            'ForAnyValue:StringLike':
              'cognito-identity.amazonaws.com:amr': authenticated
    Policies:
      - PolicyName: CognitoAuthorizedPolicy
        PolicyDocument:
          Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - cognito-sync:*
                - cognito-identity:*
              Resource: '*'

IdentityPoolRoleAttachment:
  Type: AWS::Cognito::IdentityPoolRoleAttachment
  Properties:
    IdentityPoolId: !Ref IdentityPool
    Roles:
      authenticated: !GetAtt AuthenticatedRole.Arn
```

### Authentication Flow with Federated Login

#### Frontend Authentication Implementation
```typescript
// AWS Amplify configuration
import { Amplify, Auth } from 'aws-amplify';

const amplifyConfig = {
  Auth: {
    region: process.env.REACT_APP_AWS_REGION,
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID,
    identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID,
    oauth: {
      domain: process.env.REACT_APP_COGNITO_DOMAIN,
      scope: ['email', 'openid', 'profile'],
      redirectSignIn: process.env.REACT_APP_REDIRECT_SIGN_IN,
      redirectSignOut: process.env.REACT_APP_REDIRECT_SIGN_OUT,
      responseType: 'code'
    }
  }
};

Amplify.configure(amplifyConfig);

// Authentication service
class AuthService {
  // Sign in with email/password
  async signIn(email: string, password: string) {
    try {
      const user = await Auth.signIn(email, password);
      return this.handleAuthSuccess(user);
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Sign in with Google
  async signInWithGoogle() {
    try {
      await Auth.federatedSignIn({ provider: 'Google' });
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Sign in with Amazon
  async signInWithAmazon() {
    try {
      await Auth.federatedSignIn({ provider: 'LoginWithAmazon' });
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Get current authenticated user
  async getCurrentUser() {
    try {
      const user = await Auth.currentAuthenticatedUser();
      return {
        userId: user.attributes.sub,
        email: user.attributes.email,
        firstName: user.attributes.given_name,
        lastName: user.attributes.family_name,
        role: user.attributes['custom:role'] || 'user',
        provider: user.attributes.identities ? 
          JSON.parse(user.attributes.identities)[0].providerName : 'COGNITO'
      };
    } catch (error) {
      return null;
    }
  }

  // Get JWT token for API calls
  async getIdToken() {
    try {
      const session = await Auth.currentSession();
      return session.getIdToken().getJwtToken();
    } catch (error) {
      throw new Error('No valid session');
    }
  }

  // Sign out
  async signOut() {
    try {
      await Auth.signOut();
    } catch (error) {
      console.error('Sign out error:', error);
    }
  }

  private handleAuthSuccess(user: any) {
    return {
      userId: user.attributes.sub,
      email: user.attributes.email,
      firstName: user.attributes.given_name,
      lastName: user.attributes.family_name,
      isNewUser: user.challengeName === 'NEW_PASSWORD_REQUIRED'
    };
  }

  private handleAuthError(error: any) {
    switch (error.code) {
      case 'UserNotConfirmedException':
        return new Error('Please verify your email address');
      case 'NotAuthorizedException':
        return new Error('Invalid email or password');
      case 'UserNotFoundException':
        return new Error('User not found');
      default:
        return new Error(error.message || 'Authentication failed');
    }
  }
}
```

### Backend API Authorization with Cognito
```typescript
// API Gateway Cognito Authorizer
const cognitoAuthorizer = {
  type: 'COGNITO_USER_POOLS',
  authorizerId: {
    Ref: 'CognitoAuthorizer'
  }
};

// CloudFormation for API Gateway Authorizer
const apiGatewayAuthorizer = {
  CognitoAuthorizer: {
    Type: 'AWS::ApiGateway::Authorizer',
    Properties: {
      Name: 'CognitoAuthorizer',
      Type: 'COGNITO_USER_POOLS',
      IdentitySource: 'method.request.header.Authorization',
      RestApiId: { Ref: 'ApiGatewayRestApi' },
      ProviderARNs: [
        { 'Fn::GetAtt': ['UserPool', 'Arn'] }
      ]
    }
  }
};

// Lambda function to handle Cognito JWT tokens
const validateCognitoToken = async (event: any) => {
  try {
    // Extract user info from Cognito JWT token
    const claims = event.requestContext.authorizer.claims;
    
    const user = {
      userId: claims.sub,
      email: claims.email,
      firstName: claims.given_name,
      lastName: claims.family_name,
      role: claims['custom:role'] || 'user',
      provider: claims.identities ? 
        JSON.parse(claims.identities)[0].providerName : 'COGNITO'
    };

    // Store/update user in DynamoDB if needed
    await upsertUser(user);
    
    return user;
  } catch (error) {
    throw new Error('Invalid token');
  }
};

// User synchronization with DynamoDB
const upsertUser = async (cognitoUser: any) => {
  const user = {
    userId: cognitoUser.userId,
    email: cognitoUser.email,
    firstName: cognitoUser.firstName,
    lastName: cognitoUser.lastName,
    role: cognitoUser.role,
    provider: cognitoUser.provider,
    updatedAt: new Date().toISOString(),
    lastLoginAt: new Date().toISOString()
  };

  await dynamoClient.update({
    TableName: 'ai-assistant-users',
    Key: { userId: user.userId },
    UpdateExpression: `
      SET email = :email,
          firstName = :firstName,
          lastName = :lastName,
          #role = :role,
          provider = :provider,
          updatedAt = :updatedAt,
          lastLoginAt = :lastLoginAt
    `,
    ExpressionAttributeNames: {
      '#role': 'role'
    },
    ExpressionAttributeValues: {
      ':email': user.email,
      ':firstName': user.firstName,
      ':lastName': user.lastName,
      ':role': user.role,
      ':provider': user.provider,
      ':updatedAt': user.updatedAt,
      ':lastLoginAt': user.lastLoginAt
    },
    ReturnValues: 'ALL_NEW'
  });
};
```

## Authorization Architecture

### Cognito-Based Access Control
**User Attributes in Cognito**:
- **Standard Attributes**: email, given_name, family_name, sub (userId)
- **Custom Attributes**: custom:role (user/admin)
- **Provider Information**: identities (for federated users)

**Permission Matrix**:
| Resource | User | Admin |
|----------|------|-------|
| Upload Documents | ✓ | ✓ |
| View Own Documents | ✓ | ✓ |
| Delete Own Documents | ✓ | ✓ |
| Query AI System | ✓ | ✓ |
| View All Documents | ✗ | ✓ |
| User Management | ✗ | ✓ |

### API Authorization with Cognito
**Implementation**: API Gateway Cognito User Pool Authorizer
**Authorization Flow**:
```yaml
# API Gateway Method with Cognito Authorization
DocumentsGetMethod:
  Type: AWS::ApiGateway::Method
  Properties:
    RestApiId: !Ref ApiGatewayRestApi
    ResourceId: !Ref DocumentsResource
    HttpMethod: GET
    AuthorizationType: COGNITO_USER_POOLS
    AuthorizerId: !Ref CognitoAuthorizer
    Integration:
      Type: AWS_PROXY
      IntegrationHttpMethod: POST
      Uri: !Sub 
        - arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${LambdaArn}/invocations
        - LambdaArn: !GetAtt DocumentServiceLambda.Arn
```

### Lambda Authorization Handler
```typescript
// Extract user context from Cognito authorizer
const getUserFromEvent = (event: APIGatewayProxyEvent): CognitoUser => {
  const claims = event.requestContext.authorizer?.claims;
  
  if (!claims) {
    throw new Error('No authorization claims found');
  }

  return {
    userId: claims.sub,
    email: claims.email,
    firstName: claims.given_name || '',
    lastName: claims.family_name || '',
    role: claims['custom:role'] || 'user',
    provider: getProviderFromClaims(claims),
    emailVerified: claims.email_verified === 'true'
  };
};

const getProviderFromClaims = (claims: any): string => {
  if (claims.identities) {
    const identities = JSON.parse(claims.identities);
    return identities[0]?.providerName || 'COGNITO';
  }
  return 'COGNITO';
};

// Role-based authorization middleware
const requireRole = (requiredRole: 'user' | 'admin') => {
  return (user: CognitoUser) => {
    if (requiredRole === 'admin' && user.role !== 'admin') {
      throw new Error('Admin access required');
    }
    return true;
  };
};

// Resource ownership validation
const validateDocumentAccess = async (userId: string, documentId: string) => {
  const document = await getDocument(documentId);
  
  if (!document) {
    throw new Error('Document not found');
  }
  
  if (document.userId !== userId) {
    throw new Error('Access denied');
  }
  
  return document;
};
```

### Federated Identity Management
```typescript
// Handle different identity providers
const handleFederatedUser = async (cognitoUser: CognitoUser) => {
  // Check if user exists in our system
  let existingUser = await getUserById(cognitoUser.userId);
  
  if (!existingUser) {
    // Create new user record for federated login
    existingUser = await createUserFromCognito(cognitoUser);
  } else {
    // Update user information from provider
    await updateUserFromCognito(existingUser.userId, cognitoUser);
  }
  
  return existingUser;
};

const createUserFromCognito = async (cognitoUser: CognitoUser) => {
  const user = {
    userId: cognitoUser.userId,
    email: cognitoUser.email,
    firstName: cognitoUser.firstName,
    lastName: cognitoUser.lastName,
    role: 'user', // Default role for new users
    provider: cognitoUser.provider,
    isActive: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    lastLoginAt: new Date().toISOString(),
    loginCount: 1,
    preferences: {
      theme: 'light',
      notifications: true,
      language: 'en'
    },
    metadata: {
      registrationSource: cognitoUser.provider.toLowerCase(),
      emailVerified: cognitoUser.emailVerified,
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

## Data Security

### Encryption at Rest

#### DynamoDB Encryption
- **Method**: AWS managed encryption using AWS KMS
- **Key Management**: AWS managed keys (default)
- **Scope**: All table data and indexes

```yaml
# DynamoDB Encryption Configuration
UsersTable:
  Type: AWS::DynamoDB::Table
  Properties:
    SSESpecification:
      SSEEnabled: true
      KMSMasterKeyId: alias/aws/dynamodb
```

#### S3 Encryption
- **Method**: Server-side encryption with S3 managed keys (SSE-S3)
- **Scope**: All uploaded documents
- **Key Rotation**: Automatic key rotation

```yaml
# S3 Bucket Encryption
DocumentBucket:
  Type: AWS::S3::Bucket
  Properties:
    BucketEncryption:
      ServerSideEncryptionConfiguration:
        - ServerSideEncryptionByDefault:
            SSEAlgorithm: AES256
          BucketKeyEnabled: true
```

#### OpenSearch Encryption
- **Method**: AWS managed encryption
- **Scope**: All indexed data and vectors
- **Key Management**: Service-managed keys

### Encryption in Transit

#### HTTPS/TLS Configuration
- **API Gateway**: TLS 1.2+ enforced
- **Frontend**: HTTPS only with HSTS headers
- **Internal Communication**: AWS service-to-service encryption

**Security Headers**:
```javascript
// Security headers for API responses
const securityHeaders = {
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Content-Security-Policy': "default-src 'self'",
  'Referrer-Policy': 'strict-origin-when-cross-origin'
};
```

## Network Security

### API Gateway Security

#### Rate Limiting
- **Throttling**: 1000 requests per second per API key
- **Burst Limit**: 2000 requests
- **Per-User Limits**: 100 requests per minute per user

```yaml
# API Gateway Throttling
ApiGatewayRestApi:
  Type: AWS::ApiGateway::RestApi
  Properties:
    ThrottleSettings:
      RateLimit: 1000
      BurstLimit: 2000
```

#### Request Validation
- **Input Validation**: JSON schema validation for all POST/PUT requests
- **Parameter Validation**: Query parameter and path parameter validation
- **Content-Type Validation**: Strict content-type checking

```json
// Request validation schema example
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "type": "object",
  "properties": {
    "email": {
      "type": "string",
      "format": "email",
      "maxLength": 255
    },
    "password": {
      "type": "string",
      "minLength": 8,
      "maxLength": 128
    }
  },
  "required": ["email", "password"],
  "additionalProperties": false
}
```

### CORS Configuration
**Policy**: Restrictive CORS policy for production
```javascript
// CORS Configuration
const corsConfig = {
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With'],
  credentials: true,
  maxAge: 86400 // 24 hours
};
```

## Input Validation and Sanitization

### Server-Side Validation
**Validation Library**: Joi for comprehensive input validation
**Validation Rules**:
- **Email**: Valid email format, maximum length
- **Passwords**: Complexity requirements, length limits
- **File Uploads**: File type, size, and content validation
- **Query Parameters**: Type checking and sanitization

```javascript
// Input validation schemas
const Joi = require('joi');

const loginSchema = Joi.object({
  email: Joi.string().email().max(255).required(),
  password: Joi.string().min(8).max(128).required()
});

const documentUploadSchema = Joi.object({
  filename: Joi.string().max(255).required(),
  contentType: Joi.string().valid(
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/markdown',
    'text/plain'
  ).required(),
  size: Joi.number().max(10 * 1024 * 1024).required() // 10MB limit
});
```

### File Upload Security
**File Type Validation**: MIME type and file extension checking
**File Size Limits**: 10MB maximum per file
**Content Scanning**: Basic malware detection (future enhancement)
**Filename Sanitization**: Remove dangerous characters

```javascript
// File upload validation
const validateFileUpload = (file) => {
  const allowedTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/markdown',
    'text/plain'
  ];
  
  const allowedExtensions = ['.pdf', '.docx', '.md', '.txt'];
  
  // Validate MIME type
  if (!allowedTypes.includes(file.mimetype)) {
    throw new Error('Invalid file type');
  }
  
  // Validate file extension
  const ext = path.extname(file.originalname).toLowerCase();
  if (!allowedExtensions.includes(ext)) {
    throw new Error('Invalid file extension');
  }
  
  // Validate file size
  if (file.size > 10 * 1024 * 1024) {
    throw new Error('File too large');
  }
  
  return true;
};
```

## IAM Security

### Lambda Execution Roles
**Principle**: Each Lambda function has its own IAM role with minimal permissions

#### Authentication Service Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/ai-assistant-users*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

#### Document Service Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::ai-assistant-documents/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/ai-assistant-documents*"
    }
  ]
}
```

#### Processing Service Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::ai-assistant-documents/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
    },
    {
      "Effect": "Allow",
      "Action": [
        "aoss:APIAccessAll"
      ],
      "Resource": "arn:aws:aoss:*:*:collection/ai-assistant-vectors"
    }
  ]
}
```

### Cross-Service Access Control
**Service-to-Service Authentication**: IAM roles for service authentication
**Resource-Based Policies**: S3 bucket policies and OpenSearch access policies
**Temporary Credentials**: STS tokens for cross-service access

## Audit and Logging

### CloudTrail Configuration
**Purpose**: API call auditing and compliance
**Configuration**:
```yaml
CloudTrail:
  Type: AWS::CloudTrail::Trail
  Properties:
    TrailName: ai-assistant-audit-trail
    S3BucketName: !Ref AuditLogsBucket
    IncludeGlobalServiceEvents: true
    IsMultiRegionTrail: true
    EnableLogFileValidation: true
    EventSelectors:
      - ReadWriteType: All
        IncludeManagementEvents: true
        DataResources:
          - Type: AWS::S3::Object
            Values: 
              - "arn:aws:s3:::ai-assistant-documents/*"
          - Type: AWS::DynamoDB::Table
            Values:
              - "arn:aws:dynamodb:*:*:table/ai-assistant-*"
```

### Application Logging
**Log Levels**: ERROR, WARN, INFO, DEBUG
**Structured Logging**: JSON format for easy parsing
**Sensitive Data**: No passwords, tokens, or PII in logs

```javascript
// Structured logging implementation
const logger = {
  info: (message, metadata = {}) => {
    console.log(JSON.stringify({
      level: 'INFO',
      timestamp: new Date().toISOString(),
      message,
      ...metadata,
      requestId: context.awsRequestId
    }));
  },
  
  error: (message, error = {}, metadata = {}) => {
    console.error(JSON.stringify({
      level: 'ERROR',
      timestamp: new Date().toISOString(),
      message,
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack
      },
      ...metadata,
      requestId: context.awsRequestId
    }));
  }
};
```

### Security Event Monitoring
**Events to Monitor**:
- Failed authentication attempts
- Unauthorized access attempts
- Unusual API usage patterns
- File upload anomalies
- System errors and exceptions

**Alerting Rules**:
```yaml
# CloudWatch Alarms for Security Events
FailedLoginAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: HighFailedLoginAttempts
    AlarmDescription: High number of failed login attempts
    MetricName: FailedLogins
    Namespace: AI-Assistant/Security
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 1
    Threshold: 10
    ComparisonOperator: GreaterThanThreshold
    AlarmActions:
      - !Ref SecurityAlertsTopic
```

## Data Privacy and Compliance

### Data Classification
**Sensitive Data Types**:
- User credentials (passwords, tokens)
- Personal information (email addresses)
- Business documents (uploaded content)
- System logs (access patterns)

**Data Handling Policies**:
- **Encryption**: All sensitive data encrypted
- **Access Control**: Role-based access to sensitive data
- **Retention**: Automated data lifecycle management
- **Deletion**: Secure data deletion procedures

### Privacy Controls
**User Rights**:
- **Data Access**: Users can view their own data
- **Data Portability**: Export user documents (future)
- **Data Deletion**: Account and data deletion
- **Consent Management**: Clear privacy policy and consent

**Implementation**:
```javascript
// Data deletion service
const deleteUserData = async (userId) => {
  // Delete user documents from S3
  await deleteUserDocuments(userId);
  
  // Delete document metadata from DynamoDB
  await deleteDocumentMetadata(userId);
  
  // Delete vector embeddings from OpenSearch
  await deleteUserVectors(userId);
  
  // Delete user account
  await deleteUserAccount(userId);
  
  // Log deletion for audit
  logger.info('User data deleted', { userId, action: 'data_deletion' });
};
```

## Incident Response

### Security Incident Categories
1. **Authentication Breaches**: Compromised user accounts
2. **Data Breaches**: Unauthorized access to documents
3. **System Intrusions**: Malicious system access
4. **DDoS Attacks**: Service availability attacks

### Response Procedures
**Immediate Response** (0-1 hour):
- Identify and contain the incident
- Assess the scope and impact
- Notify stakeholders
- Preserve evidence

**Investigation** (1-24 hours):
- Analyze logs and system state
- Determine root cause
- Document findings
- Plan remediation

**Recovery** (24-72 hours):
- Implement fixes and patches
- Restore normal operations
- Monitor for recurring issues
- Update security measures

**Post-Incident** (1-2 weeks):
- Conduct post-mortem analysis
- Update security procedures
- Implement preventive measures
- Document lessons learned

## Security Testing

### Automated Security Testing
**SAST (Static Application Security Testing)**:
- Code vulnerability scanning
- Dependency vulnerability checking
- Security rule enforcement

**DAST (Dynamic Application Security Testing)**:
- API security testing
- Authentication bypass testing
- Input validation testing

### Manual Security Testing
**Penetration Testing**: Quarterly external security assessments
**Code Reviews**: Security-focused code reviews for all changes
**Configuration Reviews**: Regular AWS configuration audits

### Security Metrics
**Key Performance Indicators**:
- Authentication success rate
- Failed login attempt patterns
- API error rates
- Security alert response times
- Vulnerability remediation times

**Monitoring Dashboard**:
- Real-time security event monitoring
- User activity patterns
- System health indicators
- Compliance status tracking
