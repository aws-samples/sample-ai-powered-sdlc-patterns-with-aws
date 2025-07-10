# AWS Cognito Authentication Design

## Overview
This document outlines the updated authentication architecture using AWS Cognito User Pools with federated identity providers (Google and Amazon) instead of custom JWT authentication.

## AWS Cognito User Pool Configuration

### User Pool Setup
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
        TemporaryPasswordValidityDays: 7
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
      - Name: role
        AttributeDataType: String
        Required: false
        Mutable: true
        DeveloperOnlyAttribute: false
    UserPoolTags:
      Environment: !Ref Environment
      Application: AI-Assistant
    AccountRecoverySetting:
      RecoveryMechanisms:
        - Name: verified_email
          Priority: 1

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
      - aws.cognito.signin.user.admin
    AllowedOAuthFlowsUserPoolClient: true
    ExplicitAuthFlows:
      - ALLOW_USER_SRP_AUTH
      - ALLOW_REFRESH_TOKEN_AUTH
      - ALLOW_USER_PASSWORD_AUTH
    PreventUserExistenceErrors: ENABLED
    ReadAttributes:
      - email
      - given_name
      - family_name
      - custom:role
    WriteAttributes:
      - given_name
      - family_name
```

### Federated Identity Providers

#### Google Identity Provider
```yaml
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
    IdpIdentifiers:
      - Google
```

#### Amazon Identity Provider (Login with Amazon)
```yaml
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
      family_name: name
      username: user_id
    IdpIdentifiers:
      - LoginWithAmazon
```

### Cognito Hosted UI Domain
```yaml
UserPoolDomain:
  Type: AWS::Cognito::UserPoolDomain
  Properties:
    Domain: !Sub "ai-assistant-auth-${Environment}-${AWS::AccountId}"
    UserPoolId: !Ref UserPool
```

## Frontend Integration with AWS Amplify

### Amplify Configuration
```typescript
// amplify-config.ts
import { Amplify } from 'aws-amplify';

const amplifyConfig = {
  Auth: {
    region: process.env.REACT_APP_AWS_REGION || 'us-east-1',
    userPoolId: process.env.REACT_APP_USER_POOL_ID,
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID,
    identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID,
    oauth: {
      domain: process.env.REACT_APP_COGNITO_DOMAIN,
      scope: ['email', 'openid', 'profile', 'aws.cognito.signin.user.admin'],
      redirectSignIn: process.env.REACT_APP_REDIRECT_SIGN_IN || 'http://localhost:3000/auth/callback',
      redirectSignOut: process.env.REACT_APP_REDIRECT_SIGN_OUT || 'http://localhost:3000/auth/logout',
      responseType: 'code'
    }
  }
};

Amplify.configure(amplifyConfig);
export default amplifyConfig;
```

### Authentication Service
```typescript
// auth.service.ts
import { Auth } from 'aws-amplify';

export interface AuthUser {
  userId: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'user' | 'admin';
  provider: 'COGNITO' | 'Google' | 'LoginWithAmazon';
  emailVerified: boolean;
}

class AuthService {
  // Sign in with email/password
  async signIn(email: string, password: string): Promise<AuthUser> {
    try {
      const user = await Auth.signIn(email, password);
      return this.mapCognitoUser(user);
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Sign up with email/password
  async signUp(email: string, password: string, firstName: string, lastName: string): Promise<void> {
    try {
      await Auth.signUp({
        username: email,
        password,
        attributes: {
          email,
          given_name: firstName,
          family_name: lastName,
          'custom:role': 'user'
        }
      });
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Confirm sign up with verification code
  async confirmSignUp(email: string, code: string): Promise<void> {
    try {
      await Auth.confirmSignUp(email, code);
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Sign in with Google
  async signInWithGoogle(): Promise<void> {
    try {
      await Auth.federatedSignIn({ provider: 'Google' });
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Sign in with Amazon
  async signInWithAmazon(): Promise<void> {
    try {
      await Auth.federatedSignIn({ provider: 'LoginWithAmazon' });
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Get current authenticated user
  async getCurrentUser(): Promise<AuthUser | null> {
    try {
      const user = await Auth.currentAuthenticatedUser();
      return this.mapCognitoUser(user);
    } catch (error) {
      return null;
    }
  }

  // Get JWT token for API calls
  async getIdToken(): Promise<string> {
    try {
      const session = await Auth.currentSession();
      return session.getIdToken().getJwtToken();
    } catch (error) {
      throw new Error('No valid session');
    }
  }

  // Sign out
  async signOut(): Promise<void> {
    try {
      await Auth.signOut();
    } catch (error) {
      console.error('Sign out error:', error);
    }
  }

  // Forgot password
  async forgotPassword(email: string): Promise<void> {
    try {
      await Auth.forgotPassword(email);
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  // Confirm forgot password
  async forgotPasswordSubmit(email: string, code: string, newPassword: string): Promise<void> {
    try {
      await Auth.forgotPasswordSubmit(email, code, newPassword);
    } catch (error) {
      throw this.handleAuthError(error);
    }
  }

  private mapCognitoUser(cognitoUser: any): AuthUser {
    const attributes = cognitoUser.attributes || {};
    const identities = attributes.identities ? JSON.parse(attributes.identities) : [];
    
    return {
      userId: attributes.sub,
      email: attributes.email,
      firstName: attributes.given_name || '',
      lastName: attributes.family_name || '',
      role: attributes['custom:role'] || 'user',
      provider: identities.length > 0 ? identities[0].providerName : 'COGNITO',
      emailVerified: attributes.email_verified === 'true'
    };
  }

  private handleAuthError(error: any): Error {
    switch (error.code) {
      case 'UserNotConfirmedException':
        return new Error('Please verify your email address');
      case 'NotAuthorizedException':
        return new Error('Invalid email or password');
      case 'UserNotFoundException':
        return new Error('User not found');
      case 'InvalidPasswordException':
        return new Error('Password does not meet requirements');
      case 'UsernameExistsException':
        return new Error('User already exists');
      case 'CodeMismatchException':
        return new Error('Invalid verification code');
      case 'ExpiredCodeException':
        return new Error('Verification code has expired');
      default:
        return new Error(error.message || 'Authentication failed');
    }
  }
}

export const authService = new AuthService();
```

## Backend API Integration

### API Gateway Cognito Authorizer
```yaml
# CloudFormation for API Gateway Cognito Authorizer
CognitoAuthorizer:
  Type: AWS::ApiGateway::Authorizer
  Properties:
    Name: !Sub "CognitoAuthorizer-${Environment}"
    Type: COGNITO_USER_POOLS
    IdentitySource: method.request.header.Authorization
    RestApiId: !Ref ApiGatewayRestApi
    ProviderARNs:
      - !GetAtt UserPool.Arn

# Example API method with Cognito authorization
DocumentsGetMethod:
  Type: AWS::ApiGateway::Method
  Properties:
    RestApiId: !Ref ApiGatewayRestApi
    ResourceId: !Ref DocumentsResource
    HttpMethod: GET
    AuthorizationType: COGNITO_USER_POOLS
    AuthorizerId: !Ref CognitoAuthorizer
    RequestParameters:
      method.request.header.Authorization: true
    Integration:
      Type: AWS_PROXY
      IntegrationHttpMethod: POST
      Uri: !Sub 
        - arn:aws:apigateway:${AWS::Region}:lambda:path/2015-03-31/functions/${LambdaArn}/invocations
        - LambdaArn: !GetAtt DocumentServiceLambda.Arn
```

### Lambda Function Authorization Handler
```typescript
// cognito-auth.ts
import { APIGatewayProxyEvent } from 'aws-lambda';

export interface CognitoUser {
  userId: string;
  email: string;
  firstName: string;
  lastName: string;
  role: 'user' | 'admin';
  provider: string;
  emailVerified: boolean;
  username: string;
}

export const getUserFromEvent = (event: APIGatewayProxyEvent): CognitoUser => {
  const claims = event.requestContext.authorizer?.claims;
  
  if (!claims) {
    throw new Error('No authorization claims found');
  }

  const identities = claims.identities ? JSON.parse(claims.identities) : [];
  const provider = identities.length > 0 ? identities[0].providerName : 'COGNITO';

  return {
    userId: claims.sub,
    email: claims.email,
    firstName: claims.given_name || '',
    lastName: claims.family_name || '',
    role: claims['custom:role'] || 'user',
    provider,
    emailVerified: claims.email_verified === 'true',
    username: claims['cognito:username']
  };
};

// Middleware for role-based authorization
export const requireRole = (requiredRole: 'user' | 'admin') => {
  return (user: CognitoUser): boolean => {
    if (requiredRole === 'admin' && user.role !== 'admin') {
      throw new Error('Admin access required');
    }
    return true;
  };
};

// User synchronization with DynamoDB
export const syncUserWithDynamoDB = async (cognitoUser: CognitoUser): Promise<void> => {
  const userRecord = {
    userId: cognitoUser.userId,
    email: cognitoUser.email,
    firstName: cognitoUser.firstName,
    lastName: cognitoUser.lastName,
    role: cognitoUser.role,
    provider: cognitoUser.provider,
    isActive: true,
    updatedAt: new Date().toISOString(),
    lastLoginAt: new Date().toISOString(),
    metadata: {
      registrationSource: cognitoUser.provider.toLowerCase(),
      emailVerified: cognitoUser.emailVerified,
      cognitoUsername: cognitoUser.username
    }
  };

  // Upsert user record
  await dynamoClient.update({
    TableName: process.env.USERS_TABLE!,
    Key: { userId: cognitoUser.userId },
    UpdateExpression: `
      SET email = :email,
          firstName = :firstName,
          lastName = :lastName,
          #role = :role,
          provider = :provider,
          isActive = :isActive,
          updatedAt = :updatedAt,
          lastLoginAt = :lastLoginAt,
          metadata = :metadata
    `,
    ExpressionAttributeNames: {
      '#role': 'role'
    },
    ExpressionAttributeValues: {
      ':email': userRecord.email,
      ':firstName': userRecord.firstName,
      ':lastName': userRecord.lastName,
      ':role': userRecord.role,
      ':provider': userRecord.provider,
      ':isActive': userRecord.isActive,
      ':updatedAt': userRecord.updatedAt,
      ':lastLoginAt': userRecord.lastLoginAt,
      ':metadata': userRecord.metadata
    }
  });
};
```

## Updated User Data Model

### DynamoDB Users Table Schema
```typescript
interface User {
  userId: string;           // Primary key (Cognito sub)
  email: string;           // From Cognito email attribute
  firstName: string;       // From Cognito given_name
  lastName: string;        // From Cognito family_name
  role: 'user' | 'admin';  // From Cognito custom:role attribute
  provider: 'COGNITO' | 'Google' | 'LoginWithAmazon'; // Identity provider
  isActive: boolean;       // Account status
  createdAt: string;       // ISO timestamp (first login)
  updatedAt: string;       // ISO timestamp (last update)
  lastLoginAt: string;     // ISO timestamp (last login)
  loginCount: number;      // Total login count
  preferences: {
    theme: 'light' | 'dark';
    notifications: boolean;
    language: string;
  };
  metadata: {
    registrationSource: string; // cognito, google, amazon
    emailVerified: boolean;     // From Cognito email_verified
    cognitoUsername: string;    // Cognito username
    termsAcceptedAt?: string;   // Terms acceptance timestamp
  };
}
```

## Security Considerations

### Token Validation
- **Automatic Validation**: API Gateway automatically validates Cognito JWT tokens
- **Token Expiration**: Cognito handles token refresh automatically
- **Revocation**: Tokens can be revoked through Cognito admin APIs

### Federated Identity Security
- **Provider Verification**: Only configured identity providers are allowed
- **Attribute Mapping**: Secure mapping of provider attributes to Cognito attributes
- **Account Linking**: Automatic linking of accounts with same email address

### Data Protection
- **PII Handling**: Minimal PII stored in DynamoDB, primary data in Cognito
- **Encryption**: All Cognito data encrypted at rest and in transit
- **Compliance**: Cognito provides GDPR, HIPAA compliance features

## Migration Strategy

### From Custom JWT to Cognito
1. **Phase 1**: Deploy Cognito infrastructure alongside existing auth
2. **Phase 2**: Update frontend to support both auth methods
3. **Phase 3**: Migrate existing users to Cognito
4. **Phase 4**: Remove custom JWT authentication
5. **Phase 5**: Clean up legacy authentication code

### User Migration Lambda
```typescript
// Cognito User Migration Lambda Trigger
export const handler = async (event: any) => {
  if (event.triggerSource === 'UserMigration_Authentication') {
    // Validate user against existing system
    const user = await validateExistingUser(event.userName, event.request.password);
    
    if (user) {
      event.response.userAttributes = {
        email: user.email,
        given_name: user.firstName,
        family_name: user.lastName,
        'custom:role': user.role,
        email_verified: 'true'
      };
      event.response.finalUserStatus = 'CONFIRMED';
      event.response.messageAction = 'SUPPRESS';
    }
  }
  
  return event;
};
```

This updated architecture provides:
- **Simplified Authentication**: No custom JWT management
- **Federated Login**: Google and Amazon identity providers
- **Enhanced Security**: AWS-managed security features
- **Scalability**: Built-in scaling and availability
- **Compliance**: Enterprise-grade compliance features
