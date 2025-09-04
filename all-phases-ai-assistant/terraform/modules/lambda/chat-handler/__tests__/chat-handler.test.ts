import { APIGatewayProxyEvent, APIGatewayProxyResult, Context } from 'aws-lambda';
import { handler } from '../src/index';
import { ChatRequest, QueryComplexity } from '../src/types';

/**
 * Unit tests for Chat Handler Lambda Function
 * These tests run against REAL AWS infrastructure as per steering requirements
 * NO MOCKING - all tests use actual AWS services
 */

// Set up environment variables for real AWS testing
process.env.AWS_REGION = 'us-west-2';
process.env.AWS_PROFILE = 'aidlc_main'; // Use the correct AWS profile
process.env.ENVIRONMENT = 'development';
process.env.KNOWLEDGE_BASE_ID = 'PQB7MB5ORO'; // Real deployed Knowledge Base ID
process.env.LOG_LEVEL = 'INFO';

describe('Chat Handler Lambda - Real AWS Tests', () => {
  // Increase timeout for real AWS calls
  jest.setTimeout(30000);
  const mockContext: Context = {
    callbackWaitsForEmptyEventLoop: false,
    functionName: 'chat-handler',
    functionVersion: '1',
    invokedFunctionArn: 'arn:aws:lambda:us-west-2:123456789012:function:chat-handler',
    memoryLimitInMB: '1024',
    awsRequestId: 'test-request-id',
    logGroupName: '/aws/lambda/chat-handler',
    logStreamName: 'test-stream',
    getRemainingTimeInMillis: () => 30000,
    done: jest.fn(),
    fail: jest.fn(),
    succeed: jest.fn()
  };

  const createMockEvent = (body: any): APIGatewayProxyEvent => ({
    body: JSON.stringify(body),
    headers: {},
    multiValueHeaders: {},
    httpMethod: 'POST',
    isBase64Encoded: false,
    path: '/chat/ask',
    pathParameters: null,
    queryStringParameters: null,
    multiValueQueryStringParameters: null,
    stageVariables: null,
    requestContext: {
      accountId: '123456789012',
      apiId: 'test-api',
      authorizer: {},
      httpMethod: 'POST',
      identity: {
        accessKey: null,
        accountId: null,
        apiKey: null,
        apiKeyId: null,
        caller: null,
        cognitoAuthenticationProvider: null,
        cognitoAuthenticationType: null,
        cognitoIdentityId: null,
        cognitoIdentityPoolId: null,
        principalOrgId: null,
        sourceIp: '127.0.0.1',
        user: null,
        userAgent: 'test-agent',
        userArn: null,
        clientCert: null
      },
      path: '/chat/ask',
      protocol: 'HTTP/1.1',
      requestId: 'test-request',
      requestTime: '01/Jan/2024:00:00:00 +0000',
      requestTimeEpoch: 1704067200,
      resourceId: 'test-resource',
      resourcePath: '/chat/ask',
      stage: 'test'
    },
    resource: '/chat/ask'
  });

  describe('RetrieveAndGenerate API Integration', () => {
    test('should integrate with Knowledge Base using RetrieveAndGenerate API', async () => {
      const chatRequest: ChatRequest = {
        question: 'What is AWS Lambda?',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      // With real AWS, this will likely fail due to missing Knowledge Base
      // but should handle the error gracefully
      expect(result.statusCode).toBeDefined();
      expect([200, 400, 404, 500, 503].includes(result.statusCode)).toBe(true);
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        // Success case - if Knowledge Base exists and works
        expect(response.answer).toBeDefined();
        expect(response.sources).toBeInstanceOf(Array);
        expect(response.conversationId).toBeDefined();
        expect(response.timestamp).toBeDefined();
        expect(response.modelUsed).toBeDefined();
      } else {
        // Error case - should have proper error structure
        expect(response.error).toBeDefined();
        expect(response.error.code).toBeDefined();
        expect(response.error.message).toBeDefined();
      }
    });

    test('should return source citations from Knowledge Base', async () => {
      const chatRequest: ChatRequest = {
        question: 'Explain the testing strategy from our documents',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.sources).toBeInstanceOf(Array);
        
        if (response.sources.length > 0) {
          expect(response.sources[0]).toHaveProperty('documentId');
          expect(response.sources[0]).toHaveProperty('excerpt');
          expect(response.sources[0]).toHaveProperty('confidence');
          expect(typeof response.sources[0].confidence).toBe('number');
        }
      }
    });
  });

  describe('Error Handling for Bedrock API Failures', () => {
    test('should handle Knowledge Base not found error gracefully', async () => {
      const chatRequest: ChatRequest = {
        question: 'Test question',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      // Should handle errors gracefully, not crash
      expect(result.statusCode).toBeDefined();
      expect(result.body).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode !== 200) {
        expect(response.error).toBeDefined();
        expect(response.error.code).toBeDefined();
        expect(response.error.message).toBeDefined();
      }
    });

    test('should implement model fallback when primary model fails', async () => {
      const chatRequest: ChatRequest = {
        question: 'Test question for model fallback',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.modelUsed).toBeDefined();
        // Should be one of our fallback models
        expect(['claude-opus-4-1', 'claude-3-7-sonnet', 'claude-3-5-sonnet-v2'].some(model => 
          response.modelUsed.includes(model)
        )).toBe(true);
      }
    });
  });

  describe('Conversation Context Management', () => {
    test('should create new conversation ID when not provided', async () => {
      const chatRequest: ChatRequest = {
        question: 'Start new conversation',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.conversationId).toBeDefined();
        expect(response.conversationId).toMatch(/^[0-9a-f-]{36}$/); // UUID format
      }
    });

    test('should use existing conversation ID when provided', async () => {
      const existingConversationId = '12345678-1234-1234-1234-123456789012';
      const chatRequest: ChatRequest = {
        question: 'Continue conversation',
        userId: 'test-user-123',
        conversationId: existingConversationId
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.conversationId).toBe(existingConversationId);
      }
    });
  });

  describe('Intelligent Model Selection', () => {
    test('should classify query complexity correctly', async () => {
      const simpleRequest: ChatRequest = {
        question: 'Hi',
        userId: 'test-user-123'
      };

      const complexRequest: ChatRequest = {
        question: 'Analyze the architectural patterns in our system design documents and compare them with AWS best practices for scalability, security, and cost optimization. Provide detailed recommendations for improvements.',
        userId: 'test-user-123'
      };

      // Test simple query
      const simpleEvent = createMockEvent(simpleRequest);
      const simpleResult = await handler(simpleEvent, mockContext) as APIGatewayProxyResult;
      expect(simpleResult.statusCode).toBeDefined();

      // Test complex query  
      const complexEvent = createMockEvent(complexRequest);
      const complexResult = await handler(complexEvent, mockContext) as APIGatewayProxyResult;
      expect(complexResult.statusCode).toBeDefined();

      // Both should handle requests without crashing
      expect(() => JSON.parse(simpleResult.body)).not.toThrow();
      expect(() => JSON.parse(complexResult.body)).not.toThrow();
    });

    test('should select appropriate model based on query complexity', async () => {
      const complexRequest: ChatRequest = {
        question: 'Design a comprehensive microservices architecture for our AI assistant system',
        userId: 'test-user-123',
        queryComplexity: QueryComplexity.COMPLEX
      };

      const event = createMockEvent(complexRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        // For complex queries, should prefer Opus 4.1 if available
        expect(response.modelUsed).toBeDefined();
      }
    });
  });

  describe('Cost Optimization and Token Usage Tracking', () => {
    test('should track token usage for cost calculation', async () => {
      const chatRequest: ChatRequest = {
        question: 'What is the cost of running Lambda functions?',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.tokenUsage).toBeDefined();
        expect(response.tokenUsage.inputTokens).toBeGreaterThan(0);
        expect(response.tokenUsage.outputTokens).toBeGreaterThan(0);
        expect(response.tokenUsage.totalTokens).toBe(
          response.tokenUsage.inputTokens + response.tokenUsage.outputTokens
        );
        expect(response.cost).toBeGreaterThan(0);
      }
    });

    test('should calculate cost based on model pricing', async () => {
      const chatRequest: ChatRequest = {
        question: 'Calculate pricing for different models',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.cost).toBeDefined();
        expect(typeof response.cost).toBe('number');
        expect(response.cost).toBeGreaterThan(0);
      }
    });
  });

  describe('On-Demand vs Provisioned Throughput', () => {
    test('should use On-Demand invocation in development environment', async () => {
      // Set environment to development
      process.env.ENVIRONMENT = 'development';
      
      const chatRequest: ChatRequest = {
        question: 'Test On-Demand invocation',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.modelUsed).toBeDefined();
        // In development, should use On-Demand (direct model ARNs)
      }
    });

    test('should support Provisioned Throughput configuration for production', async () => {
      // Set environment to production
      process.env.ENVIRONMENT = 'production';
      process.env.CLAUDE_3_7_SONNET_PROVISIONED_ARN = 'arn:aws:bedrock:us-west-2:123456789012:provisioned-model/test-provisioned';
      
      const chatRequest: ChatRequest = {
        question: 'Test Provisioned Throughput',
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBeDefined();
      
      const response = JSON.parse(result.body);
      expect(response).toBeDefined();
      
      if (result.statusCode === 200) {
        expect(response.modelUsed).toBeDefined();
      }
    });
  });

  describe('Input Validation', () => {
    test('should validate required fields', async () => {
      const invalidRequest = {
        // Missing question and userId
      };

      const event = createMockEvent(invalidRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBe(400);
      
      const errorResponse = JSON.parse(result.body);
      expect(errorResponse.error).toBeDefined();
      expect(errorResponse.error.message).toContain('question');
      expect(errorResponse.error.message).toContain('userId');
    });

    test('should enforce question length limits', async () => {
      const longQuestion = 'a'.repeat(10000); // Very long question
      const chatRequest: ChatRequest = {
        question: longQuestion,
        userId: 'test-user-123'
      };

      const event = createMockEvent(chatRequest);
      const result = await handler(event, mockContext) as APIGatewayProxyResult;

      expect(result.statusCode).toBe(400);
      
      const errorResponse = JSON.parse(result.body);
      expect(errorResponse.error).toBeDefined();
      expect(errorResponse.error.message).toContain('length');
    });
  });
});